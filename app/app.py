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

from mvde import APP_NAME, BRAND, ETAPAS, __version__, automatizacion, demos, ia, justificacion, proyecto, salud  # noqa: E402
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

tab_pipe, tab_health, tab_src, tab_proj, tab_data, tab_ai, tab_just, tab_auto, tab_help = st.tabs([
    t("tab_pipeline", lang), t("tab_health", lang), t("tab_sources", lang), t("tab_project", lang), t("tab_data", lang), t("tab_ai", lang),
    t("tab_rationale", lang), t("tab_automation", lang), t("tab_help", lang)])


def _guardar_spec(spec: dict) -> None:
    """Escribe el YAML en la carpeta del proyecto y recarga el pipeline."""
    ruta = Path(st.session_state["mvde_ruta"])
    proyecto.guardar(spec, ruta)
    _cargar_desde_yaml(ruta)


# ----------------------------------------------------------------- salud
ETAPA_DE_AREA = {"datos": "silver", "calidad": "calidad", "modelo": "gold", "gobernanza": "gobernanza", "bi": "reporte", "ml": "ml"}


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
