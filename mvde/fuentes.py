# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 1 · Fuentes: cualquier origen a un DataFrame, con procedencia.

Tipos: csv, excel, parquet, json, sqlite, sql (URL SQLAlchemy, sólo lectura),
url (http/https), carpeta (varios archivos del mismo esquema), kaggle (CLI
oficial) y duckdb. Rutas s3:// gs:// az:// abfs:// funcionan con
`opciones.storage_options` si está instalado el fsspec correspondiente.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import sqlite3
import subprocess
import urllib.request
from pathlib import Path

import pandas as pd

from . import confidencial

# Segunda red, y a propósito CORTA. La primera red (empezar por SELECT/WITH y
# una sola sentencia) ya deja afuera casi todo; esto atrapa lo que todavía
# puede escribir DENTRO de una única sentencia de lectura — sobre todo
# `SELECT ... INTO tabla`, que crea una tabla, y `FOR UPDATE`, que toma
# bloqueos en la base de producción del cliente.
#
# Deliberadamente NO están `replace`, `set`, `copy`, `call` ni `analyze`:
# `SELECT REPLACE(nombre,'a','b')` es una función de texto perfectamente
# legítima, y una lista negra que rechaza consultas buenas es una lista negra
# que alguien va a terminar apagando.
_ESCRITURA = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|merge"
    r"|exec|execute|grant|revoke|into)\b", re.I)
_ARRANQUE_LECTURA = re.compile(r"^\(*\s*(select|with)\b", re.I)
_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_NUBE = ("s3://", "gs://", "gcs://", "az://", "abfs://", "abfss://", "adl://")


class FuenteError(RuntimeError):
    pass


# ---------------------------------------------------------------- sólo lectura
def _sin_literales_ni_comentarios(sql: str) -> str:
    """Reemplaza literales de texto y comentarios por un espacio.

    Hay que hacerlo ANTES de buscar `;` o palabras de escritura: un
    `SELECT 'texto; con punto y coma'` es perfectamente legítimo, y un
    `WHERE nota = 'update ya'` también. Sin este paso, la validación
    rechaza consultas buenas — que es la forma en que un control de
    seguridad se termina apagando.
    """
    fuera, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c in ("'", '"', "`"):                       # literal o identificador citado
            cierre, i = c, i + 1
            while i < n:
                if sql[i] == cierre:
                    if i + 1 < n and sql[i + 1] == cierre:   # '' escapado adentro
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            fuera.append(" ")
            continue
        if c == "-" and sql.startswith("--", i):       # comentario de línea
            j = sql.find("\n", i)
            i = n if j < 0 else j
            fuera.append(" ")
            continue
        if c == "/" and sql.startswith("/*", i):       # comentario de bloque
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
            fuera.append(" ")
            continue
        fuera.append(c)
        i += 1
    return "".join(fuera)


def es_solo_lectura(consulta: str) -> bool:
    """Si la consulta se puede ejecutar contra la base de un cliente.

    Lista BLANCA, no negra: tiene que empezar por SELECT o WITH. Y no puede
    traer una segunda sentencia — antes de esto, `SELECT 1; DROP TABLE x`
    pasaba, porque la validación sólo miraba el arranque.
    """
    if not (consulta or "").strip():
        return False
    limpia = _sin_literales_ni_comentarios(consulta).strip()
    if not limpia:
        return False
    if not _ARRANQUE_LECTURA.match(limpia):
        return False
    # Un `;` final (o varios, con espacios) es válido; cualquier cosa
    # DESPUÉS de un `;` es una segunda sentencia.
    cuerpo, _, resto = limpia.partition(";")
    if resto.replace(";", "").strip():
        return False
    return not _ESCRITURA.search(cuerpo)


def exigir_solo_lectura(consulta: str, nombre: str) -> None:
    """Corta la etapa nombrando la fuente, para saber cuál del YAML revisar."""
    if es_solo_lectura(consulta):
        return
    raise FuenteError(
        f"fuente «{nombre}»: la consulta no es de sólo lectura. Se admite UNA sentencia "
        "que empiece con SELECT o WITH, sin una segunda sentencia después del punto y coma. "
        "Este producto no escribe en la base del cliente."
    )


def expandir_entorno(texto: str, nombre: str) -> str:
    """Expande `${VARIABLE}` con el entorno. Falla CERRADO si falta.

    La regla del proyecto es que la credencial va por entorno y nunca en el
    YAML versionado — pero sin esta función la única forma de conectarse era
    escribir la contraseña en el YAML. Y si la variable no está, se corta con
    el nombre a la vista en vez de armar una URL con la contraseña vacía: ese
    modo de falla silencioso ya se pagó una vez con el hash que la
    interpolación del `.env` cortaba por la mitad.
    """
    faltan = [v for v in _VARIABLE.findall(texto or "") if os.environ.get(v) is None]
    if faltan:
        raise FuenteError(
            f"fuente «{nombre}»: la variable de entorno {', '.join(faltan)} no está definida. "
            "Definila en el despliegue; la credencial no va en el YAML."
        )
    return _VARIABLE.sub(lambda m: os.environ[m.group(1)], texto or "")


