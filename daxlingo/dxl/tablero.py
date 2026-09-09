# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Generador de tableros: del modelo a un reporte con visuales,
slicers (filtros) y navegación, listo para exportar como .pbit o PBIP.

El layout es el formato interno de Power BI Desktop: cada visual necesita su
`prototypeQuery` (la consulta semántica) y sus proyecciones en el rol correcto
del tipo de visual — con el rol equivocado el visual se dibuja vacío, sin
error, que es lo peor. La técnica está heredada y probada del generador de
los tableros del proyecto original de este repo
(powerbi/generar_pbit.py).
"""
from __future__ import annotations

import json
import re
import unicodedata
import uuid

from . import jerarquia
from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

ANCHO, ALTO = 1280, 720
MARGEN = 20
FILA_NAV, ALTO_NAV = 4, 32
FILA_TITULO = 44
# El slicer necesita alto para su desplegable: con 32 px sólo entraba la
# cabecera y en pantalla se veía una barra de color sin filtro adentro —
# «faltan los filtros». 56 px dejan cabecera + control.
FILA_SLICER, ALTO_SLICER = 96, 56
FILA_KPI, ALTO_KPI = 164, 104
FILA_CONTENIDO = 284

# Con marca, el encabezado lleva el logo a la izquierda y todo baja: el
# título arranca al lado del logo y la navegación se va a la derecha.
ALTO_MARCA = 78
LOGO_ANCHO, LOGO_ALTO = 52, 60


# ==========================================================================
# Marca del reporte: colores y logo
#
# Sin marca, el tablero sale como salió siempre (títulos sin fondo, series
# con el color del tema base). Con marca, el color de la empresa manda en
# lo que se ve primero: encabezado de cada visual, cabecera de las tablas,
# cabecera de los filtros y las series de los gráficos.
# ==========================================================================
MARCA_DEFECTO = {
    "primario": "#081527",       # fondo de encabezados y series
    "tinta": "#081527",          # texto de títulos y valores
    "sobre_primario": "#FFFFFF",  # texto ARRIBA del primario
    "fondo": "#FFFFFF",
    "logo": "",                  # nombre del recurso registrado, si hay
}


def paleta(marca: dict | None) -> dict | None:
    """Completa la marca con los valores por defecto. `None` → sin marca."""
    if not marca:
        return None
    p = dict(MARCA_DEFECTO)
    p.update({k: v for k, v in marca.items() if v})
    return p


def _lit(valor: str) -> dict:
    return {"expr": {"Literal": {"Value": valor}}}


def _texto_lit(valor: str) -> str:
    """Un texto como literal de PBIR: entre comillas simples y escapado.

    La comilla simple se escapa DUPLICÁNDOLA, igual que en DAX. Sin esto,
    un título con apóstrofo —«Ventas de O'Brien», o una página que el
    usuario escribió con una comilla— cerraba el literal antes de tiempo
    y Desktop abría el visual sin título o rechazaba la expresión. Los
    títulos ahora salen de nombres de tabla y de texto que escribe el
    usuario: dejarlo sin escapar es cuestión de tiempo.
    """
    return "'" + str(valor).replace("'", "''") + "'"


def _color(hex_: str) -> dict:
    """Un color sólido como lo escribe Power BI: '#RRGGBB' entre comillas."""
    return {"solid": {"color": _lit(f"'{hex_}'")}}

# (rol de la categoría, rol de las medidas) por tipo de visual.
ROLES = {
    "card": (None, "Values"),
    "multiRowCard": (None, "Values"),
    "tableEx": ("Values", "Values"),
    # `pivotTable` es el nombre que Power BI Desktop ESCRIBE: al abrir un
    # archivo generado con «matrix» y volver a guardarlo, Desktop lo
    # reescribe como pivotTable. De 13 archivos reales, 70 visuales son
    # pivotTable y 1 matrix. Se emite directamente el que el producto usa.
    "pivotTable": ("Rows", "Values"),
    "matrix": ("Rows", "Values"),
    "clusteredBarChart": ("Category", "Y"),
    "clusteredColumnChart": ("Category", "Y"),
    "lineChart": ("Category", "Y"),
    "areaChart": ("Category", "Y"),
    "donutChart": ("Category", "Y"),
    "pieChart": ("Category", "Y"),
    "slicer": ("Values", "Values"),
}


def _slug(titulo: str) -> str:
    """Nombre estable de sección: los botones de navegación referencian por
    nombre, así que tiene que ser determinístico entre regeneraciones."""
    limpio = "".join(
        c if c.isalnum() else "_"
        for c in unicodedata.normalize("NFKD", titulo)
        .encode("ascii", "ignore").decode())
    return "s" + re.sub(r"_+", "_", limpio).strip("_").lower()


def _medida_ref(tabla: str, nombre: str, alias: str = "m") -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Source": alias}},
                        "Property": nombre},
            "Name": f"{tabla}.{nombre}"}


def _columna_ref(tabla: str, col: str, alias: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": alias}},
                       "Property": col},
            "Name": f"{tabla}.{col}"}


VERDE, ROJO = "#12B886", "#E03131"


NEUTRO = "#F2F4F7"


def _regla_color(tabla: str, medida: str) -> dict:
    """Rojo cuando cae, verde cuando crece, con el cero en el medio.

    **Tercer intento, y el primero verificado contra un archivo real.**
    Los dos anteriores no pintaban nada:

    1. «Field value» — el color lo devolvía una medida `Color Var …` del
       modelo. La medida existía y la referencia quedaba escrita, pero en
       pantalla los valores salían negros.
    2. Una expresión `Conditional` con `Cases`/`ComparisonKind`. Parecía
       autocontenida y correcta. Al abrir el .pbit en Desktop y volver a
       guardarlo, Desktop la había **descartado**: dejó
       `"properties": {}` con el selector intacto. Ahí quedó la prueba de
       que esa forma no es la que el producto acepta.

    Ésta es la que Desktop ESCRIBE: `FillRule` con un `linearGradient3`
    sobre la propia medida. `min` y `max` van sin `value` —el valor más
    bajo y el más alto de lo que el visual muestre— y el `mid` anclado en
    0, que es lo que pone el rojo abajo del cero y el verde arriba sin
    depender de la escala: sirve igual para puntos porcentuales que para
    una variación en tanto por uno.
    """
    return {"solid": {"color": {"expr": {"FillRule": {
        "Input": {"Measure": {"Expression": {"SourceRef": {"Entity": tabla}},
                              "Property": medida}},
        "FillRule": {"linearGradient3": {
            "min": {"color": {"Literal": {"Value": f"'{ROJO}'"}}},
            "mid": {"color": {"Literal": {"Value": f"'{NEUTRO}'"}},
                    "value": {"Literal": {"Value": "0D"}}},
            "max": {"color": {"Literal": {"Value": f"'{VERDE}'"}}},
            "nullColoringStrategy": {
                "strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}


# Sin esto la regla se aplica a UN punto y no a la columna: es la otra
# mitad de por qué el semáforo no se veía. Todo formato condicional de
# los archivos reales lo lleva.
_TODAS_LAS_FILAS = [{"dataViewWildcard": {"matchingOption": 1}}]


def _es_variacion(nombre: str) -> bool:
    """Una medida que expresa un CAMBIO: crece o cae, y eso tiene color.

    Se decide por el nombre porque es lo único que hay al armar el visual
    —el valor no se conoce hasta que Power BI ejecuta la consulta—, con
    las MISMAS reglas con que se clasifican los roles (`dxl/roles.py`).
    Antes la prueba pedía que el nombre empezara con «Var» o terminara en
    «pp», y las medidas que genera este programa se llaman «Total Ventas
    var mes %»: ni una cosa ni la otra, así que la matriz de períodos
    salía en blanco y negro y la tarjeta de variación, sin color. El
    semáforo es lo primero que se mira en un informe gerencial.
    """
    from .roles import _RE_PP, _RE_VAR
    return bool(_RE_VAR.search(nombre or "") or _RE_PP.search(nombre or ""))


def _semaforo(medidas: list[tuple[str, str]],
              colores: dict[str, tuple[str, str]] | None = None) -> list[dict]:
    """Formato condicional para TODA medida de variación del visual.

    `colores` ya no hace falta —queda por compatibilidad de firma— porque
    la regla es autosuficiente: antes había que crear una medida
    `Color Var …` en el modelo y pasarla acá, y si ese cableado se
    cortaba en cualquier punto, el semáforo desaparecía sin avisar. Lo
    que decide ahora es el nombre de la medida, que está siempre.

    El `selector.metadata` dice A QUÉ columna del visual se le aplica:
    sin él, Power BI no sabe cuál de las cinco medidas pintar.
    """
    reglas = []
    for tabla, nombre in medidas:
        if not _es_variacion(nombre):
            continue
        reglas.append({
            "properties": {"backColor": _regla_color(tabla, nombre)},
            # `data` + `metadata`: la columna entera, no un punto suelto.
            "selector": {"data": _TODAS_LAS_FILAS,
                         "metadata": f"{tabla}.{nombre}"},
        })
    return reglas


# Las dos mitades de una comparación: lo PROPIO y el resto del mercado.
# Cuando un gráfico muestra las dos, cada serie va de un color distinto —
# dos líneas del mismo color obligan a leer la leyenda para saber cuál es
# cuál, que es justo lo que un gráfico tiene que ahorrar.
#
# Por PALABRA ENTERA y sin «total»: la lista arrancó como subcadenas y
# «Ventas Totales» —una medida propia como cualquier otra— quedaba del
# lado del mercado, con lo que un gráfico de una sola serie se pintaba
# gris de competencia. Los plurales van escritos porque emparejar por
# prefijo mete «marketing» adentro de «market».
_MERCADO = ("mercado", "mercados", "market", "markets",
            "industria", "industrias", "competencia", "competencias",
            "competidor", "competidores", "competitor", "competitors",
            "competition")


def _fichas(nombre: str) -> set[str]:
    """Las palabras del nombre, sin acentos ni mayúsculas."""
    return set(_norm(nombre).replace("_", " ").split())


def _es_del_mercado(nombre: str) -> bool:
    return bool(_fichas(nombre) & set(_MERCADO))


def _contraparte_mercado(nombre: str,
                         todas: list[tuple[str, str]]
                         ) -> tuple[str, str] | None:
    """La otra mitad de la comparación, si el modelo la tiene.

    Si `nombre` es una medida propia, devuelve la del mercado que mide lo
    mismo; si es del mercado, la propia. El emparejamiento es por las
    palabras que quedan al sacar las del mercado: «Ventas Mercado USD»
    deja `{ventas, usd}`, que está contenido en «Ventas Adium USD». Ante
    varias candidatas gana la que menos palabras sobrantes tiene, para no
    aparear una medida simple con la versión YTD de la otra.
    """
    base = _fichas(nombre) - set(_MERCADO)
    if not base:
        return None
    del_mercado = _es_del_mercado(nombre)
    mejor: tuple[str, str] | None = None
    coste: int | None = None
    for tabla, otro in todas:
        if otro == nombre or _es_del_mercado(otro) == del_mercado:
            continue
        fichas = _fichas(otro) - set(_MERCADO)
        if not (base <= fichas or fichas <= base):
            continue
        distancia = len(base ^ fichas)
        if coste is None or distancia < coste:
            mejor, coste = (tabla, otro), distancia
    return mejor


_RE_SHARE_TB = re.compile(r"\bshare\b|participaci[oó]n|\bcuota\b", re.I)


def _con_contraparte(pares: list[tuple[str, str]],
                     todas: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Suma al gráfico la serie que falta para que la comparación exista.

    Un gráfico con «Ventas Adium USD» sola no compara nada: el pedido era
    ver la evolución de lo propio CONTRA el mercado, siempre y sin que
    haya que pedirlo tema por tema. Si el modelo no tiene la contraparte,
    no se inventa: el gráfico queda como estaba.
    """
    salida = list(pares)
    for _t, nombre in pares:
        # Sólo los NIVELES tienen contraparte. Un share ya ES la relación
        # entre lo propio y el mercado: ponerle al lado el nivel del
        # mercado mezcla un porcentaje con una cifra en pesos en el mismo
        # eje, y el gráfico deja de leerse. Lo mismo una variación.
        if _es_variacion(nombre) or _RE_SHARE_TB.search(nombre):
            continue
        otro = _contraparte_mercado(nombre, todas)
        if otro and otro not in salida:
            salida.append(otro)
    return salida


def _series_comparadas(medidas: list[tuple[str, str]],
                       m: dict) -> list[dict]:
    """Un color por serie cuando el gráfico compara propio contra mercado.

    Sólo se pinta si hay de las DOS: una sola serie no es una comparación
    y darle un color «de competencia» sería mentir sobre lo que muestra.
    """
    propias = [n for _t, n in medidas if not _es_del_mercado(n)]
    ajenas = [n for _t, n in medidas if _es_del_mercado(n)]
    if not (propias and ajenas):
        return []
    reglas = []
    for tabla, nombre in medidas:
        color = "#9AA3AF" if _es_del_mercado(nombre) else m["primario"]
        reglas.append({
            "properties": {"fill": _color(color)},
            "selector": {"metadata": f"{tabla}.{nombre}"},
        })
    return reglas


TINTA_NEUTRA = "#1F2A3C"


