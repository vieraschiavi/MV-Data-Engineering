"""Salud por área, sugerencias con parche, antes/después y target automático."""
import pandas as pd
import pytest
import yaml

from mvde import demos, proyecto, salud
from mvde.orquestador import Pipeline


@pytest.fixture(scope="module")
def pelado(tmp_path_factory):
    """La demo de ventas con el YAML reducido al mínimo: sin reglas, sin KPIs, sin dueño, sin ML."""
    carpeta = tmp_path_factory.mktemp("pelado")
    ruta = demos.crear("ventas", carpeta)
    spec = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    spec["calidad"] = {"criticos_cortan": True, "reglas": []}
    spec["kpis"] = []
    spec["gobernanza"] = {}
    spec["ml"] = None
    spec["vistas"] = {}
    ruta.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    p = Pipeline.desde_yaml(ruta)
    p.correr()
    return p


def test_kpis_automaticos_cuando_no_hay(pelado):
    assert pelado.resultados["reporte"].ok and pelado.kpis and pelado.spec.get("_kpis_automaticos")
    assert pelado.resultados["dax"].evidencia["medidas"]


def test_salud_evalua_todas_las_areas(pelado):
    ev = salud.evaluar(pelado)
    assert 0 < ev["total"] <= 100 and {"datos", "calidad", "modelo", "gobernanza", "bi"} <= set(ev["areas"])
    assert (pelado.salida / "salud_historial.json").exists()


def test_sugerencias_traen_parches_y_mejoran_la_salud(pelado):
    antes = salud.evaluar(pelado)
    sugs = salud.sugerencias(pelado)
    codigos = {s["codigo"] for s in sugs}
    assert {"regla_unico", "regla_referencia", "sin_dueno", "sin_kpis", "target"} <= codigos, codigos
    nuevo, n = salud.aplicar_todas(pelado.spec, sugs)
    assert n >= 5
    assert nuevo["gobernanza"]["dueno"] and nuevo["kpis"] and nuevo["ml"]["target"]
    assert any(r["tipo"] == "referencia" for r in nuevo["calidad"]["reglas"])
    assert not (pelado.spec.get("gobernanza") or {}).get("dueno")   # no muta el original
    proyecto.guardar(nuevo, pelado.spec["_ruta"])
    p2 = Pipeline.desde_yaml(pelado.spec["_ruta"])
    res = p2.correr()
    assert all(r.ok for r in res.values()), {e: r.estado() for e, r in res.items()}
    despues = salud.evaluar(p2)
    assert despues["total"] > antes["total"]
    ad = salud.antes_despues(p2)
    assert ad and ad["delta_total"] > 0 and ad["despues"]["total"] == despues["total"]


def test_sugerir_target_prefiere_binarias_con_nombre():
    df = pd.DataFrame({"id": range(100), "default_flag": [0, 1] * 50, "monto": range(100), "categoria": ["a", "b"] * 50})
    c = salud.sugerir_target(df)
    assert c[0]["columna"] == "default_flag" and c[0]["tipo"] == "clasificacion"
    assert any(x["columna"] == "monto" and x["tipo"] == "regresion" for x in c)


def test_aplicar_no_muta_y_es_idempotente():
    spec = {"nombre": "x", "fuentes": [{"nombre": "a", "ruta": "a.csv"}]}
    sug = {"parche": {"regla": {"tabla": "a", "columna": "id", "tipo": "unico", "critico": True}}}
    n1 = salud.aplicar(spec, sug)
    assert "calidad" not in spec and len(n1["calidad"]["reglas"]) == 1


def test_dimension_pasa_de_scd1_a_scd2_sin_romper():
    """Subir una dimensión a SCD 2 con un parquet previo de SCD 1 (sin is_current) arranca la historia."""
    from mvde import gold
    df = pd.DataFrame({"sku": ["a", "b"], "precio": [1.0, 2.0]})
    previa = gold.dimension(df, {"nombre": "dim_p", "clave": "sku", "scd": 1})
    assert "is_current" not in previa.columns
    nueva = gold.dimension(df, {"nombre": "dim_p", "clave": "sku", "scd": 2}, existente=previa)
    assert nueva["is_current"].all() and (nueva["version"] == 1).all() and len(nueva) == 2
