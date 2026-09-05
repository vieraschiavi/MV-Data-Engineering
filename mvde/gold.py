# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 5 · Gold: el modelo estrella declarado en `modelo` del YAML.

  dimensiones:
    - nombre: dim_cliente, desde: clientes, clave: id_cliente,
      atributos: [..] (opcional: todas), scd: 1 | 2
  hechos:
    - nombre: fact_pago, desde: pagos, fecha: fecha_pago,
      claves: {id_cliente: dim_cliente}, medidas: [monto] (opcional)
  calendario: auto | {desde: 2020-01-01, hasta: 2025-12-31} | null

Sin `modelo`, cada tabla silver pasa a gold tal cual (prefijo `tbl_`) más
un calendario si hay fechas: alcanza para reportar y para Power BI.
"""
from __future__ import annotations

import hashlib
from datetime import date

import numpy as np
import pandas as pd

LEJANO = pd.Timestamp("9999-12-31")


def _hash_attrs(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df[cols].astype(str).agg("|".join, axis=1).map(lambda s: hashlib.md5(s.encode()).hexdigest())


def dimension(df: pd.DataFrame, cfg: dict, existente: pd.DataFrame | None = None,
              a_fecha: date | None = None) -> pd.DataFrame:
    clave = cfg["clave"]
    attrs = [c for c in (cfg.get("atributos") or [c for c in df.columns if c != clave]) if c in df.columns]
    base = df[[clave] + attrs].drop_duplicates(subset=[clave], keep="last").reset_index(drop=True)
    sk = f"{cfg['nombre']}_key"
    if int(cfg.get("scd", 1)) != 2:
        base.insert(0, sk, np.arange(1, len(base) + 1))
        return base
    hoy = pd.Timestamp(a_fecha or date.today())
    base["attr_hash"] = _hash_attrs(base, attrs) if attrs else ""
    # Una tabla previa sin columnas de historia (venía como SCD 1) no sirve de base:
    # la historia arranca en esta corrida en vez de romper con KeyError.
    if existente is not None and not {"is_current", "version", "attr_hash"} <= set(existente.columns):
        existente = None
    if existente is None or existente.empty:
        base["valid_from"], base["valid_to"], base["is_current"], base["version"] = hoy, LEJANO, True, 1
        dim = base
    else:
        cur = existente[existente["is_current"]].set_index(clave)
        inc = base.set_index(clave)
        cambiados = inc.index[inc.index.isin(cur.index) & (inc["attr_hash"] != cur.reindex(inc.index)["attr_hash"])]
        nuevos = inc.index[~inc.index.isin(cur.index)]
        cerrado = existente.copy()
        mask = cerrado[clave].isin(cambiados) & cerrado["is_current"]
        cerrado.loc[mask, ["valid_to", "is_current"]] = [hoy, False]
        versiones = existente.groupby(clave)["version"].max()
        abiertos = inc.loc[list(cambiados) + list(nuevos)].reset_index()
        abiertos["valid_from"], abiertos["valid_to"], abiertos["is_current"] = hoy, LEJANO, True
        abiertos["version"] = abiertos[clave].map(versiones).fillna(0).astype(int) + 1
        dim = pd.concat([cerrado.drop(columns=[sk], errors="ignore"), abiertos], ignore_index=True)
    dim = dim.sort_values([clave, "version"]).reset_index(drop=True)
    dim.insert(0, sk, np.arange(1, len(dim) + 1))
    return dim


def calendario(desde: str, hasta: str) -> pd.DataFrame:
    dias = pd.date_range(desde, hasta, freq="D")
    c = pd.DataFrame({"fecha": dias})
    c.insert(0, "fecha_key", c["fecha"].dt.strftime("%Y%m%d").astype(int))
    c["anio"] = c["fecha"].dt.year
    c["trimestre"] = "T" + c["fecha"].dt.quarter.astype(str)
    c["mes_nro"] = c["fecha"].dt.month
    c["mes"] = c["fecha"].dt.strftime("%b")
    c["anio_mes"] = c["fecha"].dt.strftime("%Y-%m")
    c["anio_mes_orden"] = c["anio"] * 100 + c["mes_nro"]
    c["dia_semana"] = c["fecha"].dt.day_name().str[:3]
    c["es_fin_de_semana"] = c["fecha"].dt.dayofweek >= 5
    return c


def _rango_fechas(tablas: dict[str, pd.DataFrame]) -> tuple[str, str] | None:
    minimo, maximo = None, None
    for df in tablas.values():
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                lo, hi = df[col].min(), df[col].max()
                if pd.notna(lo):
                    minimo = lo if minimo is None or lo < minimo else minimo
                    maximo = hi if maximo is None or hi > maximo else maximo
    if minimo is None:
        return None
    return (minimo.replace(day=1).strftime("%Y-%m-%d"), (maximo + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d"))


def hecho(df: pd.DataFrame, cfg: dict, dims: dict[str, pd.DataFrame], dim_cfg: dict[str, dict]) -> pd.DataFrame:
    f = df.copy()
    for col, dim_nombre in (cfg.get("claves") or {}).items():
        d = dims[dim_nombre]
        natural = dim_cfg[dim_nombre]["clave"]
        sk = f"{dim_nombre}_key"
        actual = d[d["is_current"]] if "is_current" in d.columns else d
        mapa = actual[[natural, sk]]
        antes = len(f)
        f = f.merge(mapa, left_on=col, right_on=natural, how="left", validate="many_to_one")
        if len(f) != antes:
            raise RuntimeError(f"el join {cfg['nombre']}.{col} → {dim_nombre} multiplicó filas")
        if natural != col:
            f = f.drop(columns=[natural])
        f = f.drop(columns=[col])
    if cfg.get("fecha") and cfg["fecha"] in f.columns:
        fechas = pd.to_datetime(f[cfg["fecha"]], errors="coerce")
        f["fecha_key"] = fechas.dt.strftime("%Y%m%d").fillna("0").astype(int)
        f = f.drop(columns=[cfg["fecha"]])
    claves = [c for c in f.columns if c.endswith("_key")]
    return f[claves + [c for c in f.columns if c not in claves]]


def construir(spec: dict, silver: dict[str, pd.DataFrame], previo: dict[str, pd.DataFrame] | None = None,
              a_fecha: date | None = None) -> tuple[dict[str, pd.DataFrame], list[str]]:
    modelo = spec.get("modelo") or {}
    previo = previo or {}
    notas: list[str] = []
    gold: dict[str, pd.DataFrame] = {}
    dim_cfg = {d["nombre"]: d for d in modelo.get("dimensiones", []) or []}
    for d in dim_cfg.values():
        if d["desde"] not in silver:
            raise RuntimeError(f"dimensión {d['nombre']}: la tabla silver «{d['desde']}» no existe")
        gold[d["nombre"]] = dimension(silver[d["desde"]], d, previo.get(d["nombre"]), a_fecha)
        notas.append(f"{d['nombre']}: {len(gold[d['nombre']])} filas (SCD {d.get('scd', 1)})")
    cal = modelo.get("calendario", "auto")
    if cal == "auto":
        rango = _rango_fechas(silver)
        if rango:
            gold["dim_calendario"] = calendario(*rango)
            notas.append(f"dim_calendario: {rango[0]} → {rango[1]}")
    elif isinstance(cal, dict):
        gold["dim_calendario"] = calendario(str(cal["desde"]), str(cal["hasta"]))
        notas.append(f"dim_calendario: {cal['desde']} → {cal['hasta']}")
    for h in modelo.get("hechos", []) or []:
        if h["desde"] not in silver:
            raise RuntimeError(f"hecho {h['nombre']}: la tabla silver «{h['desde']}» no existe")
        gold[h["nombre"]] = hecho(silver[h["desde"]], h, gold, dim_cfg)
        notas.append(f"{h['nombre']}: {len(gold[h['nombre']])} filas")
    if not dim_cfg and not modelo.get("hechos"):
        for nombre, df in silver.items():
            out = df.copy()
            fechas = [c for c in out.columns if pd.api.types.is_datetime64_any_dtype(out[c])]
            if fechas and "dim_calendario" in gold:
                out["fecha_key"] = out[fechas[0]].dt.strftime("%Y%m%d").fillna("0").astype(int)
            gold[f"tbl_{nombre}"] = out
            notas.append(f"tbl_{nombre}: {len(out)} filas (sin modelo declarado, pasa tal cual)")
    return gold, notas
