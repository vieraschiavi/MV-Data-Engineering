# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · ¿Hasta cuándo llegan los datos de cada tabla?

**El problema, que no es armar otro tablero.** Antes de mirar un número
hay que saber si el dato que lo alimenta está al día. Media hora
explicando una caída de ventas que era una carga que no corrió es la
forma más cara de perder una reunión — y pasa seguido, porque esa
información no está en ningún lado del informe.

Este módulo arma el panel de frescura: una fila por tabla con hasta
cuándo llegan sus datos, cuántas filas trae, cada cuánto se actualiza y
si está al día o atrasada.

**La regla que lo hace confiable, otra vez: no inventar la fecha.**
Un `.pbit` NO guarda cuándo se refrescó cada tabla — en un modelo de
importación ese dato vive en el workspace o en la instancia de Analysis
Services, no en el archivo. Así que acá se distinguen tres cosas que un
panel descuidado mezcla en una sola columna:

  fecha de los datos    el máximo de la columna de fecha de la tabla. Es
                        real, se mide sobre las filas, y es lo que de
                        verdad le importa a quien pregunta «¿está al
                        día?».
  fecha de carga        cuándo se escribió el archivo. Sale del
                        manifiesto de gobierno, que lo estampa el
                        exportador. Para una tabla que apunta a un
                        archivo de disco, y solo en escritorio, se puede
                        mirar además la fecha del propio archivo.
  cadencia              cada cuánto llegan datos nuevos, DEDUCIDA de las
                        fechas que la tabla ya tiene. No es una promesa
                        del proceso: es lo que se observa.

Cuando algo no se puede saber, la fila lo dice. Un panel de monitoreo que
rellena huecos con supuestos es peor que no tenerlo: da tranquilidad sin
respaldo, que es exactamente lo contrario de para lo que se lo mira.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from .catalogo import Catalogo
from .i18n import IDIOMA_DEFECTO, t as traducir

#: Estados de una tabla, de mejor a peor.
AL_DIA, ATRASADA, PARCIAL, SIN_FECHA, SIN_DATOS = (
    "al_dia", "atrasada", "parcial", "sin_fecha", "sin_datos")

#: Los estados, en un solo lugar. Existe para que agregar uno y olvidarse
#: del texto —o del conteo del panel— rompa un test en vez de mostrar una
#: clave cruda en la grilla.
ESTADOS = (AL_DIA, ATRASADA, PARCIAL, SIN_FECHA, SIN_DATOS)

#: Cadencias que se reconocen, con su paso en días y cuánta tolerancia
#: se le da antes de llamarla atrasada. La tolerancia no es un número
#: redondo por gusto: una carga diaria que no corrió el fin de semana no
#: está rota, y una mensual que llega el día 3 tampoco.
CADENCIAS: tuple[tuple[str, float, float], ...] = (
    ("diaria", 1.0, 3.0),
    ("semanal", 7.0, 10.0),
    ("quincenal", 15.0, 20.0),
    ("mensual", 30.0, 40.0),
    ("trimestral", 91.0, 115.0),
)

