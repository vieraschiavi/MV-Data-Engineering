# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Una tabla nueva a partir de un pedido escrito.

«¿Qué tabla agregarías para tener un informe más completo?» tiene que
terminar en una tabla DE VERDAD adentro del modelo: con sus columnas,
su expresión (DAX de tabla), sus relaciones con lo que ya existe y sus
medidas — y solo después de que el usuario vio la propuesta y la aceptó.

Dos caminos, un solo validador:

  · **Plantillas** (sin IA): los pedidos frecuentes —una tabla resumen
    por una columna, una tabla de parámetro para escenarios— se arman
    acá, con los objetos reales del catálogo.
  · **IA** (con la clave del usuario): propone la especificación en
    JSON; acá se valida cada referencia contra el catálogo antes de
    entrar al plan. Una tabla que referencia una columna inventada no
    se crea: se dice por qué.

Las columnas de una tabla calculada las declara Desktop al evaluarla,
pero el archivo tiene que traerlas declaradas para que las relaciones y
los visuales las encuentren. Se infieren de la expresión: los pares
«"Nombre", expresión», las columnas de agrupación y las de DATATABLE.
"""
from __future__ import annotations

import copy
import re
import uuid

from .catalogo import Catalogo, _norm, validar_referencias
from .i18n import IDIOMA_DEFECTO, t as traducir

_TIPOS_DATATABLE = {"STRING": "string", "INTEGER": "int64",
                    "DOUBLE": "double", "CURRENCY": "decimal",
                    "DATETIME": "dateTime", "BOOLEAN": "boolean"}
_RE_REF = re.compile(r"^\s*(?:'(?P<t1>[^']+)'|(?P<t2>[A-Za-z_][\w]*))"
                     r"\s*\[(?P<c>[^\]]+)\]\s*$")
_RE_CADENA = re.compile(r'^\s*"(?P<n>(?:[^"]|"")*)"\s*$')
_AGREGA = re.compile(r"\b(?:SUM|SUMX|COUNT|COUNTX|COUNTROWS|DISTINCTCOUNT"
                     r"|AVERAGE|AVERAGEX|MIN|MINX|MAX|MAXX|DIVIDE|CALCULATE"
                     r"|RANKX|PERCENTILE)\w*\s*\(|^\s*\[", re.I)
_TEXTO = re.compile(r"\b(?:FORMAT|CONCATENATE|LEFT|RIGHT|MID|UPPER|LOWER"
                    r"|SUBSTITUTE|TRIM)\s*\(|^\s*\"", re.I)


# ==========================================================================
# Leer una expresión DAX de tabla
# ==========================================================================
def _llamada(dax: str) -> tuple[str, list[str]] | None:
    """`FUNC ( a, b, c )` → ("FUNC", ["a", "b", "c"]) respetando
    paréntesis anidados y cadenas. `None` si no es una llamada."""
    texto = dax.strip()
    m = re.match(r"^([A-Za-z_][\w.]*)\s*\(", texto)
    if not m or not texto.endswith(")"):
        return None
    nombre = m.group(1).upper()
    cuerpo = texto[m.end():-1]
    args: list[str] = []
    actual: list[str] = []
    nivel = 0
    en_cadena = False
    for ch in cuerpo:
        if ch == '"':
            en_cadena = not en_cadena
        if not en_cadena:
            if ch in "({":
                nivel += 1
            elif ch in ")}":
                nivel -= 1
            elif ch == "," and nivel == 0:
                args.append("".join(actual).strip())
                actual = []
                continue
        actual.append(ch)
    if actual or args:
        args.append("".join(actual).strip())
    return nombre, args


def _tipo_de_expresion(expr: str) -> str:
    if _TEXTO.search(expr):
        return "string"
    if _AGREGA.search(expr) or re.match(r"^\s*-?\d", expr):
        return "double"
    return "string"


def _columna_de_ref(cat: Catalogo, ref: str) -> dict | None:
    m = _RE_REF.match(ref)
    if not m:
        return None
    tabla = m.group("t1") or m.group("t2")
    t = cat.tabla(tabla)
    col = m.group("c")
    tipo = "string"
    if t:
        real = next((c for c in t["columnas"]
                     if _norm(c["nombre"]) == _norm(col)), None)
        if real:
            col, tipo = real["nombre"], real.get("tipo") or "string"
    return {"name": col, "dataType": tipo}


def _todas(cat: Catalogo, tabla: str) -> list[dict]:
    t = cat.tabla(tabla.strip().strip("'"))
    if not t:
        return []
    return [{"name": c["nombre"], "dataType": c.get("tipo") or "string"}
            for c in t["columnas"]]


def columnas_de_dax(dax: str, cat: Catalogo) -> list[dict]:
    """Las columnas que va a producir esta expresión de tabla.

    Es una lectura estructural, no una evaluación: alcanza para
    declararlas en el archivo (Desktop confirma los tipos al evaluar) y
    para validar que una relación apunte a una columna que EXISTE.
    """
    salida: list[dict] = []

    def _sumar(col):
        if col and not any(_norm(c["name"]) == _norm(col["name"])
                           for c in salida):
            salida.append(col)

    llamada = _llamada(dax)
    if llamada is None:
        texto = dax.strip()
        if _RE_REF.match(texto):
            _sumar(_columna_de_ref(cat, texto))
        elif texto:
            for c in _todas(cat, texto):
                _sumar(c)
        return salida
    nombre, args = llamada
    if nombre == "GENERATESERIES":
        return [{"name": "Value", "dataType": "double"}]
    if nombre == "DATATABLE":
        for i in range(0, len(args) - 1, 2):
            n, tipo = _RE_CADENA.match(args[i]), args[i + 1].strip().upper()
            if n and tipo in _TIPOS_DATATABLE:
                _sumar({"name": n.group("n").replace('""', '"'),
                        "dataType": _TIPOS_DATATABLE[tipo]})
            else:
                break
        return salida
    if nombre in ("VALUES", "DISTINCT", "ALL", "ALLNOBLANKROW",
                  "ALLSELECTED"):
        for a in args:
            ref = _columna_de_ref(cat, a)
            if ref:
                _sumar(ref)
            else:
                for c in _todas(cat, a):
                    _sumar(c)
        return salida
    if nombre in ("FILTER", "CALCULATETABLE", "UNION", "EXCEPT",
                  "INTERSECT", "SAMPLE"):
        for c in columnas_de_dax(args[0], cat) if args else []:
            _sumar(c)
        return salida
    if nombre == "TOPN" and len(args) > 1:
        for c in columnas_de_dax(args[1], cat):
            _sumar(c)
        return salida
    if nombre in ("SUMMARIZECOLUMNS", "SUMMARIZE", "ADDCOLUMNS",
                  "SELECTCOLUMNS", "GROUPBY", "ROW", "CROSSJOIN",
                  "GENERATE", "NATURALLEFTOUTERJOIN",
                  "NATURALINNERJOIN", "TREATAS"):
        conserva_base = nombre in ("SUMMARIZE", "ADDCOLUMNS", "GROUPBY",
                                   "CROSSJOIN", "GENERATE",
                                   "NATURALLEFTOUTERJOIN",
                                   "NATURALINNERJOIN")
        i = 0
        if nombre in ("SUMMARIZE", "ADDCOLUMNS", "SELECTCOLUMNS", "GROUPBY"):
            if conserva_base and args:
                for c in columnas_de_dax(args[0], cat):
                    _sumar(c)
            i = 1
        while i < len(args):
            a = args[i]
            n = _RE_CADENA.match(a)
            if n and i + 1 < len(args):
                _sumar({"name": n.group("n").replace('""', '"'),
                        "dataType": _tipo_de_expresion(args[i + 1])})
                i += 2
                continue
            ref = _columna_de_ref(cat, a)
            if ref:
                _sumar(ref)
            elif nombre in ("CROSSJOIN", "GENERATE", "NATURALLEFTOUTERJOIN",
                            "NATURALINNERJOIN"):
                for c in columnas_de_dax(a, cat):
                    _sumar(c)
            i += 1
        return salida
    return salida


# ==========================================================================
# Validar la especificación
# ==========================================================================
def validar(cat: Catalogo, nombre: str, dax: str,
            relaciones: list | None = None, medidas: list | None = None,
            idioma: str = IDIOMA_DEFECTO) -> list[str]:
    """Todo lo que impediría crear la tabla, en el idioma del usuario.
    Lista vacía = se puede crear."""
    errores: list[str] = []
    nombre = (nombre or "").strip()
    if not nombre:
        errores.append(traducir("tb_err_nombre", idioma))
    elif cat.tabla(nombre):
        errores.append(traducir("tb_err_existe", idioma).format(tabla=nombre))
    dax = (dax or "").strip()
    if not dax:
        errores.append(traducir("tb_err_dax", idioma))
        return errores
    errores += validar_referencias(dax, cat, idioma)
    columnas = {_norm(c["name"]) for c in columnas_de_dax(dax, cat)}
    if not columnas:
        errores.append(traducir("tb_err_sin_columnas", idioma))
    for r in relaciones or []:
        if not isinstance(r, dict):
            errores.append(traducir("tb_err_relacion", idioma).format(rel=r))
            continue
        propia = r.get("desde_col") if not r.get("desde_tabla") \
            else r.get("hacia_col")
        ajena_t = r.get("hacia_tabla") if not r.get("desde_tabla") \
            else r.get("desde_tabla")
        ajena_c = r.get("hacia_col") if not r.get("desde_tabla") \
            else r.get("desde_col")
        if _norm(propia or "") not in columnas:
            errores.append(traducir("tb_err_col_nueva", idioma).format(
                col=propia, tabla=nombre))
        if not ajena_t or not cat.existe_columna(ajena_t, ajena_c or ""):
            errores.append(traducir("tb_err_col_ajena", idioma).format(
                obj=f"{ajena_t}[{ajena_c}]"))
    for m in medidas or []:
        if not isinstance(m, dict) or not m.get("nombre") or not m.get("dax"):
            errores.append(traducir("tb_err_medida", idioma).format(med=m))
            continue
        if cat.medida(m["nombre"]):
            errores.append(traducir("tb_err_medida_existe", idioma).format(
                med=m["nombre"]))
    return errores


def _con_tabla(cat: Catalogo, nombre: str, columnas: list[dict]) -> Catalogo:
    """Un catálogo que ya conoce la tabla nueva, para validar las medidas
    que la referencian."""
    modelo = {"model": {"tables": [{"name": nombre, "columns": [
        {"name": c["name"], "dataType": c["dataType"]} for c in columnas]}]}}
    nuevo = Catalogo.desde_modelo(modelo)
    nuevo.tablas = cat.tablas + nuevo.tablas
    nuevo.relaciones = list(cat.relaciones)
    return nuevo


# ==========================================================================
# Crear
# ==========================================================================
def crear(modelo: dict, nombre: str, dax: str, descripcion: str = "",
          relaciones: list | None = None, medidas: list | None = None,
          idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Agrega la tabla calculada, sus relaciones y sus medidas.

    La tabla se crea entera o no se crea (los errores de la tabla misma
    son un ValueError). Una relación o una medida que no pasa la
    validación NO frena a las demás: se informa como cambio no aplicado,
    porque una tabla sin una de sus tres relaciones sigue sirviendo y el
    usuario tiene que saber cuál faltó.
    """
    from . import relaciones as rel_mod
    from . import transformador

    cat = Catalogo.desde_modelo(modelo)
    errores = validar(cat, nombre, dax, relaciones=None, medidas=None,
                      idioma=idioma)
    if errores:
        raise ValueError(" · ".join(errores))
    nombre = nombre.strip()
    columnas = columnas_de_dax(dax, cat)
    modelo = copy.deepcopy(modelo)
    tabla = {
        "name": nombre,
        "lineageTag": str(uuid.uuid4()),
        "columns": [{
            "type": "calculatedTableColumn",
            "name": c["name"], "dataType": c["dataType"],
            "isNameInferred": True, "isDataTypeInferred": True,
            "sourceColumn": f"[{c['name']}]",
            "lineageTag": str(uuid.uuid4()),
            "summarizeBy": "none",
            "annotations": [{"name": "SummarizationSetBy", "value": "User"}],
        } for c in columnas],
        "partitions": [{"name": nombre, "mode": "import",
                        "source": {"type": "calculated",
                                   "expression": dax.strip().split("\n")}}],
    }
    if descripcion:
        tabla["description"] = descripcion
    modelo.setdefault("model", {}).setdefault("tables", []).append(tabla)
    cambios = [traducir("tb_creada", idioma).format(
        tabla=nombre, n=len(columnas),
        cols=", ".join(c["name"] for c in columnas[:8]))]

    for r in relaciones or []:
        if not isinstance(r, dict):
            continue
        if r.get("desde_tabla"):
            partes = (r["desde_tabla"], r.get("desde_col", ""),
                      nombre, r.get("hacia_col", ""))
        else:
            partes = (nombre, r.get("desde_col", ""),
                      r.get("hacia_tabla", ""), r.get("hacia_col", ""))
        try:
            modelo, c = rel_mod.agregar(modelo, *partes, idioma)
            cambios += c
        except ValueError as exc:
            cambios.append(traducir("tb_rel_fallo", idioma).format(
                rel=f"{partes[0]}[{partes[1]}] → {partes[2]}[{partes[3]}]",
                motivo=exc))

    for m in medidas or []:
        if not isinstance(m, dict) or not m.get("nombre") or not m.get("dax"):
            continue
        try:
            modelo, c = transformador.agregar_medida(
                modelo, m["nombre"], m["dax"], formato=m.get("formato", ""),
                descripcion=m.get("descripcion", ""), idioma=idioma)
            cambios += c
        except ValueError as exc:
            cambios.append(traducir("tb_med_fallo", idioma).format(
                med=m["nombre"], motivo=exc))
    return modelo, cambios


