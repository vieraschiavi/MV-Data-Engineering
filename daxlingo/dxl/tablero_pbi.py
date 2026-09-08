#!/usr/bin/env python3
# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · El antes y el después, dibujados COMO UN TABLERO DE POWER BI.

Por qué existe
--------------
El video y la infografía contaban el trabajo en el idioma de quien arregla
modelos: reglas, severidades, salud 37 → 98. Un gerente que mira eso no ve
qué gana — ve una nota de un examen que no rindió.

Lo que ese gerente SÍ reconoce es su propio tablero. Así que acá se dibuja
uno: fondo gris claro, tarjetas blancas, segmentaciones arriba, la tipografía
y la paleta de Power BI. Y se dibuja DOS VECES, con el mismo layout y los
mismos visuales, cambiando solo lo que el programa arregla. La diferencia se
ve sin leer una palabra: a la izquierda una tarjeta que dice «(En blanco)» y
un visual que no puede dibujarse; a la derecha, los dos con su número.

Honestidad de lo que se muestra
-------------------------------
Los síntomas del lado ANTES no son adorno: cada uno es la cara visible de un
hallazgo REAL de la auditoría, el que el programa encuentra y corrige.

  · tarjeta «(En blanco)»    ← R09: relación bidireccional / muchos-a-muchos
                                ambiguo. La medida no resuelve y Power BI
                                muestra el blanco, sin decir por qué.
  · visual que no dibuja     ← el mismo camino ambiguo, del lado del gráfico.
  · «sin sincronizar»        ← el slicer que estaba fuera de los grupos de
                                sincronización (1 de 74; el programa lo
                                sincronizó en 4 páginas).
  · salud 37 → 98            ← la cifra real de la auditoría del tablero A.

Y los NÚMEROS que se ven en el lado «después» no son inventados ni elegidos
para que luzcan: se calculan acá mismo, de los CSV del modelo demo que el
producto distribuye (`datos/demo/sintetico/`), que es un dataset 100 %
sintético generado con semilla fija. Si el demo se regenera, estos números
cambian solos — no hay una tabla de valores lindos escrita a mano.

Se usa en tres lugares, con este mismo dibujo:
    · el video del caso real  (build_video_caso.py → panel_tablero)
    · la pieza de LinkedIn    (build_linkedin.py)
    · el programa             (app/app.py, pestaña Analizador)

Vive en `dxl/` y no en `media/` porque es parte del PRODUCTO: el programa lo
dibuja en vivo en la pestaña Analizador. `media/` y `web/` no viajan en el
instalador (ver los filtros de desktop/package.json), así que un módulo de
marketing ahí sería invisible para el cliente. Pillow ya viaja: streamlit lo
declara como dependencia.

Para regenerar los PNG de la web y de LinkedIn:
    python daxlingo/media/build_tablero.py          # es, en, pt
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]

DEMO = RAIZ / "datos" / "demo" / "sintetico"

# Medidas de referencia del lienzo. Quien lo use lo escala con `.resize()`:
# dibujar siempre al mismo tamaño y reducir después da un resultado parejo en
# el video (1920×1080), en LinkedIn (1080×1350) y en el programa.
ANCHO, ALTO = 1120, 700

# ---- paleta de Power BI ---------------------------------------------------
# El look es la mitad del mensaje: si no se parece a Power BI, el cliente no
# reconoce su tablero y todo el ejercicio se cae. Estos son los colores del
# tema por defecto (light) y los grises de la interfaz.
FONDO = (241, 241, 241)        # lienzo del informe
TARJETA = (255, 255, 255)
BORDE = (225, 225, 225)
TITULO = (37, 36, 35)          # gris casi negro de los títulos de visual
TEXTO = (97, 97, 97)
SUAVE = (161, 159, 157)
CABECERA = (32, 31, 30)
SERIE = [(17, 141, 255), (18, 35, 158), (230, 108, 55),
         (107, 0, 123), (224, 68, 167)]
OK = (16, 124, 16)             # verde de Power BI
MAL = (168, 0, 0)              # rojo de error
AVISO = (223, 106, 0)
AMARILLO = (217, 179, 0)

