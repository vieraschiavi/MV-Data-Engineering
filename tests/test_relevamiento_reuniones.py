"""Relevamiento (preguntas al cliente, repreguntas, puente al YAML) y reuniones
(transcripción a minuta, y de la minuta a respuestas del relevamiento)."""
import json

import pytest

from mvde import ETAPAS, relevamiento, reuniones
from mvde.i18n import LANGS

VTT = """WEBVTT

00:00:01.000 --> 00:00:09.500
<v Ana Pérez>Buenos días. Los datos de ventas salen del SAP, y el maestro de clientes viene de una planilla.

00:00:09.500 --> 00:00:15.000
<v Ana Pérez>La planilla se actualiza todos los días a las 8 de la mañana.

00:00:16.000 --> 00:00:28.000
<v Diego Sosa>El problema es que no tenemos acceso directo al SAP. Habría que ver con Sistemas.

00:00:29.000 --> 00:00:41.000
<v Ana Pérez>Decidimos entonces arrancar con la exportación diaria. ¿Quién es el dueño del dato de ventas?

00:00:42.000 --> 00:00:52.000
<v Diego Sosa>El dueño es Marcela Rodríguez, de Comercial. Yo te paso el contacto mañana.
"""


# ------------------------------------------------------------------ relevamiento
def test_hay_preguntas_para_las_doce_etapas_en_los_tres_idiomas():
    for lang in LANGS:
        cat = relevamiento.catalogo(lang)
        assert len(cat) >= 40
        assert {q["etapa"] for q in cat} == set(ETAPAS), "toda etapa del pipeline tiene que tener preguntas"
        # Si faltara un texto, `t` devuelve la clave cruda: eso no puede pasar.
        assert not [q for q in cat if q["pregunta"].startswith("rq_") or q["porque"].startswith("rq_")]
        assert not [q for q in cat if q["rol_texto"].startswith("rol_")]


def test_responder_no_muta_el_original_y_registra_quien_contesto():
    d = relevamiento.vacio("Conaprole")
    d2 = relevamiento.responder(d, "fuentes_sistemas", "SAP y una planilla", "Ana Pérez", "Comercial")
    assert d["respuestas"] == {}, "el original no se toca"
    fila = d2["respuestas"]["fuentes_sistemas"]
    assert fila["respuesta"] == "SAP y una planilla" and fila["responsable"] == "Ana Pérez"
    assert fila["area"] == "Comercial" and fila["estado"] == "respondida" and fila["fecha"]


def test_avance_cuenta_respondidas_y_no_aplica():
    d = relevamiento.vacio()
    total = len(relevamiento.catalogo("es"))
    assert sum(a["respondidas"] for a in relevamiento.avance(d)) == 0
    d = relevamiento.responder(d, "ml_decision", "Priorizar la gestión de cobranza", "Marcela")
    d = relevamiento.responder(d, "ml_casos", "", estado="no_aplica")
    av = relevamiento.avance(d)
    assert sum(a["respondidas"] for a in av) == 2, "«no aplica» también cierra la pregunta"
    assert sum(a["total"] for a in av) == total


@pytest.mark.parametrize("respuesta,esperado", [
    ("", "rp_sin_respuesta"),
    ("no sé, habría que ver con Sistemas cómo se accede a eso", "rp_incertidumbre"),
    ("depende del mes y de la campaña que esté corriendo", "rp_depende"),
    ("sale del SAP de la empresa y de ahí lo bajamos", "rp_sistema_sin_acceso"),
])
def test_las_repreguntas_locales_detectan_la_forma_de_la_respuesta(respuesta, esperado):
    """Sin IA: no mira el tema, mira por qué la respuesta no alcanza para decidir."""
    from mvde.i18n import t
    q = next(x for x in relevamiento.catalogo("es") if x["id"] == "fuentes_volumen")
    salida = relevamiento.repreguntas_locales(q["pregunta"], respuesta)
    assert t(esperado, "es") in salida, salida


