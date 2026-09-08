# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Lo que se puede MEDIR del archivo, no describir.

El informe ya contaba qué hay adentro de un modelo: tablas, relaciones,
Power Query, medidas, páginas. Contar no es auditar. Este módulo agrega
lo que un analista senior hace antes de creerle a un tablero:

  · **Integridad referencial.** Cuántas claves del lado muchos no existen
    del lado uno. Una relación con huérfanos no falla: manda esas filas a
    un miembro «en blanco» que nadie mira, y el total del informe queda
    por debajo del total real sin que nada lo avise.
  · **Cifras de control.** El valor calculado de cada medida que se puede
    reproducir sin motor DAX. Es contra lo que se valida un tablero: si
    la tarjeta no da este número, hay un filtro de más o de menos.
  · **Decisiones de modelado, justificadas.** Por qué esta columna está
    oculta, por qué esta relación está inactiva, por qué aquella tabla no
    se relaciona con nada. Un informe que las lista sin explicarlas
    obliga a adivinar si son decisiones o descuidos.
  · **Concentración.** Qué porción del negocio hacen los primeros diez.

Todo sale de las FILAS que viajan adentro del archivo. Cuando no hay
datos empotrados, cada función devuelve vacío y el informe lo dice — no
se estima, no se infiere, no se rellena.
"""
from __future__ import annotations

import re

from .catalogo import Catalogo, _norm

# Con menos filas que esto, un porcentaje de huérfanos no significa nada
# y ponerlo en un informe es darle peso a un accidente.
MINIMO_FILAS = 5


def _indice(cols: list[str]) -> dict[str, int]:
    return {_norm(c): i for i, c in enumerate(cols)}


def _columna(datos, tabla: str, columna: str) -> list | None:
    """Los valores de una columna, o `None` si no viajan en el archivo."""
    for nombre, (cols, filas) in (datos or {}).items():
        if _norm(nombre) != _norm(tabla):
            continue
        i = _indice(cols).get(_norm(columna))
        if i is None:
            return None
        return [f[i] if i < len(f) else None for f in filas]
    return None


# ==========================================================================
# 1 · Integridad referencial
# ==========================================================================
def integridad(cat: Catalogo, datos: dict) -> list[dict]:
    """Por relación: huérfanos, claves repetidas del lado uno y vacíos.

    Las tres cosas que rompen un total sin dar error. El huérfano manda
    filas a un miembro en blanco; la clave repetida del lado uno hace que
    Power BI rechace la relación o multiplique filas; el vacío en la
    clave es una fila que no se suma a ningún grupo.
    """
    salida = []
    for r in cat.relaciones:
        muchos = _columna(datos, r["desde_tabla"], r["desde_col"])
        uno = _columna(datos, r["hacia_tabla"], r["hacia_col"])
        if muchos is None or uno is None or len(muchos) < MINIMO_FILAS:
            continue
        validos = {v for v in uno if v is not None and v != ""}
        vacios = sum(1 for v in muchos if v is None or v == "")
        huerfanos = sum(1 for v in muchos
                        if v not in validos and v is not None and v != "")
        sin_vacios = [v for v in uno if v is not None and v != ""]
        repetidas = len(sin_vacios) - len(set(sin_vacios))
        salida.append({
            "desde": f'{r["desde_tabla"]}[{r["desde_col"]}]',
            "hacia": f'{r["hacia_tabla"]}[{r["hacia_col"]}]',
            "filas": len(muchos),
            "huerfanos": huerfanos,
            "vacios": vacios,
            "repetidas_uno": repetidas,
            "limpia": huerfanos == 0 and vacios == 0 and repetidas == 0,
        })
    return salida


# ==========================================================================
# 2 · Cifras de control
# ==========================================================================
# Las cuatro formas de medida que se pueden reproducir sin motor DAX. No
# hay más a propósito: el objetivo es dar números CIERTOS contra los que
# validar el tablero, y una aproximación sería peor que no dar nada.
_PATRONES = (
    ("suma", re.compile(
        r"^\s*SUM\s*\(\s*'?([^'\[\]]+?)'?\s*\[\s*([^\]]+?)\s*\]\s*\)\s*$",
        re.IGNORECASE)),
    ("promedio", re.compile(
        r"^\s*AVERAGE\s*\(\s*'?([^'\[\]]+?)'?\s*\[\s*([^\]]+?)\s*\]\s*\)\s*$",
        re.IGNORECASE)),
    ("distintos", re.compile(
        r"^\s*DISTINCTCOUNT\s*\(\s*'?([^'\[\]]+?)'?\s*\[\s*([^\]]+?)\s*\]"
        r"\s*\)\s*$", re.IGNORECASE)),
    ("filas", re.compile(
        r"^\s*COUNTROWS\s*\(\s*'?([^'\[\]]+?)'?\s*\)\s*$", re.IGNORECASE)),
)


def numero(v) -> float | None:
    """El valor como número, o `None` si no lo es.

    Los datos empotrados viajan como TEXTO —el M los tipa después, con
    `Table.TransformColumnTypes`— así que pedir `isinstance(v, float)`
    daba cero en todas las sumas. La cultura del empotrado es `en-US`
    (`dataset._CULTURA_EMBEBIDA`), así que el separador decimal es el
    punto: convertir con `float` es correcto, no una suposición.
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _numeros(valores) -> list[float]:
    return [n for n in (numero(v) for v in valores or []) if n is not None]


