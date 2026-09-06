# © 2026 Martín Viera. Todos los derechos reservados.
"""Relevamiento con el cliente: las preguntas que hay que hacer antes de escribir
una línea de código, separadas por etapa del pipeline.

Cada pregunta guarda quién la respondió, de qué área, qué dijo y cuándo. Dos
cosas la separan de un cuestionario en Word:

  - **Repreguntas.** Una respuesta vaga («depende», «más o menos semanal») no es
    una respuesta: es una reunión más en tres semanas. El módulo detecta la
    forma de la respuesta y propone qué volver a preguntar, con o sin IA.
  - **Puente al YAML.** Las respuestas que tienen una traducción sin ambigüedad
    (el dueño del dato, la frecuencia de carga) se proponen como cambios
    concretos del proyecto. El relevamiento configura el pipeline, no lo
    acompaña.

Las respuestas viven en `relevamiento.json`, al lado del YAML del proyecto, así
viajan con él.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from .i18n import t
from .textos_relevamiento import PREGUNTAS, ROLES  # noqa: F401  (ROLES se usa desde la app)

ESTADOS = ("pendiente", "respondida", "no_aplica", "repreguntar")
ARCHIVO = "relevamiento.json"

# Señales de que la respuesta todavía no cierra nada.
_INCERTIDUMBRE = re.compile(
    r"\b(no s[eé]|ni idea|creo que|me parece|habr[íi]a que ver|hay que preguntar|no estoy seguro|"
    r"capaz|quiz[áa]s?|tal vez|i think|not sure|i don't know|maybe|n[ãa]o sei|acho que|talvez)\b", re.I)
_DEPENDE = re.compile(r"\b(depende|var[íi]a|seg[úu]n el caso|it depends|varies|depende do caso)\b", re.I)
_PIDE_NUMERO = re.compile(
    r"(cu[áa]nt|cada cu[áa]nto|qu[ée] hora|desde qu[ée] fecha|how many|how much|how often|what time|"
    r"from what date|quant|de quanto em quanto|que horas)", re.I)
_TIENE_NUMERO = re.compile(r"\d")
_SISTEMA = re.compile(r"\b(sap|oracle|salesforce|dynamics|siebel|as/?400|mainframe|erp|crm|sql server|"
                      r"postgres|mysql|snowflake|bigquery|redshift|sistema)\b", re.I)
_ACCESO = re.compile(r"\b(usuario|user|api|sftp|ftp|vista|view|export|exportaci[óo]n|permiso|credencial|"
                     r"read.?only|solo lectura|s[óo]lo lectura|conexi[óo]n|acesso|acceso)\b", re.I)

_FRECUENCIAS = [
    ("horaria", r"\b(cada hora|por hora|hourly|de hora em hora)\b"),
    ("diaria", r"\b(diari[ao]|todos los d[íi]as|daily|every day|di[áa]ri[ao]|todo dia)\b"),
    ("semanal", r"\b(semanal|cada semana|weekly|por semana)\b"),
    ("quincenal", r"\b(quincenal|cada quince d[íi]as|biweekly|quinzenal)\b"),
    ("mensual", r"\b(mensual|cada mes|monthly|por mes|mensal)\b"),
]
_HORA = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")


# ------------------------------------------------------------------ catálogo
def catalogo(lang: str = "es") -> list[dict]:
    """Las preguntas en orden, con su etapa, su por qué y a quién preguntarle."""
    return [{"id": f"{etapa}_{clave}", "etapa": etapa, "clave": clave, "rol": rol,
             "rol_texto": t(f"rol_{rol}", lang),
             "pregunta": t(f"rq_{etapa}_{clave}", lang),
             "porque": t(f"rq_{etapa}_{clave}_por", lang)}
            for etapa, clave, rol in PREGUNTAS]


def por_etapa(lang: str = "es") -> dict[str, list[dict]]:
    salida: dict[str, list[dict]] = {}
    for q in catalogo(lang):
        salida.setdefault(q["etapa"], []).append(q)
    return salida


# ------------------------------------------------------------------ archivo
def ruta_de(spec: dict) -> Path:
    """Al lado del YAML del proyecto; si el proyecto no tiene ruta, en la salida."""
    base = spec.get("_base") or "."
    return Path(base) / ARCHIVO


def vacio(cliente: str = "") -> dict:
    return {"cliente": cliente, "actualizado": "", "respuestas": {}}


def cargar(ruta: str | Path) -> dict:
    p = Path(ruta)
    if not p.exists():
        return vacio()
    try:
        datos = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return vacio()
    datos.setdefault("respuestas", {})
    datos.setdefault("cliente", "")
    return datos


def guardar(datos: dict, ruta: str | Path) -> Path:
    p = Path(ruta)
    salida = dict(datos)
    salida["actualizado"] = datetime.now().isoformat(timespec="seconds")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def responder(datos: dict, id_pregunta: str, respuesta: str, responsable: str = "",
              area: str = "", estado: str = "", notas: str = "") -> dict:
    """Devuelve una copia con la respuesta cargada. No muta el original."""
    nuevo = deepcopy(datos)
    texto = (respuesta or "").strip()
    nuevo.setdefault("respuestas", {})[id_pregunta] = {
        **nuevo.get("respuestas", {}).get(id_pregunta, {}),
        "respuesta": texto, "responsable": (responsable or "").strip(), "area": (area or "").strip(),
        "notas": (notas or "").strip(),
        "estado": estado or ("respondida" if texto else "pendiente"),
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    return nuevo


def avance(datos: dict, lang: str = "es") -> list[dict]:
    """Cuántas preguntas cerradas por etapa. Es el semáforo del relevamiento."""
    respuestas = datos.get("respuestas") or {}
    filas = []
    for etapa, preguntas in por_etapa(lang).items():
        cerradas = sum(1 for q in preguntas
                       if (respuestas.get(q["id"], {}).get("estado")) in ("respondida", "no_aplica"))
        filas.append({"etapa": etapa, "titulo": t(f"st_{etapa}", lang), "total": len(preguntas),
                      "respondidas": cerradas,
                      "pct": round(100 * cerradas / len(preguntas), 1) if preguntas else 0.0})
    return filas


# ------------------------------------------------------------------ repreguntas
def repreguntas_locales(pregunta: str, respuesta: str, responsable: str = "", lang: str = "es") -> list[str]:
    """Sin IA: mira la FORMA de la respuesta, no el tema. Detecta lo que hace que
    una respuesta no sirva para decidir nada."""
    texto = (respuesta or "").strip()
    salida: list[str] = []
    if not texto:
        return [t("rp_sin_respuesta", lang)]
    if len(texto) < 20:
        salida.append(t("rp_muy_corta", lang))
    if _INCERTIDUMBRE.search(texto):
        salida.append(t("rp_incertidumbre", lang))
    if _DEPENDE.search(texto):
        salida.append(t("rp_depende", lang))
    if _PIDE_NUMERO.search(pregunta or "") and not _TIENE_NUMERO.search(texto):
        salida.append(t("rp_falta_numero", lang))
    if _SISTEMA.search(texto) and not _ACCESO.search(texto):
        salida.append(t("rp_sistema_sin_acceso", lang))
    if not (responsable or "").strip():
        salida.append(t("rp_sin_responsable", lang))
    return salida


_SISTEMA_IA = ("Sos analista de datos relevando a un cliente para un pipeline de ingeniería de datos. "
               "Te dan una pregunta del relevamiento y la respuesta que dio el cliente. "
               "Devolvé entre 2 y 4 REPREGUNTAS concretas y cortas que hagan falta para poder decidir "
               "la implementación: lo que la respuesta deja sin definir. Nada de cortesías ni preámbulo. "
               "Una repregunta por línea, empezando con «- ». Si la respuesta ya alcanza para decidir, "
               "devolvé una sola línea: «- (la respuesta alcanza)».")


def repreguntas(pregunta: str, respuesta: str, porque: str = "", responsable: str = "", lang: str = "es",
                proveedor: str = "", modelo: str = "", api_key: str | None = None, endpoint: str = "") -> dict:
    """Con proveedor de IA configurado, repreguntas específicas del tema; sin él,
    las locales por forma de la respuesta. Siempre devuelve algo."""
    locales = repreguntas_locales(pregunta, respuesta, responsable, lang)
    from . import ia
    if not proveedor or not ia.hay_clave(proveedor, api_key) or not ia.disponible():
        return {"repreguntas": locales, "modo": "local"}
    mensaje = (f"Pregunta del relevamiento: {pregunta}\n"
               f"Para qué sirve la respuesta: {porque}\n"
               f"Respuesta del cliente: {respuesta or '(sin responder)'}\n"
               f"Idioma de la salida: {lang}")
    try:
        texto = ia._dxl().consultar([{"role": "user", "content": mensaje}], sistema=_SISTEMA_IA,
                                    proveedor=proveedor, modelo=modelo, api_key=api_key,
                                    endpoint=endpoint, max_tokens=400)
    except Exception as exc:  # noqa: BLE001 - la IA es aditiva: si falla, quedan las locales
        return {"repreguntas": locales, "modo": "local", "error": str(exc).splitlines()[0]}
    de_ia = [ln.strip(" -•\t") for ln in texto.splitlines() if ln.strip().startswith(("-", "•"))]
    de_ia = [x for x in de_ia if x and not x.startswith("(")]
    return {"repreguntas": de_ia or locales, "modo": f"{proveedor}/{modelo or 'defecto'}",
            "locales": locales}


def guardar_repreguntas(datos: dict, id_pregunta: str, lista: list[str]) -> dict:
    nuevo = deepcopy(datos)
    fila = nuevo.setdefault("respuestas", {}).setdefault(id_pregunta, {})
    fila["repreguntas"] = list(lista)
    if lista:
        fila.setdefault("estado", "pendiente")
    return nuevo


# ------------------------------------------------------------------ puente al YAML
def _frecuencia(texto: str) -> str | None:
    for nombre, patron in _FRECUENCIAS:
        if re.search(patron, texto or "", re.I):
            return nombre
    return None


def sugerencias_yaml(datos: dict, lang: str = "es") -> list[dict]:
    """Respuestas que se traducen al YAML sin interpretación. Sólo las que tienen
    una lectura única: el resto queda como nota para el que implementa."""
    r = datos.get("respuestas") or {}
    salida: list[dict] = []

    dueno = (r.get("gobernanza_dueno_dato", {}).get("respuesta") or "").strip()
    if dueno and len(dueno) < 120:
        salida.append({"campo": "gobernanza.dueno", "valor": dueno,
                       "parche": {"dueno": dueno}, "origen": "gobernanza_dueno_dato"})

    for clave in ("entrega_frecuencia", "powerbi_refresco"):
        texto = (r.get(clave, {}).get("respuesta") or "")
        frec = _frecuencia(texto)
        if frec:
            salida.append({"campo": "frescura.cada", "valor": frec,
                           "parche": {"frescura_cada": frec}, "origen": clave})
            break

    hora = _HORA.search((r.get("entrega_frecuencia", {}).get("respuesta") or ""))
    if hora:
        valor = f"{int(hora.group(1)):02d}:{hora.group(2)}"
        salida.append({"campo": "automatizacion.hora", "valor": valor,
                       "parche": {"hora": valor}, "origen": "entrega_frecuencia"})

    pii = (r.get("gobernanza_pii", {}).get("respuesta") or "")
    columnas = re.findall(r"\b([a-z_]{3,}(?:\.[a-z_]{3,})?)\b", pii.lower())
    columnas = [c for c in columnas if c not in {"los", "las", "campos", "datos", "personales", "que",
                                                 "and", "the", "fields", "data", "personal", "dados",
                                                 "pessoais", "campos", "nadie", "puede", "ver"}]
    if columnas:
        salida.append({"campo": "gobernanza.pii", "valor": ", ".join(dict.fromkeys(columnas))[:200],
                       "parche": {"pii": list(dict.fromkeys(columnas))[:12]}, "origen": "gobernanza_pii"})
    return salida


def aplicar_sugerencia(spec: dict, sugerencia: dict) -> dict:
    """Copia del spec con el cambio aplicado. No muta el original."""
    s = deepcopy(spec)
    p = sugerencia.get("parche") or {}
    if "dueno" in p:
        s.setdefault("gobernanza", {})["dueno"] = p["dueno"]
    if "pii" in p:
        g = s.setdefault("gobernanza", {})
        g["pii"] = sorted(set(g.get("pii") or []) | set(p["pii"]))
    if "frescura_cada" in p:
        s.setdefault("frescura", {})["cada"] = p["frescura_cada"]
    if "hora" in p:
        s.setdefault("automatizacion", {})["hora"] = p["hora"]
    return s


# ------------------------------------------------------------------ salida
def filas(datos: dict, lang: str = "es") -> list[dict]:
    """El relevamiento entero como tabla, para exportar o mostrar."""
    r = datos.get("respuestas") or {}
    out = []
    for q in catalogo(lang):
        d = r.get(q["id"], {})
        out.append({
            "etapa": t(f"st_{q['etapa']}", lang), "id": q["id"],
            "pregunta": q["pregunta"], "porque": q["porque"], "rol": q["rol_texto"],
            "respuesta": d.get("respuesta", ""), "responsable": d.get("responsable", ""),
            "area": d.get("area", ""), "estado": d.get("estado", "pendiente"),
            "fecha": d.get("fecha", ""), "repreguntas": " · ".join(d.get("repreguntas") or []),
            "notas": d.get("notas", ""),
        })
    return out


def markdown(datos: dict, lang: str = "es") -> str:
    av = avance(datos, lang)
    cerradas = sum(a["respondidas"] for a in av)
    total = sum(a["total"] for a in av)
    lineas = [f"# {t('rv_titulo', lang)}" + (f" · {datos.get('cliente')}" if datos.get("cliente") else ""), "",
              f"{cerradas}/{total} · {datos.get('actualizado', '')}", ""]
    etapa_actual = None
    for f in filas(datos, lang):
        if f["etapa"] != etapa_actual:
            etapa_actual = f["etapa"]
            lineas += ["", f"## {etapa_actual}", ""]
        lineas.append(f"**{f['pregunta']}**")
        lineas.append(f"<sub>{t('rv_why', lang)} {f['porque']} · {t('rv_ask', lang)} {f['rol']}</sub>")
        lineas.append("")
        lineas.append(f"- {t('rv_answer', lang)}: {f['respuesta'] or '—'}")
        quien = f"{f['responsable']}{' (' + f['area'] + ')' if f['area'] else ''}" if f["responsable"] else "—"
        lineas.append(f"- {t('rv_who', lang)}: {quien}")
        if f["repreguntas"]:
            lineas.append(f"- {t('rv_followups', lang)}: {f['repreguntas']}")
        if f["notas"]:
            lineas.append(f"- {t('rv_notes', lang)}: {f['notas']}")
        lineas.append("")
    return "\n".join(lineas) + "\n"


def excel(ruta: str | Path, datos: dict, lang: str = "es") -> Path:
    """Una hoja por etapa, para mandárselo al cliente y que lo complete."""
    import pandas as pd
    p = Path(ruta)
    p.parent.mkdir(parents=True, exist_ok=True)
    todas = filas(datos, lang)
    with pd.ExcelWriter(p, engine="xlsxwriter") as w:
        pd.DataFrame(avance(datos, lang)).to_excel(w, sheet_name="Avance", index=False)
        for etapa in dict.fromkeys(f["etapa"] for f in todas):
            hoja = re.sub(r"[\\/*?:\[\]]", "", etapa)[:31]
            pd.DataFrame([f for f in todas if f["etapa"] == etapa]).to_excel(w, sheet_name=hoja, index=False)
    return p
