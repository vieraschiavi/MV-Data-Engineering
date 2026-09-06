# © 2026 Martín Viera. Todos los derechos reservados.
"""El proyecto: un YAML que declara fuentes, capas, calidad, modelo, KPIs.

`cargar()` lo lee y lo valida con mensajes accionables; `esqueleto()` genera
uno a partir de un DataFrame para arrancar cualquier proyecto en un minuto.
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

TIPOS_FUENTE = {"csv", "excel", "parquet", "json", "sqlite", "sql", "url", "kaggle", "carpeta", "duckdb"}
TIPOS_REGLA = {"no_nulo", "unico", "rango", "valores", "regex", "filas_min", "filas_exactas",
               "referencia", "fresco", "positivo", "no_negativo", "expresion"}
AGREGACIONES = {"sum", "count", "count_distinct", "avg", "min", "max"}

PLANTILLA = {
    "nombre": "Mi proyecto",
    "descripcion": "",
    "idioma": "es",
    "salida": "salidas",
    "fuentes": [],
    "silver": {},
    "calidad": {"criticos_cortan": True, "reglas": []},
    "modelo": {"dimensiones": [], "hechos": [], "calendario": "auto"},
    "vistas": {},
    "kpis": [],
    "gobernanza": {"dueno": "", "pii": [], "descripciones": {}},
    # Cada cuánto se espera dato nuevo. Por tabla se afina en `frescura.tablas`.
    "frescura": {"cada": "diaria", "tablas": {}},
    "ml": None,
    "reporte": {"titulo": "", "graficos": "auto"},
    "powerbi": {"generar": True, "nombre": ""},
    "automatizacion": {"hora": "05:00", "reintentos": 3},
}


class ProyectoInvalido(ValueError):
    pass


def cargar(ruta: str | Path) -> dict:
    ruta = Path(ruta)
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ProyectoInvalido(f"YAML mal formado en {ruta.name}: {exc}") from exc
    spec = normalizar(datos)
    spec["_ruta"] = str(ruta.resolve())
    spec["_base"] = str(ruta.resolve().parent)
    return spec


def desde_texto(texto: str, base: str | Path = ".") -> dict:
    try:
        datos = yaml.safe_load(texto) or {}
    except yaml.YAMLError as exc:
        raise ProyectoInvalido(f"YAML mal formado: {exc}") from exc
    spec = normalizar(datos)
    spec["_ruta"] = ""
    spec["_base"] = str(Path(base).resolve())
    return spec


def normalizar(datos: dict) -> dict:
    """Completa defaults y valida lo mínimo para que cada etapa no adivine."""
    if not isinstance(datos, dict):
        raise ProyectoInvalido("el proyecto tiene que ser un mapa YAML (clave: valor)")
    spec = copy.deepcopy(PLANTILLA)
    for k, v in datos.items():
        if isinstance(v, dict) and isinstance(spec.get(k), dict):
            spec[k] = {**spec[k], **v}
        else:
            spec[k] = v
    if not spec.get("nombre"):
        raise ProyectoInvalido("falta `nombre`")
    if not spec.get("fuentes"):
        raise ProyectoInvalido("falta `fuentes`: al menos una fuente de datos")
    nombres = set()
    for i, f in enumerate(spec["fuentes"]):
        if not isinstance(f, dict) or not f.get("nombre"):
            raise ProyectoInvalido(f"la fuente #{i + 1} no tiene `nombre`")
        if f.get("tipo", "csv") not in TIPOS_FUENTE:
            raise ProyectoInvalido(f"fuente «{f['nombre']}»: tipo `{f.get('tipo')}` desconocido; válidos: {sorted(TIPOS_FUENTE)}")
        if f["nombre"] in nombres:
            raise ProyectoInvalido(f"dos fuentes se llaman «{f['nombre']}»")
        nombres.add(f["nombre"])
        f.setdefault("tipo", "csv")
    for r in spec["calidad"].get("reglas", []) or []:
        if r.get("tipo") not in TIPOS_REGLA:
            raise ProyectoInvalido(f"regla de calidad con tipo `{r.get('tipo')}` desconocido; válidos: {sorted(TIPOS_REGLA)}")
        if not r.get("tabla"):
            raise ProyectoInvalido(f"regla `{r.get('tipo')}` sin `tabla`")
        r.setdefault("critico", True)
        r.setdefault("dimension", _dimension_por_defecto(r["tipo"]))
    for k in spec["kpis"] or []:
        if not k.get("nombre"):
            raise ProyectoInvalido("hay un KPI sin `nombre`")
        if k.get("tipo", "agregacion") == "agregacion":
            if k.get("agregacion", "sum") not in AGREGACIONES:
                raise ProyectoInvalido(f"KPI «{k['nombre']}»: agregación `{k.get('agregacion')}` desconocida")
            if not k.get("tabla"):
                raise ProyectoInvalido(f"KPI «{k['nombre']}» sin `tabla`")
    for d in spec["modelo"].get("dimensiones", []) or []:
        for campo in ("nombre", "desde", "clave"):
            if not d.get(campo):
                raise ProyectoInvalido(f"dimensión sin `{campo}`: {d}")
        d.setdefault("scd", 1)
    for h in spec["modelo"].get("hechos", []) or []:
        for campo in ("nombre", "desde"):
            if not h.get(campo):
                raise ProyectoInvalido(f"hecho sin `{campo}`: {h}")
        h.setdefault("claves", {})
    return spec


def _dimension_por_defecto(tipo: str) -> str:
    return {"no_nulo": "completitud", "filas_min": "completitud", "filas_exactas": "completitud",
            "unico": "unicidad", "referencia": "consistencia", "fresco": "oportunidad",
            "expresion": "exactitud"}.get(tipo, "validez")


def a_yaml(spec: dict) -> str:
    limpio = {k: v for k, v in spec.items() if not k.startswith("_")}
    return yaml.safe_dump(limpio, sort_keys=False, allow_unicode=True, width=100)


def guardar(spec: dict, ruta: str | Path) -> Path:
    ruta = Path(ruta)
    ruta.write_text(a_yaml(spec), encoding="utf-8")
    return ruta


def esqueleto(nombre_tabla: str, df, ruta_archivo: str, tipo: str = "csv") -> dict:
    """Un proyecto arrancado desde un DataFrame: tipado automático, reglas
    sugeridas (clave única, no nulos en columnas llenas, rangos), calendario
    automático y un KPI de conteo. Es el punto de partida, no el final."""
    import pandas as pd

    reglas = [{"tabla": nombre_tabla, "tipo": "filas_min", "valor": max(1, int(len(df) * 0.5)), "critico": True}]
    kpis = [{"nombre": f"{nombre_tabla} · filas", "tabla": nombre_tabla, "agregacion": "count", "formato": "#,0"}]
    clave = None
    for col in df.columns:
        s = df[col]
        if s.isna().mean() == 0:
            reglas.append({"tabla": nombre_tabla, "columna": col, "tipo": "no_nulo", "critico": False})
        if clave is None and s.is_unique and s.notna().all() and (
                pd.api.types.is_integer_dtype(s) or pd.api.types.is_string_dtype(s)):
            clave = col
            reglas.append({"tabla": nombre_tabla, "columna": col, "tipo": "unico", "critico": True})
        if pd.api.types.is_numeric_dtype(s) and s.notna().any() and col != clave:
            kpis.append({"nombre": f"{col} · total", "tabla": nombre_tabla, "columna": col,
                         "agregacion": "sum", "formato": "#,0"})
            if (s.dropna() >= 0).all():
                reglas.append({"tabla": nombre_tabla, "columna": col, "tipo": "no_negativo", "critico": False})
    spec = copy.deepcopy(PLANTILLA)
    spec.update({
        "nombre": nombre_tabla,
        "fuentes": [{"nombre": nombre_tabla, "tipo": tipo, "ruta": ruta_archivo}],
        "silver": {nombre_tabla: {"tipos": "auto", "deduplicar": [clave] if clave else []}},
        "calidad": {"criticos_cortan": True, "reglas": reglas},
        "kpis": kpis[:8],
        "reporte": {"titulo": nombre_tabla, "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": nombre_tabla},
    })
    return normalizar(spec)