def cifras_control(cat: Catalogo, datos: dict) -> list[dict]:
    """El valor de cada medida que se puede reproducir sin motor DAX.

    Es la tabla contra la que se valida el tablero: si una tarjeta no da
    este número sin filtros, sobra o falta un filtro. Las medidas con
    CALCULATE, inteligencia de tiempo o razones NO están — decir «no la
    pude calcular» es información; inventarle un valor aproximado no.
    """
    salida = []
    for m in cat.medidas():
        expr = (m.get("expresion") or "").strip()
        for clase, patron in _PATRONES:
            mm = patron.match(expr)
            if not mm:
                continue
            tabla = mm.group(1).strip()
            valor = None
            if clase == "filas":
                datos_t = (datos or {}).get(tabla)
                if datos_t is None:
                    for n, d in (datos or {}).items():
                        if _norm(n) == _norm(tabla):
                            datos_t = d
                            break
                valor = len(datos_t[1]) if datos_t else None
            else:
                col = _columna(datos, tabla, mm.group(2).strip())
                if col is not None:
                    if clase == "suma":
                        valor = sum(_numeros(col))
                    elif clase == "promedio":
                        nums = _numeros(col)
                        valor = sum(nums) / len(nums) if nums else None
                    else:
                        valor = len({v for v in col
                                     if v is not None and v != ""})
            if valor is not None:
                salida.append({"medida": m["nombre"], "clase": clase,
                               "valor": valor,
                               "formato": m.get("formato") or ""})
            break
    return salida


def medidas_gemelas(cifras: list[dict]) -> list[dict]:
    """Medidas distintas que devuelven EXACTAMENTE el mismo número.

    No es un empate casual: sale de evaluar las dos contra los datos
    reales. Pasa cuando una tabla trae una columna que vale 1 en todas
    las filas —un `Visitas[Visitas]` o un `Enviado` que marca «sí»— y el
    modelo termina con `SUM ( T[col] )` y `COUNTROWS ( T )` conviviendo:
    el mismo número con dos nombres, que es la forma más barata de que
    dos tableros del mismo informe se contradigan sin que nadie note por
    qué. Se reporta, no se corrige solo: cuál de los dos nombres sobra lo
    decide quien conoce el negocio.

    Sólo mira las medidas que `cifras_control` pudo calcular, y descarta
    el valor 0 —donde coincidir no dice nada.
    """
    por_valor: dict[float, list[str]] = {}
    for c in cifras:
        valor = c.get("valor")
        if valor in (None, 0):
            continue
        por_valor.setdefault(round(float(valor), 6), []).append(c["medida"])
    return [{"valor": v, "medidas": sorted(ms)}
            for v, ms in sorted(por_valor.items()) if len(ms) > 1]


