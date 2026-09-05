"""Las dos demos corren las 12 etapas; el gate corta; se reanuda desde una etapa."""
import json
import zipfile
from pathlib import Path

import pytest
import yaml

from mvde import ETAPAS, demos
from mvde.orquestador import Pipeline


@pytest.fixture(scope="module")
def cobranzas(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("cob")
    ruta = demos.crear("cobranzas", carpeta)
    p = Pipeline.desde_yaml(ruta)
    p.correr()
    return p


def test_demo_cobranzas_corre_las_doce_etapas(cobranzas):
    estados = {e: cobranzas.resultados[e].estado() for e in ETAPAS}
    assert all(v == "ok" for v in estados.values()), estados
    assert (cobranzas.dirs["entrega"] / "RESUMEN.md").exists()
    assert json.loads(cobranzas._estado_path().read_text())["etapas"]["entrega"]["ok"]


def test_demo_cobranzas_productos_coherentes(cobranzas):
    r = cobranzas.resultados
    assert r["calidad"].evidencia["puntaje"] >= 80 and r["calidad"].evidencia["fallidas"]  # el defecto inyectado se ve
    assert r["gold"].evidencia["tablas"]["dim_cliente"] == 4000
    assert any(k["nombre"] == "Tasa de default %" for k in r["reporte"].evidencia["kpis"])
    assert r["ml"].evidencia["metricas"]["auc"] > 0.6
    assert r["powerbi"].evidencia["auditoria"] >= 90
    pbit = next(Path(a) for a in r["powerbi"].artefactos if a.endswith("Cobranzas.pbit"))
    modelo = json.loads(zipfile.ZipFile(pbit).read("DataModelSchema").decode("utf-16-le"))["model"]
    nombres = {t["name"] for t in modelo["tables"]}
    assert {"dim_cliente", "fact_cuota", "dim_calendario", "_Medidas"} <= nombres
    assert len(modelo["relationships"]) >= 3


def test_gate_corta_y_las_siguientes_no_corren(tmp_path):
    ruta = demos.crear("cobranzas", tmp_path)
    spec = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    spec["calidad"]["reglas"].append({"tabla": "clientes", "columna": "edad", "tipo": "rango", "min": 30, "max": 40, "critico": True})
    ruta.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    p = Pipeline.desde_yaml(ruta)
    res = p.correr()
    assert res["calidad"].estado() == "fallo" and "gold" not in res
    # se arregla la regla y se reanuda desde calidad, sin releer las fuentes
    spec["calidad"]["reglas"].pop()
    ruta.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    p2 = Pipeline.desde_yaml(ruta)
    res2 = p2.correr(desde="calidad", hasta="almacen")
    assert res2["calidad"].ok and res2["almacen"].ok and "reporte" not in res2


def test_demo_ventas_tres_formatos_de_origen(tmp_path):
    ruta = demos.crear("ventas", tmp_path)
    p = Pipeline.desde_yaml(ruta)
    res = p.correr(hasta="reporte")
    assert all(res[e].ok for e in ETAPAS[:ETAPAS.index("reporte") + 1]), {e: r.estado() for e, r in res.items()}
    assert res["fuentes"].evidencia["sucursales"]["columnas"] == 3      # csv con ';' bien partido
    assert any("duplicados" in n for n in res["silver"].evidencia["ventas"]["notas"])


def test_cli_validar_y_automatizar(tmp_path):
    from mvde.cli import main
    ruta = demos.crear("ventas", tmp_path)
    assert main(["validar", str(ruta)]) == 0
    assert main(["automatizar", str(ruta)]) == 0
    assert (tmp_path / "dag_airflow.py").exists() and (tmp_path / "correr_pipeline.bat").exists()
    compile((tmp_path / "dag_airflow.py").read_text(encoding="utf-8"), "dag", "exec")
