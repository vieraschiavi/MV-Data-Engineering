# © 2026 Martín Viera. Todos los derechos reservados.
"""Monitoreo de cargas: cuándo se actualizó por última vez cada tabla.

Antes de mirar un KPI hay una pregunta más barata y más urgente: ¿el dato que
estoy mirando es de hoy? Este módulo responde eso por tabla, separando dos
fechas que se confunden todo el tiempo:

  - **fecha de los datos**: hasta cuándo llega la información (el máximo de la
    columna de fecha del negocio). Es la que le importa a quien lee el tablero.
  - **fecha de carga**: cuándo corrió la ingesta (el sello que bronze escribe en
    `_ingestado_en`). Es la que le importa a quien opera el pipeline.

Un proceso puede correr puntual todas las mañanas y traer datos viejos: ahí la
carga está al día y el dato no. Mostrar una sola de las dos esconde ese caso.

La frecuencia esperada se declara en el YAML (`frescura`), y el historial de
corridas permite comparar contra la frecuencia REAL con la que se actualiza.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# Cada cuánto se espera que llegue dato nuevo, en horas.
PERIODOS = {"horaria": 1, "diaria": 24, "semanal": 24 * 7, "quincenal": 24 * 15, "mensual": 24 * 30}
# Margen sobre el período antes de gritar: una carga diaria que llega a las 9 de
# la mañana no está atrasada a las 8, y el fin de semana corre el calendario.
_MARGEN = 1.15
_MARGEN_MINIMO_HORAS = 2
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

ESTADOS = ("actualizada", "atrasada", "sin_fecha", "vacia")


def config(spec: dict) -> dict:
    """Sección `frescura` del YAML, con lo que falte por defecto."""
    cfg = dict(spec.get("frescura") or {})
    cfg.setdefault("cada", "diaria")
    cfg.setdefault("tablas", {})
    return cfg


def _cfg_tabla(cfg: dict, tabla: str) -> dict:
    propia = dict((cfg.get("tablas") or {}).get(tabla) or {})
    propia.setdefault("cada", cfg.get("cada", "diaria"))
    cada = propia["cada"]
    if propia.get("tolerancia_horas") is None:
        base = PERIODOS.get(cada, PERIODOS["diaria"])
        propia["tolerancia_horas"] = round(max(base * _MARGEN, base + _MARGEN_MINIMO_HORAS), 1)
    return propia


# ------------------------------------------------------------------ fechas
def _fecha_maxima(df: pd.DataFrame, preferida: str | None = None) -> tuple[pd.Timestamp | None, str | None]:
    """La fecha de negocio más reciente de la tabla y de qué columna salió."""
    candidatas = [preferida] if preferida and preferida in df.columns else []
    candidatas += [c for c in df.columns
                   if c not in candidatas and pd.api.types.is_datetime64_any_dtype(df[c])]
    mejor, col = None, None
    for c in candidatas:
        serie = df[c].dropna()
        if serie.empty:
            continue
        tope = pd.Timestamp(serie.max())
        if tope.tzinfo is not None:
            tope = tope.tz_convert(None) if hasattr(tope, "tz_convert") else tope.tz_localize(None)
        # Una fecha futura no es frescura: suele ser un vencimiento o una
        # proyección, no «hasta cuándo llega el dato».
        if tope > pd.Timestamp(datetime.now()) + pd.Timedelta(days=1):
            continue
        if mejor is None or tope > mejor:
            mejor, col = tope, c
    return mejor, col


def _fecha_desde_clave(df: pd.DataFrame) -> pd.Timestamp | None:
    """Las tablas de hechos guardan la fecha como entero AAAAMMDD en `fecha_key`."""
    if "fecha_key" not in df.columns:
        return None
    serie = pd.to_numeric(df["fecha_key"], errors="coerce").dropna()
    serie = serie[serie > 19000101]
    if serie.empty:
        return None
    return pd.to_datetime(str(int(serie.max())), format="%Y%m%d", errors="coerce")


def _horas(desde: datetime | pd.Timestamp | None, hasta: datetime) -> float | None:
    if desde is None:
        return None
    d = desde.to_pydatetime() if isinstance(desde, pd.Timestamp) else desde
    if d.tzinfo is not None and hasta.tzinfo is None:
        d = d.astimezone(timezone.utc).replace(tzinfo=None)
    if d.tzinfo is None and hasta.tzinfo is not None:
        d = d.replace(tzinfo=timezone.utc)
    return round((hasta - d).total_seconds() / 3600, 1)


# ------------------------------------------------------------------ evaluar
def evaluar(pipeline, ahora: datetime | None = None) -> list[dict]:
    """Una fila por tabla: filas, fecha del dato, fecha de carga y estado."""
    ahora = ahora or datetime.now()
    ahora_utc = datetime.now(timezone.utc) if ahora.tzinfo is None else ahora
    cfg = config(pipeline.spec)
    silver_cfg = pipeline.spec.get("silver") or {}
    filas: list[dict] = []

    # 1) las tablas que se cargan: fuente → bronze → silver
    for f in pipeline.spec.get("fuentes", []):
        nombre = f["nombre"]
        df = pipeline.silver.get(nombre)
        if df is None:
            continue
        propia = _cfg_tabla(cfg, nombre)
        declaradas = (silver_cfg.get(nombre) or {}).get("fechas") or []
        fecha_datos, columna = _fecha_maxima(df, propia.get("columna_fecha") or (declaradas[0] if declaradas else None))
        meta = {}
        try:
            from . import bronze
            meta = bronze.metadatos(nombre, pipeline.dirs["bronze"])
        except Exception:  # noqa: BLE001 - sin bronze en disco se sigue con la fecha del dato
            meta = {}
        carga = pd.to_datetime(meta.get("ingestado_en"), errors="coerce", utc=True) if meta.get("ingestado_en") else None
        filas.append(_fila(nombre, "origen", f.get("tipo", ""), df, fecha_datos, columna,
                           None if carga is None or pd.isna(carga) else carga.to_pydatetime(),
                           propia, ahora, ahora_utc, origen=meta.get("fuente") or f.get("ruta") or f.get("url", "")))

    # 2) las tablas del modelo que llevan fecha: se sirven al tablero y a Power BI
    for nombre, df in (pipeline.gold or {}).items():
        if nombre.startswith("dim_") or nombre == "ml_scores":
            continue
        fecha_datos = _fecha_desde_clave(df)
        columna = "fecha_key" if fecha_datos is not None else None
        if fecha_datos is None:
            fecha_datos, columna = _fecha_maxima(df)
        propia = _cfg_tabla(cfg, nombre)
        filas.append(_fila(nombre, "modelo", "gold", df, fecha_datos, columna, None, propia, ahora, ahora_utc))
    return filas


def _fila(nombre, capa, tipo, df, fecha_datos, columna, fecha_carga, propia, ahora, ahora_utc, origen="") -> dict:
    n = int(len(df))
    horas_datos = _horas(fecha_datos, ahora)
    horas_carga = _horas(fecha_carga, ahora_utc)
    tolerancia = float(propia["tolerancia_horas"])
    # El dato manda: una carga puntual con información vieja no está al día.
    referencia = horas_datos if horas_datos is not None else horas_carga
    if n == 0:
        estado = "vacia"
    elif referencia is None:
        estado = "sin_fecha"
    elif referencia <= tolerancia:
        estado = "actualizada"
    else:
        estado = "atrasada"
    return {
        "tabla": nombre, "capa": capa, "tipo": tipo, "origen": origen, "filas": n,
        "fecha_datos": None if fecha_datos is None else pd.Timestamp(fecha_datos).isoformat(timespec="seconds"),
        "columna_fecha": columna,
        "fecha_carga": None if fecha_carga is None else fecha_carga.isoformat(timespec="seconds"),
        "horas_desde_datos": horas_datos, "horas_desde_carga": horas_carga,
        "cada": propia["cada"], "dia_esperado": propia.get("dia_esperado"),
        "tolerancia_horas": tolerancia, "estado": estado,
    }


def resumen(filas: list[dict]) -> dict:
    return {e: sum(1 for f in filas if f["estado"] == e) for e in ESTADOS} | {"tablas": len(filas)}


# ------------------------------------------------------------------ historial
def _ruta(pipeline) -> Path:
    return pipeline.salida / "frescura_historial.json"


def registrar(pipeline, filas: list[dict]) -> Path:
    """Una entrada por corrida. De acá sale la frecuencia REAL de actualización."""
    p = _ruta(pipeline)
    hist = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    hist.append({"corrida": datetime.now().isoformat(timespec="seconds"),
                 "tablas": {f["tabla"]: {"fecha_datos": f["fecha_datos"], "fecha_carga": f["fecha_carga"],
                                         "filas": f["filas"], "estado": f["estado"]} for f in filas}})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(hist[-200:], indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def historial(pipeline) -> list[dict]:
    p = _ruta(pipeline)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def frecuencia_real(hist: list[dict], tabla: str) -> dict | None:
    """Cada cuántas horas cambió de verdad el dato de esa tabla, medido sobre el
    historial. Con menos de dos fechas distintas todavía no hay nada que medir."""
    vistas: list[pd.Timestamp] = []
    for corrida in hist:
        f = (corrida.get("tablas") or {}).get(tabla, {}).get("fecha_datos")
        if not f:
            continue
        ts = pd.to_datetime(f, errors="coerce")
        if pd.notna(ts) and (not vistas or ts != vistas[-1]):
            vistas.append(ts)
    if len(vistas) < 2:
        return None
    deltas = [(b - a).total_seconds() / 3600 for a, b in zip(vistas, vistas[1:]) if b > a]
    if not deltas:
        return None
    return {"observaciones": len(vistas), "mediana_horas": round(statistics.median(deltas), 1),
            "minimo_horas": round(min(deltas), 1), "maximo_horas": round(max(deltas), 1)}


def proxima_carga(fila: dict, ahora: datetime | None = None) -> str | None:
    """Cuándo debería llegar la próxima actualización, según lo declarado."""
    ahora = ahora or datetime.now()
    base = fila.get("fecha_carga") or fila.get("fecha_datos")
    if not base:
        return None
    ts = pd.to_datetime(base, errors="coerce")
    if pd.isna(ts):
        return None
    horas = PERIODOS.get(fila.get("cada", "diaria"), PERIODOS["diaria"])
    ts = ts.tz_localize(None) if ts.tzinfo is not None else ts
    return (ts.to_pydatetime() + timedelta(hours=horas)).isoformat(timespec="seconds")