# ==========================================================================
# 3 · Decisiones de modelado, con su porqué
# ==========================================================================
def _duplica_dimension(cat: Catalogo, tabla: str, columna: str) -> str:
    """`Dim[Col]` visible con el mismo nombre, si la hay al otro lado.

    Es el ocultamiento MÁS defendible de todos y el que más cuesta
    explicar sin el dato a mano: una tabla de hechos desnormalizada
    arrastra la especialidad del médico, y la dimensión Médico la tiene
    también. Los dos campos se llaman igual y filtran distinto.
    """
    vecinas = {r["hacia_tabla"] for r in cat.relaciones
               if _norm(r["desde_tabla"]) == _norm(tabla)}
    for otra in vecinas:
        for t, c in cat.columnas():
            if (_norm(t) == _norm(otra) and _norm(c["nombre"]) == _norm(columna)
                    and not c.get("oculta")):
                return f'{t}[{c["nombre"]}]'
    return ""


def _ordena_a(cat: Catalogo, tabla: str, columna: str) -> str:
    """`Tabla[Col]` que se ordena POR esta columna, si existe.

    La marca vive en la columna visible («Mes ordena por MesNumero»), no
    en la oculta, así que hay que buscarla al revés.
    """
    for t, c in cat.columnas():
        if (_norm(t) == _norm(tabla)
                and _norm(c.get("orden_por") or "") == _norm(columna)):
            return f'{t}[{c["nombre"]}]'
    return ""


def _tiene_medida(cat: Catalogo, tabla: str, columna: str) -> bool:
    """¿Alguna medida ya agrega esa columna?"""
    aguja = f"{_norm(tabla)}[{_norm(columna)}]"
    for m in cat.medidas():
        expr = _norm(m.get("expresion") or "")
        if aguja in expr or f"[{_norm(columna)}]" in expr and _norm(tabla) in expr:
            return True
    return False


