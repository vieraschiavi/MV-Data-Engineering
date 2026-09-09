# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Ingesta de datasets crudos: CSV, Excel y SQL.

Antes de que exista un .pbix ya hay datos: un CSV exportado, un Excel, el
script de la base. Este módulo los lee y PROPONE un modelo tabular real
(TMSL) sobre el que corren el analizador, los arreglos y el generador de
DAX — el mismo circuito que un .pbit. La propuesta es honesta: cada tipo
inferido, cada relación deducida y cada hueco (calendario que falta, ruta
de origen a ajustar) queda dicho en `notas`, nunca en silencio.

Sin dependencias nuevas a propósito: el CSV se lee con la stdlib, el .xlsx
se abre como lo que es (un zip con XML adentro) y el SQL se parsea como
texto — acá no se conecta a ninguna base: se lee el DDL (CREATE TABLE) y
las FOREIGN KEY dicen las relaciones. Las particiones del modelo llevan
Power Query (M) de verdad, así el .pbit exportado abre en Desktop y
refresca contra el origen una vez ajustada la ruta o el servidor.
"""
from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from .catalogo import _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

# Cuántas filas se muestrean para inferir tipos y unicidad. Alcanza para
# decidir y mantiene la carga instantánea con archivos grandes.
_MUESTRA = 500

# Techo para empotrar los datos DENTRO del .pbit. Pasado esto, el archivo
# se vuelve incómodo de mandar por mail y de abrir: mejor dejar el origen
# apuntando al archivo y decirlo, que fabricar un .pbit de 80 MB.
_MAX_FILAS_EMBEBIDAS = 50_000
_MAX_CELDAS_EMBEBIDAS = 400_000

# Marcas de columna clave, al principio o al final del nombre normalizado:
# «IdCliente», «cliente_id», «CodProducto», «SKU». Pegadas o con separador —
# la forma pegada («idcliente») es la más común y la que un \b no ve.
_RE_CLAVE = re.compile(
    r"^(?:id|cod|codigo|code|clave|key|sku|nro)[ _-]?"
    r"|[ _-]?(?:id|codigo|code|clave|key|sku|nro)$")

_RE_FECHA = re.compile(
    r"^\s*(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\s*$")
_RE_NUMERO = re.compile(r"^\s*-?\d+(?:[.,]\d+)?\s*$")
_RE_ENTERO = re.compile(r"^\s*-?\d+\s*$")
_BOOLEANOS = {"true", "false", "si", "sí", "no", "verdadero", "falso"}


def _encabezados(fila: list[str]) -> list[str]:
    """Los nombres de columna: sin vacíos y sin repetidos.

    Un modelo tabular no admite dos columnas con el mismo nombre, y el
    `Table.FromRows` de M tampoco: una planilla con `Importe,Importe`
    generaba un modelo que Power BI rechaza. Se numeran igual que las
    tablas homónimas.
    """
    salida: list[str] = []
    vistos: dict[str, int] = {}
    for i, c in enumerate(fila):
        nombre = (c or "").strip() or f"Columna{i + 1}"
        clave = _norm(nombre)
        vistos[clave] = vistos.get(clave, 0) + 1
        if vistos[clave] > 1:
            nombre = f"{nombre} ({vistos[clave]})"
        salida.append(nombre)
    return salida


def _hasta_el_techo(filas: list[list[str]], ancho: int) -> list[list[str]]:
    """Las filas recortadas al ancho del encabezado, hasta una más que el
    techo de empotrado (esa de más es la que delata que no entra).

    El techo mira las dos cotas —filas y celdas—: con 60 columnas, 50.000
    filas serían 3 millones de celdas que igual se iban a descartar, y
    hasta entonces se quedaban ocupando memoria toda la sesión.
    """
    tope = min(_MAX_FILAS_EMBEBIDAS,
               _MAX_CELDAS_EMBEBIDAS // max(ancho, 1)) + 1
    return [f[:ancho] + [""] * (ancho - len(f)) for f in filas[:tope]]


def es_dataset(ruta: str | Path) -> bool:
    return Path(ruta).suffix.lower() in (".csv", ".xlsx", ".sql")


# ==========================================================================
# Inferencia de tipos sobre valores de texto
# ==========================================================================
def _tipo_de(valores: list[str]) -> str:
    """El dataType TMSL que mejor describe la muestra (sin adivinar de más:
    con un solo valor que no encaja, la columna es string)."""
    utiles = [v.strip() for v in valores if v and v.strip()]
    if not utiles:
        return "string"
    if all(_RE_FECHA.match(v) for v in utiles):
        return "dateTime"
    if all(_RE_ENTERO.match(v) for v in utiles):
        return "int64"
    if all(_RE_NUMERO.match(v) for v in utiles):
        return "double"
    if all(v.lower() in _BOOLEANOS for v in utiles):
        return "boolean"
    return "string"


def _es_clave(nombre: str) -> bool:
    return bool(_RE_CLAVE.search(_norm(nombre)))


# ==========================================================================
# CSV
# ==========================================================================
def _leer_csv(ruta: Path) -> dict:
    try:
        texto = ruta.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        texto = ruta.read_text(encoding="latin-1")
    muestra = texto[:4096]
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t|")
        sep = dialecto.delimiter
    except csv.Error:
        # El sniffer falla con una sola columna; el separador más frecuente
        # de la primera línea decide, con coma como último recurso.
        primera = texto.splitlines()[0] if texto.splitlines() else ""
        sep = max(",;\t|", key=primera.count)
    filas = list(csv.reader(io.StringIO(texto), delimiter=sep))
    filas = [f for f in filas if any(c.strip() for c in f)]
    if not filas:
        raise ValueError(ruta.name)
    encabezados = _encabezados(filas[0])
    datos = filas[1:_MUESTRA + 1]
    columnas = []
    for i, nombre in enumerate(encabezados):
        valores = [f[i] for f in datos if i < len(f)]
        columnas.append({
            "nombre": nombre,
            "tipo": _tipo_de(valores),
            "unica": bool(valores) and len(
                {v.strip() for v in valores if v.strip()}) == len(
                [v for v in valores if v.strip()]),
        })
    return {"nombre": ruta.stem, "columnas": columnas,
            "filas": max(len(texto.splitlines()) - 1, len(datos)),
            "origen": "csv", "archivo": ruta.name, "sep": sep,
            # La carpeta REAL de donde salió, para que el Power Query
            # apunte ahí y no a una ruta inventada.
            "carpeta": str(ruta.resolve().parent).replace("\\", "/") + "/",
            # Las filas COMPLETAS: son las que se empotran en el .pbit
            # cuando se pide una demo autocontenida. Se guarda UNA más que
            # el techo: alcanza para saber que no entra sin cargar en
            # memoria un archivo de millones de filas que igual no se
            # va a empotrar.
            "datos": _hasta_el_techo(filas[1:], len(encabezados))}


# ==========================================================================
# Excel (.xlsx): zip + XML, sin openpyxl
# ==========================================================================
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_R = ("{http://schemas.openxmlformats.org/officeDocument/2006/"
         "relationships}")

# Formatos numéricos integrados que son fechas (ECMA-376 §18.8.30).
_FMT_FECHA = set(range(14, 23)) | set(range(45, 48))


def _estilos_fecha(z: zipfile.ZipFile) -> set[int]:
    """Índices de cellXfs cuyo formato numérico es de fecha/hora."""
    try:
        raiz = ET.fromstring(z.read("xl/styles.xml"))
    except (KeyError, ET.ParseError):
        return set()
    propios = set()
    for f in raiz.iter(f"{_NS}numFmt"):
        codigo = re.sub(r'"[^"]*"|\[[^\]]*\]', "", f.get("formatCode", ""))
        if re.search(r"[dmyhs]", codigo, re.I):
            propios.add(int(f.get("numFmtId", "-1")))
    indices = set()
    xfs = raiz.find(f"{_NS}cellXfs")
    for i, xf in enumerate(xfs.findall(f"{_NS}xf") if xfs is not None else []):
        fmt = int(xf.get("numFmtId", "0"))
        if fmt in _FMT_FECHA or fmt in propios:
            indices.add(i)
    return indices


def _fecha_excel(serial: float) -> str:
    # Época de Excel (con su año bisiesto fantasma de 1900 ya absorbido).
    base = datetime(1899, 12, 30)
    return (base + timedelta(days=serial)).strftime("%Y-%m-%d %H:%M:%S") \
        .replace(" 00:00:00", "")


def _columna_de(ref: str) -> int:
    """'BC7' → índice 54 (0-based)."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _celdas(hoja: bytes, cadenas: list[str],
            estilos: set[int]) -> list[list[str]]:
    filas: list[list[str]] = []
    for fila in ET.fromstring(hoja).iter(f"{_NS}row"):
        celdas: dict[int, str] = {}
        for c in fila.iter(f"{_NS}c"):
            idx = _columna_de(c.get("r", "")) if c.get("r") else len(celdas)
            tipo = c.get("t", "n")
            v = c.find(f"{_NS}v")
            if tipo == "s" and v is not None:
                texto = cadenas[int(v.text)] if v.text else ""
            elif tipo == "inlineStr":
                texto = "".join(t.text or ""
                                for t in c.iter(f"{_NS}t"))
            elif v is not None and v.text is not None:
                texto = v.text
                if tipo == "n" and int(c.get("s", "-1")) in estilos:
                    try:
                        texto = _fecha_excel(float(v.text))
                    except ValueError:
                        pass
                elif tipo == "b":
                    texto = "true" if v.text == "1" else "false"
            else:
                texto = ""
            if idx >= 0:
                celdas[idx] = texto
        if celdas:
            ancho = max(celdas) + 1
            filas.append([celdas.get(i, "") for i in range(ancho)])
    return filas


