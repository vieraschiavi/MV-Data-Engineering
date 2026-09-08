# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Carga y escritura de archivos de Power BI.

Formatos que entiende:

  · .pbit  — Power BI Template. Es un zip con el modelo tabular (TMSL) en
             `DataModelSchema` y el reporte en `Report/Layout`, ambos en
             UTF-16 LE con BOM. Se lee y se escribe completo.
  · PBIP   — Power BI Project. Carpetas *.SemanticModel (model.bim) y
             *.Report (report.json). Se lee y se escribe completo.
  · .bim   — el modelo TMSL suelto (Tabular Editor lo abre directo).
  · .pbix  — se lee el LAYOUT del reporte y, de ahí, un catálogo parcial.
             El modelo tabular de un .pbix viaja en `DataModel`, un binario
             comprimido propietario de Analysis Services (Xpress9) que no se
             puede abrir desde afuera de Power BI. No se inventa lo que no se
             puede leer: se avisa y se ofrece el camino .pbit/PBIP.

Todas las funciones trabajan sobre dicts planos de Python (el JSON de TMSL
tal cual), sin clases intermedias: lo que se carga se puede volver a escribir.
"""
from __future__ import annotations

import copy
import io
import json
import re
import uuid as _uuid
import zipfile
from pathlib import Path

from . import pbir


# ==========================================================================
# Codificación interna de .pbit / .pbix
# ==========================================================================
def _u16(texto: str) -> bytes:
    """Las partes internas de un .pbit van en UTF-16 LE **sin BOM**.

    Así las escribe Power BI Desktop (verificado sobre archivos reales — el
    mismo hallazgo documentado en corrector.py para `Report/Layout`). Antes
    esto anteponía el BOM `FF FE`, y Power BI rechazaba las plantillas
    exportadas con «el archivo está cifrado o dañado»: para un lector que
    decodifica UTF-16-LE crudo, el BOM es un carácter basura delante del
    `{` y el JSON ya no parsea. Nuestro propio `_des16` tolera las dos
    variantes, así que el error nunca aparecía de este lado — solo en
    Desktop, que es donde importa.
    """
    return texto.encode("utf-16-le")


def _des16(crudo: bytes) -> str:
    """Decodifica una parte interna, tolerando BOM UTF-16 o UTF-8 plano."""
    if crudo[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return crudo.decode("utf-16")
    if crudo[:3] == b"\xef\xbb\xbf":
        return crudo[3:].decode("utf-8")
    # Sin BOM — que es como Power BI escribe `Report/Layout`. Se decide por
    # el byte nulo: un texto UTF-8 no tiene ninguno, y un UTF-16-LE con
    # contenido ASCII tiene uno cada dos.
    #
    # Antes esto probaba UTF-8 primero y caía a UTF-16 sólo si reventaba, y
    # funcionaba de casualidad: los reportes en español tienen acentos, que en
    # UTF-16-LE dan bytes inválidos como UTF-8, así que el decode fallaba y el
    # fallback acertaba. Un reporte SIN un solo carácter no-ASCII decodifica
    # «bien» a una cadena llena de NULs, y ahí el JSON revienta y el archivo
    # queda ilegible sin explicación.
    if b"\x00" in crudo[:512]:
        return crudo.decode("utf-16-le")
    return crudo.decode("utf-8")


# Tipo MIME por extensión de los archivos embebidos (el logo del reporte).
# Un `<Default>` por extensión: es como lo escribe Power BI cuando pegás una
# imagen en el informe.
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".bmp": "image/bmp", ".svg": "image/svg+xml"}


def _content_types(con_datamashup: bool = False,
                   extensiones: set[str] | None = None,
                   pbir: bool = False) -> str:
    """El [Content_Types].xml del .pbit, declarando las partes que se escriben.

    Se arma en función de lo que realmente va adentro: declarar una parte que
    no existe —o escribir una sin declararla— es de las cosas que hacen que
    Power BI rechace el archivo como corrupto. `extensiones` son las de los
    recursos embebidos (imágenes), que se declaran como `<Default>`.
    """
    # El orden y los tipos son los que escribe Desktop, medidos sobre
    # archivos reales: los Override van en el mismo orden en que las
    # partes están en el zip, y `Settings`/`Metadata` se declaran como
    # `application/json` (el resto va con el tipo vacío).
    partes = ["/Version", "/DiagramLayout", "/Settings", "/Metadata",
              "/DataModelSchema"]
    if not pbir:
        partes.insert(1, "/Report/Layout")
    if con_datamashup:
        partes.append("/DataMashup")
    con_tipo = {"/Settings", "/Metadata"}
    overrides = "".join(
        f'<Override PartName="{p}" ContentType='
        f'"{"application/json" if p in con_tipo else ""}" />'
        for p in partes)
    # Con el tipo VACÍO, igual que el `json`. Es lo que escribe Desktop:
    # medido sobre sus archivos, el `<Default Extension="png">` va con
    # `ContentType=""`, no con `image/png`. El MIME correcto de la imagen
    # no es lo que este XML declara —acá se declara la parte del paquete—,
    # y poner uno que Desktop no escribe es apartarse del formato sin
    # ganar nada.
    defaults = "".join(
        f'<Default Extension="{ext.lstrip(".")}" ContentType="" />'
        for ext in sorted(extensiones or ()) if ext in _MIME)
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="json" ContentType="" />'
            f"{defaults}{overrides}</Types>")


# Compatibilidad: algunos módulos importaban la constante.
CONTENT_TYPES = _content_types()

# Cualquier `<Override>` de SecurityBindings en el [Content_Types].xml,
# escrito como sea (el orden de atributos cambia entre versiones). Mismo
# criterio que corrector.RE_SECURITY — duplicado a propósito: modelo.py es
# la capa de abajo y no debe importar del corrector.
# La versión del CONTENEDOR, y va atada al formato en que se escribe el
# reporte. Medido sobre 28 archivos reales, la correlación no tiene una
# sola excepción:
#
#     1.28  ->  Report/Layout        (el formato clásico, un solo JSON)
#     1.32  ->  Report/definition/   (PBIR, una carpeta por página/visual)
#
# Acá se escribe PBIR, así que la versión es 1.32. Cruzar el par —una
# versión con el otro formato— es una combinación que no existe en ningún
# archivo real, y Desktop la rechaza con «este archivo está dañado o se ha
# creado con una versión no reconocida de Power BI Desktop».
#
# Hubo dos errores encadenados acá, y conviene dejarlos escritos:
#
#  1. Se subió este número a 1.32 dejando el layout clásico adentro. Par
#     cruzado, archivo rechazado.
#  2. Se «corrigió» bajándolo a 1.28 para que fuera con el layout clásico.
#     El par cerraba, pero el archivo seguía sin abrir: la conclusión salía
#     de mirar `.pbix` y `.pbit` juntos, y los 1.28 + layout clásico del
#     inventario eran todos `.pbix`. Un `.pbix` es un archivo de datos, no
#     una plantilla, y Desktop no los lee igual.
#
# Mirando SOLO plantillas, los 13 `.pbit` reales son PBIR sin excepción.
# Por eso ahora el reporte se escribe en PBIR (ver `pbir.py`).
# `verificacion.py` verifica el par.
VERSION_PBIT = "1.32"

# El formato de reporte que corresponde a cada versión de contenedor.
VERSION_POR_FORMATO = {"layout": "1.28", "pbir": "1.32"}

# La release de Power BI y la versión del motor de Power Query que el
# archivo declara. Medidas sobre archivos reales: son números del
# PRODUCTO, no del contenido, y se copian en vez de inventarse porque su
# formato es un contrato de Microsoft que no se puede adivinar.
RELEASE_PBI = "2026.08"
VERSION_MASHUP = "2.105.1143.0"

RE_SECURITY = re.compile(r"<Override\b[^>]*SecurityBindings[^>]*/?>",
                         re.IGNORECASE)


# ==========================================================================
# Carga
# ==========================================================================
def cargar(ruta: str | Path) -> dict:
    """
    Carga un archivo/carpeta de Power BI y devuelve un dict con:

      formato       'pbit' | 'pbip' | 'bim' | 'pbix'
      modelo        el TMSL completo (dict) o None si no se pudo leer
      layout        el layout del reporte (dict) o None
      advertencias  lista de strings con lo que NO se pudo leer y por qué

    Un archivo corrupto o truncado (zip roto, JSON a medio escribir) no tira
    un traceback crudo — cae en `advertencias` como cualquier otro «no se
    pudo leer», que es lo que ya hacía `_cargar_pbip` para el caso de un
    model.bim faltante. Sin esto, subir un .pbit corrupto en la app rompía
    la pestaña con un `JSONDecodeError` sin traducir en vez de avisar.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe: {ruta}")

    sufijo = ruta.suffix.lower()
    if sufijo == ".pbit":
        formato, cargador = "pbit", _cargar_pbit
    elif sufijo == ".pbix":
        formato, cargador = "pbix", _cargar_pbix
    elif sufijo == ".bim" or (sufijo == ".json" and ruta.name != "report.json"):
        formato, cargador = "bim", _cargar_bim
    elif sufijo in (".csv", ".xlsx", ".sql"):
        # Datos crudos: no hay modelo que leer — se PROPONE uno (tipos
        # inferidos, relaciones deducidas, Power Query real) y sobre esa
        # propuesta corren el analizador y los arreglos como con un .pbit.
        from . import dataset as _dataset
        return _dataset.cargar(ruta)
    elif sufijo == ".pbip" or ruta.is_dir():
        formato, cargador = "pbip", _cargar_pbip
    else:
        raise ValueError(
            f"Formato no reconocido: {ruta.name}. "
            "Se aceptan .pbit, .pbix, .bim, .pbip, una carpeta PBIP, "
            "o datos crudos .csv, .xlsx y .sql."
        )
    try:
        return cargador(ruta)
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError,
            KeyError, OSError) as exc:
        return {"formato": formato, "modelo": None, "layout": None,
                "advertencias": [
                    f"No se pudo leer {ruta.name} ({type(exc).__name__}): "
                    f"{exc}. ¿El archivo está corrupto o incompleto?"],
                "origen": str(ruta)}