def test_una_respuesta_completa_con_responsable_no_dispara_ruido():
    q = next(x for x in relevamiento.catalogo("es") if x["id"] == "fuentes_volumen")
    salida = relevamiento.repreguntas_locales(
        q["pregunta"], "Hoy son 4.200.000 filas y crecen unas 180.000 por mes.", "Ana Pérez")
    assert salida == []


def test_repreguntas_sin_proveedor_cae_en_las_locales():
    q = relevamiento.catalogo("es")[0]
    r = relevamiento.repreguntas(q["pregunta"], "", q["porque"], "", "es", proveedor="")
    assert r["modo"] == "local" and r["repreguntas"]


def test_las_respuestas_se_traducen_a_cambios_del_yaml():
    d = relevamiento.vacio("Conaprole")
    d = relevamiento.responder(d, "gobernanza_dueno_dato", "Marcela Rodríguez, de Comercial")
    d = relevamiento.responder(d, "entrega_frecuencia", "Todos los días, listo a las 08:00")
    d = relevamiento.responder(d, "gobernanza_pii", "documento, telefono y email")
    campos = {s["campo"]: s for s in relevamiento.sugerencias_yaml(d)}
    assert campos["gobernanza.dueno"]["valor"].startswith("Marcela")
    assert campos["frescura.cada"]["valor"] == "diaria"
    assert campos["automatizacion.hora"]["valor"] == "08:00"
    spec = {"nombre": "x", "gobernanza": {"dueno": "", "pii": []}}
    nuevo = relevamiento.aplicar_sugerencia(spec, campos["gobernanza.dueno"])
    assert nuevo["gobernanza"]["dueno"].startswith("Marcela")
    assert spec["gobernanza"]["dueno"] == "", "aplicar no muta el spec original"
    con_pii = relevamiento.aplicar_sugerencia(spec, campos["gobernanza.pii"])
    assert {"documento", "telefono", "email"} <= set(con_pii["gobernanza"]["pii"])


