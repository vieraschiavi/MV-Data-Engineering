# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · El mapa del modelo, dibujado como lo dibuja Power BI.

Por qué existe este módulo
--------------------------
La versión anterior era un `digraph` de cajas con el nombre de la tabla y un
`20 col · 117 med` adentro. Funcionaba, pero no se parecía en nada a la vista
de modelo de Power BI y no decía lo único que un mapa de relaciones tiene que
decir: QUÉ COLUMNA se une con QUÉ COLUMNA, y de qué lado está el «uno» y de
qué lado el «muchos».

Acá se arma el mismo diagrama con el vocabulario visual de Power BI:

  · cada tabla es una TARJETA con barra de título y sus campos listados;
  · las claves de relación van primero y resaltadas, porque son las que
    explican el diagrama — el resto de las columnas es contexto;
  · la línea sale del campo y llega al campo, no del borde de una caja al
    borde de otra;
  · en cada extremo va la cardinalidad (`1` y `*`), que es lo que convierte
    un dibujo lindo en un diagrama que se puede auditar.

Se hace con etiquetas HTML de Graphviz (`shape=plaintext` + `<TABLE>`), que es
lo que permite las filas por campo y los `PORT` para anclar las aristas.

Vive en `dxl/` y no en `app/app.py` a propósito: devuelve un string DOT, así
que se puede testear sin levantar Streamlit — que es la regla del proyecto.
"""
from __future__ import annotations

# Paleta: la misma del producto, en los tonos que usa la vista de modelo de
# Power BI (barra de título sólida, cuerpo más oscuro, acento ámbar).
FONDO_TARJETA = "#12294a"
BARRA = "#1c3f63"
BARRA_FECHAS = "#2a5c3f"   # la tabla de calendario se distingue de un vistazo
TINTA = "#eaf1fb"
CAMPO = "#c3d3e8"
CLAVE = "#f2b441"
BORDE = "#24456e"
LINEA = "#7f9ec4"
ALERTA = "#e0645c"         # bidireccional: el que rompe los totales

# Cuántas columnas se listan por tarjeta antes de resumir el resto. Un modelo
# real tiene tablas de 40 columnas: dibujarlas todas hace un PNG ilegible y
# lento de renderizar en el navegador. Las claves NUNCA se recortan (van
# aparte, ver `_campos`), así que el diagrama no pierde información: lo que se
# resume es el relleno.
MAX_COLUMNAS = 4


def _esc(texto: str) -> str:
    """Escapa para etiqueta HTML de Graphviz.

    `&` va primero o se re-escaparían los `&amp;` recién puestos. Un nombre de
    columna con `&` o `<` es perfectamente legal en Power BI y sin esto rompe
    el DOT entero — no esa tabla: el DOT entero, y el mapa no se dibuja.
    """
    return (str(texto).replace("&", "&amp;")
                      .replace("<", "&lt;")
                      .replace(">", "&gt;")
                      .replace('"', "&quot;"))


def _id(nombre: str) -> str:
    """Identificador de nodo seguro para DOT (va entre comillas)."""
    return str(nombre).replace('"', '\\"')


def _puerto(columna: str) -> str:
    """PORT de una fila.

    Graphviz sólo acepta alfanuméricos y `_` en un PORT, pero los nombres de
    columna traen espacios, acentos y puntos. Se usa el índice de la columna
    dentro de la tarjeta, que es estable dentro del render y no puede colisionar.
    """
    return columna


def _campos(tabla: dict, claves: set[str]) -> list[tuple[str, bool]]:
    """Los campos a listar: primero las claves, después relleno hasta el tope.

    Devuelve (nombre, es_clave). Las claves van completas siempre — son las
    que el diagrama tiene que poder explicar.
    """
    nombres = [c["nombre"] for c in tabla["columnas"]]
    de_clave = [n for n in nombres if n in claves]
    resto = [n for n in nombres if n not in claves]
    hueco = max(0, MAX_COLUMNAS - len(de_clave))
    return ([(n, True) for n in de_clave] +
            [(n, False) for n in resto[:hueco]])


def _tarjeta(tabla: dict, claves: set[str], es_fechas: bool,
             etiqueta_mas: str) -> str:
    """Una tabla como tarjeta de Power BI: barra de título y campos."""
    barra = BARRA_FECHAS if es_fechas else BARRA
    filas = [
        f'<TR><TD BGCOLOR="{barra}" ALIGN="LEFT" CELLPADDING="7">'
        f'<FONT COLOR="{TINTA}" POINT-SIZE="13"><B>{_esc(tabla["nombre"])}'
        f'</B></FONT></TD></TR>'
    ]

    mostrados = _campos(tabla, claves)
    for nombre, es_clave in mostrados:
        color = CLAVE if es_clave else CAMPO
        # La clave lleva un rombo delante, igual que Power BI marca los campos
        # que participan de una relación.
        marca = "◆ " if es_clave else ""
        filas.append(
            f'<TR><TD PORT="{_esc(_puerto(nombre))}" ALIGN="LEFT" '
            f'CELLPADDING="4"><FONT COLOR="{color}" POINT-SIZE="10">'
            f'{marca}{_esc(nombre)}</FONT></TD></TR>')

    ocultas = len(tabla["columnas"]) - len(mostrados)
    medidas = len(tabla["medidas"])
    pie = []
    if ocultas > 0:
        pie.append(f"+{ocultas} {etiqueta_mas}")
    if medidas:
        pie.append(f"Σ {medidas}")     # Σ: medidas, como en Power BI
    if pie:
        filas.append(
            f'<TR><TD ALIGN="LEFT" CELLPADDING="4">'
            f'<FONT COLOR="{LINEA}" POINT-SIZE="9">{_esc(" · ".join(pie))}'
            f'</FONT></TD></TR>')

    cuerpo = "".join(filas)
    return (f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" '
            f'CELLPADDING="0" BGCOLOR="{FONDO_TARJETA}" COLOR="{BORDE}">'
            f'{cuerpo}</TABLE>>')


def construir(catalogo, etiqueta_mas: str = "más") -> str:
    """DOT del mapa del modelo. `catalogo` es un `dxl.catalogo.Catalogo`.

    `etiqueta_mas` se pasa traducido desde la UI: este módulo no importa i18n
    para poder testearse solo.
    """
    tablas = [t for t in catalogo.tablas if not t["interna"]]
    presentes = {t["nombre"] for t in tablas}
    fechas = (catalogo.tabla_fechas() or {}).get("nombre")

    # Qué columnas participan de alguna relación, por tabla.
    claves: dict[str, set[str]] = {}
    for r in catalogo.relaciones:
        claves.setdefault(r["desde_tabla"], set()).add(r["desde_col"])
        claves.setdefault(r["hacia_tabla"], set()).add(r["hacia_col"])

    lineas = [
        "digraph modelo {",
        '  rankdir=LR;',
        '  bgcolor="transparent";',
        # splines=spline y NO ortho. `ortho` da el ángulo recto de Power BI
        # pero en Graphviz no esquiva los nodos: con 38 relaciones dibujaba
        # las líneas POR ENCIMA de las tarjetas, cruzando los nombres de los
        # campos. Un mapa cuyas líneas tapan el texto que explican no sirve.
        # `spline` rutea alrededor de los nodos.
        '  splines=spline;',
        '  nodesep=0.32; ranksep=2.0;',
        '  node [shape=plaintext, fontname="Segoe UI,Helvetica,Arial"];',
        # labeldistance/labelangle en 0 y el `1`/`*` como label suelto: con
        # los valores por defecto la cardinalidad aterrizaba ENCIMA de la
        # tarjeta, y se leía «SKU1» en vez de «SKU» con un «1» al lado.
        f'  edge [color="{LINEA}", fontcolor="{CLAVE}", fontsize=12, '
        'fontname="Segoe UI,Helvetica,Arial", penwidth=1.5, '
        'arrowsize=0.7, labeldistance=2.6, labelangle=18, labelfontsize=12];',
    ]

    for tb in tablas:
        etiqueta = _tarjeta(tb, claves.get(tb["nombre"], set()),
                            tb["nombre"] == fechas, etiqueta_mas)
        lineas.append(f'  "{_id(tb["nombre"])}" [label={etiqueta}];')

    for r in catalogo.relaciones:
        # Una relación puede nombrar una tabla que el catálogo no trae (un
        # .pbix da catálogo parcial). Dibujar una arista contra un nodo que no
        # existe hace que Graphviz lo invente como caja vacía, que es peor que
        # no dibujarla.
        if r["desde_tabla"] not in presentes or r["hacia_tabla"] not in presentes:
            continue

        attrs = [
            # Cardinalidad en los extremos: `desde` es el lado muchos y
            # `hacia` el lado uno, salvo muchos-a-muchos.
            f'taillabel="{"*" if not r["muchos_a_muchos"] else "*"}"',
            f'headlabel="{"*" if r["muchos_a_muchos"] else "1"}"',
        ]
        if r["bidireccional"]:
            attrs.append(f'dir=both color="{ALERTA}" penwidth=2.2')
        if not r["activa"]:
            attrs.append("style=dashed")

        # Los puntos cardinales `:e` y `:w` son lo que saca la línea POR EL
        # BORDE de la tarjeta en vez de nacer en medio del texto. Con
        # rankdir=LR la arista sale por el este y entra por el oeste, así que
        # ni la línea ni su etiqueta de cardinalidad pisan el nombre del campo.
        lineas.append(
            f'  "{_id(r["desde_tabla"])}":"{_esc(_puerto(r["desde_col"]))}":e -> '
            f'"{_id(r["hacia_tabla"])}":"{_esc(_puerto(r["hacia_col"]))}":w'
            f' [{" ".join(attrs)}];')

    lineas.append("}")
    return "\n".join(lineas)
