"""Proyección de series: que el backtest no se haga trampa, que la elección se
banque decir «nadie le gana al tonto», y que TimesFM entre como un backend más
sin poder saltearse la licencia."""
import numpy as np
import pandas as pd
import pytest

from mvde import proyeccion as P


def _estacional(n=60, m=12, nivel=100.0, pendiente=1.0, ruido=0.0, seed=7):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    ciclo = np.array([10, -5, 0, 8, 12, -3, -8, 4, 6, -2, 1, 9], dtype=float)
    return nivel + pendiente * t + ciclo[t % m] + rng.normal(0, ruido, n)


# --------------------------------------------------------------- armar la serie
def test_la_serie_completa_los_periodos_sin_datos_con_cero():
    df = pd.DataFrame({"f": ["2025-01-05", "2025-01-20", "2025-03-02"], "v": [10, 5, 7]})
    s = P.serie(df, "f", "v", "mensual")
    assert list(s["periodo"].dt.strftime("%Y-%m")) == ["2025-01", "2025-02", "2025-03"]
    assert list(s["valor"]) == [15.0, 0.0, 7.0], "febrero sin datos es un cero, no un agujero"


def test_la_serie_entiende_el_fecha_key_entero_de_gold():
    """Las tablas de hechos no guardan la fecha: guardan AAAAMMDD como entero.
    Leerlo como número de nanosegundos daría 1970 y arruinaría la serie."""
    df = pd.DataFrame({"fecha_key": [20250101, 20250102, 20250104], "v": [1.0, 2.0, 3.0]})
    s = P.serie(df, "fecha_key", "v", "diaria")
    assert s["periodo"].iloc[0] == pd.Timestamp("2025-01-01")
    assert list(s["valor"]) == [1.0, 2.0, 0.0, 3.0]


def test_la_serie_avisa_que_le_falta_una_columna_o_la_frecuencia():
    df = pd.DataFrame({"f": ["2025-01-01"], "v": [1]})
    with pytest.raises(ValueError, match="necesita"):
        P.serie(df, "f", "no_existe")
    with pytest.raises(ValueError, match="frecuencia"):
        P.serie(df, "f", "v", "cada_luna_llena")


# -------------------------------------------------------------------- backtest
def test_el_backtest_no_ve_nada_posterior_al_corte():
    """Un backend que espía el futuro no puede: sólo recibe la historia previa."""
    v = _estacional(48)
    vistos = []

    def espia(historia, horizonte, m):
        vistos.append(len(historia))
        return np.repeat(historia[-1], horizonte)

    bt = P.backtest(v, horizonte=3, estacionalidad=12, origenes=4, backends={"espia": espia})
    assert vistos == [42, 43, 44, 45], "cada corte entrena con todo lo anterior y nada más"
    assert bt["cortes"][-1] + 3 == len(v), "el último corte llega justo al final de la serie"


def test_una_serie_corta_se_niega_a_dar_un_numero():
    with pytest.raises(ValueError, match="no alcanza"):
        P.backtest(np.arange(20, dtype=float), horizonte=3, estacionalidad=12)


def test_la_estacional_ingenua_es_perfecta_en_una_serie_perfectamente_estacional():
    v = np.tile([10.0, 20.0, 30.0, 40.0], 12)
    bt = P.backtest(v, horizonte=4, estacionalidad=4, origenes=5)
    fila = next(f for f in bt["resultados"] if f["backend"] == "naive_estacional")
    assert fila["mae"] == pytest.approx(0.0, abs=1e-9)
    assert P.elegir(bt)["le_gana_a_la_referencia"] is False, "no hay nada que mejorarle a un error de cero"


def test_con_tendencia_mas_estacionalidad_algun_modelo_le_gana_a_la_referencia():
    bt = P.backtest(_estacional(60, ruido=2.0), horizonte=3, estacionalidad=12, origenes=6)
    e = P.elegir(bt)
    assert e["le_gana_a_la_referencia"], e["comparacion"]
    assert e["mejora_pct"] > 0 and e["backend"] in {"tendencia_estacional", "holt_winters"}