# Fuentes, buscadas en el sistema en vez de escritas a mano.
#
# La primera versión tenía las rutas de DejaVu de Linux fijas en el código y
# reventaba en Windows con `OSError: cannot open resource` — y no la pestaña
# sola: la app entera, porque Streamlit corre el script de arriba abajo. El
# clásico «anduvo en mi máquina»: acá se desarrolla en Linux y el producto se
# vende para Windows.
#
# El orden no es casual. Segoe UI va primera porque es LA tipografía de Power
# BI: en la máquina de un cliente de Windows el lienzo sale con la letra de
# verdad, no con una parecida.
_CANDIDATAS = {
    "normal": [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "negrita": [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
}

# Carpetas donde rastrear si ninguna candidata está. Es el plan B antes de
# rendirse: una instalación puede tener fuentes perfectamente usables con
# otros nombres.
_CARPETAS = [r"C:\Windows\Fonts", "/usr/share/fonts", "/Library/Fonts",
             "/System/Library/Fonts", str(Path.home() / ".fonts")]

_resueltas: dict[str, str | None] = {}


def _archivo_fuente(estilo: str) -> str | None:
    if estilo in _resueltas:
        return _resueltas[estilo]
    for ruta in _CANDIDATAS[estilo]:
        if Path(ruta).exists():
            _resueltas[estilo] = ruta
            return ruta
    # Ninguna de las conocidas: se busca CUALQUIER TrueType instalada.
    negrita = estilo == "negrita"
    for carpeta in _CARPETAS:
        base = Path(carpeta)
        if not base.is_dir():
            continue
        for ttf in sorted(base.rglob("*.ttf")):
            if ("bold" in ttf.name.lower()) == negrita:
                _resueltas[estilo] = str(ttf)
                return str(ttf)
    _resueltas[estilo] = None
    return None


def fuente(estilo: str, tamano: int):
    """La fuente pedida, o la de PIL si el sistema no tiene ninguna.

    Nunca levanta: el lienzo es una ayuda visual, y quedarse sin una
    tipografía no puede ser motivo para que el programa no abra.
    """
    ruta = _archivo_fuente(estilo)
    if ruta:
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            _resueltas[estilo] = None
    try:                       # Pillow >= 10.1 acepta tamaño en la default
        return ImageFont.load_default(size=tamano)
    except TypeError:          # Pillow viejo: sale chica, pero sale
        return ImageFont.load_default()


# ==========================================================================
# Los datos: reales, del demo sintético que viaja con el producto
# ==========================================================================
_cache: dict | None = None


def datos() -> dict:
    """Agregados del modelo demo. Se calculan, no se escriben.

    Un panel de marketing con cifras copiadas a mano es un panel que
    envejece solo y termina mostrando algo que el producto ya no hace. Acá
    se leen los mismos CSV que abre el programa cuando alguien toca «probar
    con el modelo demo», así que lo que se ve en la imagen es exactamente lo
    que va a ver en pantalla.
    """
    global _cache
    if _cache is not None:
        return _cache

    # `datos/demo/sintetico/` está gitignoreado A PROPÓSITO: los CSV son
    # artefactos regenerables con semilla fija (SEMILLA = 42), no fuente. O
    # sea que existen en una copia de trabajo y en el paquete que se
    # entrega, pero NO en un clon limpio ni en el runner de CI — que es
    # exactamente donde esto reventó con FileNotFoundError, después de pasar
    # perfecto en local.
    #
    # Se regeneran acá en vez de commitearse: la semilla fija garantiza los
    # mismos bytes, tarda una décima de segundo, y así no hay dos copias de
    # los datos que puedan discrepar.
    if not (DEMO / "ventas.csv").exists():
        sys.path.insert(0, str(RAIZ / "datos" / "demo"))
        import generar_sintetico
        generar_sintetico.generar_datos(DEMO)

    def leer(nombre):
        with open(DEMO / nombre, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    ventas = leer("ventas.csv")
    clientes = {c["IdCliente"]: c for c in leer("clientes.csv")}
    productos = {p["IdProducto"]: p for p in leer("productos.csv")}

    importe = sum(float(v["Importe"]) for v in ventas)
    costo = sum(float(v["Costo"]) for v in ventas)

    por_pais: Counter = Counter()
    por_cat: Counter = Counter()
    por_mes: Counter = Counter()
    costo_cat: Counter = Counter()
    for v in ventas:
        imp = float(v["Importe"])
        cat = productos[v["IdProducto"]]["Categoria"]
        por_pais[clientes[v["IdCliente"]]["Pais"]] += imp
        por_cat[cat] += imp
        costo_cat[cat] += float(v["Costo"])
        por_mes[v["Fecha"][:7]] += imp

    _cache = {
        "ventas": importe,
        "margen": (importe - costo) / importe * 100,
        "unidades": sum(int(v["Cantidad"]) for v in ventas),
        "pais": por_pais.most_common(5),
        "categoria": por_cat.most_common(4),
        "margen_categoria": {c: (por_cat[c] - costo_cat[c]) / por_cat[c] * 100
                             for c in por_cat},
        "mes": [por_mes[m] for m in sorted(por_mes)],
    }
    return _cache


def _millones(v: float) -> str:
    """26.590.066 → «26,6 M». Formato rioplatense: coma decimal."""
    return f"{v / 1e6:,.1f} M".replace(".", ",")


def _miles(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


# ==========================================================================
# Piezas de la interfaz de Power BI
# ==========================================================================
def _visual(dib, caja, titulo, f_tit):
    """El contenedor blanco con su título, que es la unidad de todo informe."""
    dib.rounded_rectangle(caja, radius=4, fill=TARJETA, outline=BORDE, width=1)
    if titulo:
        dib.text((caja[0] + 14, caja[1] + 11), titulo, font=f_tit, fill=TITULO)
    return caja


def _tarjeta_kpi(dib, caja, etiqueta, valor, *, blanco=None, chico=False):
    """Tarjeta de KPI. `blanco=True` la dibuja como la ve el cliente cuando la
    medida no resuelve: «(En blanco)» en gris, que es literalmente lo que
    escribe Power BI — sin un error, sin una pista de por qué."""
    x0, y0, x1, y1 = caja
    dib.rounded_rectangle(caja, radius=4, fill=TARJETA, outline=BORDE, width=1)
    f_val = fuente("negrita", 34 if not chico else 30)
    f_et = fuente("normal", 15)

    if blanco:
        texto, color = blanco, SUAVE
        f_val = fuente("normal", 27)
    else:
        texto, color = valor, TITULO
    cx = (x0 + x1) / 2
    ancho = dib.textlength(texto, font=f_val)
    dib.text((cx - ancho / 2, y0 + 26), texto, font=f_val, fill=color)
    ancho_et = dib.textlength(etiqueta, font=f_et)
    dib.text((cx - ancho_et / 2, y1 - 30), etiqueta, font=f_et, fill=TEXTO)

    if blanco:
        # El triangulito de advertencia NO existe en Power BI para este caso
        # —ese es justo el problema, no avisa nada— así que se marca con el
        # borde, que sí es una licencia nuestra y se lee como «mirá acá».
        dib.rounded_rectangle(caja, radius=4, outline=MAL, width=2)


def _barras(dib, caja, pares, f_et, t, *, roto=False):
    """Barras horizontales, como el gráfico de barras agrupadas de Power BI.

    `roto=True` dibuja lo que el cliente ve cuando el camino de filtrado es
    ambiguo: el marco del visual con el cartel de error en el medio, en vez
    del gráfico. Es el mensaje textual de Power BI.
    """
    x0, y0, x1, y1 = caja
    if roto:
        f_msg = fuente("normal", 16)
        f_sub = fuente("normal", 13)
        msg, sub = t["err_visual"], t["err_relacion"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # El cuadradito roto, arriba del texto: es el ícono que Power BI
        # pone cuando un visual no puede resolverse.
        lado = 26
        dib.rounded_rectangle([cx - lado / 2, cy - 46, cx + lado / 2, cy - 46 + lado],
                              radius=3, outline=MAL, width=2)
        dib.line([cx - 6, cy - 40, cx + 6, cy - 28], fill=MAL, width=2)
        dib.line([cx + 6, cy - 40, cx - 6, cy - 28], fill=MAL, width=2)
        for texto, fnt, dy, col in ((msg, f_msg, 0, TITULO), (sub, f_sub, 24, TEXTO)):
            dib.text((cx - dib.textlength(texto, font=fnt) / 2, cy + dy),
                     texto, font=fnt, fill=col)
        return

    tope = max(v for _, v in pares) or 1
    alto_b = (y1 - y0) // len(pares)
    ancho_et = max(dib.textlength(n, font=f_et) for n, _ in pares) + 12
    for i, (nombre, valor) in enumerate(pares):
        yy = y0 + i * alto_b
        dib.text((x0, yy + (alto_b - f_et.size) / 2 - 1), nombre,
                 font=f_et, fill=TEXTO)
        bx = x0 + ancho_et
        largo = (x1 - bx - 54) * (valor / tope)
        dib.rectangle([bx, yy + 5, bx + largo, yy + alto_b - 7], fill=SERIE[0])
        v = _millones(valor)
        dib.text((bx + largo + 8, yy + (alto_b - f_et.size) / 2 - 1), v,
                 font=f_et, fill=TEXTO)


def _lineas(dib, caja, serie, f_et):
    """Gráfico de líneas de 24 meses. Es el mismo en los dos lados: no todo
    está roto en un tablero con problemas, y decirlo es parte de ser
    creíble."""
    x0, y0, x1, y1 = caja
    tope, piso = max(serie), min(serie)
    rango = (tope - piso) or 1
    paso = (x1 - x0) / (len(serie) - 1)
    puntos = [(x0 + i * paso, y1 - (v - piso) / rango * (y1 - y0))
              for i, v in enumerate(serie)]
    # Relleno tenue bajo la línea, como el área del tema por defecto.
    dib.polygon(puntos + [(x1, y1), (x0, y1)], fill=(222, 238, 255))
    dib.line(puntos, fill=SERIE[0], width=3, joint="curve")


def _slicer(dib, caja, titulo, valor, f_tit, f_val, *, aviso=None):
    """Segmentación (slicer) desplegable. `aviso` pinta la etiqueta de estado
    de sincronización: es el hallazgo que ningún cliente ve solo, porque
    filtrar en una página y que otra no cambie parece «así es Power BI»."""
    x0, y0, x1, y1 = caja
    dib.rounded_rectangle(caja, radius=4, fill=TARJETA, outline=BORDE, width=1)
    dib.text((x0 + 10, y0 + 7), titulo, font=f_tit, fill=TEXTO)
    dib.text((x0 + 10, y0 + 26), valor, font=f_val, fill=TITULO)
    # La flechita del desplegable.
    fx, fy = x1 - 20, y0 + 30
    dib.polygon([(fx, fy), (fx + 10, fy), (fx + 5, fy + 6)], fill=TEXTO)
    if aviso:
        texto, color = aviso
        f = fuente("negrita", 11)
        an = dib.textlength(texto, font=f) + 14
        dib.rounded_rectangle([x1 - an - 6, y1 - 20, x1 - 6, y1 - 4],
                              radius=8, fill=color)
        dib.text((x1 - an, y1 - 18), texto, font=f, fill=TARJETA)


def _chip_salud(dib, caja, valor, hallazgos, t, *, bien):
    """El único visual que NO es del cliente: la lectura del programa sobre
    ese mismo informe. Va con la estética de una tarjeta más para que se lea
    como parte del tablero y no como un cartel pegado encima.

    El número grande va a la IZQUIERDA y las dos etiquetas apiladas a la
    derecha. La primera versión los superponía —el 40 px de la cifra se comía
    la línea de abajo— y quedaba ilegible justo el dato que ancla la placa.
    """
    x0, y0, x1, y1 = caja
    color = OK if bien else MAL
    dib.rounded_rectangle(caja, radius=4, fill=TARJETA, outline=color, width=2)
    f_num = fuente("negrita", 38)
    f_et = fuente("normal", 13)
    f_min = fuente("normal", 11)

    dib.text((x0 + 16, y0 + 12), str(valor), font=f_num, fill=color)
    an = dib.textlength(str(valor), font=f_num)
    dib.text((x0 + 18 + an, y0 + 30), "/100", font=f_min, fill=SUAVE)

    izq = x0 + 24 + an + dib.textlength("/100", font=f_min)
    dib.text((izq, y0 + 12), t["salud"], font=f_et, fill=TEXTO)
    txt = f"{hallazgos} {t['hallazgos']}"
    dib.text((izq, y0 + 33), txt, font=f_et, fill=color)


# ==========================================================================
# El lienzo entero
# ==========================================================================
def lienzo(estado: str, t: dict) -> Image.Image:
    """Una página de informe de Power BI. `estado` es "antes" o "despues".

    El layout es IDÉNTICO en los dos: mismas posiciones, mismos visuales,
    mismo orden. Es lo que hace legible la comparación — si además se moviera
    todo, la diferencia dejaría de saltar a la vista y habría que buscarla.
    """
    roto = estado == "antes"
    d = datos()
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    dib = ImageDraw.Draw(img)

    f_tit_vis = fuente("negrita", 15)
    f_et = fuente("normal", 14)
    f_min = fuente("normal", 12)

    # ---- barra de cabecera del informe -----------------------------------
    dib.rectangle([0, 0, ANCHO, 54], fill=CABECERA)
    dib.text((24, 16), t["titulo_informe"], font=fuente("negrita", 20),
             fill=(255, 255, 255))
    est = t["est_antes"] if roto else t["est_despues"]
    f_est = fuente("negrita", 13)
    an = dib.textlength(est, font=f_est) + 26
    dib.rounded_rectangle([ANCHO - an - 24, 15, ANCHO - 24, 39], radius=12,
                          fill=MAL if roto else OK)
    dib.text((ANCHO - an - 11, 20), est, font=f_est, fill=(255, 255, 255))

    m = 22                      # margen del lienzo
    y = 54 + m

    # ---- fila de segmentaciones ------------------------------------------
    ancho_s = 232
    _slicer(dib, [m, y, m + ancho_s, y + 62], t["sl_pais"], t["sl_todos"],
            f_min, f_et,
            aviso=(t["sin_sincronizar"], MAL) if roto
            else (t["sincronizado"], OK))
    _slicer(dib, [m + ancho_s + 14, y, m + 2 * ancho_s + 14, y + 62],
            t["sl_categoria"], t["sl_todos"], f_min, f_et)
    _chip_salud(dib, [ANCHO - m - 250, y, ANCHO - m, y + 62],
                37 if roto else 98, 21 if roto else 7, t, bien=not roto)

    y += 62 + 16

    # ---- fila de KPI ------------------------------------------------------
    ancho_k = (ANCHO - 2 * m - 2 * 14) // 3
    _tarjeta_kpi(dib, [m, y, m + ancho_k, y + 104], t["kpi_ventas"],
                 _millones(d["ventas"]))
    # El margen es la medida que cae: depende de la relación ambigua.
    _tarjeta_kpi(dib, [m + ancho_k + 14, y, m + 2 * ancho_k + 14, y + 104],
                 t["kpi_margen"], f"{d['margen']:.1f} %".replace(".", ","),
                 blanco=t["blanco"] if roto else None)
    _tarjeta_kpi(dib, [m + 2 * (ancho_k + 14), y, m + 3 * ancho_k + 28,
                       y + 104], t["kpi_unidades"], _miles(d["unidades"]))

    y += 104 + 16

    # ---- gráficos ---------------------------------------------------------
    alto_g = 236
    ancho_g = (ANCHO - 2 * m - 14) // 2
    caja_b = _visual(dib, [m, y, m + ancho_g, y + alto_g], t["g_pais"],
                     f_tit_vis)
    _barras(dib, [caja_b[0] + 16, caja_b[1] + 46, caja_b[2] - 16,
                  caja_b[3] - 16], d["pais"], f_et, t, roto=roto)

    caja_l = _visual(dib, [m + ancho_g + 14, y, ANCHO - m, y + alto_g],
                     t["g_mes"], f_tit_vis)
    _lineas(dib, [caja_l[0] + 16, caja_l[1] + 52, caja_l[2] - 16,
                  caja_l[3] - 22], d["mes"], f_et)

    y += alto_g + 16

    # ---- tabla de categorías ---------------------------------------------
    caja_t = _visual(dib, [m, y, ANCHO - m, ALTO - m], t["g_categoria"],
                     f_tit_vis)
    # Ritmo vertical del visual de tabla, medido desde su borde: el título
    # ocupa hasta +30, así que los encabezados de columna arrancan en +46 y
    # no en +24 — ahí se montaban sobre «Ventas por categoría».
    tx, ty = caja_t[0] + 16, caja_t[1] + 68
    ancho_col = (caja_t[2] - tx - 16) // 4
    f_col = fuente("negrita", 12)
    # Dos medidas por categoría, y ahí se ve cómo se propaga el problema:
    # «Ventas» resuelve siempre, «Margen %» es la que depende de la relación
    # ambigua. Antes esta tabla mostraba el valor Y un «(En blanco)» al lado,
    # que se contradecía solo: o resuelve o no resuelve.
    dib.text((tx, ty), t["kpi_ventas"], font=f_col, fill=SUAVE)
    dib.text((tx, ty + 40), t["kpi_margen"], font=f_col, fill=SUAVE)
    for i, (nombre, valor) in enumerate(d["categoria"]):
        cx = tx + 110 + i * (ancho_col - 28)
        dib.text((cx, ty - 22), nombre, font=f_min, fill=TEXTO)
        dib.text((cx, ty - 2), _millones(valor), font=fuente("negrita", 16),
                 fill=TITULO)
        if roto:
            dib.text((cx, ty + 38), t["blanco"], font=f_min, fill=SUAVE)
        else:
            margen = d["margen_categoria"][nombre]
            dib.text((cx, ty + 36), f"{margen:.1f} %".replace(".", ","),
                     font=fuente("negrita", 16), fill=TITULO)
    return img


def par(t: dict) -> Image.Image:
    """Los dos lienzos, lado a lado, con la flecha en el medio. Es la imagen
    que se publica: el antes solo no dice nada, y el después solo no se
    distingue de cualquier captura de tablero."""
    a, b = lienzo("antes", t), lienzo("despues", t)
    hueco = 92
    img = Image.new("RGB", (ANCHO * 2 + hueco, ALTO), (255, 255, 255))
    img.paste(a, (0, 0))
    img.paste(b, (ANCHO + hueco, 0))
    dib = ImageDraw.Draw(img)
    cx, cy = ANCHO + hueco // 2, ALTO // 2
    dib.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(8, 21, 39))
    dib.polygon([(cx - 12, cy - 15), (cx + 14, cy), (cx - 12, cy + 15)],
                fill=(242, 180, 65))
    return img


# ==========================================================================
# Textos
# ==========================================================================
TEXTOS = {
    "es": {
        "titulo_informe": "Ventas y margen · Informe mensual",
        "est_antes": "ANTES", "est_despues": "DESPUÉS",
        "sl_pais": "País", "sl_categoria": "Categoría", "sl_todos": "Todos",
        "sin_sincronizar": "SIN SINCRONIZAR", "sincronizado": "SINCRONIZADO",
        "kpi_ventas": "Ventas", "kpi_margen": "Margen %",
        "kpi_unidades": "Unidades",
        "g_pais": "Ventas por país", "g_mes": "Ventas por mes",
        "g_categoria": "Ventas por categoría",
        "salud": "salud del modelo", "hallazgos": "hallazgos",
        "blanco": "(En blanco)",
        "err_visual": "No se puede mostrar la visualización",
        "err_relacion": "No se puede determinar una relación entre los campos",
    },
    "en": {
        "titulo_informe": "Sales and margin · Monthly report",
        "est_antes": "BEFORE", "est_despues": "AFTER",
        "sl_pais": "Country", "sl_categoria": "Category", "sl_todos": "All",
        "sin_sincronizar": "NOT SYNCED", "sincronizado": "SYNCED",
        "kpi_ventas": "Sales", "kpi_margen": "Margin %",
        "kpi_unidades": "Units",
        "g_pais": "Sales by country", "g_mes": "Sales by month",
        "g_categoria": "Sales by category",
        "salud": "model health", "hallazgos": "findings",
        "blanco": "(Blank)",
        "err_visual": "Can't display the visual",
        "err_relacion": "We can't determine the relationships between the fields",
    },
    "pt": {
        "titulo_informe": "Vendas e margem · Relatório mensal",
        "est_antes": "ANTES", "est_despues": "DEPOIS",
        "sl_pais": "País", "sl_categoria": "Categoria", "sl_todos": "Todos",
        "sin_sincronizar": "SEM SINCRONIZAR", "sincronizado": "SINCRONIZADO",
        "kpi_ventas": "Vendas", "kpi_margen": "Margem %",
        "kpi_unidades": "Unidades",
        "g_pais": "Vendas por país", "g_mes": "Vendas por mês",
        "g_categoria": "Vendas por categoria",
        "salud": "saúde do modelo", "hallazgos": "achados",
        "blanco": "(Em branco)",
        "err_visual": "Não é possível exibir a visualização",
        "err_relacion": "Não é possível determinar uma relação entre os campos",
    },
}
