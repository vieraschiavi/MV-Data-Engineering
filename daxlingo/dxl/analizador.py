# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Analizador de buenas prácticas del modelo.

Reglas al estilo Best Practice Analyzer (Tabular Editor / Bravo), elegidas por
impacto real: rendimiento, corrección de resultados y mantenibilidad. Cada
hallazgo dice QUÉ objeto, POR QUÉ importa y CÓMO se arregla; las marcadas
`auto=True` las aplica `transformador.py` sin intervención manual.
"""
from __future__ import annotations

import math
import re

from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

SEVERIDADES = ("alta", "media", "baja")


def _h(rid: str, severidad: str, objeto: str, auto: bool = False,
       **datos: str) -> dict:
    """Un hallazgo.

    El TEXTO no vive acá: `rid` («R04») es la clave de i18n y `datos` completa
    los huecos de la plantilla. Antes el título y la explicación eran cadenas
    en español metidas en este archivo, así que la pestaña Analizador salía en
    español aunque la app estuviera en inglés o portugués. Para leerlo en un
    idioma, `describir(h, idioma)`.
    """
    return {"regla": rid, "severidad": severidad, "objeto": objeto,
            "auto": auto, "datos": datos}


# A qué ÁREA de mejora pertenece cada regla: es el vocabulario del usuario
# (DAX, modelado, calendario, transformación, dashboard), no el interno.
# R07 es «transformación» a propósito: su arreglo es bajar el cálculo a
# Power Query. Las reglas RPxx del reporte son todas «dashboard».
AREA_POR_REGLA = {
    "R00": "modelado",
    "R01": "dax", "R02": "dax", "R03": "dax", "R04": "dax", "R05": "dax",
    "R06": "dax",
    "R07": "transformacion",
    "R08": "modelado", "R09": "modelado", "R10": "modelado",
    "R11": "modelado", "R12": "modelado", "R15": "modelado",
    "R16": "modelado",
    "R13": "calendario", "R14": "calendario",
    "R20": "calendario",
    "R18": "dax", "R19": "dax",
    "R17": "transformacion",
}


# Etiquetas de período donde el orden alfabético NO es el cronológico y
# por eso hace falta `sortByColumn`. «Trimestre» y «Semestre» quedan
# afuera a propósito: sus valores son `T1..T4` y `S1/S2`, que ordenan
# bien solos. El caso que rompe es el nombre del mes — «abril» antes que
# «enero»— y cualquier etiqueta que combine año y mes.
_PERIODO = ("mes", "month", "mês")


def _parece_periodo(nombre: str) -> bool:
    """Por PALABRA, no por subcadena: «triMEStre» y «seMEStre» contienen
    «mes» y se colaban en el aviso, que es justo lo contrario de lo que
    hay que decir — esos dos ordenan bien solos."""
    palabras = {p.lower() for p in re.findall(
        r"[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+|[A-ZÁÉÍÓÚÑ]+(?![a-z])|\d+", nombre)}
    if palabras & {"numero", "número", "number", "orden", "order",
                   "nro", "num", "id"}:
        return False
    return bool(palabras & set(_PERIODO))


def area(rid: str, idioma: str = IDIOMA_DEFECTO) -> str:
    """El nombre del área de la regla, en el idioma pedido."""
    clave = AREA_POR_REGLA.get(rid, "dashboard" if rid.startswith("RP")
                               else "modelado")
    return traducir(f"area_{clave}", idioma)


def describir(h: dict, idioma: str = IDIOMA_DEFECTO) -> dict:
    """Título, por qué importa y cómo se arregla, en el idioma pedido."""
    rid = h["regla"]
    datos = h.get("datos") or {}

    def _t(sufijo: str) -> str:
        txt = traducir(f"regla_{rid}{sufijo}", idioma)
        try:
            return txt.format(**datos)
        except (KeyError, IndexError):
            return txt          # plantilla sin hueco, o dato ausente

    return {"titulo": f"{rid} · {_t('')}",
            "detalle": _t("_detalle"), "arreglo": _t("_arreglo")}


# --------------------------------------------------------------------------
# Ruido de una expresión DAX: literales de texto (con «""» como comilla
# escapada) y comentarios de línea o de bloque. Una sola alternación, para
# que gane el que EMPIEZA primero: un «--» adentro de un string es texto, y
# una comilla adentro de un comentario es comentario.
RE_RUIDO_DAX = re.compile(
    r'"(?:[^"]|"")*"'
    r"|/\*.*?\*/"
    r"|//[^\n]*|--[^\n]*",
    re.DOTALL)


def _solo_codigo_dax(expr: str) -> str:
    """La expresión sin strings ni comentarios, para las reglas de sintaxis.

    Sin esto, R01 acusaba de «división con /» a la barra de un formato de
    fecha ("dd/MM/yyyy"), de un comentario o de una etiqueta ("unidades/mes")
    — con severidad alta y marcada como arreglable. El literal se reemplaza
    por «""» y no por vacío para conservar la forma de la expresión.
    """
    return RE_RUIDO_DAX.sub(
        lambda m: '""' if m.group(0).startswith('"') else " ", expr)


RE_CONCATENA = re.compile(r'&\s*"|"\s*&')

# Funciones que devuelven texto SIEMPRE, sin necesidad de concatenar. Es
# la otra forma en que este programa arma una respuesta en palabras («el
# producto con más ventas»): `CONCATENATEX` sobre un `TOPN`. Sin esto,
# esas medidas se trataban como numéricas y terminaban de KPI en una
# tarjeta y de base de comparativos contra el año anterior.
RE_FUNC_TEXTO = re.compile(r"\b(?:CONCATENATEX|COMBINEVALUES)\s*\(", re.I)


def _devuelve_texto(expr: str) -> bool:
    """¿La medida arma una cadena? Se decide por la concatenación.

    Un literal de texto pegado con `&` sólo aparece cuando se está
    construyendo una frase: en una medida numérica los strings son
    máscaras de FORMAT o etiquetas de comparación, y no llevan `&` al
    lado. Conservador a propósito — ante la duda, la medida se trata
    como numérica y la regla sigue aplicando.
    """
    limpio = _sin_comentarios_dax(expr or "")
    return bool(RE_CONCATENA.search(limpio) or RE_FUNC_TEXTO.search(limpio))


def _hereda_texto(expr: str, cat: Catalogo) -> bool:
    """La medida arma texto a través de OTRAS medidas.

    Un `SWITCH` que elige entre cinco lecturas no concatena nada: el
    texto lo devuelven las medidas que llama. Sin mirar un nivel de
    indirección, la regla del formato volvía a reclamarle máscara
    numérica a una medida que devuelve una frase.
    """
    from .catalogo import referencias_dax

    llamadas = [n for n in referencias_dax(expr)["medidas"] if cat.medida(n)]
    if not llamadas:
        return False
    return all(_devuelve_texto(cat.medida(n).get("expresion", ""))
               for n in llamadas)


def es_medida_de_texto(expr: str, cat: Catalogo | None = None) -> bool:
    """¿Esta medida devuelve texto? Directo o a través de las que llama.

    Es lo que hace que ni el analizador (R02) ni el gate de salida le
    reclamen máscara numérica a una conclusión escrita en palabras.
    """
    return _devuelve_texto(expr) or (cat is not None
                                     and _hereda_texto(expr, cat))


def _sin_comentarios_dax(expr: str) -> str:
    """Sólo saca los comentarios; los strings quedan.

    Es la versión para comparar medidas entre sí (R05): dos medidas idénticas
    salvo por un comentario SON duplicadas, pero dos que difieren en un
    literal de texto no.
    """
    return RE_RUIDO_DAX.sub(
        lambda m: m.group(0) if m.group(0).startswith('"') else " ", expr)


# Un filtro de CALCULATE escrito como predicado sobre una columna:
# `Tabla[Col] = "x"` o `Tabla[Col] IN { … }`. Es la forma que PISA el
# contexto exterior — Power BI la expande a ALL(Tabla[Col]) + el filtro.
RE_PREDICADO = re.compile(
    r"'?([A-Za-z_][\w .]*?)'?\s*\[\s*([^\[\]]+?)\s*\]\s*"
    r"(?:=|<>|>=|<=|>|<|\bIN\b)", re.IGNORECASE)
RE_KEEPFILTERS = re.compile(r"\bKEEPFILTERS\s*\(", re.IGNORECASE)
RE_CALCULATE = re.compile(r"\bCALCULATE(?:TABLE)?\s*\(", re.IGNORECASE)


RE_LITERAL = re.compile(r'"((?:[^"]|"")*)"')


# Identificadores entre corchetes, vacíos. Se usa SÓLO donde se busca un
# OPERADOR: los corchetes se conservan para no alterar la forma de la
# expresión, pero su contenido —que es un nombre elegido por una persona y
# puede tener barras, guiones o porcentajes— deja de confundirse con sintaxis.
# No se aplica dentro de `_solo_codigo_dax` porque otras reglas SÍ necesitan
# leer los nombres (qué columna se pisa, por ejemplo).
RE_IDENTIFICADOR = re.compile(r"\[[^\]]*\]")


def _sin_identificadores(codigo: str) -> str:
    return RE_IDENTIFICADOR.sub("[]", codigo)


def _columna_pisada(codigo: str, nombre: str = "",
                    crudo: str = "") -> str:
    """La primera columna que un CALCULATE fija sin KEEPFILTERS, si hay.

    Es el error de DAX más caro de detectar a ojo porque no falla: la
    medida devuelve un número perfectamente plausible y la matriz repite
    ese mismo número en todas las filas. Apareció así — una medida de
    duración media filtrada por canal, en una tabla abierta POR canal, y
    los cuatro canales daban 11,2.

    Sólo se mira dentro de un CALCULATE, y sólo el predicado directo:
    `FILTER` y `REMOVEFILTERS` son decisiones explícitas de quien escribe,
    y `KEEPFILTERS` es exactamente el arreglo.
    """
    if not RE_CALCULATE.search(codigo) or RE_KEEPFILTERS.search(codigo):
        return ""
    limpio = _sin_llamadas(codigo, RE_EXPLICITAS)
    m = RE_CALCULATE.search(limpio)
    if not m:
        return ""
    m2 = RE_PREDICADO.search(limpio, m.end())
    if not m2:
        return ""
    # Si el NOMBRE de la medida ya nombra el valor que fija, quien la
    # escribió está aislando esa porción a propósito: «Ventas Adium USD»
    # fija Corporacion = "Adium" y «Visitas Realizadas» fija
    # Estado = "Realizada". Acusarlas era ruido — y ruido de severidad
    # alta, que es peor: tapa los casos reales.
    # La búsqueda del literal va sobre la expresión CRUDA: `codigo` ya
    # viene con los strings vaciados (es lo que necesitan las otras
    # reglas), así que ahí «Adium» era `""` y la excepción no se aplicaba
    # nunca — la medida seguía acusada.
    resto = (crudo or codigo)[max(0, m2.start() - 40):m2.end() + 200]
    palabras = {p.lower() for p in re.findall(r"[\wÁÉÍÓÚÑáéíóúñ]+", nombre)}
    for lit in RE_LITERAL.findall(resto):
        base = lit.strip().lower()
        if base and any(base.startswith(p) or p.startswith(base)
                        for p in palabras if len(p) > 3):
            return ""
    return f"{m2.group(1)}[{m2.group(2)}]"


# Funciones cuyo argumento NO cuenta para R18: quien las escribe está
# decidiendo a mano qué hacer con el contexto, y R04 ya opina sobre
# FILTER. La regla apunta al predicado suelto, que es el que sorprende.
RE_EXPLICITAS = re.compile(
    r"\b(FILTER|REMOVEFILTERS|ALL|ALLEXCEPT|ALLSELECTED|TREATAS)\s*\(",
    re.IGNORECASE)


def _sin_llamadas(codigo: str, cuales: re.Pattern) -> str:
    """El código con las llamadas a esas funciones vaciadas (paréntesis
    balanceados), para poder buscar en lo que queda."""
    salida = codigo
    while (m := cuales.search(salida)):
        i, nivel = m.end(), 1
        while i < len(salida) and nivel:
            nivel += (salida[i] == "(") - (salida[i] == ")")
            i += 1
        salida = salida[:m.start()] + " " * (i - m.start()) + salida[i:]
    return salida


# La familia de funciones que desplaza un año atrás, y la huella de la
# guardia que hace comparable esa comparación.
RE_DESPLAZA_ANO = re.compile(
    r"\bSAMEPERIODLASTYEAR\s*\(|\bPARALLELPERIOD\s*\([^)]*YEAR|"
    r"\bDATEADD\s*\([^)]*YEAR", re.IGNORECASE)
# Las dos formas válidas de no caer en la trampa del año incompleto:
#   · contar los días de cada lado y devolver BLANK si no coinciden, o
#   · recortar las dos puntas a la ventana comparable, corriendo con
#     DATEADD las fechas del año anterior que sí existen.
# La segunda es la que genera este programa —da un número en vez de una
# columna vacía—, pero la primera sigue siendo correcta y hay modelos que
# la usan, así que ninguna de las dos se denuncia.
RE_GUARDIA = re.compile(
    r"\bCOUNTROWS\s*\(\s*VALUES\s*\(|\bDATEADD\s*\(", re.IGNORECASE)


def _cadena_dax(cat: Catalogo, nombre: str,
                vistas: set[str] | None = None) -> str:
    """El DAX de la medida más el de todas las que llama, concatenado."""
    from .catalogo import referencias_dax

    vistas = vistas if vistas is not None else set()
    if nombre in vistas:
        return ""
    vistas.add(nombre)
    m = cat.medida(nombre)
    if not m:
        return ""
    expr = m.get("expresion") or ""
    partes = [expr]
    for otra in referencias_dax(expr)["medidas"]:
        partes.append(_cadena_dax(cat, otra, vistas))
    return "\n".join(partes)


def _var_sin_guardia(cat: Catalogo, nombre: str, codigo: str) -> bool:
    """Una variación interanual que no se niega a responder.

    `SAMEPERIODLASTYEAR` devuelve sólo las fechas que EXISTEN en el
    calendario. Si el modelo arranca a mitad de la serie, el período
    desplazado queda corto y la medida compara dieciocho meses contra
    seis: en pantalla apareció un +211 % que era puro artefacto — la
    comparación honesta del mismo tramo daba +9,7 %.

    El DAX no está mal escrito; lo que falta es la guardia que cuenta los
    días de cada lado y devuelve BLANK cuando no coinciden. Una celda
    vacía dice «no comparable»; un número inflado dice una mentira con
    cara de dato.
    """
    # Sólo las medidas que expresan un CAMBIO: un valor del año anterior
    # a secas está perfecto sin guardia, es la resta la que engaña.
    es_var = ("DIVIDE" in codigo.upper() and "-" in codigo) or \
        re.match(r"\s*(var|delta|dif)\b", nombre, re.IGNORECASE)
    if not es_var:
        return False
    cadena = _cadena_dax(cat, nombre)
    return bool(RE_DESPLAZA_ANO.search(cadena)) and \
        not RE_GUARDIA.search(cadena)


RE_DIVISION = re.compile(r"[\w\)\]]\s*/\s*[\w\(\[']")
RE_IFERROR = re.compile(r"\bIFERROR\s*\(", re.IGNORECASE)
RE_FILTER_TABLA = re.compile(r"\bFILTER\s*\(\s*'?([A-Za-z_][\w ]*)'?\s*,",
                             re.IGNORECASE)
RE_VALUES_ESCALAR = re.compile(r"\bIF\s*\(\s*HASONEVALUE", re.IGNORECASE)


def analizar(cat: Catalogo,
             usadas_por_el_reporte: set[str] | None = None) -> list[dict]:
    """Corre todas las reglas y devuelve los hallazgos ordenados por severidad.

    `usadas_por_el_reporte` son los nombres de tabla que algún visual pone
    en un eje. Sirve para R12: una tabla sin relaciones que un visual usa
    NO está suelta —es una tabla de eje desconectada a propósito, como la
    que lista las páginas de un diccionario de medidas—, y acusarla manda
    a borrar justo lo que sostiene la página. Sin el layout a mano el
    comportamiento es el de siempre.
    """
    hallazgos: list[dict] = []
    if cat.parcial:
        hallazgos.append(_h("R00", "media", "(modelo)"))
        return hallazgos

    hallazgos += _reglas_medidas(cat)
    hallazgos += _reglas_columnas(cat)
    hallazgos += _reglas_relaciones(cat)
    hallazgos += _reglas_modelo(cat, usadas_por_el_reporte)

    orden = {s: i for i, s in enumerate(SEVERIDADES)}
    hallazgos.sort(key=lambda x: (orden.get(x["severidad"], 9), x["regla"]))
    return hallazgos


# --------------------------------------------------------------------------
def _reglas_medidas(cat: Catalogo) -> list[dict]:
    out = []
    vistas: dict[str, str] = {}
    for m in cat.medidas():
        nombre, expr = m["nombre"], m["expresion"]
        objeto = f"[{nombre}]"
        # Las reglas de sintaxis miran el CÓDIGO, no los strings ni los
        # comentarios: la barra de "dd/MM/yyyy" no es una división.
        codigo = _solo_codigo_dax(expr)

        # La barra se busca sobre el código SIN los identificadores entre
        # corchetes. Un nombre de medida o de columna puede tener una barra
        # perfectamente legítima —«RCS promedio (miles/ml)», «Litros/vaca»— y
        # sin esto R01 acusaba de «división con /» a una expresión que usa
        # DIVIDE() correctamente, sólo porque el nombre al que se refiere tiene
        # una unidad adentro. Es el mismo falso positivo que ya se había
        # arreglado para los literales de texto ("dd/MM/yyyy"), en el otro
        # lugar donde una barra no es un operador.
        if RE_DIVISION.search(_sin_identificadores(codigo)):
            out.append(_h("R01", "alta", objeto, auto=True))

        # Una medida que devuelve TEXTO no tiene formato numérico, y
        # exigírselo era un falso positivo que además bajaba la salud del
        # modelo: las lecturas del informe («mejora 12,4 % contra el año
        # anterior») son medidas legítimas y sin máscara posible.
        if not m["formato"] and not _devuelve_texto(expr) \
                and not _hereda_texto(expr, cat):
            out.append(_h("R02", "media", objeto, auto=True))

        if RE_IFERROR.search(codigo):
            out.append(_h("R03", "media", objeto))

        # R18: un CALCULATE que fija una columna SIN KEEPFILTERS le pisa el
        # contexto a cualquier visual que use esa misma columna como eje.
        # No da error: da el MISMO número en todas las filas.
        pisada = _columna_pisada(codigo, nombre, expr)
        if pisada:
            out.append(_h("R18", "media", objeto, columna=pisada))

        if _var_sin_guardia(cat, nombre, codigo):
            out.append(_h("R19", "alta", objeto))

        mfil = RE_FILTER_TABLA.search(codigo)
        if mfil and cat.tabla(mfil.group(1)):
            out.append(_h("R04", "media", objeto, tabla=mfil.group(1)))

        clave = re.sub(r"\s+", " ", _sin_comentarios_dax(expr)).strip().lower()
        if clave and clave in vistas:
            out.append(_h("R05", "baja", objeto, medida=vistas[clave]))
        elif clave:
            vistas[clave] = nombre

        if nombre != nombre.strip():
            out.append(_h("R06", "baja", objeto))
    return out


def _reglas_columnas(cat: Catalogo) -> list[dict]:
    out = []
    lados_muchos = {(_norm(r["desde_tabla"]), _norm(r["desde_col"]))
                    for r in cat.relaciones}
    # Cualquiera de los dos extremos de una relación. R07 no castiga a una
    # columna calculada que existe PARA relacionar: es el uso legítimo que
    # la propia regla enumera («filtrar, agrupar o relacionar»), y en los
    # modelos reales es el más común — la clave compuesta
    # `Distribuidor & Canal` que une el hecho con su tabla de objetivos.
    extremos = {(_norm(r["desde_tabla"]), _norm(r["desde_col"]))
                for r in cat.relaciones} | \
               {(_norm(r["hacia_tabla"]), _norm(r["hacia_col"]))
                for r in cat.relaciones}
    for t in cat.tablas:
        if t["interna"]:
            continue
        # Columnas que ordenan a otra (sortByColumn): también uso legítimo —
        # el «Orden SEPA» que existe sólo para que las categorías salgan en
        # el orden del negocio y no alfabético.
        ordenadoras = {_norm(c.get("orden_por", ""))
                       for c in t["columnas"] if c.get("orden_por")}
        for c in t["columnas"]:
            objeto = f"{t['nombre']}[{c['nombre']}]"
            es_clave_rel = (_norm(t["nombre"]), _norm(c["nombre"])) in extremos
            es_ordenadora = _norm(c["nombre"]) in ordenadoras
            # En una tabla calculada (un calendario DAX, un puente) TODAS
            # las columnas derivadas son calculadas por definición: no hay
            # origen al que bajarlas, así que R07 no aplica.
            if c["calculada"] and not es_clave_rel and not es_ordenadora \
                    and not t.get("calculada"):
                out.append(_h("R07", "media", objeto))
            es_clave = ((_norm(t["nombre"]), _norm(c["nombre"])) in lados_muchos
                        or re.search(r"(^id[_ ]|[_ ]id$|^id$)",
                                     _norm(c["nombre"])))
            if es_clave and not c["oculta"] and (
                    (_norm(t["nombre"]), _norm(c["nombre"])) in lados_muchos):
                out.append(_h("R08", "baja", objeto, auto=True))
    return out


def _es_puente(t: dict) -> bool:
    """Tabla puente: oculta, sin medidas, solo columnas clave (ocultas).

    Es la pieza central del arreglo canónico de muchos-a-muchos: claves
    únicas + una pata bidireccional. Ese patrón lo RECOMIENDA la regla R10,
    así que R09 no puede denunciarlo — sería el producto acusando a quien
    aplicó su propio consejo."""
    return (t["oculta"] and not t["medidas"] and t["columnas"]
            and all(c["oculta"] for c in t["columnas"]))


def _reglas_relaciones(cat: Catalogo) -> list[dict]:
    puentes = {_norm(t["nombre"]) for t in cat.tablas if _es_puente(t)}
    out = []
    for r in cat.relaciones:
        objeto = (f"{r['desde_tabla']}[{r['desde_col']}] → "
                  f"{r['hacia_tabla']}[{r['hacia_col']}]")
        if r["bidireccional"] and _norm(r["hacia_tabla"]) not in puentes:
            out.append(_h("R09", "alta", objeto))
        if r["muchos_a_muchos"]:
            out.append(_h("R10", "alta", objeto))
        if not r["activa"]:
            out.append(_h("R11", "baja", objeto))
    return out


def _reglas_modelo(cat: Catalogo,
                   usadas_por_el_reporte: set[str] | None = None
                   ) -> list[dict]:
    out = []
    visibles = [t for t in cat.tablas if not t["interna"]]

    conectadas = set()
    for r in cat.relaciones:
        conectadas.add(_norm(r["desde_tabla"]))
        conectadas.add(_norm(r["hacia_tabla"]))
    # Una tabla sin relaciones que alguna DAX consume directo NO está
    # suelta: es una tabla de línea base o de parámetros, desconectada a
    # propósito. En un archivo real, la «tabla suelta» era el denominador
    # de una medida — DIVIDE ( ..., DISTINCTCOUNT ( 'la suelta'[Nombre] ) )
    # — y R12 pedía revisarla como si nadie la usara.
    corpus = "\n".join(
        [m["expresion"] for t in cat.tablas for m in t["medidas"]]
        + [c["expresion"] for t in cat.tablas for c in t["columnas"]
           if c["calculada"]]).lower()
    for t in visibles:
        solo_medidas = t["medidas"] and all(
            c["oculta"] for c in t["columnas"]) or not t["columnas"]
        en_el_reporte = _norm(t["nombre"]) in {
            _norm(x) for x in (usadas_por_el_reporte or set())}
        if len(visibles) > 1 and _norm(t["nombre"]) not in conectadas \
                and not solo_medidas and t["nombre"].lower() not in corpus \
                and not en_el_reporte:
            out.append(_h("R12", "media", t["nombre"]))

    if any(t["interna"] for t in cat.tablas):
        out.append(_h("R13", "media", "(modelo)"))

    cal = cat.tabla_fechas()
    if not cal and any(
            c["tipo"] == "dateTime" for t in visibles for c in t["columnas"]):
        out.append(_h("R14", "media", "(modelo)", auto=True))
    # R20: hay calendario y NO sirve. Que exista una tabla de fechas no
    # alcanza: sin `dataCategory = Time` ni clave de fecha, TOTALYTD y
    # SAMEPERIODLASTYEAR devuelven en blanco, y sin `sortByColumn` los
    # meses salen alfabéticos —abril antes que enero—. Un dataset que
    # trae su propia hoja de calendario llega siempre así, y el archivo
    # abre igual: los números están mal sin que nada avise.
    if cal:
        sin_marca = not cal["es_calendario"]
        sin_clave = not any(c["tipo"] == "dateTime" and c.get("clave")
                            for c in cal["columnas"])
        sin_orden = [c["nombre"] for c in cal["columnas"]
                     if c["tipo"] == "string" and not c.get("orden_por")
                     and _parece_periodo(c["nombre"])]
        if sin_marca or sin_clave or sin_orden:
            out.append(_h("R20", "media", cal["nombre"], auto=True))

    # R16: columnas visibles sin formato. Una fecha cruda o un importe sin
    # separador de miles se ve en CADA visual que la use; formatearla en el
    # modelo la arregla en todos a la vez. Las claves no cuentan: un Id con
    # «#,0» queda peor que crudo.
    claves = {(_norm(r["desde_tabla"]), _norm(r["desde_col"]))
              for r in cat.relaciones} | \
             {(_norm(r["hacia_tabla"]), _norm(r["hacia_col"]))
              for r in cat.relaciones}
    for t in visibles:
        if t["oculta"]:
            continue
        for c in t["columnas"]:
            nombre = _norm(c["nombre"])
            if c["oculta"] or c["formato"] \
                    or (_norm(t["nombre"]), nombre) in claves \
                    or "id" in (nombre[:2], nombre[-2:]):
                continue
            if c["tipo"] in ("dateTime", "double", "decimal", "int64"):
                out.append(_h("R16", "baja",
                              f"{t['nombre']}[{c['nombre']}]", auto=True))

    con_medidas = [t["nombre"] for t in visibles
                   if t["medidas"] and any(not c["oculta"] for c in t["columnas"])]
    if len(con_medidas) >= 2:
        out.append(_h("R15", "baja", ", ".join(con_medidas[:5]), auto=True))

    # R17: el origen apunta a la carpeta personal de una máquina. El
    # archivo abre igual (los datos están importados) y falla recién al
    # Actualizar, con «No se puede encontrar una parte de la ruta de
    # acceso» — el error más común de campo y el más confuso, porque no
    # tiene nada que ver con el modelo.
    from .origenes import _es_personal, _RE_RUTA
    for t in cat.tablas:
        if t["interna"]:
            continue
        rutas = {m.group(1) for m in _RE_RUTA.finditer(t.get("origen_m", ""))}
        frágiles = sorted(r for r in rutas if _es_personal(r))
        if frágiles:
            out.append(_h("R17", "media", t["nombre"],
                          ruta=frágiles[0]))
    return out


_MAX_DATOS_POR_CLAVE = 5

# Claves cuyo número es «cuántos en total»: al agrupar se SUMAN. Juntarlas
# como nombres daba «Borrar las 2, 1 copias», que además de ilegible esconde
# el único número accionable del renglón — que hay que borrar 3.
_SUMAR = frozenset({"sobran", "cuantas"})


def _juntar(clave: str, lista: list[str]) -> str:
    """Junta los valores de una misma clave de todos los hallazgos del grupo.

    Los nombres se enumeran; los números NO. Un conteo no se enumera porque
    «aparece 3, 2 veces» no es una frase: o se suma (cuántos hay que borrar)
    o se da el rango (en cuántas páginas está repetido).
    """
    if len(lista) <= 1:
        return lista[0] if lista else ""
    numeros = [v for v in lista if v.lstrip("-").isdigit()]
    if len(numeros) == len(lista):
        if clave in _SUMAR:
            return str(sum(int(v) for v in numeros))
        bajo, alto = min(map(int, numeros)), max(map(int, numeros))
        return str(bajo) if bajo == alto else f"{bajo}–{alto}"
    recorte = lista[:_MAX_DATOS_POR_CLAVE]
    # Si los valores ya traen comas adentro (una lista de campos), juntarlos
    # con coma los funde en una sola enumeración donde no se ve dónde termina
    # uno y empieza el otro.
    sep = " · " if any("," in v for v in recorte) else ", "
    texto = sep.join(recorte)
    return texto + "…" if len(lista) > _MAX_DATOS_POR_CLAVE else texto


def agrupar(hallazgos: list[dict]) -> list[dict]:
    """
    Agrupa los hallazgos por regla. Cuarenta medidas sin formato son UN
    problema con cuarenta ocurrencias, no cuarenta problemas: mostrarlos
    sueltos entierra los hallazgos graves debajo del ruido.

    `datos` se junta de TODOS los hallazgos del grupo, no solo del primero:
    si R04 agrupa filtros sobre cinco tablas distintas, el detalle tiene que
    nombrarlas a las cinco (`{tabla}` → "Ventas, Clientes, Pedidos…"), no
    solo la primera con las otras cuatro calladas debajo del «· 5×».
    """
    grupos: dict[str, dict] = {}
    valores: dict[str, dict[str, list[str]]] = {}
    for h in hallazgos:
        g = grupos.setdefault(h["regla"], {
            "regla": h["regla"], "severidad": h["severidad"],
            "datos": {}, "auto": h["auto"], "objetos": [],
        })
        g["objetos"].append(h["objeto"])
        vistos = valores.setdefault(h["regla"], {})
        for clave, valor in (h.get("datos") or {}).items():
            lista = vistos.setdefault(clave, [])
            if valor not in lista:
                lista.append(valor)
    for regla, por_clave in valores.items():
        grupos[regla]["datos"] = {clave: _juntar(clave, lista)
                                  for clave, lista in por_clave.items()}
    orden = {s: i for i, s in enumerate(SEVERIDADES)}
    return sorted(grupos.values(),
                  key=lambda g: (orden.get(g["severidad"], 9), g["regla"]))


def puntaje(hallazgos: list[dict]) -> int:
    """
    Salud del modelo 0-100.

    El castigo se cuenta POR REGLA, no por ocurrencia, y se satura a 3× el
    peso: un modelo con 40 medidas sin formato tiene el mismo problema que
    uno con 5, no ocho veces peor.

    Y la escala tiene rendimiento decreciente: hasta castigo 60 es lineal
    (100 − castigo), y de ahí en más decae en curva continua en vez de
    clavarse en cero. El motivo es un reporte de campo textual — «siempre
    dice 0» — y es cierto: con `100 − castigo` a secas, tres reglas altas
    con tres objetos ya suman 108 y CUALQUIER archivo real arrancaba en 0.
    Un medidor que siempre dice lo mismo no mide: dos archivos mal de
    maneras distintas tienen que dar números distintos, y arreglar la
    mitad de los problemas se tiene que VER en la aguja.
    """
    pesos = {"alta": 12, "media": 5, "baja": 2}
    castigo = 0
    for grupo in agrupar(hallazgos):
        peso = pesos.get(grupo["severidad"], 2)
        castigo += peso * min(len(grupo["objetos"]), 3)
    if castigo <= 60:
        return 100 - castigo
    # Continua en la rodilla (castigo 60 → 40 por las dos ramas) y
    # asintótica a 0: siempre queda pendiente para discriminar.
    return round(40 * math.exp(-(castigo - 60) / 40))