def _tinta_legible(m: dict) -> str:
    """La tinta de la marca, salvo que se confunda con el semáforo.

    Una marca roja o verde pinta los valores del mismo color que usa el
    formato condicional para decir «cayó» o «creció», y entonces el
    semáforo deja de significar algo: todo está siempre en rojo. En ese
    caso el cuerpo va en un gris azulado neutro y la marca se queda con
    los encabezados, que es donde se la reconoce igual.
    """
    import colorsys

    tinta = m.get("tinta") or TINTA_NEUTRA
    if len(tinta) != 7:
        return TINTA_NEUTRA
    r, g, b = (int(tinta[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    grados = h * 360
    # Por TONO, no por «un canal más alto que los otros»: ese criterio
    # dejaba pasar un verde de marca y rechazaba un violeta, que se lee
    # perfecto. Rojo y verde son bandas concretas del círculo, y sólo
    # molestan si el color está saturado — un gris azulado apagado no se
    # confunde con nada.
    rojo = grados < 20 or grados > 340
    verde = 90 <= grados <= 165
    return TINTA_NEUTRA if s > 0.35 and (rojo or verde) else tinta


def _objetos_de_marca(tipo: str, m: dict) -> dict:
    """Los `objects` que pintan un visual con la marca, por tipo.

    Cada tipo de visual nombra distinto lo mismo: una tabla tiene
    `columnHeaders`, una tarjeta tiene `labels`, un gráfico tiene
    `dataPoint`. Poner la propiedad en el objeto equivocado no da error —
    simplemente no pinta nada, que es peor.
    """
    objetos: dict = {}
    if tipo in ("clusteredBarChart", "clusteredColumnChart", "lineChart",
                "areaChart"):
        objetos["dataPoint"] = [{"properties": {
            "defaultColor": _color(m["primario"])}}]
        # Los valores ESCRITOS sobre el gráfico. Un gráfico sin números
        # obliga a estimar la altura de una barra a ojo, que es
        # exactamente lo que un tablero tiene que evitar.
        objetos["labels"] = [{"properties": {
            "show": _lit("true"),
            "color": _color(_tinta_legible(m)),
            "fontSize": _lit("9D"),
            "labelDisplayUnits": _lit("0D"),
            "labelPrecision": _lit("0D")}}]
    elif tipo in ("tableEx", "matrix", "pivotTable"):
        objetos["columnHeaders"] = [{"properties": {
            "fontColor": _color(m["sobre_primario"]),
            "backColor": _color(m["primario"]),
            "bold": _lit("true")}}]
        # El CUERPO de la tabla en tinta de lectura, no en el color de la
        # marca. Con una marca roja, los cuatro canales y la fila de total
        # salían en rojo y todo el informe se leía como si estuviera mal:
        # el rojo tiene que significar «cayó», y para eso no puede estar
        # puesto de decoración. La marca manda en la cabecera, que es
        # donde se la reconoce.
        objetos["values"] = [{"properties": {
            "fontColor": _color(_tinta_legible(m)),
            "backColor": _color(m["fondo"])}}]
        objetos["total"] = [{"properties": {
            "fontColor": _color(_tinta_legible(m)), "bold": _lit("true")}}]
    elif tipo in ("card", "multiRowCard"):
        # El número, grande y en la tinta de la marca; la etiqueta, chica
        # y en gris. La jerarquía entre los dos es lo que hace que un KPI
        # se lea de un vistazo.
        objetos["labels"] = [{"properties": {
            "color": _color(_tinta_legible(m)), "fontSize": _lit("30D"),
            "bold": _lit("true"), "labelDisplayUnits": _lit("0D")}}]
        objetos["categoryLabels"] = [{"properties": {
            "color": _color("#6B7A8D"), "fontSize": _lit("9D")}}]
    return objetos


def _tarjeta_con_cuerpo(m: dict) -> dict:
    """Fondo, borde y sombra de una tarjeta KPI.

    Van en `vcObjects` (el CONTENEDOR), no en `objects` (el contenido).
    Puesto en el objeto equivocado no da error: simplemente no pinta, que
    es la trampa de siempre en este formato.
    """
    return {
        "background": [{"properties": {
            "show": _lit("true"), "color": _color(m["fondo"]),
            "transparency": _lit("0D")}}],
        "border": [{"properties": {
            "show": _lit("true"), "color": _color("#E3E8F0"),
            "radius": _lit("6D")}}],
        "dropShadow": [{"properties": {
            "show": _lit("true"), "color": _color("#B8C2CF"),
            "position": _lit("'Outer'"), "preset": _lit("'BottomRight'")}}],
    }


def visual(tipo: str, x: int, y: int, w: int, h: int, *,
           medidas: list[tuple[str, str]] | None = None,
           categoria: tuple[str, str] | None = None,
           titulo: str | None = None, z: int = 0,
           marca: dict | None = None,
           colores: dict[str, tuple[str, str]] | None = None,
           formato: dict | None = None) -> dict:
    """
    Un visualContainer. `medidas` son pares (tabla, nombre_medida) — la tabla
    es la que aloja la medida en el modelo, no una tabla fija.
    """
    medidas = medidas or []
    rol_cat, rol_med = ROLES.get(tipo, ("Category", "Y"))
    from_, select, proyecciones = [], [], {}

    # `categoria` puede ser UNA columna o varias: en una matriz, varias
    # forman la jerarquía de filas y Power BI la deja desplegar (área →
    # ATC4 → molécula → producto). Es la forma de comparar cuatro niveles
    # sin cuatro tablas al lado.
    cats = ([categoria] if categoria and isinstance(categoria[0], str)
            else list(categoria or []))
    if cats and rol_cat:
        for i, (tabla, col) in enumerate(cats):
            alias = f"c{i}"
            from_.append({"Name": alias, "Entity": tabla, "Type": 0})
            select.append(_columna_ref(tabla, col, alias))
            proyecciones.setdefault(rol_cat, []).append(
                {"queryRef": f"{tabla}.{col}"})

    alias_por_tabla: dict[str, str] = {}
    for i, (tabla, nombre) in enumerate(medidas):
        alias = alias_por_tabla.get(tabla)
        if alias is None:
            alias = f"m{len(alias_por_tabla)}"
            alias_por_tabla[tabla] = alias
            from_.append({"Name": alias, "Entity": tabla, "Type": 0})
        select.append(_medida_ref(tabla, nombre, alias))
        proyecciones.setdefault(rol_med, []).append(
            {"queryRef": f"{tabla}.{nombre}"})

    objetos = _objetos_de_marca(tipo, marca) if marca else {}
    if marca and tipo in ("lineChart", "areaChart", "clusteredBarChart",
                          "clusteredColumnChart"):
        series = _series_comparadas(medidas, marca)
        if series:
            objetos["dataPoint"] = objetos.get("dataPoint", []) + series
    if medidas:
        # El semáforo pisa el color de texto de la marca SOLO en las
        # medidas que lo piden; el resto de los valores queda con la tinta.
        reglas = _semaforo(medidas, colores)
        if reglas:
            if tipo in ("tableEx", "matrix", "pivotTable"):
                objetos["values"] = objetos.get("values", []) + reglas
            elif tipo == "card":
                # En una tarjeta el número ES el visual: no hay columna a
                # la que apuntar, así que la regla va sin selector y sobre
                # el COLOR DE LETRA — pintarle el fondo entero de verde a
                # una tarjeta la vuelve ilegible.
                objetos["labels"] = [
                    {"properties": {"color": r["properties"]["backColor"]}}
                    for r in reglas
                ] + [o for o in objetos.get("labels", []) if "selector" not in o]
    # Lo que pide quien arma el visual manda sobre lo que puso la marca:
    # una tarjeta de texto necesita otra tipografía que una de KPI.
    for clave, valor in (formato or {}).items():
        objetos[clave] = valor
    if titulo:
        props = {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": _texto_lit(titulo)}}},
            "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
        }
        if marca:
            # El encabezado de CADA visual con el color de la empresa: es
            # lo que hace que el informe entero se lea como de la marca.
            props["fontColor"] = _color(marca["sobre_primario"])
            props["background"] = _color(marca["primario"])
            props["alignment"] = _lit("'left'")
        objetos["title"] = [{"properties": props}]

    conf = {
        "name": uuid.uuid4().hex[:20],
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z,
                                           "width": w, "height": h}}],
        "singleVisual": {
            "visualType": tipo,
            "projections": proyecciones,
            "prototypeQuery": {"Version": 2, "From": from_, "Select": select},
            "drillFilterOtherVisuals": True,
            "objects": objetos,
        },
    }
    if tipo == "card" and marca:
        conf["singleVisual"]["vcObjects"] = _tarjeta_con_cuerpo(marca)
    return {"x": x, "y": y, "z": z, "width": w, "height": h,
            "config": json.dumps(conf, ensure_ascii=False)}


def texto(x: int, y: int, w: int, h: int, contenido: str,
          tamano: int = 12, z: int = 0, color: str = "",
          negrita: bool = False) -> dict:
    estilo = {"fontSize": f"{tamano}px"}
    if color:
        estilo["color"] = color
    if negrita:
        estilo["fontWeight"] = "bold"
    conf = {
        "name": uuid.uuid4().hex[:20],
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z,
                                           "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "textbox",
            "drillFilterOtherVisuals": True,
            "objects": {"general": [{"properties": {"paragraphs": [{
                "textRuns": [{"value": contenido, "textStyle": estilo}]
            }]}}]},
        },
    }
    return {"x": x, "y": y, "z": z, "width": w, "height": h,
            "config": json.dumps(conf, ensure_ascii=False)}


def imagen(x: int, y: int, w: int, h: int, recurso: str, z: int = 0) -> dict:
    """El logo, apuntando a un archivo embebido en el propio .pbit.

    `recurso` es el nombre del ítem en el paquete `RegisteredResources` —
    el mismo mecanismo con el que Power BI Desktop guarda una imagen
    pegada en el reporte. El archivo viaja adentro del .pbit
    (`Report/StaticResources/RegisteredResources/<recurso>`), así que no
    depende de ninguna ruta ni de internet.
    """
    conf = {
        "name": uuid.uuid5(uuid.NAMESPACE_DNS, f"img{recurso}{x}{y}").hex[:20],
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z,
                                           "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "image",
            "objects": {"general": [{"properties": {
                "imageUrl": {"expr": {"ResourcePackageItem": {
                    "PackageName": "RegisteredResources",
                    "PackageType": 1, "ItemName": recurso}}},
                "imageScalingType": _lit("'Fit'"),
            }}]},
            "drillFilterOtherVisuals": True,
        },
    }
    return {"x": x, "y": y, "z": z, "width": w, "height": h,
            "config": json.dumps(conf, ensure_ascii=False)}


