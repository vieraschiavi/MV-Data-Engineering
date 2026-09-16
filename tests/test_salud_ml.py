"""El puntaje de ML premia un modelo creíble, no un número alto.

La fórmula anterior hacía dos cosas mal a la vez:

1. **Premiaba el AUC sin techo** (0,9 → 100). En el mismo motor que tiene un
   chequeo de fugas, el puntaje le daba 100 tanto a un modelo excelente como a
   uno con una columna del futuro entre las features. Un puntaje que no
   distingue esas dos cosas no sirve para nada.
2. **Miraba sólo AUC-ROC** e ignoraba el lift del decil 10, que es el número
   con el que un equipo de cobranzas decide si el modelo le sirve — y que el
   motor ya calculaba.

Efecto colateral de (1): un modelo de cobranzas realista (AUC 0,75, lift 2,77)
quedaba en 55,8/100, o sea que el puntaje llamaba «malo» a lo que en riesgo de
crédito es normal y sano.

Estos tests fijan la propiedad que justifica el cambio: **un modelo con fuga
tiene que puntuar PEOR que uno honesto**. Si alguien vuelve a atar el puntaje
al AUC crudo, esto lo marca.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import demos, ml, salud  # noqa: E402
from mvde.orquestador import Pipeline  # noqa: E402


def _res(auc, lift, base=0.2148, brecha=0.0):
    return {"modelo": "X", "tipo": "clasificacion",
            "metricas": {"auc": auc, "lift_decil10": lift, "tasa_base": base},
            "brecha_seleccion_holdout": brecha}


def _p(auc, lift, **kw):
    return salud._puntaje_clasificacion(_res(auc, lift, **kw))["puntaje"]


# ── la propiedad por la que se cambió la fórmula ───────────────────────────
def test_un_modelo_con_fuga_puntua_peor_que_uno_honesto():
    """Con la fórmula anterior era al revés: el de AUC 0,99 sacaba 100."""
    honesto = _p(0.82, 3.40)
    con_fuga = _p(0.99, 4.60)
    assert con_fuga < honesto, f"fuga {con_fuga} no puede ganarle a honesto {honesto}"


def test_el_auc_sospechoso_queda_marcado_en_el_resultado():
    assert salud._puntaje_clasificacion(_res(0.99, 4.6))["sospecha_fuga"] is True
    assert salud._puntaje_clasificacion(_res(0.82, 3.4))["sospecha_fuga"] is False


def test_por_encima_del_techo_el_auc_no_sigue_comprando_puntaje():
    """0,80 es donde vive un modelo de riesgo bueno. De ahí para arriba, más
    AUC no es más credibilidad, y el puntaje deja de subir."""
    assert _p(0.85, 3.0) == _p(0.92, 3.0)
    assert _p(0.80, 3.0) == _p(0.85, 3.0)


def test_debajo_del_techo_mas_auc_si_compra_puntaje():
    assert _p(0.60, 2.0) < _p(0.70, 2.0) < _p(0.80, 2.0)


def test_el_azar_no_puntua():
    assert _p(0.50, 1.0) == 0.0
    assert _p(0.51, 1.02) < 5


# ── el lift se normaliza por su propio techo ───────────────────────────────
def test_el_lift_se_compara_contra_lo_alcanzable_no_en_crudo():
    """El lift máximo posible es 1/tasa_base. Con tasa 47 % un lift de 2,0 es
    casi perfecto; con tasa 21 % el mismo 2,0 es la mitad de lo alcanzable.
    Comparar lifts crudos entre problemas con distinta prevalencia no dice
    nada, y era lo que hacía falta para que `kash` y `cobranzas` fueran
    comparables."""
    casi_perfecto = _p(0.80, 2.0, base=0.4767)     # techo 2,10
    a_mitad_de_camino = _p(0.80, 2.0, base=0.2148)  # techo 4,66
    assert casi_perfecto > a_mitad_de_camino


def test_un_lift_al_azar_no_suma_utilidad():
    assert _p(0.80, 1.0) < _p(0.80, 2.0)


def test_sin_lift_medible_no_se_inventa_uno():
    """Con pocas filas el motor no calcula el lift. El puntaje se reparte sobre
    lo que sí se midió en vez de castigar por un dato que no existe."""
    r = salud._puntaje_clasificacion(
        {"modelo": "X", "metricas": {"auc": 0.80, "tasa_base": 0.2}, "brecha_seleccion_holdout": 0.0})
    assert r["puntaje"] == 100.0
    assert "sin lift medible" in r["detalle"]


def test_la_brecha_seleccion_holdout_sigue_restando():
    assert _p(0.80, 3.0, brecha=0.10) < _p(0.80, 3.0, brecha=0.0)


def test_el_detalle_dice_de_donde_sale_el_numero():
    d = salud._puntaje_clasificacion(_res(0.7569, 2.77))["detalle"]
    assert "AUC" in d and "lift decil 10" in d and "alcanzable" in d and "brecha" in d


# ── atributos protegidos ───────────────────────────────────────────────────
def test_detecta_el_atributo_protegido_y_propone_la_columna_original():
    """Hay que excluir `sexo`, no `sexo_Femenino`: la dummy la arma el motor."""
    assert salud._features_protegidas(["sexo_Femenino", "sexo_Masculino", "edad"]) == {"sexo"}
    assert salud._features_protegidas(["estado_civil_Casado"]) == {"estado_civil"}
    assert salud._features_protegidas(["gender", "raza", "union_member"]) == {"gender", "raza", "union_member"}


def test_no_marca_una_columna_que_solo_contiene_la_palabra():
    """Un control que grita por `terraza` es un control que alguien apaga."""
    assert salud._features_protegidas(["sexto_mes", "terraza", "razon_social", "limite_credito"]) == set()


def test_la_edad_no_esta_en_la_lista_a_proposito():
    """En scoring de crédito se usa de forma habitual y legal en varias
    jurisdicciones. Marcarla convertiría el hallazgo en ruido."""
    assert salud._features_protegidas(["edad", "age", "edad_cliente"]) == set()
    assert "edad" not in salud.PROTEGIDOS


def test_sugiere_excluir_el_atributo_protegido_con_severidad_alta():
    class Falso:
        ml = {"tipo": "clasificacion", "metricas": {"auc": 0.75, "tasa_base": 0.2, "lift_decil10": 2.0},
              "features": ["sexo_Femenino", "sexo_Masculino", "pct_pagado"], "notas": [],
              "brecha_seleccion_holdout": 0.01}
        spec, gold, silver, tablas, resultados = {}, {}, {}, {}, {}
        calidad = gobernanza = None
    s = [x for x in salud.sugerencias(Falso()) if x["codigo"] == "atributo_protegido"]
    assert s, "un modelo que decide con el sexo del titular tiene que salir en las sugerencias"
    assert s[0]["severidad"] == "alta"
    assert s[0]["parche"] == {"ml_excluir": ["sexo"]}
    # El parche tiene que ser aplicable al YAML tal cual.
    nuevo = salud.aplicar({"ml": {"target": "t"}}, s[0])
    assert nuevo["ml"]["excluir"] == ["sexo"]


# ── sobre la corrida real ──────────────────────────────────────────────────
def _corrida(tmp_path, nombre="cobranzas"):
    p = Pipeline.desde_yaml(demos.crear(nombre, tmp_path))
    p.correr(hasta="ml")
    return p


def test_la_demo_de_cobranzas_no_decide_con_el_sexo_del_titular(tmp_path):
    """Estaba en el `ml.sql` de la demo. Un gerente de riesgo que lo note corta
    la reunión, y con razón."""
    p = _corrida(tmp_path)
    assert salud._features_protegidas(p.ml["features"]) == set()
    assert not any(f.lower().startswith("sexo") for f in p.ml["features"])
    assert [x for x in salud.sugerencias(p) if x["codigo"] == "atributo_protegido"] == []


def test_la_corrida_deja_por_escrito_que_vio_el_modelo(tmp_path):
    """`importancia` es el top 15: no alcanza para revisar después si entró una
    columna que no debía entrar."""
    p = _corrida(tmp_path)
    assert p.ml["features"] and len(p.ml["features"]) >= len(p.ml["importancia"])
    assert "pct_pagado" in p.ml["features"]


def test_los_modelos_lineales_van_escalados_y_su_importancia_no_sale_vacia(tmp_path):
    """Sin desenvolver el Pipeline, `|coef_|` no existe y la tabla de
    importancia queda en blanco justo cuando gana el modelo lineal."""
    from sklearn.pipeline import Pipeline as SkPipeline
    for tipo, lineal in (("clasificacion", "Regresión logística"), ("regresion", "Ridge")):
        assert isinstance(ml._modelos(tipo)[lineal], SkPipeline)
    p = _corrida(tmp_path)
    if "logística" in p.ml["modelo"]:
        assert p.ml["importancia"], "ganó el lineal y la importancia salió vacía"


# ---------------------------------------------------------------------------
# El corte y la fila: dos cosas que hacían que «mejoró» no fuera verificable.
# ---------------------------------------------------------------------------

def _set(n=600, extra=False, seed=7):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"id_cliente": np.arange(1, n + 1),
                      "x": rng.normal(size=n),
                      "y": rng.integers(0, 2, n)})
    if extra:                                  # una feature más, como en la vida real
        d["z"] = rng.normal(size=n)
    return d


def test_con_id_declarado_agregar_una_columna_no_reparte_otro_holdout():
    """La propiedad sin la cual ningún «el cambio mejoró el modelo» es verificable.

    Con el corte por huella de contenido, agregar una feature le cambia el hash
    a todas las filas: la corrida de antes y la de después miden sobre
    poblaciones distintas, y la diferencia de AUC no dice si el cambio sirvió.
    Pasó en la demo `cobranzas`: una feature buena BAJÓ el puntaje de 64,4 a
    62,4 porque el reparte nuevo daba una brecha selección→holdout de 0,0572
    contra 0,0077, y la brecha descuenta. Sobre un corte fijo la misma feature
    da 0,0004 y el puntaje sube a 81,2.
    """
    cfg = {"target": "y", "tipo": "clasificacion", "id": "id_cliente"}
    a = ml._cortes(_set(), cfg, [])
    b = ml._cortes(_set(extra=True), cfg, [])
    for i, (x, z) in enumerate(zip(a, b)):
        assert set(_set()["id_cliente"].values[x]) == set(_set(extra=True)["id_cliente"].values[z]), \
            f"el tramo {i} cambió de integrantes al agregar una columna"


def test_sin_id_declarado_el_corte_avisa_que_no_se_puede_comparar():
    """Si no hay clave, el corte sigue siendo por contenido — y la corrida lo
    dice, en vez de dejar que alguien compare dos números que no se comparan."""
    notas: list[str] = []
    ml._cortes(_set(), {"target": "y", "tipo": "clasificacion"}, notas)
    dicho = " ".join(notas).lower()
    assert "huella de contenido" in dicho
    assert "no" in dicho and "comparan" in dicho
    assert "`id`" in dicho or "id`" in dicho, "no dice cómo arreglarlo"


def test_el_corte_por_id_queda_por_escrito_en_la_corrida():
    notas: list[str] = []
    ml._cortes(_set(), {"target": "y", "tipo": "clasificacion", "id": "id_cliente"}, notas)
    assert "id_cliente" in " ".join(notas)


def test_el_set_de_ml_de_cobranzas_tiene_una_fila_por_cliente(tmp_path):
    """Una fila que es el promedio de dos personas no es de nadie.

    El GROUP BY de la consulta era por (default, edad, educación, sucursal,
    límite) y fusionaba clientes que compartían esos cinco valores: 4.000
    clientes entraban al modelo como 3.812 filas, con los agregados de 188
    pares mezclados. Corría verde y nadie se enteraba.
    """
    p = Pipeline.desde_yaml(demos.crear("cobranzas", tmp_path))
    p.correr(hasta="entrega")
    clientes = len(p.gold["dim_cliente"][p.gold["dim_cliente"]["is_current"]])
    partes = p.ml["filas_train"] + p.ml["filas_seleccion"] + p.ml["filas_holdout"]
    assert partes == clientes, f"{clientes} clientes entraron al modelo como {partes} filas"
    assert p.ml["filas_scoreadas"] == clientes


def test_el_modelo_de_cobranzas_ve_el_atraso_del_ultimo_mes_cerrado(tmp_path):
    """Es la variable central de una cobranza y entraba en versión desafilada.

    La consulta miraba el máximo del trimestre: un cliente que estuvo 2 meses
    atrasado en octubre y se puso al día en diciembre entraba igual que uno que
    sigue atrasado hoy. Correlación con el default: 0,4513 el último mes contra
    0,3481 el máximo del trimestre. No es fuga — el target es la cuota del mes
    SIGUIENTE y el último mes cerrado es lo que hay sobre la mesa al decidir a
    quién llamar.
    """
    p = Pipeline.desde_yaml(demos.crear("cobranzas", tmp_path))
    p.correr(hasta="entrega")
    assert "atraso_ult_mes" in p.ml["features"]
    assert p.ml["metricas"]["auc"] >= 0.74, p.ml["metricas"]
    assert p.ml["metricas"]["lift_decil10"] >= 3.0, p.ml["metricas"]
