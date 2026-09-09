# © 2026 Martín Viera. Todos los derechos reservados.

"""El traspaso de MV DAX Lab a un programa de gobierno de datos.

**El problema.** Una IA arma un tablero en segundos y ahí termina su
trabajo. Lo que queda después —quién es dueño de este dato, cómo se
definió este indicador, de dónde salió, se puede auditar, escala— no está
en ningún lado, y es exactamente lo que hace falta para que alguien tome
una decisión cara mirando la pantalla. El `.pbit` que sale de acá lleva el
modelo y el reporte; lo que NO llevaba era el rastro de cómo se armó.

**Lo que este módulo hace.** Escribe ese rastro adentro del propio
archivo, como una anotación del modelo TMSL. Va ahí y no en un archivo
aparte por dos razones: un documento suelto se pierde en el segundo
reenvío, y agregar una parte nueva al `.pbit` obliga a declararla en el
`[Content_Types].xml` —y una parte mal declarada es de las cosas que hacen
que Power BI Desktop rechace el archivo entero. Las anotaciones son
territorio estándar de TMSL: Desktop las conserva, no las muestra, y no
tocan el contenedor.

**Qué se anota y qué no.** Solo lo que este programa SABE y el que recibe
el archivo no puede deducir del TMSL:

- cuántas filas trae cada tabla (van comprimidas adentro del Power Query,
  así que contarlas desde afuera exige descomprimir);
- qué papel juega cada tabla en el modelo (hecho, dimensión, calendario,
  desconectada);
- por qué cada medida está escrita como está (`diccionario.porque`);
- cuál es la empresa propia, cuando se eligió una.

Lo que NO se anota, a propósito: dueño y steward del dato. Son decisiones
de la organización, no del generador. Ponerles «N/D» haría que una
política de responsables los contara como asignados, que es peor que
dejarlos vacíos.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .catalogo import Catalogo
from .i18n import IDIOMA_DEFECTO

#: Nombre de la anotación del modelo donde viaja el manifiesto.
ANOTACION = "MVDaxLab_Gobernanza"

#: Versión del formato del manifiesto. El que lo lee compara contra esto
#: antes de confiar en las claves: un manifiesto de una versión que no
#: conoce se ignora entero en vez de leerse a medias.
FORMATO = 1

GENERADOR = "MV DAX Lab"

HECHO, DIMENSION, CALENDARIO, SUELTA = "hecho", "dimension", "calendario", "suelta"


def _filas(tabla: dict) -> int | None:
    """Cuántas filas empotradas trae la tabla, o `None` si no trae."""
    from .dataset import filas_embebidas
    datos = filas_embebidas(tabla)
    return len(datos[1]) if datos else None


def _papeles(modelo: dict) -> dict[str, str]:
    """Qué papel juega cada tabla, leído de cómo la usan las relaciones.

    Del lado «muchos» de una relación y sin nadie que la apunte: es un
    hecho. Apuntada por otras: dimensión. Sin ninguna relación: suelta
    —el diccionario, la lectura, cualquier tabla de apoyo—. La de fechas
    se nombra aparte porque es la que habilita toda la inteligencia de
    tiempo, y un modelo sin ella es un modelo que no puede comparar
    períodos.
    """
    mm = modelo.get("model", {})
    tablas = [t.get("name", "") for t in mm.get("tables", [])]
    apuntadas, apuntan = set(), set()
    for r in mm.get("relationships", []) or []:
        apuntan.add(r.get("fromTable"))
        apuntadas.add(r.get("toTable"))
    cal = Catalogo.desde_modelo(modelo).tabla_fechas() or {}
    nombre_cal = cal.get("nombre") or cal.get("name")
    papeles = {}
    for nombre in tablas:
        if nombre == nombre_cal:
            papeles[nombre] = CALENDARIO
        elif nombre in apuntadas:
            papeles[nombre] = DIMENSION
        elif nombre in apuntan:
            papeles[nombre] = HECHO
        else:
            papeles[nombre] = SUELTA
    return papeles


def manifiesto(modelo: dict, idioma: str = IDIOMA_DEFECTO) -> dict:
    """El rastro de cómo se armó este modelo, listo para anotar."""
    from . import diccionario, empresa
    from .verificacion import conexion_de

    cat = Catalogo.desde_modelo(modelo)
    papeles = _papeles(modelo)

    tablas = []
    for t in modelo.get("model", {}).get("tables", []):
        nombre = t.get("name", "")
        origenes = {conexion_de((p.get("source") or {}).get("expression"))
                    for p in t.get("partitions", []) or []}
        tablas.append({
            "nombre": nombre,
            "filas": _filas(t),
            "columnas": len(t.get("columns", []) or []),
            "papel": papeles.get(nombre, SUELTA),
            "origen": sorted(origenes)[0] if origenes else "ninguna",
            "oculta": bool(t.get("isHidden")),
        })

    medidas = []
    for m in sorted(cat.medidas(), key=lambda x: x["nombre"]):
        medidas.append({
            "nombre": m["nombre"],
            "tabla": m.get("tabla") or "",
            "carpeta": m.get("carpeta") or "",
            "formato": m.get("formato") or "",
            "porque": diccionario.porque(m.get("expresion") or "", idioma),
        })

    return {
        "formato": FORMATO,
        "generador": GENERADOR,
        # Cuándo se escribió el archivo. Es el único dato de FECHA que se
        # puede afirmar: un .pbit no guarda cuándo se refrescó cada tabla
        # —en un modelo de importación eso vive en el workspace, no en el
        # archivo—, así que el panel de frescura usa esto para «fecha de
        # carga» y mide la frescura de los datos por otro lado.
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "idioma": idioma,
        "empresa_propia": empresa.propia(modelo) or "",
        "tablas": tablas,
        "medidas": medidas,
        "relaciones": len(modelo.get("model", {}).get("relationships", []) or []),
    }


def anotar(modelo: dict, idioma: str = IDIOMA_DEFECTO) -> dict:
    """Devuelve el modelo con el manifiesto puesto como anotación.

    Idempotente: vuelve a escribirlo si ya estaba, en vez de acumular
    anotaciones repetidas que el lector tendría que desempatar.
    """
    nuevo = json.loads(json.dumps(modelo))
    mm = nuevo.setdefault("model", {})
    anots = [a for a in mm.get("annotations", []) or []
             if a.get("name") != ANOTACION]
    anots.append({"name": ANOTACION,
                  "value": json.dumps(manifiesto(modelo, idioma),
                                      ensure_ascii=False,
                                      separators=(",", ":"))})
    mm["annotations"] = anots
    return nuevo


def leer(modelo: dict) -> dict | None:
    """El manifiesto de un modelo, o `None` si no lo trae o no se entiende.

    Nunca levanta: un archivo de otro generador —o de una versión futura
    del formato— tiene que poder abrirse igual, sin manifiesto, no dar un
    error. Que no haya rastro no es una falla del archivo; leerlo mal, sí.
    """
    for a in (modelo.get("model", {}).get("annotations") or []):
        if a.get("name") != ANOTACION:
            continue
        try:
            datos = json.loads(a.get("value") or "")
        except (ValueError, TypeError):
            return None
        if isinstance(datos, dict) and datos.get("formato") == FORMATO:
            return datos
        return None
    return None