def _leer_pbir(z: zipfile.ZipFile) -> dict | None:
    """El reporte en formato PBIR (`Report/definition/*`) como layout clásico.

    Desde 2024 Power BI guarda el reporte como una carpeta de JSONs chicos
    —un `visual.json` por visual— en vez del `Report/Layout` monolítico.
    Es el formato por defecto de los archivos NUEVOS: sin este lector, el
    programa quedaba ciego justo ante lo que la gente acaba de guardar.

    Se traduce a la MISMA forma que produce `Report/Layout`, así todas las
    reglas de reporte (RP01–RP08) corren sin enterarse del formato. Los
    campos que las reglas usan y dónde viven en PBIR:

      posición        visual.json → position{x, y, width, height}
      tipo            visual.json → visual.visualType
      campos          visual.json → visual.query (formas Column/Measure/
                      HierarchyLevel, las mismas que el formato viejo)
      filtros         visual.json → filterConfig (por visual)
      sincronizado    visual.json → visual.syncGroup
      formato         visual.json → visual.objects
      título          visual.json → visual.visualContainerObjects.title
      página oculta   page.json   → visibility == "HiddenInViewMode"
      filtro página   page.json   → filterConfig
      orden           pages.json  → pageOrder
    """
    nombres = z.namelist()
    meta = "Report/definition/pages/pages.json"
    if meta not in nombres:
        return None
    orden = json.loads(z.read(meta).decode("utf-8")).get("pageOrder", [])

    secciones = []
    for pid in orden:
        base = f"Report/definition/pages/{pid}"
        try:
            pj = json.loads(z.read(f"{base}/page.json").decode("utf-8"))
        except KeyError:
            continue
        vcs = []
        prefijo = f"{base}/visuals/"
        for n in nombres:
            if not (n.startswith(prefijo) and n.endswith("/visual.json")):
                continue
            v = json.loads(z.read(n).decode("utf-8"))
            vis = v.get("visual") or {}
            sv = {
                "visualType": vis.get("visualType"),
                "query": vis.get("query"),
                "syncGroup": vis.get("syncGroup"),
                # `objects` es el FORMATO del visual: entre otras cosas,
                # el formato condicional (verde si crece, rojo si cae).
                # Sin leerlo acá, abrir un PBIR y volver a exportarlo
                # devolvía el archivo sin un solo semáforo —y en silencio,
                # porque el reporte seguía teniendo todos sus visuales.
                "objects": vis.get("objects"),
                "vcObjects": vis.get("visualContainerObjects"),
            }
            pos = v.get("position") or {}
            vcs.append({
                "x": pos.get("x", 0), "y": pos.get("y", 0),
                "z": pos.get("z"),
                "width": pos.get("width", 0), "height": pos.get("height", 0),
                "config": json.dumps({"singleVisual": sv},
                                     ensure_ascii=False),
                # dict, no string: `filtros_de` acepta los dos.
                "filters": v.get("filterConfig") or "",
            })
        secciones.append({
            "displayName": pj.get("displayName", pid),
            "config": json.dumps(
                {"visibility": 1}
                if pj.get("visibility") == "HiddenInViewMode" else {}),
            "filters": pj.get("filterConfig") or "",
            "width": pj.get("width", 1280),
            "height": pj.get("height", 720),
            "visualContainers": vcs,
        })
    return {"sections": secciones, "formato_reporte": "pbir"}