def decisiones(cat: Catalogo) -> list[dict]:
    """Por qué el modelo está como está, objeto por objeto.

    Un informe que lista las columnas ocultas y las relaciones inactivas
    sin explicarlas obliga al que lo lee a adivinar si son decisiones o
    descuidos — y en la duda las «arregla», que es peor. Cada línea de acá
    dice qué se hizo, por qué, y qué pasaría si se deshiciera.
    """
    salida = []
    claves_muchos = {(_norm(r["desde_tabla"]), _norm(r["desde_col"]))
                     for r in cat.relaciones}
    claves_uno = {(_norm(r["hacia_tabla"]), _norm(r["hacia_col"]))
                  for r in cat.relaciones}
    for tabla, c in cat.columnas():
        if not c.get("oculta"):
            continue
        par = (_norm(tabla), _norm(c["nombre"]))
        if par in claves_muchos or par in claves_uno:
            salida.append({
                "objeto": f'{tabla}[{c["nombre"]}]', "que": "columna oculta",
                "porque": "es la clave de una relación: el filtro viaja "
                          "igual con la columna oculta, y mostrarla invita "
                          "a agrupar por un identificador que no dice nada "
                          "en un informe.",
                "si_se_deshace": "aparece en el panel de campos una columna "
                                 "que sólo genera gráficos por ID."})
        elif _ordena_a(cat, tabla, c["nombre"]):
            quien = _ordena_a(cat, tabla, c["nombre"])
            salida.append({
                "objeto": f'{tabla}[{c["nombre"]}]', "que": "columna oculta",
                "porque": f"es la que ordena a {quien}. Existe para que "
                          "«marzo» vaya después de «febrero» y no en orden "
                          "alfabético; su valor —un número de orden— no es "
                          "una lectura de negocio.",
                "si_se_deshace": "el panel ofrece dos campos donde hay un "
                                 "solo concepto, y agrupar por el número "
                                 "da un eje sin etiquetas."})
        elif _duplica_dimension(cat, tabla, c["nombre"]):
            otra = _duplica_dimension(cat, tabla, c["nombre"])
            salida.append({
                "objeto": f'{tabla}[{c["nombre"]}]', "que": "columna oculta",
                "porque": f'el mismo dato ya está en {otra}, que es su '
                          "dimensión. Dejar las dos visibles pone dos campos "
                          "con el mismo nombre en el panel, y NO son "
                          f'intercambiables: el de {tabla} sólo filtra esa '
                          "tabla de hechos, así que un informe abierto por "
                          "uno u otro da números distintos sin que se vea "
                          "por qué.",
                "si_se_deshace": "dos campos homónimos que producen "
                                 "resultados distintos: el error más difícil "
                                 "de encontrar en un informe."})
        elif _tiene_medida(cat, tabla, c["nombre"]):
            salida.append({
                "objeto": f'{tabla}[{c["nombre"]}]', "que": "columna oculta",
                "porque": "ya hay una medida que la agrega con la lógica "
                          "correcta. Si la columna queda a la vista, "
                          "arrastrarla al visual produce una suma implícita "
                          "que ignora esa lógica.",
                "si_se_deshace": "conviven la medida y la suma automática de "
                                 "la columna, y dan números distintos."})
        else:
            salida.append({
                "objeto": f'{tabla}[{c["nombre"]}]', "que": "columna oculta",
                "porque": "es una columna técnica o intermedia de un "
                          "cálculo: no responde ninguna pregunta de negocio "
                          "por sí sola.",
                "si_se_deshace": "suma ruido al panel de campos sin agregar "
                                 "una lectura nueva."})
    for r in cat.relaciones:
        nombre = (f'{r["desde_tabla"]}[{r["desde_col"]}] → '
                  f'{r["hacia_tabla"]}[{r["hacia_col"]}]')
        if not r.get("activa", True):
            salida.append({
                "objeto": nombre, "que": "relación inactiva",
                "porque": "entre las dos tablas ya hay un camino activo. "
                          "Dos caminos simultáneos serían ambiguos y Power "
                          "BI no deja guardar el modelo; ésta queda "
                          "disponible para usarla con USERELATIONSHIP en "
                          "la medida puntual que la necesite.",
                "si_se_deshace": "el modelo no abre: «ambigüedad en el "
                                 "camino de filtro»."})
        if r.get("bidireccional"):
            salida.append({
                "objeto": nombre, "que": "filtro en las dos direcciones",
                "porque": "alguna medida necesita que el lado uno se entere "
                          "del filtro del lado muchos.",
                "si_se_deshace": "esa medida deja de responder al filtro. "
                                 "Conviene volver a dirección simple y "
                                 "resolverlo con CROSSFILTER adentro de la "
                                 "medida: la bidireccional afecta a TODO el "
                                 "modelo, no sólo a donde hacía falta."})
    lados = {_norm(t) for r in cat.relaciones
             for t in (r["desde_tabla"], r["hacia_tabla"])}
    for t in cat.tablas:
        if t["interna"] or _norm(t["nombre"]) in lados:
            continue
        salida.append({
            "objeto": t["nombre"], "que": "tabla sin relaciones",
            "porque": "es un eje suelto (parámetros, etiquetas, el índice "
                      "de conclusiones) o quedó sin conectar. Si es un eje, "
                      "está bien así: relacionarla haría que elegir un "
                      "valor escondiera los datos del resto.",
            "si_se_deshace": "si NO era un eje, sus columnas no filtran "
                             "nada y cualquier gráfico por ellas muestra el "
                             "mismo total en cada fila."})
    return salida


# ==========================================================================
# 4 · Concentración
# ==========================================================================
def _hechos_de(cat: Catalogo, dim: str) -> list[tuple[str, str]]:
    """Las tablas de hechos colgadas de esta dimensión, con su clave."""
    return [(r["desde_tabla"], r["desde_col"]) for r in cat.relaciones
            if _norm(r["hacia_tabla"]) == _norm(dim) and r.get("activa", True)]


