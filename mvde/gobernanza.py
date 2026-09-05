# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 7 · Gobernanza: catálogo, diccionario, linaje, PII y puntajes.
Sale como JSON (para MV Data Governance / Purview / Collibra) y Excel."""
from __future__ import annotations

import re

import pandas as pd

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
                    "descripcion": descripciones.get(f"{tabla}.{col}", descripciones.get(col, "")),
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
