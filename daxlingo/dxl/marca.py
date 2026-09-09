# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · La marca de la empresa, sacada de su logo.

Subís el logo y el programa deduce la paleta: el color corporativo (el que
va en los encabezados, las cabeceras de tabla y de filtro, y las series de
los gráficos) y el color de texto. Nadie tiene que saber el código
hexadecimal de su propia marca — está en el archivo que ya tiene.

Dos decisiones que hacen la diferencia entre «tiene los colores» y «se ve
bien»:

  · **El blanco y los grises no son la marca.** Un logo es mayormente
    fondo: el color que lo identifica suele ocupar poco y ser el más
    saturado, no el más frecuente. Se puntúa frecuencia × saturación.
  · **El texto arriba del color se elige por contraste, no por gusto.**
    Sobre un rojo intenso va blanco; sobre un amarillo corporativo, texto
    oscuro — con blanco no se leería. Se mide con la fórmula de
    luminancia relativa de WCAG, no a ojo.

Si el logo no tiene ningún color propio (un logo en blanco y negro) se
dice `None` y la app cae a elegir los colores a mano: inventar una marca
que no está en el archivo sería peor que preguntar.
"""
from __future__ import annotations

import colorsys
import io

# Gris azulado sobrio para el texto cuando el logo no aporta uno oscuro.
TINTA_NEUTRA = "#33404F"

# Cuánto se agrupan los tonos parecidos al contar (un degradé o un JPG con
# artefactos tiene cientos de rojos casi iguales: sin agrupar, ninguno gana).
_PASO = 24
_LADO_MAX = 220          # la imagen se achica antes de contar: es igual de
                         # representativo y no cuelga con un logo enorme


def _rgb_a_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _luminancia(rgb: tuple[int, int, int]) -> float:
    """Luminancia relativa WCAG (0 = negro, 1 = blanco)."""
    canales = []
    for v in rgb:
        c = v / 255
        canales.append(c / 12.92 if c <= 0.04045
                       else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canales
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Relación de contraste WCAG entre dos colores (1 a 21)."""
    la, lb = _luminancia(a), _luminancia(b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


# Contraste mínimo para un encabezado (texto grande y en negrita): 3:1 es
# el umbral WCAG AA para ese tamaño.
CONTRASTE_MINIMO = 3.0


def texto_sobre(fondo: str) -> str:
    """Blanco o casi-negro: el que se LEA sobre ese fondo.

    Se prefiere el blanco —es lo que hace cualquier manual de marca sobre
    un color corporativo— y solo se cae al oscuro cuando el blanco NO
    llega al contraste mínimo. Elegir por «el número más alto» pondría
    texto negro sobre un rojo intenso: técnicamente más contrastado y
    visualmente equivocado. Sobre un amarillo, en cambio, el blanco
    directamente no se lee, y ahí el oscuro es obligatorio.
    """
    rgb = _hex_a_rgb(fondo)
    if contraste(rgb, (255, 255, 255)) >= CONTRASTE_MINIMO:
        return "#FFFFFF"
    return "#1A1A1A"


def _hex_a_rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _cuenta(datos: bytes) -> list[tuple[tuple[int, int, int], int]]:
    """Colores agrupados del logo, del más al menos frecuente.

    De cada grupo se devuelve el PROMEDIO real de sus píxeles, no el
    centro del casillero: así el color que sale es un color que está de
    verdad en el logo (`#FF0030`, no un `#FC0C3C` aproximado que nadie
    reconocería como su marca).
    """
    from PIL import Image
    im = Image.open(io.BytesIO(datos))
    im = im.convert("RGBA")
    im.thumbnail((_LADO_MAX, _LADO_MAX))
    # `tobytes()` y no `getdata()`: la segunda quedó deprecada y se elimina
    # en Pillow 14 (2027). Esto es un producto que se instala y sigue
    # corriendo por años — no puede traer una bomba con fecha.
    crudo = im.tobytes()
    grupos: dict[tuple[int, int, int], list[int]] = {}
    for i in range(0, len(crudo), 4):
        r, g, b, a = crudo[i], crudo[i + 1], crudo[i + 2], crudo[i + 3]
        if a < 128:
            continue                      # transparente: no es color
        clave = (r // _PASO, g // _PASO, b // _PASO)
        acum = grupos.get(clave)
        if acum is None:
            grupos[clave] = [r, g, b, 1]
        else:
            acum[0] += r
            acum[1] += g
            acum[2] += b
            acum[3] += 1
    salida = [((round(r / n), round(g / n), round(b / n)), n)
              for r, g, b, n in grupos.values()]
    salida.sort(key=lambda par: -par[1])
    return salida


def colores_de_logo(datos: bytes) -> dict | None:
    """
    La paleta que se deduce del logo, o `None` si no se puede.

    Devuelve `{"primario", "tinta", "sobre_primario"}`. `None` cuando el
    archivo no se puede leer (no hay Pillow, imagen corrupta) o cuando el
    logo no tiene ningún color propio: ahí los colores se eligen a mano.
    """
    try:
        colores = _cuenta(datos)
    except Exception:
        # Cualquier cosa: Pillow ausente, formato raro, archivo cortado. La
        # marca es opcional — que falle no puede tumbar una exportación.
        return None
    if not colores:
        return None

    total = sum(n for _c, n in colores)
    mejor, mejor_puntaje = None, 0.0
    oscuro, oscuro_n = None, 0
    for rgb, n in colores:
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in rgb))
        parte = n / total
        # El color de marca: saturado y presente. El peso de la saturación
        # es al cuadrado porque un gris frecuente no es la marca de nadie.
        #
        # No hay tope superior de brillo: el blanco lo descarta la
        # saturación (un blanco tiene s≈0), y ponerle techo dejaba afuera
        # justo a los colores más corporativos —un rojo o un amarillo
        # puros tienen v≈0.99— que es lo que este filtro debe encontrar.
        if s >= 0.25 and v >= 0.15:
            puntaje = parte * (s ** 2) * (0.5 + v)
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje = rgb, puntaje
        # El color de texto: el oscuro más frecuente del logo.
        if v <= 0.55 and n > oscuro_n:
            oscuro, oscuro_n = rgb, n

    if mejor is None:
        return None                      # logo sin color propio

    primario = _rgb_a_hex(mejor)
    tinta = _rgb_a_hex(oscuro) if oscuro else TINTA_NEUTRA
    # Si el «oscuro» es casi el mismo color de marca, el texto perdería el
    # contraste con los encabezados: mejor la tinta neutra.
    if oscuro and contraste(oscuro, mejor) < 1.6:
        tinta = TINTA_NEUTRA
    return {"primario": primario, "tinta": tinta,
            "sobre_primario": texto_sobre(primario)}


def desde_logo(datos: bytes, nombre: str = "logo.png") -> dict | None:
    """La marca completa lista para `tablero.disenar_auto(marca=...)`."""
    paleta = colores_de_logo(datos)
    if paleta is None:
        return None
    return {**paleta, "fondo": "#FFFFFF", "logo": nombre}
