# © 2026 Martín Viera. Todos los derechos reservados.

"""La RUTA de una entidad: sus contactos, en orden, vengan de donde vengan.

Un modelo típico guarda cada canal en su propia tabla de hechos —visitas
en una, envíos digitales en otra, llamadas en una tercera— con columnas
distintas y vocabularios distintos. Cada tabla responde bien «¿cuántas
visitas hubo?», y ninguna responde las preguntas que de verdad importan:

  · ¿Cuántos contactos tuvo este cliente, sumando todo?
  · ¿Cuál fue el PRIMERO? ¿Y el orden de los que siguieron?
  · ¿Qué secuencia de canales antecede a una compra?
  · ¿Rinde más el canal caro o el barato, medidos igual?

Con las tablas separadas, cada una de ésas obliga a un `UNION` en DAX que
no escala y que nadie mantiene. Este módulo arma **una fila por contacto**
con cuatro columnas que ninguna de las tablas de origen tiene:

    Tipo        de qué tabla de hechos vino ese contacto
    Canal       el canal concreto, en un vocabulario común
    Resultado   qué pasó con él, también en vocabulario común
    Orden       el número de contacto DE ESA ENTIDAD

`Orden` es lo que convierte una lista en una ruta. Sin él se puede contar;
con él se puede leer la secuencia.

**No inventa nada.** Cada fila sale de una fila real de una tabla de
hechos. Si el modelo no tiene dos hechos que compartan la misma entidad y
el mismo calendario, no hay ruta que armar y se devuelve el modelo intacto.
"""
from __future__ import annotations

from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

TABLA = "Ruta"
COLS = ("ContactoID", "Fecha", "EntidadID", "Tipo", "Canal", "Resultado",
        "Orden")

# Nombres que delatan la columna de ESTADO de un hecho: es la que da el
# «Resultado» sin tener que deducirlo de banderas numéricas.
_ESTADO = ("estado", "status", "resultado", "result", "situacion",
           "situación", "outcome")

# Cuántos valores distintos puede tener una columna para servir de canal o
# de estado. Por encima de eso no es una categoría, es un identificador —
# y un «canal» con doscientos valores no agrupa nada.
MAX_CATEGORIAS = 12


def _columnas_de(cat: Catalogo, tabla: str) -> list[dict]:
    return [c for t, c in cat.columnas() if _norm(t) == _norm(tabla)]


def _clave_hacia(cat: Catalogo, hecho: str, dim: str) -> str:
    """La columna de `hecho` que apunta a `dim`, si hay relación."""
    for r in cat.relaciones:
        if _norm(r["desde_tabla"]) == _norm(hecho) \
                and _norm(r["hacia_tabla"]) == _norm(dim):
            return r["desde_col"]
    return ""


def entidad_principal(cat: Catalogo) -> str:
    """La dimensión de la que cuelgan más tablas de hechos.

    Es la que protagoniza la ruta: el cliente, el médico, el paciente, el
    equipo. El calendario queda fuera —de él cuelga todo, y una ruta «de
    la fecha» no significa nada.
    """
    from . import dataset

    cuenta: dict[str, int] = {}
    for r in cat.relaciones:
        destino = r["hacia_tabla"]
        t = next((x for x in cat.tablas
                  if _norm(x["nombre"]) == _norm(destino)), None)
        if not t or t["es_calendario"] or t["interna"]:
            continue
        cuenta[destino] = cuenta.get(destino, 0) + 1
    if not cuenta:
        return ""

    def _filas(nombre: str) -> int:
        d = dataset.filas_embebidas(cat.tabla(nombre) or {})
        return len(d[1]) if d else 0

    # Primero cuántos hechos la tocan; a igualdad —o casi—, la dimensión
    # más POBLADA. Una ruta es por entidad, y las entidades son muchas
    # (cien médicos, miles de clientes) mientras que un catálogo de
    # productos es corto. Sin este desempate, un modelo donde el producto
    # toca un hecho más que el cliente devolvía «la ruta del producto»,
    # que no significa nada.
    tope = max(cuenta.values())
    # «tope - 1» y no «tope»: empatar por poco es empatar. Lo que decide
    # entre dos dimensiones igual de conectadas es cuál tiene más filas.
    candidatas = [n for n, c in cuenta.items() if c >= tope - 1]
    elegida = max(candidatas, key=_filas)
    return elegida if cuenta[elegida] >= 2 else ""