def test_un_backend_que_revienta_no_tumba_el_backtest():
    def roto(historia, horizonte, m):
        raise RuntimeError("no tengo pesos")

    def corto(historia, horizonte, m):
        return np.array([1.0])

    backends = dict(P.BACKENDS_BASE, roto=roto, corto=corto)
    bt = P.backtest(_estacional(48), 3, 12, 4, backends)
    fallidos = {f["backend"]: f for f in bt["resultados"] if f["origenes"] == 0}
    assert "no tengo pesos" in fallidos["roto"]["error"]
    assert "3 valores" in fallidos["corto"]["error"] or "1 valores" in fallidos["corto"]["error"]
    assert P.elegir(bt)["backend"] not in fallidos, "el ganador sale de los que sí corrieron"


def test_la_tendencia_es_local_y_no_extrapola_la_temporada_pasada():
    """Con estacionalidad anual, una recta ajustada sobre todo el histórico
    proyecta el desplome de la temporada alta a la baja. La ventana local es lo
    que evita ese error, y por eso el corte está fijado y no se toca."""
    t = np.arange(300)
    v = 1000 + 300 * np.sin(2 * np.pi * t / 365) + 50 * ((t % 7) >= 5)
    pred = P._tendencia_estacional(v, 14, 7)
    assert abs(pred.mean() - v[-14:].mean()) < 150, f"se despegó del nivel reciente: {pred.mean():.0f}"


def test_metricas_smape_aguanta_ceros_y_mape_se_calla():
    m = P._metricas(np.array([0.0, 10.0]), np.array([0.0, 12.0]))
    assert m["mape"] is None, "con un cero real el MAPE es infinito: no se reporta"
    assert 0 < m["smape"] < 20 and m["mae"] == 1.0


# --------------------------------------------------------------------- TimesFM
def test_los_pesos_3_0_no_se_cargan_sin_declarar_uso_no_comercial():
    """Es una restricción de licencia, no un detalle técnico: el error tiene que
    salir ANTES de mirar si torch está instalado."""
    with pytest.raises(RuntimeError, match="non-commercial|no comercial"):
        P.backend_timesfm("google/timesfm-3.0-pytorch")
    assert P.CHECKPOINT_DEFECTO in P.PESOS_COMERCIALES


def test_declarando_investigacion_los_pesos_3_0_pasan_la_puerta_de_licencia():
    """El permiso existe: investigar con los 3.0 es un uso permitido. Lo que la
    puerta impide es que entren sin que nadie lo haya decidido."""
    ok, _ = P.timesfm_disponible()
    with pytest.raises(RuntimeError) as e:
        P.backend_timesfm("google/timesfm-3.0-pytorch", permitir_no_comercial=True)
    # Ya no se queja de la licencia: ahora se queja (acá) de que falta el paquete.
    assert "non-commercial" not in str(e.value) and "no comercial" not in str(e.value)
    assert ok or "no está instalado" in str(e.value)


def test_una_corrida_de_investigacion_queda_marcada_en_la_salida():
    """Prender el permiso es legítimo y tiene que dejar rastro: seis meses
    después la salida se ve idéntica a una comercial."""
    df = pd.DataFrame({"fecha_key": [int(d.strftime("%Y%m%d")) for d in pd.date_range("2021-01-01", periods=48, freq="MS")],
                       "monto": _estacional(48, ruido=2.0)})
    cfg = {"fecha": "fecha_key", "valor": "monto", "horizonte": 3, "origenes": 4,
           "timesfm": {"checkpoint": "google/timesfm-3.0-pytorch", "permitir_no_comercial": True}}
    # Sustituto de los pesos: acá no hay torch ni acceso a Hugging Face, pero el
    # camino de marcado es el mismo con pesos de verdad.
    real = P.backend_timesfm
    P.backend_timesfm = lambda *a, **k: P._naive_estacional
    try:
        res = P.correr(df, cfg)
    finally:
        P.backend_timesfm = real
    assert res["licencia_no_comercial"] is True
    aviso = [n for n in res["notas"] if "ATENCIÓN" in n]
    assert aviso and "non-commercial" in aviso[0] and P.CHECKPOINT_DEFECTO in aviso[0]