def _cargar_pbit(ruta: Path) -> dict:
    resultado = {"formato": "pbit", "modelo": None, "layout": None,
                 "datamashup": None, "advertencias": [], "origen": str(ruta),
                 # El archivo entero, tal como vino. Es lo que permite que
                 # `exportar_pbit(original=...)` devuelva un contenedor
                 # idéntico al de Power BI Desktop (Metadata, Settings,
                 # DiagramLayout, el reporte PBIR completo...) en vez de
                 # fabricar uno desde cero que Desktop puede rechazar.
                 "crudo": ruta.read_bytes()}
    with zipfile.ZipFile(ruta) as z:
        nombres = set(z.namelist())
        if "DataModelSchema" in nombres:
            resultado["modelo"] = json.loads(_des16(z.read("DataModelSchema")))
        else:
            resultado["advertencias"].append(
                "El .pbit no trae DataModelSchema — ¿está corrupto?")
        if "Report/Layout" in nombres:
            resultado["layout"] = json.loads(_des16(z.read("Report/Layout")))
        else:
            resultado["layout"] = _leer_pbir(z)
        resultado["datamashup"] = _leer_datamashup(z, nombres)
    return resultado


def _leer_datamashup(z: zipfile.ZipFile, nombres: set) -> bytes | None:
    """Los bytes crudos de la parte `DataMashup`, si el archivo la trae.

    Ahí viven las consultas de Power Query (el código M) y las credenciales
    de conexión. Es un binario propietario: no se interpreta, se copia tal
    cual. Antes ni se leía, así que un modelo que entraba con sus consultas
    salía sin ellas y en Power BI no quedaba de dónde refrescar los datos —
    la pérdida era silenciosa, nadie la veía hasta abrir el archivo.
    """
    for nombre in ("DataMashup", "Formulas/Section1.m"):
        if nombre in nombres:
            return z.read(nombre)
    return None


def _cargar_pbix(ruta: Path) -> dict:
    resultado = {"formato": "pbix", "modelo": None, "layout": None,
                 "advertencias": [], "origen": str(ruta)}
    with zipfile.ZipFile(ruta) as z:
        nombres = set(z.namelist())
        # Algunos .pbix con modelo en vivo (live connection) sí traen el
        # esquema en claro. Si está, lo aprovechamos — y se guarda el
        # contenedor para poder reexportarlo (son chicos: no llevan datos).
        if "DataModelSchema" in nombres:
            resultado["modelo"] = json.loads(_des16(z.read("DataModelSchema")))
            resultado["crudo"] = ruta.read_bytes()
        elif "DataModel" in nombres:
            resultado["advertencias"].append(
                "El modelo tabular del .pbix viaja comprimido en un binario "
                "propietario de Analysis Services y no se puede leer desde "
                "afuera de Power BI. Se leyó el reporte (páginas y visuales) y "
                "un catálogo parcial de lo que los visuales referencian. Para "
                "el modelo completo: en Power BI Desktop, Archivo → Exportar → "
                "Plantilla de Power BI (.pbit), o guardar como Proyecto (PBIP)."
            )
        if "Report/Layout" in nombres:
            resultado["layout"] = json.loads(_des16(z.read("Report/Layout")))
        else:
            resultado["layout"] = _leer_pbir(z)
    return resultado


def _cargar_bim(ruta: Path) -> dict:
    modelo = json.loads(ruta.read_text(encoding="utf-8-sig"))
    # Un model.bim es el objeto database de TMSL: {name, compatibilityLevel,
    # model:{...}}. Si vino el `model` pelado, lo envolvemos para uniformar.
    if "model" not in modelo and "tables" in modelo:
        modelo = {"name": ruta.stem, "compatibilityLevel": 1606, "model": modelo}
    return {"formato": "bim", "modelo": modelo, "layout": None,
            "advertencias": [], "origen": str(ruta)}


def _cargar_pbip(ruta: Path) -> dict:
    """`ruta` puede ser el archivo .pbip o la carpeta que lo contiene."""
    base = ruta.parent if ruta.suffix.lower() == ".pbip" else ruta
    resultado = {"formato": "pbip", "modelo": None, "layout": None,
                 "advertencias": [], "origen": str(ruta)}

    bims = sorted(base.glob("*.SemanticModel/model.bim"))
    if ruta.suffix.lower() == ".pbip":
        # Si nos dieron el .pbip puntual, priorizamos su modelo homónimo.
        propio = base / f"{ruta.stem}.SemanticModel" / "model.bim"
        if propio.exists():
            bims = [propio]
    if bims:
        resultado["modelo"] = json.loads(bims[0].read_text(encoding="utf-8-sig"))
    else:
        tmdl = sorted(base.glob("*.SemanticModel/definition/*.tmdl"))
        if tmdl:
            resultado["advertencias"].append(
                "El modelo está en formato TMDL (carpeta definition/). Este "
                "motor lee model.bim (TMSL). En Power BI Desktop: Opciones → "
                "Vista previa → desactivar TMDL, o exportá un .pbit."
            )
        else:
            resultado["advertencias"].append(
                "No se encontró *.SemanticModel/model.bim junto al .pbip.")

    reportes = sorted(base.glob("*.Report/report.json"))
    if ruta.suffix.lower() == ".pbip":
        propio = base / f"{ruta.stem}.Report" / "report.json"
        if propio.exists():
            reportes = [propio]
    if reportes:
        resultado["layout"] = json.loads(reportes[0].read_text(encoding="utf-8-sig"))
    return resultado