def crear_accion(modelo: dict, nombre: str = "", dax: str = "",
                 descripcion: str = "", relaciones: list | None = None,
                 medidas: list | None = None,
                 idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """La misma `crear`, con el contrato del registro de acciones."""
    return crear(modelo, nombre, dax, descripcion, relaciones, medidas,
                 idioma)


def describir(cat: Catalogo, nombre: str, dax: str,
              relaciones: list | None = None, medidas: list | None = None,
              idioma: str = IDIOMA_DEFECTO) -> str:
    """Una línea para el plan: qué tabla, con qué, relacionada con qué."""
    columnas = columnas_de_dax(dax, cat)
    rels = []
    for r in relaciones or []:
        if not isinstance(r, dict):
            continue
        if r.get("desde_tabla"):
            rels.append(f"{r['desde_tabla']}[{r.get('desde_col')}] → "
                        f"{nombre}[{r.get('hacia_col')}]")
        else:
            rels.append(f"{nombre}[{r.get('desde_col')}] → "
                        f"{r.get('hacia_tabla')}[{r.get('hacia_col')}]")
    meds = [m.get("nombre", "") for m in medidas or [] if isinstance(m, dict)]
    return traducir("nlp_d_crear_tabla", idioma).format(
        tabla=nombre, cols=", ".join(c["name"] for c in columnas) or "—",
        rels=" · ".join(rels) or "—", meds=", ".join(meds) or "—")


# ==========================================================================
# Plantillas (sin IA)
# ==========================================================================
_RE_RESUMEN = re.compile(
    r"(?:tabla|table|tabela)\b[^\n]*?\b(?:por|by|para\s+cada|per)\s+"
    r"(?P<col>[^,;.]+?)\s*(?:\(|$|con\b|with\b)", re.I)
_RE_PARAMETRO = re.compile(
    r"(?:par[aá]metro|parameter|what[\s-]?if|escenario|scenario)\w*"
    r"[^\n]*?(?P<a>-?\d+(?:[.,]\d+)?)\s*(?:a|to|hasta|até|-|–)\s*"
    r"(?P<b>-?\d+(?:[.,]\d+)?)(?:[^\n]*?(?:paso|step|de\s+a|cada|passo)\s*"
    r"(?P<p>\d+(?:[.,]\d+)?))?", re.I)


def _num(s: str) -> str:
    return s.replace(",", ".")


def plantilla(cat: Catalogo, pedido: str,
              idioma: str = IDIOMA_DEFECTO) -> dict | None:
    """La especificación de una tabla para los pedidos que se resuelven
    sin IA. `None` si el pedido no es de esos."""
    from . import kpis

    m = _RE_PARAMETRO.search(pedido)
    if m:
        a, b = _num(m.group("a")), _num(m.group("b"))
        paso = _num(m.group("p")) if m.group("p") else "1"
        nombre = traducir("tb_nombre_parametro", idioma)
        medida = traducir("tb_medida_parametro", idioma).format(tabla=nombre)
        return {"nombre": nombre,
                "dax": f"GENERATESERIES ( {a}, {b}, {paso} )",
                "descripcion": pedido.strip(),
                "relaciones": [],
                "medidas": [{"nombre": medida,
                             "dax": f"SELECTEDVALUE ( '{nombre}'[Value], {a} )",
                             "formato": "#,0.##"}]}

    m = _RE_RESUMEN.search(pedido)
    if m:
        hallada = cat.buscar_columna(m.group("col").strip())
        if not hallada:
            return None
        tabla, col = hallada
        principales = [n for n in kpis.principales(cat, 4) if cat.medida(n)]
        if not principales:
            return None
        nombre = traducir("tb_nombre_resumen", idioma).format(col=col["nombre"])
        pares = ",\n".join(f'    "{n}", [{n}]' for n in principales)
        dax = (f"SUMMARIZECOLUMNS (\n    '{tabla}'[{col['nombre']}],\n"
               f"{pares}\n)")
        return {"nombre": nombre, "dax": dax, "descripcion": pedido.strip(),
                "relaciones": [], "medidas": []}
    return None
