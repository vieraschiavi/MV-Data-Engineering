# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 2 · Bronze: lo que llegó, exactamente, con linaje. Idempotente."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def escribir(nombre: str, df: pd.DataFrame, procedencia: dict, carpeta: Path) -> Path:
    out = df.copy()
    out["_fuente"] = procedencia.get("origen", "")
    out["_ingestado_en"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out["_hash_fuente"] = procedencia.get("hash", "")
    destino = carpeta / nombre
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "part-000.parquet"
    # Todo a tipos que Parquet acepte sin sorpresas: objetos mixtos → texto.
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].astype("string")
    out.to_parquet(ruta, index=False)          # sobrescribe la partición completa
    return ruta


def leer(nombre: str, carpeta: Path) -> pd.DataFrame:
    df = pd.read_parquet(carpeta / nombre / "part-000.parquet")
    return df[[c for c in df.columns if not c.startswith("_")]]


def metadatos(nombre: str, carpeta: Path) -> dict:
    """El linaje que escribió `escribir`: de dónde vino, cuándo se ingestó y con
    qué hash. Es la fuente de la fecha/hora de carga que muestra el monitoreo."""
    ruta = carpeta / nombre / "part-000.parquet"
    if not ruta.exists():
        return {}
    columnas = [c for c in pd.read_parquet(ruta).columns if c.startswith("_")]
    if not columnas:
        return {}
    fila = pd.read_parquet(ruta, columns=columnas).head(1)
    if fila.empty:
        return {}
    return {c.lstrip("_"): (None if pd.isna(fila.iloc[0][c]) else str(fila.iloc[0][c])) for c in columnas}
