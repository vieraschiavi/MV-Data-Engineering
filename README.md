# MV Data Engineering

**Cualquier proyecto de datos, de la fuente al reporte final, por etapas y sin fallas silenciosas.**
*Any data project, from source to final report, stage by stage, with no silent failures. ·
Qualquer projeto de dados, da fonte ao relatório final, por etapas e sem falhas silenciosas.*

Programa de escritorio/web (ES · EN · PT) para encarar un proyecto de ingeniería de
datos completo declarando **un YAML** y corriendo **doce etapas con gate**: si una
falla, las siguientes no corren y la evidencia dice por qué.

```
1 Fuentes → 2 Bronze → 3 Silver → 4 Calidad → 5 Gold → 6 Almacén → 7 Gobernanza
→ 8 ML → 9 Reporte → 10 DAX → 11 Power BI → 12 Entrega
```

| Etapa | Qué hace | Sale |
|---|---|---|
| Fuentes | CSV, Excel, Parquet, JSON, SQLite, DuckDB, SQL (SQLAlchemy, sólo lectura), URL, carpeta, Kaggle, rutas s3/az/gs | procedencia + hash |
| Bronze | crudo tal cual en Parquet con linaje; idempotente | `bronze/<tabla>/part-000.parquet` |
| Silver | renombrar, tipar (auto o declarado), decodificar, fechas, filtrar, deduplicar, despivotear, derivar | `silver/*.parquet` |
| Calidad | reglas por dimensión (no_nulo, unico, rango, valores, regex, referencia, fresco, expresion…); **crítica = corta** | `calidad.json` con puntaje |
| Gold | dimensiones SCD 1/2 con claves surrogadas, calendario automático, hechos con joins validados | `gold/*.parquet` |
| Almacén | DuckDB con esquema `gold` + vistas SQL del YAML; publicación opcional a SQL Server/PostgreSQL | `warehouse.duckdb` |
| Gobernanza | catálogo, diccionario, linaje fuente→KPI, PII, puntajes por dimensión | `gobernanza.json`, `catalogo.csv` |
| ML | clasificación/regresión (sklearn) con corte temporal, chequeo de fuga, importancias, scores a gold | `ml.json`, `ml_scores` |
| Reporte | KPIs (agregación, ratio, SQL), gráficos, Excel corporativo y HTML autocontenido | `reporte.xlsx`, `reporte.html` |
| DAX | medidas generadas: DIVIDE, KEEPFILTERS, REMOVEFILTERS, DATEADD | `measures.dax` |
| Power BI | `.pbit` + PBIP con modelo, relaciones, medidas y tablero, auditado (MV DAX Lab) | `<nombre>.pbit`, `_demo.pbit` |
| Entrega | manifiesto, resumen ejecutivo y copia de lo entregable | `entrega/` |

## Correr

```bash
./run.sh                                   # Linux/macOS → abre el programa
MV_DataEngineering.bat                     # Windows, doble clic
python -m mvde demo cobranzas ./demo --correr     # demo financiera, 12 etapas en ~10 s
python -m mvde demo ventas ./demo2 --correr       # demo consumo masivo (Excel + CSV ; + Parquet)
python -m mvde nuevo mis_datos.csv         # YAML de arranque desde cualquier archivo
python -m mvde correr proyecto.yaml --desde gold   # reanudar desde una etapa
python -m mvde automatizar proyecto.yaml   # .bat (Programador de tareas), cron, DAG de Airflow
python -m pytest -q tests                  # 19 tests
```

## El YAML, en una pantalla

```yaml
nombre: Cobranzas
fuentes:
  - {nombre: clientes, tipo: csv, ruta: clientes.csv}
  - {nombre: cuotas, tipo: sql, url: mssql+pyodbc://usr:pwd@srv/db?driver=ODBC+Driver+17, consulta: "SELECT ... "}
silver:
  clientes: {tipos: auto, decodificar: {sexo: {"1": Masculino, "2": Femenino}}, deduplicar: [id_cliente]}
  cuotas:   {fechas: [fecha_vencimiento], derivar: {en_mora: "meses_atraso >= 1"}}
calidad:
  reglas:
    - {tabla: clientes, columna: id_cliente, tipo: unico, critico: true}
    - {tabla: cuotas, columna: id_cliente, tipo: referencia, a: clientes.id_cliente}
modelo:
  dimensiones: [{nombre: dim_cliente, desde: clientes, clave: id_cliente, scd: 2}]
  hechos: [{nombre: fact_cuota, desde: cuotas, fecha: fecha_vencimiento, claves: {id_cliente: dim_cliente}}]
kpis:
  - {nombre: Monto cobrado, tabla: fact_cuota, columna: monto_pagado, agregacion: sum, por: canal}
  - {nombre: "% Cobrado", tipo: ratio, numerador: {tabla: fact_cuota, columna: monto_pagado, agregacion: sum},
     denominador: {tabla: fact_cuota, columna: monto_cuota, agregacion: sum}, formato: "0.0%"}
ml: {sql: "SELECT ... FROM gold.fact_cliente_riesgo ...", target: default_proximo_mes}
powerbi: {generar: true, nombre: Cobranzas}
```

Las dos demos (`mvde/demos.py`) son el YAML completo de referencia: datos 100 %
sintéticos con defectos inyectados a propósito para que el gate tenga algo que decir.

## Estructura

```
mv-data-engineering/
├── mvde/            motor: proyecto · fuentes · bronze · silver · calidad · gold · almacen ·
│                    gobernanza · ml · reporte · dax · powerbi · orquestador · automatizacion · demos · cli · i18n
├── app/app.py       programa Streamlit (ES/EN/PT), misma familia visual que MV Data Governance
├── tests/           19 tests: motor, i18n, demos end-to-end, gate, reanudación, CLI
├── run.sh · MV_DataEngineering.bat · requirements.txt · CLAUDE.md
```

La etapa Power BI usa `../daxlingo/dxl` (MV DAX Lab, en este mismo repo). Si no está,
la etapa se omite y el resto del pipeline sigue.
