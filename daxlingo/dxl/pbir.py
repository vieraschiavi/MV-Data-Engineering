# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Escribir el reporte en formato PBIR.

Un `.pbit` guarda su reporte de dos formas posibles: el **layout clásico**
—un único `Report/Layout` con todo adentro— y **PBIR**, una carpeta
`Report/definition/` con un archivo por página y por visual.

**Por qué existe este módulo.** Los 13 `.pbit` reales medidos son TODOS
PBIR con `Version` 1.32. Ninguno usa el layout clásico. Los únicos que lo
usan son los que escribía este programa, y en Power BI Desktop daban
«este archivo está dañado o se ha creado con una versión no reconocida».
La confusión venía de mirar `.pbix` junto con `.pbit`: los `.pbix` sí
traen layout clásico con `Version` 1.28, pero un `.pbix` es un archivo de
datos, no una plantilla, y Desktop no los lee igual.

Acá se traduce el layout clásico —que es lo que arma `tablero.py`, y no
hace falta reescribir— a la forma que Desktop espera en una plantilla.
La traducción es determinista: cada `visualContainer` es un `visual.json`.

La única parte con enjundia es la consulta. El clásico la guarda en
`prototypeQuery`, con un `From` que da alias a las tablas y un `Select`
que las referencia por ese alias; PBIR la guarda en `query.queryState`,
agrupada por rol visual y **sin alias**, con la tabla nombrada directo.
Traducir es resolver el alias contra el `From` y agrupar por el rol que
ya dice `projections`.
"""
from __future__ import annotations

import copy
import json
import re

_BASE = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
         "definition/")
ESQUEMAS = {
    "version": f"{_BASE}versionMetadata/1.0.0/schema.json",
    "report": f"{_BASE}report/3.3.0/schema.json",
    "pages": f"{_BASE}pagesMetadata/1.1.0/schema.json",
    "page": f"{_BASE}page/2.1.0/schema.json",
    "visual": f"{_BASE}visualContainer/2.12.0/schema.json",
}
VERSION_PBIR = "2.0.0"

# El tema base del reporte, y el archivo del tema VIAJA en el paquete.
#
# Acá se cometió dos veces el mismo error, y las dos veces por medir sobre
# el archivo equivocado. La conclusión anterior —«el tema es uno integrado
# de Power BI, se declara y no viaja, porque lo trae Desktop»— salió de
# mirar un `.pbix` que Desktop escribió: ahí efectivamente se declara
# `BaseThemes/CY24SU10.json` y el archivo no está adentro.
#
# Pero un `.pbix` no es una plantilla. Medido sobre dos `.pbit` REALES,
# escritos por Desktop 2026.08, los dos traen el archivo del tema adentro:
#
#     Report/StaticResources/SharedResources/BaseThemes/CY22SU03.json
#
# Un `.pbix` se abre con el Desktop que lo escribió a mano; una plantilla
# viaja a otra máquina y tiene que ser autosuficiente. Declarar un recurso
# que no está en el paquete deja un puntero colgado, y Desktop responde
# «este archivo está dañado o se ha creado con una versión no reconocida».
#
# El tema que se escribe es PROPIO —nombre y paleta de este programa, o la
# del logo de quien exporta—, no una copia de uno de Microsoft: se declara
# lo que se puede escribir, y se escribe lo que se declara.
NOMBRE_TEMA = "MVDAXLab"

# La paleta del tema base cuando el informe no trae marca. Son los colores
# del producto; con logo, el primero se reemplaza por el de la empresa.
COLORES_TEMA = ("#1F4E79", "#2E9BDA", "#7DC242", "#F2B441", "#D64550",
                "#6B4EA0", "#0E8C7F", "#8C6D46")

# Las versiones de esquema que Desktop estampa al importar el tema.
VERSIONES_AL_IMPORTAR = {"visual": "1.8.91", "report": "2.0.91",
                         "page": "1.3.91"}

# En el clásico la opción de pantalla es un número; en PBIR, un nombre.
_DISPLAY = {1: "FitToPage", 2: "FitToWidth", 3: "ActualSize"}

_RE_SEGURO = re.compile(r"[^A-Za-z0-9_]+")


def _nombre_carpeta(nombre: str, usados: set[str], i: int) -> str:
    """Un nombre de carpeta seguro y único para una página o un visual.

    Va a ser una ruta dentro del zip, así que no puede llevar acentos,
    espacios ni barras. Si al limpiarlo queda vacío o repetido, se
    desempata con el ordinal — dos páginas nunca pueden compartir carpeta.
    """
    base = _RE_SEGURO.sub("", nombre or "")[:40] or f"Pagina{i}"
    candidato = base
    n = 0
    while candidato in usados:
        n += 1
        candidato = f"{base}{n}"
    usados.add(candidato)
    return candidato


def _objetos_de(config) -> dict:
    """Los `objects` de formato que la sección clásica guarda en su config."""
    try:
        return (json.loads(config or "{}") or {}).get("objects") or {}
    except (ValueError, TypeError):
        return {}


def _imagenes_declaradas(layout: dict | None) -> list[dict]:
    """Los recursos registrados (imágenes) que el layout clásico declara.

    La forma la escribe Desktop: `{name, path, type: "Image"}`. Sin esta
    declaración el archivo viaja adentro del paquete pero el visual de
    imagen no lo encuentra, que era la limitación anotada acá.
    """
    for envoltorio in (layout or {}).get("resourcePackages") or []:
        paquete = envoltorio.get("resourcePackage", {})
        if paquete.get("name") != "RegisteredResources":
            continue
        return [{"name": i.get("name") or i.get("path"),
                 "path": i.get("path"), "type": "Image"}
                for i in paquete.get("items") or [] if i.get("path")]
    return []


def _alias_de(proto: dict) -> dict[str, str]:
    """`{alias: tabla}` según el `From` de la consulta clásica."""
    return {f.get("Name", ""): f.get("Entity", "")
            for f in (proto or {}).get("From", []) if f.get("Name")}


def _sin_alias(nodo, alias: dict[str, str]):
    """La misma expresión con la tabla nombrada directo, sin el alias.

    PBIR no lleva el `From`, así que un `SourceRef` que apunta a `Source:
    "m0"` no tendría contra qué resolverse: se reemplaza por la entidad.
    """
    if isinstance(nodo, list):
        return [_sin_alias(x, alias) for x in nodo]
    if not isinstance(nodo, dict):
        return nodo
    if set(nodo) == {"Source"} and nodo["Source"] in alias:
        return {"Entity": alias[nodo["Source"]]}
    return {k: _sin_alias(v, alias) for k, v in nodo.items()}


def _query_state(sv: dict) -> dict:
    """`projections` + `prototypeQuery` → el `queryState` de PBIR.

    `projections` ya dice a qué rol visual va cada campo (`Values`,
    `Category`, `Rows`…) referenciándolo por `queryRef`; el campo en sí
    está en el `Select` de la consulta, bajo ese mismo nombre.
    """
    proto = sv.get("prototypeQuery") or {}
    alias = _alias_de(proto)
    por_ref = {}
    for sel in proto.get("Select", []):
        ref = sel.get("Name")
        if not ref:
            continue
        campo = {k: v for k, v in sel.items() if k != "Name"}
        por_ref[ref] = _sin_alias(campo, alias)

    estado = {}
    for rol, campos in (sv.get("projections") or {}).items():
        proyecciones = []
        for c in campos:
            ref = c.get("queryRef")
            if ref not in por_ref:
                continue
            entrada = {"field": por_ref[ref], "queryRef": ref}
            if c.get("displayName"):
                entrada["displayName"] = c["displayName"]
            proyecciones.append(entrada)
        if proyecciones:
            estado[rol] = {"projections": proyecciones}
    return {"queryState": estado} if estado else {}


def visual_pbir(contenedor: dict, nombre: str) -> dict:
    """Un `visualContainer` clásico como el `visual.json` de PBIR."""
    try:
        cfg = json.loads(contenedor.get("config") or "{}")
    except (ValueError, TypeError):
        cfg = {}
    sv = cfg.get("singleVisual") or {}

    visual = {"visualType": sv.get("visualType", "card")}
    consulta = _query_state(sv)
    if consulta:
        visual["query"] = consulta
    if sv.get("objects"):
        visual["objects"] = copy.deepcopy(sv["objects"])
    # En PBIR el formato del contenedor (fondo, borde, sombra) cambia de
    # nombre: `vcObjects` pasa a ser `visualContainerObjects`.
    if sv.get("vcObjects"):
        visual["visualContainerObjects"] = copy.deepcopy(sv["vcObjects"])
    if sv.get("drillFilterOtherVisuals") is not None:
        visual["drillFilterOtherVisuals"] = sv["drillFilterOtherVisuals"]

    return {
        "$schema": ESQUEMAS["visual"],
        "name": nombre,
        "position": {
            "x": contenedor.get("x", 0), "y": contenedor.get("y", 0),
            "z": contenedor.get("z", 0),
            "width": contenedor.get("width", 0),
            "height": contenedor.get("height", 0),
        },
        "visual": visual,
    }


def tema_base() -> dict:
    """El tema base que se escribe adentro del paquete.

    Un tema de Power BI es un JSON chico: el nombre, la lista de colores
    de datos y los tres colores de estructura. Alcanza con eso, y es lo
    que hace que el archivo sea autosuficiente.

    No lleva los colores de la marca de quien exporta: esos ya van puestos
    visual por visual —título, tarjetas, series propio vs mercado—, que es
    donde se ven. El tema es el piso para lo que ningún visual fija.
    """
    return {
        "name": NOMBRE_TEMA,
        "dataColors": list(COLORES_TEMA),
        "background": "#FFFFFF",
        "foreground": "#1A2B3C",
        "tableAccent": COLORES_TEMA[0],
    }


def partes(layout: dict | None) -> dict[str, bytes]:
    """El layout clásico como el árbol de archivos `Report/definition/`.

    Devuelve `{ruta_en_el_zip: bytes}`. Todo en UTF-8 —no UTF-16 como las
    partes viejas del contenedor— que es como los escribe Desktop.
    """
    layout = layout or {}
    secciones = layout.get("sections") or []

    def dump(obj) -> bytes:
        return json.dumps(obj, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")

    # `report.json` con EXACTAMENTE las claves que escribe Desktop para
    # este tablero: ni una más. Acá llegó a tener siete —`filterConfig`,
    # `objects` y `slowDataSourceSettings` de más— copiadas de un archivo
    # de otro cliente y otra versión de Desktop. Mezclar campos de dos
    # versiones de esquema produce una combinación que no corresponde a
    # ninguna, y el reporte no carga.
    recursos: list[dict] = [{
        "name": "SharedResources", "type": "SharedResources",
        "items": [{"name": NOMBRE_TEMA,
                   "path": f"BaseThemes/{NOMBRE_TEMA}.json",
                   "type": "BaseTheme"}]}]
    imagenes = _imagenes_declaradas(layout)
    if imagenes:
        recursos.append({"name": "RegisteredResources",
                         "type": "RegisteredResources", "items": imagenes})

    salida: dict[str, bytes] = {
        # El archivo del tema que `report.json` declara. Sin esto queda un
        # puntero colgado y la plantilla no abre — ver `NOMBRE_TEMA`.
        f"Report/StaticResources/SharedResources/BaseThemes/"
        f"{NOMBRE_TEMA}.json": dump(tema_base()),
        "Report/definition/version.json": dump({
            "$schema": ESQUEMAS["version"], "version": VERSION_PBIR}),
        "Report/definition/report.json": dump({
            "$schema": ESQUEMAS["report"],
            "themeCollection": {"baseTheme": {
                "name": NOMBRE_TEMA,
                "reportVersionAtImport": VERSIONES_AL_IMPORTAR,
                "type": "SharedResources"}},
            "resourcePackages": recursos,
            "settings": {"defaultDrillFilterOtherVisuals": True,
                         "allowChangeFilterTypes": True,
                         "useEnhancedTooltips": False},
        }),
    }

    usados: set[str] = set()
    # Los nombres de visual se desduplican contra TODO el reporte, no
    # contra la página. En el layout clásico un botón de navegación puede
    # repetir su nombre en cada página —van aislados dentro de su
    # sección—, pero en PBIR el `name` identifica al visual en el reporte
    # entero y ningún archivo real repite uno. Reiniciar este conjunto en
    # cada página dejaba 10 identificadores duplicados entre 85 visuales.
    vistos: set[str] = set()
    orden: list[str] = []
    for i, sec in enumerate(secciones):
        nombre = _nombre_carpeta(sec.get("name") or sec.get("displayName"),
                                 usados, i)
        orden.append(nombre)
        pagina = {
            "$schema": ESQUEMAS["page"],
            "name": nombre,
            "displayName": sec.get("displayName") or nombre,
            "displayOption": _DISPLAY.get(sec.get("displayOption", 1),
                                          "FitToPage"),
            "height": sec.get("height", 720),
            "width": sec.get("width", 1280),
        }
        # El formato de la página (fondo, lienzo) viaja en el `config` de
        # la sección clásica y en PBIR va como `objects`. Sin
        # `filterConfig`: Desktop no lo escribe en la página.
        objetos = _objetos_de(sec.get("config"))
        if objetos:
            pagina["objects"] = objetos
        salida[f"Report/definition/pages/{nombre}/page.json"] = dump(pagina)

        for j, vc in enumerate(sec.get("visualContainers") or []):
            try:
                cfg = json.loads(vc.get("config") or "{}")
            except (ValueError, TypeError):
                cfg = {}
            vid = _nombre_carpeta(cfg.get("name") or f"visual{j}", vistos, j)
            salida[f"Report/definition/pages/{nombre}/visuals/{vid}"
                   "/visual.json"] = dump(visual_pbir(vc, vid))

    salida["Report/definition/pages/pages.json"] = dump({
        "$schema": ESQUEMAS["pages"],
        "pageOrder": orden,
        "activePageName": orden[0] if orden else "",
    })
    return salida
