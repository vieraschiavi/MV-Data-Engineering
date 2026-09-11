#!/usr/bin/env python3
# © 2026 Martín Viera. Todos los derechos reservados.
"""Mide hasta dónde aguanta el motor en ESTA máquina, con datos reales.

Para qué existe
---------------
Las demos tienen entre cientos y miles de filas. Un proyecto de cliente puede
tener millones. La diferencia no se estima leyendo el código: se mide. Sin este
número, cualquier plazo que se prometa en una propuesta es una adivinanza — y el
que la paga es el que ejecuta.

Qué mide
--------
El pico de memoria y el tiempo de las etapas que cargan datos en memoria
(`fuentes` → `bronze` → `silver`), que son las que definen el techo. Las etapas
posteriores trabajan sobre agregados y no mueven la aguja.

Cómo usarlo
-----------
    python scripts/medir_volumen.py                    # curva por defecto
    python scripts/medir_volumen.py --filas 2000000    # un tamaño puntual
    python scripts/medir_volumen.py --columnas 40      # tablas anchas

En la VM del cliente, antes de diseñar nada: correlo con el volumen que declaró
el relevamiento (pregunta `fuentes / volumen` del catálogo). Si el número que dio
el cliente está arriba del techo que imprime esto, la arquitectura cambia ANTES
de escribir el YAML, no después del primer incidente.
"""
from __future__ import annotations

import argparse
import gc
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

CURVA = (50_000, 250_000, 1_000_000, 2_000_000)


def pico_mb() -> float:
    """Pico de memoria residente del proceso, en MB. En Linux viene en KB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def ram_disponible_mb() -> float | None:
    try:
        for linea in Path("/proc/meminfo").read_text().splitlines():
            if linea.startswith("MemAvailable:"):
                return int(linea.split()[1]) / 1024
    except OSError:
        pass
    return None


def generar_csv(ruta: Path, filas: int, columnas: int, semilla: int = 42) -> float:
    """Una tabla de hechos con la forma habitual: fecha, claves, monto, texto."""
    r = np.random.default_rng(semilla)
    datos = {
        "fecha": pd.to_datetime("2024-01-01") + pd.to_timedelta(r.integers(0, 730, filas), unit="D"),
        "id_entidad": r.integers(1, max(2, filas // 50), filas),
        "categoria": r.choice(["A", "B", "C", "D", "E", "F"], filas),
        "monto": np.round(r.gamma(2.0, 500.0, filas), 2),
        "cantidad": r.integers(1, 400, filas),
    }
    for i in range(max(0, columnas - len(datos))):
        datos[f"extra_{i:02d}"] = np.round(r.normal(100, 25, filas), 3)
    pd.DataFrame(datos).to_csv(ruta, index=False)
    del datos
    gc.collect()
    return ruta.stat().st_size / 1024 / 1024


def proyecto(base: Path, csv: Path) -> Path:
    spec = {
        "proyecto": "medicion-volumen",
        "descripcion": "Datos sintéticos para medir el techo del motor. No son de ningún cliente.",
        "salida": str(base / "salida"),
        "fuentes": [{"nombre": "hechos", "tipo": "csv", "ruta": str(csv)}],
        "silver": {"hechos": {"fechas": ["fecha"]}},
        # Sin gold/ml/reporte: acá se mide el techo de memoria, que lo fijan
        # fuentes + bronze + silver. Lo demás trabaja sobre agregados.
        "calidad": {"reglas": []},
    }
    ruta = base / "proyecto.yaml"
    ruta.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ruta


def medir(filas: int, columnas: int) -> dict:
    from mvde.orquestador import Pipeline

    base = Path(tempfile.mkdtemp(prefix="mvde_vol_"))
    try:
        mb_csv = generar_csv(base / "hechos.csv", filas, columnas)
        antes = pico_mb()
        p = Pipeline.desde_yaml(proyecto(base, base / "hechos.csv"))
        tiempos = {}
        for etapa in ("fuentes", "bronze", "silver"):
            t0 = time.perf_counter()
            r = p.etapa(etapa)
            tiempos[etapa] = time.perf_counter() - t0
            if not r.ok:
                return {"filas": filas, "error": f"{etapa}: {r.mensaje}", "mb_csv": mb_csv}
        pico = pico_mb()
        return {
            "filas": filas, "mb_csv": mb_csv,
            "pico_mb": pico, "delta_mb": pico - antes,
            "bytes_fila": (pico - antes) * 1024 * 1024 / filas if filas else 0,
            "seg_total": sum(tiempos.values()), "tiempos": tiempos,
        }
    finally:
        shutil.rmtree(base, ignore_errors=True)
        gc.collect()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--filas", type=int, help="medir un solo tamaño")
    ap.add_argument("--columnas", type=int, default=10)
    a = ap.parse_args()
    tamanos = [a.filas] if a.filas else list(CURVA)

    ram = ram_disponible_mb()
    print(f"RAM disponible: {ram:,.0f} MB" if ram else "RAM disponible: no se pudo leer")
    print(f"Columnas por tabla: {a.columnas}\n")
    print(f"{'filas':>12} {'CSV MB':>9} {'RAM pico MB':>12} {'B/fila':>8} {'seg':>7}  detalle por etapa")
    print("-" * 96)

    filas_ok, bytes_fila = [], []
    for n in tamanos:
        try:
            m = medir(n, a.columnas)
        except MemoryError:
            print(f"{n:>12,} {'—':>9} {'MemoryError':>12}   <-- TECHO ALCANZADO")
            break
        if "error" in m:
            print(f"{n:>12,} {m['mb_csv']:>9,.1f} {'FALLA':>12}   {m['error'][:50]}")
            break
        det = "  ".join(f"{k} {v:.1f}s" for k, v in m["tiempos"].items())
        print(f"{m['filas']:>12,} {m['mb_csv']:>9,.1f} {m['pico_mb']:>12,.0f} "
              f"{m['bytes_fila']:>8,.0f} {m['seg_total']:>7.1f}  {det}")
        filas_ok.append(n)
        bytes_fila.append(m["bytes_fila"])

    if filas_ok and ram:
        # El pico lo fija que `tablas` (bronze) y `silver` viven a la vez, así
        # que se toma el consumo medido y se deja un 25 % de aire para el resto
        # del proceso y para el sistema operativo.
        b = max(bytes_fila)
        techo = int(ram * 0.75 * 1024 * 1024 / b)
        print("-" * 96)
        print(f"Consumo medido: ~{b:,.0f} bytes por fila (con {a.columnas} columnas).")
        print(f"Techo estimado en esta máquina: ~{techo:,} filas por tabla "
              f"(75 % de {ram:,.0f} MB disponibles).")
        print("\nEste número NO es una propiedad del producto: depende de la máquina y del")
        print("ancho de la tabla. Medilo en la VM del cliente con SU volumen antes de")
        print("comprometer una arquitectura o un plazo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
