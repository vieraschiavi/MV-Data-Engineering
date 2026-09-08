# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · KPIs sugeridos desde el catálogo del modelo.

Mira lo que el modelo TIENE — columnas numéricas de las tablas de hechos,
pares importe/costo, claves hacia dimensiones, calendario — y propone las
medidas que un tablero gerencial pide siempre: totales, margen y margen %,
conteo de operaciones, únicos por dimensión, y acumulado del año + variación
interanual cuando hay calendario. Cada sugerencia lleva su porqué y su DAX
**validado contra el catálogo** antes de salir (la misma vara
anti-alucinación del generador): acá no se sugiere nada que referencie algo
que no existe. Nada se agrega solo — agregarlas es una acción aparte, y las
que ya existen con ese nombre se saltean.
"""
from __future__ import annotations

import re

from .catalogo import Catalogo, TIPOS_NUMERICOS, _norm, validar_referencias
from .i18n import IDIOMA_DEFECTO, t as traducir

# Cuántos «Total <columna>» como máximo por tabla: un hecho con 14 columnas
# numéricas no necesita 14 totales de arranque, necesita los primeros.
_MAX_TOTALES = 4

_IMPORTE = ("importe", "venta", "ventas", "monto", "amount", "revenue",
            "ingreso", "ingresos", "receita", "vendas", "facturacion",
            "faturamento", "total")
_COSTO = ("costo", "costos", "coste", "cost", "custo", "custos")


def _formula(dax: str) -> str:
    """La fórmula sin espacios ni mayúsculas: dos medidas con el mismo
    cálculo y distinto nombre son la MISMA medida."""
    return re.sub(r"\s+", " ", dax or "").strip().lower()


def _tabla_ref(tabla: str) -> str:
    return tabla if tabla.isidentifier() else f"'{tabla}'"


def _ref(tabla: str, columna: str) -> str:
    return f"{_tabla_ref(tabla)}[{columna}]"


def _es_importe(nombre: str) -> bool:
    n = _norm(nombre)
    return any(p in n for p in _IMPORTE)


def _es_costo(nombre: str) -> bool:
    n = _norm(nombre)
    return any(p in n for p in _COSTO)


def _hechos(cat: Catalogo) -> list[dict]:
    """Las tablas de hechos: lado «muchos» de alguna relación; si el modelo
    no tiene relaciones, cualquier tabla visible con columnas numéricas."""
    muchos = {_norm(r["desde_tabla"]) for r in cat.relaciones}
    # El calendario queda afuera aunque todavía no esté MARCADO como tal:
    # sumar la columna «Anio» da 24.300 y no significa nada, pero es un
    # número y llegaba a ser el KPI principal del tablero. La marca la
    # pone R20; el dataset crudo llega sin ella.
    cal = cat.tabla_fechas()
    fuera = {_norm(cal["nombre"])} if cal else set()
    visibles = [t for t in cat.tablas
                if not t["interna"] and not t["oculta"]
                and not t["es_calendario"]
                and _norm(t["nombre"]) not in fuera]
    hechos = [t for t in visibles if _norm(t["nombre"]) in muchos]
    if not hechos:
        hechos = [t for t in visibles
                  if any(c["tipo"] in TIPOS_NUMERICOS and not c["oculta"]
                         and not _clave(c["nombre"]) for c in t["columnas"])]
    return hechos


def _clave(nombre: str) -> bool:
    n = _norm(nombre)
    return "id" in (n[:2], n[-2:]) or n.startswith(("cod", "sku", "nro"))


# Cuántas medidas se cruzan con cada dimensión para las preguntas de
# «¿cuál?». Sin tope, un modelo de cien medidas y ocho dimensiones
# proponía ochocientas sugerencias — y una lista así no se lee, se cierra.
_MAX_CUAL = 2

# Cuántas veces se vuelve a preguntar qué falta. Tres alcanza: las
# sugerencias de segundo orden dependen de las de primer orden, y no hay
# terceras. El tope existe para que un modelo raro no cicle.
_MAX_PASADAS = 3


def _es_texto_dax(expr: str) -> bool:
    """¿La medida ya devuelve texto? Entonces no se le busca un «cuál»."""
    from .analizador import es_medida_de_texto
    return es_medida_de_texto(expr or "")


def _columna_etiqueta(tabla: dict) -> str:
    """La columna con la que se NOMBRA a un miembro de esa dimensión.

    La primera de texto visible que no sea la clave: es la que el usuario
    reconoce. Responder «cuál producto» con un identificador interno es
    no responder.
    """
    for c in tabla["columnas"]:
        if c.get("oculta") or c["tipo"] != "string":
            continue
        if _clave(c["nombre"]):
            continue
        return c["nombre"]
    return ""


def sugerir(cat: Catalogo, idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Los KPIs que este modelo pide, cada uno con su porqué y su DAX ya
    validado. Devuelve [] antes que inventar."""
    sugerencias: list[dict] = []
    existentes = {_norm(m["nombre"]) for m in cat.medidas()}
    # Las fórmulas que el modelo YA tiene, normalizadas. Un modelo con
    # «Ventas Mercado USD = SUM(Mercado[VentasUSD])» no necesita un «Total
    # VentasUSD» con exactamente el mismo DAX: el nombre difiere, la medida
    # es la misma, y el nombre que ya está es el que eligió quien armó el
    # modelo. Duplicarla es además lo que el propio analizador denuncia
    # (R05), así que sugerirla sería mandar al usuario a romper su archivo.
    formulas = {_formula(m.get("expresion", "")) for m in cat.medidas()}
    # Fórmula → nombre de la medida que ya la calcula. Sirve para APOYARSE
    # en lo que el modelo tiene en vez de reescribirlo: un acumulado se
    # sugiere como `TOTALYTD ( [Ventas Mercado USD], … )` y no como
    # `TOTALYTD ( SUM ( Mercado[VentasUSD] ), … )`. Son el mismo número,
    # pero la primera forma es la que el modelo ya usa —así el dedupe de
    # `proponer` la reconoce como repetida— y, cuando NO es repetida, deja
    # una medida encadenada en vez de una copia de la lógica base.
    por_formula = {_formula(m.get("expresion", "")): m["nombre"]
                   for m in cat.medidas()}

    def base_de(expresion: str) -> str:
        """`[Medida]` si el modelo ya calcula esa expresión; si no, la misma."""
        nombre = por_formula.get(_formula(expresion))
        return f"[{nombre}]" if nombre else expresion

    def ya_hay_variacion(base: str) -> bool:
        """¿El modelo ya compara esa base contra el año anterior?

        La comparación de fórmulas no alcanza acá: dos variaciones pueden
        dar el MISMO número escritas distinto —una nombrando la medida `AA`
        del modelo y la otra inlineando su `CALCULATE`—, y sugerir la
        segunda deja dos nombres para un solo número. Se busca por firma:
        una medida que divida una diferencia y que, siguiendo la cadena de
        medidas que llama, termine en `SAMEPERIODLASTYEAR` sobre esta base.
        """
        from .analizador import _cadena_dax
        if not base.startswith("["):
            return False
        for m in cat.medidas():
            expr = m.get("expresion") or ""
            if base not in expr or "DIVIDE" not in expr.upper():
                continue
            if "SAMEPERIODLASTYEAR" in _cadena_dax(cat, m["nombre"]).upper():
                return True
        return False

    def proponer(nombre, dax, formato, clave_por_que, **datos):
        if _norm(nombre) in existentes:
            return
        if _formula(dax) in formulas:
            return          # ya existe, con otro nombre
        if validar_referencias(dax, cat):
            return          # referencia algo que no existe: no sale
        formulas.add(_formula(dax))
        existentes.add(_norm(nombre))
        sugerencias.append({
            "nombre": nombre, "dax": dax, "formato": formato,
            "por_que": traducir(clave_por_que, idioma).format(**datos)})

    principal = None      # (tabla, columna) del importe más creíble
    for t in _hechos(cat):
        numericas = [c for c in t["columnas"]
                     if c["tipo"] in TIPOS_NUMERICOS and not c["oculta"]
                     and not _clave(c["nombre"])]
        for c in numericas[:_MAX_TOTALES]:
            ref = _ref(t["nombre"], c["nombre"])
            formato = "#,0.00" if c["tipo"] in ("double", "decimal") \
                else "#,0"
            proponer(
                traducir("kpi_total", idioma).format(col=c["nombre"]),
                f"SUM ( {ref} )", formato, "kpi_pq_total",
                col=c["nombre"], tabla=t["nombre"])
            if principal is None and _es_importe(c["nombre"]):
                principal = (t["nombre"], c["nombre"])

        importe = next((c for c in numericas if _es_importe(c["nombre"])),
                       None)
        costo = next((c for c in numericas if _es_costo(c["nombre"])), None)
        if importe and costo:
            ri = _ref(t["nombre"], importe["nombre"])
            rc = _ref(t["nombre"], costo["nombre"])
            margen = traducir("kpi_margen", idioma)
            proponer(margen, f"SUM ( {ri} ) - SUM ( {rc} )", "#,0.00",
                     "kpi_pq_margen", importe=importe["nombre"],
                     costo=costo["nombre"])
            proponer(
                traducir("kpi_margen_pct", idioma),
                f"DIVIDE ( SUM ( {ri} ) - SUM ( {rc} ), SUM ( {ri} ) )",
                "0.0 %", "kpi_pq_margen_pct", importe=importe["nombre"])

        proponer(
            traducir("kpi_operaciones", idioma).format(tabla=t["nombre"]),
            f"COUNTROWS ( {_tabla_ref(t['nombre'])} )",
            "#,0", "kpi_pq_operaciones", tabla=t["nombre"])

        for r in cat.relaciones:
            if _norm(r["desde_tabla"]) != _norm(t["nombre"]):
                continue
            dim = next((x for x in cat.tablas
                        if _norm(x["nombre"]) == _norm(r["hacia_tabla"])),
                       None)
            if not dim or dim["es_calendario"] or dim["interna"]:
                continue
            proponer(
                traducir("kpi_unicos", idioma).format(
                    dim=dim["nombre"], tabla=t["nombre"]),
                f"DISTINCTCOUNT ( {_ref(t['nombre'], r['desde_col'])} )",
                "#,0", "kpi_pq_unicos", dim=dim["nombre"],
                tabla=t["nombre"])

    # ---- «¿CUÁL?» — las preguntas que un número no contesta -----------
    # Un tablero responde «cuánto» con medidas y «cuál» obligando a leer
    # una tabla ordenada. `CONCATENATEX ( TOPN ( 1, … ) )` lo contesta en
    # una tarjeta, y se recalcula con el filtro: cambia si el usuario
    # elige otro año o segmento, que es la diferencia entre un tablero y
    # una captura de pantalla.
    principales_med = [m["nombre"] for m in cat.medidas()
                       if not _es_texto_dax(m.get("expresion", ""))][:_MAX_CUAL]
    for dim in cat.tablas:
        if dim["es_calendario"] or dim["interna"]:
            continue
        etiqueta = _columna_etiqueta(dim)
        if not etiqueta:
            continue
        ref_dim = _ref(dim["nombre"], etiqueta)
        for nombre_med in principales_med:
            proponer(
                traducir("kpi_cual", idioma).format(
                    dim=etiqueta, medida=nombre_med),
                f"CONCATENATEX (\n"
                f"    TOPN ( 1, VALUES ( {ref_dim} ), [{nombre_med}], DESC ),\n"
                f"    {ref_dim}, \", \"\n)",
                "General", "kpi_pq_cual", dim=etiqueta, medida=nombre_med)

    fecha = cat.columna_fecha()
    if fecha and principal:
        rf = _ref(*fecha)
        rp = _ref(*principal)
        # El acumulado y la variación se apoyan en la medida base que el
        # modelo YA tiene, si la tiene. Sin esto se sugería un
        # «Total VentasUSD YTD» idéntico en valor al «Ventas Mercado USD
        # YTD» del modelo: dos nombres para el mismo número, que es
        # exactamente lo que un tablero no puede tener.
        suma = base_de(f"SUM ( {rp} )")
        base = traducir("kpi_total", idioma).format(col=principal[1])
        proponer(
            traducir("kpi_ytd", idioma).format(base=base),
            f"TOTALYTD ( {suma}, {rf} )", "#,0.00", "kpi_pq_ytd",
            base=base)
        if not ya_hay_variacion(suma):
            from .periodos import dax_var_comparable
            proponer(
                traducir("kpi_vs_aa", idioma).format(base=base),
                dax_var_comparable(suma, fecha[0], fecha[1]),
                "0.0 %", "kpi_pq_vs_aa", base=base)
    return sugerencias


