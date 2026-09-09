# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · La lectura del informe: qué significa cada página, en DAX.

Un tablero muestra números; no dice qué hacer con ellos. Este módulo
escribe, por cada página del reporte, una medida de TEXTO que responde
tres preguntas de un analista sentado al lado:

  1. Qué mide esta página y cuánto da hoy.
  2. Mejor o peor que el mismo período del año anterior, y por cuánto.
  3. Contra el mercado —si el modelo lo tiene—: si crecimos por encima
     ganamos participación, y si crecimos por debajo la perdimos aunque
     el número propio suba. Con la acción que se desprende de eso.

**En DAX y no en texto fijo.** La conclusión tiene que recalcularse
cuando alguien elige otro año, otro mes o una categoría; un cartel
escrito al exportar dice lo de ese día y miente en cuanto se toca un
filtro. Por eso la lectura es una medida más del modelo.

**Nunca inventa.** Si no hay tabla de fechas, no hay comparación contra
el año anterior y la medida lo dice con todas las letras en vez de
mostrar un cero. Si no hay medida de mercado, no habla de participación.
"""
from __future__ import annotations

from .catalogo import Catalogo, validar_referencias
from .i18n import IDIOMA_DEFECTO

# El prefijo con el que el generador de tableros reconoce estas medidas.
PREFIJO = "Lectura · "
CARPETA = "Análisis"

# Palabras que delatan una medida de mercado/competencia. Duplicadas a
# propósito de `tablero._MERCADO`: son dos decisiones distintas —una pinta
# series, la otra elige con quién compararse— y atarlas hace que tocar el
# color cambie el texto de las conclusiones.
_MERCADO = ("mercado", "mercados", "market", "markets", "industria",
            "industrias", "competencia", "competidor", "competidores",
            "competitor", "competitors")


def _fichas(nombre: str) -> set[str]:
    from .catalogo import _norm
    return set(_norm(nombre).replace("_", " ").split())


def _es_del_mercado(nombre: str) -> bool:
    return bool(_fichas(nombre) & set(_MERCADO))


def _es_porcentual(nombre: str) -> bool:
    bajo = nombre.lower().strip()
    return bajo.endswith(("%", " pp", "share")) or "share" in bajo


def _formato_de(nombre: str) -> str:
    """Con qué máscara se escribe el valor dentro de la frase."""
    return "0.0 %" if _es_porcentual(nombre) else "#,##0"


def _anterior_de(nombre: str, cat: Catalogo) -> str | None:
    """La medida «mismo período del año anterior» que YA existe, si existe.

    Se prefiere la del modelo antes que fabricar un `SAMEPERIODLASTYEAR`
    propio: el autor pudo haberla definido sobre otra columna de fecha —
    la del cierre contable, por ejemplo— y su versión es la correcta.
    """
    objetivo = _fichas(nombre) | {"aa"}
    for m in cat.medidas():
        otro = m["nombre"]
        if otro == nombre:
            continue
        if _fichas(otro) == objetivo:
            return otro
    return None


def _variacion_del_mercado(nombre: str, cat: Catalogo) -> str | None:
    """La variación de la medida de mercado equivalente, si el modelo la trae.

    Es lo que permite decir «creciste, pero menos que el mercado»: sin
    ella la página informa que subimos y calla que perdimos terreno.
    """
    if _es_del_mercado(nombre):
        return None
    base = _fichas(nombre)
    mejor, mejor_p = None, 0
    for m in cat.medidas():
        otro = m["nombre"]
        fichas = _fichas(otro)
        if not (fichas & set(_MERCADO)) or "var" not in fichas:
            continue
        if not _es_porcentual(otro) or otro.lower().endswith("pp"):
            continue
        p = len(base & fichas)
        if p > mejor_p:
            mejor, mejor_p = otro, p
    if mejor_p >= 2:
        return mejor
    # Al menos dos palabras en común: con una sola, «Var Unidades
    # Mercado %» se aparea con cualquier medida que diga «Unidades». Pero
    # el umbral deja afuera el caso más común de todos —«Unidades Adium»
    # contra «Var Unidades Mercado %» comparten sólo «unidades», porque
    # la marca propia JAMÁS aparece en una medida de mercado—, así que
    # cuando el nombre no alcanza se pregunta por la estructura.
    return _por_la_formula(nombre, cat)


def _por_la_formula(nombre: str, cat: Catalogo) -> str | None:
    """El apareo con el mercado leído del DAX y no del nombre.

    Una medida propia suele DERIVAR de la de mercado —«Unidades Adium =
    CALCULATE ( [Unidades Mercado], … )»—, y esa llamada dice con
    precisión cuál es su contraparte: no hay que adivinarla por palabras
    compartidas. Es la señal más fuerte que hay, y por eso vale como
    desempate cuando el nombre no alcanza.
    """
    from .catalogo import referencias_dax

    m = cat.medida(nombre)
    if not m:
        return None
    llamadas = [n for n in referencias_dax(m.get("expresion") or "")["medidas"]
                if _es_del_mercado(n)]
    for base_mkt in llamadas:
        objetivo = _fichas(base_mkt) | {"var"}
        for otra in cat.medidas():
            fichas = _fichas(otra["nombre"])
            if objetivo <= fichas and _es_porcentual(otra["nombre"]) \
                    and not otra["nombre"].lower().endswith("pp"):
                return otra["nombre"]
    return None


# Sufijos de acumulación. Una lectura NO debe partir de uno: la frase ya
# se recalcula con el filtro de la página, así que leer un acumulado
# adentro mezcla dos nociones de período y dice «el trimestre creció»
# cuando el usuario está mirando un mes.
_ACUMULADOS = ("qtd", "ytd", "std", "mtd")


def _contraparte_propia(nombre: str, cat: Catalogo) -> str | None:
    """La medida PROPIA equivalente a una de mercado, si el modelo la trae.

    Una página armada sólo con medidas de mercado —«Ventas Mercado USD
    QTD», «Unidades Mercado YTD»…— dejaba a la lectura sin nada propio de
    donde agarrarse, y terminaba narrando cómo le fue AL MERCADO. La
    conclusión de un tablero de Adium tiene que hablar de Adium.

    Se busca la medida que comparte más palabras con la de mercado sin
    ser de mercado, y entre las candidatas gana la que NO acumula: la
    lectura ya se recalcula con el filtro de la página.
    """
    if not _es_del_mercado(nombre):
        return None
    # El acumulado NO se hereda: si la página de mercado leía un QTD, la
    # contraparte propia se busca por «ventas USD», no por «ventas USD
    # QTD». Sin sacarlo de la base, la medida acumulada ganaba por tener
    # una palabra más en común y volvíamos a leer un trimestre adentro de
    # una frase que ya responde al filtro de la página.
    base = _fichas(nombre) - set(_MERCADO) - set(_ACUMULADOS)
    mejor, mejor_p = None, 0
    for m in cat.medidas():
        otro = m["nombre"]
        if _es_del_mercado(otro) or _es_variacion_nombre(otro):
            continue
        fichas = _fichas(otro)
        p = len(base & fichas)
        # Sin acumulado gana siempre: se le suma medio punto para que
        # desempate contra el que comparte las mismas palabras y sí acumula.
        if not (fichas & set(_ACUMULADOS)):
            p += 0.5
        if p > mejor_p:
            mejor, mejor_p = otro, p
    # Al menos dos palabras en común, como en el apareo con el mercado.
    return mejor if mejor_p >= 2 else None


def _es_variacion_nombre(nombre: str) -> bool:
    from .tablero import _es_variacion
    return _es_variacion(nombre)


def _txt(cadena: str) -> str:
    """Un literal de texto DAX: las comillas dobles se duplican."""
    return '"' + cadena.replace('"', '""') + '"'


def dax_lectura(pagina: str, medida: str, *,
                anterior: str | None = None,
                fecha: tuple[str, str] | None = None,
                var_mercado: str | None = None) -> str:
    """El DAX de la lectura de una página.

    `anterior` es la medida del año anterior si el modelo la tiene;
    si no, se calcula con `SAMEPERIODLASTYEAR` sobre `fecha`. Sin
    ninguna de las dos, la medida devuelve el valor y dice explícitamente
    que no hay con qué compararlo — que es la verdad, no un cero.
    """
    fmt = _formato_de(medida)
    # Un share no varía «un 12 %»: varía puntos porcentuales. Y su cambio
    # ya CONTIENE la comparación contra el mercado —si el share sube es
    # porque crecimos más que él—, así que ponerle al lado la variación
    # del mercado dice dos veces lo mismo y a veces se contradice.
    porcentual = _es_porcentual(medida)
    if porcentual:
        var_mercado = None
    # `_val` es el valor que se MUESTRA: el del filtro tal cual, para que
    # coincida con lo que dice la tarjeta de al lado. La comparación usa
    # su propio par recortado —`_hoy` contra `_ant`—, porque las dos
    # puntas tienen que abarcar el mismo tramo de días.
    lineas = [f"VAR _val = [{medida}]"]
    # La medida `AA` del modelo se usa SÓLO si no hay columna de fecha.
    # Con fecha manda el recorte de ventana: una `AA` escrita con
    # `SAMEPERIODLASTYEAR` a secas arrastra la trampa del año incompleto,
    # y acá la trampa se convierte en una frase — «mejora 211,3 % contra
    # el mismo período del año anterior»— que es peor que el número
    # suelto. Lo destapó R19 sobre este mismo módulo.
    if fecha:
        # Sin esto la conclusión decía «mejora 211,3 % contra el mismo
        # período del año anterior» sobre un modelo que enfrentaba
        # dieciocho meses contra seis — una mentira escrita en palabras,
        # que es peor que un número raro en una tabla. Recortar las dos
        # puntas da la frase correcta en vez de callarse.
        tabla, col = fecha
        ref = f"'{tabla}'[{col}]"
        lineas.append(f"VAR _fechasAnt =\n"
                      f"    CALCULATETABLE ( VALUES ( {ref} ), "
                      f"SAMEPERIODLASTYEAR ( {ref} ) )")
        lineas.append(f"VAR _ant = CALCULATE ( [{medida}], _fechasAnt )")
        lineas.append(f"VAR _hoy =\n"
                      f"    CALCULATE ( [{medida}], "
                      f"DATEADD ( _fechasAnt, 1, YEAR ) )")
    elif anterior:
        lineas.append(f"VAR _ant = [{anterior}]")
        lineas.append("VAR _hoy = _val")
    else:
        lineas.append("VAR _ant = BLANK ()")
        lineas.append("VAR _hoy = _val")
    lineas.append("VAR _var = " + ("( _hoy - _ant ) * 100" if porcentual
                                   else "DIVIDE ( _hoy - _ant, _ant )"))
    lineas.append("VAR _comparable = "
                  "NOT ISBLANK ( _ant ) && _ant <> 0")
    lineas.append(f"VAR _mkt = {f'[{var_mercado}]' if var_mercado else 'BLANK ()'}")
    lineas.append(f"VAR _que = {_txt(medida + ': ')} & "
                  f'FORMAT ( _val, "{fmt}" )')
    lineas.append(
        "VAR _mov =\n"
        "    IF (\n"
        "        NOT _comparable,\n"
        f"        {_txt(' · no hay período anterior comparable con este filtro')},\n"
        f"        {_txt(' · ')} & IF ( _var >= 0, {_txt('mejora ')}, {_txt('cae ')} )\n"
        + ('            & FORMAT ( ABS ( _var ), "0.0" ) & " pp"\n' if porcentual
           else '            & FORMAT ( ABS ( _var ), "0.0 %" )\n')
        + f"            & {_txt(' contra el mismo período del año anterior')}\n"
        "    )")
    lineas.append(
        "VAR _rel =\n"
        "    IF (\n"
        f"        ISBLANK ( _mkt ) || NOT _comparable, {_txt('')},\n"
        f"        {_txt(' · el mercado ')} & IF ( _mkt >= 0, {_txt('creció ')}, "
        f"{_txt('cayó ')} )\n"
        '            & FORMAT ( ABS ( _mkt ), "0.0 %" )\n'
        f"            & IF ( _var >= _mkt, {_txt(', así que ganamos participación')},"
        f" {_txt(', así que perdemos participación')} )\n"
        "    )")
    cae = (' → perdemos participación: mirar precio y presencia donde el '
           'mercado crece y nosotros no') if porcentual else \
        " → dónde mirar: las categorías y zonas que más caen"
    lineas.append(
        "VAR _accion =\n"
        "    IF (\n"
        f"        NOT _comparable, {_txt('')},\n"
        "        IF (\n"
        f"            _var < 0, {_txt(cae)},\n"
        "            IF (\n"
        "                NOT ISBLANK ( _mkt ) && _var < _mkt,\n"
        f"                {_txt(' → dónde mirar: precio y presencia donde el mercado crece y nosotros no')},\n"
        f"                {_txt(' → sostener la inversión donde ya rinde y replicarla en lo rezagado')}\n"
        "            )\n"
        "        )\n"
        "    )")
    lineas.append(f"RETURN {_txt(pagina + ' — ')} & _que & _mov & _rel & _accion")
    return "\n".join(lineas)


def lecturas(cat: Catalogo, paginas: list[tuple[str, str]]
             ) -> list[dict]:
    """Una medida de lectura por página, validada contra el catálogo.

    `paginas` son pares (título de la página, medida protagonista). Lo
    que referencia algo que no existe no sale: antes que una página de
    análisis con medidas rotas, no hay página.
    """
    fecha = cat.columna_fecha()
    salida = []
    for pagina, medida in paginas:
        if not medida or cat.medida(medida) is None:
            continue
        dax = dax_lectura(
            pagina, medida,
            anterior=_anterior_de(medida, cat), fecha=fecha,
            var_mercado=_variacion_del_mercado(medida, cat))
        if validar_referencias(dax, cat):
            continue
        salida.append({
            "pagina": pagina,
            "nombre": PREFIJO + pagina,
            "dax": dax,
            "medida": medida,
        })
    return salida


def agregar_lecturas(modelo: dict, paginas: list[tuple[str, str]],
                     idioma: str = IDIOMA_DEFECTO
                     ) -> tuple[dict, list[dict]]:
    """Suma al modelo las medidas de lectura y devuelve sus descriptores.

    Devuelve el modelo (posiblemente modificado) y la lista de lecturas
    efectivamente agregadas, en el orden de las páginas.
    """
    from . import transformador

    cat = Catalogo.desde_modelo(modelo)
    propuestas = lecturas(cat, paginas)
    agregadas = []
    for p in propuestas:
        if cat.medida(p["nombre"]) is not None:
            agregadas.append(p)
            continue
        modelo, _ = transformador.agregar_medida(
            modelo, p["nombre"], p["dax"],
            descripcion=f"Lectura automática de la página «{p['pagina']}».",
            carpeta=CARPETA, idioma=idioma)
        agregadas.append(p)
    if agregadas:
        modelo = _armar_eje(modelo, [p["pagina"] for p in agregadas], idioma)
    return modelo, agregadas


def _armar_eje(modelo: dict, paginas: list[str],
               idioma: str = IDIOMA_DEFECTO) -> dict:
    """La tabla suelta de páginas y la medida que las recorre."""
    import copy

    from . import transformador

    modelo = copy.deepcopy(modelo)
    tablas = modelo.setdefault("model", {}).setdefault("tables", [])
    if not any(t.get("name") == TABLA_LECTURA for t in tablas):
        tablas.append(_tabla_lectura(paginas))
    cat = Catalogo.desde_modelo(modelo)
    if cat.medida(MEDIDA_UNICA) is None:
        dax = _dax_unica(paginas)
        if not validar_referencias(dax, cat):
            modelo, _ = transformador.agregar_medida(
                modelo, MEDIDA_UNICA, dax,
                descripcion="Muestra la conclusión de la página listada "
                            "en cada fila.",
                carpeta=CARPETA, idioma=idioma)
    return modelo


TABLA_LECTURA = "_Lectura"
COL_PAGINA = "Página"
COL_ORDEN = "Orden"
MEDIDA_UNICA = "Lectura del informe"


def _tabla_lectura(paginas: list[str]) -> dict:
    """Una tabla suelta con una fila por página, para poder LISTARLAS.

    Sin esto la única forma de mostrar cinco conclusiones era ponerlas
    como cinco medidas en una tarjeta, y la tarjeta las acomoda en
    columnas de 230 px: cada frase entraba cortada en la primera línea y
    la página no decía nada. Con una fila por página, el texto va en una
    celda de tabla —que sí ajusta— y se lee entero.

    Es una tabla DESCONECTADA a propósito: no filtra nada ni la filtra
    nadie, sólo da el eje sobre el que se recorren las conclusiones.
    """
    from . import dataset

    filas = [[i + 1, p] for i, p in enumerate(paginas)]
    return {
        "name": TABLA_LECTURA,
        "columns": [
            {"name": COL_ORDEN, "dataType": "int64",
             "sourceColumn": COL_ORDEN, "isHidden": True,
             "summarizeBy": "none", "formatString": "0"},
            {"name": COL_PAGINA, "dataType": "string",
             "sourceColumn": COL_PAGINA, "summarizeBy": "none",
             "sortByColumn": COL_ORDEN},
        ],
        "partitions": [{
            "name": TABLA_LECTURA, "mode": "import",
            "source": {"type": "m", "expression": dataset.m_embebido(
                [COL_ORDEN, COL_PAGINA], filas,
                {COL_ORDEN: "int64", COL_PAGINA: "string"})},
        }],
    }


def _dax_unica(paginas: list[str]) -> str:
    """La medida que elige qué conclusión mostrar en cada fila."""
    ramas = "".join(
        f"    {_txt(p)}, [{PREFIJO}{p}],\n" for p in paginas)
    return (f"SWITCH (\n    SELECTEDVALUE ( '{TABLA_LECTURA}'[{COL_PAGINA}] ),\n"
            f"{ramas}    BLANK ()\n)")


def _protagonista(tema: dict, existe, cat: Catalogo | None = None
                  ) -> str | None:
    """La medida que mejor representa a la página.

    Se prefiere un NIVEL antes que una variación: la lectura calcula ella
    misma el cambio contra el año anterior, y partir de «Var Ventas %»
    daría la variación de una variación, que no significa nada.
    """
    from .tablero import _es_variacion

    kpis = [n for n in (tema.get("kpis") or []) if existe(n)]
    niveles = [n for n in kpis if not _es_variacion(n)]
    # Lo PROPIO antes que el mercado: leer la página desde «Ventas
    # Mercado» deja fuera la única comparación que importa —cómo nos fue
    # a nosotros contra él— y la conclusión se queda sin la mitad.
    propias = [n for n in niveles if not _es_del_mercado(n)]
    # Dentro de lo propio manda el ORDEN que eligió el autor del tema: la
    # primera tarjeta es el asunto de la página. Preferir un importe sobre
    # un share parecía una mejora y era peor — en una página de share
    # sacaba la medida del título y leía la que estaba de contexto.
    if propias:
        return propias[0]
    if niveles:
        # Todos los KPIs son del mercado: antes se leía el mercado y la
        # conclusión hablaba de otro. Si el modelo tiene la contraparte
        # propia, la lectura arranca de ahí.
        if cat is not None:
            propia = _contraparte_propia(niveles[0], cat)
            if propia:
                return propia
        return niveles[0]
    if existe(tema.get("linea")):
        return tema["linea"]
    barras = tema.get("barras")
    if barras and existe(barras[0]):
        return barras[0]
    for n in (tema.get("tabla") or {}).get("medidas") or []:
        if existe(n):
            return n
    return kpis[0] if kpis else None


def preparar_temas(modelo: dict, temas: list[dict],
                   idioma: str = IDIOMA_DEFECTO
                   ) -> tuple[dict, list[dict]]:
    """Modelo + lecturas para un tablero por temas, una por página."""
    cat = Catalogo.desde_modelo(modelo)
    paginas = []
    for tema in temas or []:
        medida = _protagonista(tema, lambda n: bool(n)
                               and cat.medida(n) is not None, cat)
        if medida:
            paginas.append((tema["titulo"], medida))
    return agregar_lecturas(modelo, paginas, idioma)


def preparar_auto(modelo: dict, medidas_sel: list[str] | None = None,
                  idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[dict]]:
    """Modelo + lecturas para el tablero automático: UNA por página.

    Con el tablero temático —una página por cada cosa que el negocio
    mide— la página de análisis tiene que leer cada una: un informe de
    diez páginas con una sola conclusión escrita quedaba incompleto, y
    así lo reportó un usuario. Cada lectura toma la medida principal de
    su tema; si el dataset no da para temas, sale la lectura única del
    tablero de dos páginas de siempre.
    """
    from .tablero import TITULOS_AUTO, temas_automaticos

    cat = Catalogo.desde_modelo(modelo)
    todas = cat.medidas()
    elegidas = [n for n in (medidas_sel or []) if cat.medida(n)] \
        or [m["nombre"] for m in todas[:5]]
    if not elegidas:
        return modelo, []
    pares: list[tuple[str, str]] = []
    for tema in temas_automaticos(cat, medidas_sel, idioma):
        principal = next((n for n in tema.get("kpis", [])
                          if cat.medida(n)), None)
        if principal:
            pares.append((tema["titulo"], principal))
    if not pares:
        pares = [(TITULOS_AUTO[0], elegidas[0])]
    return agregar_lecturas(modelo, pares, idioma)