_RE_FECHA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def _a_fecha(valor) -> date | None:
    """Una fecha de verdad, o `None`. Nunca una aproximación."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    m = _RE_FECHA.match(str(valor or "").strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _columna_fecha(tabla: dict) -> str | None:
    """La columna por la que se mide la frescura de esta tabla.

    Se prefiere la declarada como fecha en el modelo; el nombre solo se
    mira si no hay ninguna tipada, porque el tipo lo puso el pipeline y
    el nombre lo puso quien armó el Excel.
    """
    columnas = tabla.get("columnas") or []
    tipadas = [c["nombre"] for c in columnas if c.get("tipo") == "dateTime"]
    if tipadas:
        return tipadas[0]
    for c in columnas:
        if re.search(r"fecha|date|periodo|dia\b", c["nombre"], re.IGNORECASE):
            return c["nombre"]
    return None


def _cadencia(fechas: list[date]) -> tuple[str, float] | None:
    """Cada cuánto llegan datos nuevos, deducido de las fechas presentes.

    Se usa la MEDIANA de los saltos y no el promedio: un hueco por un
    feriado o una carga que faltó arrastraría el promedio y haría pasar
    una tabla diaria por semanal.
    """
    unicas = sorted(set(fechas))
    if len(unicas) < 3:
        return None
    saltos = sorted((unicas[i + 1] - unicas[i]).days
                    for i in range(len(unicas) - 1))
    mediana = saltos[len(saltos) // 2]
    if mediana <= 0:
        return None
    mejor = min(CADENCIAS, key=lambda c: abs(c[1] - mediana))
    return (mejor[0], mejor[2]) if abs(mejor[1] - mediana) <= mejor[1] else None


def _de_una_tabla(tabla_cat: dict, tabla_tmsl: dict, hoy: date,
                  cargado: str, crudas: dict | None = None,
                  totales: dict | None = None) -> dict:
    from .dataset import filas_embebidas

    nombre = tabla_cat["nombre"]
    fila = {"tabla": nombre, "columna": "", "filas": None,
            "fecha_datos": None, "fecha_carga": cargado,
            "cadencia": "", "dias": None, "estado": SIN_DATOS}

    # Las filas EMPOTRADAS son las que viajan dentro del archivo, pero
    # arriba del techo de empotrado (tablas grandes) no hay ninguna — y
    # esas son justo las tablas de producción para las que se mira un
    # panel de cargas. Sus filas sí están: en el dataset que se cargó en
    # esta sesión. Se prueban las dos fuentes antes de decir «no se puede
    # medir», porque decirlo cuando el dato estaba a mano es la manera de
    # que el panel quede en blanco en el único caso que importa.
    datos = filas_embebidas(tabla_tmsl) or (crudas or {}).get(nombre)
    if not datos:
        # Ni adentro ni en la sesión: la tabla apunta afuera (o es
        # calculada) y este panel no va a inventar por dónde.
        return fila
    columnas, filas = datos

    # El total REAL de la tabla, que arriba del techo NO es el de las filas
    # que se leyeron: el lector corta en 50.001 a propósito. Decir «50.001
    # filas» de un archivo de 200.000 es la clase de número que se copia a
    # una presentación.
    total = (totales or {}).get(nombre)
    parcial = bool(total and total > len(filas))
    fila["filas"] = total or len(filas)

    col = _columna_fecha(tabla_cat)
    if not col or col not in columnas:
        fila["estado"] = SIN_FECHA
        return fila
    fila["columna"] = col

    i = columnas.index(col)
    fechas = [f for f in (_a_fecha(x[i]) for x in filas if i < len(x)) if f]
    if not fechas:
        fila["estado"] = SIN_FECHA
        return fila

    ultima = max(fechas)
    fila["fecha_datos"] = ultima.isoformat()
    fila["dias"] = (hoy - ultima).days

    cad = _cadencia(fechas)
    if cad:
        fila["cadencia"], tolerancia = cad
        fila["estado"] = AL_DIA if fila["dias"] <= tolerancia else ATRASADA
    else:
        # Sin cadencia reconocible no se puede decir si está atrasada:
        # tres fechas sueltas no son un ritmo. Se informa la antigüedad y
        # se deja el juicio a quien conoce el proceso.
        fila["estado"] = AL_DIA if fila["dias"] <= 1 else SIN_FECHA

    if parcial and fila["estado"] != AL_DIA:
        # De una lectura parcial la fecha máxima es un PISO, no la fecha
        # de la tabla: las filas que no se leyeron solo pueden ser más
        # nuevas. Por eso «al día» sí se puede afirmar —el piso ya alcanza
        # y el resto no lo empeora— y «atrasada» NO: la carga de ayer
        # puede estar en las filas que quedaron sin leer. Un rojo falso
        # cuesta lo mismo que un verde falso: una reunión entera.
        fila["estado"] = PARCIAL
        fila["fecha_datos"], fila["dias"] = None, None
    return fila


def panel(modelo: dict, hoy: date | None = None,
          idioma: str = IDIOMA_DEFECTO, meta: dict | None = None) -> dict:
    """Una fila por tabla con hasta cuándo llegan sus datos.

    `hoy` se puede fijar para que los tests no dependan del calendario —
    un panel que se pone en rojo solo porque pasó el tiempo no se puede
    testear. `meta` es el dataset crudo de la sesión, cuando lo hay: sin
    él, una tabla demasiado grande para viajar dentro del archivo sale
    como «no se puede medir» aunque sus filas estén cargadas.
    """
    from .dataset import datos_de_meta
    from .gobernanza import leer

    hoy = hoy or datetime.now(timezone.utc).date()
    manifiesto = leer(modelo) or {}
    cargado = manifiesto.get("generado") or ""

    cat = Catalogo.desde_modelo(modelo)
    por_nombre = {t.get("name"): t
                  for t in modelo.get("model", {}).get("tables", [])}
    crudas = datos_de_meta(meta) if meta else {}
    totales = {t.get("nombre", ""): t.get("filas")
               for t in (meta or {}).get("tablas", []) or []}

    filas = [_de_una_tabla(t, por_nombre.get(t["nombre"], {}), hoy, cargado,
                           crudas, totales)
             for t in cat.tablas if not t.get("interna")]

    conteo = {e: sum(1 for f in filas if f["estado"] == e) for e in ESTADOS}
    medibles = [f for f in filas if f["fecha_datos"]]
    return {
        "hoy": hoy.isoformat(),
        "cargado": cargado,
        "filas": filas,
        "conteo": conteo,
        # La tabla que más atrasada está manda: un tablero es tan fresco
        # como su peor fuente, y promediar la antigüedad esconde justo la
        # que hay que mirar.
        "peor": max((f for f in medibles), key=lambda f: f["dias"], default=None),
        "total_filas": sum(f["filas"] or 0 for f in filas),
    }


def estado_texto(estado: str, idioma: str = IDIOMA_DEFECTO) -> str:
    return traducir(f"fr_estado_{estado}", idioma)


def documento(pan: dict, idioma: str = IDIOMA_DEFECTO) -> list[tuple]:
    """El panel como bloques de `documento.py` — HTML, Word y PDF."""
    guion = "—"
    doc: list[tuple] = [
        ("p", traducir("fr_intro", idioma)),
        ("kv", [
            (traducir("fr_c_hoy", idioma), pan["hoy"]),
            (traducir("fr_c_carga", idioma), pan["cargado"] or guion),
            (traducir("fr_al_dia", idioma), pan["conteo"][AL_DIA]),
            (traducir("fr_atrasadas", idioma), pan["conteo"][ATRASADA]),
        ]),
        ("tabla",
         [traducir("fr_c_tabla", idioma), traducir("fr_c_filas", idioma),
          traducir("fr_c_datos", idioma), traducir("fr_c_cadencia", idioma),
          traducir("fr_c_dias", idioma), traducir("fr_c_estado", idioma)],
         [[f["tabla"],
           guion if f["filas"] is None else f["filas"],
           f["fecha_datos"] or guion,
           traducir(f'fr_cad_{f["cadencia"]}', idioma) if f["cadencia"] else guion,
           guion if f["dias"] is None else f["dias"],
           estado_texto(f["estado"], idioma)]
          for f in pan["filas"]]),
    ]
    if pan["peor"]:
        doc.append(("nota", "warn" if pan["conteo"][ATRASADA] else "info",
                    traducir("fr_peor", idioma),
                    traducir("fr_peor_detalle", idioma).format(
                        tabla=pan["peor"]["tabla"],
                        fecha=pan["peor"]["fecha_datos"],
                        dias=pan["peor"]["dias"])))
    doc.append(("nota", "info", traducir("fr_honestidad_t", idioma),
                traducir("fr_honestidad", idioma)))
    return doc
