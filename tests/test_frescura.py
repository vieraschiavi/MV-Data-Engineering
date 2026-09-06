"""Monitoreo de cargas: fecha del dato vs. fecha de carga, estado, historial y
frecuencia real medida."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from mvde import demos, frescura
from mvde.orquestador import Pipeline


@pytest.fixture(scope="module")
def cob(tmp_path_factory):
    ruta = demos.crear("cobranzas", tmp_path_factory.mktemp("frescura"))
    p = Pipeline.desde_yaml(ruta)
    p.correr()
    return p


def test_cada_tabla_usada_aparece_con_sus_dos_fechas(cob):
    filas = {f["tabla"]: f for f in cob.frescura}
    assert {"clientes", "cuotas", "fact_cuota"} <= set(filas)
    cuotas = filas["cuotas"]
    # La fecha de carga sale del sello que bronze escribe en la ingesta.
    assert cuotas["fecha_carga"] and cuotas["filas"] == 48_000
    # La fecha del dato sale de la columna de fecha del negocio, no de la carga.
    assert cuotas["fecha_datos"] and cuotas["columna_fecha"] == "fecha_vencimiento"
    assert cuotas["fecha_datos"][:4] == "2025"
    assert cuotas["fecha_carga"] > cuotas["fecha_datos"], "cargar es posterior a los datos que trae"


def test_tabla_sin_columna_de_fecha_se_juzga_por_la_carga(cob):
    clientes = next(f for f in cob.frescura if f["tabla"] == "clientes")
    assert clientes["fecha_datos"] is None and clientes["fecha_carga"]
    assert clientes["estado"] == "actualizada", "recién ingestada: la carga es de hace segundos"


def test_la_demo_declara_la_frecuencia_de_cada_tabla(cob):
    filas = {f["tabla"]: f for f in cob.frescura}
    assert filas["clientes"]["cada"] == "diaria"
    assert filas["cuotas"]["cada"] == "mensual", "las cuotas son mensuales, no diarias"
    assert filas["cuotas"]["tolerancia_horas"] > filas["clientes"]["tolerancia_horas"]


def test_el_estado_compara_contra_la_tolerancia_declarada():
    """Un dato de hace tres horas está al día para una carga diaria; el mismo dato
    de hace tres días, no."""
    ahora = datetime(2026, 6, 15, 12, 0)
    df = pd.DataFrame({"f": pd.to_datetime([ahora - timedelta(hours=3)])})
    cfg = frescura._cfg_tabla({"cada": "diaria", "tablas": {}}, "t")
    fresca = frescura._fila("t", "origen", "csv", df, df["f"].max(), "f", None, cfg, ahora, ahora)
    assert fresca["estado"] == "actualizada" and fresca["horas_desde_datos"] == 3.0
    vieja = frescura._fila("t", "origen", "csv", df, ahora - timedelta(days=3), "f", None, cfg, ahora, ahora)
    assert vieja["estado"] == "atrasada" and vieja["horas_desde_datos"] == 72.0


def test_tabla_vacia_se_marca_vacia_aunque_la_carga_sea_de_recien():
    ahora = datetime(2026, 6, 15, 12, 0)
    cfg = frescura._cfg_tabla({"cada": "diaria", "tablas": {}}, "t")
    fila = frescura._fila("t", "origen", "csv", pd.DataFrame({"f": []}), None, None,
                          ahora.replace(tzinfo=timezone.utc), cfg, ahora, ahora.replace(tzinfo=timezone.utc))
    assert fila["estado"] == "vacia" and fila["filas"] == 0


def test_una_fecha_futura_no_cuenta_como_frescura():
    """Un vencimiento a 90 días no significa que el dato llegue hasta dentro de
    tres meses: si contara, toda cartera de créditos aparecería siempre al día."""
    hoy = pd.Timestamp(datetime.now())
    df = pd.DataFrame({"vencimiento": pd.to_datetime([hoy + pd.Timedelta(days=90)]),
                       "pago": pd.to_datetime([hoy - pd.Timedelta(days=2)])})
    tope, col = frescura._fecha_maxima(df)
    assert col == "pago" and tope < hoy


def test_historial_y_frecuencia_real(cob):
    assert (cob.salida / "frescura_historial.json").exists()
    hist = frescura.historial(cob)
    assert hist and "cuotas" in hist[-1]["tablas"]
    # Con una sola fecha observada todavía no hay frecuencia que medir.
    assert frescura.frecuencia_real(hist, "cuotas") is None
    # Con fechas que avanzan un mes, la mediana lo refleja.
    inventado = [{"corrida": f"2026-0{m}-01T06:00:00",
                  "tablas": {"cuotas": {"fecha_datos": f"2026-0{m}-01T00:00:00", "fecha_carga": None,
                                        "filas": 10, "estado": "actualizada"}}} for m in (1, 2, 3, 4)]
    real = frescura.frecuencia_real(inventado, "cuotas")
    assert real["observaciones"] == 4 and 672 <= real["mediana_horas"] <= 745, real


def test_proxima_carga_suma_el_periodo_declarado():
    fila = {"fecha_carga": "2026-06-15T06:00:00", "fecha_datos": None, "cada": "diaria"}
    assert frescura.proxima_carga(fila).startswith("2026-06-16T06:00")
    assert frescura.proxima_carga({"fecha_carga": None, "fecha_datos": None, "cada": "diaria"}) is None


def test_el_json_de_entrega_trae_resumen_y_tablas(cob):
    import json
    datos = json.loads((cob.dirs["entrega"] / "frescura.json").read_text(encoding="utf-8"))
    assert datos["resumen"]["tablas"] == len(datos["tablas"])
    assert sum(datos["resumen"][e] for e in frescura.ESTADOS) == datos["resumen"]["tablas"]
