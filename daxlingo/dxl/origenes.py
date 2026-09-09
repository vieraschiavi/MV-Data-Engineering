# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Orígenes de datos: dónde busca cada consulta y cómo moverlos.

El error de campo que motivó este módulo, literal de Power BI Desktop:

    Actualizar — 1 consulta está bloqueada por los siguientes errores:
    Proyecto VAR · File or Folder: No se puede encontrar una parte de la
    ruta de acceso 'C:\\Users\\...\\Encuesta 6.xlsx'.

No es un defecto del modelo: Power Query guarda la ruta COMPLETA de cada
archivo, con el nombre de usuario y la carpeta de quien lo armó. En cuanto
el archivo se mueve, se renombra, se abre en otra PC o OneDrive lo
sincroniza en otro lado, el refresh se corta. Y el archivo abre igual —los
datos importados siguen adentro—, así que la falla aparece recién al
actualizar.

Este módulo hace tres cosas:

  · `detectar` — qué origen usa cada consulta y cuál es frágil (una ruta
    personal de una máquina, tipo `C:\\Users\\...` u OneDrive).
  · `repuntar` — cambiar una carpeta base por otra en TODAS las consultas
    de una vez, respetando el resto de la M.
  · `parametrizar` — dejar la carpeta en un parámetro de Power Query, para
    que la próxima mudanza se arregle en un solo lugar.

