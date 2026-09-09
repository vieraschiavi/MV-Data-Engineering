# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Analizador del REPORTE (páginas y visuales).

Por qué existe, y por qué importa más de lo que parece
-----------------------------------------------------
El analizador de `analizador.py` mira el MODELO: medidas, columnas,
relaciones. Es lo correcto, pero tiene un techo duro: el modelo tabular de un
`.pbix` viaja en `DataModel`, un binario propietario de Analysis Services que
no se puede abrir desde afuera de Power BI. O sea que con el archivo que la
gente REALMENTE tiene a mano —un `.pbix`— ese analizador no puede decir nada
y devuelve el aviso R00.

Pero el REPORTE de un `.pbix` sí es legible: `Report/Layout` es JSON. Y ahí
hay hallazgos que valen plata y que ningún analizador de modelo ve nunca:

  · el mismo gráfico pegado tres veces en la misma página;
  · un botón tapado al 100% por un slicer, o sea inalcanzable con el mouse;
  · tres páginas que muestran exactamente los mismos visuales;
  · el mismo filtro replicado en siete páginas en vez de sincronizado;
  · visuales que ocupan lugar y no muestran ningún dato;
  · las tablas `LocalDateTable_*` que Power BI genera solo cuando
    «Auto date/time» está activo — la única pista del modelo que se ve
    desde el reporte, y de las que más pesan.

Los hallazgos salen con la MISMA forma que los de `analizador.py`
(`{regla, severidad, objeto, auto, datos}`), así que comparten `describir()`,
`agrupar()` y `puntaje()` sin ninguna capa de traducción.

