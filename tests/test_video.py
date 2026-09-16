"""El guion de los videos: que esté completo en los tres idiomas y que la voz y
la imagen no se puedan desalinear."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets" / "video"))
import narracion  # noqa: E402


def test_el_guion_esta_completo_en_los_tres_idiomas():
    """Si a un idioma le falta una locución, el video sale MUDO en el medio de
    una escena — se nota y parece roto."""
    assert narracion.faltantes() == {}
    assert set(narracion.IDIOMAS) == {"es", "en", "pt"}
    for i in narracion.IDIOMAS:
        assert set(narracion.GUION[i]) == set(narracion.CLAVES), f"{i} no tiene las mismas claves"


def test_cada_idioma_habla_con_una_voz_de_ese_idioma():
    """Una voz «español neutro» le arruina el registro rioplatense al guion."""
    assert narracion.VOCES_EDGE["es"].startswith("es-AR"), "el español es ARGENTINO a propósito"
    for i, voz in narracion.VOCES_EDGE.items():
        assert voz.startswith(i + "-"), f"{i} habla con una voz {voz}"


def test_la_voz_y_la_imagen_cubren_las_mismas_escenas():
    """El guion visual y el hablado tienen que casar clave a clave: una escena
    sin locución queda muda y una locución sin escena no se escucha nunca."""
    import build_video
    usadas = {c for esc in build_video.ESCENAS.values() for c, _, _ in esc}
    assert usadas == set(narracion.CLAVES)
    for cual, escenas in build_video.ESCENAS.items():
        for clave, titulos, _cap in escenas:
            assert set(titulos) == set(narracion.IDIOMAS), f"{cual}/{clave}: falta un título"


def test_las_capturas_que_el_video_usa_existen():
    from build_video import ESCENAS, IMG, SUFIJO
    for escenas in ESCENAS.values():
        for _clave, _t, cap in escenas:
            if not cap:
                continue
            for idioma in narracion.IDIOMAS:
                nombre = f"{idioma}_{SUFIJO[idioma][cap]}.jpg" if cap in SUFIJO[idioma] else f"{cap}.jpg"
                assert (IMG / nombre).exists(), f"falta la captura {nombre}"


def test_las_cifras_que_el_video_muestra_son_las_que_da_el_motor(tmp_path):
    """El video no puede citar un número que el programa ya no devuelve.

    El guion decía «98,9 sobre cien». Ese 98,9 es el `total` de
    `salud.evaluar()`, y nada verificaba que siguiera siendo 98,9: la fórmula
    del puntaje ya cambió una vez en este repo, y si vuelve a cambiar el único
    que se entera es quien esté mirando el video con el cliente al lado.

    Ahora el video cita `narracion.CIFRAS_CARTERA` y esto corre la demo de
    verdad. Si una cifra se movió, el arreglo es actualizar la constante y
    re-renderizar la placa — no dejar el video andando con el número viejo.
    """
    from mvde import demos, salud
    from mvde.orquestador import Pipeline

    p = Pipeline.desde_yaml(demos.crear("cartera", tmp_path))
    p.correr(hasta="entrega")
    ev = salud.evaluar(p)
    c = narracion.CIFRAS_CARTERA

    assert ev["medido"]["puntaje"] == c["medido"], (
        f"el video muestra {c['medido']} medido y el motor da {ev['medido']['puntaje']}")
    assert ev["medido"]["areas"] == c["areas_medidas"]
    assert ev["completitud"]["declarados"] == c["declarados"]
    assert ev["completitud"]["posibles"] == c["posibles"]


def test_la_locucion_no_recita_el_puntaje():
    """El número vive en la placa; la voz dice qué ES el número.

    Una placa se re-renderiza gratis. Un MP3 hay que volver a generarlo en los
    tres idiomas, y mientras no se genere el video miente con voz propia. Por
    eso el puntaje no vuelve al guion hablado.
    """
    palabras = ("noventa y ocho", "ninety-eight", "noventa e oito",
                "sobre cien", "out of a hundred", "em cem", "por encima de nueve")
    for idioma in narracion.IDIOMAS:
        dicho = narracion.GUION[idioma]["demo_salud"].lower()
        assert not any(ch.isdigit() for ch in dicho), f"{idioma}: la locución recita un número"
        for w in palabras:
            assert w not in dicho, f"{idioma}: la locución vuelve a recitar el puntaje («{w}»)"


def test_la_placa_escribe_el_decimal_como_lo_escribe_cada_idioma():
    """«98.3» en la versión española se lee como un error de la herramienta."""
    assert narracion.cifra("es", 98.3) == "98,3"
    assert narracion.cifra("pt", 98.3) == "98,3"
    assert narracion.cifra("en", 98.3) == "98.3"
