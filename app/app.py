# © 2026 Martín Viera. Todos los derechos reservados.
# Software propietario. Ver LICENSE — prohibida su redistribución.
"""MV Data Engineering · programa (Streamlit, ES/EN/PT).

Un proyecto YAML → 12 etapas con gate, cada una con su evidencia y sus
artefactos descargables. La UI no calcula nada: todo lo hace `mvde/`.
"""
from __future__ import annotations

import html
import io
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import APP_NAME, BRAND, ETAPAS, __version__, auth, automatizacion, demos, frescura, ia, justificacion, proyecto, relevamiento, reuniones, salud, transformaciones  # noqa: E402
from mvde.i18n import DEFAULT_LANG, LANG_NAMES, LANGS, t  # noqa: E402
from mvde.orquestador import Pipeline  # noqa: E402

st.set_page_config(page_title=APP_NAME, page_icon="", layout="wide")
st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stToolbar"], [data-testid="stMainMenu"], #MainMenu,
[data-testid="stStatusWidget"], [data-testid="stDecoration"], footer {{ display: none !important; }}
.stApp {{ background: linear-gradient(160deg, {BRAND['navy']} 0%, #0a1a2f 100%); }}
h1, h2, h3 {{ color: {BRAND['ink']}; }}
[data-testid="stMetricValue"] {{ color: {BRAND['amber']}; }}
[data-testid="stMetricLabel"] {{ color: {BRAND['muted']}; }}
[data-testid="stSidebar"] {{ background: {BRAND['navy2']}; }}
.mv-badge {{ display:inline-block; background:rgba(242,180,65,.12); border:1px solid rgba(242,180,65,.4);
  color:{BRAND['amber']}; border-radius:20px; padding:4px 14px; font-size:12px; font-weight:700;
  letter-spacing:.06em; text-transform:uppercase; margin-bottom:6px; }}
.mv-etapa {{ border:1px solid rgba(157,176,200,.25); border-radius:10px; padding:10px 14px; margin:4px 0;
  background:rgba(255,255,255,.03); color:{BRAND['ink']}; }}
.mv-ok {{ border-left:4px solid {BRAND['green']}; }} .mv-fallo {{ border-left:4px solid {BRAND['red']}; }}
.mv-omitida {{ border-left:4px solid {BRAND['muted']}; }} .mv-pendiente {{ border-left:4px solid rgba(157,176,200,.4); }}
.mv-etapa small {{ color:{BRAND['muted']}; }}
/* Tarjetas del monitoreo de cargas: una por tabla, semáforo abajo. */
.mv-carga {{ border:1px solid rgba(157,176,200,.22); border-radius:10px; padding:10px 12px; margin:4px 0;
  background:rgba(255,255,255,.035); color:{BRAND['ink']}; height:100%; }}
.mv-carga .t {{ font-weight:700; font-size:14px; letter-spacing:.01em; }}
.mv-carga .l {{ color:{BRAND['muted']}; font-size:11px; text-transform:uppercase; letter-spacing:.06em; }}
.mv-carga .d {{ color:{BRAND['ink']}; font-size:12px; margin-top:6px; line-height:1.5; }}
.mv-carga .d b {{ color:{BRAND['muted']}; font-weight:600; }}
.mv-chip {{ display:inline-block; border-radius:4px; padding:2px 9px; font-size:10.5px; font-weight:700;
  letter-spacing:.06em; margin-top:8px; }}
.mv-chip.actualizada {{ background:{BRAND['green']}; color:#03201a; }}
.mv-chip.atrasada {{ background:{BRAND['red']}; color:#2a0606; }}
.mv-chip.sin_fecha {{ background:{BRAND['muted']}; color:#0b1626; }}
.mv-chip.vacia {{ background:{BRAND['amber2']}; color:#2a1a02; }}
/* Texto claro en todo lo que Streamlit pinta con su propio color: pestañas,
   etiquetas de widgets, captions, expanders. El tema oscuro de
   .streamlit/config.toml hace el grueso; esto cubre lo que el tema deja gris. */
[data-testid="stTabs"] button p, [data-testid="stTabs"] button {{ color:{BRAND['ink']} !important; font-weight:600; }}
[data-testid="stTabs"] button[aria-selected="true"] p {{ color:{BRAND['amber']} !important; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .stCaption {{ color:{BRAND['muted']} !important; }}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, label[data-testid="stWidgetLabel"] {{ color:{BRAND['ink']} !important; }}
[data-testid="stRadio"] label p, [data-testid="stRadio"] label span, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] span {{ color:{BRAND['ink']} !important; }}
[data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {{ color:{BRAND['ink']} !important; }}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{ color:{BRAND['ink']}; }}
.stApp a {{ color:#8fc1ff; }}
</style>""", unsafe_allow_html=True)

ICONO = {"ok": "✅", "fallo": "❌", "omitida": "⏭️", "pendiente": "⬜"}


def _dir_trabajo() -> Path:
    d = st.session_state.get("mvde_dir")
    if not d:
        d = tempfile.mkdtemp(prefix="mvde_")
        st.session_state["mvde_dir"] = d
    return Path(d)


def _pipeline() -> Pipeline | None:
    return st.session_state.get("mvde_pipeline")


def _cargar_desde_yaml(ruta: Path) -> None:
    st.session_state["mvde_pipeline"] = Pipeline.desde_yaml(ruta)
    st.session_state["mvde_yaml"] = ruta.read_text(encoding="utf-8")
    st.session_state["mvde_ruta"] = str(ruta)


# ----------------------------------------------------------------- login
# Sólo aparece si el despliegue declaró usuarios (ver mvde/auth.py). En el
# escritorio no hay variable, no hay login y la app abre como siempre.
def _puerta() -> None:
    if not auth.activo() or auth.sesion_usuario(st.session_state):
        return
    lang_login = st.session_state.get("lang", DEFAULT_LANG)
    st.markdown("<span class='mv-badge'>MV · Data Engineering</span>", unsafe_allow_html=True)
    st.title(t("auth_title", lang_login))
    st.caption(t("auth_intro", lang_login))
    with st.form("mvde_login"):
        usuario = st.text_input(t("auth_user", lang_login), key="auth_u")
        clave = st.text_input(t("auth_password", lang_login), type="password", key="auth_p")
        enviar = st.form_submit_button(t("auth_enter", lang_login), type="primary")
    if enviar:
        espera = auth.bloqueado(usuario)
        if espera:
            st.error(t("auth_locked", lang_login).format(segundos=espera))
        elif auth.verificar(usuario, clave):
            auth.abrir_sesion(st.session_state, usuario)
            st.rerun()
        else:
            # Un solo mensaje para usuario inexistente y contraseña mala: decir
            # cuál de los dos falló regala la mitad de la credencial.
            st.error(t("auth_bad", lang_login))
    st.stop()


_puerta()


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"## {APP_NAME}")
    lang = st.radio(f"{t('language', 'es')} / Language / Idioma", LANGS, format_func=lambda c: LANG_NAMES[c], horizontal=True, key="lang")
    st.caption(t("sidebar_help", lang))
    st.divider()
    st.markdown(f"**{t('project', lang)}**")
    modo = st.radio(t("project", lang), [t("project_demo", lang), t("project_upload", lang), t("project_new", lang)], label_visibility="collapsed", key="modo")
    if modo == t("project_demo", lang):
        demo = st.selectbox(t("project_source_pick", lang), demos.NOMBRES, key="demo_nombre")
        if st.button("↓ " + t("project_demo", lang), key="demo_btn"):
            carpeta = _dir_trabajo() / f"demo_{demo}"
            _cargar_desde_yaml(demos.crear(demo, carpeta))
            st.rerun()
    elif modo == t("project_upload", lang):
        up = st.file_uploader("YAML", type=["yaml", "yml"], key="up_yaml")
        datos = st.file_uploader("CSV / XLSX / Parquet", type=["csv", "xlsx", "parquet", "json"], accept_multiple_files=True, key="up_datos")
        if up is not None and st.button(t("yaml_apply", lang), key="up_btn"):
            carpeta = _dir_trabajo() / "subido"
            carpeta.mkdir(exist_ok=True)
            for f in datos or []:
                (carpeta / f.name).write_bytes(f.getvalue())
            ruta = carpeta / "proyecto.yaml"
            ruta.write_bytes(up.getvalue())
            try:
                _cargar_desde_yaml(ruta)
                st.rerun()
            except proyecto.ProyectoInvalido as exc:
                st.error(f"{t('yaml_invalid', lang)}: {exc}")
    else:
        st.caption(t("new_project_hint", lang))
        archivo = st.file_uploader("CSV / XLSX / Parquet", type=["csv", "xlsx", "parquet"], key="new_file")
        if archivo is not None and st.button(t("project_new", lang), key="new_btn"):
            carpeta = _dir_trabajo() / "nuevo"
            carpeta.mkdir(exist_ok=True)
            p = carpeta / archivo.name
            p.write_bytes(archivo.getvalue())
            tipo = {"csv": "csv", "xlsx": "excel", "parquet": "parquet"}[p.suffix.lstrip(".").lower()]
            df = pd.read_csv(p, sep=None, engine="python") if tipo == "csv" else pd.read_excel(p) if tipo == "excel" else pd.read_parquet(p)
            spec = proyecto.esqueleto(p.stem, df, p.name, tipo)
            ruta = proyecto.guardar(spec, carpeta / "proyecto.yaml")
            _cargar_desde_yaml(ruta)
            st.rerun()
    st.divider()
    quien = auth.sesion_usuario(st.session_state)
    if quien:
        st.caption(t("auth_as", lang).format(usuario=quien))
        if st.button(t("auth_logout", lang), key="auth_salir"):
            auth.cerrar_sesion(st.session_state)
            st.rerun()
    st.caption(f"v{__version__} · {t('demo_note', lang)}")

st.markdown("<span class='mv-badge'>MV · Data Engineering</span>", unsafe_allow_html=True)
st.title(APP_NAME)
st.caption(t("app_tagline", lang))

p = _pipeline()
if p is None:
    st.info(t("no_project", lang))
    st.stop()

# El orden cuenta la historia del trabajo: primero se releva y se reúne uno con
# el cliente, después se construye el pipeline, y al final se opera.
(tab_pipe, tab_survey, tab_meet, tab_health, tab_load, tab_src, tab_proj,
 tab_data, tab_ai, tab_just, tab_trans, tab_auto, tab_help) = st.tabs([
    t("tab_pipeline", lang), t("tab_survey", lang), t("tab_meetings", lang), t("tab_health", lang),
    t("tab_loads", lang), t("tab_sources", lang), t("tab_project", lang), t("tab_data", lang),
    t("tab_ai", lang), t("tab_rationale", lang), t("tab_transforms", lang),
    t("tab_automation", lang), t("tab_help", lang)])


def _ia_config() -> dict:
    """Proveedor, modelo y clave que se hayan cargado en la pestaña IA. Las dos
    pestañas nuevas usan la misma configuración: una sola clave para todo."""
    prov = st.session_state.get("ai_prov", "")
    return {"proveedor": prov, "modelo": st.session_state.get(f"ai_model_{prov}", ""),
            "api_key": st.session_state.get("ai_key", "") or None,
            "endpoint": st.session_state.get("ai_endpoint", "")}


def _guardar_spec(spec: dict) -> None:
    """Escribe el YAML en la carpeta del proyecto y recarga el pipeline."""
    ruta = Path(st.session_state["mvde_ruta"])
    proyecto.guardar(spec, ruta)
    _cargar_desde_yaml(ruta)


# ----------------------------------------------------------------- salud
ETAPA_DE_AREA = {"datos": "silver", "calidad": "calidad", "modelo": "gold", "gobernanza": "gobernanza", "bi": "reporte", "ml": "ml"}


def _tabla_ml(p: Pipeline, nombre: str) -> pd.DataFrame | None:
    """La tabla que dejó la etapa ML, de memoria o del disco (la app se
    rerenderiza sin volver a correr el pipeline)."""
    if nombre in p.gold:
        return p.gold[nombre]
    ruta = p.dirs["ml"] / f"{nombre}.parquet"
    return pd.read_parquet(ruta) if ruta.exists() else None


def _serie_proyectada(p: Pipeline, ev: dict, lang: str) -> None:
    """La proyección con la evidencia que la respalda, en este orden: qué se
    eligió y por qué, cómo le fue contra un pasado que ya se conoce, y recién
    después el futuro con su banda de desvío."""
    if ev.get("licencia_no_comercial"):
        st.error(t("pr_no_comercial", lang))
    segmentos = ev.get("segmentos") or []
    serie = _tabla_ml(p, "proyeccion")
    comp = _tabla_ml(p, "proyeccion_backtest")
    if serie is None:
        st.json({"metricas": ev.get("metricas"), "notas": ev.get("notas", [])})
        return
    nombres = [s["segmento"] for s in segmentos] or sorted(serie["segmento"].unique())
    sel = st.selectbox(t("pr_segmento", lang), nombres, key="pr_seg") if len(nombres) > 1 else nombres[0]
    info = next((x for x in segmentos if x["segmento"] == sel), None) or {
        "modelo": ev.get("modelo"), "metricas": ev.get("metricas"), "porque": ev.get("porque"),
        "gana": (ev.get("eleccion") or {}).get("le_gana_a_la_referencia"), "bandas": ev.get("bandas") or []}
    met = info.get("metricas") or {}
    c = st.columns(4)
    c[0].metric(t("pr_modelo", lang), info.get("modelo", "—"))
    c[1].metric(t("pr_error", lang), f"{round(float(met.get('smape') or 0), 2)} %")
    c[2].metric(t("pr_vs_ref", lang), f"{info.get('mejora_pct')} %" if info.get("mejora_pct") is not None else "—")
    c[3].metric(t("pr_origenes", lang), met.get("origenes_backtest", 0))
    (st.success if info.get("gana") else st.warning)(info.get("porque") or "—")

    d = serie[serie["segmento"] == sel].assign(periodo=lambda x: pd.to_datetime(x["periodo"])).sort_values("periodo")
    if comp is not None and len(comp):
        cs = comp[comp["segmento"] == sel]
        if len(cs):
            st.markdown(f"**{t('pr_real_vs', lang)}**")
            st.caption(t("pr_real_vs_pie", lang))
            ult = cs[cs["corte"] == cs["corte"].max()].assign(periodo=lambda x: pd.to_datetime(x["periodo"]))
            st.line_chart(ult.set_index("periodo")[["real", "proyectado"]])
            st.dataframe(cs.groupby("paso").agg(**{
                t("pr_n", lang): ("desvio_pct", "size"),
                t("pr_desvio_medio", lang): ("desvio_pct", "mean"),
                t("pr_desvio_abs", lang): ("desvio_pct", lambda x: x.abs().mean()),
            }).round(2), use_container_width=True)

    st.markdown(f"**{t('pr_futuro', lang)}**")
    st.line_chart(pd.DataFrame({
        t("pr_historia", lang): d["valor"].where(d["tipo"] == "historia"),
        t("pr_proyeccion", lang): d["valor"].where(d["tipo"] == "proyeccion"),
        t("pr_banda_baja", lang): d["banda_baja"], t("pr_banda_alta", lang): d["banda_alta"],
    }).set_index(d["periodo"]))
    fut = d[d["tipo"] == "proyeccion"]
    if len(fut):
        tabla = fut[["dias", "periodo", "valor", "banda_baja", "banda_alta"]].copy()
        tabla["dias"] = tabla["dias"].astype(int)
        tabla["periodo"] = tabla["periodo"].dt.strftime("%Y-%m-%d")
        for c in ("valor", "banda_baja", "banda_alta"):
            tabla[c] = pd.to_numeric(tabla[c], errors="coerce").round(0)
        st.dataframe(tabla.rename(columns={
            "dias": t("pr_dias", lang), "periodo": t("pr_periodo", lang), "valor": t("pr_proyeccion", lang),
            "banda_baja": t("pr_banda_baja", lang), "banda_alta": t("pr_banda_alta", lang)}),
            use_container_width=True, hide_index=True)
    if len(segmentos) > 1:
        st.markdown(f"**{t('pr_por_segmento', lang)}**")
        st.dataframe(pd.DataFrame([{
            t("pr_segmento", lang): x["segmento"], t("pr_modelo", lang): x["modelo"],
            "sMAPE %": (x["metricas"] or {}).get("smape"), t("pr_vs_ref", lang): x["mejora_pct"],
            t("pr_gana_col", lang): "✅" if x["gana"] else "—",
            t("pr_periodos", lang): x.get("periodos")} for x in segmentos]), use_container_width=True, hide_index=True)
    if ev.get("pesos_ensemble"):
        st.caption(t("pr_pesos", lang) + " · " + ", ".join(f"{k} {round(100 * v)} %"
                                                          for k, v in list(ev["pesos_ensemble"].items())[:6]))
    for n in ev.get("notas", []):
        st.caption(f"· {n}")


def _aplicar_y_correr(sugs: list[dict]) -> int:
    nuevo, n = salud.aplicar_todas(p.spec, sugs)
    if n:
        _guardar_spec(nuevo)
        p2 = _pipeline()
        desde = min((ETAPAS.index(ETAPA_DE_AREA.get(sg["area"], "silver")) for sg in sugs if sg.get("aplicable")), default=0)
        p2._rehidratar(ETAPAS[desde])
        p2.correr(desde=ETAPAS[desde])
    return n


with tab_health:
    st.markdown(t("h_intro", lang))
    if not p.resultados:
        st.info(t("status_pending", lang))
    else:
        ev = salud.evaluar(p)
        cols = st.columns(len(ev["areas"]) + 1)
        cols[0].metric(t("h_total", lang), f"{ev['total']}")
        for i, (a, v) in enumerate(ev["areas"].items(), 1):
            cols[i].metric(a, f"{v['puntaje']}", help=v["detalle"])
        ad = salud.antes_despues(p)
        if ad:
            st.markdown(f"**{t('h_before', lang)} → {t('h_after', lang)}** · {ad['antes']['fecha'][:16]} → {ad['despues']['fecha'][:16]} · "
                        f"{t('h_total', lang)}: {ad['antes']['total']} → {ad['despues']['total']} ({'+' if ad['delta_total'] >= 0 else ''}{ad['delta_total']})")
            st.dataframe(pd.DataFrame(ad["areas"]).rename(columns={"area": t("h_area", lang), "antes": t("h_before", lang), "despues": t("h_after", lang), "delta": t("h_delta", lang)}),
                         use_container_width=True, hide_index=True)
        else:
            st.caption(t("h_no_history", lang))
        hist = salud.historial(p)
        if len(hist) >= 2:
            st.line_chart(pd.DataFrame([{"fecha": h["fecha"][:16], "total": h["total"], **h["areas"]} for h in hist]).set_index("fecha"))
        if p.spec.get("_kpis_automaticos"):
            st.warning(t("h_auto_kpis", lang))
        st.divider()
        sugs = salud.sugerencias(p)
        st.markdown(f"### {t('h_suggestions', lang)} · {len(sugs)}")
        if not sugs:
            st.success(t("h_none", lang))
        else:
            if any(x["aplicable"] for x in sugs) and st.button(t("h_apply_all", lang), type="primary", key="h_apply_all"):
                with st.spinner("…"):
                    n = _aplicar_y_correr(sugs)
                st.success(t("h_applied", lang).format(n=n))
                st.rerun()
            for i, sg in enumerate(sugs):
                c1, c2 = st.columns([6, 1])
                sev = t(f"h_sev_{sg['severidad']}", lang)
                c1.markdown(f"<div class='mv-etapa mv-{'fallo' if sg['severidad'] == 'alta' else 'omitida' if sg['severidad'] == 'media' else 'ok'}'>"
                            f"<b>{sg['titulo']}</b> · <small>{sg['area']} · {sev}{'' if sg['aplicable'] else ' · ' + t('h_manual', lang)}</small><br><small>{sg['detalle']}</small></div>",
                            unsafe_allow_html=True)
                if sg["aplicable"] and c2.button(t("h_apply", lang), key=f"h_apply_{i}"):
                    with st.spinner("…"):
                        _aplicar_y_correr([sg])
                    st.rerun()
        if not p.spec.get("ml") and p.gold:
            cands = [{"tabla": tn, **c} for tn, df in p.gold.items() if not tn.startswith("dim_") for c in salud.sugerir_target(df)[:3]]
            if cands:
                st.markdown(f"**{t('h_target', lang)}**")
                st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

# ----------------------------------------------------------------- relevamiento
@st.cache_data(show_spinner=False, max_entries=8)
def _excel_relevamiento(datos_json: str, lang: str) -> bytes:
    """El botón de descarga necesita los bytes en cada render. Sin caché eso
    escribía un .xlsx en un temporal nuevo cada vez que alguien tipeaba una
    letra, y en un servidor que no se apaga eso se acumula."""
    ruta = Path(tempfile.mkdtemp()) / "relevamiento.xlsx"
    relevamiento.excel(ruta, json.loads(datos_json), lang)
    datos = ruta.read_bytes()
    ruta.unlink(missing_ok=True)
    ruta.parent.rmdir()
    return datos


def _ruta_relevamiento() -> Path:
    return relevamiento.ruta_de(p.spec)


def _relevamiento() -> dict:
    if "mvde_relev" not in st.session_state:
        st.session_state["mvde_relev"] = relevamiento.cargar(_ruta_relevamiento())
    return st.session_state["mvde_relev"]


def _guardar_relevamiento(datos: dict) -> Path:
    st.session_state["mvde_relev"] = datos
    return relevamiento.guardar(datos, _ruta_relevamiento())


with tab_survey:
    st.markdown(t("rv_intro", lang))
    datos_rv = _relevamiento()
    c_cli, c_av = st.columns([2, 5])
    cliente = c_cli.text_input(t("rv_client", lang), value=datos_rv.get("cliente", ""), key="rv_cliente")
    if cliente != datos_rv.get("cliente", ""):
        datos_rv = {**datos_rv, "cliente": cliente}
        _guardar_relevamiento(datos_rv)
    avance = relevamiento.avance(datos_rv, lang)
    cerradas, total = sum(a["respondidas"] for a in avance), sum(a["total"] for a in avance)
    c_av.markdown(f"**{t('rv_progress', lang)}** · {cerradas}/{total}")
    c_av.progress(cerradas / total if total else 0.0)
    st.dataframe(pd.DataFrame([{t("x_etapa", lang): a["titulo"], t("rv_answer", lang): a["respondidas"],
                                "total": a["total"], "%": a["pct"]} for a in avance]),
                 use_container_width=True, hide_index=True, height=210)
    st.divider()

    etapas_rv = list(relevamiento.por_etapa(lang))
    c_e, c_f = st.columns([3, 2])
    etapa_rv = c_e.selectbox(t("x_etapa", lang), etapas_rv, format_func=lambda e: t(f"st_{e}", lang), key="rv_etapa")
    solo_faltan = c_f.checkbox(t("rv_filter_pending", lang), key="rv_faltan")
    respuestas = datos_rv.get("respuestas") or {}
    ESTADOS_RV = list(relevamiento.ESTADOS)
    for q in relevamiento.por_etapa(lang)[etapa_rv]:
        actual = respuestas.get(q["id"], {})
        if solo_faltan and actual.get("estado") in ("respondida", "no_aplica"):
            continue
        icono = {"respondida": "✅", "no_aplica": "⏭️", "repreguntar": "🔁"}.get(actual.get("estado"), "⬜")
        with st.expander(f"{icono} {q['pregunta']}", expanded=not actual.get("respuesta")):
            st.caption(f"**{t('rv_why', lang)}** {q['porque']}  ·  **{t('rv_ask', lang)}** {q['rol_texto']}")
            resp = st.text_area(t("rv_answer", lang), value=actual.get("respuesta", ""), key=f"rv_r_{q['id']}", height=90)
            k1, k2, k3 = st.columns([2, 2, 2])
            quien = k1.text_input(t("rv_who", lang), value=actual.get("responsable", ""), key=f"rv_q_{q['id']}")
            area = k2.text_input(t("rv_area", lang), value=actual.get("area", ""), key=f"rv_a_{q['id']}")
            estado = k3.selectbox(t("rv_state", lang), ESTADOS_RV, index=ESTADOS_RV.index(actual.get("estado", "pendiente")),
                                  format_func=lambda e: t(f"rv_s_{e}", lang), key=f"rv_e_{q['id']}")
            notas = st.text_input(t("rv_notes", lang), value=actual.get("notas", ""), key=f"rv_n_{q['id']}")
            b1, b2, _b = st.columns([2, 2, 4])
            if b1.button(t("rv_save", lang), key=f"rv_save_{q['id']}", type="primary"):
                ruta_rv = _guardar_relevamiento(relevamiento.responder(datos_rv, q["id"], resp, quien, area, estado, notas))
                st.success(t("rv_saved", lang).format(ruta=ruta_rv.name))
                st.rerun()
            if b2.button(t("rv_ask_ai", lang), key=f"rv_ai_{q['id']}"):
                with st.spinner("…"):
                    r = relevamiento.repreguntas(q["pregunta"], resp, q["porque"], quien, lang, **_ia_config())
                _guardar_relevamiento(relevamiento.guardar_repreguntas(datos_rv, q["id"], r["repreguntas"]))
                st.rerun()
            pendientes = actual.get("repreguntas") or []
            if pendientes:
                st.markdown(f"**{t('rv_followups', lang)}**")
                for x in pendientes:
                    st.markdown(f"<div class='mv-etapa mv-omitida'><small>{html.escape(x)}</small></div>", unsafe_allow_html=True)

    st.divider()
    st.markdown(f"### {t('rv_to_yaml', lang)}")
    sugs_rv = relevamiento.sugerencias_yaml(datos_rv, lang)
    if not sugs_rv:
        st.caption(t("rv_to_yaml_none", lang))
    for i, sg in enumerate(sugs_rv):
        c1, c2 = st.columns([6, 1])
        c1.markdown(f"<div class='mv-etapa mv-ok'><b>{sg['campo']}</b> = {html.escape(str(sg['valor']))}"
                    f"<br><small>{sg['origen']}</small></div>", unsafe_allow_html=True)
        if c2.button(t("rv_apply", lang), key=f"rv_ap_{i}"):
            _guardar_spec(relevamiento.aplicar_sugerencia(p.spec, sg))
            st.rerun()
    st.divider()
    st.markdown(f"**{t('rv_export', lang)}**")
    e1, e2, e3 = st.columns(3)
    e1.download_button("Markdown", relevamiento.markdown(datos_rv, lang).encode("utf-8"),
                       file_name=f"RELEVAMIENTO_{lang}.md", key="dl_rv_md")
    e2.download_button("Excel", _excel_relevamiento(json.dumps(datos_rv, ensure_ascii=False, sort_keys=True), lang),
                       file_name=f"RELEVAMIENTO_{lang}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_rv_xlsx")
    e3.download_button("JSON", json.dumps(datos_rv, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="relevamiento.json", mime="application/json", key="dl_rv_json")

# ----------------------------------------------------------------- reuniones
with tab_meet:
    st.markdown(t("mt_intro", lang))
    titulo_rn = st.text_input(t("mt_title", lang), key="mt_titulo")
    origen = st.radio(t("mt_source", lang),
                      ["mt_src_file", "mt_src_audio", "mt_src_mic", "mt_src_paste"],
                      format_func=lambda k: t(k, lang), horizontal=True, key="mt_origen")
    turnos = st.session_state.get("mvde_turnos") or []

    def _cargar_turnos(nuevos: list, aviso: str = "") -> None:
        st.session_state["mvde_turnos"] = nuevos
        if aviso:
            st.session_state["mvde_turnos_aviso"] = aviso

    if origen == "mt_src_file":
        st.caption(t("mt_file_hint", lang))
        sub = st.file_uploader("VTT / SRT / TXT", type=list(reuniones.FORMATOS_TEXTO), key="mt_file")
        if sub is not None and st.button(t("mt_build", lang), key="mt_b_file", type="primary"):
            _cargar_turnos(reuniones.parsear(sub.getvalue().decode("utf-8", "ignore"), sub.name))
            st.rerun()
    elif origen == "mt_src_paste":
        texto_rn = st.text_area(t("mt_transcript", lang), height=200, key="mt_texto")
        if texto_rn.strip() and st.button(t("mt_build", lang), key="mt_b_paste", type="primary"):
            _cargar_turnos(reuniones.parsear(texto_rn))
            st.rerun()
    else:
        st.caption(t("mt_audio_hint", lang).format(mb=reuniones.LIMITE_MB) if origen == "mt_src_audio"
                   else t("mt_mic_hint", lang))
        audio = (st.file_uploader("audio / video", type=list(reuniones.FORMATOS_AUDIO), key="mt_audio")
                 if origen == "mt_src_audio" else st.audio_input(t("mt_src_mic", lang), key="mt_mic"))
        c1, c2 = st.columns([2, 3])
        trans = c1.selectbox(t("mt_provider", lang), list(reuniones.TRANSCRIPTORES),
                             format_func=lambda k: reuniones.TRANSCRIPTORES[k]["nombre"], key="mt_prov")
        clave_rn = c2.text_input(t("ai_key", lang), type="password",
                                 value=st.session_state.get("ai_key", "") if st.session_state.get("ai_prov") == trans else "",
                                 key="mt_key")
        if audio is not None and st.button(t("mt_transcribe", lang), key="mt_b_audio", type="primary"):
            with st.spinner("…"):
                try:
                    r = reuniones.transcribir(audio.getvalue(), getattr(audio, "name", "audio.wav"),
                                              trans, clave_rn, idioma=lang)
                    _cargar_turnos(r["turnos"], t("mt_no_speakers", lang))
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    if not turnos:
        st.info(t("mt_empty", lang))
    else:
        m = reuniones.minuta(turnos, titulo_rn, lang)
        if not m["con_hablantes"]:
            st.warning(t("mt_no_speakers", lang))
        c = st.columns(4)
        c[0].metric(t("mt_people", lang), len(m["participantes"]))
        c[1].metric(t("mt_decisions", lang), len(m["decisiones"]))
        c[2].metric(t("mt_commitments", lang), len(m["compromisos"]))
        c[3].metric(t("mt_risks", lang), len(m["riesgos"]))
        st.dataframe(pd.DataFrame(m["participantes"]), use_container_width=True, hide_index=True)
        for clave, titulo in (("decisiones", "mt_decisions"), ("compromisos", "mt_commitments"),
                              ("riesgos", "mt_risks"), ("preguntas", "mt_questions")):
            items = m[clave]
            st.markdown(f"### {t(titulo, lang)} · {len(items)}")
            if not items:
                st.caption(t("mt_none", lang))
            for it in items[:30]:
                marca = f" · {int(it['inicio']) // 60:02d}:{int(it['inicio']) % 60:02d}" if it.get("inicio") is not None else ""
                cuando = f" <b>[{html.escape(str(it['cuando']))}]</b>" if it.get("cuando") else ""
                st.markdown(f"<div class='mv-etapa mv-ok'><b>{html.escape(it.get('hablante') or '?')}</b>"
                            f"<small>{marca}</small>: {html.escape(it['texto'])}{cuando}</div>", unsafe_allow_html=True)
        if m["menciones"]:
            st.markdown(f"### {t('mt_by_stage', lang)}")
            for etapa_m, items in m["menciones"].items():
                with st.expander(f"{t(f'st_{etapa_m}', lang)} · {len(items)}"):
                    for it in items[:10]:
                        st.markdown(f"- **{it.get('hablante') or '?'}**: {it['texto']}")
        if st.button(t("mt_ai_add", lang), key="mt_ai"):
            with st.spinner("…"):
                m["resumen_ia"] = reuniones.resumen_ia(turnos, lang, **_ia_config())
            st.session_state["mvde_resumen_ia"] = m["resumen_ia"]
            st.rerun()
        if st.session_state.get("mvde_resumen_ia"):
            m["resumen_ia"] = st.session_state["mvde_resumen_ia"]
            st.markdown(f"### {t('mt_ai_summary', lang)}")
            st.markdown(m["resumen_ia"])

        st.divider()
        st.markdown(f"### {t('mt_to_survey', lang)}")
        st.caption(t("mt_to_survey_hint", lang))
        propuestas = reuniones.sugerir_respuestas(turnos, lang)
        if not propuestas:
            st.caption(t("mt_none", lang))
        catalogo_rv = {q["id"]: q for q in relevamiento.catalogo(lang)}
        for i, (qid, prop) in enumerate(list(propuestas.items())[:12]):
            q = catalogo_rv[qid]
            c1, c2 = st.columns([6, 1])
            c1.markdown(f"<div class='mv-etapa mv-omitida'><b>{html.escape(q['pregunta'])}</b><br>"
                        f"<small>{html.escape(prop.get('hablante') or '?')}: {html.escape(prop['texto'])}</small></div>",
                        unsafe_allow_html=True)
            if c2.button(t("mt_use", lang), key=f"mt_use_{i}"):
                base_rv = _relevamiento()
                _guardar_relevamiento(relevamiento.responder(
                    base_rv, qid, prop["texto"], prop.get("hablante") or "", "",
                    "repreguntar", t("mt_titulo", lang) + ": " + (titulo_rn or "")))
                st.success(t("rv_saved", lang).format(ruta=relevamiento.ARCHIVO))

        st.divider()
        g1, g2 = st.columns(2)
        if g1.button(t("mt_build", lang) + " → " + t("download", lang), key="mt_guardar", type="primary"):
            ruta_m = reuniones.guardar(reuniones.carpeta(p), m, turnos)
            st.success(t("mt_saved", lang).format(ruta=ruta_m.name))
        g2.download_button(f"{t('download', lang)} MINUTA_{lang}.md",
                           reuniones.markdown(m, lang).encode("utf-8"),
                           file_name=f"MINUTA_{lang}.md", key="dl_minuta")
        previas = reuniones.listar(reuniones.carpeta(p))
        if previas:
            with st.expander(f"{t('mt_previous', lang)} · {len(previas)}"):
                for f_ in previas[:20]:
                    st.markdown(f"- `{f_.name}`")

# ----------------------------------------------------------------- cargas
def _hace(horas: float | None, lang: str) -> str:
    if horas is None:
        return "—"
    if horas < 48:
        return t("fr_ago", lang).format(horas=f"{horas:,.0f}".replace(",", "."))
    return t("fr_ago_days", lang).format(dias=f"{horas / 24:,.0f}".replace(",", "."))


with tab_load:
    st.markdown(t("fr_intro", lang))
    if not p.resultados or not p.silver:
        st.info(t("status_pending", lang))
    else:
        filas = p.frescura or frescura.evaluar(p)
        res = frescura.resumen(filas)
        st.markdown(f"**{t('tab_loads', lang)}** · {t('fr_updated_at', lang).format(fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
        c = st.columns(4)
        for i, e in enumerate(frescura.ESTADOS):
            c[i].metric(t(f"fr_e_{e}", lang), res.get(e, 0))
        # Tarjetas: una por tabla, en filas de a cinco como un tablero de operación.
        POR_FILA = 5
        for arranque in range(0, len(filas), POR_FILA):
            cols = st.columns(POR_FILA)
            for col, f in zip(cols, filas[arranque:arranque + POR_FILA]):
                dato = (f["fecha_datos"] or "").replace("T", " ")[:16]
                carga = (f["fecha_carga"] or "").replace("T", " ")[:16]
                detalle = ""
                if f["estado"] == "sin_fecha":
                    detalle = f"<br><small style='color:{BRAND['muted']}'>{t('fr_no_date_hint', lang)}</small>"
                elif f["estado"] == "atrasada" and f["fecha_datos"]:
                    detalle = (f"<br><small style='color:{BRAND['muted']}'>"
                               f"{t('fr_late_hint', lang).format(fecha=dato, tolerancia=int(f['tolerancia_horas']))}</small>")
                col.markdown(
                    f"<div class='mv-carga'><div class='t'>{html.escape(f['tabla'])}</div>"
                    f"<div class='l'>{f['capa']} · {t('fr_every', lang)} {f['cada']}</div>"
                    f"<div class='d'><b>{t('fr_data', lang)}:</b> {dato or '—'} <small>{_hace(f['horas_desde_datos'], lang) if f['fecha_datos'] else ''}</small><br>"
                    f"<b>{t('fr_load', lang)}:</b> {carga or '—'} <small>{_hace(f['horas_desde_carga'], lang) if f['fecha_carga'] else ''}</small><br>"
                    f"<b>{t('fr_rows', lang)}:</b> {f['filas']:,}".replace(",", ".")
                    + f"</div><span class='mv-chip {f['estado']}'>{t('fr_e_' + f['estado'], lang)}</span>{detalle}</div>",
                    unsafe_allow_html=True)
        st.divider()
        # Frecuencia REAL: cada cuánto cambió el dato de verdad, según el historial.
        hist = frescura.historial(p)
        st.markdown(f"### {t('fr_real', lang)}")
        medidas = []
        for f in filas:
            real = frescura.frecuencia_real(hist, f["tabla"])
            if real:
                medidas.append({t("fr_table", lang): f["tabla"], t("fr_every", lang): f["cada"],
                                f"{t('fr_median', lang)} (h)": real["mediana_horas"],
                                "min (h)": real["minimo_horas"], "max (h)": real["maximo_horas"],
                                "n": real["observaciones"]})
        if medidas:
            st.dataframe(pd.DataFrame(medidas), use_container_width=True, hide_index=True)
        else:
            st.caption(f"{t('fr_real_none', lang)}  ·  {t('fr_history', lang)}: {len(hist)}")
        with st.expander(t("fr_table", lang)):
            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
        st.caption(t("fr_declare", lang))
        st.download_button(f"{t('download', lang)} frescura.json",
                           json.dumps({"resumen": res, "tablas": filas}, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name="frescura.json", mime="application/json", key="dl_frescura")

# ----------------------------------------------------------------- fuentes
with tab_src:
    st.markdown(t("src_intro", lang))
    st.markdown(f"**{t('src_current', lang)}**")
    st.dataframe(pd.DataFrame([{"nombre": f["nombre"], "tipo": f.get("tipo"), "ruta/url": f.get("ruta") or f.get("url", "")}
                               for f in p.spec["fuentes"]]), use_container_width=True, hide_index=True)
    c_f, c_s = st.columns(2)
    with c_f:
        st.markdown(f"**{t('src_files', lang)}**")
        subidos = st.file_uploader("CSV / XLSX / Parquet / JSON", type=["csv", "txt", "xlsx", "parquet", "json"],
                                   accept_multiple_files=True, key="src_files")
        if subidos and st.button(t("src_add_files", lang), key="src_add_files"):
            base = Path(st.session_state["mvde_ruta"]).parent
            spec = dict(p.spec)
            nombres = {f["nombre"] for f in spec["fuentes"]}
            for f in subidos:
                (base / f.name).write_bytes(f.getvalue())
                tipo = {"csv": "csv", "txt": "csv", "xlsx": "excel", "parquet": "parquet", "json": "json"}[f.name.rsplit(".", 1)[-1].lower()]
                nombre = Path(f.name).stem.lower().replace(" ", "_")
                if nombre not in nombres:
                    spec["fuentes"].append({"nombre": nombre, "tipo": tipo, "ruta": f.name})
                    spec.setdefault("silver", {})[nombre] = {"tipos": "auto"}
            _guardar_spec(spec)
            st.rerun()
    with c_s:
        st.markdown(f"**{t('src_sql', lang)}**")
        motor = st.selectbox(t("src_engine", lang), ["SQL Server (pyodbc)", "PostgreSQL", "MySQL / MariaDB", "SQLite (archivo)", "DuckDB (archivo)"], key="src_engine")
        nombre_f = st.text_input(t("src_name", lang), value="tabla_sql", key="src_name")
        if motor in ("SQLite (archivo)", "DuckDB (archivo)"):
            ruta_db = st.text_input("ruta .db / .duckdb", key="src_dbfile")
            consulta = st.text_area(t("src_query", lang), key="src_query_file", height=80)
            if st.button(t("src_add_sql", lang), key="src_add_file_db"):
                spec = dict(p.spec)
                f = {"nombre": nombre_f, "tipo": "sqlite" if motor.startswith("SQLite") else "duckdb", "ruta": ruta_db}
                f["consulta" if consulta.strip().lower().startswith(("select", "with")) else "tabla"] = consulta.strip() or nombre_f
                spec["fuentes"].append(f)
                _guardar_spec(spec)
                st.rerun()
        else:
            host = st.text_input(t("src_host", lang), key="src_host")
            base_db = st.text_input(t("src_db", lang), key="src_db")
            usuario = st.text_input(t("src_user", lang), key="src_user")
            var_pwd = st.text_input(t("src_pwd_env", lang), value="DB_PASSWORD", key="src_pwd_env")
            consulta = st.text_area(t("src_query", lang), key="src_query", height=80)
            st.caption(t("src_pwd_hint", lang))
            pref = {"SQL Server (pyodbc)": "mssql+pyodbc://{u}:{p}@{h}/{d}?driver=ODBC+Driver+17+for+SQL+Server",
                    "PostgreSQL": "postgresql+psycopg2://{u}:{p}@{h}/{d}", "MySQL / MariaDB": "mysql+pymysql://{u}:{p}@{h}/{d}"}[motor]
            url_env = pref.format(u=usuario, p="${" + var_pwd + "}", h=host, d=base_db)
            st.code(url_env, language="text")
            b1, b2 = st.columns(2)
            if b1.button(t("src_test", lang), key="src_test"):
                pwd = os.environ.get(var_pwd, "")
                if not pwd:
                    st.warning(f"{var_pwd} = ∅")
                else:
                    try:
                        import sqlalchemy as sa
                        with sa.create_engine(pref.format(u=usuario, p=pwd, h=host, d=base_db)).connect() as con:
                            con.execute(sa.text("SELECT 1"))
                        st.success("OK")
                    except Exception as exc:  # noqa: BLE001 - se muestra el motivo
                        st.error(str(exc).splitlines()[0])
            if b2.button(t("src_add_sql", lang), key="src_add_sql"):
                spec = dict(p.spec)
                f = {"nombre": nombre_f, "tipo": "sql", "url": url_env}
                f["consulta" if consulta.strip().lower().startswith(("select", "with")) else "tabla"] = consulta.strip() or nombre_f
                spec["fuentes"].append(f)
                spec.setdefault("silver", {})[nombre_f] = {"tipos": "auto"}
                _guardar_spec(spec)
                st.rerun()

# ----------------------------------------------------------------- pipeline
with tab_pipe:
    c1, c2 = st.columns([2, 5])
    with c1:
        if st.button(t("run_all", lang), type="primary", key="run_all"):
            with st.spinner("…"):
                p.correr()
            st.rerun()
    ok = [e for e, r in p.resultados.items() if r.ok]
    fallo = [e for e, r in p.resultados.items() if not r.ok and not r.omitida]
    if fallo:
        r = p.resultados[fallo[0]]
        st.error(t("gate_stopped", lang).format(etapa=t(f"st_{fallo[0]}", lang), motivo=r.error))
    elif len(p.resultados) == len(ETAPAS):
        st.success(t("all_ok", lang).format(n=len(ETAPAS), seg=sum(r.segundos for r in p.resultados.values())))
    for e in ETAPAS:
        r = p.resultados.get(e)
        estado = r.estado() if r else "pendiente"
        st.markdown(f"<div class='mv-etapa mv-{estado}'>{ICONO[estado]} <b>{t(f'st_{e}', lang)}</b> · "
                    f"<small>{t(f'd_{e}', lang)}</small><br><small>{(r.resumen or r.error) if r else t('status_pending', lang)}"
                    f"{f' · {r.segundos}s' if r else ''}</small></div>", unsafe_allow_html=True)
        with st.expander(f"{t('evidence', lang)} · {t(f'st_{e}', lang)}", expanded=False):
            b1, b2, _ = st.columns([1, 1, 4])
            if b1.button(t("run_stage", lang), key=f"run_{e}"):
                if e != "fuentes":
                    p._rehidratar(e)
                p.etapa(e)
                st.rerun()
            if b2.button(t("run_from", lang), key=f"from_{e}"):
                p.correr(desde=e)
                st.rerun()
            if r:
                if r.error:
                    st.code(r.error)
                ev = r.evidencia or {}
                if e == "calidad" and ev.get("por_dimension"):
                    st.dataframe(pd.DataFrame(ev["por_dimension"]).T, use_container_width=True)
                    if ev.get("fallidas"):
                        st.dataframe(pd.DataFrame(ev["fallidas"]), use_container_width=True)
                elif e == "reporte" and ev.get("kpis"):
                    cols = st.columns(min(4, len(ev["kpis"])))
                    for i, k in enumerate(ev["kpis"]):
                        cols[i % 4].metric(k["nombre"], k["valor"])
                elif e == "dax" and ev.get("medidas"):
                    st.dataframe(pd.DataFrame(ev["medidas"]), use_container_width=True)
                elif e == "ml" and ev.get("tipo") == "serie":
                    _serie_proyectada(p, ev, lang)
                elif e == "ml" and ev.get("metricas"):
                    st.json({"metricas": ev["metricas"], "importancia": ev.get("importancia", {}), "notas": ev.get("notas", [])})
                elif e == "gobernanza" and ev.get("linaje"):
                    st.json(ev.get("puntajes", {}))
                    st.dataframe(pd.DataFrame(ev["linaje"]), use_container_width=True)
                elif ev:
                    st.json(ev)
                if r.artefactos:
                    st.markdown(f"**{t('artifacts', lang)}**")
                    for i, a in enumerate(r.artefactos):
                        pa = Path(a)
                        if pa.is_file():
                            if pa.suffix == ".png":
                                st.image(str(pa))
                            # La clave lleva el índice: dos artefactos pueden llamarse igual (bronze/x/part-000.parquet).
                            st.download_button(f"{t('download', lang)} {pa.parent.name}/{pa.name}", pa.read_bytes(),
                                               file_name=pa.name, key=f"dl_{e}_{i}")
                        else:
                            st.caption(str(pa))
    if (p.dirs["entrega"] / "RESUMEN.md").exists():
        st.divider()
        st.markdown(f"### {t('st_entrega', lang)}")
        st.markdown((p.dirs["entrega"] / "RESUMEN.md").read_text(encoding="utf-8"))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in p.dirs["entrega"].rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(p.dirs["entrega"]))
        st.download_button(f"{t('download', lang)} entrega.zip", buf.getvalue(), file_name="entrega.zip", key="dl_entrega")

# ----------------------------------------------------------------- proyecto
with tab_proj:
    st.markdown(f"**{t('yaml_editor', lang)}**")
    texto = st.text_area("YAML", st.session_state.get("mvde_yaml", ""), height=520, key="yaml_txt", label_visibility="collapsed")
    if st.button(t("yaml_apply", lang), key="yaml_apply"):
        try:
            base = Path(st.session_state["mvde_ruta"]).parent
            spec = proyecto.desde_texto(texto, base)
            ruta = base / "proyecto.yaml"
            ruta.write_text(texto, encoding="utf-8")
            _cargar_desde_yaml(ruta)
            st.success("OK")
            st.rerun()
        except proyecto.ProyectoInvalido as exc:
            st.error(f"{t('yaml_invalid', lang)}: {exc}")

# ----------------------------------------------------------------- datos
with tab_data:
    capas = {"bronze": p.tablas, "silver": p.silver, "gold": p.gold}
    capa = st.selectbox(t("layer", lang), list(capas), key="capa")
    tablas = capas[capa]
    if not tablas:
        st.info(t("status_pending", lang))
    else:
        nombre = st.selectbox(t("tables_loaded", lang), list(tablas), key="tabla_sel")
        df = tablas[nombre]
        m1, m2 = st.columns(2)
        m1.metric(t("rows", lang), f"{len(df):,}")
        m2.metric(t("columns", lang), df.shape[1])
        st.markdown(f"**{t('preview', lang)}**")
        st.dataframe(df.head(200), use_container_width=True)
        st.dataframe(pd.DataFrame({"columna": df.columns, "tipo": [str(x) for x in df.dtypes], "nulos %": [round(100 * float(df[c].isna().mean()), 1) for c in df.columns]}), use_container_width=True)

# ----------------------------------------------------------------- IA
with tab_ai:
    st.markdown(t("ai_intro", lang))
    provs = ia.proveedores()
    if not ia.disponible():
        st.warning(t("ai_no_dxl", lang))
    c1, c2, c3 = st.columns([2, 2, 3])
    prov = c1.selectbox(t("ai_provider", lang), list(provs), format_func=lambda k: provs[k]["nombre"], key="ai_prov")
    modelos_est = [m for m, _ in provs[prov].get("modelos", [])]
    modelos = st.session_state.get(f"ai_modelos_{prov}") or modelos_est
    modelo = c2.selectbox(t("ai_model", lang), modelos, key=f"ai_model_{prov}")
    clave = c3.text_input(t("ai_key", lang), type="password", key="ai_key") if provs[prov].get("env") else ""
    endpoint = st.text_input(t("ai_endpoint", lang), key="ai_endpoint") if provs[prov].get("necesita_endpoint") else ""
    b1, b2, _ = st.columns([2, 2, 4])
    if b1.button(t("ai_refresh", lang), key="ai_refresh"):
        try:
            lista = ia.listar_modelos(prov, clave or None, endpoint)
            st.session_state[f"ai_modelos_{prov}"] = lista or modelos_est
            st.success(t("ai_models_updated", lang).format(n=len(lista)))
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    if b2.button(t("ai_test", lang), key="ai_test"):
        try:
            st.success(ia._dxl().probar_conexion(prov, modelo, clave or None, endpoint))
        except Exception as exc:  # noqa: BLE001 - se muestra el motivo
            st.error(str(exc).splitlines()[0])
    st.divider()
    pregunta = st.text_area(t("ai_ask", lang), placeholder=t("ai_ask_hint", lang), key="ai_q", height=90)
    if st.button(t("ai_send", lang), type="primary", key="ai_send") and pregunta.strip():
        with st.spinner("…"):
            try:
                r = ia.preguntar(pregunta, p, prov, modelo, clave or None, endpoint, lang)
            except Exception as exc:  # noqa: BLE001 - la IA falló: se dice y se ofrece el modo local
                r = {"respuesta": f"{exc}", "sql": None, "tabla": None, "modo": "error", "nota": "", "error": str(exc)}
        st.session_state.setdefault("ai_hist", []).insert(0, {"q": pregunta, **{k: v for k, v in r.items() if k != "tabla"}, "tabla": r.get("tabla")})
    for i, h in enumerate(st.session_state.get("ai_hist", [])[:8]):
        with st.container(border=True):
            st.markdown(f"**{h['q']}**  \n<small>{t('ai_mode', lang)}: {h['modo']}</small>", unsafe_allow_html=True)
            st.markdown(h["respuesta"])
            if h.get("sql"):
                st.caption(t("ai_sql_used", lang))
                st.code(h["sql"], language="sql")
            if h.get("tabla") is not None:
                st.dataframe(h["tabla"], use_container_width=True)

# ----------------------------------------------------------------- justificación
with tab_just:
    if not p.resultados:
        st.info(t("status_pending", lang))
    else:
        for j in justificacion.generar(p, lang):
            st.markdown(f"<div class='mv-etapa mv-{j['estado']}'>{ICONO.get(j['estado'], '⬜')} <b>{j['titulo']}</b><br>"
                        f"<small><b>{t('j_que', lang)}</b> {j['que']}</small><br>"
                        f"<small><b>{t('j_tec', lang)}</b> {j['tecnico']}</small><br>"
                        f"<small><b>{t('j_ger', lang)}</b> {j['gerencia']}</small></div>", unsafe_allow_html=True)
        md = justificacion.markdown(p, lang)
        st.download_button(f"{t('download', lang)} JUSTIFICACION_{lang}.md", md.encode("utf-8"), file_name=f"JUSTIFICACION_{lang}.md", key="dl_just")

# ----------------------------------------------------------------- transformaciones
with tab_trans:
    if not p.resultados:
        st.info(t("x_no_steps", lang))
    else:
        pasos_ = transformaciones.pasos(p, lang)
        st.markdown(t("x_intro", lang).format(fecha=datetime.now().strftime("%Y-%m-%d %H:%M"), n_pasos=len(pasos_),
                                              n_etapas=len({s_["etapa"] for s_ in pasos_})))
        c_v, c_e = st.columns([1, 2])
        vista = c_v.radio(t("x_view", lang), [t("x_view_all", lang), t("x_view_tec", lang), t("x_view_cri", lang)], horizontal=True, key="x_view")
        etapas_con = [e for e in ETAPAS if any(s_["etapa"] == e for s_ in pasos_)]
        elegidas = c_e.multiselect(t("x_filter_stage", lang), etapas_con, default=etapas_con, format_func=lambda e: t(f"st_{e}", lang), key="x_etapas")
        st.dataframe(pd.DataFrame(transformaciones.resumen(pasos_, lang)).rename(
            columns={"etapa": t("x_etapa", lang), "pasos": t("x_n_pasos", lang), "fallos": t("x_failed", lang), "objetos": t("x_objeto", lang)}),
            use_container_width=True, hide_index=True)
        st.markdown(f"**{t('x_export', lang)}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.download_button("HTML", transformaciones.html(p, lang).encode("utf-8"), file_name=f"TRANSFORMACIONES_{lang}.html", mime="text/html", key="dl_x_html")
        for col, fmt, fn, mime in ((c2, "docx", transformaciones.docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                                   (c3, "pdf", transformaciones.pdf, "application/pdf")):
            try:
                col.download_button("Word" if fmt == "docx" else "PDF", fn(p, lang), file_name=f"TRANSFORMACIONES_{lang}.{fmt}", mime=mime, key=f"dl_x_{fmt}")
            except RuntimeError as exc:
                col.caption(str(exc))
        c4.download_button("JSON", json.dumps(pasos_, ensure_ascii=False, indent=2).encode("utf-8"), file_name=f"TRANSFORMACIONES_{lang}.json", mime="application/json", key="dl_x_json")
        st.caption(t("x_export_hint", lang))
        etapa_actual = None
        for s_ in pasos_:
            if s_["etapa"] not in elegidas:
                continue
            if s_["etapa"] != etapa_actual:
                etapa_actual = s_["etapa"]
                st.markdown(f"### {s_['etapa_titulo']}")
                st.caption(t(f"d_{etapa_actual}", lang))
            lineas = []
            if vista != t("x_view_cri", lang):
                lineas.append(f"<small><b>{t('x_tec', lang)}</b> {html.escape(s_['tecnico'])}</small>")
            if vista != t("x_view_tec", lang):
                lineas.append(f"<small><b style='color:{BRAND['amber']}'>{t('x_cri', lang)}</b> {html.escape(s_['criollo'])}</small>")
                lineas.append(f"<small><b style='color:{BRAND['blue']}'>{t('x_imp', lang)}</b> {html.escape(s_['impacto'])}</small>")
            if vista != t("x_view_cri", lang):
                lineas.append(f"<small>{t('x_ev', lang)}: {html.escape(str(s_['evidencia']))}</small>")
            st.markdown(f"<div class='mv-etapa mv-{s_['estado']}'><b style='color:{BRAND['amber']}'>{s_['n']}</b> &nbsp;<b>{html.escape(s_['objeto'])}</b> "
                        f"<small>· {s_['tipo']}</small><br>" + "<br>".join(lineas) + "</div>", unsafe_allow_html=True)

# ----------------------------------------------------------------- automatización
with tab_auto:
    st.markdown(t("automation_intro", lang))
    ruta = st.session_state.get("mvde_ruta", "proyecto.yaml")
    st.markdown(f"**{t('cli_hint', lang)}**")
    st.code(automatizacion.comando(ruta), language="bash")
    st.code(automatizacion.bat_windows(Path(ruta).name), language="bat")
    st.code(automatizacion.cron(ruta, (p.spec.get("automatizacion") or {}).get("hora", "05:00")), language="bash")
    st.code(automatizacion.dag_airflow(p.spec, ruta), language="python")

# ----------------------------------------------------------------- ayuda
with tab_help:
    st.markdown(t("help_text", lang))
    st.code(json.dumps({"etapas": ETAPAS}, indent=2))
    st.caption(f"{APP_NAME} v{__version__} · {os.getcwd()}")
