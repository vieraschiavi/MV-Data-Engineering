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
| ML | AutoML honesto: tres modelos, corte 60/20/20 (el número sale del holdout, con la brecha selección→holdout), chequeo de fuga, scoring de un segundo conjunto (backtest a ciegas) y salida de cartera al estilo MV Kobra AI: probpago, decil, segmento, estrategia, valor esperado, prioridad | `ml.json`, `ml_scores`, `cartera_priorizada.xlsx` |
| Reporte | KPIs (agregación, ratio, SQL), gráficos, Excel corporativo y HTML autocontenido | `reporte.xlsx`, `reporte.html` |
| DAX | medidas generadas: DIVIDE, KEEPFILTERS, REMOVEFILTERS, DATEADD | `measures.dax` |
| Power BI | `.pbit` + PBIP con modelo, relaciones, medidas y tablero, auditado (MV DAX Lab) | `<nombre>.pbit`, `_demo.pbit` |
| Entrega | manifiesto, resumen ejecutivo, salud + historial, monitoreo de cargas (`frescura.json`), **justificación etapa por etapa para técnicos y gerencia** (ES + EN), **bitácora de transformaciones en HTML / Word / PDF** y copia de lo entregable | `entrega/` |

## En la app

- **Fuentes:** subís archivos (CSV, Excel, Parquet, JSON) o declarás una conexión SQL de sólo lectura (SQL Server, PostgreSQL, MySQL, SQLite, DuckDB); la contraseña se lee de una variable de entorno, nunca va al YAML.
- **IA:** elegís proveedor (Claude, OpenAI, Gemini, Copilot/Azure, Groq, Mistral, DeepSeek, Ollama local) y modelo con tu propia clave, actualizás la lista de modelos desde la API del proveedor y preguntás en lenguaje natural: la IA propone una consulta, el motor la ejecuta en el almacén (sólo lectura) y la IA interpreta el resultado. Sin clave, el modo local responde con los KPIs, la calidad y el modelo.
- **Cargas:** monitoreo de actualización tabla por tabla, con las dos fechas que suelen confundirse: hasta cuándo llega el **dato** y cuándo corrió la **carga**. Un proceso puntual puede traer información vieja, y así se ve. Semáforo por tabla (actualizada / atrasada / sin fecha / vacía), frecuencia esperada declarada en el YAML (`frescura`), frecuencia **real** medida sobre el historial de corridas, y `frescura.json` en cada entrega.
- **Salud:** puntaje por área (datos, calidad, modelo, gobernanza, BI, ML), mejoras sugeridas con parche al YAML que se aplican con un clic, y el antes/después de cada corrida.
- **Justificación:** para cada etapa, qué se hizo con los números de la corrida, la lectura técnica y la lectura gerencial. Se descarga en Markdown.
- **Transformaciones:** la bitácora completa de la corrida —cada transformación y característica técnica, en el orden del pipeline— contada tres veces por paso: **técnico** (qué se hizo exactamente), **en criollo** (para un jefe o gerente) e **impacto río abajo** (qué cambia en el modelo, los KPIs o el tablero). Filtro por etapa, vista sólo técnica o sólo criolla, y exportación a **HTML, Word y PDF** (también quedan en `entrega/` en cada corrida).
- **Demos:** `cobranzas` (financiera sintética), `ventas` (consumo masivo, tres formatos de origen) y `kash` (backtest a ciegas de una financiera: train con 12 meses de pagos y ventana futura + score de la misma fecha, esquema real con `;` y BOM, datos 100 % sintéticos calibrados con estadísticas agregadas).

## Correr

```bash
./run.sh                                   # Linux/macOS → abre el programa
MV_DataEngineering.bat                     # Windows, doble clic
python -m mvde demo cobranzas ./demo --correr     # demo financiera, 12 etapas en ~10 s
python -m mvde demo ventas ./demo2 --correr       # demo consumo masivo (Excel + CSV ; + Parquet)
python -m mvde demo kash ./demo3 --correr         # backtest a ciegas: train + score, ProbPago y cartera priorizada
python -m mvde nuevo mis_datos.csv         # YAML de arranque desde cualquier archivo
python -m mvde correr proyecto.yaml --desde gold   # reanudar desde una etapa
python -m mvde automatizar proyecto.yaml   # .bat (Programador de tareas), cron, DAG de Airflow
python -m pytest -q tests                  # 26 tests
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
ml: {tabla: fact_cliente_train, tabla_score: fact_cliente_score, target: pago_val, id: dim_cliente_key,
     excluir: [NMesesConPago_VAL], cobranzas: {monto: monto_ref, dias_mora: DiasAtraso_Actual}}
powerbi: {generar: true, nombre: Cobranzas}
```

Las dos demos (`mvde/demos.py`) son el YAML completo de referencia: datos 100 %
sintéticos con defectos inyectados a propósito para que el gate tenga algo que decir.

## En un servidor (sin instalar nada en las PC)

Cuando la política de la empresa prohíbe instalar programas, o el equipo es de
varias personas, la app se publica en una VM y cada uno entra por el navegador.

```bash
mkdir -p secretos datos
python3 -m mvde usuario martin >> secretos/usuarios.txt   # pide la clave sin mostrarla
docker compose up -d --build
```

El login se enciende solo cuando hay usuarios declarados: en el escritorio
(`run.sh`, el `.bat`) sigue abriendo sin pedir nada. Las contraseñas se guardan
como PBKDF2-HMAC-SHA256 con sal por usuario, cinco intentos fallidos bloquean
cinco minutos, y las credenciales van en un archivo montado que Docker Compose
nunca interpola. La guía completa para el área de infraestructura, con
requisitos, HTTPS, cuenta de base de sólo lectura y solución de problemas, está
en [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

## Estructura

```
mv-data-engineering/
├── mvde/            motor: proyecto · fuentes · bronze · silver · calidad · gold · almacen · gobernanza ·
│                    ml · reporte · dax · powerbi · ia · justificacion · salud · frescura · transformaciones · auth · orquestador · automatizacion · demos · cli · i18n
├── app/app.py       programa Streamlit (ES/EN/PT), misma familia visual que MV Data Governance
├── tests/           55 tests: motor, i18n, tres demos end-to-end, gate, reanudación, CLI, IA local, justificación, salud, cargas, transformaciones, login
├── docs/DESPLIEGUE.md  puesta en marcha en servidor (para infraestructura del cliente)
├── Dockerfile · docker-compose.yml   despliegue en VM: la gente entra por navegador
├── run.sh · MV_DataEngineering.bat · requirements.txt · CLAUDE.md
```

La etapa Power BI usa `../daxlingo/dxl` (MV DAX Lab, en este mismo repo). Si no está,
la etapa se omite y el resto del pipeline sigue.