# ==========================================================================
# Varios archivos del MISMO proyecto
# ==========================================================================
# Qué formato manda para el MODELO. Un .pbix casi nunca lo trae legible (su
# DataModel es binario propietario), mientras que el .pbit, el PBIP y el .bim
# lo traen completo en TMSL. Así que si llegan los dos, el modelo sale del
# segundo — que es exactamente el consejo que el programa venía dando por
# escrito y ahora puede aplicar solo.
_PRIORIDAD_MODELO = {"bim": 3, "pbip": 2, "pbit": 2, "pbix": 1,
                     # Un modelo INFERIDO de datos crudos pierde contra
                     # cualquier modelo real que venga en otro archivo.
                     "dataset": 0}


def _peso_layout(layout: dict | None) -> int:
    """Cuánto reporte hay realmente acá. Decide cuál de dos layouts se queda."""
    if not layout:
        return 0
    secciones = layout.get("sections") or []
    return sum(1 + len(s.get("visualContainers") or []) for s in secciones)


def combinar(cargados: list[dict]) -> dict:
    """Funde varios archivos del mismo proyecto en un solo `cargado`.

    Nace de un pedido concreto: «que permita subir más de 1 archivo, por
    ejemplo el .pbix y el .pbit del mismo proyecto, y no tenga esos errores
    que muestra». Los dos archivos son mitades complementarias del mismo
    trabajo:

        .pbix  →  el REPORTE de verdad (páginas, visuales, filtros), pero su
                  modelo viaja en un binario propietario e ilegible.
        .pbit  →  el MODELO completo en TMSL, con un reporte que puede estar
                  más pobre o directamente vacío.

    Por separado, cada uno deja al programa medio ciego. Juntos se cubren, y
    el aviso de «no se pudo leer el modelo del .pbix» deja de tener sentido:
    el modelo SÍ está, vino del otro archivo. Por eso ese aviso se descarta
    cuando el modelo aparece — un cartel de error que ya no es cierto es
    ruido que le hace creer al usuario que algo quedó mal.

    `crudo` y `datamashup` se toman SIEMPRE del archivo que aportó el modelo:
    son su contenedor y sus consultas. Mezclarlos con los de otro archivo
    produciría un .pbit que no corresponde a nada.
    """
    utiles = [c for c in cargados if c]
    if not utiles:
        raise ValueError("No se cargó ningún archivo.")

    # Varios archivos CRUDOS (CSV/Excel/SQL) no compiten entre sí como
    # compiten un .pbit y un .pbix: son tablas del mismo dataset. Se funden
    # en UNA propuesta — re-infiriendo las relaciones sobre el conjunto —
    # antes de que el resto de la combinación elija fuentes.
    crudos = [c for c in utiles if c.get("formato") == "dataset"]
    if len(crudos) > 1:
        from . import dataset as _dataset
        fusionado = _dataset.fusionar(crudos)
        utiles = [c for c in utiles
                  if c.get("formato") != "dataset"] + [fusionado]

    if len(utiles) == 1:
        return utiles[0]

    con_modelo = [c for c in utiles if c.get("modelo")]
    fuente_modelo = max(
        con_modelo,
        key=lambda c: _PRIORIDAD_MODELO.get(c.get("formato", ""), 0),
        default=None)
    fuente_layout = max(utiles, key=lambda c: _peso_layout(c.get("layout")))

    avisos: list[str] = []
    for c in utiles:
        for a in c.get("advertencias", []):
            # El aviso de «el modelo del .pbix es ilegible» ya no aplica si
            # otro archivo lo trajo. Se compara por la frase que lo
            # identifica y no por igualdad exacta: el texto se traduce.
            if fuente_modelo is not None and "propietario" in a:
                continue
            if a not in avisos:
                avisos.append(a)

    combinado = {
        "formato": "+".join(dict.fromkeys(c.get("formato", "?")
                                          for c in utiles)),
        "modelo": fuente_modelo.get("modelo") if fuente_modelo else None,
        "layout": fuente_layout.get("layout"),
        "advertencias": avisos,
        "origen": " + ".join(str(c.get("origen", "")) for c in utiles),
        # Del MISMO archivo que el modelo, no del que quedó más a mano.
        "crudo": fuente_modelo.get("crudo") if fuente_modelo else None,
        "datamashup": (fuente_modelo.get("datamashup")
                       if fuente_modelo else None),
        # Para poder decirlo en pantalla en vez de que el usuario adivine de
        # cuál de los archivos salió cada mitad.
        "de_modelo": fuente_modelo.get("origen") if fuente_modelo else None,
        "de_reporte": (fuente_layout.get("origen")
                       if fuente_layout.get("layout") else None),
        # Las notas de inferencia viajan solo si el modelo elegido es la
        # propuesta del dataset: pegadas a otro modelo serían mentira.
        "notas": (fuente_modelo.get("notas", [])
                  if fuente_modelo else []),
        # La materia prima del dataset, del MISMO archivo que el modelo.
        # Sin esto, subir un CSV junto a un .pbix ilegible daba un modelo
        # que venía del CSV pero sin sus filas: al exportar no se podían
        # meter los datos adentro, y el .pbit volvía a abrir vacío en la
        # máquina del cliente — el bug de campo, intacto y sin aviso.
        "dataset_meta": (fuente_modelo.get("dataset_meta")
                         if fuente_modelo else None),
    }
    return combinado


