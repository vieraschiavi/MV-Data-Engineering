# © 2026 Martín Viera. Todos los derechos reservados.

"""De una columna a la jerarquía con la que se despliega.

Una matriz con «Producto» en las filas ocupa media pantalla y contesta
una pregunta. La misma matriz con «Área terapéutica → Molécula →
Producto» ocupa exactamente lo mismo y contesta tres: quien mira abre el
nivel que le interesa y deja el resto plegado. Es la diferencia entre un
informe que hay que scrollear y uno que se navega, y es lo que se pidió
como «tablas con drill down así se optimiza espacio».

Cómo se decide el orden, de lo general a lo particular:

1. **La jerarquía declarada en el modelo.** Si el `.pbix` de origen ya
   tiene una, esa manda: alguien la pensó.
2. **El calendario**, que tiene un orden que no se discute: año → mes.
3. **El vocabulario.** «Área», «categoría» y «familia» contienen a
   «línea» y «molécula», que contienen a «producto» y «SKU». Se arma la
   cadena sólo cuando los rangos son ESTRICTAMENTE crecientes: dos
   columnas del mismo rango —«segmento» y «canal»— no se contienen entre
   sí y ponerlas una adentro de la otra inventa una jerarquía que el
   negocio no tiene.

Sin ninguna de las tres pistas la columna queda sola, que es lo que
había antes: una jerarquía inventada es peor que ninguna.
"""
from __future__ import annotations

import re
import unicodedata

from .catalogo import Catalogo

MAX_NIVELES = 3


def _norm(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in limpio if not unicodedata.combining(c)).lower()


# De lo que contiene a lo contenido. El rango es la profundidad: un
# rango menor envuelve a uno mayor.
_RANGOS: tuple[tuple[str, int], ...] = (
    (r"\bpais\b|\bcountry\b|\bnacion\b", 0),
    (r"\bregion\b|\bzona\b|\bterritorio\b|\bmacro", 0),
    (r"\barea\b|areaterapeutica|\bsector\b|\bdivision\b|\bunidad\s*de\s*negocio",
     0),
    (r"\bcategoria\b|\bcategory\b|\bfamilia\b|\bfamily\b|\brubro\b", 1),
    (r"\bclase\b|\bclass\b|\bgrupo\b|\bgroup\b|\bespecialidad\b|\batc\d*\b", 1),
    (r"\bsubcategoria\b|\bsubfamilia\b|\bsubrubro\b|\blinea\b|\bline\b", 2),
    (r"\bmarca\b|\bbrand\b|\bmolecula\b|\bmolecule\b|\bprincipio\b", 2),
    (r"\bprovincia\b|\bestado\b|\bstate\b|\bdepartamento\b", 2),
    (r"\bproducto\b|\bproduct\b|\bproduto\b|\bsku\b|\barticulo\b|\bitem\b", 3),
    (r"\bciudad\b|\bcity\b|\bcidade\b|\blocalidad\b", 3),
    (r"\bsucursal\b|\btienda\b|\bstore\b|\bpunto\s*de\s*venta\b|\bpdv\b", 3),
)


def rango(nombre: str) -> int | None:
    """Qué tan general es una columna, o `None` si el vocabulario no la
    reconoce. Sin rango no se la mete en ninguna cadena."""
    limpio = _norm(nombre)
    for patron, valor in _RANGOS:
        if re.search(patron, limpio):
            return valor
    return None


def _declarada(cat: Catalogo, tabla: str,
               columna: str) -> list[tuple[str, str]]:
    """Los niveles de la jerarquía que el modelo YA declara, hasta la
    columna pedida. Vacío si no hay ninguna que la contenga."""
    for t in cat.tablas:
        if _norm(t["nombre"]) != _norm(tabla):
            continue
        for h in t.get("jerarquias") or []:
            cols = [n for n in h.get("niveles") or []]
            if any(_norm(c) == _norm(columna) for c in cols):
                corte = next(i for i, c in enumerate(cols)
                             if _norm(c) == _norm(columna))
                return [(t["nombre"], c) for c in cols[:corte + 1]]
    return []


# El único orden que no se discute: el año contiene al semestre, que
# contiene al trimestre, que contiene al mes. Se toman las columnas que
# EXISTEN en el calendario del modelo —un calendario en inglés dice
# `Quarter`— y los niveles que faltan simplemente no aparecen.
_ESCALA_TIEMPO = ("anio", "semestre", "trimestre", "anio_mes")


def _calendario(cat: Catalogo, cal: dict) -> list[tuple[str, str]]:
    from .periodos import _SINONIMOS

    presentes = {_norm(c["nombre"]): c["nombre"] for c in cal["columnas"]
                 if not c.get("oculta")}
    salida = []
    for clave in _ESCALA_TIEMPO:
        real = next((presentes[_norm(a)] for a in _SINONIMOS.get(clave, ())
                     if _norm(a) in presentes), None)
        if real:
            salida.append((cal["nombre"], real))
    return salida


def de(cat: Catalogo, dim: tuple[str, str],
       maximo: int = MAX_NIVELES) -> list[tuple[str, str]]:
    """La jerarquía que termina en `dim`, de lo general a lo particular.

    Siempre devuelve al menos `[dim]`: una columna sin parientes se
    dibuja sola, como siempre.
    """
    tabla, columna = dim
    declarada = _declarada(cat, tabla, columna)
    if len(declarada) > 1:
        return declarada[-maximo:]

    cal = cat.tabla_fechas()
    if cal and _norm(cal["nombre"]) == _norm(tabla):
        cortes = _calendario(cat, cal)
        if any(_norm(c) == _norm(columna) for _t, c in cortes):
            corte = next(i for i, (_t, c) in enumerate(cortes)
                         if _norm(c) == _norm(columna))
            # El tiempo admite un nivel más que el resto: año → semestre →
            # trimestre → mes es UNA matriz que contesta las cuatro
            # comparaciones que se piden, en el lugar de una.
            return cortes[max(0, corte + 1 - max(maximo, 4)):corte + 1]
        return [dim]

    propio = rango(columna)
    if propio is None:
        return [dim]

    from .tablero import _es_dimension

    candidatas: list[tuple[int, str]] = []
    for t, c in cat.columnas(solo_visibles=True):
        if _norm(t) != _norm(tabla) or _norm(c["nombre"]) == _norm(columna):
            continue
        r = rango(c["nombre"])
        if r is None or r >= propio or not _es_dimension(t, c, cat):
            continue
        candidatas.append((r, c["nombre"]))
    if not candidatas:
        return [dim]

    # Un nivel por rango: dos columnas igual de generales no se contienen
    # entre sí, y encadenarlas inventa una jerarquía que no existe.
    por_rango: dict[int, str] = {}
    for r, nombre in sorted(candidatas):
        por_rango.setdefault(r, nombre)
    niveles = [(tabla, por_rango[r]) for r in sorted(por_rango)]
    return (niveles + [dim])[-maximo:]


def hoja(dim) -> tuple[str, str]:
    """El nivel más fino de una jerarquía: el que da título al visual."""
    if dim and isinstance(dim[0], str):
        return dim  # type: ignore[return-value]
    return dim[-1] if dim else ("", "")


def niveles(dim) -> list[tuple[str, str]]:
    """`dim` como lista de niveles, venga una columna o una jerarquía."""
    if not dim:
        return []
    return [dim] if isinstance(dim[0], str) else list(dim)