def _sin_credencial(url: str) -> str:
    """Para mensajes de error: `postgresql://u:clave@host/db` → `postgresql://u:***@host/db`."""
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", url or "")


def _ruta(fuente: dict, base: str) -> str:
    ruta = str(fuente.get("ruta", ""))
    if not ruta:
        raise FuenteError(f"fuente «{fuente['nombre']}» sin `ruta`")
    if ruta.startswith(_NUBE) or ruta.startswith(("http://", "https://")):
        # Único punto por donde pasan TODAS las rutas del YAML, así que acá se
        # atrapa también el caso que se escapa de `_leer_url`: una fuente
        # declarada `tipo: csv` cuya `ruta` es un http:// o un s3://.
        que = "leer una ruta de nube" if confidencial.es_ruta_de_nube(ruta) else "leer una ruta remota"
        confidencial.exigir_local(que, ruta)
        return ruta
    p = Path(ruta)
    return str(p if p.is_absolute() else Path(base) / p)


def _opciones(fuente: dict) -> dict:
    return dict(fuente.get("opciones") or {})


def plan_lectura_csv(ruta: str, op: dict) -> dict:
    """Decide con qué opciones se lee un CSV, priorizando el motor en C.

    Antes esto era `sep=None, engine="python"`: detectaba el separador solo,
    pero a costa de usar el motor de Python de pandas. Medido sobre un millón
    de filas: **5,42 s contra 0,67 s** del motor en C — ocho veces, y lo pagaba
    cada lectura de cada corrida.

    La detección se sigue haciendo (el separador de un CSV exportado de Excel en
    español es `;`, y pedirle al usuario que lo declare es una fricción que no
    hace falta), pero acá y sobre la primera línea, para después leer en C.
    Lo que el YAML declara explícito gana siempre.
    """
    plan = dict(op)
    plan.setdefault("encoding", "utf-8-sig")   # el BOM de Excel no se vuelve parte del encabezado
    if "sep" in op or "delimiter" in op:
        return plan                            # lo declaró el YAML: no se toca
    try:
        with open(ruta, encoding=plan["encoding"], errors="replace") as fh:
            muestra = fh.read(64 * 1024)
        primera = next((ln for ln in muestra.splitlines() if ln.strip()), "")
        if not primera:
            raise ValueError("archivo sin líneas")
        # Se elige el candidato que más veces aparece en el encabezado. El
        # Sniffer de csv se confunde con comas dentro de literales; contar sobre
        # la primera línea es más simple y acierta en los casos que importan.
        cand = max((",", ";", "\t", "|"), key=primera.count)
        if primera.count(cand) == 0:
            raise ValueError("un solo campo")
        plan["sep"] = cand
    except (OSError, ValueError, StopIteration):
        # No se pudo detectar: se cae al camino de antes. Perder velocidad es
        # aceptable; no poder leer el archivo, no.
        plan["sep"] = None
        plan["engine"] = "python"
    return plan


def memoria_mb(df: pd.DataFrame) -> float:
    """Lo que ocupa el DataFrame en memoria, contando el texto de verdad."""
    return float(df.memory_usage(deep=True).sum()) / 1024 / 1024