def hechos_de_contacto(cat: Catalogo, entidad: str = "") -> list[str]:
    """Las tablas de hechos que pueden unificarse en una ruta.

    Requisito doble y no negociable: la tabla tiene que llegar a la
    entidad Y al calendario. Sin la entidad no hay de quién es el
    contacto; sin la fecha no hay orden posible, y sin orden esto es una
    lista, no una ruta.
    """
    entidad = entidad or entidad_principal(cat)
    if not entidad:
        return []
    _cal = cat.tabla_fechas()
    cal = _cal["nombre"] if _cal else ""
    salida = []
    for t in cat.tablas:
        if t["interna"] or t["es_calendario"] or _norm(t["nombre"]) == _norm(entidad):
            continue
        if not _clave_hacia(cat, t["nombre"], entidad):
            continue
        if cal and not _clave_hacia(cat, t["nombre"], cal):
            continue
        salida.append(t["nombre"])
    return salida


def _por_nombre(cat: Catalogo, tabla: str,
                preferidas: tuple[str, ...]) -> str:
    """La columna de texto cuyo NOMBRE dice qué es. Sólo por nombre.

    Quien armó el modelo ya la bautizó «Estado» o «Canal»; adivinar por
    cardinalidad cuando no hay nombre es lo que hacía que el canal y el
    resultado terminaran siendo LA MISMA columna —los dos caían al mismo
    fallback— y la ruta mostrara «Realizada» como si fuera un canal.
    """
    for c in _columnas_de(cat, tabla):
        if c.get("oculta") or c["tipo"] != "string":
            continue
        if any(p in _norm(c["nombre"]) for p in preferidas):
            return c["nombre"]
    return ""


def _canal_de(cat: Catalogo, tabla: str, datos: dict, estado: str) -> str:
    """La columna de canal, o vacío para usar el nombre del hecho.

    Se descarta explícitamente la que ya se usó como estado: son dos
    preguntas distintas —por dónde llegó y qué pasó— y colapsarlas en una
    columna deja la ruta sin la mitad de la información.
    """
    directa = _por_nombre(cat, tabla, ("canal", "channel", "medio", "via",
                                       "vía"))
    if directa and directa != estado:
        return directa
    filas = datos.get(tabla)
    if not filas:
        return ""
    nombres, valores = filas
    mejor, menos = "", MAX_CATEGORIAS + 1
    for c in _columnas_de(cat, tabla):
        if c.get("oculta") or c["tipo"] != "string":
            continue
        if c["nombre"] in (estado,) or c["nombre"] not in nombres:
            continue
        i = nombres.index(c["nombre"])
        distintos = len({f[i] for f in valores})
        if 1 < distintos <= MAX_CATEGORIAS and distintos < menos:
            mejor, menos = c["nombre"], distintos
    return mejor


def _banderas(cat: Catalogo, tabla: str, datos: dict) -> list[str]:
    """Las columnas 0/1 del hecho, de la más superficial a la más profunda.

    Un envío digital suele traer `Enviado`, `Abierto`, `Click`: tres
    banderas que en realidad son UN estado con tres niveles. Se ordenan
    por cuántas filas la tienen prendida —la más rara es la más profunda—
    para poder decir «llegó hasta acá» en vez de cargar tres columnas.
    """
    filas = datos.get(tabla)
    if not filas:
        return []
    nombres, valores = filas
    cand = []
    for c in _columnas_de(cat, tabla):
        if c["tipo"] not in ("int64", "double", "decimal"):
            continue
        if c["nombre"] not in nombres:
            continue
        i = nombres.index(c["nombre"])
        vistos = {str(f[i]).strip() for f in valores}
        if vistos and vistos <= {"0", "1", "0.0", "1.0", ""}:
            prendidas = sum(1 for f in valores
                            if str(f[i]).strip() in ("1", "1.0"))
            cand.append((prendidas, c["nombre"]))
    # De menos prendidas a más: la bandera rara es el resultado profundo.
    return [n for _p, n in sorted(cand)]


