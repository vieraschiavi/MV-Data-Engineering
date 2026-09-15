"""Efectividad de campañas: cada test fija una trampa que el módulo ya pisó.

Todo lo que se verifica acá salió de correr el motor sobre la demo y ver que
daba mal. No son tests defensivos escritos por si acaso: son las cosas que el
módulo midió mal antes de medirlas bien, y el número que las delató está en el
comentario de cada uno — el lift de 1451 %, el margen de +42.640 que era
diciembre, el 100 % de retención de una cohorte de dos clientes.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import campanas, demos  # noqa: E402
from mvde.orquestador import Pipeline  # noqa: E402


# ── el juego de datos mínimo, armado a mano para que cada caso sea exacto ──
def _venta(dias, unidades, precio, costo_unit, sku="A", cliente="c1"):
    return pd.DataFrame([{"fecha": d, "sku": sku, "cliente": cliente, "unidades": unidades,
                          "importe": round(unidades * precio, 2), "costo": round(unidades * costo_unit, 2)}
                         for d in dias])


def _cfg(**extra):
    base = {
        "fecha": "fecha", "producto": "sku", "cliente": "cliente",
        "medidas": {"unidades": "unidades", "importe": "importe", "costo": "costo"},
        "calendario": {"tabla": "cal", "campana": "campana", "edicion": "edicion",
                       "desde": "desde", "hasta": "hasta"},
        "ventana": {"baseline_dias": 20, "arrastre_dias": 10, "blackout_dias": 5},
        "cohortes": {"granularidad": "mensual", "periodos": 2},
    }
    base.update(extra)
    return base


CAL = pd.DataFrame([{"campana": "C", "edicion": "e1", "desde": "2025-03-01", "hasta": "2025-03-10"}])


# ── 1 · las ventanas ──────────────────────────────────────────────────────
def test_el_blackout_queda_fuera_del_baseline():
    """La semana previa está contaminada por el anuncio: si entra al baseline,
    el baseline baja y el lift sube sin que haya pasado nada."""
    w = campanas.ventanas(pd.Timestamp("2025-03-01"), pd.Timestamp("2025-03-10"),
                          {"ventana": {"baseline_dias": 20, "arrastre_dias": 10, "blackout_dias": 5}})
    assert w["baseline"][1] == pd.Timestamp("2025-02-23")      # 5 días antes del 28/02
    assert w["blackout"] == (pd.Timestamp("2025-02-24"), pd.Timestamp("2025-02-28"))
    assert w["durante"] == (pd.Timestamp("2025-03-01"), pd.Timestamp("2025-03-10"))
    assert w["arrastre"] == (pd.Timestamp("2025-03-11"), pd.Timestamp("2025-03-20"))
    # Y no se solapan: el blackout está entre el baseline y la campaña.
    assert w["baseline"][1] < w["blackout"][0] < w["durante"][0]


def test_sin_arrastre_declarado_no_se_inventa_ventana_posterior():
    w = campanas.ventanas(pd.Timestamp("2025-03-01"), pd.Timestamp("2025-03-10"),
                          {"ventana": {"arrastre_dias": 0, "blackout_dias": 0}})
    assert w["arrastre"] is None and w["blackout"] is None


# ── 2 · adelantar no es vender ────────────────────────────────────────────
def test_una_campana_que_solo_adelanta_venta_no_cuenta_como_incremental():
    """El caso que casi nadie mide: sube durante y se derrumba después. Mirando
    sólo la ventana de campaña esto da +120 % de lift y parece un éxito."""
    base = pd.date_range("2025-02-04", "2025-02-23")      # 20 días de baseline
    camp = pd.date_range("2025-03-01", "2025-03-10")      # 10 días de campaña
    post = pd.date_range("2025-03-11", "2025-03-25")      # 15 días de arrastre
    d = pd.concat([_venta(base, 10, 100, 60), _venta(camp, 22, 100, 60), _venta(post, 1, 100, 60)])
    # (22−10)×10 = +120 durante, (1−10)×15 = −135 después: la ventana da negativo.
    cfg = _cfg(ventana={"baseline_dias": 20, "arrastre_dias": 15, "blackout_dias": 5})
    ef = campanas.correr(d, cfg, {"cal": CAL})["tablas"]["campanas_efecto"].iloc[0]
    assert ef["lift_bruto_pct"] == 120.0, "durante la campaña sí vendió 2,2 veces más"
    assert ef["incremental_unidades"] < 0, "pero en la ventana completa no hubo venta nueva"
    assert ef["veredicto"] in ("adelanto", "peor")
    assert "adelant" in ef["porque"] or "menos" in ef["porque"]


def test_una_campana_que_sostiene_despues_si_es_incremental():
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    post = pd.date_range("2025-03-11", "2025-03-20")
    d = pd.concat([_venta(base, 10, 100, 60), _venta(camp, 18, 100, 60), _venta(post, 11, 100, 60)])
    ef = campanas.correr(d, _cfg(), {"cal": CAL})["tablas"]["campanas_efecto"].iloc[0]
    assert ef["incremental_unidades"] > 0 and ef["veredicto"].startswith("incremental")


# ── 3 · más unidades puede ser peor negocio ───────────────────────────────
def test_vender_mas_con_margen_negativo_no_es_un_exito():
    """Vende el doble de unidades por debajo del costo. El gráfico de unidades
    dice éxito; el veredicto tiene que decir lo contrario."""
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    post = pd.date_range("2025-03-11", "2025-03-20")
    d = pd.concat([_venta(base, 10, 100, 60),
                   _venta(camp, 20, 50, 60),      # precio 50 contra costo 60
                   _venta(post, 10, 100, 60)])
    ef = campanas.correr(d, _cfg(), {"cal": CAL})["tablas"]["campanas_efecto"].iloc[0]
    assert ef["lift_bruto_pct"] == 100.0
    assert ef["incremental_margen_durante"] < 0
    assert ef["veredicto"] == "vendio_mas_gano_menos"
    assert "descuento" in ef["porque"]


def test_distingue_el_margen_que_se_come_el_descuento_del_que_se_come_la_resaca():
    """Las dos pierden margen y la acción es opuesta: en una hay que tocar el
    descuento, en la otra espaciar la campaña. Antes las dos decían «el
    descuento se comió el margen», que en la segunda es falso."""
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    post = pd.date_range("2025-03-11", "2025-03-20")
    # Durante gana margen (precio 95 > costo 60), después se derrumba.
    d = pd.concat([_venta(base, 10, 100, 60), _venta(camp, 14, 95, 60), _venta(post, 2, 100, 60)])
    ef = campanas.correr(d, _cfg(), {"cal": CAL})["tablas"]["campanas_efecto"].iloc[0]
    if ef["incremental_unidades"] > 0 and ef["incremental_margen"] < 0:
        assert ef["veredicto"] == "margen_lo_come_la_resaca"
        assert ef["incremental_margen_durante"] > 0, "durante la campaña el margen cerró bien"


def test_sin_costo_lo_dice_y_no_finge_medir_rentabilidad():
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    d = pd.concat([_venta(base, 10, 100, 60), _venta(camp, 20, 100, 60)]).drop(columns=["costo"])
    cfg = _cfg(medidas={"unidades": "unidades", "importe": "importe"})
    r = campanas.correr(d, cfg, {"cal": CAL})
    assert r["resumen"]["rentabilidad_medida"] is False
    assert any("rentabilidad" in n for n in r["resumen"]["notas"])
    assert r["tablas"]["campanas_efecto"].iloc[0]["margen_pct_campana"] is None


# ── 4 · el descuento se mide contra el precio de antes ────────────────────
def test_detecta_el_precio_inflado_antes_de_la_baja():
    """El precio venía en 100, sube a 120 en el blackout y la campaña lo «baja»
    a 90. Contra el precio previo parece 25 % de descuento; contra el precio de
    verdad son 10 %. Los 15 puntos de diferencia son los fabricados."""
    limpio = pd.date_range("2025-02-04", "2025-02-23")
    black = pd.date_range("2025-02-24", "2025-02-28")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    d = pd.concat([_venta(limpio, 10, 100, 60), _venta(black, 10, 120, 60), _venta(camp, 20, 90, 60)])
    r = campanas.correr(d, _cfg(), {"cal": CAL})
    pr = r["tablas"]["campanas_precio"].iloc[0]
    assert pr["precio_referencia"] == 100 and pr["precio_previo"] == 120 and pr["precio_campana"] == 90
    assert pr["descuento_real_pct"] == 10.0, "contra el precio de verdad, el descuento es 10 %"
    assert pr["descuento_aparente_pct"] == 25.0, "contra el precio inflado, parece 25 %"
    assert bool(pr["precio_inflado_antes"]) is True
    assert pr["puntos_inflados"] == 15.0
    assert any(a["veredicto"] == "descuento_inflado" for a in r["resumen"]["alertas"])


def test_una_suba_chica_no_dispara_la_alerta():
    """Un control que grita por un 2 % de ajuste de lista es un control que
    alguien apaga."""
    limpio = pd.date_range("2025-02-04", "2025-02-23")
    black = pd.date_range("2025-02-24", "2025-02-28")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    d = pd.concat([_venta(limpio, 10, 100, 60), _venta(black, 10, 102, 60), _venta(camp, 20, 80, 60)])
    pr = campanas.correr(d, _cfg(), {"cal": CAL})["tablas"]["campanas_precio"].iloc[0]
    assert bool(pr["precio_inflado_antes"]) is False


# ── 5 · el control y su guarda ────────────────────────────────────────────
def _con_control(unid_ctrl_durante):
    """Dos SKU: A en campaña, B afuera. B es el control."""
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    post = pd.date_range("2025-03-11", "2025-03-20")
    d = pd.concat([
        _venta(base, 10, 100, 60, sku="A"), _venta(camp, 20, 100, 60, sku="A"), _venta(post, 10, 100, 60, sku="A"),
        _venta(base, 10, 100, 60, sku="B"), _venta(camp, unid_ctrl_durante, 100, 60, sku="B"),
        _venta(post, 10, 100, 60, sku="B"),
    ])
    alc = pd.DataFrame([{"campana": "C", "edicion": "e1", "sku": "A"}])
    cfg = _cfg()
    cfg["calendario"] = {**cfg["calendario"], "alcance_tabla": "alc", "alcance_producto": "sku"}
    return campanas.correr(d, cfg, {"cal": CAL, "alc": alc})["tablas"]["campanas_efecto"]


def test_el_control_descuenta_lo_que_movio_a_los_dos_grupos():
    """El control subió 50 %: parte del lift bruto es la época, no la campaña.
    Éste es el arreglo que destapó que Black Friday perdía plata: contra un
    baseline plano daba +42.640 de margen, y era diciembre."""
    ef = _con_control(15).iloc[0]
    assert ef["metodo"] == "dif-en-dif"
    assert ef["lift_bruto_pct"] == 100.0
    assert ef["control_durante_pct"] == 50.0
    assert ef["lift_pct"] == pytest.approx(33.33, abs=0.1), "100 % bruto ÷ 1,5 del control"


def test_marca_sustitucion_cuando_el_control_cae():
    ef = _con_control(9).iloc[0]          # el control baja 10 %
    assert bool(ef["posible_sustitucion"]) is True
    assert ef["veredicto"] == "incremental_con_sustitucion"
    assert "otros productos" in ef["porque"]


def test_descarta_el_control_cuando_la_campana_se_lo_llevo_puesto():
    """Un control que se movió 60 % no es un control: la campaña lo afectó, y
    dividir por ese factor no corrige, amplifica. Con un control que caía 65 %
    el lift corregido daba 1451 % — un número que no es un número."""
    ef = _con_control(4).iloc[0]          # el control se derrumba 60 %
    assert bool(ef["control_descartado"]) is True
    assert ef["metodo"] == "baseline"
    assert ef["lift_pct"] == ef["lift_bruto_pct"], "se vuelve al bruto en vez de inventar una corrección"
    assert ef["veredicto"] == "incremental_sin_control"
    assert "estacionalidad" in ef["porque"]


def test_sin_alcance_declarado_avisa_que_no_hay_control():
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    d = pd.concat([_venta(base, 10, 100, 60), _venta(camp, 20, 100, 60)])
    r = campanas.correr(d, _cfg(), {"cal": CAL})
    assert r["tablas"]["campanas_efecto"].iloc[0]["metodo"] == "baseline"
    assert any("estacionalidad" in n for n in r["resumen"]["notas"])


# ── 6 · los cortes del RFM ────────────────────────────────────────────────
def test_los_cortes_del_rfm_se_devuelven_para_poder_fijarlos():
    """Sin fijarlos, «Campeones creció 12 %» puede ser el corte moviéndose."""
    base = pd.date_range("2025-02-04", "2025-02-23")
    camp = pd.date_range("2025-03-01", "2025-03-10")
    filas = []
    for i in range(30):
        filas.append(_venta(base[: (i % 15) + 1], 2, 100, 60, cliente=f"c{i:02d}"))
        filas.append(_venta(camp[: (i % 8) + 1], 3, 90, 60, cliente=f"c{i:02d}"))
    r = campanas.correr(pd.concat(filas), _cfg(), {"cal": CAL})
    meta = r["resumen"]["rfm"]
    assert set(meta["cortes"]) == {"recencia", "frecuencia", "monetario"}
    assert meta["cortes_fijados"] is False
    assert "fijar" in meta["nota_cortes"]
    # Y con los cortes puestos, la corrida los respeta y lo declara.
    cfg = _cfg(rfm={"ventana_dias": 365, "cortes": meta["cortes"]})
    m2 = campanas.correr(pd.concat(filas), cfg, {"cal": CAL})["resumen"]["rfm"]
    assert m2["cortes_fijados"] is True and m2["cortes"] == meta["cortes"]


def test_el_rfm_usa_los_once_segmentos_conocidos():
    base = pd.date_range("2025-01-01", "2025-03-10")
    filas = [_venta(base[: (i % 40) + 1], 2, 100, 60, cliente=f"c{i:03d}") for i in range(60)]
    rfm = campanas.correr(pd.concat(filas), _cfg(), {"cal": CAL})["tablas"]["campanas_rfm"]
    assert set(rfm["segmento_rfm"]) <= set(campanas.SEGMENTOS_RFM)
    assert rfm["rfm"].str.len().eq(3).all(), "el código RFM son tres dígitos"


# ── 7 · sobre la corrida real de la demo ──────────────────────────────────
@pytest.fixture(scope="module")
def corrida(tmp_path_factory):
    d = tmp_path_factory.mktemp("campanas")
    p = Pipeline.desde_yaml(demos.crear("campanas", d))
    p.correr(hasta="reporte")
    return p


def test_la_demo_corre_y_deja_las_tablas_en_gold(corrida):
    esperadas = {"campanas_efecto", "campanas_panel", "campanas_vs_edicion", "campanas_precio",
                 "campanas_stock", "campanas_rfm", "campanas_rfm_alcance",
                 "campanas_cohortes", "campanas_cohortes_origen"}
    assert esperadas <= set(corrida.gold), f"faltan en gold: {esperadas - set(corrida.gold)}"


def test_compara_contra_la_edicion_anterior_y_la_anterior_a_esa(corrida):
    v = corrida.gold["campanas_vs_edicion"]
    assert set(v["relacion"]) == {"anterior", "anterior_anterior"}
    pr = v[(v["campana"] == "Precios Redondos") & (v["relacion"] == "anterior_anterior")]
    assert len(pr) >= 2, "cinco ediciones dan al menos tres comparaciones a dos saltos"


def test_la_edicion_mas_corta_se_compara_por_dia_y_no_por_total(corrida):
    """2025-09 dura 10 días contra 14 de la anterior. En totales la caída es
    mucho mayor que por día, y el número que sirve es el por día."""
    v = corrida.gold["campanas_vs_edicion"]
    f = v[(v["campana"] == "Precios Redondos") & (v["edicion"] == "2025-09") & (v["relacion"] == "anterior")].iloc[0]
    assert f["dias"] == 10 and f["dias_contra"] == 14
    assert f["var_unidades_pct"] is not None
    # El like-for-like existe y se informa cuánto de la venta cubre.
    assert f["skus_lfl"] > 0 and 0 < f["cobertura_lfl_pct"] <= 100


def test_el_quiebre_de_stock_censura_y_sale_del_like_for_like(corrida):
    st = corrida.gold["campanas_stock"]
    cens = st[st["medicion_censurada"]]
    assert len(cens) >= 1, "la demo inyecta un quiebre a propósito"
    assert set(cens["producto"]) <= set(__import__("mvde.demo_campanas", fromlist=["x"]).SKUS_QUIEBRE)
    v = corrida.gold["campanas_vs_edicion"]
    assert v["skus_excluidos_por_stock"].sum() >= 1, "el censurado tiene que salir del LFL"


def test_encuentra_el_precio_inflado_que_la_demo_inyecto(corrida):
    """La demo sube 14 % en el blackout de Precios Redondos 2025-05. El motor
    tiene que encontrarlo con esa magnitud, no «alguna» alerta."""
    from mvde import demo_campanas as dc
    pr = corrida.gold["campanas_precio"]
    inf = pr[(pr["campana"] == dc.INFLADO[0]) & (pr["edicion"] == dc.INFLADO[1]) & pr["precio_inflado_antes"]]
    assert len(inf) >= 10, "la suba se aplicó a todo el surtido de esa edición"
    assert abs(inf["suba_previa_pct"].median() - dc.SUBA_PREVIA * 100) < 3.0


def test_la_campana_que_adelanta_venta_queda_marcada(corrida):
    """«Semana del Cliente» es 7 días de pico y 28 de resaca sobre los SKU
    promocionados: el incremental de la ventana completa da negativo."""
    ef = corrida.gold["campanas_efecto"]
    sc = ef[(ef["campana"] == "Semana del Cliente") & (ef["dimension"] == "TOTAL")]
    assert len(sc) == 2
    assert (sc["incremental_unidades"] < 0).all(), "las dos ediciones adelantan venta"
    assert set(sc["veredicto"]) <= {"adelanto", "peor"}


def test_black_friday_pierde_margen_durante_la_campana(corrida):
    """45 % de descuento contra un costo del 62 % del precio de lista: la
    ventana de campaña tiene que dar margen incremental negativo en las dos
    ediciones, independientemente de lo que pase después."""
    ef = corrida.gold["campanas_efecto"]
    bf = ef[(ef["campana"] == "Black Friday") & (ef["dimension"] == "TOTAL")]
    assert len(bf) == 2
    assert (bf["incremental_margen_durante"] < 0).all()


def test_las_cohortes_chicas_vienen_marcadas(corrida):
    """Una cohorte de dos clientes retiene «100 %» por el tamaño. El dato viaja
    con su marca para que nadie lo cite como si fuera real."""
    co = corrida.gold["campanas_cohortes_origen"]
    assert "muestra_chica" in co.columns and "clientes_origen" in co.columns
    chicas = co[co["muestra_chica"]]
    if len(chicas):
        assert (chicas["clientes_origen"] < campanas.COHORTE_MINIMA).all()


def test_las_cohortes_inmaduras_vienen_marcadas(corrida):
    co = corrida.gold["campanas_cohortes"]
    assert {"madura", "periodos_observables"} <= set(co.columns)
    assert not co["madura"].all(), "las últimas cohortes no tuvieron tiempo de retener"


def test_el_alcance_por_segmento_rfm_dice_a_quien_le_vendio(corrida):
    """Eso es lo que vuelve «segmentada» a una campaña: no el público declarado,
    sino a quién le vendió de verdad."""
    ra = corrida.gold["campanas_rfm_alcance"]
    assert {"campana", "edicion", "segmento_rfm", "clientes", "participacion_importe_pct"} <= set(ra.columns)
    primera = ra.iloc[0]
    una = ra[(ra["campana"] == primera["campana"]) & (ra["edicion"] == primera["edicion"])]
    assert abs(una["participacion_importe_pct"].sum() - 100) < 1.0


def test_el_analisis_se_segmenta_por_la_dimension_declarada(corrida):
    ef = corrida.gold["campanas_efecto"]
    assert "region" in set(ef["dimension"]), "la demo declara `segmento: [region]`"
    assert set(ef[ef["dimension"] == "region"]["valor"]) >= {"Sur", "Este", "Litoral"}


# ── 8 · falla ruidoso ─────────────────────────────────────────────────────
def test_sin_calendario_no_finge_medir():
    d = _venta(pd.date_range("2025-03-01", "2025-03-10"), 10, 100, 60)
    with pytest.raises(campanas.CampanaError, match="calendario"):
        campanas.correr(d, _cfg(), {})


def test_una_edicion_con_fechas_dadas_vuelta_corta():
    d = _venta(pd.date_range("2025-03-01", "2025-03-10"), 10, 100, 60)
    cal = pd.DataFrame([{"campana": "C", "edicion": "e1", "desde": "2025-03-10", "hasta": "2025-03-01"}])
    with pytest.raises(campanas.CampanaError, match="anterior a"):
        campanas.correr(d, _cfg(), {"cal": cal})


def test_un_segmento_que_no_existe_corta_en_vez_de_ignorarse():
    """Ignorar un segmento mal escrito devuelve un análisis que parece completo
    y no lo es."""
    d = _venta(pd.date_range("2025-02-04", "2025-03-10"), 10, 100, 60)
    with pytest.raises(campanas.CampanaError, match="segmento"):
        campanas.correr(d, _cfg(segmento=["canal_que_no_existe"]), {"cal": CAL})


def test_una_medida_inexistente_lo_dice_con_el_nombre():
    d = _venta(pd.date_range("2025-02-04", "2025-03-10"), 10, 100, 60)
    with pytest.raises(campanas.CampanaError, match="unidades_vendidas"):
        campanas.correr(d, _cfg(medidas={"unidades": "unidades_vendidas", "importe": "importe"}), {"cal": CAL})
