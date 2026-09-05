"""Funciones puras del motor: silver, calidad (gate), gold (SCD2), DAX."""
from datetime import date

import pandas as pd
import pytest

from mvde import calidad, dax, gold, proyecto, silver


def test_tipar_auto_convierte_numeros_con_formato_latino_y_fechas():
    df = pd.DataFrame({"monto": ["$ 1.234,50", "2.000,00", "15"], "fecha": ["2025-01-05", "2025-02-10", "2025-03-01"], "txt": ["a", "b", "c"]})
    out, cambios = silver.tipar(df, "auto")
    assert out["monto"].tolist() == [1234.5, 2000.0, 15.0]
    assert pd.api.types.is_datetime64_any_dtype(out["fecha"])
    assert "monto→decimal" in cambios and "fecha→fecha" in cambios


def test_transformar_decodifica_deduplica_y_deriva():
    df = pd.DataFrame({"id": [1, 1, 2], "sexo": [1, 1, 2], "x": [10, 20, 30]})
    out, notas = silver.transformar("t", df, {"decodificar": {"sexo": {"1": "M", "2": "F"}}, "deduplicar": ["id"], "derivar": {"doble": "x * 2"}})
    assert out["sexo"].tolist() == ["M", "F"] and out["doble"].tolist() == [40, 60]
    assert any("deduplicar" in n for n in notas)


def test_despivotear_grupos_mapea_columnas_a_periodos():
    df = pd.DataFrame({"id": [1], "PAY_0": [2], "PAY_2": [0], "BILL1": [100.0], "BILL2": [90.0]})
    out = silver.despivotear_grupos(df, {"id": ["id"], "periodo": "mes", "grupos": {"pago": {"sep": "PAY_0", "ago": "PAY_2"}, "monto": {"sep": "BILL1", "ago": "BILL2"}}})
    assert len(out) == 2
    assert out.loc[out.mes == "sep", "pago"].iloc[0] == 2 and out.loc[out.mes == "ago", "monto"].iloc[0] == 90.0


def test_calidad_gate_corta_con_critica_y_no_con_informativa():
    tablas = {"c": pd.DataFrame({"id": [1, 1, 2], "edad": [30, 200, 40]})}
    spec = {"calidad": {"criticos_cortan": True, "reglas": [
        {"tabla": "c", "columna": "id", "tipo": "unico", "critico": True, "dimension": "unicidad"},
        {"tabla": "c", "columna": "edad", "tipo": "rango", "min": 18, "max": 100, "critico": False, "dimension": "validez"}]}}
    res = calidad.correr(spec, tablas)
    assert not res["paso"] and res["criticas_fallidas"] == ["unico:c.id"]
    spec["calidad"]["reglas"][0]["critico"] = False
    assert calidad.correr(spec, tablas)["paso"]


def test_calidad_referencia_y_expresion():
    tablas = {"a": pd.DataFrame({"k": [1, 2, 9], "x": [1, 2, 3], "y": [2, 4, 7]}), "b": pd.DataFrame({"k": [1, 2]})}
    r1 = calidad.evaluar_regla({"tabla": "a", "columna": "k", "tipo": "referencia", "a": "b.k"}, tablas)
    r2 = calidad.evaluar_regla({"tabla": "a", "tipo": "expresion", "expresion": "y == x * 2"}, tablas)
    assert not r1.paso and "1 huérfanos" in r1.detalle
    assert not r2.paso and "1 filas" in r2.detalle


