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
| Credencial para el despliegue con login | `python -m mvde usuario <nombre>` |
| Levantar en servidor | `docker compose up -d --build` (ver `docs/DESPLIEGUE.md`) |
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
- `auth.py`: el login es OPCIONAL y se enciende solo si el despliegue declara `MVDE_USUARIOS` o `MVDE_USUARIOS_ARCHIVO`; sin eso el escritorio abre como siempre. PBKDF2-HMAC-SHA256 con sal por usuario, comparación en tiempo constante, cinco intentos y bloqueo. Falla CERRADO: variable declarada y credenciales ilegibles = nadie entra. No pasar hashes por un `.env` de Docker Compose: los interpola y los corta (ver `docs/DESPLIEGUE.md`).
- `frescura.py` (monitoreo de cargas): separa SIEMPRE la fecha del dato (máximo de la columna de fecha del negocio) de la fecha de carga (`_ingestado_en` que escribe bronze). El estado se juzga por el dato cuando existe, y sólo cae en la carga cuando la tabla no tiene columna de fecha. Ignora fechas futuras: un vencimiento a 90 días no es frescura. La frecuencia esperada se declara en `frescura` del YAML; la real se mide sobre `frescura_historial.json`.
- `relevamiento.py` + `textos_relevamiento.py`: catálogo de 48 preguntas al cliente, una por etapa del pipeline, con su «para qué sirve». `responder` y `aplicar_sugerencia` NO mutan el original. Las repreguntas locales miran la FORMA de la respuesta (vaga, sin número, sistema sin acceso), no el tema: funcionan sin IA. `sugerencias_yaml` sólo propone lo que tiene lectura única (dueño, frecuencia, hora, PII); lo ambiguo queda como nota para el que implementa. Las respuestas viven en `relevamiento.json` al lado del YAML.
- `reuniones.py`: la mejor entrada es el `.vtt` de Teams/Zoom/Meet/WebEx, que YA trae hablante y minuto. La transcripción de audio suelto NO separa hablantes y el módulo lo declara (`sin_hablantes`, aviso en la minuta): no inventar nombres. La minuta se arma por reglas con la cita y el minuto de cada ítem; la IA agrega un resumen POR ENCIMA, nunca reemplaza la evidencia. `sugerir_respuestas` propone respuestas del relevamiento a confirmar a mano (quedan en estado `repreguntar`, no cuentan como cerradas).
- `proyeccion.py` + `metodos_serie.py` (`ml.tipo: serie`): proyección de series con **backtest de origen móvil**. Reglas que no se relajan: (1) en cada corte se entrena SÓLO con lo anterior al corte; (2) la referencia es la **estacional ingenua** y todo backend se reporta con su mejora o su pérdida contra ella — si nadie le gana, se proyecta con ella y se dice; (3) las **bandas de desvío son empíricas** (percentiles del error relativo que ESE modelo tuvo por paso del horizonte), nunca una fórmula ni una campana supuesta, y van corridas por el sesgo medido; (4) el **ensemble** se pondera con los cortes ANTERIORES a cada corte que mide (ponderar con el corte que se está midiendo infla la precisión); (5) con `segmento` se proyecta **un modelo por segmento** más el TOTAL, y cada elección viene con su `porque` citando los números del backtest. Los ocho métodos de `metodos_serie.py` son la adaptación del motor de proyecciones de cobranzas (V32/Shiny) SIN su tabla de pesos por nombre de segmento y SIN el mes del calendario adentro: razonan por posición del ciclo, así el mismo código sirve para series diarias, mensuales o trimestrales. La salida entra a gold y al almacén como `proyeccion` (historia + futuro + banda) y `proyeccion_backtest` (real vs. proyectado sobre el pasado).
- `proyeccion.py` · **TimesFM** es un backend opcional (`ml.timesfm`), no una dependencia: si falta `torch` o el checkpoint, la etapa no se cae, lo deja escrito en `notas` y sigue con los demás. Los pesos hasta la 2.5 son Apache-2.0; **los de la 3.0 son licencia no comercial** (investigación sí, producción no) y el motor se niega a cargarlos salvo `permitir_no_comercial: true` declarado a propósito. Cuando ese permiso se usa, la corrida queda marcada en las cuatro superficies — `licencia_no_comercial: true` en el resultado, aviso en el resumen de la etapa, error rojo en la app, paso con aviso en la bitácora y hallazgo de severidad ALTA en `salud.py` — para que una corrida de investigación no termine entregada a un cliente por olvido.
- `transformaciones.py` arma la bitácora (técnico / criollo / impacto por paso) desde `resultados` y el YAML; sus textos viven en `textos_transformaciones.py` (se mezclan en `i18n._T`, así el test de paridad los cubre). Exporta HTML / Word (python-docx) / PDF (reportlab); si falta una biblioteca lo dice, no rompe.
