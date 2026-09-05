# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 7 · Gobernanza: catálogo, diccionario, linaje, PII y puntajes.
Sale como JSON (para MV Data Governance / Purview / Collibra) y Excel."""
from __future__ import annotations

import re

import pandas as pd

# Columnas que fabrica el motor (claves surrogadas, historia SCD 2, calendario):
# vienen documentadas de fábrica, así la cobertura mide lo que el negocio debe escribir.
_TECNICAS = {
    "valid_from": "SCD 2 · desde cuándo rige esta versión de la fila",
    "valid_to": "SCD 2 · hasta cuándo rigió (9999-12-31 = vigente)",
    "is_current": "SCD 2 · True en la versión vigente",
    "version": "SCD 2 · número de versión de la clave natural",
    "attr_hash": "SCD 2 · hash de los atributos, detecta cambios",
    "fecha_key": "Clave del calendario (AAAAMMDD)",
    "fecha": "Fecha calendario (una fila por día)",
    "anio": "Año", "trimestre": "Trimestre (T1..T4)", "mes_nro": "Número de mes", "mes": "Mes abreviado",
    "anio_mes": "Año-mes (AAAA-MM)", "anio_mes_orden": "Orden numérico del año-mes",
    "dia_semana": "Día de la semana abreviado", "es_fin_de_semana": "True sábado y domingo",
    "_ingestado_en": "Bronze · momento de la ingesta (UTC)", "_fuente": "Bronze · archivo o consulta de origen", "_hash_fuente": "Bronze · hash del archivo de origen",
}


def descripcion_tecnica(tabla: str, col: str) -> str:
    if col.endswith("_key"):
        return "Clave surrogada de " + col[:-4] if not tabla.startswith("dim_") or col != f"{tabla}_key" else "Clave surrogada de la dimensión"
    if col.endswith("_hash"):
        return _TECNICAS["attr_hash"]
    if tabla in ("dim_calendario", "calendario") or col in ("valid_from", "valid_to", "is_current", "version", "attr_hash", "_ingestado_en", "_fuente", "_hash_fuente"):
        return _TECNICAS.get(col, "")
    return ""


_PII = re.compile(r"(dni|cuit|cuil|cpf|ssn|documento|email|mail|telefono|tel[eé]fono|phone|celular|direccion|address|nombre|apellido|name|surname|tarjeta|card)", re.I)


def catalogo(capas: dict[str, dict[str, pd.DataFrame]], spec: dict) -> pd.DataFrame:
    descripciones = (spec.get("gobernanza") or {}).get("descripciones") or {}
    pii_declaradas = set((spec.get("gobernanza") or {}).get("pii") or [])
    filas = []
    for capa, tablas in capas.items():
        for tabla, df in tablas.items():
            for col in df.columns:
                s = df[col]
                filas.append({
                    "capa": capa, "tabla": tabla, "columna": col, "tipo": str(s.dtype),
                    "nulos_pct": round(100 * float(s.isna().mean()), 2),
                    "distintos": int(s.nunique(dropna=True)),
                    "es_clave": bool(col.endswith("_key") or col.startswith("id_") or col.lower() == "id"),
                    "pii": bool(col in pii_declaradas or f"{tabla}.{col}" in pii_declaradas or _PII.search(col)),
                    "descripcion": descripciones.get(f"{tabla}.{col}", descripciones.get(col, "")) or descripcion_tecnica(tabla, col),
                })
    return pd.DataFrame(filas)


def linaje(spec: dict, silver_cfg: dict, gold: dict[str, pd.DataFrame]) -> list[dict]:
    """Aristas origen → destino, capa por capa, con la operación."""
    aristas = []
    for f in spec.get("fuentes", []):
        aristas.append({"desde": f"{f.get('tipo')}:{f.get('ruta') or f.get('url', '')}", "hasta": f"bronze.{f['nombre']}", "operacion": "ingesta"})
        aristas.append({"desde": f"bronze.{f['nombre']}", "hasta": f"silver.{f['nombre']}",
                        "operacion": ", ".join(k for k in (silver_cfg.get(f["nombre"]) or {}) if k != "tipos") or "tipado"})
    modelo = spec.get("modelo") or {}
    for d in modelo.get("dimensiones", []) or []:
        aristas.append({"desde": f"silver.{d['desde']}", "hasta": f"gold.{d['nombre']}", "operacion": f"dimensión SCD{d.get('scd', 1)}"})
    for h in modelo.get("hechos", []) or []:
        aristas.append({"desde": f"silver.{h['desde']}", "hasta": f"gold.{h['nombre']}", "operacion": "hecho"})
        for _col, dim in (h.get("claves") or {}).items():
            aristas.append({"desde": f"gold.{dim}", "hasta": f"gold.{h['nombre']}", "operacion": "clave surrogada"})
    if not modelo.get("dimensiones") and not modelo.get("hechos"):
        for t in gold:
            if t.startswith("tbl_"):
                aristas.append({"desde": f"silver.{t[4:]}", "hasta": f"gold.{t}", "operacion": "copia"})
    for v in (spec.get("vistas") or {}):
        aristas.append({"desde": "gold.*", "hasta": f"gold.{v}", "operacion": "vista"})
    for k in spec.get("kpis") or []:
        aristas.append({"desde": f"gold.{k.get('tabla', '*')}", "hasta": f"kpi.{k['nombre']}", "operacion": k.get("agregacion", k.get("tipo", ""))})
    return aristas


def puntajes(calidad: dict, cat: pd.DataFrame) -> dict:
    doc = round(100 * float((cat["descripcion"] != "").mean()), 1) if len(cat) else 0.0
    return {
        "calidad": calidad.get("puntaje"),
        "por_dimension": {d: v.get("puntaje") for d, v in (calidad.get("por_dimension") or {}).items()},
        "documentacion_pct": doc,
        "columnas_pii": int(cat["pii"].sum()) if len(cat) else 0,
        "tablas": int(cat[["capa", "tabla"]].drop_duplicates().shape[0]) if len(cat) else 0,
    }