# ==========================================================================
# Escritura
# ==========================================================================
def _layout_clasico(layout: dict | None) -> bool:
    """¿Es un layout `Report/Layout` de verdad, escribible tal cual?

    `_leer_pbir` marca su traducción con `formato_reporte: "pbir"`. Esa
    traducción existe SOLO para que las reglas de reporte corran: conserva lo
    que las reglas miran y descarta el resto. Escribirla como `Report/Layout`
    produce un reporte al que le falta casi todo — era una de las razones por
    las que Power BI rechazaba el archivo exportado.
    """
    return layout is not None and layout.get("formato_reporte") != "pbir"


def _formato_layout(layout: dict | None) -> str:
    """`layout` o `pbir`: en qué formato hay que escribir este reporte."""
    return "layout" if _layout_clasico(layout) else "pbir"


def _formato_reporte(nombres) -> str:
    """El formato del reporte que trae un contenedor, por sus partes."""
    if any(str(n).startswith("Report/definition/") for n in nombres):
        return "pbir"
    return "layout" if "Report/Layout" in set(nombres) else "pbir"


def _reexportar_pbit(original: bytes, modelo: dict, layout: dict | None,
                     destino: Path,
                     recursos: dict[str, bytes] | None = None) -> Path:
    """El mismo contenedor que escribió Power BI, con el modelo nuevo adentro.

    Se copia cada parte byte a byte (Metadata, Settings, DiagramLayout, el
    reporte PBIR completo, DataMashup...) y se reemplaza únicamente lo que
    este programa realmente cambió: `DataModelSchema` siempre, y
    `Report/Layout` solo si el original lo traía y el layout en memoria es el
    clásico (el mismo objeto cargado, mutado por las transformaciones).

    `SecurityBindings` se descarta, junto con su declaración en
    [Content_Types].xml: es un blob DPAPI atado a la máquina y al usuario que
    guardó el archivo original; dejarlo desincronizado del contenido nuevo es
    motivo de rechazo. Power BI simplemente vuelve a pedir credenciales.
    """
    nuevos = {RECURSOS_PBIT + n: d for n, d in (recursos or {}).items()}
    with zipfile.ZipFile(io.BytesIO(original)) as zin, \
            zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        # La `Version` la manda el formato del reporte que el contenedor
        # LLEVA, no la que venía escrita. Copiarla a ciegas propagaba el
        # par cruzado: un archivo que entra con 1.32 sobre `Report/Layout`
        # —el formato de la 1.28— sale igual de roto, y Desktop lo rechaza
        # con «está dañado o se ha creado con una versión no reconocida».
        # Un programa que arregla modelos no puede devolver intacto un
        # contenedor que sabe leer como inválido.
        version = VERSION_POR_FORMATO[_formato_reporte(zin.namelist())]
        for info in zin.infolist():
            n = info.filename
            if n == "SecurityBindings" or n in nuevos:
                continue          # el recurso nuevo pisa al viejo homónimo
            if n == "Version":
                zout.writestr(n, _u16(version))
            elif n == "[Content_Types].xml":
                # `utf-8-sig` se come el BOM al decodificar y `writestr`
                # de un str lo escribe sin él: el archivo reexportado
                # perdía un BOM que el original SÍ traía. Se repone, que
                # es como lo escribe Desktop en todos los archivos reales.
                xml = RE_SECURITY.sub(
                    "", zin.read(n).decode("utf-8-sig", "replace"))
                zout.writestr(n, b"\xef\xbb\xbf" + _declarar_extensiones(
                    xml, nuevos).encode("utf-8"))
            elif n == "DataModelSchema":
                zout.writestr(n, _u16(json.dumps(
                    preparar_para_desktop(modelo), ensure_ascii=False)))
            elif n == "Report/Layout" and _layout_clasico(layout):
                zout.writestr(n, _u16(json.dumps(layout, ensure_ascii=False)))
            else:
                zout.writestr(n, zin.read(n))
        for n, datos in nuevos.items():
            zout.writestr(n, datos)
    return destino


def _declarar_extensiones(xml: str, recursos: dict[str, bytes]) -> str:
    """Agrega al [Content_Types].xml los `<Default>` de las extensiones que
    el contenedor todavía no declara. Sin esto, una imagen embebida vuelve
    corrupto todo el archivo — el paquete OPC exige declarar cada tipo."""
    for ext in sorted({Path(n).suffix.lower() for n in recursos}):
        if ext not in _MIME:
            continue
        seco = ext.lstrip(".")
        if f'Extension="{seco}"' in xml:
            continue
        corte = xml.find(">", xml.find("<Types")) + 1
        xml = (xml[:corte]
               + f'<Default Extension="{seco}" '
                 f'ContentType="{_MIME[ext]}" />'
               + xml[corte:])
    return xml


RECURSOS_PBIT = "Report/StaticResources/RegisteredResources/"


# El nivel de compatibilidad mínimo que Desktop acepta JUNTO con
# `defaultPowerBIDataSourceVersion = powerBI_V3`, medido sobre archivos
# reales (dos .pbit distintos, ambos en 1606). Ponerle la bandera a un
# modelo en un nivel más viejo —1567, el que este programa usaba antes de
# saber esto— no da el síntoma anterior (panel de datos vacío): da uno
# peor. Desktop rechaza el archivo ENTERO al abrirlo, antes de intentar
# leer nada: «Este archivo está dañado o se ha creado con una versión no
# reconocida de Power BI Desktop». La bandera y el nivel viajan juntos; no
# se puede subir una sin la otra.
COMPATIBILIDAD_V3 = 1606