def slicer(x: int, y: int, w: int, h: int, tabla: str, columna: str,
           titulo: str, marca: dict | None = None) -> dict:
    """Segmentación: filtra todos los visuales de la página."""
    cabecera = {
        "show": {"expr": {"Literal": {"Value": "true"}}},
        "text": {"expr": {"Literal": {"Value": _texto_lit(titulo)}}},
        "fontSize": _lit("10D"),
    }
    if marca:
        # La cabecera va con el color de la marca en la LETRA, no como
        # fondo sólido: pintada de fondo, la barra se comía el filtro y
        # sólo se veía un rectángulo de color.
        cabecera["fontColor"] = _color(marca["primario"])
        cabecera["background"] = _color(marca["fondo"])
        cabecera["bold"] = _lit("true")
        cabecera["outline"] = _lit("'BottomOnly'")
    conf = {
        "name": uuid.uuid5(uuid.NAMESPACE_DNS,
                           f"sl{tabla}{columna}{x}{y}").hex[:20],
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 50,
                                           "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "slicer",
            # El mismo filtro repetido en varias páginas se SINCRONIZA:
            # elegir «Cardiología» en una página y volver a elegirla en la
            # siguiente es el trabajo manual que hace que dos páginas
            # muestren cosas distintas sin que nadie se dé cuenta. Va
            # DENTRO de singleVisual, que es donde lo escribe Power BI —y
            # donde lo lee el analizador de reportes de este programa.
            "syncGroup": {
                "groupName": f"sync_{_slug(tabla)}_{_slug(columna)}",
                "fieldChanges": True, "filterChanges": True},
            "projections": {"Values": [{"queryRef": f"{tabla}.{columna}"}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": tabla, "Type": 0}],
                "Select": [_columna_ref(tabla, columna, "c")],
            },
            "objects": {
                "header": [{"properties": cabecera}],
                # Desplegable: ocupa poco y se puede usar. En modo lista,
                # un slicer bajo muestra la cabecera y nada más.
                "data": [{"properties": {"mode": _lit("'Dropdown'")}}],
                "items": [{"properties": {
                    "fontSize": _lit("10D"),
                    "fontColor": _color((marca or MARCA_DEFECTO)["tinta"])}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return {"x": x, "y": y, "z": 50, "width": w, "height": h,
            "config": json.dumps(conf, ensure_ascii=False)}


def boton_navegacion(x, y, w, h, etiqueta: str, destino: str,
                     activo: bool = False, marca: dict | None = None) -> dict:
    """Botón con acción PageNavigation real hacia otra página del reporte."""
    def lit(v):
        return {"expr": {"Literal": {"Value": v}}}

    if marca:
        fondo = f"'{marca['primario']}'" if activo else f"'{marca['fondo']}'"
        letra = (f"'{marca['sobre_primario']}'" if activo
                 else f"'{marca['tinta']}'")
        borde = f"'{marca['primario']}'"
    else:
        fondo = "'#081527'" if activo else "'#FFFFFF'"
        letra = "'#F2B441'" if activo else "'#081527'"
        borde = "'#081527'"
    conf = {
        "name": uuid.uuid5(uuid.NAMESPACE_DNS,
                           f"btn{destino}{etiqueta}{x}").hex[:20],
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 100,
                                           "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "actionButton",
            "objects": {
                "icon": [{"properties": {"shapeType": lit("'blank'")},
                          "selector": {"id": "default"}}],
                "text": [{"properties": {
                    "show": lit("true"), "text": lit(_texto_lit(etiqueta)),
                    "fontSize": lit("10D"),
                    "fontColor": {"solid": {"color": lit(letra)}},
                    "bold": lit("true" if activo else "false"),
                }, "selector": {"id": "default"}}],
                "fill": [{"properties": {
                    "show": lit("true"),
                    "fillColor": {"solid": {"color": lit(fondo)}},
                    "transparency": lit("0D"),
                }, "selector": {"id": "default"}}],
                "outline": [{"properties": {
                    "show": lit("true"),
                    "lineColor": {"solid": {"color": lit(borde)}},
                    "weight": lit("1D"),
                }, "selector": {"id": "default"}}],
            },
            "vcObjects": {"visualLink": [{"properties": {
                "show": lit("true"),
                "type": lit("'PageNavigation'"),
                "navigationSection": lit(_texto_lit(destino)),
            }}]},
            "drillFilterOtherVisuals": True,
        },
    }
    return {"x": x, "y": y, "z": 100, "width": w, "height": h,
            "config": json.dumps(conf, ensure_ascii=False)}


def pagina(nombre: str, visuales: list[dict], ordinal: int,
           marca: dict | None = None) -> dict:
    config: dict = {}
    if marca:
        # Lienzo blanco y el borde del lienzo en un gris muy claro: el
        # color de la marca tiene que destacar, no competir con el fondo.
        config["objects"] = {
            "background": [{"properties": {
                "color": _color(marca["fondo"]),
                "transparency": _lit("0D")}}],
            "outspace": [{"properties": {
                "color": _color("#F4F6F8"),
                "transparency": _lit("0D")}}],
        }
    return {
        "name": _slug(nombre),
        "displayName": nombre,
        "displayOption": 1,
        "width": ANCHO,
        "height": ALTO,
        "ordinal": ordinal,
        "visualContainers": visuales,
        "config": json.dumps(config, ensure_ascii=False),
        "filters": "[]",
    }


def envolver_layout(secciones: list[dict],
                    recursos: list[str] | None = None) -> dict:
    # NO se declara ningún `SharedResources`/`BaseThemes`. Acá se declaraba
    # un tema base `CY24SU10.json` que NUNCA se escribía dentro del .pbit:
    # una referencia colgada a una parte inexistente, que es de las cosas
    # que hacen que Desktop rechace el archivo como dañado. Un .pbit real
    # que declara su tema base TRAE el archivo del tema adentro.
    #
    # La regla es la de tres líneas más abajo, que ya estaba escrita para
    # los recursos registrados y no se aplicaba acá: declarado y presente,
    # o ninguna de las dos. Sin tema declarado Desktop aplica el suyo por
    # defecto, y el aspecto del tablero no cambia porque los colores de
    # marca van puestos visual por visual, no en el tema.
    paquetes: list[dict] = []
    if recursos:
        # Los archivos embebidos (el logo) tienen que estar DECLARADOS acá,
        # además de existir dentro del .pbit: si falta cualquiera de las
        # dos mitades, el visual de imagen queda vacío sin decir por qué.
        paquetes.append({"resourcePackage": {
            "name": "RegisteredResources", "type": 1,
            "items": [{"type": 100, "path": r, "name": r}
                      for r in recursos],
        }})
    return {
        "id": 0,
        "resourcePackages": paquetes,
        "sections": secciones,
        # Sin `themeCollection`: apuntaba al mismo tema que no viaja en el
        # paquete. Se va con su `resourcePackage`, no por separado.
        "config": json.dumps({
            "version": "5.43",
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
            "settings": {"useNewFilterPaneExperience": True,
                         "allowChangeFilterTypes": True},
        }, ensure_ascii=False),
        # Filtros a nivel reporte: ninguno, pero la clave va igual. Todo
        # layout escrito por Desktop la trae, y las secciones de acá ya
        # llevaban la suya — faltaba solo la de la raíz.
        "filters": "[]",
        "layoutOptimization": 0,
    }


# ==========================================================================
# Diseño automático
# ==========================================================================
TITULOS_AUTO = ["01 · Resumen", "02 · Detalle"]


def _lecturas_validas(cat: Catalogo,
                      lecturas: list[dict] | None) -> list[dict]:
    """Las lecturas cuya medida EXISTE en el modelo, con su tabla.

    Una página de análisis que apunta a una medida que no está se dibuja
    igual y sale vacía en pantalla, sin decir por qué: mejor no dibujarla.
    """
    from .lectura import COL_PAGINA, MEDIDA_UNICA, TABLA_LECTURA

    salida = []
    for le in lecturas or []:
        m = cat.medida(le.get("nombre", ""))
        if m:
            salida.append({**le, "tabla": m["tabla"]})
    if not salida:
        return salida
    # El eje de páginas y la medida que las recorre: si están, la página
    # de análisis se dibuja como tabla —una fila por pestaña— en vez de
    # tarjetas que cortan la frase.
    unica = cat.medida(MEDIDA_UNICA)
    if unica and cat.existe_columna(TABLA_LECTURA, COL_PAGINA):
        salida[0] = {**salida[0],
                     "eje": (TABLA_LECTURA, COL_PAGINA),
                     "unica": (unica["tabla"], MEDIDA_UNICA)}
    return salida


def disenar_auto(cat: Catalogo, medidas_sel: list[str] | None = None,
                 titulo: str = "Tablero",
                 marca: dict | None = None,
                 lecturas: list[dict] | None = None,
                 temas_extra: list[dict] | None = None,
                 idioma: str = IDIOMA_DEFECTO) -> dict:
    """
    Arma el tablero a partir del catálogo, con las páginas que el dataset
    dé: una por cada cosa que el negocio mide, más segmentos y análisis.
    Si el modelo mide una sola cosa, sale el tablero de dos páginas —
    resumen (KPIs, evolución, ranking) y detalle (matriz + tabla).

    `medidas_sel`: nombres de medidas para las tarjetas (si no, las que
    `kpis.principales` elija). `temas_extra`: páginas que el usuario
    escribió a mano y quiere ADEMÁS de las automáticas — se agregan al
    final, con la misma forma de tema que `disenar_temas`.

    Devuelve el layout listo para `modelo.exportar_pbit` / `exportar_pbip`.
    """
    todas = cat.medidas()
    if not todas:
        raise ValueError("El modelo no tiene medidas: generá alguna primero "
                         "(pestaña Generar DAX) o cargá otro modelo.")
    # Cuando el modelo mide varias cosas distintas —ventas, visitas,
    # interacciones, mercado— apretarlas en «Resumen» y «Detalle» las
    # amontona: cada hecho merece su página. Si el dataset no da para
    # eso, se cae al tablero de dos páginas de siempre.
    temas = temas_automaticos(cat, medidas_sel, idioma)
    if temas:
        return disenar_temas(cat, temas + list(temas_extra or []),
                             titulo, marca, lecturas=lecturas)
    por_nombre = {m["nombre"]: m for m in todas}
    elegidas = [por_nombre[n] for n in (medidas_sel or []) if n in por_nombre] \
        or todas[:5]
    elegidas = elegidas[:5]
    pares = [(m["tabla"], m["nombre"]) for m in elegidas]

    dims = _dimensiones(cat, maximo=3)
    fecha = cat.columna_fecha()
    cortes = _cortes_pagina(cat)
    universo = [(md["tabla"], md["nombre"]) for md in todas]

    m = paleta(marca)
    titulos = list(TITULOS_AUTO)
    secciones = [
        _pagina_resumen(titulos, titulo, pares, dims, fecha, m, cortes,
                        universo, metas_de(cat, pares)),
        _pagina_detalle(titulos, titulo, pares, dims, m, cortes, cat),
    ]
    pares_seg, _fuera = cortes_utiles(
        cat, _pendientes(cat, secciones), pares)
    if pares_seg:
        secciones += _paginas_segmentos(
            titulo, pares_seg, cortes, m, len(secciones), cat)
    validas = _lecturas_validas(cat, lecturas)
    if validas:
        globales = _pares(_kpis_globales(cat, medidas_sel), por_nombre)
        secciones.append(_pagina_analisis(
            titulos, titulo, validas, cortes_de_analisis(cat, validas, cortes),
            m, len(secciones), globales, None,
            metas_de(cat, globales), fecha))
    dicc = _pagina_diccionario(titulo, cat, m, len(secciones))
    if dicc:
        secciones.append(dicc)
    recursos = [m["logo"]] if m and m.get("logo") else None
    return envolver_layout(secciones, recursos)


def disenar_temas(cat: Catalogo, temas: list[dict], titulo: str = "Tablero",
                  marca: dict | None = None,
                  colores: dict[str, tuple[str, str]] | None = None,
                  lecturas: list[dict] | None = None) -> dict:
    """
    Un tablero de N páginas, una por TEMA. Es la versión prolija de
    `disenar_auto`: en vez de dos páginas fijas («Resumen» y «Detalle»)
    con todo amontonado, cada tema tiene su página con sus propios KPIs,
    su gráfico y su tabla.

    Cada tema es un dict:

        {"titulo": "Mercado y share",
         "kpis":   ["Share Adium USD %", ...],     # tarjetas (hasta 5)
         "linea":  "Ventas Mercado USD",           # evolución temporal
         "barras": ("Ventas Mercado USD", ("Producto", "Corporacion")),
         "tabla":  {"medidas": [...], "por": ("Producto", "Corporacion")},
         "filtros": [("Medico", "Especialidad"), ...]}

    Todo es opcional salvo el título: un tema sin gráfico ni tabla es una
    página de puros KPIs, y no pasa nada.
    """
    if not temas:
        raise ValueError("No hay temas para armar el tablero.")
    m = paleta(marca)
    por_nombre = {md["nombre"]: md for md in cat.medidas()}
    fecha = cat.columna_fecha()
    titulos = [t["titulo"] for t in temas]
    secciones = []
    for i, tema in enumerate(temas):
        secciones.append(_pagina_tema(tema, titulos, titulo, por_nombre,
                                      fecha, m, colores, i, cat))
    cortes = _cortes_pagina(cat)
    # Las candidatas, en el orden en que los temas las declararon: el
    # corte se abre con la medida más importante que ESA dimensión filtre.
    candidatas = _candidatas_segmento(temas, por_nombre)
    pares_seg, _fuera = cortes_utiles(
        cat, _pendientes(cat, secciones), candidatas)
    if pares_seg:
        secciones += _paginas_segmentos(
            titulo, pares_seg, cortes, m, len(secciones), cat, colores)
    validas = _lecturas_validas(cat, lecturas)
    if validas:
        globales = _pares(_kpis_globales(cat), por_nombre)
        secciones.append(_pagina_analisis(
            titulos, titulo, validas, cortes_de_analisis(cat, validas, cortes),
            m, len(secciones), globales, colores,
            metas_de(cat, globales), fecha))
    dicc = _pagina_diccionario(titulo, cat, m, len(secciones))
    if dicc:
        secciones.append(dicc)
    recursos = [m["logo"]] if m and m.get("logo") else None
    return envolver_layout(secciones, recursos)


def _pares(nombres, por_nombre) -> list[tuple[str, str]]:
    """(tabla, medida) de las medidas que EXISTEN, en el orden pedido."""
    return [(por_nombre[n]["tabla"], n) for n in nombres or []
            if n in por_nombre]


def _pagina_tema(tema, titulos, titulo, por_nombre, fecha, m, colores,
                 ordinal, cat=None) -> dict:
    nombre = tema["titulo"]
    universo = [(md["tabla"], md["nombre"]) for md in por_nombre.values()]
    visuales = (_barra_nav(titulos, nombre, m)
                + _encabezado(f"{titulo} · {nombre}",
                              tema.get("subtitulo", ""), m))
    desplazo = ALTO_MARCA - FILA_SLICER + 8 if m else 0
    y = FILA_SLICER + desplazo
    filtros = list(tema.get("filtros") or [])
    # Los del tema mandan, pero la página nunca sale sin año, período y
    # categoría: un informe que no se puede filtrar por tiempo obliga a
    # abrir Power BI y agregarlo a mano.
    cortes = _cortes_pagina(cat, filtros) if cat is not None else filtros
    if cortes:
        visuales += _fila_slicers(cortes, None, m, y)
        y += ALTO_SLICER + 12

    kpis_ = _pares(tema.get("kpis"), por_nombre)[:5]
    if kpis_:
        metas = metas_de(cat, kpis_) if cat is not None else {}
        visuales += _kpis(kpis_, m, y, colores, metas, fecha)
        y += ALTO_KPI + 12

    alto_libre = ALTO - y - MARGEN
    linea = tema.get("linea")
    barras = tema.get("barras")
    tabla = tema.get("tabla")
    abajo = [x for x in (linea, barras, tabla) if x]
    if not abajo:
        return pagina(nombre, visuales, ordinal, m)

    # Una fila para la evolución (ancho completo) y otra que se reparte
    # entre barras y tabla: es el orden en que se lee un informe.
    if linea and fecha and linea in por_nombre and len(abajo) > 1:
        alto_linea = alto_libre // 2 - 6
        visuales.append(visual(
            "lineChart", MARGEN, y, ANCHO - 2 * MARGEN, alto_linea,
            medidas=_con_contraparte(_pares([linea], por_nombre),
                                     universo),
            categoria=fecha,
            titulo=f"{linea} en el tiempo", marca=m, colores=colores))
        y += alto_linea + 12
        alto_libre = ALTO - y - MARGEN
        abajo = [x for x in (barras, tabla) if x]
    elif linea and fecha and linea in por_nombre:
        visuales.append(visual(
            "lineChart", MARGEN, y, ANCHO - 2 * MARGEN, alto_libre,
            medidas=_con_contraparte(_pares([linea], por_nombre),
                                     universo),
            categoria=fecha,
            titulo=f"{linea} en el tiempo", marca=m, colores=colores))
        return pagina(nombre, visuales, ordinal, m)

    ancho = ((ANCHO - 2 * MARGEN - 12 * (len(abajo) - 1)) // len(abajo)
             if abajo else 0)
    x = MARGEN
    for pieza in abajo:
        if pieza is barras:
            medida, dim = pieza
            # El eje puede ser una jerarquía: el gráfico abre por el nivel
            # más general y se baja al detalle sin ocupar más lugar.
            niveles = jerarquia.niveles(dim)
            # Una medida constante contra ESTE eje dibuja la misma barra
            # repetida. Se intenta la equivalente propia; si no la hay,
            # la pieza no se dibuja — mejor un hueco que un hallazgo falso.
            if cat is not None and medida in por_nombre:
                cambio = _sin_eje_reemplazadas(
                    cat, [(por_nombre[medida]["tabla"], medida)], niveles)
                medida = cambio[0][1] if cambio else medida
                if sin_eje(cat, [(por_nombre[medida]["tabla"], medida)],
                           niveles):
                    x += ancho + 12
                    continue
            if medida in por_nombre:
                visuales.append(visual(
                    "clusteredBarChart", x, y, ancho, alto_libre,
                    medidas=_con_contraparte(
                        _pares([medida], por_nombre), universo),
                    categoria=niveles,
                    titulo=f"{medida} por {niveles[0][1]}", marca=m,
                    colores=colores))
        elif pieza is tabla:
            medidas_t = _pares(pieza.get("medidas"), por_nombre)
            if cat is not None:
                # Una medida que quedaría constante por construcción se
                # cambia por su equivalente propia: un «0,0 pp» repetido
                # en todas las filas parece un dato y no lo es. La que no
                # tiene equivalente se SACA de este visual — sigue en el
                # modelo y en las tarjetas, donde un total global es un
                # dato legítimo, pero no al lado de un eje que no la mueve.
                medidas_t = _sin_eje_reemplazadas(
                    cat, medidas_t, pieza.get("por"))
                constantes = {n for _t, n in sin_eje(
                    cat, medidas_t, pieza.get("por"))}
                medidas_t = [par for par in medidas_t
                             if par[1] not in constantes]
            if medidas_t:
                visuales.append(visual(
                    "pivotTable", x, y, ancho, alto_libre, medidas=medidas_t,
                    categoria=pieza.get("por"),
                    titulo=pieza.get("titulo", ""), marca=m,
                    colores=colores))
        x += ancho + 12
    return pagina(nombre, visuales, ordinal, m)


# Una columna que guarda el NOMBRE de algo no es una dimensión: tiene
# tantos valores como filas y un gráfico por ella es una lista, no un
# corte. Se descartan por nombre porque la cardinalidad no se conoce
# hasta que Power BI carga los datos.
# `InteraccionID` se colaba: el patrón pedía separador antes del «id» y
# el camelCase no lo tiene. `(?<=[a-z])ID$` es sensible a mayúsculas a
# propósito — «Madrid» termina en «id» y no es una clave.
_RE_CLAVE = re.compile(r"(^id[_ ]|[_ ]id$|^id$|codigo|code)", re.IGNORECASE)
_RE_CLAVE_CAMEL = re.compile(r"(?<=[a-z])(ID|Id)$|^(ID|Id)(?=[A-Z])")
_RE_NOMINAL = re.compile(
    r"(nombre|apellido|razon|email|mail|direccion|telefono|descripcion|"
    r"observacion|comentario|name|address|phone)", re.IGNORECASE)


def _es_dimension(tabla: str, c: dict, cat: Catalogo) -> bool:
    """¿Sirve para cortar el negocio en pedazos comparables?

    El booleano cuenta: «tiene consentimiento digital» parte el panel en
    dos y es exactamente la pregunta que alguien quiere ver contestada.
    Quedaba afuera sólo porque el filtro pedía `string`.
    """
    if c["tipo"] not in ("string", "boolean"):
        return False
    if (_RE_CLAVE.search(c["nombre"]) or _RE_CLAVE_CAMEL.search(c["nombre"])
            or _RE_NOMINAL.search(c["nombre"])):
        return False
    # El calendario no: el tiempo ya tiene sus gráficos y sus filtros, y
    # «Ventas por Mes» en una página de segmentos es un eje repetido.
    cal = cat.tabla_fechas()
    return not (cal and _norm(cal["nombre"]) == _norm(tabla))


def _dimensiones(cat: Catalogo, maximo: int = 3) -> list[tuple[str, str]]:
    """Columnas visibles que sirven de dimensión Y FILTRAN algo.

    «Sirven de dimensión» no alcanza: la columna tiene que llegar, por las
    relaciones, a alguna tabla de hechos. Antes se tomaban las primeras
    columnas de texto en el orden del catálogo, y si la primera hoja del
    Excel era el glosario del dataset, sus columnas terminaban de eje y de
    filtro en la PORTADA: cada barra mostraba el mismo total —el 8,0 % de
    todo— con cara de hallazgo, y los slicers no filtraban nada. Visto en
    Desktop por un usuario, en la primera página de su informe.
    """
    hechos = set(_hechos_del_modelo(cat))
    out = []
    for tabla, c in cat.columnas(solo_visibles=True):
        if not _es_dimension(tabla, c, cat):
            continue
        if hechos and not filtra(cat, tabla, hechos):
            continue
        out.append((tabla, c["nombre"]))
        if len(out) >= maximo:
            break
    return out


# Cuántos filtros entran en la fila sin que cada uno quede tan angosto
# que no se lea la opción elegida.
MAX_CORTES = 5

# El orden importa: primero el tiempo (año y período), después las
# categorías. Es el orden en que se filtra un informe de verdad.
# Año y período mensual alcanzan: sumar el trimestre comía el
# lugar de las categorías, que es lo que de verdad se filtra.
_CORTES_TIEMPO = ("anio", "anio_mes")


def _cortes_calendario(cat: Catalogo) -> list[tuple[str, str]]:
    """Año y período del calendario, si el modelo los tiene.

    Se toman las columnas que EXISTEN en la tabla de fechas, no las que
    este programa hubiera puesto: un calendario en inglés dice `Year` y
    un slicer contra una columna inventada es un visual roto.
    """
    from .periodos import _SINONIMOS

    cal = cat.tabla_fechas()
    if cal is None:
        return []
    presentes = {_norm(c["nombre"]): c["nombre"] for c in cal["columnas"]
                 if not c.get("isHidden")}
    salida = []
    for clave in _CORTES_TIEMPO:
        real = next((presentes[_norm(a)] for a in _SINONIMOS.get(clave, ())
                     if _norm(a) in presentes), None)
        if real:
            salida.append((cal["nombre"], real))
    return salida


def _cortes_pagina(cat: Catalogo,
                   propios: list[tuple[str, str]] | None = None
                   ) -> list[tuple[str, str]]:
    """Los filtros de una página: los del tema, después tiempo y categorías.

    Antes cada página mostraba solamente lo que el tema declaraba, y un
    tema sin `filtros` salía sin ninguno — de ahí que faltaran el año, el
    mes y las categorías en todo el informe.
    """
    # El tiempo primero: un informe se filtra por año y período antes que
    # por categoría, y la fila se lee de izquierda a derecha.
    candidatos = _cortes_calendario(cat) + list(propios or []) \
        + _dimensiones(cat, maximo=MAX_CORTES)
    salida: list[tuple[str, str]] = []
    for corte in candidatos:
        if corte not in salida:
            salida.append(corte)
        if len(salida) >= MAX_CORTES:
            break
    return salida


def _fila_slicers(dims: list[tuple[str, str]],
                  fecha: tuple[str, str] | None,
                  marca: dict | None = None, y: int = FILA_SLICER
                  ) -> list[dict]:
    cortes = []
    for corte in list(dims) + ([fecha] if fecha else []):
        if corte not in cortes:
            cortes.append(corte)
    cortes = cortes[:MAX_CORTES]
    if not cortes:
        return []
    ancho = (ANCHO - 2 * MARGEN - 10 * (len(cortes) - 1)) // len(cortes)
    return [slicer(MARGEN + i * (ancho + 10), y, ancho, ALTO_SLICER,
                   t, c, c, marca)
            for i, (t, c) in enumerate(cortes)]


# Cuántas páginas temáticas se arman como mucho. Más que esto y el
# informe deja de ser un informe: es un archivo por el que hay que
# navegar. Las de segmentos y análisis van aparte, encima de este tope.
MAX_TEMAS = 8

# Cuántas medidas entran en la tabla de una página temática.
_MEDIDAS_TABLA = 4


def _mapa_de_medidas(cat: Catalogo) -> dict[str, set[str]]:
    """Qué tablas toca cada medida, calculado UNA vez.

    `tablas_de_medida` sigue la cadena de llamadas y es recursiva: pedirla
    por cada medida y por cada tabla de hechos multiplicaba el trabajo por
    cinco en un modelo mediano — medido en la suite, 12 s a 58 s.
    """
    return {m["nombre"]: tablas_de_medida(cat, m["nombre"])
            for m in cat.medidas()}


def _hechos_del_modelo(cat: Catalogo,
                       mapa: dict[str, set[str]] | None = None) -> list[str]:
    """Las tablas de hechos, de la que más medidas tiene a la que menos.

    Es el lado «muchos» de alguna relación: lo que se mide. Si el modelo
    no tiene relaciones —un solo archivo suelto—, cualquier tabla visible
    con medidas encima cuenta, que es lo único que se puede afirmar.
    """
    mapa = mapa if mapa is not None else _mapa_de_medidas(cat)
    muchos = {_norm(r["desde_tabla"]) for r in cat.relaciones}
    cuenta: dict[str, int] = {}
    for tablas in mapa.values():
        for t in tablas:
            cuenta[t] = cuenta.get(t, 0) + 1
    candidatas = [t["nombre"] for t in cat.tablas
                  if not t["interna"] and not t["oculta"]
                  and (not muchos or _norm(t["nombre"]) in muchos)]
    cal = cat.tabla_fechas()
    if cal:
        candidatas = [t for t in candidatas
                      if _norm(t) != _norm(cal["nombre"])]
    con_medidas = [t for t in candidatas if cuenta.get(t)]
    return sorted(con_medidas, key=lambda t: (-cuenta[t], t))


def _sin_texto(cat: Catalogo, nombres: list[str]) -> list[str]:
    """Sólo las medidas numéricas: una frase no se grafica.

    Una medida de texto —la lectura de una página, un «¿cuál producto
    vende más?»— en una línea de tiempo o en una barra es un visual roto;
    y como tarjeta de la portada, una oración entera donde va un número.
    """
    from .analizador import es_medida_de_texto

    salida = []
    for n in nombres:
        m = cat.medida(n)
        if m and not es_medida_de_texto(m.get("expresion", ""), cat):
            salida.append(n)
    return salida


def _medidas_de(cat: Catalogo, hecho: str,
                mapa: dict[str, set[str]]) -> list[str]:
    """Las medidas NUMÉRICAS que se calculan sobre esta tabla de hechos."""
    return _sin_texto(cat, [
        m["nombre"] for m in cat.medidas()
        if _norm(hecho) in {_norm(t)
                            for t in mapa.get(m["nombre"], set())}])


def _dimensiones_de(cat: Catalogo, hechos: str | set[str],
                    maximo: int = MAX_CORTES) -> list[tuple[str, str]]:
    """Las dimensiones que de verdad filtran a estas tablas de hechos.

    No es lo mismo que «las dimensiones del modelo»: cortar las visitas
    por una columna de la tabla de mercado no filtra nada y dibuja el
    mismo total en todas las barras — un número que parece un hallazgo.
    """
    objetivo = {hechos} if isinstance(hechos, str) else set(hechos)
    salida: list[tuple[str, str]] = []
    vistas: set[str] = set()
    for tabla, c in cat.columnas(solo_visibles=True):
        if not _es_dimension(tabla, c, cat) or c["nombre"] in vistas:
            continue
        if not filtra(cat, tabla, objetivo):
            continue
        salida.append((tabla, c["nombre"]))
        vistas.add(c["nombre"])
        if len(salida) >= maximo:
            break
    return salida


def _columna_periodo(cat: Catalogo) -> tuple[str, str] | None:
    """La columna del calendario con la que se lee una serie de tiempo en
    una tabla: «2025-03», no la fecha día por día."""
    cortes = _cortes_calendario(cat)
    return cortes[-1] if cortes else None


def _columna_competencia(cat: Catalogo) -> tuple[str, str] | None:
    """La columna que dice QUIÉN vende: el eje de la matriz de
    competidores. `None` si el modelo no tiene competencia adentro."""
    from .periodos import columna_corporacion
    return columna_corporacion(cat)


def _tema_de(cat: Catalogo, titulo: str, disponibles: list[str],
             dims: list[tuple[str, str]], fecha, idioma: str,
             orden: list[str] | None = None) -> dict | None:
    """Una página con la lectura con la que se decide.

    Siempre en el mismo orden, porque es el orden en que se pregunta:
    dónde estoy (el nivel), contra quién (el mercado), cuánto peso (el
    share), cómo vengo (la variación) y cuánto gané o perdí (los puntos).
    Abajo, la evolución en el tiempo, el ranking por la dimensión que más
    explica y la matriz de períodos —hoy, el año anterior, la variación y
    el acumulado— que es donde se ve si el mes malo es un mes o una
    tendencia.
    """
    from . import roles

    bl = roles.bloque(cat, disponibles, orden)
    if not bl.get("nivel"):
        return None
    # ¿El calendario llega a lo que mide esta página? Un hecho sin fecha
    # —un padrón de puntos de venta, una tabla de objetivos— no tiene
    # evolución que dibujar: la línea saldría con el mismo total en todos
    # los meses. Es el mismo criterio que aplica el gate de salida.
    hechos_nivel = tablas_de_medida(cat, bl["nivel"])
    con_tiempo = bool(fecha) and (not hechos_nivel
                                  or filtra(cat, fecha[0], hechos_nivel))
    tarjetas = roles.tarjetas(cat, bl, disponibles)
    tema = {"titulo": titulo, "kpis": tarjetas, "filtros": dims,
            "linea": bl["nivel"] if con_tiempo else None}
    if dims:
        tema["barras"] = (bl["nivel"], jerarquia.de(cat, dims[0]))
    # La matriz de períodos: la respuesta a «¿cómo venimos?». Va por
    # AnioMes y no por una dimensión cualquiera — comparar contra el año
    # anterior sólo significa algo sobre un eje de tiempo.
    columnas = roles.columnas_periodo(cat, bl)
    periodo = _columna_periodo(cat) if con_tiempo else None
    if periodo and len(columnas) > 1:
        # Con la jerarquía del calendario en las filas —año → año-mes— la
        # matriz entra plegada en doce filas y se abre al mes que
        # interesa, en vez de gastar la página en un scroll.
        tema["tabla"] = {"medidas": columnas[:_MEDIDAS_TABLA + 1],
                         "por": jerarquia.de(cat, periodo),
                         "titulo": traducir("tb_tabla_periodos", idioma)}
    elif dims and (len(columnas) > 1 or len(dims) > 1):
        # Una matriz de UNA sola columna, al lado de la barra que ya
        # muestra esa misma medida por esa misma dimensión, es la misma
        # información dos veces: el «repite info» adentro de una página.
        # Con otra dimensión o con algo que comparar, sí aporta.
        base = dims[1] if len(dims) > 1 else dims[0]
        tema["tabla"] = {"medidas": columnas[:_MEDIDAS_TABLA],
                         "por": jerarquia.de(cat, base)}
    return tema


def _tema_competencia(cat: Catalogo, disponibles: list[str],
                      dims: list[tuple[str, str]],
                      idioma: str) -> dict | None:
    """La página que el usuario pide primero en un informe de mercado:
    quién vende cuánto, qué parte se lleva cada uno, cuánto se movió y en
    qué puesto estamos.

    El share de las TARJETAS es el de la empresa propia —no depende del
    filtro—, y el de la MATRIZ es el del contexto: ahí cada fila es una
    corporación y su participación es lo que corresponde leer.
    """
    from . import roles

    corp = _columna_competencia(cat)
    if not corp:
        return None
    bl = roles.bloque(cat, disponibles)
    columnas = roles.columnas_competencia(cat, bl)
    if not bl.get("nivel") or len(columnas) < 2:
        return None
    tarjetas = [n for n in (bl.get("mercado"), bl.get("share"),
                            bl.get("pp"), bl.get("nivel"),
                            bl.get("variacion")) if n]
    return {
        "titulo": traducir("tb_tema_competencia", idioma),
        "kpis": tarjetas[:5],
        "filtros": dims,
        "barras": (bl.get("share_contexto") or bl["nivel"], corp),
        "tabla": {"medidas": columnas, "por": jerarquia.de(cat, corp),
                  "titulo": traducir("tb_tabla_competencia", idioma)},
    }


def _repetida(tema: dict, hechas: list[dict]) -> bool:
    """¿Esta página dice lo mismo que otra que ya está?

    La portada se arma con la medida más importante del modelo, y esa
    medida vive en la tabla de hechos más grande — con lo cual la página
    de ESA tabla salía con las mismas cinco tarjetas, la misma línea y la
    misma matriz que la portada. Dos pestañas idénticas con distinto
    nombre: el «repite info» del reclamo, medido después visual por
    visual en el archivo entregado.

    El criterio es lo que se DIBUJA, no el título: las mismas tarjetas,
    la misma línea, el mismo gráfico y la misma matriz. Dos páginas que
    coinciden en las cuatro cosas muestran los mismos números —lo único
    distinto eran los slicers— y la segunda no agrega nada. Compararlas
    por la medida que las encabeza sería demasiado: la portada y la
    página de ventas empiezan las dos por las ventas y después cuentan
    cosas distintas.
    """
    def firma(t: dict):
        return (tuple(t.get("kpis") or []), t.get("linea"),
                repr(t.get("barras")), repr(t.get("tabla")))

    if not tema.get("kpis"):
        return False
    return any(firma(t) == firma(tema) for t in hechas)


def temas_automaticos(cat: Catalogo,
                      medidas_sel: list[str] | None = None,
                      idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Los temas que este dataset da para un informe, sin que nadie los
    escriba.

    Un informe de verdad no es «resumen y detalle»: es una página por
    cada cosa que el negocio mide —las ventas, las visitas, las
    interacciones digitales, el mercado— y cada una con sus KPIs, su
    evolución, su ranking y su matriz de períodos.

    Cada tema toma la tabla de hechos, las medidas que se calculan sobre
    ella y las dimensiones que DE VERDAD la filtran. Una dimensión que no
    llega a ese hecho no entra: dibujaría el mismo total en cada barra. Y
    cada medida entra en el visual que le corresponde POR SU ROL
    (`dxl/roles.py`): el nivel a la primera tarjeta y a la línea, la
    variación con semáforo, el share al lado, el año anterior a la matriz.
    Elegirlas sólo por puntaje ponía tres shares del año pasado en las
    tarjetas y ningún nivel del negocio.
    """
    mapa = _mapa_de_medidas(cat)
    hechos = _hechos_del_modelo(cat, mapa)[:MAX_TEMAS - 2]
    if not hechos:
        return []
    fecha = cat.columna_fecha()
    temas: list[dict] = []
    todas = _sin_texto(cat, [m["nombre"] for m in cat.medidas()])

    # La portada: la lectura global del negocio.
    eleccion = _sin_texto(cat, [n for n in (medidas_sel or [])
                                if cat.medida(n)])
    tablas_kpi = {t for n in (eleccion or todas) for t in mapa.get(n, set())}
    dims_g = _dimensiones_de(cat, tablas_kpi, maximo=2) if tablas_kpi else []
    portada = _tema_de(cat, traducir("tb_tema_resumen", idioma), todas,
                       dims_g, fecha, idioma, orden=eleccion)
    if portada:
        temas.append(portada)

    # La competencia, cuando el modelo la trae adentro.
    competencia = _tema_competencia(cat, todas, dims_g, idioma)
    if competencia:
        temas.append(competencia)

    for hecho in hechos:
        propias = _sin_texto(cat, _medidas_de(cat, hecho, mapa))
        if not propias:
            continue
        tema = _tema_de(cat, hecho, propias, _dimensiones_de(cat, hecho),
                        fecha, idioma)
        if tema and not _repetida(tema, temas):
            temas.append(tema)
    # Una sola página temática no es un informe temático: con un único
    # hecho, la portada y su página dicen lo mismo dos veces.
    return temas if len(temas) > 2 else []


def tarjeta_kpi(x: int, y: int, w: int, h: int, *,
                medida: tuple[str, str], meta: tuple[str, str],
                fecha: tuple[str, str], titulo: str = "",
                marca: dict | None = None) -> dict:
    """El visual KPI de Power BI: valor, tendencia y objetivo.

    Es el que muestra la flecha y pinta el número de verde o rojo SOLO
    con los datos —compara `medida` contra `meta` a lo largo de `fecha`—
    sin ninguna regla de formato condicional. Con una tarjeta común hay
    que poner el nivel en una y la variación en otra, y el crecimiento
    hay que deducirlo.

    Los tres roles son `Indicator`, `TrendLine` y `Goal`. **No pude
    verificarlos contra un archivo real**: ninguno de los 13 `.pbit`/
    `.pbix` de referencia usa este visual. Si en Desktop la tarjeta sale
    en blanco, es acá donde hay que mirar primero — el resto del visual
    (query, proyecciones, formato) sigue la misma forma que los demás,
    que sí están verificados.
    """
    tabla_m, nombre_m = medida
    tabla_g, nombre_g = meta
    tabla_f, col_f = fecha
    alias = {}

    def _al(t: str) -> str:
        if t not in alias:
            alias[t] = f"e{len(alias)}"
        return alias[t]

    select = [_medida_ref(tabla_m, nombre_m, _al(tabla_m)),
              _columna_ref(tabla_f, col_f, _al(tabla_f)),
              _medida_ref(tabla_g, nombre_g, _al(tabla_g))]
    from_ = [{"Name": a, "Entity": t, "Type": 0} for t, a in alias.items()]
    objetos = {}
    if marca:
        objetos["indicator"] = [{"properties": {
            "fontSize": _lit("28D"), "color": _color(marca["tinta"])}}]
        objetos["trendline"] = [{"properties": {"show": _lit("true")}}]
        objetos["goals"] = [{"properties": {
            "show": _lit("true"), "showGoal": _lit("true"),
            "showDistance": _lit("true")}}]
    if titulo:
        props = {"show": _lit("true"), "text": _lit(f"'{titulo}'"),
                 "fontSize": _lit("11D")}
        if marca:
            props["fontColor"] = _color(marca["sobre_primario"])
            props["background"] = _color(marca["primario"])
            props["alignment"] = _lit("'left'")
        objetos["title"] = [{"properties": props}]
    conf = {
        "name": uuid.uuid4().hex[:20],
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0,
                                           "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "kpi",
            "projections": {
                "Indicator": [{"queryRef": f"{tabla_m}.{nombre_m}"}],
                "TrendLine": [{"queryRef": f"{tabla_f}.{col_f}"}],
                "Goal": [{"queryRef": f"{tabla_g}.{nombre_g}"}],
            },
            "prototypeQuery": {"Version": 2, "From": from_, "Select": select},
            "drillFilterOtherVisuals": True,
            "objects": objetos,
        },
    }
    if marca:
        conf["singleVisual"]["vcObjects"] = _tarjeta_con_cuerpo(marca)
    return {"x": x, "y": y, "z": 0, "width": w, "height": h,
            "config": json.dumps(conf, ensure_ascii=False)}


def _kpis(pares: list[tuple[str, str]], marca: dict | None = None,
          y: int = FILA_KPI,
          colores: dict[str, tuple[str, str]] | None = None,
          metas: dict[str, tuple[str, str]] | None = None,
          fecha: tuple[str, str] | None = None) -> list[dict]:
    """Las tarjetas de la fila superior.

    `colores` NO era opcional por descuido: sin él, una tarjeta que
    muestra «Var Share % pp» salía del mismo color que las demás. El
    semáforo llegaba a las tablas y no a lo primero que se mira.

    Cuando una medida tiene su año anterior en el modelo (`metas`) y hay
    calendario, la tarjeta pasa a ser un **KPI**: el mismo número, pero
    con la tendencia dibujada y el color puesto por los datos. Sin eso
    hay que leer dos tarjetas —el nivel en una, la variación en otra— y
    hacer la cuenta a ojo.
    """
    ancho = (ANCHO - 2 * MARGEN - 12 * (len(pares) - 1)) // len(pares)
    salida = []
    for i, p in enumerate(pares):
        x = MARGEN + i * (ancho + 12)
        meta = (metas or {}).get(p[1])
        if meta and fecha:
            salida.append(tarjeta_kpi(x, y, ancho, ALTO_KPI, medida=p,
                                      meta=meta, fecha=fecha, titulo=p[1],
                                      marca=marca))
        else:
            salida.append(visual("card", x, y, ancho, ALTO_KPI, medidas=[p],
                                 titulo=p[1], marca=marca, colores=colores))
    return salida


def metas_de(cat: Catalogo,
             pares: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Para cada medida, su «mismo período del año anterior», si existe.

    Es el objetivo contra el que el KPI decide si creció o cayó. Se busca
    la medida del modelo, no se fabrica: el autor pudo definirla sobre
    otra columna de fecha y su versión es la correcta.
    """
    from .lectura import _anterior_de

    salida = {}
    for _t, nombre in pares:
        otra = _anterior_de(nombre, cat)
        m = cat.medida(otra) if otra else None
        if m:
            salida[nombre] = (m["tabla"], m["nombre"])
    return salida


def _barra_nav(titulos: list[str], actual: str,
               marca: dict | None = None) -> list[dict]:
    """No se dibuja ninguna barra de botones.

    Los `actionButton` salían en Desktop como rectángulos con borde y sin
    texto —dos reportes de campo seguidos— y no hay forma de depurar el
    renderizado desde acá. Power BI ya trae las pestañas de página abajo:
    la navegación no se pierde, se deja de dibujar una versión rota de
    algo que el producto ya hace bien.
    """
    return []


def _barra_nav_botones(titulos: list[str], actual: str,
                       marca: dict | None = None) -> list[dict]:
    ancho = min(190, (ANCHO - 2 * MARGEN) // max(len(titulos), 1) - 6)
    if not marca:
        return [boton_navegacion(MARGEN + i * (ancho + 6), FILA_NAV, ancho,
                                 ALTO_NAV, t, _slug(t), activo=(t == actual))
                for i, t in enumerate(titulos)]
    # Con marca, la navegación va a la DERECHA del encabezado: el lugar de
    # arriba a la izquierda es del logo.
    ancho = 150
    x0 = ANCHO - MARGEN - len(titulos) * (ancho + 6) + 6
    return [boton_navegacion(x0 + i * (ancho + 6), 24, ancho, ALTO_NAV,
                             t, _slug(t), activo=(t == actual), marca=marca)
            for i, t in enumerate(titulos)]


def _encabezado(titulo: str, subtitulo: str,
                marca: dict | None = None) -> list[dict]:
    if not marca:
        return [texto(MARGEN, FILA_TITULO, 760, 30, titulo, 18),
                texto(MARGEN, FILA_TITULO + 28, 760, 24, subtitulo, 10)]
    piezas = []
    x_texto = MARGEN
    if marca.get("logo"):
        piezas.append(imagen(MARGEN, 9, LOGO_ANCHO, LOGO_ALTO, marca["logo"]))
        x_texto = MARGEN + LOGO_ANCHO + 14
    # Título y bajada como UN bloque compacto: 22 px de título + 16 de
    # bajada, pegados. Separados «por las dudas» se pisaban igual, porque
    # el alto que Power BI le da a un cuadro de texto no es el que uno
    # declara — es el del texto renderizado.
    piezas += [
        texto(x_texto, 14, 720, 22, titulo, 16, color=marca["tinta"],
              negrita=True),
        texto(x_texto, 38, 720, 16, subtitulo, 9, color="#6B7A8D"),
    ]
    return piezas


TITULO_ANALISIS = "Análisis"
TITULO_SEGMENTOS = "Segmentos"

# Cuántos cortes entran por página (2 × 2) y cuántas páginas como mucho.
# El tope existe para que un modelo con cuarenta columnas de texto no
# genere siete páginas que nadie va a mirar.
#
# Eran seis por página cuando cada corte era una barra: con matrices de
# cuatro columnas, seis dejaban 160 px de alto —tres filas y el resto
# cortado— y volvían a ser un adorno. Cuatro entran a 250 px, que es una
# tabla que se lee; los cortes que sobran pasan a la segunda página.
POR_PAGINA_SEG, MAX_PAGINAS_SEG = 4, 2


def tablas_de_medida(cat: Catalogo, medida: str,
                     vistas: set[str] | None = None) -> set[str]:
    """Sobre qué tablas se calcula una medida, siguiendo las que llama.

    `[Share Adium USD %]` no nombra ninguna tabla: llama a
    `[Ventas Adium USD]` y a `[Mercado Total USD]`, y son ésas las que
    terminan en `Mercado`. Sin seguir la cadena, la medida parece no
    depender de nada y cualquier corte parecería válido.
    """
    from .catalogo import referencias_dax

    vistas = vistas if vistas is not None else set()
    if medida in vistas:
        return set()
    vistas.add(medida)
    m = cat.medida(medida)
    if not m:
        return set()
    expr = m.get("expresion", "") or ""
    refs = referencias_dax(expr)
    tablas = {t for t, _c in refs["columnas"] if cat.tabla(t)}
    # También la tabla nombrada SOLA: `COUNTROWS ( Ventas )` no menciona
    # ninguna columna, así que la medida parecía no depender de nada y
    # cualquier corte quedaba descartado por «no la filtra».
    tablas |= _tablas_sueltas(cat, expr)
    for otra in refs["medidas"]:
        tablas |= tablas_de_medida(cat, otra, vistas)
    return tablas


def _tablas_sueltas(cat: Catalogo, expr: str) -> set[str]:
    """Las tablas del modelo nombradas sin columna dentro del DAX."""
    sin_cols = re.sub(r"\[[^\[\]]*\]", " ", expr or "")
    salida = set()
    for t in cat.tablas:
        nombre = t["nombre"]
        patron = (re.escape(f"'{nombre}'") if re.search(r"[^\w]", nombre)
                  else rf"\b{re.escape(nombre)}\b")
        if re.search(patron, sin_cols):
            salida.add(nombre)
    return salida


def filtra(cat: Catalogo, dimension: str, hechos: set[str]) -> bool:
    """¿Un corte por esta tabla cambia el número de esas tablas de hechos?

    El filtro viaja del lado UNO al lado MUCHOS, así que se sale desde
    cada tabla de hechos y se sube por las relaciones: si en algún salto
    se llega a la dimensión, el corte filtra.

    Dibujar un corte que no filtra es la peor clase de gráfico: no da
    error, muestra el MISMO total en cada barra y parece un hallazgo
    («todas las ciudades tienen 58 % de share»). Pasó exactamente eso.
    """
    if _norm(dimension) in {_norm(h) for h in hechos}:
        return True
    padres: dict[str, set[str]] = {}
    for r in cat.relaciones:
        if not r.get("activa", True):
            continue
        padres.setdefault(_norm(r["desde_tabla"]), set()).add(
            _norm(r["hacia_tabla"]))
        # Un filtro bidireccional también baja: el lado uno se entera.
        if r.get("bidireccional"):
            padres.setdefault(_norm(r["hacia_tabla"]), set()).add(
                _norm(r["desde_tabla"]))
    objetivo = _norm(dimension)
    pendientes = [_norm(h) for h in hechos]
    vistas = set()
    while pendientes:
        t = pendientes.pop()
        if t == objetivo:
            return True
        if t in vistas:
            continue
        vistas.add(t)
        pendientes.extend(padres.get(t, ()))
    return False


_RE_REMOVEFILTERS = re.compile(
    r"REMOVEFILTERS\s*\(\s*'?([^'\[\]()]+?)'?\s*\[\s*([^\]]+?)\s*\]\s*\)",
    re.IGNORECASE)


def eje_requerido(cat: Catalogo, medida: str,
                  vistas: set[str] | None = None) -> set[str]:
    """Las columnas cuyo filtro la medida QUITA, siguiendo las que llama.

    Un share cuyo denominador hace `REMOVEFILTERS(Mercado[Corporacion])`
    solo significa algo cuando la corporación está en el eje del visual:
    en cualquier otro lado el numerador y el denominador se filtran igual
    y da 100 % en todas las filas — y su variación contra el año
    anterior, exactamente 0. Es un número que parece un dato y no lo es.
    """
    vistas = vistas if vistas is not None else set()
    if medida in vistas:
        return set()
    vistas.add(medida)
    m = cat.medida(medida)
    if not m:
        return set()
    expr = m.get("expresion") or ""
    ejes = {_norm(c) for _t, c in _RE_REMOVEFILTERS.findall(expr)}
    from .catalogo import referencias_dax
    for otra in referencias_dax(expr)["medidas"]:
        ejes |= eje_requerido(cat, otra, vistas)
    # Una columna que la medida además FIJA no la deja constante: en
    # «Share Adium USD %» el denominador quita el filtro de corporación
    # pero el numerador la clava en Adium, así que el share se mueve con
    # el área, con el producto y con el mes. Sin esta resta la regla
    # acusaba justo a las medidas que sí funcionan.
    return ejes - _columnas_fijadas(cat, medida)


_RE_FIJADA = re.compile(
    r"'?([A-Za-z_][\w .]*?)'?\s*\[\s*([^\[\]]+?)\s*\]\s*(?:=|\bIN\b)",
    re.IGNORECASE)


def _columnas_fijadas(cat: Catalogo, medida: str,
                      vistas: set[str] | None = None) -> set[str]:
    """Las columnas que la medida clava en un valor, en toda la cadena."""
    vistas = vistas if vistas is not None else set()
    if medida in vistas:
        return set()
    vistas.add(medida)
    m = cat.medida(medida)
    if not m:
        return set()
    expr = m.get("expresion") or ""
    fijas = {_norm(c) for _t, c in _RE_FIJADA.findall(expr)}
    from .catalogo import referencias_dax
    for otra in referencias_dax(expr)["medidas"]:
        fijas |= _columnas_fijadas(cat, otra, vistas)
    return fijas


def _columnas_pisadas(cat: Catalogo, medida: str,
                      vistas: set[str] | None = None) -> set[str]:
    """Las columnas que la medida clava PISANDO el filtro de la fila.

    Es un subconjunto de `_columnas_fijadas`: acá no cuentan las que van
    dentro de `KEEPFILTERS`, porque ésas se INTERSECAN con el filtro de la
    fila en vez de reemplazarlo. La diferencia se ve en pantalla:

      CALCULATE ( AVERAGE ( T[Min] ), T[Canal] IN { "Portal" } )
          → los cuatro canales muestran el promedio de Portal.
      CALCULATE ( AVERAGE ( T[Min] ), KEEPFILTERS ( T[Canal] IN { … } ) )
          → Portal y Webinar muestran lo suyo, los otros dos quedan en
            blanco. Correcto, y por eso no se toca.

    Sin esta distinción el detector acusaba a «Duración Media Min» —que
    varía de verdad: Portal 12,24 y Webinar 8,40— y el generador le
    buscaba un reemplazo que no hacía falta.
    """
    from .analizador import RE_KEEPFILTERS, _sin_llamadas

    vistas = vistas if vistas is not None else set()
    if medida in vistas:
        return set()
    vistas.add(medida)
    m = cat.medida(medida)
    if not m:
        return set()
    expr = _sin_llamadas(m.get("expresion") or "", RE_KEEPFILTERS)
    pisa = {_norm(c) for _t, c in _RE_FIJADA.findall(expr)}
    from .catalogo import referencias_dax
    for otra in referencias_dax(m.get("expresion") or "")["medidas"]:
        pisa |= _columnas_pisadas(cat, otra, vistas)
    return pisa


def sin_eje(cat: Catalogo, medidas: list[tuple[str, str]],
            categorias: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Las medidas que van a mostrar el MISMO número en todas las filas.

    Dos formas de lo mismo, y las dos aparecieron en pantalla:

    · La medida QUITA el filtro de una columna que el visual no tiene en
      el eje. El numerador y el denominador se filtran igual y da 100 %,
      o 0,0 en su variación. Fue el «me parece raro el 0».
    · La medida CLAVA una columna que el visual SÍ tiene en el eje. El
      filtro de la medida reemplaza al de la fila, así que las tres
      barras de «Visitas Realizadas por Estado» daban 554 — el conteo de
      «Realizada»— cuando el reparto real era 554 / 55 / 41.

    En los dos casos el gráfico no da error, muestra un número plausible
    y repetido, y parece un hallazgo.
    """
    # `categorias` puede ser UNA columna o varias, igual que en `visual`.
    cats = ([categorias] if categorias and isinstance(categorias[0], str)
            else list(categorias or []))
    presentes = {_norm(c) for _t, c in cats}
    fuera = []
    for par in medidas:
        pide = eje_requerido(cat, par[1])
        # PISA, no sólo fija: lo que va dentro de KEEPFILTERS se interseca
        # con el filtro de la fila y deja que la medida se mueva.
        clava = _columnas_pisadas(cat, par[1])
        if clava & presentes:
            fuera.append(par)
            continue
        if not pide or (pide & presentes):
            continue
        # Una medida ADITIVA que quita una columna sigue moviéndose por
        # cualquier OTRO eje que la filtre: el total del mercado —que
        # quita la corporación— dibuja una curva perfectamente real mes a
        # mes, y es justo la serie de comparación propio-vs-mercado. La
        # regla la acusaba igual y el tablero perdía esa línea. Un RATIO
        # no se salva así: el corte mueve numerador y denominador por
        # igual y el cociente queda clavado en 100 %.
        if not _es_razon(cat, par[1]):
            tablas = tablas_de_medida(cat, par[1])
            if any(_norm(c) not in pide and filtra(cat, t, tablas)
                   for t, c in cats):
                continue
        fuera.append(par)
    return fuera


def _sin_eje_reemplazadas(cat: Catalogo, medidas: list[tuple[str, str]],
                          categorias) -> list[tuple[str, str]]:
    """Cambia la medida que quedaría constante por su equivalente propia.

    `Var Share Unidades % pp` sin corporación en el eje da 0 en todas las
    filas; `Var Share Adium Unidades % pp` mide lo mismo para lo propio y
    sí se mueve. Si el modelo no tiene la equivalente, se deja como está:
    la elección es del autor del tema, y el gate de salida lo reporta.
    """
    problematicas = {n for _t, n in sin_eje(cat, medidas, categorias)}
    if not problematicas:
        return medidas
    salida = []
    for tabla, nombre in medidas:
        if nombre not in problematicas:
            salida.append((tabla, nombre))
            continue
        base = _fichas(nombre)
        mejor, coste = None, None
        for m in cat.medidas():
            otro = m["nombre"]
            if otro == nombre or sin_eje(cat, [(m["tabla"], otro)],
                                         categorias):
                continue
            fichas = _fichas(otro)
            if not base <= fichas:
                continue
            d = len(fichas - base)
            if coste is None or d < coste:
                mejor, coste = (m["tabla"], otro), d
        salida.append(mejor or (tabla, nombre))
    return salida


def _es_razon(cat: Catalogo, medida: str,
              vistas: set[str] | None = None) -> bool:
    """¿La medida es un cociente (o llama a uno)?

    Es la distinción que decide si «quita un filtro» la deja constante:
    un RATIO cortado por cualquier eje mueve numerador y denominador por
    igual y queda clavado en 100 %; una SUMA que quita la corporación
    —el total del mercado— sigue repartiéndose por mes y por producto,
    que es exactamente la serie de comparación propio-vs-mercado. Se
    sigue la cadena de llamadas porque el cociente puede estar dos
    medidas más abajo, y se mira el código sin literales para que la
    barra de un formato de fecha no cuente como división.
    """
    from .analizador import _solo_codigo_dax
    from .catalogo import referencias_dax

    vistas = vistas if vistas is not None else set()
    if medida in vistas:
        return False
    vistas.add(medida)
    m = cat.medida(medida) or {}
    codigo = _solo_codigo_dax(m.get("expresion") or "").upper()
    if "DIVIDE" in codigo or "/" in codigo or "AVERAGE" in codigo:
        return True
    return any(_es_razon(cat, otra, vistas)
               for otra in referencias_dax(codigo)["medidas"])


def _es_aditiva(cat: Catalogo, medida: str) -> bool:
    """Una medida que SUMA, no una razón.

    Para abrir el negocio por dimensión hace falta algo que se reparta
    entre las categorías. Un share cuyo denominador quita filtros da
    100 % en cada producto —el numerador y el denominador se filtran
    igual— y la página entera no dice nada.
    """
    m = cat.medida(medida) or {}
    dax = (m.get("expresion") or "").upper()
    return not ("DIVIDE" in dax or "/" in dax
                or "REMOVEFILTERS" in dax or "ALL(" in dax
                or "AVERAGE" in dax)


def _candidatas_segmento(temas: list[dict],
                         por_nombre: dict) -> list[tuple[str, str]]:
    """Con qué medidas se pueden abrir los segmentos, en orden de preferencia.

    Lo PROPIO antes que el mercado —«Ventas por Molécula» del mercado
    entero describe la categoría, no el negocio de quien mira el informe—
    y un nivel antes que una variación, que sin base no se entiende. Se
    devuelven TODAS porque no hay una medida que sirva para todo corte:
    el share vive sobre la tabla de mercado y no lo filtra el médico, así
    que la ciudad se abre con visitas o recetas y el producto con ventas.
    """
    vistas, orden = set(), []
    for t in temas:
        for n in t.get("kpis") or []:
            if n in por_nombre and n not in vistas and not _es_variacion(n):
                vistas.add(n)
                orden.append(n)
    propias = [n for n in orden if not _es_del_mercado(n)]
    ajenas = [n for n in orden if _es_del_mercado(n)]
    # Y detrás, el resto de las medidas del modelo. Hace falta cuando la
    # que el tema eligió no sirve para ese corte: «Visitas Realizadas»
    # clava el estado, así que abierta POR estado da el mismo número en
    # las tres barras — pero «Visitas Totales» existe y da el reparto de
    # verdad. Sin este respaldo, el corte se perdía entero.
    from .analizador import es_medida_de_texto
    resto = [md["nombre"] for md in por_nombre.values()
             if md["nombre"] not in vistas
             and not _es_variacion(md["nombre"])
             # Una medida de TEXTO no abre un gráfico de barras: la
             # lectura del informe llegó a emparejarse con su propio eje
             # de páginas y salió una página de segmentos con una frase.
             and not es_medida_de_texto(md.get("expresion", ""))]
    return [(por_nombre[n]["tabla"], n) for n in propias + ajenas + resto]


def _pendientes(cat: Catalogo,
                secciones: list[dict]) -> list[tuple[str, str]]:
    """Las dimensiones del modelo que ninguna página abrió todavía."""
    # Por NOMBRE de columna, no por (tabla, columna): un modelo
    # desnormalizado repite «Corporacion» en la tabla de hechos, y abrir
    # dos veces la misma dimensión es una página que no agrega nada.
    usados = {_norm(col) for _t, col in _ejes_usados(secciones)}
    salida, vistos = [], set()
    for t, c in cat.columnas(solo_visibles=True):
        clave = _norm(c["nombre"])
        if clave in usados or clave in vistos:
            continue
        if not _es_dimension(t, c, cat):
            continue
        vistos.add(clave)
        salida.append((t, c["nombre"]))
    return salida


def _ejes_usados(secciones: list[dict]) -> set[tuple[str, str]]:
    """Las columnas que YA son el eje de un gráfico o una tabla.

    Un slicer no cuenta: filtrar por «Segmento» no es lo mismo que ver
    cuánto aporta cada segmento, y era justo lo que faltaba.
    """
    usados = set()
    for s in secciones:
        for v in s.get("visualContainers", []):
            sv = json.loads(v["config"])["singleVisual"]
            if sv["visualType"] == "slicer":
                continue
            for sel in sv.get("prototypeQuery", {}).get("Select", []):
                col = sel.get("Column")
                if col:
                    usados.add((sel["Name"].split(".")[0],
                                col["Property"]))
    return usados


def cortes_utiles(cat: Catalogo, dimensiones: list[tuple[str, str]],
                  candidatas: list[tuple[str, str]]
                  ) -> tuple[list[tuple], list[tuple[tuple, str]]]:
    """Empareja cada dimensión con una medida que esa dimensión FILTRE.

    Devuelve `(pares, descartadas)`. Una dimensión sin medida que la
    responda no se dibuja, y el motivo queda anotado para el informe: es
    la diferencia entre una página vacía y una que muestra el mismo 58 %
    en las siete ciudades porque la medida vive en una tabla que el
    médico no toca.

    No se prueba una medida por dimensión y listo: se prueba en el orden
    en que el tema las declaró, así el corte se abre con la medida más
    importante que efectivamente responde.
    """
    hechos = {n: tablas_de_medida(cat, n) for _t, n in candidatas}
    pares, descartadas = [], []
    for dim in dimensiones:
        elegida = next(
            (par for par in candidatas
             if _es_aditiva(cat, par[1])
             and filtra(cat, dim[0], hechos[par[1]])
             # Y que no CLAVE la columna del corte: «Visitas Realizadas»
             # abierta por Estado da el mismo número en las tres barras.
             and not sin_eje(cat, [par], [dim])),
            None)
        if elegida:
            pares.append((dim, elegida))
        else:
            descartadas.append(
                (dim, f"ninguna medida del tablero se filtra por "
                      f"«{dim[0]}»: el corte daría el mismo total en cada "
                      f"categoría"))
    return pares, descartadas


def _columnas_corte(cat, medida: tuple[str, str],
                    dim) -> list[tuple[str, str]]:
    """Las columnas con las que se lee un corte: cuánto, cuánto antes,
    cuánto cambió y cuánto pesa.

    Una barra sola dice quién es más grande y nada más. La misma
    dimensión con «hoy · mismo período del año anterior · variación % ·
    acumulado», con el rojo y el verde puestos, dice además si el grande
    está creciendo o cayendo — que es la pregunta que se hace quien mira.
    Sin comparativos en el modelo se devuelve la medida sola y el corte
    sale como gráfico, como antes.
    """
    from . import roles

    if cat is None:
        return [medida]
    disponibles = [m["nombre"] for m in cat.medidas()]
    bl = roles.con_nivel(cat, disponibles, medida[1])
    if not bl:
        return [medida]
    nombres = roles.columnas_periodo(cat, bl)[:_MEDIDAS_TABLA]
    por_nombre = {m["nombre"]: m for m in cat.medidas()}
    pares = [(por_nombre[n]["tabla"], n) for n in nombres if n in por_nombre]
    # Contra ESTE eje, una medida que no se mueve es ruido: la misma
    # cifra repetida en todas las filas parece un dato y no lo es.
    pares = _sin_eje_reemplazadas(cat, pares, dim)
    constantes = {n for _t, n in sin_eje(cat, pares, dim)}
    return [p for p in pares if p[1] not in constantes] or [medida]


def _paginas_segmentos(titulo, pares, cortes, marca, ordinal0,
                       cat=None, colores=None) -> list[dict]:
    """Una lectura por cada dimensión que ninguna página usa como eje.

    El generador armaba el informe con las dos o tres primeras dimensiones
    y dejaba el resto afuera sin decirlo: en un modelo farmacéutico eso
    significaba ningún tablero de potencial del médico, de consentimiento
    digital, de molécula ni de tipo de visita. Todas columnas que estaban
    ahí y que el negocio mira.

    `pares` son `(dimensión, medida)` ya emparejados por `cortes_utiles`:
    cada corte se abre con una medida que esa dimensión realmente filtra.

    Lo que había acá eran SEIS gráficos de barras monocromos por página,
    cada uno con un solo número por categoría. Ahora cada corte es una
    matriz con su jerarquía desplegable y sus comparativos —hoy, el año
    anterior, la variación con semáforo—, y entran dos por fila en vez de
    tres: menos visuales, mucha más información por centímetro.
    """
    salida = []
    for p in range(min(MAX_PAGINAS_SEG,
                       -(-len(pares) // POR_PAGINA_SEG))):
        grupo = pares[p * POR_PAGINA_SEG:(p + 1) * POR_PAGINA_SEG]
        nombre = TITULO_SEGMENTOS if p == 0 else f"{TITULO_SEGMENTOS} {p + 1}"
        desplazo = ALTO_MARCA - FILA_SLICER + 8 if marca else 0
        y = FILA_SLICER + desplazo
        visuales = (_encabezado(
            f"{titulo} · {nombre}",
            "Cada corte, con una medida que ese corte filtra de verdad",
            marca)
            + _fila_slicers(cortes or [], None, marca, y))
        y0 = y + (ALTO_SLICER + 12 if cortes else 0)
        por_fila = 2
        filas = max(1, -(-len(grupo) // por_fila))
        ancho = (ANCHO - 2 * MARGEN - 12 * (por_fila - 1)) // por_fila
        alto = (ALTO - y0 - MARGEN - 12 * (filas - 1)) // filas
        for i, (dim, medida) in enumerate(grupo):
            niveles = jerarquia.de(cat, dim) if cat is not None else [dim]
            columnas = _columnas_corte(cat, medida, niveles)
            x = MARGEN + (i % por_fila) * (ancho + 12)
            yy = y0 + (i // por_fila) * (alto + 12)
            tipo = "pivotTable" if len(columnas) > 1 else "clusteredBarChart"
            visuales.append(visual(
                tipo, x, yy, ancho, alto,
                medidas=columnas, categoria=niveles,
                titulo=f"{medida[1]} por {niveles[0][1]}", marca=marca,
                colores=colores))
        salida.append(pagina(nombre, visuales, ordinal0 + p, marca))
    return salida


def cortes_de_analisis(cat: Catalogo, lecturas: list[dict],
                       cortes: list[tuple[str, str]]
                       ) -> list[tuple[str, str]]:
    """Los filtros de la página de análisis: los que MUEVEN la conclusión.

    La página heredaba los cortes genéricos —especialidad, ciudad,
    segmento— y cuatro de las seis conclusiones no se movían con ellos:
    hablan de ventas y share, que viven sobre la tabla de mercado, y el
    médico no la toca. Un filtro que no cambia el texto que tiene al lado
    es peor que no estar: parece que el informe no responde.

    El calendario se conserva siempre —filtra todo lo que tenga fecha— y
    de las categorías quedan las que filtran al menos una de las medidas
    que las lecturas usan.
    """
    protagonistas = [le.get("medida") for le in lecturas if le.get("medida")]
    if not protagonistas:
        return cortes
    hechos = {n: tablas_de_medida(cat, n) for n in protagonistas}
    cal = cat.tabla_fechas()
    nombre_cal = _norm(cal["nombre"]) if cal else ""
    # La MAYORÍA, no «al menos una»: un corte que mueve dos de seis
    # conclusiones y deja las otras cuatro quietas se ve igual de roto
    # que uno que no mueve ninguna. El calendario se conserva siempre —
    # filtra todo lo que tenga fecha.
    minimo = (len(protagonistas) + 1) // 2
    salida = []
    for c in cortes:
        if _norm(c[0]) == nombre_cal:
            salida.append(c)
            continue
        mueve = sum(1 for n in protagonistas if filtra(cat, c[0], hechos[n]))
        if mueve >= minimo:
            salida.append(c)
    return salida


def _pagina_diccionario(titulo: str, cat: Catalogo, marca,
                        ordinal: int) -> dict | None:
    """La página que explica cada medida: fórmula y por qué está así.

    El diccionario viaja como tabla desconectada dentro del modelo
    (`dxl/diccionario.py`), así que no es un cartel escrito al exportar:
    quien recibe el archivo lo abre y ahí está, con la misma información
    que el informe. Sin esta página el diccionario existía y no se veía —
    estaba en el modelo y nadie lo miraba nunca.
    """
    from .diccionario import TABLA as TABLA_DICC

    tabla = next((t for t in cat.tablas
                  if _norm(t["nombre"]) == _norm(TABLA_DICC)), None)
    if not tabla or not tabla["columnas"]:
        return None
    columnas = [(tabla["nombre"], c["nombre"]) for c in tabla["columnas"]
                if not c["oculta"]]
    if not columnas:
        return None
    nombre = traducir("tb_pagina_medidas", IDIOMA_DEFECTO)
    desplazo = ALTO_MARCA - FILA_SLICER + 8 if marca else 0
    y = FILA_SLICER + desplazo
    visuales = _encabezado(
        f"{titulo} · {nombre}",
        traducir("tb_pagina_medidas_sub", IDIOMA_DEFECTO), marca)
    visuales.append(visual(
        "tableEx", MARGEN, y, ANCHO - 2 * MARGEN, ALTO - y - MARGEN,
        categoria=columnas, titulo=nombre, marca=marca,
        formato={"values": [{"properties": {
            "wordWrap": _lit("true"), "fontSize": _lit("10D")}}]}))
    return pagina(nombre, visuales, ordinal, marca)


def _kpis_globales(cat: Catalogo,
                   medidas_sel: list[str] | None = None) -> list[str]:
    """Las cinco cifras que resumen el informe: nivel, mercado, share,
    variación y puntos. Las mismas de la portada, para que la página de
    conclusiones hable de los mismos números."""
    from . import roles
    todas = _sin_texto(cat, [m["nombre"] for m in cat.medidas()])
    eleccion = _sin_texto(cat, [n for n in (medidas_sel or [])
                                if cat.medida(n)])
    bl = roles.bloque(cat, todas, eleccion)
    return roles.tarjetas(cat, bl, todas) if bl else []


def _pagina_analisis(titulos, titulo, lecturas, cortes, marca,
                     ordinal, kpis_globales=None, colores=None,
                     metas=None, fecha=None) -> dict:
    """La última página: qué dice cada pestaña y qué hacer con eso.

    Las conclusiones son medidas de texto del modelo (`dxl/lectura.py`),
    no un cartel escrito al exportar: se recalculan cuando alguien elige
    otro año, otro mes o una categoría. Un texto fijo diría lo del día en
    que se generó el archivo y mentiría con el primer filtro.
    """
    desplazo = ALTO_MARCA - FILA_SLICER + 8 if marca else 0
    y = FILA_SLICER + desplazo
    visuales = (_encabezado(
        f"{titulo} · {TITULO_ANALISIS}",
        "Lectura automática de cada página — se recalcula con los filtros",
        marca) + _fila_slicers(cortes or [], None, marca, y))
    y0 = y + (ALTO_SLICER + 12 if cortes else 0)
    # Los números que la lectura menciona, arriba de la lectura. Una
    # página de conclusiones sin una sola cifra obliga a volver a la
    # pestaña anterior para saber de qué se está hablando: se reportó
    # como «la pestaña análisis está mal hecha», y tenía razón.
    if kpis_globales:
        visuales += _kpis(kpis_globales[:5], marca, y0, colores,
                          metas or {}, fecha)
        y0 += ALTO_KPI + 12
    eje = lecturas[0].get("eje")
    unica = lecturas[0].get("unica")
    if eje and unica:
        # Una FILA por página. La tarjeta de varias filas acomodaba las
        # cinco conclusiones en columnas de 230 px y cortaba cada frase en
        # la primera línea: la pestaña no decía nada. Una celda de tabla
        # ajusta el texto y se lee entera.
        visuales.append(visual(
            "tableEx", MARGEN, y0, ANCHO - 2 * MARGEN, ALTO - y0 - MARGEN,
            medidas=[unica], categoria=eje, titulo="Conclusiones",
            marca=marca, formato={"values": [{"properties": {
                "fontColor": _color(marca["tinta"] if marca else "#081527"),
                "backColor": _color(marca["fondo"] if marca else "#FFFFFF"),
                "wordWrap": _lit("true"), "fontSize": _lit("11D")}}]}))
    else:
        pares = [(le["tabla"], le["nombre"]) for le in lecturas]
        visuales.append(visual(
            "multiRowCard", MARGEN, y0, ANCHO - 2 * MARGEN,
            ALTO - y0 - MARGEN, medidas=pares, titulo="Conclusiones",
            marca=marca,
            formato={"labels": [{"properties": {
                "color": _color(marca["tinta"] if marca else "#081527"),
                "fontSize": _lit("11D"), "bold": _lit("false")}}]}))
    return pagina(TITULO_ANALISIS, visuales, ordinal, marca)


def _pagina_resumen(titulos, titulo, pares, dims, fecha, marca=None,
                    cortes=None, universo=None, metas=None) -> dict:
    # Con marca, el encabezado ocupa una banda propia y todo baja.
    desplazo = ALTO_MARCA - FILA_SLICER + 8 if marca else 0
    y_slicer = FILA_SLICER + desplazo
    y_kpi = FILA_KPI + desplazo
    visuales = (_barra_nav(titulos, titulos[0], marca)
                + _encabezado(titulo, "Generado por MV DAX Lab", marca)
                + _fila_slicers(cortes if cortes is not None else dims,
                                None if cortes else fecha, marca, y_slicer)
                + _kpis(pares, marca, y_kpi, None, metas, fecha))
    y0 = y_kpi + ALTO_KPI + 12
    alto_libre = ALTO - y0 - MARGEN
    mitad = (ANCHO - 2 * MARGEN - 12) // 2
    principal = pares[0]

    if fecha:
        visuales.append(visual(
            "lineChart", MARGEN, y0, ANCHO - 2 * MARGEN, alto_libre // 2 - 6,
            medidas=_con_contraparte([principal], universo or []),
            categoria=fecha,
            titulo=f"{principal[1]} en el tiempo", marca=marca))
        y1 = y0 + alto_libre // 2 + 6
        alto_abajo = alto_libre // 2 - 6
    else:
        y1, alto_abajo = y0, alto_libre

    if dims:
        visuales.append(visual(
            "clusteredBarChart", MARGEN, y1, mitad, alto_abajo,
            medidas=[principal], categoria=dims[0],
            titulo=f"{principal[1]} por {dims[0][1]}", marca=marca))
    if len(dims) > 1:
        visuales.append(visual(
            "donutChart", MARGEN + mitad + 12, y1, mitad, alto_abajo,
            medidas=[principal], categoria=dims[1],
            titulo=f"{principal[1]} por {dims[1][1]}", marca=marca))
    elif not dims and not fecha:
        visuales.append(texto(
            MARGEN, y1, ANCHO - 2 * MARGEN, 60,
            "El modelo no tiene dimensiones de texto visibles para graficar; "
            "quedan los KPI.", 11))
    return pagina(titulos[0], visuales, 0, marca)


def _pagina_detalle(titulos, titulo, pares, dims, marca=None,
                    cortes=None, cat=None) -> dict:
    desplazo = ALTO_MARCA - FILA_SLICER + 8 if marca else 0
    y_slicer = FILA_SLICER + desplazo
    visuales = (_barra_nav(titulos, titulos[1], marca)
                + _encabezado(f"{titulo} · Detalle",
                              "Matriz de medidas por dimensión", marca)
                + _fila_slicers(cortes if cortes is not None else dims,
                                None, marca, y_slicer))
    y0 = y_slicer + ALTO_SLICER + 12
    alto_libre = ALTO - y0 - MARGEN
    if dims:
        # El mismo tratamiento que la tabla de un tema: la medida que
        # quedaría constante contra este eje se cambia por su equivalente
        # propia, y la que no tiene equivalente se saca del visual.
        if cat is not None:
            pares = _sin_eje_reemplazadas(cat, pares, dims[0])
            constantes = {n for _t, n in sin_eje(cat, pares, [dims[0]])}
            pares = [par for par in pares if par[1] not in constantes] \
                or pares[:1]
        visuales.append(visual(
            "pivotTable", MARGEN, y0, ANCHO - 2 * MARGEN, alto_libre,
            medidas=pares, categoria=dims[0],
            titulo=f"Medidas por {dims[0][1]}", marca=marca))
    else:
        visuales.append(visual(
            "multiRowCard", MARGEN, y0, ANCHO - 2 * MARGEN, alto_libre,
            medidas=pares, titulo="Medidas", marca=marca))
    return pagina(titulos[1], visuales, 1, marca)


# ==========================================================================
# Páginas escritas por el usuario
#
# Lo automático cubre lo que el dataset dice. Lo que el negocio QUIERE ver
# —una página de cobertura comercial, un ranking propio, la comparación
# que hace el gerente todos los lunes— no está en los datos: está en la
# cabeza de quien pide el informe. Esto le da un lugar donde escribirlo,
# en el mismo vocabulario del informe, y lo agrega a lo generado en vez de
# reemplazarlo.
# ==========================================================================
_CLAVES_TEMA = {
    "titulo": ("pagina", "página", "page", "hoja", "titulo", "título"),
    "kpis": ("kpis", "kpi", "tarjetas", "cards", "indicadores"),
    "linea": ("linea", "línea", "line", "evolucion", "evolución", "tiempo"),
    "barras": ("barras", "bars", "ranking", "bar"),
    "tabla": ("tabla", "table", "matriz", "matrix"),
    "filtros": ("filtros", "filters", "cortes", "slicers"),
}

# La palabra que separa las medidas de la dimensión: «Total Visitas POR
# Especialidad». Es como se dice en los tres idiomas.
_POR = (" por ", " by ", " per ")


def _parte_por(texto: str) -> tuple[str, str]:
    bajo = texto.lower()
    for sep in _POR:
        i = bajo.rfind(sep)
        if i >= 0:
            return texto[:i].strip(), texto[i + len(sep):].strip()
    return texto.strip(), ""


def _resolver_medidas(cat: Catalogo, texto: str,
                      faltan: list[str]) -> list[str]:
    salida = []
    for pedazo in [p.strip() for p in texto.split(",") if p.strip()]:
        m = cat.medida(pedazo) or cat.buscar_medida(pedazo)
        if m:
            salida.append(m["nombre"])
        else:
            faltan.append(pedazo)
    return salida


def _resolver_dimension(cat: Catalogo, texto: str,
                        faltan: list[str]) -> tuple[str, str] | None:
    if not texto:
        return None
    hallada = cat.buscar_columna(texto)
    if hallada:
        return (hallada[0], hallada[1]["nombre"])
    faltan.append(texto)
    return None


def temas_escritos(texto: str, cat: Catalogo) -> tuple[list[dict],
                                                       list[str]]:
    """Convierte lo que el usuario escribió en páginas del tablero.

    El formato es el que alguien escribiría solo, una línea por cosa:

        Página: Cobertura comercial
        KPIs: Total Visitas, Cobertura %
        Línea: Total Visitas
        Barras: Total Visitas por Especialidad
        Tabla: Total Visitas, Cobertura % por Ciudad
        Filtros: Especialidad, Ciudad

    Devuelve `(temas, no_entendidos)`. Cada nombre se resuelve contra el
    catálogo REAL: lo que no existe se devuelve en la segunda lista con el
    texto tal cual se escribió, nunca se inventa una medida ni una
    columna. Es la misma regla del intérprete de transformaciones — y es
    lo que evita que una página pedida a mano salga con visuales rotos.
    """
    temas: list[dict] = []
    faltan: list[str] = []
    actual: dict | None = None
    for linea in (texto or "").splitlines():
        linea = linea.strip()
        if not linea or ":" not in linea:
            continue
        etiqueta, _, valor = linea.partition(":")
        clave = next((k for k, alias in _CLAVES_TEMA.items()
                      if _norm(etiqueta) in {_norm(a) for a in alias}), None)
        valor = valor.strip()
        if clave is None or not valor:
            continue
        if clave == "titulo":
            if actual:
                temas.append(actual)
            actual = {"titulo": valor}
            continue
        if actual is None:
            # Sin «Página:» delante no hay dónde poner esto. Se abre una
            # con el nombre de lo primero que se pidió en vez de perderlo.
            actual = {"titulo": valor.split(",")[0].strip()}
        if clave == "kpis":
            actual["kpis"] = _resolver_medidas(cat, valor, faltan)
        elif clave == "linea":
            elegidas = _resolver_medidas(cat, valor, faltan)
            if elegidas:
                actual["linea"] = elegidas[0]
        elif clave == "barras":
            medidas, dim = _parte_por(valor)
            elegidas = _resolver_medidas(cat, medidas, faltan)
            columna = _resolver_dimension(cat, dim, faltan)
            if elegidas and columna:
                actual["barras"] = (elegidas[0], columna)
        elif clave == "tabla":
            medidas, dim = _parte_por(valor)
            elegidas = _resolver_medidas(cat, medidas, faltan)
            columna = _resolver_dimension(cat, dim, faltan)
            if elegidas:
                actual["tabla"] = {"medidas": elegidas, "por": columna}
        elif clave == "filtros":
            cortes = [_resolver_dimension(cat, p.strip(), faltan)
                      for p in valor.split(",") if p.strip()]
            actual["filtros"] = [c for c in cortes if c]
    if actual:
        temas.append(actual)
    # Una página sin nada adentro no es una página: sería un título solo.
    utiles = [t for t in temas
              if any(t.get(k) for k in ("kpis", "linea", "barras", "tabla"))]
    return utiles, faltan
