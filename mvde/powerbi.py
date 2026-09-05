# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 11 · Power BI: .pbit + PBIP desde los CSV de gold, con el motor MV DAX
Lab (`daxlingo/dxl`, en este mismo repositorio). Sin Windows ni Desktop."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

RUTA_DATOS_DEFECTO = "C:\\MVDataEngineering\\gold\\"


def _dxl():
    candidatos = [Path(__file__).resolve().parents[2] / "daxlingo", Path.cwd() / "daxlingo",
                  Path(__file__).resolve().parents[1] / "daxlingo"]
    for c in candidatos:
        if (c / "dxl").exists():
            if str(c) not in sys.path:
                sys.path.insert(0, str(c))
            break
    from dxl import catalogo, dataset, tablero, transformador  # noqa: E402
    from dxl import modelo as modmod  # noqa: E402
    return catalogo, dataset, tablero, transformador, modmod


def disponible() -> bool:
    try:
        _dxl()
        return True
    except ImportError:
        return False


def _inyectar_medidas(modelo: dict, medidas: list[dict]) -> None:
    tablas = {t["name"]: t for t in modelo["model"]["tables"]}
    for m in medidas:
        t = tablas.get(m["tabla"])
        if t is None:
            continue
        t.setdefault("measures", [])
        t["measures"] = [x for x in t["measures"] if x.get("name") != m["nombre"]]
        t["measures"].append({"name": m["nombre"], "expression": m["expresion"], "formatString": m["formato"],
                              "description": m.get("descripcion", "")})


def _relaciones(modelo: dict, spec: dict, gold: dict[str, pd.DataFrame]) -> None:
    rels = []
    dims = {d["nombre"]: d for d in (spec.get("modelo") or {}).get("dimensiones", []) or []}
    for h in (spec.get("modelo") or {}).get("hechos", []) or []:
        for _col, dim in (h.get("claves") or {}).items():
            if dim in dims and dim in gold:
                rels.append((h["nombre"], f"{dim}_key", dim, f"{dim}_key"))
        if "dim_calendario" in gold and "fecha_key" in gold.get(h["nombre"], pd.DataFrame()).columns:
            rels.append((h["nombre"], "fecha_key", "dim_calendario", "fecha_key"))
    if not rels:
        for nombre, df in gold.items():
            if nombre != "dim_calendario" and "dim_calendario" in gold and "fecha_key" in df.columns:
                rels.append((nombre, "fecha_key", "dim_calendario", "fecha_key"))
    if rels:
        modelo["model"]["relationships"] = [
            {"name": f"rel_{i}", "fromTable": a, "fromColumn": b, "toTable": c, "toColumn": d, "crossFilteringBehavior": "oneDirection"}
            for i, (a, b, c, d) in enumerate(rels)]


def _pulir(modelo: dict) -> None:
    for t in modelo["model"]["tables"]:
        if t["name"] == "dim_calendario":
            t["dataCategory"] = "Time"
        for c in t.get("columns", []):
            if t["name"] == "dim_calendario" and c["name"] == "fecha":
                c["isKey"] = True
            if t["name"] == "dim_calendario" and c["name"] == "mes":
                c["sortByColumn"] = "mes_nro"
            if t["name"] == "dim_calendario" and c["name"] == "anio_mes":
                c["sortByColumn"] = "anio_mes_orden"
            if c["name"].endswith("_key") or c["name"] in ("attr_hash", "anio_mes_orden", "version"):
                c["isHidden"] = True
            elif c.get("dataType") == "dateTime" and not c.get("formatString"):
                c["formatString"] = "dd/mm/yyyy"
            elif c.get("dataType") in ("double", "int64") and not c.get("formatString"):
                c["formatString"] = "#,0.00" if c["dataType"] == "double" else "#,0"
            if t["name"].startswith("dim_") and c.get("dataType") in ("int64", "double"):
                c["summarizeBy"] = "none"


def _parametrizar(modelo: dict, carpeta: str) -> None:
    for t in modelo["model"]["tables"]:
        for part in t.get("partitions", []):
            src = part.get("source", {})
            expr = src.get("expression")
            if isinstance(expr, list):
                src["expression"] = [ln.replace(f'"{carpeta}', 'DataPath & "') for ln in expr]
            elif isinstance(expr, str):
                src["expression"] = expr.replace(f'"{carpeta}', 'DataPath & "')
    modelo["model"]["tables"].append({
        "name": "DataPath", "isHidden": True,
        "columns": [{"name": "DataPath", "dataType": "string", "sourceColumn": "DataPath"}],
        "partitions": [{"name": "DataPath", "mode": "import", "source": {"type": "m", "expression": [
            f'"{RUTA_DATOS_DEFECTO}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]']}}],
    })


def generar(spec: dict, gold: dict[str, pd.DataFrame], medidas: list[dict], carpeta_csv: Path,
            salida: Path, nombre: str, embebido: bool = False, idioma: str = "es") -> dict:
    catalogo, dataset, tablero, transformador, modmod = _dxl()
    carpeta_csv.mkdir(parents=True, exist_ok=True)
    archivos = []
    for t, df in gold.items():
        p = carpeta_csv / f"{t}.csv"
        (df.head(45_000) if embebido else df).to_csv(p, index=False)
        archivos.append(p)
    cargado = dataset.cargar_varios(archivos, idioma, embebido=embebido)
    modelo = cargado["modelo"]
    _inyectar_medidas(modelo, medidas)
    _relaciones(modelo, spec, gold)
    _pulir(modelo)
    if embebido:
        modelo, _ = dataset.empotrar(modelo, cargado.get("dataset_meta"), idioma)
    else:
        _parametrizar(modelo, carpeta_csv.resolve().as_posix() + "/")
    modelo, _ = transformador.crear_tabla_medidas(modelo, idioma, nombre="_Medidas")
    cat = catalogo.Catalogo.desde_modelo(modelo)
    try:
        layout = tablero.disenar_auto(cat, titulo=nombre, idioma=idioma)
    except ValueError:
        layout = None
    salida.mkdir(parents=True, exist_ok=True)
    pbit = modmod.exportar_pbit(modelo, layout, salida / f"{nombre}.pbit", descripcion="Generado por MV Data Engineering")
    pbip = salida / f"{nombre}_pbip"
    if pbip.exists():
        shutil.rmtree(pbip)
    modmod.exportar_pbip(modelo, layout, pbip, nombre)
    from dxl import analizador
    hallazgos = analizador.analizar(cat)
    return {"pbit": str(pbit), "pbip": str(pbip), "tablas": len(modelo["model"]["tables"]),
            "medidas": len(medidas), "relaciones": len(modelo["model"].get("relationships", [])),
            "auditoria": analizador.puntaje(hallazgos), "hallazgos": [(h["regla"], h["objeto"]) for h in hallazgos]}