def test_una_corrida_comercial_no_lleva_la_marca():
    df = pd.DataFrame({"fecha_key": [int(d.strftime("%Y%m%d")) for d in pd.date_range("2021-01-01", periods=48, freq="MS")],
                       "monto": _estacional(48, ruido=2.0)})
    real = P.backend_timesfm
    P.backend_timesfm = lambda *a, **k: P._naive_estacional
    try:
        res = P.correr(df, {"fecha": "fecha_key", "valor": "monto", "horizonte": 3, "origenes": 4,
                            "timesfm": {"checkpoint": P.CHECKPOINT_DEFECTO}})
    finally:
        P.backend_timesfm = real
    assert res["licencia_no_comercial"] is False
    assert not [n for n in res["notas"] if "ATENCIÓN" in n]


def test_sin_el_paquete_instalado_el_motivo_se_explica():
    ok, motivo = P.timesfm_disponible()
    assert ok or ("timesfm" in motivo or "torch" in motivo)
    if not ok:
        with pytest.raises(RuntimeError, match="no está instalado"):
            P.backend_timesfm()


def test_un_backend_externo_compite_en_igualdad_de_condiciones():
    """Sustituto de TimesFM: el camino de integración se prueba sin bajar pesos."""
    v = _estacional(60, ruido=1.0)

    def oraculo(historia, horizonte, m):
        # Casi perfecto, pero calculado SOLO con la historia que recibe.
        return P._tendencia_estacional(historia, horizonte, m)

    bt = P.backtest(v, 3, 12, 6, dict(P.BACKENDS_BASE, timesfm=oraculo))
    e = P.elegir(bt)
    assert "timesfm" in {f["backend"] for f in bt["resultados"]}
    assert e["le_gana_a_la_referencia"]


# ------------------------------------------------------------------ todo junto
def test_correr_devuelve_historia_y_futuro_en_la_misma_tabla():
    df = pd.DataFrame({"fecha_key": [int(d.strftime("%Y%m%d")) for d in pd.date_range("2021-01-01", periods=60, freq="MS")],
                       "monto": _estacional(60, ruido=2.0)})
    res = P.correr(df, {"fecha": "fecha_key", "valor": "monto", "frecuencia": "mensual", "horizonte": 3, "origenes": 6})
    s = res["serie"]
    assert res["tipo"] == "serie" and set(s["tipo"]) == {"historia", "proyeccion"}
    assert (s["tipo"] == "proyeccion").sum() == 3
    assert s["periodo"].is_monotonic_increasing, "el futuro va después del pasado"
    assert s.loc[s["tipo"] == "proyeccion", "backend"].nunique() == 1
    # Compatible con la etapa tabular: el reporte lee `metricas` y `modelo`.
    assert res["modelo"] and res["metricas"]["origenes_backtest"] == 6


def test_correr_no_rompe_si_timesfm_no_esta_y_lo_deja_escrito():
    df = pd.DataFrame({"fecha_key": [int(d.strftime("%Y%m%d")) for d in pd.date_range("2021-01-01", periods=48, freq="MS")],
                       "monto": _estacional(48, ruido=2.0)})
    cfg = {"fecha": "fecha_key", "valor": "monto", "horizonte": 3, "origenes": 4,
           "timesfm": {"checkpoint": "google/timesfm-3.0-pytorch"}}
    res = P.correr(df, cfg)
    assert res["serie"] is not None, "una proyección no se cae porque falte un backend opcional"
    assert any("TimesFM no entró" in n for n in res["notas"])


def test_correr_exige_fecha_y_valor():
    with pytest.raises(KeyError):
        P.correr(pd.DataFrame({"a": [1]}), {"valor": "a"})


# ------------------------------------- métodos portados del motor de cobranzas
def test_los_metodos_portados_no_miran_el_calendario_sino_el_ciclo():
    """El motor original razona con «mismo mes del año»; acá con «misma posición
    del ciclo», así el mismo código sirve para series diarias o trimestrales."""
    from mvde import metodos_serie as M
    v = np.tile([10.0, 40.0, 20.0, 30.0], 10)          # ciclo de 4, no de 12
    for nombre, fn in M.BACKENDS.items():
        pred = fn(v, 4, 4)
        assert len(pred) == 4 and np.all(np.isfinite(pred)), nombre
    assert M.BACKENDS["yoy"](v, 4, 4) == pytest.approx([10, 40, 20, 30], rel=0.05)


