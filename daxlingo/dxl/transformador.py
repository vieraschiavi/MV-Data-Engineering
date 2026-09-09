# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Transformaciones seguras del modelo.

Cada transformación recibe el TMSL, devuelve una COPIA modificada y la lista
de cambios aplicados — nunca muta el original ni toca el archivo de entrada.
Son los «arreglos automáticos» de las reglas del analizador, más operaciones
de edición (agregar medida, renombrar con propagación).
"""
from __future__ import annotations

import copy
import re
import uuid as _uuid

from .analizador import RE_RUIDO_DAX
from .i18n import IDIOMA_DEFECTO, t as traducir
from .catalogo import _norm
from .modelo import expr_lineas, expr_texto


def _sub_fuera_del_ruido(patron: re.Pattern, repl: str,
                         expr: str) -> tuple[str, int]:
    """Como `patron.subn`, pero sin tocar strings ni comentarios.

    El caso que obligó a esto: una medida con la etiqueta "escala 2/3"
    quedaba convertida en "escala DIVIDE ( 2, 3 )" — el arreglo automático
    reescribía ADENTRO del literal y corrompía el texto que ve el usuario.
    Los tramos de ruido se copian tal cual; la sustitución corre sólo sobre
    el código entre ellos.
    """
    partes: list[str] = []
    pos = total = 0
    for m in RE_RUIDO_DAX.finditer(expr):
        seg, n = patron.subn(repl, expr[pos:m.start()])
        total += n
        partes.append(seg)
        partes.append(m.group(0))
        pos = m.end()
    seg, n = patron.subn(repl, expr[pos:])
    total += n
    partes.append(seg)
    return "".join(partes), total


def _tablas(modelo: dict) -> list[dict]:
    return modelo.get("model", modelo).get("tables", [])


def _medidas(modelo: dict):
    for t in _tablas(modelo):
        for m in t.get("measures", []):
            yield t, m


# ==========================================================================
def aplicar_divide(modelo: dict,
                   idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """
    Reemplaza divisiones «a / b» simples por DIVIDE(a, b) en las medidas.
    Solo convierte los casos inequívocos (operandos simples: referencia,
    número o función cerrada); lo ambiguo se deja y se informa.
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    # Operandos que se convierten sin ambigüedad: referencia, número, función
    # con un nivel de anidado, o grupo entre paréntesis con un nivel adentro.
    #
    # El interior de los paréntesis es `(?:[^()]|\(...\))*` — de a UN carácter
    # — y no `(?:[^()]+|...)*`. Con el `+` adentro de la repetición, un texto
    # se puede partir de muchísimas formas y cuando el match FALLA (no hay
    # «/» después) el motor las prueba todas: con nombres de tabla con
    # espacio («'Proyecto VAR'»), seis medidas de un archivo real tardaban
    # MINUTOS cada una. Con un carácter por vuelta el fallo es lineal.
    operando = (r"(?:\((?:[^()]|\([^()]*\))*\)"
                r"|'[^']+'\[[^\[\]]+\]|[A-Za-z_]\w*\[[^\[\]]+\]|\[[^\[\]]+\]"
                r"|\b[A-Z][A-Z0-9]*\s*\((?:[^()]|\([^()]*\))*\)"
                r"|\d+(?:\.\d+)?)")
    patron = re.compile(f"({operando})\\s*/\\s*({operando})")
    for t, m in _medidas(modelo):
        expr = expr_texto(m.get("expression"))
        nuevo, n = _sub_fuera_del_ruido(patron, r"DIVIDE ( \1, \2 )", expr)
        if n:
            m["expression"] = expr_lineas(nuevo)
            cambios.append(traducir("tr_divide", idioma).format(
                obj=m["name"], n=n))
    return modelo, cambios


