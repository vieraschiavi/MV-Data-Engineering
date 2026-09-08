# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Intérprete de transformaciones en lenguaje natural.

Convierte pedidos escritos («ocultar la columna IdCliente», «formato
porcentaje para Margen», «renombrar Ventas a Ventas Netas») en un PLAN de
acciones sobre las primitivas de `transformador`. El plan se muestra antes
de aplicar nada: el usuario ve exactamente qué se entendió y sobre qué
objeto real del modelo, y recién ahí confirma.

Dos principios que no se negocian:

- **Nunca adivinar.** Cada nombre se resuelve contra el catálogo real
  (`Catalogo.buscar_medida` / `buscar_columna`); lo que no matchea se lista
  en «no entendí» con el motivo, jamás se inventa un objeto.
- **La IA es opcional y desconfiada.** Sin clave, el intérprete de
  keywords trilingüe (ES/EN/PT) alcanza para los pedidos frecuentes. Con
  clave, la IA solo PROPONE un JSON que acá se valida acción por acción
  contra el registro y el catálogo — una alucinación se descarta, no se
  aplica.

Crear medidas nuevas queda fuera a propósito: eso ya lo hace la pestaña
«Generar DAX» con validación anti-alucinación propia.
"""
from __future__ import annotations

import copy
import json
import re

from . import analizador, empresa, kpis, origenes, periodos
from . import proveedores_ia, tablas, transformador
from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir


# --------------------------------------------------------------------------
# Acciones compuestas: analizar, corregir todo, KPIs. Mismo contrato que
# las primitivas — fn(modelo, idioma) -> (modelo, cambios) — así el plan
# las trata igual. Las que solo INFORMAN devuelven el modelo intacto.
# --------------------------------------------------------------------------
def _analizar_modelo(modelo: dict,
                     idioma: str = IDIOMA_DEFECTO) -> tuple[dict,
                                                            list[str]]:
    """Informe de qué está mal, sin tocar nada."""
    hallazgos = analizador.analizar(Catalogo.desde_modelo(modelo))
    lineas = [traducir("nlp_salud", idioma).format(
        puntos=analizador.puntaje(hallazgos), n=len(hallazgos))]
    for g in analizador.agrupar(hallazgos):
        txt = analizador.describir(g, idioma)
        lineas.append(traducir("nlp_mal", idioma).format(
            que=txt["titulo"], n=len(g["objetos"])))
    if len(lineas) == 1:
        lineas.append(traducir("nlp_sin_problemas", idioma))
    return modelo, lineas


def _corregir_todo(modelo: dict,
                   idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Analiza, aplica TODOS los arreglos automáticos y cuenta las dos
    mitades: qué estaba mal y qué se hizo. Lo que no tiene arreglo
    automático se lista como pendiente en vez de callarse."""
    hallazgos = analizador.analizar(Catalogo.desde_modelo(modelo))
    if not hallazgos:
        return modelo, [traducir("nlp_sin_problemas", idioma)]
    lineas: list[str] = []
    reglas: set[str] = set()
    for g in analizador.agrupar(hallazgos):
        txt = analizador.describir(g, idioma)
        if g["regla"] in transformador.ARREGLOS_POR_REGLA:
            reglas.add(g["regla"])
            lineas.append(traducir("nlp_mal", idioma).format(
                que=txt["titulo"], n=len(g["objetos"])))
        else:
            lineas.append(traducir("nlp_queda_mano", idioma).format(
                que=txt["titulo"]))
    modelo, cambios = transformador.aplicar_elegidos(modelo, reglas, idioma)
    return modelo, lineas + cambios


