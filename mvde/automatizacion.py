# © 2026 Martín Viera. Todos los derechos reservados.
"""Genera lo necesario para que el proyecto corra solo: comando, .bat para el
Programador de tareas de Windows, línea de cron y DAG de Airflow."""
from __future__ import annotations

from pathlib import Path


def comando(ruta_yaml: str) -> str:
    return f'python -m mvde correr "{ruta_yaml}"'


def bat_windows(ruta_yaml: str, python: str = "python") -> str:
    return f"""@echo off
REM MV Data Engineering · corrida diaria. Programar con:
REM   schtasks /Create /SC DAILY /ST 05:00 /TN "MVDE_pipeline" /TR "\\"%~f0\\""
cd /d "%~dp0"
{python} -m mvde correr "{ruta_yaml}" >> mvde_corridas.log 2>&1
if errorlevel 1 (
  echo [%date% %time%] FALLO >> mvde_corridas.log
  exit /b 1
)
echo [%date% %time%] OK >> mvde_corridas.log
"""


def cron(ruta_yaml: str, hora: str = "05:00") -> str:
    h, m = hora.split(":")
    return f"{int(m)} {int(h)} * * * cd {Path(ruta_yaml).resolve().parent} && python -m mvde correr {Path(ruta_yaml).name} >> mvde_corridas.log 2>&1"


def dag_airflow(spec: dict, ruta_yaml: str) -> str:
    from . import ETAPAS
    hora = (spec.get("automatizacion") or {}).get("hora", "05:00")
    h, m = hora.split(":")
    reint = (spec.get("automatizacion") or {}).get("reintentos", 3)
    dag_id = "mvde_" + "".join(c if c.isalnum() else "_" for c in spec["nombre"].lower())
    tareas = "\n".join(f'    t_{e} = PythonOperator(task_id="{e}", python_callable=lambda e="{e}": _etapa(e))' for e in ETAPAS)
    cadena = " >> ".join(f"t_{e}" for e in ETAPAS)
    return f'''"""DAG generado por MV Data Engineering para «{spec["nombre"]}».
Cada tarea corre UNA etapa del mismo pipeline (mvde.orquestador): si una
falla, Airflow reintenta {reint} veces y las siguientes no corren."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

RUTA_YAML = r"{ruta_yaml}"


def _etapa(nombre: str) -> None:
    from mvde.orquestador import Pipeline
    p = Pipeline.desde_yaml(RUTA_YAML)
    if nombre != "fuentes":
        p._rehidratar(nombre)
    r = p.etapa(nombre)
    if not r.ok and not r.omitida:
        raise RuntimeError(f"{{nombre}}: {{r.error}}")


with DAG(
    dag_id="{dag_id}",
    start_date=datetime(2026, 1, 1),
    schedule="{int(m)} {int(h)} * * *",
    catchup=False,
    max_active_runs=1,
    default_args={{"owner": "data-eng", "retries": {reint}, "retry_delay": timedelta(minutes=5),
                  "execution_timeout": timedelta(minutes=60)}},
    tags=["mvde"],
) as dag:
{tareas}
    {cadena}
'''
