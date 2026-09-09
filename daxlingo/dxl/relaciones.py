# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Las relaciones del modelo, explicadas y editables.

Un modelo propuesto desde un dataset crudo trae sus relaciones inferidas,
y un modelo cargado de un .pbit las trae declaradas. En los dos casos el
usuario tiene que poder leer POR QUÉ existe cada una —qué evidencia la
sostiene y qué hace con los filtros— y cambiarla si no está de acuerdo:
quitarla, apagarla, darla vuelta o agregar la que falta.

Explicar no es decorar: una relación que no se entiende no se corrige, y
una relación mal inferida (dos columnas que se llaman igual y no tienen
nada que ver) hace que los visuales filtren mal sin dar un solo error.
"""
from __future__ import annotations

import copy
import uuid

from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

# Cómo se sostiene una relación, de más a menos evidencia.
FECHA = "fecha"
TABLA_ID = "tabla_id"
MISMO_NOMBRE = "mismo_nombre"
DECLARADA = "declarada"


def _regla(cat: Catalogo, r: dict) -> str:
    from .dataset import _misma_entidad, _raiz_de_clave

    fechas = cat.tabla_fechas() or {}
    if fechas and _norm(r["hacia_tabla"]) == _norm(fechas.get("nombre", "")):
        return FECHA
    hacia = cat.tabla(r["hacia_tabla"]) or {"columnas": []}
    col = next((c for c in hacia["columnas"]
                if _norm(c["nombre"]) == _norm(r["hacia_col"])), None)
    if col and col.get("tipo") == "dateTime":
        return FECHA
    if _norm(r["desde_col"]) == _norm(r["hacia_col"]):
        return MISMO_NOMBRE
    if _misma_entidad(_raiz_de_clave(r["desde_col"]), r["hacia_tabla"]):
        return TABLA_ID
    return DECLARADA


def explicar(cat: Catalogo, r: dict, idioma: str = IDIOMA_DEFECTO) -> dict:
    """Por qué existe esta relación y qué hace con los filtros.

    Devuelve `regla`, `evidencia` (la razón, en el idioma del usuario),
    `filtro` (hacia dónde viaja), `avisos` (bidireccional, inactiva,
    muchos a muchos) y `medidas` (cuántas medidas del modelo se apoyan en
    la tabla del lado «muchos», que es lo que esta relación pone a
    disposición de los cortes).
    """
    regla = _regla(cat, r)
    desde = f"{r['desde_tabla']}[{r['desde_col']}]"
    hacia = f"{r['hacia_tabla']}[{r['hacia_col']}]"
    evidencia = traducir({
        FECHA: "rel_por_fecha", TABLA_ID: "rel_por_tabla_id",
        MISMO_NOMBRE: "rel_por_nombre", DECLARADA: "rel_declarada",
    }[regla], idioma).format(desde=desde, hacia=hacia,
                             tabla=r["hacia_tabla"])
    filtro = traducir("rel_filtro", idioma).format(
        dimension=r["hacia_tabla"], hecho=r["desde_tabla"])
    avisos: list[str] = []
    if r.get("bidireccional"):
        avisos.append(traducir("rel_bidireccional_aviso", idioma))
    if not r.get("activa", True):
        avisos.append(traducir("rel_inactiva", idioma))
    if r.get("muchos_a_muchos"):
        avisos.append(traducir("rel_muchos_a_muchos", idioma))
    hecho = _norm(r["desde_tabla"])
    medidas = sum(1 for m in cat.medidas()
                  if hecho in _norm(m.get("expresion", "")))
    return {"regla": regla, "evidencia": evidencia, "filtro": filtro,
            "avisos": avisos, "medidas": medidas}


def explicar_todas(cat: Catalogo, idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Cada relación del catálogo con su explicación, en orden."""
    return [{**r, **explicar(cat, r, idioma)} for r in cat.relaciones]