def _sugerir_kpis(modelo: dict,
                  idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Informe de KPIs sugeridos, sin agregarlos."""
    sugeridos = kpis.sugerir(Catalogo.desde_modelo(modelo), idioma)
    if not sugeridos:
        return modelo, [traducir("kpi_nada", idioma)]
    return modelo, [traducir("nlp_kpi_sugerido", idioma).format(
        nombre=s["nombre"], dax=s["dax"], porque=s["por_que"])
        for s in sugeridos]


def _agregar_diccionario(modelo: dict,
                         idioma: str = IDIOMA_DEFECTO) -> tuple[dict,
                                                                list[str]]:
    """El diccionario de medidas, como tabla del modelo.

    Va DESPUÉS de crear las medidas: documenta lo que hay. Viaja adentro
    del archivo, así que quien lo recibe abre el .pbit y ahí está la
    fórmula de cada medida y por qué está escrita así — sin depender de
    que alguien le mande el informe aparte.
    """
    import copy

    from . import diccionario

    antes = {t.get("name") for t in modelo.get("model", {}).get("tables", [])}
    nuevo = diccionario.agregar(copy.deepcopy(modelo), idioma)
    tablas = nuevo.get("model", {}).get("tables", [])
    creada = next((t for t in tablas if t.get("name") not in antes), None)
    if creada is None:
        return nuevo, []
    filas = len(diccionario.filas(Catalogo.desde_modelo(modelo), idioma))
    return nuevo, [traducir("nlp_diccionario", idioma).format(
        tabla=creada["name"], n=filas)]


def _agregar_ruta(modelo: dict,
                  idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """La ruta de la entidad, con los datos que el modelo ya lleve adentro."""
    from . import ruta as ruta_mod

    return ruta_mod.agregar(modelo, idioma)


def _fijar_empresa(modelo: dict, nombre: str = "",
                   idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """La empresa propia, validada contra los valores reales si los hay."""
    return empresa.elegir(modelo, nombre, idioma=idioma)


def _ver_origenes(modelo: dict,
                  idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Informe de dónde lee cada consulta, marcando las rutas frágiles."""
    encontrados = origenes.detectar(modelo)
    if not encontrados:
        return modelo, [traducir("nlp_sin_origenes", idioma)]
    return modelo, [traducir("nlp_or_linea", idioma).format(
        tabla=o["tabla"], ruta=o["ruta"],
        aviso=f" — {traducir('or_fragil', idioma)}" if o["fragil"] else "")
        for o in encontrados]


def _formatos_todos(modelo: dict,
                    idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """«Asignar formatos» del intérprete cubre medidas Y columnas: es lo
    que la frase pide, aunque el analizador los reporte como dos reglas."""
    modelo, c1 = transformador.asignar_formatos(modelo, idioma)
    modelo, c2 = transformador.asignar_formatos_columnas(modelo, idioma)
    return modelo, c1 + c2

# --------------------------------------------------------------------------
# Registro de acciones: qué primitiva ejecuta cada una y qué argumentos
# acepta. Es también el contrato que se le exige al JSON de la IA — una
# acción o un argumento fuera de este registro se rechaza.
# --------------------------------------------------------------------------
ACCIONES: dict[str, dict] = {
    "ocultar_columna": {
        "fn": transformador.ocultar_columna,
        "args": {"tabla": str, "columna": str, "ocultar": bool},
    },
    "formato_medida": {
        "fn": transformador.formato_medida,
        "args": {"nombre": str, "formato": str},
    },
    "renombrar_medida": {
        "fn": transformador.renombrar_medida,
        "args": {"actual": str, "nuevo": str},
    },
    "eliminar_medida": {
        "fn": transformador.eliminar_medida,
        "args": {"nombre": str},
    },
    "formato_columna": {
        "fn": transformador.formato_columna,
        "args": {"tabla": str, "columna": str, "formato": str},
    },
    "crear_tabla_medidas": {"fn": transformador.crear_tabla_medidas,
                            "args": {}},
    "ocultar_claves": {"fn": transformador.ocultar_claves, "args": {}},
    "asignar_formatos": {"fn": _formatos_todos, "args": {}},
    "aplicar_divide": {"fn": transformador.aplicar_divide, "args": {}},
    "relaciones_a_una_direccion": {
        "fn": transformador.relaciones_a_una_direccion, "args": {}},
    "sacar_auto_fecha": {"fn": transformador.sacar_auto_fecha, "args": {}},
    "agregar_calendario": {"fn": transformador.agregar_calendario,
                           "args": {}},
    "agregar_kpis": {"fn": kpis.agregar_kpis, "args": {}},
    "agregar_comparativos": {"fn": periodos.agregar_comparativos,
                             "args": {}},
    "sugerir_kpis": {"fn": _sugerir_kpis, "args": {}},
    "analizar_modelo": {"fn": _analizar_modelo, "args": {}},
    "corregir_todo": {"fn": _corregir_todo, "args": {}},
    "agregar_diccionario": {"fn": _agregar_diccionario,
                            "args": {}},
    "agregar_ruta": {"fn": _agregar_ruta, "args": {}},
    # Una tabla nueva a partir de un pedido: expresión DAX de tabla,
    # relaciones con lo que existe y medidas. Validada contra el catálogo
    # antes de entrar al plan (dxl/tablas.py).
    # Quién es «nosotros» en el mercado: con esto existe «Share Empresa %».
    "fijar_empresa": {"fn": _fijar_empresa, "args": {"nombre": str}},
    "crear_tabla": {
        "fn": tablas.crear_accion,
        "args": {"nombre": str, "dax": str, "descripcion": str,
                 "relaciones": list, "medidas": list},
    },
    "ver_origenes": {"fn": _ver_origenes, "args": {}},
    "repuntar_origen": {
        "fn": origenes.repuntar,
        "args": {"vieja": str, "nueva": str},
    },
    "buscar_archivos": {
        "fn": origenes.buscar_y_repuntar,
        "args": {"carpeta_raiz": str},
    },
}

# Formatos con nombre: la palabra que la gente dice → el formatString real.
_FORMATOS: list[tuple[tuple[str, ...], str]] = [
    (("porcentaje", "porcentual", "percent", "percentage", "porcentagem",
      "percentual", "%"), "0.0 %"),
    (("moneda", "currency", "moeda", "dolares", "pesos", "reais", "usd",
      "$"), "$ #,0.00"),
    (("decimal", "decimales", "decimais"), "#,0.00"),
    (("entero", "enteros", "integer", "inteiro", "inteiros", "miles",
      "thousands", "milhares"), "#,0"),
    (("fecha", "date", "data"), "dd/mm/yyyy"),
]

_RE_COMILLAS = re.compile(r"""['"«\[]([^'"»\[\]]+)['"»\]]""")


def _sin_comillas(texto: str) -> str:
    m = _RE_COMILLAS.fullmatch(texto.strip())
    return m.group(1).strip() if m else texto.strip()


def _detalle(clave: str, idioma: str, **campos) -> str:
    return traducir(clave, idioma).format(**campos)


# --------------------------------------------------------------------------
# Reglas de intención, en orden: la primera que matchea gana. Los patrones
# corren sobre la línea ORIGINAL (case-insensitive) para no perder el
# casing de los nombres nuevos; la resolución difusa ya es insensible a
# acentos por su cuenta (`catalogo._norm`).
# --------------------------------------------------------------------------
_RE_CORREGIR_TODO = re.compile(
    r"(?:corregir|corregí|arreglar|arreglá|aplicar|aplicá|fix|corrigir"
    r"|apply|conserta)\w*\b.*\b(?:todo|todos|tudo|all|everything)\b"
    r"|\btodo\s+autom[aá]tico", re.I)
_RE_ANALIZAR = re.compile(
    r"\b(?:analiz|revis|analis|analyze|analyse|review|diagnos)\w*"
    r"|qu[eé]\s+est[aá]\s+mal|what'?s\s+wrong|o\s+que\s+est[aá]\s+errado",
    re.I)
_RE_KPI = re.compile(r"\bkpis?\b", re.I)
_RE_ORIGENES = re.compile(
    r"\bor[ií]gen\w*\b|\bsources?\b|\bfontes?\b|\brutas?\b|\bpaths?\b"
    r"|\bcaminhos?\b|de\s+d[oó]nde\s+lee", re.I)
_RE_BUSCAR = re.compile(
    r"(?:buscar|busc[aá]|encontrar|encontr[aá]|find|search|localizar"
    r"|procurar|achar)\w*\b[^\n]*?\b(?:en|in|em|dentro\s+de|bajo|under)\s+"
    r"(?P<x>(?:[A-Za-z]:[\\/]|\\\\|/)[^\n]*)$", re.I)
_RE_REPUNTAR = re.compile(
    r"(?:cambiar|cambi[aá]|mover|move|repuntar|reapuntar|change|mudar"
    r"|trocar|apuntar|apunt[aá]|point)\w*\b[^\n]*?"
    r"(?P<x>(?:[A-Za-z]:[\\/]|\\\\)[^\n]*?)\s*(?:->|→|\ba\b|\bto\b|\bpor\b"
    r"|\bpara\b)\s*(?P<y>(?:[A-Za-z]:[\\/]|\\\\|https?://)[^\n]*)$", re.I)
_RE_AGREGAR = re.compile(
    r"\b(?:agregar|agregá|crear|creá|añadir|poner|armar|generar|add"
    r"|create|criar|adicionar|aplicar|aplicá)\w*", re.I)
_RE_CALENDARIO = re.compile(
    r"\bcalend[aá]r(?:io)?\b|(?:tabla|tabela|table)\s+de\s+"
    r"(?:fechas?|datas?)|date\s+table", re.I)
# Comparativos de período. Cubre las formas en que se pide de verdad:
# «compará YTD contra YTD-1», «mes vs mes año anterior», «que tenga
# trimestres y semestres», «variación interanual».
_RE_COMPARATIVOS = re.compile(
    r"\b(?:comparativ|compar[aá]|interanual|year[\s-]?over[\s-]?year|yoy)\w*"
    r"|(?:vs\.?|versus|contra)\s+(?:el\s+)?(?:mismo\s+)?"
    r"(?:mes|trimestre|semestre|per[ií]odo|a[nñ]o|year|quarter|semester)"
    r"|\bytd\s*(?:vs\.?|versus|contra|-\s*1)"
    r"|\ba[nñ]o\s+anterior\b|\bprevious\s+year\b|\bano\s+anterior\b"
    r"|\b(?:trimestres?\s+y\s+semestres?|semestres?\s+y\s+trimestres?)\b",
    re.I)
_RE_EMPRESA = re.compile(
    r"(?:(?:la\s+)?(?:empresa|compa[nñ][ií]a|corporaci[oó]n|laboratorio"
    r"|firma|company|corporation|empresa\s+propia)\s+"
    r"(?:propia|referente|nuestra|principal|due[nñ]a|own|reference|do\s+"
    r"relat[oó]rio|del\s+informe|of\s+the\s+report)?\s*(?:es|:|=|is|é)"
    r"|\bsomos\b|\bwe\s+are\b|\bn[oó]s\s+somos\b|\bnosotros\s+somos\b)"
    r"\s+(?P<x>.+)$", re.I)
_RE_RUTA = re.compile(
    r"\b(?:ruta|recorrido|trayectoria|itinerario|journey|jornada"
    r"|hcp\s?360|customer\s?360|cliente\s?360|360)\b", re.I)
_RE_ARCHIVOS = re.compile(
    r"\b(?:archivos?|files?|arquivos?|carpetas?|folders?|pastas?"
    r"|or[ií]gen\w*|sources?|fontes?)\b|[A-Za-z]:[\\/]|\\\\|de\s+d[oó]nde",
    re.I)
_RE_CREAR_TABLA = re.compile(
    r"(?:crear|creá|crearías|agregar|agregá|agregarías|añadir|armar"
    r"|generar|nueva|new|create|add|criar|adicionar)\w*\s+"
    r"(?:una\s+|a\s+|uma\s+|la\s+|the\s+)?(?:tabla|table|tabela)\b"
    r"|(?:tabla|table|tabela)\s+(?:adicional|nueva|nova|extra|additional)",
    re.I)
_RE_TABLA_MEDIDAS = re.compile(
    r"(?:tabla|tabela|table)\s+de\s+medidas|measures?\s+table", re.I)
_RE_CLAVES = re.compile(
    r"(?:ocultar|esconder|hide)\b.*\b(?:claves?|keys?|chaves?)\b", re.I)
_RE_DIRECCION = re.compile(
    r"bidireccional|bidirecional|bidirectional"
    r"|una\s+(?:sola\s+)?direcci[oó]n|(?:one|single)\s+direction"
    r"|uma\s+(?:[úu]nica\s+|s[óo]\s+)?dire[cç][aã]o", re.I)
_RE_AUTOFECHA = re.compile(
    r"auto[- ]?(?:fecha|date|data)|fechas?\s+autom|datas?\s+autom"
    r"|date\s?tables?\s+autom|autodate", re.I)
_RE_DIVIDE = re.compile(r"\bdivide\b", re.I)
_RE_FORMATOS_AUTO = re.compile(
    r"(?:asignar|assign|atribuir|poner|dar|aplicar|apply|arreglar|fix)"
    r"\w*\b.*\b(?:formatos|formats)\b", re.I)
_RE_CREAR_MEDIDA = re.compile(
    r"(?:crear|creá|agregar|agregá|añadir|nueva?|create|add|new|criar"
    r"|adicionar)\w*\s+(?:la\s+|a\s+|una\s+|uma\s+)?(?:medida|measure)\b",
    re.I)
_RE_RENOMBRAR = re.compile(
    r"(?:renombr|rename|renomea|renomeie|cambiar\s+el\s+nombre\s+de)\w*\s+"
    r"(?:la\s+)?(?:medida\s+|measure\s+|a\s+medida\s+)?"
    r"(?P<x>.+?)\s+(?:->|→|\ba\b|\bto\b|\bcomo\b|\bpara\b|\bpor\b)\s+"
    r"(?P<y>.+)$", re.I)
_RE_ELIMINAR = re.compile(
    r"(?:eliminar|eliminá|borrar|borrá|delete|remove|excluir|apagar"
    r"|quitar|quitá|sacar|sacá)\w*\s+(?:la\s+)?"
    r"(?:medida|measure|a\s+medida)\s+(?P<x>.+)$", re.I)
_RE_COLUMNA = re.compile(
    r"(?P<verbo>ocultar|ocultá|esconder|hide|mostrar|mostrá|show|unhide"
    r"|exibir)\w*\b.*?\b(?:la\s+|a\s+)?(?:columna|column|coluna)\s+"
    r"(?P<x>.+?)"
    r"(?:\s+(?:de|of|da|do|en|in|na)\s+(?:la\s+)?"
    r"(?:tabla|table|tabela)\s+(?P<t>.+))?$", re.I)
_RE_FORMATO = re.compile(
    r"format\w*|formato", re.I)
_MOSTRAR = ("mostrar", "mostrá", "show", "unhide", "exibir")

# Palabras de relleno que se descartan al aislar el nombre de la medida en
# un pedido de formato: «poner formato porcentaje a la medida Margen».
_RUIDO_FORMATO = frozenset({
    "poner", "pone", "dar", "da", "aplicar", "aplica", "apply", "set",
    "usar", "use", "formato", "format", "formatear", "formatar", "como",
    "as", "a", "en", "in", "de", "of", "la", "el", "the", "para", "for",
    "con", "with", "com", "medida", "measure", "à",
    "columna", "column", "coluna", "tabla", "table", "tabela",
})


def _parsear(linea: str, cat: Catalogo,
             idioma: str,
             modelo: dict | None = None) -> tuple[dict | None, str | None]:
    """
    (item_del_plan, None) si la línea se entendió y resolvió;
    (None, motivo) si no. Motivo vacío = ni siquiera se reconoció el verbo.
    """
    # ---- acciones globales, sin nombres que resolver -------------------
    if _RE_CREAR_MEDIDA.search(linea):
        return None, traducir("nlp_usa_generar", idioma)
    # KPI antes que «corregir todo»: «agregá todos los KPIs» es de KPIs.
    if _RE_KPI.search(linea):
        if _RE_AGREGAR.search(linea):
            return {"accion": "agregar_kpis", "args": {},
                    "detalle": _detalle("nlp_d_kpis_agregar", idioma)}, None
        return {"accion": "sugerir_kpis", "args": {},
                "detalle": _detalle("nlp_d_kpis_sugerir", idioma)}, None
    # «La empresa propia es X» / «somos X»: quién es nosotros en el mercado.
    m = _RE_EMPRESA.search(linea)
    if m:
        nombre = _sin_comillas(m.group("x").strip(" ."))
        valores = empresa.candidatas(modelo) if modelo else []
        real = next((v for v in valores if _norm(v) == _norm(nombre)), None)
        if valores and real is None:
            parecidas = [v for v in valores if _norm(nombre) in _norm(v)]
            if len(parecidas) == 1:
                real = parecidas[0]
            else:
                return None, traducir("em_no_esta", idioma).format(
                    texto=nombre, lista=", ".join(valores[:12]))
        return {"accion": "fijar_empresa", "args": {"nombre": real or nombre},
                "detalle": _detalle("nlp_d_empresa", idioma,
                                    empresa=real or nombre)}, None
    # La ruta de la entidad (journey, HCP360, recorrido de contactos) va
    # ANTES que «orígenes»: «rutas» también quiere decir rutas de archivos,
    # y sin esto «armá la ruta médica» mostraba de dónde lee cada consulta.
    if _RE_RUTA.search(linea) and not _RE_ARCHIVOS.search(linea):
        return {"accion": "agregar_ruta", "args": {},
                "detalle": _detalle("nlp_d_ruta", idioma)}, None
    # Una tabla nueva: se arma con plantilla si el pedido es de los que
    # se resuelven sin IA; si no, se dice qué hace falta en vez de callar.
    if _RE_CREAR_TABLA.search(linea) and not _RE_TABLA_MEDIDAS.search(linea) \
            and not _RE_CALENDARIO.search(linea):
        spec = tablas.plantilla(cat, linea, idioma)
        if spec is None:
            return None, traducir("nlp_tabla_necesita_ia", idioma).format(
                texto=linea.strip())
        errores = tablas.validar(cat, spec["nombre"], spec["dax"],
                                 spec["relaciones"], spec["medidas"], idioma)
        if errores:
            return None, " · ".join(errores)
        return {"accion": "crear_tabla", "args": spec,
                "detalle": tablas.describir(
                    cat, spec["nombre"], spec["dax"], spec["relaciones"],
                    spec["medidas"], idioma)}, None
    # Buscar los archivos que faltan: una sola ruta y el verbo buscar.
    m = _RE_BUSCAR.search(linea)
    if m:
        carpeta = _sin_comillas(m.group("x").strip(" ."))
        return {"accion": "buscar_archivos",
                "args": {"carpeta_raiz": carpeta},
                "detalle": _detalle("nlp_d_buscar", idioma,
                                    carpeta=carpeta)}, None
    # Repuntar antes que «cambiar todo»: una línea con dos rutas es esto.
    m = _RE_REPUNTAR.search(linea)
    if m:
        vieja = _sin_comillas(m.group("x").strip(" ."))
        nueva = _sin_comillas(m.group("y").strip(" ."))
        return {"accion": "repuntar_origen",
                "args": {"vieja": vieja, "nueva": nueva},
                "detalle": _detalle("nlp_d_repuntar", idioma,
                                    antes=vieja, despues=nueva)}, None
    if _RE_ORIGENES.search(linea):
        return {"accion": "ver_origenes", "args": {},
                "detalle": _detalle("nlp_d_origenes", idioma)}, None
    if _RE_CORREGIR_TODO.search(linea):
        return {"accion": "corregir_todo", "args": {},
                "detalle": _detalle("nlp_d_corregir_todo", idioma)}, None
    if _RE_ANALIZAR.search(linea):
        return {"accion": "analizar_modelo", "args": {},
                "detalle": _detalle("nlp_d_analizar", idioma)}, None
    if _RE_TABLA_MEDIDAS.search(linea):
        return {"accion": "crear_tabla_medidas", "args": {},
                "detalle": _detalle("nlp_d_tabla_medidas", idioma)}, None
    if _RE_CLAVES.search(linea):
        return {"accion": "ocultar_claves", "args": {},
                "detalle": _detalle("nlp_d_claves", idioma)}, None
    if _RE_DIRECCION.search(linea):
        return {"accion": "relaciones_a_una_direccion", "args": {},
                "detalle": _detalle("nlp_d_direccion", idioma)}, None
    if _RE_AUTOFECHA.search(linea):
        return {"accion": "sacar_auto_fecha", "args": {},
                "detalle": _detalle("nlp_d_autofecha", idioma)}, None
    # ANTES que el calendario, y no es un detalle: «compará el mismo mes del
    # año anterior usando el calendario» menciona las dos cosas, y lo que
    # el usuario pide es la comparación. Al revés recibía una tabla de
    # fechas y ningún comparativo, sin aviso.
    if _RE_COMPARATIVOS.search(linea):
        return {"accion": "agregar_comparativos", "args": {},
                "detalle": _detalle("nlp_d_comparativos", idioma)}, None
    # Después de auto-fecha: «sacar las tablas de auto-fecha» no es esto.
    if _RE_CALENDARIO.search(linea):
        return {"accion": "agregar_calendario", "args": {},
                "detalle": _detalle("nlp_d_calendario", idioma)}, None
    if _RE_DIVIDE.search(linea):
        return {"accion": "aplicar_divide", "args": {},
                "detalle": _detalle("nlp_d_divide", idioma)}, None
    if _RE_FORMATOS_AUTO.search(linea):
        return {"accion": "asignar_formatos", "args": {},
                "detalle": _detalle("nlp_d_formatos", idioma)}, None

    # ---- renombrar / eliminar medida -----------------------------------
    m = _RE_RENOMBRAR.search(linea)
    if m:
        pedido = _sin_comillas(m.group("x"))
        nuevo = _sin_comillas(m.group("y"))
        medida = cat.buscar_medida(pedido)
        if not medida:
            return None, traducir("nlp_no_medida", idioma).format(
                texto=pedido)
        return {"accion": "renombrar_medida",
                "args": {"actual": medida["nombre"], "nuevo": nuevo},
                "detalle": _detalle("nlp_d_renombrar", idioma,
                                    antes=medida["nombre"],
                                    despues=nuevo)}, None
    m = _RE_ELIMINAR.search(linea)
    if m:
        pedido = _sin_comillas(m.group("x"))
        medida = cat.buscar_medida(pedido)
        if not medida:
            return None, traducir("nlp_no_medida", idioma).format(
                texto=pedido)
        return {"accion": "eliminar_medida",
                "args": {"nombre": medida["nombre"]},
                "detalle": _detalle("nlp_d_eliminar", idioma,
                                    obj=medida["nombre"])}, None

    # ---- ocultar / mostrar una columna ---------------------------------
    m = _RE_COLUMNA.search(linea)
    if m:
        pedido = _sin_comillas(m.group("x"))
        tabla_pedida = _sin_comillas(m.group("t") or "")
        ocultar = _norm(m.group("verbo")) not in _MOSTRAR
        if tabla_pedida:
            t = cat.tabla(tabla_pedida)
            col = None
            if t:
                objetivo = _norm(pedido)
                col = next((c for c in t["columnas"]
                            if _norm(c["nombre"]) == objetivo), None)
            hallada = (t["nombre"], col) if t and col else None
        else:
            hallada = cat.buscar_columna(pedido)
        if not hallada:
            return None, traducir("nlp_no_columna", idioma).format(
                texto=pedido)
        nombre_t, col = hallada
        obj = f"{nombre_t}[{col['nombre']}]"
        return {"accion": "ocultar_columna",
                "args": {"tabla": nombre_t, "columna": col["nombre"],
                         "ocultar": ocultar},
                "detalle": _detalle(
                    "nlp_d_ocultar" if ocultar else "nlp_d_mostrar",
                    idioma, obj=obj)}, None

    # ---- formato puntual de una medida o una columna -------------------
    if _RE_FORMATO.search(linea):
        es_columna = bool(re.search(r"\b(?:columna|column|coluna)\b",
                                    linea, re.I))
        palabras = re.split(r"[^\w%$]+", linea)
        formato = None
        resto: list[str] = []
        for p in palabras:
            if not p:
                continue
            np = _norm(p)
            elegido = next((f for alias, f in _FORMATOS if np in alias),
                           None)
            if elegido and formato is None:
                formato = elegido
            elif np not in _RUIDO_FORMATO:
                resto.append(p)
        if formato:
            pedido = " ".join(resto).strip()
            if es_columna:
                hallada = cat.buscar_columna(pedido) if pedido else None
                if not hallada:
                    return None, traducir("nlp_no_columna", idioma).format(
                        texto=pedido or linea)
                nombre_t, col = hallada
                return {"accion": "formato_columna",
                        "args": {"tabla": nombre_t,
                                 "columna": col["nombre"],
                                 "formato": formato},
                        "detalle": _detalle(
                            "nlp_d_formato_col", idioma,
                            obj=f"{nombre_t}[{col['nombre']}]",
                            formato=formato)}, None
            medida = cat.buscar_medida(pedido) if pedido else None
            if not medida:
                return None, traducir("nlp_no_medida", idioma).format(
                    texto=pedido or linea)
            return {"accion": "formato_medida",
                    "args": {"nombre": medida["nombre"],
                             "formato": formato},
                    "detalle": _detalle("nlp_d_formato", idioma,
                                        obj=medida["nombre"],
                                        formato=formato)}, None

    return None, ""


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------
def interpretar(texto: str, modelo: dict,
                idioma: str = IDIOMA_DEFECTO
                ) -> tuple[list[dict], list[str]]:
    """
    Texto libre → (plan, no_entendidos). Un pedido por línea o separado
    por «;». Cada item del plan trae la acción, los argumentos ya
    resueltos contra el modelo y una descripción legible para confirmar.
    """
    cat = Catalogo.desde_modelo(modelo)
    plan: list[dict] = []
    no_entendidos: list[str] = []
    for cruda in re.split(r"[\n;]+", texto or ""):
        linea = cruda.strip(" \t.·-•")
        if not linea:
            continue
        item, motivo = _parsear(linea, cat, idioma, modelo)
        if item:
            plan.append(item)
        else:
            no_entendidos.append(f"«{linea}» — {motivo}" if motivo
                                 else f"«{linea}»")
    return plan, no_entendidos


# Las transformaciones automáticas que se OFRECEN como sugerencias, en el
# orden en que conviene aplicarlas. Cada una se prueba en seco sobre una
# copia: si no cambia nada, no se sugiere. Es la lista que el usuario
# aprueba una por una o toda junta desde la pantalla — el ETL automático
# que antes solo corría escondido dentro de «preparar el modelo».
ETL_SUGERIBLE = (
    "sacar_auto_fecha", "agregar_calendario", "ocultar_claves",
    "asignar_formatos", "aplicar_divide", "relaciones_a_una_direccion",
    "crear_tabla_medidas", "agregar_kpis", "agregar_comparativos",
    "agregar_diccionario",
)


def sugerencias_etl(modelo: dict,
                    idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Qué transformaciones automáticas aplican a ESTE modelo, y qué
    harían exactamente.

    Se corre cada acción sobre una copia y se mira si el modelo cambió:
    no hay una segunda lógica de «¿aplica?» que pueda desincronizarse de
    la acción real. Lo que se muestra como «haría esto» es literalmente
    lo que va a pasar al aprobarla. Cada sugerencia sale evaluada sobre
    el modelo ORIGINAL, no encadenada: así el usuario ve qué aporta cada
    una por separado.
    """
    salida: list[dict] = []
    for nombre in ETL_SUGERIBLE:
        accion = ACCIONES.get(nombre)
        if not accion:
            continue
        try:
            nuevo, cambios = accion["fn"](copy.deepcopy(modelo), idioma=idioma)
        except Exception:                             # noqa: BLE001
            continue
        if nuevo == modelo:
            continue
        salida.append({"accion": nombre,
                       "titulo": _detalle(_TITULO_ETL[nombre], idioma),
                       "cambios": cambios, "n": len(cambios)})
    return salida


_TITULO_ETL = {
    "sacar_auto_fecha": "nlp_d_autofecha",
    "agregar_calendario": "nlp_d_calendario",
    "ocultar_claves": "nlp_d_claves",
    "asignar_formatos": "nlp_d_formatos",
    "aplicar_divide": "nlp_d_divide",
    "relaciones_a_una_direccion": "nlp_d_direccion",
    "crear_tabla_medidas": "nlp_d_tabla_medidas",
    "agregar_kpis": "nlp_d_kpis_agregar",
    "agregar_comparativos": "nlp_d_comparativos",
    "agregar_diccionario": "nlp_d_diccionario",
}


def aplicar_plan(modelo: dict, plan: list[dict],
                 idioma: str = IDIOMA_DEFECTO
                 ) -> tuple[dict, list[str], list[str]]:
    """
    Aplica el plan en orden. Un item que falla (p. ej. eliminar una medida
    referenciada) no frena a los demás: su error se devuelve aparte.
    """
    cambios: list[str] = []
    errores: list[str] = []
    for item in plan:
        accion = ACCIONES.get(item.get("accion", ""))
        if not accion:
            errores.append(str(item.get("accion")))
            continue
        try:
            modelo, c = accion["fn"](modelo, **item.get("args", {}),
                                     idioma=idioma)
            cambios.extend(c)
        except ValueError as exc:
            errores.append(str(exc))
    return modelo, cambios, errores


# --------------------------------------------------------------------------
# Camino opcional con IA: la IA propone, el validador dispone.
# --------------------------------------------------------------------------
def _prompt_ia(cat: Catalogo) -> str:
    acciones = {nombre: {arg: tipo.__name__
                         for arg, tipo in spec["args"].items()}
                for nombre, spec in ACCIONES.items()}
    catalogo = {
        "tablas": {t["nombre"]: [c["nombre"] for c in t["columnas"]]
                   for t in cat.tablas if not t["interna"]},
        "medidas": [m["nombre"] for m in cat.medidas()],
    }
    return (
        "Sos un traductor de pedidos a acciones sobre un modelo tabular de "
        "Power BI. Respondé SOLO un array JSON, sin texto alrededor. Cada "
        "elemento: {\"accion\": <nombre>, \"args\": {...}}. Acciones "
        "disponibles y sus argumentos (no existen otras):\n"
        f"{json.dumps(acciones, ensure_ascii=False)}\n"
        "Objetos reales del modelo (no existen otros):\n"
        f"{json.dumps(catalogo, ensure_ascii=False)}\n"
        "Usá los nombres EXACTOS del modelo. Si un pedido no se puede "
        "cumplir con estas acciones u objetos, omitilo. Los formatos "
        "van como formatString de Power BI (p. ej. \"0.0 %\", \"#,0\").\n"
        "Para una TABLA NUEVA (resumen, dimensión derivada, segmentación, "
        "parámetro de escenarios, tabla puente) usá crear_tabla con: "
        "nombre; dax = expresión DAX de TABLA (SUMMARIZECOLUMNS, "
        "ADDCOLUMNS, SELECTCOLUMNS, DATATABLE, GENERATESERIES, VALUES, "
        "FILTER…) que use SOLO tablas, columnas y medidas del catálogo; "
        "descripcion; relaciones = lista de {\"desde_col\": columna de la "
        "tabla nueva, \"hacia_tabla\": tabla existente, \"hacia_col\": su "
        "columna} (o {\"desde_tabla\", \"desde_col\", \"hacia_col\"} si la "
        "nueva es la dimensión); medidas = lista de {\"nombre\", \"dax\", "
        "\"formato\"}. Para la ruta o recorrido de una entidad (visitas, "
        "contactos, journey, 360) usá agregar_ruta: el programa la arma "
        "solo con los datos del modelo."
    )


def _validar_item_ia(bruto, cat: Catalogo, idioma: str,
                     modelo_actual: dict | None = None
                     ) -> tuple[dict | None, str]:
    """Un item propuesto por la IA → item del plan validado, o motivo."""
    if not isinstance(bruto, dict):
        return None, str(bruto)
    nombre = bruto.get("accion", "")
    spec = ACCIONES.get(nombre)
    if not spec:
        return None, str(nombre)
    args = bruto.get("args") or {}
    if not isinstance(args, dict) or set(args) - set(spec["args"]) \
            or any(not isinstance(v, spec["args"][k])
                   for k, v in args.items()):
        return None, f"{nombre}: {args}"

    # Que lo nombrado EXISTA — acá muere la alucinación.
    if nombre == "ocultar_columna":
        tabla, col = args.get("tabla", ""), args.get("columna", "")
        if not cat.existe_columna(tabla, col):
            return None, f"{tabla}[{col}]"
        detalle = _detalle(
            "nlp_d_ocultar" if args.get("ocultar", True) else "nlp_d_mostrar",
            idioma, obj=f"{tabla}[{col}]")
    elif nombre == "formato_columna":
        tabla, col = args.get("tabla", ""), args.get("columna", "")
        if not cat.existe_columna(tabla, col):
            return None, f"{tabla}[{col}]"
        detalle = _detalle("nlp_d_formato_col", idioma,
                           obj=f"{tabla}[{col}]",
                           formato=args.get("formato", ""))
    elif nombre in ("formato_medida", "eliminar_medida"):
        medida = cat.medida(args.get("nombre", ""))
        if not medida:
            return None, args.get("nombre", "")
        args["nombre"] = medida["nombre"]
        detalle = (_detalle("nlp_d_formato", idioma, obj=medida["nombre"],
                            formato=args.get("formato", ""))
                   if nombre == "formato_medida"
                   else _detalle("nlp_d_eliminar", idioma,
                                 obj=medida["nombre"]))
    elif nombre == "buscar_archivos":
        carpeta = args.get("carpeta_raiz", "")
        if not carpeta:
            return None, nombre
        detalle = _detalle("nlp_d_buscar", idioma, carpeta=carpeta)
    elif nombre == "repuntar_origen":
        vieja, nueva = args.get("vieja", ""), args.get("nueva", "")
        if not vieja or not nueva:
            return None, f"{vieja} → {nueva}"
        # Que la carpeta vieja EXISTA entre los orígenes del modelo: si la
        # IA la inventó, el repuntado no haría nada y el usuario creería
        # que sí.
        conocidas = {_norm(c).replace("/", "\\").rstrip("\\")
                     for c in origenes.carpetas(modelo_actual or {})}
        if _norm(vieja).replace("/", "\\").rstrip("\\") not in conocidas:
            return None, vieja
        detalle = _detalle("nlp_d_repuntar", idioma, antes=vieja,
                           despues=nueva)
    elif nombre == "renombrar_medida":
        medida = cat.medida(args.get("actual", ""))
        if not medida or not args.get("nuevo"):
            return None, args.get("actual", "")
        args["actual"] = medida["nombre"]
        detalle = _detalle("nlp_d_renombrar", idioma,
                           antes=medida["nombre"], despues=args["nuevo"])
    elif nombre == "fijar_empresa":
        pedido = (args.get("nombre") or "").strip()
        if not pedido:
            return None, nombre
        valores = empresa.candidatas(modelo_actual or {}) if modelo_actual else []
        real = next((v for v in valores if _norm(v) == _norm(pedido)), None)
        if valores and real is None:
            return None, pedido
        args = {"nombre": real or pedido}
        detalle = _detalle("nlp_d_empresa", idioma, empresa=args["nombre"])
    elif nombre == "crear_tabla":
        errores = tablas.validar(
            cat, args.get("nombre", ""), args.get("dax", ""),
            relaciones=args.get("relaciones"), medidas=args.get("medidas"),
            idioma=idioma)
        if errores:
            return None, f"{args.get('nombre', '')}: " + " · ".join(errores)
        detalle = tablas.describir(
            cat, args.get("nombre", ""), args.get("dax", ""),
            relaciones=args.get("relaciones"), medidas=args.get("medidas"),
            idioma=idioma)
    else:
        clave = _DESCRIPCION_GLOBAL.get(nombre)
        if clave is None:
            # Acción real sin descripción propia: se acepta igual, con
            # su nombre. Antes esto era un KeyError y la acción correcta
            # (`agregar_ruta` para «ruta médica / HCP360») se descartaba
            # como «no entendí».
            detalle = nombre.replace("_", " ")
        else:
            detalle = _detalle(clave, idioma)
        args = {}
    return {"accion": nombre, "args": args, "detalle": detalle}, ""


_DESCRIPCION_GLOBAL = {
    "crear_tabla_medidas": "nlp_d_tabla_medidas",
    "ocultar_claves": "nlp_d_claves",
    "asignar_formatos": "nlp_d_formatos",
    "aplicar_divide": "nlp_d_divide",
    "relaciones_a_una_direccion": "nlp_d_direccion",
    "sacar_auto_fecha": "nlp_d_autofecha",
    "agregar_calendario": "nlp_d_calendario",
    "agregar_kpis": "nlp_d_kpis_agregar",
    "sugerir_kpis": "nlp_d_kpis_sugerir",
    "analizar_modelo": "nlp_d_analizar",
    "corregir_todo": "nlp_d_corregir_todo",
    "ver_origenes": "nlp_d_origenes",
    "agregar_comparativos": "nlp_d_comparativos",
    "agregar_diccionario": "nlp_d_diccionario",
    "agregar_ruta": "nlp_d_ruta",
}


def _json_ia(respuesta: str):
    """El array JSON de la respuesta, tolerando cercos ```json ... ```."""
    texto = respuesta.strip()
    texto = re.sub(r"^```\w*\s*|\s*```$", "", texto)
    inicio, fin = texto.find("["), texto.rfind("]")
    if inicio < 0 or fin <= inicio:
        return []
    try:
        datos = json.loads(texto[inicio:fin + 1])
    except ValueError:
        return []
    return datos if isinstance(datos, list) else []


def interpretar_con_ia(texto: str, modelo: dict,
                       idioma: str = IDIOMA_DEFECTO,
                       proveedor: str = proveedores_ia.PROVEEDOR_DEFECTO,
                       modelo_ia: str = "", api_key: str | None = None,
                       endpoint: str = "") -> tuple[list[dict], list[str]]:
    """
    Como `interpretar`, pero con la IA proponiendo el plan. Todo lo que la
    IA devuelva se valida contra ACCIONES y el catálogo: lo inválido va a
    no_entendidos con la clave `nlp_ia_descartado`, nunca al plan.
    """
    cat = Catalogo.desde_modelo(modelo)
    respuesta = proveedores_ia.consultar(
        [{"role": "user", "content": texto}], sistema=_prompt_ia(cat),
        proveedor=proveedor, modelo=modelo_ia, api_key=api_key,
        endpoint=endpoint)
    plan: list[dict] = []
    no_entendidos: list[str] = []
    for bruto in _json_ia(respuesta):
        item, motivo = _validar_item_ia(bruto, cat, idioma, modelo)
        if item:
            plan.append(item)
        else:
            no_entendidos.append(
                traducir("nlp_ia_descartado", idioma).format(texto=motivo))
    if not plan and not no_entendidos:
        no_entendidos.append(traducir("nlp_nada", idioma))
    return plan, no_entendidos