def ram_disponible_mb() -> float | None:
    """MB disponibles según el sistema. `None` si no se puede saber."""
    try:
        for linea in Path("/proc/meminfo").read_text().splitlines():
            if linea.startswith("MemAvailable:"):
                return int(linea.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


# El pico del pipeline es ~2× la tabla, porque `tablas` (bronze) y `silver`
# viven a la vez. Si una sola tabla ya pasa este porcentaje de la RAM
# disponible, la corrida entera está en riesgo y hay que decirlo ANTES.
_UMBRAL_RAM = 0.35


def aviso_de_volumen(nombre: str, df: pd.DataFrame) -> str:
    """Aviso —no corte— cuando la tabla no entra cómoda en esta máquina.

    No corta a propósito: el que decide si sigue es el dueño del proyecto, no
    el motor. Lo que no puede pasar es que se entere con un MemoryError a mitad
    de la etapa gold, sin saber cuál de las tablas lo causó.
    """
    ram = ram_disponible_mb()
    if not ram:
        # Sin dato real no se inventa un aviso: un aviso falso entrena a la
        # gente a ignorar los avisos.
        return ""
    mb = memoria_mb(df)
    if mb < ram * _UMBRAL_RAM:
        return ""
    return (f"la tabla «{nombre}» ocupa {mb:,.0f} MB en memoria y hay {ram:,.0f} MB "
            f"disponibles. El pipeline mantiene bronze y silver a la vez, así que el pico "
            f"es cerca del doble. Medí el techo de esta máquina con "
            f"`python scripts/medir_volumen.py` y, si no alcanza, cargá por partición "
            f"o usá `limite_filas` para probar.")


def _leer_archivo(ruta: str, tipo: str, fuente: dict) -> pd.DataFrame:
    op = _opciones(fuente)
    storage = {"storage_options": op.pop("storage_options")} if "storage_options" in op else {}
    if tipo == "csv":
        plan = plan_lectura_csv(ruta, op)
        limite = fuente.get("limite_filas")
        if limite:
            plan.setdefault("nrows", int(limite))
        return pd.read_csv(ruta, **plan, **storage)
    if tipo == "excel":
        return pd.read_excel(ruta, sheet_name=fuente.get("hoja", 0), **op, **storage)
    if tipo == "parquet":
        return pd.read_parquet(ruta, **op, **storage)
    if tipo == "json":
        return pd.read_json(ruta, **op, **storage)
    raise FuenteError(f"tipo de archivo `{tipo}` no soportado")


def _leer_sqlite(ruta: str, fuente: dict) -> pd.DataFrame:
    if not Path(ruta).exists():
        raise FuenteError(f"no existe {ruta}")
    consulta = fuente.get("consulta") or f'SELECT * FROM "{fuente.get("tabla", fuente["nombre"])}"'
    exigir_solo_lectura(consulta, fuente["nombre"])
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(consulta, con)
    finally:
        con.close()


# Cómo se pide una transacción de sólo lectura en cada motor. Donde el motor
# no lo soporta (SQL Server), la defensa que queda es la validación de la
# consulta más el rollback — y el usuario de base de sólo lectura, que es el
# único control definitivo y lo aplica el cliente, no este programa.
_READ_ONLY_POR_MOTOR = {
    "postgresql": "SET TRANSACTION READ ONLY",
    "mysql": "SET SESSION TRANSACTION READ ONLY",
    "mariadb": "SET SESSION TRANSACTION READ ONLY",
    "oracle": "SET TRANSACTION READ ONLY",
}


def _leer_sql(fuente: dict) -> pd.DataFrame:
    try:
        import sqlalchemy as sa
    except ImportError as exc:
        raise FuenteError("instalá sqlalchemy (+ el driver del motor) para fuentes `sql`") from exc
    url = fuente.get("url")
    if not url:
        raise FuenteError(f"fuente «{fuente['nombre']}» tipo sql sin `url` (SQLAlchemy)")

    # El orden importa: primero se valida la consulta, DESPUÉS se conecta. Una
    # consulta que escribe no tiene que llegar ni a abrir la conexión.
    consulta = fuente.get("consulta") or f"SELECT * FROM {fuente.get('tabla', fuente['nombre'])}"
    exigir_solo_lectura(consulta, fuente["nombre"])
    url = expandir_entorno(str(url), fuente["nombre"])

    try:
        motor = sa.create_engine(url)
    except Exception as exc:                        # noqa: BLE001 - se re-lanza sin credencial
        raise FuenteError(
            f"fuente «{fuente['nombre']}»: no se pudo abrir la conexión "
            f"({_sin_credencial(url)}): {exc}"
        ) from None

    dialecto = (getattr(motor.dialect, "name", "") or "").lower()
    try:
        con = motor.connect()
    except Exception as exc:                        # noqa: BLE001
        # El mensaje de un driver suele traer la URL entera, con la contraseña.
        raise FuenteError(
            f"fuente «{fuente['nombre']}»: no se pudo conectar a "
            f"{_sin_credencial(url)} — {type(exc).__name__}"
        ) from None

    with con:
        trans = con.begin()
        try:
            sentencia = _READ_ONLY_POR_MOTOR.get(dialecto)
            if sentencia:
                con.execute(sa.text(sentencia))
            return pd.read_sql_query(sa.text(consulta), con)
        finally:
            # Siempre se deshace: la lectura no necesita confirmar nada, y si
            # algo escribió por un camino que no previmos, no queda.
            trans.rollback()


def _leer_duckdb(ruta: str, fuente: dict) -> pd.DataFrame:
    import duckdb
    consulta = fuente.get("consulta") or f'SELECT * FROM {fuente.get("tabla", fuente["nombre"])}'
    exigir_solo_lectura(consulta, fuente["nombre"])
    con = duckdb.connect(ruta, read_only=True)
    try:
        return con.execute(consulta).df()
    finally:
        con.close()


def _leer_url(fuente: dict) -> pd.DataFrame:
    url = fuente["ruta"]
    # Una fuente `url` sale de la red del cliente por definición: es el primer
    # lugar donde un YAML copiado de otro proyecto filtra sin que nadie lo note.
    confidencial.exigir_local("leer una fuente por URL", url)
    formato = fuente.get("formato", "csv")
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - URL declarada por el usuario
        datos = r.read()
    buf = io.BytesIO(datos)
    if formato == "csv":
        return pd.read_csv(buf, **_opciones(fuente))
    if formato == "json":
        return pd.read_json(buf)
    if formato == "parquet":
        return pd.read_parquet(buf)
    if formato == "excel":
        return pd.read_excel(buf, sheet_name=fuente.get("hoja", 0))
    raise FuenteError(f"formato `{formato}` no soportado para url")


def _leer_carpeta(ruta: str, fuente: dict) -> pd.DataFrame:
    patron = fuente.get("patron", "*.csv")
    archivos = sorted(Path(ruta).glob(patron))
    if not archivos:
        raise FuenteError(f"la carpeta {ruta} no tiene archivos {patron}")
    tipo = "csv" if patron.endswith("csv") else "parquet" if patron.endswith("parquet") else "excel"
    partes = []
    for a in archivos:
        df = _leer_archivo(str(a), tipo, fuente)
        df["_archivo"] = a.name
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def _leer_kaggle(fuente: dict, base: str) -> pd.DataFrame:
    destino = Path(base) / str(fuente.get("destino", "data/raw"))
    archivo = destino / fuente["archivo"]
    if not archivo.exists():
        # Sólo se bloquea la DESCARGA. Si el archivo ya está en el disco de la
        # VM, leerlo no cruza ningún borde y el modo no tiene por qué impedirlo.
        confidencial.exigir_local("descargar un dataset de Kaggle", str(fuente.get("dataset", "")))
        if shutil.which("kaggle") is None:
            raise FuenteError("falta el CLI de Kaggle (pip install kaggle) y el archivo no está descargado")
        destino.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "datasets", "download", "-d", fuente["dataset"], "-p", str(destino),
                        "--unzip", "--force"], check=True)
    return _leer_archivo(str(archivo), fuente.get("formato", "csv"), fuente)