def cruce(cat: Catalogo, datos: dict, dimension: tuple[str, str],
          top: int = 12) -> dict | None:
    """Todo lo que le pasa a un mismo miembro, en una sola tabla.

    Un informe puede tener una página de visitas, otra de recetas y otra
    de digital y no responder la única pregunta que decide el
    presupuesto: **¿el esfuerzo está puesto donde rinde?** Para eso hay
    que traer las tres tablas de hechos al mismo renglón del médico y
    dividir por la cantidad de médicos del grupo — sin normalizar, el
    grupo más grande siempre parece el mejor.

    Devuelve, por cada valor de la dimensión: cuántos miembros tiene y,
    por cada tabla de hechos colgada de ella, el total y el promedio por
    miembro.
    """
    tabla_d, col_d = dimension
    etiquetas = _columna(datos, tabla_d, col_d)
    if not etiquetas:
        return None
    clave_dim = next((r["hacia_col"] for r in cat.relaciones
                      if _norm(r["hacia_tabla"]) == _norm(tabla_d)), None)
    ids = _columna(datos, tabla_d, clave_dim) if clave_dim else None
    if not ids or len(ids) != len(etiquetas):
        return None
    grupo_de = {str(i): e for i, e in zip(ids, etiquetas)}
    miembros: dict[str, int] = {}
    for e in etiquetas:
        miembros[str(e)] = miembros.get(str(e), 0) + 1

    columnas = []
    for hechos, clave in _hechos_de(cat, tabla_d):
        t = cat.tabla(hechos)
        if not t or hechos not in (datos or {}):
            continue
        claves = _columna(datos, hechos, clave)
        if not claves:
            continue
        # La columna numérica de mayor suma es la que mide ese hecho:
        # PXs en recetas, visitas en visitas, enviados en digital.
        mejor, suma_mejor = None, 0.0
        for c in t["columnas"]:
            if c["tipo"] not in ("int64", "double", "decimal"):
                continue
            if re.search(r"(id$|^id|orden|anio|año|year)", c["nombre"],
                         re.IGNORECASE):
                continue
            vals = _numeros(_columna(datos, hechos, c["nombre"]))
            if sum(vals) > suma_mejor:
                mejor, suma_mejor = c["nombre"], sum(vals)
        valores = (_columna(datos, hechos, mejor) if mejor
                   else [1] * len(claves))
        acum: dict[str, float] = {}
        for k, v in zip(claves, valores):
            g = grupo_de.get(str(k))
            n = numero(v)
            if g is not None and n is not None:
                acum[str(g)] = acum.get(str(g), 0.0) + n
        if acum:
            columnas.append({"hechos": hechos, "columna": mejor or "filas",
                             "por_grupo": acum})
    if len(columnas) < 2:
        return None
    orden = sorted(miembros, key=lambda g: -sum(
        c["por_grupo"].get(g, 0.0) for c in columnas))
    return {"dimension": f"{tabla_d}[{col_d}]", "miembros": miembros,
            "columnas": columnas, "grupos": orden[:top]}


def desalineacion(res: dict | None) -> dict | None:
    """¿El esfuerzo está puesto donde NO rinde?

    De las tablas cruzadas, la de **resultado** es la que más varía entre
    grupos —lo que distingue a un grupo de otro es cuánto produce, no
    cuánto se le dedica— y las demás son **esfuerzo**. Si el grupo que
    menos produce recibe tanto o más esfuerzo por miembro que el que más
    produce, eso es plata puesta donde no vuelve, y es la única
    conclusión de un informe que cambia un presupuesto.

    Devuelve `None` cuando no hay desalineación: no forzar un hallazgo
    es parte de que el hallazgo valga algo cuando aparece.
    """
    if not res or len(res["grupos"]) < 2 or len(res["columnas"]) < 2:
        return None

    def por_miembro(col, g):
        n = res["miembros"].get(g, 0)
        return col["por_grupo"].get(g, 0.0) / n if n else 0.0

    def dispersion(col):
        vals = [por_miembro(col, g) for g in res["grupos"]]
        vals = [v for v in vals if v > 0]
        return (max(vals) / min(vals)) if len(vals) > 1 and min(vals) else 0.0

    resultado = max(res["columnas"], key=dispersion)
    if dispersion(resultado) < 1.5:
        return None
    esfuerzos = [c for c in res["columnas"] if c is not resultado]
    orden = sorted(res["grupos"], key=lambda g: -por_miembro(resultado, g))
    mejor, peor = orden[0], orden[-1]
    culpables = []
    for c in esfuerzos:
        if por_miembro(c, peor) >= por_miembro(c, mejor):
            culpables.append({
                "hechos": c["hechos"],
                "en_el_peor": por_miembro(c, peor),
                "en_el_mejor": por_miembro(c, mejor)})
    if not culpables:
        return None
    return {
        "dimension": res["dimension"], "mejor": mejor, "peor": peor,
        "resultado": resultado["hechos"],
        "veces": (por_miembro(resultado, mejor)
                  / por_miembro(resultado, peor)
                  if por_miembro(resultado, peor) else 0.0),
        "rinde_mejor": por_miembro(resultado, mejor),
        "rinde_peor": por_miembro(resultado, peor),
        "esfuerzos": culpables,
    }