def _leer_xlsx(ruta: Path) -> list[dict]:
    tablas = []
    with zipfile.ZipFile(ruta) as z:
        try:
            cadenas = ["".join(t.text or ""
                               for t in si.iter(f"{_NS}t"))
                       for si in ET.fromstring(
                           z.read("xl/sharedStrings.xml"))
                       .iter(f"{_NS}si")]
        except KeyError:
            cadenas = []
        estilos = _estilos_fecha(z)
        libro = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target")
                for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        for hoja in libro.iter(f"{_NS}sheet"):
            destino = rels.get(hoja.get(f"{_NS_R}id"), "")
            if not destino:
                continue
            if not destino.startswith("/"):
                destino = "xl/" + destino
            filas = _celdas(z.read(destino.lstrip("/")), cadenas, estilos)
            filas = [f for f in filas if any(c.strip() for c in f)]
            if len(filas) < 2:
                continue
            encabezados = _encabezados(filas[0])
            datos = filas[1:_MUESTRA + 1]
            columnas = []
            for i, nombre in enumerate(encabezados):
                valores = [f[i] for f in datos if i < len(f)]
                columnas.append({
                    "nombre": nombre, "tipo": _tipo_de(valores),
                    "unica": bool(valores) and len(
                        {v.strip() for v in valores if v.strip()}) == len(
                        [v for v in valores if v.strip()]),
                })
            tablas.append({"nombre": hoja.get("name", ruta.stem),
                           "columnas": columnas, "filas": len(filas) - 1,
                           "origen": "xlsx", "archivo": ruta.name,
                           "carpeta": str(ruta.resolve().parent).replace(
                               "\\", "/") + "/",
                           "hoja": hoja.get("name", ""),
                           "datos": _hasta_el_techo(filas[1:],
                                                    len(encabezados))})
    if not tablas:
        raise ValueError(ruta.name)
    return tablas


# ==========================================================================
# SQL: el DDL dice el esquema; las FOREIGN KEY dicen las relaciones.
# Nunca se conecta a nada — es texto.
# ==========================================================================
_TIPOS_SQL = [
    (("bigint", "int", "smallint", "tinyint", "integer", "serial"), "int64"),
    (("decimal", "numeric", "money", "smallmoney"), "decimal"),
    (("float", "real", "double"), "double"),
    (("date", "datetime", "datetime2", "smalldatetime", "timestamp",
      "time"), "dateTime"),
    (("bit", "boolean", "bool"), "boolean"),
]

_RE_CREATE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?"
    r"(?:[\[\"`']?\w+[\]\"`']?\s*\.\s*)?"
    r"[\[\"`']?(?P<nombre>\w+)[\]\"`']?\s*\(", re.I)
_RE_FK = re.compile(
    r"foreign\s+key\s*\(\s*[\[\"`']?(?P<col>[\w ]+?)[\]\"`']?\s*\)\s*"
    r"references\s+(?:[\[\"`']?\w+[\]\"`']?\s*\.\s*)?"
    r"[\[\"`']?(?P<tabla>\w+)[\]\"`']?\s*"
    r"(?:\(\s*[\[\"`']?(?P<col_dest>[\w ]+?)[\]\"`']?\s*\))?", re.I)
_RE_REF_INLINE = re.compile(
    r"references\s+(?:[\[\"`']?\w+[\]\"`']?\s*\.\s*)?"
    r"[\[\"`']?(?P<tabla>\w+)[\]\"`']?\s*"
    r"(?:\(\s*[\[\"`']?(?P<col_dest>[\w ]+?)[\]\"`']?\s*\))?", re.I)
_RE_PK = re.compile(
    r"primary\s+key\s*(?:\(\s*[\[\"`']?(?P<col>[\w ]+?)[\]\"`']?\s*\))?",
    re.I)