Las consultas de un .pbit pueden vivir en dos lados: las particiones del
modelo (lo que se lee y se reescribe acá) y la parte binaria `DataMashup`
del contenedor, que este programa NO reescribe. Si el archivo la trae,
`repuntar` lo dice en vez de dar por hecho un arreglo a medias.
"""
from __future__ import annotations

import os
import re

from .catalogo import _norm
from .i18n import IDIOMA_DEFECTO, t as traducir
from .modelo import expr_lineas, expr_texto

# Rutas de archivo dentro de una expresión M. En M la barra invertida no
# escapa nada (la comilla se escapa duplicándola), así que la ruta viaja
# literal entre comillas.
# `C:\...`, `\\servidor\...` y también una ruta POSIX absoluta con al menos
# dos tramos (`/datos/ventas.xlsx`). Lo último no aparece en un informe
# hecho en Windows, pero sí cuando el motor corre en Linux o macOS —donde
# se desarrolla y se testea—, y sin eso el circuito de buscar y repuntar
# no se podría probar de punta a punta. Dos tramos como mínimo para no
# confundir un separador suelto («/») con una ruta.
_RE_RUTA = re.compile(r'"((?:[A-Za-z]:[\\/]|\\\\|/[^"/\s][^"]*/)[^"]*)"')
_RE_URL = re.compile(r'"(https?://[^"]+)"')
_RE_SQL = re.compile(r'Sql\.Databases?\s*\(\s*"([^"]*)"\s*,\s*"([^"]*)"')

# Lo que delata una ruta personal: la carpeta de un usuario concreto o una
# sincronización de nube atada a una cuenta.
_PERSONALES = ("\\users\\", "/users/", "onedrive", "dropbox",
               "google drive", "\\documents\\", "\\documentos\\",
               "\\escritorio\\", "\\desktop\\")


def _carpeta_de(ruta: str) -> str:
    corte = max(ruta.rfind("\\"), ruta.rfind("/"))
    return ruta[:corte + 1] if corte >= 0 else ""


def _es_personal(ruta: str) -> bool:
    return any(p in _norm(ruta) for p in _PERSONALES)


def _particiones(modelo: dict):
    """Las consultas M que PUEDEN tener un origen afuera.

    Una tabla con los datos empotrados no tiene ninguno: sus filas viajan
    adentro del archivo. Mirarla igual no era inofensivo — el base64 de
    esas filas se leía como si fueran rutas.
    """
    for t in modelo.get("model", modelo).get("tables", []):
        for p in t.get("partitions", []):
            fuente = p.get("source") or {}
            if fuente.get("type") != "m":
                continue
            texto = expr_texto(fuente.get("expression"))
            if "Binary.Decompress" in texto and "Table.FromRows" in texto:
                continue
            yield t, p, fuente


# Las funciones de M que salen a buscar algo AFUERA. Una ruta solo cuenta
# si está en el argumento de alguna de ellas.
_M_EXTERNO = ("File.Contents", "Excel.Workbook", "Csv.Document",
              "Sql.Database", "Web.Contents", "Folder.Files", "Odbc.",
              "SharePoint.", "OData.Feed", "Json.Document(Web")

# Cuánto texto después del nombre de la función se mira buscando la ruta.
_VENTANA = 400


def _tramos_externos(texto: str) -> list[str]:
    """Los pedazos de la consulta donde una ruta significa algo.

    Barrer la consulta entera parecía más simple y era falso: en una tabla
    con los datos empotrados, el base64 viaja partido en trozos de 500
    caracteres entre comillas, y cualquiera que arranque con «/» y tenga
    otra «/» adentro es, para una regex de rutas POSIX, una ruta
    impecable. La pestaña Exportar avisaba «2 archivos de origen NO están
    donde las consultas los buscan» —con nombres ilegibles— sobre un
    archivo que lleva los datos adentro y no necesita refrescar nada.
    """
    tramos = []
    for fn in _M_EXTERNO:
        desde = 0
        while (i := texto.find(fn, desde)) >= 0:
            desde = i + len(fn)
            tramos.append(texto[desde:desde + _VENTANA])
    return tramos


def detectar(modelo: dict) -> list[dict]:
    """Un renglón por origen encontrado: tabla, tipo, dónde apunta y si es
    frágil. Sin adivinar: solo lo que la expresión M dice."""
    encontrados: list[dict] = []
    for t, _p, fuente in _particiones(modelo):
        texto = expr_texto(fuente.get("expression"))
        vistos: set[str] = set()
        for m in _RE_RUTA.finditer("\n".join(_tramos_externos(texto))):
            ruta = m.group(1)
            if ruta in vistos:
                continue
            vistos.add(ruta)
            es_carpeta = ruta.endswith(("\\", "/"))
            encontrados.append({
                "tabla": t.get("name", ""),
                "tipo": "carpeta" if es_carpeta else "archivo",
                "ruta": ruta,
                "carpeta": ruta if es_carpeta else _carpeta_de(ruta),
                "fragil": _es_personal(ruta),
            })
        for m in _RE_SQL.finditer(texto):
            encontrados.append({
                "tabla": t.get("name", ""), "tipo": "sql",
                "ruta": f"{m.group(1)} · {m.group(2)}",
                "carpeta": "", "fragil": False})
        for m in _RE_URL.finditer(texto):
            encontrados.append({
                "tabla": t.get("name", ""), "tipo": "web",
                "ruta": m.group(1), "carpeta": "", "fragil": False})
    return encontrados


def carpetas(modelo: dict) -> list[str]:
    """Las carpetas base distintas que usan los orígenes de archivo, de la
    más usada a la menos."""
    cuenta: dict[str, int] = {}
    for o in detectar(modelo):
        if o["carpeta"]:
            cuenta[o["carpeta"]] = cuenta.get(o["carpeta"], 0) + 1
    return [c for c, _ in sorted(cuenta.items(), key=lambda par: -par[1])]


# ==========================================================================
# ¿Están los archivos donde el informe los busca? Y si no, ¿dónde están?
#
# Esto es lo que convierte el diagnóstico en arreglo. El programa corre en
# la misma máquina que Power BI Desktop, así que puede mirar el disco: no
# hace falta que nadie adivine cuál de las seis rutas está rota ni salir a
# buscar los Excel a mano.
# ==========================================================================
def _nombre_de(ruta: str) -> str:
    corte = max(ruta.rfind("\\"), ruta.rfind("/"))
    return ruta[corte + 1:] if corte >= 0 else ruta


def _local(ruta: str) -> str:
    """La ruta como la entiende ESTE sistema operativo.

    Las rutas del modelo son de Windows (`C:\\...`). Corriendo en Windows
    se usan tal cual; en Linux/macOS —donde se desarrolla y se testea— no
    existen, y decir «no está» sería una respuesta inventada: por eso
    `verificar` distingue «no está» de «no puedo saberlo».
    """
    return ruta.replace("\\", os.sep) if os.sep != "\\" else ruta


def verificar(modelo: dict) -> list[dict]:
    """Los orígenes de archivo con una clave `existe` de más:

        True   el archivo está donde la consulta lo busca
        False  NO está — esta consulta va a fallar al Actualizar
        None   no se puede saber desde acá (ruta de red, o el modelo se
               está mirando en otra máquina que la del informe)
    """
    salida = []
    en_windows = os.name == "nt"
    for o in detectar(modelo):
        if o["tipo"] not in ("archivo", "carpeta"):
            continue
        ruta = o["ruta"]
        existe: bool | None = None
        if ruta.startswith("\\\\"):
            existe = None            # UNC: puede requerir credenciales
        elif re.match(r"^[A-Za-z]:", ruta) and not en_windows:
            existe = None            # ruta de Windows, no estamos en Windows
        else:
            try:
                existe = os.path.exists(_local(ruta))
            except OSError:
                existe = None
        salida.append({**o, "existe": existe,
                       "nombre": _nombre_de(ruta)})
    return salida


# Cuántas carpetas se recorren como mucho al buscar. Un OneDrive entero
# puede tener cientos de miles de archivos; sin tope, «Buscar» parecería
# colgado. Al cortar se dice, no se miente diciendo que no está.
_MAX_CARPETAS = 20000

# Carpetas que no se recorren: nunca guardan los datos del informe y son
# las que más archivos tienen.
_IGNORADAS = {"node_modules", ".git", "$recycle.bin", "windows",
              "appdata", "__pycache__", ".venv", "venv",
              "system volume information"}


def buscar(modelo: dict, carpeta_raiz: str,
           solo_faltantes: bool = True) -> dict:
    """Busca por NOMBRE los archivos del modelo dentro de `carpeta_raiz`.

    Cada archivo se resuelve por separado: en un caso real los seis Excel
    de un informe pueden haber quedado en carpetas distintas, y cambiar
    una sola carpeta base no los alcanza a todos.

    Devuelve:
      encontrados   {ruta_vieja: ruta_nueva} — uno solo y sin ambigüedad
      ambiguos      {ruta_vieja: [candidatas]} — aparece más de una vez
      sin_encontrar [ruta_vieja, ...]
      cortado       True si se alcanzó el tope de carpetas recorridas
    """
    faltantes = [o for o in verificar(modelo)
                 if o["tipo"] == "archivo"
                 and (o["existe"] is not True or not solo_faltantes)]
    buscados = {}
    for o in faltantes:
        buscados.setdefault(_norm(o["nombre"]), []).append(o["ruta"])
    if not buscados:
        return {"encontrados": {}, "ambiguos": {}, "sin_encontrar": [],
                "cortado": False}

    hallados: dict[str, list[str]] = {}
    carpetas_vistas = 0
    cortado = False
    for base, dirs, archivos in os.walk(carpeta_raiz):
        carpetas_vistas += 1
        if carpetas_vistas > _MAX_CARPETAS:
            cortado = True
            break
        dirs[:] = [d for d in dirs
                   if _norm(d) not in _IGNORADAS and not d.startswith(".")]
        for archivo in archivos:
            clave = _norm(archivo)
            if clave in buscados:
                hallados.setdefault(clave, []).append(
                    os.path.join(base, archivo))

    encontrados: dict[str, str] = {}
    ambiguos: dict[str, list[str]] = {}
    sin_encontrar: list[str] = []
    for clave, viejas in buscados.items():
        candidatas = sorted(set(hallados.get(clave, [])))
        for vieja in viejas:
            if len(candidatas) == 1:
                encontrados[vieja] = candidatas[0]
            elif candidatas:
                ambiguos[vieja] = candidatas
            else:
                sin_encontrar.append(vieja)
    return {"encontrados": encontrados, "ambiguos": ambiguos,
            "sin_encontrar": sin_encontrar, "cortado": cortado}


def repuntar_archivos(modelo: dict, mapeo: dict[str, str],
                      idioma: str = IDIOMA_DEFECTO,
                      datamashup: bytes | None = None
                      ) -> tuple[dict, list[str]]:
    """Aplica un mapeo ARCHIVO por archivo (no una carpeta base entera).

    La ruta nueva se escribe tal como la dio el sistema donde se buscó
    —barra invertida en Windows, que es donde corre Power BI—: forzar un
    separador produciría, en cualquier otro sistema, una ruta que no
    existe en ningún lado.
    """
    import copy
    modelo = copy.deepcopy(modelo)
    if not mapeo:
        return modelo, [traducir("or_nada_que_repuntar", idioma)]
    normalizado = {_norm(v).replace("/", "\\"): n
                   for v, n in mapeo.items()}

    def cambiar(ruta: str) -> str | None:
        return normalizado.get(_norm(ruta).replace("/", "\\"))

    modelo, hechos = _sustituir(modelo, cambiar)
    if not hechos:
        return modelo, [traducir("or_nada_que_repuntar", idioma)]
    cambios = [traducir("or_repuntado", idioma).format(
        tabla=tabla, antes=antes, despues=despues)
        for tabla, antes, despues in hechos]
    if datamashup:
        cambios.append(traducir("or_datamashup", idioma))
    return modelo, cambios


def buscar_y_repuntar(modelo: dict, carpeta_raiz: str,
                      idioma: str = IDIOMA_DEFECTO,
                      datamashup: bytes | None = None
                      ) -> tuple[dict, list[str]]:
    """Busca los archivos que faltan bajo `carpeta_raiz` y repunta los que
    aparecen una sola vez. Lo ambiguo y lo que no aparece se informa: no se
    elige por el usuario cuando hay dos archivos con el mismo nombre."""
    if not carpeta_raiz or not os.path.isdir(_local(carpeta_raiz)):
        raise ValueError(traducir("or_err_carpeta", idioma).format(
            carpeta=carpeta_raiz or "—"))
    hallazgo = buscar(modelo, _local(carpeta_raiz))
    modelo, cambios = repuntar_archivos(
        modelo, hallazgo["encontrados"], idioma, datamashup)
    for vieja, candidatas in hallazgo["ambiguos"].items():
        cambios.append(traducir("or_ambiguo", idioma).format(
            archivo=_nombre_de(vieja), n=len(candidatas),
            opciones=" · ".join(candidatas[:3])))
    for vieja in hallazgo["sin_encontrar"]:
        cambios.append(traducir("or_no_aparece", idioma).format(
            archivo=_nombre_de(vieja), carpeta=carpeta_raiz))
    if hallazgo["cortado"]:
        cambios.append(traducir("or_busqueda_cortada", idioma).format(
            n=_MAX_CARPETAS))
    return modelo, cambios


def _sustituir(modelo: dict, cambiar) -> tuple[dict, list[tuple[str, str,
                                                                str]]]:
    """Aplica `cambiar(ruta) -> nueva_ruta | None` a cada ruta de cada
    partición. Devuelve el modelo (mutado) y qué cambió."""
    hechos: list[tuple[str, str, str]] = []
    for t, _p, fuente in _particiones(modelo):
        texto = expr_texto(fuente.get("expression"))
        nuevo = texto

        def _repl(m):
            ruta = m.group(1)
            destino = cambiar(ruta)
            if destino is None or destino == ruta:
                return m.group(0)
            hechos.append((t.get("name", ""), ruta, destino))
            return '"' + destino + '"'

        nuevo = _RE_RUTA.sub(_repl, nuevo)
        if nuevo != texto:
            fuente["expression"] = expr_lineas(nuevo)
    return modelo, hechos


def repuntar(modelo: dict, vieja: str, nueva: str,
             idioma: str = IDIOMA_DEFECTO,
             datamashup: bytes | None = None) -> tuple[dict, list[str]]:
    """Cambia la carpeta base `vieja` por `nueva` en todas las consultas.

    La comparación es sin distinguir mayúsculas ni el tipo de barra —
    Windows no las distingue y quien pega una ruta la pega como le viene.
    """
    import copy
    modelo = copy.deepcopy(modelo)
    if not vieja or not nueva:
        raise ValueError(traducir("or_err_vacio", idioma))
    if not nueva.endswith(("\\", "/")):
        nueva += "\\" if "\\" in nueva else "/"
    objetivo = _norm(vieja).replace("/", "\\")
    if not objetivo.endswith("\\"):
        objetivo += "\\"

    def cambiar(ruta: str) -> str | None:
        plano = _norm(ruta).replace("/", "\\")
        if not plano.startswith(objetivo):
            return None
        return nueva + ruta[len(objetivo):].lstrip("\\/")

    modelo, hechos = _sustituir(modelo, cambiar)
    if not hechos:
        return modelo, [traducir("or_sin_coincidencias", idioma).format(
            carpeta=vieja)]
    cambios = [traducir("or_repuntado", idioma).format(
        tabla=tabla, antes=antes, despues=despues)
        for tabla, antes, despues in hechos]
    if datamashup:
        # Las consultas también viven en el contenedor binario, que este
        # programa no reescribe: decirlo es la diferencia entre un arreglo
        # y la ilusión de un arreglo.
        cambios.append(traducir("or_datamashup", idioma))
    return modelo, cambios


_NOMBRE_PARAM = {"es": "CarpetaDatos", "en": "DataFolder",
                 "pt": "PastaDados"}


def parametrizar(modelo: dict, carpeta: str = "",
                 idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Deja la carpeta base en un parámetro de Power Query y hace que todas
    las consultas lo usen. La próxima mudanza se arregla en un solo lugar,
    sin abrir consulta por consulta."""
    import copy
    modelo = copy.deepcopy(modelo)
    m = modelo.get("model", modelo)
    if not carpeta:
        disponibles = carpetas(modelo)
        if not disponibles:
            return modelo, [traducir("or_sin_archivos", idioma)]
        carpeta = disponibles[0]
    if not carpeta.endswith(("\\", "/")):
        carpeta += "\\" if "\\" in carpeta else "/"

    nombre = _NOMBRE_PARAM.get(idioma, _NOMBRE_PARAM["es"])
    objetivo = _norm(carpeta).replace("/", "\\")

    tocadas: list[str] = []
    for t, _p, fuente in _particiones(modelo):
        texto = expr_texto(fuente.get("expression"))

        def _repl(mm):
            ruta = mm.group(1)
            plano = _norm(ruta).replace("/", "\\")
            if not plano.startswith(objetivo):
                return mm.group(0)
            resto = ruta[len(carpeta):].replace('"', '""')
            return f'{nombre} & "{resto}"'

        nuevo = _RE_RUTA.sub(_repl, texto)
        if nuevo != texto:
            fuente["expression"] = expr_lineas(nuevo)
            tocadas.append(t.get("name", ""))

    if not tocadas:
        return modelo, [traducir("or_sin_coincidencias", idioma).format(
            carpeta=carpeta)]

    # El parámetro, como expresión M del modelo — la misma forma en que
    # Power Query guarda un parámetro con su valor actual.
    expresiones = m.setdefault("expressions", [])
    valor = carpeta.replace('"', '""')
    existente = next((e for e in expresiones if e.get("name") == nombre),
                     None)
    definicion = {
        "name": nombre,
        "kind": "m",
        "expression": [
            f'"{valor}" meta [IsParameterQuery=true, Type="Text", '
            "IsParameterQueryRequired=true]"],
        "annotations": [{"name": "PBI_ResultType", "value": "Text"}],
    }
    if existente:
        existente.update(definicion)
    else:
        expresiones.append(definicion)
    return modelo, [traducir("or_parametrizado", idioma).format(
        param=nombre, carpeta=carpeta, n=len(set(tocadas)))]


