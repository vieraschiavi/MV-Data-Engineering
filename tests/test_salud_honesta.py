"""El puntaje de salud dice QUÉ es y qué no es.

El problema que arregla esto: `evaluar()` promediaba en un solo número dos
cosas que no se pueden promediar.

  · **Mediciones** sobre los datos reales — el porcentaje de reglas de calidad
    que pasaron, el sMAPE del backtest y si le gana a la estacional ingenua, la
    auditoría del `.pbit`. Esas son magnitudes con unidad.
  · **Completitud de la declaración** — «¿declaraste dimensiones?», «¿pusiste
    un dueño del dato?», «¿hay calendario?». Eso es una lista de verificación
    con pesos elegidos por quien escribió el motor (40 + 25 + 20 + 15).

Promediar las dos y presentar «96,4/100» como métrica de calidad es
indefendible frente a un gerente técnico: la mitad del número es el programa
felicitándose por que el YAML está completo. Ahora cada área declara su tipo,
el resultado separa lo medido de lo declarado, y lleva por escrito que es una
autoevaluación.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import demos, salud  # noqa: E402
from mvde.orquestador import Pipeline  # noqa: E402


def _corrida(tmp_path):
    p = Pipeline.desde_yaml(demos.crear("cartera", tmp_path))
    p.correr(hasta="entrega")
    return p


def test_cada_area_declara_si_mide_o_verifica(tmp_path):
    ev = salud.evaluar(_corrida(tmp_path))
    assert ev["areas"], "no evaluó ninguna área"
    for nombre, a in ev["areas"].items():
        assert a.get("tipo") in salud.TIPOS, f"«{nombre}» no declara su tipo"


def test_separa_lo_medido_de_lo_declarado(tmp_path):
    ev = salud.evaluar(_corrida(tmp_path))
    assert "medido" in ev and "completitud" in ev
    # La completitud se cuenta, no se puntúa: es «n de m controles».
    assert set(ev["completitud"]) >= {"declarados", "posibles"}
    assert ev["completitud"]["posibles"] >= ev["completitud"]["declarados"] >= 0


def test_lo_medido_solo_promedia_areas_de_medicion(tmp_path):
    ev = salud.evaluar(_corrida(tmp_path))
    med = [a["puntaje"] for a in ev["areas"].values() if a["tipo"] == "medicion"]
    if med:
        assert abs(ev["medido"]["puntaje"] - round(sum(med) / len(med), 1)) < 0.05
        assert ev["medido"]["areas"] == len(med)


def test_dice_por_escrito_que_es_una_autoevaluacion(tmp_path):
    """Sin esta leyenda el número viaja solo a una presentación."""
    ev = salud.evaluar(_corrida(tmp_path))
    assert ev["es_autoevaluacion"] is True
    nota = ev["nota"].lower()
    assert "autoevaluación" in nota
    assert "no" in nota and ("certifica" in nota or "calidad de los datos" in nota)


def test_el_total_sigue_existiendo_para_no_romper_lo_de_antes(tmp_path):
    """Se agrega información, no se rompe la que ya consumían la app, el
    historial y el manifiesto."""
    ev = salud.evaluar(_corrida(tmp_path))
    assert 0 < ev["total"] <= 100
    assert isinstance(ev["areas"], dict) and "fecha" in ev


def test_el_modelo_es_checklist_y_no_medicion(tmp_path):
    """Es el caso más claro: 40 + 25 + 20 + 15 por declarar cosas en el YAML.
    Nada de eso mide un dato."""
    ev = salud.evaluar(_corrida(tmp_path))
    if "modelo" in ev["areas"]:
        assert ev["areas"]["modelo"]["tipo"] == "checklist"


def test_la_calidad_es_medicion(tmp_path):
    """Sale de correr reglas contra los datos reales: eso sí es una medición."""
    ev = salud.evaluar(_corrida(tmp_path))
    if "calidad" in ev["areas"]:
        assert ev["areas"]["calidad"]["tipo"] == "medicion"


def test_el_resumen_de_entrega_no_vende_el_numero_como_calidad(tmp_path):
    """El `RESUMEN.md` es lo que se le manda al cliente. Si ahí dice
    «salud 96/100» sin aclarar qué es, el número se cita en una reunión."""
    p = _corrida(tmp_path)
    texto = (p.dirs["entrega"] / "RESUMEN.md").read_text(encoding="utf-8")
    assert "autoevaluación" in texto.lower()
