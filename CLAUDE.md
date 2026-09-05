# CLAUDE.md — MV Data Engineering

Producto de este repo (hermano de `daxlingo/`, que reusa para DAX/.pbit).
Motor en `mvde/` (importable sin Streamlit), app en `app/app.py`, CLI `python -m mvde`.

## Comandos
| Acción | Comando |
|---|---|
| App | `./run.sh` (Linux/macOS) · `MV_DataEngineering.bat` (Windows) · `streamlit run app/app.py` |
| Demo end-to-end | `python -m mvde demo cobranzas ./demo_mvde --correr` (o `ventas`, `kash`) |
| Correr un proyecto | `python -m mvde correr proyecto.yaml [--desde gold] [--hasta reporte]` |
| Una etapa | `python -m mvde etapa proyecto.yaml calidad` |
| Nuevo proyecto desde un archivo | `python -m mvde nuevo datos.csv` |
| Automatizar | `python -m mvde automatizar proyecto.yaml` (.bat + cron + DAG Airflow) |
| Salud y mejoras sugeridas | `python -m mvde salud proyecto.yaml [--aplicar]` |
| Tests | `python -m pytest -q tests` |
| Lint | `ruff check .` (config en la raíz del repo) |

## Reglas
- Doce etapas fijas (`mvde.ETAPAS`); cada una es `_<etapa>()` en `orquestador.Pipeline` y devuelve `Resultado`. Una etapa que falla corta las siguientes; `ml` y `powerbi` son opcionales (se omiten, no cortan).
- Toda decisión vive en el YAML del proyecto (`proyecto.py` lo valida). Nada de rutas ni reglas hardcodeadas en el motor.
- Texto de cara al usuario en `mvde/i18n.py`, con las tres claves ES/EN/PT (test de paridad).
- Fuentes SQL sólo lectura; credenciales por URL/variables de entorno, nunca en el YAML versionado.
- Las demos son 100 % sintéticas con semilla fija y defectos inyectados a propósito. La demo `kash` replica el ESQUEMA de un backtest real (calibrado con estadísticas agregadas); ninguna fila real entra al repo.
- IA (`ia.py`): opcional y aditiva, claves sólo en sesión/entorno; el SQL que propone la IA se ejecuta sólo si es SELECT/WITH.
- `salud.py` puntúa por área y sugiere parches al YAML; `aplicar` nunca muta el spec original.
- `transformaciones.py` arma la bitácora (técnico / criollo / impacto por paso) desde `resultados` y el YAML; sus textos viven en `textos_transformaciones.py` (se mezclan en `i18n._T`, así el test de paridad los cubre). Exporta HTML / Word (python-docx) / PDF (reportlab); si falta una biblioteca lo dice, no rompe.