def test_ida_y_vuelta_al_disco(tmp_path):
    d = relevamiento.responder(relevamiento.vacio("Conaprole"), "reporte_kpis", "Cobranza del mes", "Ana")
    ruta = relevamiento.guardar(d, tmp_path / relevamiento.ARCHIVO)
    vuelta = relevamiento.cargar(ruta)
    assert vuelta["cliente"] == "Conaprole" and vuelta["actualizado"]
    assert vuelta["respuestas"]["reporte_kpis"]["responsable"] == "Ana"
    # Un archivo ilegible no rompe la pestaña: se arranca de cero.
    (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
    assert relevamiento.cargar(tmp_path / "roto.json")["respuestas"] == {}
    assert relevamiento.cargar(tmp_path / "no_existe.json")["respuestas"] == {}


def test_exporta_markdown_y_excel(tmp_path):
    d = relevamiento.responder(relevamiento.vacio("Conaprole"), "calidad_criticas", "Que falte un día de ventas", "Diego", "TI")
    md = relevamiento.markdown(d, "es")
    assert "Conaprole" in md and "Que falte un día de ventas" in md and "Diego" in md
    ruta = relevamiento.excel(tmp_path / "r.xlsx", d, "es")
    assert ruta.exists() and ruta.stat().st_size > 5000


# ------------------------------------------------------------------ reuniones
def test_vtt_de_la_plataforma_trae_hablantes_y_minutos():
    tn = reuniones.parsear(VTT)
    # Cinco subtítulos: los dos primeros son de Ana seguidos y se fusionan; después
    # alterna, así que quedan cuatro turnos de conversación.
    assert len(tn) == 4, "los subtítulos seguidos del mismo hablante son un solo turno"
    assert [x["hablante"] for x in tn] == ["Ana Pérez", "Diego Sosa", "Ana Pérez", "Diego Sosa"]
    assert tn[0]["inicio"] == 1.0 and tn[0]["fin"] == 15.0
    assert "planilla" in tn[0]["texto"] and "8 de la mañana" in tn[0]["texto"]


def test_texto_plano_con_nombre_y_dos_puntos():
    tn = reuniones.parsear("Ana: Los datos salen del ERP.\nDiego: No tenemos acceso todavía.")
    assert [x["hablante"] for x in tn] == ["Ana", "Diego"]
    assert tn[0]["inicio"] is None


def test_transcripcion_sin_hablantes_se_declara_como_tal():
    tn = reuniones.parsear("Se habló de las fuentes y de la calidad del dato, sin nombres.")
    m = reuniones.minuta(tn)
    assert m["con_hablantes"] is False
    assert m["participantes"][0]["hablante"] == "?"


def test_la_minuta_extrae_decisiones_compromisos_riesgos_y_preguntas():
    m = reuniones.minuta(reuniones.parsear(VTT), "Kickoff")
    assert [p["hablante"] for p in m["participantes"]][0] == "Ana Pérez", "ordena por cuánto habló"
    assert any("Decidimos" in d["texto"] for d in m["decisiones"])
    assert any("te paso" in c["texto"] for c in m["compromisos"])
    assert m["compromisos"][0]["cuando"] == "mañana", "el compromiso guarda el cuándo si se dijo"
    assert any("no tenemos acceso" in r["texto"].lower() for r in m["riesgos"])
    assert any(q["texto"].endswith("?") for q in m["preguntas"])
    # Cada ítem es trazable: quién lo dijo y en qué minuto.
    assert all("hablante" in d and "inicio" in d for d in m["decisiones"])


def test_las_menciones_se_atan_a_las_etapas_del_pipeline():
    m = reuniones.minuta(reuniones.parsear(VTT))
    assert "fuentes" in m["menciones"], "se habló de SAP y de una planilla"
    assert set(m["menciones"]) <= set(ETAPAS)


def test_de_la_reunion_salen_respuestas_propuestas_para_el_relevamiento():
    propuestas = reuniones.sugerir_respuestas(reuniones.parsear(VTT), "es")
    assert propuestas, "algo de lo que se dijo tiene que engancharse con alguna pregunta"
    assert set(propuestas) <= {q["id"] for q in relevamiento.catalogo("es")}
    for prop in propuestas.values():
        assert prop["texto"] and prop["coincidencias"] >= 2


def test_transcribir_avisa_cuando_el_proveedor_no_transcribe():
    with pytest.raises(RuntimeError, match="no transcribe audio"):
        reuniones.transcribir(b"x", "a.mp3", "claude", "clave")
    with pytest.raises(RuntimeError, match="[Ff]alta la clave"):
        reuniones.transcribir(b"x", "a.mp3", "openai", "")
    grande = b"x" * (reuniones.LIMITE_MB * 1024 * 1024 + 1)
    with pytest.raises(RuntimeError, match="límite"):
        reuniones.transcribir(grande, "a.mp3", "openai", "clave")


def test_guardar_y_listar_minutas(tmp_path):
    tn = reuniones.parsear(VTT)
    m = reuniones.minuta(tn, "Kickoff Conaprole")
    ruta = reuniones.guardar(tmp_path, m, tn)
    assert ruta.exists() and "Kickoff_Conaprole" in ruta.name
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    assert guardado["minuta"]["titulo"] == "Kickoff Conaprole" and len(guardado["turnos"]) == 4
    assert reuniones.listar(tmp_path) == [ruta]
    assert reuniones.listar(tmp_path / "no_existe") == []


def test_markdown_de_la_minuta_en_los_tres_idiomas():
    m = reuniones.minuta(reuniones.parsear(VTT), "Kickoff")
    for lang in LANGS:
        md = reuniones.markdown(m, lang)
        assert "Ana Pérez" in md and "Decidimos" in md
        assert "mt_" not in md, "una clave sin traducir se colaría como texto"
