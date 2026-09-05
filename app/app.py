# © 2026 Martín Viera. Todos los derechos reservados.
# Software propietario. Ver LICENSE — prohibida su redistribución.
"""MV Data Engineering · programa (Streamlit, ES/EN/PT).

Un proyecto YAML → 12 etapas con gate, cada una con su evidencia y sus
artefactos descargables. La UI no calcula nada: todo lo hace `mvde/`.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import APP_NAME, BRAND, ETAPAS, __version__, automatizacion, demos, proyecto  # noqa: E402
from mvde.i18n import LANG_NAMES, LANGS, t  # noqa: E402
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
    st.caption(f"v{__version__} · {t('demo_note', lang)}")

st.markdown("<span class='mv-badge'>MV · Data Engineering</span>", unsafe_allow_html=True)
st.title(APP_NAME)
st.caption(t("app_tagline", lang))

p = _pipeline()
if p is None:
    st.info(t("no_project", lang))
    st.stop()

tab_pipe, tab_proj, tab_data, tab_auto, tab_help = st.tabs([
    t("tab_pipeline", lang), t("tab_project", lang), t("tab_data", lang), t("tab_automation", lang), t("tab_help", lang)])

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
