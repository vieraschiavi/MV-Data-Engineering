# © 2026 Martín Viera. Todos los derechos reservados.
"""Salud del proyecto y sugerencias de mejora, al estilo de MV Data Governance
(índice por dimensión) y MV DAX Lab (puntaje de salud + arreglo automático).

`evaluar(pipeline)` → puntaje 0-100 por área (datos, calidad, modelo,
gobernanza, bi, ml) y total. Se guarda por corrida en `salud_historial.json`
para mostrar el ANTES y el DESPUÉS de aplicar mejoras.

`sugerencias(pipeline)` → lista de mejoras con severidad y, cuando se puede,
un PARCHE al YAML que `aplicar()` deja escrito: reglas de calidad que faltan,
calendario, KPIs, target de ML, fugas a excluir, dueño, PII, SCD 2… Lo que no
se puede parchear sin criterio humano (descripciones, nombres de negocio) se
sugiere con el dato exacto que falta.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

AREAS = ["datos", "calidad", "modelo", "gobernanza", "bi", "ml"]
_MAGNITUD = ("monto", "importe", "amount", "precio", "price", "unidad", "cantidad", "qty", "dias", "edad", "age",
             "limite", "limit", "saldo", "cuota", "pago", "paid", "venta", "total", "ingreso", "costo")


# ------------------------------------------------------------------ ayudas
def _pct(n, d) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _clave_candidata(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if c.endswith("_key") or c.endswith("_hash"):
            continue
        s = df[c]
        if s.notna().all() and s.is_unique and (pd.api.types.is_integer_dtype(s) or pd.api.types.is_string_dtype(s) or s.dtype == object):
            return c
    return None


def _texto_que_parece_numero(s: pd.Series) -> bool:
    if not (pd.api.types.is_string_dtype(s) or s.dtype == object):
        return False
    m = s.dropna().astype(str).str.strip().head(500)
    if m.empty:
        return False
    return m.str.replace(r"[\$\s.,-]", "", regex=True).str.isdigit().mean() > 0.95


def sugerir_target(df: pd.DataFrame, excluir: set[str] | None = None) -> list[dict]:
    """Columnas que pueden ser objetivo de un modelo, ordenadas por plausibilidad."""
    excluir = excluir or set()
    out = []
    n = len(df)
    for c in df.columns:
        if c in excluir or c.endswith("_key") or c.endswith("_hash") or n == 0:
            continue
        s = df[c].dropna()
        if s.empty:
            continue
        nun = s.nunique()
        nombre = c.lower()
        pista = any(p in nombre for p in ("default", "pago", "paid", "churn", "fraude", "fraud", "target", "objetivo", "label", "mora", "baja", "compra", "convers"))
        if pd.api.types.is_bool_dtype(s) or (nun == 2 and (pd.api.types.is_numeric_dtype(s) or pd.api.types.is_string_dtype(s) or s.dtype == object)):
            tasa = float(pd.to_numeric(s, errors="coerce").mean()) if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s) else None
            out.append({"columna": c, "tipo": "clasificacion", "clases": int(nun), "tasa_positiva": round(tasa, 4) if tasa is not None else None,
                        "puntaje": 3 + (2 if pista else 0)})
        elif pd.api.types.is_numeric_dtype(s) and nun > 20 and not nombre.startswith("id"):
            monetario = any(p in nombre for p in ("monto", "importe", "amount", "precio", "price", "venta", "revenue", "ingreso", "costo"))
            out.append({"columna": c, "tipo": "regresion", "clases": None, "tasa_positiva": None, "puntaje": 1 + (2 if monetario else 0) + (1 if pista else 0)})
    return sorted(out, key=lambda x: -x["puntaje"])


# ------------------------------------------------------------------ salud
def evaluar(pipeline) -> dict:
    spec, r = pipeline.spec, pipeline.resultados
    areas: dict[str, dict] = {}

    # datos: tipado y unicidad en silver
    if pipeline.silver:
        cols = sum(len(df.columns) for df in pipeline.silver.values())
        mal_tipadas = sum(1 for df in pipeline.silver.values() for c in df.columns if _texto_que_parece_numero(df[c]))
        con_clave = sum(1 for df in pipeline.silver.values() if _clave_candidata(df))
        p = 100 - _pct(mal_tipadas, cols) * 2 - (0 if con_clave == len(pipeline.silver) else 15)
        areas["datos"] = {"puntaje": max(0, round(p, 1)), "detalle": f"{cols} columnas, {mal_tipadas} texto-que-es-número, {con_clave}/{len(pipeline.silver)} tablas con clave única"}
    # calidad: gate + cobertura de reglas declaradas
    if pipeline.calidad:
        declaradas = spec.get("calidad", {}).get("reglas", []) or []
        con_reglas = {x["tabla"] for x in declaradas}
        cobertura = _pct(len([t for t in pipeline.silver if t in con_reglas]), len(pipeline.silver)) if pipeline.silver else 0
        p = 0.7 * float(pipeline.calidad.get("puntaje", 0)) + 0.3 * cobertura
        areas["calidad"] = {"puntaje": round(p, 1), "detalle": f"gate {pipeline.calidad.get('puntaje')} · {len(declaradas)} reglas declaradas · cobertura {cobertura} % de las tablas"}
    # modelo: estrella declarada, calendario, SCD
    if pipeline.gold:
        modelo = spec.get("modelo") or {}
        dims, hechos = modelo.get("dimensiones") or [], modelo.get("hechos") or []
        p = 40 + (25 if dims else 0) + (20 if hechos else 0) + (15 if "dim_calendario" in pipeline.gold else 0)
        areas["modelo"] = {"puntaje": p, "detalle": f"{len(dims)} dimensiones, {len(hechos)} hechos, calendario {'sí' if 'dim_calendario' in pipeline.gold else 'no'}"}
    # gobernanza
    if "gobernanza" in r and r["gobernanza"].ok:
        pj = r["gobernanza"].evidencia.get("puntajes", {})
        doc = float(pj.get("documentacion_pct") or 0)
        dueno = bool((spec.get("gobernanza") or {}).get("dueno"))
        pii_dec = len((spec.get("gobernanza") or {}).get("pii") or [])
        pii_det = int(pj.get("columnas_pii") or 0)
        p = 0.6 * doc + (20 if dueno else 0) + (20 if pii_det == 0 or pii_dec else 0)
        areas["gobernanza"] = {"puntaje": round(min(100, p), 1), "detalle": f"documentación {doc} % · dueño {'sí' if dueno else 'no'} · PII detectadas {pii_det}, declaradas {pii_dec}"}
    # bi
    if "powerbi" in r and r["powerbi"].ok and not r["powerbi"].omitida:
        ev = r["powerbi"].evidencia
        p = 0.8 * float(ev.get("auditoria", 0)) + (20 if ev.get("medidas") else 0)
        areas["bi"] = {"puntaje": round(min(100, p), 1), "detalle": f"auditoría {ev.get('auditoria')}/100 · {ev.get('medidas')} medidas · {ev.get('relaciones')} relaciones"}
    elif "dax" in r and r["dax"].ok:
        areas["bi"] = {"puntaje": 60 if r["dax"].evidencia.get("medidas") else 30, "detalle": f"{len(r['dax'].evidencia.get('medidas', []))} medidas DAX, sin .pbit"}
    # ml
    if pipeline.ml and pipeline.ml.get("tipo") == "serie":
        # En una proyección no hay AUC ni R²: lo que importa es cuánto se
        # equivoca (sMAPE) y si le gana a repetir el ciclo anterior. Un modelo
        # que no le gana al tonto no suma, aunque sea grande.
        m = pipeline.ml.get("metricas") or {}
        e = pipeline.ml.get("eleccion") or {}
        smape = float(m.get("smape") or 100)
        p = max(0.0, 100 - smape * (100 / 30))              # sMAPE 0 % → 100; 30 % o más → 0
        if e.get("le_gana_a_la_referencia"):
            p += min(20.0, max(0.0, float(e.get("mejora_pct") or 0)) / 2)
        veredicto = (f"+{e.get('mejora_pct')} % vs {e.get('referencia')}" if e.get("le_gana_a_la_referencia")
                     else f"no le gana a {e.get('referencia')}")
        areas["ml"] = {"puntaje": round(max(0, min(100, p)), 1),
                       "detalle": f"{pipeline.ml.get('modelo')} · sMAPE {round(smape, 2)} % · {veredicto} · "
                                  f"{m.get('origenes_backtest')} orígenes de backtest"}
    elif pipeline.ml:
        m = pipeline.ml.get("metricas") or {}
        base = m.get("auc") if m.get("auc") is not None else m.get("r2")
        brecha = abs(float(pipeline.ml.get("brecha_seleccion_holdout") or 0))
        # AUC 0,5 = azar → 0; AUC 0,9 = 100. R² directo. La brecha grande resta.
        p = (max(0.0, (float(base) - 0.5) / 0.4) * 100 if m.get("auc") is not None else max(0.0, float(base or 0)) * 100) - min(30, brecha * 300)
        areas["ml"] = {"puntaje": round(max(0, min(100, p)), 1), "detalle": f"{pipeline.ml.get('modelo')} · {'AUC' if m.get('auc') is not None else 'R²'} {base} · brecha {pipeline.ml.get('brecha_seleccion_holdout')}"}
    total = round(sum(a["puntaje"] for a in areas.values()) / len(areas), 1) if areas else 0.0
    return {"total": total, "areas": areas, "fecha": datetime.now().isoformat(timespec="seconds")}


def registrar(pipeline, salud: dict) -> Path:
    p = pipeline.salida / "salud_historial.json"
    hist = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    hist.append({"fecha": salud["fecha"], "total": salud["total"], "areas": {k: v["puntaje"] for k, v in salud["areas"].items()}})
    p.write_text(json.dumps(hist[-50:], indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def historial(pipeline) -> list[dict]:
    p = pipeline.salida / "salud_historial.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def antes_despues(pipeline) -> dict | None:
    h = historial(pipeline)
    if len(h) < 2:
        return None
    a, d = h[-2], h[-1]
    areas = sorted(set(a["areas"]) | set(d["areas"]))
    return {"antes": a, "despues": d, "delta_total": round(d["total"] - a["total"], 1),
            "areas": [{"area": k, "antes": a["areas"].get(k), "despues": d["areas"].get(k),
                       "delta": round((d["areas"].get(k) or 0) - (a["areas"].get(k) or 0), 1)} for k in areas]}


# ------------------------------------------------------------------ sugerencias
def sugerencias(pipeline) -> list[dict]:
    spec, r = pipeline.spec, pipeline.resultados
    out: list[dict] = []
    reglas = spec.get("calidad", {}).get("reglas", []) or []

    def tiene(tabla, tipo, col=None):
        return any(x["tabla"] == tabla and x["tipo"] == tipo and (col is None or x.get("columna") == col) for x in reglas)

    for nombre, df in pipeline.silver.items():
        clave = _clave_candidata(df)
        if clave and not tiene(nombre, "unico", clave):
            out.append({"area": "calidad", "codigo": "regla_unico", "severidad": "alta", "aplicable": True,
                        "titulo": f"{nombre}: declarar {clave} como clave única",
                        "detalle": "Hoy es única de hecho; sin regla, un duplicado del origen entra a gold sin que nadie lo vea.",
                        "parche": {"regla": {"tabla": nombre, "columna": clave, "tipo": "unico", "critico": True}}})
        if not tiene(nombre, "filas_min"):
            out.append({"area": "calidad", "codigo": "regla_filas", "severidad": "media", "aplicable": True,
                        "titulo": f"{nombre}: piso de filas ({max(1, int(len(df) * 0.5)):,})",
                        "detalle": "Una carga a medias (archivo cortado, consulta filtrada) pasaría sin aviso.",
                        "parche": {"regla": {"tabla": nombre, "tipo": "filas_min", "valor": max(1, int(len(df) * 0.5)), "critico": True}}})
        for c in df.columns:
            if _texto_que_parece_numero(df[c]):
                out.append({"area": "datos", "codigo": "tipo_numero", "severidad": "media", "aplicable": True,
                            "titulo": f"{nombre}.{c}: es texto pero contiene números",
                            "detalle": "Declararla decimal en silver: sumar texto da error o, peor, cero.",
                            "parche": {"silver_tipo": {"tabla": nombre, "columna": c, "tipo": "decimal"}}})
            s = df[c]
            es_id = c == clave or c.lower().startswith("id") or c.lower().endswith("id") or c.lower().endswith("_id")
            es_magnitud = any(k in c.lower() for k in _MAGNITUD)
            if (pd.api.types.is_numeric_dtype(s) and s.notna().any() and (s.dropna() >= 0).all() and not c.endswith("_key")
                    and not es_id and es_magnitud and not tiene(nombre, "no_negativo", c) and s.nunique() > 2
                    and sum(1 for x in out if x["codigo"] == "regla_no_negativo" and x["parche"]["regla"]["tabla"] == nombre) < 3):
                out.append({"area": "calidad", "codigo": "regla_no_negativo", "severidad": "baja", "aplicable": True,
                            "titulo": f"{nombre}.{c}: nunca es negativa, declararlo",
                            "detalle": "Un signo invertido en el origen se detecta en la etapa de calidad, no en el tablero.",
                            "parche": {"regla": {"tabla": nombre, "columna": c, "tipo": "no_negativo", "critico": False}}})
    # referencias entre tablas: misma columna, valores contenidos
    nombres = list(pipeline.silver)
    for a in nombres:
        for b in nombres:
            if a == b:
                continue
            for c in pipeline.silver[a].columns:
                if c in pipeline.silver[b].columns and _clave_candidata(pipeline.silver[b]) == c and not tiene(a, "referencia", c):
                    if pipeline.silver[a][c].dropna().isin(pipeline.silver[b][c]).mean() > 0.95:
                        out.append({"area": "calidad", "codigo": "regla_referencia", "severidad": "alta", "aplicable": True,
                                    "titulo": f"{a}.{c} → {b}.{c}: declarar la referencia",
                                    "detalle": "Los huérfanos desaparecen del join sin aviso; la regla los cuenta.",
                                    "parche": {"regla": {"tabla": a, "columna": c, "tipo": "referencia", "a": f"{b}.{c}", "critico": True}}})
    # modelo
    modelo = spec.get("modelo") or {}
    if pipeline.silver and not (modelo.get("dimensiones") or modelo.get("hechos")):
        out.append({"area": "modelo", "codigo": "sin_estrella", "severidad": "alta", "aplicable": False,
                    "titulo": "No hay modelo estrella declarado: gold es una copia de silver",
                    "detalle": "Declarar `modelo.dimensiones` (clave + atributos, SCD 2 si cambian) y `modelo.hechos` (fecha + claves). Sin eso Power BI no tiene relaciones que seguir."})
    if pipeline.gold and "dim_calendario" not in pipeline.gold and any(pd.api.types.is_datetime64_any_dtype(df[c]) for df in pipeline.silver.values() for c in df.columns):
        out.append({"area": "modelo", "codigo": "sin_calendario", "severidad": "media", "aplicable": True,
                    "titulo": "Hay fechas pero no calendario", "detalle": "Sin dim_calendario no funciona la time intelligence en DAX.",
                    "parche": {"modelo_calendario": "auto"}})
    for d in modelo.get("dimensiones") or []:
        if int(d.get("scd", 1)) != 2 and d["desde"] in pipeline.silver:
            attrs = [c for c in (d.get("atributos") or pipeline.silver[d["desde"]].columns) if c != d["clave"] and pd.api.types.is_numeric_dtype(pipeline.silver[d["desde"]].get(c, pd.Series(dtype=float)))]
            if attrs:
                out.append({"area": "modelo", "codigo": "scd2", "severidad": "baja", "aplicable": True,
                            "titulo": f"{d['nombre']}: atributos numéricos que cambian ({', '.join(attrs[:3])}) sin historia",
                            "detalle": "SCD 2 guarda la versión vigente en cada momento; SCD 1 reescribe el pasado.",
                            "parche": {"scd2": d["nombre"]}})
    # gobernanza
    gob = spec.get("gobernanza") or {}
    if not gob.get("dueno"):
        out.append({"area": "gobernanza", "codigo": "sin_dueno", "severidad": "media", "aplicable": True, "titulo": "El proyecto no tiene dueño declarado",
                    "detalle": "Toda auditoría empieza por «¿de quién es este dato?».", "parche": {"dueno": "BI / Datos"}})
    if "gobernanza" in r and r["gobernanza"].ok:
        cat = pipeline.catalogo if len(pipeline.catalogo) else pd.DataFrame()
        if len(cat):
            sin_doc = cat[(cat["capa"] == "gold") & (cat["descripcion"] == "") & (~cat["columna"].str.endswith("_key"))]
            if len(sin_doc):
                cols = ", ".join((sin_doc["tabla"] + "." + sin_doc["columna"]).head(8))
                out.append({"area": "gobernanza", "codigo": "sin_descripcion", "severidad": "media", "aplicable": False,
                            "titulo": f"{len(sin_doc)} columnas de gold sin descripción", "detalle": f"Agregá `gobernanza.descripciones` para: {cols}{'…' if len(sin_doc) > 8 else ''}."})
            pii_det = cat[cat["pii"]]
            declaradas = set(gob.get("pii") or [])
            faltan = [f"{t}.{c}" for t, c in zip(pii_det["tabla"], pii_det["columna"]) if c not in declaradas and f"{t}.{c}" not in declaradas]
            if faltan:
                out.append({"area": "gobernanza", "codigo": "pii", "severidad": "alta", "aplicable": True,
                            "titulo": f"{len(set(faltan))} columnas parecen PII y no están declaradas",
                            "detalle": ", ".join(sorted(set(faltan))[:8]), "parche": {"pii": sorted(set(faltan))}})
    # KPIs y BI
    # El orquestador rellena KPIs automáticos al reportar y lo marca; para la
    # sugerencia cuentan como "no declarados": el parche los deja escritos en el YAML.
    if (not spec.get("kpis") or spec.get("_kpis_automaticos")) and pipeline.gold:
        from .reporte import kpis_automaticos
        auto = kpis_automaticos(pipeline.gold)
        if auto:
            out.append({"area": "bi", "codigo": "sin_kpis", "severidad": "alta", "aplicable": True,
                        "titulo": f"No hay KPIs declarados: se proponen {len(auto)}",
                        "detalle": "; ".join(k["nombre"] for k in auto[:6]), "parche": {"kpis": auto}})
    if "powerbi" in r and r["powerbi"].ok and not r["powerbi"].omitida:
        for regla, objeto in r["powerbi"].evidencia.get("hallazgos", []):
            if regla == "R12" and objeto == "DataPath":
                continue
            out.append({"area": "bi", "codigo": f"pbi_{regla}", "severidad": "baja", "aplicable": False,
                        "titulo": f"Auditoría del modelo: {regla} en {objeto}", "detalle": "Ver el detalle en MV DAX Lab (Analizar) y aplicar el arreglo automático."})
    # ML
    ml_cfg = spec.get("ml")
    if not ml_cfg and pipeline.gold:
        candidatos = []
        for t, df in pipeline.gold.items():
            if t.startswith("dim_") or t == "ml_scores":
                continue
            for c in sugerir_target(df)[:2]:
                candidatos.append((t, c))
        if candidatos:
            t, c = candidatos[0]
            out.append({"area": "ml", "codigo": "target", "severidad": "media", "aplicable": True,
                        "titulo": f"Sin modelo: {t}.{c['columna']} parece un objetivo de {c['tipo']}",
                        "detalle": "; ".join(f"{tt}.{cc['columna']} ({cc['tipo']})" for tt, cc in candidatos[:5]),
                        "parche": {"ml": {"tabla": t, "target": c["columna"], "tipo": c["tipo"]}}})
    elif pipeline.ml and pipeline.ml.get("tipo") == "serie":
        e = pipeline.ml.get("eleccion") or {}
        bt = pipeline.ml.get("backtest") or {}
        if not e.get("le_gana_a_la_referencia"):
            out.append({"area": "ml", "codigo": "serie_sin_ganador", "severidad": "media", "aplicable": False,
                        "titulo": f"Ningún modelo le gana a «{e.get('referencia')}»",
                        "detalle": "Se proyecta con la referencia, que es lo honesto. Para mejorarla: más historia, "
                                   "declarar la estacionalidad correcta en `ml.estacionalidad`, o separar la serie "
                                   "por segmento en vez de proyectar el total."})
        if bt.get("origenes", 0) < 6:
            out.append({"area": "ml", "codigo": "serie_pocos_origenes", "severidad": "media", "aplicable": False,
                        "titulo": f"El backtest corrió con {bt.get('origenes')} orígenes",
                        "detalle": "Con pocos cortes, la diferencia entre modelos puede ser suerte. "
                                   "Sumar historia antes de decidir con este número."})
        for n in pipeline.ml.get("notas", []):
            if "TimesFM no entró" in n:
                out.append({"area": "ml", "codigo": "serie_timesfm", "severidad": "baja", "aplicable": False,
                            "titulo": "TimesFM quedó fuera del backtest", "detalle": n})
    elif pipeline.ml:
        for n in pipeline.ml.get("notas", []):
            if n.startswith("fuga:"):
                import re
                cols = re.findall(r"'([^']+)'", n)
                if cols:
                    out.append({"area": "ml", "codigo": "fuga", "severidad": "alta", "aplicable": True,
                                "titulo": f"Fuga de información: {', '.join(cols)} replican el target",
                                "detalle": "Se quitaron en la corrida; conviene excluirlas en el YAML para que quede escrito.",
                                "parche": {"ml_excluir": cols}})
        m = pipeline.ml.get("metricas") or {}
        if m.get("tasa_base") is not None and (m["tasa_base"] < 0.05 or m["tasa_base"] > 0.95):
            out.append({"area": "ml", "codigo": "desbalance", "severidad": "media", "aplicable": False,
                        "titulo": f"Target muy desbalanceado (tasa {m['tasa_base']})", "detalle": "Mirar AUC-PR y el lift del decil superior antes que accuracy."})
        if pipeline.ml.get("brecha_seleccion_holdout") is not None and abs(float(pipeline.ml["brecha_seleccion_holdout"])) > 0.05:
            out.append({"area": "ml", "codigo": "brecha", "severidad": "media", "aplicable": False,
                        "titulo": f"Brecha selección→holdout de {pipeline.ml['brecha_seleccion_holdout']}",
                        "detalle": "El modelo elegido rinde distinto fuera de la selección: más datos, menos features o regularización."})
    orden = {"alta": 0, "media": 1, "baja": 2}
    return sorted(out, key=lambda s: orden[s["severidad"]])


def aplicar(spec: dict, sugerencia: dict) -> dict:
    """Devuelve una COPIA del spec con el parche aplicado (nunca muta el original)."""
    s = copy.deepcopy(spec)
    p = sugerencia.get("parche") or {}
    if "regla" in p:
        s.setdefault("calidad", {}).setdefault("reglas", []).append(p["regla"])
    if "silver_tipo" in p:
        st = p["silver_tipo"]
        cfg = s.setdefault("silver", {}).setdefault(st["tabla"], {})
        tipos = cfg.get("tipos")
        cfg["tipos"] = {**(tipos if isinstance(tipos, dict) else {}), st["columna"]: st["tipo"]}
    if "modelo_calendario" in p:
        s.setdefault("modelo", {})["calendario"] = p["modelo_calendario"]
    if "scd2" in p:
        for d in s.get("modelo", {}).get("dimensiones", []) or []:
            if d["nombre"] == p["scd2"]:
                d["scd"] = 2
    if "dueno" in p:
        s.setdefault("gobernanza", {})["dueno"] = p["dueno"]
    if "pii" in p:
        g = s.setdefault("gobernanza", {})
        g["pii"] = sorted(set(g.get("pii") or []) | set(p["pii"]))
    if "kpis" in p:
        previos = [] if s.get("_kpis_automaticos") else list(s.get("kpis") or [])
        nombres = {k.get("nombre") for k in previos}
        s["kpis"] = previos + [k for k in p["kpis"] if k.get("nombre") not in nombres]
        s.pop("_kpis_automaticos", None)
    if "ml" in p:
        s["ml"] = p["ml"]
    if "ml_excluir" in p and s.get("ml"):
        s["ml"]["excluir"] = sorted(set(s["ml"].get("excluir") or []) | set(p["ml_excluir"]))
    return s


def aplicar_todas(spec: dict, lista: list[dict]) -> tuple[dict, int]:
    n = 0
    for sug in lista:
        if sug.get("aplicable"):
            spec = aplicar(spec, sug)
            n += 1
    return spec, n