def test_las_barandas_evitan_que_una_tendencia_se_dispare():
    from mvde import metodos_serie as M
    v = np.concatenate([np.full(24, 100.0), np.array([100.0, 400.0])])   # un salto absurdo al final
    pred = M.BACKENDS["tendencia_amortiguada"](v, 6, 12)
    reciente = float(np.mean(v[-6:]))
    assert pred.max() <= reciente * M.TECHO_VS_RECIENTE * 1.01, pred


def test_el_metodo_encadena_su_propia_prediccion():
    """Cada paso del horizonte usa el anterior como historia, igual que el motor
    original: eso es lo que después mide el backtest."""
    from mvde import metodos_serie as M
    vistos = []
    fn = M._recursivo(lambda v, k, m: (vistos.append(len(v)), float(v[-1]) + 1)[1])
    assert list(fn(np.array([1.0, 2.0, 3.0]), 3, 12)) == [4.0, 5.0, 6.0]
    assert vistos == [3, 4, 5]


# ------------------------------------------------ ensemble, bandas y segmentos
def test_el_ensemble_no_se_pondera_con_el_corte_que_esta_midiendo():
    """Ponderar con el resultado del mismo corte que se mide infla la precisión.
    Por eso el ensemble usa un corte menos que los métodos sueltos."""
    bt = P.backtest(_estacional(60, ruido=2.0), 3, 12, 6)
    ens = next(f for f in bt["resultados"] if f["backend"] == P.ENSEMBLE)
    suelto = next(f for f in bt["resultados"] if f["backend"] == "naive")
    assert ens["origenes"] == suelto["origenes"] - 1
    assert abs(sum(bt["pesos_ensemble"].values()) - 1) < 0.01, "los pesos se guardan redondeados, pero suman uno"
    assert P.ENSEMBLE not in bt["pesos_ensemble"], "el ensemble no puede ponderarse a sí mismo"


def test_sin_pesos_el_ensemble_se_niega_a_proyectar():
    with pytest.raises(ValueError, match="pesos"):
        P.proyectar(_estacional(48), 3, P.ENSEMBLE, 12)


def test_la_banda_sale_de_errores_medidos_paso_por_paso():
    bt = P.backtest(_estacional(72, ruido=6.0), horizonte=6, estacionalidad=12, origenes=8)
    b = P.bandas(bt, "naive_estacional", nivel=0.8)
    assert [x["paso"] for x in b] == [1, 2, 3, 4, 5, 6]
    assert all(x["n"] == 8 for x in b), "cada paso usa todos los cortes"
    ancho = [x["alto"] - x["bajo"] for x in b]
    assert all(a > 0 for a in ancho), ancho
    # El ancho lo dicta el error medido y nada más: no hay fórmula que lo abra
    # con la raíz del horizonte. La estacional ingenua se equivoca parecido al
    # paso 1 que al 6, y la banda tiene que decir eso, no lo que se espera.
    assert all(b[i]["bajo"] <= b[i]["sesgo"] <= b[i]["alto"] for i in range(6))
    # Con más ruido, banda más ancha: es la propiedad que le da sentido.
    ruidosa = P.bandas(P.backtest(_estacional(72, ruido=20.0, seed=11), 6, 12, 8), "naive_estacional")
    assert (ruidosa[0]["alto"] - ruidosa[0]["bajo"]) > ancho[0]
    with pytest.raises(ValueError, match="entre 0 y 1"):
        P.bandas(bt, "naive_estacional", nivel=80)


def test_aplicar_bandas_corrige_por_el_sesgo_del_modelo():
    """Si el modelo viene tirando 10 % alto, el piso de la banda tiene que estar
    por debajo de la proyección, no simétrico alrededor."""
    b = [{"paso": 1, "n": 5, "bajo": 0.05, "alto": 0.15, "sesgo": 0.10}]
    d = P.aplicar_bandas(np.array([110.0]), b)
    assert d["banda_baja"].iloc[0] < 110 and d["banda_alta"].iloc[0] < 110
    assert d["banda_baja"].iloc[0] == pytest.approx(110 / 1.15)


