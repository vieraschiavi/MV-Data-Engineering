# © 2026 Martín Viera. Todos los derechos reservados.
"""La justificación de cada etapa, para dos públicos: técnicos (qué se hizo y
cómo se verifica) y gerentes (qué riesgo evita y qué decisión habilita). Se
arma con las evidencias reales de la corrida, así que los números son los
del pipeline, no una plantilla."""
from __future__ import annotations

from . import ETAPAS
from .i18n import t


def _n(ev: dict, *claves, defecto="—"):
    cur = ev
    for k in claves:
        if not isinstance(cur, dict) or k not in cur:
            return defecto
        cur = cur[k]
    return cur


def datos_de(pipeline) -> dict:
    """Los valores que rellenan las plantillas de justificación."""
    r = pipeline.resultados
    ev = lambda e: (r[e].evidencia if e in r else {})  # noqa: E731
    fuentes = ev("fuentes")
    calidad = ev("calidad")
    gold = ev("gold")
    alm = ev("almacen")
    gob = ev("gobernanza")
    mlv = ev("ml")
    rep = ev("reporte")
    dax = ev("dax")
    pbi = ev("powerbi")
    filas = sum(int(f.get("filas", 0)) for f in fuentes.values()) if fuentes else 0
    met = mlv.get("metricas") or {}
    return {
        "n_fuentes": len(fuentes), "filas_fuentes": f"{filas:,}".replace(",", "."),
        "tipos_fuentes": ", ".join(sorted({f.get("tipo", "") for f in fuentes.values()})) or "—",
        "n_tablas_silver": len(ev("silver")), "notas_silver": "; ".join(n for v in ev("silver").values() for n in v.get("notas", [])[:2])[:300] or "—",
        "reglas": calidad.get("reglas", "—"), "puntaje": calidad.get("puntaje", "—"),
        "hallazgos": len(calidad.get("fallidas", [])),
        "criticas": ", ".join(pipeline.calidad.get("criticas_fallidas", [])) or "—",
        "n_gold": len(gold.get("tablas", {})), "tablas_gold": ", ".join(gold.get("tablas", {})) or "—",
        "n_vistas": len(alm.get("vistas", [])), "vistas": ", ".join(alm.get("vistas", [])) or "—",
        "tablas_catalogadas": _n(gob, "puntajes", "tablas"), "aristas": len(gob.get("linaje", [])), "pii": _n(gob, "puntajes", "columnas_pii"),
        "documentacion": _n(gob, "puntajes", "documentacion_pct"),
        "ml_tipo": mlv.get("tipo", "—"), "ml_modelo": mlv.get("modelo", "—"),
        "ml_metrica": (f"AUC {met.get('auc')}" if met.get("auc") is not None else f"R² {met.get('r2')}" if met.get("r2") is not None else "—"),
        "ml_lift": met.get("lift_decil10", "—"), "ml_brecha": mlv.get("brecha_seleccion_holdout", "—"),
        "ml_scoreadas": mlv.get("filas_scoreadas", "—"), "ml_top": ", ".join(list(mlv.get("importancia", {}))[:4]) or "—",
        "n_kpis": len(rep.get("kpis", [])), "kpis": "; ".join(f"{k['nombre']} = {k['valor']}" for k in rep.get("kpis", [])[:6]) or "—",
        "n_graficos": len(rep.get("graficos", [])),
        "n_medidas": len(dax.get("medidas", [])),
        "pbi_tablas": pbi.get("tablas", "—"), "pbi_relaciones": pbi.get("relaciones", "—"), "pbi_auditoria": pbi.get("auditoria", "—"),
        "segundos": round(sum(x.segundos for x in r.values()), 1),
    }


def generar(pipeline, lang: str = "es") -> list[dict]:
    d = datos_de(pipeline)
    salida = []
    for e in ETAPAS:
        r = pipeline.resultados.get(e)
        estado = r.estado() if r else "pendiente"
        salida.append({
            "etapa": e, "titulo": t(f"st_{e}", lang), "estado": estado,
            "que": t(f"j_{e}_que", lang).format(**d),
            "tecnico": t(f"j_{e}_tec", lang).format(**d),
            "gerencia": t(f"j_{e}_ger", lang).format(**d),
        })
    return salida


def markdown(pipeline, lang: str = "es") -> str:
    d = datos_de(pipeline)
    lineas = [f"# {pipeline.spec['nombre']} · {t('j_titulo', lang)}", "",
              t("j_intro", lang).format(**d), ""]
    for j in generar(pipeline, lang):
        lineas += [f"## {j['titulo']} · {j['estado']}", "", f"**{t('j_que', lang)}** {j['que']}", "",
                   f"**{t('j_tec', lang)}** {j['tecnico']}", "", f"**{t('j_ger', lang)}** {j['gerencia']}", ""]
    return "\n".join(lineas)
