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
import re
import shutil
import sqlite3
import subprocess
import urllib.request
from pathlib import Path

import pandas as pd

from . import confidencial

_ESCRITURA = re.compile(r"^\s*(insert|update|delete|drop|alter|create|truncate|merge|exec|grant)\b", re.I)
_NUBE = ("s3://", "gs://", "gcs://", "az://", "abfs://", "abfss://", "adl://")


class FuenteError(RuntimeError):
    pass


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


def _leer_archivo(ruta: str, tipo: str, fuente: dict) -> pd.DataFrame:
    op = _opciones(fuente)
    storage = {"storage_options": op.pop("storage_options")} if "storage_options" in op else {}
    if tipo == "csv":
        op.setdefault("sep", None)
        op.setdefault("engine", "python")
        op.setdefault("encoding", "utf-8-sig")     # el BOM de Excel no se vuelve parte del primer encabezado
        return pd.read_csv(ruta, **op, **storage)
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
    if _ESCRITURA.match(consulta):
        raise FuenteError("sólo se admiten consultas de lectura (SELECT / WITH)")
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(consulta, con)
    finally:
        con.close()


def _leer_sql(fuente: dict) -> pd.DataFrame:
    try:
        import sqlalchemy as sa
    except ImportError as exc:
        raise FuenteError("instalá sqlalchemy (+ el driver del motor) para fuentes `sql`") from exc
    url = fuente.get("url")
    if not url:
        raise FuenteError(f"fuente «{fuente['nombre']}» tipo sql sin `url` (SQLAlchemy)")
    consulta = fuente.get("consulta") or f"SELECT * FROM {fuente.get('tabla', fuente['nombre'])}"
    if _ESCRITURA.match(consulta):
        raise FuenteError("sólo se admiten consultas de lectura (SELECT / WITH)")
    motor = sa.create_engine(url)
    with motor.connect() as con:
        return pd.read_sql_query(sa.text(consulta), con)


def _leer_duckdb(ruta: str, fuente: dict) -> pd.DataFrame:
    import duckdb
    consulta = fuente.get("consulta") or f'SELECT * FROM {fuente.get("tabla", fuente["nombre"])}'
    if _ESCRITURA.match(consulta):
        raise FuenteError("sólo se admiten consultas de lectura (SELECT / WITH)")
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
    firma = hashlib.sha1(pd.util.hash_pandas_object(df.head(10_000), index=False).values.tobytes()).hexdigest()[:12]
    return df, {"nombre": fuente["nombre"], "tipo": tipo, "origen": origen, "filas": int(len(df)),
                "columnas": int(df.shape[1]), "hash": firma}
