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
- **Relevamiento:** las 48 preguntas que hay que hacerle al cliente antes de escribir una línea de código, separadas por las 12 etapas del pipeline. Cada una trae **para qué sirve la respuesta** (qué decisión del pipeline depende de ella) y a qué rol preguntársela; se anota quién respondió, de qué área y qué dijo. Cuando la respuesta no alcanza para decidir, el casillero de **repreguntas** propone qué volver a preguntar: sin IA detecta la forma de la respuesta (vaga, sin número, nombra un sistema sin decir cómo se accede), y con IA agrega las específicas del tema. Las respuestas con una traducción única **se aplican al YAML** con un clic (dueño del dato, frecuencia, hora, PII). Export a Markdown, Excel y JSON.
- **Reuniones:** de la reunión a la minuta. Tres entradas: la **transcripción que ya generó Teams, Zoom, Meet o WebEx** (`.vtt`, con hablante y minuto, sin necesidad de IA ni conexión), un **archivo de audio o video**, o el **micrófono** para la reunión presencial. La minuta sale por reglas —participantes y cuánto habló cada uno, decisiones, compromisos con su fecha, riesgos, preguntas abiertas y menciones por etapa del pipeline—, cada cosa con la cita y el minuto de donde salió; con IA se agrega un resumen ejecutivo por encima, nunca en lugar de la evidencia. Lo que se dijo en la reunión se propone como respuesta del relevamiento, para confirmar a mano.
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
python -m mvde demo cartera ./demo4 --correr      # cobranza mensual por estado: proyección a 30/60/90/120/150/180 días
python -m mvde nuevo mis_datos.csv         # YAML de arranque desde cualquier archivo
python -m mvde correr proyecto.yaml --desde gold   # reanudar desde una etapa
python -m mvde automatizar proyecto.yaml   # .bat (Programador de tareas), cron, DAG de Airflow
python -m pytest -q tests                  # 107 tests
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

## Proyección de series (`ml.tipo: serie`)

La etapa ML tiene dos caminos. El tabular (clasificación/regresión, corte 60/20/20)
y el de **series de tiempo**, para cuando la pregunta es *«¿cuánto vamos a cobrar
en los próximos seis meses?»*.

```yaml
ml:
  tipo: serie
  tabla: fact_cartera          # o `sql:` sobre el almacén
  fecha: fecha_key             # entiende el entero AAAAMMDD de gold
  valor: total_cobrado
  frecuencia: mensual          # diaria | semanal | mensual | trimestral | anual
  horizonte: 6                 # 6 meses = 30/60/90/120/150/180 días
  origenes: 7                  # cortes del backtest
  banda: 0.8                   # nivel de la banda de desvío
  segmento: [estado, tipo_cliente]   # un modelo por segmento, más el TOTAL
  # timesfm: {checkpoint: google/timesfm-2.5-200m-pytorch}   # opcional
```

Lo que hace, en orden:

1. **Backtest de origen móvil.** Corta la serie en varios puntos del pasado; en
   cada corte entrena SÓLO con lo anterior y predice el tramo siguiente, que
   compara con lo que realmente pasó. Nunca entra un dato posterior al corte.
2. **Elige el modelo con ese número, no con una opinión.** Compiten catorce
   backends: cinco básicos (ingenuo, estacional ingenuo, media móvil, drift,
   tendencia estacional), Holt-Winters, ocho métodos portados de un motor de
   proyecciones de cobranzas (YoY, MoM, Theta, reversión a la media, tendencia
   amortiguada, ciclo con decaimiento, pendiente del ciclo, factor anual) y un
   **ensemble** ponderado por lo que cada uno acertó.
3. **Se mide contra el tonto.** La referencia es repetir el mismo período del
   ciclo anterior. Si ningún modelo le gana, se proyecta con la referencia y el
   informe lo dice con todas las letras.