def asignar_formatos(modelo: dict,
                     idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Asigna formatString a las medidas que no lo tienen, por heurística."""
    modelo = copy.deepcopy(modelo)
    cambios = []
    for t, m in _medidas(modelo):
        if m.get("formatString"):
            continue
        nombre = _norm(m.get("name", ""))
        expr = expr_texto(m.get("expression")).upper()
        if "%" in nombre or "porcentaje" in nombre or "margen" in nombre \
                or "tasa" in nombre or ("DIVIDE" in expr and "SUM" in expr
                                        and "ALLSELECTED" in expr):
            formato = "0.0 %"
        elif "COUNTROWS" in expr or "DISTINCTCOUNT" in expr \
                or "COUNT" in expr or "RANKX" in expr:
            formato = "#,0"
        elif "promedio" in nombre or "media" in nombre or "precio" in nombre \
                or "ticket" in nombre:
            formato = "#,0.00"
        else:
            formato = "#,0"
        m["formatString"] = formato
        cambios.append(traducir("tr_formato", idioma).format(
            obj=m["name"], formato=formato))
    return modelo, cambios


def ocultar_claves(modelo: dict,
                   idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Oculta las columnas que son lado «muchos» de una relación."""
    modelo = copy.deepcopy(modelo)
    cambios = []
    m = modelo.get("model", modelo)
    claves = {(_norm(r.get("fromTable", "")), _norm(r.get("fromColumn", "")))
              for r in m.get("relationships", [])}
    for t in _tablas(modelo):
        for c in t.get("columns", []):
            if (_norm(t.get("name", "")), _norm(c.get("name", ""))) in claves \
                    and not c.get("isHidden"):
                c["isHidden"] = True
                cambios.append(traducir("tr_oculta_clave", idioma).format(
                    obj=f"{t['name']}[{c['name']}]"))
    return modelo, cambios


def _nueva_tabla_medidas(nombre: str) -> dict:
    """La tabla vacía donde viven los cálculos: una columna oculta y nada
    más. Es lo que hace un modelador para que el panel de campos tenga el
    modelo de un lado y las medidas del otro."""
    return {
        "name": nombre,
        "columns": [{
            "name": "_", "dataType": "string", "isHidden": True,
            "sourceColumn": "_", "summarizeBy": "none",
            "annotations": [{"name": "SummarizationSetBy",
                             "value": "Automatic"}],
        }],
        "partitions": [{
            "name": nombre, "mode": "import",
            "source": {"type": "m", "expression": [
                "let", '    Origen = #table({"_"}, {{""}})',
                "in", "    Origen"]},
        }],
        "measures": [],
    }


def crear_tabla_medidas(modelo: dict, idioma: str = IDIOMA_DEFECTO,
                        nombre: str = "_Medidas") -> tuple[dict, list[str]]:
    """
    Mueve todas las medidas a una tabla de medidas dedicada (la crea si no
    existe). El panel de campos queda con el modelo a un lado y los cálculos
    al otro.

    El idioma va SEGUNDO como en todos los arreglos de ARREGLOS_POR_REGLA:
    el despacho genérico los llama `fn(modelo, idioma)` posicional, y con
    `nombre` en ese lugar la tabla de medidas terminaba llamándose «es».
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    tablas = _tablas(modelo)
    destino = next((t for t in tablas if t.get("name") == nombre), None)
    if destino is None:
        destino = _nueva_tabla_medidas(nombre)
        tablas.append(destino)
        cambios.append(traducir("tr_tabla_medidas_creada", idioma).format(
            nombre=nombre))
    destino.setdefault("measures", [])
    nombres_movidos: set[str] = set()
    for t in tablas:
        if t is destino:
            continue
        movidas = t.pop("measures", [])
        if movidas:
            destino["measures"].extend(movidas)
            nombres_movidos |= {x.get("name", "") for x in movidas}
            cambios.append(traducir("tr_movidas", idioma).format(
                n=len(movidas), origen=t["name"]))

    # Una medida referenciada CON su tabla —'Proyecto VAR'[Porcentaje]— deja
    # de existir en esa tabla apenas se mueve, y Power BI rechaza el modelo
    # al abrirlo. Se dejan sin calificar, que es la forma correcta (y la
    # única estable) de nombrar una medida en DAX. Fuera de strings y
    # comentarios, como todo el resto de las reescrituras.
    if nombres_movidos:
        alternativa = "|".join(re.escape(n) for n in sorted(nombres_movidos))
        patron = re.compile(r"(?:'[^']+'|\b[A-Za-z_]\w*)"
                            rf"\[({alternativa})\]")
        n_total = 0
        for _t, md in _medidas(modelo):
            expr = expr_texto(md.get("expression"))
            nuevo, n = _sub_fuera_del_ruido(patron, r"[\1]", expr)
            if n:
                md["expression"] = expr_lineas(nuevo)
                n_total += n
        for t in tablas:
            for c in t.get("columns", []):
                if not c.get("expression"):
                    continue
                expr = expr_texto(c["expression"])
                nuevo, n = _sub_fuera_del_ruido(patron, r"[\1]", expr)
                if n:
                    c["expression"] = expr_lineas(nuevo)
                    n_total += n
        if n_total:
            cambios.append(traducir("tr_refs_medidas", idioma).format(
                n=n_total))
    return modelo, cambios


def agregar_medida(modelo: dict, nombre: str, dax: str, formato: str = "",
                   descripcion: str = "", tabla: str = "",
                   carpeta: str = "",
                   idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """
    Agrega una medida al modelo. Si no se indica tabla, usa la tabla de
    medidas (creándola si hace falta) o la primera con medidas.
    """
    modelo = copy.deepcopy(modelo)
    tablas = _tablas(modelo)
    if not tablas:
        raise ValueError(traducir("tr_sin_tablas", idioma))

    for _, m in _medidas(modelo):
        if _norm(m.get("name", "")) == _norm(nombre):
            raise ValueError(
                traducir("tr_err_medida_existe", idioma).format(nombre=nombre))

    destino = None
    if tabla:
        destino = next((t for t in tablas
                        if _norm(t.get("name", "")) == _norm(tabla)), None)
        if destino is None:
            raise ValueError(
                traducir("tr_err_tabla_no_existe", idioma).format(tabla=tabla))
    if destino is None:
        destino = next((t for t in tablas
                        if t.get("name", "").lstrip("_").lower()
                        in ("medidas", "measures")), None)
    if destino is None:
        destino = next((t for t in tablas if t.get("measures")), None)
    if destino is None:
        # Sin tabla de medidas y sin ninguna que ya tenga medidas, esto
        # caía en `tablas[0]` — la PRIMERA del modelo, que es la primera
        # hoja del Excel por puro azar. Un dataset que empieza con la hoja
        # «Diccionario» terminaba con las 37 medidas del negocio adentro
        # del glosario. Se crea la tabla de medidas, que es lo que el
        # docstring prometía y lo que haría cualquiera a mano.
        destino = _nueva_tabla_medidas("_Medidas")
        tablas.append(destino)

    medida = {"name": nombre, "expression": expr_lineas(dax)}
    if formato:
        medida["formatString"] = formato
    if descripcion:
        medida["description"] = descripcion
    if carpeta:
        medida["displayFolder"] = carpeta
    destino.setdefault("measures", []).append(medida)
    return modelo, [traducir("tr_medida_agregada", idioma).format(
        nombre=nombre, tabla=destino["name"])]


def renombrar_medida(modelo: dict, actual: str, nuevo: str,
                     idioma: str = IDIOMA_DEFECTO
                     ) -> tuple[dict, list[str]]:
    """Renombra una medida y propaga la referencia [actual] en el resto."""
    modelo = copy.deepcopy(modelo)
    cambios = []
    encontrada = False
    for t, m in _medidas(modelo):
        if m.get("name") == actual:
            m["name"] = nuevo
            encontrada = True
            cambios.append(traducir("tr_renombrada", idioma).format(
                antes=actual, despues=nuevo))
            break
    if not encontrada:
        raise ValueError(
            traducir("tr_err_medida_no_existe", idioma).format(nombre=actual))
    patron = re.compile(r"\[" + re.escape(actual) + r"\]")
    for t, m in _medidas(modelo):
        expr = expr_texto(m.get("expression"))
        nuevo_expr, n = patron.subn(f"[{nuevo}]", expr)
        if n:
            m["expression"] = expr_lineas(nuevo_expr)
            cambios.append(traducir("tr_referencias", idioma).format(
                obj=m["name"], n=n))
    return modelo, cambios


def eliminar_medida(modelo: dict, nombre: str,
                    idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Elimina una medida — se niega si otra medida la referencia."""
    modelo = copy.deepcopy(modelo)
    patron = re.compile(r"\[" + re.escape(nombre) + r"\]")
    usada_por = [m["name"] for _, m in _medidas(modelo)
                 if m.get("name") != nombre
                 and patron.search(expr_texto(m.get("expression")))]
    if usada_por:
        raise ValueError(traducir("tr_err_medida_referenciada", idioma).format(
            nombre=nombre,
            lista=", ".join(f"[{u}]" for u in usada_por)))
    for t in _tablas(modelo):
        antes = len(t.get("measures", []))
        t["measures"] = [m for m in t.get("measures", [])
                         if m.get("name") != nombre]
        if len(t["measures"]) < antes:
            return modelo, [traducir("tr_medida_eliminada", idioma).format(
                nombre=nombre, tabla=t["name"])]
    raise ValueError(
        traducir("tr_err_medida_no_existe", idioma).format(nombre=nombre))


def ocultar_columna(modelo: dict, tabla: str, columna: str,
                    ocultar: bool = True,
                    idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Oculta (o vuelve a mostrar) una columna puntual del modelo."""
    modelo = copy.deepcopy(modelo)
    for t in _tablas(modelo):
        if _norm(t.get("name", "")) != _norm(tabla):
            continue
        for c in t.get("columns", []):
            if _norm(c.get("name", "")) != _norm(columna):
                continue
            obj = f"{t['name']}[{c['name']}]"
            if bool(c.get("isHidden")) == ocultar:
                return modelo, [
                    traducir("tr_col_ya_estaba", idioma).format(obj=obj)]
            if ocultar:
                c["isHidden"] = True
            else:
                # Quitar la clave y no dejar `false` escrito: es como lo
                # escribe Desktop, que solo la anota cuando está oculta.
                c.pop("isHidden", None)
            clave = "tr_col_oculta" if ocultar else "tr_col_visible"
            return modelo, [traducir(clave, idioma).format(obj=obj)]
    raise ValueError(traducir("tr_err_columna_no_existe", idioma).format(
        tabla=tabla, col=columna))


def formato_medida(modelo: dict, nombre: str, formato: str,
                   idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Fija el formatString de una medida puntual (pisa el que tenga)."""
    modelo = copy.deepcopy(modelo)
    for _t, m in _medidas(modelo):
        if _norm(m.get("name", "")) == _norm(nombre):
            m["formatString"] = formato
            return modelo, [traducir("tr_formato", idioma).format(
                obj=m["name"], formato=formato)]
    raise ValueError(
        traducir("tr_err_medida_no_existe", idioma).format(nombre=nombre))


# ==========================================================================
# Patrón seguro de R04: COUNTROWS ( FILTER ( 'T', 'T'[col] <op> literal ) ).
# SOLO este caso se reescribe: la equivalencia exacta —con KEEPFILTERS, ver
# abajo— vale para un predicado simple de columna; cualquier cosa más rica
# (AND, OR, referencias a medidas) se deja como está y se informa.
_RE_FILTER_SIMPLE = re.compile(
    r"COUNTROWS\s*\(\s*FILTER\s*\(\s*"
    r"('?[A-Za-z_][\w ]*'?)\s*,\s*"                     # la tabla
    r"('?[A-Za-z_][\w ]*'?\[[^\[\]]+\])\s*"             # 'T'[col]
    r"(=|<>|<=|>=|<|>)\s*"
    r"(\"(?:[^\"]|\"\")*\"|-?\d+(?:\.\d+)?)"            # literal
    r"\s*\)\s*\)",
    re.IGNORECASE)


def _sub_conservando_strings(patron: re.Pattern, repl: str,
                             expr: str) -> tuple[str, int]:
    """Como `_sub_fuera_del_ruido`, pero los strings SÍ son buscables.

    Hace falta acá y no en DIVIDE: el patrón de R04 tiene que matchear el
    literal del predicado (`[Respuesta] = "SI"`), así que excluir los
    strings lo dejaba ciego — con la otra variante la reescritura nunca
    encontraba nada, y el test lo demostró antes que un usuario.
    Los comentarios siguen afuera: un ejemplo comentado no se reescribe.
    """
    partes: list[str] = []
    pos = total = 0
    buffer = ""

    def volcar():
        nonlocal buffer, total
        seg, n = patron.subn(repl, buffer)
        total += n
        partes.append(seg)
        buffer = ""

    for m in RE_RUIDO_DAX.finditer(expr):
        buffer += expr[pos:m.start()]
        if m.group(0).startswith('"'):
            buffer += m.group(0)      # el string es parte del código buscable
        else:
            volcar()                  # el comentario corta el segmento
            partes.append(m.group(0))
        pos = m.end()
    buffer += expr[pos:]
    volcar()
    return "".join(partes), total


def arreglar_filter_simple(modelo: dict,
                           idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """R04, caso seguro: FILTER sobre la tabla entera con predicado simple.

    `COUNTROWS(FILTER('T','T'[c]="SI"))` pasa a
    `CALCULATE(COUNTROWS('T'), KEEPFILTERS('T'[c]="SI"))`.

    El KEEPFILTERS no es adorno: `CALCULATE(..., 'T'[c]="SI")` a secas
    REEMPLAZA el filtro que el usuario tenga sobre esa columna — con un
    slicer en «NO», el original da 0 y la versión sin KEEPFILTERS daría el
    conteo de «SI». Con KEEPFILTERS los filtros se INTERSECAN, que es
    exactamente lo que hacía el FILTER original, y el motor lo resuelve en
    el storage engine en vez de iterar la tabla.
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    for t, m in _medidas(modelo):
        expr = expr_texto(m.get("expression"))
        nuevo, n = _sub_conservando_strings(
            _RE_FILTER_SIMPLE,
            r"CALCULATE ( COUNTROWS ( \1 ), KEEPFILTERS ( \2 \3 \4 ) )",
            expr)
        if n:
            m["expression"] = expr_lineas(nuevo)
            cambios.append(traducir("tr_filter_simple", idioma).format(
                obj=m["name"], n=n))
    return modelo, cambios


def relaciones_a_una_direccion(modelo: dict,
                               idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """R09: las relaciones bidireccionales pasan a una sola dirección.

    OJO, y la interfaz lo dice antes de aplicarlo: esto CAMBIA el
    cross-filtrado de los visuales que dependían de la vuelta. Es el arreglo
    que la regla recomienda —resolver el caso puntual con CROSSFILTER dentro
    de la medida que lo necesite— pero no es gratis, por eso nunca es
    automático: se elige, sugerencia por sugerencia.
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    # La pata bidireccional de una tabla puente NO se toca: es el arreglo
    # canónico que la propia R10 recomienda (el analizador tampoco la marca).
    puentes = {_norm(t.get("name", "")) for t in _tablas(modelo)
               if t.get("isHidden") and not t.get("measures")
               and t.get("columns")
               and all(c.get("isHidden") for c in t["columns"])}
    for r in modelo.get("model", {}).get("relationships", []):
        if r.get("crossFilteringBehavior") == "bothDirections" \
                and _norm(r.get("toTable", "")) not in puentes:
            del r["crossFilteringBehavior"]
            # `securityFilteringBehavior: bothDirections` (la casilla «Aplicar
            # el filtro de seguridad en ambas direcciones» del RLS) solo es
            # legal si el cross-filtrado también es bidireccional. Dejarla
            # colgada produce un modelo que Analysis Services RECHAZA al
            # abrir: «cannot have SecurityFilterBehavior set to
            # BothDirections when the CrossFilterBehavior is set to
            # OneDirection» — reporte de campo, con el archivo real del
            # cliente, en la pantalla de Power BI Desktop. Se borra la clave
            # (el default es oneDirection), igual que con el cross.
            if r.get("securityFilteringBehavior") == "bothDirections":
                del r["securityFilteringBehavior"]
            cambios.append(traducir("tr_unidireccional", idioma).format(
                desde=f'{r.get("fromTable")}[{r.get("fromColumn")}]',
                hacia=f'{r.get("toTable")}[{r.get("toColumn")}]'))
    return modelo, cambios


def sacar_auto_fecha(modelo: dict,
                     idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """R13: borra las tablas de fecha automáticas y apaga su regeneración.

    Tres cosas, y las tres hacen falta:
      · borrar las `LocalDateTable_*` / `DateTableTemplate_*`;
      · borrar las relaciones y las `variations` que las referencian —
        una variation colgando de una tabla que ya no existe es de lo que
        Power BI rechaza al abrir;
      · poner la annotation `__PBI_TimeIntelligenceEnabled = 0`, porque sin
        eso Desktop las REGENERA al abrir el archivo y el arreglo dura un
        doble clic.
    """
    modelo = copy.deepcopy(modelo)
    m = modelo.get("model", {})
    autos = {t["name"] for t in m.get("tables", [])
             if t.get("name", "").startswith(("LocalDateTable_",
                                              "DateTableTemplate_"))}
    if not autos:
        return modelo, []

    m["tables"] = [t for t in m["tables"] if t["name"] not in autos]
    m["relationships"] = [
        r for r in m.get("relationships", [])
        if r.get("fromTable") not in autos and r.get("toTable") not in autos]
    for t in m["tables"]:
        for c in t.get("columns", []):
            c.pop("variations", None)

    anotaciones = m.setdefault("annotations", [])
    for a in anotaciones:
        if a.get("name") == "__PBI_TimeIntelligenceEnabled":
            a["value"] = "0"
            break
    else:
        anotaciones.append({"name": "__PBI_TimeIntelligenceEnabled",
                            "value": "0"})
    return modelo, [traducir("tr_auto_fecha", idioma).format(
        cuantas=str(len(autos)))]


# Nombres de las columnas del calendario que se crea. Van por idioma de la
# UI: el calendario es contenido NUEVO, así que sale en el idioma en el que
# el usuario trabaja.
_CALENDARIO = {
    "es": {"tabla": "Calendario", "fecha": "Fecha", "anio": "Año",
           "mes": "Mes", "mes_num": "MesNúm", "anio_mes": "AñoMes"},
    "en": {"tabla": "Calendar", "fecha": "Date", "anio": "Year",
           "mes": "Month", "mes_num": "MonthNum", "anio_mes": "YearMonth"},
    "pt": {"tabla": "Calendário", "fecha": "Data", "anio": "Ano",
           "mes": "Mês", "mes_num": "MêsNúm", "anio_mes": "AnoMês"},
}


def _col_calculada(nombre: str, dax: str, tipo: str, **extra) -> dict:
    """Una columna calculada con el idioma completo de Desktop — el mismo
    que el puente de R10: sin lineageTag y las anotaciones, el motor
    descarta la columna al evaluar y el modelo no abre."""
    col = {
        "type": "calculated", "name": nombre, "dataType": tipo,
        "isDataTypeInferred": True,
        "expression": dax,
        "lineageTag": str(_uuid.uuid4()),
        "summarizeBy": "none",
        "annotations": [{"name": "SummarizationSetBy", "value": "User"}],
    }
    col.update(extra)
    return col


# Palabras que delatan qué mide una etiqueta de período. El orden de una
# etiqueta de texto no se puede adivinar de la nada, pero sí se puede leer
# del nombre: «Mes» ordena por el número de mes y «AñoMes» por año×100+mes.
_PALABRAS_MES = ("mes", "month", "mês")
_PALABRAS_ANIO = ("anio", "año", "ano", "year", "aa", "yyyy")


def _palabras(nombre: str) -> set[str]:
    return {p.lower() for p in re.findall(
        r"[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+|[A-ZÁÉÍÓÚÑ]+(?![a-z])|\d+", nombre)}


def _orden_de_etiqueta(nombre: str, ref: str) -> str | None:
    """El DAX que ordena cronológicamente una etiqueta de período."""
    palabras = _palabras(nombre)
    tiene_mes = bool(palabras & set(_PALABRAS_MES))
    tiene_anio = bool(palabras & set(_PALABRAS_ANIO))
    if tiene_mes and tiene_anio:
        return f"YEAR ( {ref} ) * 100 + MONTH ( {ref} )"
    if tiene_mes:
        return f"MONTH ( {ref} )"
    return None


def _hermana_numerica(tabla: dict, nombre: str) -> str | None:
    """La columna numérica que ya ordena a esta etiqueta, si existe.

    `Mes` ↔ `MesNumero` es la pareja más común en un dataset real; usarla
    es mejor que fabricar una columna calculada que dice lo mismo.
    """
    raiz = _norm(nombre)
    for c in tabla.get("columns", []):
        if c.get("dataType") not in ("int64", "double", "decimal"):
            continue
        otra = _norm(c.get("name", ""))
        if otra != raiz and otra.startswith(raiz) and \
                otra[len(raiz):] in ("numero", "num", "nro", "orden",
                                     "number", "order", "n"):
            return c["name"]
    return None


def marcar_calendario(modelo: dict,
                      idioma: str = IDIOMA_DEFECTO) -> tuple[dict,
                                                             list[str]]:
    """Deja lista la tabla de fechas que el modelo YA tiene.

    Un dataset que trae su propia hoja de calendario llega sin nada de lo
    que Power BI necesita para reconocerla: sin `dataCategory = Time`, sin
    clave de fecha y con los meses ordenados alfabéticamente. Así,
    TOTALYTD y SAMEPERIODLASTYEAR devuelven en blanco y abril sale antes
    que enero — el archivo abre y los números están mal, que es la peor
    forma de fallar. Antes esto no lo arreglaba nadie: `agregar_calendario`
    veía que había calendario y se iba sin tocarlo.
    """
    from .catalogo import Catalogo
    modelo = copy.deepcopy(modelo)
    cat = Catalogo.desde_modelo(modelo)
    cal = cat.tabla_fechas()
    if not cal:
        return modelo, []
    cruda = next((t for t in _tablas(modelo)
                  if t.get("name") == cal["nombre"]), None)
    if cruda is None:
        return modelo, []
    fechas = [c for c in cruda.get("columns", [])
              if c.get("dataType") == "dateTime"]
    if not fechas:
        return modelo, []
    clave = fechas[0]
    cambios: list[str] = []
    if cruda.get("dataCategory") != "Time":
        cruda["dataCategory"] = "Time"
        cambios.append(traducir("tr_cal_marcada", idioma).format(
            tabla=cruda["name"]))
    if not clave.get("isKey"):
        clave["isKey"] = True
        cambios.append(traducir("tr_cal_clave", idioma).format(
            columna=f'{cruda["name"]}[{clave["name"]}]'))

    ref = f"'{cruda['name']}'[{clave['name']}]"
    nombres = {c.get("name") for c in cruda.get("columns", [])}
    for col in list(cruda.get("columns", [])):
        if col.get("dataType") != "string" or col.get("sortByColumn"):
            continue
        hermana = _hermana_numerica(cruda, col["name"])
        if hermana:
            col["sortByColumn"] = hermana
            cambios.append(traducir("tr_cal_orden", idioma).format(
                columna=f'{cruda["name"]}[{col["name"]}]', orden=hermana))
            continue
        formula = _orden_de_etiqueta(col["name"], ref)
        if not formula:
            continue
        nuevo = f"{col['name']}Orden"
        if nuevo in nombres:
            continue
        cruda["columns"].append(_col_calculada(
            nuevo, formula, "int64", isHidden=True, formatString="0"))
        nombres.add(nuevo)
        col["sortByColumn"] = nuevo
        cambios.append(traducir("tr_cal_orden", idioma).format(
            columna=f'{cruda["name"]}[{col["name"]}]', orden=nuevo))
    return modelo, cambios


def agregar_calendario(modelo: dict,
                       idioma: str = IDIOMA_DEFECTO) -> tuple[dict,
                                                              list[str]]:
    """R14: crea la tabla calendario que falta y la relaciona con las fechas.

    Una tabla calculada sobre CALENDARAUTO() —que sola abarca todas las
    fechas del modelo—, marcada como tabla de tiempo (dataCategory Time,
    clave en la fecha), con Año/Mes/AñoMes listos para usar y el mes
    ordenado por su número. Se relaciona con la PRIMERA columna de fecha de
    cada tabla; las demás fechas de la misma tabla quedan para relaciones
    inactivas que el usuario decida. Si ya hay calendario, no toca nada.
    """
    from .catalogo import Catalogo
    modelo = copy.deepcopy(modelo)
    cat = Catalogo.desde_modelo(modelo)
    if cat.tabla_fechas():
        # Hay calendario, pero «hay» no es «sirve»: se deja marcado, con
        # su clave y con los meses ordenados por número. Irse sin tocarlo
        # dejaba la inteligencia de tiempo en blanco y los meses
        # alfabéticos, con el archivo abriendo igual.
        modelo, marcas = marcar_calendario(modelo, idioma)
        return modelo, [traducir("tr_cal_ya_hay", idioma).format(
            tabla=cat.tabla_fechas()["nombre"])] + marcas

    con_fecha = []
    for t in _tablas(modelo):
        if t.get("name", "").startswith(("LocalDateTable_",
                                         "DateTableTemplate_")):
            continue
        col = next((c for c in t.get("columns", [])
                    if c.get("dataType") == "dateTime"), None)
        if col is not None:
            con_fecha.append((t["name"], col["name"]))
    if not con_fecha:
        raise ValueError(traducir("tr_cal_sin_fechas", idioma))

    n = _CALENDARIO.get(idioma, _CALENDARIO["es"])
    tabla, fecha = n["tabla"], n["fecha"]
    ref = f"'{tabla}'[{fecha}]"
    calendario = {
        "name": tabla,
        "dataCategory": "Time",
        "lineageTag": str(_uuid.uuid4()),
        "columns": [
            {
                "type": "calculatedTableColumn",
                "name": fecha, "dataType": "dateTime",
                "isKey": True,
                "isNameInferred": True, "isDataTypeInferred": True,
                "sourceColumn": f"[{fecha}]",
                "formatString": "dd/mm/yyyy",
                "lineageTag": str(_uuid.uuid4()),
                "summarizeBy": "none",
                "annotations": [{"name": "SummarizationSetBy",
                                 "value": "User"}],
            },
            # El año va con formato «0»: con separador de miles quedaría
            # «2.024», que no es un año.
            _col_calculada(n["anio"], f"YEAR ( {ref} )", "int64",
                           formatString="0"),
            _col_calculada(n["mes_num"], f"MONTH ( {ref} )", "int64",
                           isHidden=True),
            _col_calculada(n["mes"], f'FORMAT ( {ref}, "MMM" )', "string",
                           sortByColumn=n["mes_num"]),
            # La etiqueta del período con su columna de orden NUMÉRICA.
            # «YYYY-MM» ordena bien alfabéticamente por casualidad del
            # formato; con un orden explícito deja de depender de eso, y
            # es lo que la inteligencia de tiempo espera encontrar.
            _col_calculada(n["anio_mes"] + "Orden",
                           f"YEAR ( {ref} ) * 100 + MONTH ( {ref} )",
                           "int64", isHidden=True, formatString="0"),
            _col_calculada(n["anio_mes"], f'FORMAT ( {ref}, "YYYY-MM" )',
                           "string", sortByColumn=n["anio_mes"] + "Orden"),
        ],
        "partitions": [{
            "name": tabla, "mode": "import",
            "source": {"type": "calculated", "expression": [
                "SELECTCOLUMNS (",
                "    CALENDARAUTO (),",
                f'    "{fecha}", [Date]',
                ")"]},
        }],
    }
    m = modelo.get("model", modelo)
    m.setdefault("tables", []).append(calendario)
    cambios = [traducir("tr_cal_creado", idioma).format(tabla=tabla)]
    for t_nombre, c_nombre in con_fecha:
        m.setdefault("relationships", []).append({
            "name": str(_uuid.uuid4()),
            "fromTable": t_nombre, "fromColumn": c_nombre,
            "toTable": tabla, "toColumn": fecha,
        })
        cambios.append(traducir("tr_cal_relacion", idioma).format(
            desde=f"{t_nombre}[{c_nombre}]", hacia=f"{tabla}[{fecha}]"))
    return modelo, cambios


def formato_columna(modelo: dict, tabla: str, columna: str, formato: str,
                    idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Fija el formatString de una columna puntual (pisa el que tenga)."""
    modelo = copy.deepcopy(modelo)
    for t in _tablas(modelo):
        if _norm(t.get("name", "")) != _norm(tabla):
            continue
        for c in t.get("columns", []):
            if _norm(c.get("name", "")) == _norm(columna):
                c["formatString"] = formato
                return modelo, [traducir("tr_formato", idioma).format(
                    obj=f"{t['name']}[{c['name']}]", formato=formato)]
    raise ValueError(traducir("tr_err_columna_no_existe", idioma).format(
        tabla=tabla, col=columna))


def asignar_formatos_columnas(modelo: dict,
                              idioma: str = IDIOMA_DEFECTO
                              ) -> tuple[dict, list[str]]:
    """R16: formatea las columnas visibles que no tienen formato.

    Fechas → dd/mm/yyyy; decimales → #,0.00; enteros → #,0. Las claves no
    se tocan: un Id con separador de miles («1.234») queda peor que crudo —
    por eso se saltean las columnas de relación y las que se llaman como
    clave.
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    m = modelo.get("model", modelo)
    claves = set()
    for r in m.get("relationships", []):
        claves.add((_norm(r.get("fromTable", "")),
                    _norm(r.get("fromColumn", ""))))
        claves.add((_norm(r.get("toTable", "")),
                    _norm(r.get("toColumn", ""))))
    for t in _tablas(modelo):
        if t.get("name", "").startswith(("LocalDateTable_",
                                         "DateTableTemplate_")):
            continue
        for c in t.get("columns", []):
            if c.get("formatString") or c.get("isHidden") \
                    or t.get("isHidden"):
                continue
            par = (_norm(t.get("name", "")), _norm(c.get("name", "")))
            nombre = _norm(c.get("name", ""))
            if par in claves or "id" in (nombre[:2], nombre[-2:]):
                continue
            tipo = c.get("dataType", "")
            if tipo == "dateTime":
                formato = "dd/mm/yyyy"
            elif tipo in ("double", "decimal"):
                formato = "#,0.00"
            elif tipo == "int64":
                # Un año con separador de miles es «2.024»: no es un año.
                formato = "0" if nombre in ("año", "anio", "ano", "year") \
                    else "#,0"
            else:
                continue
            c["formatString"] = formato
            cambios.append(traducir("tr_formato", idioma).format(
                obj=f"{t['name']}[{c['name']}]", formato=formato))
    return modelo, cambios


# Qué arreglo corre para cada regla cuando el usuario la marca. Es la tabla
# que usa la pestaña Analizador para aplicar SOLO lo elegido.
def puentes_para_m2m(modelo: dict,
                     idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """R10: reemplaza cada relación muchos-a-muchos por una tabla puente.

    El arreglo canónico: una tabla calculada oculta con las claves únicas de
    los dos lados, y dos relaciones muchos-a-uno hacia ella. La pata del lado
    que filtraba lleva `bothDirections` para reproducir EXACTAMENTE el flujo
    de filtro original (en una relación de una dirección filtra el lado
    «uno», así que acá: tabla → puente → la otra tabla). Ni más ni menos
    filtrado que antes — el punto es no cambiar ninguna cifra publicada.
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    m = modelo.get("model", {})
    rels = m.get("relationships", [])
    tablas = _tablas(modelo)
    nombres = {_norm(t.get("name", "")) for t in tablas}

    def _tipo_col(tabla: str, col: str) -> str:
        for t in tablas:
            if _norm(t.get("name", "")) == _norm(tabla):
                for c in t.get("columns", []):
                    if _norm(c.get("name", "")) == _norm(col):
                        return c.get("dataType", "string")
        return "string"

    for r in list(rels):
        if not (r.get("fromCardinality", "many") == "many"
                and r.get("toCardinality", "one") == "many"):
            continue
        ft, fc = r.get("fromTable", ""), r.get("fromColumn", "")
        tt, tc = r.get("toTable", ""), r.get("toColumn", "")
        nombre = base = f"_Puente {fc}"
        i = 2
        while _norm(nombre) in nombres:
            nombre = f"{base} ({i})"
            i += 1
        nombres.add(_norm(nombre))
        # La DAX del puente usa SELECTCOLUMNS y no DISTINCT('T'[c]) directo,
        # y no es estilo: es lo que hace que la relación sobreviva.
        #
        # Una referencia directa de columna conserva el LINAJE, así que la
        # columna que produce `DISTINCT ( UNION ( DISTINCT ( 'T'[c] ) ... ) )`
        # sale nombrada con la forma calificada ('T'[c] — DAX Studio lo
        # muestra literal en el encabezado). El `sourceColumn: "[c]"`
        # declarado no matchea con eso: al evaluar la tabla, el motor
        # descarta la columna declarada, crea la inferida, y la relación
        # queda apuntando a un objeto que ya no existe. Es el error de campo
        # exacto, con el sufijo nuestro en el nombre:
        #
        #   Relationship '..._a' uses an invalid column ID 74.
        #
        # SELECTCOLUMNS fija el nombre de salida a mano — determinístico, y
        # el mismo aunque las dos columnas de origen se llamen distinto (el
        # caso real: «#Cliente» de un lado, «# Cliente» del otro). Pierde el
        # linaje, que para una clave de puente no aporta nada: el filtro
        # viaja por las relaciones.
        fc_lit = fc.replace('"', '""')
        tablas.append({
            "name": nombre, "isHidden": True,
            # Con el lineageTag y el isDataTypeInferred que Power BI Desktop
            # les pone a sus propias tablas calculadas (copiado de un archivo
            # real, no supuesto): en los modelos V3 todos los objetos los
            # llevan.
            "lineageTag": str(_uuid.uuid4()),
            "columns": [{
                "type": "calculatedTableColumn",
                "name": fc, "dataType": _tipo_col(ft, fc),
                "isNameInferred": True, "isDataTypeInferred": True,
                "isHidden": True, "sourceColumn": f"[{fc}]",
                "lineageTag": str(_uuid.uuid4()), "summarizeBy": "none",
                "annotations": [{"name": "SummarizationSetBy",
                                 "value": "User"}],
            }],
            "partitions": [{
                "name": nombre, "mode": "import",
                "source": {"type": "calculated", "expression": [
                    "DISTINCT (",
                    "    UNION (",
                    f'        SELECTCOLUMNS ( \'{ft}\', "{fc_lit}", '
                    f"'{ft}'[{fc}] ),",
                    f'        SELECTCOLUMNS ( \'{tt}\', "{fc_lit}", '
                    f"'{tt}'[{tc}] )",
                    "    )",
                    ")",
                ]},
            }],
        })
        rels.remove(r)
        viejo = r.get("name", "m2m")
        rels.append({"name": f"{viejo}_a", "fromTable": ft, "fromColumn": fc,
                     "toTable": nombre, "toColumn": fc})
        pata_b = {"name": f"{viejo}_b", "fromTable": tt, "fromColumn": tc,
                  "toTable": nombre, "toColumn": fc,
                  "crossFilteringBehavior": "bothDirections"}
        # Si la relación original propagaba el filtro de SEGURIDAD (RLS) en
        # ambas direcciones, la pata bidireccional del puente lo conserva —
        # es la única donde es legal (security both exige cross both; en la
        # pata _a, que queda unidireccional, Analysis Services lo rechaza al
        # abrir). Así el RLS del lado «uno» sigue llegando al otro lado a
        # través del puente. La vuelta (RLS del lado «muchos» hacia el «uno»)
        # no tiene representación legal sin volver todo bidireccional, que es
        # exactamente lo que este arreglo deshace — y perderla acompaña al
        # cambio de topología que el usuario eligió al marcar la casilla.
        if r.get("securityFilteringBehavior") == "bothDirections":
            pata_b["securityFilteringBehavior"] = "bothDirections"
        rels.append(pata_b)
        cambios.append(traducir("tr_puente", idioma).format(
            desde=f"{ft}[{fc}]", hacia=f"{tt}[{tc}]", puente=nombre))
    return modelo, cambios


def borrar_tablas_sueltas(modelo: dict,
                          idioma: str = IDIOMA_DEFECTO
                          ) -> tuple[dict, list[str]]:
    """R12, versión segura: borra SOLO tablas ocultas, sin relaciones, sin
    medidas y que ninguna expresión DAX del modelo menciona.

    Una tabla suelta VISIBLE no se toca — el arreglo correcto ahí es
    relacionarla (sus filtros hoy no filtran nada), no borrarla. Esta
    función limpia el otro caso: la tabla legacy que quedó oculta,
    desconectada y sin un solo uso, ocupando memoria y confundiendo a
    quien abre el modelo.
    """
    modelo = copy.deepcopy(modelo)
    cambios = []
    m = modelo.get("model", {})
    tablas = m.get("tables", [])
    rels = m.get("relationships", [])
    conectadas = ({_norm(r.get("fromTable", "")) for r in rels}
                  | {_norm(r.get("toTable", "")) for r in rels})
    corpus = []
    for t in tablas:
        for md in t.get("measures", []):
            corpus.append(expr_texto(md.get("expression")))
        for c in t.get("columns", []):
            if c.get("expression"):
                corpus.append(expr_texto(c.get("expression")))
        for p in t.get("partitions", []):
            src = p.get("source", {})
            if src.get("type") == "calculated":
                corpus.append(expr_texto(src.get("expression")))
    texto = "\n".join(corpus).lower()
    for t in list(tablas):
        nombre = t.get("name", "")
        if (not t.get("isHidden")
                or nombre.startswith(("LocalDateTable_", "DateTableTemplate_"))
                or _norm(nombre) in conectadas
                or t.get("measures")
                or nombre.lower() in texto):
            continue
        tablas.remove(t)
        cambios.append(traducir("tr_tabla_suelta_borrada", idioma).format(
            nombre=nombre))
    return modelo, cambios


def reapuntar_medidas(obj, movidas: set[str], destino: str = "_Medidas") -> int:
    """Re-apunta en un JSON de reporte las referencias a medidas movidas.

    Un visual nombra la medida por su tabla de origen
    (`Measure.Expression.SourceRef.Entity`): mover las medidas a `_Medidas`
    sin tocar esto deja el reporte con referencias rotas — era el motivo por
    el que el arreglo de R15 no se aplicaba a archivos con reporte. Muta el
    objeto in place y devuelve cuántas referencias corrigió. Los nombres de
    medida son únicos en todo el modelo, así que alcanza con el Property.
    """
    n = 0
    if isinstance(obj, dict):
        for clave, valor in obj.items():
            if (clave == "Measure" and isinstance(valor, dict)
                    and valor.get("Property") in movidas):
                ref = (valor.get("Expression") or {}).get("SourceRef")
                if isinstance(ref, dict) and ref.get("Entity") \
                        and ref["Entity"] != destino:
                    ref["Entity"] = destino
                    n += 1
            n += reapuntar_medidas(valor, movidas, destino)
    elif isinstance(obj, list):
        for x in obj:
            n += reapuntar_medidas(x, movidas, destino)
    return n


ARREGLOS_POR_REGLA = {
    "R01": aplicar_divide,
    "R02": asignar_formatos,
    "R04": arreglar_filter_simple,
    "R08": ocultar_claves,
    "R09": relaciones_a_una_direccion,
    "R10": puentes_para_m2m,
    "R12": borrar_tablas_sueltas,
    "R13": sacar_auto_fecha,
    "R14": agregar_calendario,
    "R20": marcar_calendario,
    "R15": crear_tabla_medidas,
    "R16": asignar_formatos_columnas,
}


def aplicar_elegidos(modelo: dict, reglas: set[str],
                     idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Aplica SOLO los arreglos de las reglas que el usuario marcó.

    Es la versión con consentimiento por sugerencia: la pestaña Analizador
    muestra una casilla por regla y esto corre únicamente lo elegido, en el
    mismo orden seguro de siempre.
    """
    cambios: list[str] = []
    # El orden importa: R09 antes que R10 (primero se apagan las
    # bidireccionales existentes, recién después el puente agrega la SUYA,
    # que tanto la regla como el arreglo de R09 saben respetar); R08 DESPUÉS
    # de R10, porque el puente convierte columnas en claves de relación que
    # también hay que ocultar; R12 con las relaciones ya definitivas; R13
    # (sacar el auto-fecha) antes que R14 (crear el calendario de verdad),
    # para que el calendario nuevo no conviva con las tablas automáticas;
    # R16 al final, con las claves de relación ya definitivas para no
    # formatear un Id; R20 (marcar el calendario que YA hay) junto a R14,
    # que es la otra mitad del mismo problema — uno crea el calendario que
    # falta, el otro deja usable el que vino con el dataset.
    for rid in ["R01", "R02", "R04", "R09", "R10", "R08", "R12", "R13",
                "R14", "R20", "R15", "R16"]:
        if rid in reglas:
            modelo, c = ARREGLOS_POR_REGLA[rid](modelo, idioma)
            cambios += c
    return modelo, cambios


def aplicar_arreglos(modelo: dict, hallazgos: list[dict],
                     idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """
    Aplica en cadena todos los arreglos automáticos que el analizador marcó
    (`auto=True`), en orden seguro. Devuelve el modelo nuevo y el log.
    """
    cambios: list[str] = []
    reglas = {h["regla"] for h in hallazgos if h.get("auto")}
    if "R01" in reglas:
        modelo, c = aplicar_divide(modelo, idioma)
        cambios += c
    if "R02" in reglas:
        modelo, c = asignar_formatos(modelo, idioma)
        cambios += c
    if "R08" in reglas:
        modelo, c = ocultar_claves(modelo, idioma)
        cambios += c
    if "R15" in reglas:
        modelo, c = crear_tabla_medidas(modelo, idioma=idioma)
        cambios += c
    return modelo, cambios
