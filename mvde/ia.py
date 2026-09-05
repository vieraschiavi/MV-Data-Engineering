# © 2026 Martín Viera. Todos los derechos reservados.
"""IA opcional y aditiva: elegir proveedor y modelo (BYOK), actualizar la lista
de modelos desde la API del proveedor, y responder preguntas en lenguaje
natural sobre la corrida con respuestas ANALIZADAS: la IA propone un SQL
sobre el almacén, el motor lo ejecuta (sólo lectura) y la IA interpreta el
resultado. Sin clave, un modo local responde con los KPIs, la calidad, el
catálogo y el modelo de la corrida.

El transporte a cada proveedor es el de MV DAX Lab (`daxlingo/dxl/
proveedores_ia.py`, en este repo): un solo `consultar()` para Claude, OpenAI,
Gemini, Copilot/Azure, Groq, Mistral, DeepSeek y Ollama. Si no está, queda
sólo el modo local. Las claves viven en la sesión o en el entorno; nunca en
el YAML ni en disco.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

_LOCAL = {
    "claude": {"nombre": "Claude (Anthropic)", "env": "ANTHROPIC_API_KEY", "modelos": [("claude-sonnet-5", "Sonnet 5")]},
    "openai": {"nombre": "ChatGPT (OpenAI)", "env": "OPENAI_API_KEY", "modelos": [("gpt-5-mini", "GPT-5 mini")]},
    "ollama": {"nombre": "Ollama (local, sin clave)", "env": "", "modelos": [("llama3.1", "Llama 3.1 local")], "sin_clave": True},
}


def _dxl():
    for c in (Path(__file__).resolve().parents[2] / "daxlingo", Path.cwd() / "daxlingo"):
        if (c / "dxl").exists() and str(c) not in sys.path:
            sys.path.insert(0, str(c))
    from dxl import proveedores_ia  # noqa: E402
    return proveedores_ia


def disponible() -> bool:
    try:
        _dxl()
        return True
    except ImportError:
        return False


def proveedores() -> dict:
    try:
        return _dxl().PROVEEDORES
    except ImportError:
        return _LOCAL


def hay_clave(proveedor: str, api_key: str | None) -> bool:
    try:
        return _dxl().hay_clave(proveedor, api_key)
    except ImportError:
        import os
        cfg = _LOCAL.get(proveedor, {})
        return bool(cfg.get("sin_clave") or api_key or os.environ.get(cfg.get("env", ""), ""))


# ------------------------------------------------------------------ modelos
_ENDPOINTS_MODELOS = {
    "openai": "https://api.openai.com/v1/models",
    "groq": "https://api.groq.com/openai/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "deepseek": "https://api.deepseek.com/models",
    "claude": "https://api.anthropic.com/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
    "ollama": "http://localhost:11434/api/tags",
}


def listar_modelos(proveedor: str, api_key: str | None = None, endpoint: str = "") -> list[str]:
    """Modelos disponibles HOY según la API del proveedor (la lista estática del
    producto envejece; ésta no). Lanza RuntimeError con el motivo si no se puede."""
    url = _ENDPOINTS_MODELOS.get(proveedor)
    if proveedor == "copilot":
        if not endpoint:
            raise RuntimeError("Azure OpenAI: indicá el endpoint del recurso")
        url = endpoint.rstrip("/") + "/openai/models?api-version=2024-10-21"
    if not url:
        raise RuntimeError(f"el proveedor {proveedor} no publica una lista de modelos")
    clave = api_key or ""
    if not clave:
        import os
        clave = os.environ.get(proveedores().get(proveedor, {}).get("env", ""), "")
    headers = {"User-Agent": "mvde"}
    if proveedor == "claude":
        headers.update({"x-api-key": clave, "anthropic-version": "2023-06-01"})
    elif proveedor == "gemini":
        url += f"?key={clave}"
    elif proveedor == "copilot":
        headers["api-key"] = clave
    elif proveedor != "ollama":
        headers["Authorization"] = f"Bearer {clave}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:  # noqa: S310
            datos = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{proveedor}: HTTP {exc.code} — {'clave inválida' if exc.code in (401, 403) else exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"{proveedor}: sin conexión ({getattr(exc, 'reason', exc)})") from exc
    return _extraer_modelos(proveedor, datos)


def _extraer_modelos(proveedor: str, datos: dict) -> list[str]:
    """Normaliza la respuesta de cada API a una lista de ids ordenada."""
    if proveedor == "ollama":
        ids = [m.get("name", "") for m in datos.get("models", [])]
    elif proveedor == "gemini":
        ids = [m.get("name", "").replace("models/", "") for m in datos.get("models", [])
               if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    else:
        ids = [m.get("id", "") for m in datos.get("data", [])]
    ids = [i for i in ids if i]
    if proveedor == "openai":
        ids = [i for i in ids if i.startswith(("gpt", "o1", "o3", "o4")) and "realtime" not in i and "audio" not in i]
    return sorted(set(ids), reverse=True)


# ------------------------------------------------------------------ contexto
def contexto(pipeline) -> str:
    """Lo que la IA necesita saber de la corrida, en texto corto."""
    partes = [f"Proyecto: {pipeline.spec['nombre']}. {pipeline.spec.get('descripcion', '')}".strip()]
    if pipeline.gold:
        partes.append("Tablas del almacén DuckDB (esquema gold):")
        for n, df in pipeline.gold.items():
            cols = ", ".join(f"{c} ({str(df[c].dtype)})" for c in list(df.columns)[:40])
            partes.append(f"- gold.{n} [{len(df)} filas]: {cols}")
    if pipeline.spec.get("vistas"):
        partes.append("Vistas: " + ", ".join(f"gold.{v}" for v in pipeline.spec["vistas"]))
    if pipeline.kpis:
        partes.append("KPIs de la corrida: " + "; ".join(f"{k['nombre']} = {k['texto']}" for k in pipeline.kpis))
    if pipeline.calidad:
        partes.append(f"Calidad: puntaje {pipeline.calidad.get('puntaje')} sobre {pipeline.calidad.get('reglas')} reglas; "
                      + ("hallazgos: " + "; ".join(f"{r['regla']}: {r['detalle']}" for r in pipeline.calidad.get("fallidas", [])[:8]) if pipeline.calidad.get("fallidas") else "sin hallazgos"))
    if pipeline.ml:
        partes.append(f"Modelo: {pipeline.ml.get('tipo')} {pipeline.ml.get('modelo', '')}, métricas holdout {pipeline.ml.get('metricas')}, "
                      f"importancia {list(pipeline.ml.get('importancia', {}).items())[:8]}")
    return "\n".join(partes)


SISTEMA_SQL = ("Sos un analista de datos senior. Te dan el esquema de un almacén DuckDB (esquema gold) y una pregunta. "
               "Respondé SOLO un JSON con dos claves: \"sql\" (una consulta SELECT válida en DuckDB sobre las tablas dadas, "
               "con LIMIT 200 como máximo, o null si la pregunta se contesta sin consultar) y \"nota\" (una línea sobre cómo la vas a contestar). "
               "Nunca escribas INSERT/UPDATE/DELETE/DROP. Usá nombres de columna exactamente como aparecen.")
SISTEMA_RESPUESTA = ("Sos un analista de datos que explica resultados a técnicos y gerentes en el idioma de la pregunta. "
                     "Respondé en menos de 200 palabras: primero el número o hallazgo, después qué significa para el negocio, "
                     "después una salvedad si corresponde. No inventes datos que no estén en el contexto o en la tabla.")


def _extraer_json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def preguntar(pregunta: str, pipeline, proveedor: str = "", modelo: str = "", api_key: str | None = None,
              endpoint: str = "", idioma: str = "es") -> dict:
    """Devuelve {respuesta, sql, tabla (DataFrame|None), modo}."""
    ctx = contexto(pipeline)
    if not proveedor or not hay_clave(proveedor, api_key) or not disponible():
        return responder_local(pregunta, pipeline)
    from .almacen import consultar
    pia = _dxl()
    plan = _extraer_json(pia.consultar([{"role": "user", "content": f"{ctx}\n\nPregunta: {pregunta}"}], sistema=SISTEMA_SQL,
                                       proveedor=proveedor, modelo=modelo, api_key=api_key, endpoint=endpoint, max_tokens=800))
    sql, tabla, error_sql = plan.get("sql"), None, ""
    if sql and pipeline.ruta_db.exists():
        if not re.match(r"^\s*(select|with)\b", sql, re.I):
            error_sql = "la IA propuso una consulta que no es de lectura; se descartó"
            sql = None
        else:
            try:
                tabla = consultar(pipeline.ruta_db, sql if re.search(r"\blimit\b", sql, re.I) else sql.rstrip("; ") + " LIMIT 200")
            except Exception as exc:  # noqa: BLE001 - el SQL lo escribió la IA, se informa y se sigue
                error_sql = f"la consulta propuesta falló: {str(exc).splitlines()[0]}"
    resultado_txt = tabla.head(50).to_string() if tabla is not None else (error_sql or "sin consulta")
    respuesta = pia.consultar([{"role": "user", "content": f"Contexto:\n{ctx}\n\nPregunta: {pregunta}\n\nConsulta usada: {sql}\nResultado:\n{resultado_txt}"}],
                              sistema=SISTEMA_RESPUESTA, proveedor=proveedor, modelo=modelo, api_key=api_key, endpoint=endpoint, max_tokens=900)
    return {"respuesta": respuesta.strip(), "sql": sql, "tabla": tabla, "modo": f"{proveedor}/{modelo or 'defecto'}", "nota": plan.get("nota", ""), "error": error_sql}


def responder_local(pregunta: str, pipeline) -> dict:
    """Sin IA: busca la pregunta en los KPIs, la calidad, el modelo y el catálogo,
    y acepta un SELECT escrito a mano sobre el almacén."""
    q = pregunta.strip()
    if re.match(r"^\s*(select|with)\b", q, re.I):
        from .almacen import consultar
        try:
            tabla = consultar(pipeline.ruta_db, q if re.search(r"\blimit\b", q, re.I) else q.rstrip("; ") + " LIMIT 200")
            return {"respuesta": f"{len(tabla)} filas.", "sql": q, "tabla": tabla, "modo": "local/sql", "nota": "", "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"respuesta": f"La consulta falló: {str(exc).splitlines()[0]}", "sql": q, "tabla": None, "modo": "local/sql", "nota": "", "error": str(exc)}
    palabras = {w for w in re.findall(r"\w+", q.lower()) if len(w) > 3}
    lineas = []
    for k in pipeline.kpis or []:
        if palabras & set(re.findall(r"\w+", k["nombre"].lower())):
            lineas.append(f"{k['nombre']}: {k['texto']}")
    if pipeline.calidad and palabras & {"calidad", "quality", "reglas", "hallazgos", "errores", "qualidade"}:
        lineas.append(f"Calidad: {pipeline.calidad.get('puntaje')} / 100 en {pipeline.calidad.get('reglas')} reglas; "
                      + (", ".join(f"{r['regla']} ({r['detalle']})" for r in pipeline.calidad.get("fallidas", [])) or "sin hallazgos"))
    if pipeline.ml and palabras & {"modelo", "model", "auc", "precision", "score", "probpago", "prediccion", "predicción", "importancia", "variables"}:
        lineas.append(f"Modelo {pipeline.ml.get('modelo', '')} ({pipeline.ml.get('tipo')}): métricas holdout {pipeline.ml.get('metricas')}; "
                      f"variables más importantes: {', '.join(list(pipeline.ml.get('importancia', {}))[:6])}")
    if pipeline.gold and palabras & {"tablas", "tables", "columnas", "columns", "esquema", "schema", "modelo"}:
        lineas.append("Tablas: " + ", ".join(f"{n} ({len(df)} filas)" for n, df in pipeline.gold.items()))
    if not lineas:
        lineas = ["Sin proveedor de IA configurado sólo puedo responder sobre KPIs, calidad, modelo y tablas de esta corrida, "
                  "o ejecutar un SELECT que escribas vos. Configurá un proveedor en la pestaña IA para preguntas libres."]
        if pipeline.kpis:
            lineas.append("KPIs disponibles: " + "; ".join(f"{k['nombre']} = {k['texto']}" for k in pipeline.kpis))
    return {"respuesta": "\n".join(lineas), "sql": None, "tabla": None, "modo": "local", "nota": "", "error": ""}


def tabla_a_texto(tabla: pd.DataFrame | None) -> str:
    return "" if tabla is None else tabla.head(50).to_string()
