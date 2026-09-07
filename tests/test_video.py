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
