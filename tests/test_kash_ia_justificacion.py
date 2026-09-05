"""Demo Kash (train + score de la misma fecha, salida estilo Kobra), IA en modo
local y justificación etapa por etapa."""
import json

import pandas as pd
import pytest

from mvde import ETAPAS, demos, ia, justificacion
from mvde.orquestador import Pipeline


@pytest.fixture(scope="module")
def kash(tmp_path_factory):
    ruta = demos.crear("kash", tmp_path_factory.mktemp("kash"))
    p = Pipeline.desde_yaml(ruta)
    p.correr()
    return p


def test_kash_archivos_tienen_el_esquema_real(kash):
    base = kash.spec["_base"]
    train = pd.read_csv(f"{base}/BACKTEST_TRAIN.csv", sep=";", encoding="utf-8-sig")
    score = pd.read_csv(f"{base}/BACKTEST_SCORE.csv", sep=";", encoding="utf-8-sig")
    assert list(train.columns[:6]) == ["IdCliente", "CuotaEfectivaRef", "DiasAtraso_Actual", "Estado", "SubEstado", "ScoreCash"]
    assert {f"Monto_M{k}" for k in range(1, 13)} <= set(train.columns) and {f"Pago_M{k}" for k in range(1, 13)} <= set(score.columns)
    assert "NMesesConPago_VAL" in train.columns and "NMesesConPago_VAL" not in score.columns
    assert (train["Formato"] == "PIVOT").all() and train["IdCliente"].is_unique


def test_kash_doce_etapas_y_scoring_estilo_kobra(kash):
    estados = {e: kash.resultados[e].estado() for e in ETAPAS}
    assert all(v == "ok" for v in estados.values()), estados
    ev = kash.resultados["ml"].evidencia
    assert ev["metricas"]["auc"] > 0.8 and ev["filas_scoreadas"] == 6000 and ev["brecha_seleccion_holdout"] is not None
    assert len(ev["comparacion"]) == 3                                   # tres modelos comparados
    scores = kash.gold["ml_scores"]
    assert {"dim_cliente_key", "probpago", "decil", "segmento_propension", "estrategia", "valor_esperado_recupero", "prioridad"} <= set(scores.columns)
    assert scores["prioridad"].is_unique and set(scores["segmento_propension"]) <= {"Baja", "Media", "Alta"}
    assert any(a.endswith("cartera_priorizada.xlsx") for a in kash.resultados["ml"].artefactos)
    kpis = {k["nombre"]: k["valor"] for k in kash.resultados["reporte"].evidencia["kpis"]}
    assert "ProbPago promedio %" in kpis and "Valor esperado de recupero" in kpis


def test_kash_despivoteo_produce_fact_mensual(kash):
    assert kash.resultados["gold"].evidencia["tablas"]["fact_pago_mes"] == 6000 * 12
    assert "dim_calendario" in kash.gold


def test_justificacion_usa_numeros_reales(kash):
    js = justificacion.generar(kash, "es")
    assert len(js) == 12 and all(j["que"] and j["tecnico"] and j["gerencia"] for j in js)
    ml = next(j for j in js if j["etapa"] == "ml")
    assert "AUC" in ml["que"] and "{" not in ml["que"]
    for lang in ("es", "en", "pt"):
        md = justificacion.markdown(kash, lang)
        assert "{" not in md and md.count("## ") == 12
    assert (kash.dirs["entrega"] / "JUSTIFICACION_es.md").exists() and (kash.dirs["entrega"] / "JUSTIFICACION_en.md").exists()


def test_ia_modo_local_responde_con_la_corrida(kash):
    r = ia.preguntar("¿cuál es el valor esperado de recupero?", kash, proveedor="")
    assert r["modo"] == "local" and "Valor esperado" in r["respuesta"]
    r = ia.preguntar("qué precisión tiene el modelo", kash, proveedor="")
    assert "auc" in r["respuesta"].lower()
    r = ia.preguntar("SELECT estrategia, COUNT(*) n FROM gold.ml_scores GROUP BY 1", kash, proveedor="")
    assert r["tabla"] is not None and len(r["tabla"]) >= 3
    r = ia.preguntar("DELETE FROM gold.ml_scores", kash, proveedor="")
    assert r["tabla"] is None


def test_ia_extrae_modelos_de_cada_api():
    assert ia._extraer_modelos("openai", {"data": [{"id": "gpt-5"}, {"id": "gpt-4o-audio"}, {"id": "text-embedding-3"}]}) == ["gpt-5"]
    assert ia._extraer_modelos("claude", {"data": [{"id": "claude-sonnet-5"}, {"id": "claude-haiku-4-5"}]}) == ["claude-sonnet-5", "claude-haiku-4-5"]
    assert ia._extraer_modelos("gemini", {"models": [{"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
                                                     {"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]}]}) == ["gemini-2.5-pro"]
    assert ia._extraer_modelos("ollama", {"models": [{"name": "llama3.1"}]}) == ["llama3.1"]
    assert "claude" in ia.proveedores() and ia.contexto is not None


def test_ia_contexto_incluye_tablas_y_kpis(kash):
    ctx = ia.contexto(kash)
    assert "gold.ml_scores" in ctx and "KPIs de la corrida" in ctx and json.dumps(ctx) is not None