def leer(fuente: dict, base: str = ".") -> tuple[pd.DataFrame, dict]:
    """Devuelve (DataFrame, procedencia). La procedencia va a bronze y al linaje."""
    tipo = fuente.get("tipo", "csv")
    if tipo in ("csv", "excel", "parquet", "json"):
        ruta = _ruta(fuente, base)
        if not ruta.startswith(_NUBE) and not Path(ruta).exists():
            raise FuenteError(f"fuente «{fuente['nombre']}»: no existe {ruta}")
        df = _leer_archivo(ruta, tipo, fuente)
        origen = ruta
    elif tipo == "sqlite":
        origen = _ruta(fuente, base)
        df = _leer_sqlite(origen, fuente)
    elif tipo == "duckdb":
        origen = _ruta(fuente, base)
        df = _leer_duckdb(origen, fuente)
    elif tipo == "sql":
        df = _leer_sql(fuente)
        origen = re.sub(r"://[^@]*@", "://***@", str(fuente.get("url")))  # sin credenciales
    elif tipo == "url":
        df = _leer_url(fuente)
        origen = fuente["ruta"]
    elif tipo == "carpeta":
        origen = _ruta(fuente, base)
        df = _leer_carpeta(origen, fuente)
    elif tipo == "kaggle":
        df = _leer_kaggle(fuente, base)
        origen = f"kaggle:{fuente['dataset']}/{fuente['archivo']}"
    else:
        raise FuenteError(f"tipo `{tipo}` desconocido")
    if df is None or df.empty:
        raise FuenteError(f"fuente «{fuente['nombre']}» llegó vacía")
    df.columns = [str(c).strip() for c in df.columns]

    # `limite_filas` en tipos que no lo aplican en la lectura (sql, parquet…):
    # se recorta acá para que la opción signifique lo mismo en todas.
    limite = fuente.get("limite_filas")
    if limite and len(df) > int(limite):
        df = df.head(int(limite)).copy()

    firma = hashlib.sha1(pd.util.hash_pandas_object(df.head(10_000), index=False).values.tobytes()).hexdigest()[:12]
    proc = {"nombre": fuente["nombre"], "tipo": tipo, "origen": origen, "filas": int(len(df)),
            "columnas": int(df.shape[1]), "hash": firma,
            "memoria_mb": round(memoria_mb(df), 2)}
    if limite:
        # Una corrida limitada que no lo dice es una corrida que alguien va a
        # presentar como si fuera el total.
        proc["limite_filas"] = int(limite)
        proc["parcial"] = True
    aviso = aviso_de_volumen(fuente["nombre"], df)
    if aviso:
        proc["aviso_volumen"] = aviso
    return df, proc