_CONSTRAINT = ("primary key", "foreign key", "constraint", "unique",
               "check", "index", "key ")


def _cuerpo_parentesis(texto: str, desde: int) -> str:
    """El contenido entre el paréntesis que abre en `desde` y su cierre."""
    nivel = 0
    for i in range(desde, len(texto)):
        if texto[i] == "(":
            nivel += 1
        elif texto[i] == ")":
            nivel -= 1
            if nivel == 0:
                return texto[desde + 1:i]
    return texto[desde + 1:]


def _partir_columnas(cuerpo: str) -> list[str]:
    partes, nivel, actual = [], 0, []
    for ch in cuerpo:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0:
            partes.append("".join(actual))
            actual = []
        else:
            actual.append(ch)
    partes.append("".join(actual))
    return [p.strip() for p in partes if p.strip()]


def _leer_sql(texto: str, nombre_archivo: str) -> tuple[list[dict],
                                                        list[dict]]:
    texto = re.sub(r"--[^\n]*|/\*.*?\*/", "", texto, flags=re.DOTALL)
    tablas: list[dict] = []
    relaciones: list[dict] = []
    for m in _RE_CREATE.finditer(texto):
        nombre = m.group("nombre")
        cuerpo = _cuerpo_parentesis(texto, m.end() - 1)
        columnas: list[dict] = []
        for linea in _partir_columnas(cuerpo):
            baja = linea.lower()
            if baja.startswith(_CONSTRAINT):
                fk = _RE_FK.search(linea)
                if fk:
                    relaciones.append({
                        "desde_tabla": nombre,
                        "desde_col": fk.group("col").strip(),
                        "hacia_tabla": fk.group("tabla"),
                        "hacia_col": (fk.group("col_dest")
                                      or fk.group("col")).strip()})
                pk = _RE_PK.search(linea)
                if pk and pk.group("col"):
                    for c in columnas:
                        if _norm(c["nombre"]) == _norm(pk.group("col")):
                            c["unica"] = True
                continue
            mc = re.match(r"[\[\"`']?(?P<col>[\w ]+?)[\]\"`']?\s+"
                          r"(?P<tipo>\w+)", linea)
            if not mc:
                continue
            tipo_sql = mc.group("tipo").lower()
            tipo = next((t for alias, t in _TIPOS_SQL if tipo_sql in alias),
                        "string")
            col = {"nombre": mc.group("col").strip(), "tipo": tipo,
                   "unica": "primary key" in baja or " unique" in baja}
            ref = _RE_REF_INLINE.search(linea)
            if ref:
                relaciones.append({
                    "desde_tabla": nombre, "desde_col": col["nombre"],
                    "hacia_tabla": ref.group("tabla"),
                    "hacia_col": (ref.group("col_dest")
                                  or col["nombre"]).strip()})
            columnas.append(col)
        if columnas:
            tablas.append({"nombre": nombre, "columnas": columnas,
                           "filas": 0, "origen": "sql",
                           "archivo": nombre_archivo})
    if not tablas:
        raise ValueError(nombre_archivo)
    return tablas, relaciones


# ==========================================================================
# Power Query (M) de las particiones: origen REAL, no un stub
# ==========================================================================
_TIPO_M = {"int64": "Int64.Type", "double": "type number",
           "decimal": "Currency.Type", "dateTime": "type datetime",
           "boolean": "type logical", "string": "type text"}

# Carpeta que el M generado sugiere como ubicación de los archivos. Es TEXTO
# dentro del Power Query que el usuario ajusta en Desktop (la nota
# `ds_ruta_m` lo dice) — el programa jamás la abre. Va como tupla de
# candidatas, la forma que la guardia de rutas absolutas del producto
# reconoce como «sugerencia, no dependencia».
# Carpeta que se usa cuando NO se sabe de dónde salió el archivo (un
# modelo reconstruido sin su materia prima). Va como tupla de candidatas,
# la forma que la guardia de rutas absolutas del producto reconoce como
# «sugerencia, no dependencia» — y la nota `ds_ruta_m` avisa que hay que
# ajustarla. Cuando SÍ se sabe, manda la carpeta real: apuntar a una ruta
# inventada garantiza que el refresco falle en la máquina del cliente, que
# es de donde salió todo este problema.
_CARPETAS_DATOS = ("C:/Datos/",)


def _carpeta_de(tabla: dict) -> str:
    """De dónde lee esta tabla: su carpeta real si se conoce."""
    return tabla.get("carpeta") or _CARPETAS_DATOS[0]


def _m_texto(texto: str) -> str:
    return '"' + texto.replace('"', '""') + '"'


def _m_tipos(tabla: dict, paso_previo: str) -> str:
    pares = ", ".join(
        "{" + _m_texto(c["nombre"]) + ", " + _TIPO_M[c["tipo"]] + "}"
        for c in tabla["columnas"])
    return (f"    Tipos = Table.TransformColumnTypes({paso_previo}, "
            f"{{{pares}}})")


# Cultura con la que se convierten los tipos de una tabla empotrada. Los
# valores se escriben normalizados a formato invariante (fecha ISO, punto
# decimal), así que la conversión no depende del idioma de la máquina que
# abre el archivo: el mismo .pbit da los mismos números en Montevideo y en
# Ámsterdam.
_CULTURA_EMBEBIDA = "en-US"

_RE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})"
                     r"(?:[ T](\d{1,2}:\d{2}(?::\d{2})?))?$")
_RE_DMY = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
                     r"(?:[ T](\d{1,2}:\d{2}(?::\d{2})?))?$")


def _orden_fecha(valores: list[str]) -> tuple[str, bool]:
    """`("dia"|"mes", adivinado)`: qué va primero en fechas `03/04/2024`.

    Se decide mirando la columna ENTERA, no un valor: alcanza un solo
    `25/12` para saber que el día va primero, y un solo `12/25` para saber
    que va el mes.

    Cuando NINGÚN valor de la columna pasa de 12 no hay forma de saberlo
    —un export estadounidense de enero a diciembre es indistinguible de uno
    español— y se asume día primero, que es lo que escribe cualquier
    planilla en español. Ahí el segundo valor vuelve `True` y quien llama
    tiene que DECIRLO: al empotrar, el texto original ya no queda en el
    archivo, así que un mes y un día invertidos en silencio no se pueden
    descubrir después.
    """
    dia = mes = hay = False
    for v in valores:
        m = _RE_DMY.match((v or "").strip())
        if not m:
            continue
        hay = True
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            dia = True
        if b > 12:
            mes = True
    if mes and not dia:
        return "mes", False
    return "dia", hay and not dia