# ==========================================================================
# Edición
# ==========================================================================
def _misma(r: dict, desde_tabla: str, desde_col: str,
           hacia_tabla: str, hacia_col: str) -> bool:
    return (_norm(r.get("fromTable", "")) == _norm(desde_tabla)
            and _norm(r.get("fromColumn", "")) == _norm(desde_col)
            and _norm(r.get("toTable", "")) == _norm(hacia_tabla)
            and _norm(r.get("toColumn", "")) == _norm(hacia_col))


def _buscar(modelo: dict, desde_tabla: str, desde_col: str,
            hacia_tabla: str, hacia_col: str) -> dict | None:
    for r in modelo.get("model", {}).get("relationships", []):
        if _misma(r, desde_tabla, desde_col, hacia_tabla, hacia_col):
            return r
    return None


def _etiqueta(desde_tabla, desde_col, hacia_tabla, hacia_col) -> str:
    return f"{desde_tabla}[{desde_col}] → {hacia_tabla}[{hacia_col}]"


def quitar(modelo: dict, desde_tabla: str, desde_col: str,
           hacia_tabla: str, hacia_col: str,
           idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Saca la relación del modelo. Las medidas que la usaban con
    USERELATIONSHIP quedan referenciando algo que no existe: se avisa."""
    modelo = copy.deepcopy(modelo)
    m = modelo.get("model", {})
    antes = len(m.get("relationships", []))
    m["relationships"] = [r for r in m.get("relationships", [])
                          if not _misma(r, desde_tabla, desde_col,
                                        hacia_tabla, hacia_col)]
    if len(m["relationships"]) == antes:
        raise ValueError(traducir("rel_err_no_existe", idioma))
    cambios = [traducir("rel_quitada", idioma).format(
        rel=_etiqueta(desde_tabla, desde_col, hacia_tabla, hacia_col))]
    usan = _medidas_que_usan(modelo, desde_tabla, desde_col,
                             hacia_tabla, hacia_col)
    if usan:
        cambios.append(traducir("rel_aviso_userelationship", idioma).format(
            lista=" · ".join(usan[:6])))
    return modelo, cambios


def _medidas_que_usan(modelo, desde_tabla, desde_col,
                      hacia_tabla, hacia_col) -> list[str]:
    a = _norm(f"{desde_tabla}[{desde_col}]")
    b = _norm(f"{hacia_tabla}[{hacia_col}]")
    salida = []
    for t in modelo.get("model", {}).get("tables", []):
        for me in t.get("measures", []):
            expr = me.get("expression")
            texto = _norm("\n".join(expr) if isinstance(expr, list)
                          else str(expr or ""))
            if "userelationship" in texto and a in texto and b in texto:
                salida.append(me.get("name", ""))
    return salida


def activar(modelo: dict, desde_tabla: str, desde_col: str,
            hacia_tabla: str, hacia_col: str, activa: bool,
            idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Prende o apaga la relación.

    Prender una entre dos tablas que ya tienen otra activa no se puede:
    Power BI rechaza dos caminos activos entre las mismas tablas. Se
    avisa en vez de escribir un modelo que Desktop no va a abrir.
    """
    modelo = copy.deepcopy(modelo)
    r = _buscar(modelo, desde_tabla, desde_col, hacia_tabla, hacia_col)
    if r is None:
        raise ValueError(traducir("rel_err_no_existe", idioma))
    if activa:
        par = {_norm(desde_tabla), _norm(hacia_tabla)}
        for otra in modelo["model"].get("relationships", []):
            if otra is r or not otra.get("isActive", True):
                continue
            if {_norm(otra.get("fromTable", "")),
                    _norm(otra.get("toTable", ""))} == par:
                raise ValueError(traducir("rel_err_dos_activas", idioma))
        r.pop("isActive", None)
        clave = "rel_activada"
    else:
        r["isActive"] = False
        clave = "rel_desactivada"
    return modelo, [traducir(clave, idioma).format(
        rel=_etiqueta(desde_tabla, desde_col, hacia_tabla, hacia_col))]


def direccion(modelo: dict, desde_tabla: str, desde_col: str,
              hacia_tabla: str, hacia_col: str, ambas: bool,
              idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Filtro en una dirección (lo recomendado) o en ambas."""
    modelo = copy.deepcopy(modelo)
    r = _buscar(modelo, desde_tabla, desde_col, hacia_tabla, hacia_col)
    if r is None:
        raise ValueError(traducir("rel_err_no_existe", idioma))
    if ambas:
        r["crossFilteringBehavior"] = "bothDirections"
        clave = "rel_direccion_ambas"
    else:
        r.pop("crossFilteringBehavior", None)
        # La casilla de seguridad en ambas direcciones sólo es legal con
        # el cross-filtrado bidireccional: colgada, Desktop rechaza el
        # modelo entero (ya pasó con el arreglo R09).
        r.pop("securityFilteringBehavior", None)
        clave = "rel_direccion_una"
    return modelo, [traducir(clave, idioma).format(
        rel=_etiqueta(desde_tabla, desde_col, hacia_tabla, hacia_col))]


def agregar(modelo: dict, desde_tabla: str, desde_col: str,
            hacia_tabla: str, hacia_col: str,
            idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Agrega una relación muchos-a-uno validando lo que Power BI exige.

    Las dos columnas tienen que existir y ser del mismo tipo; no puede
    ser una tabla consigo misma; y si el par de tablas ya tiene una
    relación activa, la nueva entra INACTIVA (se usa con
    USERELATIONSHIP), que es exactamente lo que hace Desktop.
    """
    cat = Catalogo.desde_modelo(modelo)
    t_desde, t_hacia = cat.tabla(desde_tabla), cat.tabla(hacia_tabla)
    if not t_desde or not t_hacia:
        raise ValueError(traducir("rel_err_tabla", idioma).format(
            tabla=desde_tabla if not t_desde else hacia_tabla))
    if _norm(desde_tabla) == _norm(hacia_tabla):
        raise ValueError(traducir("rel_err_misma", idioma))

    def _col(t, nombre):
        return next((c for c in t["columnas"]
                     if _norm(c["nombre"]) == _norm(nombre)), None)
    c_desde, c_hacia = _col(t_desde, desde_col), _col(t_hacia, hacia_col)
    if not c_desde or not c_hacia:
        raise ValueError(traducir("rel_err_columna", idioma).format(
            col=desde_col if not c_desde else hacia_col))
    if c_desde.get("tipo") != c_hacia.get("tipo"):
        raise ValueError(traducir("rel_err_tipo", idioma).format(
            a=c_desde.get("tipo"), b=c_hacia.get("tipo")))
    if _buscar(modelo, desde_tabla, desde_col, hacia_tabla, hacia_col):
        raise ValueError(traducir("rel_err_existe", idioma))

    modelo = copy.deepcopy(modelo)
    m = modelo.setdefault("model", {})
    par = {_norm(desde_tabla), _norm(hacia_tabla)}
    ya_activa = any(
        r.get("isActive", True)
        and {_norm(r.get("fromTable", "")),
             _norm(r.get("toTable", ""))} == par
        for r in m.get("relationships", []))
    nueva = {"name": str(uuid.uuid4()),
             "fromTable": t_desde["nombre"], "fromColumn": c_desde["nombre"],
             "toTable": t_hacia["nombre"], "toColumn": c_hacia["nombre"]}
    if ya_activa:
        nueva["isActive"] = False
    m.setdefault("relationships", []).append(nueva)
    etiqueta = _etiqueta(t_desde["nombre"], c_desde["nombre"],
                         t_hacia["nombre"], c_hacia["nombre"])
    cambios = [traducir("rel_agregada_inactiva" if ya_activa
                        else "rel_agregada", idioma).format(rel=etiqueta)]
    return modelo, cambios


def invertir(modelo: dict, desde_tabla: str, desde_col: str,
             hacia_tabla: str, hacia_col: str,
             idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Da vuelta los lados: el «uno» pasa a ser «muchos» y viceversa."""
    modelo, c1 = quitar(modelo, desde_tabla, desde_col, hacia_tabla,
                        hacia_col, idioma)
    modelo, c2 = agregar(modelo, hacia_tabla, hacia_col, desde_tabla,
                         desde_col, idioma)
    return modelo, c1[:1] + c2