Nunca se marcan `auto=True`: mover o borrar un visual cambia lo que ve el
usuario del tablero, y eso lo decide una persona, no el programa.
"""
from __future__ import annotations

import collections
import json

# Estos tipos no muestran datos por diseño, así que no tener campos es lo
# esperado y no un hallazgo.
SIN_DATOS_OK = frozenset({
    "textbox", "image", "shape", "basicShape", "actionButton",
    "bookmarkNavigator", "pageNavigator",
})

# Cuánto se tienen que superponer dos visuales para considerar que uno tapa
# al otro. 70% deja pasar el solape decorativo (una tarjeta sobre un fondo) y
# marca el que hace inalcanzable lo de abajo.
SOLAPE_TAPA = 0.7

# A partir de cuántas páginas repetir el mismo filtro deja de ser práctica
# normal y pasa a ser mantenimiento duplicado. Con 3 ya conviene sincronizar.
PAGINAS_REPETIDO = 3

# Cuántos visuales entran en una página antes de que moleste. Por arriba de
# VISUALES_COMODOS ya cuesta leerla; por arriba de VISUALES_LENTOS además se
# nota al abrirla, porque cada visual dispara su propia consulta al modelo.
VISUALES_COMODOS = 9
VISUALES_LENTOS = 16


def _h(rid: str, severidad: str, objeto: str, **datos) -> dict:
    """Un hallazgo, con la misma forma que los de analizador.py."""
    return {"regla": rid, "severidad": severidad, "objeto": objeto,
            "auto": False, "datos": datos}


def _json(texto):
    """Los campos `config`/`query` del layout son JSON DENTRO de un string."""
    if not texto:
        return {}
    if isinstance(texto, dict):
        return texto
    try:
        return json.loads(texto)
    except (ValueError, TypeError):
        return {}


def campos_de(obj) -> set[str]:
    """Todos los campos (`Tabla.Columna`) que referencia un visual.

    Se recorre el árbol entero en vez de leer rutas fijas: la forma del JSON
    de un visual cambia entre tipos y entre versiones de Power BI, y una ruta
    fija devuelve vacío en silencio con el primer tipo que no encaja.
    """
    campos: set[str] = set()

    def hurgar(o):
        if isinstance(o, dict):
            for clave, valor in o.items():
                if (clave in ("Column", "Measure", "HierarchyLevel")
                        and isinstance(valor, dict)):
                    # Un nivel de jerarquía (p. ej. Año de una jerarquía de
                    # fechas) no trae Property: trae Level.
                    prop = valor.get("Property") or valor.get("Level") or ""
                    exp = valor.get("Expression") or {}
                    ent = ""
                    if isinstance(exp, dict):
                        ent = (exp.get("SourceRef") or {}).get("Entity", "")
                        if not ent:
                            # HierarchyLevel: la entidad está un nivel más
                            # adentro (Expression.Hierarchy.Expression).
                            jer = exp.get("Hierarchy") or {}
                            ent = (((jer.get("Expression") or {})
                                    .get("SourceRef") or {}).get("Entity", ""))
                    if prop:
                        campos.add(f"{ent}.{prop}" if ent else prop)
                hurgar(valor)
        elif isinstance(o, list):
            for x in o:
                hurgar(x)

    hurgar(obj)
    return campos


AUTO_FECHA = ("LocalDateTable_", "DateTableTemplate_")


def _corto(campo: str) -> str:
    """Acorta el nombre de una tabla de fecha automática."""
    tabla, _, resto = campo.partition(".")
    for pre in AUTO_FECHA:
        if tabla.startswith(pre):
            return f"{pre}….{resto}" if resto else f"{pre}…"
    return campo


def etiqueta(campos: tuple[str, ...], maximo: int = 2) -> str:
    """Nombre corto de los campos de un visual, para poder distinguirlo.

    Sin esto dos hallazgos distintos salen con el MISMO texto: seis slicers
    de seis campos distintos, repetidos en las mismas páginas, se leían como
    seis renglones idénticos que decían «slicer». Quien lo lee no sabe cuál
    es cuál, y el informe parece roto aunque los seis sean ciertos.
    """
    if not campos:
        return "—"
    # `LocalDateTable_a0b4225d-d1c3-40e8-b7b3-41eb0c6104ec.Año` ocupa media
    # línea y no aporta: el GUID no se elige ni se busca. El nombre completo
    # va igual en RP06, que es el hallazgo que se acciona.
    vistos = [_corto(c) for c in campos[:maximo]]
    if len(campos) > maximo:
        vistos.append(f"+{len(campos) - maximo}")
    return ", ".join(vistos)


VOLATIL = frozenset({"name", "restatement", "cachedDisplayNames",
                     "cachedValueItems", "displayName"})


def _sin_ruido(o):
    """Saca de un filtro lo que cambia entre dos copias idénticas.

    Power BI le pone a cada filtro un `name` propio («Filter4cdd14f0a45…»),
    así que dos visuales copiados y pegados nunca tienen filtros iguales
    byte a byte aunque filtren exactamente lo mismo. Sin normalizar esto la
    comparación no encuentra NINGÚN duplicado y la regla queda muerta.
    """
    if isinstance(o, dict):
        return {k: _sin_ruido(v) for k, v in sorted(o.items())
                if k not in VOLATIL}
    if isinstance(o, list):
        return [_sin_ruido(x) for x in o]
    return o


def filtros_de(vc: dict) -> str:
    """Firma de los filtros de nivel visual, normalizada y estable.

    Es el dato que distingue dos visuales que por tipo y campos parecen el
    mismo. En un archivo real había tres gráficos idénticos lado a lado que
    en realidad filtraban distinto —uno excluía un canal, otro no— y tratarlos
    como copias llevaba a recomendar borrar visuales que SÍ dicen cosas
    distintas. Es el peor error posible acá: destruye el tablero de quien
    siguió el consejo.
    """
    crudo = vc.get("filters")
    if not crudo:
        return ""
    if not isinstance(crudo, str):
        return json.dumps(_sin_ruido(crudo), sort_keys=True, ensure_ascii=False)
    try:
        datos = json.loads(crudo)
    except (ValueError, TypeError):
        # Había filtros y no se pudieron leer. Devolver "" los haría pasar por
        # «sin filtros» y compararían iguales a dos visuales que tal vez no lo
        # son; mejor una firma propia que no agrupa con nada.
        return f"?{len(crudo)}"
    # Ojo: `[]` es un parseo EXITOSO que quiere decir «sin filtros», no una
    # falla. Tratarlo como ilegible le daba firma «?2» a medio reporte.
    return json.dumps(_sin_ruido(datos), sort_keys=True, ensure_ascii=False)


def titulo_de(sv: dict) -> str:
    """El título que se ve arriba del visual, si es un texto fijo."""
    try:
        objs = (sv.get("vcObjects") or {}).get("title") or []
        return str(objs[0]["properties"]["text"]["expr"]["Literal"]["Value"]
                   ).strip("'")
    except (KeyError, IndexError, TypeError):
        return ""


def _interseccion(a: dict, b: dict) -> float:
    """Área cruda del rectángulo donde a y b se pisan."""
    ax, ay = a.get("x") or 0, a.get("y") or 0
    aw, ah = a.get("w") or 0, a.get("h") or 0
    bx, by = b.get("x") or 0, b.get("y") or 0
    bw, bh = b.get("w") or 0, b.get("h") or 0
    ancho = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    alto = max(0, min(ay + ah, by + bh) - max(ay, by))
    return ancho * alto


def _solape(a: dict, b: dict) -> float:
    """Fracción del visual MÁS CHICO que queda tapada por el otro."""
    menor = min((a.get("w") or 0) * (a.get("h") or 0),
                (b.get("w") or 0) * (b.get("h") or 0))
    return (_interseccion(a, b) / menor) if menor else 0.0


def leer(layout: dict) -> list[dict]:
    """Normaliza `Report/Layout` a páginas con sus visuales."""
    paginas = []
    for sec in (layout or {}).get("sections", []) or []:
        cfg_pag = _json(sec.get("config"))
        visuales = []
        for vc in sec.get("visualContainers", []) or []:
            cfg = _json(vc.get("config"))
            sv = cfg.get("singleVisual") or {}
            # El `singleVisual` PRIMERO, y el `query` sólo como respaldo.
            # Al revés estaba mal y se notaba recién con archivos reales: el
            # `query` de un visual lleva además el contexto de filtro de toda
            # la página, así que devolvía una sopa de campos de otros visuales.
            # Dos slicers distintos —uno de Distribuidor, otro de Pregunta—
            # terminaban con la misma lista de cuatro campos y la regla de
            # duplicados los daba por copias.
            campos = campos_de(sv) or campos_de(_json(vc.get("query")))
            # Un slicer sincronizado NO se mantiene por separado: cambia junto
            # con sus pares. Sin mirar esto, la regla de filtros repetidos
            # denuncia justamente al que YA está bien resuelto.
            grupo = (sv.get("syncGroup") or {}).get("groupName") or ""
            visuales.append({
                "tipo": sv.get("visualType") or "?",
                "campos": tuple(sorted(campos)),
                "filtros": filtros_de(vc),
                "titulo": titulo_de(sv),
                "sincronizado": grupo,
                "x": vc.get("x"), "y": vc.get("y"),
                "w": vc.get("width"), "h": vc.get("height"),
                # El eje z decide quién queda ARRIBA cuando dos visuales se
                # pisan. None (layouts viejos sin el dato) ≠ 0: sin z no se
                # puede saber el orden y las reglas caen al criterio anterior.
                "z": vc.get("z"),
            })
        paginas.append({
            "nombre": (sec.get("displayName") or "?").strip(),
            "oculta": cfg_pag.get("visibility") == 1,
            # El filtro de NIVEL DE PÁGINA: dos páginas que filtran distinto
            # muestran datos distintos aunque tengan los mismos visuales.
            "filtros": filtros_de(sec),
            "visuales": visuales,
        })
    return paginas


def analizar(layout: dict) -> list[dict]:
    """Corre las reglas de reporte. Devuelve hallazgos ordenados."""
    paginas = leer(layout)
    if not paginas:
        return []

    hallazgos: list[dict] = []
    hallazgos += _dup_misma_pagina(paginas)
    hallazgos += _tapados(paginas)
    hallazgos += _repetidos_entre_paginas(paginas)
    hallazgos += _sin_datos(paginas)
    hallazgos += _auto_fecha(paginas)
    hallazgos += _pagina_recargada(paginas)
    hallazgos += _paginas_ocultas(paginas)

    orden = {"alta": 0, "media": 1, "baja": 2}
    hallazgos.sort(key=lambda h: (orden.get(h["severidad"], 9), h["regla"]))
    return hallazgos


# --------------------------------------------------------------------------
def _dup_misma_pagina(paginas) -> list[dict]:
    """RP01 · el mismo visual, con los mismos campos, repetido en una página.

    Nadie pone el mismo gráfico dos veces a propósito: es copiar y pegar que
    quedó. Cuesta una consulta más al modelo por cada copia.
    """
    fuera = []
    for pag in paginas:
        # La clave incluye filtros Y título: para poder decir «borralo, no se
        # pierde ninguna cifra» los dos visuales tienen que ser el mismo en
        # todo, no sólo en tipo y campos.
        cuenta = collections.Counter(
            (v["tipo"], v["campos"], v["filtros"], v["titulo"])
            for v in pag["visuales"] if v["campos"])
        for (tipo, campos, _f, _t), n in cuenta.items():
            if n > 1:
                etq = etiqueta(campos)
                fuera.append(_h("RP01", "alta",
                                f'{pag["nombre"]} · {tipo} · {etq}',
                                pagina=pag["nombre"], tipo=tipo, campo=etq,
                                veces=str(n), sobran=str(n - 1)))
    return fuera


def _tapados(paginas) -> list[dict]:
    """RP02 · un visual tapado por otro: existe y no se puede usar.

    El caso que más aparece es un slicer encima de un botón de acción. El
    botón conserva su acción configurada y es inalcanzable con el mouse, así
    que el tablero tiene una función muerta que nadie sabe que está muerta.

    El solape solo no alcanza: hay que mirar el eje z. Un botón «Volver»
    chico puesto A PROPÓSITO sobre la esquina de un slicer (z más alto) está
    100% dentro del rectángulo del slicer y aun así es perfectamente
    clickeable — el tapado es el que quedó ABAJO, y lo que importa es qué
    fracción DE ÉL desaparece. En dos tableros reales, el mismo botón Volver
    encima de un slicer generaba un falso «botón tapado» por página.
    """
    fuera = []
    for pag in paginas:
        vs = pag["visuales"]
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                a, b = vs[i], vs[j]
                za, zb = a.get("z"), b.get("z")
                if za is not None and zb is not None and za != zb:
                    encima, debajo = (a, b) if za > zb else (b, a)
                    area = (debajo["w"] or 0) * (debajo["h"] or 0)
                    sol = (_interseccion(a, b) / area) if area else 0.0
                else:
                    # Sin z (layouts viejos) no se sabe quién quedó arriba:
                    # se mantiene el criterio del más chico, que es el que
                    # suele quedar sepultado.
                    encima, debajo = a, b
                    sol = _solape(a, b)
                if sol > SOLAPE_TAPA:
                    fuera.append(_h(
                        "RP02", "alta",
                        f'{pag["nombre"]} · {encima["tipo"]} / {debajo["tipo"]}',
                        pagina=pag["nombre"], encima=encima["tipo"],
                        debajo=debajo["tipo"], solape=f"{sol:.0%}"))
    return fuera


def _repetidos_entre_paginas(paginas) -> list[dict]:
    """RP03 · el mismo visual replicado en varias páginas.

    Para un filtro es práctica normal hasta cierto punto; pasado
    PAGINAS_REPETIDO conviene sincronizarlo, porque mantenerlos por separado
    es lo que hace que dos páginas muestren números que no cierran entre sí.
    Para un gráfico es directamente contenido duplicado.
    """
    # Sin el título a propósito: RP04 justamente denuncia «la misma historia
    # con otro título». Los filtros SÍ van — un gráfico filtrado distinto no
    # cuenta la misma historia.
    donde = collections.defaultdict(set)
    for pag in paginas:
        for v in pag["visuales"]:
            if not v["campos"]:
                continue
            # Un slicer sincronizado no cuenta como copia a mantener: ya
            # cambia junto con sus pares, que es justo lo que la regla pide.
            # Sin esto el producto le marca un problema a quien lo resolvió
            # bien — y era el caso de los dos .pbix reales, donde 20 de 25 y
            # 48 de 49 slicers estaban en grupos de sincronización.
            if v["tipo"] == "slicer" and v.get("sincronizado"):
                continue
            # El filtro de página entra en la clave: «Puntaje Global», «…Dist»
            # y «…ARCOR» tienen los mismos visuales y filtran distinto a nivel
            # página, así que NO cuentan la misma historia — cuentan tres.
            donde[(v["tipo"], v["campos"], v["filtros"],
                   pag["filtros"])].add(pag["nombre"])

    fuera = []
    for (tipo, campos, _filtros, _pag), pags in donde.items():
        etq = etiqueta(campos)
        if tipo == "slicer":
            if len(pags) >= PAGINAS_REPETIDO:
                fuera.append(_h("RP03", "media", f"{tipo} · {etq}", tipo=tipo,
                                campo=etq, paginas=str(len(pags)),
                                donde=", ".join(sorted(pags))))
        elif len(pags) > 1:
            fuera.append(_h("RP04", "media", f"{tipo} · {etq}", tipo=tipo,
                            campo=etq, paginas=str(len(pags)),
                            donde=", ".join(sorted(pags))))
    return fuera


def _sin_datos(paginas) -> list[dict]:
    """RP05 · un visual de datos que no referencia ningún campo.

    Ocupa lugar, se consulta, y no muestra nada. Los cuadros de texto,
    imágenes y botones quedan fuera: no tener campos es lo que se espera
    de ellos.
    """
    fuera = []
    for pag in paginas:
        for v in pag["visuales"]:
            # Tipo desconocido = no se pudo leer el `config` del visual. Sin
            # saber qué es no se puede afirmar que le falten campos: podría
            # ser un cuadro de texto. Un archivo dañado no debe producir un
            # diagnóstico inventado.
            if v["tipo"] == "?":
                continue
            if not v["campos"] and v["tipo"] not in SIN_DATOS_OK:
                fuera.append(_h("RP05", "media",
                                f'{pag["nombre"]} · {v["tipo"]}',
                                pagina=pag["nombre"], tipo=v["tipo"]))
    return fuera


def _auto_fecha(paginas) -> list[dict]:
    """RP06 · tablas de fecha automáticas de Power BI.

    Power BI crea una `LocalDateTable_<guid>` por CADA campo de fecha cuando
    «Auto date/time» está activo. Infla el modelo, no se puede controlar, y
    no se ve en ninguna parte de la interfaz. Es el único hallazgo del modelo
    que se puede detectar leyendo sólo el reporte — aparece porque algún
    visual la referencia.
    """
    autos = set()
    for pag in paginas:
        for v in pag["visuales"]:
            for campo in v["campos"]:
                tabla = campo.split(".")[0]
                if tabla.startswith(AUTO_FECHA):
                    autos.add(tabla)
    if not autos:
        return []
    return [_h("RP06", "alta", "(modelo)", cuantas=str(len(autos)),
               ejemplo=sorted(autos)[0])]


# Visuales que NO consultan el modelo ni compiten por la atención: la
# decoración de la página. Un logo, un título, un botón de navegación o una
# forma no cuentan para «página recargada».
DECORATIVOS = frozenset({"textbox", "image", "actionButton", "shape",
                         "basicShape", "bookmarkNavigator",
                         "pageNavigator"})


def _pagina_recargada(paginas) -> list[dict]:
    """RP08 · demasiados visuales en una página.

    Dos costos distintos, y por eso dos umbrales. Pasando VISUALES_COMODOS la
    página cansa: quien la mira no sabe dónde empezar. Pasando VISUALES_LENTOS
    además se nota al abrirla, porque cada visual dispara su propia consulta al
    modelo y el render espera a la última.

    Se cuentan SOLO los visuales con datos. Un encabezado con logo, título y
    botones de navegación suma cinco contenedores que no consultan nada: con
    ellos adentro, una página prolija de seis gráficos se acusaba de
    recargada — la regla castigaba justo al que se tomó el trabajo de
    ponerle un encabezado.
    """
    fuera = []
    for pag in paginas:
        n = sum(1 for v in pag["visuales"]
                if v.get("tipo") not in DECORATIVOS)
        if n < VISUALES_COMODOS:
            continue
        grave = n >= VISUALES_LENTOS
        fuera.append(_h("RP08", "media" if grave else "baja", pag["nombre"],
                        pagina=pag["nombre"], cuantos=str(n),
                        comodos=str(VISUALES_COMODOS - 1)))
    return fuera


def _paginas_ocultas(paginas) -> list[dict]:
    """RP07 · páginas ocultas.

    No siempre es un error —se usan para tooltips y drill-through— pero una
    página oculta que nadie recuerda es trabajo que se sigue refrescando sin
    que nadie lo mire.
    """
    ocultas = [p["nombre"] for p in paginas if p["oculta"]]
    if not ocultas:
        return []
    return [_h("RP07", "baja", ", ".join(ocultas),
               cuantas=str(len(ocultas)), donde=", ".join(ocultas))]


def resumen(layout: dict) -> dict:
    """Cifras del reporte, para la cabecera de la pestaña."""
    paginas = leer(layout)
    visuales = [v for p in paginas for v in p["visuales"]]
    return {
        "paginas": len(paginas),
        "visuales": len(visuales),
        "slicers": sum(1 for v in visuales if v["tipo"] == "slicer"),
    }


def tablas_usadas(layout: dict | None) -> set[str]:
    """Las tablas que algún visual del reporte pone en un eje o en un valor.

    R12 la usa para no acusar de «suelta» a una tabla desconectada que el
    tablero sí consume — el caso típico es la tabla de eje de una página
    de documentación, que a propósito no se relaciona con nada.
    """
    salida: set[str] = set()
    for s_ in (layout or {}).get("sections", []) or []:
        for vc in s_.get("visualContainers") or []:
            # El `config` viaja como CADENA JSON: recorrer el contenedor
            # sin parsearlo devuelve vacío en silencio, que era justo lo
            # que dejaba a la tabla del diccionario fuera de la lista.
            cfg = _json(vc.get("config")) or {}
            sv = cfg.get("singleVisual") or cfg
            for campo in (campos_de(sv) or campos_de(_json(vc.get("query")))
                          or campos_de(vc)):
                tabla, _, _campo = campo.rpartition(".")
                if tabla:
                    salida.add(tabla)
    return salida
