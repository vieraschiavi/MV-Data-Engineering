# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Qué se le hizo al dataset, en orden, y por qué.

**El problema.** El programa le hace quince cosas a un dataset antes de
entregar el `.pbit`. Quien lo recibe ve el resultado y no el camino: no
sabe que la tabla de fechas no estaba y se creó, ni por qué una columna
quedó oculta, ni qué garantiza que los números cierren. Cuando alguien
pregunta «¿y esto de dónde salió?», la respuesta hoy es abrir el modelo y
deducirlo.

**Qué arma este módulo.** La BITÁCORA del pipeline: una etapa por paso, en
el orden en que ocurren, y cada una contada dos veces —en técnico y en
criollo— más por qué existe y qué cambia aguas abajo. La misma página le
sirve al que va a mantener el modelo y al que firma.

**La regla que lo hace confiable.** El estado de cada etapa NO se asume:
se MIDE sobre el modelo entregado. Si el calendario está, es porque hay
una tabla marcada `dataCategory = Time`; si no está, la bitácora dice que
no está en vez de describir una etapa que nunca corrió. Un documento que
narra lo que el programa «suele hacer» es peor que no tener documento:
parece evidencia y no lo es.

Los textos viven en `i18n` con las tres claves de idioma, como todo lo que
ve un usuario. Acá solo está el orden, la detección y la evidencia.
"""
from __future__ import annotations

import re

from .catalogo import Catalogo
from .i18n import IDIOMA_DEFECTO, t as traducir

#: Estados posibles de una etapa.
APLICADA, SIN_APLICAR, SIN_DATOS = "aplicada", "sin_aplicar", "sin_datos"

#: Funciones DAX que solo aparecen cuando hay inteligencia de tiempo.
_RE_TIEMPO = re.compile(
    r"\b(TOTALYTD|TOTALQTD|SAMEPERIODLASTYEAR|DATEADD|DATESBETWEEN|"
    r"PARALLELPERIOD|DATESYTD)\s*\(", re.IGNORECASE)

#: Marca de los datos empotrados dentro de la expresión M.
_RE_EMPOTRADO = re.compile(r"Table\.FromRows|Binary\.Decompress")


def _texto_m(tabla: dict) -> str:
    salida = []
    for p in tabla.get("partitions", []) or []:
        expr = (p.get("source") or {}).get("expression")
        salida.append("\n".join(expr) if isinstance(expr, list) else str(expr or ""))
    return "\n".join(salida)


def _dax(m: dict) -> str:
    expr = m.get("expresion") or m.get("expression") or ""
    return "\n".join(expr) if isinstance(expr, list) else str(expr)


# ==========================================================================
# La detección: qué se puede afirmar mirando el modelo entregado
# ==========================================================================
def _det_origen(ctx) -> tuple[str, list[str]]:
    tablas = [t for t in ctx["tablas"] if not t.get("interna")]
    if not tablas:
        return SIN_APLICAR, []
    from .verificacion import conexion_de
    tipos: dict[str, int] = {}
    for t in ctx["modelo"].get("model", {}).get("tables", []):
        for p in t.get("partitions", []) or []:
            tipo = conexion_de((p.get("source") or {}).get("expression"))
            tipos[tipo] = tipos.get(tipo, 0) + 1
    return APLICADA, [f"{len(tablas)}", " · ".join(
        f"{k}: {v}" for k, v in sorted(tipos.items()))]


def _det_perfilado(ctx) -> tuple[str, list[str]]:
    tipadas = con_formato = 0
    for t in ctx["modelo"].get("model", {}).get("tables", []):
        for c in t.get("columns", []):
            if c.get("dataType") not in (None, "", "automatic"):
                tipadas += 1
            if c.get("formatString"):
                con_formato += 1
    estado = APLICADA if tipadas else SIN_APLICAR
    return estado, [str(tipadas), str(con_formato)]


def _det_relaciones(ctx) -> tuple[str, list[str]]:
    rels = ctx["modelo"].get("model", {}).get("relationships", []) or []
    bidi = sum(1 for r in rels
               if r.get("crossFilteringBehavior") == "bothDirections")
    return (APLICADA if rels else SIN_APLICAR), [str(len(rels)), str(bidi)]


def _det_correccion(ctx) -> tuple[str, list[str]]:
    ocultas = 0
    for t in ctx["modelo"].get("model", {}).get("tables", []):
        ocultas += sum(1 for c in t.get("columns", []) if c.get("isHidden"))
    return (APLICADA if ocultas else SIN_APLICAR), [str(ocultas)]


def _det_calendario(ctx) -> tuple[str, list[str]]:
    cal = ctx["cat"].tabla_fechas()
    if not cal:
        return SIN_APLICAR, []
    return APLICADA, [cal.get("nombre", "?"),
                      str(len(cal.get("columnas") or []))]


def _det_empresa(ctx) -> tuple[str, list[str]]:
    from .empresa import propia
    nombre = propia(ctx["modelo"])
    return (APLICADA, [nombre]) if nombre else (SIN_APLICAR, [])


def _det_kpis(ctx) -> tuple[str, list[str]]:
    base = [m for m in ctx["medidas"] if not _RE_TIEMPO.search(_dax(m))]
    return (APLICADA if base else SIN_APLICAR), [str(len(base))]


def _det_comparativos(ctx) -> tuple[str, list[str]]:
    tiempo = [m for m in ctx["medidas"] if _RE_TIEMPO.search(_dax(m))]
    carpetas = sorted({m.get("carpeta") for m in tiempo if m.get("carpeta")})
    return ((APLICADA if tiempo else SIN_APLICAR),
            [str(len(tiempo)), " · ".join(carpetas) or "—"])


def _det_derivadas(ctx) -> tuple[str, list[str]]:
    """Tablas que agregó el pipeline y que NO tienen su propia etapa.

    El calendario, el diccionario, la lectura y la tabla contenedora de
    medidas también son tablas que no venían en el origen — pero cada una
    ya se cuenta en su etapa. Listarlas otra vez acá haría que la bitácora
    dijera dos veces lo mismo con dos nombres distintos, que es la forma
    más barata de que un documento pierda credibilidad.
    """
    from .diccionario import TABLA as TABLA_DIC
    from .lectura import TABLA_LECTURA
    from .ruta import TABLA as TABLA_RUTA
    tablas = ctx["modelo"].get("model", {}).get("tables", [])
    nombres = {t.get("name") for t in tablas}
    cal = ctx["cat"].tabla_fechas() or {}
    con_etapa = {TABLA_DIC, TABLA_LECTURA, "_Medidas",
                 cal.get("nombre") or cal.get("name")}
    extras = {t.get("name") for t in tablas
              if any((p.get("source") or {}).get("type") == "calculated"
                     for p in t.get("partitions", []) or [])}
    if TABLA_RUTA in nombres:
        extras.add(TABLA_RUTA)
    extras = sorted(x for x in extras - con_etapa if x)
    return ((APLICADA if extras else SIN_APLICAR),
            [str(len(extras)), " · ".join(extras) or "—"])


def _det_diccionario(ctx) -> tuple[str, list[str]]:
    from .diccionario import TABLA
    tabla = next((t for t in ctx["modelo"].get("model", {}).get("tables", [])
                  if t.get("name") == TABLA), None)
    return (APLICADA, [TABLA]) if tabla else (SIN_APLICAR, [])


def _det_lectura(ctx) -> tuple[str, list[str]]:
    from .lectura import TABLA_LECTURA
    tabla = next((t for t in ctx["modelo"].get("model", {}).get("tables", [])
                  if t.get("name") == TABLA_LECTURA), None)
    return (APLICADA, [TABLA_LECTURA]) if tabla else (SIN_APLICAR, [])


def _det_tablero(ctx) -> tuple[str, list[str]]:
    layout = ctx.get("layout")
    if not layout:
        return SIN_DATOS, []
    secciones = layout.get("sections") or []
    visuales = sum(len(s.get("visualContainers") or []) for s in secciones)
    return APLICADA, [str(len(secciones)), str(visuales)]


def _det_empotrado(ctx) -> tuple[str, list[str]]:
    dentro = [t.get("name") for t in ctx["modelo"].get("model", {}).get("tables", [])
              if _RE_EMPOTRADO.search(_texto_m(t))]
    return ((APLICADA if dentro else SIN_APLICAR), [str(len(dentro))])


def _det_gobernanza(ctx) -> tuple[str, list[str]]:
    """La ficha se escribe AL EXPORTAR, no antes.

    El modelo que vive en memoria durante la sesión no la lleva: se la
    pone `preparar_para_desktop`, que corre cuando se escribe el archivo.
    Mirar solo el modelo daba «no aplicada» para un archivo entregado que
    sí la llevaba adentro — un falso negativo que hacía dudar de la única
    parte del documento que tiene que ser incuestionable. Cuando hay
    veredicto del gate, manda el gate: audita el archivo escrito.
    """
    from .gobernanza import leer
    manifiesto = leer(ctx["modelo"])
    if manifiesto:
        return APLICADA, [str(len(manifiesto.get("tablas") or [])),
                          str(len(manifiesto.get("medidas") or []))]
    verif = ctx.get("verificacion") or {}
    item = next((i for i in verif.get("items") or []
                 if i.get("clave") == "traspaso"), None)
    if item and item.get("estado") == "ok":
        cat = ctx["cat"]
        return APLICADA, [str(len([t for t in cat.tablas])),
                          str(len(cat.medidas()))]
    return SIN_APLICAR, []


def _det_gate(ctx) -> tuple[str, list[str]]:
    verif = ctx.get("verificacion")
    if not verif:
        return SIN_DATOS, []
    return APLICADA, [str(len(verif.get("items") or [])),
                      str(verif.get("faltan", 0)), str(verif.get("avisos", 0))]


# ==========================================================================
# El orden del pipeline
# ==========================================================================
#: `(clave, detector, [modulos])`. La clave manda: los cuatro textos de
#: cada etapa viven en i18n como `bit_<clave>_titulo`, `_tec`, `_criollo`,
#: `_porque` e `_impacto`, y la evidencia como `bit_<clave>_ev`.
ETAPAS: tuple[tuple[str, object, tuple[str, ...]], ...] = (
    ("origen", _det_origen, ("dataset", "origenes")),
    ("perfilado", _det_perfilado, ("dataset", "analizador")),
    ("relaciones", _det_relaciones, ("relaciones",)),
    ("correccion", _det_correccion, ("corrector", "transformador")),
    ("calendario", _det_calendario, ("transformador", "periodos")),
    ("empresa", _det_empresa, ("empresa",)),
    ("kpis", _det_kpis, ("kpis",)),
    ("comparativos", _det_comparativos, ("periodos",)),
    ("derivadas", _det_derivadas, ("tablas", "ruta")),
    ("diccionario", _det_diccionario, ("diccionario",)),
    ("lectura", _det_lectura, ("lectura", "analitica")),
    ("tablero", _det_tablero, ("tablero", "roles", "jerarquia", "pbir")),
    ("empotrado", _det_empotrado, ("dataset",)),
    ("gobernanza", _det_gobernanza, ("gobernanza",)),
    ("gate", _det_gate, ("verificacion",)),
)


def construir(modelo: dict, layout: dict | None = None,
              verificacion: dict | None = None,
              historial: list[str] | None = None,
              idioma: str = IDIOMA_DEFECTO) -> dict:
    """La bitácora completa: cabecera, etapas en orden e historial real.

    `historial` son los cambios que la sesión aplicó de verdad, tal como
    los devolvió cada acción. Va aparte de las etapas a propósito: las
    etapas explican el pipeline, el historial dice qué se tocó en ESTA
    corrida. Mezclarlos haría que una etapa no aplicada pareciera aplicada
    porque «el programa la tiene».
    """
    cat = Catalogo.desde_modelo(modelo)
    ctx = {"modelo": modelo, "cat": cat, "tablas": cat.tablas,
           "medidas": cat.medidas(), "layout": layout,
           "verificacion": verificacion}

    etapas = []
    for orden, (clave, detector, modulos) in enumerate(ETAPAS, 1):
        try:
            estado, datos = detector(ctx)
        except Exception:                                 # noqa: BLE001
            # Una etapa que no se puede medir se declara sin datos, no se
            # inventa: la bitácora vale por lo que afirma con evidencia.
            estado, datos = SIN_DATOS, []
        evidencia = ""
        if estado == APLICADA:
            plantilla = traducir(f"bit_{clave}_ev", idioma)
            try:
                evidencia = plantilla.format(*datos)
            except (IndexError, KeyError):
                evidencia = " · ".join(str(d) for d in datos)
        etapas.append({
            "orden": orden,
            "clave": clave,
            "titulo": traducir(f"bit_{clave}_titulo", idioma),
            "tecnico": traducir(f"bit_{clave}_tec", idioma),
            "criollo": traducir(f"bit_{clave}_criollo", idioma),
            "porque": traducir(f"bit_{clave}_porque", idioma),
            "impacto": traducir(f"bit_{clave}_impacto", idioma),
            "estado": estado,
            "estado_texto": traducir(f"bit_estado_{estado}", idioma),
            "evidencia": evidencia,
            "modulos": list(modulos),
        })

    aplicadas = sum(1 for e in etapas if e["estado"] == APLICADA)
    return {
        "etapas": etapas,
        "historial": list(historial or []),
        "resumen": {
            "etapas": len(etapas),
            "aplicadas": aplicadas,
            "tablas": len([t for t in cat.tablas if not t.get("interna")]),
            "medidas": len(cat.medidas()),
            "relaciones": len(modelo.get("model", {}).get("relationships", []) or []),
            "paginas": len((layout or {}).get("sections") or []),
        },
    }


# ==========================================================================
# La bitácora como documento
# ==========================================================================
def documento(bit: dict, titulo: str = "", idioma: str = IDIOMA_DEFECTO):
    """Traduce la bitácora a los bloques de `documento.py`.

    Un solo armado para los tres formatos: si el HTML y el Word se
    escribieran por separado, el día que alguien agregue una etapa uno de
    los dos queda viejo y nadie se entera hasta que lo lee un cliente.
    """
    r = bit["resumen"]
    doc: list[tuple] = [
        ("p", traducir("bit_intro", idioma)),
        ("kv", [
            (traducir("bit_r_etapas", idioma), f'{r["aplicadas"]}/{r["etapas"]}'),
            (traducir("bit_r_tablas", idioma), r["tablas"]),
            (traducir("bit_r_medidas", idioma), r["medidas"]),
            (traducir("bit_r_relaciones", idioma), r["relaciones"]),
            (traducir("bit_r_paginas", idioma), r["paginas"]),
        ]),
        ("h3", traducir("bit_mapa", idioma)),
        ("tabla",
         [traducir("bit_c_paso", idioma), traducir("bit_c_etapa", idioma),
          traducir("bit_c_estado", idioma), traducir("bit_c_evidencia", idioma)],
         [[e["orden"], e["titulo"], e["estado_texto"], e["evidencia"] or "—"]
          for e in bit["etapas"]]),
        ("salto",),
    ]
    for e in bit["etapas"]:
        doc.append(("h2", e["titulo"], str(e["orden"])))
        doc.append(("kv", [
            (traducir("bit_c_estado", idioma),
             f'{e["estado_texto"]}{" · " + e["evidencia"] if e["evidencia"] else ""}'),
            (traducir("bit_c_modulos", idioma),
             " · ".join(f"dxl/{m}.py" for m in e["modulos"])),
        ]))
        doc.append(("h3", traducir("bit_h_tecnico", idioma)))
        doc.append(("p", e["tecnico"]))
        doc.append(("h3", traducir("bit_h_criollo", idioma)))
        doc.append(("p", e["criollo"]))
        doc.append(("h3", traducir("bit_h_porque", idioma)))
        doc.append(("p", e["porque"]))
        doc.append(("h3", traducir("bit_h_impacto", idioma)))
        doc.append(("p", e["impacto"]))

    if bit["historial"]:
        doc.append(("salto",))
        doc.append(("h2", traducir("bit_historial", idioma), ""))
        doc.append(("p", traducir("bit_historial_intro", idioma)))
        doc.append(("lista", list(bit["historial"])))
    return doc