def preparar_para_desktop(modelo: dict) -> dict:
    """Completa el modelo con lo que Power BI Desktop EXIGE para leerlo.

    Esto no es cosmética: sin `defaultPowerBIDataSourceVersion` en
    «powerBI_V3», Desktop interpreta el modelo con el formato viejo, donde
    las consultas de Power Query NO viven en las particiones sino en una
    parte binaria aparte (`DataMashup`). Como esa parte no existe en un
    archivo armado desde cero, Desktop no encuentra ninguna consulta,
    DESCARTA EL MODELO ENTERO y abre el archivo con el panel de datos
    vacío: «Aún no ha cargado ningún dato».

    El reporte carga igual —las páginas y el logo aparecen— así que el
    archivo parece medio bien y está del todo mal: cada visual queda
    huérfano. Es exactamente el síntoma que se reportó desde el campo, y
    el que un round-trip contra nuestro propio lector no puede detectar:
    nuestro lector entiende las particiones, Desktop no las mira siquiera.

    Se completa también lo que Desktop escribe siempre y algunos motores
    esperan: la cultura de las consultas, las opciones de acceso a datos y
    el orden de las consultas.
    """
    modelo = copy.deepcopy(modelo)
    m = modelo.setdefault("model", {})
    cultura = m.get("culture") or "es-ES"
    m["culture"] = cultura
    # LA bandera. Sin ella, nada de lo de abajo importa. Se anota si YA
    # estaba puesta (un modelo que vino de un .pbit real que la traía) para
    # no tocarle el nivel de compatibilidad a algo que Desktop mismo
    # escribió con una combinación propia.
    tenia_v3 = "defaultPowerBIDataSourceVersion" in m
    m.setdefault("defaultPowerBIDataSourceVersion", "powerBI_V3")
    m.setdefault("sourceQueryCulture", cultura)
    m.setdefault("dataAccessOptions", {"legacyRedirects": True,
                                       "returnErrorValuesAsNull": True})
    if tenia_v3:
        modelo.setdefault("compatibilityLevel", COMPATIBILIDAD_V3)
    else:
        # La bandera es NUEVA acá: el nivel tiene que acompañarla, aunque
        # el modelo ya trajera uno más bajo (`dataset.py` fija 1567 desde
        # que se propone el modelo, antes de saber que esto iba a hacer
        # falta). `setdefault` no alcanza — hay que subir lo que ya está.
        modelo["compatibilityLevel"] = max(
            modelo.get("compatibilityLevel") or 0, COMPATIBILIDAD_V3)

    # El orden de las consultas en el panel: Desktop lo escribe siempre y
    # sin él las tablas aparecen en un orden arbitrario.
    orden = [t.get("name") for t in m.get("tables", [])
             if t.get("name") and any(
                 p.get("source", {}).get("type") == "m"
                 for p in t.get("partitions", []))]
    anotaciones = {a.get("name"): a for a in m.get("annotations", [])}
    if orden and "PBI_QueryOrder" not in anotaciones:
        m.setdefault("annotations", []).append(
            {"name": "PBI_QueryOrder",
             "value": json.dumps(orden, ensure_ascii=False)})

    for t in m.get("tables", []):
        t.setdefault("lineageTag", str(_uuid.uuid4()))
        for c in t.get("columns", []):
            c.setdefault("lineageTag", str(_uuid.uuid4()))
            c.setdefault("summarizeBy", "none")
        for p in t.get("partitions", []):
            # Desktop nombra las particiones «<tabla>-<guid>». No es
            # obligatorio, pero sí que el nombre sea único en el modelo.
            p.setdefault("mode", "import")

    # El rastro de cómo se armó este modelo, para que un programa de
    # gobierno de datos no tenga que adivinarlo. Va acá y no en cada
    # exportador porque todos pasan por esta función: el .pbit, la
    # reexportación sobre el contenedor original y el PBIP. Si algo falla
    # al armarlo, el archivo sale igual sin el rastro — un manifiesto es
    # un extra, y ningún extra puede impedir que se entregue el tablero.
    try:
        from .gobernanza import anotar
        modelo = anotar(modelo)
    except Exception:                                     # noqa: BLE001
        pass
    return modelo


def _diagrama(modelo: dict) -> dict:
    """El `DiagramLayout`: dónde se dibuja cada tabla en la vista Modelo.

    Se acomoda como un ESQUEMA ESTRELLA, que es lo que el modelo es:
    las dimensiones arriba, los hechos abajo, y cada hecho centrado bajo
    las dimensiones a las que se conecta. Así las relaciones quedan
    cortas y verticales, y de un vistazo se ve quién filtra a quién.

    Antes era una grilla de cinco columnas por orden de aparición: las
    tablas caían donde tocaba y las relaciones cruzaban el diagrama de
    lado a lado, con lo cual la vista Modelo no decía nada. La grilla es
    más fácil de escribir y es exactamente igual de inútil para leer.

    Power BI reordena en cuanto el usuario mueve una tabla; esto es el
    punto de partida, y un punto de partida legible ahorra el rato de
    acomodarlas a mano.
    """
    m = modelo.get("model", modelo)
    tablas = [t for t in m.get("tables", [])
              if not t.get("name", "").startswith(("LocalDateTable_",
                                                   "DateTableTemplate_"))]
    nombres = [t.get("name", "") for t in tablas]

    # Quién está del lado «muchos» (hecho) y quién del lado «uno»
    # (dimensión). Una tabla puede ser las dos cosas —una dimensión
    # puente— y en ese caso manda el lado «muchos»: es donde vive el dato.
    desde = {r.get("fromTable") for r in m.get("relationships", [])}
    hacia = {r.get("toTable") for r in m.get("relationships", [])}
    # Una tabla que solo tiene medidas no es ni hecho ni dimensión: es el
    # cajón de las medidas y va aparte, sin estorbar la lectura.
    solo_medidas = {t["name"] for t in tablas
                    if t.get("measures") and not [
                        c for c in t.get("columns", [])
                        if not c.get("isHidden")]}
    hechos = [n for n in nombres if n in desde and n not in solo_medidas]
    dims = [n for n in nombres
            if n in hacia and n not in desde and n not in solo_medidas]
    sueltas = [n for n in nombres
               if n not in hechos and n not in dims and n not in solo_medidas]

    ANCHO_N, ALTO_N, SEP_X, SEP_Y = 234.0, 240.0, 60.0, 300.0
    paso = ANCHO_N + SEP_X
    ubic: dict[str, tuple[float, float]] = {}

    # Fila de arriba: las dimensiones, en su orden.
    for i, n in enumerate(dims):
        ubic[n] = (i * paso, 0.0)

    # Fila de abajo: cada hecho bajo el centro de SUS dimensiones, para
    # que sus relaciones bajen rectas en vez de cruzar el diagrama.
    por_hecho: dict[str, list[float]] = {}
    for r in m.get("relationships", []):
        f, t = r.get("fromTable"), r.get("toTable")
        if f in hechos and t in ubic:
            por_hecho.setdefault(f, []).append(ubic[t][0])
    orden = sorted(hechos, key=lambda h: (sum(por_hecho.get(h, [0.0]))
                                          / max(len(por_hecho.get(h, [1])), 1)))
    for i, n in enumerate(orden):
        ubic[n] = (i * paso, ALTO_N + SEP_Y)

    # Lo que no participa de ninguna relación va en una tercera fila: no
    # tiene con quién alinearse y no debe meterse entre los que sí.
    for i, n in enumerate(sueltas):
        ubic[n] = (i * paso, 2 * (ALTO_N + SEP_Y))
    # El cajón de medidas: a la izquierda y a media altura entre las dos
    # filas, para que se lea como lo que es —ni hecho ni dimensión— en
    # vez de mezclarse en la fila de las dimensiones.
    medio = (ALTO_N + SEP_Y) / 2
    for i, n in enumerate(sorted(solo_medidas)):
        ubic[n] = (-paso, medio + i * (ALTO_N + 40.0))

    # Que nada quede en coordenada negativa: Power BI dibuja desde 0,0.
    dx = -min((x for x, _y in ubic.values()), default=0.0)
    nodos = [{"location": {"x": ubic.get(n, (0.0, 0.0))[0] + dx,
                           "y": ubic.get(n, (0.0, 0.0))[1]},
              "nodeIndex": n,
              "size": {"height": ALTO_N, "width": ANCHO_N},
              "zIndex": i}
             for i, n in enumerate(nombres)]
    return {"version": "1.1.0",
            "diagrams": [{"ordinal": 0,
                          "scrollPosition": {"x": 0, "y": 0},
                          "nodes": nodos,
                          "name": "All tables",
                          "zoomValue": 90,
                          "pinKeyFieldsToTop": False,
                          "showAllFields": False,
                          "hideKeyFieldsWhenCollapsed": False}],
            # Cuál diagrama se abre y cuál es el de por defecto. Los dos
            # `.pbit` reales medidos los traen; sin ellos la vista Modelo
            # arranca sin diagrama seleccionado.
            "selectedDiagram": "All tables",
            "defaultDiagram": "All tables"}


