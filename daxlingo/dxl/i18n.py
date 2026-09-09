# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Textos trilingües (ES / EN / PT).

Todo texto de cara al usuario vive acá con las tres claves. La paridad está
cubierta por tests: si agregás una clave y le falta un idioma, el test rompe.
La misma tabla alimenta la app de escritorio; la landing tiene su espejo en
`web/assets/i18n.js` (también con test de paridad contra este archivo).
"""
from __future__ import annotations

IDIOMAS = ("es", "en", "pt")
NOMBRES_IDIOMA = {"es": "Español", "en": "English", "pt": "Português"}
IDIOMA_DEFECTO = "es"

T: dict[str, dict[str, str]] = {
    # ---- marca y encabezado -------------------------------------------
    "lema": {
        "es": "Tu modelo de Power BI, explicado, corregido y exportado.",
        "en": "Your Power BI model: explained, fixed and exported.",
        "pt": "Seu modelo de Power BI, explicado, corrigido e exportado.",
    },
    "idioma": {"es": "Idioma", "en": "Language", "pt": "Idioma"},
    # Ojo: este texto se inyecta dentro de un <div>, así que va en HTML, no en
    # markdown — los asteriscos saldrían literales.
    "sin_modelo": {
        "es": "Sin modelo cargado — empezá por la pestaña <b>Modelo</b>.",
        "en": "No model loaded — start on the <b>Model</b> tab.",
        "pt": "Sem modelo carregado — comece pela aba <b>Modelo</b>.",
    },
    "tablas": {"es": "Tablas", "en": "Tables", "pt": "Tabelas"},
    "columnas": {"es": "Columnas", "en": "Columns", "pt": "Colunas"},
    "medidas": {"es": "Medidas", "en": "Measures", "pt": "Medidas"},
    "relaciones": {"es": "Relaciones", "en": "Relationships", "pt": "Relações"},

    # ---- pestañas ------------------------------------------------------
    "tab_guia": {"es": "Guía", "en": "Guide", "pt": "Guia"},
    "tab_modelo": {"es": "Modelo", "en": "Model", "pt": "Modelo"},
    "tab_relaciones": {"es": "Relaciones", "en": "Relationships",
                       "pt": "Relações"},
    "tab_analizador": {"es": "Analizador", "en": "Analyzer",
                       "pt": "Analisador"},
    "tab_generar": {"es": "Generar DAX", "en": "Generate DAX",
                    "pt": "Gerar DAX"},
    "tab_explicar": {"es": "Explicador", "en": "Explainer",
                     "pt": "Explicador"},
    "tab_transformar": {"es": "Transformar", "en": "Transform",
                        "pt": "Transformar"},
    "tab_exportar": {"es": "Exportar", "en": "Export",
                     "pt": "Exportar"},
    "tab_fabric": {"es": "Fabric", "en": "Fabric", "pt": "Fabric"},
    "tab_overlay": {"es": "Asistente de pantalla",
                    "en": "Screen assistant",
                    "pt": "Assistente de tela"},
    "tab_academia": {"es": "Academia DAX", "en": "DAX Academy",
                     "pt": "Academia DAX"},
    "tab_herramientas": {"es": "Herramientas", "en": "Tools",
                         "pt": "Ferramentas"},
    "tab_licencia": {"es": "Licencia", "en": "License",
                     "pt": "Licença"},
    "tab_config": {"es": "Configuración", "en": "Settings",
                   "pt": "Configuração"},

    # ---- guía ----------------------------------------------------------
    "guia_titulo": {
        "es": "El ciclo completo, verificable",
        "en": "The full cycle, verifiable",
        "pt": "O ciclo completo, verificável",
    },
    "guia_ciclo": {
        "es": "**inspeccionar → modelar → construir → validar → verificar → exportar**",
        "en": "**inspect → model → build → validate → verify → export**",
        "pt": "**inspecionar → modelar → construir → validar → verificar → exportar**",
    },
    "guia_pasos": {
        "es": """
1. **Modelo** — cargá un `.pbit`, un proyecto **PBIP**, un `model.bim` o un
   `.pbix` (de un `.pbix` se lee el reporte y un catálogo parcial; el modelo
   tabular viaja en un binario propietario — la app te dice cómo obtener el
   completo).
2. **Relaciones** — el modelo dibujado: tablas, cardinalidades, calendario.
3. **Analizador** — reglas de buenas prácticas con severidad y arreglo; las
   automáticas se aplican con un clic.
4. **Generar DAX** — pedile medidas en tu idioma. Sin API key usa el motor
   de reglas local; con tu clave, pedidos libres con la IA que elijas. En
   ambos casos la expresión se **valida contra el catálogo**.
5. **Transformar** — renombrar con propagación, columnas calculadas, tabla
   de medidas, formatos.
6. **Exportar** — de vuelta a `.pbit` o **PBIP**, con **tablero automático**:
   KPIs, evolución, barras, dona, matriz y filtros.
7. **Fabric** — publicación directa por API o vía integración Git del PBIP.
8. **Asistente de pantalla** — F9 / Shift+F9 / Ctrl+F9 y lo que la IA
   propone se aplica acá con un clic.
9. **Academia DAX** — práctica por niveles con verificación instantánea.
""",
        "en": """
1. **Model** — load a `.pbit`, a **PBIP** project, a `model.bim` or a
   `.pbix` (from a `.pbix` we read the report and a partial catalog; its
   tabular model ships as a proprietary binary — the app tells you how to get
   the full one).
2. **Relationships** — the model drawn: tables, cardinality, calendar.
3. **Analyzer** — best-practice rules with severity and fix; the automatic
   ones apply in one click.
4. **Generate DAX** — ask for measures in your language. With no API key it
   uses the local rules engine; with your key, free-form requests through the
   AI you choose. Either way the expression is **validated against the
   catalog**.
5. **Transform** — rename with reference propagation, calculated columns,
   measures table, formats.
6. **Export** — back to `.pbit` or **PBIP**, with an **automatic report**:
   KPIs, trend, bars, donut, matrix and slicers.
7. **Fabric** — direct API publish or via the PBIP Git integration.
8. **Screen assistant** — F9 / Shift+F9 / Ctrl+F9, and whatever the AI
   proposes applies here in one click.
9. **DAX Academy** — levelled practice with instant checking.
""",
        "pt": """
1. **Modelo** — carregue um `.pbit`, um projeto **PBIP**, um `model.bim` ou
   um `.pbix` (de um `.pbix` lemos o relatório e um catálogo parcial; o modelo
   tabular vem num binário proprietário — o app explica como obter o
   completo).
2. **Relações** — o modelo desenhado: tabelas, cardinalidades, calendário.
3. **Analisador** — regras de boas práticas com severidade e correção; as
   automáticas se aplicam com um clique.
4. **Gerar DAX** — peça medidas no seu idioma. Sem API key usa o motor de
   regras local; com sua chave, pedidos livres com a IA que escolher. Nos dois
   casos a expressão é **validada contra o catálogo**.
5. **Transformar** — renomear com propagação, colunas calculadas, tabela de
   medidas, formatos.
6. **Exportar** — de volta a `.pbit` ou **PBIP**, com **painel automático**:
   KPIs, evolução, barras, rosca, matriz e filtros.
7. **Fabric** — publicação direta por API ou via integração Git do PBIP.
8. **Assistente de tela** — F9 / Shift+F9 / Ctrl+F9 e o que a IA propõe se
   aplica aqui com um clique.
9. **Academia DAX** — prática por níveis com verificação instantânea.
""",
    },
    "guia_demo": {
        "es": "La demo trae un modelo de ejemplo con 117 medidas y 20 tablas, "
              "listo en **Modelo**, sin subir nada.",
        "en": "The demo ships an example model with 117 measures and 20 "
              "tables, ready in **Model**, with nothing to upload.",
        "pt": "A demo traz um modelo de exemplo com 117 medidas e 20 tabelas, "
              "pronto em **Modelo**, sem enviar nada.",
    },

    # ---- modelo --------------------------------------------------------
    "cargar_modelo": {"es": "Cargar un modelo", "en": "Load a model",
                      "pt": "Carregar um modelo"},
    "arrastra": {
        "es": "Arrastrá un .pbit, .pbix, model.bim o un PBIP comprimido (.zip)",
        "en": "Drop a .pbit, .pbix, model.bim or a zipped PBIP (.zip)",
        "pt": "Arraste um .pbit, .pbix, model.bim ou um PBIP em .zip",
    },
    "btn_cargar": {"es": "Cargar archivo", "en": "Load file",
                   "pt": "Carregar arquivo"},
    "modelo_demo": {"es": "Modelo de ejemplo · 117 medidas, 20 tablas",
                    "en": "Example model · 117 measures, 20 tables",
                    "pt": "Modelo de exemplo · 117 medidas, 20 tabelas"},
    "btn_demo": {"es": "Cargar el modelo demo", "en": "Load the demo model",
                 "pt": "Carregar o modelo demo"},
    "no_se_pudo_cargar": {"es": "No se pudo cargar", "en": "Could not load",
                          "pt": "Não foi possível carregar"},
    "catalogo_parcial": {"es": "catálogo PARCIAL", "en": "PARTIAL catalog",
                         "pt": "catálogo PARCIAL"},
    "cambios_sesion": {
        "es": "Cambios aplicados en esta sesión:",
        "en": "Changes applied in this session:",
        "pt": "Mudanças aplicadas nesta sessão:",
    },
    "oculta": {"es": "Oculta", "en": "Hidden", "pt": "Oculta"},
    "calculada": {"es": "Calculada", "en": "Calculated", "pt": "Calculada"},
    "tipo": {"es": "Tipo", "en": "Type", "pt": "Tipo"},
    "columna": {"es": "Columna", "en": "Column", "pt": "Coluna"},
    "sin_formato": {"es": "sin formato", "en": "no format", "pt": "sem formato"},

    # ---- relaciones ----------------------------------------------------
    "mapa_modelo": {"es": "Mapa del modelo", "en": "Model map",
                    "pt": "Mapa do modelo"},
    "carga_primero": {"es": "Cargá un modelo primero.",
                      "en": "Load a model first.",
                      "pt": "Carregue um modelo primeiro."},
    "sin_relaciones": {
        "es": "El modelo no declara relaciones (o el catálogo es parcial).",
        "en": "The model declares no relationships (or the catalog is partial).",
        "pt": "O modelo não declara relações (ou o catálogo é parcial).",
    },
    "leyenda_grafo": {
        "es": "◆ = campo con relación. Cardinalidad en cada extremo: "
              "* = muchos, 1 = uno. Rojo doble = bidireccional (revisar). "
              "Punteada = inactiva. Verde = tabla de calendario. Σ = medidas.",
        "en": "◆ = field in a relationship. Cardinality at each end: "
              "* = many, 1 = one. Double red = bidirectional (review). "
              "Dashed = inactive. Green = date table. Σ = measures.",
        "pt": "◆ = campo com relação. Cardinalidade em cada ponta: "
              "* = muitos, 1 = um. Vermelho duplo = bidirecional (revisar). "
              "Tracejada = inativa. Verde = tabela de calendário. Σ = medidas.",
    },
    # El «+N más» del pie de cada tarjeta del mapa. Va traducido desde la UI
    # porque dxl/mapa.py no importa i18n (así se puede testear solo).
    "mapa_mas": {"es": "más", "en": "more", "pt": "mais"},

    # ---- analizador ----------------------------------------------------
    "buenas_practicas": {"es": "Buenas prácticas del modelo",
                         "en": "Model best practices",
                         "pt": "Boas práticas do modelo"},
    "salud": {"es": "Salud del modelo", "en": "Model health",
              "pt": "Saúde do modelo"},
    "hallazgos": {"es": "Hallazgos", "en": "Findings", "pt": "Achados"},
    "arreglables": {"es": "Arreglables en 1 clic", "en": "One-click fixes",
                    "pt": "Corrigíveis em 1 clique"},
    "por_que_importa": {"es": "Por qué importa", "en": "Why it matters",
                        "pt": "Por que importa"},
    "como_se_arregla": {"es": "Cómo se arregla", "en": "How to fix it",
                        "pt": "Como corrigir"},
    "arreglable_auto": {"es": "Arreglable automáticamente",
                        "en": "Fixable automatically",
                        "pt": "Corrigível automaticamente"},
    "btn_arreglar": {
        "es": "Aplicar todos los arreglos automáticos",
        "en": "Apply every automatic fix",
        "pt": "Aplicar todas as correções automáticas",
    },
    "cambios_aplicados": {"es": "cambio(s) aplicados.",
                          "en": "change(s) applied.",
                          "pt": "mudança(s) aplicadas."},
    "opinion_ia": {"es": "Opinión de la IA sobre este modelo",
                   "en": "AI opinion on this model",
                   "pt": "Opinião da IA sobre este modelo"},
    "consultando": {"es": "Consultando…", "en": "Asking…",
                    "pt": "Consultando…"},
    "sin_clave_opinion": {
        "es": "Con una API key (Configuración) también tenés la opinión de "
              "la IA sobre el modelo.",
        "en": "With an API key (Settings) you also get the AI's opinion on "
              "the model.",
        "pt": "Com uma API key (Configuração) você também recebe a opinião "
              "da IA sobre o modelo.",
    },

    # ---- generar -------------------------------------------------------
    "gen_titulo": {
        "es": "De tu idioma a DAX, sin inventar columnas",
        "en": "From your language to DAX, without inventing columns",
        "pt": "Do seu idioma para DAX, sem inventar colunas",
    },
    "gen_pregunta": {"es": "¿Qué medida necesitás?",
                     "en": "Which measure do you need?",
                     "pt": "Qual medida você precisa?"},
    "gen_ejemplos": {
        "es": "p. ej.: total de ventas · % del total · ventas vs año anterior "
              "· media móvil 3 meses · ranking de país por ventas",
        "en": "e.g.: total sales · % of total · sales vs last year · 3-month "
              "moving average · ranking of country by sales",
        "pt": "ex.: total de vendas · % do total · vendas vs ano anterior · "
              "média móvel 3 meses · ranking de país por vendas",
    },
    "gen_motor": {"es": "motor", "en": "engine", "pt": "motor"},
    "gen_porque": {"es": "Por qué", "en": "Why", "pt": "Por quê"},
    "gen_agregar": {"es": "Agregar esta medida al modelo",
                    "en": "Add this measure to the model",
                    "pt": "Adicionar esta medida ao modelo"},
    "formato": {"es": "formato", "en": "format", "pt": "formato"},

    # ---- explicador ----------------------------------------------------
    "exp_titulo": {"es": "Pegá DAX, salí entendiéndolo",
                   "en": "Paste DAX, walk away understanding it",
                   "pt": "Cole DAX, saia entendendo"},
    "exp_selector": {
        "es": "Explicar una medida del modelo o pegar DAX",
        "en": "Explain a model measure or paste DAX",
        "pt": "Explicar uma medida do modelo ou colar DAX",
    },
    "exp_pegar": {"es": "(pegar una expresión)", "en": "(paste an expression)",
                  "pt": "(colar uma expressão)"},
    "exp_expresion": {"es": "Expresión DAX", "en": "DAX expression",
                      "pt": "Expressão DAX"},
    "exp_nivel": {"es": "nivel", "en": "level", "pt": "nível"},
    "exp_funcion": {"es": "Función", "en": "Function", "pt": "Função"},
    "exp_que_hace": {"es": "Qué hace", "en": "What it does", "pt": "O que faz"},
    "exp_categoria": {"es": "Categoría", "en": "Category", "pt": "Categoria"},

    # ---- transformar ---------------------------------------------------
    "tr_titulo": {
        "es": "Transformaciones seguras (siempre sobre una copia)",
        "en": "Safe transformations (always on a copy)",
        "pt": "Transformações seguras (sempre sobre uma cópia)",
    },
    "tr_necesito_completo": {
        "es": "Necesito el modelo completo (.pbit / PBIP / .bim).",
        "en": "I need the full model (.pbit / PBIP / .bim).",
        "pt": "Preciso do modelo completo (.pbit / PBIP / .bim).",
    },
    "tr_renombrar": {
        "es": "Renombrar medida (propaga referencias)",
        "en": "Rename measure (propagates references)",
        "pt": "Renomear medida (propaga referências)",
    },
    "tr_medida": {"es": "Medida", "en": "Measure", "pt": "Medida"},
    "tr_nuevo_nombre": {"es": "Nuevo nombre", "en": "New name",
                        "pt": "Novo nome"},
    "tr_btn_renombrar": {"es": "Renombrar", "en": "Rename", "pt": "Renomear"},
    "tr_tabla_medidas": {"es": "Crear tabla de medidas",
                         "en": "Create measures table",
                         "pt": "Criar tabela de medidas"},
    "tr_btn_concentrar": {
        "es": "Concentrar todas las medidas en «_Medidas»",
        "en": "Move every measure into “_Medidas”",
        "pt": "Concentrar todas as medidas em “_Medidas”",
    },
    "tr_col_calculada": {"es": "Columna calculada", "en": "Calculated column",
                         "pt": "Coluna calculada"},
    "tr_tabla": {"es": "Tabla", "en": "Table", "pt": "Tabela"},
    "tr_nombre_col": {"es": "Nombre de la columna", "en": "Column name",
                      "pt": "Nome da coluna"},
    "tr_btn_agregar_col": {"es": "Agregar columna", "en": "Add column",
                           "pt": "Adicionar coluna"},
    "tr_formatos": {"es": "Formatos y claves", "en": "Formats and keys",
                    "pt": "Formatos e chaves"},
    "tr_btn_formatos": {
        "es": "Asignar formatos faltantes + ocultar claves",
        "en": "Assign missing formats + hide keys",
        "pt": "Atribuir formatos faltantes + ocultar chaves",
    },
    "nada_que_mover": {"es": "Nada que mover.", "en": "Nothing to move.",
                       "pt": "Nada a mover."},

    # ---- exportar ------------------------------------------------------
    "ex_titulo": {
        "es": "Exportar con tablero, filtros y navegación",
        "en": "Export with report, slicers and navigation",
        "pt": "Exportar com painel, filtros e navegação",
    },
    "ex_nombre": {"es": "Nombre del archivo", "en": "File name",
                  "pt": "Nome do arquivo"},
    "ex_medidas": {
        "es": "Medidas para el tablero automático (hasta 5; vacío = primeras 5)",
        "en": "Measures for the automatic report (up to 5; empty = first 5)",
        "pt": "Medidas para o painel automático (até 5; vazio = primeiras 5)",
    },
    "ex_que_reporte": {
        "es": "Qué reporte viaja en el archivo",
        "en": "Which report goes in the file",
        "pt": "Qual relatório vai no arquivo",
    },
    "ex_op_conservar": {
        "es": "Conservar mi reporte original con las correcciones (recomendado)",
        "en": "Keep my original report with the fixes (recommended)",
        "pt": "Manter meu relatório original com as correções (recomendado)",
    },
    "ex_op_tablero": {
        "es": "Reemplazarlo por un tablero de muestra generado (KPIs + evolución + barras + matriz)",
        "en": "Replace it with a generated sample dashboard (KPIs + trend + bars + matrix)",
        "pt": "Substituí-lo por um painel de amostra gerado (KPIs + evolução + barras + matriz)",
    },
    "ex_op_solo_modelo": {
        "es": "Solo el modelo, sin reporte",
        "en": "Only the model, no report",
        "pt": "Só o modelo, sem relatório",
    },
    "ex_aviso_tablero": {
        "es": "El archivo va a llevar SOLO el tablero generado: tus páginas y visuales originales NO viajan en este export. Para conservarlos, elegí la primera opción.",
        "en": "The file will carry ONLY the generated dashboard: your original pages and visuals do NOT travel in this export. To keep them, pick the first option.",
        "pt": "O arquivo vai levar SÓ o painel gerado: suas páginas e visuais originais NÃO viajam neste export. Para mantê-los, escolha a primeira opção.",
    },
    "ex_abre_sin_datos": {
        "es": "Un .pbit no lleva datos: al abrirlo, Desktop va a pedir «Actualizar» para cargarlos desde los orígenes (y «Actualizar ahora» si el modelo tiene tablas calculadas, como el calendario o los puentes). Hasta ahí, los visuales se ven «(En blanco)» — es normal, no es un archivo roto.",
        "en": "A .pbit carries no data: on open, Desktop will ask to “Refresh” to load it from the sources (and “Refresh now” if the model has calculated tables, like the calendar or the bridges). Until then, visuals show “(Blank)” — that is normal, not a broken file.",
        "pt": "Um .pbit não leva dados: ao abrir, o Desktop vai pedir «Atualizar» para carregá-los das origens (e «Atualizar agora» se o modelo tem tabelas calculadas, como o calendário ou as pontes). Até lá, os visuais aparecem «(Em branco)» — é normal, não é um arquivo quebrado.",
    },
    "ex_no_necesita_refrescar": {
        "es": "Este archivo lleva los datos adentro: abre y muestra todo sin Actualizar y sin buscar ningún archivo. Se puede mandar por mail y abre igual en cualquier máquina.",
        "en": "This file carries the data inside: it opens and shows everything without Refresh and without looking for any file. It can be emailed and opens the same on any machine.",
        "pt": "Este arquivo leva os dados dentro: abre e mostra tudo sem Atualizar e sem procurar nenhum arquivo. Pode ser enviado por e-mail e abre igual em qualquer máquina.",
    },
    "ex_empotrar": {
        "es": "Incluir los datos DENTRO del archivo (abre solo, sin buscar el Excel/CSV)",
        "en": "Include the data INSIDE the file (opens on its own, without looking for the Excel/CSV)",
        "pt": "Incluir os dados DENTRO do arquivo (abre sozinho, sem procurar o Excel/CSV)",
    },
    "ex_empotrar_ayuda": {
        "es": "Las filas viajan adentro del .pbit, en el mismo formato que usa «Introducir datos» de Power BI. El archivo abre y muestra todo en cualquier máquina, sin copiar planillas ni ajustar rutas. Destildalo si querés que el archivo refresque contra el Excel, el CSV o la base originales.",
        "en": "The rows travel inside the .pbit, in the same format Power BI's “Enter data” uses. The file opens and shows everything on any machine, without copying spreadsheets or adjusting paths. Untick it if you want the file to refresh against the original Excel, CSV or database.",
        "pt": "As linhas viajam dentro do .pbit, no mesmo formato que o «Inserir dados» do Power BI usa. O arquivo abre e mostra tudo em qualquer máquina, sem copiar planilhas nem ajustar caminhos. Desmarque se quiser que o arquivo atualize contra o Excel, o CSV ou o banco originais.",
    },
    "ex_no_se_entrega": {
        "es": "Este archivo NO se entrega: {n} controles en falta. Power BI lo va a rechazar al abrirlo. Arreglá lo que dice el detalle de arriba y volvé a exportar.",
        "en": "This file is NOT handed over: {n} checks failed. Power BI will reject it on open. Fix what the detail above says and export again.",
        "pt": "Este arquivo NÃO se entrega: {n} controlos em falta. O Power BI vai rejeitá-lo ao abrir. Corrija o que diz o detalhe acima e exporte de novo.",
    },
    "ex_bajar_igual": {
        "es": "Descargarlo igual (sabiendo que no va a abrir)",
        "en": "Download it anyway (knowing it will not open)",
        "pt": "Baixar mesmo assim (sabendo que não vai abrir)",
    },

    "ex_paginas_propias": {
        "es": "Páginas propias — escribí lo que querés ver además de lo automático",
        "en": "Your own pages — write what you want to see on top of the automatic ones",
        "pt": "Páginas próprias — escreva o que quer ver além do automático",
    },
    "ex_paginas_propias_ayuda": {
        "es": "Una línea por cosa. Cada nombre se busca en el modelo real: lo que no exista se avisa, no se inventa. Las páginas que escribas se AGREGAN a las generadas, no las reemplazan.",
        "en": "One line per item. Every name is looked up in the real model: whatever does not exist is reported, never invented. The pages you write are ADDED to the generated ones, they do not replace them.",
        "pt": "Uma linha por coisa. Cada nome é procurado no modelo real: o que não existir é avisado, não inventado. As páginas que escrever são ADICIONADAS às geradas, não as substituem.",
    },
    "ex_paginas_propias_campo": {
        "es": "Lo que querés que tenga el tablero",
        "en": "What you want the report to have",
        "pt": "O que quer que o painel tenha",
    },
    "ex_paginas_propias_ejemplo": {
        "es": "Página: Cobertura comercial\nKPIs: Total Visitas, Cobertura %\nLínea: Total Visitas\nBarras: Total Visitas por Especialidad\nTabla: Total Visitas, Total PXs por Ciudad\nFiltros: Especialidad, Ciudad",
        "en": "Page: Commercial coverage\nKPIs: Total Visits, Coverage %\nLine: Total Visits\nBars: Total Visits by Specialty\nTable: Total Visits, Total Rx by City\nFilters: Specialty, City",
        "pt": "Página: Cobertura comercial\nKPIs: Total Visitas, Cobertura %\nLinha: Total Visitas\nBarras: Total Visitas por Especialidade\nTabela: Total Visitas, Total PXs por Cidade\nFiltros: Especialidade, Cidade",
    },
    "ex_paginas_propias_ok": {
        "es": "{n} páginas propias listas: {lista}",
        "en": "{n} of your own pages ready: {lista}",
        "pt": "{n} páginas próprias prontas: {lista}",
    },
    "ex_paginas_propias_faltan": {
        "es": "No están en el modelo y quedaron afuera: {lista}. Escribilos como figuran en el panel de campos, o creá primero la medida en «Generar DAX».",
        "en": "Not in the model, so they were left out: {lista}. Write them as they appear in the field pane, or create the measure first in “Generate DAX”.",
        "pt": "Não estão no modelo e ficaram de fora: {lista}. Escreva-os como aparecem no painel de campos, ou crie primeiro a medida em «Gerar DAX».",
    },

    "ex_faltan_origenes": {
        "es": "{n} archivos de origen NO están donde las consultas los buscan ({lista}). El «Actualizar» de este export va a fallar y todo va a quedar en blanco. Arreglalo antes en la pestaña Power Query («Buscar y arreglar solo»).",
        "en": "{n} source files are NOT where the queries look for them ({lista}). This export's “Refresh” will fail and everything will stay blank. Fix it first in the Power Query tab (“Find and fix automatically”).",
        "pt": "{n} arquivos de origem NÃO estão onde as consultas os procuram ({lista}). O «Atualizar» deste export vai falhar e tudo vai ficar em branco. Corrija antes na aba Power Query («Procurar e corrigir sozinho»).",
    },
    "ex_marca": {
        "es": "Marca de la empresa (logo y colores)",
        "en": "Company brand (logo and colors)",
        "pt": "Marca da empresa (logo e cores)",
    },
    "ex_color_primario": {
        "es": "Color principal", "en": "Primary color", "pt": "Cor principal",
    },
    "ex_color_tinta": {
        "es": "Color del texto", "en": "Text color", "pt": "Cor do texto",
    },
    "ex_logo": {
        "es": "Logo (PNG o JPG)", "en": "Logo (PNG or JPG)",
        "pt": "Logo (PNG ou JPG)",
    },
    "ex_marca_detectada": {
        "es": "Colores tomados de tu logo: {primario} para encabezados y {tinta} para los textos. Podés cambiarlos abajo.",
        "en": "Colors taken from your logo: {primario} for headers and {tinta} for text. You can change them below.",
        "pt": "Cores tiradas do seu logo: {primario} para cabeçalhos e {tinta} para os textos. Pode alterá-las abaixo.",
    },
    "ex_marca_sin_color": {
        "es": "El logo no tiene un color propio (es blanco y negro o gris): elegí los colores a mano abajo.",
        "en": "The logo has no color of its own (black and white or grey): pick the colors by hand below.",
        "pt": "O logo não tem cor própria (preto e branco ou cinza): escolha as cores à mão abaixo.",
    },
    "ex_preparar": {
        "es": "Preparar el modelo antes de dibujar: calendario si falta, KPIs del negocio y arreglos automáticos",
        "en": "Prepare the model before drawing: calendar if missing, business KPIs and automatic fixes",
        "pt": "Preparar o modelo antes de desenhar: calendário se faltar, KPIs do negócio e correções automáticas",
    },
    "ex_preparado": {
        "es": "Lo que se preparó",
        "en": "What was prepared",
        "pt": "O que foi preparado",
    },
    "ex_usar_marca": {
        "es": "Aplicar la marca: logo arriba a la izquierda y el color en encabezados, tablas y filtros",
        "en": "Apply the brand: logo at the top left and the color on headers, tables and slicers",
        "pt": "Aplicar a marca: logo em cima à esquerda e a cor em cabeçalhos, tabelas e filtros",
    },
    "ex_btn_pbit": {"es": "⬇️ Generar .pbit", "en": "⬇️ Build .pbit",
                    "pt": "⬇️ Gerar .pbit"},
    "ex_btn_pbip": {"es": "⬇️ Generar PBIP (zip)", "en": "⬇️ Build PBIP (zip)",
                    "pt": "⬇️ Gerar PBIP (zip)"},
    "ex_descargar": {"es": "Descargar", "en": "Download", "pt": "Baixar"},
    "ex_nota_pbit": {
        "es": "Doble clic → Power BI Desktop → Archivo → Guardar como → .pbix",
        "en": "Double-click → Power BI Desktop → File → Save as → .pbix",
        "pt": "Duplo clique → Power BI Desktop → Arquivo → Salvar como → .pbix",
    },
    "ex_nota_pbip": {
        "es": "Formato de control de versiones — y el que entiende la "
              "integración Git de Fabric.",
        "en": "The version-control format — and the one Fabric's Git "
              "integration understands.",
        "pt": "Formato de controle de versão — e o que a integração Git do "
              "Fabric entende.",
    },

    # ---- fabric --------------------------------------------------------
    "fab_titulo": {"es": "Publicar en Microsoft Fabric",
                   "en": "Publish to Microsoft Fabric",
                   "pt": "Publicar no Microsoft Fabric"},
    "fab_token": {"es": "Token de Fabric (no se guarda)",
                  "en": "Fabric token (never stored)",
                  "pt": "Token do Fabric (não é salvo)"},
    "fab_workspace": {"es": "Workspace", "en": "Workspace", "pt": "Workspace"},
    "fab_nombre_item": {"es": "Nombre del ítem", "en": "Item name",
                        "pt": "Nome do item"},
    "fab_btn": {"es": "Publicar en Fabric", "en": "Publish to Fabric",
                "pt": "Publicar no Fabric"},
    "fab_publicando": {"es": "Publicando…", "en": "Publishing…",
                       "pt": "Publicando…"},
    "fab_error": {"es": "Fabric respondió con error",
                  "en": "Fabric returned an error",
                  "pt": "O Fabric respondeu com erro"},
    "fab_mcp_nota": {
        "es": "El MCP remoto oficial de Power BI también trabaja sobre "
              "modelos ya publicados — configuralo desde Herramientas.",
        "en": "Power BI's official remote MCP also works on already published "
              "models — set it up from Tools.",
        "pt": "O MCP remoto oficial do Power BI também funciona sobre modelos "
              "já publicados — configure em Ferramentas.",
    },

    # ---- overlay -------------------------------------------------------
    "ov_titulo": {
        "es": "DAX Overlay: capturá la pantalla, aplicá el resultado acá",
        "en": "DAX Overlay: capture the screen, apply the result here",
        "pt": "DAX Overlay: capture a tela, aplique o resultado aqui",
    },
    "ov_atajo": {"es": "Atajo", "en": "Shortcut", "pt": "Atalho"},
    "ov_que_hace": {"es": "Qué hace", "en": "What it does", "pt": "O que faz"},
    "ov_f9": {
        "es": "Captura **toda la pantalla** y la resuelve con la IA",
        "en": "Captures the **whole screen** and solves it with the AI",
        "pt": "Captura **a tela inteira** e resolve com a IA",
    },
    "ov_shift_f9": {
        "es": "Seleccionás un **rectángulo** con el mouse",
        "en": "You drag a **rectangle** with the mouse",
        "pt": "Você seleciona um **retângulo** com o mouse",
    },
    "ov_ctrl_f9": {
        "es": "Abre una ventana para **escribir la consulta**",
        "en": "Opens a window to **type your request**",
        "pt": "Abre uma janela para **escrever a consulta**",
    },
    "ov_limpiar_mem": {"es": "Limpia la memoria de capturas previas",
                       "en": "Clears the previous-capture memory",
                       "pt": "Limpa a memória de capturas anteriores"},
    "ov_explica": {
        "es": "Cada respuesta se explica **paso a paso** y queda en la "
              "**bandeja** de abajo: si trae medidas o columnas calculadas, "
              "se aplican al modelo cargado con un clic.",
        "en": "Every answer is explained **step by step** and lands in the "
              "**inbox** below: if it carries measures or calculated "
              "columns, they apply to the loaded model in one click.",
        "pt": "Cada resposta é explicada **passo a passo** e fica na "
              "**caixa** abaixo: se trouxer medidas ou colunas calculadas, "
              "elas se aplicam ao modelo carregado com um clique.",
    },
    "ov_escribir": {
        "es": "…o escribí la consulta acá mismo (sin overlay)",
        "en": "…or type your request right here (no overlay)",
        "pt": "…ou escreva a consulta aqui mesmo (sem overlay)",
    },
    "ov_placeholder": {
        "es": "p. ej.: necesito el margen % por categoría con semáforo, "
              "¿qué medidas armo?",
        "en": "e.g.: I need margin % by category with a traffic light, "
              "which measures should I build?",
        "pt": "ex.: preciso da margem % por categoria com semáforo, "
              "quais medidas eu crio?",
    },
    "ov_btn_resolver": {"es": "Resolver con la IA", "en": "Solve with the AI",
                        "pt": "Resolver com a IA"},
    "ov_bandeja": {"es": "Bandeja del overlay", "en": "Overlay inbox",
                   "pt": "Caixa do overlay"},
    "ov_vacia": {
        "es": "Sin resultados todavía. Usá el overlay o la consulta de arriba.",
        "en": "Nothing yet. Use the overlay or the box above.",
        "pt": "Nada ainda. Use o overlay ou a consulta acima.",
    },
    "ov_aplicar": {"es": "Aplicar", "en": "Apply", "pt": "Aplicar"},
    "ov_descartar": {"es": "Descartar", "en": "Discard", "pt": "Descartar"},
    "ov_tabla_destino": {"es": "Tabla destino", "en": "Target table",
                         "pt": "Tabela destino"},
    "ov_limpiar": {"es": "Limpiar resueltos", "en": "Clear resolved",
                   "pt": "Limpar resolvidos"},

    # ---- academia ------------------------------------------------------
    "ac_titulo": {
        "es": "Academia DAX — práctica con verificación instantánea",
        "en": "DAX Academy — practice with instant checking",
        "pt": "Academia DAX — prática com verificação instantânea",
    },
    "ac_nivel": {"es": "Nivel", "en": "Level", "pt": "Nível"},
    "ac_proximo": {"es": "Próximo nivel", "en": "Next level",
                   "pt": "Próximo nível"},
    "ac_faltan": {"es": "faltan", "en": "needs", "pt": "faltam"},
    "ac_maximo": {"es": "¡máximo!", "en": "maxed out!", "pt": "máximo!"},
    "ac_modelo_practica": {
        "es": "El modelo de práctica (común a todos los ejercicios)",
        "en": "The practice model (shared by every exercise)",
        "pt": "O modelo de prática (comum a todos os exercícios)",
    },
    "ac_tu_dax": {"es": "Tu DAX", "en": "Your DAX", "pt": "Seu DAX"},
    "ac_verificar": {"es": "Verificar", "en": "Check", "pt": "Verificar"},
    "ac_pista": {"es": "Pista", "en": "Hint", "pt": "Dica"},
    "ac_sin_pista": {"es": "Sin pista para este.", "en": "No hint for this one.",
                     "pt": "Sem dica para este."},

    # ---- herramientas --------------------------------------------------
    "he_titulo": {
        "es": "El stack del analista Power BI moderno, operativo",
        "en": "The modern Power BI analyst stack, operational",
        "pt": "O stack do analista Power BI moderno, operacional",
    },
    "he_detectada": {"es": "detectada", "en": "detected", "pt": "detectada"},
    "he_no_detectada": {"es": "no detectada acá", "en": "not detected here",
                        "pt": "não detectada aqui"},
    "he_sitio": {"es": "sitio", "en": "site", "pt": "site"},
    # Estados de la pestaña Herramientas. Antes había uno solo ("no detectada
    # acá") aplicado a las diez, incluidas las que son sitios web.
    "he_instalada": {"es": "instalada", "en": "installed", "pt": "instalada"},
    # «no detectada», no «no instalada»: la detección mira rutas conocidas,
    # el registro y el PATH — puede no encontrar una herramienta que SÍ está
    # (pasó con Power BI Desktop, en la máquina de quien lo usa todos los
    # días). Afirmar «no instalada» sobre esa base es mentirle al usuario
    # sobre su propia máquina.
    "he_falta": {"es": "no detectada", "en": "not detected",
                 "pt": "não detectada"},
    "he_web": {"es": "en el navegador", "en": "in the browser",
               "pt": "no navegador"},
    "he_incluida": {"es": "incluida en Desktop", "en": "included in Desktop",
                    "pt": "incluida no Desktop"},
    "he_lista": {"es": "la genera esta app", "en": "generated by this app",
                 "pt": "gerada por este app"},
    "he_sin_soporte": {"es": "solo en Windows", "en": "Windows only",
                       "pt": "so no Windows"},
    "he_abrir": {"es": "Abrir", "en": "Open", "pt": "Abrir"},
    "he_descargar": {"es": "Descargar", "en": "Download", "pt": "Baixar"},
    "he_resumen": {
        "es": "{n} de {total} del stack disponibles en esta máquina.",
        "en": "{n} of {total} in the stack available on this machine.",
        "pt": "{n} de {total} do stack disponiveis nesta maquina."},
    "he_para_daxstudio": {"es": "Para DAX Studio", "en": "For DAX Studio",
                          "pt": "Para o DAX Studio"},
    "he_para_tabular": {"es": "Para Tabular Editor / ALM Toolkit",
                        "en": "For Tabular Editor / ALM Toolkit",
                        "pt": "Para Tabular Editor / ALM Toolkit"},
    "he_para_mcp": {"es": "Para agentes de IA (MCP)", "en": "For AI agents (MCP)",
                    "pt": "Para agentes de IA (MCP)"},
    "he_para_desktop": {
        "es": "Para Power BI Desktop y Bravo",
        "en": "For Power BI Desktop and Bravo",
        "pt": "Para Power BI Desktop e Bravo",
    },
    "he_para_pbip": {
        "es": "Para VS Code, Service y Fabric (PBIP)",
        "en": "For VS Code, Service and Fabric (PBIP)",
        "pt": "Para VS Code, Service e Fabric (PBIP)",
    },
    "he_para_pq": {
        "es": "Para Power Query",
        "en": "For Power Query",
        "pt": "Para Power Query",
    },
    "he_pq_vacio": {
        "es": "El modelo cargado no trae consultas M (particiones calculadas "
              "o modelo armado desde cero).",
        "en": "The loaded model has no M queries (calculated partitions or a "
              "model built from scratch).",
        "pt": "O modelo carregado não traz consultas M (partições calculadas "
              "ou modelo montado do zero).",
    },
    "he_para_alm": {
        "es": "Para ALM Toolkit: las dos versiones del modelo",
        "en": "For ALM Toolkit: both versions of the model",
        "pt": "Para ALM Toolkit: as duas versões do modelo",
    },
    "he_alm_antes": {
        "es": "antes (como se cargó)",
        "en": "before (as loaded)",
        "pt": "antes (como foi carregado)",
    },
    "he_alm_despues": {
        "es": "después (con lo aplicado)",
        "en": "after (with changes applied)",
        "pt": "depois (com o aplicado)",
    },
    "he_alm_nota": {
        "es": "Compará antes.bim como source y despues.bim como target. Si "
              "todavía no aplicaste ningún arreglo, los dos son iguales.",
        "en": "Compare antes.bim as source and despues.bim as target. If you "
              "haven't applied any fix yet, both are identical.",
        "pt": "Compare antes.bim como source e despues.bim como target. Se "
              "ainda não aplicou nenhuma correção, os dois são iguais.",
    },
    "he_mcp_nota": {
        "es": "Incluye el MCP remoto oficial de Power BI, el MCP local de "
              "modelado y el servidor MCP de esta plataforma.",
        "en": "Includes Power BI's official remote MCP, the local modeling "
              "MCP and this platform's own MCP server.",
        "pt": "Inclui o MCP remoto oficial do Power BI, o MCP local de "
              "modelagem e o servidor MCP desta plataforma.",
    },
    "he_carga_medidas": {"es": "Cargá un modelo con medidas.",
                         "en": "Load a model with measures.",
                         "pt": "Carregue um modelo com medidas."},

    # ---- licencia ------------------------------------------------------
    "lic_titulo": {"es": "Licencia y edición", "en": "License and edition",
                   "pt": "Licença e edição"},
    "lic_edicion": {"es": "Edición", "en": "Edition", "pt": "Edição"},
    "lic_estado": {"es": "Estado", "en": "Status", "pt": "Status"},
    "lic_dias": {"es": "Días restantes", "en": "Days left",
                 "pt": "Dias restantes"},
    "lic_activa": {"es": "activa", "en": "active", "pt": "ativa"},
    "lic_vencida": {"es": "vencida", "en": "expired", "pt": "expirada"},
    "lic_pegar": {"es": "Pegá tu clave de licencia",
                  "en": "Paste your license key",
                  "pt": "Cole sua chave de licença"},
    "lic_activar": {"es": "Activar", "en": "Activate", "pt": "Ativar"},
    "lic_activada": {"es": "Licencia activada.", "en": "License activated.",
                     "pt": "Licença ativada."},
    "lic_invalida": {
        "es": "Clave inválida: revisá que esté completa y sin espacios.",
        "en": "Invalid key: check it is complete and has no spaces.",
        "pt": "Chave inválida: verifique se está completa e sem espaços.",
    },
    "lic_comprar": {"es": "Comprar una licencia", "en": "Buy a license",
                    "pt": "Comprar uma licença"},
    "lic_perpetua": {
        "es": "Licencia perpetua: no vence.",
        "en": "Perpetual license: it does not expire.",
        "pt": "Licença perpétua: não vence.",
    },
    "lic_mensual": {
        "es": "Suscripción mensual. La clave vale 32 días y se renueva sola "
              "mientras la suscripción siga activa: cuando falten pocos días, "
              "entrá al enlace de renovación y pegá la clave nueva.",
        "en": "Monthly subscription. The key lasts 32 days and renews itself "
              "while the subscription stays active: when it is close to "
              "expiring, open the renewal link and paste the new key.",
        "pt": "Assinatura mensal. A chave vale 32 dias e se renova sozinha "
              "enquanto a assinatura seguir ativa: quando faltarem poucos "
              "dias, abra o link de renovação e cole a chave nova.",
    },
    "lic_renovar": {"es": "Renovar la clave", "en": "Renew the key",
                    "pt": "Renovar a chave"},
    "lic_por_vencer": {
        "es": "Tu clave vence pronto. Renovala para no quedarte afuera.",
        "en": "Your key expires soon. Renew it so you are not locked out.",
        "pt": "Sua chave vence em breve. Renove para não ficar de fora.",
    },
    "lic_demo_activa": {
        "es": "Estás en la prueba gratuita de 7 días, con todo desbloqueado.",
        "en": "You are on the free 7-day trial, with everything unlocked.",
        "pt": "Você está no teste gratuito de 7 dias, com tudo liberado.",
    },
    "lic_demo_vencida": {
        "es": "La prueba de 7 días terminó. El analizador, el explicador y la "
              "Academia siguen abiertos; para generar DAX, transformar, "
              "exportar y publicar hace falta una licencia.",
        "en": "The 7-day trial is over. Analyzer, explainer and Academy stay "
              "open; generating DAX, transforming, exporting and publishing "
              "need a license.",
        "pt": "O teste de 7 dias terminou. Analisador, explicador e Academia "
              "seguem abertos; gerar DAX, transformar, exportar e publicar "
              "exigem uma licença.",
    },
    "lic_sin_licencia": {
        "es": "Esta copia necesita una licencia para funcionar. Comprala en "
              "la web y pegá la clave acá abajo.",
        "en": "This copy needs a license to run. Buy one on the site and "
              "paste the key below.",
        "pt": "Esta cópia precisa de uma licença para funcionar. Compre no "
              "site e cole a chave abaixo.",
    },
    "lic_sin_licencia_corto": {
        "es": "sin licencia", "en": "no license", "pt": "sem licença"},
    "lic_bloqueado": {
        "es": "Esta función necesita una licencia activa. Miralo en Licencia.",
        "en": "This feature needs an active license. See License.",
        "pt": "Este recurso precisa de uma licença ativa. Veja Licença.",
    },
    "lic_owner": {
        "es": "Edición OWNER: todo desbloqueado, sin vencimiento.",
        "en": "OWNER edition: everything unlocked, no expiry.",
        "pt": "Edição OWNER: tudo liberado, sem vencimento.",
    },

    # ---- configuración -------------------------------------------------
    "cfg_titulo": {"es": "Configuración", "en": "Settings",
                   "pt": "Configuração"},
    "cfg_ia": {"es": "IA — opcional, con tu propia clave (BYOK)",
               "en": "AI — optional, bring your own key (BYOK)",
               "pt": "IA — opcional, com sua própria chave (BYOK)"},
    "cfg_proveedor": {"es": "Proveedor de IA", "en": "AI provider",
                      "pt": "Provedor de IA"},
    "cfg_modelo": {"es": "Modelo", "en": "Model", "pt": "Modelo"},
    "cfg_clave": {
        "es": "API key (solo esta sesión; no se guarda en disco)",
        "en": "API key (this session only; never written to disk)",
        "pt": "API key (apenas esta sessão; não é gravada em disco)",
    },
    "cfg_probar": {"es": "Probar la conexión", "en": "Test the connection",
                   "pt": "Testar a conexão"},
    "cfg_ok": {"es": "Conexión correcta.", "en": "Connection OK.",
               "pt": "Conexão correta."},
    "cfg_nota_ia": {
        "es": "Si el modelo elegido está saturado, se cae solo al siguiente "
              "de la lista, con reintentos. Sin clave, todo lo demás "
              "funciona igual: motor de reglas, analizador, explicador y "
              "export.",
        "en": "If the chosen model is overloaded it falls back to the next "
              "one, with retries. With no key everything else works the "
              "same: rules engine, analyzer, explainer and export.",
        "pt": "Se o modelo escolhido estiver sobrecarregado, cai sozinho para "
              "o próximo, com novas tentativas. Sem chave, todo o resto "
              "funciona igual: motor de regras, analisador, explicador e "
              "exportação.",
    },
    "cfg_mcp": {"es": "Conexión MCP", "en": "MCP connection",
                "pt": "Conexão MCP"},
    "cfg_mcp_nota": {
        "es": "El archivo .mcp.json que se descarga acá sirve para cualquier "
              "agente que hable MCP (Claude, ChatGPT, Copilot, Gemini): les "
              "da acceso al MCP remoto oficial de Power BI, al MCP local de "
              "modelado y al servidor de esta plataforma.",
        "en": "The .mcp.json you download here works for any MCP-speaking "
              "agent (Claude, ChatGPT, Copilot, Gemini): it gives them "
              "Power BI's official remote MCP, the local modeling MCP and "
              "this platform's server.",
        "pt": "O .mcp.json baixado aqui serve para qualquer agente que fale "
              "MCP (Claude, ChatGPT, Copilot, Gemini): dá a eles o MCP "
              "remoto oficial do Power BI, o MCP local de modelagem e o "
              "servidor desta plataforma.",
    },
    "cfg_bandeja": {"es": "Bandeja del overlay", "en": "Overlay inbox",
                    "pt": "Caixa do overlay"},
    "cfg_historial": {"es": "Historial de cambios de la sesión:",
                      "en": "Session change log:",
                      "pt": "Histórico de mudanças da sessão:"},
    # ---- reglas del analizador ----------------------------------------
    # Título, por qué importa y cómo se arregla, de las 16 reglas. Vivían
    # hardcodeadas en español dentro de `analizador.py`, así que la pestaña
    # salía en español aunque la app estuviera en inglés o portugués.
    # {tabla} y {medida} los completa `analizador.describir()`.
    "regla_R00": {
        "es": "Catálogo parcial",
        "en": "Partial catalog",
        "pt": "Catálogo parcial",
    },
    "regla_R00_detalle": {
        "es": "Este catálogo salió del layout de un .pbix: solo se ve lo que los visuales usan, no el modelo completo.",
        "en": "This catalog came from a .pbix layout: you only see what the visuals use, not the whole model.",
        "pt": "Este catálogo veio do layout de um .pbix: só se vê o que os visuais usam, não o modelo completo.",
    },
    "regla_R00_arreglo": {
        "es": "Exportá el archivo como .pbit o PBIP desde Power BI Desktop para el análisis completo.",
        "en": "Export the file as .pbit or PBIP from Power BI Desktop for the full analysis.",
        "pt": "Exporte o arquivo como .pbit ou PBIP no Power BI Desktop para a análise completa.",
    },
    "regla_R01": {
        "es": "División con «/»",
        "en": "Division with “/”",
        "pt": "Divisão com «/»",
    },
    "regla_R01_detalle": {
        "es": "Una división con «/» revienta con dividendo 0 o BLANK y muestra infinito o error en el visual.",
        "en": "A “/” division blows up with a 0 or BLANK divisor and shows infinity or an error in the visual.",
        "pt": "Uma divisão com «/» quebra com divisor 0 ou BLANK e mostra infinito ou erro no visual.",
    },
    "regla_R01_arreglo": {
        "es": "Usar DIVIDE(numerador, denominador): devuelve BLANK ante cero, sin costo extra.",
        "en": "Use DIVIDE(numerator, denominator): it returns BLANK on zero, at no extra cost.",
        "pt": "Use DIVIDE(numerador, denominador): devolve BLANK diante de zero, sem custo extra.",
    },
    "regla_R02": {
        "es": "Medida sin formato",
        "en": "Measure with no format",
        "pt": "Medida sem formato",
    },
    "regla_R02_detalle": {
        "es": "Sin formatString, cada visual muestra el número como quiere: decimales de más, sin separador de miles, porcentajes crudos.",
        "en": "Without formatString, every visual renders the number its own way: stray decimals, no thousands separator, raw percentages.",
        "pt": "Sem formatString, cada visual mostra o número como quer: decimais a mais, sem separador de milhares, percentuais crus.",
    },
    "regla_R02_arreglo": {
        "es": "Asignar un formato explícito (#,0 · #,0.00 · 0.0 %).",
        "en": "Set an explicit format (#,0 · #,0.00 · 0.0 %).",
        "pt": "Atribuir um formato explícito (#,0 · #,0.00 · 0.0 %).",
    },
    "regla_R03": {
        "es": "IFERROR en medida",
        "en": "IFERROR in a measure",
        "pt": "IFERROR na medida",
    },
    "regla_R03_detalle": {
        "es": "IFERROR fuerza al motor a evaluar fila por fila esperando el error: caro y esconde problemas de datos.",
        "en": "IFERROR forces the engine to evaluate row by row waiting for the error: expensive, and it hides data problems.",
        "pt": "IFERROR força o motor a avaliar linha a linha esperando o erro: caro e esconde problemas de dados.",
    },
    "regla_R03_arreglo": {
        "es": "Prevenir el error (DIVIDE, buscar el caso borde) en vez de taparlo.",
        "en": "Prevent the error (DIVIDE, handle the edge case) instead of masking it.",
        "pt": "Prevenir o erro (DIVIDE, tratar o caso limite) em vez de tapá-lo.",
    },
    # Cifras del reporte, en la cabecera del Analizador.
    "paginas": {"es": "Páginas", "en": "Pages", "pt": "Páginas"},
    "visuales": {"es": "Visuales", "en": "Visuals", "pt": "Visuais"},
    "son_filtros": {"es": "son filtros", "en": "are slicers",
                    "pt": "são filtros"},

    # ---- reglas del REPORTE (páginas y visuales) ----------------------
    # Corren sobre Report/Layout, así que funcionan con un .pbix suelto:
    # son las únicas que dan hallazgos cuando el modelo no se puede leer.
    "regla_RP01": {
        "es": 'Visual duplicado en la misma página',
        "en": 'Duplicate visual on the same page',
        "pt": 'Visual duplicado na mesma página',
    },
    "regla_RP01_detalle": {
        "es": '«{tipo}» ({campo}) aparece {veces} veces en «{pagina}». Nadie pone el mismo gráfico dos veces a propósito: es copiar y pegar que quedó, y cada copia cuesta una consulta más al modelo.',
        "en": '«{tipo}» ({campo}) appears {veces} times on «{pagina}». Nobody duplicates a chart on purpose: it is left-over copy-paste, and every copy costs one more query against the model.',
        "pt": '«{tipo}» ({campo}) aparece {veces} vezes em «{pagina}». Ninguém duplica um gráfico de propósito: é copiar e colar que ficou, e cada cópia custa mais uma consulta ao modelo.',
    },
    "regla_RP01_arreglo": {
        "es": 'Copias a borrar: {sobran}. No se pierde ninguna cifra del tablero.',
        "en": 'Extra copies to delete: {sobran}. No figure is lost from the report.',
        "pt": 'Cópias a apagar: {sobran}. Nenhum número do painel se perde.',
    },
    "regla_RP02": {
        "es": 'Visual tapado: existe y no se puede usar',
        "en": 'Covered visual: it exists and cannot be used',
        "pt": 'Visual coberto: existe e não dá para usar',
    },
    "regla_RP02_detalle": {
        "es": 'En «{pagina}», «{encima}» tapa a «{debajo}» en un {solape}. Lo de abajo conserva su configuración y es inalcanzable con el mouse: el tablero tiene una función muerta que nadie sabe que está muerta.',
        "en": 'On «{pagina}», «{encima}» covers «{debajo}» by {solape}. The one underneath keeps its configuration and is unreachable with the mouse: the report has a dead feature nobody knows is dead.',
        "pt": 'Em «{pagina}», «{encima}» cobre «{debajo}» em {solape}. O de baixo mantém a configuração e fica inalcançável com o mouse: o painel tem uma função morta que ninguém sabe que está morta.',
    },
    "regla_RP02_arreglo": {
        "es": 'Mover uno de los dos. Si el de abajo ya no se usa, borrarlo — pero decidirlo, no dejarlo tapado.',
        "en": 'Move one of the two. If the one underneath is no longer used, delete it — but decide, do not leave it covered.',
        "pt": 'Mover um dos dois. Se o de baixo não se usa mais, apagar — mas decidir, não deixar coberto.',
    },
    "regla_RP03": {
        "es": 'Mismo filtro repetido en varias páginas',
        "en": 'Same filter repeated across pages',
        "pt": 'Mesmo filtro repetido em várias páginas',
    },
    "regla_RP03_detalle": {
        "es": 'El mismo «{tipo}» de {campo} está replicado en {paginas} páginas ({donde}). Cada copia se mantiene por separado, y basta que una quede distinta para que dos páginas muestren números que no cierran entre sí.',
        "en": 'The same «{tipo}» on {campo} is replicated across {paginas} pages ({donde}). Each copy is maintained separately, and one drifting is enough for two pages to show numbers that do not agree.',
        "pt": 'O mesmo «{tipo}» de {campo} está replicado em {paginas} páginas ({donde}). Cada cópia é mantida à parte, e basta uma ficar diferente para duas páginas mostrarem números que não batem.',
    },
    "regla_RP03_arreglo": {
        "es": 'Sincronizar segmentaciones (Ver → Sincronizar segmentaciones) o pasarlo al panel de filtros: se define una vez y vale para todo el reporte.',
        "en": 'Sync the slicers (View → Sync slicers) or move it to the filter pane: define it once and it holds for the whole report.',
        "pt": 'Sincronizar as segmentações (Ver → Sincronizar segmentações) ou passar para o painel de filtros: define-se uma vez e vale para o relatório todo.',
    },
    "regla_RP04": {
        "es": 'Mismo gráfico en varias páginas',
        "en": 'Same chart on several pages',
        "pt": 'Mesmo gráfico em várias páginas',
    },
    "regla_RP04_detalle": {
        "es": '«{tipo}» de {campo} aparece en {paginas} páginas ({donde}). Para quien mira el tablero son varias páginas que cuentan la misma historia con otro título.',
        "en": '«{tipo}» on {campo} appears on {paginas} pages ({donde}). To whoever reads the report these are several pages telling the same story under a different title.',
        "pt": '«{tipo}» de {campo} aparece em {paginas} páginas ({donde}). Para quem olha o painel são várias páginas contando a mesma história com outro título.',
    },
    "regla_RP04_arreglo": {
        "es": 'Consolidar en una sola página con un selector de período. Menos superficie que mantener y una sola versión de la verdad.',
        "en": 'Consolidate into a single page with a period selector. Less surface to maintain and one single version of the truth.',
        "pt": 'Consolidar numa página só com um seletor de período. Menos superfície para manter e uma só versão da verdade.',
    },
    "regla_RP05": {
        "es": 'Visual sin ningún dato',
        "en": 'Visual with no data at all',
        "pt": 'Visual sem nenhum dado',
    },
    "regla_RP05_detalle": {
        "es": '«{tipo}» en «{pagina}» no referencia ningún campo. Ocupa lugar, se consulta y no muestra nada.',
        "en": '«{tipo}» on «{pagina}» references no field at all. It takes up space, gets queried, and shows nothing.',
        "pt": '«{tipo}» em «{pagina}» não referencia nenhum campo. Ocupa lugar, é consultado e não mostra nada.',
    },
    "regla_RP05_arreglo": {
        "es": 'Asignarle campos o borrarlo.',
        "en": 'Give it fields or delete it.',
        "pt": 'Atribuir campos ou apagar.',
    },
    "regla_RP06": {
        "es": 'Power BI está generando tablas de fecha ocultas',
        "en": 'Power BI is generating hidden date tables',
        "pt": 'Power BI está gerando tabelas de data ocultas',
    },
    "regla_RP06_detalle": {
        "es": 'Tablas de fecha automática detectadas: {cuantas}, del tipo «{ejemplo}». Power BI crea una por CADA campo de fecha cuando «Auto date/time» está activo: inflan el modelo, no se pueden controlar y no aparecen en la interfaz.',
        "en": 'Auto date tables found: {cuantas}, like «{ejemplo}». Power BI creates one for EVERY date field when «Auto date/time» is on: they bloat the model, cannot be controlled and never show up in the interface.',
        "pt": 'Tabelas de data automática detectadas: {cuantas}, do tipo «{ejemplo}». O Power BI cria uma para CADA campo de data quando «Auto date/time» está ligado: incham o modelo, não dá para controlar e não aparecem na interface.',
    },
    "regla_RP06_arreglo": {
        "es": 'Archivo → Opciones → Carga de datos → desactivar «Auto date/time», y usar una tabla de calendario propia marcada como tabla de fechas.',
        "en": 'File → Options → Data load → turn off «Auto date/time», and use your own calendar table marked as the date table.',
        "pt": 'Arquivo → Opções → Carga de dados → desativar «Auto date/time» e usar uma tabela de calendário própria marcada como tabela de datas.',
    },
    "regla_RP08": {
        "es": 'Página recargada de visuales',
        "en": 'Page overloaded with visuals',
        "pt": 'Página sobrecarregada de visuais',
    },
    "regla_RP08_detalle": {
        "es": '«{pagina}» tiene {cuantos} visuales. Cada uno dispara su propia consulta al modelo y el render espera a la última, así que la página tarda en abrir; y quien la mira no sabe por dónde empezar. Como referencia, hasta {comodos} se lee cómodo.',
        "en": '«{pagina}» has {cuantos} visuals. Each one fires its own query against the model and the render waits for the last, so the page is slow to open; and whoever reads it does not know where to start. As a reference, up to {comodos} reads comfortably.',
        "pt": '«{pagina}» tem {cuantos} visuais. Cada um dispara a sua própria consulta ao modelo e o render espera pelo último, então a página demora a abrir; e quem olha não sabe por onde começar. Como referência, até {comodos} lê-se confortável.',
    },
    "regla_RP08_arreglo": {
        "es": 'Dejar arriba la idea principal y mandar el detalle a una página aparte con drill-through. Lo que no sirve para decidir, se saca.',
        "en": 'Keep the main idea at the top and move the detail to a separate page with drill-through. Whatever does not help decide, remove it.',
        "pt": 'Deixar em cima a ideia principal e mandar o detalhe para outra página com drill-through. O que não serve para decidir, tira-se.',
    },
    "regla_RP07": {
        "es": 'Páginas ocultas',
        "en": 'Hidden pages',
        "pt": 'Páginas ocultas',
    },
    "regla_RP07_detalle": {
        "es": 'Páginas ocultas: {cuantas} ({donde}). No siempre es un error —se usan para tooltips y drill-through— pero una página oculta que nadie recuerda se sigue refrescando sin que nadie la mire.',
        "en": 'Hidden pages: {cuantas} ({donde}). Not always a mistake — they back tooltips and drill-through — but a hidden page nobody remembers keeps refreshing with nobody looking at it.',
        "pt": 'Páginas ocultas: {cuantas} ({donde}). Nem sempre é erro — servem para tooltips e drill-through — mas uma página oculta que ninguém lembra continua sendo atualizada sem ninguém olhar.',
    },
    "regla_RP07_arreglo": {
        "es": 'Confirmar que cada una respalda un tooltip o un drill-through. Las que no, borrarlas.',
        "en": 'Confirm each one backs a tooltip or a drill-through. Delete the ones that do not.',
        "pt": 'Confirmar que cada uma serve a um tooltip ou drill-through. As que não, apagar.',
    },

    "regla_R04": {
        "es": "FILTER sobre tabla entera",
        "en": "FILTER over a whole table",
        "pt": "FILTER sobre tabela inteira",
    },
    "regla_R04_detalle": {
        "es": "FILTER('{tabla}', …) materializa la tabla completa dentro de CALCULATE cuando un filtro de columna alcanza.",
        "en": "FILTER('{tabla}', …) materialises the entire table inside CALCULATE when a column filter would do.",
        "pt": "FILTER('{tabla}', …) materializa a tabela inteira dentro de CALCULATE quando um filtro de coluna bastaria.",
    },
    "regla_R04_arreglo": {
        "es": "Filtrar la columna (Tabla[Col] = valor) o usar KEEPFILTERS(VALUES(Tabla[Col])).",
        "en": "Filter the column (Table[Col] = value) or use KEEPFILTERS(VALUES(Table[Col])).",
        "pt": "Filtrar a coluna (Tabela[Col] = valor) ou usar KEEPFILTERS(VALUES(Tabela[Col])).",
    },
    "regla_R05": {
        "es": "Medida duplicada",
        "en": "Duplicate measure",
        "pt": "Medida duplicada",
    },
    "regla_R05_detalle": {
        "es": "Tiene exactamente la misma expresión que [{medida}].",
        "en": "It has exactly the same expression as [{medida}].",
        "pt": "Tem exatamente a mesma expressão que [{medida}].",
    },
    "regla_R05_arreglo": {
        "es": "Dejar una sola y referenciarla desde la otra si hace falta el alias.",
        "en": "Keep one and reference it from the other if you need the alias.",
        "pt": "Deixar uma só e referenciá-la a partir da outra se precisar do alias.",
    },
    "regla_R06": {
        "es": "Espacios en el nombre",
        "en": "Spaces in the name",
        "pt": "Espaços no nome",
    },
    "regla_R06_detalle": {
        "es": "El nombre empieza o termina con espacios: invisible en el panel y fuente de referencias rotas.",
        "en": "The name starts or ends with spaces: invisible in the field pane and a source of broken references.",
        "pt": "O nome começa ou termina com espaços: invisível no painel e fonte de referências quebradas.",
    },
    "regla_R06_arreglo": {
        "es": "Renombrar sin espacios en los bordes.",
        "en": "Rename it without leading or trailing spaces.",
        "pt": "Renomear sem espaços nas bordas.",
    },
    "regla_R07": {
        "es": "Columna calculada",
        "en": "Calculated column",
        "pt": "Coluna calculada",
    },
    "regla_R07_detalle": {
        "es": "Las columnas calculadas se materializan en el modelo y no se comprimen tan bien como las nativas; casi siempre hay una versión en Power Query o una medida.",
        "en": "Calculated columns are materialised in the model and compress worse than native ones; there is almost always a Power Query version or a measure.",
        "pt": "As colunas calculadas são materializadas no modelo e comprimem pior que as nativas; quase sempre há uma versão no Power Query ou uma medida.",
    },
    "regla_R07_arreglo": {
        "es": "Mover el cálculo a Power Query (mejor compresión) o convertirlo en medida si es agregable.",
        "en": "Move the calculation to Power Query (better compression) or turn it into a measure if it aggregates.",
        "pt": "Mover o cálculo para o Power Query (melhor compressão) ou convertê-lo em medida se for agregável.",
    },
    "regla_R08": {
        "es": "Clave foránea visible",
        "en": "Visible foreign key",
        "pt": "Chave estrangeira visível",
    },
    "regla_R08_detalle": {
        "es": "Las columnas que solo existen para relacionar tablas confunden en el panel de campos y tientan a sumarlas.",
        "en": "Columns that exist only to relate tables clutter the field pane and tempt people to sum them.",
        "pt": "As colunas que só existem para relacionar tabelas confundem no painel de campos e tentam a somá-las.",
    },
    "regla_R08_arreglo": {
        "es": "Ocultarla (isHidden). El filtro sigue funcionando igual.",
        "en": "Hide it (isHidden). The relationship keeps working exactly the same.",
        "pt": "Ocultá-la (isHidden). O filtro continua funcionando igual.",
    },
    "regla_R09": {
        "es": "Relación bidireccional",
        "en": "Bidirectional relationship",
        "pt": "Relação bidirecional",
    },
    "regla_R09_detalle": {
        "es": "El filtro cruzado en ambas direcciones genera ambigüedad de caminos y resultados que cambian según el visual.",
        "en": "Cross-filtering in both directions creates ambiguous paths and results that change from one visual to another.",
        "pt": "O filtro cruzado nas duas direções gera ambiguidade de caminhos e resultados que mudam conforme o visual.",
    },
    "regla_R09_arreglo": {
        "es": "Volver a dirección simple y resolver el caso puntual con CROSSFILTER dentro de la medida que lo necesite.",
        "en": "Go back to single direction and solve the specific case with CROSSFILTER inside the measure that needs it.",
        "pt": "Voltar à direção simples e resolver o caso pontual com CROSSFILTER dentro da medida que precisar.",
    },
    "regla_R10": {
        "es": "Relación muchos a muchos",
        "en": "Many-to-many relationship",
        "pt": "Relação muitos para muitos",
    },
    "regla_R10_detalle": {
        "es": "Las relaciones N:N ocultan duplicados en las claves y degradan el rendimiento del motor.",
        "en": "N:N relationships hide duplicate keys and degrade engine performance.",
        "pt": "As relações N:N escondem duplicados nas chaves e degradam o desempenho do motor.",
    },
    "regla_R10_arreglo": {
        "es": "Interponer una tabla puente con la clave única (esquema estrella).",
        "en": "Put a bridge table with the unique key in between (star schema).",
        "pt": "Interpor uma tabela ponte com a chave única (esquema estrela).",
    },
    "regla_R11": {
        "es": "Relación inactiva",
        "en": "Inactive relationship",
        "pt": "Relação inativa",
    },
    "regla_R11_detalle": {
        "es": "Está definida pero apagada: solo actúa vía USERELATIONSHIP.",
        "en": "It is defined but switched off: it only applies through USERELATIONSHIP.",
        "pt": "Está definida mas desligada: só atua via USERELATIONSHIP.",
    },
    "regla_R11_arreglo": {
        "es": "Confirmar que alguna medida la usa; si no, eliminarla.",
        "en": "Confirm some measure uses it; if not, delete it.",
        "pt": "Confirmar que alguma medida a usa; se não, eliminá-la.",
    },
    "regla_R12": {
        "es": "Tabla sin relaciones",
        "en": "Table with no relationships",
        "pt": "Tabela sem relações",
    },
    "regla_R12_detalle": {
        "es": "No participa de ninguna relación: sus filtros no viajan a ninguna otra tabla.",
        "en": "It takes part in no relationship: its filters never reach any other table.",
        "pt": "Não participa de nenhuma relação: seus filtros não chegam a nenhuma outra tabela.",
    },
    "regla_R12_arreglo": {
        "es": "Relacionarla al modelo o, si es tabla auxiliar, ocultarla.",
        "en": "Relate it to the model or, if it is a helper table, hide it.",
        "pt": "Relacioná-la ao modelo ou, se for tabela auxiliar, ocultá-la.",
    },
    "regla_R13": {
        "es": "Auto date/time activo",
        "en": "Auto date/time on",
        "pt": "Auto date/time ativo",
    },
    "regla_R13_detalle": {
        "es": "Power BI creó tablas de calendario ocultas por cada columna de fecha (LocalDateTable_*): infla el modelo y duplica lógica.",
        "en": "Power BI created a hidden date table for every date column (LocalDateTable_*): it bloats the model and duplicates logic.",
        "pt": "O Power BI criou tabelas de calendário ocultas para cada coluna de data (LocalDateTable_*): infla o modelo e duplica lógica.",
    },
    "regla_R13_arreglo": {
        "es": "Desactivar Auto date/time y usar una única tabla de calendario marcada como tabla de fechas.",
        "en": "Turn Auto date/time off and use a single date table marked as such.",
        "pt": "Desativar o Auto date/time e usar uma única tabela de calendário marcada como tabela de datas.",
    },
    "regla_R14": {
        "es": "Sin tabla de calendario",
        "en": "No date table",
        "pt": "Sem tabela de calendário",
    },
    "regla_R14_detalle": {
        "es": "Hay columnas de fecha pero ninguna tabla de calendario marcada: la inteligencia de tiempo (YTD, año anterior) puede devolver resultados incorrectos sin avisar.",
        "en": "There are date columns but no marked date table: time intelligence (YTD, previous year) can return wrong results with no warning.",
        "pt": "Há colunas de data mas nenhuma tabela de calendário marcada: a inteligência de tempo (YTD, ano anterior) pode devolver resultados incorretos sem avisar.",
    },
    "regla_R14_arreglo": {
        "es": "Crear una tabla de calendario continua y marcarla como tabla de fechas.",
        "en": "Create a continuous date table and mark it as the date table.",
        "pt": "Criar uma tabela de calendário contínua e marcá-la como tabela de datas.",
    },

    "regla_R20": {
        "es": "Calendario sin marcar ni ordenar",
        "en": "Date table not marked or sorted",
        "pt": "Calendário sem marcar nem ordenar",
    },
    "regla_R20_detalle": {
        "es": "Hay tabla de fechas, pero Power BI no la reconoce como tal: sin la marca de tabla de fechas y su clave, TOTALYTD y SAMEPERIODLASTYEAR devuelven en blanco; sin columna de orden, los meses salen alfabéticos (abril antes que enero). Un dataset que trae su propia hoja de calendario llega siempre así, y el archivo abre igual — los números están mal sin que nada avise.",
        "en": "There is a date table, but Power BI does not recognise it as one: without the date-table mark and its key, TOTALYTD and SAMEPERIODLASTYEAR return blank; without a sort column, months come out alphabetically (April before January). A dataset that brings its own calendar sheet always arrives like this, and the file opens all the same — the numbers are wrong with nothing warning you.",
        "pt": "Há tabela de datas, mas o Power BI não a reconhece como tal: sem a marca de tabela de datas e a sua chave, TOTALYTD e SAMEPERIODLASTYEAR devolvem em branco; sem coluna de ordem, os meses saem alfabéticos (abril antes de janeiro). Um dataset que traz a sua própria folha de calendário chega sempre assim, e o arquivo abre do mesmo jeito — os números estão mal sem que nada avise.",
    },
    "regla_R20_arreglo": {
        "es": "Marcarla como tabla de fechas, poner la clave en su columna de fecha y ordenar cada etiqueta de período por su columna numérica.",
        "en": "Mark it as the date table, set the key on its date column and sort every period label by its numeric column.",
        "pt": "Marcá-la como tabela de datas, pôr a chave na sua coluna de data e ordenar cada etiqueta de período pela sua coluna numérica.",
    },
    "regla_R15": {
        "es": "Medidas dispersas",
        "en": "Scattered measures",
        "pt": "Medidas dispersas",
    },
    "regla_R15_detalle": {
        "es": "Las medidas viven repartidas en tablas de datos; el panel de campos mezcla modelo y cálculos.",
        "en": "Measures live spread across data tables; the field pane mixes model and calculations.",
        "pt": "As medidas vivem espalhadas por tabelas de dados; o painel de campos mistura modelo e cálculos.",
    },
    "regla_R15_arreglo": {
        "es": "Concentrarlas en una tabla de medidas dedicada.",
        "en": "Concentrate them in a dedicated measures table.",
        "pt": "Concentrá-las numa tabela de medidas dedicada.",
    },
    "regla_R18": {
        "es": "CALCULATE que pisa el contexto del visual",
        "en": "CALCULATE that overrides the visual's context",
        "pt": "CALCULATE que sobrescreve o contexto do visual",
    },
    "regla_R18_detalle": {
        "es": "La medida fija «{columna}» dentro de un CALCULATE sin KEEPFILTERS. Power BI expande ese filtro a ALL sobre la columna, así que reemplaza —no cruza— el filtro que viene del visual: en una tabla o un gráfico abierto por esa misma columna, todas las filas muestran el MISMO número. No da error y el valor es plausible, que es lo que lo vuelve difícil de ver.",
        "en": "The measure pins “{columna}” inside a CALCULATE without KEEPFILTERS. Power BI expands that filter to ALL over the column, so it replaces — rather than intersects — the filter coming from the visual: in a table or chart broken down by that same column, every row shows the SAME number. It raises no error and the value looks plausible, which is what makes it hard to spot.",
        "pt": "A medida fixa «{columna}» dentro de um CALCULATE sem KEEPFILTERS. O Power BI expande esse filtro para ALL sobre a coluna, então ele substitui — não cruza — o filtro que vem do visual: numa tabela ou gráfico aberto por essa mesma coluna, todas as linhas mostram o MESMO número. Não dá erro e o valor é plausível, que é o que o torna difícil de ver.",
    },
    "regla_R18_arreglo": {
        "es": "Envolver el predicado en KEEPFILTERS: CALCULATE ( ..., KEEPFILTERS ( Tabla[Col] = \"x\" ) ). Así los dos filtros se cruzan y cada fila muestra lo suyo. Si la intención era ignorar el visual a propósito, dejarlo y decirlo en el nombre de la medida.",
        "en": "Wrap the predicate in KEEPFILTERS: CALCULATE ( ..., KEEPFILTERS ( Table[Col] = \"x\" ) ). Both filters then intersect and each row shows its own value. If ignoring the visual was intentional, keep it and say so in the measure name.",
        "pt": "Envolver o predicado em KEEPFILTERS: CALCULATE ( ..., KEEPFILTERS ( Tabela[Col] = \"x\" ) ). Assim os dois filtros se cruzam e cada linha mostra o seu. Se ignorar o visual era intencional, manter e dizê-lo no nome da medida.",
    },
    "regla_R19": {
        "es": "Variación interanual sin guardia de comparabilidad",
        "en": "Year-over-year change with no comparability guard",
        "pt": "Variação interanual sem guarda de comparabilidade",
    },
    "regla_R19_detalle": {
        "es": "La medida compara contra el mismo período del año anterior, pero no comprueba que ese período exista completo. SAMEPERIODLASTYEAR devuelve SÓLO las fechas que hay en el calendario: si el modelo arranca a mitad de la serie, el lado anterior queda corto y la cuenta compara —por ejemplo— dieciocho meses contra seis. El resultado es un porcentaje enorme que parece un crecimiento espectacular y es puro artefacto del año incompleto.",
        "en": "The measure compares against the same period last year, but does not check that the period exists in full. SAMEPERIODLASTYEAR returns ONLY the dates present in the calendar: if the model starts mid-series, the previous side comes up short and the calculation compares — say — eighteen months against six. The result is a huge percentage that looks like spectacular growth and is pure incomplete-year artifact.",
        "pt": "A medida compara contra o mesmo período do ano anterior, mas não verifica que esse período exista completo. SAMEPERIODLASTYEAR devolve SÓ as datas que há no calendário: se o modelo começa no meio da série, o lado anterior fica curto e a conta compara — por exemplo — dezoito meses contra seis. O resultado é uma percentagem enorme que parece um crescimento espetacular e é puro artefacto do ano incompleto.",
    },
    "regla_R19_arreglo": {
        "es": "Contar los días de cada lado y devolver BLANK cuando no coinciden: VAR DiasHoy = COUNTROWS ( VALUES ( Calendario[Fecha] ) ), VAR DiasAntes = CALCULATE ( COUNTROWS ( VALUES ( Calendario[Fecha] ) ), SAMEPERIODLASTYEAR ( Calendario[Fecha] ) ), y RETURN IF ( DiasHoy = DiasAntes, ... ). Una celda vacía dice «no comparable»; un número inflado dice una mentira con cara de dato.",
        "en": "Count the days on each side and return BLANK when they differ: VAR DiasHoy = COUNTROWS ( VALUES ( Calendar[Date] ) ), VAR DiasAntes = CALCULATE ( COUNTROWS ( VALUES ( Calendar[Date] ) ), SAMEPERIODLASTYEAR ( Calendar[Date] ) ), then RETURN IF ( DiasHoy = DiasAntes, ... ). An empty cell says “not comparable”; an inflated number tells a lie shaped like data.",
        "pt": "Contar os dias de cada lado e devolver BLANK quando não coincidem: VAR DiasHoy = COUNTROWS ( VALUES ( Calendario[Data] ) ), VAR DiasAntes = CALCULATE ( COUNTROWS ( VALUES ( Calendario[Data] ) ), SAMEPERIODLASTYEAR ( Calendario[Data] ) ), e RETURN IF ( DiasHoy = DiasAntes, ... ). Uma célula vazia diz «não comparável»; um número inflado diz uma mentira com cara de dado.",
    },
    "regla_R17": {
        "es": "El origen apunta a una carpeta personal",
        "en": "The source points to a personal folder",
        "pt": "A origem aponta para uma pasta pessoal",
    },
    "regla_R17_detalle": {
        "es": "La consulta lee de «{ruta}», una ruta con el usuario y las carpetas de una máquina concreta (OneDrive, Documentos, Escritorio). El archivo abre igual porque los datos ya están importados, pero al Actualizar Power BI corta con «No se puede encontrar una parte de la ruta de acceso» apenas el archivo se mueve, se renombra, lo sincroniza OneDrive en otro lado o alguien abre el informe en otra PC.",
        "en": "The query reads from “{ruta}”, a path with the user name and folders of one specific machine (OneDrive, Documents, Desktop). The file still opens because the data is already imported, but on Refresh Power BI stops with “Could not find a part of the path” as soon as the file moves, is renamed, OneDrive syncs it elsewhere, or someone opens the report on another PC.",
        "pt": "A consulta lê de «{ruta}», um caminho com o usuário e as pastas de uma máquina específica (OneDrive, Documentos, Área de Trabalho). O arquivo abre mesmo assim porque os dados já estão importados, mas ao Atualizar o Power BI para com «Não foi possível encontrar parte do caminho» assim que o arquivo é movido, renomeado, sincronizado pelo OneDrive noutro lugar, ou aberto em outro PC.",
    },
    "regla_R17_arreglo": {
        "es": "Poner los archivos en una carpeta compartida (OneDrive/SharePoint como URL, o una unidad de red) y repuntar los orígenes ahí; o dejar la carpeta en un parámetro de Power Query para cambiarla en un solo lugar. Las dos cosas se hacen desde la pestaña Power Query de este programa.",
        "en": "Put the files in a shared folder (OneDrive/SharePoint as a URL, or a network drive) and repoint the sources there; or keep the folder in a Power Query parameter so it changes in one place. Both are available in this program's Power Query tab.",
        "pt": "Colocar os arquivos numa pasta compartilhada (OneDrive/SharePoint como URL, ou uma unidade de rede) e reapontar as origens para lá; ou deixar a pasta num parâmetro do Power Query para mudá-la num só lugar. As duas coisas estão na aba Power Query deste programa.",
    },
    "or_titulo": {
        "es": "De dónde lee cada consulta",
        "en": "Where each query reads from",
        "pt": "De onde cada consulta lê",
    },
    "or_lema": {
        "es": "Si al Actualizar Power BI dice «No se puede encontrar una parte de la ruta de acceso», es esto: el archivo ya no está donde la consulta lo busca.",
        "en": "If on Refresh Power BI says “Could not find a part of the path”, this is it: the file is no longer where the query looks for it.",
        "pt": "Se ao Atualizar o Power BI diz «Não foi possível encontrar parte do caminho», é isto: o arquivo já não está onde a consulta o procura.",
    },
    "or_fragil": {
        "es": "carpeta personal — se rompe al mover el archivo o abrirlo en otra PC",
        "en": "personal folder — breaks when the file moves or opens on another PC",
        "pt": "pasta pessoal — quebra ao mover o arquivo ou abri-lo noutro PC",
    },
    "or_carpeta_vieja": {
        "es": "Carpeta actual", "en": "Current folder", "pt": "Pasta atual",
    },
    "or_carpeta_nueva": {
        "es": "Carpeta nueva (dónde están ahora los archivos)",
        "en": "New folder (where the files are now)",
        "pt": "Pasta nova (onde os arquivos estão agora)",
    },
    "or_btn_repuntar": {
        "es": "Cambiar la carpeta en todas las consultas",
        "en": "Change the folder in every query",
        "pt": "Mudar a pasta em todas as consultas",
    },
    "or_btn_parametrizar": {
        "es": "Dejar la carpeta en un parámetro",
        "en": "Move the folder into a parameter",
        "pt": "Deixar a pasta num parâmetro",
    },
    "or_repuntado": {
        "es": "«{tabla}»: {antes} → {despues}",
        "en": "“{tabla}”: {antes} → {despues}",
        "pt": "«{tabla}»: {antes} → {despues}",
    },
    "or_parametrizado": {
        "es": "Parámetro «{param}» = {carpeta} — {n} consultas lo usan ahora; para mudar los archivos, cambiás el parámetro y listo",
        "en": "Parameter “{param}” = {carpeta} — {n} queries use it now; to move the files, change the parameter and that's it",
        "pt": "Parâmetro «{param}» = {carpeta} — {n} consultas o usam agora; para mudar os arquivos, muda o parâmetro e pronto",
    },
    "or_sin_coincidencias": {
        "es": "Ninguna consulta lee de «{carpeta}»: no hubo nada que cambiar",
        "en": "No query reads from “{carpeta}”: there was nothing to change",
        "pt": "Nenhuma consulta lê de «{carpeta}»: não havia nada a mudar",
    },
    "or_sin_archivos": {
        "es": "Ninguna consulta lee de un archivo o carpeta: no hay ruta que parametrizar.",
        "en": "No query reads from a file or folder: there is no path to parameterize.",
        "pt": "Nenhuma consulta lê de um arquivo ou pasta: não há caminho a parametrizar.",
    },
    "or_existe_si": {
        "es": "el archivo está", "en": "file is there",
        "pt": "o arquivo está",
    },
    "or_existe_no": {
        "es": "FALTA — esta consulta va a fallar al Actualizar",
        "en": "MISSING — this query will fail on Refresh",
        "pt": "FALTA — esta consulta vai falhar ao Atualizar",
    },
    "or_existe_quizas": {
        "es": "no se puede comprobar desde acá (ruta de red o de otra PC)",
        "en": "cannot be checked from here (network path or another PC)",
        "pt": "não dá para verificar daqui (caminho de rede ou de outro PC)",
    },
    "or_buscar_en": {
        "es": "Carpeta donde buscar los archivos que faltan",
        "en": "Folder to search the missing files in",
        "pt": "Pasta onde procurar os arquivos que faltam",
    },
    "or_btn_buscar": {
        "es": "Buscar y arreglar solo",
        "en": "Find and fix automatically",
        "pt": "Procurar e corrigir sozinho",
    },
    "or_subir": {
        "es": "…o subí los archivos que faltan y los meto adentro del modelo",
        "en": "…or upload the missing files and I'll embed them in the model",
        "pt": "…ou envie os arquivos que faltam e eu os coloco dentro do modelo",
    },
    "or_subir_nota": {
        "es": "Los datos quedan DENTRO del archivo: la consulta deja de depender de una ruta y el .pbit abre en cualquier máquina sin refrescar.",
        "en": "The data ends up INSIDE the file: the query stops depending on a path and the .pbit opens on any machine without refreshing.",
        "pt": "Os dados ficam DENTRO do arquivo: a consulta deixa de depender de um caminho e o .pbit abre em qualquer máquina sem atualizar.",
    },
    "or_btn_subir": {
        "es": "Empotrar los archivos subidos",
        "en": "Embed the uploaded files",
        "pt": "Embutir os arquivos enviados",
    },
    "or_subidos_empotrados": {
        "es": "{n} tablas quedaron con los datos adentro: {lista}",
        "en": "{n} tables now carry their data inside: {lista}",
        "pt": "{n} tabelas ficaram com os dados dentro: {lista}",
    },
    "or_subidos_sin_pareja": {
        "es": "Lo subido no coincide con ninguna tabla del modelo ({lista}): revisá que los nombres de las hojas o los archivos sean los de las tablas",
        "en": "What you uploaded matches no table in the model ({lista}): check that the sheet or file names are the table names",
        "pt": "O enviado não corresponde a nenhuma tabela do modelo ({lista}): confira se os nomes das planilhas ou arquivos são os das tabelas",
    },
    "or_nada_que_repuntar": {
        "es": "No hubo ningún archivo para repuntar",
        "en": "There was no file to repoint",
        "pt": "Não houve nenhum arquivo para reapontar",
    },
    "or_ambiguo": {
        "es": "«{archivo}» aparece {n} veces en esa carpeta — no se eligió ninguna para no acertarle a la equivocada: {opciones}",
        "en": "“{archivo}” appears {n} times in that folder — none was picked, to avoid choosing the wrong one: {opciones}",
        "pt": "«{archivo}» aparece {n} vezes nessa pasta — nenhuma foi escolhida, para não acertar na errada: {opciones}",
    },
    "or_no_aparece": {
        "es": "«{archivo}» no aparece en «{carpeta}» ni en sus subcarpetas",
        "en": "“{archivo}” is not in “{carpeta}” or its subfolders",
        "pt": "«{archivo}» não aparece em «{carpeta}» nem nas suas subpastas",
    },
    "or_busqueda_cortada": {
        "es": "La búsqueda se detuvo en {n} carpetas: si algún archivo no apareció, probá con una carpeta más precisa",
        "en": "The search stopped at {n} folders: if a file did not show up, try a more specific folder",
        "pt": "A busca parou em {n} pastas: se algum arquivo não apareceu, tente uma pasta mais específica",
    },
    "or_err_carpeta": {
        "es": "La carpeta «{carpeta}» no existe en esta PC.",
        "en": "Folder “{carpeta}” does not exist on this PC.",
        "pt": "A pasta «{carpeta}» não existe neste PC.",
    },
    "or_faltan_n": {
        "es": "{n} de {total} archivos no están donde el informe los busca",
        "en": "{n} of {total} files are not where the report looks for them",
        "pt": "{n} de {total} arquivos não estão onde o relatório os procura",
    },
    "nlp_d_buscar": {
        "es": "Buscar los archivos que faltan en «{carpeta}» y repuntar las consultas",
        "en": "Search the missing files in “{carpeta}” and repoint the queries",
        "pt": "Procurar os arquivos que faltam em «{carpeta}» e reapontar as consultas",
    },
    "or_err_vacio": {
        "es": "Hay que indicar la carpeta actual y la nueva.",
        "en": "Both the current and the new folder are required.",
        "pt": "É preciso indicar a pasta atual e a nova.",
    },
    "or_datamashup": {
        "es": "⚠ Este archivo además guarda las consultas en su contenedor interno (DataMashup), que no se reescribe acá: si al Actualizar sigue apareciendo la ruta vieja, cambiala en Desktop con Inicio → Transformar datos → Configuración de origen de datos → Cambiar origen.",
        "en": "⚠ This file also stores the queries in its internal container (DataMashup), which is not rewritten here: if Refresh still shows the old path, change it in Desktop with Home → Transform data → Data source settings → Change Source.",
        "pt": "⚠ Este arquivo também guarda as consultas no seu contêiner interno (DataMashup), que não é reescrito aqui: se ao Atualizar ainda aparecer o caminho antigo, mude-o no Desktop em Início → Transformar dados → Configurações da fonte de dados → Alterar Fonte.",
    },
    "nlp_d_origenes": {
        "es": "Listar de dónde lee cada consulta y marcar las rutas frágiles",
        "en": "List where each query reads from and flag fragile paths",
        "pt": "Listar de onde cada consulta lê e marcar os caminhos frágeis",
    },
    "nlp_d_repuntar": {
        "es": "Cambiar la carpeta de origen: {antes} → {despues}",
        "en": "Change the source folder: {antes} → {despues}",
        "pt": "Mudar a pasta de origem: {antes} → {despues}",
    },
    "nlp_or_linea": {
        "es": "«{tabla}» lee de {ruta}{aviso}",
        "en": "“{tabla}” reads from {ruta}{aviso}",
        "pt": "«{tabla}» lê de {ruta}{aviso}",
    },
    "nlp_sin_origenes": {
        "es": "No hay orígenes de archivo, carpeta, SQL ni web en las consultas del modelo.",
        "en": "There are no file, folder, SQL or web sources in the model's queries.",
        "pt": "Não há origens de arquivo, pasta, SQL nem web nas consultas do modelo.",
    },
    "regla_R16": {
        "es": "Columna visible sin formato",
        "en": "Visible column without a format",
        "pt": "Coluna visível sem formato",
    },
    "regla_R16_detalle": {
        "es": "Una fecha cruda o un número sin separador de miles se ve mal en CADA visual que use la columna. El formato se define una vez en el modelo y todos los visuales lo heredan.",
        "en": "A raw date or a number without thousands separator looks wrong in EVERY visual using the column. The format is set once in the model and every visual inherits it.",
        "pt": "Uma data crua ou um número sem separador de milhares fica mal em CADA visual que use a coluna. O formato define-se uma vez no modelo e todos os visuais o herdam.",
    },
    "regla_R16_arreglo": {
        "es": "Asignar formato según el tipo: fechas dd/mm/yyyy, decimales #,0.00, enteros #,0 (las claves no se tocan).",
        "en": "Assign a format by type: dates dd/mm/yyyy, decimals #,0.00, integers #,0 (keys are left alone).",
        "pt": "Atribuir formato conforme o tipo: datas dd/mm/yyyy, decimais #,0.00, inteiros #,0 (as chaves não se tocam).",
    },
    # ---- explicador: base de conocimiento DAX y prosa -----------------
    # Las 62 descripciones de función, las categorías y las frases del
    # explicador. Estaban en español dentro de `explicador.py`, así que la
    # pestaña Explicador contestaba en español con la app en otro idioma.
    "fn_SUM": {
        "es": "suma los valores de una columna",
        "en": "sums the values of a column",
        "pt": "soma os valores de uma coluna",
    },
    "fn_SUMX": {
        "es": "recorre la tabla fila por fila, evalúa la expresión y suma los resultados",
        "en": "walks the table row by row, evaluates the expression and sums the results",
        "pt": "percorre a tabela linha a linha, avalia a expressão e soma os resultados",
    },
    "fn_AVERAGE": {
        "es": "promedia los valores de una columna",
        "en": "averages the values of a column",
        "pt": "faz a média dos valores de uma coluna",
    },
    "fn_AVERAGEX": {
        "es": "recorre la tabla fila por fila y promedia la expresión evaluada",
        "en": "walks the table row by row and averages the evaluated expression",
        "pt": "percorre a tabela linha a linha e faz a média da expressão avaliada",
    },
    "fn_MIN": {
        "es": "devuelve el mínimo de una columna",
        "en": "returns the minimum of a column",
        "pt": "devolve o mínimo de uma coluna",
    },
    "fn_MAX": {
        "es": "devuelve el máximo de una columna",
        "en": "returns the maximum of a column",
        "pt": "devolve o máximo de uma coluna",
    },
    "fn_MINX": {
        "es": "mínimo de una expresión evaluada fila por fila",
        "en": "minimum of an expression evaluated row by row",
        "pt": "mínimo de uma expressão avaliada linha a linha",
    },
    "fn_MAXX": {
        "es": "máximo de una expresión evaluada fila por fila",
        "en": "maximum of an expression evaluated row by row",
        "pt": "máximo de uma expressão avaliada linha a linha",
    },
    "fn_COUNT": {
        "es": "cuenta los valores no vacíos de una columna",
        "en": "counts the non-blank values of a column",
        "pt": "conta os valores não vazios de uma coluna",
    },
    "fn_COUNTROWS": {
        "es": "cuenta las filas de una tabla",
        "en": "counts the rows of a table",
        "pt": "conta as linhas de uma tabela",
    },
    "fn_COUNTX": {
        "es": "cuenta evaluando una expresión fila por fila",
        "en": "counts by evaluating an expression row by row",
        "pt": "conta avaliando uma expressão linha a linha",
    },
    "fn_DISTINCTCOUNT": {
        "es": "cuenta los valores distintos de una columna",
        "en": "counts the distinct values of a column",
        "pt": "conta os valores distintos de uma coluna",
    },
    "fn_CALCULATE": {
        "es": "evalúa la expresión CAMBIANDO el contexto de filtro con los filtros que se le pasan",
        "en": "evaluates the expression CHANGING the filter context with the filters it receives",
        "pt": "avalia a expressão MUDANDO o contexto de filtro com os filtros que recebe",
    },
    "fn_CALCULATETABLE": {
        "es": "como CALCULATE pero devuelve una tabla",
        "en": "like CALCULATE but returns a table",
        "pt": "como CALCULATE mas devolve uma tabela",
    },
    "fn_FILTER": {
        "es": "devuelve las filas de la tabla que cumplen la condición",
        "en": "returns the rows of the table that meet the condition",
        "pt": "devolve as linhas da tabela que cumprem a condição",
    },
    "fn_ALL": {
        "es": "quita los filtros de la tabla o columna indicada",
        "en": "removes the filters from the given table or column",
        "pt": "remove os filtros da tabela ou coluna indicada",
    },
    "fn_ALLEXCEPT": {
        "es": "quita todos los filtros salvo los de las columnas indicadas",
        "en": "removes every filter except those on the given columns",
        "pt": "remove todos os filtros exceto os das colunas indicadas",
    },
    "fn_ALLSELECTED": {
        "es": "quita los filtros internos del visual pero respeta los slicers",
        "en": "removes the visual's inner filters but respects the slicers",
        "pt": "remove os filtros internos do visual mas respeita os slicers",
    },
    "fn_REMOVEFILTERS": {
        "es": "quita filtros — versión moderna y legible de ALL",
        "en": "removes filters — the modern, readable version of ALL",
        "pt": "remove filtros — versão moderna e legível de ALL",
    },
    "fn_KEEPFILTERS": {
        "es": "agrega el filtro sin pisar los existentes (intersección)",
        "en": "adds the filter without overwriting the existing ones (intersection)",
        "pt": "adiciona o filtro sem sobrepor os existentes (interseção)",
    },
    "fn_VALUES": {
        "es": "devuelve los valores visibles (distintos) de una columna en el contexto actual",
        "en": "returns the visible (distinct) values of a column in the current context",
        "pt": "devolve os valores visíveis (distintos) de uma coluna no contexto atual",
    },
    "fn_DISTINCT": {
        "es": "devuelve los valores distintos de una columna",
        "en": "returns the distinct values of a column",
        "pt": "devolve os valores distintos de uma coluna",
    },
    "fn_SELECTEDVALUE": {
        "es": "devuelve el valor si hay UNO solo visible; si no, el alternativo",
        "en": "returns the value if exactly ONE is visible; otherwise the fallback",
        "pt": "devolve o valor se houver apenas UM visível; caso contrário, o alternativo",
    },
    "fn_HASONEVALUE": {
        "es": "verdadero si la columna tiene un único valor visible",
        "en": "true if the column has a single visible value",
        "pt": "verdadeiro se a coluna tem um único valor visível",
    },
    "fn_ISFILTERED": {
        "es": "verdadero si la columna está siendo filtrada",
        "en": "true if the column is being filtered",
        "pt": "verdadeiro se a coluna está sendo filtrada",
    },
    "fn_DIVIDE": {
        "es": "divide de forma segura: ante denominador 0 o BLANK devuelve BLANK (o el alternativo)",
        "en": "divides safely: on a 0 or BLANK divisor it returns BLANK (or the fallback)",
        "pt": "divide de forma segura: com divisor 0 ou BLANK devolve BLANK (ou o alternativo)",
    },
    "fn_IF": {
        "es": "evalúa una condición y devuelve una de dos ramas",
        "en": "evaluates a condition and returns one of two branches",
        "pt": "avalia uma condição e devolve um de dois ramos",
    },
    "fn_SWITCH": {
        "es": "compara contra varios casos y devuelve la rama que coincide",
        "en": "compares against several cases and returns the matching branch",
        "pt": "compara com vários casos e devolve o ramo que coincide",
    },
    "fn_AND": {
        "es": "verdadero si ambas condiciones lo son",
        "en": "true if both conditions are true",
        "pt": "verdadeiro se ambas as condições o forem",
    },
    "fn_OR": {
        "es": "verdadero si alguna condición lo es",
        "en": "true if either condition is true",
        "pt": "verdadeiro se alguma condição o for",
    },
    "fn_NOT": {
        "es": "invierte la condición",
        "en": "inverts the condition",
        "pt": "inverte a condição",
    },
    "fn_COALESCE": {
        "es": "devuelve el primer valor no BLANK de la lista",
        "en": "returns the first non-BLANK value in the list",
        "pt": "devolve o primeiro valor não BLANK da lista",
    },
    "fn_ISBLANK": {
        "es": "verdadero si el valor es BLANK",
        "en": "true if the value is BLANK",
        "pt": "verdadeiro se o valor é BLANK",
    },
    "fn_BLANK": {
        "es": "devuelve el valor vacío BLANK",
        "en": "returns the empty BLANK value",
        "pt": "devolve o valor vazio BLANK",
    },
    "fn_TOTALYTD": {
        "es": "acumula la expresión desde el inicio del año hasta la fecha del contexto",
        "en": "accumulates the expression from the start of the year to the context date",
        "pt": "acumula a expressão desde o início do ano até a data do contexto",
    },
    "fn_TOTALQTD": {
        "es": "acumula desde el inicio del trimestre",
        "en": "accumulates from the start of the quarter",
        "pt": "acumula desde o início do trimestre",
    },
    "fn_TOTALMTD": {
        "es": "acumula desde el inicio del mes",
        "en": "accumulates from the start of the month",
        "pt": "acumula desde o início do mês",
    },
    "fn_SAMEPERIODLASTYEAR": {
        "es": "desplaza las fechas del contexto un año hacia atrás",
        "en": "shifts the context dates one year back",
        "pt": "desloca as datas do contexto um ano para trás",
    },
    "fn_DATEADD": {
        "es": "desplaza las fechas del contexto el intervalo indicado",
        "en": "shifts the context dates by the given interval",
        "pt": "desloca as datas do contexto pelo intervalo indicado",
    },
    "fn_DATESINPERIOD": {
        "es": "devuelve las fechas de un período móvil que termina en la fecha dada",
        "en": "returns the dates of a rolling period ending on the given date",
        "pt": "devolve as datas de um período móvel que termina na data dada",
    },
    "fn_DATESYTD": {
        "es": "las fechas desde el inicio del año hasta la actual",
        "en": "the dates from the start of the year to the current one",
        "pt": "as datas desde o início do ano até a atual",
    },
    "fn_PREVIOUSMONTH": {
        "es": "las fechas del mes anterior completo",
        "en": "the dates of the whole previous month",
        "pt": "as datas do mês anterior completo",
    },
    "fn_LASTDATE": {
        "es": "la última fecha visible en el contexto",
        "en": "the last date visible in the context",
        "pt": "a última data visível no contexto",
    },
    "fn_FIRSTDATE": {
        "es": "la primera fecha visible en el contexto",
        "en": "the first date visible in the context",
        "pt": "a primeira data visível no contexto",
    },
    "fn_EOMONTH": {
        "es": "el fin de mes de una fecha, con corrimiento opcional",
        "en": "the end of month of a date, with an optional offset",
        "pt": "o fim de mês de uma data, com deslocamento opcional",
    },
    "fn_TODAY": {
        "es": "la fecha de hoy",
        "en": "today's date",
        "pt": "a data de hoje",
    },
    "fn_RANKX": {
        "es": "posición de cada elemento al ordenar la tabla por la expresión",
        "en": "the position of each item when sorting the table by the expression",
        "pt": "posição de cada elemento ao ordenar a tabela pela expressão",
    },
    "fn_TOPN": {
        "es": "las N filas con mayor valor de la expresión",
        "en": "the N rows with the highest value of the expression",
        "pt": "as N linhas com maior valor da expressão",
    },
    "fn_RELATED": {
        "es": "trae el valor desde el lado «uno» de la relación",
        "en": "brings the value from the “one” side of the relationship",
        "pt": "traz o valor do lado «um» da relação",
    },
    "fn_RELATEDTABLE": {
        "es": "las filas relacionadas desde el lado «muchos»",
        "en": "the related rows from the “many” side",
        "pt": "as linhas relacionadas do lado «muitos»",
    },
    "fn_USERELATIONSHIP": {
        "es": "activa una relación inactiva solo dentro de este cálculo",
        "en": "activates an inactive relationship only inside this calculation",
        "pt": "ativa uma relação inativa apenas dentro deste cálculo",
    },
    "fn_CROSSFILTER": {
        "es": "cambia la dirección del filtro de una relación solo en este cálculo",
        "en": "changes a relationship's filter direction only in this calculation",
        "pt": "muda a direção do filtro de uma relação apenas neste cálculo",
    },
    "fn_TREATAS": {
        "es": "aplica los valores de una tabla como filtro sobre otras columnas",
        "en": "applies a table's values as a filter over other columns",
        "pt": "aplica os valores de uma tabela como filtro sobre outras colunas",
    },
    "fn_LOOKUPVALUE": {
        "es": "busca un valor en otra tabla por igualdad de claves",
        "en": "looks a value up in another table by matching keys",
        "pt": "busca um valor em outra tabela por igualdade de chaves",
    },
    "fn_SUMMARIZE": {
        "es": "agrupa una tabla por columnas",
        "en": "groups a table by columns",
        "pt": "agrupa uma tabela por colunas",
    },
    "fn_ADDCOLUMNS": {
        "es": "agrega columnas calculadas a una tabla en memoria",
        "en": "adds calculated columns to an in-memory table",
        "pt": "adiciona colunas calculadas a uma tabela em memória",
    },
    "fn_SELECTCOLUMNS": {
        "es": "proyecta columnas de una tabla",
        "en": "projects columns from a table",
        "pt": "projeta colunas de uma tabela",
    },
    "fn_UNION": {
        "es": "apila dos tablas",
        "en": "stacks two tables",
        "pt": "empilha duas tabelas",
    },
    "fn_CONCATENATEX": {
        "es": "concatena textos evaluados fila por fila",
        "en": "concatenates texts evaluated row by row",
        "pt": "concatena textos avaliados linha a linha",
    },
    "fn_FORMAT": {
        "es": "convierte un valor a texto con formato",
        "en": "converts a value to formatted text",
        "pt": "converte um valor em texto com formato",
    },
    "fn_VAR": {
        "es": "define una variable: se evalúa una vez y se reutiliza",
        "en": "declares a variable: evaluated once and reused",
        "pt": "define uma variável: é avaliada uma vez e reutilizada",
    },
    "fn_RETURN": {
        "es": "devuelve el resultado final usando las variables definidas",
        "en": "returns the final result using the declared variables",
        "pt": "devolve o resultado final usando as variáveis definidas",
    },
    "catfn_agregacion": {
        "es": "agregación",
        "en": "aggregation",
        "pt": "agregação",
    },
    "catfn_iterador": {
        "es": "iterador",
        "en": "iterator",
        "pt": "iterador",
    },
    "catfn_contexto": {
        "es": "contexto",
        "en": "context",
        "pt": "contexto",
    },
    "catfn_tabla": {
        "es": "tabla",
        "en": "table",
        "pt": "tabela",
    },
    "catfn_matematica": {
        "es": "matemática",
        "en": "maths",
        "pt": "matemática",
    },
    "catfn_logica": {
        "es": "lógica",
        "en": "logic",
        "pt": "lógica",
    },
    "catfn_tiempo": {
        "es": "tiempo",
        "en": "time intelligence",
        "pt": "tempo",
    },
    "catfn_ranking": {
        "es": "ranking",
        "en": "ranking",
        "pt": "ranking",
    },
    "catfn_relacion": {
        "es": "relación",
        "en": "relationship",
        "pt": "relação",
    },
    "catfn_texto": {
        "es": "texto",
        "en": "text",
        "pt": "texto",
    },
    "catfn_estructura": {
        "es": "estructura",
        "en": "structure",
        "pt": "estrutura",
    },
    "catfn_otra": {
        "es": "otra",
        "en": "other",
        "pt": "outra",
    },
    "exp_vacia": {
        "es": "Expresión vacía.",
        "en": "Empty expression.",
        "pt": "Expressão vazia.",
    },
    "exp_fn_desconocida": {
        "es": "función DAX",
        "en": "DAX function",
        "pt": "função DAX",
    },
    "exp_quien_medida": {
        "es": "La medida [{nombre}]",
        "en": "Measure [{nombre}]",
        "pt": "A medida [{nombre}]",
    },
    "exp_quien_expresion": {
        "es": "La expresión",
        "en": "The expression",
        "pt": "A expressão",
    },
    "exp_res_tiempo": {
        "es": "{quien} calcula un valor con inteligencia de tiempo: desplaza o acumula el período del contexto antes de agregar.",
        "en": "{quien} computes a value with time intelligence: it shifts or accumulates the context period before aggregating.",
        "pt": "{quien} calcula um valor com inteligência de tempo: desloca ou acumula o período do contexto antes de agregar.",
    },
    "exp_res_ytd": {
        "es": "{quien} acumula el valor desde el inicio del año.",
        "en": "{quien} accumulates the value from the start of the year.",
        "pt": "{quien} acumula o valor desde o início do ano.",
    },
    "exp_res_rank": {
        "es": "{quien} calcula una posición en un ranking.",
        "en": "{quien} computes a position in a ranking.",
        "pt": "{quien} calcula uma posição num ranking.",
    },
    "exp_res_divide": {
        "es": "{quien} calcula un cociente con división segura.",
        "en": "{quien} computes a ratio with safe division.",
        "pt": "{quien} calcula um quociente com divisão segura.",
    },
    "exp_res_calculate": {
        "es": "{quien} agrega un valor modificando antes el contexto de filtro (eso es CALCULATE: cambia sobre qué filas se calcula).",
        "en": "{quien} aggregates a value after modifying the filter context (that is what CALCULATE does: it changes which rows are used).",
        "pt": "{quien} agrega um valor modificando antes o contexto de filtro (isso é CALCULATE: muda sobre quais linhas se calcula).",
    },
    "exp_res_base": {
        "es": "{quien} {base}{sobre}.",
        "en": "{quien} {base}{sobre}.",
        "pt": "{quien} {base}{sobre}.",
    },
    "exp_res_simple": {
        "es": "{quien} evalúa una expresión aritmética simple.",
        "en": "{quien} evaluates a simple arithmetic expression.",
        "pt": "{quien} avalia uma expressão aritmética simples.",
    },
    "exp_sobre": {
        "es": " sobre {col}",
        "en": " over {col}",
        "pt": " sobre {col}",
    },
    "exp_paso_var": {
        "es": "Define {n} variable(s) ({lista}{mas}): cada una se evalúa una sola vez y congela su valor — más rápido y más legible.",
        "en": "Declares {n} variable(s) ({lista}{mas}): each is evaluated once and freezes its value — faster and easier to read.",
        "pt": "Define {n} variável(is) ({lista}{mas}): cada uma é avaliada uma só vez e congela seu valor — mais rápido e mais legível.",
    },
    "exp_paso_calculate": {
        "es": "CALCULATE cambia el contexto de filtro: los filtros que recibe reemplazan (o intersecan, con KEEPFILTERS) a los del visual antes de evaluar la expresión.",
        "en": "CALCULATE changes the filter context: the filters it receives replace (or intersect, with KEEPFILTERS) the visual's own before the expression is evaluated.",
        "pt": "CALCULATE muda o contexto de filtro: os filtros que recebe substituem (ou intersectam, com KEEPFILTERS) os do visual antes de avaliar a expressão.",
    },
    "exp_paso_iterador": {
        "es": "{lista} recorre(n) la tabla fila por fila: el costo crece con la cantidad de filas visibles.",
        "en": "{lista} walk(s) the table row by row: the cost grows with the number of visible rows.",
        "pt": "{lista} percorre(m) a tabela linha a linha: o custo cresce com a quantidade de linhas visíveis.",
    },
    "exp_paso_tiempo": {
        "es": "Inteligencia de tiempo ({lista}): necesita una tabla de calendario continua y marcada como tabla de fechas para dar resultados correctos.",
        "en": "Time intelligence ({lista}): it needs a continuous date table, marked as such, to return correct results.",
        "pt": "Inteligência de tempo ({lista}): precisa de uma tabela de calendário contínua e marcada como tabela de datas para dar resultados corretos.",
    },
    "exp_paso_medidas": {
        "es": "Reutiliza medidas existentes ({lista}): el cambio en la medida base se propaga solo.",
        "en": "Reuses existing measures ({lista}): a change in the base measure propagates on its own.",
        "pt": "Reutiliza medidas existentes ({lista}): a mudança na medida base se propaga sozinha.",
    },
    "exp_paso_directo": {
        "es": "Agregación directa sobre el contexto del visual, sin modificar filtros.",
        "en": "Direct aggregation over the visual's context, with no filter changes.",
        "pt": "Agregação direta sobre o contexto do visual, sem modificar filtros.",
    },
    "nivel_basico": {
        "es": "básico",
        "en": "basic",
        "pt": "básico",
    },
    "nivel_intermedio": {
        "es": "intermedio",
        "en": "intermediate",
        "pt": "intermediário",
    },
    "nivel_avanzado": {
        "es": "avanzado",
        "en": "advanced",
        "pt": "avançado",
    },
    # ---- transformador, generador y nombre de la edición ---------------
    # Último resto de texto de usuario que vivía hardcodeado en español.
    "tr_divide": {
        "es": "[{obj}]: {n} división(es) «/» → DIVIDE",
        "en": "[{obj}]: {n} “/” division(s) → DIVIDE",
        "pt": "[{obj}]: {n} divisão(ões) «/» → DIVIDE",
    },
    "tr_formato": {
        "es": "[{obj}]: formato → {formato}",
        "en": "[{obj}]: format → {formato}",
        "pt": "[{obj}]: formato → {formato}",
    },
    "tr_oculta_clave": {
        "es": "{obj}: oculta (clave de relación)",
        "en": "{obj}: hidden (relationship key)",
        "pt": "{obj}: oculta (chave de relação)",
    },
    "tr_tabla_medidas_creada": {
        "es": "Tabla de medidas «{nombre}» creada",
        "en": "Measures table “{nombre}” created",
        "pt": "Tabela de medidas «{nombre}» criada",
    },
    "tr_movidas": {
        "es": "{n} medida(s) movida(s) desde {origen}",
        "en": "{n} measure(s) moved from {origen}",
        "pt": "{n} medida(s) movida(s) de {origen}",
    },
    "tr_renombrada": {
        "es": "[{antes}] → [{despues}]",
        "en": "[{antes}] → [{despues}]",
        "pt": "[{antes}] → [{despues}]",
    },
    "tr_referencias": {
        "es": "[{obj}]: {n} referencia(s) actualizada(s)",
        "en": "[{obj}]: {n} reference(s) updated",
        "pt": "[{obj}]: {n} referência(s) atualizada(s)",
    },
    "tr_sin_tablas": {
        "es": "El modelo no tiene tablas.",
        "en": "The model has no tables.",
        "pt": "O modelo não tem tabelas.",
    },
    "tr_medida_agregada": {
        "es": "Medida [{nombre}] agregada en «{tabla}»",
        "en": "Measure [{nombre}] added to “{tabla}”",
        "pt": "Medida [{nombre}] adicionada em «{tabla}»",
    },
    "tr_medida_eliminada": {
        "es": "Medida [{nombre}] eliminada de «{tabla}»",
        "en": "Measure [{nombre}] removed from “{tabla}”",
        "pt": "Medida [{nombre}] removida de «{tabla}»",
    },
    "tr_err_medida_existe": {
        "es": "Ya existe una medida llamada [{nombre}].",
        "en": "A measure named [{nombre}] already exists.",
        "pt": "Já existe uma medida chamada [{nombre}].",
    },
    "tr_err_tabla_no_existe": {
        "es": "La tabla «{tabla}» no existe.",
        "en": "The table “{tabla}” does not exist.",
        "pt": "A tabela «{tabla}» não existe.",
    },
    "tr_err_medida_no_existe": {
        "es": "No existe la medida [{nombre}].",
        "en": "Measure [{nombre}] does not exist.",
        "pt": "Não existe a medida [{nombre}].",
    },
    "tr_err_medida_referenciada": {
        "es": "[{nombre}] está referenciada por: {lista}. Actualizá esas medidas antes de eliminarla.",
        "en": "[{nombre}] is referenced by: {lista}. Update those measures before removing it.",
        "pt": "[{nombre}] está referenciada por: {lista}. Atualize essas medidas antes de removê-la.",
    },
    "tr_col_oculta": {
        "es": "Columna {obj} oculta",
        "en": "Column {obj} hidden",
        "pt": "Coluna {obj} oculta",
    },
    "tr_col_visible": {
        "es": "Columna {obj} visible de nuevo",
        "en": "Column {obj} visible again",
        "pt": "Coluna {obj} visível de novo",
    },
    "tr_col_ya_estaba": {
        "es": "{obj} ya estaba así — no hubo nada que cambiar",
        "en": "{obj} was already like that — nothing to change",
        "pt": "{obj} já estava assim — não havia nada a mudar",
    },
    "tr_err_columna_no_existe": {
        "es": "No existe la columna «{col}» en la tabla «{tabla}».",
        "en": "Column “{col}” does not exist in table “{tabla}”.",
        "pt": "Não existe a coluna «{col}» na tabela «{tabla}».",
    },
    "nlp_titulo": {
        "es": "Pedilo en tu idioma",
        "en": "Ask in plain language",
        "pt": "Peça no seu idioma",
    },
    "nlp_ayuda": {
        "es": "Un pedido por línea. Nada se aplica hasta que veas el plan y lo confirmes.",
        "en": "One request per line. Nothing is applied until you see the plan and confirm it.",
        "pt": "Um pedido por linha. Nada é aplicado até você ver o plano e confirmar.",
    },
    "nlp_ejemplos": {
        "es": "corregir todo automáticamente\nanalizar el modelo\ncrear la tabla calendario\nagregar los KPIs\nformato porcentaje para Margen\nocultar la columna IdCliente",
        "en": "fix everything automatically\nanalyze the model\ncreate the calendar table\nadd the KPIs\npercent format for Margin\nhide column CustomerId",
        "pt": "corrigir tudo automaticamente\nanalisar o modelo\ncriar a tabela calendário\nadicionar os KPIs\nformato percentual para Margem\nocultar a coluna IdCliente",
    },
    "nlp_resultado": {
        "es": "Hecho — esto pasó:",
        "en": "Done — this is what happened:",
        "pt": "Feito — foi isto que aconteceu:",
    },
    "nlp_btn_interpretar": {
        "es": "Interpretar", "en": "Interpret", "pt": "Interpretar",
    },
    "nlp_btn_aplicar": {
        "es": "Aplicar el plan", "en": "Apply the plan", "pt": "Aplicar o plano",
    },
    "nlp_plan": {
        "es": "Esto es lo que entendí:",
        "en": "This is what I understood:",
        "pt": "Foi isto que eu entendi:",
    },
    "nlp_no_entendi": {
        "es": "No entendí (y no voy a adivinar):",
        "en": "I did not understand (and I won't guess):",
        "pt": "Não entendi (e não vou adivinhar):",
    },
    "nlp_nada": {
        "es": "No reconocí ningún pedido en ese texto.",
        "en": "I did not recognize any request in that text.",
        "pt": "Não reconheci nenhum pedido nesse texto.",
    },
    "nlp_usa_generar": {
        "es": "para crear medidas nuevas usá la pestaña «Generar DAX», que valida contra tu modelo",
        "en": "to create new measures use the “Generate DAX” tab, which validates against your model",
        "pt": "para criar medidas novas use a aba «Gerar DAX», que valida contra o seu modelo",
    },
    "nlp_no_medida": {
        "es": "no encontré ninguna medida parecida a «{texto}»",
        "en": "no measure resembles “{texto}”",
        "pt": "não encontrei nenhuma medida parecida com «{texto}»",
    },
    "nlp_no_columna": {
        "es": "no encontré ninguna columna parecida a «{texto}»",
        "en": "no column resembles “{texto}”",
        "pt": "não encontrei nenhuma coluna parecida com «{texto}»",
    },
    "nlp_con_ia": {
        "es": "Interpretar con IA (para pedidos más libres)",
        "en": "Interpret with AI (for freer requests)",
        "pt": "Interpretar com IA (para pedidos mais livres)",
    },
    "nlp_ia_descartado": {
        "es": "la IA propuso «{texto}», pero no coincide con nada del modelo — se descartó",
        "en": "the AI proposed “{texto}”, but it matches nothing in the model — discarded",
        "pt": "a IA propôs «{texto}», mas não corresponde a nada no modelo — descartado",
    },
    "nlp_d_ocultar": {
        "es": "Ocultar la columna {obj}",
        "en": "Hide column {obj}",
        "pt": "Ocultar a coluna {obj}",
    },
    "nlp_d_mostrar": {
        "es": "Mostrar la columna {obj}",
        "en": "Show column {obj}",
        "pt": "Mostrar a coluna {obj}",
    },
    "nlp_d_formato": {
        "es": "Formato «{formato}» para la medida [{obj}]",
        "en": "Format “{formato}” for measure [{obj}]",
        "pt": "Formato «{formato}» para a medida [{obj}]",
    },
    "nlp_d_formato_col": {
        "es": "Formato «{formato}» para la columna {obj}",
        "en": "Format “{formato}” for column {obj}",
        "pt": "Formato «{formato}» para a coluna {obj}",
    },
    "nlp_d_renombrar": {
        "es": "Renombrar [{antes}] → [{despues}]",
        "en": "Rename [{antes}] → [{despues}]",
        "pt": "Renomear [{antes}] → [{despues}]",
    },
    "nlp_d_eliminar": {
        "es": "Eliminar la medida [{obj}]",
        "en": "Delete measure [{obj}]",
        "pt": "Excluir a medida [{obj}]",
    },
    "nlp_d_tabla_medidas": {
        "es": "Crear la tabla de medidas y mover ahí los cálculos",
        "en": "Create the measures table and move the calculations there",
        "pt": "Criar a tabela de medidas e mover os cálculos para lá",
    },
    "nlp_d_claves": {
        "es": "Ocultar las columnas clave de las relaciones",
        "en": "Hide the key columns of the relationships",
        "pt": "Ocultar as colunas-chave das relações",
    },
    "nlp_d_formatos": {
        "es": "Asignar formato a las medidas que no tienen",
        "en": "Assign a format to measures that lack one",
        "pt": "Atribuir formato às medidas que não têm",
    },
    "nlp_d_divide": {
        "es": "Convertir divisiones «a / b» en DIVIDE(a, b)",
        "en": "Convert “a / b” divisions into DIVIDE(a, b)",
        "pt": "Converter divisões «a / b» em DIVIDE(a, b)",
    },
    "nlp_d_direccion": {
        "es": "Pasar las relaciones bidireccionales a una sola dirección",
        "en": "Turn bidirectional relationships into single direction",
        "pt": "Passar as relações bidirecionais para uma só direção",
    },
    "nlp_d_autofecha": {
        "es": "Apagar las tablas de fecha automáticas",
        "en": "Turn off the automatic date tables",
        "pt": "Desligar as tabelas de data automáticas",
    },
    "nlp_d_corregir_todo": {
        "es": "Analizar el modelo y aplicar TODOS los arreglos automáticos, explicando qué estaba mal y qué se hizo",
        "en": "Analyze the model and apply ALL automatic fixes, explaining what was wrong and what was done",
        "pt": "Analisar o modelo e aplicar TODAS as correções automáticas, explicando o que estava errado e o que foi feito",
    },
    "nlp_d_analizar": {
        "es": "Analizar el modelo y listar qué está mal (sin tocar nada)",
        "en": "Analyze the model and list what is wrong (touching nothing)",
        "pt": "Analisar o modelo e listar o que está errado (sem tocar em nada)",
    },
    "nlp_d_calendario": {
        "es": "Crear la tabla calendario y relacionarla con las fechas del modelo",
        "en": "Create the calendar table and relate it to the model's dates",
        "pt": "Criar a tabela calendário e relacioná-la com as datas do modelo",
    },
    "nlp_d_kpis_agregar": {
        "es": "Agregar los KPIs que el modelo pide (totales, margen, únicos, YTD…)",
        "en": "Add the KPIs the model asks for (totals, margin, unique counts, YTD…)",
        "pt": "Adicionar os KPIs que o modelo pede (totais, margem, únicos, YTD…)",
    },
    "nlp_d_kpis_sugerir": {
        "es": "Sugerir KPIs con su DAX y su porqué (sin agregarlos)",
        "en": "Suggest KPIs with their DAX and rationale (without adding them)",
        "pt": "Sugerir KPIs com seu DAX e seu porquê (sem adicioná-los)",
    },
    "nlp_salud": {
        "es": "Salud del modelo: {puntos}/100 · {n} hallazgos",
        "en": "Model health: {puntos}/100 · {n} findings",
        "pt": "Saúde do modelo: {puntos}/100 · {n} achados",
    },
    "nlp_sin_problemas": {
        "es": "El análisis no encontró nada para arreglar.",
        "en": "The analysis found nothing to fix.",
        "pt": "A análise não encontrou nada para corrigir.",
    },
    "nlp_mal": {
        "es": "Mal: {que} · {n}×",
        "en": "Wrong: {que} · {n}×",
        "pt": "Errado: {que} · {n}×",
    },
    "nlp_queda_mano": {
        "es": "Queda a mano (sin arreglo automático): {que}",
        "en": "Left for you (no automatic fix): {que}",
        "pt": "Fica manual (sem correção automática): {que}",
    },
    "nlp_kpi_sugerido": {
        "es": "KPI sugerido [{nombre}]: {dax} — {porque}",
        "en": "Suggested KPI [{nombre}]: {dax} — {porque}",
        "pt": "KPI sugerido [{nombre}]: {dax} — {porque}",
    },
    "pe_sin_calendario": {
        "es": 'El modelo no tiene tabla calendario: los comparativos de período necesitan una. Creála primero (Analizador → arreglar R14, o «agregá el calendario» por texto).',
        "en": 'The model has no calendar table: period comparisons need one. Create it first (Analyzer → fix R14, or “add the calendar” by text).',
        "pt": 'O modelo não tem tabela calendário: os comparativos de período precisam de uma. Crie-a primeiro (Analisador → corrigir R14, ou «adicione o calendário» por texto).',
    },
    "pe_columna": {
        "es": 'Columna «{columna}» agregada a {tabla} — sin ella el comparativo interanual no se puede calcular',
        "en": 'Column “{columna}” added to {tabla} — without it the year-on-year comparison cannot be calculated',
        "pt": 'Coluna «{columna}» adicionada a {tabla} — sem ela o comparativo interanual não pode ser calculado',
    },
    "pe_columna_m": {
        "es": "Columna «{columna}» agregada a {tabla} EN POWER QUERY — ahí no cuesta memoria ni se recalcula en cada refresco, que es lo que pasaría como columna calculada en DAX",
        "en": "Column “{columna}” added to {tabla} IN POWER QUERY — there it costs no memory and is not recomputed on every refresh, which is what would happen as a DAX calculated column",
        "pt": "Coluna «{columna}» adicionada a {tabla} NO POWER QUERY — ali não custa memória nem é recalculada a cada atualização, que é o que aconteceria como coluna calculada em DAX",
    },
    "nlp_d_comparativos": {
        "es": "agregar los comparativos de período: mes, trimestre, semestre, YTD y año contra el año anterior, en valor, en unidades y en share",
        "en": "add the period comparisons: month, quarter, semester, YTD and year against the previous year, in value, units and share",
        "pt": "adicionar os comparativos de período: mês, trimestre, semestre, YTD e ano contra o ano anterior, em valor, unidades e share",
    },
    "pe_carpeta_tiempo": {
        "es": '02 Tiempo',
        "en": '02 Time',
        "pt": '02 Tempo',
    },
    "pe_carpeta_share": {
        "es": '03 Mercado y share',
        "en": '03 Market and share',
        "pt": '03 Mercado e share',
    },
    "pe_grano_mes": {
        "es": 'mes',
        "en": 'month',
        "pt": 'mês',
    },
    "pe_grano_trimestre": {
        "es": 'trimestre',
        "en": 'quarter',
        "pt": 'trimestre',
    },
    "pe_grano_semestre": {
        "es": 'semestre',
        "en": 'semester',
        "pt": 'semestre',
    },
    "pe_grano_ytd": {
        "es": 'YTD',
        "en": 'YTD',
        "pt": 'YTD',
    },
    "pe_grano_anio": {
        "es": 'año',
        "en": 'year',
        "pt": 'ano',
    },
    "pe_mercado": {
        "es": '{base} Mercado',
        "en": '{base} Market',
        "pt": '{base} Mercado',
    },
    "pe_ytd": {
        "es": '{base} YTD',
        "en": '{base} YTD',
        "pt": '{base} YTD',
    },
    "pe_anterior": {
        "es": '{base} {grano} AA',
        "en": '{base} {grano} PY',
        "pt": '{base} {grano} AA',
    },
    "pe_anterior_simple": {
        "es": "{base} AA",
        "en": "{base} PY",
        "pt": "{base} AA",
    },
    "pe_variacion": {
        "es": '{base} var {grano} %',
        "en": '{base} var {grano} %',
        "pt": '{base} var {grano} %',
    },
    "pe_share": {
        "es": 'Share {base} {grano} %',
        "en": 'Share {base} {grano} %',
        "pt": 'Share {base} {grano} %',
    },
    "pe_share_simple": {
        "es": "Share {base} %",
        "en": "Share {base} %",
        "pt": "Share {base} %",
    },
    "pe_share_anterior": {
        "es": 'Share {base} {grano} AA %',
        "en": 'Share {base} {grano} PY %',
        "pt": 'Share {base} {grano} AA %',
    },
    "pe_share_pp": {
        "es": 'Share {base} {grano} var pp',
        "en": 'Share {base} {grano} var pp',
        "pt": 'Share {base} {grano} var pp',
    },
    "pe_pq_mercado": {
        "es": 'El mercado total: el mismo {base} sin el filtro de {columna}. Es el denominador del share — si no se saca ese filtro, elegir tu corporación da 100 % siempre.',
        "en": 'The total market: the same {base} without the {columna} filter. It is the share denominator — without removing that filter, picking your corporation always gives 100 %.',
        "pt": 'O mercado total: o mesmo {base} sem o filtro de {columna}. É o denominador do share — sem tirar esse filtro, escolher sua corporação dá sempre 100 %.',
    },
    "pe_pq_mercado_ant": {
        "es": 'El mercado del mismo {grano} del año anterior. Hace falta aparte: el share del año pasado se recalcula con SU numerador y SU denominador, no se arrastra.',
        "en": "The market for the same {grano} of the previous year. It is needed separately: last year's share is recalculated with ITS numerator and ITS denominator, it is not carried over.",
        "pt": 'O mercado do mesmo {grano} do ano anterior. É necessário à parte: o share do ano passado é recalculado com O SEU numerador e O SEU denominador, não é arrastado.',
    },
    "pe_pq_anterior": {
        "es": '{base} en el mismo {grano} del año anterior. Se desplaza la columna de orden con TREATAS y no con SAMEPERIODLASTYEAR: así funciona también con meses sueltos elegidos en un segmentador, y con semestres, que en DAX no tienen función propia.',
        "en": '{base} in the same {grano} of the previous year. The order column is shifted with TREATAS rather than SAMEPERIODLASTYEAR: that way it also works with non-contiguous months picked in a slicer, and with semesters, which have no function of their own in DAX.',
        "pt": '{base} no mesmo {grano} do ano anterior. Desloca-se a coluna de ordem com TREATAS e não com SAMEPERIODLASTYEAR: assim funciona também com meses soltos escolhidos num segmentador, e com semestres, que no DAX não têm função própria.',
    },
    "pe_pq_variacion": {
        "es": 'Cuánto se movió {base} contra el mismo {grano} del año anterior, en porcentaje y con signo.',
        "en": 'How much {base} moved against the same {grano} of the previous year, as a signed percentage.',
        "pt": 'Quanto {base} se moveu contra o mesmo {grano} do ano anterior, em percentagem e com sinal.',
    },
    "pe_pq_ytd": {
        "es": '{base} acumulado del año, RECORTADO al mes de cierre — de los dos años. Sin ese recorte, un año que llega a junio contra un año completo muestra una caída que no existe.',
        "en": '{base} accumulated for the year, TRIMMED to the closing month — for both years. Without that trim, a year that reaches June against a full year shows a drop that does not exist.',
        "pt": '{base} acumulado do ano, RECORTADO ao mês de fechamento — dos dois anos. Sem esse recorte, um ano que chega a junho contra um ano completo mostra uma queda que não existe.',
    },
    "pe_pq_share": {
        "es": 'La participación de mercado de {base} en el {grano}: lo propio dividido el mercado total del mismo período.',
        "en": 'The market share of {base} in the {grano}: your own divided by the total market of the same period.',
        "pt": 'A participação de mercado de {base} no {grano}: o próprio dividido pelo mercado total do mesmo período.',
    },
    "pe_pq_share_ant": {
        "es": 'El share del mismo {grano} del año anterior, con numerador y denominador de ESE período.',
        "en": 'The share of the same {grano} of the previous year, with numerator and denominator from THAT period.',
        "pt": 'O share do mesmo {grano} do ano anterior, com numerador e denominador DAQUELE período.',
    },
    "pe_pq_pp": {
        "es": 'Cuánto share ganó o perdió {base} en el {grano}, en PUNTOS PORCENTUALES. Pasar de 20 % a 22 % es +2,0 pp, no +10 %: decirlo en % confunde el share con su variación.',
        "en": 'How much share {base} gained or lost in the {grano}, in PERCENTAGE POINTS. Going from 20 % to 22 % is +2.0 pp, not +10 %: saying it in % confuses the share with its change.',
        "pt": 'Quanto share {base} ganhou ou perdeu no {grano}, em PONTOS PERCENTUAIS. Passar de 20 % para 22 % é +2,0 pp, não +10 %: dizê-lo em % confunde o share com a sua variação.',
    },
    "pe_nada": {
        "es": 'No se pudo proponer ningún comparativo de período: hace falta un calendario relacionado y al menos una medida de ventas o de unidades.',
        "en": 'No period comparison could be proposed: a related calendar and at least one sales or units measure are needed.',
        "pt": 'Não foi possível propor nenhum comparativo de período: é necessário um calendário relacionado e ao menos uma medida de vendas ou de unidades.',
    },
    "inf_integridad": {
        "es": "Integridad referencial",
        "en": "Referential integrity",
        "pt": "Integridade referencial",
    },
    "inf_int_sin_t": {
        "es": "No se pudo comprobar la integridad",
        "en": "Integrity could not be checked",
        "pt": "Não foi possível verificar a integridade",
    },
    "inf_int_sin": {
        "es": "El archivo no trae las filas adentro, así que no hay contra qué contrastar las claves. Cargá el origen (Excel, CSV o SQL) y esta sección sale con los conteos reales.",
        "en": "The file does not carry its rows, so there is nothing to check the keys against. Load the source (Excel, CSV or SQL) and this section comes out with the real counts.",
        "pt": "O arquivo não traz as linhas dentro, então não há contra o que contrastar as chaves. Carregue a origem (Excel, CSV ou SQL) e esta seção sai com as contagens reais.",
    },
    "inf_int_bien_t": {
        "es": "Las {total} relaciones están limpias",
        "en": "All {total} relationships are clean",
        "pt": "As {total} relações estão limpas",
    },
    "inf_int_bien": {
        "es": "Ninguna clave del lado muchos apunta a un valor que no existe del lado uno, no hay claves vacías y ninguna clave del lado uno está repetida. Es la mitad del valor de haberlo comprobado: se puede confiar en los totales.",
        "en": "No key on the many side points to a value missing on the one side, there are no empty keys, and no key on the one side is duplicated. That is half the value of having checked: the totals can be trusted.",
        "pt": "Nenhuma chave do lado muitos aponta para um valor que não existe do lado um, não há chaves vazias e nenhuma chave do lado um está repetida. É metade do valor de ter verificado: dá para confiar nos totais.",
    },
    "inf_int_mal_t": {
        "es": "{n} de {total} relaciones necesitan revisión",
        "en": "{n} of {total} relationships need review",
        "pt": "{n} de {total} relações precisam de revisão",
    },
    "inf_int_mal": {
        "es": "Una relación con huérfanos no da error: manda esas filas a un miembro «en blanco» que nadie mira, y el total del informe queda por debajo del real sin que nada lo avise. Revisá las filas marcadas antes de publicar.",
        "en": "A relationship with orphans raises no error: it sends those rows to a “blank” member nobody looks at, and the report total ends up below the real one with nothing warning about it. Check the flagged rows before publishing.",
        "pt": "Uma relação com órfãos não dá erro: manda essas linhas para um membro «em branco» que ninguém olha, e o total do relatório fica abaixo do real sem nada avisar. Revise as linhas marcadas antes de publicar.",
    },
    "inf_int_muchos": {
        "es": "Lado muchos",
        "en": "Many side",
        "pt": "Lado muitos",
    },
    "inf_int_uno": {
        "es": "Lado uno",
        "en": "One side",
        "pt": "Lado um",
    },
    "inf_int_huerfanos": {
        "es": "Huérfanos",
        "en": "Orphans",
        "pt": "Órfãos",
    },
    "inf_int_vacios": {
        "es": "Claves vacías",
        "en": "Empty keys",
        "pt": "Chaves vazias",
    },
    "inf_int_repetidas": {
        "es": "Repetidas lado uno",
        "en": "Duplicates on one side",
        "pt": "Repetidas lado um",
    },
    "inf_int_limpia": {
        "es": "Limpia",
        "en": "Clean",
        "pt": "Limpa",
    },
    "inf_int_revisar": {
        "es": "Revisar",
        "en": "Review",
        "pt": "Revisar",
    },
    "inf_dec_t": {
        "es": "Decisiones de modelado, y por qué",
        "en": "Modelling decisions, and why",
        "pt": "Decisões de modelagem, e por quê",
    },
    "inf_dec_lead": {
        "es": "Listar las columnas ocultas y las relaciones inactivas sin explicarlas obliga a adivinar si son decisiones o descuidos — y en la duda alguien las «arregla», que es lo peor que puede pasar.",
        "en": "Listing hidden columns and inactive relationships without explaining them forces the reader to guess whether they are decisions or oversights — and in doubt someone “fixes” them, which is the worst outcome.",
        "pt": "Listar as colunas ocultas e as relações inativas sem explicá-las obriga a adivinhar se são decisões ou descuidos — e na dúvida alguém as «conserta», que é o pior que pode acontecer.",
    },
    "inf_dec_objeto": {
        "es": "Objeto",
        "en": "Object",
        "pt": "Objeto",
    },
    "inf_dec_que": {
        "es": "Qué se hizo",
        "en": "What was done",
        "pt": "O que se fez",
    },
    "inf_dec_porque": {
        "es": "Por qué",
        "en": "Why",
        "pt": "Por quê",
    },
    "inf_dec_si": {
        "es": "Si se deshace",
        "en": "If undone",
        "pt": "Se for desfeito",
    },
    "inf_dec_mas": {
        "es": "Y {n} decisiones más del mismo tipo.",
        "en": "And {n} more decisions of the same kind.",
        "pt": "E mais {n} decisões do mesmo tipo.",
    },
    "inf_s_control": {
        "es": "Cifras de control",
        "en": "Control figures",
        "pt": "Cifras de controle",
    },
    "inf_ctl_lead": {
        "es": "El valor real de cada medida que se puede reproducir sin motor DAX. Es la tabla contra la que se valida el tablero: si una tarjeta sin filtros no da este número, sobra o falta un filtro.",
        "en": "The real value of every measure that can be reproduced without a DAX engine. This is the table a dashboard is validated against: if an unfiltered card does not show this number, a filter is missing or extra.",
        "pt": "O valor real de cada medida que pode ser reproduzida sem motor DAX. É a tabela contra a qual se valida o painel: se um cartão sem filtros não dá este número, sobra ou falta um filtro.",
    },
    "inf_ctl_sin_t": {
        "es": "No hay cifras de control",
        "en": "No control figures",
        "pt": "Não há cifras de controle",
    },
    "inf_ctl_sin": {
        "es": "Para calcularlas hace falta que las filas viajen adentro del archivo, o cargar el origen. Sin datos no se estima: un valor aproximado en esta tabla sería una mentira con formato de dato.",
        "en": "Computing them requires the rows to travel inside the file, or the source to be loaded. Without data nothing is estimated: an approximate value in this table would be a lie formatted as data.",
        "pt": "Para calculá-las é preciso que as linhas viajem dentro do arquivo, ou carregar a origem. Sem dados não se estima: um valor aproximado nesta tabela seria uma mentira com formato de dado.",
    },
    "inf_ctl_como": {
        "es": "Cómo se calcula",
        "en": "How it is computed",
        "pt": "Como se calcula",
    },
    "inf_ctl_valor": {
        "es": "Valor sin filtros",
        "en": "Value with no filters",
        "pt": "Valor sem filtros",
    },
    "inf_ctl_suma": {
        "es": "Suma de la columna",
        "en": "Sum of the column",
        "pt": "Soma da coluna",
    },
    "inf_ctl_promedio": {
        "es": "Promedio de la columna",
        "en": "Average of the column",
        "pt": "Média da coluna",
    },
    "inf_ctl_distintos": {
        "es": "Valores distintos",
        "en": "Distinct values",
        "pt": "Valores distintos",
    },
    "inf_ctl_filas": {
        "es": "Filas de la tabla",
        "en": "Rows in the table",
        "pt": "Linhas da tabela",
    },
    "inf_ctl_alcance_t": {
        "es": "Hasta dónde llega esta comprobación",
        "en": "How far this check goes",
        "pt": "Até onde vai esta verificação",
    },
    "inf_ctl_alcance": {
        "es": "Se pudieron calcular {n} de {total} medidas. Las otras {resto} usan CALCULATE, inteligencia de tiempo o razones, que necesitan el motor de Power BI: decir «no la pude calcular» es información, inventarle un valor aproximado no.",
        "en": "{n} of {total} measures could be computed. The other {resto} use CALCULATE, time intelligence or ratios, which need the Power BI engine: saying “I could not compute it” is information, giving it an approximate value is not.",
        "pt": "Foi possível calcular {n} de {total} medidas. As outras {resto} usam CALCULATE, inteligência de tempo ou razões, que precisam do motor do Power BI: dizer «não consegui calcular» é informação, inventar um valor aproximado não.",
    },
    "inf_ctl_gemelas_t": {
        "es": "Dos nombres para el mismo número",
        "en": "Two names for the same number",
        "pt": "Dois nomes para o mesmo número",
    },
    "inf_ctl_gemelas": {
        "es": "{medidas} devuelven el mismo valor ({valor}) sobre el total, sin filtros. Hay dos causas posibles y conviene distinguirlas: si son la MISMA cuenta escrita distinto —típico cuando una columna vale 1 en todas las filas, y entonces sumarla es contar filas— sobra una y hay que borrarla; si son cuentas distintas que hoy empatan, se van a separar en cuanto se filtre por mes o por categoría, y la que hay que revisar es la página que las muestre juntas sin ese corte.",
        "en": "{medidas} return the same value ({valor}) on the unfiltered total. There are two possible causes and they are worth telling apart: if they are the SAME count written differently — typical when a column is 1 on every row, so summing it is counting rows — one of them is redundant and should go; if they are different counts that happen to tie today, they will separate as soon as you filter by month or category, and what needs review is any page showing them together without that slicer.",
        "pt": "{medidas} devolvem o mesmo valor ({valor}) no total, sem filtros. Há duas causas possíveis e convém distingui-las: se são a MESMA contagem escrita de outra forma — típico quando uma coluna vale 1 em todas as linhas, e então somá-la é contar linhas — uma sobra e deve ser removida; se são contagens distintas que hoje empatam, vão se separar assim que filtrar por mês ou categoria, e o que precisa de revisão é a página que as mostre juntas sem esse corte.",
    },
    # ---- Estrella vs. copo de nieve ------------------------------------
    "inf_forma_t": {
        "es": "Estrella o copo de nieve",
        "en": "Star or snowflake",
        "pt": "Estrela ou floco de neve",
    },
    "inf_forma_lead": {
        "es": "La forma del modelo no es una preferencia de estilo: decide cuántos saltos tiene que dar un filtro para llegar al hecho que se mide. Cada salto cuesta tiempo de cálculo y agrega una oportunidad más de que el filtro no llegue y el visual muestre el mismo número en todas las filas.",
        "en": "The shape of the model is not a matter of taste: it decides how many hops a filter must travel to reach the fact being measured. Every hop costs query time and adds one more chance for the filter not to arrive, leaving the visual showing the same number on every row.",
        "pt": "A forma do modelo não é preferência de estilo: decide quantos saltos um filtro precisa dar para chegar ao fato medido. Cada salto custa tempo de cálculo e acrescenta mais uma chance de o filtro não chegar, deixando o visual com o mesmo número em todas as linhas.",
    },
    "inf_forma_col_que": {"es": "En qué se diferencian", "en": "How they differ", "pt": "Em que diferem"},
    "inf_forma_col_estrella": {"es": "Estrella", "en": "Star", "pt": "Estrela"},
    "inf_forma_col_copo": {"es": "Copo de nieve", "en": "Snowflake", "pt": "Floco de neve"},
    "inf_forma_f1_que": {"es": "Cómo se conectan las tablas", "en": "How tables connect", "pt": "Como as tabelas se conectam"},
    "inf_forma_f1_estrella": {
        "es": "Cada dimensión cuelga DIRECTO del hecho. Un solo salto.",
        "en": "Every dimension hangs DIRECTLY off the fact. One single hop.",
        "pt": "Cada dimensão pende DIRETO do fato. Um único salto.",
    },
    "inf_forma_f1_copo": {
        "es": "Una dimensión cuelga de otra dimensión, y ésa del hecho. Dos saltos o más.",
        "en": "A dimension hangs off another dimension, and that one off the fact. Two hops or more.",
        "pt": "Uma dimensão pende de outra dimensão, e essa do fato. Dois saltos ou mais.",
    },
    "inf_forma_f2_que": {"es": "Cómo se ve", "en": "What it looks like", "pt": "Como se vê"},
    "inf_forma_f2_estrella": {
        "es": "Producto → Ventas ← Fecha. Las dimensiones rodean al hecho.",
        "en": "Product → Sales ← Date. Dimensions surround the fact.",
        "pt": "Produto → Vendas ← Data. As dimensões cercam o fato.",
    },
    "inf_forma_f2_copo": {
        "es": "Categoría → Producto → Ventas. La categoría no toca al hecho.",
        "en": "Category → Product → Sales. Category never touches the fact.",
        "pt": "Categoria → Produto → Vendas. A categoria não toca o fato.",
    },
    "inf_forma_f3_que": {"es": "Qué gana", "en": "What it gains", "pt": "O que ganha"},
    "inf_forma_f3_estrella": {
        "es": "Consultas más rápidas, DAX más simple, y un panel de campos que se entiende sin explicación.",
        "en": "Faster queries, simpler DAX, and a field pane that needs no explanation.",
        "pt": "Consultas mais rápidas, DAX mais simples e um painel de campos que se entende sem explicação.",
    },
    "inf_forma_f3_copo": {
        "es": "Menos repetición de texto en la base: la categoría se escribe una vez y no en cada producto.",
        "en": "Less repeated text in storage: the category is written once, not on every product.",
        "pt": "Menos repetição de texto na base: a categoria se escreve uma vez, não em cada produto.",
    },
    "inf_forma_f4_que": {"es": "Qué cuesta", "en": "What it costs", "pt": "O que custa"},
    "inf_forma_f4_estrella": {
        "es": "La dimensión repite valores. En un modelo analítico eso es barato: el motor comprime por columna.",
        "en": "The dimension repeats values. In an analytical model that is cheap: the engine compresses by column.",
        "pt": "A dimensão repete valores. Num modelo analítico isso é barato: o motor comprime por coluna.",
    },
    "inf_forma_f4_copo": {
        "es": "Cada salto extra es más lento y más frágil. Es la forma natural de una base transaccional, no de un modelo de análisis.",
        "en": "Each extra hop is slower and more fragile. It is the natural shape of a transactional database, not of an analytical model.",
        "pt": "Cada salto extra é mais lento e mais frágil. É a forma natural de um banco transacional, não de um modelo de análise.",
    },
    "inf_forma_estrella_t": {
        "es": "Este modelo es una estrella",
        "en": "This model is a star",
        "pt": "Este modelo é uma estrela",
    },
    "inf_forma_estrella": {
        "es": "{hechos} tablas de hechos y {dims} dimensiones, y ninguna dimensión cuelga de otra: todo filtro llega al hecho en un solo salto. Es la forma recomendada para Power BI y no hay nada que cambiar acá.",
        "en": "{hechos} fact tables and {dims} dimensions, and no dimension hangs off another: every filter reaches the fact in a single hop. This is the recommended shape for Power BI and there is nothing to change here.",
        "pt": "{hechos} tabelas de fatos e {dims} dimensões, e nenhuma dimensão pende de outra: todo filtro chega ao fato num único salto. É a forma recomendada para Power BI e não há o que mudar aqui.",
    },
    "inf_forma_copo_t": {
        "es": "Este modelo es un copo de nieve",
        "en": "This model is a snowflake",
        "pt": "Este modelo é um floco de neve",
    },
    "inf_forma_copo": {
        "es": "{tablas} está en el medio: cuelga de otra dimensión en vez de colgar del hecho. Funciona, pero cada filtro que venga de ahí da un salto de más. Si el informe se pone lento o alguna medida no responde a un corte, aplanar esa tabla dentro de su dimensión —en Power Query, no en DAX— es el primer arreglo a probar.",
        "en": "{tablas} sits in the middle: it hangs off another dimension instead of off the fact. It works, but every filter coming from there travels one extra hop. If the report gets slow or a measure stops responding to a slicer, flattening that table into its dimension —in Power Query, not in DAX— is the first fix to try.",
        "pt": "{tablas} está no meio: pende de outra dimensão em vez de pender do fato. Funciona, mas todo filtro que vem dali dá um salto a mais. Se o relatório ficar lento ou alguma medida não responder a um corte, achatar essa tabela dentro da sua dimensão —no Power Query, não em DAX— é o primeiro ajuste a tentar.",
    },
    # ---- Modificadores de contexto de filtro ----------------------------
    "inf_mod_t": {
        "es": "Los cuatro modificadores de filtro, y cuál usar",
        "en": "The four filter modifiers, and which one to use",
        "pt": "Os quatro modificadores de filtro, e qual usar",
    },
    "inf_mod_lead": {
        "es": "Es la pregunta que más se repite al leer un DAX ajeno: «¿por qué acá dice ALL y allá ALLSELECTED?». Importa porque los cuatro devuelven un número creíble y sólo uno responde la pregunta que se hizo. La regla corta: primero decidí QUÉ TOTAL querés como denominador, y recién después escribí la función.",
        "en": "This is the most common question when reading someone else's DAX: “why ALL here and ALLSELECTED there?”. It matters because all four return a believable number and only one answers the question actually asked. Short rule: first decide WHICH TOTAL you want as the denominator, and only then write the function.",
        "pt": "É a pergunta que mais se repete ao ler um DAX alheio: «por que aqui diz ALL e ali ALLSELECTED?». Importa porque os quatro devolvem um número plausível e só um responde à pergunta feita. Regra curta: primeiro decida QUAL TOTAL você quer como denominador e só então escreva a função.",
    },
    "inf_mod_col_fn": {"es": "Función", "en": "Function", "pt": "Função"},
    "inf_mod_col_cuando": {"es": "Cuándo la querés", "en": "When you want it", "pt": "Quando você a quer"},
    "inf_mod_col_ej": {"es": "Ejemplo", "en": "Example", "pt": "Exemplo"},
    "inf_mod_col_da": {"es": "Qué devuelve", "en": "What it returns", "pt": "O que devolve"},
    "inf_mod_usado": {"es": "usada acá", "en": "used here", "pt": "usada aqui"},
    "inf_mod_all_fn": {"es": "ALL / REMOVEFILTERS", "en": "ALL / REMOVEFILTERS", "pt": "ALL / REMOVEFILTERS"},
    "inf_mod_all_cuando": {
        "es": "Querés el TOTAL ABSOLUTO: el 100 % de la tabla, sin importar qué filtró el usuario.",
        "en": "You want the ABSOLUTE TOTAL: 100 % of the table, no matter what the user filtered.",
        "pt": "Você quer o TOTAL ABSOLUTO: 100 % da tabela, não importa o que o usuário filtrou.",
    },
    "inf_mod_all_ej": {
        "es": "% del total =\nDIVIDE (\n    [Ventas],\n    CALCULATE ( [Ventas], REMOVEFILTERS ( Producto ) )\n)",
        "en": "% of total =\nDIVIDE (\n    [Sales],\n    CALCULATE ( [Sales], REMOVEFILTERS ( Product ) )\n)",
        "pt": "% do total =\nDIVIDE (\n    [Vendas],\n    CALCULATE ( [Vendas], REMOVEFILTERS ( Produto ) )\n)",
    },
    "inf_mod_all_da": {
        "es": "Si el usuario filtra una categoría, el denominador NO cambia: sigue siendo la venta de todos los productos. Los porcentajes de la pantalla ya no suman 100 %.",
        "en": "If the user filters a category, the denominator does NOT change: it stays the sales of every product. The percentages on screen no longer add up to 100 %.",
        "pt": "Se o usuário filtra uma categoria, o denominador NÃO muda: continua sendo a venda de todos os produtos. As porcentagens da tela já não somam 100 %.",
    },
    "inf_mod_allselected_fn": {"es": "ALLSELECTED", "en": "ALLSELECTED", "pt": "ALLSELECTED"},
    "inf_mod_allselected_cuando": {
        "es": "Querés el total DE LO QUE EL USUARIO VE en pantalla: respeta los segmentadores, ignora sólo el eje del visual.",
        "en": "You want the total OF WHAT THE USER SEES on screen: it respects the slicers and ignores only the visual's own axis.",
        "pt": "Você quer o total DO QUE O USUÁRIO VÊ na tela: respeita os segmentadores e ignora só o eixo do visual.",
    },
    "inf_mod_allselected_ej": {
        "es": "% de lo visible =\nDIVIDE (\n    [Ventas],\n    CALCULATE ( [Ventas], ALLSELECTED ( Producto ) )\n)",
        "en": "% of what is shown =\nDIVIDE (\n    [Sales],\n    CALCULATE ( [Sales], ALLSELECTED ( Product ) )\n)",
        "pt": "% do visível =\nDIVIDE (\n    [Vendas],\n    CALCULATE ( [Vendas], ALLSELECTED ( Produto ) )\n)",
    },
    "inf_mod_allselected_da": {
        "es": "Los porcentajes SIEMPRE suman 100 % en la pantalla, filtre lo que filtre el usuario. Es la que quiere casi todo gráfico de participación.",
        "en": "The percentages ALWAYS add up to 100 % on screen, whatever the user filters. This is the one nearly every share chart wants.",
        "pt": "As porcentagens SEMPRE somam 100 % na tela, filtre o que filtrar o usuário. É a que quase todo gráfico de participação quer.",
    },
    "inf_mod_allexcept_fn": {"es": "ALLEXCEPT", "en": "ALLEXCEPT", "pt": "ALLEXCEPT"},
    "inf_mod_allexcept_cuando": {
        "es": "Querés soltar TODOS los filtros de una tabla MENOS uno: el total dentro de un grupo.",
        "en": "You want to drop ALL filters on a table EXCEPT one: the total within a group.",
        "pt": "Você quer soltar TODOS os filtros de uma tabela MENOS um: o total dentro de um grupo.",
    },
    "inf_mod_allexcept_ej": {
        "es": "% dentro de la categoría =\nDIVIDE (\n    [Ventas],\n    CALCULATE (\n        [Ventas],\n        ALLEXCEPT ( Producto, Producto[Categoria] )\n    )\n)",
        "en": "% within category =\nDIVIDE (\n    [Sales],\n    CALCULATE (\n        [Sales],\n        ALLEXCEPT ( Product, Product[Category] )\n    )\n)",
        "pt": "% dentro da categoria =\nDIVIDE (\n    [Vendas],\n    CALCULATE (\n        [Vendas],\n        ALLEXCEPT ( Produto, Produto[Categoria] )\n    )\n)",
    },
    "inf_mod_allexcept_da": {
        "es": "Cada producto contra el total de SU categoría. Dentro de cada categoría los porcentajes suman 100 %, y entre categorías no.",
        "en": "Each product against the total of ITS category. Within each category the percentages add up to 100 %, across categories they do not.",
        "pt": "Cada produto contra o total da SUA categoria. Dentro de cada categoria as porcentagens somam 100 %, entre categorias não.",
    },
    "inf_mod_keepfilters_fn": {"es": "KEEPFILTERS", "en": "KEEPFILTERS", "pt": "KEEPFILTERS"},
    "inf_mod_keepfilters_cuando": {
        "es": "Vas a AGREGAR una condición y NO querés que reemplace el filtro que ya tiene la fila.",
        "en": "You are about to ADD a condition and do NOT want it to replace the filter the row already has.",
        "pt": "Você vai ADICIONAR uma condição e NÃO quer que ela substitua o filtro que a linha já tem.",
    },
    "inf_mod_keepfilters_ej": {
        "es": "-- SIN keepfilters: pisa el eje\nVentas Norte =\nCALCULATE ( [Ventas], Region[Zona] = \"Norte\" )\n\n-- CON keepfilters: se interseca\nVentas Norte =\nCALCULATE (\n    [Ventas],\n    KEEPFILTERS ( Region[Zona] = \"Norte\" )\n)",
        "en": "-- WITHOUT keepfilters: it overrides the axis\nNorth Sales =\nCALCULATE ( [Sales], Region[Zone] = \"North\" )\n\n-- WITH keepfilters: it intersects\nNorth Sales =\nCALCULATE (\n    [Sales],\n    KEEPFILTERS ( Region[Zone] = \"North\" )\n)",
        "pt": "-- SEM keepfilters: atropela o eixo\nVendas Norte =\nCALCULATE ( [Vendas], Regiao[Zona] = \"Norte\" )\n\n-- COM keepfilters: intersecta\nVendas Norte =\nCALCULATE (\n    [Vendas],\n    KEEPFILTERS ( Regiao[Zona] = \"Norte\" )\n)",
    },
    "inf_mod_keepfilters_da": {
        "es": "En una tabla abierta POR zona: sin KEEPFILTERS las cuatro zonas muestran el número del Norte —el filtro de la medida reemplaza al de la fila—; con KEEPFILTERS el Norte muestra lo suyo y las otras quedan en blanco, que es lo correcto.",
        "en": "In a table broken down BY zone: without KEEPFILTERS all four zones show the North number —the measure's filter replaces the row's—; with KEEPFILTERS the North shows its own and the others come back blank, which is correct.",
        "pt": "Numa tabela aberta POR zona: sem KEEPFILTERS as quatro zonas mostram o número do Norte —o filtro da medida substitui o da linha—; com KEEPFILTERS o Norte mostra o seu e as outras ficam em branco, que é o correto.",
    },
    "inf_mod_regla_t": {
        "es": "Cómo elegir sin equivocarse",
        "en": "How to choose without getting it wrong",
        "pt": "Como escolher sem errar",
    },
    "inf_mod_regla": {
        "es": "Preguntate qué tiene que pasar cuando el usuario mueve un segmentador. Si el denominador NO se tiene que mover, es ALL/REMOVEFILTERS. Si se tiene que mover con el segmentador pero no con el eje del visual, es ALLSELECTED. Si se tiene que mover sólo dentro de un grupo, es ALLEXCEPT. Y si en vez de un denominador estás agregando una condición, va KEEPFILTERS salvo que quieras a propósito pisar el eje.",
        "en": "Ask yourself what must happen when the user moves a slicer. If the denominator must NOT move, it is ALL/REMOVEFILTERS. If it must move with the slicer but not with the visual's axis, it is ALLSELECTED. If it must move only within a group, it is ALLEXCEPT. And if instead of a denominator you are adding a condition, use KEEPFILTERS unless you deliberately want to override the axis.",
        "pt": "Pergunte-se o que deve acontecer quando o usuário move um segmentador. Se o denominador NÃO deve se mover, é ALL/REMOVEFILTERS. Se deve se mover com o segmentador mas não com o eixo do visual, é ALLSELECTED. Se deve se mover só dentro de um grupo, é ALLEXCEPT. E se em vez de um denominador você está adicionando uma condição, use KEEPFILTERS a menos que queira de propósito atropelar o eixo.",
    },
    # ---- Diccionario de medidas: por qué cada fórmula es así -----------
    "dic_ventana": {
        "es": "Recorta las dos puntas a la ventana que sí existe en el calendario, para no comparar 18 meses contra 6.",
        "en": "Clips both ends to the window that actually exists in the calendar, so it never compares 18 months against 6.",
        "pt": "Recorta as duas pontas para a janela que existe no calendário, para não comparar 18 meses contra 6.",
    },
    "dic_guardia": {
        "es": "Cuenta los días de cada lado y devuelve vacío si no coinciden: una celda vacía dice «no comparable».",
        "en": "Counts the days on each side and returns blank if they differ: an empty cell says “not comparable”.",
        "pt": "Conta os dias de cada lado e devolve vazio se não coincidem: uma célula vazia diz «não comparável».",
    },
    "dic_aa": {
        "es": "Desplaza el período visible un año atrás para comparar contra el mismo tramo.",
        "en": "Shifts the visible period one year back to compare against the same stretch.",
        "pt": "Desloca o período visível um ano atrás para comparar contra o mesmo trecho.",
    },
    "dic_ytd": {
        "es": "Acumula desde el 1 de enero hasta la fecha visible.",
        "en": "Accumulates from January 1st up to the visible date.",
        "pt": "Acumula desde 1º de janeiro até a data visível.",
    },
    "dic_qtd": {
        "es": "Acumula desde el inicio del trimestre visible.",
        "en": "Accumulates from the start of the visible quarter.",
        "pt": "Acumula desde o início do trimestre visível.",
    },
    "dic_entre": {
        "es": "Acumula entre dos fechas calculadas, porque no hay función nativa para ese período.",
        "en": "Accumulates between two computed dates, because there is no native function for that period.",
        "pt": "Acumula entre duas datas calculadas, porque não há função nativa para esse período.",
    },
    "dic_quita": {
        "es": "Quita un filtro a propósito para que el denominador sea el TOTAL ABSOLUTO y no se mueva con el corte del usuario.",
        "en": "Deliberately drops a filter so the denominator is the ABSOLUTE TOTAL and does not move with the user's slicer.",
        "pt": "Tira um filtro de propósito para que o denominador seja o TOTAL ABSOLUTO e não se mova com o corte do usuário.",
    },
    "dic_visible": {
        "es": "El denominador es el total DE LO QUE SE VE en pantalla: respeta los segmentadores, ignora el eje del visual.",
        "en": "The denominator is the total OF WHAT IS SHOWN on screen: it respects slicers and ignores the visual's axis.",
        "pt": "O denominador é o total DO QUE SE VÊ na tela: respeita os segmentadores e ignora o eixo do visual.",
    },
    "dic_salvo": {
        "es": "Suelta todos los filtros de la tabla menos uno: da el total DENTRO del grupo.",
        "en": "Drops every filter on the table except one: it gives the total WITHIN the group.",
        "pt": "Solta todos os filtros da tabela menos um: dá o total DENTRO do grupo.",
    },
    "dic_keep": {
        "es": "Agrega la condición SIN pisar el filtro de la fila: se intersecan, así la medida sigue variando con el eje.",
        "en": "Adds the condition WITHOUT overriding the row's filter: they intersect, so the measure still varies with the axis.",
        "pt": "Adiciona a condição SEM atropelar o filtro da linha: intersectam-se, então a medida continua variando com o eixo.",
    },
    "dic_promedio_x": {
        "es": "Promedia la medida período a período, no sobre el total: un acumulado largo daría un número que no se puede gestionar.",
        "en": "Averages the measure period by period, not over the whole total: a long cumulative figure would be unmanageable.",
        "pt": "Faz a média da medida período a período, não sobre o total: um acumulado longo daria um número que não se pode gerir.",
    },
    "dic_ranking": {
        "es": "Ordena contra todos los valores de la columna, no sólo contra los visibles.",
        "en": "Ranks against every value in the column, not just the visible ones.",
        "pt": "Ordena contra todos os valores da coluna, não só contra os visíveis.",
    },
    "dic_distintos": {
        "es": "Cuenta valores DISTINTOS: mide alcance, no volumen. Un médico con diez visitas cuenta una vez.",
        "en": "Counts DISTINCT values: it measures reach, not volume. A doctor with ten visits counts once.",
        "pt": "Conta valores DISTINTOS: mede alcance, não volume. Um médico com dez visitas conta uma vez.",
    },
    "dic_division": {
        "es": "Divide con DIVIDE y no con «/»: si el denominador es cero devuelve vacío en vez de un error que rompe el visual.",
        "en": "Divides with DIVIDE and not “/”: if the denominator is zero it returns blank instead of an error that breaks the visual.",
        "pt": "Divide com DIVIDE e não com «/»: se o denominador for zero devolve vazio em vez de um erro que quebra o visual.",
    },
    "dic_filas": {
        "es": "Cuenta filas de la tabla: el volumen de operaciones del período.",
        "en": "Counts table rows: the volume of transactions in the period.",
        "pt": "Conta linhas da tabela: o volume de operações do período.",
    },
    "dic_texto": {
        "es": "Devuelve TEXTO, no un número: se recalcula con los filtros, así que la conclusión que escribe cambia con lo que el usuario elige.",
        "en": "Returns TEXT, not a number: it recalculates with the filters, so the conclusion it writes changes with the user's selection.",
        "pt": "Devolve TEXTO, não um número: recalcula-se com os filtros, então a conclusão que escreve muda com o que o usuário escolhe.",
    },
    "dic_condicion": {
        "es": "Aplica una condición extra al contexto de filtro que trae el visual.",
        "en": "Applies an extra condition on top of the filter context the visual brings.",
        "pt": "Aplica uma condição extra ao contexto de filtro que o visual traz.",
    },
    "dic_suma": {
        "es": "Suma una columna: es la medida base sobre la que se construyen las demás.",
        "en": "Sums a column: it is the base measure the others are built on.",
        "pt": "Soma uma coluna: é a medida base sobre a qual as outras se constroem.",
    },
    "dic_directa": {
        "es": "Cálculo directo, sin modificar el contexto de filtro.",
        "en": "Direct calculation, with no change to the filter context.",
        "pt": "Cálculo direto, sem modificar o contexto de filtro.",
    },
    "dic_pagina": {
        "es": "Diccionario de medidas",
        "en": "Measure dictionary",
        "pt": "Dicionário de medidas",
    },
    "dic_titulo": {
        "es": "Cada medida, su fórmula y por qué está escrita así",
        "en": "Every measure, its formula and why it is written that way",
        "pt": "Cada medida, sua fórmula e por que está escrita assim",
    },
    # ---- Ruta: los contactos de una entidad, en orden ------------------
    "ruta_sin_resultado": {
        "es": "Sin resultado registrado", "en": "No result recorded",
        "pt": "Sem resultado registrado",
    },
    "ruta_med_contactos": {"es": "Contactos", "en": "Contacts",
                           "pt": "Contatos"},
    "ruta_pq_contactos": {
        "es": "Todos los contactos sumados, venga del canal que venga. Es la pregunta que las tablas separadas no podían responder sin un UNION.",
        "en": "Every contact added up, whatever the channel. It is the question separate tables could not answer without a UNION.",
        "pt": "Todos os contatos somados, venha do canal que vier. É a pergunta que as tabelas separadas não podiam responder sem um UNION.",
    },
    "ruta_med_por_entidad": {"es": "Contactos por Entidad",
                             "en": "Contacts per Entity",
                             "pt": "Contatos por Entidade"},
    "ruta_pq_por_entidad": {
        "es": "La intensidad real del esfuerzo: cuántas veces se toca en promedio a cada uno, sumando todos los canales.",
        "en": "The real intensity of the effort: how many times each one is touched on average, across every channel.",
        "pt": "A intensidade real do esforço: quantas vezes se toca em média cada um, somando todos os canais.",
    },
    "ruta_med_larga": {"es": "Ruta Más Larga", "en": "Longest Journey",
                       "pt": "Rota Mais Longa"},
    "ruta_pq_larga": {
        "es": "Cuántos contactos acumula el más trabajado. Es el techo del esfuerzo, no el promedio: sirve para ver si hay alguien sobre-contactado.",
        "en": "How many contacts the most-worked one accumulates. It is the ceiling of the effort, not the average: it shows whether anyone is over-contacted.",
        "pt": "Quantos contatos acumula o mais trabalhado. É o teto do esforço, não a média: serve para ver se há alguém sobrecontatado.",
    },
    "ruta_med_efectivos": {"es": "Contactos Efectivos",
                           "en": "Effective Contacts",
                           "pt": "Contatos Efetivos"},
    "ruta_pq_efectivos": {
        "es": "Los que llegaron a destino. Una visita cancelada y un envío que nadie abrió cuestan igual y valen distinto.",
        "en": "The ones that landed. A cancelled visit and an unopened email cost the same and are worth different things.",
        "pt": "Os que chegaram ao destino. Uma visita cancelada e um envio que ninguém abriu custam igual e valem diferente.",
    },
    "ruta_med_efectividad": {"es": "Efectividad del Contacto %",
                             "en": "Contact Effectiveness %",
                             "pt": "Efetividade do Contato %"},
    "ruta_pq_efectividad": {
        "es": "Qué proporción del esfuerzo llegó a destino. Comparable entre canales porque los dos usan el mismo vocabulario de resultado.",
        "en": "What share of the effort landed. Comparable across channels because both use the same result vocabulary.",
        "pt": "Que proporção do esforço chegou ao destino. Comparável entre canais porque ambos usam o mesmo vocabulário de resultado.",
    },
    "ruta_pagina": {"es": "Ruta", "en": "Journey", "pt": "Rota"},
    "ruta_titulo": {
        "es": "La ruta, contacto por contacto · elegí uno en el corte para seguir su secuencia",
        "en": "The journey, contact by contact · pick one in the slicer to follow its sequence",
        "pt": "A rota, contato a contato · escolha um no corte para seguir sua sequência",
    },
    "inf_conc_t": {
        "es": "Concentración",
        "en": "Concentration",
        "pt": "Concentração",
    },
    "inf_conc_titulo": {
        "es": "Dónde está el negocio",
        "en": "Where the business is",
        "pt": "Onde está o negócio",
    },
    "inf_conc": {
        "es": "Los primeros {n} de {miembros} hacen el {parte} % del total de {valor}. Es el número que decide dónde se pone el esfuerzo: cuanto más concentrado, más caro es perder uno.",
        "en": "The top {n} of {miembros} account for {parte} % of total {valor}. This is the number that decides where effort goes: the more concentrated, the more expensive losing one becomes.",
        "pt": "Os primeiros {n} de {miembros} fazem {parte} % do total de {valor}. É o número que decide onde se coloca o esforço: quanto mais concentrado, mais caro é perder um.",
    },
    "inf_conc_parte": {
        "es": "Parte del total",
        "en": "Share of total",
        "pt": "Parte do total",
    },
    "inf_con_t": {
        "es": "Conclusiones para decidir",
        "en": "Conclusions to act on",
        "pt": "Conclusões para decidir",
    },
    "inf_con_cada": {
        "es": "Conclusión {i}",
        "en": "Conclusion {i}",
        "pt": "Conclusão {i}",
    },
    "inf_con_share": {
        "es": "{propia} creció {propio:+.1f} % y el mercado {mercado:+.1f} %: la participación se movió {pp:+.1f} puntos. Crecer por debajo del mercado es perder terreno aunque el número propio suba — la decisión no es «vender más», es dónde el mercado crece y nosotros no.",
        "en": "{propia} grew {propio:+.1f} % against a market at {mercado:+.1f} %: share moved {pp:+.1f} points. Growing below the market means losing ground even when the own number rises — the decision is not “sell more”, it is where the market grows and we do not.",
        "pt": "{propia} cresceu {propio:+.1f} % e o mercado {mercado:+.1f} %: a participação moveu-se {pp:+.1f} pontos. Crescer abaixo do mercado é perder terreno mesmo que o número próprio suba — a decisão não é «vender mais», é onde o mercado cresce e nós não.",
    },
    "inf_con_conc": {
        "es": "Los primeros {n} de {miembros} de {dimension} hacen el {parte} % del negocio. Con esa concentración, perder uno cuesta más que ganar tres de la cola: el esfuerzo comercial y el stock se defienden ahí primero.",
        "en": "The top {n} of {miembros} in {dimension} account for {parte} % of the business. At that concentration, losing one costs more than winning three from the tail: commercial effort and stock are defended there first.",
        "pt": "Os primeiros {n} de {miembros} de {dimension} fazem {parte} % do negócio. Com essa concentração, perder um custa mais do que ganhar três da cauda: o esforço comercial e o estoque defendem-se ali primeiro.",
    },
    "inf_con_int_bien": {
        "es": "Las {total} relaciones están limpias: ningún total del informe está por debajo del real por claves que no cruzan. Los números se pueden llevar a una reunión.",
        "en": "All {total} relationships are clean: no report total falls below the real one because of keys that do not match. The numbers can be taken to a meeting.",
        "pt": "As {total} relações estão limpas: nenhum total do relatório fica abaixo do real por chaves que não cruzam. Os números podem ir para uma reunião.",
    },
    "inf_con_int_mal": {
        "es": "{n} de {total} relaciones tienen claves que no cruzan. Hasta resolverlo, cualquier total de este informe puede estar por debajo del real, y no hay forma de saber por cuánto sin arreglarlo primero.",
        "en": "{n} of {total} relationships have keys that do not match. Until that is resolved, any total in this report may fall below the real one, and there is no way to know by how much without fixing it first.",
        "pt": "{n} de {total} relações têm chaves que não cruzam. Até resolver isso, qualquer total deste relatório pode estar abaixo do real, e não há como saber por quanto sem consertar primeiro.",
    },
    "inf_con_altas": {
        "es": "Hay {n} hallazgo(s) de severidad alta. Son los que rompen números o hacen que Power BI rechace el modelo: se resuelven antes de publicar, no después.",
        "en": "There are {n} high-severity finding(s). These break numbers or make Power BI reject the model: they are resolved before publishing, not after.",
        "pt": "Há {n} achado(s) de severidade alta. São os que quebram números ou fazem o Power BI rejeitar o modelo: resolvem-se antes de publicar, não depois.",
    },
    "vf_ejes": {
        "es": "Ejes que las medidas escuchan",
        "en": "Axes the measures respond to",
        "pt": "Eixos que as medidas escutam",
    },
    "vf_ejes_ok": {
        "es": "En los {total} visuales con eje y medidas, cada eje llega por las relaciones a las tablas de sus medidas.",
        "en": "Across the {total} visuals with an axis and measures, every axis reaches its measures' tables through the relationships.",
        "pt": "Nos {total} visuais com eixo e medidas, cada eixo chega pelas relações às tabelas das suas medidas.",
    },
    "vf_ejes_falta": {
        "es": "{n} ejes que las medidas del visual no escuchan ({lista}). No dan error: repiten el MISMO total en cada barra y en cada fila, con cara de hallazgo — el peor gráfico posible.",
        "en": "{n} axes the visual's measures do not respond to ({lista}). They throw no error: they repeat the SAME total on every bar and every row, looking like a finding — the worst possible chart.",
        "pt": "{n} eixos que as medidas do visual não escutam ({lista}). Não dão erro: repetem o MESMO total em cada barra e em cada linha, com cara de descoberta — o pior gráfico possível.",
    },

    "vf_constantes": {
        "es": "Medidas que no se mueven",
        "en": "Measures that do not move",
        "pt": "Medidas que não se movem",
    },
    "vf_constantes_ok": {
        "es": "Ninguna medida queda constante por construcción: cada columna de cada visual responde al eje que tiene al lado.",
        "en": "No measure is constant by construction: every column in every visual responds to the axis next to it.",
        "pt": "Nenhuma medida fica constante por construção: cada coluna de cada visual responde ao eixo que tem ao lado.",
    },
    "vf_constantes_aviso": {
        "es": "{n} medida(s) van a mostrar el MISMO número en todas las filas ({lista}): quitan el filtro de una columna que el visual no tiene en el eje, así que el numerador y el denominador se filtran igual. Da 100 % —o 0,0 en su variación— y parece un dato.",
        "en": "{n} measure(s) will show the SAME number in every row ({lista}): they remove the filter on a column the visual does not have on its axis, so numerator and denominator are filtered alike. It reads 100 % — or 0.0 for its variation — and looks like data.",
        "pt": "{n} medida(s) vão mostrar o MESMO número em todas as linhas ({lista}): removem o filtro de uma coluna que o visual não tem no eixo, então numerador e denominador filtram-se igual. Dá 100 % — ou 0,0 na variação — e parece um dado.",
    },
    "inf_cru_t": {
        "es": "Esfuerzo contra retorno",
        "en": "Effort against return",
        "pt": "Esforço contra retorno",
    },
    "inf_cru_lead": {
        "es": "Todo lo que le pasa a un mismo miembro, en una sola tabla. Los totales por grupo no alcanzan —el grupo más grande siempre parece el mejor—, así que todo va dividido por la cantidad de miembros del grupo.",
        "en": "Everything that happens to one member, in a single table. Group totals are not enough — the largest group always looks best — so everything is divided by the number of members in the group.",
        "pt": "Tudo o que acontece a um mesmo membro, numa só tabela. Os totais por grupo não bastam — o grupo maior sempre parece o melhor — então tudo vai dividido pela quantidade de membros do grupo.",
    },
    "inf_cru_miembros": {
        "es": "Miembros",
        "en": "Members",
        "pt": "Membros",
    },
    "inf_cru_cada": {
        "es": "por miembro",
        "en": "per member",
        "pt": "por membro",
    },
    "inf_cru_mal_t": {
        "es": "El esfuerzo no está donde rinde",
        "en": "Effort is not where the return is",
        "pt": "O esforço não está onde rende",
    },
    "inf_cru_mal": {
        "es": "«{mejor}» rinde {veces} veces más que «{peor}» en {resultado} ({rinde_mejor} contra {rinde_peor} por miembro), y sin embargo recibe igual o menos esfuerzo:",
        "en": "“{mejor}” returns {veces}× more than “{peor}” in {resultado} ({rinde_mejor} against {rinde_peor} per member), and yet receives the same or less effort:",
        "pt": "«{mejor}» rende {veces} vezes mais que «{peor}» em {resultado} ({rinde_mejor} contra {rinde_peor} por membro), e mesmo assim recebe igual ou menos esforço:",
    },
    "inf_cru_esfuerzo": {
        "es": "{hechos}, {peor} por miembro en el que menos rinde contra {mejor} en el que más",
        "en": "{hechos}, {peor} per member in the lowest-return group against {mejor} in the highest",
        "pt": "{hechos}, {peor} por membro no que menos rende contra {mejor} no que mais",
    },
    "inf_cru_bien_t": {
        "es": "El esfuerzo acompaña al retorno",
        "en": "Effort follows the return",
        "pt": "O esforço acompanha o retorno",
    },
    "inf_cru_bien": {
        "es": "El grupo que más produce no recibe menos esfuerzo que el que menos produce. Que esté bien puesto también es una conclusión, y no se fuerza un hallazgo donde no lo hay.",
        "en": "The highest-producing group does not receive less effort than the lowest. That it is well allocated is a conclusion too, and no finding is forced where there is none.",
        "pt": "O grupo que mais produz não recebe menos esforço que o que menos produz. Que esteja bem alocado também é uma conclusão, e não se força um achado onde não há.",
    },
    "inf_con_cruce": {
        "es": "El esfuerzo comercial no sigue al retorno: «{mejor}» produce {veces} veces más que «{peor}» por miembro y no recibe más contacto. Mover esfuerzo del grupo de abajo al de arriba no cuesta presupuesto nuevo — es la decisión más barata que este informe habilita.",
        "en": "Commercial effort does not follow the return: “{mejor}” produces {veces}× more than “{peor}” per member and does not receive more contact. Moving effort from the bottom group to the top one costs no new budget — it is the cheapest decision this report enables.",
        "pt": "O esforço comercial não segue o retorno: «{mejor}» produz {veces} vezes mais que «{peor}» por membro e não recebe mais contato. Mover esforço do grupo de baixo para o de cima não custa orçamento novo — é a decisão mais barata que este relatório habilita.",
    },
    "inf_titulo": {
        "es": 'Informe del modelo — {nombre}',
        "en": 'Model report — {nombre}',
        "pt": 'Relatório do modelo — {nombre}',
    },
    "inf_subtitulo": {
        "es": 'Auditoría del dataset, modelo, Power Query, medidas y tablero · generado el {fecha} por MV DAX Lab',
        "en": 'Dataset audit, model, Power Query, measures and report · generated on {fecha} by MV DAX Lab',
        "pt": 'Auditoria do dataset, modelo, Power Query, medidas e painel · gerado em {fecha} por MV DAX Lab',
    },
    "inf_pie": {
        "es": 'Cada número de este documento sale de lo que se leyó del archivo. Donde no hubo dato, se dice — no se completa.',
        "en": 'Every number in this document comes from what was read in the file. Where there was no data, it says so — it is not filled in.',
        "pt": 'Cada número deste documento vem do que foi lido do arquivo. Onde não houve dado, diz-se — não se preenche.',
    },
    "inf_s_resumen": {
        "es": 'Resumen y salud',
        "en": 'Summary and health',
        "pt": 'Resumo e saúde',
    },
    "inf_s_auditoria": {
        "es": 'Auditoría del dataset',
        "en": 'Dataset audit',
        "pt": 'Auditoria do dataset',
    },
    "inf_s_modelo": {
        "es": 'Modelo relacional',
        "en": 'Relational model',
        "pt": 'Modelo relacional',
    },
    "inf_s_pq": {
        "es": 'Power Query, tabla por tabla',
        "en": 'Power Query, table by table',
        "pt": 'Power Query, tabela por tabela',
    },
    "inf_s_medidas": {
        "es": 'Las medidas DAX',
        "en": 'The DAX measures',
        "pt": 'As medidas DAX',
    },
    "inf_s_tablero": {
        "es": 'El tablero, página por página',
        "en": 'The report, page by page',
        "pt": 'O painel, página por página',
    },
    "inf_s_reco": {
        "es": 'Qué conviene hacer ahora',
        "en": 'What to do now',
        "pt": 'O que convém fazer agora',
    },
    "inf_k_tablas": {
        "es": 'Tablas',
        "en": 'Tables',
        "pt": 'Tabelas',
    },
    "inf_k_medidas": {
        "es": 'Medidas',
        "en": 'Measures',
        "pt": 'Medidas',
    },
    "inf_k_relaciones": {
        "es": 'Relaciones',
        "en": 'Relationships',
        "pt": 'Relações',
    },
    "inf_k_numericas": {
        "es": 'Columnas numéricas',
        "en": 'Numeric columns',
        "pt": 'Colunas numéricas',
    },
    "inf_k_salud": {
        "es": 'Salud',
        "en": 'Health',
        "pt": 'Saúde',
    },
    "inf_sin_hallazgos_t": {
        "es": 'Sin hallazgos',
        "en": 'No findings',
        "pt": 'Sem achados',
    },
    "inf_sin_hallazgos": {
        "es": 'El analizador no encontró nada para corregir: ni DAX duplicado, ni relaciones ambiguas, ni columnas calculadas que deberían estar en Power Query, ni calendario faltante.',
        "en": 'The analyzer found nothing to fix: no duplicate DAX, no ambiguous relationships, no calculated columns that belong in Power Query, no missing calendar.',
        "pt": 'O analisador não encontrou nada para corrigir: nem DAX duplicado, nem relações ambíguas, nem colunas calculadas que deveriam estar no Power Query, nem calendário faltando.',
    },
    "inf_criticos_t": {
        "es": 'Hay que arreglar esto antes de publicar',
        "en": 'This must be fixed before publishing',
        "pt": 'Isto deve ser corrigido antes de publicar',
    },
    "inf_criticos": {
        "es": '{n} hallazgo(s) de severidad ALTA. Son los que rompen números o hacen que Power BI rechace el modelo — están detallados abajo con su arreglo.',
        "en": '{n} HIGH severity finding(s). These break numbers or make Power BI reject the model — they are detailed below with their fix.',
        "pt": '{n} achado(s) de severidade ALTA. São os que quebram números ou fazem o Power BI rejeitar o modelo — estão detalhados abaixo com a sua correção.',
    },
    "inf_medios_t": {
        "es": 'Para revisar',
        "en": 'To review',
        "pt": 'Para revisar',
    },
    "inf_medios": {
        "es": '{n} hallazgo(s) de severidad media: no rompen el archivo, pero cuestan memoria, tiempo de refresco o claridad.',
        "en": '{n} medium severity finding(s): they do not break the file, but they cost memory, refresh time or clarity.',
        "pt": '{n} achado(s) de severidade média: não quebram o arquivo, mas custam memória, tempo de atualização ou clareza.',
    },
    "inf_bajos_t": {
        "es": 'Detalles menores',
        "en": 'Minor details',
        "pt": 'Detalhes menores',
    },
    "inf_bajos": {
        "es": '{n} hallazgo(s) de severidad baja. Nada urgente: son prolijidad.',
        "en": '{n} low severity finding(s). Nothing urgent: these are tidiness.',
        "pt": '{n} achado(s) de severidade baixa. Nada urgente: é capricho.',
    },
    "inf_col_area": {
        "es": 'Área',
        "en": 'Area',
        "pt": 'Área',
    },
    "inf_col_hallazgos": {
        "es": 'Hallazgos',
        "en": 'Findings',
        "pt": 'Achados',
    },
    "inf_audit_lead": {
        "es": 'Qué hay adentro del archivo: cada tabla, qué papel cumple en el modelo, y cuánto trae.',
        "en": 'What is inside the file: each table, the role it plays in the model, and how much it carries.',
        "pt": 'O que há dentro do arquivo: cada tabela, o papel que cumpre no modelo, e quanto traz.',
    },
    "inf_col_tabla": {
        "es": 'Tabla',
        "en": 'Table',
        "pt": 'Tabela',
    },
    "inf_col_papel": {
        "es": 'Papel',
        "en": 'Role',
        "pt": 'Papel',
    },
    "inf_col_columnas": {
        "es": 'Columnas',
        "en": 'Columns',
        "pt": 'Colunas',
    },
    "inf_col_medidas": {
        "es": 'Medidas',
        "en": 'Measures',
        "pt": 'Medidas',
    },
    "inf_col_filas": {
        "es": 'Filas',
        "en": 'Rows',
        "pt": 'Linhas',
    },
    "inf_hecho": {
        "es": 'Hecho',
        "en": 'Fact',
        "pt": 'Fato',
    },
    "inf_dimension": {
        "es": 'Dimensión',
        "en": 'Dimension',
        "pt": 'Dimensão',
    },
    "inf_calendario": {
        "es": 'Calendario',
        "en": 'Calendar',
        "pt": 'Calendário',
    },
    "inf_tabla_medidas": {
        "es": 'Tabla de medidas',
        "en": 'Measures table',
        "pt": 'Tabela de medidas',
    },
    "inf_suelta": {
        "es": 'Suelta (sin relación)',
        "en": 'Unrelated',
        "pt": 'Solta (sem relação)',
    },
    "inf_trampas": {
        "es": 'Lo que el dataset delata',
        "en": 'What the dataset gives away',
        "pt": 'O que o dataset revela',
    },
    "inf_limpio_t": {
        "es": 'Nada que corregir',
        "en": 'Nothing to fix',
        "pt": 'Nada a corrigir',
    },
    "inf_limpio": {
        "es": 'Ninguna de las reglas del analizador se disparó sobre este modelo.',
        "en": 'None of the analyzer rules fired on this model.',
        "pt": 'Nenhuma das regras do analisador disparou sobre este modelo.',
    },
    "inf_perfilado": {
        "es": 'Perfilado de los datos',
        "en": 'Data profiling',
        "pt": 'Perfilamento dos dados',
    },
    "inf_sin_datos_t": {
        "es": 'No hay datos para perfilar',
        "en": 'No data to profile',
        "pt": 'Não há dados para perfilar',
    },
    "inf_sin_datos": {
        "es": 'Este archivo trae el modelo pero no las filas (un .pbit no lleva datos, y de un .pbix solo se puede leer la estructura). Cargá el Excel, el CSV o el SQL de origen y el perfilado sale con las distribuciones reales.',
        "en": 'This file carries the model but not the rows (a .pbit carries no data, and from a .pbix only the structure can be read). Load the source Excel, CSV or SQL and profiling comes out with real distributions.',
        "pt": 'Este arquivo traz o modelo mas não as linhas (um .pbit não leva dados, e de um .pbix só se pode ler a estrutura). Carregue o Excel, o CSV ou o SQL de origem e o perfilamento sai com as distribuições reais.',
    },
    "inf_filas_leidas": {
        "es": 'filas leídas',
        "en": 'rows read',
        "pt": 'linhas lidas',
    },
    "inf_col_columna": {
        "es": 'Columna',
        "en": 'Column',
        "pt": 'Coluna',
    },
    "inf_col_tipo": {
        "es": 'Tipo',
        "en": 'Type',
        "pt": 'Tipo',
    },
    "inf_col_distintos": {
        "es": 'Distintos',
        "en": 'Distinct',
        "pt": 'Distintos',
    },
    "inf_col_vacios": {
        "es": 'Vacíos',
        "en": 'Empty',
        "pt": 'Vazios',
    },
    "inf_col_muestra": {
        "es": 'Muestra',
        "en": 'Sample',
        "pt": 'Amostra',
    },
    "inf_modelo_lead": {
        "es": 'Cómo se conectan las tablas. Una relación mal puesta no da error: da un número equivocado con toda confianza.',
        "en": 'How the tables connect. A wrong relationship gives no error: it gives a wrong number with full confidence.',
        "pt": 'Como as tabelas se conectam. Uma relação mal posta não dá erro: dá um número errado com toda a confiança.',
    },
    "inf_diagrama": {
        "es": "El diagrama del modelo, en formato Graphviz (DOT). Pegalo en cualquier visor de Graphviz —o en la pestaña Modelo del programa— para verlo dibujado.",
        "en": "The model diagram, in Graphviz (DOT) format. Paste it into any Graphviz viewer —or into the program's Model tab— to see it drawn.",
        "pt": "O diagrama do modelo, em formato Graphviz (DOT). Cole-o em qualquer visualizador de Graphviz —ou na aba Modelo do programa— para vê-lo desenhado.",
    },
    "inf_una_tabla_t": {
        "es": "Una sola tabla",
        "en": "A single table",
        "pt": "Uma única tabela",
    },
    "inf_una_tabla": {
        "es": "El modelo tiene una sola tabla, así que no hay relaciones que revisar. No es un defecto: es lo que hay.",
        "en": "The model has a single table, so there are no relationships to review. That is not a defect: it is what there is.",
        "pt": "O modelo tem uma única tabela, então não há relações a rever. Não é um defeito: é o que há.",
    },
    "inf_col_muchos": {
        "es": 'Lado muchos',
        "en": 'Many side',
        "pt": 'Lado muitos',
    },
    "inf_col_uno": {
        "es": 'Lado uno',
        "en": 'One side',
        "pt": 'Lado um',
    },
    "inf_col_card": {
        "es": 'Cardinalidad',
        "en": 'Cardinality',
        "pt": 'Cardinalidade',
    },
    "inf_col_estado": {
        "es": 'Estado',
        "en": 'State',
        "pt": 'Estado',
    },
    "inf_col_filtro": {
        "es": 'Filtro',
        "en": 'Filter',
        "pt": 'Filtro',
    },
    "inf_activa": {
        "es": 'Activa',
        "en": 'Active',
        "pt": 'Ativa',
    },
    "inf_inactiva": {
        "es": 'Inactiva',
        "en": 'Inactive',
        "pt": 'Inativa',
    },
    "inf_sin_rel_t": {
        "es": 'El modelo no tiene ni una relación',
        "en": 'The model has no relationships at all',
        "pt": 'O modelo não tem nenhuma relação',
    },
    "inf_sin_rel": {
        "es": 'Sin relaciones, cada tabla vive sola: los filtros no viajan y cualquier visual que cruce dos tablas va a dar el total repetido. Es lo primero que hay que resolver.',
        "en": 'Without relationships each table lives alone: filters do not travel and any visual crossing two tables will repeat the total. This is the first thing to solve.',
        "pt": 'Sem relações cada tabela vive sozinha: os filtros não viajam e qualquer visual que cruze duas tabelas vai dar o total repetido. É a primeira coisa a resolver.',
    },
    "inf_pq_lead": {
        "es": 'De dónde sale cada tabla, en su propio idioma (M). Es lo que se ejecuta en cada Actualizar.',
        "en": 'Where each table comes from, in its own language (M). This is what runs on every Refresh.',
        "pt": 'De onde sai cada tabela, na sua própria linguagem (M). É o que se executa em cada Atualização.',
    },
    "inf_sin_pq_t": {
        "es": 'Sin consultas de origen',
        "en": 'No source queries',
        "pt": 'Sem consultas de origem',
    },
    "inf_sin_pq": {
        "es": 'Ninguna tabla trae su Power Query: o son tablas calculadas en DAX, o el archivo no incluyó las consultas.',
        "en": 'No table brings its Power Query: either they are DAX calculated tables, or the file did not include the queries.',
        "pt": 'Nenhuma tabela traz o seu Power Query: ou são tabelas calculadas em DAX, ou o arquivo não incluiu as consultas.',
    },
    "inf_medidas_lead": {
        "es": 'Las {n} medidas del modelo, agrupadas por carpeta, con su formato y su fórmula.',
        "en": 'The {n} model measures, grouped by folder, with their format and formula.',
        "pt": 'As {n} medidas do modelo, agrupadas por pasta, com o seu formato e a sua fórmula.',
    },
    "inf_sin_carpeta": {
        "es": 'Sin carpeta',
        "en": 'No folder',
        "pt": 'Sem pasta',
    },
    "inf_sin_medidas_t": {
        "es": 'El modelo no tiene ni una medida',
        "en": 'The model has no measures',
        "pt": 'O modelo não tem nenhuma medida',
    },
    "inf_sin_medidas": {
        "es": 'Sin medidas, cada visual suma columnas sueltas: no hay una definición única de «ventas» y dos personas pueden sacar dos números distintos de la misma tabla.',
        "en": 'Without measures each visual sums loose columns: there is no single definition of “sales” and two people can get two different numbers from the same table.',
        "pt": 'Sem medidas cada visual soma colunas soltas: não há uma definição única de «vendas» e duas pessoas podem tirar dois números diferentes da mesma tabela.',
    },
    "inf_col_medida": {
        "es": 'Medida',
        "en": 'Measure',
        "pt": 'Medida',
    },
    "inf_col_formato": {
        "es": 'Formato',
        "en": 'Format',
        "pt": 'Formato',
    },
    "inf_sin_reporte_t": {
        "es": 'El archivo no trae reporte',
        "en": 'The file carries no report',
        "pt": 'O arquivo não traz relatório',
    },
    "inf_sin_reporte": {
        "es": 'Se cargó el modelo pero no las páginas del tablero. El informe cubre el modelo; la parte visual queda afuera.',
        "en": 'The model was loaded but not the report pages. This report covers the model; the visual part is left out.',
        "pt": 'Carregou-se o modelo mas não as páginas do painel. O relatório cobre o modelo; a parte visual fica de fora.',
    },
    "inf_reco_lead": {
        "es": 'En orden de impacto: primero lo que rompe números, después lo que cuesta memoria o claridad. Lo marcado «solo» lo arregla el programa sin que toques nada.',
        "en": 'In order of impact: first what breaks numbers, then what costs memory or clarity. What is marked “auto” the program fixes without you touching anything.',
        "pt": 'Por ordem de impacto: primeiro o que quebra números, depois o que custa memória ou clareza. O marcado «sozinho» o programa corrige sem que toque em nada.',
    },
    "inf_col_regla": {
        "es": 'Regla',
        "en": 'Rule',
        "pt": 'Regra',
    },
    "inf_col_que": {
        "es": 'Qué pasa y cómo se arregla',
        "en": 'What happens and how to fix it',
        "pt": 'O que acontece e como se corrige',
    },
    "inf_col_solo": {
        "es": '¿Solo?',
        "en": 'Auto?',
        "pt": 'Sozinho?',
    },
    "inf_auto": {
        "es": 'Sí',
        "en": 'Yes',
        "pt": 'Sim',
    },
    "inf_kpis_t": {
        "es": 'Medidas que este modelo pide y todavía no tiene',
        "en": 'Measures this model asks for and does not have yet',
        "pt": 'Medidas que este modelo pede e ainda não tem',
    },
    "inf_kpis": {
        "es": '{n} sugerencias, entre ellas: {lista}. Cada una está validada contra el catálogo — no referencia nada que no exista.',
        "en": '{n} suggestions, among them: {lista}. Each one is validated against the catalog — it references nothing that does not exist.',
        "pt": '{n} sugestões, entre elas: {lista}. Cada uma está validada contra o catálogo — não referencia nada que não exista.',
    },
    "inf_nada_que_hacer_t": {
        "es": 'No hay nada pendiente',
        "en": 'Nothing pending',
        "pt": 'Não há nada pendente',
    },
    "inf_nada_que_hacer": {
        "es": 'Ni hallazgos del analizador ni medidas obvias faltando. El modelo está listo.',
        "en": 'Neither analyzer findings nor obvious missing measures. The model is ready.',
        "pt": 'Nem achados do analisador nem medidas óbvias faltando. O modelo está pronto.',
    },
    "an_informe_titulo": {
        "es": 'Informe completo del modelo, para llevarse',
        "en": 'Full model report, to take away',
        "pt": 'Relatório completo do modelo, para levar',
    },
    "an_informe_nota": {
        "es": 'Todo lo de arriba escrito como documento: auditoría del dataset, modelo relacional, Power Query tabla por tabla, las medidas por carpeta, el tablero página por página y qué conviene hacer ahora — con lo importante resaltado en color según su gravedad. Es un HTML solo: abre en cualquier navegador, se manda por mail y se imprime a PDF sin instalar nada.',
        "en": 'Everything above written as a document: dataset audit, relational model, Power Query table by table, measures by folder, the report page by page and what to do now — with the important parts highlighted in color by severity. It is a single HTML file: it opens in any browser, can be emailed and printed to PDF without installing anything.',
        "pt": 'Tudo o que está acima escrito como documento: auditoria do dataset, modelo relacional, Power Query tabela por tabela, as medidas por pasta, o painel página por página e o que convém fazer agora — com o importante destacado em cor conforme a gravidade. É um HTML só: abre em qualquer navegador, envia-se por e-mail e imprime-se em PDF sem instalar nada.',
    },
    "an_informe_btn": {
        "es": 'Generar el informe',
        "en": 'Generate the report',
        "pt": 'Gerar o relatório',
    },
    "an_informe_generando": {
        "es": 'Escribiendo el informe…',
        "en": 'Writing the report…',
        "pt": 'Escrevendo o relatório…',
    },
    "an_preguntar_titulo": {
        "es": 'Preguntarle al informe',
        "en": 'Ask the report',
        "pt": 'Perguntar ao relatório',
    },
    "an_preguntar_nota": {
        "es": 'Escribí la pregunta en tu idioma. La respuesta se arma con lo que el programa MIDIÓ sobre este archivo —hallazgos, tablas, medidas, perfilado— y la IA solo la redacta. Los números no los pone la IA.',
        "en": 'Write the question in your own language. The answer is built from what the program MEASURED on this file —findings, tables, measures, profiling— and the AI only writes it up. The numbers do not come from the AI.',
        "pt": 'Escreva a pergunta no seu idioma. A resposta é montada com o que o programa MEDIU sobre este arquivo —achados, tabelas, medidas, perfilamento— e a IA apenas a redige. Os números não vêm da IA.',
    },
    "an_preguntar_ph": {
        "es": 'Por ejemplo: ¿qué está mal en el modelo? ¿de dónde sale la medida de ventas? ¿qué columnas tienen vacíos?',
        "en": 'For example: what is wrong with the model? where does the sales measure come from? which columns have blanks?',
        "pt": 'Por exemplo: o que está errado no modelo? de onde sai a medida de vendas? que colunas têm vazios?',
    },
    "an_preguntar_btn": {
        "es": "Preguntar",
        "en": "Ask",
        "pt": "Perguntar",
    },
    "an_preguntar_evidencia": {
        "es": 'Con qué se respondió',
        "en": 'What the answer is based on',
        "pt": 'Com o que se respondeu',
    },
    "an_preguntar_sin_ia": {
        "es": 'Respondido sin IA: no hay clave configurada para el proveedor elegido. Los hechos son los mismos; con clave, además se redactan.',
        "en": 'Answered without AI: no key is configured for the chosen provider. The facts are the same; with a key they are also written up.',
        "pt": 'Respondido sem IA: não há chave configurada para o provedor escolhido. Os fatos são os mesmos; com chave, além disso são redigidos.',
    },
    "inf_y_mas": {
        "es": "y {n} más",
        "en": "and {n} more",
        "pt": "e mais {n}",
    },
    "inf_parcial_t": {
        "es": "De este archivo no se pudo leer el modelo",
        "en": "The model could not be read from this file",
        "pt": "Deste arquivo não foi possível ler o modelo",
    },
    "inf_parcial": {
        "es": "Es un .pbix: el modelo viaja en un binario propietario que solo Power BI Desktop sabe abrir, y de acá solo se pudo leer el reporte. Por eso este informe no lleva nota de salud: puntuar un modelo que no se pudo analizar daría un número alto y falso. Para el informe completo, abrilo en Desktop y guardalo como .pbit, o cargá el Excel/CSV/SQL de origen.",
        "en": "It is a .pbix: the model travels in a proprietary binary that only Power BI Desktop can open, and only the report could be read here. That is why this report carries no health score: scoring a model that could not be analyzed would give a high, false number. For the full report, open it in Desktop and save it as .pbit, or load the source Excel/CSV/SQL.",
        "pt": "É um .pbix: o modelo viaja num binário proprietário que só o Power BI Desktop sabe abrir, e daqui só foi possível ler o relatório. Por isso este relatório não leva nota de saúde: pontuar um modelo que não se pôde analisar daria um número alto e falso. Para o relatório completo, abra-o no Desktop e salve como .pbit, ou carregue o Excel/CSV/SQL de origem.",
    },
    "inf_ev_cortada": {
        "es": "(hay {n} hechos más que también coinciden con la pregunta y no entraron en esta lista — preguntá algo más específico para verlos)",
        "en": "(there are {n} more facts that also match the question and did not fit in this list — ask something more specific to see them)",
        "pt": "(há mais {n} fatos que também coincidem com a pergunta e não entraram nesta lista — pergunte algo mais específico para vê-los)",
    },
    "inf_ev_resumen": {
        "es": 'El modelo tiene {tablas} tablas, {medidas} medidas y {relaciones} relaciones. Salud del analizador: {salud}/100.',
        "en": 'The model has {tablas} tables, {medidas} measures and {relaciones} relationships. Analyzer health: {salud}/100.',
        "pt": 'O modelo tem {tablas} tabelas, {medidas} medidas e {relaciones} relações. Saúde do analisador: {salud}/100.',
    },
    "inf_ev_brecha": {
        "es": "PORQUÉ (calculado sobre las filas del archivo, {previo} vs {actual}, {meses} meses comparables): {propia} creció {propio:+.1f} % y el mercado {mercado:+.1f} %, así que el share se movió {pp:+.2f} puntos porcentuales.",
        "en": "WHY (computed on the file's rows, {previo} vs {actual}, {meses} comparable months): {propia} grew {propio:+.1f} % and the market {mercado:+.1f} %, so share moved {pp:+.2f} percentage points.",
        "pt": "PORQUÊ (calculado sobre as linhas do arquivo, {previo} vs {actual}, {meses} meses comparáveis): {propia} cresceu {propio:+.1f} % e o mercado {mercado:+.1f} %, então o share moveu-se {pp:+.2f} pontos percentuais.",
    },
    "inf_ev_efectos": {
        "es": "Descompuesto por {dim}: DESEMPEÑO {desempeno:+.2f} pp (vender mejor o peor que el mercado en los mismos segmentos) y MEZCLA {mezcla:+.2f} pp (estar pesado en segmentos que crecen poco). Las dos partes suman exactamente la brecha.",
        "en": "Decomposed by {dim}: PERFORMANCE {desempeno:+.2f} pp (selling better or worse than the market in the same segments) and MIX {mezcla:+.2f} pp (being heavy in slow-growing segments). The two parts add up exactly to the gap.",
        "pt": "Decomposto por {dim}: DESEMPENHO {desempeno:+.2f} pp (vender melhor ou pior que o mercado nos mesmos segmentos) e MIX {mezcla:+.2f} pp (estar pesado em segmentos que crescem pouco). As duas partes somam exatamente a diferença.",
    },
    "inf_ev_segmento": {
        "es": "{dim} = «{miembro}»: aporta {pp:+.2f} pp al share; pesa {peso:.1f} % de lo propio; crece {propio:+.1f} % contra un mercado que crece {mercado:+.1f} %.",
        "en": "{dim} = “{miembro}”: contributes {pp:+.2f} pp to share; is {peso:.1f} % of own; grows {propio:+.1f} % against a market growing {mercado:+.1f} %.",
        "pt": "{dim} = «{miembro}»: aporta {pp:+.2f} pp ao share; pesa {peso:.1f} % do próprio; cresce {propio:+.1f} % contra um mercado que cresce {mercado:+.1f} %.",
    },
    "inf_ev_precio": {
        "es": "Precio medio {var:+.1f} % con unidades {unidades:+.1f} %: el volumen aportó {vol:+,.0f} y el precio {pre:+,.0f}.",
        "en": "Average price {var:+.1f} % with units {unidades:+.1f} %: volume contributed {vol:+,.0f} and price {pre:+,.0f}.",
        "pt": "Preço médio {var:+.1f} % com unidades {unidades:+.1f} %: o volume aportou {vol:+,.0f} e o preço {pre:+,.0f}.",
    },
    "inf_ev_medida": {
        "es": 'Medida [{nombre}] · formato {formato} · DAX: {dax}',
        "en": 'Measure [{nombre}] · format {formato} · DAX: {dax}',
        "pt": 'Medida [{nombre}] · formato {formato} · DAX: {dax}',
    },
    "inf_ev_tabla": {
        "es": 'Tabla «{nombre}» ({papel}) · columnas: {columnas}',
        "en": 'Table “{nombre}” ({papel}) · columns: {columnas}',
        "pt": 'Tabela «{nombre}» ({papel}) · colunas: {columnas}',
    },
    "inf_ev_columna": {
        "es": 'Columna {tabla}[{columna}] de tipo {tipo}',
        "en": 'Column {tabla}[{columna}] of type {tipo}',
        "pt": 'Coluna {tabla}[{columna}] do tipo {tipo}',
    },
    "inf_ev_perfil": {
        "es": '{tabla}[{columna}]: {filas} filas leídas, {distintos} valores distintos, {vacios} vacías',
        "en": '{tabla}[{columna}]: {filas} rows read, {distintos} distinct values, {vacios} empty',
        "pt": '{tabla}[{columna}]: {filas} linhas lidas, {distintos} valores distintos, {vacios} vazias',
    },
    "inf_ia_sistema": {
        "es": 'Sos un analista de Power BI. Respondés SOLO con los hechos que te dan: no inventás números, no completás lo que falta y no supones nada del negocio. Si la evidencia no alcanza para responder, lo decís en una línea y explicás qué haría falta cargar. Español rioplatense, directo, sin relleno.',
        "en": 'You are a Power BI analyst. You answer ONLY with the facts you are given: you do not invent numbers, you do not fill in what is missing and you assume nothing about the business. If the evidence is not enough to answer, you say so in one line and explain what would need to be loaded. Direct, no filler.',
        "pt": 'És um analista de Power BI. Respondes SÓ com os factos que te dão: não inventas números, não completas o que falta e não supões nada do negócio. Se a evidência não chega para responder, dize-lo numa linha e explicas o que faria falta carregar. Direto, sem enchimento.',
    },
    "inf_ia_prompt": {
        "es": 'Pregunta sobre este modelo de Power BI:\n\n{pregunta}\n\nEstos son los hechos que se midieron sobre el archivo y que tienen que ver con la pregunta:\n{contexto}\n\nRespondé usando únicamente esa evidencia. Si no alcanza, decilo y explicá qué haría falta cargar.',
        "en": 'Question about this Power BI model:\n\n{pregunta}\n\nThese are the facts measured on the file that relate to the question:\n{contexto}\n\nAnswer using only that evidence. If it is not enough, say so and explain what would need to be loaded.',
        "pt": 'Pergunta sobre este modelo de Power BI:\n\n{pregunta}\n\nEstes são os fatos medidos sobre o arquivo que têm a ver com a pergunta:\n{contexto}\n\nResponda usando unicamente essa evidência. Se não bastar, diga-o e explique o que faria falta carregar.',
    },
    "inf_ia_falla": {
        "es": 'No se pudo consultar a la IA ({motivo}). Va la respuesta del motor local, con los mismos hechos:',
        "en": "The AI could not be queried ({motivo}). Here is the local engine's answer, with the same facts:",
        "pt": 'Não foi possível consultar a IA ({motivo}). Vai a resposta do motor local, com os mesmos fatos:',
    },
    "inf_local_intro": {
        "es": 'Esto es lo que el programa midió sobre tu archivo y tiene que ver con la pregunta:',
        "en": 'This is what the program measured on your file that relates to the question:',
        "pt": 'Isto é o que o programa mediu sobre o seu arquivo e tem a ver com a pergunta:',
    },
    "inf_sin_respuesta": {
        "es": 'No encontré nada en este archivo que responda esa pregunta. Probá nombrando una tabla, una medida o una columna del modelo — o cargá el Excel/CSV de origen, que agrega el perfilado de los datos.',
        "en": 'I found nothing in this file that answers that question. Try naming a table, a measure or a column of the model — or load the source Excel/CSV, which adds data profiling.',
        "pt": 'Não encontrei nada neste arquivo que responda essa pergunta. Tente nomear uma tabela, uma medida ou uma coluna do modelo — ou carregue o Excel/CSV de origem, que acrescenta o perfilamento dos dados.',
    },
    "an_op_precio_t": {
        "es": 'El precio medio bajó',
        "en": 'Average price fell',
        "pt": 'O preço médio caiu',
    },
    "an_op_precio": {
        "es": 'Las unidades crecieron {unidades:+.1f} % pero el dinero no siguió: el precio medio se movió {var:+.1f} %. Eso te costó {efecto:+,.0f} de facturación. Si no fue una decisión deliberada de precio, revisá descuentos, mix de presentaciones y notas de crédito.',
        "en": 'Units grew {unidades:+.1f} % but money did not follow: average price moved {var:+.1f} %. That cost you {efecto:+,.0f} in revenue. If it was not a deliberate pricing decision, review discounts, pack mix and credit notes.',
        "pt": 'As unidades cresceram {unidades:+.1f} % mas o dinheiro não seguiu: o preço médio moveu-se {var:+.1f} %. Isso custou {efecto:+,.0f} de faturamento. Se não foi uma decisão deliberada de preço, revise descontos, mix de apresentações e notas de crédito.',
    },
    "an_op_desempeno": {
        "es": 'En «{miembro}» crecés {propio:+.1f} % contra un mercado que crece {mercado:+.1f} %: perdés DONDE COMPETÍS, y eso vale {pp:+.2f} pp de share. Es el caso que se arregla vendiendo mejor ahí — cobertura, frecuencia de visita, disponibilidad.',
        "en": 'In “{miembro}” you grow {propio:+.1f} % against a market growing {mercado:+.1f} %: you are losing WHERE YOU COMPETE, and that is worth {pp:+.2f} pp of share. This is the case fixed by selling better there — coverage, call frequency, availability.',
        "pt": 'Em «{miembro}» cresce {propio:+.1f} % contra um mercado que cresce {mercado:+.1f} %: perde ONDE COMPETE, e isso vale {pp:+.2f} pp de share. É o caso que se corrige vendendo melhor ali — cobertura, frequência de visita, disponibilidade.',
    },
    "an_op_mezcla": {
        "es": '«{miembro}» crece {mercado:+.1f} % en el mercado y ahí pesás {peso:.1f} % de lo tuyo: estás sub-representado en un segmento que tracciona, y eso te resta {pp:+.2f} pp de share. Esto NO se arregla apretando a la fuerza de ventas — es una decisión de portafolio.',
        "en": '“{miembro}” grows {mercado:+.1f} % in the market and it is {peso:.1f} % of your own: you are under-represented in a segment that pulls, and that costs you {pp:+.2f} pp of share. This is NOT fixed by pushing the sales force — it is a portfolio decision.',
        "pt": '«{miembro}» cresce {mercado:+.1f} % no mercado e ali pesa {peso:.1f} % do seu: está sub-representado num segmento que puxa, e isso tira-lhe {pp:+.2f} pp de share. Isto NÃO se corrige apertando a força de vendas — é uma decisão de portfólio.',
    },
    "an_op_fuerte": {
        "es": '«{miembro}» es lo que te está sosteniendo: crecés {propio:+.1f} % contra {mercado:+.1f} % del mercado y aporta {pp:+.2f} pp. Vale protegerlo antes que perseguir lo que cae.',
        "en": "“{miembro}” is what is holding you up: you grow {propio:+.1f} % against the market's {mercado:+.1f} % and it contributes {pp:+.2f} pp. Worth protecting before chasing what is falling.",
        "pt": '«{miembro}» é o que o está sustentando: cresce {propio:+.1f} % contra {mercado:+.1f} % do mercado e aporta {pp:+.2f} pp. Vale protegê-lo antes de perseguir o que cai.',
    },
    "inf_s_porque": {
        "es": 'Por qué se movió el share',
        "en": 'Why the share moved',
        "pt": 'Por que o share se moveu',
    },
    "inf_pq_lead2": {
        "es": 'La pregunta que hace un analista senior cuando ve el informe: no cuánto se movió, sino por qué. Todo lo que sigue sale de las filas del archivo, y las partes suman exactamente el total — se puede verificar.',
        "en": "The question a senior analyst asks when they see the report: not how much it moved, but why. Everything below comes from the file's rows, and the parts add up exactly to the total — it can be verified.",
        "pt": 'A pergunta que um analista sénior faz ao ver o relatório: não quanto se moveu, mas porquê. Tudo o que segue sai das linhas do arquivo, e as partes somam exatamente o total — pode ser verificado.',
    },
    "inf_pq_titular": {
        "es": '{propia} creció {propio:+.1f} % y el mercado {mercado:+.1f} %: {pp:+.2f} pp de share',
        "en": '{propia} grew {propio:+.1f} % and the market {mercado:+.1f} %: {pp:+.2f} pp of share',
        "pt": '{propia} cresceu {propio:+.1f} % e o mercado {mercado:+.1f} %: {pp:+.2f} pp de share',
    },
    "inf_pq_periodo": {
        "es": 'Comparación {previo} contra {actual}, recortada a los {meses} meses que los dos años tienen. Sin ese recorte, comparar un año a medio andar contra uno completo muestra una caída que no existe.',
        "en": 'Comparison {previo} against {actual}, trimmed to the {meses} months both years have. Without that trim, comparing a half-finished year against a complete one shows a drop that does not exist.',
        "pt": 'Comparação {previo} contra {actual}, recortada aos {meses} meses que os dois anos têm. Sem esse recorte, comparar um ano a meio contra um completo mostra uma queda que não existe.',
    },
    "inf_pq_desempeno": {
        "es": 'Desempeño',
        "en": 'Performance',
        "pt": 'Desempenho',
    },
    "inf_pq_mezcla": {
        "es": 'Mezcla',
        "en": 'Mix',
        "pt": 'Mix',
    },
    "inf_pq_explica_desempeno": {
        "es": 'Cuánto de la brecha es vender peor (o mejor) que el mercado EN LOS MISMOS segmentos. Se arregla con esfuerzo comercial.',
        "en": 'How much of the gap is selling worse (or better) than the market IN THE SAME segments. Fixed with commercial effort.',
        "pt": 'Quanto da diferença é vender pior (ou melhor) que o mercado NOS MESMOS segmentos. Corrige-se com esforço comercial.',
    },
    "inf_pq_explica_mezcla": {
        "es": 'Cuánto es estar parado en el lugar equivocado: pesado en segmentos que crecen poco, liviano en los que crecen. Se arregla con portafolio, no con esfuerzo.',
        "en": 'How much is standing in the wrong place: heavy in slow-growing segments, light in growing ones. Fixed with portfolio, not effort.',
        "pt": 'Quanto é estar no lugar errado: pesado em segmentos que crescem pouco, leve nos que crescem. Corrige-se com portfólio, não com esforço.',
    },
    "inf_pq_veredicto_mezcla": {
        "es": 'El problema NO es cómo vendés: es dónde estás',
        "en": 'The problem is NOT how you sell: it is where you are',
        "pt": 'O problema NÃO é como vende: é onde está',
    },
    "inf_pq_veredicto_mezcla_txt": {
        "es": 'De los {brecha:.2f} puntos que quedaste por debajo del mercado, {mezcla:.2f} son de mezcla y solo {desempeno:.2f} de desempeño. Donde competís cara a cara no vendés peor — el problema es el peso del portafolio en los segmentos que traccionan. Apretar a la fuerza de ventas no mueve este número.',
        "en": 'Of the {brecha:.2f} points you fell below the market, {mezcla:.2f} are mix and only {desempeno:.2f} performance. Where you compete head to head you do not sell worse — the problem is portfolio weight in the segments that pull. Pushing the sales force does not move this number.',
        "pt": 'Dos {brecha:.2f} pontos que ficou abaixo do mercado, {mezcla:.2f} são de mix e apenas {desempeno:.2f} de desempenho. Onde compete cara a cara não vende pior — o problema é o peso do portfólio nos segmentos que puxam. Apertar a força de vendas não move este número.',
    },
    "inf_pq_veredicto_desempeno": {
        "es": 'El problema es competitivo, no de portafolio',
        "en": 'The problem is competitive, not portfolio',
        "pt": 'O problema é competitivo, não de portfólio',
    },
    "inf_pq_veredicto_desempeno_txt": {
        "es": 'De los {brecha:.2f} puntos de brecha, {desempeno:.2f} son de desempeño: estás perdiendo en los mismos segmentos donde competís. Eso se recupera con acción comercial — cobertura, frecuencia, disponibilidad — y es más rápido de mover que una decisión de portafolio.',
        "en": 'Of the {brecha:.2f} points of gap, {desempeno:.2f} are performance: you are losing in the same segments where you compete. That is recovered with commercial action — coverage, frequency, availability — and is faster to move than a portfolio decision.',
        "pt": 'Dos {brecha:.2f} pontos de diferença, {desempeno:.2f} são de desempenho: está perdendo nos mesmos segmentos onde compete. Isso recupera-se com ação comercial — cobertura, frequência, disponibilidade — e é mais rápido de mover que uma decisão de portfólio.',
    },
    "inf_pq_grafico": {
        "es": 'Cuánto aporta cada {dim} a los {pp:+.2f} pp — ordenado por peso',
        "en": 'How much each {dim} contributes to the {pp:+.2f} pp — sorted by weight',
        "pt": 'Quanto cada {dim} aporta aos {pp:+.2f} pp — ordenado por peso',
    },
    "inf_pq_no_compite": {
        "es": 'En este corte cada miembro pertenece a una sola corporación, así que no hay competencia cara a cara que medir: el desempeño da cero por construcción y todo lo que se ve es mezcla. Es correcto, pero explica menos que un corte donde estén las dos partes.',
        "en": 'In this breakdown each member belongs to a single corporation, so there is no head-to-head competition to measure: performance is zero by construction and everything seen is mix. It is correct, but explains less than a breakdown where both sides are present.',
        "pt": 'Neste corte cada membro pertence a uma única corporação, então não há concorrência cara a cara para medir: o desempenho dá zero por construção e tudo o que se vê é mix. É correto, mas explica menos que um corte onde estejam as duas partes.',
    },
    "inf_pq_precio_t": {
        "es": 'Volumen contra precio',
        "en": 'Volume against price',
        "pt": 'Volume contra preço',
    },
    "inf_pq_precio": {
        "es": 'Vendiste {unidades:+.1f} % más unidades pero el dinero creció {valor:+.1f} %: el precio medio pasó de {p0:,.2f} a {p1:,.2f} ({var:+.1f} %). El volumen aportó {vol:+,.0f} y el precio restó {pre:+,.0f}. Las dos partes suman exactamente el cambio real ({delta:+,.0f}).',
        "en": 'You sold {unidades:+.1f} % more units but money grew {valor:+.1f} %: average price went from {p0:,.2f} to {p1:,.2f} ({var:+.1f} %). Volume contributed {vol:+,.0f} and price subtracted {pre:+,.0f}. The two parts add up exactly to the real change ({delta:+,.0f}).',
        "pt": 'Vendeu {unidades:+.1f} % mais unidades mas o dinheiro cresceu {valor:+.1f} %: o preço médio passou de {p0:,.2f} para {p1:,.2f} ({var:+.1f} %). O volume aportou {vol:+,.0f} e o preço subtraiu {pre:+,.0f}. As duas partes somam exatamente a mudança real ({delta:+,.0f}).',
    },
    "inf_pq_oportunidades": {
        "es": 'Oportunidades de mejora',
        "en": 'Improvement opportunities',
        "pt": 'Oportunidades de melhoria',
    },
    "inf_pq_sin_datos_t": {
        "es": 'No se puede explicar por qué se movió',
        "en": 'Cannot explain why it moved',
        "pt": 'Não é possível explicar por que se moveu',
    },
    "inf_pq_sin_datos": {
        "es": 'Para esto hacen falta tres cosas: las filas adentro del archivo, dos años comparables, y una columna que separe lo propio de la competencia. Cargá el Excel/CSV de origen y exportá con los datos incluidos — sin eso, cualquier explicación sería inventada.',
        "en": 'Three things are needed: the rows inside the file, two comparable years, and a column separating your own from the competition. Load the source Excel/CSV and export with the data included — without that, any explanation would be made up.',
        "pt": 'Para isto são precisas três coisas: as linhas dentro do arquivo, dois anos comparáveis, e uma coluna que separe o próprio da concorrência. Carregue o Excel/CSV de origem e exporte com os dados incluídos — sem isso, qualquer explicação seria inventada.',
    },
    "inf_pq_sin_propia_t": {
        "es": 'No se puede saber cuál corporación es la tuya',
        "en": 'Cannot tell which corporation is yours',
        "pt": 'Não é possível saber qual corporação é a sua',
    },
    "inf_pq_sin_propia": {
        "es": 'La columna «{columna}» separa {n} corporaciones ({lista}), pero ninguna medida del modelo nombra a una en particular. Creá una medida que la nombre —por ejemplo «Ventas <tu empresa> USD»— y este análisis sale solo. No se adivina por tamaño: la más grande puede ser la competencia.',
        "en": 'Column “{columna}” separates {n} corporations ({lista}), but no model measure names one in particular. Create a measure naming it —for example “Sales <your company> USD”— and this analysis comes out on its own. It is not guessed by size: the largest may be the competition.',
        "pt": 'A coluna «{columna}» separa {n} corporações ({lista}), mas nenhuma medida do modelo nomeia uma em particular. Crie uma medida que a nomeie —por exemplo «Vendas <a sua empresa> USD»— e esta análise sai sozinha. Não se adivinha por tamanho: a maior pode ser a concorrência.',
    },
    "inf_pq_col_miembro": {
        "es": 'Segmento',
        "en": 'Segment',
        "pt": 'Segmento',
    },
    "inf_pq_col_aporte": {
        "es": 'Aporte (pp)',
        "en": 'Contribution (pp)',
        "pt": 'Aporte (pp)',
    },
    "inf_pq_col_peso": {
        "es": 'Peso propio',
        "en": 'Own weight',
        "pt": 'Peso próprio',
    },
    "inf_pq_col_crec": {
        "es": 'Crece propio',
        "en": 'Own growth',
        "pt": 'Cresce próprio',
    },
    "inf_pq_col_crec_mkt": {
        "es": 'Crece mercado',
        "en": 'Market growth',
        "pt": 'Cresce mercado',
    },
    "inf_pq_identidad": {
        "es": 'Verificación: las partes suman {suma:.4f} y la brecha real es {real:.4f}. Diferencia: {residuo:.9f}.',
        "en": 'Check: the parts add up to {suma:.4f} and the real gap is {real:.4f}. Difference: {residuo:.9f}.',
        "pt": 'Verificação: as partes somam {suma:.4f} e a diferença real é {real:.4f}. Diferença: {residuo:.9f}.',
    },
    "ds_tabla": {
        "es": "Tabla «{tabla}» ({cols} columnas, tipos inferidos de {archivo})",
        "en": "Table “{tabla}” ({cols} columns, types inferred from {archivo})",
        "pt": "Tabela «{tabla}» ({cols} colunas, tipos inferidos de {archivo})",
    },
    "ds_relacion": {
        "es": "Relación propuesta: {desde} → {hacia}",
        "en": "Proposed relationship: {desde} → {hacia}",
        "pt": "Relação proposta: {desde} → {hacia}",
    },
    "ds_rel_ambigua": {
        "es": "Posible relación {par}: no se propuso porque las dos columnas son únicas y no se puede saber cuál es la dimensión — creala a mano si corresponde",
        "en": "Possible relationship {par}: not proposed because both columns are unique and the dimension side cannot be told — create it by hand if it applies",
        "pt": "Possível relação {par}: não foi proposta porque as duas colunas são únicas e não dá para saber qual é a dimensão — crie manualmente se corresponder",
    },
    "ds_ruta_m": {
        "es": "El Power Query de cada tabla apunta a C:/Datos/<archivo>: al abrir en Desktop, ajustá la ruta al lugar real del archivo",
        "en": "Each table's Power Query points to C:/Datos/<file>: when opening in Desktop, adjust the path to the file's real location",
        "pt": "O Power Query de cada tabela aponta para C:/Datos/<arquivo>: ao abrir no Desktop, ajuste o caminho para o local real do arquivo",
    },
    "ds_sql_conexion": {
        "es": "Las tablas SQL apuntan a Sql.Database(\"SERVIDOR\", \"BASE\"): completá el servidor y la base reales en Desktop — acá no se conecta a ninguna base",
        "en": "SQL tables point to Sql.Database(\"SERVIDOR\", \"BASE\"): fill in the real server and database in Desktop — nothing connects to a database here",
        "pt": "As tabelas SQL apontam para Sql.Database(\"SERVIDOR\", \"BASE\"): preencha o servidor e o banco reais no Desktop — aqui nada se conecta a banco algum",
    },
    "ds_embebido": {
        "es": "Datos incluidos DENTRO del archivo: {tablas} tabla(s), {filas} filas. Abre y muestra todo sin buscar ningún Excel, CSV ni base — no hace falta refrescar",
        "en": "Data included INSIDE the file: {tablas} table(s), {filas} rows. It opens and shows everything without looking for any Excel, CSV or database — no refresh needed",
        "pt": "Dados incluídos DENTRO do arquivo: {tablas} tabela(s), {filas} linhas. Abre e mostra tudo sem procurar nenhum Excel, CSV ou banco — não precisa atualizar",
    },
    "ds_embebido_parcial": {
        "es": "{tablas} tabla(s) con {filas} filas quedaron DENTRO del archivo, pero no todas: mientras quede una tabla apuntando afuera, si ese Actualizar falla Power BI descarta el modelo entero. Mirá abajo cuáles faltan.",
        "en": "{tablas} table(s) with {filas} rows went INSIDE the file, but not all of them: while one table still points outside, if that Refresh fails Power BI discards the whole model. See below which ones are missing.",
        "pt": "{tablas} tabela(s) com {filas} linhas ficaram DENTRO do arquivo, mas não todas: enquanto uma tabela continuar apontando para fora, se essa Atualização falhar o Power BI descarta o modelo inteiro. Veja abaixo quais faltam.",
    },
    "ds_no_embebido": {
        "es": "«{tabla}» no se incluyó dentro del archivo: tiene {filas} filas × {columnas} columnas y los topes son {maximo} filas y {maximo_celdas} celdas — quedó apuntando al origen y hay que ajustar la ruta al abrir",
        "en": "“{tabla}” was not included inside the file: it has {filas} rows × {columnas} columns and the ceilings are {maximo} rows and {maximo_celdas} cells — it still points to the source and the path must be adjusted on opening",
        "pt": "«{tabla}» não foi incluída dentro do arquivo: tem {filas} linhas × {columnas} colunas e os limites são {maximo} linhas e {maximo_celdas} células — continua apontando para a origem e o caminho deve ser ajustado ao abrir",
    },
    "ds_no_embebido_sin_filas": {
        "es": "«{tabla}» vino de un script SQL: trae el esquema pero ninguna fila, así que no hay nada que incluir — sigue apuntando a la base y hay que completar servidor y base al abrir",
        "en": "“{tabla}” came from a SQL script: it brings the schema but no rows, so there is nothing to include — it still points to the database and server and database must be filled in on opening",
        "pt": "«{tabla}» veio de um script SQL: traz o esquema mas nenhuma linha, então não há nada a incluir — continua apontando para o banco e é preciso preencher servidor e banco ao abrir",
    },
    "ds_afuera_igual": {
        "es": "{n} tabla(s) del modelo siguen saliendo a buscar datos afuera ({lista}): no vinieron de los archivos cargados, así que el empotrado no las alcanza",
        "en": "{n} model table(s) still reach outside for data ({lista}): they did not come from the loaded files, so embedding does not reach them",
        "pt": "{n} tabela(s) do modelo continuam buscando dados fora ({lista}): não vieram dos arquivos carregados, então a inclusão não as alcança",
    },
    "ds_nada_que_empotrar": {
        "es": "No hay datos para incluir dentro del archivo: este modelo no vino de un Excel, un CSV ni un SQL cargados acá",
        "en": "There is no data to include inside the file: this model did not come from an Excel, CSV or SQL loaded here",
        "pt": "Não há dados para incluir dentro do arquivo: este modelo não veio de um Excel, CSV ou SQL carregados aqui",
    },
    "ds_fecha_ambigua": {
        "es": "Fechas tipo 03/04/2024 en {columnas}: ningún valor de esas columnas pasa de 12, así que no hay forma de saber si el día va primero. Se asumió DÍA primero (formato español). Si tus datos son de un sistema en inglés, mes y día quedan invertidos — revisalo antes de usar el archivo.",
        "en": "Dates like 03/04/2024 in {columnas}: no value in those columns goes above 12, so there is no way to tell whether the day comes first. DAY first was assumed (Spanish format). If your data comes from an English system, month and day end up swapped — check it before using the file.",
        "pt": "Datas tipo 03/04/2024 em {columnas}: nenhum valor dessas colunas passa de 12, então não há como saber se o dia vem primeiro. Assumiu-se DIA primeiro (formato espanhol). Se seus dados vêm de um sistema em inglês, mês e dia ficam invertidos — verifique antes de usar o arquivo.",
    },
    "ds_no_leido": {
        "es": "No se pudo leer {archivo}: se siguió sin ese archivo",
        "en": "Could not read {archivo}: continued without that file",
        "pt": "Não foi possível ler {archivo}: continuou-se sem esse arquivo",
    },
    "ds_vacio": {
        "es": "Ningún archivo de datos se pudo leer.",
        "en": "No data file could be read.",
        "pt": "Nenhum arquivo de dados pôde ser lido.",
    },
    "ds_notas_titulo": {
        "es": "Modelo propuesto desde tus datos — qué se infirió y qué ajustar",
        "en": "Model proposed from your data — what was inferred and what to adjust",
        "pt": "Modelo proposto a partir dos seus dados — o que foi inferido e o que ajustar",
    },
    "tr_cal_ya_hay": {
        "es": "Ya hay una tabla de calendario («{tabla}») — no se creó otra",
        "en": "There is already a date table (“{tabla}”) — no other was created",
        "pt": "Já existe uma tabela de calendário («{tabla}») — não se criou outra",
    },
    "ruta_creada": {
        "es": "Ruta de «{entidad}» creada como tabla «{tabla}» ({n} columnas): todos los contactos en una sola línea de tiempo, con cobertura, frecuencia y efectividad",
        "en": "Journey of “{entidad}” created as table “{tabla}” ({n} columns): every contact on a single timeline, with coverage, frequency and effectiveness",
        "pt": "Rota de «{entidad}» criada como tabela «{tabla}» ({n} colunas): todos os contactos numa só linha de tempo, com cobertura, frequência e efetividade",
    },
    "ruta_no_aplica": {
        "es": "No hay ruta que armar: hace falta una entidad (cliente, médico, alumno) con al menos DOS tablas de contacto que lleguen a ella. Acá se encontró «{entidad}» con {n}.",
        "en": "There is no journey to build: it needs an entity (customer, doctor, student) with at least TWO contact tables reaching it. Here “{entidad}” was found with {n}.",
        "pt": "Não há rota para montar: é preciso uma entidade (cliente, médico, aluno) com pelo menos DUAS tabelas de contacto que cheguem a ela. Aqui encontrou-se «{entidad}» com {n}.",
    },
    "ruta_no_hay_datos": {
        "es": "«{entidad}» tiene {n} tablas de contacto y la ruta se puede armar, pero todavía no hay filas adentro del modelo: se arma al preparar el tablero desde el dataset, o sobre un archivo que ya lleve los datos.",
        "en": "“{entidad}” has {n} contact tables and the journey can be built, but there are no rows inside the model yet: it is built when preparing the report from the dataset, or on a file that already carries the data.",
        "pt": "«{entidad}» tem {n} tabelas de contacto e a rota pode ser montada, mas ainda não há linhas dentro do modelo: monta-se ao preparar o painel a partir do dataset, ou sobre um arquivo que já leve os dados.",
    },
    "nlp_diccionario": {
        "es": "Diccionario de medidas agregado como tabla «{tabla}»: {n} medidas con su fórmula y el porqué de cada decisión, adentro del archivo",
        "en": "Measure dictionary added as table “{tabla}”: {n} measures with their formula and the reason behind each decision, inside the file",
        "pt": "Dicionário de medidas adicionado como tabela «{tabla}»: {n} medidas com a sua fórmula e o porquê de cada decisão, dentro do arquivo",
    },

    "tb_pagina_medidas": {
        "es": "Medidas", "en": "Measures", "pt": "Medidas",
    },
    "tb_pagina_medidas_sub": {
        "es": "Qué mide cada medida, su fórmula y por qué está escrita así",
        "en": "What each measure measures, its formula and why it is written that way",
        "pt": "O que mede cada medida, a sua fórmula e porque está escrita assim",
    },

    "tb_tema_resumen": {
        "es": "Resumen ejecutivo",
        "en": "Executive summary",
        "pt": "Resumo executivo",
    },

    "tr_cal_marcada": {
        "es": "«{tabla}» marcada como tabla de fechas: sin esa marca, TOTALYTD y SAMEPERIODLASTYEAR devuelven en blanco",
        "en": "“{tabla}” marked as a date table: without that mark, TOTALYTD and SAMEPERIODLASTYEAR return blank",
        "pt": "«{tabla}» marcada como tabela de datas: sem essa marca, TOTALYTD e SAMEPERIODLASTYEAR devolvem em branco",
    },
    "tr_cal_clave": {
        "es": "{columna} es la clave de fecha del calendario",
        "en": "{columna} is the calendar's date key",
        "pt": "{columna} é a chave de data do calendário",
    },
    "tr_cal_orden": {
        "es": "{columna} ordena por «{orden}» (si no, abril sale antes que enero)",
        "en": "{columna} sorts by “{orden}” (otherwise April comes before January)",
        "pt": "{columna} ordena por «{orden}» (senão, abril sai antes de janeiro)",
    },
    "tr_cal_sin_fechas": {
        "es": "El modelo no tiene ninguna columna de fecha: no hay a qué relacionar un calendario.",
        "en": "The model has no date column: there is nothing to relate a calendar to.",
        "pt": "O modelo não tem nenhuma coluna de data: não há a que relacionar um calendário.",
    },
    "tr_cal_creado": {
        "es": "Tabla «{tabla}» creada (fecha, año, mes ordenado y año-mes) y marcada como tabla de tiempo",
        "en": "Table “{tabla}” created (date, year, sorted month and year-month) and marked as time table",
        "pt": "Tabela «{tabla}» criada (data, ano, mês ordenado e ano-mês) e marcada como tabela de tempo",
    },
    "tr_cal_relacion": {
        "es": "Relación creada: {desde} → {hacia}",
        "en": "Relationship created: {desde} → {hacia}",
        "pt": "Relação criada: {desde} → {hacia}",
    },
    "kpi_total": {"es": "Total {col}", "en": "Total {col}",
                  "pt": "Total {col}"},
    "kpi_margen": {"es": "Margen", "en": "Margin", "pt": "Margem"},
    "kpi_margen_pct": {"es": "Margen %", "en": "Margin %", "pt": "Margem %"},
    "kpi_operaciones": {"es": "Operaciones {tabla}",
                        "en": "{tabla} rows", "pt": "Operações {tabla}"},
    # El nombre dice sobre QUÉ hecho se cuenta. La misma dimensión suele
    # colgar de varias tablas de hechos —«Producto» de Visitas y de
    # Recetas—, y sin la tabla las dos sugerencias se llamaban igual
    # aunque contaran cosas distintas: productos promocionados y
    # productos recetados no son el mismo número.
    "kpi_unicos": {"es": "{dim} únicos en {tabla}",
                   "en": "Unique {dim} in {tabla}",
                   "pt": "{dim} únicos em {tabla}"},
    "kpi_cual": {"es": "{dim} con más {medida}",
                 "en": "{dim} with most {medida}",
                 "pt": "{dim} com mais {medida}"},
    "kpi_pq_cual": {
        "es": "Responde «¿cuál?» y no «¿cuánto?»: devuelve el nombre del «{dim}» que encabeza «{medida}», y se recalcula con el filtro — cambia si se elige otro período.",
        "en": "Answers “which?” instead of “how much?”: it returns the name of the “{dim}” that leads “{medida}”, and recalculates with the filter — it changes if another period is selected.",
        "pt": "Responde «qual?» e não «quanto?»: devolve o nome do «{dim}» que lidera «{medida}», e recalcula-se com o filtro — muda se outro período for escolhido.",
    },
    "kpi_ytd": {"es": "{base} YTD", "en": "{base} YTD", "pt": "{base} YTD"},
    "kpi_vs_aa": {"es": "{base} vs año anterior",
                  "en": "{base} vs last year",
                  "pt": "{base} vs ano anterior"},
    "kpi_pq_total": {
        "es": "«{col}» es una métrica de «{tabla}»: el total es la medida base que todo tablero pide primero",
        "en": "“{col}” is a metric of “{tabla}”: its total is the base measure every dashboard asks for first",
        "pt": "«{col}» é uma métrica de «{tabla}»: o total é a medida base que todo painel pede primeiro",
    },
    "kpi_pq_margen": {
        "es": "Hay «{importe}» y «{costo}» en la misma tabla: la diferencia es el margen",
        "en": "There are “{importe}” and “{costo}” in the same table: the difference is the margin",
        "pt": "Há «{importe}» e «{costo}» na mesma tabela: a diferença é a margem",
    },
    "kpi_pq_margen_pct": {
        "es": "El margen sobre «{importe}», en porcentaje — con DIVIDE, que no explota con cero",
        "en": "The margin over “{importe}”, as a percentage — with DIVIDE, which doesn't blow up on zero",
        "pt": "A margem sobre «{importe}», em porcentagem — com DIVIDE, que não explode com zero",
    },
    "kpi_pq_operaciones": {
        "es": "Cuántas filas tiene «{tabla}»: el volumen de operaciones del período",
        "en": "How many rows “{tabla}” has: the period's operation volume",
        "pt": "Quantas linhas tem «{tabla}»: o volume de operações do período",
    },
    "kpi_pq_unicos": {
        "es": "Cuántos «{dim}» distintos aparecen en «{tabla}»: alcance, no volumen",
        "en": "How many distinct “{dim}” appear in “{tabla}”: reach, not volume",
        "pt": "Quantos «{dim}» distintos aparecem em «{tabla}»: alcance, não volume",
    },
    "kpi_pq_ytd": {
        "es": "El acumulado del año de «{base}», sobre la tabla calendario del modelo",
        "en": "The year-to-date of “{base}”, over the model's date table",
        "pt": "O acumulado do ano de «{base}», sobre a tabela calendário do modelo",
    },
    "kpi_pq_vs_aa": {
        "es": "La variación de «{base}» contra el mismo período del año anterior",
        "en": "The change of “{base}” against the same period last year",
        "pt": "A variação de «{base}» contra o mesmo período do ano anterior",
    },
    "area_dax": {"es": "DAX", "en": "DAX", "pt": "DAX"},
    "area_modelado": {"es": "Modelado", "en": "Modeling", "pt": "Modelagem"},
    "area_calendario": {"es": "Calendario", "en": "Calendar",
                        "pt": "Calendário"},
    "area_transformacion": {"es": "Transformación", "en": "Transformation",
                            "pt": "Transformação"},
    "area_dashboard": {"es": "Dashboard", "en": "Dashboard",
                       "pt": "Dashboard"},
    "an_kpis_titulo": {
        "es": "KPIs que este modelo pide y no tiene",
        "en": "KPIs this model asks for and doesn't have",
        "pt": "KPIs que este modelo pede e não tem",
    },
    "an_kpis_btn": {
        "es": "Agregar todos los KPIs sugeridos",
        "en": "Add all suggested KPIs",
        "pt": "Adicionar todos os KPIs sugeridos",
    },
    "kpi_nada": {
        "es": "No hay KPIs para sugerir: el modelo no tiene columnas numéricas visibles sin medida, o ya están todos.",
        "en": "No KPIs to suggest: the model has no visible numeric columns without a measure, or they all exist already.",
        "pt": "Não há KPIs a sugerir: o modelo não tem colunas numéricas visíveis sem medida, ou já estão todos.",
    },
    "gen_vacio": {
        "es": "Escribí qué medida querés: p. ej. «total de ventas», «ventas vs año anterior».",
        "en": "Type the measure you want: e.g. “total sales”, “sales vs last year”.",
        "pt": "Escreva a medida que quer: p. ex. «total de vendas», «vendas vs ano anterior».",
    },
    "gen_sin_modelo": {
        "es": "Primero cargá un modelo: el generador solo escribe DAX validado contra tu catálogo.",
        "en": "Load a model first: the generator only writes DAX validated against your catalog.",
        "pt": "Carregue um modelo primeiro: o gerador só escreve DAX validado contra o seu catálogo.",
    },
    "gen_sin_patron": {
        "es": "El motor de reglas no reconoció el patrón y la IA falló: {motivo}",
        "en": "The rule engine did not recognise the pattern and the AI failed: {motivo}",
        "pt": "O motor de regras não reconheceu o padrão e a IA falhou: {motivo}",
    },
    "edicion_owner": {
        "es": "owner",
        "en": "owner",
        "pt": "owner",
    },
    "edicion_profesional": {
        "es": "profesional",
        "en": "professional",
        "pt": "profissional",
    },
    "edicion_demo": {
        "es": "demo",
        "en": "demo",
        "pt": "demo",
    },
    "gen_sin_reconocer": {
        "es": "No reconocí el patrón del pedido. Probá con: total / promedio / máximo / mínimo / conteo distinto de <columna>, «% del total por <dimensión>», «<columna> acumulado del año», «<columna> vs año anterior», «media móvil 3 meses de <columna>», «ranking de <dimensión> por <columna>». Con una clave de IA configurada, el pedido libre también funciona.",
        "en": "I did not recognise the request pattern. Try: total / average / max / min / distinct count of <column>, “% of total by <dimension>”, “<column> year to date”, “<column> vs last year”, “3-month moving average of <column>”, “rank <dimension> by <column>”. With an AI key configured, free-form requests work too.",
        "pt": "Não reconheci o padrão do pedido. Tente: total / média / máximo / mínimo / contagem distinta de <coluna>, «% do total por <dimensão>», «<coluna> acumulado do ano», «<coluna> vs ano anterior», «média móvel 3 meses de <coluna>», «ranking de <dimensão> por <coluna>». Com uma chave de IA configurada, o pedido livre também funciona.",
    },
    # ---- explicaciones del generador de DAX ---------------------------
    # Lo que se muestra junto a cada medida generada por el motor de reglas.
    "genx_ya_existe": {
        "es": "El modelo ya tiene esa medida: {medida}. Reutilizarla en vez de sumar la columna a mano mantiene un solo lugar de verdad.",
        "en": "The model already has that measure: {medida}. Reusing it instead of summing the column by hand keeps a single source of truth.",
        "pt": "O modelo já tem essa medida: {medida}. Reutilizá-la em vez de somar a coluna à mão mantém um único lugar de verdade.",
    },
    "genx_suma": {
        "es": "Suma la columna {col} en el contexto del visual: cada celda/fila del reporte filtra qué filas entran en la suma.",
        "en": "Sums the column {col} in the visual's context: every cell/row of the report filters which rows go into the sum.",
        "pt": "Soma a coluna {col} no contexto do visual: cada célula/linha do relatório filtra quais linhas entram na soma.",
    },
    "genx_promedio": {
        "es": "Promedia {col} sobre las filas visibles.",
        "en": "Averages {col} over the visible rows.",
        "pt": "Faz a média de {col} sobre as linhas visíveis.",
    },
    "genx_minmax": {
        "es": "{fn} devuelve el {extremo} valor visible de {col}.",
        "en": "{fn} returns the {extremo} visible value of {col}.",
        "pt": "{fn} devolve o {extremo} valor visível de {col}.",
    },
    "genx_distintos": {
        "es": "Cuenta los valores únicos de {col} en el contexto actual.",
        "en": "Counts the unique values of {col} in the current context.",
        "pt": "Conta os valores únicos de {col} no contexto atual.",
    },
    "genx_filas": {
        "es": "Cuenta las filas visibles de la tabla {tabla}.",
        "en": "Counts the visible rows of the table {tabla}.",
        "pt": "Conta as linhas visíveis da tabela {tabla}.",
    },
    "genx_pct_total": {
        "es": "Divide el valor del contexto actual por el mismo valor sin los filtros del visual (ALLSELECTED respeta los slicers): eso es la participación sobre el total. DIVIDE evita el error ante total 0.",
        "en": "Divides the current context's value by the same value without the visual's filters (ALLSELECTED respects the slicers): that is the share of total. DIVIDE avoids the error when the total is 0.",
        "pt": "Divide o valor do contexto atual pelo mesmo valor sem os filtros do visual (ALLSELECTED respeita os slicers): isso é a participação sobre o total. DIVIDE evita o erro com total 0.",
    },
    "genx_ytd": {
        "es": "TOTALYTD acumula {base} desde el 1 de enero hasta la fecha del contexto, usando el calendario {calendario}.",
        "en": "TOTALYTD accumulates {base} from 1 January to the context date, using the {calendario} date table.",
        "pt": "TOTALYTD acumula {base} desde 1º de janeiro até a data do contexto, usando o calendário {calendario}.",
    },
    "genx_vs_aa": {
        "es": "Calcula el valor actual y el del mismo período del año anterior (SAMEPERIODLASTYEAR desplaza el calendario), y devuelve la variación relativa con DIVIDE.",
        "en": "Computes the current value and the same period last year (SAMEPERIODLASTYEAR shifts the date table), and returns the relative change with DIVIDE.",
        "pt": "Calcula o valor atual e o do mesmo período do ano anterior (SAMEPERIODLASTYEAR desloca o calendário), e devolve a variação relativa com DIVIDE.",
    },
    "genx_media_movil": {
        "es": "DATESINPERIOD arma la ventana de los últimos {meses} meses y AVERAGEX promedia el valor mensual dentro de ella — suaviza el ruido de los picos.",
        "en": "DATESINPERIOD builds the window of the last {meses} months and AVERAGEX averages the monthly value inside it — it smooths out spikes.",
        "pt": "DATESINPERIOD monta a janela dos últimos {meses} meses e AVERAGEX faz a média do valor mensal dentro dela — suaviza o ruído dos picos.",
    },
    "genx_ranking": {
        "es": "RANKX ordena todos los valores visibles de {col} por {base} descendente y devuelve la posición de cada uno.",
        "en": "RANKX sorts every visible value of {col} by {base} descending and returns each one's position.",
        "pt": "RANKX ordena todos os valores visíveis de {col} por {base} descendente e devolve a posição de cada um.",
    },
    "genx_topn": {
        "es": "TOPN elige los {n} valores de {col} con mayor {base}; KEEPFILTERS los aplica como filtro sin pisar el contexto del visual.",
        "en": "TOPN picks the {n} values of {col} with the highest {base}; KEEPFILTERS applies them as a filter without overriding the visual's context.",
        "pt": "TOPN escolhe os {n} valores de {col} com maior {base}; KEEPFILTERS os aplica como filtro sem sobrepor o contexto do visual.",
    },
    "genx_mayor": {"es": "mayor", "en": "highest", "pt": "maior"},
    "genx_menor": {"es": "menor", "en": "lowest", "pt": "menor"},
    "genx_ambiguo": {
        "es": "Usé {elegida} porque el pedido no aclara cuál; en el modelo también están {otras}.",
        "en": "I used {elegida} because the request does not say which one; the model also has {otras}.",
        "pt": "Usei {elegida} porque o pedido não esclarece qual; no modelo também estão {otras}.",
    },
    # ---- errores puntuales de cada regla -------------------------------
    "genx_sin_columna_suma": {
        "es": "No encontré una columna numérica que se parezca a «{objetivo}» en el modelo.",
        "en": "I could not find a numeric column that resembles “{objetivo}” in the model.",
        "pt": "Não encontrei uma coluna numérica parecida com «{objetivo}» no modelo.",
    },
    "genx_sin_columna_promedio": {
        "es": "No encontré una columna numérica para promediar en «{texto}».",
        "en": "I could not find a numeric column to average in “{texto}”.",
        "pt": "Não encontrei uma coluna numérica para fazer a média em «{texto}».",
    },
    "genx_sin_columna_conteo": {
        "es": "No encontré la columna a contar en «{texto}».",
        "en": "I could not find the column to count in “{texto}”.",
        "pt": "Não encontrei a coluna para contar em «{texto}».",
    },
    "genx_sin_base_pct": {
        "es": "No encontré sobre qué calcular el % del total. Decime la medida o la columna: «% del total de <medida>».",
        "en": "I could not find what to calculate the % of total on. Tell me the measure or the column: “% of total of <measure>”.",
        "pt": "Não encontrei sobre o que calcular o % do total. Diga a medida ou a coluna: «% do total de <medida>».",
    },
    "genx_sin_calendario_ytd": {
        "es": "Para un acumulado del año necesito una tabla de calendario en el modelo, y no encontré ninguna.",
        "en": "For a year-to-date accumulation I need a date table in the model, and I could not find one.",
        "pt": "Para um acumulado do ano preciso de uma tabela de calendário no modelo, e não encontrei nenhuma.",
    },
    "genx_sin_base_ytd": {
        "es": "No encontré qué acumular en «{texto}».",
        "en": "I could not find what to accumulate in “{texto}”.",
        "pt": "Não encontrei o que acumular em «{texto}».",
    },
    "genx_sin_calendario_aa": {
        "es": "Para comparar contra el año anterior necesito una tabla de calendario, y no encontré ninguna.",
        "en": "To compare against last year I need a date table, and I could not find one.",
        "pt": "Para comparar com o ano anterior preciso de uma tabela de calendário, e não encontrei nenhuma.",
    },
    "genx_sin_base_aa": {
        "es": "No encontré qué comparar en «{texto}».",
        "en": "I could not find what to compare in “{texto}”.",
        "pt": "Não encontrei o que comparar em «{texto}».",
    },
    "genx_sin_calendario_mm": {
        "es": "Para una media móvil necesito una tabla de calendario en el modelo.",
        "en": "For a moving average I need a date table in the model.",
        "pt": "Para uma média móvel preciso de uma tabela de calendário no modelo.",
    },
    "genx_sin_base_mm": {
        "es": "No encontré qué promediar en «{texto}».",
        "en": "I could not find what to average in “{texto}”.",
        "pt": "Não encontrei o que fazer a média em «{texto}».",
    },
    "genx_sin_ranking": {
        "es": "Para un ranking necesito la dimensión y la métrica: «ranking de <columna> por <métrica>».",
        "en": "For a ranking I need the dimension and the metric: “rank <column> by <metric>”.",
        "pt": "Para um ranking preciso da dimensão e da métrica: «ranking de <coluna> por <métrica>».",
    },
    "genx_sin_topn": {
        "es": "Para un top {n} necesito dimensión y métrica: «top {n} <columna> por <métrica>».",
        "en": "For a top {n} I need a dimension and a metric: “top {n} <column> by <metric>”.",
        "pt": "Para um top {n} preciso de dimensão e métrica: «top {n} <coluna> por <métrica>».",
    },
    "genx_ia_sin_json": {
        "es": "la IA no devolvió JSON",
        "en": "the AI did not return JSON",
        "pt": "a IA não devolveu JSON",
    },
    "genx_ia_error": {
        "es": "IA: {error}",
        "en": "AI: {error}",
        "pt": "IA: {error}",
    },
    "genx_ia_referencias_invalidas": {
        "es": "La IA propuso referencias que no existen en el modelo (descartado): {detalle}",
        "en": "The AI proposed references that do not exist in the model (discarded): {detalle}",
        "pt": "A IA propôs referências que não existem no modelo (descartado): {detalle}",
    },
    # ---- nombres de las medidas que arma el motor de reglas ------------
    "genx_nombre_total": {"es": "Total {col}", "en": "Total {col}",
                          "pt": "Total {col}"},
    "genx_nombre_promedio": {"es": "Promedio {col}", "en": "Average {col}",
                             "pt": "Média {col}"},
    "genx_nombre_maximo": {"es": "Máximo {col}", "en": "Maximum {col}",
                           "pt": "Máximo {col}"},
    "genx_nombre_minimo": {"es": "Mínimo {col}", "en": "Minimum {col}",
                           "pt": "Mínimo {col}"},
    "genx_nombre_distintos": {"es": "{entidad} distintos",
                              "en": "Distinct {entidad}",
                              "pt": "{entidad} distintos"},
    "genx_nombre_filas": {"es": "Filas de {tabla}", "en": "Rows of {tabla}",
                          "pt": "Linhas de {tabla}"},
    "genx_nombre_pct_total": {"es": "% del total · {base}",
                              "en": "% of total · {base}",
                              "pt": "% do total · {base}"},
    "genx_nombre_ytd": {"es": "{base} YTD", "en": "{base} YTD",
                        "pt": "{base} YTD"},
    "genx_nombre_vs_aa": {"es": "{base} · var. % vs AA",
                          "en": "{base} · % change vs LY",
                          "pt": "{base} · var. % vs AA"},
    "genx_nombre_media_movil": {
        "es": "{base} · media móvil {meses}m",
        "en": "{base} · {meses}m moving average",
        "pt": "{base} · média móvel {meses}m",
    },
    "genx_nombre_ranking": {"es": "Ranking {col} por {base}",
                            "en": "Ranking {col} by {base}",
                            "pt": "Ranking {col} por {base}"},
    "genx_nombre_topn": {"es": "{base} · top {n} {col}",
                        "en": "{base} · top {n} {col}",
                        "pt": "{base} · top {n} {col}"},
    # ---- patrones de la ficha: filtrada, iterador, ticket, inactiva ------
    "genx_nombre_filtrada": {"es": "{base} · {valor}",
                             "en": "{base} · {valor}",
                             "pt": "{base} · {valor}"},
    "genx_filtrada": {
        "es": "CALCULATE evalúa {base} reemplazando el filtro sobre {col} por «{valor}». Un filtro simple de columna, no FILTER sobre la tabla entera: reemplaza sólo esa columna y deja el resto del contexto intacto.",
        "en": "CALCULATE evaluates {base} replacing the filter on {col} with «{valor}». A simple column filter, not FILTER over the whole table: it replaces only that column and leaves the rest of the context untouched.",
        "pt": "CALCULATE avalia {base} substituindo o filtro sobre {col} por «{valor}». Um filtro simples de coluna, não FILTER sobre a tabela inteira: substitui só essa coluna e deixa o resto do contexto intacto.",
    },
    "genx_sin_columna_filtro": {
        "es": "No encontré la columna «{col}» en el modelo, así que no armo el filtro.",
        "en": "I could not find a column «{col}» in the model, so I am not building the filter.",
        "pt": "Não encontrei a coluna «{col}» no modelo, então não monto o filtro.",
    },
    "genx_sin_base_filtro": {
        "es": "Entendí el filtro pero no qué medir en «{texto}».",
        "en": "I understood the filter but not what to measure in «{texto}».",
        "pt": "Entendi o filtro mas não o que medir em «{texto}».",
    },
    "genx_nombre_iterador": {"es": "{a} × {b}",
                             "en": "{a} × {b}",
                             "pt": "{a} × {b}"},
    "genx_iterador": {
        "es": "SUMX recorre {tabla} fila por fila, multiplica {a} por {b} en cada una y recién después suma. Hace falta porque el producto no existe como columna: SUM no puede multiplicar antes de agregar.",
        "en": "SUMX walks {tabla} row by row, multiplies {a} by {b} on each one and only then sums. It is needed because the product does not exist as a column: SUM cannot multiply before aggregating.",
        "pt": "SUMX percorre {tabla} linha por linha, multiplica {a} por {b} em cada uma e só depois soma. É preciso porque o produto não existe como coluna: SUM não pode multiplicar antes de agregar.",
    },
    "genx_nombre_ticket": {"es": "Ticket promedio · {base}",
                           "en": "Average ticket · {base}",
                           "pt": "Ticket médio · {base}"},
    "genx_ticket": {
        "es": "{base} dividido por la cantidad de {clave} distintos, con DIVIDE para que no rompa si el denominador es cero. Ojo: no es AVERAGE — AVERAGE promedia líneas, y esto promedia operaciones, que dan números distintos.",
        "en": "{base} divided by the number of distinct {clave}, with DIVIDE so it does not break when the denominator is zero. Note: this is not AVERAGE — AVERAGE averages lines, this averages transactions, and they give different numbers.",
        "pt": "{base} dividido pela quantidade de {clave} distintos, com DIVIDE para não quebrar se o denominador for zero. Atenção: não é AVERAGE — AVERAGE faz média de linhas, isto faz média de operações, e dão números diferentes.",
    },
    "genx_sin_base_ticket": {
        "es": "No sé sobre qué importe calcular el ticket promedio.",
        "en": "I do not know which amount to compute the average ticket on.",
        "pt": "Não sei sobre qual valor calcular o ticket médio.",
    },
    "genx_sin_clave_ticket": {
        "es": "No encontré una columna que identifique cada operación para contar. Decime cuál con «ticket promedio por <columna>».",
        "en": "I could not find a column identifying each transaction to count. Tell me which one with «average ticket by <column>».",
        "pt": "Não encontrei uma coluna que identifique cada operação para contar. Diga qual com «ticket médio por <coluna>».",
    },
    "genx_nombre_inactiva": {"es": "{base} por {col}",
                             "en": "{base} by {col}",
                             "pt": "{base} por {col}"},
    "genx_inactiva": {
        "es": "El modelo tiene una relación INACTIVA entre {izq} y {der}. USERELATIONSHIP la activa sólo dentro de este CALCULATE, así que {base} se mide por esa fecha sin tocar el resto del modelo. Es la alternativa a duplicar la tabla calendario.",
        "en": "The model has an INACTIVE relationship between {izq} and {der}. USERELATIONSHIP turns it on only inside this CALCULATE, so {base} is measured by that date without touching the rest of the model. It is the alternative to duplicating the calendar table.",
        "pt": "O modelo tem uma relação INATIVA entre {izq} e {der}. USERELATIONSHIP a ativa só dentro deste CALCULATE, então {base} é medido por essa data sem mexer no resto do modelo. É a alternativa a duplicar a tabela calendário.",
    },
    # ---- arreglos nuevos del transformador -------------------------------
    "tr_filter_simple": {
        "es": "[{obj}]: {n} FILTER sobre la tabla entera → CALCULATE + KEEPFILTERS (mismo resultado, sin iterar la tabla).",
        "en": "[{obj}]: {n} FILTER over the whole table → CALCULATE + KEEPFILTERS (same result, no table scan).",
        "pt": "[{obj}]: {n} FILTER sobre a tabela inteira → CALCULATE + KEEPFILTERS (mesmo resultado, sem varrer a tabela).",
    },
    "tr_unidireccional": {
        "es": "Relación {desde} → {hacia}: de bidireccional a una sola dirección. Ojo: cambia el cross-filtrado de los visuales que dependían de la vuelta.",
        "en": "Relationship {desde} → {hacia}: from bidirectional to single direction. Note: this changes cross-filtering for visuals that relied on the return path.",
        "pt": "Relação {desde} → {hacia}: de bidirecional para uma só direção. Atenção: muda o cross-filtro dos visuais que dependiam da volta.",
    },
    "tr_auto_fecha": {
        "es": "Se borraron {cuantas} tablas de fecha automáticas y se apagó su regeneración (__PBI_TimeIntelligenceEnabled = 0).",
        "en": "{cuantas} automatic date tables were removed and their regeneration turned off (__PBI_TimeIntelligenceEnabled = 0).",
        "pt": "Apagaram-se {cuantas} tabelas de data automáticas e desligou-se a sua regeneração (__PBI_TimeIntelligenceEnabled = 0).",
    },
    "an_elegir_arreglos": {
        "es": "Elegí qué arreglos aplicar — nada se toca sin tu casilla marcada:",
        "en": "Choose which fixes to apply — nothing is touched without its box checked:",
        "pt": "Escolha quais correções aplicar — nada é tocado sem a caixa marcada:",
    },
    "an_cambia_filtrado": {
        "es": "cambia el cross-filtrado",
        "en": "changes cross-filtering",
        "pt": "muda o cross-filtro",
    },
    "carga_modelo_de": {
        "es": "Modelo leído de", "en": "Model read from",
        "pt": "Modelo lido de",
    },
    "carga_reporte_de": {
        "es": "reporte, de", "en": "report, from", "pt": "relatório, de",
    },
    "err_aislado": {
        "es": "El fallo quedó encerrado en esta pestaña: el resto del "
              "programa sigue funcionando y tu modelo no se perdió.",
        "en": "The failure is contained in this tab: the rest of the program "
              "keeps working and your model was not lost.",
        "pt": "A falha ficou contida nesta aba: o resto do programa continua "
              "funcionando e seu modelo não foi perdido.",
    },
    "err_detalle": {
        "es": "Ver detalle técnico (para reportarlo)",
        "en": "Technical detail (to report it)",
        "pt": "Detalhe técnico (para reportar)",
    },
    "ac_sin_banco": {
        "es": "No se encontró el banco de ejercicios (datos/ejercicios.json). "
              "El resto del programa funciona normalmente.",
        "en": "The exercise bank was not found (datos/ejercicios.json). "
              "The rest of the program works normally.",
        "pt": "O banco de exercícios não foi encontrado (datos/ejercicios.json). "
              "O resto do programa funciona normalmente.",
    },
    "an_como_lo_ve": {
        "es": "Cómo lo ve quien usa el tablero",
        "en": "What the person using the report sees",
        "pt": "Como vê quem usa o painel",
    },
    "an_como_lo_ve_nota": {
        "es": "Los mismos hallazgos, dibujados como un informe de Power BI. "
              "El «antes» muestra el síntoma que ve el cliente —una tarjeta "
              "en blanco, un visual que no dibuja—; los números salen del "
              "modelo demo sintético que trae el programa.",
        "en": "The same findings, drawn as a Power BI report. The «before» "
              "shows the symptom the client sees —a blank card, a visual "
              "that will not render—; the numbers come from the synthetic "
              "demo model shipped with the program.",
        "pt": "Os mesmos achados, desenhados como um relatório do Power BI. "
              "O «antes» mostra o sintoma que o cliente vê —um cartão em "
              "branco, um visual que não desenha—; os números vêm do modelo "
              "demo sintético que acompanha o programa.",
    },
    "an_borra_tablas": {
        "es": "borra tablas ocultas sin relaciones ni uso",
        "en": "deletes hidden tables with no relationships or usage",
        "pt": "apaga tabelas ocultas sem relações nem uso",
    },
    "an_mueve_medidas": {
        "es": "los visuales que nombran medidas por su tabla deben re-apuntarse",
        "en": "visuals that name measures by their table must be re-pointed",
        "pt": "os visuais que nomeiam medidas pela tabela devem ser re-apontados",
    },
    "tr_puente": {
        "es": "Muchos-a-muchos {desde} → {hacia} reemplazada por la tabla puente «{puente}» (claves únicas + una pata bidireccional). El flujo de filtro queda idéntico: ninguna cifra cambia.",
        "en": "Many-to-many {desde} → {hacia} replaced by bridge table «{puente}» (unique keys + one bidirectional leg). Filter flow stays identical: no figure changes.",
        "pt": "Muitos-para-muitos {desde} → {hacia} substituída pela tabela ponte «{puente}» (chaves únicas + uma perna bidirecional). O fluxo de filtro fica idêntico: nenhum número muda.",
    },
    "tr_refs_medidas": {
        "es": "{n} referencia(s) DAX a medidas movidas quedaron sin calificar (una medida no se nombra con su tabla: al moverla, esa referencia deja de existir).",
        "en": "{n} DAX reference(s) to moved measures were unqualified (a measure is not named with its table: once moved, that reference stops existing).",
        "pt": "{n} referência(s) DAX a medidas movidas ficaram sem qualificar (uma medida não se nomeia com a sua tabela: ao movê-la, essa referência deixa de existir).",
    },
    "tr_tabla_suelta_borrada": {
        "es": "Tabla «{nombre}» borrada: estaba oculta, sin relaciones, sin medidas y ninguna expresión del modelo la usa.",
        "en": "Table «{nombre}» deleted: it was hidden, had no relationships, no measures, and no expression in the model uses it.",
        "pt": "Tabela «{nombre}» apagada: estava oculta, sem relações, sem medidas e nenhuma expressão do modelo a usa.",
    },
    # ---- corrector del reporte ------------------------------------------
    "co_borrado": {
        "es": "Se borró una copia exacta de «{tipo}» en «{pagina}». No se pierde ninguna cifra: era el mismo visual con los mismos campos, filtros y título.",
        "en": "An exact copy of «{tipo}» on «{pagina}» was deleted. No figure is lost: it was the same visual with the same fields, filters and title.",
        "pt": "Apagou-se uma cópia exata de «{tipo}» em «{pagina}». Nenhum número se perde: era o mesmo visual com os mesmos campos, filtros e título.",
    },
    "co_movido": {
        "es": "Se movió «{tipo}» en «{pagina}» a ({x}, {y}): estaba tapado y no se podía usar con el mouse.",
        "en": "«{tipo}» on «{pagina}» was moved to ({x}, {y}): it was covered and could not be clicked.",
        "pt": "Moveu-se «{tipo}» em «{pagina}» para ({x}, {y}): estava tapado e não dava para clicar.",
    },
    "co_sin_lugar": {
        "es": "«{tipo}» sigue tapado en «{pagina}»: no hay lugar libre en el lienzo para moverlo sin pisar otra cosa. Hay que decidirlo a mano.",
        "en": "«{tipo}» is still covered on «{pagina}»: there is no free space on the canvas to move it without overlapping something else. It needs a manual decision.",
        "pt": "«{tipo}» continua tapado em «{pagina}»: não há espaço livre na tela para o mover sem sobrepor outra coisa. É preciso decidir à mão.",
    },
    "co_sin_layout": {
        "es": "El archivo no trae un reporte legible, así que no hay nada que corregir.",
        "en": "The file has no readable report, so there is nothing to fix.",
        "pt": "O arquivo não traz um relatório legível, então não há nada a corrigir.",
    },
    # ---- Power Query: SQL que se pliega al origen ------------------------
    "tab_powerquery": {"es": "Power Query", "en": "Power Query", "pt": "Power Query"},
    "pq_titulo": {"es": "Lo que conviene bajar al origen",
                  "en": "What belongs at the source",
                  "pt": "O que convém baixar para a origem"},
    "pq_lema": {
        "es": "Lo más cerca del origen posible: limpieza, tipado, filtros y combinaciones van acá. En DAX quedan sólo los cálculos que dependen del filtro del usuario.",
        "en": "As close to the source as possible: cleaning, typing, filters and joins belong here. Only calculations that depend on the user's filter stay in DAX.",
        "pt": "O mais perto da origem possível: limpeza, tipagem, filtros e combinações ficam aqui. Em DAX ficam só os cálculos que dependem do filtro do usuário.",
    },
    "pq_motor": {"es": "Motor de la base", "en": "Database engine", "pt": "Motor da base"},
    "pq_servidor": {"es": "Servidor", "en": "Server", "pt": "Servidor"},
    "pq_base": {"es": "Base de datos", "en": "Database", "pt": "Base de dados"},
    "pq_sugerencias": {"es": "En este modelo",
                       "en": "In this model", "pt": "Neste modelo"},
    "pq_que_hacer": {"es": "Qué querés armar", "en": "What to build",
                     "pt": "O que queres montar"},
    "pq_receta_desnormalizar": {"es": "Traer una dimensión al hecho",
                                "en": "Bring a dimension into the fact",
                                "pt": "Trazer uma dimensão para o facto"},
    "pq_receta_normalizar": {"es": "Pasar columnas a filas",
                             "en": "Turn columns into rows",
                             "pt": "Passar colunas a linhas"},
    "pq_receta_columna": {"es": "Columna calculada en el origen",
                          "en": "Calculated column at the source",
                          "pt": "Coluna calculada na origem"},
    "pq_relacion": {"es": "Relación", "en": "Relationship", "pt": "Relação"},
    "pq_sin_relaciones": {
        "es": "Este modelo no tiene relaciones activas para aplanar.",
        "en": "This model has no active relationships to flatten.",
        "pt": "Este modelo não tem relações ativas para achatar.",
    },
    "pq_columnas_a_traer": {"es": "Columnas a traer",
                            "en": "Columns to bring", "pt": "Colunas a trazer"},
    "pq_tabla": {"es": "Tabla", "en": "Table", "pt": "Tabela"},
    "pq_columnas_fijas": {"es": "Columnas que se quedan como están",
                          "en": "Columns that stay as they are",
                          "pt": "Colunas que ficam como estão"},
    "pq_columnas_a_filas": {"es": "Columnas que pasan a ser filas",
                            "en": "Columns that become rows",
                            "pt": "Colunas que passam a linhas"},
    "pq_nombre_columna": {"es": "Nombre de la columna nueva",
                          "en": "New column name",
                          "pt": "Nome da coluna nova"},
    "pq_expresion_sql": {"es": "Expresión SQL", "en": "SQL expression",
                         "pt": "Expressão SQL"},
    "pq_paso_m": {"es": "Paso de Power Query (editor avanzado)",
                  "en": "Power Query step (advanced editor)",
                  "pt": "Passo de Power Query (editor avançado)"},
    "pq_alternativa_m": {
        "es": "Alternativa sin SQL nativo, si preferís hacerlo con pasos de M:",
        "en": "Alternative without native SQL, if you prefer M steps:",
        "pt": "Alternativa sem SQL nativo, se preferires passos de M:",
    },

    "pq_sql_vacio": {"es": "La consulta está vacía.",
                     "en": "The query is empty.",
                     "pt": "A consulta está vazia."},
    "pq_varios_statements": {
        "es": "No se permite ejecutar varias sentencias en una sola consulta.",
        "en": "Running several statements in one query is not allowed.",
        "pt": "Não é permitido executar várias sentenças numa só consulta.",
    },
    "pq_no_select": {
        "es": "MV DAX Lab es de solo lectura: la consulta debe empezar con SELECT o WITH.",
        "en": "MV DAX Lab is read-only: the query must start with SELECT or WITH.",
        "pt": "MV DAX Lab é somente leitura: a consulta deve começar com SELECT ou WITH.",
    },
    "pq_operacion_prohibida": {
        "es": "Operación no permitida: '{op}'. El programa nunca modifica tu base de datos.",
        "en": "Operation not allowed: '{op}'. The program never modifies your database.",
        "pt": "Operação não permitida: '{op}'. O programa nunca modifica a tua base de dados.",
    },
    "pq_sin_columnas": {
        "es": "Hay que elegir al menos una columna.",
        "en": "Pick at least one column.",
        "pt": "É preciso escolher pelo menos uma coluna.",
    },
    "pq_sin_expresion": {
        "es": "Falta el nombre de la columna o la expresión.",
        "en": "The column name or the expression is missing.",
        "pt": "Falta o nome da coluna ou a expressão.",
    },
    "pq_titulo_desnormalizar": {
        "es": "Traer {dim} dentro de {hecho}",
        "en": "Bring {dim} into {hecho}",
        "pt": "Trazer {dim} para dentro de {hecho}",
    },
    "pq_nota_desnormalizar": {
        "es": "LEFT JOIN y no INNER: un INNER descarta en silencio las filas de {hecho} que no tienen fila en {dim}, y el total deja de cerrar contra la suma cruda sin que nadie se entere. Con LEFT los huérfanos quedan en NULL y se ven.",
        "en": "LEFT JOIN and not INNER: an INNER silently drops the rows of {hecho} with no match in {dim}, and the total stops reconciling against the raw sum with nobody noticing. With LEFT the orphans stay as NULL and show up.",
        "pt": "LEFT JOIN e não INNER: um INNER descarta em silêncio as linhas de {hecho} sem correspondência em {dim}, e o total deixa de bater com a soma crua sem ninguém perceber. Com LEFT os órfãos ficam em NULL e aparecem.",
    },
    "pq_titulo_normalizar": {
        "es": "Pasar columnas a filas en {tabla}",
        "en": "Turn columns into rows in {tabla}",
        "pt": "Passar colunas a linhas em {tabla}",
    },
    "pq_nota_normalizar": {
        "es": "{cuantas} columnas pasan a ser valores de «{atributo}». Con una columna por mes hay que reescribir el informe cada vez que aparece un mes nuevo; con los meses como filas, el mismo DAX sirve para siempre. Se genera UNION ALL en vez del operador UNPIVOT porque UNPIVOT no existe en MySQL ni PostgreSQL.",
        "en": "{cuantas} columns become values of «{atributo}». With one column per month the report must be rewritten every time a new month shows up; with months as rows, the same DAX works forever. UNION ALL is generated instead of the UNPIVOT operator because UNPIVOT does not exist in MySQL or PostgreSQL.",
        "pt": "{cuantas} colunas passam a ser valores de «{atributo}». Com uma coluna por mês é preciso reescrever o relatório sempre que aparece um mês novo; com os meses como linhas, o mesmo DAX serve para sempre. Gera-se UNION ALL em vez do operador UNPIVOT porque UNPIVOT não existe no MySQL nem no PostgreSQL.",
    },
    "pq_titulo_columna": {
        "es": "Resolver {nombre} en el origen, no en DAX",
        "en": "Resolve {nombre} at the source, not in DAX",
        "pt": "Resolver {nombre} na origem, não em DAX",
    },
    "pq_nota_columna": {
        "es": "«{nombre}» calculada en el origen comprime mejor y no ocupa lugar en el modelo. Una columna calculada en DAX se materializa fila por fila y queda fija; sólo vale la pena cuando el valor se necesita para filtrar, agrupar o relacionar.",
        "en": "«{nombre}» computed at the source compresses better and takes no space in the model. A DAX calculated column materialises row by row and stays fixed; it is only worth it when the value is needed to filter, group or relate.",
        "pt": "«{nombre}» calculada na origem comprime melhor e não ocupa lugar no modelo. Uma coluna calculada em DAX materializa-se linha a linha e fica fixa; só vale a pena quando o valor é preciso para filtrar, agrupar ou relacionar.",
    },
    "pq_m_reemplazar": {
        "es": "reemplazar por la expresión M equivalente",
        "en": "replace with the equivalent M expression",
        "pt": "substituir pela expressão M equivalente",
    },
    "pq_sug_columna": {
        "es": "«{col}» de {tabla} es una columna calculada en DAX: si se puede resolver en el origen, comprime mejor.",
        "en": "«{col}» in {tabla} is a DAX calculated column: if it can be resolved at the source, it compresses better.",
        "pt": "«{col}» de {tabla} é uma coluna calculada em DAX: se puder ser resolvida na origem, comprime melhor.",
    },
    "pq_sug_join": {
        "es": "{dim} se puede traer dentro de {hecho} en el origen si el modelo estrella no aporta acá.",
        "en": "{dim} can be brought into {hecho} at the source if the star schema adds nothing here.",
        "pt": "{dim} pode ser trazida para dentro de {hecho} na origem se o esquema estrela não ajudar aqui.",
    },
    "pq_aviso_plegado": {
        "es": "Ojo con el plegado: una consulta nativa está perfecta como PRIMER paso —la ejecuta entera el servidor— pero todo lo que venga después en el editor deja de traducirse a SQL y lo procesa el motor local. Se verifica con clic derecho en el paso → Ver consulta nativa: si está gris, se rompió.",
        "en": "Mind the folding: a native query is perfect as the FIRST step — the server runs all of it — but everything after it in the editor stops being translated to SQL and is processed by the local engine. Check it with right click on the step → View native query: if it is greyed out, folding broke.",
        "pt": "Atenção ao folding: uma consulta nativa é perfeita como PRIMEIRO passo — o servidor executa-a inteira — mas tudo o que vier depois no editor deixa de ser traduzido para SQL e é processado pelo motor local. Verifica-se com clique direito no passo → Ver consulta nativa: se estiver cinzento, quebrou.",
    },
    "pq_aviso_nombres": {
        "es": "Los nombres salen del MODELO, no de la base: casi siempre coinciden con la vista de origen, pero no tienen por qué. Revisá el SQL antes de pegarlo.",
        "en": "The names come from the MODEL, not the database: they almost always match the source view, but they do not have to. Review the SQL before pasting it.",
        "pt": "Os nomes vêm do MODELO, não da base: quase sempre coincidem com a vista de origem, mas não têm de coincidir. Revê o SQL antes de colar.",
    },
    # ---- validación de referencias contra el catálogo -------------------
    "cat_tabla_inexistente": {
        "es": "La tabla '{tabla}' no existe en el modelo.",
        "en": "Table '{tabla}' does not exist in the model.",
        "pt": "A tabela '{tabla}' não existe no modelo.",
    },
    "cat_columna_inexistente": {
        "es": "La columna {tabla}[{col}] no existe en el modelo.",
        "en": "Column {tabla}[{col}] does not exist in the model.",
        "pt": "A coluna {tabla}[{col}] não existe no modelo.",
    },
    "cat_medida_inexistente": {
        "es": "La medida [{medida}] no existe en el modelo.",
        "en": "Measure [{medida}] does not exist in the model.",
        "pt": "A medida [{medida}] não existe no modelo.",
    },

    # ---- gate de salida: auditoría del archivo YA ESCRITO ---------------
    # Un título por ítem y un detalle por estado. El detalle lleva la
    # evidencia concreta (cuántos, cuáles) — el punto del gate es que no
    # se pueda decir "listo" sin poder mostrar qué se miró.
    "vf_titulo": {"es": "Verificación del archivo exportado",
                  "en": "Exported file check",
                  "pt": "Verificação do arquivo exportado"},
    "vf_explicacion": {
        "es": "Esto NO revisa el modelo en memoria: abre el archivo que se acaba de escribir —el mismo que se le manda al cliente— y lo audita como lo haría alguien que lo recibe sin saber cómo se generó.",
        "en": "This does NOT check the in-memory model: it opens the file just written — the very one you hand over — and audits it the way someone receiving it would, knowing nothing about how it was made.",
        "pt": "Isto NÃO revê o modelo em memória: abre o arquivo acabado de escrever — o mesmo que se entrega ao cliente — e audita-o como faria quem o recebe sem saber como foi gerado.",
    },
    "vf_sin_desktop": {
        "es": "Lo único que no se puede comprobar desde acá es abrirlo en Power BI Desktop (esto corre en Linux). Todo lo demás está verificado contra el archivo real, no contra lo que creíamos haber escrito.",
        "en": "The one thing that cannot be checked from here is opening it in Power BI Desktop (this runs on Linux). Everything else is verified against the real file, not against what we thought we had written.",
        "pt": "A única coisa que não se pode comprovar daqui é abri-lo no Power BI Desktop (isto corre em Linux). Todo o resto está verificado contra o arquivo real, não contra o que julgávamos ter escrito.",
    },

    "vf_archivo": {"es": "Archivo", "en": "File", "pt": "Arquivo"},
    "vf_archivo_ok": {
        "es": "{ruta} — {kb} KB en disco.",
        "en": "{ruta} — {kb} KB on disk.",
        "pt": "{ruta} — {kb} KB em disco.",
    },
    "vf_archivo_falta": {
        "es": "No existe: {ruta}. No se escribió nada.",
        "en": "Does not exist: {ruta}. Nothing was written.",
        "pt": "Não existe: {ruta}. Não se escreveu nada.",
    },

    "vf_zip": {"es": "Formato del contenedor", "en": "Container format",
               "pt": "Formato do contentor"},
    "vf_zip_falta": {
        "es": "No es un zip válido, así que Power BI ni lo va a intentar abrir ({motivo}).",
        "en": "Not a valid zip, so Power BI will not even try to open it ({motivo}).",
        "pt": "Não é um zip válido, por isso o Power BI nem o vai tentar abrir ({motivo}).",
    },

    "vf_contenedor": {"es": "Partes obligatorias", "en": "Required parts",
                      "pt": "Partes obrigatórias"},
    "vf_contenedor_ok": {
        "es": "Están las tres partes que Power BI exige (Version, [Content_Types].xml, DataModelSchema); {n} partes en total.",
        "en": "All three parts Power BI requires are present (Version, [Content_Types].xml, DataModelSchema); {n} parts in total.",
        "pt": "Estão as três partes que o Power BI exige (Version, [Content_Types].xml, DataModelSchema); {n} partes no total.",
    },
    "vf_contenedor_falta": {
        "es": "Faltan partes obligatorias: {partes}. Power BI abre sin modelo o rechaza el archivo.",
        "en": "Required parts are missing: {partes}. Power BI opens with no model or rejects the file.",
        "pt": "Faltam partes obrigatórias: {partes}. O Power BI abre sem modelo ou rejeita o arquivo.",
    },

    "vf_contenedor_pbip": {"es": "Estructura del proyecto",
                           "en": "Project structure",
                           "pt": "Estrutura do projeto"},
    "vf_contenedor_pbip_ok": {
        "es": "Proyecto PBIP con el modelo en {bim}; {n} archivos en total.",
        "en": "PBIP project with the model in {bim}; {n} files in total.",
        "pt": "Projeto PBIP com o modelo em {bim}; {n} arquivos no total.",
    },

    "vf_content_types": {"es": "Declaración de partes",
                         "en": "Part declaration",
                         "pt": "Declaração de partes"},
    "vf_content_types_ok": {
        "es": "El [Content_Types].xml declara exactamente lo que hay adentro.",
        "en": "[Content_Types].xml declares exactly what is inside.",
        "pt": "O [Content_Types].xml declara exatamente o que está dentro.",
    },
    "vf_content_types_falta": {
        "es": "Declaración incoherente — declaradas y ausentes: {sobran}; escritas sin declarar: {faltan}. Es la causa clásica de «este archivo está dañado».",
        "en": "Inconsistent declaration — declared but absent: {sobran}; written but undeclared: {faltan}. This is the classic cause of \"this file is corrupt\".",
        "pt": "Declaração incoerente — declaradas e ausentes: {sobran}; escritas sem declarar: {faltan}. É a causa clássica de «este arquivo está danificado».",
    },

    "vf_esquema": {"es": "Lectura del modelo", "en": "Model read",
                   "pt": "Leitura do modelo"},
    "vf_esquema_falta": {
        "es": "El DataModelSchema no se pudo leer ({motivo}). Tiene que ser JSON en UTF-16LE.",
        "en": "DataModelSchema could not be read ({motivo}). It must be JSON in UTF-16LE.",
        "pt": "O DataModelSchema não se conseguiu ler ({motivo}). Tem de ser JSON em UTF-16LE.",
    },

    "vf_modelo": {"es": "Modelo de datos", "en": "Data model",
                  "pt": "Modelo de dados"},
    "vf_modelo_ok": {
        "es": "{tablas} tablas y {relaciones} relaciones dentro del archivo.",
        "en": "{tablas} tables and {relaciones} relationships inside the file.",
        "pt": "{tablas} tabelas e {relaciones} relações dentro do arquivo.",
    },
    "vf_modelo_falta": {
        "es": "El archivo no lleva ninguna tabla: se abre vacío.",
        "en": "The file carries no tables at all: it opens empty.",
        "pt": "O arquivo não leva nenhuma tabela: abre vazio.",
    },

    "vf_compatibilidad": {"es": "Formato que Desktop sabe leer",
                          "en": "Format Desktop can read",
                          "pt": "Formato que o Desktop sabe ler"},
    "vf_compatibilidad_ok": {
        "es": "{version} con nivel de compatibilidad {nivel}: Desktop lee el Power Query desde las particiones del modelo.",
        "en": "{version} with compatibility level {nivel}: Desktop reads Power Query from the model partitions.",
        "pt": "{version} com nível de compatibilidade {nivel}: o Desktop lê o Power Query a partir das partições do modelo.",
    },
    "vf_compatibilidad_falta": {
        "es": "Combinación inválida: {version} con nivel {nivel} (mínimo {minimo}). Sin powerBI_V3 Desktop busca el Power Query en un binario que no está y descarta el modelo; con el flag pero con nivel viejo, rechaza el archivo como dañado.",
        "en": "Invalid combination: {version} at level {nivel} (minimum {minimo}). Without powerBI_V3, Desktop looks for Power Query in a binary that is not there and discards the model; with the flag but an old level, it rejects the file as corrupt.",
        "pt": "Combinação inválida: {version} com nível {nivel} (mínimo {minimo}). Sem powerBI_V3 o Desktop procura o Power Query num binário que não existe e descarta o modelo; com a flag mas com nível antigo, rejeita o arquivo como danificado.",
    },

    "vf_version_formato": {"es": "Versión y formato del reporte",
                           "en": "Container version vs report format",
                           "pt": "Versão e formato do relatório"},
    "vf_version_formato_ok": {
        "es": "Versión {version} con reporte en formato {formato}: el par que Desktop espera.",
        "en": "Version {version} with the report in {formato} format: the pair Desktop expects.",
        "pt": "Versão {version} com relatório em formato {formato}: o par que o Desktop espera.",
    },
    "vf_version_formato_falta": {
        "es": "Versión {version} con el reporte en formato {formato}, que corresponde a la {esperada}. Cruzar el par hace que Desktop rechace el archivo con «está dañado o se ha creado con una versión no reconocida».",
        "en": "Version {version} with the report in {formato} format, which belongs to {esperada}. Crossing the pair makes Desktop reject the file with \"corrupt or created with an unrecognised version\".",
        "pt": "Versão {version} com o relatório em formato {formato}, que corresponde à {esperada}. Cruzar o par faz o Desktop rejeitar o arquivo com «está danificado ou foi criado com uma versão não reconhecida».",
    },

    "vf_conexion": {"es": "Origen de cada tabla", "en": "Each table's source",
                    "pt": "Origem de cada tabela"},
    "vf_conexion_ok": {
        "es": "Todas las tablas tienen de dónde traer los datos ({detalle}).",
        "en": "Every table has somewhere to pull data from ({detalle}).",
        "pt": "Todas as tabelas têm de onde trazer os dados ({detalle}).",
    },
    "vf_conexion_falta": {
        "es": "Sin origen de datos: {sin_origen}. Esas tablas abren vacías y no hay forma de refrescarlas.",
        "en": "No data source: {sin_origen}. Those tables open empty and there is no way to refresh them.",
        "pt": "Sem origem de dados: {sin_origen}. Essas tabelas abrem vazias e não há forma de as atualizar.",
    },

    "vf_autonomo": {"es": "¿Abre solo?", "en": "Opens standalone?",
                    "pt": "Abre sozinho?"},
    "vf_autonomo_ok": {
        "es": "Sí: las {embebidas} tablas llevan los datos adentro del archivo. Abre en cualquier máquina sin copiar nada al lado.",
        "en": "Yes: all {embebidas} tables carry their data inside the file. It opens on any machine with nothing copied alongside.",
        "pt": "Sim: as {embebidas} tabelas levam os dados dentro do arquivo. Abre em qualquer máquina sem copiar nada ao lado.",
    },
    "vf_autonomo_aviso": {
        "es": "{afuera} tablas leen de afuera ({lista}) y {embebidas} llevan los datos adentro. Las de afuera necesitan que el origen esté disponible en la máquina que abre el archivo.",
        "en": "{afuera} tables read from outside ({lista}) and {embebidas} carry their data inside. The external ones need the source available on the machine opening the file.",
        "pt": "{afuera} tabelas leem de fora ({lista}) e {embebidas} levam os dados dentro. As de fora precisam que a origem esteja disponível na máquina que abre o arquivo.",
    },

    "vf_rutas": {"es": "Rutas escritas en la consulta",
                 "en": "Paths written into the query",
                 "pt": "Caminhos escritos na consulta"},
    "vf_rutas_aviso": {
        "es": "{n} rutas absolutas dentro del Power Query ({lista}); {faltan} no existen en esta máquina. Andan donde se generaron: si el archivo cambia de carpeta o de PC hay que reapuntarlas, o exportar con la carpeta como parámetro para que el archivo la pregunte al abrirse.",
        "en": "{n} absolute paths inside Power Query ({lista}); {faltan} do not exist on this machine. They work where they were generated: if the file moves folder or PC they must be repointed, or export with the folder as a parameter so the file asks for it on open.",
        "pt": "{n} caminhos absolutos dentro do Power Query ({lista}); {faltan} não existem nesta máquina. Funcionam onde foram gerados: se o arquivo mudar de pasta ou de PC há que reapontá-los, ou exportar com a pasta como parâmetro para que o arquivo a pergunte ao abrir.",
    },

    "vf_columnas": {"es": "Columnas declaradas vs. producidas",
                    "en": "Declared vs. produced columns",
                    "pt": "Colunas declaradas vs. produzidas"},
    "vf_columnas_ok": {
        "es": "Cada columna que el modelo declara es una que la consulta devuelve.",
        "en": "Every column the model declares is one the query returns.",
        "pt": "Cada coluna que o modelo declara é uma que a consulta devolve.",
    },
    "vf_columnas_falta": {
        "es": "{n} columnas declaradas que la consulta no produce ({lista}). El archivo abre, pero esas tablas quedan en error al refrescar.",
        "en": "{n} declared columns the query does not produce ({lista}). The file opens, but those tables error out on refresh.",
        "pt": "{n} colunas declaradas que a consulta não produz ({lista}). O arquivo abre, mas essas tabelas ficam em erro ao atualizar.",
    },

    "vf_powerquery": {"es": "Sintaxis del Power Query",
                      "en": "Power Query syntax",
                      "pt": "Sintaxe do Power Query"},
    "vf_powerquery_ok": {
        "es": "Las {consultas} consultas M están bien formadas.",
        "en": "All {consultas} M queries are well formed.",
        "pt": "As {consultas} consultas M estão bem formadas.",
    },
    "vf_powerquery_falta": {
        "es": "{n} consultas M con errores de sintaxis ({lista}). El motor de Power Query las rechaza al abrir y la tabla no carga.",
        "en": "{n} M queries with syntax errors ({lista}). The Power Query engine rejects them on open and the table does not load.",
        "pt": "{n} consultas M com erros de sintaxe ({lista}). O motor do Power Query rejeita-as ao abrir e a tabela não carrega.",
    },

    "vf_dax": {"es": "DAX del archivo", "en": "DAX in the file",
               "pt": "DAX do arquivo"},
    "vf_dax_ok": {
        "es": "{medidas} medidas y todas referencian tablas, columnas y medidas que existen.",
        "en": "{medidas} measures, all referencing tables, columns and measures that exist.",
        "pt": "{medidas} medidas e todas referenciam tabelas, colunas e medidas que existem.",
    },
    "vf_dax_falta": {
        "es": "{rotas} de {medidas} medidas referencian algo que no está en el modelo ({lista}).",
        "en": "{rotas} of {medidas} measures reference something not in the model ({lista}).",
        "pt": "{rotas} de {medidas} medidas referenciam algo que não está no modelo ({lista}).",
    },

    "vf_formatos": {"es": "Formato de las medidas", "en": "Measure formatting",
                    "pt": "Formato das medidas"},
    "vf_formatos_ok": {
        "es": "Todas las medidas tienen formato definido.",
        "en": "Every measure has a format string.",
        "pt": "Todas as medidas têm formato definido.",
    },
    "vf_formatos_aviso": {
        "es": "{n} medidas sin formato ({lista}): se ven con los decimales crudos.",
        "en": "{n} measures without a format ({lista}): they show raw decimals.",
        "pt": "{n} medidas sem formato ({lista}): veem-se com os decimais crus.",
    },

    "vf_relaciones": {"es": "Modelado", "en": "Modelling", "pt": "Modelação"},
    "vf_relaciones_ok": {
        "es": "{n} relaciones entre las {tablas} tablas visibles.",
        "en": "{n} relationships across the {tablas} visible tables.",
        "pt": "{n} relações entre as {tablas} tabelas visíveis.",
    },
    "vf_relaciones_falta": {
        "es": "{tablas} tablas visibles y ninguna relación: cada visual filtra solo su propia tabla y los cruces dan cualquier cosa.",
        "en": "{tablas} visible tables and no relationships: each visual filters only its own table and any cross-table figure is meaningless.",
        "pt": "{tablas} tabelas visíveis e nenhuma relação: cada visual filtra apenas a sua tabela e os cruzamentos dão qualquer coisa.",
    },

    "vf_nombres": {"es": "Nombres del modelo",
                   "en": "Model names", "pt": "Nomes do modelo"},
    "vf_nombres_ok": {
        "es": "Las {tablas} tablas y sus {medidas} medidas no repiten nombres, y cada orden y cada jerarquía apuntan a una columna que existe.",
        "en": "The {tablas} tables and their {medidas} measures repeat no names, and every sort order and hierarchy points at a column that exists.",
        "pt": "As {tablas} tabelas e as suas {medidas} medidas não repetem nomes, e cada ordem e cada hierarquia apontam para uma coluna que existe.",
    },
    "vf_nombres_falta": {
        "es": "{n} problemas de nombres ({lista}). Desktop los rechaza al abrir, y el DAX puede estar impecable: no es la fórmula, es cómo el modelo se nombra a sí mismo.",
        "en": "{n} naming problems ({lista}). Desktop rejects them on open, and the DAX may be flawless: it is not the formula, it is how the model names itself.",
        "pt": "{n} problemas de nomes ({lista}). O Desktop rejeita-os ao abrir, e o DAX pode estar impecável: não é a fórmula, é como o modelo se nomeia a si próprio.",
    },
    "vf_nom_col_repetida": {
        "es": "{tabla} tiene dos columnas «{columna}»",
        "en": "{tabla} has two «{columna}» columns",
        "pt": "{tabla} tem duas colunas «{columna}»",
    },
    "vf_nom_medida": {
        "es": "la medida «{medida}» está definida {n} veces",
        "en": "measure «{medida}» is defined {n} times",
        "pt": "a medida «{medida}» está definida {n} vezes",
    },
    "vf_nom_orden": {
        "es": "{tabla}[{columna}] ordena por «{orden}», que no existe",
        "en": "{tabla}[{columna}] sorts by «{orden}», which does not exist",
        "pt": "{tabla}[{columna}] ordena por «{orden}», que não existe",
    },
    "vf_nom_jerarquia": {
        "es": "la jerarquía «{jerarquia}» de {tabla} usa la columna «{columna}», que no existe",
        "en": "hierarchy «{jerarquia}» in {tabla} uses column «{columna}», which does not exist",
        "pt": "a hierarquia «{jerarquia}» de {tabla} usa a coluna «{columna}», que não existe",
    },

    "vf_integridad": {"es": "Relaciones que Power BI puede crear",
                      "en": "Relationships Power BI can create",
                      "pt": "Relações que o Power BI pode criar"},
    "vf_integridad_ok": {
        "es": "Las {total} relaciones tienen sus dos extremos, tipos que coinciden, el lado uno único y sin blancos, y el filtro no da la vuelta en círculo.",
        "en": "All {total} relationships have both endpoints, matching types, a unique and blank-free one side, and the filter cannot loop back around.",
        "pt": "As {total} relações têm os dois extremos, tipos que coincidem, o lado um único e sem brancos, e o filtro não dá a volta em círculo.",
    },
    "vf_integridad_falta": {
        "es": "{n} de {total} relaciones no se pueden crear: {lista}. Power BI no carga el modelo y el archivo abre sin datos.",
        "en": "{n} of {total} relationships cannot be created: {lista}. Power BI will not load the model and the file opens with no data.",
        "pt": "{n} de {total} relações não se podem criar: {lista}. O Power BI não carrega o modelo e o arquivo abre sem dados.",
    },
    "vf_rel_extremo": {
        "es": "{rel}: {lado} no existe",
        "en": "{rel}: {lado} does not exist",
        "pt": "{rel}: {lado} não existe",
    },
    "vf_rel_tipos": {
        "es": "{rel}: tipos distintos ({uno} vs {otro})",
        "en": "{rel}: different types ({uno} vs {otro})",
        "pt": "{rel}: tipos diferentes ({uno} vs {otro})",
    },
    "vf_rel_repetido": {
        "es": "{rel}: el lado uno repite el valor {valor}",
        "en": "{rel}: the one side repeats the value {valor}",
        "pt": "{rel}: o lado um repete o valor {valor}",
    },
    "vf_rel_vacio": {
        "es": "{rel}: el lado uno tiene {n} valores vacíos",
        "en": "{rel}: the one side has {n} blank values",
        "pt": "{rel}: o lado um tem {n} valores vazios",
    },
    "vf_rel_dobles": {
        "es": "{a} ↔ {b}: {n} relaciones activas entre las mismas tablas",
        "en": "{a} ↔ {b}: {n} active relationships between the same tables",
        "pt": "{a} ↔ {b}: {n} relações ativas entre as mesmas tabelas",
    },
    "vf_rel_ciclo": {
        "es": "el filtro vuelve al punto de partida ({camino})",
        "en": "the filter comes back to where it started ({camino})",
        "pt": "o filtro volta ao ponto de partida ({camino})",
    },

    "vf_tipos": {"es": "Datos contra el tipo declarado",
                 "en": "Data against the declared type",
                 "pt": "Dados contra o tipo declarado"},
    "vf_tipos_ok": {
        "es": "Cada valor de las {tablas} tablas con datos adentro se convierte al tipo que el modelo declara.",
        "en": "Every value across the {tablas} tables carrying data converts to the type the model declares.",
        "pt": "Cada valor das {tablas} tabelas com dados dentro converte-se ao tipo que o modelo declara.",
    },
    "vf_tipos_falta": {
        "es": "{n} columnas traen valores que no se convierten al tipo declarado ({lista}). No falla al abrir: falla al refrescar, y la tabla queda en error con el resto del modelo aparentando estar bien.",
        "en": "{n} columns carry values that do not convert to the declared type ({lista}). It does not fail on open: it fails on refresh, leaving the table in error while the rest of the model looks fine.",
        "pt": "{n} colunas trazem valores que não se convertem ao tipo declarado ({lista}). Não falha ao abrir: falha ao atualizar, e a tabela fica em erro com o resto do modelo a parecer bem.",
    },

    "vf_filtros": {"es": "Campos que usan los filtros",
                   "en": "Fields the filters use",
                   "pt": "Campos que os filtros usam"},
    "vf_filtros_ok": {
        "es": "Los {total} filtros del reporte apuntan a campos que existen.",
        "en": "All {total} report filters point at fields that exist.",
        "pt": "Os {total} filtros do relatório apontam para campos que existem.",
    },
    "vf_filtros_falta": {
        "es": "{n} filtros apuntan a campos que el modelo no tiene ({lista}). Un filtro roto no se ve: el visual dibuja igual, con otros números.",
        "en": "{n} filters point at fields the model does not have ({lista}). A broken filter is invisible: the visual still draws, with different numbers.",
        "pt": "{n} filtros apontam para campos que o modelo não tem ({lista}). Um filtro partido não se vê: o visual desenha do mesmo jeito, com outros números.",
    },

    # ======================================================================
    # Bitácora del pipeline — cada etapa contada dos veces
    # ======================================================================
    # El mismo hecho, en técnico y en criollo. No es redundancia: son dos
    # lectores distintos y ninguno de los dos lee bien el texto del otro.
    # El que mantiene el modelo necesita el nombre exacto de la propiedad
    # TMSL; el que firma necesita saber qué pasa si eso no está.
    # ======================================================================
    # Las dos formas de instalarlo
    # ======================================================================
    # El modo se muestra siempre: sin esta línea, «no me aparece el buscador
    # de archivos» es un misterio en vez de una respuesta de un renglón.
    "ent_modo_escritorio": {
        "es": "Instalación de escritorio · todo disponible",
        "en": "Desktop install · everything available",
        # «secretária» es la MESA, no la computadora: «instalação de
        # secretária» se lee «instalación de escritorio-mueble». El término
        # que se entiende en las dos variantes del portugués es «desktop».
        "pt": "Instalação de desktop · tudo disponível",
    },
    # ---- login opcional (dxl/auth.py) ---------------------------------
    "auth_titulo": {"es": "Entrar", "en": "Sign in", "pt": "Entrar"},
    "auth_intro": {
        "es": "Esta instalación pide usuario y contraseña porque corre en un servidor, al alcance de una red.",
        "en": "This install asks for a username and password because it runs on a server, reachable from a network.",
        "pt": "Esta instalação pede usuário e senha porque roda num servidor, ao alcance de uma rede.",
    },
    "auth_usuario": {"es": "Usuario", "en": "Username", "pt": "Usuário"},
    "auth_clave": {"es": "Contraseña", "en": "Password", "pt": "Senha"},
    "auth_entrar": {"es": "Entrar", "en": "Sign in", "pt": "Entrar"},
    # Un solo mensaje para «no existe» y «contraseña mala»: distinguirlos
    # regala la mitad de la credencial.
    "auth_mal": {
        "es": "Usuario o contraseña incorrectos.",
        "en": "Incorrect username or password.",
        "pt": "Usuário ou senha incorretos.",
    },
    "auth_bloqueado": {
        "es": "Demasiados intentos fallidos. Probá de nuevo en {segundos} segundos.",
        "en": "Too many failed attempts. Try again in {segundos} seconds.",
        "pt": "Tentativas falhas demais. Tente de novo em {segundos} segundos.",
    },
    "auth_como": {"es": "Entraste como {usuario}",
                  "en": "Signed in as {usuario}",
                  "pt": "Você entrou como {usuario}"},
    "auth_salir": {"es": "Cerrar sesión", "en": "Sign out", "pt": "Sair"},
    "auth_desprotegido": {
        "es": "Servidor SIN login: cualquiera que alcance esta URL entra, sube datos y baja archivos. Declará usuarios en MVDAX_USUARIOS (generá la línea con «python -m dxl.auth <nombre>») o dejá la app detrás del proxy/SSO del cliente.",
        "en": "Server with NO login: anyone who can reach this URL gets in, uploads data and downloads files. Declare users in MVDAX_USUARIOS (generate the line with «python -m dxl.auth <name>») or keep the app behind the client's proxy/SSO.",
        "pt": "Servidor SEM login: qualquer um que alcance esta URL entra, sobe dados e baixa arquivos. Declare usuários em MVDAX_USUARIOS (gere a linha com «python -m dxl.auth <nome>») ou deixe o app atrás do proxy/SSO do cliente.",
    },
    "ent_modo_servidor": {
        "es": "Instalación en servidor · las 3 funciones de máquina local están apagadas",
        "en": "Server install · the 3 local-machine features are off",
        "pt": "Instalação em servidor · as 3 funções de máquina local estão desligadas",
    },
    "ent_sin_buscador": {
        "es": "Instalado en un servidor, este buscador recorrería el disco DEL SERVIDOR y no el tuyo: es otra función, no la misma con menos alcance. Subí los archivos con el cargador de acá arriba, que además es lo que corresponde desde un navegador.",
        "en": "On a server install this search would walk the SERVER's disk, not yours: a different feature, not the same one with less reach. Use the uploader above, which is what a browser should do anyway.",
        "pt": "Instalado num servidor, este localizador percorreria o disco DO SERVIDOR e não o seu: é outra função, não a mesma com menos alcance. Carregue os arquivos com o carregador acima, que é o que corresponde a partir de um navegador.",
    },
    "ent_sin_deteccion": {
        "es": "El semáforo de «instalada» mira la máquina donde corre el programa, y acá es un servidor: no hay ningún Power BI Desktop que detectar. Todo lo demás de esta pestaña —exportar el modelo en el formato que cada herramienta abre— funciona igual.",
        "en": "The «installed» indicator looks at the machine running the program, and here that is a server: there is no Power BI Desktop to detect. Everything else on this tab — exporting the model in the format each tool opens — works the same.",
        "pt": "O semáforo de «instalada» olha para a máquina onde o programa roda, e aqui é um servidor: não há nenhum Power BI Desktop para detectar. Todo o resto desta aba — exportar o modelo no formato que cada ferramenta abre — funciona igual.",
    },
    "ent_sin_overlay": {
        "es": "El overlay engancha el teclado de la máquina donde corre el programa. En un servidor no hay teclado que escuchar: esto se usa con la instalación de escritorio.",
        "en": "The overlay hooks the keyboard of the machine running the program. On a server there is no keyboard to listen to: this one is for the desktop install.",
        "pt": "O overlay se conecta ao teclado da máquina onde o programa roda. Num servidor não há teclado para escutar: isto se usa com a instalação de desktop.",
    },
    # ======================================================================
    # Frescura — hasta cuándo llegan los datos de cada tabla
    # ======================================================================
    "tab_frescura": {"es": "Frescura", "en": "Freshness",
                     "pt": "Frescura"},
    "fr_titulo": {"es": "Frescura de los datos",
                  "en": "Data freshness", "pt": "Frescura dos dados"},
    "fr_bajada": {
        "es": "Hasta cuándo llegan los datos de cada tabla, cada cuánto se actualizan y cuáles están atrasadas. Antes de discutir un número conviene saber si el dato que lo alimenta está al día.",
        "en": "How far the data of each table goes, how often it refreshes, and which ones are stale. Before arguing about a number it helps to know whether the data behind it is current.",
        "pt": "Até quando chegam os dados de cada tabela, de quanto em quanto tempo se atualizam e quais estão atrasadas. Antes de discutir um número convém saber se o dado que o alimenta está em dia.",
    },
    # Nota de idioma: el portugués de este archivo es mayoritariamente
    # brasileño («arquivo», «usuário», «tela», «aba»). Estas claves salieron
    # en portugués europeo y se alinearon: mezclar las dos variantes en la
    # misma pantalla se lee como una traducción automática.
    "fr_intro": {
        "es": "Una fila por tabla. La «fecha de los datos» se mide sobre las filas que el archivo trae adentro; la cadencia se deduce de las fechas que ya tiene, no de una promesa del proceso.",
        "en": "One row per table. The «data date» is measured on the rows the file carries inside; the cadence is inferred from the dates already present, not from a promise about the process.",
        "pt": "Uma linha por tabela. A «data dos dados» se mede sobre as linhas que o arquivo traz dentro; a cadência se deduz das datas que ele já tem, não de uma promessa do processo.",
    },
    "fr_c_tabla": {"es": "Tabla", "en": "Table", "pt": "Tabela"},
    "fr_c_filas": {"es": "Filas", "en": "Rows", "pt": "Linhas"},
    "fr_c_datos": {"es": "Datos hasta", "en": "Data through",
                   "pt": "Dados até"},
    "fr_c_cadencia": {"es": "Cadencia", "en": "Cadence", "pt": "Cadência"},
    "fr_c_dias": {"es": "Días de atraso", "en": "Days behind",
                  "pt": "Dias de atraso"},
    "fr_c_estado": {"es": "Estado", "en": "Status", "pt": "Estado"},
    "fr_c_hoy": {"es": "Medido el", "en": "Measured on", "pt": "Medido em"},
    "fr_c_carga": {"es": "Archivo escrito el", "en": "File written on",
                   "pt": "Arquivo escrito em"},
    "fr_al_dia": {"es": "Tablas al día", "en": "Tables up to date",
                  "pt": "Tabelas em dia"},
    "fr_atrasadas": {"es": "Tablas atrasadas", "en": "Stale tables",
                     "pt": "Tabelas atrasadas"},
    "fr_estado_al_dia": {"es": "Al día", "en": "Up to date", "pt": "Em dia"},
    "fr_estado_atrasada": {"es": "Atrasada", "en": "Stale",
                           "pt": "Atrasada"},
    "fr_estado_parcial": {
        "es": "Tabla grande: solo se leyó una parte, no se afirma la fecha",
        "en": "Large table: only part was read, the date is not asserted",
        "pt": "Tabela grande: só se leu uma parte, a data não se afirma"},
    "fr_estado_sin_fecha": {"es": "Sin columna de fecha utilizable",
                            "en": "No usable date column",
                            "pt": "Sem coluna de data utilizável"},
    "fr_estado_sin_datos": {"es": "Sin filas adentro para medir",
                            "en": "No rows inside to measure",
                            "pt": "Sem linhas dentro para medir"},
    "fr_cad_diaria": {"es": "diaria", "en": "daily", "pt": "diária"},
    "fr_cad_semanal": {"es": "semanal", "en": "weekly", "pt": "semanal"},
    "fr_cad_quincenal": {"es": "quincenal", "en": "fortnightly",
                         "pt": "quinzenal"},
    "fr_cad_mensual": {"es": "mensual", "en": "monthly", "pt": "mensal"},
    "fr_cad_trimestral": {"es": "trimestral", "en": "quarterly",
                          "pt": "trimestral"},
    "fr_peor": {"es": "La que manda", "en": "The one that governs",
                "pt": "A que manda"},
    "fr_peor_detalle": {
        "es": "«{tabla}» llega hasta {fecha} ({dias} días). Un tablero es tan fresco como su peor fuente: promediar la antigüedad esconde justo la que hay que mirar.",
        "en": "«{tabla}» goes through {fecha} ({dias} days). A report is only as fresh as its worst source: averaging the age hides exactly the one to look at.",
        "pt": "«{tabla}» chega até {fecha} ({dias} dias). Um painel é tão fresco quanto a sua pior fonte: tirar a média da antiguidade esconde justamente a que é preciso olhar.",
    },
    "fr_honestidad_t": {"es": "Qué se mide y qué no",
                        "en": "What is measured and what is not",
                        "pt": "O que se mede e o que não"},
    "fr_honestidad": {
        "es": "Un .pbit NO guarda cuándo se refrescó cada tabla: en un modelo de importación ese dato vive en el workspace, no en el archivo. Por eso acá se separan la fecha de los DATOS (medida sobre las filas) de la fecha en que se escribió el ARCHIVO. Lo que no se puede saber, la fila lo dice.",
        "en": "A .pbit does NOT record when each table was refreshed: in an import model that lives in the workspace, not in the file. So the DATA date (measured on the rows) is kept apart from the date the FILE was written. Whatever cannot be known, the row says so.",
        "pt": "Um .pbit NÃO guarda quando cada tabela foi atualizada: num modelo de importação esse dado vive na área de trabalho, não no arquivo. Por isso aqui se separa a data dos DADOS (medida sobre as linhas) da data em que o ARQUIVO foi escrito. O que não se pode saber, a linha diz.",
    },
    "fr_sin_medibles": {
        "es": "Ninguna tabla trae filas adentro para medir. Cargá un dataset o exportá con los datos empotrados, y este panel se llena solo.",
        "en": "No table carries rows inside to measure. Load a dataset or export with the data embedded, and this panel fills itself.",
        "pt": "Nenhuma tabela traz linhas dentro para medir. Carregue um dataset ou exporte com os dados embutidos, e este painel se preenche sozinho.",
    },
    "fr_descargar": {"es": "Descargar el panel",
                     "en": "Download the panel",
                     "pt": "Baixar o painel"},
    "fr_doc_titulo": {"es": "Frescura de los datos · MV DAX Lab",
                      "en": "Data freshness · MV DAX Lab",
                      "pt": "Frescura dos dados · MV DAX Lab"},
    "tab_bitacora": {"es": "Bitácora", "en": "Log", "pt": "Registro"},
    "bi_titulo": {"es": "Bitácora del pipeline",
                  "en": "Pipeline log", "pt": "Registro do pipeline"},
    "bi_bajada": {
        "es": "Qué se le hizo al dataset, en orden, en técnico y en criollo — para el que mantiene el modelo y para el que firma.",
        "en": "What was done to the dataset, in order, in technical and in plain terms — for whoever maintains the model and for whoever signs off.",
        "pt": "O que se fez ao dataset, por ordem, em técnico e em linguagem simples — para quem mantém o modelo e para quem assina.",
    },
    "bi_descargar": {"es": "Descargar el documento",
                     "en": "Download the document",
                     "pt": "Baixar o documento"},
    "bi_doc_titulo": {"es": "Bitácora del pipeline · MV DAX Lab",
                      "en": "Pipeline log · MV DAX Lab",
                      "pt": "Registro do pipeline · MV DAX Lab"},
    "bit_intro": {
        "es": "Cada etapa del pipeline, en el orden en que ocurre, contada en técnico y en criollo. El estado NO se asume: se mide sobre el modelo entregado, así que una etapa que no se aplicó aparece como no aplicada.",
        "en": "Every stage of the pipeline, in the order it happens, told in technical and in plain terms. Status is NOT assumed: it is measured on the delivered model, so a stage that did not run shows as not applied.",
        "pt": "Cada etapa do pipeline, na ordem em que ocorre, contada em técnico e em linguagem simples. O estado NÃO se assume: mede-se sobre o modelo entregue, portanto uma etapa que não correu aparece como não aplicada.",
    },
    "bit_mapa": {"es": "Mapa del pipeline", "en": "Pipeline map",
                 "pt": "Mapa do pipeline"},
    "bit_historial": {"es": "Lo que se tocó en esta sesión",
                      "en": "What was changed in this session",
                      "pt": "O que se mexeu nesta sessão"},
    "bit_historial_intro": {
        "es": "Los cambios que se aplicaron de verdad en esta corrida, en orden. Va aparte de las etapas a propósito: las etapas explican el pipeline, esto dice qué se tocó hoy.",
        "en": "The changes actually applied in this run, in order. Kept apart from the stages on purpose: the stages explain the pipeline, this says what was touched today.",
        "pt": "As alterações realmente aplicadas nesta execução, por ordem. Fica à parte das etapas de propósito: as etapas explicam o pipeline, isto diz o que se mexeu hoje.",
    },
    "bit_r_etapas": {"es": "Etapas aplicadas", "en": "Stages applied",
                     "pt": "Etapas aplicadas"},
    "bit_r_tablas": {"es": "Tablas", "en": "Tables", "pt": "Tabelas"},
    "bit_r_medidas": {"es": "Medidas", "en": "Measures", "pt": "Medidas"},
    "bit_r_relaciones": {"es": "Relaciones", "en": "Relationships",
                         "pt": "Relações"},
    "bit_r_paginas": {"es": "Páginas del tablero", "en": "Report pages",
                      "pt": "Páginas do painel"},
    "bit_c_paso": {"es": "Paso", "en": "Step", "pt": "Passo"},
    "bit_c_etapa": {"es": "Etapa", "en": "Stage", "pt": "Etapa"},
    "bit_c_estado": {"es": "Estado", "en": "Status", "pt": "Estado"},
    "bit_c_evidencia": {"es": "Evidencia", "en": "Evidence",
                        "pt": "Evidência"},
    "bit_c_modulos": {"es": "Dónde vive", "en": "Where it lives",
                      "pt": "Onde vive"},
    "bit_h_tecnico": {"es": "En técnico", "en": "In technical terms",
                      "pt": "Em técnico"},
    "bit_h_criollo": {"es": "En criollo", "en": "In plain terms",
                      "pt": "Em linguagem simples"},
    "bit_h_porque": {"es": "Por qué se hace", "en": "Why it is done",
                     "pt": "Porque se faz"},
    "bit_h_impacto": {"es": "Cómo repercute", "en": "How it ripples through",
                      "pt": "Como repercute"},
    "bit_estado_aplicada": {"es": "Aplicada", "en": "Applied",
                            "pt": "Aplicada"},
    "bit_estado_sin_aplicar": {"es": "No aplicada", "en": "Not applied",
                               "pt": "Não aplicada"},
    "bit_estado_sin_datos": {"es": "Sin datos para juzgar",
                             "en": "No data to judge",
                             "pt": "Sem dados para julgar"},

    # ---- 1 · origen ----
    "bit_origen_titulo": {"es": "Lectura del origen",
                          "en": "Reading the source", "pt": "Leitura da origem"},
    "bit_origen_tec": {
        "es": "Lee CSV, Excel, SQL, .pbit o .pbix y propone un modelo tabular: una tabla por hoja o consulta, con sus columnas. El origen de cada tabla queda escrito en la expresión M de su partición.",
        "en": "Reads CSV, Excel, SQL, .pbit or .pbix and proposes a tabular model: one table per sheet or query, with its columns. Each table's source is written into its partition's M expression.",
        "pt": "Lê CSV, Excel, SQL, .pbit ou .pbix e propõe um modelo tabular: uma tabela por folha ou consulta, com as suas colunas. A origem de cada tabela fica escrita na expressão M da sua partição.",
    },
    "bit_origen_criollo": {
        "es": "Se abre el archivo que trajiste y se arma la estructura de tablas. Nada más: todavía no se calcula ningún número.",
        "en": "The file you brought is opened and the table structure is built. Nothing else yet: no number is calculated at this point.",
        "pt": "Abre-se o arquivo que trouxeste e monta-se a estrutura de tabelas. Mais nada: ainda não se calcula nenhum número.",
    },
    "bit_origen_porque": {
        "es": "Todo lo que sigue se apoya en esta lectura. Si acá se entiende mal una hoja, el error viaja hasta el tablero y recién aparece al final, cuando ya cuesta caro.",
        "en": "Everything downstream rests on this reading. Misread a sheet here and the error travels all the way to the report, surfacing only at the end, when it is expensive.",
        "pt": "Tudo o que se segue assenta nesta leitura. Se aqui se entende mal uma folha, o erro viaja até ao painel e só aparece no fim, quando já sai caro.",
    },
    "bit_origen_impacto": {
        "es": "Define cuántas tablas hay y de dónde saca las filas cada una.",
        "en": "Determines how many tables there are and where each one gets its rows.",
        "pt": "Define quantas tabelas existem e de onde cada uma tira as linhas.",
    },
    "bit_origen_ev": {"es": "{0} tablas · orígenes: {1}",
                      "en": "{0} tables · sources: {1}",
                      "pt": "{0} tabelas · origens: {1}"},

    # ---- 2 · perfilado ----
    "bit_perfilado_titulo": {"es": "Tipos y formatos", "en": "Types and formats",
                             "pt": "Tipos e formatos"},
    "bit_perfilado_tec": {
        "es": "Infiere el tipo de cada columna (texto, entero, decimal, fecha) y le asigna su `formatString`.",
        "en": "Infers each column's data type (text, integer, decimal, date) and assigns its `formatString`.",
        "pt": "Infere o tipo de cada coluna (texto, inteiro, decimal, data) e atribui o seu `formatString`.",
    },
    "bit_perfilado_criollo": {
        "es": "Se decide si cada columna es número, texto o fecha, y cómo se muestra. Es lo que hace que un importe se vea como $ 1.234 y no como 1234.0.",
        "en": "It is decided whether each column is a number, text or a date, and how it is displayed. It is what makes an amount read as $1,234 instead of 1234.0.",
        "pt": "Decide-se se cada coluna é número, texto ou data, e como se mostra. É o que faz um valor aparecer como 1.234 € e não como 1234.0.",
    },
    "bit_perfilado_porque": {
        "es": "Power BI no suma texto ni compara períodos sobre una fecha guardada como cadena. Sin esto el modelo abre y no calcula.",
        "en": "Power BI cannot sum text nor compare periods over a date stored as a string. Without this the model opens and does not compute.",
        "pt": "O Power BI não soma texto nem compara períodos sobre uma data guardada como cadeia. Sem isto o modelo abre e não calcula.",
    },
    "bit_perfilado_impacto": {
        "es": "Habilita las sumas, los promedios y toda la inteligencia de tiempo.",
        "en": "Enables sums, averages and the whole of time intelligence.",
        "pt": "Habilita as somas, as médias e toda a inteligência de tempo.",
    },
    "bit_perfilado_ev": {"es": "{0} columnas tipadas · {1} con formato",
                         "en": "{0} typed columns · {1} formatted",
                         "pt": "{0} colunas tipadas · {1} com formato"},

    # ---- 3 · relaciones ----
    "bit_relaciones_titulo": {"es": "Relaciones entre tablas",
                              "en": "Relationships", "pt": "Relações"},
    "bit_relaciones_tec": {
        "es": "Detecta claves candidatas y crea relaciones muchos-a-uno con dirección de filtro simple. Las bidireccionales quedan como excepción justificada, no como regla.",
        "en": "Detects candidate keys and creates many-to-one relationships with single filter direction. Bidirectional ones stay a justified exception, not the rule.",
        "pt": "Deteta chaves candidatas e cria relações muitos-para-um com direção de filtro simples. As bidirecionais ficam como exceção justificada, não como regra.",
    },
    "bit_relaciones_criollo": {
        "es": "Se conecta cada tabla con las demás para que un filtro puesto en una se sienta en todas.",
        "en": "Each table is wired to the others so that a filter set on one is felt across all of them.",
        "pt": "Liga-se cada tabela às restantes para que um filtro posto numa se sinta em todas.",
    },
    "bit_relaciones_porque": {
        "es": "Sin relaciones cada visual mira su propia tabla y los totales no cruzan. Con relaciones de más, el filtro puede dar la vuelta y los números se vuelven ambiguos.",
        "en": "Without relationships each visual looks only at its own table and totals never cross. With too many, the filter can loop back and the numbers turn ambiguous.",
        "pt": "Sem relações cada visual olha para a sua própria tabela e os totais não cruzam. Com relações a mais, o filtro pode dar a volta e os números tornam-se ambíguos.",
    },
    "bit_relaciones_impacto": {
        "es": "Define qué filtra a qué: es la columna vertebral del modelo.",
        "en": "Determines what filters what: it is the model's backbone.",
        "pt": "Define o que filtra o quê: é a coluna vertebral do modelo.",
    },
    "bit_relaciones_ev": {"es": "{0} relaciones · {1} bidireccionales",
                          "en": "{0} relationships · {1} bidirectional",
                          "pt": "{0} relações · {1} bidirecionais"},

    # ---- 4 · corrección ----
    "bit_correccion_titulo": {"es": "Reglas de modelado",
                              "en": "Modelling rules",
                              "pt": "Regras de modelação"},
    "bit_correccion_tec": {
        "es": "Corre el catálogo de reglas del analizador —clave foránea visible, columna sin formato, modelo sin calendario— y aplica las correcciones aceptadas: ocultar, formatear, ordenar.",
        "en": "Runs the analyser's rule catalogue — visible foreign key, unformatted column, model with no calendar — and applies the accepted fixes: hide, format, sort.",
        "pt": "Corre o catálogo de regras do analisador — chave estrangeira visível, coluna sem formato, modelo sem calendário — e aplica as correções aceites: ocultar, formatar, ordenar.",
    },
    "bit_correccion_criollo": {
        "es": "Se revisa el modelo contra una lista de errores frecuentes y se arreglan los que correspondan.",
        "en": "The model is checked against a list of common mistakes and the applicable ones are fixed.",
        "pt": "Revê-se o modelo contra uma lista de erros frequentes e corrigem-se os que se aplicam.",
    },
    "bit_correccion_porque": {
        "es": "Son los defectos que trae siempre un modelo hecho a las apuradas, y los que hacen que el usuario final vea columnas técnicas que no le sirven para nada.",
        "en": "These are the defects a rushed model always carries, and what makes the end user see technical columns that are of no use to them.",
        "pt": "São os defeitos que um modelo feito à pressa traz sempre, e o que faz o usuário final ver colunas técnicas que não lhe servem de nada.",
    },
    "bit_correccion_impacto": {
        "es": "Deja el panel de campos limpio: se ve lo que se usa, no la plomería.",
        "en": "Leaves the field pane clean: what gets used shows, the plumbing does not.",
        "pt": "Deixa o painel de campos limpo: vê-se o que se usa, não a canalização.",
    },
    "bit_correccion_ev": {"es": "{0} columnas ocultas",
                          "en": "{0} hidden columns",
                          "pt": "{0} colunas ocultas"},

    # ---- 5 · calendario ----
    "bit_calendario_titulo": {"es": "Tabla de fechas", "en": "Date table",
                              "pt": "Tabela de datas"},
    "bit_calendario_tec": {
        "es": "Crea una tabla de fechas continua con año, semestre, trimestre, mes y año-mes ordenado, la marca `dataCategory = Time` y la relaciona con cada tabla de hechos.",
        "en": "Creates a continuous date table with year, half, quarter, month and sortable year-month, marks it `dataCategory = Time` and relates it to every fact table.",
        "pt": "Cria uma tabela de datas contínua com ano, semestre, trimestre, mês e ano-mês ordenado, marca-a `dataCategory = Time` e relaciona-a com cada tabela de factos.",
    },
    "bit_calendario_criollo": {
        "es": "Se arma un calendario propio para poder comparar meses, trimestres y años entre sí.",
        "en": "A dedicated calendar is built so months, quarters and years can be compared against each other.",
        "pt": "Monta-se um calendário próprio para poder comparar meses, trimestres e anos entre si.",
    },
    "bit_calendario_porque": {
        "es": "Power BI no compara períodos usando la columna de fecha de una tabla de hechos. Sin tabla de fechas marcada, TOTALYTD y compañía devuelven cualquier cosa, o nada.",
        "en": "Power BI does not compare periods off a fact table's date column. Without a marked date table, TOTALYTD and friends return anything, or nothing.",
        "pt": "O Power BI não compara períodos usando a coluna de data de uma tabela de factos. Sem tabela de datas marcada, TOTALYTD e companhia devolvem qualquer coisa, ou nada.",
    },
    "bit_calendario_impacto": {
        "es": "Habilita todo el bloque de comparativos y el drill down de tiempo (año → semestre → trimestre → mes).",
        "en": "Enables the whole comparatives block and the time drill-down (year → half → quarter → month).",
        "pt": "Habilita todo o bloco de comparativos e o drill down de tempo (ano → semestre → trimestre → mês).",
    },
    "bit_calendario_ev": {"es": "«{0}» con {1} columnas",
                          "en": "«{0}» with {1} columns",
                          "pt": "«{0}» com {1} colunas"},

    # ---- 6 · empresa ----
    "bit_empresa_titulo": {"es": "Empresa propia", "en": "Own company",
                           "pt": "Empresa própria"},
    "bit_empresa_tec": {
        "es": "Marca cuál valor de la dimensión corporativa es la empresa del usuario y lo anota en el modelo. Las medidas de share la usan como numerador y el resto del universo como denominador.",
        "en": "Flags which value of the corporate dimension is the user's own company and annotates it in the model. Share measures use it as numerator and the rest of the universe as denominator.",
        "pt": "Marca qual valor da dimensão corporativa é a empresa do usuário e anota-o no modelo. As medidas de quota usam-na como numerador e o resto do universo como denominador.",
    },
    "bit_empresa_criollo": {
        "es": "Se le dice al modelo cuál de todas las empresas del dataset sos vos.",
        "en": "The model is told which of all the companies in the dataset is you.",
        "pt": "Diz-se ao modelo qual de todas as empresas do dataset és tu.",
    },
    "bit_empresa_porque": {
        "es": "Sin eso el share propio da 100 % —se compara contra sí mismo— y la comparación contra el mercado directamente no existe.",
        "en": "Without it your own share reads 100 % — compared against itself — and the comparison against the market simply does not exist.",
        "pt": "Sem isso a quota própria dá 100 % — compara-se contra si mesma — e a comparação contra o mercado simplesmente não existe.",
    },
    "bit_empresa_impacto": {
        "es": "Habilita share propio contra mercado, y el color propio distinto del de los competidores.",
        "en": "Enables own share against market, and your own colour set apart from competitors'.",
        "pt": "Habilita quota própria contra mercado, e a cor própria distinta da dos concorrentes.",
    },
    "bit_empresa_ev": {"es": "«{0}»", "en": "«{0}»", "pt": "«{0}»"},

    # ---- 7 · KPIs ----
    "bit_kpis_titulo": {"es": "Medidas base", "en": "Base measures",
                        "pt": "Medidas base"},
    "bit_kpis_tec": {
        "es": "Crea las medidas base sobre cada columna numérica y de conteo —total, operaciones, únicos, promedio— en DAX explícito, no como agregaciones implícitas.",
        "en": "Creates the base measures over each numeric and count column — total, operations, distinct, average — in explicit DAX, not as implicit aggregations.",
        "pt": "Cria as medidas base sobre cada coluna numérica e de contagem — total, operações, únicos, média — em DAX explícito, não como agregações implícitas.",
    },
    "bit_kpis_criollo": {
        "es": "Se escriben los indicadores básicos: cuánto, cuántos, cuántos distintos, promedio.",
        "en": "The basic indicators are written: how much, how many, how many distinct, average.",
        "pt": "Escrevem-se os indicadores básicos: quanto, quantos, quantos distintos, média.",
    },
    "bit_kpis_porque": {
        "es": "Una agregación implícita no se puede formatear, ni reutilizar, ni auditar. Una medida escrita sí, y es la que después se referencia desde otras.",
        "en": "An implicit aggregation cannot be formatted, reused or audited. A written measure can, and it is what other measures reference later.",
        "pt": "Uma agregação implícita não se pode formatar, nem reutilizar, nem auditar. Uma medida escrita sim, e é a que depois se referencia a partir de outras.",
    },
    "bit_kpis_impacto": {
        "es": "Son los ladrillos de todo lo demás: los comparativos se apoyan sobre estas.",
        "en": "They are the bricks for everything else: the comparatives rest on these.",
        "pt": "São os tijolos de tudo o resto: os comparativos assentam nestas.",
    },
    "bit_kpis_ev": {"es": "{0} medidas base", "en": "{0} base measures",
                    "pt": "{0} medidas base"},

    # ---- 8 · comparativos ----
    "bit_comparativos_titulo": {"es": "Inteligencia de tiempo",
                                "en": "Time intelligence",
                                "pt": "Inteligência de tempo"},
    "bit_comparativos_tec": {
        "es": "Genera la matriz de comparativos: acumulado del año, mismo período del año anterior, variación en % y en puntos porcentuales, sobre importes, unidades y share.",
        "en": "Generates the comparatives matrix: year-to-date, same period last year, variation in % and in percentage points, over amounts, units and share.",
        "pt": "Gera a matriz de comparativos: acumulado do ano, mesmo período do ano anterior, variação em % e em pontos percentuais, sobre valores, unidades e quota.",
    },
    "bit_comparativos_criollo": {
        "es": "Se agregan las comparaciones contra el año pasado y contra el acumulado, que es lo primero que pregunta cualquier gerencia.",
        "en": "Comparisons against last year and against the running total are added — the first thing any manager asks for.",
        "pt": "Acrescentam-se as comparações contra o ano passado e contra o acumulado, que é a primeira coisa que qualquer gerência pergunta.",
    },
    "bit_comparativos_porque": {
        "es": "Un número solo no dice nada; dice algo comparado. Escribir esto a mano son horas, y es justo donde más se equivoca la gente.",
        "en": "A number alone says nothing; it says something once compared. Writing this by hand takes hours, and it is exactly where people get it wrong most often.",
        "pt": "Um número sozinho não diz nada; diz algo comparado. Escrever isto à mão são horas, e é precisamente onde as pessoas mais se enganam.",
    },
    "bit_comparativos_impacto": {
        "es": "Cada matriz del tablero responde mes, trimestre, semestre y año con las mismas medidas, sin duplicarlas.",
        "en": "Every matrix in the report answers month, quarter, half and year with the same measures, without duplicating them.",
        "pt": "Cada matriz do painel responde mês, trimestre, semestre e ano com as mesmas medidas, sem as duplicar.",
    },
    "bit_comparativos_ev": {"es": "{0} medidas de tiempo · carpetas: {1}",
                            "en": "{0} time measures · folders: {1}",
                            "pt": "{0} medidas de tempo · pastas: {1}"},

    # ---- 9 · derivadas ----
    "bit_derivadas_titulo": {"es": "Tablas agregadas a pedido",
                             "en": "Tables added on request",
                             "pt": "Tabelas acrescentadas a pedido"},
    "bit_derivadas_tec": {
        "es": "Tablas nuevas definidas por el usuario o por el pipeline, con sus columnas, su DAX y sus relaciones, validadas contra el catálogo antes de integrarse al modelo.",
        "en": "New tables defined by the user or by the pipeline, with their columns, DAX and relationships, validated against the catalogue before being merged into the model.",
        "pt": "Tabelas novas definidas pelo usuário ou pelo pipeline, com as suas colunas, o seu DAX e as suas relações, validadas contra o catálogo antes de se integrarem no modelo.",
    },
    "bit_derivadas_criollo": {
        "es": "Tablas que no venían en el archivo original y se agregaron porque hacían falta.",
        "en": "Tables that were not in the original file and were added because they were needed.",
        "pt": "Tabelas que não vinham no arquivo original e foram acrescentadas porque faziam falta.",
    },
    "bit_derivadas_porque": {
        "es": "Un pedido de negocio no siempre se resuelve con una medida: a veces hace falta una tabla que el origen no trae.",
        "en": "A business request is not always solved with a measure: sometimes it needs a table the source does not carry.",
        "pt": "Um pedido de negócio nem sempre se resolve com uma medida: por vezes é preciso uma tabela que a origem não traz.",
    },
    "bit_derivadas_impacto": {
        "es": "Agrega dimensiones de análisis que el dataset original no permitía.",
        "en": "Adds analysis dimensions the original dataset did not allow.",
        "pt": "Acrescenta dimensões de análise que o dataset original não permitia.",
    },
    "bit_derivadas_ev": {"es": "{0} tablas: {1}", "en": "{0} tables: {1}",
                         "pt": "{0} tabelas: {1}"},

    # ---- 10 · diccionario ----
    "bit_diccionario_titulo": {"es": "Diccionario de medidas",
                               "en": "Measure dictionary",
                               "pt": "Dicionário de medidas"},
    "bit_diccionario_tec": {
        "es": "Tabla desconectada con una fila por medida: nombre, carpeta, formato, su DAX y la razón de cada decisión de diseño, leída del propio DAX y no inventada.",
        "en": "A disconnected table with one row per measure: name, folder, format, its DAX and the reason behind each design decision, read from the DAX itself and never invented.",
        "pt": "Tabela desligada com uma linha por medida: nome, pasta, formato, o seu DAX e a razão de cada decisão de desenho, lida do próprio DAX e não inventada.",
    },
    "bit_diccionario_criollo": {
        "es": "Un diccionario adentro del archivo que explica qué hace cada indicador y por qué está escrito así.",
        "en": "A dictionary inside the file explaining what each indicator does and why it is written that way.",
        "pt": "Um dicionário dentro do arquivo que explica o que faz cada indicador e porque está escrito assim.",
    },
    "bit_diccionario_porque": {
        "es": "Quien hereda el modelo tiene hoy dos opciones: leer todo el DAX, o tocar y ver qué se rompe. Las dos son caras.",
        "en": "Whoever inherits the model has two options today: read all the DAX, or poke it and see what breaks. Both are expensive.",
        "pt": "Quem herda o modelo tem hoje duas opções: ler todo o DAX, ou mexer e ver o que parte. As duas são caras.",
    },
    "bit_diccionario_impacto": {
        "es": "El archivo se explica solo; no depende de un documento aparte que se pierde en el segundo reenvío.",
        "en": "The file explains itself; it does not depend on a separate document that gets lost on the second forward.",
        "pt": "O arquivo explica-se sozinho; não depende de um documento à parte que se perde no segundo reencaminhamento.",
    },
    "bit_diccionario_ev": {"es": "tabla «{0}»", "en": "table «{0}»",
                           "pt": "tabela «{0}»"},

    # ---- 11 · lectura ----
    "bit_lectura_titulo": {"es": "Conclusiones automáticas",
                           "en": "Automatic readings",
                           "pt": "Conclusões automáticas"},
    "bit_lectura_tec": {
        "es": "Recorre el modelo y arma una lectura por página —qué muestra, qué se destaca, qué mirar— sin IA: sale de las medidas y de los datos, así que nunca contradice al tablero.",
        "en": "Walks the model and builds a reading per page — what it shows, what stands out, what to look at — with no AI: it comes from the measures and the data, so it never contradicts the report.",
        "pt": "Percorre o modelo e monta uma leitura por página — o que mostra, o que se destaca, o que olhar — sem IA: sai das medidas e dos dados, por isso nunca contradiz o painel.",
    },
    "bit_lectura_criollo": {
        "es": "El tablero viene con un texto que dice qué está mostrando cada pantalla.",
        "en": "The report ships with text saying what each screen is showing.",
        "pt": "O painel vem com um texto que diz o que cada tela está mostrando.",
    },
    "bit_lectura_porque": {
        "es": "Un tablero sin lectura obliga a que alguien lo presente. Con lectura se puede mandar por mail y se entiende igual.",
        "en": "A report with no reading needs someone to present it. With one it can be emailed and still be understood.",
        "pt": "Um painel sem leitura obriga a que alguém o apresente. Com leitura pode ser enviado por email e se entende do mesmo jeito.",
    },
    "bit_lectura_impacto": {
        "es": "Baja el tiempo entre recibir el archivo y entender qué dice.",
        "en": "Cuts the time between receiving the file and understanding what it says.",
        "pt": "Reduz o tempo entre receber o arquivo e perceber o que diz.",
    },
    "bit_lectura_ev": {"es": "tabla «{0}»", "en": "table «{0}»",
                       "pt": "tabela «{0}»"},

    # ---- 12 · tablero ----
    "bit_tablero_titulo": {"es": "Diseño del tablero", "en": "Report design",
                           "pt": "Desenho do painel"},
    "bit_tablero_tec": {
        "es": "Arma las páginas en formato PBIR: KPIs, líneas, barras y matrices con jerarquías de drill down, filtros por página, semáforo por formato condicional y paleta propia.",
        "en": "Builds the pages in PBIR format: KPIs, lines, bars and matrices with drill-down hierarchies, per-page filters, conditional-formatting traffic lights and a dedicated palette.",
        "pt": "Monta as páginas em formato PBIR: KPIs, linhas, barras e matrizes com hierarquias de drill down, filtros por página, semáforo por formatação condicional e paleta própria.",
    },
    "bit_tablero_criollo": {
        "es": "Se dibuja el tablero: las pantallas, los gráficos, los filtros y los colores.",
        "en": "The report is drawn: the screens, the charts, the filters and the colours.",
        "pt": "Desenha-se o painel: as telas, os gráficos, os filtros e as cores.",
    },
    "bit_tablero_porque": {
        "es": "Es la parte que el cliente ve. Un modelo impecable con un tablero feo se percibe como un trabajo malo, y esa percepción no se discute con argumentos técnicos.",
        "en": "It is the part the client sees. A flawless model with an ugly report is perceived as bad work, and that perception is not argued away with technical points.",
        "pt": "É a parte que o cliente vê. Um modelo impecável com um painel feio é percebido como um trabalho mau, e essa perceção não se discute com argumentos técnicos.",
    },
    "bit_tablero_impacto": {
        "es": "Define qué se ve, en qué orden y con cuánto detalle se puede bajar.",
        "en": "Determines what is seen, in what order, and how far down one can drill.",
        "pt": "Define o que se vê, por que ordem e com quanto detalhe se pode descer.",
    },
    "bit_tablero_ev": {"es": "{0} páginas · {1} visuales",
                       "en": "{0} pages · {1} visuals",
                       "pt": "{0} páginas · {1} visuais"},

    # ---- 13 · empotrado ----
    "bit_empotrado_titulo": {"es": "Datos adentro del archivo",
                             "en": "Data inside the file",
                             "pt": "Dados dentro do arquivo"},
    "bit_empotrado_tec": {
        "es": "Convierte las filas en una expresión M —`Table.FromRows` sobre JSON comprimido en base64— dentro de la partición de cada tabla, igual que hace «Introducir datos» de Power BI.",
        "en": "Turns the rows into an M expression — `Table.FromRows` over base64-compressed JSON — inside each table's partition, the same way Power BI's «Enter data» does.",
        "pt": "Converte as linhas numa expressão M — `Table.FromRows` sobre JSON comprimido em base64 — dentro da partição de cada tabela, tal como faz o «Introduzir dados» do Power BI.",
    },
    "bit_empotrado_criollo": {
        "es": "Los datos viajan adentro del archivo: se abre en cualquier computadora sin pedir la carpeta de origen.",
        "en": "The data travels inside the file: it opens on any computer without asking for the source folder.",
        "pt": "Os dados viajam dentro do arquivo: abre em qualquer computador sem pedir a pasta de origem.",
    },
    "bit_empotrado_porque": {
        "es": "Un modelo que apunta a una ruta anda en la máquina donde se armó y en ninguna otra. Repuntar a una copia temporal dura hasta que se cierra la sesión.",
        "en": "A model pointing at a path works on the machine where it was built and nowhere else. Repointing at a temporary copy lasts until the session closes.",
        "pt": "Um modelo que aponta para um caminho funciona na máquina onde foi montado e em mais nenhuma. Reapontar para uma cópia temporária dura até a sessão fechar.",
    },
    "bit_empotrado_impacto": {
        "es": "El `.pbit` se puede mandar por mail y abre del otro lado.",
        "en": "The `.pbit` can be emailed and opens on the other end.",
        "pt": "O `.pbit` pode ser enviado por email e abre do outro lado.",
    },
    "bit_empotrado_ev": {"es": "{0} tablas con datos adentro",
                         "en": "{0} tables with data inside",
                         "pt": "{0} tabelas com dados dentro"},

    # ---- 14 · gobernanza ----
    "bit_gobernanza_titulo": {"es": "Ficha para gobierno de datos",
                              "en": "Data governance record",
                              "pt": "Ficha para governo de dados"},
    "bit_gobernanza_tec": {
        "es": "Anota en el modelo TMSL un manifiesto con filas y papel de cada tabla y la definición de negocio de cada medida, para que un catálogo de datos lo lea sin abrir Power BI.",
        "en": "Annotates the TMSL model with a manifest carrying each table's row count and role plus each measure's business definition, so a data catalogue can read it without opening Power BI.",
        "pt": "Anota no modelo TMSL um manifesto com linhas e papel de cada tabela e a definição de negócio de cada medida, para que um catálogo de dados o leia sem abrir o Power BI.",
    },
    "bit_gobernanza_criollo": {
        "es": "El archivo lleva su propia ficha: qué trae, de dónde salió y qué significa cada indicador.",
        "en": "The file carries its own record: what it holds, where it came from and what each indicator means.",
        "pt": "O arquivo leva a sua própria ficha: o que traz, de onde saiu e o que significa cada indicador.",
    },
    "bit_gobernanza_porque": {
        "es": "Un tablero sin esa ficha no se puede auditar ni gobernar: es una foto sin fecha ni autor.",
        "en": "A report without that record cannot be audited or governed: it is a photograph with no date and no author.",
        "pt": "Um painel sem essa ficha não se pode auditar nem governar: é uma fotografia sem data nem autor.",
    },
    "bit_gobernanza_impacto": {
        "es": "Un catálogo de datos lo ingiere solo, sin que nadie transcriba nada a mano.",
        "en": "A data catalogue ingests it on its own, with nobody transcribing anything by hand.",
        "pt": "Um catálogo de dados ingere-o sozinho, sem que ninguém transcreva nada à mão.",
    },
    "bit_gobernanza_ev": {"es": "{0} tablas · {1} medidas declaradas",
                          "en": "{0} tables · {1} measures declared",
                          "pt": "{0} tabelas · {1} medidas declaradas"},

    # ---- 15 · gate ----
    "bit_gate_titulo": {"es": "Verificación de salida", "en": "Output gate",
                        "pt": "Verificação de saída"},
    "bit_gate_tec": {
        "es": "Abre el archivo ya escrito y lo audita ítem por ítem contra lo que declara un `.pbit` real: contenedor, codificación, particiones, relaciones, cada referencia DAX y cada campo de cada visual.",
        "en": "Opens the file just written and audits it item by item against what a real `.pbit` declares: container, encoding, partitions, relationships, every DAX reference and every field of every visual.",
        "pt": "Abre o arquivo já escrito e audita-o item a item contra o que declara um `.pbit` real: contentor, codificação, partições, relações, cada referência DAX e cada campo de cada visual.",
    },
    "bit_gate_criollo": {
        "es": "Antes de entregar, el programa abre lo que acaba de escribir y lo revisa como si lo recibiera de un tercero.",
        "en": "Before handing over, the program opens what it just wrote and inspects it as if it had received it from someone else.",
        "pt": "Antes de entregar, o programa abre o que acabou de escrever e revê-o como se o tivesse recebido de um terceiro.",
    },
    "bit_gate_porque": {
        "es": "Dos veces se entregó un archivo «verificado» que en Power BI Desktop no servía, porque la verificación era contra el lector de este mismo programa. Un round-trip contra uno mismo no verifica nada.",
        "en": "Twice a «verified» file was delivered that did not work in Power BI Desktop, because verification ran against this program's own reader. A round-trip against yourself verifies nothing.",
        "pt": "Duas vezes se entregou um arquivo «verificado» que no Power BI Desktop não servia, porque a verificação era contra o leitor deste mesmo programa. Um round-trip contra si próprio não verifica nada.",
    },
    "bit_gate_impacto": {
        "es": "Nada sale con una referencia colgada, una parte que falta o un visual que no se puede leer.",
        "en": "Nothing ships with a dangling reference, a missing part or a visual that cannot be parsed.",
        "pt": "Nada sai com uma referência pendurada, uma parte em falta ou um visual que não se consegue ler.",
    },
    "bit_gate_ev": {"es": "{0} ítems · {1} faltas · {2} avisos",
                    "en": "{0} items · {1} failures · {2} warnings",
                    "pt": "{0} itens · {1} faltas · {2} avisos"},

    "vf_traspaso": {"es": "Ficha para gobierno de datos",
                    "en": "Data governance handoff",
                    "pt": "Ficha para governo de dados"},
    "vf_traspaso_ok": {
        "es": "El archivo lleva adentro su ficha de gobierno: {tablas} tablas con sus filas y su papel, y la definición de negocio de {medidas} medidas. Un catálogo de datos la lee sin abrir Power BI.",
        "en": "The file carries its governance record inside: {tablas} tables with their row counts and roles, and the business definition of {medidas} measures. A data catalog reads it without opening Power BI.",
        "pt": "O arquivo leva dentro a sua ficha de governo: {tablas} tabelas com as suas linhas e o seu papel, e a definição de negócio de {medidas} medidas. Um catálogo de dados lê-a sem abrir o Power BI.",
    },
    "vf_traspaso_aviso": {
        "es": "El archivo no lleva ficha de gobierno. Abre igual: quien lo reciba va a tener que deducir a mano cuántas filas trae cada tabla y qué significa cada medida.",
        "en": "The file carries no governance record. It opens fine: whoever receives it will have to work out by hand how many rows each table has and what each measure means.",
        "pt": "O arquivo não leva ficha de governo. Abre do mesmo jeito: quem receber terá de deduzir à mão quantas linhas traz cada tabela e o que significa cada medida.",
    },
    "vf_codificacion": {"es": "Codificación del contenedor",
                        "en": "Container encoding",
                        "pt": "Codificação do contentor"},
    "vf_codificacion_ok": {
        "es": "«Version» y «DataModelSchema» están en UTF-16LE sin BOM, como los .pbit que exporta Power BI Desktop.",
        "en": "«Version» and «DataModelSchema» are UTF-16LE without BOM, like the .pbit files Power BI Desktop exports.",
        "pt": "«Version» e «DataModelSchema» estão em UTF-16LE sem BOM, como os .pbit que o Power BI Desktop exporta.",
    },
    "vf_codificacion_falta": {
        "es": "{n} parte(s) mal codificadas: {lista}.",
        "en": "{n} badly encoded part(s): {lista}.",
        "pt": "{n} parte(s) mal codificadas: {lista}.",
    },
    "vf_cod_bom": {
        "es": "«{parte}» lleva BOM y Desktop lo lee como parte del contenido",
        "en": "«{parte}» carries a BOM and Desktop reads it as part of the content",
        "pt": "«{parte}» tem BOM e o Desktop lê-o como parte do conteúdo",
    },
    "vf_cod_utf16": {
        "es": "«{parte}» no está en UTF-16LE",
        "en": "«{parte}» is not UTF-16LE",
        "pt": "«{parte}» não está em UTF-16LE",
    },
    "vf_particiones": {"es": "Particiones de las tablas",
                       "en": "Table partitions",
                       "pt": "Partições das tabelas"},
    "vf_particiones_ok": {
        "es": "Las {tablas} tablas tienen columnas y al menos una partición de dónde traer las filas.",
        "en": "All {tablas} tables have columns and at least one partition to pull rows from.",
        "pt": "As {tablas} tabelas têm colunas e pelo menos uma partição de onde trazer as linhas.",
    },
    "vf_particiones_falta": {
        "es": "{n} de {tablas} tablas quedan sin columnas o sin partición y abren en error: {lista}.",
        "en": "{n} of {tablas} tables have no columns or no partition and open in error: {lista}.",
        "pt": "{n} de {tablas} tabelas ficam sem colunas ou sem partição e abrem em erro: {lista}.",
    },
    "vf_visuales": {"es": "Visuales del reporte",
                    "en": "Report visuals", "pt": "Visuais do relatório"},
    "vf_visuales_ok": {
        "es": "Los {total} visuales se leen, tienen su lugar en la hoja y cada campo que usan existe en el modelo.",
        "en": "All {total} visuals parse, have their place on the canvas, and every field they use exists in the model.",
        "pt": "Os {total} visuais leem-se, têm o seu lugar na folha e cada campo que usam existe no modelo.",
    },
    "vf_visuales_falta": {
        "es": "{n} problemas en {total} visuales: {lista}.",
        "en": "{n} problems across {total} visuals: {lista}.",
        "pt": "{n} problemas em {total} visuais: {lista}.",
    },
    "vf_vis_ilegible": {
        "es": "«{visual}» no se puede leer ({motivo}): Desktop lo pierde entero",
        "en": "«{visual}» cannot be parsed ({motivo}): Desktop loses it entirely",
        "pt": "«{visual}» não se consegue ler ({motivo}): o Desktop perde-o inteiro",
    },
    "vf_vis_sin_lugar": {
        "es": "«{visual}» no dice dónde va en la hoja",
        "en": "«{visual}» does not say where it goes on the canvas",
        "pt": "«{visual}» não diz onde vai na folha",
    },
    "vf_vis_afuera": {
        "es": "«{visual}» cae fuera de la hoja ({x},{y} de {ancho}×{alto}): nadie lo ve",
        "en": "«{visual}» falls outside the canvas ({x},{y} at {ancho}×{alto}): nobody sees it",
        "pt": "«{visual}» cai fora da folha ({x},{y} de {ancho}×{alto}): ninguém o vê",
    },
    "vf_vis_campo": {
        "es": "«{visual}» usa «{tabla}»[{campo}], que no existe en el modelo",
        "en": "«{visual}» uses «{tabla}»[{campo}], which does not exist in the model",
        "pt": "«{visual}» usa «{tabla}»[{campo}], que não existe no modelo",
    },
    "vf_paginas": {"es": "Índice de páginas",
                   "en": "Page index", "pt": "Índice de páginas"},
    "vf_paginas_ok": {
        "es": "El índice nombra exactamente las {total} páginas que están en el archivo, y cada una se llama adentro como su carpeta.",
        "en": "The index names exactly the {total} pages present in the file, and each one is named inside as its folder.",
        "pt": "O índice nomeia exatamente as {total} páginas que estão no arquivo, e cada uma chama-se dentro como a sua pasta.",
    },
    "vf_paginas_falta": {
        "es": "{n} problemas en el índice de {total} páginas: {lista}.",
        "en": "{n} problems in the index of {total} pages: {lista}.",
        "pt": "{n} problemas no índice de {total} páginas: {lista}.",
    },
    "vf_pag_falta": {
        "es": "el índice nombra «{pagina}», que no está en el archivo",
        "en": "the index names «{pagina}», which is not in the file",
        "pt": "o índice nomeia «{pagina}», que não está no arquivo",
    },
    "vf_pag_suelta": {
        "es": "«{pagina}» está en el archivo y el índice no la nombra: nadie la ve",
        "en": "«{pagina}» is in the file and the index does not name it: nobody sees it",
        "pt": "«{pagina}» está no arquivo e o índice não a nomeia: ninguém a vê",
    },
    "vf_pag_repetida": {
        "es": "«{pagina}» aparece dos veces en el orden",
        "en": "«{pagina}» appears twice in the order",
        "pt": "«{pagina}» aparece duas vezes na ordem",
    },
    "vf_pag_activa": {
        "es": "la página que abre por defecto («{pagina}») no existe",
        "en": "the page that opens by default («{pagina}») does not exist",
        "pt": "a página que abre por omissão («{pagina}») não existe",
    },
    "vf_pag_sin_json": {
        "es": "«{pagina}» no tiene su page.json",
        "en": "«{pagina}» has no page.json",
        "pt": "«{pagina}» não tem o seu page.json",
    },
    "vf_pag_nombre": {
        "es": "la carpeta «{pagina}» se llama «{dentro}» adentro",
        "en": "folder «{pagina}» is named «{dentro}» inside",
        "pt": "a pasta «{pagina}» chama-se «{dentro}» por dentro",
    },

    "vf_calendario": {"es": "Calendario", "en": "Date table",
                      "pt": "Calendário"},
    "vf_calendario_ok": {
        "es": "Hay tabla de fechas: {tabla}. La inteligencia de tiempo tiene de dónde agarrarse.",
        "en": "There is a date table: {tabla}. Time intelligence has something to hold on to.",
        "pt": "Há tabela de datas: {tabla}. A inteligência de tempo tem onde se apoiar.",
    },
    "vf_calendario_aviso": {
        "es": "Hay columnas de fecha pero ninguna tabla de calendario: YTD, mes anterior y comparativos de período no van a funcionar bien.",
        "en": "There are date columns but no calendar table: YTD, prior month and period comparisons will not work properly.",
        "pt": "Há colunas de data mas nenhuma tabela de calendário: YTD, mês anterior e comparativos de período não vão funcionar bem.",
    },

    "vf_si": {"es": "sí", "en": "yes", "pt": "sim"},
    "vf_no": {"es": "NO", "en": "NO", "pt": "NÃO"},
    "vf_tiempo": {"es": "Inteligencia de tiempo",
                  "en": "Time intelligence",
                  "pt": "Inteligência de tempo"},
    "vf_tiempo_ok": {
        "es": "El calendario está marcado como tabla de fechas ({marcada}), tiene su clave ({llave}) y las etiquetas de período ordenan por su columna numérica.",
        "en": "The calendar is marked as a date table ({marcada}), has its key ({llave}) and the period labels sort by their numeric column.",
        "pt": "O calendário está marcado como tabela de datas ({marcada}), tem a sua chave ({llave}) e as etiquetas de período ordenam pela coluna numérica.",
    },
    "vf_tiempo_aviso": {
        "es": "Marcada como tabla de fechas: {marcada} · clave de fecha: {llave} · etiquetas sin orden numérico: {lista}. Sin la marca, TOTALYTD y SAMEPERIODLASTYEAR devuelven en blanco; sin orden, los meses salen alfabéticos (abril antes que enero).",
        "en": "Marked as a date table: {marcada} · date key: {llave} · labels without numeric order: {lista}. Without the mark, TOTALYTD and SAMEPERIODLASTYEAR return blank; without order, months come out alphabetically (April before January).",
        "pt": "Marcada como tabela de datas: {marcada} · chave de data: {llave} · etiquetas sem ordem numérica: {lista}. Sem a marca, TOTALYTD e SAMEPERIODLASTYEAR devolvem em branco; sem ordem, os meses saem alfabéticos (abril antes de janeiro).",
    },

    "vf_tablero": {"es": "Tablero", "en": "Report pages", "pt": "Painel"},
    "vf_tablero_ok": {
        "es": "{paginas} páginas con {visuales} visuales.",
        "en": "{paginas} pages with {visuales} visuals.",
        "pt": "{paginas} páginas com {visuales} visuais.",
    },
    "vf_tablero_aviso": {
        "es": "El archivo no trae ningún visual: abre con el lienzo en blanco y el modelo listo para armarlo a mano.",
        "en": "The file carries no visuals: it opens with a blank canvas and the model ready to build on.",
        "pt": "O arquivo não traz nenhum visual: abre com a tela em branco e o modelo pronto para montar à mão.",
    },

    "vf_identificadores": {"es": "Identificadores de los visuales",
                          "en": "Visual identifiers",
                          "pt": "Identificadores dos visuais"},
    "vf_identificadores_ok": {
        "es": "Los {total} visuales tienen identificadores distintos.",
        "en": "All {total} visuals have distinct identifiers.",
        "pt": "Os {total} visuais têm identificadores distintos.",
    },
    "vf_identificadores_falta": {
        "es": "{n} identificadores repetidos entre {total} visuales ({lista}). En PBIR el nombre identifica al visual en el reporte entero: repetirlo hace que Desktop rechace el archivo.",
        "en": "{n} duplicate identifiers across {total} visuals ({lista}). In PBIR the name identifies the visual across the whole report: repeating one makes Desktop reject the file.",
        "pt": "{n} identificadores repetidos entre {total} visuais ({lista}). Em PBIR o nome identifica o visual no relatório inteiro: repeti-lo faz o Desktop rejeitar o arquivo.",
    },

    "vf_recursos": {"es": "Recursos declarados por el tablero",
                    "en": "Resources the report declares",
                    "pt": "Recursos declarados pelo painel"},
    "vf_recursos_ok": {
        "es": "Todo recurso que el tablero declara está dentro del archivo.",
        "en": "Every resource the report declares is inside the file.",
        "pt": "Todo recurso que o painel declara está dentro do arquivo.",
    },
    "vf_recursos_falta": {
        "es": "{n} recursos declarados que no están en el paquete ({lista}). Una referencia colgada a una parte inexistente hace que Desktop rechace el archivo.",
        "en": "{n} declared resources missing from the package ({lista}). A dangling reference to a part that is not there makes Desktop reject the file.",
        "pt": "{n} recursos declarados que não estão no pacote ({lista}). Uma referência pendente a uma parte inexistente faz o Desktop rejeitar o arquivo.",
    },

    "vf_campos": {"es": "Campos que usan los visuales",
                  "en": "Fields the visuals use",
                  "pt": "Campos que os visuais usam"},
    "vf_campos_ok": {
        "es": "Cada campo que piden los visuales existe en el modelo.",
        "en": "Every field the visuals ask for exists in the model.",
        "pt": "Cada campo que os visuais pedem existe no modelo.",
    },
    "vf_campos_falta": {
        "es": "{n} campos que los visuales piden y el modelo no tiene ({lista}). Esos visuales abren con el cartel de error.",
        "en": "{n} fields the visuals ask for that the model does not have ({lista}). Those visuals open with an error card.",
        "pt": "{n} campos que os visuais pedem e o modelo não tem ({lista}). Esses visuais abrem com o aviso de erro.",
    },

    "vf_veredicto_ok": {
        "es": "LISTO — ningún faltante. {avisos} avisos (no bloquean).",
        "en": "READY — nothing missing. {avisos} warnings (non-blocking).",
        "pt": "PRONTO — nada em falta. {avisos} avisos (não bloqueiam).",
    },
    "vf_veredicto_falta": {
        "es": "NO ESTÁ LISTO — {faltan} faltantes y {avisos} avisos. Arreglá los faltantes antes de entregar el archivo.",
        "en": "NOT READY — {faltan} missing items and {avisos} warnings. Fix the missing items before handing the file over.",
        "pt": "NÃO ESTÁ PRONTO — {faltan} em falta e {avisos} avisos. Corrige o que falta antes de entregar o arquivo.",
    },
    "nlp_d_diccionario": {
        "es": 'Agregar la página y la tabla de diccionario (qué es cada tabla, columna y medida)',
        "en": 'Add the dictionary page and table (what each table, column and measure is)',
        "pt": 'Adicionar a página e a tabela de dicionário (o que é cada tabela, coluna e medida)',
    },
    "rel_por_fecha": {
        "es": 'La fecha del hecho contra el calendario: es la relación que hace andar la inteligencia de tiempo (YTD, año anterior).',
        "en": "The fact's date against the calendar: the relationship that powers time intelligence (YTD, prior year).",
        "pt": 'A data do fato contra o calendário: é a relação que faz funcionar a inteligência de tempo (YTD, ano anterior).',
    },
    "rel_por_tabla_id": {
        "es": '{desde} sigue la convención «<Tabla>ID»: apunta a la clave de {tabla}, y los valores del lado «muchos» están en el lado «uno».',
        "en": '{desde} follows the “<Table>ID” convention: it points to the key of {tabla}, and the many-side values exist on the one side.',
        "pt": '{desde} segue a convenção «<Tabela>ID»: aponta para a chave de {tabla}, e os valores do lado «muitos» estão no lado «um».',
    },
    "rel_por_nombre": {
        "es": 'Las dos columnas se llaman igual ({hacia}) y la del lado «uno» es única; los valores del hecho existen en la dimensión.',
        "en": "Both columns share the same name ({hacia}) and the one-side column is unique; the fact's values exist in the dimension.",
        "pt": 'As duas colunas têm o mesmo nome ({hacia}) e a do lado «um» é única; os valores do fato existem na dimensão.',
    },
    "rel_declarada": {
        "es": 'Declarada en el archivo de origen: la trajo el modelo tal como estaba.',
        "en": 'Declared in the source file: it came with the model as it was.',
        "pt": 'Declarada no arquivo de origem: veio com o modelo como estava.',
    },
    "rel_filtro": {
        "es": 'El filtro viaja de {dimension} a {hecho}: cortar por {dimension} cambia los números de {hecho}, no al revés.',
        "en": "The filter flows from {dimension} to {hecho}: slicing by {dimension} changes {hecho}'s numbers, not the other way around.",
        "pt": 'O filtro viaja de {dimension} para {hecho}: cortar por {dimension} muda os números de {hecho}, não o contrário.',
    },
    "rel_bidireccional_aviso": {
        "es": 'Filtra en ambas direcciones: la dimensión también se filtra desde el hecho. Es lento y ambiguo; conviene una sola dirección salvo un caso puntual.',
        "en": 'Filters in both directions: the dimension is also filtered from the fact. Slow and ambiguous; one direction is recommended unless there is a specific need.',
        "pt": 'Filtra em ambas as direções: a dimensão também é filtrada pelo fato. É lento e ambíguo; convém uma só direção salvo um caso pontual.',
    },
    "rel_inactiva": {
        "es": 'Inactiva: solo actúa dentro de una medida con USERELATIONSHIP.',
        "en": 'Inactive: it only acts inside a measure with USERELATIONSHIP.',
        "pt": 'Inativa: só age dentro de uma medida com USERELATIONSHIP.',
    },
    "rel_muchos_a_muchos": {
        "es": 'Muchos a muchos: ninguno de los dos lados es único. Los totales pueden no cerrar.',
        "en": 'Many-to-many: neither side is unique. Totals may not add up.',
        "pt": 'Muitos para muitos: nenhum dos lados é único. Os totais podem não fechar.',
    },
    "rel_quitada": {
        "es": 'Relación quitada: {rel}',
        "en": 'Relationship removed: {rel}',
        "pt": 'Relação removida: {rel}',
    },
    "rel_aviso_userelationship": {
        "es": 'Ojo: estas medidas la usaban con USERELATIONSHIP y van a fallar: {lista}',
        "en": 'Careful: these measures used it with USERELATIONSHIP and will fail: {lista}',
        "pt": 'Atenção: estas medidas a usavam com USERELATIONSHIP e vão falhar: {lista}',
    },
    "rel_activada": {
        "es": 'Relación activada: {rel}',
        "en": 'Relationship activated: {rel}',
        "pt": 'Relação ativada: {rel}',
    },
    "rel_desactivada": {
        "es": 'Relación desactivada: {rel}',
        "en": 'Relationship deactivated: {rel}',
        "pt": 'Relação desativada: {rel}',
    },
    "rel_direccion_ambas": {
        "es": 'Filtro en ambas direcciones: {rel}',
        "en": 'Filter in both directions: {rel}',
        "pt": 'Filtro em ambas as direções: {rel}',
    },
    "rel_direccion_una": {
        "es": 'Filtro en una sola dirección: {rel}',
        "en": 'Filter in a single direction: {rel}',
        "pt": 'Filtro em uma só direção: {rel}',
    },
    "rel_agregada": {
        "es": 'Relación agregada: {rel}',
        "en": 'Relationship added: {rel}',
        "pt": 'Relação adicionada: {rel}',
    },
    "rel_agregada_inactiva": {
        "es": 'Relación agregada INACTIVA (ya había una activa entre esas tablas): {rel}',
        "en": 'Relationship added INACTIVE (there was already an active one between those tables): {rel}',
        "pt": 'Relação adicionada INATIVA (já havia uma ativa entre essas tabelas): {rel}',
    },
    "rel_err_no_existe": {
        "es": 'Esa relación no existe en el modelo.',
        "en": 'That relationship does not exist in the model.',
        "pt": 'Essa relação não existe no modelo.',
    },
    "rel_err_dos_activas": {
        "es": 'Ya hay una relación activa entre esas dos tablas: Power BI no admite dos caminos activos.',
        "en": 'There is already an active relationship between those two tables: Power BI does not allow two active paths.',
        "pt": 'Já existe uma relação ativa entre essas duas tabelas: o Power BI não admite dois caminhos ativos.',
    },
    "rel_err_tabla": {
        "es": 'No existe la tabla «{tabla}».',
        "en": 'Table “{tabla}” does not exist.',
        "pt": 'A tabela «{tabla}» não existe.',
    },
    "rel_err_columna": {
        "es": 'No existe la columna «{col}».',
        "en": 'Column “{col}” does not exist.',
        "pt": 'A coluna «{col}» não existe.',
    },
    "rel_err_tipo": {
        "es": 'Las columnas son de tipos distintos ({a} y {b}): Power BI no puede relacionarlas.',
        "en": 'The columns have different types ({a} and {b}): Power BI cannot relate them.',
        "pt": 'As colunas são de tipos diferentes ({a} e {b}): o Power BI não consegue relacioná-las.',
    },
    "rel_err_misma": {
        "es": 'Una tabla no se relaciona consigo misma.',
        "en": 'A table cannot relate to itself.',
        "pt": 'Uma tabela não se relaciona consigo mesma.',
    },
    "rel_err_existe": {
        "es": 'Esa relación ya existe.',
        "en": 'That relationship already exists.',
        "pt": 'Essa relação já existe.',
    },
    "rel_lista_titulo": {
        "es": 'Cada relación, explicada',
        "en": 'Each relationship, explained',
        "pt": 'Cada relação, explicada',
    },
    "rel_lista_ayuda": {
        "es": 'Por qué existe, hacia dónde viaja el filtro y qué cambiar si no estás de acuerdo. Todo se aplica al modelo cargado; nada se escribe en tu archivo hasta exportar.',
        "en": 'Why it exists, where the filter flows and what to change if you disagree. Everything applies to the loaded model; nothing is written to your file until you export.',
        "pt": 'Por que existe, para onde viaja o filtro e o que mudar se você não concordar. Tudo se aplica ao modelo carregado; nada é gravado no seu arquivo até exportar.',
    },
    "rel_medidas_apoyadas": {
        "es": '{n} medidas se apoyan en {hecho}',
        "en": '{n} measures rely on {hecho}',
        "pt": '{n} medidas se apoiam em {hecho}',
    },
    "rel_btn_quitar": {
        "es": 'Quitar',
        "en": 'Remove',
        "pt": 'Remover',
    },
    "rel_btn_desactivar": {
        "es": 'Desactivar',
        "en": 'Deactivate',
        "pt": 'Desativar',
    },
    "rel_btn_activar": {
        "es": 'Activar',
        "en": 'Activate',
        "pt": 'Ativar',
    },
    "rel_btn_una": {
        "es": 'Una dirección',
        "en": 'Single direction',
        "pt": 'Uma direção',
    },
    "rel_btn_ambas": {
        "es": 'Ambas direcciones',
        "en": 'Both directions',
        "pt": 'Ambas as direções',
    },
    "rel_btn_invertir": {
        "es": 'Invertir lados',
        "en": 'Swap sides',
        "pt": 'Inverter lados',
    },
    "rel_agregar_titulo": {
        "es": 'Agregar una relación',
        "en": 'Add a relationship',
        "pt": 'Adicionar uma relação',
    },
    "rel_desde": {
        "es": 'Lado «muchos» (hecho)',
        "en": 'Many side (fact)',
        "pt": 'Lado «muitos» (fato)',
    },
    "rel_hacia": {
        "es": 'Lado «uno» (dimensión)',
        "en": 'One side (dimension)',
        "pt": 'Lado «um» (dimensão)',
    },
    "rel_columna": {
        "es": 'Columna',
        "en": 'Column',
        "pt": 'Coluna',
    },
    "rel_btn_agregar": {
        "es": 'Agregar relación',
        "en": 'Add relationship',
        "pt": 'Adicionar relação',
    },
    "etl_titulo": {
        "es": 'Transformaciones automáticas sugeridas (ETL)',
        "en": 'Suggested automatic transformations (ETL)',
        "pt": 'Transformações automáticas sugeridas (ETL)',
    },
    "etl_ayuda": {
        "es": 'Cada una se probó sobre una copia del modelo: lo que dice «haría» es exactamente lo que va a hacer. Aprobá las que quieras, o todas.',
        "en": 'Each one was tried on a copy of the model: what it says it “would do” is exactly what it will do. Approve the ones you want, or all of them.',
        "pt": 'Cada uma foi testada numa cópia do modelo: o que diz que «faria» é exatamente o que vai fazer. Aprove as que quiser, ou todas.',
    },
    "etl_nada": {
        "es": 'No hay transformaciones automáticas pendientes: el modelo ya tiene todo lo que este programa sabe hacer solo.',
        "en": 'No automatic transformations pending: the model already has everything this program can do by itself.',
        "pt": 'Não há transformações automáticas pendentes: o modelo já tem tudo o que este programa sabe fazer sozinho.',
    },
    "etl_haria": {
        "es": 'haría {n} cambios',
        "en": 'would make {n} changes',
        "pt": 'faria {n} mudanças',
    },
    "etl_btn_elegidas": {
        "es": 'Aplicar las elegidas',
        "en": 'Apply the selected ones',
        "pt": 'Aplicar as escolhidas',
    },
    "etl_btn_todas": {
        "es": 'Aplicar todas',
        "en": 'Apply all',
        "pt": 'Aplicar todas',
    },
    "etl_ver_cambios": {
        "es": 'Ver qué haría',
        "en": 'See what it would do',
        "pt": 'Ver o que faria',
    },
    "an_kpis_elegir": {
        "es": 'Elegí cuáles agregar (o todos)',
        "en": 'Choose which to add (or all)',
        "pt": 'Escolha quais adicionar (ou todos)',
    },
    "an_kpis_btn_elegidos": {
        "es": 'Agregar los elegidos',
        "en": 'Add the selected ones',
        "pt": 'Adicionar os escolhidos',
    },
    "an_kpis_btn_todos": {
        "es": 'Agregar todos',
        "en": 'Add all',
        "pt": 'Adicionar todos',
    },

    # ---- Datasets DEMO incluidos (registro en dxl/demos.py) ----
    "demo_ofertas_titulo": {
        "es": "Ofertas en punto de venta",
        "en": "Point-of-sale promotions",
        "pt": "Ofertas no ponto de venda",
    },
    "demo_ofertas_desc": {
        "es": "Relevamiento mensual de presencia de ofertas en comercios: puntos de venta, canales, ofertas y calendario.",
        "en": "Monthly survey of promotion presence in stores: points of sale, channels, promotions and calendar.",
        "pt": "Levantamento mensal da presença de ofertas no comércio: pontos de venda, canais, ofertas e calendário.",
    },
    "demo_relevamiento_titulo": {
        "es": "Objetivos de relevamiento",
        "en": "Survey targets",
        "pt": "Metas de levantamento",
    },
    "demo_relevamiento_desc": {
        "es": "Auditoría de puntos de venta con cuestionario Sí/No, puntaje por pregunta y objetivos mensuales por distribuidor y canal.",
        "en": "Point-of-sale audit with a Yes/No questionnaire, a score per question and monthly targets per distributor and channel.",
        "pt": "Auditoria de pontos de venda com questionário Sim/Não, pontuação por pergunta e metas mensais por distribuidor e canal.",
    },
    "demo_farma_titulo": {
        "es": "Mercado farmacéutico",
        "en": "Pharmaceutical market",
        "pt": "Mercado farmacêutico",
    },
    "demo_farma_desc": {
        "es": "Médicos, productos propios y de la competencia, visitas, recetas, interacción digital y ventas de mercado para calcular share.",
        "en": "Physicians, own and competitor products, visits, prescriptions, digital interaction and market sales to compute share.",
        "pt": "Médicos, produtos próprios e da concorrência, visitas, receitas, interação digital e vendas de mercado para calcular share.",
    },
    "fmt_medida": {
        "es": 'Medida [{nombre}] formateada',
        "en": 'Measure [{nombre}] formatted',
        "pt": 'Medida [{nombre}] formatada',
    },
    "fmt_nada": {
        "es": 'Todas las medidas ya estaban formateadas',
        "en": 'All measures were already formatted',
        "pt": 'Todas as medidas já estavam formatadas',
    },
    "he_rep_titulo": {
        "es": 'Lo que esas herramientas hacen, hecho acá adentro',
        "en": 'What those tools do, done right here',
        "pt": 'O que essas ferramentas fazem, feito aqui dentro',
    },
    "he_rep_ayuda": {
        "es": 'No hace falta instalar nada: cada función se replica sobre el modelo cargado. Lo que necesita un motor de Analysis Services (medir tiempos, tamaño real en memoria) no se simula — se dice.',
        "en": 'Nothing to install: each function is replicated on the loaded model. What needs an Analysis Services engine (timings, real memory size) is not simulated — it is stated.',
        "pt": 'Não precisa instalar nada: cada função é replicada sobre o modelo carregado. O que precisa de um motor Analysis Services (tempos, tamanho real em memória) não se simula — se diz.',
    },
    "he_rep_dax_studio": {
        "es": 'DAX Studio · Bravo — Formatear DAX',
        "en": 'DAX Studio · Bravo — Format DAX',
        "pt": 'DAX Studio · Bravo — Formatar DAX',
    },
    "he_rep_formatear_ayuda": {
        "es": 'Funciones en mayúsculas, un argumento por línea cuando la llamada es larga, VAR/RETURN en su línea. Nunca cambia lo que calcula: si no puede garantizarlo, deja la medida como estaba.',
        "en": 'Uppercase functions, one argument per line when the call is long, VAR/RETURN on their own line. It never changes what it computes: when it cannot guarantee that, the measure is left as is.',
        "pt": 'Funções em maiúsculas, um argumento por linha quando a chamada é longa, VAR/RETURN na sua linha. Nunca muda o que calcula: se não puder garantir, deixa a medida como estava.',
    },
    "he_rep_formatear_btn": {
        "es": 'Formatear todas las medidas',
        "en": 'Format all measures',
        "pt": 'Formatar todas as medidas',
    },
    "he_rep_probar": {
        "es": 'Probá con una fórmula',
        "en": 'Try it on a formula',
        "pt": 'Teste com uma fórmula',
    },
    "he_rep_bravo": {
        "es": 'Bravo — Analizar el modelo',
        "en": 'Bravo — Analyze model',
        "pt": 'Bravo — Analisar o modelo',
    },
    "he_rep_bravo_ayuda": {
        "es": 'Filas y cardinalidad de lo que viaja adentro del archivo, y las columnas que nadie usa (ni medida, ni relación, ni visual).',
        "en": 'Rows and cardinality of what travels inside the file, and the columns nobody uses (no measure, relationship or visual).',
        "pt": 'Linhas e cardinalidade do que viaja dentro do arquivo, e as colunas que ninguém usa (nem medida, nem relação, nem visual).',
    },
    "he_rep_tabla": {
        "es": 'Tabla',
        "en": 'Table',
        "pt": 'Tabela',
    },
    "he_rep_filas": {
        "es": 'Filas adentro',
        "en": 'Rows inside',
        "pt": 'Linhas dentro',
    },
    "he_rep_pesadas": {
        "es": 'Columnas con más valores distintos',
        "en": 'Columns with most distinct values',
        "pt": 'Colunas com mais valores distintos',
    },
    "he_rep_sin_uso": {
        "es": 'Columnas sin uso: {n}',
        "en": 'Unused columns: {n}',
        "pt": 'Colunas sem uso: {n}',
    },
    "he_rep_sin_uso_nada": {
        "es": 'No hay columnas sin uso demostrable.',
        "en": 'No provably unused columns.',
        "pt": 'Não há colunas sem uso demonstrável.',
    },
    "he_rep_sin_uso_nota": {
        "es": 'Sin un reporte cargado solo se acusan las columnas ocultas: una visible puede estar en un visual que acá no se ve.',
        "en": 'Without a loaded report only hidden columns are flagged: a visible one may be in a visual not seen here.',
        "pt": 'Sem um relatório carregado só se acusam as colunas ocultas: uma visível pode estar num visual que aqui não se vê.',
    },
    "he_rep_exportar_datos": {
        "es": 'Bravo — Exportar los datos de una tabla (CSV)',
        "en": "Bravo — Export a table's data (CSV)",
        "pt": 'Bravo — Exportar os dados de uma tabela (CSV)',
    },
    "he_rep_sin_datos": {
        "es": 'Esa tabla no lleva datos adentro del archivo.',
        "en": 'That table carries no data inside the file.',
        "pt": 'Essa tabela não leva dados dentro do arquivo.',
    },
    "he_rep_alm": {
        "es": 'ALM Toolkit — Comparar antes y después',
        "en": 'ALM Toolkit — Compare before and after',
        "pt": 'ALM Toolkit — Comparar antes e depois',
    },
    "he_rep_alm_ayuda": {
        "es": 'Qué cambió en esta sesión entre el modelo como se cargó y como está ahora: tablas, columnas, medidas y relaciones agregadas, quitadas o modificadas.',
        "en": 'What changed this session between the model as loaded and as it is now: tables, columns, measures and relationships added, removed or modified.',
        "pt": 'O que mudou nesta sessão entre o modelo como foi carregado e como está agora: tabelas, colunas, medidas e relações adicionadas, removidas ou modificadas.',
    },
    "he_rep_sin_diferencias": {
        "es": 'Sin diferencias: el modelo está como se cargó.',
        "en": 'No differences: the model is as it was loaded.',
        "pt": 'Sem diferenças: o modelo está como foi carregado.',
    },
    "he_rep_agregadas": {
        "es": 'agregadas',
        "en": 'added',
        "pt": 'adicionadas',
    },
    "he_rep_quitadas": {
        "es": 'quitadas',
        "en": 'removed',
        "pt": 'removidas',
    },
    "he_rep_modificadas": {
        "es": 'modificadas',
        "en": 'modified',
        "pt": 'modificadas',
    },
    "he_rep_tabular": {
        "es": 'Tabular Editor — Best Practice Analyzer',
        "en": 'Tabular Editor — Best Practice Analyzer',
        "pt": 'Tabular Editor — Best Practice Analyzer',
    },
    "he_rep_tabular_ayuda": {
        "es": 'Es la pestaña Analizador: {n} hallazgos ahora, {auto} con arreglo automático. Las transformaciones del modelo (medidas, formatos, tabla de medidas, relaciones) están en Transformar y Relaciones.',
        "en": 'That is the Analyzer tab: {n} findings now, {auto} with an automatic fix. Model transformations (measures, formats, measure table, relationships) live in Transform and Relationships.',
        "pt": 'É a aba Analisador: {n} achados agora, {auto} com correção automática. As transformações do modelo (medidas, formatos, tabela de medidas, relações) estão em Transformar e Relações.',
    },
    "he_rep_pq": {
        "es": 'Power Query — ETL automático',
        "en": 'Power Query — Automatic ETL',
        "pt": 'Power Query — ETL automático',
    },
    "he_rep_pq_ayuda": {
        "es": 'Las transformaciones automáticas (calendario, tipos, columnas de período, claves ocultas…) se aprueban una por una en Transformar; las consultas M se ven y se bajan acá (consultas.m).',
        "en": 'Automatic transformations (calendar, types, period columns, hidden keys…) are approved one by one in Transform; the M queries are shown and downloaded here (consultas.m).',
        "pt": 'As transformações automáticas (calendário, tipos, colunas de período, chaves ocultas…) são aprovadas uma por uma em Transformar; as consultas M se veem e se baixam aqui (consultas.m).',
    },
    "demo_galeria_titulo": {
        "es": 'Datasets de demostración (100 % sintéticos)',
        "en": 'Demo datasets (100% synthetic)',
        "pt": 'Datasets de demonstração (100 % sintéticos)',
    },
    "demo_galeria_ayuda": {
        "es": 'Elegí uno y cargalo: el programa propone el modelo, infiere las relaciones y deja todo listo para transformar y exportar. Los datos son inventados.',
        "en": 'Pick one and load it: the program proposes the model, infers relationships and leaves everything ready to transform and export. The data is made up.',
        "pt": 'Escolha um e carregue: o programa propõe o modelo, infere as relações e deixa tudo pronto para transformar e exportar. Os dados são inventados.',
    },
    "demo_btn_cargar": {
        "es": 'Cargar este demo',
        "en": 'Load this demo',
        "pt": 'Carregar este demo',
    },
    "demo_tablas": {
        "es": '{n} tablas',
        "en": '{n} tables',
        "pt": '{n} tabelas',
    },
    "nlp_d_ruta": {
        "es": 'Armar la ruta de la entidad principal (sus contactos en orden: visitas, recetas, interacciones…) y sus medidas — la base de un informe 360',
        "en": "Build the main entity's route (its contacts in order: visits, prescriptions, interactions…) and its measures — the base of a 360 report",
        "pt": 'Montar a rota da entidade principal (seus contatos em ordem: visitas, receitas, interações…) e suas medidas — a base de um relatório 360',
    },
    "nlp_d_crear_tabla": {
        "es": 'Crear la tabla «{tabla}» · columnas: {cols} · relaciones: {rels} · medidas: {meds}',
        "en": 'Create table “{tabla}” · columns: {cols} · relationships: {rels} · measures: {meds}',
        "pt": 'Criar a tabela «{tabla}» · colunas: {cols} · relações: {rels} · medidas: {meds}',
    },
    "nlp_tabla_necesita_ia": {
        "es": '«{texto}»: para una tabla a medida activá «Interpretar con IA» (con tu clave) o pedí una de las plantillas: «tabla resumen por <columna>» o «tabla de parámetro de 0 a 100 paso 5»',
        "en": '“{texto}”: for a custom table enable “Interpret with AI” (with your key) or ask for one of the templates: “summary table by <column>” or “parameter table from 0 to 100 step 5”',
        "pt": '«{texto}»: para uma tabela sob medida ative «Interpretar com IA» (com sua chave) ou peça um dos modelos: «tabela resumo por <coluna>» ou «tabela de parâmetro de 0 a 100 passo 5»',
    },
    "tb_err_nombre": {
        "es": 'La tabla nueva necesita un nombre.',
        "en": 'The new table needs a name.',
        "pt": 'A tabela nova precisa de um nome.',
    },
    "tb_err_existe": {
        "es": 'Ya existe una tabla «{tabla}».',
        "en": 'A table “{tabla}” already exists.',
        "pt": 'Já existe uma tabela «{tabla}».',
    },
    "tb_err_dax": {
        "es": 'La tabla nueva necesita una expresión DAX de tabla.',
        "en": 'The new table needs a DAX table expression.',
        "pt": 'A tabela nova precisa de uma expressão DAX de tabela.',
    },
    "tb_err_sin_columnas": {
        "es": 'No se pudo leer qué columnas produce la expresión: usá SUMMARIZECOLUMNS, ADDCOLUMNS, SELECTCOLUMNS, DATATABLE, VALUES o GENERATESERIES.',
        "en": 'Could not read which columns the expression produces: use SUMMARIZECOLUMNS, ADDCOLUMNS, SELECTCOLUMNS, DATATABLE, VALUES or GENERATESERIES.',
        "pt": 'Não foi possível ler quais colunas a expressão produz: use SUMMARIZECOLUMNS, ADDCOLUMNS, SELECTCOLUMNS, DATATABLE, VALUES ou GENERATESERIES.',
    },
    "tb_err_relacion": {
        "es": 'Relación mal formada: {rel}',
        "en": 'Malformed relationship: {rel}',
        "pt": 'Relação malformada: {rel}',
    },
    "tb_err_col_nueva": {
        "es": 'La columna «{col}» no está entre las que produce la tabla «{tabla}».',
        "en": 'Column “{col}” is not among those produced by table “{tabla}”.',
        "pt": 'A coluna «{col}» não está entre as que a tabela «{tabla}» produz.',
    },
    "tb_err_col_ajena": {
        "es": 'No existe {obj} en el modelo.',
        "en": '{obj} does not exist in the model.',
        "pt": '{obj} não existe no modelo.',
    },
    "tb_err_medida": {
        "es": 'Medida mal formada (necesita nombre y dax): {med}',
        "en": 'Malformed measure (needs name and dax): {med}',
        "pt": 'Medida malformada (precisa de nome e dax): {med}',
    },
    "tb_err_medida_existe": {
        "es": 'Ya existe una medida «{med}».',
        "en": 'A measure “{med}” already exists.',
        "pt": 'Já existe uma medida «{med}».',
    },
    "tb_creada": {
        "es": 'Tabla «{tabla}» creada con {n} columnas ({cols})',
        "en": 'Table “{tabla}” created with {n} columns ({cols})',
        "pt": 'Tabela «{tabla}» criada com {n} colunas ({cols})',
    },
    "tb_rel_fallo": {
        "es": 'Relación {rel} NO creada: {motivo}',
        "en": 'Relationship {rel} NOT created: {motivo}',
        "pt": 'Relação {rel} NÃO criada: {motivo}',
    },
    "tb_med_fallo": {
        "es": 'Medida [{med}] NO creada: {motivo}',
        "en": 'Measure [{med}] NOT created: {motivo}',
        "pt": 'Medida [{med}] NÃO criada: {motivo}',
    },
    "tb_nombre_parametro": {
        "es": 'Parametro',
        "en": 'Parameter',
        "pt": 'Parametro',
    },
    "tb_medida_parametro": {
        "es": 'Valor {tabla}',
        "en": '{tabla} value',
        "pt": 'Valor {tabla}',
    },
    "tb_nombre_resumen": {
        "es": 'Resumen por {col}',
        "en": 'Summary by {col}',
        "pt": 'Resumo por {col}',
    },
    "pe_share_propia": {
        "es": 'Share {empresa} {base} %',
        "en": '{empresa} share {base} %',
        "pt": 'Share {empresa} {base} %',
    },
    "pe_share_propia_ant": {
        "es": 'Share {empresa} {base} {grano} AA %',
        "en": '{empresa} share {base} {grano} PY %',
        "pt": 'Share {empresa} {base} {grano} AA %',
    },
    "pe_share_propia_pp": {
        "es": 'Share {empresa} {base} {grano} var pp',
        "en": '{empresa} share {base} {grano} var pp',
        "pt": 'Share {empresa} {base} {grano} var pp',
    },
    "pe_pq_share_propia": {
        "es": 'La participación de {empresa} en el mercado de {base}: lo de {empresa} dividido el mercado total, valga lo que valga el filtro de corporación. En una tarjeta sin filtro NO da 100 %.',
        "en": "{empresa}'s share of the {base} market: {empresa}'s figure over the total market, regardless of any corporation filter. In an unfiltered card it does NOT show 100%.",
        "pt": 'A participação de {empresa} no mercado de {base}: o de {empresa} dividido pelo mercado total, seja qual for o filtro de corporação. Num cartão sem filtro NÃO dá 100 %.',
    },
    "pe_pq_share_propia_ant": {
        "es": 'El share de {empresa} en {base} del mismo {grano} del año anterior: numerador y denominador recalculados en ese período.',
        "en": "{empresa}'s share of {base} in the same {grano} of the prior year: numerator and denominator recomputed for that period.",
        "pt": 'O share de {empresa} em {base} no mesmo {grano} do ano anterior: numerador e denominador recalculados nesse período.',
    },
    "pe_pq_share_propia_pp": {
        "es": 'Cuánto subió o bajó el share de {empresa} en {base} contra el mismo {grano} del año anterior, en puntos porcentuales.',
        "en": "How much {empresa}'s share of {base} rose or fell versus the same {grano} of the prior year, in percentage points.",
        "pt": 'Quanto o share de {empresa} em {base} subiu ou caiu contra o mesmo {grano} do ano anterior, em pontos percentuais.',
    },
    "em_fijada": {
        "es": 'Empresa propia: «{empresa}». Las demás corporaciones son competencia; el share de {empresa} ya se puede calcular sin depender del filtro.',
        "en": "Own company: “{empresa}”. The other corporations are competitors; {empresa}'s share can now be computed regardless of the filter.",
        "pt": 'Empresa própria: «{empresa}». As demais corporações são concorrência; o share de {empresa} já pode ser calculado sem depender do filtro.',
    },
    "em_borrada": {
        "es": 'Empresa propia borrada del modelo.',
        "en": 'Own company removed from the model.',
        "pt": 'Empresa própria removida do modelo.',
    },
    "em_no_esta": {
        "es": '«{texto}» no es una de las corporaciones del dataset ({lista}). Elegí una de la lista o revisá la escritura.',
        "en": "“{texto}” is not one of the dataset's corporations ({lista}). Pick one from the list or check the spelling.",
        "pt": '«{texto}» não é uma das corporações do dataset ({lista}). Escolha uma da lista ou revise a grafia.',
    },
    "em_titulo": {
        "es": 'Empresa propia (la referente del share)',
        "en": 'Own company (the share reference)',
        "pt": 'Empresa própria (a referência do share)',
    },
    "em_ayuda": {
        "es": 'El dataset trae varias corporaciones. Decí cuál es la tuya: las demás pasan a ser competencia y aparece «Share <Empresa> %», que no da 100 % en una tarjeta sin filtro. Se guarda adentro del archivo.',
        "en": 'The dataset carries several corporations. Say which one is yours: the rest become competitors and “Share <Company> %” appears, which does not show 100% in an unfiltered card. It is saved inside the file.',
        "pt": 'O dataset traz várias corporações. Diga qual é a sua: as demais passam a ser concorrência e aparece «Share <Empresa> %», que não dá 100 % num cartão sem filtro. Fica salvo dentro do arquivo.',
    },
    "em_elegir": {
        "es": 'Elegí la empresa propia',
        "en": 'Choose the own company',
        "pt": 'Escolha a empresa própria',
    },
    "em_otra": {
        "es": 'Otra (escribirla)…',
        "en": 'Other (type it)…',
        "pt": 'Outra (digitar)…',
    },
    "em_escribir": {
        "es": 'Nombre exacto de la empresa',
        "en": 'Exact company name',
        "pt": 'Nome exato da empresa',
    },
    "em_btn_fijar": {
        "es": 'Usar esta empresa',
        "en": 'Use this company',
        "pt": 'Usar esta empresa',
    },
    "em_btn_ia": {
        "es": 'Detectar con IA',
        "en": 'Detect with AI',
        "pt": 'Detectar com IA',
    },
    "em_ia_sin_evidencia": {
        "es": 'La IA no encontró evidencia suficiente para elegir una: decila vos.',
        "en": 'The AI found no evidence to pick one: choose it yourself.',
        "pt": 'A IA não encontrou evidência suficiente para escolher uma: diga você.',
    },
    "em_detectada": {
        "es": 'Detectada por las medidas del modelo: «{empresa}»',
        "en": "Detected from the model's measures: “{empresa}”",
        "pt": 'Detectada pelas medidas do modelo: «{empresa}»',
    },
    "em_actual": {
        "es": 'Empresa propia actual: «{empresa}»',
        "en": 'Current own company: “{empresa}”',
        "pt": 'Empresa própria atual: «{empresa}»',
    },
    "em_sin_columna": {
        "es": 'Este modelo no tiene columna de corporación: no hay competencia que separar.',
        "en": 'This model has no corporation column: there is no competition to separate.',
        "pt": 'Este modelo não tem coluna de corporação: não há concorrência para separar.',
    },
    "nlp_d_empresa": {
        "es": 'Fijar la empresa propia: «{empresa}» (las demás corporaciones son competencia; habilita «Share {empresa} %»)',
        "en": 'Set the own company: “{empresa}” (the other corporations are competitors; enables “Share {empresa} %”)',
        "pt": 'Fixar a empresa própria: «{empresa}» (as demais corporações são concorrência; habilita «Share {empresa} %»)',
    },
    "tb_tema_competencia": {
        "es": 'Mercado y competencia',
        "en": 'Market and competition',
        "pt": 'Mercado e concorrência',
    },
    "tb_tabla_periodos": {
        "es": 'Hoy vs. año anterior, por período',
        "en": 'Today vs. prior year, by period',
        "pt": 'Hoje vs. ano anterior, por período',
    },
    "tb_tabla_competencia": {
        "es": 'Cada competidor: cuánto vende, qué parte se lleva y cuánto se movió',
        "en": 'Each competitor: how much they sell, what share they take and how much they moved',
        "pt": 'Cada concorrente: quanto vende, que parte leva e quanto se moveu',
    },
    "pe_ranking": {
        "es": 'Ranking {base}',
        "en": '{base} ranking',
        "pt": 'Ranking {base}',
    },
    "pe_pq_ranking": {
        "es": 'En qué puesto queda cada competidor por {base}, contra todo el mercado ({columna}): el 1 es el que más vende. Es la pregunta que sigue al share.',
        "en": 'Where each competitor ranks by {base} against the whole market ({columna}): 1 is the biggest seller. It is the question that follows share.',
        "pt": 'Em que posição fica cada concorrente por {base}, contra todo o mercado ({columna}): o 1 é o que mais vende. É a pergunta que segue o share.',
    },
}


def t(clave: str, idioma: str = IDIOMA_DEFECTO) -> str:
    """Devuelve el texto en el idioma pedido; cae a español si falta."""
    entrada = T.get(clave)
    if entrada is None:
        return clave
    return entrada.get(idioma) or entrada.get(IDIOMA_DEFECTO, clave)


def faltantes() -> dict[str, list[str]]:
    """Claves a las que les falta algún idioma. Vacío = paridad completa."""
    fallas = {}
    for clave, valores in T.items():
        sin = [i for i in IDIOMAS if not valores.get(i)]
        if sin:
            fallas[clave] = sin
    return fallas