# Para emparejar nombres de tabla se ignora TODO lo que no sea letra o
# número: `_norm` deja la puntuación, y con ella «Interacc Digital» —el
# nombre que sobrevive a una hoja de Excel— no encontraba a la tabla
# «Interacc. Digital» del modelo.
_RE_SOLO_ALFANUM = re.compile(r"[^a-z0-9]+")


def _clave(nombre: str) -> str:
    return _RE_SOLO_ALFANUM.sub("", _norm(nombre or ""))


def _por_normalizado(nombres) -> dict[str, str]:
    return {_clave(n): n for n in nombres}


def empotrar_subidos(modelo: dict, rutas: list[str],
                     idioma: str = IDIOMA_DEFECTO
                     ) -> tuple[dict, list[str]]:
    """Los archivos que faltan, SUBIDOS, y metidos adentro del modelo.

    Es la alternativa a escribir una ruta de Windows a mano, que era lo
    único que había: el buscador pide una carpeta, y una carpeta no se
    puede subir. Acá se sube el archivo y el problema desaparece de raíz,
    porque la consulta deja de depender de una ruta.

    No se repunta a la copia temporal del archivo subido —viviría lo que
    dura la sesión y volvería a romperse—, se EMPOTRA: los datos quedan
    adentro del modelo, como cuando Power BI usa «Introducir datos», y el
    .pbit abre en cualquier máquina sin refrescar nada.

    El emparejamiento es por NOMBRE DE TABLA, no por ruta: una planilla
    con las hojas `Medico`, `Producto` y `Ventas` tapa esas tres tablas
    del modelo, sin que importe desde dónde las leía antes. Se compara
    normalizado, así «Interacc. Digital» encuentra a «Interacc Digital».
    """
    from . import dataset

    if not rutas:
        return modelo, [traducir("or_nada_que_repuntar", idioma)]
    cargado = dataset.cargar_varios(list(rutas), idioma)
    meta = cargado.get("dataset_meta") or {}

    # Las tablas subidas se renombran a como se llaman EN EL MODELO. El
    # empotrado empareja por nombre exacto, y sin este paso una hoja
    # llamada «Interacc Digital» no tapaba a la tabla «Interacc. Digital»:
    # el archivo salía sin decir por qué seguía yendo a buscar afuera.
    del_modelo = _por_normalizado(
        t.get("name", "") for t in modelo.get("model", {}).get("tables", []))
    for t in meta.get("tablas", []) or []:
        real = del_modelo.get(_clave(t.get("nombre", "")))
        if real:
            t["nombre"] = real

    nuevo, notas = dataset.empotrar(modelo, meta, idioma)
    subidas = {t.get("nombre") for t in meta.get("tablas", []) or []}
    tapadas = sorted(n for n in del_modelo.values() if n in subidas)
    if tapadas:
        notas.insert(0, traducir("or_subidos_empotrados", idioma).format(
            n=len(tapadas), lista=" · ".join(tapadas[:6])))
    else:
        notas.insert(0, traducir("or_subidos_sin_pareja", idioma).format(
            lista=" · ".join(sorted(subidas)[:6]) or "—"))
    return nuevo, notas