def test_scd2_abre_version_al_cambiar_y_es_idempotente():
    cfg = {"nombre": "dim_c", "clave": "id", "atributos": ["limite"], "scd": 2}
    v1 = gold.dimension(pd.DataFrame({"id": [1, 2], "limite": [100, 200]}), cfg, None, date(2026, 1, 1))
    v2 = gold.dimension(pd.DataFrame({"id": [1, 2], "limite": [100, 200]}), cfg, v1, date(2026, 2, 1))
    assert len(v2) == 2 and (v2["version"] == 1).all()
    v3 = gold.dimension(pd.DataFrame({"id": [1, 2, 3], "limite": [150, 200, 50]}), cfg, v2, date(2026, 3, 1))
    h = v3[v3.id == 1].sort_values("version")
    assert list(h["version"]) == [1, 2] and not h.iloc[0]["is_current"] and h.iloc[1]["limite"] == 150
    assert v3.groupby("id")["is_current"].sum().eq(1).all() and v3["dim_c_key"].is_unique


def test_hecho_no_multiplica_filas_y_resuelve_claves():
    silver_t = {"cli": pd.DataFrame({"id": [1, 2], "n": ["a", "b"]}),
                "pag": pd.DataFrame({"id": [1, 1, 2], "f": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-01-01"]), "m": [1.0, 2.0, 3.0]})}
    spec = {"modelo": {"dimensiones": [{"nombre": "dim_cli", "desde": "cli", "clave": "id", "scd": 1}],
                       "hechos": [{"nombre": "fact_pag", "desde": "pag", "fecha": "f", "claves": {"id": "dim_cli"}}], "calendario": "auto"}}
    g, _ = gold.construir(spec, silver_t)
    assert len(g["fact_pag"]) == 3 and set(g["fact_pag"].columns) >= {"dim_cli_key", "fecha_key", "m"}
    assert g["dim_calendario"]["fecha_key"].is_unique and g["fact_pag"]["fecha_key"].isin(g["dim_calendario"]["fecha_key"]).all()


def test_sin_modelo_pasa_las_tablas_tal_cual():
    g, notas = gold.construir({"modelo": {"calendario": None}}, {"x": pd.DataFrame({"a": [1]})})
    assert "tbl_x" in g and "dim_calendario" not in g


def test_dax_genera_divide_y_time_intelligence():
    spec = {"kpis": [{"nombre": "Monto", "tabla": "fact_v", "columna": "m", "agregacion": "sum", "formato": "#,0"},
                     {"nombre": "Ratio %", "tipo": "ratio", "numerador": {"tabla": "fact_v", "columna": "a", "agregacion": "sum"},
                      "denominador": {"tabla": "fact_v", "columna": "b", "agregacion": "sum"}, "formato": "0.0%"}]}
    texto, medidas = dax.generar(spec, ["fact_v", "dim_calendario"])
    nombres = {m["nombre"] for m in medidas}
    assert {"Monto", "Monto total", "Monto % del total", "Monto mes anterior", "Ratio %"} <= nombres
    assert "DIVIDE ( SUM ( fact_v[a] ), SUM ( fact_v[b] ) )" in texto and "DATEADD ( dim_calendario[fecha], -1, MONTH )" in texto


def test_proyecto_valida_con_mensajes_utiles():
    with pytest.raises(proyecto.ProyectoInvalido, match="fuentes"):
        proyecto.normalizar({"nombre": "x"})
    with pytest.raises(proyecto.ProyectoInvalido, match="desconocido"):
        proyecto.normalizar({"nombre": "x", "fuentes": [{"nombre": "a", "tipo": "ftp"}]})
    spec = proyecto.normalizar({"nombre": "x", "fuentes": [{"nombre": "a", "ruta": "a.csv"}]})
    assert spec["fuentes"][0]["tipo"] == "csv" and spec["calidad"]["criticos_cortan"] is True


def test_esqueleto_desde_dataframe_propone_reglas_y_kpis():
    df = pd.DataFrame({"id": [1, 2, 3], "monto": [10.0, 20.0, 30.0], "cat": ["a", "b", "a"]})
    spec = proyecto.esqueleto("ventas", df, "ventas.csv")
    tipos = {(r["tipo"], r.get("columna")) for r in spec["calidad"]["reglas"]}
    assert ("unico", "id") in tipos and ("no_negativo", "monto") in tipos
    assert any(k["agregacion"] == "sum" for k in spec["kpis"])