# Qué medida merece una TARJETA en la portada del tablero. Las señales son
# del nombre y del formato — lo único que se puede leer sin ejecutar el
# modelo — y están ordenadas por lo que un gerente mira primero.
_PESO_NOMBRE = [
    (("total", "ventas", "importe", "facturacion", "revenue", "sales",
      "receita", "monto"), 100),
    (("margen", "margin", "margem", "rentabilidad"), 90),
    (("share", "participacion", "cuota", "penetracion", "cobertura"), 85),
    (("ytd", "acumulado"), 60),
    (("vs ", "variacion", "crecimiento", "growth"), 55),
    (("tasa", "rate", "conversion", "apertura", "efectividad"), 70),
    (("unicos", "distintos", "clientes", "activos"), 65),
    (("operaciones", "cantidad", "conteo", "count", "volumen"), 50),
]


def principales(cat: Catalogo, n: int = 5,
                entre: list[str] | set[str] | None = None) -> list[str]:
    """Los `n` KPIs que van a las tarjetas del tablero, en orden.

    El generador de tableros tomaba «las primeras 5 medidas del modelo»,
    que es el orden en que quedaron guardadas: podía poner adelante un
    contador auxiliar y dejar afuera las ventas. Acá se eligen por lo que
    la medida ES, con dos criterios que se pueden explicar: qué mide
    (nombre) y cómo se muestra (un porcentaje es un indicador, un entero
    suelto suele ser un conteo de apoyo).
    """
    # `entre` acota la elección a un subconjunto —las medidas de UNA tabla
    # de hechos, para armar su página— sin duplicar el criterio de orden.
    permitidas = {_norm(x) for x in entre} if entre is not None else None
    # Con empresa propia conocida, «Share Empresa %» es el indicador de
    # tarjeta; el share por contexto sin ese filtro da 100 % en una
    # tarjeta sin corte y no puede ir adelante.
    propia = _norm(cat.anotaciones.get("MVDAX_EmpresaPropia", "") or "")
    puntuadas: list[tuple[float, int, str]] = []
    for i, m in enumerate(cat.medidas()):
        if permitidas is not None and _norm(m["nombre"]) not in permitidas:
            continue
        nombre = _norm(m["nombre"])
        puntaje = 0.0
        for marcas, peso in _PESO_NOMBRE:
            if any(p in nombre for p in marcas):
                puntaje = max(puntaje, peso)
        if propia and "share" in nombre:
            puntaje += 8 if propia in nombre else -8
        formato = (m.get("formato") or "")
        if "%" in formato:
            puntaje += 15          # un porcentaje es un indicador, no un dato
        elif "$" in formato or "#,0.00" in formato:
            puntaje += 10
        if not puntaje:
            puntaje = 10           # sirve de relleno si no hay mejores
        # El orden del modelo desempata: es el que eligió quien lo armó.
        puntuadas.append((-puntaje, i, m["nombre"]))
    puntuadas.sort()
    return [nombre for _p, _i, nombre in puntuadas[:n]]