def _por_relacion(cat: Catalogo, datos: dict, hechos: str, dim: str,
                  etiqueta: str) -> list | None:
    """La etiqueta de la dimensión, fila por fila de la tabla de hechos.

    Un solo salto de relación: alcanza para el esquema estrella, que es
    el caso que importa. Sin esto la concentración sólo podía abrirse por
    columnas que estuvieran DENTRO de la tabla de hechos, y terminaba
    eligiendo cortes que no le interesan a nadie —el año sumado por mes—
    en vez de las ventas por producto.
    """
    rel = next((r for r in cat.relaciones
                if _norm(r["desde_tabla"]) == _norm(hechos)
                and _norm(r["hacia_tabla"]) == _norm(dim)
                and r.get("activa", True)), None)
    if not rel:
        return None
    claves_dim = _columna(datos, dim, rel["hacia_col"])
    etiquetas = _columna(datos, dim, etiqueta)
    claves_hechos = _columna(datos, hechos, rel["desde_col"])
    if not claves_dim or not etiquetas or not claves_hechos:
        return None
    mapa = {str(k): e for k, e in zip(claves_dim, etiquetas)}
    return [mapa.get(str(k)) for k in claves_hechos]


def concentracion(cat: Catalogo, datos: dict, dimension: tuple[str, str],
                  columna_valor: tuple[str, str],
                  top: int = 10) -> dict | None:
    """Cuánto del total hacen los primeros `top` de una dimensión.

    El número que decide dónde se pone el esfuerzo comercial. Requiere que
    la dimensión y el valor estén en la MISMA tabla — cruzar dos tablas
    sin motor de modelo sería reimplementar Power BI, y mal.
    """
    tabla_d, col_d = dimension
    tabla_v, col_v = columna_valor
    valores = _columna(datos, tabla_v, col_v)
    if not valores:
        return None
    if _norm(tabla_d) == _norm(tabla_v):
        claves = _columna(datos, tabla_d, col_d)
    else:
        claves = _por_relacion(cat, datos, tabla_v, tabla_d, col_d)
    if not claves or len(claves) != len(valores):
        return None
    acumulado: dict[str, float] = {}
    sin_clave = 0.0
    for k, v in zip(claves, valores):
        n = numero(v)
        if n is None:
            continue
        # Una fila cuya clave no cruza NO es un miembro llamado «None»:
        # Power BI la manda a un miembro en blanco. Contarla aparte es lo
        # honesto — inventarle una categoría la deja como si fuera un
        # país más, con su porcentaje y todo.
        if k is None or str(k).strip() == "":
            sin_clave += n
            continue
        acumulado[str(k)] = acumulado.get(str(k), 0.0) + n
    if not acumulado:
        return None
    total = sum(acumulado.values())
    orden = sorted(acumulado.items(), key=lambda x: -x[1])
    cabeza = orden[:top]
    return {
        "dimension": f"{tabla_d}[{col_d}]",
        "valor": f"{tabla_v}[{col_v}]",
        "total": total,
        "sin_clave": sin_clave,
        "miembros": len(acumulado),
        "top": [{"clave": k, "valor": v,
                 "parte": (v / total) if total else 0.0} for k, v in cabeza],
        "parte_top": (sum(v for _k, v in cabeza) / total) if total else 0.0,
    }
