# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · El gate de salida: auditar el archivo YA ESCRITO.

Todo lo demás en este programa mira el modelo *en memoria*. Este módulo
abre el archivo que se acaba de escribir —el mismo byte que se le manda al
cliente— y lo audita ítem por ítem, como lo haría alguien que lo recibe sin
saber nada de cómo se generó.

**Por qué existe.** Dos veces seguidas se entregó un `.pbit` «verificado»
que en Power BI Desktop no servía: una vez abría sin ninguna tabla, otra
Desktop lo rechazaba como archivo dañado. Las dos veces la verificación
había sido circular — se exportaba y se volvía a leer con el lector de
este mismo programa, que entiende cosas que Desktop no mira. Un
round-trip contra uno mismo no verifica nada.

La regla acá es la contraria: **cada ítem se comprueba contra un criterio
externo** —lo que un `.pbit` real declara, lo que el motor de Power Query
necesita para correr, lo que el usuario va a ver si algo falta— y devuelve
`OK`, `AVISO` o `FALTA` con la evidencia concreta. Nada se da por hecho
porque «lo escribimos nosotros».

Lo que este módulo NO puede hacer, y hay que decirlo: abrir Power BI
Desktop. Corre en Linux. Verifica todo lo verificable sin Desktop, que es
mucho más de lo que se estaba verificando, y para lo que no se puede
comprobar desde acá lo dice en vez de dar por bueno.
"""
from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from pathlib import Path

from .analizador import _parece_periodo, es_medida_de_texto
from .catalogo import Catalogo, validar_referencias
from .i18n import IDIOMA_DEFECTO, t as traducir

OK, AVISO, FALTA = "ok", "aviso", "falta"

# Las partes que un .pbit tiene que llevar sí o sí. Sin cualquiera de
# ellas Power BI rechaza el archivo o abre sin modelo. Medido sobre
# archivos reales exportados por Desktop, no sobre lo que escribimos.
_PARTES_MINIMAS = ("Version", "[Content_Types].xml", "DataModelSchema")

# Funciones M que salen a buscar algo afuera del archivo.
_M_EXTERNO = ("File.Contents", "Excel.Workbook", "Csv.Document",
              "Sql.Database", "Web.Contents", "Folder.Files", "Odbc.",
              "SharePoint.", "OData.Feed")

# Cualquier literal de ruta absoluta dentro del M.
_RE_RUTA = re.compile(r'"((?:[A-Za-z]:[\\/]|\\\\|/)[^"]{2,})"')

# Las columnas que `dataset.m_embebido` declara: van justo después del
# `Compression.Deflate ) ),` en la llave de `Table.FromRows`.
_RE_COLS_EMBEBIDAS = re.compile(r"Compression\.Deflate \) \),\s*\{([^}]*)\}",
                                re.S)


def _item(clave: str, estado: str, idioma: str, **datos) -> dict:
    return {"clave": clave, "estado": estado,
            "titulo": traducir(f"vf_{clave}", idioma),
            "detalle": traducir(f"vf_{clave}_{estado}", idioma).format(**datos)}


def _texto_m(expresion) -> str:
    if isinstance(expresion, list):
        return "\n".join(str(x) for x in expresion)
    return str(expresion or "")


# ==========================================================================
# Cómo se conecta cada tabla a sus datos
# ==========================================================================
def conexion_de(expresion) -> str:
    """`embebida` · `parametro` · `ruta` · `base` · `calculada` · `ninguna`.

    Es la pregunta que decide si el archivo sirve solo o necesita algo más
    en la máquina que lo abre.
    """
    m = _texto_m(expresion)
    if not m.strip():
        return "ninguna"
    if "Binary.Decompress" in m and "Table.FromRows" in m:
        return "embebida"
    if "Sql.Database" in m or "Odbc." in m:
        return "base"
    if not any(f in m for f in _M_EXTERNO):
        return "calculada"
    # Lee de un archivo: ¿por parámetro o por ruta escrita a mano? Si el
    # argumento no arranca con un literal de texto, lo está armando con
    # algo —un parámetro— y entonces el archivo es reapuntable al abrirlo.
    for fn in ("File.Contents", "Folder.Files"):
        i = m.find(fn)
        if i < 0:
            continue
        arg = m[i + len(fn):i + len(fn) + 200]
        if not arg.lstrip().startswith('("'):
            return "parametro"
    return "ruta"


def rutas_de(modelo: dict) -> list[str]:
    """Las rutas absolutas escritas a mano dentro del Power Query.

    Se busca SOLO en el argumento de las funciones que salen a leer algo
    afuera. Barrer la consulta entera parecía más simple y era falso: en
    una tabla con los datos empotrados, el base64 se parte en trozos de
    500 caracteres y cualquiera que arranque con `/` es, para una regex de
    rutas, una ruta absoluta impecable. El gate reportaba dos «rutas» en
    un archivo que no lee nada de afuera.
    """
    salida = []
    for t in modelo.get("model", {}).get("tables", []):
        for p in t.get("partitions", []):
            texto = _texto_m(p.get("source", {}).get("expression"))
            for fn in _M_EXTERNO:
                desde = 0
                while (i := texto.find(fn, desde)) >= 0:
                    desde = i + len(fn)
                    salida += _RE_RUTA.findall(texto[desde:desde + 400])
    return sorted(set(salida))


def _layout_de(z: zipfile.ZipFile, nombres: set[str]) -> dict | None:
    """El tablero, venga en `Report/Layout` (clásico) o en PBIR."""
    if "Report/Layout" in nombres:
        try:
            return json.loads(z.read("Report/Layout").decode(
                "utf-16-le").lstrip("﻿"))
        except Exception:                             # noqa: BLE001
            return None
    from .modelo import _leer_pbir
    try:
        return _leer_pbir(z)
    except Exception:                                 # noqa: BLE001
        return None


# ==========================================================================
# El gate
# ==========================================================================
def verificar(ruta: str | Path, idioma: str = IDIOMA_DEFECTO) -> dict:
    """Audita lo escrito y devuelve el veredicto ítem por ítem.

    Acepta un `.pbit` y también una carpeta PBIP (o su archivo `.pbip`):
    el contenedor cambia, el modelo y el tablero que hay que auditar son
    los mismos, así que las dos formas terminan en la misma auditoría.

    `{"items": [...], "faltan": n, "avisos": n, "listo": bool}`. `listo`
    es `True` solo si NINGÚN ítem quedó en `FALTA` — un aviso no bloquea,
    una falta sí.
    """
    ruta = Path(ruta)
    items: list[dict] = []

    if not ruta.exists():
        items.append(_item("archivo", FALTA, idioma, ruta=ruta.name))
        return _resumen(items)

    if ruta.is_dir() or ruta.suffix.lower() == ".pbip":
        return _verificar_pbip(ruta, items, idioma)

    items.append(_item("archivo", OK, idioma,
                       ruta=ruta.name, kb=max(1, ruta.stat().st_size // 1024)))

    # ---- 1 · El contenedor ----
    try:
        z = zipfile.ZipFile(ruta)
        nombres = set(z.namelist())
    except zipfile.BadZipFile as exc:
        items.append(_item("zip", FALTA, idioma, motivo=str(exc)[:120]))
        return _resumen(items)

    faltantes = [p for p in _PARTES_MINIMAS if p not in nombres]
    items.append(_item("contenedor", FALTA if faltantes else OK, idioma,
                       partes=", ".join(faltantes) or "—", n=len(nombres)))
    if "DataModelSchema" not in nombres:
        return _resumen(items)

    # El [Content_Types].xml tiene que declarar EXACTAMENTE lo que hay:
    # declarar una parte que no está —o escribir una sin declararla— es de
    # las cosas que hacen que Desktop rechace el archivo como dañado.
    declaradas = set(re.findall(r'PartName="/([^"]+)"',
                                z.read("[Content_Types].xml").decode(
                                    "utf-8-sig", "replace")))
    # Solo las partes que van con `<Override>`: las de carpetas internas
    # (recursos, páginas PBIR) se declaran por extensión con `<Default>`.
    escritas = {n for n in nombres
                if "/" not in n or n.startswith("Report/L")}
    sin_declarar = sorted(escritas - declaradas - {"[Content_Types].xml"})
    declaradas_de_mas = sorted(declaradas - nombres)
    items.append(_item(
        "content_types",
        FALTA if (sin_declarar or declaradas_de_mas) else OK, idioma,
        sobran=", ".join(declaradas_de_mas) or "—",
        faltan=", ".join(sin_declarar) or "—"))

    # La versión del contenedor y el formato del reporte son un PAR: la
    # 1.28 va con `Report/Layout` y la 1.32 con `Report/definition/`.
    # Cruzarlos hace que Desktop rechace el archivo como «creado con una
    # versión no reconocida». Es el bug que este ítem existe para no
    # repetir: se subió la versión a 1.32 dejando el layout clásico.
    from .modelo import VERSION_POR_FORMATO
    crudo_version = z.read("Version") if "Version" in nombres else b""
    try:
        version_c = crudo_version.decode("utf-16-le").lstrip("﻿").strip()
    except Exception:                                 # noqa: BLE001
        version_c = ""

    # La codificación de `Version` es parte del formato, no un detalle: un
    # .pbit real lleva UTF-16LE **sin BOM**, y Desktop lee esos dos bytes
    # como parte del número. El ítem de arriba hacía `lstrip("﻿")`
    # antes de comparar, así que un archivo con BOM lo aprobaba: el gate
    # se estaba tapando los ojos con la mano que usaba para mirar.
    problemas_cod = []
    if crudo_version[:2] == b"\xff\xfe":
        problemas_cod.append(traducir("vf_cod_bom", idioma).format(
            parte="Version"))
    elif crudo_version[1:2] != b"\x00":
        problemas_cod.append(traducir("vf_cod_utf16", idioma).format(
            parte="Version"))
    if z.read("DataModelSchema")[1:2] != b"\x00":
        problemas_cod.append(traducir("vf_cod_utf16", idioma).format(
            parte="DataModelSchema"))
    items.append(_item("codificacion", FALTA if problemas_cod else OK, idioma,
                       n=len(problemas_cod),
                       lista=" · ".join(problemas_cod) or "—"))

    formato = ("pbir" if any(n.startswith("Report/definition/")
                             for n in nombres)
               else "layout" if "Report/Layout" in nombres else "")
    if formato:
        esperada = VERSION_POR_FORMATO[formato]
        items.append(_item(
            "version_formato", OK if version_c == esperada else FALTA,
            idioma, version=version_c or "—", formato=formato,
            esperada=esperada))

    # ---- 2 · El modelo ----
    try:
        esquema = json.loads(
            z.read("DataModelSchema").decode("utf-16-le").lstrip("﻿"))
    except Exception as exc:                          # noqa: BLE001
        items.append(_item("esquema", FALTA, idioma, motivo=str(exc)[:120]))
        return _resumen(items)

    # Ningún visual puede repetir su identificador en el reporte. En el
    # layout clásico un botón de navegación repite su `name` en cada
    # página sin consecuencias —van aislados dentro de su sección—, pero
    # en PBIR ese `name` identifica al visual en el reporte ENTERO. Diez
    # duplicados entre 85 visuales fue lo que hizo que Desktop rechazara
    # el archivo, y las carpetas no chocaban, así que nada lo delataba.
    vistos: dict[str, int] = {}
    for n in sorted(nombres):
        if not n.endswith("visual.json"):
            continue
        try:
            ident = json.loads(z.read(n).decode("utf-8-sig")).get("name")
        except Exception:                             # noqa: BLE001
            continue
        if ident:
            vistos[ident] = vistos.get(ident, 0) + 1
    repetidos = sorted(k for k, c in vistos.items() if c > 1)
    if vistos:
        items.append(_item(
            "identificadores", FALTA if repetidos else OK, idioma,
            n=len(repetidos), total=len(vistos),
            lista=" · ".join(repetidos[:5]) or "—"))

    indice = _paginas_pbir(z, nombres, idioma)
    if indice is not None:
        items.append(indice)

    visuales = _visuales_pbir(z, nombres, esquema, idioma)
    if visuales is not None:
        items.append(visuales)

    layout = _layout_de(z, nombres)

    # Todo recurso que el layout DECLARA tiene que estar dentro del
    # paquete. Se declaraba un tema base que nunca se escribía: una
    # referencia colgada a una parte inexistente, que es de las cosas que
    # hacen que Desktop rechace el archivo. Declarado y presente, o
    # ninguna de las dos.
    plantilla = ruta.suffix.lower() == ".pbit"
    colgados = [p for p in _declarados_en(z, nombres, layout, plantilla)
                if f"Report/StaticResources/{p}" not in nombres]
    if layout is not None:
        items.append(_item("recursos", FALTA if colgados else OK, idioma,
                           n=len(colgados),
                           lista=" · ".join(colgados[:5]) or "—"))

    return _auditar(esquema, layout, items, idioma)


# El paquete del tema base. El layout clásico lo numera (2) y el PBIR lo
# nombra.
_TEMAS = {2, "SharedResources"}


def _declarados_en(z: zipfile.ZipFile, nombres: set[str],
                   layout: dict | None, plantilla: bool) -> list[str]:
    """Lo que el reporte declara, leído del contenedor y no del layout.

    En PBIR los recursos se declaran en `report.json`, y el traductor a
    layout clásico —que existe para que las reglas no se enteren del
    formato— no los arrastra: sólo páginas y visuales. Con lo cual este
    control miraba un `resourcePackages` siempre vacío y aprobaba el
    archivo con el puntero colgado adentro. Se lee de donde está.
    """
    reporte = "Report/definition/report.json"
    if reporte in nombres:
        try:
            rep = json.loads(z.read(reporte).decode("utf-8-sig"))
        except Exception:                             # noqa: BLE001
            return []
        return _recursos_declarados(rep, plantilla)
    return _recursos_declarados(layout, plantilla)


def _recursos_declarados(layout: dict | None,
                         plantilla: bool = True) -> list[str]:
    """Las rutas que el layout promete Y tiene que llevar adentro.

    La excepción depende del CONTENEDOR, y confundirlos costó dos vueltas:

    · En un `.pbix`, `SharedResources` puede faltar. Desktop abre ese
      archivo con la instalación que lo escribió y el tema base sale de
      ahí. Reclamarlo era un falso positivo caro: acusaba a un archivo
      sano y escondía la falta de verdad entre el ruido.
    · En un `.pbit`, NO puede faltar. Una plantilla viaja a otra máquina y
      tiene que ser autosuficiente; los dos `.pbit` reales medidos traen
      su `BaseThemes/*.json` adentro. Dejar pasar el puntero colgado es lo
      que producía «este archivo está dañado o se ha creado con una
      versión no reconocida de Power BI Desktop».
    """
    salida = []
    for envoltorio in (layout or {}).get("resourcePackages") or []:
        paquete = envoltorio.get("resourcePackage", envoltorio)
        es_tema = (paquete.get("type") in _TEMAS
                   or paquete.get("name") in _TEMAS)
        if es_tema and not plantilla:
            continue
        carpeta = paquete.get("name", "")
        for item in paquete.get("items") or []:
            ruta = item.get("path")
            if ruta:
                salida.append(f"{carpeta}/{ruta}")
    return salida


def _verificar_pbip(ruta: Path, items: list[dict], idioma: str) -> dict:
    """Lo mismo, para un proyecto PBIP: carpeta en vez de zip.

    No hay `[Content_Types].xml` que validar —un PBIP no es un paquete
    OPC, es una carpeta— así que ese ítem no aplica y no se inventa. El
    resto del gate es idéntico: el modelo es el mismo TMSL.
    """
    carpeta = ruta.parent if ruta.is_file() else ruta
    bim = next(iter(sorted(carpeta.glob("*.SemanticModel/model.bim"))), None)
    peso = sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file())
    items.append(_item("archivo", OK, idioma,
                       ruta=carpeta.name, kb=max(1, peso // 1024)))
    if bim is None:
        items.append(_item("contenedor", FALTA, idioma,
                           partes="<nombre>.SemanticModel/model.bim", n=0))
        return _resumen(items)
    partes = [f for f in carpeta.rglob("*") if f.is_file()]
    items.append(_item("contenedor_pbip", OK, idioma,
                       bim=bim.parent.name, n=len(partes)))

    try:
        esquema = json.loads(bim.read_text(encoding="utf-8"))
    except Exception as exc:                          # noqa: BLE001
        items.append(_item("esquema", FALTA, idioma, motivo=str(exc)[:120]))
        return _resumen(items)

    layout = None
    reporte_json = next(iter(sorted(carpeta.glob("*.Report/report.json"))),
                        None)
    if reporte_json is not None:
        try:
            layout = json.loads(reporte_json.read_text(encoding="utf-8"))
        except Exception:                             # noqa: BLE001
            layout = None
    return _auditar(esquema, layout, items, idioma)


def _auditar(esquema: dict, layout: dict | None, items: list[dict],
             idioma: str) -> dict:
    """El corazón del gate: todo lo que se audita sobre el modelo escrito.

    Recibe el TMSL ya leído del contenedor que sea. De acá para abajo da
    igual si vino de un `.pbit` o de un PBIP — lo que Power BI necesita
    para abrir el modelo y refrescarlo es lo mismo en los dos casos.
    """
    mm = esquema.get("model", {})
    tablas = [t for t in mm.get("tables", [])
              if not t.get("name", "").startswith(("LocalDateTable_",
                                                   "DateTableTemplate_"))]
    items.append(_item("modelo", FALTA if not tablas else OK, idioma,
                       tablas=len(tablas),
                       relaciones=len(mm.get("relationships", []))))
    if not tablas:
        return _resumen(items)

    # La combinación exacta que Desktop exige para leer las particiones `m`.
    # Sin `powerBI_V3` busca el Power Query en un `DataMashup` binario y
    # descarta el modelo entero; con el flag pero con un nivel de
    # compatibilidad viejo, rechaza el archivo como dañado.
    from .modelo import COMPATIBILIDAD_V3
    version = mm.get("defaultPowerBIDataSourceVersion")
    nivel = esquema.get("compatibilityLevel", 0)
    coherente = version == "powerBI_V3" and nivel >= COMPATIBILIDAD_V3
    items.append(_item("compatibilidad", OK if coherente else FALTA, idioma,
                       version=version or "—", nivel=nivel,
                       minimo=COMPATIBILIDAD_V3))

    # El rastro de cómo se armó el modelo, para el que lo reciba. No es
    # obligatorio —un .pbit sin él abre igual— así que nunca reprueba: se
    # informa. Un tablero que sale sin ficha de gobierno no está roto,
    # está incompleto, y son dos cosas distintas.
    from .gobernanza import leer as leer_traspaso
    traspaso = leer_traspaso(esquema)
    items.append(_item(
        "traspaso", OK if traspaso else AVISO, idioma,
        tablas=len(traspaso.get("tablas", [])) if traspaso else 0,
        medidas=len(traspaso.get("medidas", [])) if traspaso else 0))

    # Una tabla sin partición no tiene de dónde sacar filas: Desktop
    # levanta el modelo con esa tabla en error. Sin columnas es lo mismo.
    # El ítem de conexión recorría `partitions` y una lista vacía no
    # aportaba nada a ningún tipo, así que la tabla rota no aparecía por
    # ningún lado y el archivo salía aprobado.
    huecas = [t.get("name", "?") for t in tablas
              if not t.get("partitions") or not t.get("columns")]
    items.append(_item("particiones", FALTA if huecas else OK, idioma,
                       n=len(huecas), tablas=len(tablas),
                       lista=" · ".join(huecas[:5]) or "—"))

    # ---- 3 · La conexión a los datos ----
    por_tipo: dict[str, list[str]] = {}
    for t in tablas:
        for p in t.get("partitions", []):
            tipo = conexion_de(p.get("source", {}).get("expression"))
            por_tipo.setdefault(tipo, []).append(t.get("name", "?"))
    embebidas = por_tipo.get("embebida", [])
    afuera = (por_tipo.get("ruta", []) + por_tipo.get("base", [])
              + por_tipo.get("parametro", []))
    sin_nada = por_tipo.get("ninguna", [])

    items.append(_item(
        "conexion", FALTA if sin_nada else OK, idioma,
        sin_origen=", ".join(sin_nada) or "—",
        detalle=" · ".join(f"{k}: {len(v)}" for k, v in sorted(
            por_tipo.items())) or "—"))

    # ¿Abre solo, o necesita algo que esté en la máquina que lo abre?
    if not sin_nada:
        items.append(_item(
            "autonomo", OK if not afuera else AVISO, idioma,
            embebidas=len(embebidas), afuera=len(afuera),
            lista=" · ".join(sorted(set(afuera))[:5]) or "—"))

    # Rutas absolutas: andan en la máquina donde se generaron y en ningún
    # otro lado. No es un error —es lo normal cuando el origen es un
    # archivo— pero el que recibe el .pbit tiene que saberlo.
    rutas = rutas_de(esquema)
    if rutas:
        items.append(_item(
            "rutas", AVISO, idioma, n=len(rutas),
            lista=" · ".join(rutas[:4]),
            faltan=sum(1 for r in rutas if not Path(r).exists())))

    # ---- 4 · Lo declarado contra lo que la consulta produce ----
    # Una columna declarada en el modelo que la consulta no devuelve deja
    # la tabla en error al refrescar, con el archivo abriendo igual.
    desajustes = []
    for t in tablas:
        calculadas = {c["name"] for c in t.get("columns", [])
                      if c.get("type") in ("calculated",
                                           "calculatedTableColumn")}
        for p in t.get("partitions", []):
            texto = _texto_m(p.get("source", {}).get("expression"))
            if "Table.FromRows" not in texto:
                continue
            base = _RE_COLS_EMBEBIDAS.search(texto)
            produce = set(re.findall(r'"((?:[^"]|"")*)"', base.group(1))
                          if base else [])
            produce |= set(re.findall(
                r'Table\.AddColumn\s*\([^,]+,\s*"([^"]+)"', texto))
            for c in (col["name"] for col in t.get("columns", [])):
                if c not in produce and c not in calculadas:
                    desajustes.append(f'{t["name"]}[{c}]')
    items.append(_item("columnas", FALTA if desajustes else OK, idioma,
                       n=len(desajustes),
                       lista=" · ".join(desajustes[:5]) or "—"))

    # La sintaxis del Power Query. Se validaba el DAX y no el M, así que
    # una consulta a la que le faltaba una coma entre dos pasos pasó todos
    # los controles y llegó a Desktop, que la frenó con «Se esperaba el
    # token ','». El DAX no es el único lenguaje que viaja en el archivo.
    rotas_m = []
    for t in tablas:
        for p in t.get("partitions", []):
            for err in sintaxis_m(_texto_m(p.get("source", {})
                                           .get("expression"))):
                rotas_m.append(f'{t["name"]}: {err}')
    items.append(_item("powerquery", FALTA if rotas_m else OK, idioma,
                       n=len(rotas_m), consultas=len(tablas),
                       lista=" · ".join(rotas_m[:3]) or "—"))

    # ---- 5 · El DAX ----
    cat = Catalogo.desde_modelo(esquema)
    rotas = [m["nombre"] for m in cat.medidas()
             if validar_referencias(m.get("expresion", ""), cat, idioma)]
    items.append(_item("dax", FALTA if rotas else OK, idioma,
                       medidas=len(cat.medidas()), rotas=len(rotas),
                       lista=" · ".join(rotas[:5]) or "—"))
    if cat.medidas():
        # Una medida que devuelve TEXTO —la lectura de una página, por
        # ejemplo— no tiene formato numérico que ponerle: reclamárselo era
        # un aviso que no se podía atender.
        sin_formato = [m["nombre"] for m in cat.medidas()
                       if not (m.get("formato") or "").strip()
                       and not es_medida_de_texto(m.get("expresion", ""), cat)]
        items.append(_item("formatos", AVISO if sin_formato else OK, idioma,
                           n=len(sin_formato),
                           lista=" · ".join(sin_formato[:5]) or "—"))

    # Lo declarado contra lo que los datos empotrados son de verdad. Una
    # columna declarada numérica con un texto adentro no rompe el archivo
    # al abrir: rompe al refrescar, con la tabla en error y el resto del
    # modelo aparentemente sano.
    items.append(_tipos_de_datos(tablas, idioma))
    # Los nombres con los que el modelo se referencia a sí mismo: dos
    # columnas iguales en una tabla, una medida repetida, un orden que
    # apunta a una columna que no está. Desktop rechaza las tres, y
    # ninguna la ve el DAX —las expresiones pueden estar perfectas.
    items.append(_nombres(tablas, idioma))

    # ---- 6 · El modelado ----
    visibles = [t for t in cat.tablas if not t["interna"]]
    if len(visibles) > 1:
        items.append(_item(
            "relaciones", FALTA if not cat.relaciones else OK, idioma,
            n=len(cat.relaciones), tablas=len(visibles)))
    if mm.get("relationships"):
        items.append(_integridad(mm, idioma))
    if any(c["tipo"] == "dateTime" for _t, c in cat.columnas()):
        cal = cat.tabla_fechas()
        items.append(_item("calendario", OK if cal else AVISO, idioma,
                           tabla=cal["nombre"] if cal else "—"))
        if cal:
            # Marcada como tabla de fechas y con su clave: sin eso, la
            # inteligencia de tiempo de Power BI no la reconoce y TOTALYTD
            # o SAMEPERIODLASTYEAR devuelven en blanco.
            cruda = next((t for t in tablas
                          if t.get("name") == cal["nombre"]), {})
            marcada = cruda.get("dataCategory") == "Time"
            clave = any(c.get("isKey") and c.get("dataType") == "dateTime"
                        for c in cruda.get("columns", []))
            # Las etiquetas de texto se ordenan alfabéticamente salvo que
            # tengan `sortByColumn`: «abril» antes que «enero».
            sin_orden = [c["name"] for c in cruda.get("columns", [])
                         if c.get("dataType") == "string"
                         and not c.get("sortByColumn")
                         and _parece_periodo(c["name"])]
            items.append(_item(
                "tiempo", OK if (marcada and clave and not sin_orden)
                else AVISO, idioma,
                marcada=_si_no(marcada, idioma),
                # `llave`, no `clave`: `_item` ya usa ese nombre para el
                # identificador del ítem y chocaban.
                llave=_si_no(clave, idioma),
                lista=" · ".join(sin_orden[:4]) or "—"))

    # ---- 7 · El tablero ----
    secciones = (layout or {}).get("sections", [])
    visuales = sum(len(s.get("visualContainers", [])) for s in secciones)
    items.append(_item(
        "tablero", AVISO if not visuales else OK, idioma,
        paginas=len(secciones), visuales=visuales))

    # Los campos que los visuales piden tienen que existir en el modelo:
    # si no, el visual abre con el cartelito de error y el usuario ve un
    # tablero roto sin saber por qué.
    if visuales:
        usados = Catalogo.desde_layout(layout)
        faltan_campos = [m["nombre"] for t in usados.tablas
                         for m in t["medidas"] if not cat.medida(m["nombre"])]
        faltan_campos += [f'{t["nombre"]}[{c["nombre"]}]'
                          for t in usados.tablas if cat.tabla(t["nombre"])
                          for c in t["columnas"]
                          if not cat.existe_columna(t["nombre"], c["nombre"])]
        items.append(_item(
            "campos", FALTA if faltan_campos else OK, idioma,
            n=len(faltan_campos), lista=" · ".join(faltan_campos[:5]) or "—"))
        # Los filtros no viajan en la consulta del visual: viven aparte,
        # en `filterConfig`. `desde_layout` no los mira, así que un filtro
        # apuntado a una columna que ya no existe pasaba el gate entero y
        # el usuario se lo encontraba al abrir — con el agravante de que
        # un filtro roto no se ve: el visual dibuja, con otros números.
        items.append(_filtros(cat, layout, idioma))
        items.append(_ejes(cat, layout, idioma))
        items.append(_constantes(cat, layout, idioma))

    return _resumen(items)


def _filas_de(tabla: dict):
    """Las filas empotradas de una tabla, o `None` si no lleva datos."""
    from .dataset import filas_embebidas
    return filas_embebidas(tabla)


_NUMERICOS = ("int64", "double", "decimal")
_RE_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]|$)")


def _convertible(valor, tipo: str) -> bool:
    """¿Power Query va a poder tipar este valor a lo que el modelo dice?

    Los datos empotrados viajan como TEXTO —así los escribe
    `Table.FromRows`— y el paso `TransformColumnTypes` los convierte al
    abrir. Un valor que no convierte no da un error visible en el acto:
    deja la celda en error y la tabla entera marcada, con el resto del
    modelo aparentando estar bien.
    """
    if valor in (None, ""):
        return True                        # nulo: Power Query lo acepta
    texto = str(valor)
    if tipo in _NUMERICOS:
        try:
            float(texto)
        except ValueError:
            return False
        return True
    if tipo == "dateTime":
        return bool(_RE_FECHA_ISO.match(texto))
    if tipo == "boolean":
        return texto.lower() in ("true", "false", "1", "0")
    return True


def _tipos_de_datos(tablas: list[dict], idioma: str) -> dict:
    """Cada valor empotrado contra el tipo que el modelo le declara."""
    malos, revisadas = [], 0
    for t in tablas:
        datos = _filas_de(t)
        if not datos:
            continue
        revisadas += 1
        cols, filas = datos
        tipos = {c.get("name"): c.get("dataType") for c in t.get("columns", [])}
        for i, nombre in enumerate(cols):
            tipo = tipos.get(nombre)
            if not tipo or tipo == "string":
                continue
            malo = next((f[i] for f in filas
                         if i < len(f) and not _convertible(f[i], tipo)), None)
            if malo is not None:
                malos.append(f'{t.get("name")}[{nombre}] ({tipo}): {malo!r}')
    return _item("tipos", FALTA if malos else OK, idioma,
                 n=len(malos), tablas=revisadas,
                 lista=" · ".join(malos[:4]) or "—")


def _nombres(tablas: list[dict], idioma: str) -> dict:
    """Cómo el modelo se nombra a sí mismo: sin repetidos y sin colgados."""
    problemas: list[str] = []
    medidas: Counter = Counter()
    for t in tablas:
        nombre_t = t.get("name", "?")
        columnas = [c.get("name") for c in t.get("columns", [])]
        for repetida in sorted({c for c in columnas
                                if columnas.count(c) > 1}):
            problemas.append(traducir("vf_nom_col_repetida", idioma).format(
                tabla=nombre_t, columna=repetida))
        medidas.update(m.get("name") for m in t.get("measures", []))
        for c in t.get("columns", []):
            orden = c.get("sortByColumn")
            if orden and orden not in columnas:
                problemas.append(traducir("vf_nom_orden", idioma).format(
                    tabla=nombre_t, columna=c.get("name"), orden=orden))
        for h in t.get("hierarchies", []):
            for nivel in h.get("levels", []):
                if nivel.get("column") not in columnas:
                    problemas.append(traducir(
                        "vf_nom_jerarquia", idioma).format(
                            tabla=nombre_t, jerarquia=h.get("name"),
                            columna=nivel.get("column")))
    for nombre, veces in sorted(medidas.items()):
        if veces > 1 and nombre:
            problemas.append(traducir("vf_nom_medida", idioma).format(
                medida=nombre, n=veces))
    return _item("nombres", FALTA if problemas else OK, idioma,
                 n=len(problemas), tablas=len(tablas),
                 medidas=sum(medidas.values()),
                 lista=" · ".join(problemas[:3]) or "—")


def _integridad(mm: dict, idioma: str) -> dict:
    """Las relaciones, contra lo que Power BI exige para poder crearlas.

    El gate contaba las relaciones y las daba por buenas. Contarlas no
    dice nada: una relación cuyo lado uno tiene un valor repetido hace
    que el modelo NO cargue —«la columna contiene valores duplicados»— y
    el archivo abre con el modelo vacío. Se revisa lo que Desktop revisa:
    que los dos extremos existan, que sean del mismo tipo, que el lado
    uno sea único y sin blancos, que no haya dos activas entre las mismas
    tablas, y que el filtro no pueda dar la vuelta en círculo.
    """
    todas = {t.get("name"): t for t in mm.get("tables", [])}
    problemas: list[str] = []
    activas: dict[tuple, list[str]] = {}
    # Grafo de PROPAGACIÓN, no de tablas: el filtro corre del lado uno al
    # lado muchos. Por eso dos hechos que comparten dos dimensiones
    # cierran un círculo de tablas y son un modelo legal — el filtro no
    # puede volver por el hecho. Mirar el grafo sin dirección acusaría a
    # cualquier modelo multi-hecho, que es la mitad de los que existen.
    aristas: list[tuple[str, str, str]] = []
    for numero, r in enumerate(mm.get("relationships", [])):
        ft, fc = r.get("fromTable"), r.get("fromColumn")
        tt, tc = r.get("toTable"), r.get("toColumn")
        etq = f"{ft}[{fc}] → {tt}[{tc}]"
        cols_f = {c.get("name"): c for c in
                  todas.get(ft, {}).get("columns", [])}
        cols_t = {c.get("name"): c for c in
                  todas.get(tt, {}).get("columns", [])}
        if ft not in todas or fc not in cols_f:
            problemas.append(traducir("vf_rel_extremo", idioma).format(
                rel=etq, lado=f"{ft}[{fc}]"))
            continue
        if tt not in todas or tc not in cols_t:
            problemas.append(traducir("vf_rel_extremo", idioma).format(
                rel=etq, lado=f"{tt}[{tc}]"))
            continue
        t1, t2 = cols_f[fc].get("dataType"), cols_t[tc].get("dataType")
        if t1 != t2 and not {t1, t2} <= set(_NUMERICOS):
            problemas.append(traducir("vf_rel_tipos", idioma).format(
                rel=etq, uno=t1 or "—", otro=t2 or "—"))
        datos = _filas_de(todas[tt])
        if datos and tc in datos[0]:
            i = datos[0].index(tc)
            valores = [f[i] for f in datos[1] if i < len(f)]
            vacios = sum(1 for v in valores if v in (None, ""))
            llenos = [v for v in valores if v not in (None, "")]
            repetido = next((v for v, n in Counter(llenos).items() if n > 1),
                            None)
            if repetido is not None:
                problemas.append(traducir("vf_rel_repetido", idioma).format(
                    rel=etq, valor=repetido))
            if vacios:
                problemas.append(traducir("vf_rel_vacio", idioma).format(
                    rel=etq, n=vacios))
        if r.get("isActive", True):
            par = tuple(sorted([ft, tt]))
            activas.setdefault(par, []).append(etq)
            ident = r.get("name") or f"rel{numero}"
            aristas.append((tt, ft, ident))
            if r.get("crossFilteringBehavior") == "bothDirections":
                aristas.append((ft, tt, ident))
    for par, lista in activas.items():
        if len(lista) > 1:
            problemas.append(traducir("vf_rel_dobles", idioma).format(
                a=par[0], b=par[1], n=len(lista)))
    ciclo = _ciclo(aristas)
    if ciclo:
        problemas.append(traducir("vf_rel_ciclo", idioma).format(
            camino=" → ".join(ciclo)))
    return _item("integridad", FALTA if problemas else OK, idioma,
                 n=len(problemas), total=len(mm.get("relationships", [])),
                 lista=" · ".join(problemas[:3]) or "—")


def _ciclo(aristas: list[tuple[str, str, str]]) -> list[str]:
    """El primer ciclo de propagación, o lista vacía.

    Cada arista es `(desde, hasta, relación)`. La relación importa: una
    sola relación con filtro cruzado en ambas direcciones deja ir y
    volver entre dos tablas, y eso NO es un ciclo —es una relación
    legal—. Un ciclo necesita dos relaciones distintas, así que la vuelta
    por la misma relación por la que se vino no cuenta.
    """
    salidas: dict[str, list[tuple[str, str]]] = {}
    for desde, hasta, rel in aristas:
        salidas.setdefault(desde, []).append((hasta, rel))
    camino: list[str] = []
    en_camino: set[str] = set()
    # Sin memoria de nodos ya explorados: si un nodo cierra ciclo o no
    # depende de POR QUÉ RELACIÓN se entró, y recordarlo daría por limpio
    # un camino que por otra relación sí da la vuelta. Un modelo tiene
    # decenas de relaciones, no millones; el presupuesto de pasos alcanza
    # de sobra y evita que un modelo raro cuelgue el gate.
    presupuesto = [200_000]

    def visitar(n: str, vino_por: str | None) -> list[str]:
        camino.append(n)
        en_camino.add(n)
        for destino, rel in sorted(salidas.get(n, ())):
            if rel == vino_por or presupuesto[0] <= 0:
                continue
            presupuesto[0] -= 1
            if destino in en_camino:
                return camino[camino.index(destino):] + [destino]
            hallado = visitar(destino, rel)
            if hallado:
                return hallado
        camino.pop()
        en_camino.discard(n)
        return []

    for raiz in sorted(salidas):
        hallado = visitar(raiz, None)
        if hallado:
            return hallado
    return []


def _campos_del_filtro(item) -> set[tuple[str, str, str]]:
    """Los campos de UN filtro, resolviendo los alias de su cláusula `From`.

    Adentro del filtro las columnas no se nombran por su tabla sino por
    un alias —`{"SourceRef": {"Source": "m"}}`— que la cláusula `From`
    del propio filtro traduce a la entidad real. Sin resolverlo, el campo
    queda sin tabla y acusar por eso sería acusar a un filtro sano: pasó
    exactamente eso con un filtro correcto de Corporación.
    """
    alias: dict[str, str] = {}

    def buscar_from(o):
        if isinstance(o, dict):
            for clave, valor in o.items():
                if clave == "From" and isinstance(valor, list):
                    for f in valor:
                        if isinstance(f, dict) and f.get("Name"):
                            if f.get("Entity"):
                                alias[f["Name"]] = f["Entity"]
                buscar_from(valor)
        elif isinstance(o, list):
            for valor in o:
                buscar_from(valor)

    def entidad(exp) -> str:
        if not isinstance(exp, dict):
            return ""
        ref = exp.get("SourceRef") or {}
        ent = ref.get("Entity") or alias.get(ref.get("Source") or "", "")
        if ent:
            return ent
        jer = exp.get("Hierarchy") or {}
        return entidad(jer.get("Expression") or {})

    campos: set[tuple[str, str, str]] = set()

    def hurgar(o):
        if isinstance(o, dict):
            for clave, valor in o.items():
                if (clave in ("Column", "Measure", "HierarchyLevel")
                        and isinstance(valor, dict)):
                    prop = valor.get("Property") or valor.get("Level")
                    ent = entidad(valor.get("Expression") or {})
                    if prop and ent:
                        campos.add((ent, prop, clave))
                hurgar(valor)
        elif isinstance(o, list):
            for valor in o:
                hurgar(valor)

    buscar_from(item)
    hurgar(item)
    return campos


def _filtros(cat: Catalogo, layout: dict, idioma: str) -> dict:
    """Cada campo que un filtro nombra tiene que existir en el modelo."""

    def _leer(crudo):
        if not crudo:
            return None
        if isinstance(crudo, str):
            try:
                return json.loads(crudo)
            except (ValueError, TypeError):
                return None
        return crudo

    rotos: list[str] = []
    total = 0
    for pag in layout.get("sections", []) or []:
        nombre_pag = pag.get("displayName", "?")
        fuentes = [pag.get("filters")]
        fuentes += [vc.get("filters")
                    for vc in pag.get("visualContainers", []) or []]
        for crudo in fuentes:
            datos = _leer(crudo)
            if not datos:
                continue
            lista = datos if isinstance(datos, list) else (
                datos.get("filters") or [])
            for uno in lista:
                total += 1
                for tabla, campo, clase in _campos_del_filtro(uno):
                    if not cat.tabla(tabla):
                        roto = f"{tabla}[{campo}]"
                    elif clase == "Measure":
                        roto = "" if cat.medida(campo) else f"[{campo}]"
                    elif clase == "HierarchyLevel":
                        # El nivel de una jerarquía puede llamarse distinto
                        # que la columna que lo alimenta: con la tabla
                        # existiendo, no hay evidencia de que esté roto.
                        roto = ""
                    else:
                        roto = ("" if cat.existe_columna(tabla, campo)
                                else f"{tabla}[{campo}]")
                    if not roto:
                        continue
                    etq = f"{nombre_pag} · {roto}"
                    if etq not in rotos:
                        rotos.append(etq)
    return _item("filtros", FALTA if rotos else OK, idioma,
                 n=len(rotos), total=total,
                 lista=" · ".join(rotos[:4]) or "—")


def _paginas_pbir(z: zipfile.ZipFile, nombres: set[str],
                  idioma: str) -> dict | None:
    """El índice de páginas contra las páginas que de verdad están.

    `pages.json` es el índice del reporte PBIR: si nombra una página que
    no está, Desktop rechaza el archivo; si una página está y el índice
    no la nombra, el usuario no la ve nunca —y el lector de este programa
    tampoco, así que el resto del gate ni se entera de que existe.
    """
    meta = "Report/definition/pages/pages.json"
    if meta not in nombres:
        return None
    try:
        datos = json.loads(z.read(meta).decode("utf-8-sig"))
    except Exception:                                 # noqa: BLE001
        return _item("paginas", FALTA, idioma, n=1, total=0,
                     lista=meta)
    carpetas = {n.split("/")[3] for n in nombres
                if n.startswith("Report/definition/pages/")
                and n.count("/") > 3}
    orden = list(datos.get("pageOrder") or [])
    problemas = []
    for pid in sorted(set(orden) - carpetas):
        problemas.append(traducir("vf_pag_falta", idioma).format(pagina=pid))
    for pid in sorted(carpetas - set(orden)):
        problemas.append(traducir("vf_pag_suelta", idioma).format(pagina=pid))
    for pid in sorted(k for k in set(orden) if orden.count(k) > 1):
        problemas.append(traducir("vf_pag_repetida", idioma).format(
            pagina=pid))
    activa = datos.get("activePageName")
    if activa and activa not in carpetas:
        problemas.append(traducir("vf_pag_activa", idioma).format(
            pagina=activa))
    # El nombre de adentro y el de la carpeta tienen que ser el mismo: es
    # por el nombre que el reporte referencia una página (marcadores,
    # botones de navegación, drillthrough).
    for pid in sorted(carpetas):
        try:
            pj = json.loads(z.read(
                f"Report/definition/pages/{pid}/page.json").decode("utf-8-sig"))
        except Exception:                             # noqa: BLE001
            problemas.append(traducir("vf_pag_sin_json", idioma).format(
                pagina=pid))
            continue
        if pj.get("name") != pid:
            problemas.append(traducir("vf_pag_nombre", idioma).format(
                pagina=pid, dentro=pj.get("name") or "—"))
    return _item("paginas", FALTA if problemas else OK, idioma,
                 n=len(problemas), total=len(carpetas),
                 lista=" · ".join(problemas[:3]) or "—")


def _refs_pbir(nodo, alias: dict, salida: set) -> None:
    """Junta cada `(entidad, campo)` que un JSON de PBIR referencia.

    El `From` de una consulta bautiza la tabla con un alias (`s`) y las
    proyecciones la nombran por ese alias, así que hay que recorrer dos
    veces: la primera para juntar los alias, la segunda para resolverlos.
    """
    if isinstance(nodo, dict):
        for f in nodo.get("From") or []:
            if isinstance(f, dict) and f.get("Name") and f.get("Entity"):
                alias[f["Name"]] = f["Entity"]
        exp = nodo.get("Expression")
        if isinstance(exp, dict):
            ent = _entidad_pbir(exp, alias)
            if ent:
                for clave in ("Property", "Hierarchy"):
                    if isinstance(nodo.get(clave), str):
                        salida.add((ent, nodo[clave]))
        for v in nodo.values():
            _refs_pbir(v, alias, salida)
    elif isinstance(nodo, list):
        for v in nodo:
            _refs_pbir(v, alias, salida)


def _entidad_pbir(exp: dict, alias: dict) -> str | None:
    ref = exp.get("SourceRef")
    if isinstance(ref, dict):
        return ref.get("Entity") or alias.get(ref.get("Source") or "")
    for v in exp.values():
        if isinstance(v, dict):
            hallada = _entidad_pbir(v, alias)
            if hallada:
                return hallada
    return None


def _visuales_pbir(z: zipfile.ZipFile, nombres: set[str], esquema: dict,
                   idioma: str) -> dict | None:
    """Cada visual del PBIR: que se lea, que se ubique y que sus campos existan.

    El gate miraba los visuales a través del layout traducido, y esa
    traducción se saltea en silencio lo que no entiende: un `visual.json`
    con el JSON roto desaparecía del layout y el archivo se aprobaba con
    una página menos adentro. Lo mismo con un campo que apunta a una
    tabla que ya no está: en Desktop es un visual con el cartel de error,
    y acá no lo veía nadie. Se leen los archivos como están escritos.
    """
    if not any(n.startswith("Report/definition/pages/") for n in nombres):
        return None
    from .catalogo import Catalogo
    cat = Catalogo.desde_modelo(esquema)
    jerarquias = {(t.get("name"), h.get("name"))
                  for t in esquema.get("model", {}).get("tables", [])
                  for h in t.get("hierarchies", []) or []}
    medidas = {(m["tabla"], m["nombre"]) for m in cat.medidas()}

    lienzos: dict[str, tuple[float, float]] = {}
    for n in nombres:
        if not n.endswith("/page.json"):
            continue
        try:
            pj = json.loads(z.read(n).decode("utf-8-sig"))
        except Exception:                             # noqa: BLE001
            continue
        lienzos[n.split("/")[3]] = (float(pj.get("width") or 1280),
                                    float(pj.get("height") or 720))

    problemas: list[str] = []
    total = 0
    for n in sorted(nombres):
        if not n.endswith("/visual.json"):
            continue
        total += 1
        pagina = n.split("/")[3]
        etq = f"{pagina}/{n.split('/')[5]}"
        try:
            v = json.loads(z.read(n).decode("utf-8-sig"))
        except Exception as exc:                      # noqa: BLE001
            problemas.append(traducir("vf_vis_ilegible", idioma).format(
                visual=etq, motivo=type(exc).__name__))
            continue
        pos = v.get("position")
        if not v.get("name") or not isinstance(pos, dict):
            problemas.append(traducir("vf_vis_sin_lugar", idioma).format(
                visual=etq))
            continue
        try:
            x, y = float(pos["x"]), float(pos["y"])
            ancho, alto = float(pos["width"]), float(pos["height"])
        except (KeyError, TypeError, ValueError):
            problemas.append(traducir("vf_vis_sin_lugar", idioma).format(
                visual=etq))
            continue
        lx, ly = lienzos.get(pagina, (1280.0, 720.0))
        if x < 0 or y < 0 or x + ancho > lx + 1 or y + alto > ly + 1:
            problemas.append(traducir("vf_vis_afuera", idioma).format(
                visual=etq, x=int(x), y=int(y),
                ancho=int(ancho), alto=int(alto)))
        campos: set = set()
        alias: dict = {}
        _refs_pbir(v, alias, set())
        _refs_pbir(v, alias, campos)
        for entidad, campo in sorted(campos):
            if (cat.existe_columna(entidad, campo)
                    or (entidad, campo) in medidas
                    or (entidad, campo) in jerarquias):
                continue
            problemas.append(traducir("vf_vis_campo", idioma).format(
                visual=etq, tabla=entidad, campo=campo))
    if not total:
        return None
    return _item("visuales", FALTA if problemas else OK, idioma,
                 n=len(problemas), total=total,
                 lista=" · ".join(problemas[:3]) or "—")


def _campos_visual(sv: dict) -> tuple[list[tuple[str, str]],
                                      list[tuple[str, str]]]:
    """Medidas y categorías de un visual, venga como venga.

    El layout clásico las lleva en `prototypeQuery.Select`; el PBIR, en
    `query.queryState.<rol>.projections[].field`. El ítem de ejes se
    estrenó mirando solo la primera forma y quedó CIEGO en los archivos
    nuevos — que son exactamente los que este programa exporta: el gate
    dio 0 faltas sobre el archivo con la portada rota que motivó el ítem.
    """
    medidas: list[tuple[str, str]] = []
    categorias: list[tuple[str, str]] = []

    for sel in (sv.get("prototypeQuery") or {}).get("Select", []) or []:
        tabla, _, campo = sel.get("Name", "").partition(".")
        if "Measure" in sel:
            medidas.append((tabla, campo))
        elif "Column" in sel or "HierarchyLevel" in sel:
            categorias.append((tabla, campo))

    estado = (sv.get("query") or {}).get("queryState") or {}
    for rol in estado.values():
        for proy in (rol or {}).get("projections", []) or []:
            campo = (proy or {}).get("field") or {}
            for clase, nodo in campo.items():
                if not isinstance(nodo, dict):
                    continue
                ent = (((nodo.get("Expression") or {}).get("SourceRef")
                        or {}).get("Entity", ""))
                prop = nodo.get("Property") or nodo.get("Level") or ""
                if not prop:
                    continue
                if clase == "Measure":
                    medidas.append((ent, prop))
                elif clase in ("Column", "HierarchyLevel"):
                    categorias.append((ent, prop))
    return medidas, categorias


def _ejes(cat: Catalogo, layout: dict, idioma: str) -> dict:
    """Ejes que las medidas del visual NO escuchan.

    Un gráfico cuyo eje no llega, por las relaciones, a ninguna de las
    tablas de sus medidas no da error: repite el MISMO total en cada
    barra y en cada fila, con cara de hallazgo. Pasó en la PORTADA de un
    informe entregado — el ranking cortaba por las columnas del glosario
    del dataset, una tabla suelta, y todo daba 8,0 % — y este gate lo dejó
    pasar con cero faltas. Un gate que no ve el peor gráfico posible no
    está mirando lo que el usuario ve primero.

    La medida que REFERENCIA a la tabla del eje (un `SELECTEDVALUE` sobre
    una tabla de parámetros, la lectura de la página de análisis) pasa:
    `tablas_de_medida` sigue la cadena de llamadas y esa tabla queda entre
    las suyas.
    """
    from .tablero import filtra, tablas_de_medida

    sordos: list[str] = []
    revisados = 0
    for pag in layout.get("sections", []) or []:
        for vc in pag.get("visualContainers", []) or []:
            try:
                sv = json.loads(vc["config"])["singleVisual"]
            except Exception:                          # noqa: BLE001
                continue
            medidas, categorias = _campos_visual(sv)
            if not medidas or not categorias:
                continue          # un slicer o una tabla de solo columnas
            revisados += 1
            hechos: set[str] = set()
            for _t, m in medidas:
                hechos |= tablas_de_medida(cat, m)
            if not hechos:
                continue          # sin evidencia no se acusa
            for tabla, campo in categorias:
                if not cat.tabla(tabla):
                    continue      # eso ya lo acusa el ítem de campos
                if filtra(cat, tabla, hechos):
                    continue
                etq = f'{pag.get("displayName", "?")} · {tabla}[{campo}]'
                if etq not in sordos:
                    sordos.append(etq)
    return _item("ejes", FALTA if sordos else OK, idioma,
                 n=len(sordos), total=revisados,
                 lista=" · ".join(sordos[:4]) or "—")


def _es_texto(cat: Catalogo, nombre: str) -> bool:
    """¿Esta medida del visual devuelve una frase y no un número?"""
    from .analizador import es_medida_de_texto
    m = cat.medida(nombre)
    return bool(m) and es_medida_de_texto(m.get("expresion", ""), cat)


def _constantes(cat: Catalogo, layout: dict, idioma: str) -> dict:
    """Medidas que van a salir con el MISMO número en todas las filas.

    Un share cuyo denominador quita el filtro de una columna sólo
    significa algo cuando esa columna está en el eje del visual: en
    cualquier otro lado el numerador y el denominador se filtran igual y
    da 100 % en todas las filas — y su variación contra el año anterior,
    exactamente 0,0. Un usuario lo reportó como «me parece raro el 0» y
    tenía razón: no es un defecto de dibujo, es un número que parece un
    dato y no lo es.
    """
    from .tablero import sin_eje

    malas = []
    for pag in layout.get("sections", []) or []:
        for vc in pag.get("visualContainers", []) or []:
            try:
                sv = json.loads(vc["config"])["singleVisual"]
            except Exception:                              # noqa: BLE001
                continue
            # `_campos_visual` entiende las dos formas del reporte; con la
            # vieja lectura de `prototypeQuery` este ítem estaba CIEGO en
            # los archivos PBIR — que son los que este programa exporta.
            medidas, categorias = _campos_visual(sv)
            # Sin categorías no hay «todas las filas»: una tarjeta muestra
            # UN total, y un share global en una tarjeta es un dato
            # legítimo — el 47 % de participación total. La medida se
            # vuelve mentirosa recién cuando hay un eje al lado que
            # debería moverla y no la mueve.
            if not medidas or not categorias:
                continue
            # Una medida de TEXTO no muestra «el mismo número»: muestra
            # una frase distinta por fila. La lectura de cada página del
            # informe elige con un SWITCH sobre el eje, y las medidas que
            # nombra adentro pueden quitar el filtro de una corporación
            # sin que eso signifique nada para el texto que sale.
            medidas = [(t, n) for t, n in medidas
                       if not _es_texto(cat, n)]
            if not medidas:
                continue
            for _t, nom in sin_eje(cat, medidas, categorias):
                etq = f'{pag.get("displayName", "?")} · {nom}'
                if etq not in malas:
                    malas.append(etq)
    return _item("constantes", AVISO if malas else OK, idioma,
                 n=len(malas), lista=" · ".join(malas[:4]) or "—")


def _si_no(valor: bool, idioma: str) -> str:
    return traducir("vf_si" if valor else "vf_no", idioma)


def _resumen(items: list[dict]) -> dict:
    faltan = sum(1 for i in items if i["estado"] == FALTA)
    avisos = sum(1 for i in items if i["estado"] == AVISO)
    return {"items": items, "faltan": faltan, "avisos": avisos,
            "listo": faltan == 0}


def como_texto(resultado: dict, idioma: str = IDIOMA_DEFECTO) -> str:
    """El veredicto en texto plano, para pegar en una consola o un log."""
    simbolo = {OK: "OK   ", AVISO: "AVISO", FALTA: "FALTA"}
    lineas = [f'[{simbolo[i["estado"]]}] {i["titulo"]}: {i["detalle"]}'
              for i in resultado["items"]]
    lineas.append("")
    lineas.append(traducir(
        "vf_veredicto_ok" if resultado["listo"] else "vf_veredicto_falta",
        idioma).format(faltan=resultado["faltan"],
                       avisos=resultado["avisos"]))
    return "\n".join(lineas)


# ==========================================================================
# Sintaxis del Power Query
# ==========================================================================
# Palabras de M que empiezan línea y NO son el nombre de un paso.
_CLAVES_M = {"let", "in", "if", "then", "else", "each", "and", "or", "not",
             "try", "otherwise", "error", "meta", "as", "is", "type"}

_RE_PASO = re.compile(
    r'(?:^|\n)[ \t]*(#"(?:[^"]|"")*"|[A-Za-z_][\w.]*)[ \t]*=(?![=>])')


def _sin_literales(texto: str) -> tuple[str, bool]:
    """El M sin literales ni comentarios, y si quedó un texto sin cerrar.

    El aviso viaja de vuelta porque acá es el único lugar donde se sabe:
    una comilla huérfana se blanquea igual que una bien cerrada, así que
    contarlas después del blanqueo siempre da par y no detecta nada.

    Se preservan la longitud y los saltos de línea para que las posiciones
    sigan valiendo. Sin esto, un base64 con paréntesis o una coma adentro
    de un texto descuadran cualquier conteo.
    """
    salida = list(texto)
    abierto = False
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if c == '"':
            j = i + 1
            while j < n:
                if texto[j] == '"':
                    if j + 1 < n and texto[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            abierto = abierto or j >= n
            for k in range(i, min(j + 1, n)):
                if texto[k] != "\n":
                    salida[k] = " "
            i = j + 1
        elif c == "/" and i + 1 < n and texto[i + 1] == "/":
            while i < n and texto[i] != "\n":
                salida[i] = " "
                i += 1
        elif c == "/" and i + 1 < n and texto[i + 1] == "*":
            j = texto.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if texto[k] != "\n":
                    salida[k] = " "
            i = j
        else:
            i += 1
    return "".join(salida), abierto


def _bloques_let(limpio: str) -> list[tuple[int, int]]:
    """Los pares `let`…`in` del texto, emparejados como paréntesis.

    M permite anidar: un paso puede ser una función que abre su propio
    `let`. Sin emparejarlos, los pasos del bloque de adentro se leen como
    pasos del de afuera y la consulta más común del mundo —una función
    que envuelve otra consulta— se reporta como rota.
    """
    marcas = [(m.start(), m.group()) for m in
              re.finditer(r"\b(?:let|in)\b", limpio)]
    pila, bloques = [], []
    for pos, palabra in marcas:
        if palabra == "let":
            pila.append(pos)
        elif pila:
            bloques.append((pila.pop(), pos))
    return bloques


def sintaxis_m(texto: str) -> list[str]:
    """Los errores de sintaxis del M. Vacío = sin errores detectados.

    NO es un parser de M —eso es un proyecto en sí mismo— sino el puñado
    de roturas estructurales que de verdad ocurren cuando una consulta se
    arma pegando texto: paréntesis sin cerrar, un texto sin cerrar, y
    sobre todo **un paso del `let` sin la coma que lo separa del
    siguiente**, que es lo que Power BI reporta como «Se esperaba el
    token \',\'» y lo que dejó un archivo entero sin abrir.

    Ante la duda, calla. Un falso positivo bloquearía una exportación
    legítima; un falso negativo solo deja pasar algo que Desktop igual va
    a reportar. Verificado contra 131 consultas reales: ninguna de las
    escritas por Power BI Desktop da error.
    """
    limpio, abierto = _sin_literales(texto)
    if abierto:
        return ["texto sin cerrar"]

    pares = {")": "(", "]": "[", "}": "{"}
    pila = []
    for c in limpio:
        if c in "([{":
            pila.append(c)
        elif c in pares:
            if not pila or pila.pop() != pares[c]:
                return [f"paréntesis desbalanceado en \'{c}\'"]
    if pila:
        return [f"queda sin cerrar \'{pila[-1]}\'"]

    errores = []
    bloques = _bloques_let(limpio)
    for ini, fin in bloques:
        # El cuerpo propio del bloque: se blanquean los `let` anidados
        # para que sus pasos no se cuenten como pasos de este.
        cuerpo = list(limpio[ini + 3:fin])
        for sub_i, sub_f in bloques:
            if ini < sub_i and sub_f <= fin:
                for k in range(sub_i - (ini + 3), sub_f + 2 - (ini + 3)):
                    if 0 <= k < len(cuerpo) and cuerpo[k] != "\n":
                        cuerpo[k] = " "
        errores += _pasos_sin_coma("".join(cuerpo))
    return errores


def _pasos_sin_coma(cuerpo: str) -> list[str]:
    """Dos asignaciones entre coma y coma significan que falta una coma."""
    profundidad, actual, segmentos = 0, [], []
    for c in cuerpo:
        if c in "([{":
            profundidad += 1
        elif c in ")]}":
            profundidad -= 1
        if c == "," and profundidad == 0:
            segmentos.append("".join(actual))
            actual = []
        else:
            actual.append(c)
    segmentos.append("".join(actual))

    errores = []
    for seg in segmentos:
        nombres = [m.group(1) for m in _RE_PASO.finditer("\n" + seg)
                   if m.group(1) not in _CLAVES_M]
        if len(nombres) > 1:
            errores.append("falta una coma entre los pasos "
                           + " y ".join(nombres[:2]))
    return errores
