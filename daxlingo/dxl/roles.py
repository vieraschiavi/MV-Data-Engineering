# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Qué ES cada medida, para que cada visual reciba la correcta.

El generador de tableros elegía «las cinco medidas principales» y las
repartía entre tarjetas, línea, barras y matriz. Ordenadas por puntaje,
sí; pero un puntaje no distingue un NIVEL («Ventas USD») de una
VARIACIÓN («var mes %») ni de un share del año pasado («Share YTD AA %»).
El resultado, reportado sobre un informe entregado: cinco tarjetas donde
tres eran shares del año anterior y ninguna el nivel del negocio, y una
línea que comparaba el año pasado contra el mercado de hoy.

Acá cada medida se clasifica por lo que ES —nivel, mercado, año anterior,
variación, share, puntos porcentuales, acumulado, ranking, texto— y de
ahí sale el BLOQUE GERENCIAL de una página: nivel, contra el mercado,
share, cómo viene contra el año anterior y cuántos puntos se ganaron o
perdieron. Es la lectura con la que se decide, y es la misma en un
tablero comercial, uno financiero o uno de operaciones.

La clasificación mira tres cosas, en este orden: el formato (un `"pp"` en
el formatString no deja lugar a dudas), el nombre (los que genera este
programa y los que usa la gente) y el DAX (un `RANKX` es un ranking). Lo
que no encaja en nada queda como nivel, que es el rol más inofensivo: una
tarjeta de más, nunca un número mal leído.
"""
from __future__ import annotations

import re

from .catalogo import Catalogo, _norm

# ---- roles ----------------------------------------------------------------
NIVEL = "nivel"
MERCADO = "mercado"
ANTERIOR = "anterior"
VARIACION = "variacion"
SHARE = "share"
PP = "pp"
ACUMULADO = "acumulado"
RANKING = "ranking"
TEXTO = "texto"
# Marcas que se suman al rol, no lo reemplazan.
PROPIA = "propia"

_RE_PP = re.compile(r'"pp"|\bpp\b', re.I)
_RE_AA = re.compile(
    r"\bAA\b|\bPY\b|a[nñ]o\s+anterior|ano\s+anterior|prior\s+year|"
    r"last\s+year|mismo\s+per[ií]odo", re.I)
_RE_VAR = re.compile(
    r"\bvar\b|\bvar\.|variaci[oó]n|varia[cç][aã]o|\bvs\b|versus|"
    r"crecimiento|growth|delta|\bdif\b|diferencia", re.I)
_RE_SHARE = re.compile(
    r"\bshare\b|participaci[oó]n|participa[cç][aã]o|\bcuota\b|market\s*share",
    re.I)
_RE_ACUM = re.compile(r"\bYTD\b|\bQTD\b|\bSTD\b|\bMTD\b|acumulad|accumulat",
                      re.I)
_RE_RANK = re.compile(r"\bRANKX\b", re.I)
_RE_RANK_NOMBRE = re.compile(r"\branking\b|\bposici[oó]n\b|\brank\b|\bpuesto\b",
                             re.I)

# Las palabras que marcan «esto es el mercado, no lo mío». Se comparten
# con el diseñador (`tablero._MERCADO`), que las usa para pintar las dos
# series de una comparación con colores distintos.
_MERCADO_PALABRAS = ("mercado", "mercados", "market", "markets", "industria",
                     "industrias", "competencia", "total mercado")


def _es_porcentaje(formato: str) -> bool:
    return "%" in (formato or "")


def _del_mercado(nombre: str) -> bool:
    fichas = set(re.split(r"[^0-9a-záéíóúñ]+", _norm(nombre)))
    return bool(fichas & {_norm(p) for p in _MERCADO_PALABRAS})


def etiquetas(cat: Catalogo, medida: dict | str) -> set[str]:
    """Todo lo que esta medida ES: `{"share", "propia"}`, `{"nivel",
    "mercado"}`, `{"variacion"}`…

    Son etiquetas y no un rol único a propósito: «Ventas Mercado YTD» es
    a la vez del mercado y un acumulado, y quien arma el visual necesita
    las dos cosas para elegir bien.
    """
    m = cat.medida(medida) if isinstance(medida, str) else medida
    if not m:
        return set()
    nombre = m.get("nombre", "")
    formato = m.get("formato", "") or ""
    expr = m.get("expresion", "") or ""

    from .analizador import es_medida_de_texto
    if es_medida_de_texto(expr, cat):
        return {TEXTO}

    fuera: set[str] = set()
    if _del_mercado(nombre):
        fuera.add(MERCADO)
    if _RE_ACUM.search(nombre):
        fuera.add(ACUMULADO)
    if _RE_AA.search(nombre):
        fuera.add(ANTERIOR)

    if _RE_RANK.search(expr) or _RE_RANK_NOMBRE.search(nombre):
        return fuera | {RANKING}
    # Los puntos porcentuales ganan a todo: es una diferencia de shares y
    # se lee con semáforo, no como un share.
    if _RE_PP.search(formato) or _RE_PP.search(nombre):
        return fuera | {PP, VARIACION}
    if _RE_SHARE.search(nombre):
        return fuera | {SHARE}
    # Una variación es un CAMBIO en porcentaje. El formato manda: hay
    # medidas que se llaman «… vs año anterior» y son el porcentaje de
    # variación, y otras con el mismo apellido que son el NIVEL del año
    # pasado. Confundirlas fue lo que puso una tarjeta de variación donde
    # iba el nivel del negocio.
    if _es_porcentaje(formato) and _RE_VAR.search(nombre):
        return fuera | {VARIACION}
    if ANTERIOR in fuera and not _es_porcentaje(formato):
        return fuera | {ANTERIOR}
    if _es_porcentaje(formato) and ANTERIOR not in fuera:
        # Un porcentaje que no es share ni variación (cobertura, tasa de
        # respuesta): se lee como nivel, que es lo que es.
        return fuera | {NIVEL}
    return fuera | {NIVEL}


def rol(cat: Catalogo, medida: dict | str) -> str:
    """El rol PRINCIPAL, para explicar o agrupar."""
    e = etiquetas(cat, medida)
    for r in (TEXTO, RANKING, PP, SHARE, VARIACION, ANTERIOR, NIVEL):
        if r in e:
            return r
    return NIVEL


# ---- la base: qué mide, sin los apellidos de período -----------------------
_SUFIJOS = re.compile(
    r"\b(YTD|QTD|STD|MTD|AA|PY)\b|\b(mes|trimestre|semestre|a[nñ]o|year|"
    r"quarter|semester|month)\b|\bvar\b|\bvs\b|%|\bpp\b|\bmercado\b|"
    r"\bmarket\b|\bshare\b|\bacumulado\b|\bparticipaci[oó]n\b", re.I)


def base(nombre: str) -> str:
    """«Share Total VentasUSD YTD AA %» → «total ventasusd».

    Sirve para emparejar entre sí las medidas de una misma familia: el
    nivel con su variación, con su share y con su mercado.
    """
    limpio = _SUFIJOS.sub(" ", nombre or "")
    return " ".join(_norm(limpio).split())


def _misma_familia(a: str, b: str) -> bool:
    ba, bb = base(a), base(b)
    if not ba or not bb:
        return False
    return ba == bb or ba in bb or bb in ba


# ---- el bloque gerencial ---------------------------------------------------
def _mejor(cat: Catalogo, nombres: list[str], quiere: set[str],
           evita: set[str] = frozenset(), familia: str = "",
           prefiere: tuple[str, ...] = ()) -> str | None:
    """La primera medida que tenga TODAS las etiquetas de `quiere`,
    NINGUNA de `evita` y —si se pide— la misma familia que `familia`.

    `prefiere` desempata por palabras del nombre: entre «var mes %» y
    «var YTD %» para una tarjeta se quiere la del mes, que es la lectura
    más inmediata.
    """
    candidatas = []
    for n in nombres:
        e = etiquetas(cat, n)
        if not e or not quiere <= e or e & evita:
            continue
        if familia and not _misma_familia(familia, n):
            continue
        peso = 0
        for i, palabra in enumerate(prefiere):
            if re.search(rf"\b{re.escape(palabra)}\b", n, re.I):
                peso = len(prefiere) - i
                break
        candidatas.append((-peso, len(n), n))
    candidatas.sort()
    return candidatas[0][2] if candidatas else None


def bloque(cat: Catalogo, nombres: list[str],
           orden: list[str] | None = None) -> dict:
    """Las medidas de una página, cada una en su papel.

    Devuelve `{"nivel", "mercado", "share", "share_contexto", "variacion",
    "pp", "anterior", "acumulado", "ranking"}` — `None` en lo que el
    modelo no tenga. Nunca inventa: si no hay mercado, no hay comparación
    contra el mercado y la página se arma sin ella.

    `orden` es la preferencia del usuario (las medidas que eligió): la
    primera de sus medidas que sea un nivel manda sobre el ranking
    automático, porque sabe qué mide su negocio mejor que una heurística.
    """
    from . import kpis as _kpis

    disponibles = [n for n in nombres if cat.medida(n)]
    if not disponibles:
        return {}
    # El nivel: lo que el negocio mide. Se elige entre los niveles
    # PROPIOS (nunca el del mercado, que es el denominador) con el mismo
    # ranking que usan las tarjetas.
    niveles = [n for n in (orden or []) + disponibles
               if NIVEL in etiquetas(cat, n)
               and not (etiquetas(cat, n) & {MERCADO, ANTERIOR, ACUMULADO})]
    if not niveles:
        niveles = [n for n in disponibles if NIVEL in etiquetas(cat, n)]
    if not niveles:
        return {}
    nivel = _kpis.principales(cat, 1, entre=niveles)
    nivel = nivel[0] if nivel else niveles[0]
    return con_nivel(cat, disponibles, nivel)


def con_nivel(cat: Catalogo, nombres: list[str], nivel: str) -> dict:
    """El mismo bloque, pero con el nivel YA elegido.

    Hace falta cuando la medida que encabeza no la decide el ranking sino
    el contexto: en una página de segmentos, el corte se abre con la
    medida que ESA dimensión filtra, y sus comparativos tienen que ser
    los de esa medida y no los de la más importante del modelo.
    """
    disponibles = [n for n in nombres if cat.medida(n)]
    if not cat.medida(nivel):
        return {}
    fam = nivel

    def busca(quiere, evita=frozenset(), misma_familia=True, prefiere=()):
        return _mejor(cat, disponibles, set(quiere), set(evita),
                      fam if misma_familia else "", prefiere)

    empresa = cat.anotaciones.get("MVDAX_EmpresaPropia", "")
    shares = [n for n in disponibles
              if SHARE in etiquetas(cat, n)
              and not (etiquetas(cat, n) & {ANTERIOR, PP})]
    # El share de la EMPRESA es el de las tarjetas: no depende del filtro
    # y por eso no da 100 % en una tarjeta sin cortar. El share por
    # CONTEXTO es el de la matriz de competencia, donde cada fila es una
    # corporación y ahí sí significa «la participación de esta fila».
    share_propia = next((n for n in shares
                         if empresa and _norm(empresa) in _norm(n)), None)
    share_contexto = next((n for n in shares if n != share_propia), None)
    pp_propia = next(
        (n for n in disponibles
         if PP in etiquetas(cat, n) and empresa
         and _norm(empresa) in _norm(n)
         and re.search(r"\bmes\b|\bmonth\b", n, re.I)), None)
    return {
        "nivel": nivel,
        "mercado": busca({NIVEL, MERCADO}, {ANTERIOR, ACUMULADO, VARIACION}),
        "share": share_propia or share_contexto,
        "share_contexto": share_contexto or share_propia,
        "variacion": busca({VARIACION}, {PP, SHARE},
                           prefiere=("mes", "month", "año", "ano", "year")),
        "pp": pp_propia or busca({PP}, misma_familia=False,
                                 prefiere=("mes", "month")),
        # El pp del CONTEXTO es el de la matriz de competidores: cada
        # fila es una corporación y el suyo es el que corresponde. El de
        # la empresa propia daría la misma cifra en las cinco filas.
        "pp_contexto": next(
            (n for n in disponibles
             if PP in etiquetas(cat, n)
             and not (empresa and _norm(empresa) in _norm(n))
             and re.search(r"\bmes\b|\bmonth\b", n, re.I)), None),
        "anterior": busca({ANTERIOR}, {VARIACION, SHARE, PP, ACUMULADO},
                          prefiere=("mes", "month")),
        "acumulado": busca({ACUMULADO}, {ANTERIOR, VARIACION, SHARE, PP,
                                         MERCADO}),
        "var_acumulado": busca({VARIACION, ACUMULADO}, {PP, SHARE}),
        # El ranking de LA MISMA familia: «Ranking Ventas» al lado de las
        # ventas, no el de otra medida que casualmente exista.
        "ranking": busca({RANKING}) or busca({RANKING}, misma_familia=False),
    }


def tarjetas(cat: Catalogo, bl: dict, nombres: list[str],
             cuantas: int = 5) -> list[str]:
    """Las tarjetas de arriba, en el orden en que se leen: dónde estoy
    (nivel), contra quién (mercado), cuánto peso (share), cómo vengo
    (variación) y cuánto gané o perdí (pp).

    Se completa con otros niveles del modelo antes que con más
    variaciones: cinco tarjetas de porcentajes no dicen cuánto vendió la
    empresa, y eso fue exactamente el reclamo sobre un informe entregado.
    """
    elegidas: list[str] = []
    for clave in ("nivel", "mercado", "share", "variacion", "pp"):
        n = bl.get(clave)
        if n and n not in elegidas:
            elegidas.append(n)
    if len(elegidas) < cuantas:
        from . import kpis as _kpis
        otros = [n for n in nombres
                 if n not in elegidas and cat.medida(n)
                 and NIVEL in etiquetas(cat, n)
                 and ANTERIOR not in etiquetas(cat, n)]
        for n in _kpis.principales(cat, cuantas, entre=otros):
            if n not in elegidas:
                elegidas.append(n)
            if len(elegidas) >= cuantas:
                break
    return elegidas[:cuantas]


def columnas_periodo(cat: Catalogo, bl: dict) -> list[str]:
    """Las columnas de la matriz de períodos: hoy, el año anterior, la
    variación, el acumulado y su variación. Es la tabla con la que se
    responde «¿cómo venimos?» sin abrir otra pestaña."""
    orden = ("nivel", "anterior", "variacion", "acumulado", "var_acumulado",
             "share", "pp")
    salida = []
    for clave in orden:
        n = bl.get(clave)
        if n and n not in salida:
            salida.append(n)
    return salida


def columnas_competencia(cat: Catalogo, bl: dict) -> list[str]:
    """Las columnas de la matriz de competidores: cuánto vende cada uno,
    qué parte del mercado se lleva, cuánto se movió y en qué puesto está.

    Acá el share es el del CONTEXTO —cada fila es una corporación, así
    que «su» share es lo que corresponde—, no el de la empresa propia,
    que daría la misma cifra en todas las filas.
    """
    salida = []
    for clave in ("nivel", "share_contexto", "pp_contexto", "ranking"):
        n = bl.get(clave)
        if n and n not in salida:
            salida.append(n)
    return salida
