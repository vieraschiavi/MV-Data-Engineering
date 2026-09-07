#!/usr/bin/env python3
# © 2026 Martín Viera. Todos los derechos reservados.
"""
MV Data Engineering · Montaje de los dos videos, uno por idioma.

    assets/video/MVDataEngineering_Comercial_{es,en,pt}.mp4   (~2 min, para vender)
    assets/video/MVDataEngineering_Demo_{es,en,pt}.mp4        (el pipeline end-to-end)

Los dos se copian a `landing/video/`, que es de donde la landing sirve el que
corresponde al idioma elegido por el visitante.

Las escenas usan las CAPTURAS REALES del programa (`landing/img/`), no maquetas:
si la interfaz cambia, se vuelven a sacar las capturas y el video queda al día.

Sincronización sin desfasaje
----------------------------
Cada escena dura lo que dura su locución más un respiro, medido sobre el MP3 de
`assets/video/audio/<idioma>/`. NO hay duración fija: si el guion de un idioma
es más largo, esa escena dura más en ese idioma y punto.

Sin los MP3 el video se arma igual, mudo y con una duración de lectura estimada
por largo de texto, y lo deja dicho en la salida. Es lo que permite verificar el
montaje en un entorno sin salida a internet (ver `narracion.py`).

    python assets/video/build_video.py                # los dos videos, 3 idiomas
    python assets/video/build_video.py --idioma es --video comercial
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

# Pillow, imageio e imageio-ffmpeg se importan DENTRO de las funciones que
# renderizan, no acá. No son dependencias del producto — no están en
# `requirements.txt`, son herramientas de producción de material —, y el
# módulo tiene que poder importarse sin ellas: `tests/test_video.py` lee
# ESCENAS, IMG y SUFIJO para verificar que ninguna escena apunte a una captura
# que no existe, y ese test corre en el CI, que instala sólo `requirements.txt`.
# Con los import arriba ese test se cae por ImportError sin haber mirado nada.
if TYPE_CHECKING:                # sólo para la anotación de _placa
    from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narracion import CLAVES, GUION, IDIOMAS  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
AUDIO = Path(__file__).resolve().parent / "audio"
SALIDA = Path(__file__).resolve().parent
IMG = RAIZ / "landing" / "img"

W, H, FPS = 1920, 1080, 30
TINTA, TINTA2, LINEA = (11, 27, 52), (18, 39, 68), (29, 53, 87)
TEXTO, TEXTO2, ACENTO = (232, 238, 247), (157, 176, 204), (240, 180, 41)
RESPIRO = 0.7          # segundos de aire después de que termina la locución
SIN_VOZ_CPS = 15.0     # caracteres por segundo, para estimar sin MP3

# Guion visual: por escena, el título de la placa y la captura que la acompaña.
# La clave es la misma que en narracion.GUION, y así la voz y la imagen no se
# pueden desalinear: si falta una, el test lo dice.
ESCENAS = {
    "comercial": [
        ("com_intro",    {"es": "Tu pipeline, entero", "en": "Your pipeline, whole", "pt": "Seu pipeline, inteiro"}, None),
        ("com_problema", {"es": "El problema", "en": "The problem", "pt": "O problema"}, None),
        ("com_gate",     {"es": "12 etapas con gate", "en": "12 gated stages", "pt": "12 etapas com gate"}, "1_pipeline"),
        ("com_salud",    {"es": "Se puntúa a sí mismo", "en": "It scores itself", "pt": "Pontua-se a si mesmo"}, "2_salud"),
        ("com_local",    {"es": "Tus datos, en tu máquina", "en": "Your data, on your machine", "pt": "Seus dados, na sua máquina"}, "3_cargas"),
        ("com_cierre",   {"es": "Licencia perpetua", "en": "Perpetual licence", "pt": "Licença perpétua"}, None),
    ],
    "demo": [
        ("demo_intro",      {"es": "Una corrida completa", "en": "A complete run", "pt": "Uma execução completa"}, None),
        ("demo_yaml",       {"es": "Se declara, no se programa", "en": "Declared, not programmed", "pt": "Declara-se, não se programa"}, None),
        ("demo_pipeline",   {"es": "Las 12 etapas", "en": "The 12 stages", "pt": "As 12 etapas"}, "1_pipeline"),
        ("demo_calidad",    {"es": "El gate de calidad", "en": "The quality gate", "pt": "O gate de qualidade"}, "4_transformaciones"),
        ("demo_proyeccion", {"es": "Backtest de origen móvil", "en": "Rolling-origin backtest", "pt": "Backtest de origem móvel"}, "proyeccion"),
        ("demo_banda",      {"es": "La banda es medida", "en": "The band is measured", "pt": "A faixa é medida"}, "proyeccion"),
        ("demo_salud",      {"es": "98,9 / 100", "en": "98.9 / 100", "pt": "98,9 / 100"}, "2_salud"),
        ("demo_cierre",     {"es": "De la fuente al tablero", "en": "From source to dashboard", "pt": "Da fonte ao painel"}, "5_relevamiento"),
    ],
}

# La captura de cada escena depende del idioma; `proyeccion` es la única que no
# (es un gráfico, no una pantalla con texto).
SUFIJO = {"es": {"1_pipeline": "1_pipeline", "2_salud": "2_salud", "3_cargas": "3_cargas",
                 "4_transformaciones": "4_transformaciones", "5_relevamiento": "5_relevamiento"},
          "en": {"1_pipeline": "1_pipeline", "2_salud": "2_health", "3_cargas": "3_loads",
                 "4_transformaciones": "4_transformations", "5_relevamiento": "5_discovery"},
          "pt": {"1_pipeline": "1_pipeline", "2_salud": "2_saude", "3_cargas": "3_cargas",
                 "4_transformaciones": "4_transformacoes", "5_relevamiento": "5_levantamento"}}


def _fuente(tam: int, negrita: bool = False):
    from PIL import ImageFont

    for ruta in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if negrita else ''}.ttf",
                 f"/usr/share/fonts/TTF/DejaVuSans{'-Bold' if negrita else ''}.ttf"):
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default(tam)


def _duracion_mp3(p: Path) -> float | None:
    """Largo real del MP3, con ffprobe si está y si no estimando por bitrate."""
    ff = shutil.which("ffprobe")
    if ff:
        try:
            out = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration",
                                  "-of", "csv=p=0", str(p)], capture_output=True, text=True, timeout=20)
            return float(out.stdout.strip())
        except (ValueError, subprocess.SubprocessError):
            pass
    try:                                     # 128 kbps aproximado; sólo un respaldo
        return p.stat().st_size * 8 / 128_000
    except OSError:
        return None


def _placa(titulo: str, captura: Path | None, idioma: str) -> "Image.Image":
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (W, H), TINTA)
    d = ImageDraw.Draw(im)
    # Marca arriba a la izquierda, siempre en el mismo lugar.
    d.text((80, 62), "MV · DATA ENGINEERING", font=_fuente(26, True), fill=ACENTO)
    d.text((80, 140), titulo, font=_fuente(64, True), fill=TEXTO)
    d.line([(80, 232), (80 + 120, 232)], fill=ACENTO, width=5)
    if captura and captura.exists():
        foto = Image.open(captura).convert("RGB")
        ancho = W - 160
        foto = foto.resize((ancho, int(foto.height * ancho / foto.width)), Image.LANCZOS)
        alto_max = H - 300
        if foto.height > alto_max:                     # se recorta por abajo, no se deforma
            foto = foto.crop((0, 0, foto.width, alto_max))
        caja = Image.new("RGB", (foto.width + 8, foto.height + 8), LINEA)
        caja.paste(foto, (4, 4))
        im.paste(caja, (80, 276))
    else:
        d.rectangle([80, 300, W - 80, H - 120], fill=TINTA2, outline=LINEA, width=2)
    return im


def construir(idioma: str, cual: str) -> Path:
    import imageio.v2 as imageio

    escenas, cuadros, mudas = ESCENAS[cual], [], 0
    audios: list[Path] = []
    for clave, titulos, cap in escenas:
        mp3 = AUDIO / idioma / f"{clave}.mp3"
        if mp3.exists():
            dur = (_duracion_mp3(mp3) or 3.0) + RESPIRO
            audios.append(mp3)
        else:
            dur = max(2.5, len(GUION[idioma][clave]) / SIN_VOZ_CPS) + RESPIRO
            mudas += 1
        ruta_cap = IMG / (f"{idioma}_{SUFIJO[idioma][cap]}.jpg" if cap in SUFIJO[idioma]
                          else f"{cap}.jpg") if cap else None
        placa = np.asarray(_placa(titulos[idioma], ruta_cap, idioma))
        cuadros.append((placa, dur))

    salida = SALIDA / f"MVDataEngineering_{cual.capitalize()}_{idioma}.mp4"
    escritor = imageio.get_writer(salida, fps=FPS, codec="libx264", quality=8,
                                  macro_block_size=1, ffmpeg_log_level="error")
    for placa, dur in cuadros:
        for _ in range(int(round(dur * FPS))):
            escritor.append_data(placa)
    escritor.close()

    if audios and len(audios) == len(escenas):
        salida = _pegar_audio(salida, audios)
    total = sum(d for _, d in cuadros)
    print(f"  {salida.name}  {total:.0f}s  {salida.stat().st_size/1e6:.1f} MB"
          + (f"  ⚠ {mudas}/{len(escenas)} escenas SIN voz" if mudas else "  · con voz"))
    return salida


def _pegar_audio(video: Path, audios: list[Path]) -> Path:
    """Concatena las locuciones y las monta sobre el video ya armado."""
    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    lista = video.with_suffix(".txt")
    lista.write_text("".join(f"file '{a.resolve()}'\n" for a in audios), encoding="utf-8")
    pista = video.with_name(video.stem + "_voz.mp3")
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(pista)],
                   check=True, capture_output=True)
    final = video.with_name(video.stem + "_av.mp4")
    subprocess.run([ff, "-y", "-i", str(video), "-i", str(pista), "-c:v", "copy", "-c:a", "aac",
                    "-shortest", str(final)], check=True, capture_output=True)
    final.replace(video)
    lista.unlink(missing_ok=True)
    pista.unlink(missing_ok=True)
    return video


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idioma", choices=IDIOMAS)
    ap.add_argument("--video", choices=tuple(ESCENAS))
    a = ap.parse_args()

    # El guion visual y el hablado tienen que cubrir las mismas claves.
    usadas = {c for esc in ESCENAS.values() for c, _, _ in esc}
    if (sobran := usadas - set(CLAVES)) or (faltan := set(CLAVES) - usadas):
        print(f"guion desalineado — sin locución: {sobran} · sin escena: {faltan}", file=sys.stderr)
        return 1

    destino = RAIZ / "landing" / "video"
    destino.mkdir(parents=True, exist_ok=True)
    for idioma in ([a.idioma] if a.idioma else IDIOMAS):
        print(f"=== {idioma}")
        for cual in ([a.video] if a.video else tuple(ESCENAS)):
            v = construir(idioma, cual)
            shutil.copy2(v, destino / v.name)
    print(f"\ncopiados a {destino.relative_to(RAIZ)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