def construir(modelo: dict, hechos: list[str] | None = None,
              entidad: str = "", idioma: str = IDIOMA_DEFECTO,
              datos: dict | None = None) -> dict:
    """Agrega la tabla de ruta al modelo. Devuelve el modelo intacto si no aplica.

    `hechos` deja elegir cuáles son CONTACTOS: en un modelo comercial,
    las visitas y los envíos lo son y las ventas no —son el resultado, no
    el contacto—, y esa distinción es de negocio, no de esquema. Sin
    especificar, entran todos los hechos que llegan a la entidad.

    `datos` (`{tabla: (columnas, filas)}`) es la salida para el caso más
    común de todos: un modelo recién propuesto desde un CSV o un Excel
    todavía no lleva las filas adentro —eso pasa al exportar— y sin filas
    no hay eventos que unificar. Quien tenga la materia prima la pasa
    acá; si no, se leen las del propio modelo.
    """
    from . import dataset

    cat = Catalogo.desde_modelo(modelo)
    if any(t["nombre"] == TABLA for t in cat.tablas):
        return modelo
    entidad = entidad or entidad_principal(cat)
    hechos = [h for h in (hechos or hechos_de_contacto(cat, entidad))
              if cat.tabla(h)] if entidad else []
    if len(hechos) < 2:
        return modelo          # con una sola tabla no hay nada que unificar
    datos = datos or dataset.datos_del_modelo(modelo)
    _cal = cat.tabla_fechas()
    cal = _cal["nombre"] if _cal else ""

    eventos = []
    for hecho in hechos:
        filas = datos.get(hecho)
        if not filas:
            continue
        nombres, valores = filas
        k_ent = _clave_hacia(cat, hecho, entidad)
        k_fec = _clave_hacia(cat, hecho, cal) if cal else ""
        if k_ent not in nombres or k_fec not in nombres:
            continue
        i_ent, i_fec = nombres.index(k_ent), nombres.index(k_fec)
        # El ESTADO primero, y sólo por nombre o por banderas: es lo que
        # deja al canal buscar en el resto de las columnas sin pisarlo.
        estado = _por_nombre(cat, hecho, _ESTADO)
        banderas = [] if estado else _banderas(cat, hecho, datos)
        canal = _canal_de(cat, hecho, datos, estado)
        i_can = nombres.index(canal) if canal in nombres else -1
        i_est = nombres.index(estado) if estado in nombres else -1
        idx_b = [(n, nombres.index(n)) for n in banderas if n in nombres]
        for f in valores:
            if i_est >= 0:
                res = str(f[i_est])
            elif idx_b:
                # El nivel MÁS profundo que alcanzó: un click implica
                # apertura, y una apertura implica envío. Guardar el
                # máximo y no las tres banderas es lo que permite
                # comparar contra el estado de una visita en el mismo
                # vocabulario.
                res = next((n for n, i in idx_b
                            if str(f[i]).strip() in ("1", "1.0")),
                           traducir("ruta_sin_resultado", idioma))
            else:
                res = traducir("ruta_sin_resultado", idioma)
            eventos.append([str(f[i_fec]), str(f[i_ent]), hecho,
                            str(f[i_can]) if i_can >= 0 else hecho, res])
    if not eventos:
        return modelo

    # El ORDEN es por entidad y por fecha: es lo que hace que esto sea una
    # RUTA y no una lista. Sin él no se puede preguntar cuál fue el primer
    # contacto ni cuántos hubo antes del primer resultado.
    eventos.sort(key=lambda e: (e[1], e[0]))
    n_por: dict[str, int] = {}
    final = []
    for ev in eventos:
        n_por[ev[1]] = n_por.get(ev[1], 0) + 1
        final.append([f"C{len(final) + 1:06d}"] + ev + [str(n_por[ev[1]])])

    clave_ent = next(r["hacia_col"] for r in cat.relaciones
                     if _norm(r["hacia_tabla"]) == _norm(entidad))
    clave_cal = next((r["hacia_col"] for r in cat.relaciones
                      if cal and _norm(r["hacia_tabla"]) == _norm(cal)), "")
    modelo["model"]["tables"].append({
        "name": TABLA,
        "columns": [
            {"name": "ContactoID", "dataType": "string",
             "sourceColumn": "ContactoID", "isHidden": True},
            {"name": "Fecha", "dataType": "dateTime", "sourceColumn": "Fecha",
             "isHidden": True, "formatString": "yyyy-mm-dd"},
            {"name": "EntidadID", "dataType": "string",
             "sourceColumn": "EntidadID", "isHidden": True},
            {"name": "Tipo", "dataType": "string", "sourceColumn": "Tipo",
             "summarizeBy": "none"},
            {"name": "Canal", "dataType": "string", "sourceColumn": "Canal",
             "summarizeBy": "none"},
            {"name": "Resultado", "dataType": "string",
             "sourceColumn": "Resultado", "summarizeBy": "none"},
            {"name": "Orden", "dataType": "int64", "sourceColumn": "Orden",
             "summarizeBy": "none", "formatString": "0"},
        ],
        "partitions": [{
            "name": TABLA, "mode": "import",
            "source": {"type": "m", "expression": dataset.m_embebido(
                list(COLS), final,
                tipos={"Fecha": "dateTime", "Orden": "int64"})},
        }],
    })
    import uuid
    modelo["model"].setdefault("relationships", []).append({
        "name": str(uuid.uuid4()), "fromTable": TABLA,
        "fromColumn": "EntidadID", "toTable": entidad, "toColumn": clave_ent})
    if cal and clave_cal:
        modelo["model"]["relationships"].append({
            "name": str(uuid.uuid4()), "fromTable": TABLA,
            "fromColumn": "Fecha", "toTable": cal, "toColumn": clave_cal})
    return modelo


