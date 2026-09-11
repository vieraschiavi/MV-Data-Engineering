# © 2026 Martín Viera. Todos los derechos reservados.
"""Reuniones: de la minuta a decisiones del pipeline.

Esto NO es una herramienta de reuniones. Es el puente entre lo que se dijo en
una reunión de relevamiento y las 12 etapas del pipeline, y ese puente es lo
único que hace acá que Teams, Zoom o cualquier transcriptor no haga mejor.

La entrada es **la transcripción que ya generó la plataforma**: Teams, Zoom,
Meet y WebEx exportan `.vtt` con el nombre de quien habla y el minuto exacto.
Es la mejor fuente que existe, no necesita clave de IA ni conexión, y quién
dijo qué viene resuelto de fábrica. También se acepta texto pegado a mano.

**Por qué no transcribe audio.** Lo hacía, contra OpenAI o Groq, y se sacó a
propósito por tres razones que se suman:

  1. El audio de una reunión con el cliente es el dato más sensible de todo el
     proyecto. Subirlo a un tercero para ahorrar un paso manual no es un
     intercambio que valga la pena, y en el perfil confidencial estaba
     bloqueado de todas formas.
  2. La transcripción de audio suelto **no separa hablantes**: devolvía el texto
     con sus tiempos y quién habló se asignaba a mano. Una minuta de
     relevamiento sin «quién dijo qué» pierde justamente lo que la hace servir.
  3. Todas las plataformas que el cliente ya usa generan el `.vtt` gratis,
     offline y CON hablantes. Competir con eso era perder por decisión propia.

La minuta sale de la transcripción con reglas, sin IA: participantes y cuánto
habló cada uno, decisiones, compromisos, preguntas abiertas, riesgos y menciones
por etapa del pipeline, cada cosa con la cita y el minuto de donde salió. Con
un proveedor de IA configurado se agrega un resumen ejecutivo por encima, nunca
en lugar de la evidencia.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

FORMATOS_TEXTO = ("vtt", "srt", "txt", "md")

# Términos que atan una frase a una etapa del pipeline. Mezcla los tres idiomas a
# propósito: en una reunión real se habla mitad y mitad.
PALABRAS_ETAPA: dict[str, tuple[str, ...]] = {
    "fuentes": ("sap", "erp", "crm", "origen", "source", "fonte", "base de datos", "database", "api",
                "planilla", "excel", "csv", "sftp", "archivo", "file", "extracción", "extraction"),
    "bronze": ("crudo", "raw", "histórico", "history", "retención", "retention", "backup", "respaldo",
               "reproceso", "reprocess"),
    "silver": ("limpieza", "cleansing", "transformación", "transform", "duplicado", "duplicate",
               "código", "codigo", "equivalencia", "mapeo", "mapping", "anulado", "filtro", "filter"),
    "calidad": ("calidad", "quality", "error", "inconsistencia", "validación", "validation", "control",
                "cuadrar", "conciliar", "reconcile", "falta", "vacío", "nulo", "null"),
    "gold": ("dimensión", "dimension", "hecho", "fact", "granularidad", "grain", "jerarquía", "hierarchy",
             "modelo", "model", "estrella", "star", "calendario", "calendar", "histórico de cambios"),
    "almacen": ("warehouse", "almacén", "servidor", "server", "base corporativa", "lago", "lake",
                "publicar", "publish", "ventana", "window"),
    "gobernanza": ("gobernanza", "governance", "dueño", "owner", "pii", "dato personal", "personal data",
                   "permiso", "acceso", "access", "auditoría", "audit", "normativa", "regulación",
                   "confidencial", "sensible"),
    "ml": ("modelo", "predic", "machine learning", "score", "probabilidad", "probability", "algoritmo",
           "entrenar", "train", "target", "objetivo"),
    "reporte": ("reporte", "report", "kpi", "indicador", "métrica", "metric", "tablero", "dashboard",
                "fórmula", "formula", "informe"),
    "dax": ("dax", "medida", "measure", "cálculo", "calculo", "mes anterior", "año anterior",
            "acumulado", "year to date", "ytd"),
    "powerbi": ("power bi", "powerbi", "tableau", "licencia", "license", "workspace", "espacio de trabajo",
                "publicación", "refresco", "refresh"),
    "entrega": ("automatizar", "automation", "frecuencia", "frequency", "horario", "schedule", "cron",
                "producción", "production", "responsable", "soporte", "support", "entrega", "deploy"),
}

_DECISION = re.compile(
    r"\b(decidimos|queda (?:definido|acordado|así)|acordamos|vamos a|se define|definimos|"
    r"confirmamos|arrancamos con|optamos por|we (?:agreed|decided|will)|let's go with|"
    r"ficou (?:definido|acordado)|decidimos que)\b", re.I)
_COMPROMISO = re.compile(
    r"\b(me encargo|yo lo hago|yo (?:te )?(?:paso|mando|env[íi]o)|te (?:paso|mando|env[íi]o)|"
    r"queda pendiente|nos queda|lo vemos|voy a (?:armar|mandar|pedir|revisar)|"
    r"i'?ll (?:send|check|share|ask)|i will|vou (?:mandar|passar|ver))\b", re.I)
_RIESGO = re.compile(
    r"\b(problema|riesgo|no tenemos|no existe|no hay|falta|complicado|bloquea|traba|"
    r"risk|issue|blocker|we don'?t have|missing|problema|risco|n[ãa]o temos)\b", re.I)
_FECHA_TEXTO = re.compile(
    r"\b(hoy|mañana|el lunes|el martes|el mi[ée]rcoles|el jueves|el viernes|la semana que viene|"
    r"pr[óo]xima semana|fin de mes|\d{1,2}/\d{1,2}(?:/\d{2,4})?|next week|tomorrow|"
    r"pr[óo]xima semana|semana que vem)\b", re.I)

_VTT_TIEMPO = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")
_VTT_HABLANTE = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>)?\s*$", re.I | re.S)
_LINEA_HABLANTE = re.compile(r"^\s*([A-ZÁÉÍÓÚÑ][\w .'À-ɏ-]{1,40}?)\s*:\s+(.*)$")

_VACIAS = {"que", "los", "las", "del", "una", "por", "con", "para", "como", "esta", "este", "hay",
           "the", "and", "for", "with", "that", "this", "from", "are", "was", "have",
           "uma", "para", "com", "isso", "mas", "não", "sim", "the"}


# ------------------------------------------------------------------ parseo
def _segundos(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parsear(texto: str, nombre: str = "") -> list[dict]:
    """Transcripción a turnos. Reconoce WebVTT y SRT (Teams, Zoom, Meet, WebEx) y
    el texto plano con «Nombre: lo que dijo»."""
    if not (texto or "").strip():
        return []
    limpio = texto.replace("\r\n", "\n").replace("\r", "\n")
    if limpio.lstrip().upper().startswith("WEBVTT") or _VTT_TIEMPO.search(limpio):
        return _fusionar(_parsear_vtt(limpio))
    return _fusionar(_parsear_plano(limpio))


def _parsear_vtt(texto: str) -> list[dict]:
    turnos = []
    for bloque in re.split(r"\n\s*\n", texto):
        m = _VTT_TIEMPO.search(bloque)
        if not m:
            continue
        inicio = _segundos(*m.group(1, 2, 3, 4))
        fin = _segundos(*m.group(5, 6, 7, 8))
        cuerpo = bloque[m.end():].strip()
        # Las líneas de índice numérico de SRT no son texto de nadie.
        cuerpo = "\n".join(ln for ln in cuerpo.splitlines() if not ln.strip().isdigit())
        hablante = None
        v = _VTT_HABLANTE.search(cuerpo)
        if v:
            hablante, cuerpo = v.group(1).strip(), v.group(2).strip()
        else:
            ln = _LINEA_HABLANTE.match(cuerpo.split("\n")[0])
            if ln:
                hablante = ln.group(1).strip()
                cuerpo = "\n".join([ln.group(2)] + cuerpo.split("\n")[1:])
        cuerpo = re.sub(r"<[^>]+>", "", cuerpo).strip()
        if cuerpo:
            turnos.append({"hablante": hablante, "inicio": inicio, "fin": fin, "texto": cuerpo})
    return turnos


def _parsear_plano(texto: str) -> list[dict]:
    turnos = []
    for linea in texto.split("\n"):
        if not linea.strip():
            continue
        m = _LINEA_HABLANTE.match(linea)
        if m:
            turnos.append({"hablante": m.group(1).strip(), "inicio": None, "fin": None,
                           "texto": m.group(2).strip()})
        elif turnos:
            turnos[-1]["texto"] += " " + linea.strip()
        else:
            turnos.append({"hablante": None, "inicio": None, "fin": None, "texto": linea.strip()})
    return turnos


def _fusionar(turnos: list[dict]) -> list[dict]:
    """Une los subtítulos consecutivos del mismo hablante: un VTT parte la frase
    cada pocos segundos y eso no es un turno de conversación."""
    salida: list[dict] = []
    for tn in turnos:
        if salida and salida[-1]["hablante"] == tn["hablante"] and len(salida[-1]["texto"]) < 700:
            salida[-1]["texto"] = (salida[-1]["texto"].rstrip() + " " + tn["texto"].lstrip()).strip()
            salida[-1]["fin"] = tn["fin"]
        else:
            salida.append(dict(tn))
    return salida


# ------------------------------------------------------------------ análisis
def participantes(turnos: list[dict]) -> list[dict]:
    """Quién habló y cuánto. Cuando la transcripción no trae nombres, lo dice."""
    por: dict[str, dict] = {}
    for tn in turnos:
        quien = tn.get("hablante") or "?"
        d = por.setdefault(quien, {"hablante": quien, "turnos": 0, "palabras": 0, "segundos": 0.0})
        d["turnos"] += 1
        d["palabras"] += len((tn.get("texto") or "").split())
        if tn.get("inicio") is not None and tn.get("fin") is not None:
            d["segundos"] += max(0.0, float(tn["fin"]) - float(tn["inicio"]))
    total = sum(d["palabras"] for d in por.values()) or 1
    for d in por.values():
        d["pct_palabras"] = round(100 * d["palabras"] / total, 1)
        d["segundos"] = round(d["segundos"], 1)
    return sorted(por.values(), key=lambda d: -d["palabras"])


def _frases(turnos: list[dict]) -> list[dict]:
    salida = []
    for tn in turnos:
        for frase in re.split(r"(?<=[.!?])\s+|\n+", tn.get("texto") or ""):
            frase = frase.strip()
            if len(frase) > 12:
                salida.append({"hablante": tn.get("hablante"), "inicio": tn.get("inicio"), "texto": frase})
    return salida


def _marcar(frases: list[dict], patron: re.Pattern) -> list[dict]:
    return [f for f in frases if patron.search(f["texto"])]


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))


def menciones_por_etapa(turnos: list[dict]) -> dict[str, list[dict]]:
    """Qué se dijo de cada etapa del pipeline, con la cita y quién lo dijo."""
    salida: dict[str, list[dict]] = {}
    for f in _frases(turnos):
        plano = _sin_tildes(f["texto"])
        for etapa, palabras in PALABRAS_ETAPA.items():
            if any(_sin_tildes(p) in plano for p in palabras):
                salida.setdefault(etapa, []).append(f)
    return salida


def minuta(turnos: list[dict], titulo: str = "", lang: str = "es") -> dict:
    """La minuta por reglas: todo lo que afirma se apoya en una cita del audio."""
    frases = _frases(turnos)
    compromisos = []
    for f in _marcar(frases, _COMPROMISO):
        fecha = _FECHA_TEXTO.search(f["texto"])
        compromisos.append({**f, "cuando": fecha.group(0) if fecha else None})
    return {
        "titulo": titulo or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "idioma": lang,
        "turnos": len(turnos), "palabras": sum(len((tn.get("texto") or "").split()) for tn in turnos),
        "con_hablantes": any(tn.get("hablante") for tn in turnos),
        "participantes": participantes(turnos),
        "decisiones": _marcar(frases, _DECISION),
        "compromisos": compromisos,
        "riesgos": _marcar(frases, _RIESGO),
        "preguntas": [f for f in frases if f["texto"].rstrip().endswith("?")],
        "menciones": menciones_por_etapa(turnos),
        "resumen_ia": "",
    }


_SISTEMA_MINUTA = (
    "Sos analista de datos. Te dan la transcripción de una reunión de relevamiento para un proyecto de "
    "ingeniería de datos. Escribí, en el idioma indicado, un resumen ejecutivo de 5 a 10 viñetas: qué se "
    "definió, qué quedó abierto y qué implica para el pipeline. No inventes nada que no esté en la "
    "transcripción; si algo no se dijo, no lo pongas. Sin preámbulos, sólo las viñetas con «- ».")


def resumen_ia(turnos: list[dict], lang: str = "es", proveedor: str = "", modelo: str = "",
               api_key: str | None = None, endpoint: str = "", maximo_palabras: int = 6000) -> str:
    """Resumen ejecutivo con IA. Aditivo: la minuta por reglas ya está completa."""
    from . import ia
    if not proveedor or not ia.hay_clave(proveedor, api_key) or not ia.disponible():
        return ""
    texto, cuenta = [], 0
    for tn in turnos:
        palabras = (tn.get("texto") or "").split()
        if cuenta + len(palabras) > maximo_palabras:
            break
        cuenta += len(palabras)
        texto.append(f"{tn.get('hablante') or '?'}: {tn.get('texto')}")
    try:
        return ia._dxl().consultar([{"role": "user", "content": f"Idioma: {lang}\n\n" + "\n".join(texto)}],
                                   sistema=_SISTEMA_MINUTA, proveedor=proveedor, modelo=modelo,
                                   api_key=api_key, endpoint=endpoint, max_tokens=900).strip()
    except Exception as exc:  # noqa: BLE001 - sin resumen la minuta sigue sirviendo
        return f"({exc})"


# ------------------------------------------------------------------ puente al relevamiento
def sugerir_respuestas(turnos: list[dict], lang: str = "es", minimo: int = 2) -> dict[str, dict]:
    """Propone, para cada pregunta del relevamiento, el pasaje de la reunión que
    más se le parece. Es una propuesta para confirmar a mano, no una respuesta:
    lo que se dijo al pasar no siempre es lo que el cliente sostiene."""
    from . import relevamiento
    frases = _frases(turnos)
    if not frases:
        return {}
    salida: dict[str, dict] = {}
    for q in relevamiento.catalogo(lang):
        claves = {p for p in re.findall(r"\w{4,}", _sin_tildes(q["pregunta"])) if p not in _VACIAS}
        mejor, puntaje = None, 0
        for f in frases:
            comunes = len(claves & set(re.findall(r"\w{4,}", _sin_tildes(f["texto"]))))
            if comunes > puntaje:
                mejor, puntaje = f, comunes
        if mejor and puntaje >= minimo:
            salida[q["id"]] = {"texto": mejor["texto"], "hablante": mejor.get("hablante"),
                               "inicio": mejor.get("inicio"), "coincidencias": puntaje}
    return salida


# ------------------------------------------------------------------ persistencia y salida
def carpeta(pipeline_o_ruta) -> Path:
    base = getattr(pipeline_o_ruta, "salida", None) or Path(pipeline_o_ruta)
    p = Path(base) / "reuniones"
    p.mkdir(parents=True, exist_ok=True)
    return p


def guardar(carpeta_destino: str | Path, minuta_: dict, turnos: list[dict]) -> Path:
    p = Path(carpeta_destino)
    p.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", minuta_.get("titulo", "reunion")).strip("_")[:50] or "reunion"
    ruta = p / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{slug}.json"
    ruta.write_text(json.dumps({"minuta": minuta_, "turnos": turnos}, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return ruta


def listar(carpeta_destino: str | Path) -> list[Path]:
    p = Path(carpeta_destino)
    return sorted(p.glob("*.json"), reverse=True) if p.exists() else []


def _mmss(segundos) -> str:
    if segundos is None:
        return ""
    s = int(segundos)
    return f"{s // 60:02d}:{s % 60:02d}"


def markdown(minuta_: dict, lang: str = "es") -> str:
    from .i18n import t
    L = [f"# {t('mt_titulo', lang)} · {minuta_.get('titulo', '')}", "",
         f"{minuta_.get('fecha', '')} · {minuta_.get('turnos', 0)} {t('mt_turns', lang)} · "
         f"{minuta_.get('palabras', 0)} {t('mt_words', lang)}", ""]
    if not minuta_.get("con_hablantes"):
        L += [f"> {t('mt_no_speakers', lang)}", ""]
    L += [f"## {t('mt_people', lang)}", ""]
    for p in minuta_.get("participantes", []):
        L.append(f"- **{p['hablante']}**: {p['turnos']} · {p['palabras']} ({p['pct_palabras']} %)")
    for clave, titulo in (("decisiones", "mt_decisions"), ("compromisos", "mt_commitments"),
                          ("riesgos", "mt_risks"), ("preguntas", "mt_questions")):
        items = minuta_.get(clave) or []
        L += ["", f"## {t(titulo, lang)} ({len(items)})", ""]
        if not items:
            L.append(f"- {t('mt_none', lang)}")
        for it in items[:40]:
            quien = it.get("hablante") or "?"
            cuando = f" · {_mmss(it.get('inicio'))}" if it.get("inicio") is not None else ""
            extra = f" [{it['cuando']}]" if it.get("cuando") else ""
            L.append(f"- **{quien}**{cuando}: {it['texto']}{extra}")
    menciones = minuta_.get("menciones") or {}
    if menciones:
        L += ["", f"## {t('mt_by_stage', lang)}", ""]
        for etapa, items in menciones.items():
            L.append(f"**{t(f'st_{etapa}', lang)}** ({len(items)})")
            for it in items[:6]:
                L.append(f"- {it.get('hablante') or '?'}: {it['texto']}")
            L.append("")
    if minuta_.get("resumen_ia"):
        L += [f"## {t('mt_ai_summary', lang)}", "", minuta_["resumen_ia"], ""]
    return "\n".join(L) + "\n"