4. **Banda de desvío empírica.** El piso y el techo salen de los errores que
   ESE modelo tuvo, paso por paso del horizonte — no de una campana supuesta —
   y van corridos por el sesgo medido.
5. **Un modelo por segmento.** La mora temprana y la cartera jurídica no se
   comportan igual: cada una se proyecta por separado y se queda con el modelo
   que mejor le anduvo a ella.

Sale a gold y al almacén como dos tablas: `proyeccion` (historia + futuro +
banda + días + `fecha_key`) y `proyeccion_backtest` (**real vs. proyectado
sobre el pasado**, que es la única parte verificable). Más `ml/proyeccion.xlsx`
con el modelo por segmento, el desvío por paso y el backtest completo.

Y llega hasta el tablero sin trabajo manual:

- **`dim_calendario` se estira** hasta el último período proyectado. Sin eso,
  las filas del futuro apuntan a fechas que el calendario no tiene, caen en el
  renglón «en blanco» de la relación y la línea proyectada no se dibuja — sin
  ningún error que lo avise.
- **Medidas DAX generadas**: `Histórico`, `Proyectado`, `Banda baja`,
  `Banda alta`, `Ancho de banda %`, `Línea completa`, y sobre el backtest
  `Real (backtest)`, `Proyectado (backtest)`, `Desvío del backtest %` y
  `Desvío absoluto medio %`.
- **Gráfico en el reporte**: histórico, proyección y banda sombreada, primero
  en el HTML y en el Excel.

### TimesFM (opcional)

Entra como un backend más si se lo pide y está instalado; si no, la etapa no se
cae — lo deja escrito en `notas` y sigue con los demás.

```yaml
ml:
  tipo: serie
  # ...
  timesfm:
    checkpoint: google/timesfm-2.5-200m-pytorch   # Apache-2.0 · sirve para vender y desplegar
    contexto_maximo: 512
```

Requiere `pip install timesfm[torch]` y bajar el checkpoint. **No está en
`requirements.txt` a propósito**: son gigabytes que la mayoría de los proyectos
no necesita.

**Licencia.** El código es Apache-2.0 y los pesos **hasta la 2.5 también**. Los
de la **3.0** salen bajo `timesfm-non-commercial-license-v1.0`: investigación
sí, uso comercial y en producción **no**. Para investigar con ellos hay que
declararlo:

```yaml
  timesfm:
    checkpoint: google/timesfm-3.0-pytorch
    permitir_no_comercial: true      # investigación · NO entregable a un cliente
```

Esa corrida queda **marcada de punta a punta**: el resumen de la etapa dice
`⚠ PESOS NO COMERCIALES (investigación, no entregable)`, la app muestra un
aviso rojo, la bitácora de transformaciones lo registra como paso con aviso y
`salud.py` lo levanta como hallazgo de **severidad alta**. Es para que la
decisión no se filtre sin querer a una carpeta de entrega seis meses después,
cuando ya nadie se acuerda de qué checkpoint corrió.


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
│                    ml · proyeccion · metodos_serie · reporte · dax · powerbi · ia · justificacion · salud ·
│                    frescura · relevamiento · reuniones · transformaciones · auth · orquestador ·
│                    automatizacion · demos · cli · i18n
├── app/app.py       programa Streamlit (ES/EN/PT), misma familia visual que MV Data Governance
├── tests/           107 tests: motor, i18n, cuatro demos end-to-end, gate, reanudación, CLI, IA local, justificación,
│                    salud, cargas, relevamiento, reuniones, transformaciones, login, proyección de series
├── docs/DESPLIEGUE.md  puesta en marcha en servidor (para infraestructura del cliente)
├── Dockerfile · docker-compose.yml   despliegue en VM: la gente entra por navegador
├── run.sh · MV_DataEngineering.bat · requirements.txt · CLAUDE.md
```

La etapa Power BI usa `../daxlingo/dxl` (MV DAX Lab, en este mismo repo). Si no está,
la etapa se omite y el resto del pipeline sigue.
