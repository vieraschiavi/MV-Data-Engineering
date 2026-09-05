# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 6 · Almacén: gold en DuckDB (esquema `gold`) + vistas del YAML.
Opcional: publicar las mismas tablas en un motor SQL vía SQLAlchemy."""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

_ESCRITURA = re.compile(r"^\s*(insert|update|delete|drop|alter|create|truncate|merge|exec|grant)\b", re.I)


def cargar(gold: dict[str, pd.DataFrame], ruta: Path, vistas: dict[str, str] | None = None) -> dict:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ruta))
    conteos, ok_vistas, err_vistas = {}, [], {}
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS gold")
        for nombre, df in gold.items():
            con.register("df_tmp", df)
            con.execute(f'CREATE OR REPLACE TABLE gold."{nombre}" AS SELECT * FROM df_tmp')
            con.unregister("df_tmp")
            conteos[nombre] = con.execute(f'SELECT COUNT(*) FROM gold."{nombre}"').fetchone()[0]
        for nombre, sql in (vistas or {}).items():
            try:
                con.execute(f'CREATE OR REPLACE VIEW gold."{nombre}" AS {sql}')
                con.execute(f'SELECT * FROM gold."{nombre}" LIMIT 1')
                ok_vistas.append(nombre)
            except duckdb.Error as exc:
                err_vistas[nombre] = str(exc).splitlines()[0]
    finally:
        con.close()
    return {"tablas": conteos, "vistas": ok_vistas, "vistas_con_error": err_vistas}


def consultar(ruta: Path, sql: str) -> pd.DataFrame:
    if _ESCRITURA.match(sql):
        raise ValueError("sólo lectura")
    con = duckdb.connect(str(ruta), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def publicar(gold: dict[str, pd.DataFrame], url: str, esquema: str | None = None) -> dict:
    """Escribe gold en SQL Server / PostgreSQL / MySQL (URL SQLAlchemy). Reemplaza
    tabla por tabla: es la carga idempotente más simple que existe."""
    import sqlalchemy as sa
    motor = sa.create_engine(url)
    filas = {}
    with motor.begin() as con:
        for nombre, df in gold.items():
            df.to_sql(nombre, con, schema=esquema, if_exists="replace", index=False, chunksize=5000)
            filas[nombre] = int(len(df))
    return {"publicadas": filas, "destino": re.sub(r"://[^@]*@", "://***@", url)}
