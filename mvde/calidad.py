# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 4 · Calidad: reglas declaradas + reglas automáticas, por dimensión,
con gate. Cada resultado es JSON-serializable y lleva el nombre de la regla,
la dimensión, si pasó, el detalle y si es crítica.

Tipos de regla (YAML `calidad.reglas`):
  no_nulo, unico, rango(min,max), valores(lista), regex(patron), positivo,
  no_negativo, filas_min(valor), filas_exactas(valor), referencia(a: tabla.col),
  fresco(dias, columna), expresion(expr pandas que debe ser verdadera en toda fila)
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import pandas as pd

DIMENSIONES = ["completitud", "unicidad", "validez", "consistencia", "exactitud", "oportunidad"]


@dataclass(frozen=True)
class Resultado:
    regla: str
    tabla: str
    columna: str
    dimension: str
    paso: bool
    detalle: str
    critico: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "paso", bool(self.paso))


def _col(df: pd.DataFrame, r: dict) -> pd.Series | None:
    c = r.get("columna")
    return df[c] if c and c in df.columns else None


def evaluar_regla(r: dict, tablas: dict[str, pd.DataFrame]) -> Resultado:
    tabla, tipo = r["tabla"], r["tipo"]
    nombre = f"{tipo}:{tabla}" + (f".{r['columna']}" if r.get("columna") else "")
    base = dict(regla=nombre, tabla=tabla, columna=r.get("columna", ""), dimension=r.get("dimension", "validez"),
                critico=bool(r.get("critico", True)))
    df = tablas.get(tabla)
    if df is None:
        return Resultado(paso=False, detalle=f"tabla «{tabla}» no existe en silver", **base)
    s = _col(df, r)
    if tipo not in ("filas_min", "filas_exactas", "expresion") and s is None:
        return Resultado(paso=False, detalle=f"columna «{r.get('columna')}» no existe", **base)
    if tipo == "no_nulo":
        n = int(s.isna().sum())
        return Resultado(paso=n == 0, detalle=f"{n} nulos", **base)
    if tipo == "unico":
        n = int(s.duplicated().sum())
        return Resultado(paso=n == 0, detalle=f"{n} duplicados", **base)
    if tipo == "rango":
        v = pd.to_numeric(s, errors="coerce")
        fuera = int(((v < r.get("min", -float("inf"))) | (v > r.get("max", float("inf")))).sum())
        return Resultado(paso=fuera == 0, detalle=f"{fuera} valores fuera de [{r.get('min')}, {r.get('max')}]", **base)
    if tipo == "valores":
        permitidos = {str(x) for x in r.get("valores", [])}
        fuera = int((~s.dropna().astype(str).isin(permitidos)).sum())
        return Resultado(paso=fuera == 0, detalle=f"{fuera} valores fuera de {sorted(permitidos)[:8]}", **base)
    if tipo == "regex":
        pat = re.compile(r["patron"])
        fuera = int((~s.dropna().astype(str).map(lambda v: bool(pat.match(v)))).sum())
        return Resultado(paso=fuera == 0, detalle=f"{fuera} valores no cumplen /{r['patron']}/", **base)
    if tipo in ("positivo", "no_negativo"):
        v = pd.to_numeric(s, errors="coerce")
        fuera = int((v <= 0).sum()) if tipo == "positivo" else int((v < 0).sum())
        return Resultado(paso=fuera == 0, detalle=f"{fuera} valores {'≤ 0' if tipo == 'positivo' else '< 0'}", **base)
    if tipo == "filas_min":
        return Resultado(paso=len(df) >= r["valor"], detalle=f"{len(df)} filas (mínimo {r['valor']})", **base)
    if tipo == "filas_exactas":
        return Resultado(paso=len(df) == r["valor"], detalle=f"{len(df)} filas (esperadas {r['valor']})", **base)
    if tipo == "referencia":
        t2, c2 = str(r["a"]).split(".", 1)
        if t2 not in tablas or c2 not in tablas[t2].columns:
            return Resultado(paso=False, detalle=f"referencia {r['a']} no existe", **base)
        huer = int((~s.dropna().isin(tablas[t2][c2].dropna())).sum())
        return Resultado(paso=huer == 0, detalle=f"{huer} huérfanos contra {r['a']}", **base)
    if tipo == "fresco":
        fechas = pd.to_datetime(s, errors="coerce")
        ultimo = fechas.max()
        dias = (pd.Timestamp.now() - ultimo).days if pd.notna(ultimo) else 10**6
        return Resultado(paso=dias <= r.get("dias", 1), detalle=f"último dato hace {dias} días (tope {r.get('dias', 1)})", **base)
    if tipo == "expresion":
        try:
            ok = df.eval(r["expresion"], engine="python")
            fuera = int((~ok.astype(bool)).sum())
            return Resultado(paso=fuera == 0, detalle=f"{fuera} filas no cumplen «{r['expresion']}»", **base)
        except Exception as exc:  # noqa: BLE001 - la expresión es del usuario
            return Resultado(paso=False, detalle=f"expresión inválida: {exc}", **base)
    return Resultado(paso=False, detalle=f"tipo `{tipo}` desconocido", **base)


def reglas_automaticas(tablas: dict[str, pd.DataFrame]) -> list[dict]:
    """Lo mínimo que se controla siempre aunque el YAML no diga nada:
    que cada tabla tenga filas y que ninguna columna esté 100 % vacía."""
    reglas = []
    for nombre, df in tablas.items():
        reglas.append({"tabla": nombre, "tipo": "filas_min", "valor": 1, "critico": True,
                       "dimension": "completitud"})
        for col in df.columns:
            if df[col].isna().all():
                reglas.append({"tabla": nombre, "columna": col, "tipo": "no_nulo", "critico": False,
                               "dimension": "completitud"})
    return reglas


def correr(spec: dict, tablas: dict[str, pd.DataFrame]) -> dict:
    declaradas = list(spec.get("calidad", {}).get("reglas", []) or [])
    todas = declaradas + [r for r in reglas_automaticas(tablas)
                          if not any(d["tabla"] == r["tabla"] and d["tipo"] == r["tipo"] and d.get("columna") == r.get("columna")
                                     for d in declaradas)]
    resultados = [evaluar_regla(r, tablas) for r in todas]
    por_dim = {}
    for d in DIMENSIONES:
        rs = [x for x in resultados if x.dimension == d]
        por_dim[d] = {"reglas": len(rs), "ok": sum(x.paso for x in rs),
                      "puntaje": round(100 * sum(x.paso for x in rs) / len(rs), 1) if rs else None}
    criticos_fallidos = [x for x in resultados if x.critico and not x.paso]
    return {
        "paso": not criticos_fallidos if spec.get("calidad", {}).get("criticos_cortan", True) else True,
        "puntaje": round(100 * sum(x.paso for x in resultados) / len(resultados), 1) if resultados else 100.0,
        "reglas": len(resultados),
        "fallidas": [asdict(x) for x in resultados if not x.paso],
        "criticas_fallidas": [x.regla for x in criticos_fallidos],
        "por_dimension": por_dim,
        "resultados": [asdict(x) for x in resultados],
    }