def test_real_vs_proyectado_reconstruye_el_pronostico_de_un_pasado_conocido():
    v = _estacional(48, ruido=2.0)
    s = pd.Series(pd.date_range("2021-01-01", periods=48, freq="MS"))
    bt = P.backtest(v, 3, 12, 4)
    d = P.real_vs_proyectado(bt, "naive_estacional", s)
    assert len(d) == 4 * 3 and set(d["paso"]) == {1, 2, 3}
    fila = d.iloc[0]
    assert fila["real"] == pytest.approx(v[int(fila["indice"])])
    assert fila["desvio"] == pytest.approx(fila["proyectado"] - fila["real"])


def _cartera(meses=48, seed=3):
    rng = np.random.default_rng(seed)
    filas = []
    for seg, nivel, ruido in (("A", 1000.0, 0.03), ("B", 300.0, 0.10), ("C", 50.0, 0.30)):
        for k, f in enumerate(pd.date_range("2021-01-01", periods=meses, freq="MS")):
            est = 1 + 0.12 * np.sin(2 * np.pi * (f.month - 3) / 12)
            filas.append({"fecha": f, "estado": seg, "monto": nivel * est * (1 + rng.normal(0, ruido))})
    return pd.DataFrame(filas)


def test_cada_segmento_elige_su_propio_modelo_y_ademas_se_proyecta_el_total():
    res = P.correr(_cartera(), {"fecha": "fecha", "valor": "monto", "horizonte": 6,
                                "origenes": 6, "segmento": "estado", "minimo_periodos": 24})
    nombres = [s["segmento"] for s in res["segmentos"]]
    assert nombres[0] == "TOTAL" and set(nombres[1:]) == {"A", "B", "C"}
    assert all(s["porque"] and s["metricas"]["smape"] is not None for s in res["segmentos"])
    s = res["serie"]
    assert set(s["segmento"]) == {"TOTAL", "A", "B", "C"}
    # El horizonte se expresa también en días, que es como lo pide cobranzas.
    fut = s[(s["segmento"] == "TOTAL") & (s["tipo"] == "proyeccion")]
    assert list(fut["dias"]) == [30, 60, 90, 120, 150, 180]
    # La banda no es simétrica alrededor de la proyección: está corrida por el
    # sesgo que el modelo mostró en el backtest.
    assert (fut["banda_baja"] < fut["banda_alta"]).all()
    assert fut[["banda_baja", "banda_alta"]].notna().all().all()
    # El segmento ruidoso tiene que declarar una banda más ancha que el estable.
    ancho = {x["segmento"]: x["bandas"][-1]["alto"] - x["bandas"][-1]["bajo"] for x in res["segmentos"]}
    assert ancho["C"] > ancho["A"], ancho


def test_un_segmento_sin_historia_se_omite_y_queda_dicho():
    df = _cartera()
    corto = df[df["estado"] == "A"].tail(10).assign(estado="D")
    res = P.correr(pd.concat([df, corto]), {"fecha": "fecha", "valor": "monto", "horizonte": 6,
                                            "origenes": 6, "segmento": "estado", "minimo_periodos": 24})
    assert "D" not in [s["segmento"] for s in res["segmentos"]]
    assert any("D:" in n for n in res["notas"]), res["notas"]


def test_el_segmento_sin_valor_no_queda_como_nan():
    df = _cartera(seed=5)
    df["tipo"] = np.where(df["estado"] == "A", "Puro", None)
    res = P.correr(df, {"fecha": "fecha", "valor": "monto", "horizonte": 3, "origenes": 4,
                        "segmento": ["estado", "tipo"], "minimo_periodos": 24})
    nombres = [s["segmento"] for s in res["segmentos"]]
    assert "A · Puro" in nombres
    assert not [n for n in nombres if "nan" in n.lower() or "none" in n.lower()], nombres


def test_correr_avisa_si_la_columna_de_segmento_no_existe():
    with pytest.raises(ValueError, match="segmento"):
        P.correr(_cartera(), {"fecha": "fecha", "valor": "monto", "segmento": "sucursal"})


def test_el_porque_cita_los_numeros_del_backtest():
    res = P.correr(_cartera(), {"fecha": "fecha", "valor": "monto", "horizonte": 3, "origenes": 5})
    assert res["modelo"] in res["porque"] and "cortes de backtest" in res["porque"]
    assert "referencia" in res["porque"] and "%" in res["porque"]