def _valor_embebido(texto: str, tipo: str, orden: str) -> object:
    """Una celda de texto → el valor que va en el JSON empotrado.

    Vacío es `null` (y no `""`): en una columna numérica o de fecha, el
    texto vacío rompe la conversión de tipo y Power BI marca error en la
    fila entera.
    """
    v = (texto or "").strip()
    if tipo == "string":
        return texto or ""
    if not v:
        return None
    if tipo in ("int64", "double", "decimal"):
        # Coma decimal a punto: «900,5» es un número para cualquier planilla
        # en español, y en-US no lo entiende. No se intenta desarmar
        # «1.234,56»: una columna así ni siquiera se tipa numérica (el tipo
        # se decide con `_RE_NUMERO`, que admite UN solo separador), viaja
        # como texto y no se toca.
        n = v.replace(" ", "").replace(",", ".")
        return n if _RE_NUMERO.match(n) else None
    if tipo == "dateTime":
        m = _RE_ISO.match(v)
        if m:
            y, mo, d, hora = m.group(1), m.group(2), m.group(3), m.group(4)
        else:
            m = _RE_DMY.match(v)
            if not m:
                return None
            p, s, y, hora = (m.group(1), m.group(2), m.group(3), m.group(4))
            d, mo = (p, s) if orden == "dia" else (s, p)
            if len(y) == 2:
                y = ("20" if int(y) < 70 else "19") + y
        fecha = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        return f"{fecha}T{hora}" if hora else fecha
    if tipo == "boolean":
        return v.lower() in ("true", "si", "sí", "verdadero", "1")
    return v


def retipar_con_todo(tabla: dict) -> None:
    """Re-infiere los tipos con TODAS las filas, no con la muestra.

    Los tipos se deciden sobre las primeras `_MUESTRA` filas porque eso
    mantiene la carga instantánea. Pero al empotrar se guardan hasta
    50.000, y un valor que traiciona a la muestra —una columna entera en
    las primeras 500 filas y un `s/d` en la 551— se convertiría a `null` y
    la celda DESAPARECERÍA del archivo sin dejar rastro. Con los datos ya
    en memoria no hay excusa para adivinar: se retipa con la columna
    entera y la columna se ensancha (a texto) si hace falta.

    Muta `tabla["columnas"]` en el lugar, porque el tipo del TMSL y el de
    la conversión en M tienen que ser el mismo.
    """
    datos = tabla.get("datos")
    if not datos:
        return
    for i, c in enumerate(tabla["columnas"]):
        valores = [f[i] for f in datos if i < len(f)]
        real = _tipo_de(valores)
        if real != c["tipo"]:
            # Solo se ensancha: la muestra dijo «entero» y la columna
            # entera dice «texto» → texto gana. Nunca al revés.
            c["tipo"] = real


def _filas_embebidas(tabla: dict) -> tuple[list[list], list[str]]:
    """Las filas normalizadas, y las columnas de fecha que hubo que adivinar."""
    ordenes, ambiguas = [], []
    for i, c in enumerate(tabla["columnas"]):
        if c["tipo"] != "dateTime":
            ordenes.append("dia")
            continue
        orden, adivinado = _orden_fecha([f[i] for f in tabla.get("datos", [])
                                         if i < len(f)])
        ordenes.append(orden)
        if adivinado:
            ambiguas.append(c["nombre"])
    salida = []
    for f in tabla.get("datos", []):
        salida.append([
            _valor_embebido(f[i] if i < len(f) else "", c["tipo"], ordenes[i])
            for i, c in enumerate(tabla["columnas"])])
    return salida, ambiguas


def cabe_embebido(tabla: dict) -> bool:
    """Si los datos de esta tabla entran dentro del archivo sin volverlo
    impracticable. Sin `datos` (una tabla que vino de un DDL SQL, que no
    trae filas) la respuesta es no: no hay nada que empotrar.

    Una tabla con `datos` VACÍOS sí se empotra: un CSV que solo tiene
    encabezado da una tabla vacía, y una tabla vacía adentro del archivo es
    mejor que una ruta rota que hace fallar el refresco y se lleva puesto
    el modelo entero.
    """
    datos = tabla.get("datos")
    if datos is None:
        return False
    celdas = len(datos) * max(len(tabla["columnas"]), 1)
    return (len(datos) <= _MAX_FILAS_EMBEBIDAS
            and celdas <= _MAX_CELDAS_EMBEBIDAS)