def agregar_kpis(modelo: dict,
                 idioma: str = IDIOMA_DEFECTO,
                 nombres: list[str] | set[str] | None = None
                 ) -> tuple[dict, list[str]]:
    """Agrega al modelo los KPIs sugeridos que no existan todavía.

    Es la acción detrás de «sugerí y agregá los KPIs» del intérprete.

    `nombres`: si se pasa, SOLO esos — es lo que permite aprobar las
    sugerencias una por una desde la pantalla en vez de todo o nada.
    Con `None` se agregan todas.

    Corre en PASADAS hasta que no queda nada nuevo. Hay sugerencias de
    segundo orden —«¿cuál producto tiene más ventas?» necesita que exista
    la medida de ventas— que en un modelo sin medidas no se pueden ni
    proponer ni validar. Sin las pasadas, correr la acción dos veces
    seguidas daba resultados distintos, y el usuario no tiene por qué
    saber que hay que insistir.
    """
    from . import transformador
    cambios: list[str] = []
    elegidos = {_norm(n) for n in nombres} if nombres is not None else None
    for _ in range(_MAX_PASADAS):
        sugerencias = sugerir(Catalogo.desde_modelo(modelo), idioma)
        if elegidos is not None:
            sugerencias = [s for s in sugerencias
                           if _norm(s["nombre"]) in elegidos]
        if not sugerencias:
            break
        for s in sugerencias:
            modelo, c = transformador.agregar_medida(
                modelo, s["nombre"], s["dax"], formato=s["formato"],
                descripcion=s["por_que"], idioma=idioma)
            cambios.extend(c)
    if not cambios:
        return modelo, [traducir("kpi_nada", idioma)]
    return modelo, cambios