def exportar_pbit(modelo: dict, layout: dict | None, destino: str | Path,
                  descripcion: str = "", datamashup: bytes | None = None,
                  original: bytes | None = None,
                  recursos: dict[str, bytes] | None = None) -> Path:
    """Escribe un .pbit para abrir con doble clic en Power BI Desktop.

    `original`: los bytes del .pbit del que salió el modelo (`cargar()` los
    devuelve en la clave `crudo`). Si están, el archivo NO se fabrica desde
    cero: se reexporta el contenedor original con el modelo nuevo adentro
    (ver `_reexportar_pbit`). Es el camino fiel — todo lo que Power BI
    escribió y este programa no tocó viaja byte a byte.

    `datamashup`: los bytes de la parte homónima del archivo de origen, si el
    modelo vino de un .pbit/.pbix que la traía (`cargar()` la devuelve en la
    clave `datamashup`). Ahí están las consultas de Power Query. Sin ella el
    archivo abre igual, pero el modelo queda sin origen de datos: no hay nada
    que refrescar. Se copia tal cual, no se interpreta — es un binario
    propietario de Microsoft. Con `original`, esta parte ya viaja adentro y
    el parámetro no hace falta.

    Para un modelo armado desde cero en la app no hay DataMashup que copiar, y
    ahí el .pbit sale sin esa parte, que es lo correcto: inventar una mal
    formada haría que Power BI lo rechace como corrupto.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if original:
        try:
            with zipfile.ZipFile(io.BytesIO(original)) as z:
                nombres = set(z.namelist())
        except zipfile.BadZipFile:
            nombres = None
        # El camino fiel sirve mientras el reporte que hay que escribir sea
        # del MISMO formato que el del contenedor original. Si no, hay que
        # armar desde cero: el contenedor no tiene dónde llevarlo.
        #
        # Los dos sentidos importan y sólo uno estaba contemplado:
        #
        #   · layout clásico nuevo sobre original PBIR — pisar el reporte
        #     PBIR con otra cosa sería corromperlo;
        #   · layout PBIR nuevo (el tablero GENERADO) sobre original
        #     clásico — el reexport no sabe escribir PBIR, así que dejaba
        #     el `Report/Layout` viejo y el tablero recién generado se
        #     perdía en silencio: el usuario pedía diez páginas nuevas y
        #     abría el archivo con las dos de antes.
        if nombres and "DataModelSchema" in nombres and (
                layout is None
                or _formato_reporte(nombres) == _formato_layout(layout)):
            return _reexportar_pbit(original, modelo, layout, destino,
                                    recursos)
    if not _layout_clasico(layout):
        layout = None
    # Estas tres partes se alinean con lo que escribe Power BI Desktop hoy,
    # medido sobre archivos reales. `QueriesSettings` no es decorativo: es
    # donde el template declara que hay consultas que ejecutar al abrir.
    metadata = {
        "Version": 5,
        "AutoCreatedRelationships": [],
        "FileDescription": descripcion or destino.stem,
        "CreatedFrom": "Cloud",
        # Con QUÉ release de Power BI se creó el archivo. Faltaba, y el
        # cartel que devolvía Desktop era, literalmente, «se ha creado con
        # una versión NO RECONOCIDA de Power BI Desktop»: sin este campo
        # no hay release que reconocer.
        "CreatedFromRelease": RELEASE_PBI,
    }
    settings = {
        "Version": 3,
        "ReportSettings": {},
        "QueriesSettings": {"TypeDetectionEnabled": True,
                            "RelationshipImportEnabled": True,
                            # La versión del motor de Power Query, que un
                            # archivo real siempre declara.
                            "Version": VERSION_MASHUP},
    }
    if layout is None:
        layout = {"id": 0, "resourcePackages": [], "sections": [],
                  "config": json.dumps({}), "layoutOptimization": 0}

    extensiones = {Path(n).suffix.lower() for n in (recursos or {})}
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        # El Content_Types tiene que declarar EXACTAMENTE las partes que se
        # escriben: si declara una que no está, o falta una que sí está, Power
        # BI da "corrupt or invalid report file".
        # `Version` PRIMERO y `[Content_Types].xml` segundo: es el orden
        # que traen los 28 archivos reales medidos, sin excepción. No está
        # documentado que importe, pero cuesta cero respetarlo y el
        # objetivo acá es parecerse a lo que Desktop escribe, no a lo que
        # el estándar OPC permitiría.
        z.writestr("Version", _u16(VERSION_PBIT))
        # Con BOM UTF-8, que es como lo escribe Desktop en todos los
        # archivos reales medidos.
        z.writestr("[Content_Types].xml",
                   b"\xef\xbb\xbf" + _content_types(
                       bool(datamashup), extensiones,
                       pbir=True).encode("utf-8"))
        z.writestr("DataModelSchema",
                   _u16(json.dumps(preparar_para_desktop(modelo),
                                   ensure_ascii=False)))
        z.writestr("DiagramLayout",
                   _u16(json.dumps(_diagrama(modelo), ensure_ascii=False)))
        # El reporte va en PBIR (`Report/definition/`), no en la parte
        # `Report/Layout`: es lo que trae CADA UNO de los .pbit reales
        # medidos, y lo que Desktop acepta en una plantilla.
        for parte, datos in pbir.partes(layout).items():
            z.writestr(parte, datos)
        z.writestr("Settings", _u16(json.dumps(settings, ensure_ascii=False)))
        z.writestr("Metadata", _u16(json.dumps(metadata, ensure_ascii=False)))
        if datamashup:
            # Bytes crudos: NO pasa por _u16(). Es un binario, no texto UTF-16.
            z.writestr("DataMashup", datamashup)
        for nombre, datos in (recursos or {}).items():
            # Igual que el DataMashup: binario, sin tocar. El layout ya los
            # declaró en su `resourcePackages` (ver tablero.envolver_layout).
            z.writestr(RECURSOS_PBIT + nombre, datos)
    return destino


def exportar_pbip(modelo: dict, layout: dict | None, carpeta: str | Path,
                  nombre: str, original: bytes | None = None) -> Path:
    """
    Escribe la estructura PBIP completa (control de versiones):
    <nombre>.pbip + <nombre>.SemanticModel/ + <nombre>.Report/.

    `original` (los bytes del .pbit de origen, clave `crudo` de `cargar()`):
    si trae el reporte en formato PBIR (`Report/definition/*`), esas partes se
    copian tal cual a `<nombre>.Report/` — que es exactamente la forma PBIR de
    un proyecto — en vez de escribir un `report.json` con la traducción de
    lectura, que es incompleta a propósito. Con un layout clásico nuevo (p.
    ej. el tablero generado) se escribe ese layout, como siempre.
    """
    carpeta = Path(carpeta)
    sm = carpeta / f"{nombre}.SemanticModel"
    rp = carpeta / f"{nombre}.Report"
    sm.mkdir(parents=True, exist_ok=True)
    rp.mkdir(parents=True, exist_ok=True)

    def esc(p: Path, obj) -> None:
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                     encoding="utf-8")

    esquema_plat = ("https://developer.microsoft.com/json-schemas/fabric/"
                    "gitIntegration/platformProperties/2.0.0/schema.json")
    esc(sm / ".platform", {
        "$schema": esquema_plat,
        "metadata": {"type": "SemanticModel", "displayName": nombre},
        "config": {"version": "2.0",
                   "logicalId": str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"sm{nombre}"))},
    })
    esc(sm / "definition.pbism", {"version": "1.0", "settings": {}})
    esc(sm / "model.bim", preparar_para_desktop(modelo))

    esc(rp / ".platform", {
        "$schema": esquema_plat,
        "metadata": {"type": "Report", "displayName": nombre},
        "config": {"version": "2.0",
                   "logicalId": str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"rp{nombre}"))},
    })
    esc(rp / "definition.pbir", {
        "version": "1.0",
        "datasetReference": {"byPath": {"path": f"../{nombre}.SemanticModel"}},
    })

    pbir_copiado = False
    if original and not _layout_clasico(layout):
        try:
            zin = zipfile.ZipFile(io.BytesIO(original))
        except zipfile.BadZipFile:
            zin = None
        if zin is not None:
            with zin:
                for n in zin.namelist():
                    # Report/definition/* y Report/StaticResources/* son,
                    # tal cual, el contenido de la carpeta .Report de un
                    # proyecto en formato PBIR. Se copian byte a byte.
                    if n.startswith(("Report/definition/",
                                     "Report/StaticResources/")) \
                            and not n.endswith("/"):
                        destino_parte = rp / Path(n).relative_to("Report")
                        destino_parte.parent.mkdir(parents=True,
                                                   exist_ok=True)
                        destino_parte.write_bytes(zin.read(n))
                        pbir_copiado = True
    if not pbir_copiado:
        if not _layout_clasico(layout):
            # Nunca escribir la traducción de lectura como reporte: mejor un
            # reporte vacío y válido que uno al que le falta casi todo.
            layout = None
        if layout is None:
            layout = {"id": 0, "resourcePackages": [], "sections": [],
                      "config": json.dumps({}), "layoutOptimization": 0}
        esc(rp / "report.json", layout)

    pbip = carpeta / f"{nombre}.pbip"
    esc(pbip, {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{nombre}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    return pbip


# ==========================================================================
# Utilidades sobre expresiones TMSL
# ==========================================================================
def expr_texto(expresion) -> str:
    """En TMSL una expresión puede ser un string o una lista de líneas."""
    if expresion is None:
        return ""
    if isinstance(expresion, list):
        return "\n".join(expresion)
    return str(expresion)


def expr_lineas(texto: str):
    """Inversa de expr_texto: TMSL prefiere lista de líneas si hay saltos."""
    return texto.split("\n") if "\n" in texto else texto
