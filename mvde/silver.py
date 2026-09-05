# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 3 · Silver: tablas tipadas, conformadas y con una fila por cosa real.

Todo es declarativo (YAML) y cada operación es una función pura sobre un
DataFrame, en este orden: renombrar → tipos → decodificar → fechas →
filtrar → deduplicar → despivotear → derivar → quitar.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

_RE_NUM = re.compile(r"^-?\$?\s?\d{1,3}([.,]\d{3})*([.,]\d+)?$|^-?\d+([.,]\d+)?$")


def _a_numero(s: pd.Series) -> pd.Series:
    txt = s.astype(str).str.strip().str.replace(r"[\$\s]", "", regex=True)
    # Convención decimal: si hay coma después del último punto, es decimal.
    def conv(v: str):
        if v in ("", "nan", "None", "<NA>"):
            return np.nan
        if "," in v and "." in v:
            v = v.replace(".", "").replace(",", ".") if v.rfind(",") > v.rfind(".") else v.replace(",", "")
        elif "," in v:
            v = v.replace(",", ".") if v.count(",") == 1 and len(v.split(",")[1]) != 3 else v.replace(",", "")
        try:
            return float(v)
        except ValueError:
            return np.nan
    return txt.map(conv)


def tipar(df: pd.DataFrame, tipos: dict | str | None = "auto") -> tuple[pd.DataFrame, list[str]]:
    """Tipos explícitos ({col: entero|decimal|texto|fecha|booleano}) o
    inferencia sobre columnas de texto que en realidad son número o fecha."""
    df = df.copy()
    cambios: list[str] = []
    if isinstance(tipos, dict):
        for col, tipo in tipos.items():
            if col not in df.columns:
                continue
            if tipo in ("entero", "int"):
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            elif tipo in ("decimal", "float", "numero"):
                df[col] = _a_numero(df[col]) if (df[col].dtype == object or pd.api.types.is_string_dtype(df[col])) else pd.to_numeric(df[col], errors="coerce")
            elif tipo == "fecha":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif tipo in ("booleano", "bool"):
                df[col] = df[col].map(lambda v: str(v).strip().lower() in ("1", "true", "si", "sí", "yes", "y", "t"))
            else:
                df[col] = df[col].astype("string")
            cambios.append(f"{col}→{tipo}")
        return df, cambios
    if tipos in (None, "auto"):
        for col in df.columns:
            s = df[col]
            if not (s.dtype == object or pd.api.types.is_string_dtype(s)):
                continue
            muestra = s.dropna().astype(str).str.strip()
            muestra = muestra[muestra != ""].head(2000)
            if muestra.empty:
                continue
            if muestra.map(lambda v: bool(_RE_NUM.match(v))).mean() > 0.95:
                df[col] = _a_numero(s)
                cambios.append(f"{col}→decimal")
                continue
            fechas = pd.to_datetime(muestra, errors="coerce", format="mixed", dayfirst=False)
            if fechas.notna().mean() > 0.95 and muestra.str.len().median() >= 8:
                df[col] = pd.to_datetime(s, errors="coerce", format="mixed")
                cambios.append(f"{col}→fecha")
    return df, cambios


def despivotear(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Ancho → largo. cfg: {id: [...], columnas: [...] | mapa: {col: etiqueta},
    nombre_variable: 'mes', nombre_valor: 'monto'}"""
    ids = cfg.get("id") or []
    if "mapa" in cfg:
        columnas = list(cfg["mapa"])
        largo = df.melt(id_vars=ids, value_vars=columnas, var_name=cfg.get("nombre_variable", "variable"),
                        value_name=cfg.get("nombre_valor", "valor"))
        largo[cfg.get("nombre_variable", "variable")] = largo[cfg.get("nombre_variable", "variable")].map(cfg["mapa"])
        return largo
    columnas = cfg.get("columnas") or [c for c in df.columns if c not in ids]
    return df.melt(id_vars=ids, value_vars=columnas, var_name=cfg.get("nombre_variable", "variable"),
                   value_name=cfg.get("nombre_valor", "valor"))


def despivotear_grupos(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Varios grupos de columnas que comparten una clave de período:
    cfg: {id: [...], periodo: 'mes', grupos: {pago: {abr: PAY_6, may: PAY_5}, monto: {abr: BILL6, ...}}}"""
    ids = cfg["id"]
    periodo = cfg.get("periodo", "periodo")
    grupos: dict[str, dict] = cfg["grupos"]
    periodos = list(next(iter(grupos.values())))
    partes = []
    for p in periodos:
        parte = df[ids].copy()
        parte[periodo] = p
        for medida, mapa in grupos.items():
            parte[medida] = df[mapa[p]].values
        partes.append(parte)
    return pd.concat(partes, ignore_index=True)


def transformar(nombre: str, df: pd.DataFrame, cfg: dict | None) -> tuple[pd.DataFrame, list[str]]:
    cfg = cfg or {}
    notas: list[str] = []
    out = df.copy()
    if cfg.get("renombrar"):
        out = out.rename(columns=cfg["renombrar"])
        notas.append(f"renombradas {len(cfg['renombrar'])} columnas")
    out, cambios = tipar(out, cfg.get("tipos", "auto"))
    if cambios:
        notas.append("tipos: " + ", ".join(cambios[:12]) + ("…" if len(cambios) > 12 else ""))
    for col, mapa in (cfg.get("decodificar") or {}).items():
        if col in out.columns:
            claves = {str(k): v for k, v in mapa.items()}
            out[col] = out[col].map(lambda v: claves.get(str(int(v)) if isinstance(v, float) and v.is_integer() else str(v), mapa.get("_otros", "Desconocido")))
            notas.append(f"decodificada {col}")
    for col in cfg.get("fechas") or []:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    if cfg.get("filtrar"):
        antes = len(out)
        out = out.query(cfg["filtrar"], engine="python")
        notas.append(f"filtro «{cfg['filtrar']}»: {antes - len(out)} filas fuera")
    if cfg.get("deduplicar"):
        antes = len(out)
        claves = [c for c in cfg["deduplicar"] if c in out.columns]
        out = out.drop_duplicates(subset=claves or None, keep="last")
        notas.append(f"deduplicar por {claves or 'todas'}: {antes - len(out)} duplicados fuera")
    if cfg.get("despivotear"):
        d = cfg["despivotear"]
        out = despivotear_grupos(out, d) if "grupos" in d else despivotear(out, d)
        notas.append(f"despivoteo → {len(out)} filas")
        # Las columnas que nacen en el despivoteo (el período) también pueden ser fechas.
        for col in cfg.get("fechas") or []:
            if col in out.columns and not pd.api.types.is_datetime64_any_dtype(out[col]):
                out[col] = pd.to_datetime(out[col], errors="coerce")
    for col, expr in (cfg.get("derivar") or {}).items():
        try:
            out[col] = out.eval(expr, engine="python")
        except Exception:
            out[col] = eval(expr, {"np": np, "pd": pd}, {"df": out})  # noqa: S307 - expresión del propio YAML
        notas.append(f"derivada {col}")
    if cfg.get("quitar"):
        out = out.drop(columns=[c for c in cfg["quitar"] if c in out.columns])
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].astype("string")
    return out.reset_index(drop=True), notas
