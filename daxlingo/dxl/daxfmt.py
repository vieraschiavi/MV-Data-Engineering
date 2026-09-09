# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Formateador de DAX, adentro del programa.

Es la función «Format DAX» que la gente busca en DAX Studio o en Bravo,
sin salir de acá: nombres de función en mayúsculas, un espacio entre el
nombre y el paréntesis, cada argumento en su línea cuando la llamada no
entra en un renglón, `VAR`/`RETURN` cada uno en el suyo.

La única promesa que importa: **no cambia lo que la fórmula calcula.**
Antes de devolver nada se comparan los tokens de entrada y de salida —
cadenas, identificadores, números, operadores— y si difieren en algo que
no sea espacio o mayúsculas de una función, se devuelve el original tal
cual. Un formateador que «arregla» una fórmula es un bug con buena prensa.
"""
from __future__ import annotations

import copy
import re

from .i18n import IDIOMA_DEFECTO, t as traducir

# Cuántos caracteres puede ocupar una llamada en una sola línea antes de
# abrirse con un argumento por renglón.
ANCHO = 60
SANGRIA = "    "

_TOKEN = re.compile(r'''
    (?P<cadena>"(?:[^"]|"")*")
  | (?P<tabla>'(?:[^']|'')*')
  | (?P<campo>\[[^\]]*\])
  | (?P<numero>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_.]*)
  | (?P<op><=|>=|<>|&&|\|\||[-+*/^=<>&(),{}!:])
  | (?P<espacio>\s+)
  | (?P<otro>.)
''', re.VERBOSE | re.DOTALL)

_PALABRAS = {"VAR", "RETURN", "TRUE", "FALSE", "NOT", "IN", "AND", "OR",
             "ASC", "DESC", "BLANK"}


def tokens(dax: str) -> list[tuple[str, str]]:
    """`[(tipo, texto)]` sin espacios. Las cadenas y los nombres entre
    comillas o corchetes se conservan tal cual (ahí adentro los espacios
    SÍ importan)."""
    salida = []
    for m in _TOKEN.finditer(dax or ""):
        tipo = m.lastgroup
        if tipo == "espacio":
            continue
        salida.append((tipo, m.group()))
    return salida


def _huella(toks: list[tuple[str, str]]) -> list[str]:
    """Lo que tiene que ser igual antes y después: todo, salvo el caso de
    los identificadores (funciones y palabras clave)."""
    return [t.upper() if tipo == "ident" else t for tipo, t in toks]


# ---- el árbol: llamadas con argumentos, paréntesis sueltos, tokens ----
class _Llamada:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.args: list[list] = [[]]


class _Grupo:
    def __init__(self, abre: str):
        self.abre = abre
        self.items: list = []


_CIERRA = {"(": ")", "{": "}"}


def _parsear(toks: list[tuple[str, str]]) -> list:
    pila: list = [[]]
    i = 0
    while i < len(toks):
        tipo, t = toks[i]
        arriba = pila[-1]
        if tipo == "ident" and t.upper() not in _PALABRAS \
                and i + 1 < len(toks) and toks[i + 1][1] == "(":
            nodo = _Llamada(t.upper())
            arriba.append(nodo)
            pila.append(nodo.args[0])
            i += 2
            continue
        if t in _CIERRA:
            nodo = _Grupo(t)
            arriba.append(nodo)
            pila.append(nodo.items)
            i += 1
            continue
        if t in (")", "}"):
            if len(pila) > 1:
                pila.pop()
            else:
                arriba.append((tipo, t))          # sobra: se deja pasar
            i += 1
            continue
        if t == ",":
            duenio = _duenio(pila)
            if isinstance(duenio, _Llamada):
                duenio.args.append([])
                pila[-1] = duenio.args[-1]
                i += 1
                continue
        arriba.append((tipo, t))
        i += 1
    return pila[0]


def _duenio(pila: list):
    """A qué nodo pertenece la lista que está arriba de la pila."""
    # Se guarda la referencia recorriendo hacia atrás: la lista de
    # argumentos activa es `args[-1]` de la última llamada abierta.
    for nivel in range(len(pila) - 1, 0, -1):
        lista = pila[nivel]
        for nodo in _contenedores(pila[nivel - 1]):
            if isinstance(nodo, _Llamada) and any(a is lista for a in nodo.args):
                return nodo
            if isinstance(nodo, _Grupo) and nodo.items is lista:
                return nodo
        return None
    return None


def _contenedores(lista: list):
    return [n for n in lista if isinstance(n, (_Llamada, _Grupo))]


# ---- render ----
_SIN_ESPACIO_ANTES = {")", ",", "}"}
_SIN_ESPACIO_DESPUES = {"(", "{"}
_UNARIO_TRAS = {"(", ",", "=", "<", ">", "<=", ">=", "<>", "+", "-", "*",
                "/", "^", "&&", "||", "&", "{", "IN", "RETURN", "NOT"}


def _plano(items: list) -> str:
    """Una línea, con los espacios canónicos."""
    partes: list[str] = []
    previo = ""
    previo_tipo = ""
    for it in items:
        if isinstance(it, _Llamada):
            texto = f"{it.nombre} ( " + ", ".join(
                _plano(a) for a in it.args) + " )" \
                if any(it.args) and any(a for a in it.args) \
                else f"{it.nombre} ()"
        elif isinstance(it, _Grupo):
            adentro = _plano(it.items)
            texto = (f"{it.abre} {adentro} {_CIERRA[it.abre]}" if adentro
                     else f"{it.abre}{_CIERRA[it.abre]}")
        else:
            tipo, t = it
            texto = t.upper() if tipo == "ident" and t.upper() in _PALABRAS \
                else t
        # `Tabla[Columna]` y `'Tabla'[Columna]` van pegados: el corchete
        # no es un token suelto sino la mitad de una referencia.
        pegado = (not isinstance(it, (_Llamada, _Grupo))
                  and it[0] == "campo" and previo_tipo in ("ident", "tabla"))
        if partes and not pegado \
                and not (texto == "-" and previo in _UNARIO_TRAS) \
                and not (previo == "-" and _es_unario(partes)):
            partes.append(" ")
        partes.append(texto)
        previo = texto
        previo_tipo = it[0] if isinstance(it, tuple) else "nodo"
    return "".join(partes)


def _es_unario(partes: list[str]) -> bool:
    """El «-» recién escrito, ¿es signo y no resta?"""
    # partes[-1] es "-"; lo anterior (saltando el espacio) decide.
    anteriores = [p for p in partes[:-1] if p != " "]
    return not anteriores or anteriores[-1] in _UNARIO_TRAS


def _render(items: list, nivel: int) -> str:
    plano = _plano(items)
    if len(plano) + len(SANGRIA) * nivel <= ANCHO \
            or not _contenedores(items):
        return plano
    # Hay que abrir: se renderiza item por item; las llamadas largas se
    # expanden con un argumento por línea.
    partes: list[str] = []
    for it in items:
        if isinstance(it, _Llamada) and any(a for a in it.args):
            adentro = _plano_llamada(it)
            if len(adentro) + len(SANGRIA) * nivel <= ANCHO:
                partes.append(adentro)
                continue
            sangria = SANGRIA * (nivel + 1)
            args = [",\n".join([sangria + _render(a, nivel + 1)])
                    for a in it.args]
            partes.append(f"{it.nombre} (\n" + ",\n".join(args)
                          + "\n" + SANGRIA * nivel + ")")
        elif isinstance(it, _Grupo):
            partes.append(_plano([it]))
        else:
            partes.append(_plano([it]))
    return _unir(partes)


def _plano_llamada(it: _Llamada) -> str:
    return _plano([it])


def _unir(partes: list[str]) -> str:
    salida = ""
    for p in partes:
        if not salida:
            salida = p
        elif p in _SIN_ESPACIO_ANTES or salida.endswith(("(", "{")) \
                or p.startswith(")"):
            salida += p
        else:
            salida += " " + p
    return salida


def formatear(dax: str) -> str:
    """El DAX formateado, o el original intacto si no se puede garantizar
    que calcula lo mismo."""
    original = dax or ""
    toks = tokens(original)
    if not toks:
        return original
    try:
        arbol = _parsear(toks)
        lineas = _con_var_return(arbol)
    except Exception:                                 # noqa: BLE001
        return original
    salida = "\n".join(lineas).strip()
    if _huella(tokens(salida)) != _huella(toks):
        return original
    return salida


def _con_var_return(arbol: list) -> list[str]:
    """`VAR` y `RETURN` del nivel superior, cada uno en su línea."""
    bloques: list[list] = [[]]
    for it in arbol:
        if not isinstance(it, tuple):
            bloques[-1].append(it)
            continue
        tipo, t = it
        if tipo == "ident" and t.upper() in ("VAR", "RETURN"):
            bloques.append([it])
        else:
            bloques[-1].append(it)
    lineas: list[str] = []
    for b in bloques:
        if not b:
            continue
        if isinstance(b[0], tuple) and b[0][1].upper() == "RETURN":
            lineas.append("RETURN")
            cuerpo = _render(b[1:], 1)
            lineas.append(SANGRIA + cuerpo.replace("\n", "\n" + SANGRIA))
        elif isinstance(b[0], tuple) and b[0][1].upper() == "VAR":
            # VAR nombre = expresión
            i_igual = next((i for i, x in enumerate(b)
                            if isinstance(x, tuple) and x[1] == "="), None)
            if i_igual is None:
                lineas.append(_render(b, 0))
                continue
            cabeza = _plano(b[:i_igual + 1])
            cuerpo = _render(b[i_igual + 1:], 1)
            if "\n" in cuerpo or len(cabeza) + len(cuerpo) > ANCHO:
                lineas.append(cabeza)
                lineas.append(SANGRIA + cuerpo.replace("\n", "\n" + SANGRIA))
            else:
                lineas.append(f"{cabeza} {cuerpo}")
        else:
            lineas.append(_render(b, 0))
    return lineas


def formatear_medidas(modelo: dict,
                      idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Formatea todas las medidas del modelo (las que se pueden sin cambiar
    lo que calculan). Devuelve el modelo nuevo y qué cambió."""
    modelo = copy.deepcopy(modelo)
    cambios: list[str] = []
    for t in modelo.get("model", {}).get("tables", []):
        for m in t.get("measures", []):
            expr = m.get("expression")
            texto = "\n".join(expr) if isinstance(expr, list) else str(expr or "")
            nuevo = formatear(texto)
            if nuevo != texto.strip():
                m["expression"] = nuevo.split("\n") if "\n" in nuevo else nuevo
                cambios.append(traducir("fmt_medida", idioma).format(
                    nombre=m.get("name", "")))
    if not cambios:
        cambios.append(traducir("fmt_nada", idioma))
    return modelo, cambios