def m_embebido(columnas: list[str], filas: list[list],
               tipos: dict[str, str] | None = None) -> list[str]:
    """Una consulta M con LOS DATOS ADENTRO, sin ningún archivo externo.

    Es el mismo formato que escribe Power BI Desktop cuando usás
    «Introducir datos»: el contenido va como JSON comprimido en base64 y
    `Table.FromRows` lo reconstruye. Sirve para una demo que tiene que
    abrir en cualquier máquina —sin copiar planillas, sin ajustar rutas,
    sin que el refresco falle— que es la única forma de que una demo sea
    una demo y no una lista de requisitos.

    El deflate va CRUDO (sin cabecera zlib ni checksum): es lo que espera
    `Binary.Decompress(..., Compression.Deflate)`. Con la cabecera puesta,
    Power BI no puede descomprimirlo y la tabla queda vacía.
    """
    import base64
    import zlib

    crudo = json.dumps(filas, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
    comprimido = zlib.compress(crudo, 9)[2:-4]
    texto = base64.b64encode(comprimido).decode("ascii")
    # Se parte en trozos: una sola línea de cientos de miles de caracteres
    # es ilegible en el editor de Power Query y algunos editores la cortan.
    trozos = [texto[i:i + 500] for i in range(0, len(texto), 500)]
    # Con SALTO DE LÍNEA, no solo con `&`: el objetivo es que el editor de
    # Power Query pueda mostrar la consulta. Unir 700 trozos en un único
    # renglón de 340.000 caracteres no partía nada.
    literal = (" &\n        ".join(f'"{t}"' for t in trozos)
               if trozos else '""')
    nombres = ", ".join(_m_texto(c) for c in columnas)
    lineas = [
        "let",
        f"    Origen = Table.FromRows ( Json.Document ( Binary.Decompress ("
        f" Binary.FromText ( {literal}, BinaryEncoding.Base64 ),"
        " Compression.Deflate ) ),",
        f"        {{{nombres}}} )",
    ]
    if tipos:
        pares = ", ".join("{" + _m_texto(c) + ", " + _TIPO_M[t] + "}"
                          for c, t in tipos.items() if t in _TIPO_M)
        if pares:
            lineas[-1] += ","
            lineas.append(f"    Tipos = Table.TransformColumnTypes ( Origen,"
                          f" {{{pares}}}, {_m_texto(_CULTURA_EMBEBIDA)} )")
            lineas += ["in", "    Tipos"]
            return lineas
    lineas += ["in", "    Origen"]
    return lineas


_RE_B64_EMBEBIDO = re.compile(
    r"Binary\.FromText\s*\(\s*(.*?)\s*,\s*BinaryEncoding\.Base64", re.S)
_RE_COLS_EMBEBIDO = re.compile(r"Compression\.Deflate \) \),\s*\{([^}]*)\}",
                               re.S)


def filas_embebidas(tabla: dict) -> tuple[list[str], list[list]] | None:
    """Las FILAS que viajan adentro del modelo, de vuelta a Python.

    Es la inversa de `m_embebido`. Sirve para que el informe pueda medir
    de verdad —contar huérfanos, sumar columnas, armar un Pareto— sobre
    un `.pbit` autocontenido, sin pedirle al usuario el Excel de origen
    que quizá ya no tenga.

    Devuelve `None` cuando la tabla no lleva datos adentro. Nunca
    adivina: si el base64 no descomprime o el JSON no es una lista de
    listas, es `None` y el informe dice que no pudo medir.
    """
    import base64
    import zlib

    for p in tabla.get("partitions", []):
        fuente = p.get("source", {})
        if fuente.get("type") != "m":
            continue
        expr = fuente.get("expression")
        texto = "\n".join(expr) if isinstance(expr, list) else str(expr or "")
        m = _RE_B64_EMBEBIDO.search(texto)
        mc = _RE_COLS_EMBEBIDO.search(texto)
        if not (m and mc):
            continue
        b64 = "".join(re.findall(r'"([^"]*)"', m.group(1)))
        cols = re.findall(r'"([^"]*)"', mc.group(1))
        try:
            crudo = zlib.decompress(base64.b64decode(b64), -15)
            filas = json.loads(crudo.decode("utf-8"))
        except Exception:                                  # noqa: BLE001
            return None
        if not isinstance(filas, list) or any(not isinstance(f, list)
                                              for f in filas):
            return None
        return cols, filas
    return None


def datos_del_modelo(modelo: dict) -> dict[str, tuple[list[str], list[list]]]:
    """`{tabla: (columnas, filas)}` de todo lo que viaja adentro del modelo."""
    salida = {}
    for t in modelo.get("model", {}).get("tables", []):
        leido = filas_embebidas(t)
        if leido:
            salida[t.get("name", "")] = leido
    return salida


def datos_de_meta(meta: dict | None) -> dict[str, tuple[list[str],
                                                        list[list]]]:
    """Lo mismo, pero desde la materia prima del dataset crudo.

    Un modelo recién propuesto todavía NO lleva las filas adentro —eso
    pasa recién al exportar—, así que todo lo que necesita datos para
    decidir (la ruta de la entidad, por ejemplo) miraba un modelo vacío y
    concluía que no había nada que hacer. Las filas están: están acá.
    """
    salida: dict[str, tuple[list[str], list[list]]] = {}
    for t in (meta or {}).get("tablas", []) or []:
        filas = t.get("datos") or []
        if not filas:
            continue
        salida[t.get("nombre", "")] = (
            [c["nombre"] for c in t.get("columnas", [])], filas)
    return salida


def _m_de(tabla: dict, embebido: bool = False) -> list[str]:
    if embebido and cabe_embebido(tabla):
        filas, _ambiguas = _filas_embebidas(tabla)
        return m_embebido([c["nombre"] for c in tabla["columnas"]], filas,
                          {c["nombre"]: c["tipo"] for c in tabla["columnas"]})
    if tabla["origen"] == "csv":
        sep = tabla.get("sep", ",")
        return [
            "let",
            (f"    Origen = Csv.Document(File.Contents("
             f"{_m_texto(_carpeta_de(tabla) + tabla['archivo'])}), "
             f"[Delimiter={_m_texto(sep)}, Encoding=65001]),"),
            "    Encabezados = Table.PromoteHeaders(Origen, "
            "[PromoteAllScalars=true]),",
            _m_tipos(tabla, "Encabezados"),
            "in",
            "    Tipos",
        ]
    if tabla["origen"] == "xlsx":
        return [
            "let",
            (f"    Origen = Excel.Workbook(File.Contents("
             f"{_m_texto(_carpeta_de(tabla) + tabla['archivo'])}), true)"
             f"{{[Item={_m_texto(tabla.get('hoja', tabla['nombre']))}, "
             f"Kind=\"Sheet\"]}}[Data],"),
            _m_tipos(tabla, "Origen"),
            "in",
            "    Tipos",
        ]
    return [  # sql
        "let",
        ('    Origen = Sql.Database("SERVIDOR", "BASE", '
         "[CreateNavigationProperties=false]),"),
        (f"    Tabla = Origen{{[Schema=\"dbo\", "
         f"Item={_m_texto(tabla['nombre'])}]}}[Data]"),
        "in",
        "    Tabla",
    ]


# ==========================================================================
# La propuesta de modelo
# ==========================================================================
def _valores_de(tabla: dict, columna: str) -> set[str]:
    """Los valores distintos de una columna en la muestra leída."""
    indice = next((i for i, c in enumerate(tabla["columnas"])
                   if _norm(c["nombre"]) == _norm(columna)), -1)
    if indice < 0:
        return set()
    return {f[indice].strip() for f in tabla.get("datos") or []
            if indice < len(f) and f[indice].strip()}


def _encajan(muchos: dict, col_m: str, uno: dict, col_u: str) -> bool | None:
    """¿Los valores del lado «muchos» están dentro del lado «uno»?

    `None` cuando no hay datos para decidir. Es la evidencia real de que
    dos columnas son la misma cosa: dos tablas pueden tener una columna
    `Producto` que no tenga nada que ver entre sí, y dos columnas pueden
    ser la misma clave sin que ninguna se llame `id`. Los nombres son una
    pista; los valores son la prueba.

    Se pide 90% y no 100% a propósito: en datos de verdad siempre hay un
    puñado de códigos huérfanos, y descartar la relación entera por eso
    dejaba el modelo sin relaciones —que es mucho peor que una relación
    con unas filas en blanco, y además es lo que Power BI mismo hace.
    """
    izq, der = _valores_de(muchos, col_m), _valores_de(uno, col_u)
    if not izq or not der:
        return None
    return len(izq & der) / len(izq) >= 0.9


# La palabra que marca «esto es una clave» al principio o al final del
# nombre: `MedicoID`, `id_producto`, `CodCliente`, `ClienteKey`.
_RE_RAIZ_CLAVE = re.compile(
    r"^(?:id|cod|codigo|code|clave|key|sku|nro|num|fk)[ _-]?(?=.)"
    r"|[ _-]?(?:id|cod|codigo|code|clave|key|sku|nro|num|fk)$")


def _singular(palabra: str) -> str:
    """`productos` → `producto`. Sin diccionario: solo la `s` final."""
    if len(palabra) > 3 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 2 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def _raiz_de_clave(nombre: str) -> str:
    """A qué tabla apunta un nombre de clave foránea.

    `MedicoID` → `medico` · `ID_Producto` → `producto` · `ID` → `` (la
    clave propia de la tabla, que no apunta a ninguna otra).
    """
    return _singular(_RE_RAIZ_CLAVE.sub("", _norm(nombre)))


def _misma_entidad(nombre_col: str, nombre_tabla: str) -> bool:
    return bool(nombre_col) and nombre_col == _singular(_norm(nombre_tabla))


def _clave_de(tabla: dict) -> dict | None:
    """La columna que identifica una fila de esta tabla, si la hay.

    Tiene que ser única en la muestra y llamarse como una clave: `ID`,
    `MedicoID`, `Codigo`. Con varias candidatas gana la más específica —
    la que nombra a la propia tabla— y después el `ID` pelado.
    """
    candidatas = [c for c in tabla["columnas"]
                  if c.get("unica") and _es_clave(c["nombre"])]
    if not candidatas:
        return None
    propias = [c for c in candidatas
               if _misma_entidad(_raiz_de_clave(c["nombre"]),
                                 tabla["nombre"])]
    if propias:
        return propias[0]
    peladas = [c for c in candidatas if not _raiz_de_clave(c["nombre"])]
    return peladas[0] if peladas else candidatas[0]


def _pares_candidatos(a: dict, b: dict) -> tuple[list[tuple], list[str]]:
    """Los pares de columnas que PODRÍAN ser la misma clave, y en qué
    sentido: `[(muchos, col_muchos, uno, col_uno), ...]` más las parejas
    ambiguas, que no se proponen y se informan.

    Tres formas, en orden de evidencia:

    1. **El mismo nombre** en las dos tablas (`Ventas[Producto]` ↔
       `Productos[Producto]`).
    2. **La convención `<Tabla>ID`**: `Visitas[MedicoID]` → `Medico[ID]`.
       Es la forma más común que existe en un dataset real y no la veía
       nadie, porque los nombres NO coinciden: el modelo salía con cero
       relaciones y cada visual filtraba solo su propia tabla.
    3. **La fecha contra el calendario**: una columna de fecha del hecho
       contra la columna de fecha ÚNICA de la tabla de calendario. Que
       dos tablas compartan una fecha no relacionada sigue sin ser una
       relación —eso es la señal de que falta el calendario—, pero
       cuando uno de los dos lados es el calendario, esa relación es
       justamente la que hace andar la inteligencia de tiempo.
    """
    pares: list[tuple] = []
    ambiguas: list[str] = []
    for ca in a["columnas"]:
        for cb in b["columnas"]:
            if ca["tipo"] != cb["tipo"]:
                continue
            na, nb = ca["nombre"], cb["nombre"]
            if _norm(na) == _norm(nb):
                if ca.get("unica") and not cb.get("unica"):
                    pares.append((b, nb, a, na))
                elif cb.get("unica") and not ca.get("unica"):
                    pares.append((a, na, b, nb))
                elif ca.get("unica") and cb.get("unica"):
                    # Únicas de los dos lados: la dimensión suele ser la
                    # tabla más chica, pero con igual tamaño no se adivina.
                    if a["filas"] and b["filas"] and a["filas"] != b["filas"]:
                        uno = a if a["filas"] < b["filas"] else b
                        muchos = b if uno is a else a
                        pares.append((muchos, na if muchos is a else nb,
                                      uno, na if uno is a else nb))
                    elif ca["tipo"] != "dateTime":
                        ambiguas.append(f"{a['nombre']}[{na}] ↔ "
                                        f"{b['nombre']}[{nb}]")
                continue
            if ca["tipo"] == "dateTime":
                # Fechas con distinto nombre: solo contra el calendario,
                # que es el lado con la fecha única.
                if ca.get("unica") and not cb.get("unica"):
                    pares.append((b, nb, a, na))
                elif cb.get("unica") and not ca.get("unica"):
                    pares.append((a, na, b, nb))
                continue
            # `<Tabla>ID` → la clave de esa tabla.
            if _misma_entidad(_raiz_de_clave(na), b["nombre"]) \
                    and not ca.get("unica"):
                clave = _clave_de(b)
                if clave and _norm(clave["nombre"]) == _norm(nb):
                    pares.append((a, na, b, nb))
            if _misma_entidad(_raiz_de_clave(nb), a["nombre"]) \
                    and not cb.get("unica"):
                clave = _clave_de(a)
                if clave and _norm(clave["nombre"]) == _norm(na):
                    pares.append((b, nb, a, na))
    return pares, ambiguas


def _inferir_relaciones(tablas: list[dict],
                        declaradas: list[dict]) -> tuple[list[dict],
                                                         list[str]]:
    """Relaciones por nombre de columna coincidente, con el lado «uno» en
    la columna que la muestra dice única. Lo ambiguo no se propone: se
    devuelve como nota.

    El nombre de la columna abre la puerta, pero no alcanza: cuando las
    dos tablas traen datos, la relación se propone solo si los valores
    del lado «muchos» están de verdad en el lado «uno». Eso es lo que
    permite aflojar el filtro de nombres —antes una columna tenía que
    llamarse `id`/`codigo`/`sku` para siquiera ser considerada, así que
    `Ventas[Producto] → Productos[Producto]`, que es la relación más
    común que existe, no se detectaba y el modelo salía suelto.
    """
    vistas = {(_norm(r["desde_tabla"]), _norm(r["desde_col"]),
               _norm(r["hacia_tabla"])) for r in declaradas}
    relaciones = list(declaradas)
    ambiguas: list[str] = []
    # Un par de tablas se relaciona UNA vez: dos relaciones activas entre
    # las mismas dos tablas no las acepta Power BI, y con `MedicoID` y
    # `Fecha` compartidos aparecen dos candidatas sin ningún problema.
    pares_usados: set[tuple[str, str]] = set()
    for i, a in enumerate(tablas):
        for b in tablas[i + 1:]:
            candidatos, ambiguos = _pares_candidatos(a, b)
            ambiguas += ambiguos
            for muchos, col_m, uno, col_u in candidatos:
                par = tuple(sorted([_norm(muchos["nombre"]),
                                    _norm(uno["nombre"])]))
                if par in pares_usados:
                    continue
                # La prueba: los valores del lado «muchos» tienen que estar
                # en el lado «uno». Sin datos para comprobarlo se vuelve al
                # criterio viejo —el nombre— en vez de proponer a ciegas.
                encaje = _encajan(muchos, col_m, uno, col_u)
                if encaje is False:
                    continue
                if encaje is None and not _es_clave(col_m):
                    continue
                clave = (_norm(muchos["nombre"]), _norm(col_m),
                         _norm(uno["nombre"]))
                if clave in vistas:
                    continue
                vistas.add(clave)
                pares_usados.add(par)
                relaciones.append({
                    "desde_tabla": muchos["nombre"], "desde_col": col_m,
                    "hacia_tabla": uno["nombre"], "hacia_col": col_u})
    return relaciones, ambiguas


# Funciones de M que salen a buscar algo AFUERA del archivo. Si una
# consulta usa cualquiera de estas, ese Actualizar puede fallar — y en Power
# BI una sola consulta que falla se lleva puesto el modelo entero.
_M_EXTERNO = ("File.Contents", "Excel.Workbook", "Csv.Document",
              "Sql.Database", "Web.Contents", "Folder.Files",
              "SharePoint.", "OData.Feed", "Odbc.")


def depende_de_afuera(expresion) -> bool:
    """Si esta consulta M necesita un archivo, una base o una URL."""
    texto = "\n".join(expresion) if isinstance(expresion, list) \
        else str(expresion or "")
    return any(f in texto for f in _M_EXTERNO)


def _reporte_embebido(tablas: list[dict], idioma: str) -> list[str]:
    """Qué entró, qué NO, y por qué — sin prometer de más.

    La promesa «abre sin refrescar» solo se puede hacer si NINGUNA tabla
    quedó apuntando afuera: alcanza una consulta que falle para que Power
    BI descarte el modelo entero, así que un archivo con seis tablas
    adentro y una tabla SQL colgando abre igual de roto que antes.
    """
    notas: list[str] = []
    dentro = [t for t in tablas if cabe_embebido(t)]
    afuera = [t for t in tablas if not cabe_embebido(t)]
    ambiguas: list[str] = []
    for t in dentro:
        _filas, amb = _filas_embebidas(t)
        ambiguas += [f"{t['nombre']}[{c}]" for c in amb]
    if dentro:
        notas.append(traducir(
            "ds_embebido" if not afuera else "ds_embebido_parcial",
            idioma).format(
                tablas=len(dentro),
                filas=sum(len(t.get("datos") or []) for t in dentro)))
    for t in afuera:
        if t.get("datos") is None:
            # Una tabla de DDL SQL: no hay filas que empotrar. Antes esto
            # se salteaba sin decir nada, debajo de un cartel que afirmaba
            # que el archivo no necesitaba refrescar.
            notas.append(traducir("ds_no_embebido_sin_filas", idioma).format(
                tabla=t["nombre"]))
        else:
            notas.append(traducir("ds_no_embebido", idioma).format(
                tabla=t["nombre"],
                # El conteo REAL, no el de `datos`, que viene topeado: decir
                # «tiene 50001 filas» de un archivo de 200.000 es mentira.
                filas=t.get("filas") or len(t["datos"]),
                columnas=len(t["columnas"]),
                maximo=_MAX_FILAS_EMBEBIDAS,
                maximo_celdas=_MAX_CELDAS_EMBEBIDAS))
    if ambiguas:
        notas.append(traducir("ds_fecha_ambigua", idioma).format(
            columnas=" · ".join(ambiguas[:6])))
    return notas


def _proponer(tablas: list[dict], declaradas: list[dict],
              nombre: str, idioma: str,
              embebido: bool = False) -> tuple[dict, list[str]]:
    relaciones, ambiguas = _inferir_relaciones(tablas, declaradas)
    notas: list[str] = []
    tmsl_tablas = []
    if embebido:
        for t in tablas:
            retipar_con_todo(t)
    afuera = [t for t in tablas if not cabe_embebido(t)] if embebido else []
    for t in tablas:
        columnas = []
        for c in t["columnas"]:
            col = {"name": c["nombre"], "dataType": c["tipo"],
                   "sourceColumn": c["nombre"]}
            if _es_clave(c["nombre"]):
                col["summarizeBy"] = "none"
            columnas.append(col)
        tmsl_tablas.append({
            "name": t["nombre"],
            "columns": columnas,
            "partitions": [{"name": t["nombre"], "mode": "import",
                            "source": {"type": "m",
                                       "expression": _m_de(t, embebido)}}],
        })
        notas.append(traducir("ds_tabla", idioma).format(
            tabla=t["nombre"], cols=len(t["columnas"]),
            archivo=t["archivo"]))
    tmsl_rel = []
    existentes = {_norm(t["nombre"]) for t in tablas}
    for i, r in enumerate(relaciones):
        if not {_norm(r["desde_tabla"]), _norm(r["hacia_tabla"])} <= \
                existentes:
            continue
        tmsl_rel.append({
            "name": f"rel_{i}",
            "fromTable": r["desde_tabla"], "fromColumn": r["desde_col"],
            "toTable": r["hacia_tabla"], "toColumn": r["hacia_col"]})
        notas.append(traducir("ds_relacion", idioma).format(
            desde=f"{r['desde_tabla']}[{r['desde_col']}]",
            hacia=f"{r['hacia_tabla']}[{r['hacia_col']}]"))
    for amb in ambiguas:
        notas.append(traducir("ds_rel_ambigua", idioma).format(par=amb))

    # Las notas de ruta/servidor solo aplican a lo que quedó apuntando a un
    # archivo o a una base: una tabla empotrada no tiene ruta que ajustar.
    externas = afuera if embebido else tablas
    origenes = {t["origen"] for t in externas}
    if origenes & {"csv", "xlsx"}:
        notas.append(traducir("ds_ruta_m", idioma))
    if "sql" in origenes:
        notas.append(traducir("ds_sql_conexion", idioma))
    if embebido:
        notas += _reporte_embebido(tablas, idioma)

    modelo = {
        "name": nombre,
        # El nivel que Desktop escribe en archivos reales (2026.08). No es
        # arbitrario: `modelo.preparar_para_desktop` le suma acá encima
        # `defaultPowerBIDataSourceVersion = powerBI_V3` al exportar, y esa
        # bandera con un nivel más viejo hace que Desktop rechace el
        # archivo entero como corrupto — no es solo cosmética.
        "compatibilityLevel": 1606,
        "model": {"culture": "es-ES", "tables": tmsl_tablas,
                  "relationships": tmsl_rel},
    }
    return modelo, notas


# ==========================================================================
# API pública — misma forma que `modelo.cargar`
# ==========================================================================
def cargar(ruta: str | Path, idioma: str = IDIOMA_DEFECTO,
           embebido: bool = False) -> dict:
    return cargar_varios([ruta], idioma, embebido)


def cargar_varios(rutas: list[str | Path],
                  idioma: str = IDIOMA_DEFECTO,
                  embebido: bool = False) -> dict:
    """Varios archivos crudos (CSV/XLSX/SQL) → UN modelo propuesto.

    Devuelve el mismo dict que `modelo.cargar`, con dos claves extra:
    `notas` (qué se infirió y qué falta, para decirlo en pantalla) y
    `dataset_meta` (la materia prima, para que `modelo.combinar` pueda
    re-proponer el modelo si llegan más archivos crudos).
    """
    tablas: list[dict] = []
    declaradas: list[dict] = []
    advertencias: list[str] = []
    for ruta in rutas:
        ruta = Path(ruta)
        sufijo = ruta.suffix.lower()
        try:
            if sufijo == ".csv":
                tablas.append(_leer_csv(ruta))
            elif sufijo == ".xlsx":
                tablas.extend(_leer_xlsx(ruta))
            elif sufijo == ".sql":
                t, r = _leer_sql(ruta.read_text(encoding="utf-8",
                                                errors="replace"),
                                 ruta.name)
                tablas.extend(t)
                declaradas.extend(r)
            else:
                raise ValueError(ruta.name)
        except (ValueError, OSError, zipfile.BadZipFile, ET.ParseError,
                KeyError, IndexError):
            advertencias.append(
                traducir("ds_no_leido", idioma).format(archivo=ruta.name))
    if not tablas:
        raise ValueError(traducir("ds_vacio", idioma))

    # Dos hojas o archivos con el mismo nombre de tabla: se numeran, porque
    # un modelo tabular no admite tablas homónimas.
    vistos: dict[str, int] = {}
    for t in tablas:
        clave = _norm(t["nombre"])
        vistos[clave] = vistos.get(clave, 0) + 1
        if vistos[clave] > 1:
            t["nombre"] = f"{t['nombre']} ({vistos[clave]})"

    nombre = Path(rutas[0]).stem if len(rutas) == 1 else "Dataset"
    modelo, notas = _proponer(tablas, declaradas, nombre, idioma, embebido)
    return {
        "formato": "dataset",
        "modelo": modelo,
        "layout": None,
        "advertencias": advertencias,
        "origen": " + ".join(Path(r).name for r in rutas),
        "notas": notas,
        "dataset_meta": {"tablas": tablas, "declaradas": declaradas},
    }


def puede_empotrar(modelo: dict, meta: dict | None) -> list[str]:
    """Los nombres de tabla del modelo cuyos datos se pueden meter adentro
    del archivo. Lista vacía = no hay nada para empotrar (el modelo no vino
    de datos crudos, o las tablas son demasiado grandes)."""
    if not meta:
        return []
    presentes = {t.get("name") for t in
                 modelo.get("model", {}).get("tables", [])}
    return [t["nombre"] for t in meta.get("tablas", [])
            if t["nombre"] in presentes and cabe_embebido(t)]


def empotrar(modelo: dict, meta: dict | None,
             idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Reescribe las particiones del modelo con los datos ADENTRO.

    Se hace al exportar y no al cargar porque es una decisión sobre el
    archivo que se entrega, no sobre la lectura: el mismo modelo sirve para
    un .pbit que refresca contra la base del cliente y para una demo que
    abre sola en cualquier máquina.

    Lo que NO entra se nombra, una por una: tablas demasiado grandes,
    tablas que vinieron de un DDL sin filas, y también las tablas del
    modelo que no salieron de datos crudos y siguen apuntando a un archivo
    o a una base. Eso último importa porque la promesa «abre sin
    refrescar» es todo o nada: una sola consulta que falla hace que Power
    BI descarte el modelo ENTERO.

    Devuelve `(modelo_nuevo, notas)` sin tocar el modelo recibido.
    """
    import copy
    nuevo = copy.deepcopy(modelo)
    notas: list[str] = []
    if not meta:
        return nuevo, notas
    por_nombre = {t["nombre"]: t for t in meta.get("tablas", [])}
    crudas = [t for t in meta.get("tablas", [])
              if t["nombre"] in {x.get("name") for x
                                 in nuevo.get("model", {}).get("tables", [])}]
    for t in crudas:
        if cabe_embebido(t):
            retipar_con_todo(t)
    empotradas = 0
    for tabla in nuevo.get("model", {}).get("tables", []):
        cruda = por_nombre.get(tabla.get("name"))
        if cruda is None or not cabe_embebido(cruda):
            continue
        for i, c in enumerate(tabla.get("columns", [])):
            # El tipo del TMSL sigue al que se retipó con la columna
            # entera: si se quedan distintos, la conversión de M carga un
            # texto en una columna declarada entera y la fila se rompe.
            if i < len(cruda["columnas"]):
                c["dataType"] = cruda["columnas"][i]["tipo"]
        for particion in tabla.get("partitions", []):
            origen = particion.get("source", {})
            if origen.get("type") != "m":
                continue
            # Los pasos que el preparado le agregó a esta consulta —el
            # trimestre, el semestre y sus columnas de orden— tienen que
            # SOBREVIVIR: reescribir desde la materia prima los borraba,
            # y el archivo quedaba declarando columnas que la consulta ya
            # no producía.
            from .periodos import pasos_envueltos, reenvolver
            pasos = pasos_envueltos(origen.get("expression"))
            origen["expression"] = _m_de(cruda, embebido=True)
            reenvolver(particion, pasos, tabla.get("name", ""))
        empotradas += 1
    notas += _reporte_embebido(crudas, idioma)
    # Y las tablas que el empotrado no pudo tocar y siguen saliendo a
    # buscar algo afuera: un .pbix cargado junto al CSV, una consulta que
    # el usuario escribió a mano.
    colgadas = sorted({
        t.get("name") for t in nuevo.get("model", {}).get("tables", [])
        if t.get("name") not in por_nombre
        and any(depende_de_afuera(pa.get("source", {}).get("expression"))
                for pa in t.get("partitions", []))})
    if colgadas:
        notas.append(traducir("ds_afuera_igual", idioma).format(
            n=len(colgadas), lista=" · ".join(colgadas[:6])))
    if not empotradas and not notas:
        notas.append(traducir("ds_nada_que_empotrar", idioma))
    return nuevo, notas


def fusionar(cargados: list[dict], idioma: str = IDIOMA_DEFECTO,
             embebido: bool = False) -> dict:
    """Funde varios `cargado` de formato dataset en uno, re-infiriendo las
    relaciones sobre el conjunto completo (con la materia prima guardada,
    no sobre el modelo ya cocinado)."""
    tablas: list[dict] = []
    declaradas: list[dict] = []
    advertencias: list[str] = []
    for c in cargados:
        meta = c.get("dataset_meta") or {}
        tablas.extend(meta.get("tablas", []))
        declaradas.extend(meta.get("declaradas", []))
        advertencias.extend(c.get("advertencias", []))
    modelo, notas = _proponer(tablas, declaradas, "Dataset", idioma,
                              embebido)
    return {
        "formato": "dataset",
        "modelo": modelo,
        "layout": None,
        "advertencias": advertencias,
        "origen": " + ".join(str(c.get("origen", "")) for c in cargados),
        "notas": notas,
        "dataset_meta": {"tablas": tablas, "declaradas": declaradas},
    }