def medidas(modelo: dict, idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Las medidas que la ruta habilita, si la tabla está en el modelo.

    Recibe el MODELO y no el catálogo porque necesita las filas: cuáles
    resultados cuentan como «efectivo» se lee del dato, no de una lista
    fija — cada modelo nombra sus estados como quiere.
    """
    cat = Catalogo.desde_modelo(modelo)
    if not any(t["nombre"] == TABLA for t in cat.tablas):
        return []
    efectivos = _resultados_efectivos(modelo)
    salida = [
        {"nombre": traducir("ruta_med_contactos", idioma),
         "dax": f"COUNTROWS ( '{TABLA}' )", "formato": "#,0",
         "por_que": traducir("ruta_pq_contactos", idioma)},
        {"nombre": traducir("ruta_med_por_entidad", idioma),
         "dax": f"DIVIDE (\n    [{traducir('ruta_med_contactos', idioma)}],\n"
                f"    DISTINCTCOUNT ( '{TABLA}'[EntidadID] )\n)",
         "formato": "#,0.0",
         "por_que": traducir("ruta_pq_por_entidad", idioma)},
        {"nombre": traducir("ruta_med_larga", idioma),
         "dax": f"MAX ( '{TABLA}'[Orden] )", "formato": "#,0",
         "por_que": traducir("ruta_pq_larga", idioma)},
    ]
    if efectivos:
        lista = ", ".join(f'"{v}"' for v in efectivos)
        salida.append({
            "nombre": traducir("ruta_med_efectivos", idioma),
            "dax": f"CALCULATE (\n"
                   f"    [{traducir('ruta_med_contactos', idioma)}],\n"
                   f"    KEEPFILTERS ( '{TABLA}'[Resultado] IN {{ {lista} }} )\n)",
            "formato": "#,0",
            "por_que": traducir("ruta_pq_efectivos", idioma)})
        salida.append({
            "nombre": traducir("ruta_med_efectividad", idioma),
            "dax": f"DIVIDE (\n"
                   f"    [{traducir('ruta_med_efectivos', idioma)}],\n"
                   f"    [{traducir('ruta_med_contactos', idioma)}]\n)",
            "formato": "0.0 %",
            "por_que": traducir("ruta_pq_efectividad", idioma)})
    return salida


# Un contacto «sirvió» si el resultado dice que llegó a destino. La lista
# es de palabras, no de valores fijos: cada modelo nombra sus estados como
# quiere, y lo que se busca es la INTENCIÓN.
_EFECTIVO = ("realizada", "realizado", "efectiva", "efectivo", "abierto",
             "abierta", "click", "clic", "completada", "completado",
             "atendida", "atendido", "done", "opened", "clicked")


def _resultados_efectivos(modelo: dict) -> list[str]:
    """Los valores de `Resultado` que cuentan como contacto que sirvió.

    Se leen del dato y se filtran por intención: `cat.tabla()` devuelve la
    vista del catálogo —sin particiones—, así que hay que ir a la tabla
    cruda del modelo, que es donde viven las filas empotradas.
    """
    from . import dataset

    cruda = next((t for t in modelo.get("model", {}).get("tables", [])
                  if t.get("name") == TABLA), None)
    datos = dataset.filas_embebidas(cruda or {})
    if not datos:
        return []
    nombres, valores = datos
    if "Resultado" not in nombres:
        return []
    i = nombres.index("Resultado")
    vistos = sorted({str(f[i]) for f in valores})
    return [v for v in vistos
            if any(p in _norm(v) for p in _EFECTIVO)]


def agregar(modelo: dict, idioma: str = IDIOMA_DEFECTO,
            datos: dict | None = None) -> tuple[dict, list[str]]:
    """La ruta y sus medidas, en un paso, con el contrato de siempre.

    Es lo que llaman tanto el intérprete («armá la ruta») como la
    preparación del modelo antes de dibujar. Devuelve `(modelo, cambios)`
    y nunca rompe: si el modelo no da para una ruta, lo dice y devuelve
    lo que le entró.
    """
    from . import transformador

    nuevo = construir(modelo, idioma=idioma, datos=datos)
    if not any(t.get("name") == TABLA
               for t in nuevo.get("model", {}).get("tables", [])):
        cat = Catalogo.desde_modelo(modelo)
        entidad = entidad_principal(cat)
        contactos = hechos_de_contacto(cat, entidad) if entidad else []
        # El motivo importa: «no hay dos tablas de contacto» y «las hay
        # pero todavía no tienen filas adentro» se arreglan distinto, y
        # decir el primero cuando pasa el segundo manda a buscar un
        # problema que no existe.
        clave = ("ruta_no_hay_datos" if len(contactos) >= 2
                 else "ruta_no_aplica")
        return modelo, [traducir(clave, idioma).format(
            entidad=entidad or "—", n=len(contactos))]
    cambios: list[str] = []
    for med in medidas(nuevo, idioma):
        try:
            nuevo, c = transformador.agregar_medida(
                nuevo, med["nombre"], med["dax"],
                formato=med.get("formato", ""),
                descripcion=med.get("por_que", ""), idioma=idioma)
            cambios += c
        except ValueError:
            continue                      # ya existía con ese nombre
    tabla = next(t for t in nuevo["model"]["tables"] if t["name"] == TABLA)
    return nuevo, [traducir("ruta_creada", idioma).format(
        tabla=TABLA, entidad=entidad_principal(Catalogo.desde_modelo(modelo)),
        n=len(tabla.get("columns", [])))] + cambios
