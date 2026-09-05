# © 2026 Martín Viera. Todos los derechos reservados.
"""Línea de comandos.

    python -m mvde demo cobranzas ./mi_carpeta      # crea la demo y su YAML
    python -m mvde correr proyecto.yaml [--desde gold] [--hasta reporte]
    python -m mvde etapa proyecto.yaml calidad
    python -m mvde nuevo datos.csv [--nombre ventas]   # esqueleto de YAML desde un archivo
    python -m mvde automatizar proyecto.yaml           # .bat, cron y DAG
    python -m mvde validar proyecto.yaml
    python -m mvde salud proyecto.yaml [--aplicar]      # salud por área, sugerencias y (opcional) aplicarlas
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import ETAPAS, __version__, automatizacion, demos, proyecto, salud
from .orquestador import Pipeline


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mvde", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"mvde {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("correr")
    c.add_argument("yaml")
    c.add_argument("--desde", default="fuentes", choices=ETAPAS)
    c.add_argument("--hasta", default="entrega", choices=ETAPAS)
    e = sub.add_parser("etapa")
    e.add_argument("yaml")
    e.add_argument("etapa", choices=ETAPAS)
    d = sub.add_parser("demo")
    d.add_argument("nombre", choices=demos.NOMBRES)
    d.add_argument("carpeta", nargs="?", default="./demo_mvde")
    d.add_argument("--correr", action="store_true")
    n = sub.add_parser("nuevo")
    n.add_argument("archivo")
    n.add_argument("--nombre", default=None)
    a = sub.add_parser("automatizar")
    a.add_argument("yaml")
    v = sub.add_parser("validar")
    v.add_argument("yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(message)s")

    if args.cmd == "validar":
        spec = proyecto.cargar(args.yaml)
        print(f"OK: «{spec['nombre']}» · {len(spec['fuentes'])} fuentes · {len(spec['calidad'].get('reglas', []))} reglas · {len(spec['kpis'])} KPIs")
        return 0
    if args.cmd == "demo":
        ruta = demos.crear(args.nombre, Path(args.carpeta))
        print(f"demo creada: {ruta}")
        if not args.correr:
            return 0
        args.yaml, args.desde, args.hasta = str(ruta), "fuentes", "entrega"
    if args.cmd == "nuevo":
        import pandas as pd
        p = Path(args.archivo)
        tipo = {"csv": "csv", "txt": "csv", "xlsx": "excel", "xls": "excel", "parquet": "parquet", "json": "json"}.get(p.suffix.lstrip(".").lower(), "csv")
        df = pd.read_csv(p, sep=None, engine="python") if tipo == "csv" else pd.read_excel(p) if tipo == "excel" else pd.read_parquet(p) if tipo == "parquet" else pd.read_json(p)
        spec = proyecto.esqueleto(args.nombre or p.stem, df, p.name, tipo)
        out = p.with_name(f"{args.nombre or p.stem}.yaml")
        proyecto.guardar(spec, out)
        print(f"YAML generado: {out} — editalo y después: python -m mvde correr {out.name}")
        return 0
    if args.cmd == "automatizar":
        spec = proyecto.cargar(args.yaml)
        base = Path(args.yaml).resolve().parent
        (base / "correr_pipeline.bat").write_text(automatizacion.bat_windows(Path(args.yaml).name), encoding="utf-8")
        (base / "crontab.txt").write_text(automatizacion.cron(args.yaml, (spec.get("automatizacion") or {}).get("hora", "05:00")) + "\n", encoding="utf-8")
        (base / "dag_airflow.py").write_text(automatizacion.dag_airflow(spec, str(Path(args.yaml).resolve())), encoding="utf-8")
        print(f"generados en {base}: correr_pipeline.bat · crontab.txt · dag_airflow.py")
        return 0
    p = Pipeline.desde_yaml(args.yaml)
    if args.cmd == "salud":
        p._rehidratar("entrega")
        ev = salud.evaluar(p)
        print(f"salud total {ev['total']}/100 · " + " · ".join(f"{k} {v['puntaje']}" for k, v in ev["areas"].items()))
        sugs = salud.sugerencias(p)
        for sg in sugs:
            print(f"  [{sg['severidad']:5}] {sg['area']:10} {sg['titulo']}" + ("" if sg["aplicable"] else "  (manual)"))
        if args.aplicar:
            nuevo, n = salud.aplicar_todas(p.spec, sugs)
            proyecto.guardar(nuevo, args.yaml)
            print(f"{n} mejoras aplicadas a {args.yaml}; corré de nuevo para ver el después")
        return 0
    if args.cmd == "etapa":
        if args.etapa != "fuentes":
            p._rehidratar(args.etapa)
        r = p.etapa(args.etapa)
        return 0 if r.ok or r.omitida else 1
    res = p.correr(args.desde, args.hasta)
    fallo = [e for e, r in res.items() if not r.ok and not r.omitida]
    print("\n".join(f"{r.estado():8} {e:11} {r.resumen or r.error}" for e, r in res.items()))
    print(f"salida: {p.salida}")
    return 1 if fallo else 0


if __name__ == "__main__":
    sys.exit(main())
