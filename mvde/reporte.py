# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 9 · Reporte: KPIs desde el almacén, gráficos PNG y reporte Excel + HTML.

KPI (YAML `kpis`):
  - {nombre, tabla, columna?, agregacion: sum|count|count_distinct|avg|min|max, formato, por?: col}
  - {nombre, tipo: ratio, numerador: {tabla, columna, agregacion}, denominador: {...}, formato: "0.0%"}
  - {nombre, tipo: sql, sql: "SELECT ... una fila una columna"}
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import BRAND  # noqa: E402
from .almacen import consultar  # noqa: E402

INK, MUTED, GRID, SERIE, MALO = "#1f2937", "#6b7280", "#e5e7eb", "#2563eb", "#b91c1c"


def _agg_sql(k: dict) -> str:
    agg = k.get("agregacion", "sum")
    col = k.get("columna")
    if agg == "count":
        return "COUNT(*)"
    if agg == "count_distinct":
        return f'COUNT(DISTINCT "{col}")'
    return f'{agg.upper()}("{col}")'


def sql_kpi(k: dict) -> str:
    tipo = k.get("tipo", "agregacion")
    if tipo == "sql":
        return k["sql"]
    if tipo == "ratio":
        n, d = k["numerador"], k["denominador"]
        if n.get("tabla") == d.get("tabla"):
            return f'SELECT {_agg_sql(n)} * 1.0 / NULLIF({_agg_sql(d)}, 0) FROM gold."{n["tabla"]}"'
        return (f'SELECT (SELECT {_agg_sql(n)} FROM gold."{n["tabla"]}") * 1.0 / '
                f'NULLIF((SELECT {_agg_sql(d)} FROM gold."{d["tabla"]}"), 0)')
    return f'SELECT {_agg_sql(k)} FROM gold."{k["tabla"]}"'


def formatear(valor, formato: str | None) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    f = formato or "#,0"
    if f.endswith("%"):
        dec = len(f.split(".")[1]) - 1 if "." in f else 0
        return f"{valor * 100:,.{dec}f} %".replace(",", "X").replace(".", ",").replace("X", ".")
    dec = len(f.split(".")[1]) if "." in f else 0
    return f"{valor:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def kpis_automaticos(gold: dict[str, pd.DataFrame], maximo: int = 8) -> list[dict]:
    """Cuando el YAML no declara KPIs: conteo de cada hecho y suma de sus
    columnas numéricas que no son claves. Es un punto de partida, no el final."""
    out = []
    for nombre, df in gold.items():
        if nombre.startswith("dim_") or nombre == "ml_scores":
            continue
        out.append({"nombre": f"{nombre} · filas", "tabla": nombre, "agregacion": "count", "formato": "#,0"})
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]) and not c.endswith("_key") and not pd.api.types.is_bool_dtype(df[c]) and df[c].nunique() > 2:
                out.append({"nombre": f"{c} · total", "tabla": nombre, "columna": c, "agregacion": "sum", "formato": "#,0"})
            if len(out) >= maximo:
                return out
    return out[:maximo]


def calcular_kpis(spec: dict, ruta_db: Path) -> list[dict]:
    out = []
    for k in spec.get("kpis") or []:
        try:
            v = consultar(ruta_db, sql_kpi(k)).iloc[0, 0]
            v = None if v is None or pd.isna(v) else float(v)
            out.append({"nombre": k["nombre"], "valor": v, "texto": formatear(v, k.get("formato")), "ok": True, "sql": sql_kpi(k)})
        except Exception as exc:  # noqa: BLE001 - el KPI mal escrito se reporta, no tumba la etapa
            out.append({"nombre": k["nombre"], "valor": None, "texto": "—", "ok": False, "error": str(exc).splitlines()[0], "sql": sql_kpi(k)})
    return out


def _estilo(ax, titulo, sub=""):
    ax.set_title(f"{titulo}\n{sub}" if sub else titulo, loc="left", fontsize=11, color=INK, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _p: f"{v:,.0f}".replace(",", "."))
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)


def graficos(spec: dict, ruta_db: Path, gold: dict[str, pd.DataFrame], carpeta: Path) -> list[Path]:
    """Automáticos: (1) cada KPI de suma con `por: columna` → barras; (2) si hay
    calendario y un hecho con fecha_key → serie mensual de la primera medida."""
    carpeta.mkdir(parents=True, exist_ok=True)
    salidas = []
    for i, k in enumerate(spec.get("kpis") or []):
        if k.get("tipo", "agregacion") != "agregacion" or not k.get("por"):
            continue
        por = k["por"]
        if "." in por:      # dim_sucursal.sucursal → join con la dimensión por su clave surrogada
            dim, col = por.split(".", 1)
            sql = (f'SELECT d."{col}" AS cat, {_agg_sql(k).replace(f"({chr(34)}", f"(f.{chr(34)}")} AS v FROM gold."{k["tabla"]}" f '
                   f'JOIN gold."{dim}" d USING ("{dim}_key") GROUP BY 1 ORDER BY 2 DESC LIMIT 12')
        else:
            sql = f'SELECT "{por}" AS cat, {_agg_sql(k)} AS v FROM gold."{k["tabla"]}" GROUP BY 1 ORDER BY 2 DESC LIMIT 12'
        try:
            df = consultar(ruta_db, sql)
        except Exception:  # noqa: BLE001
            continue
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(df["cat"].astype(str)[::-1], df["v"][::-1], color=SERIE, height=0.55)
        for j, v in enumerate(df["v"][::-1]):
            ax.text(v, j, " " + formatear(float(v), k.get("formato")), va="center", color=INK, fontsize=9)
        _estilo(ax, f"{k['nombre']} por {k['por']}")
        ax.xaxis.grid(True, color=GRID)
        ax.yaxis.grid(False)
        fig.tight_layout()
        p = carpeta / f"{i + 1:02d}_{k['nombre'][:30].replace(' ', '_').replace('/', '-')}.png"
        fig.savefig(p, dpi=140)
        plt.close(fig)
        salidas.append(p)
    if "dim_calendario" in gold:
        for nombre, df in gold.items():
            if "fecha_key" not in df.columns or nombre == "dim_calendario":
                continue
            medidas = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not c.endswith("_key")]
            if not medidas:
                continue
            m = medidas[0]
            serie = consultar(ruta_db, f'SELECT c.anio_mes, SUM(f."{m}") v FROM gold."{nombre}" f JOIN gold.dim_calendario c USING (fecha_key) GROUP BY 1 ORDER BY 1')
            if len(serie) < 2:
                continue
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(serie["anio_mes"], serie["v"], color=SERIE, linewidth=2, marker="o")
            _estilo(ax, f"{m} por mes · {nombre}")
            ax.tick_params(axis="x", rotation=45)
            fig.tight_layout()
            p = carpeta / f"serie_{nombre}_{m}.png"
            fig.savefig(p, dpi=140)
            plt.close(fig)
            salidas.append(p)
            break
    return salidas


def excel(ruta: Path, spec: dict, kpis: list[dict], calidad: dict, catalogo: pd.DataFrame,
          gold: dict[str, pd.DataFrame], ml: dict | None) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta, engine="xlsxwriter") as w:
        wb = w.book
        cab = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#1e3a8a", "border": 1})
        resumen = pd.DataFrame([{"KPI": k["nombre"], "Valor": k["texto"]} for k in kpis])
        resumen.to_excel(w, sheet_name="Resumen", index=False, startrow=2)
        ws = w.sheets["Resumen"]
        ws.write(0, 0, spec.get("reporte", {}).get("titulo") or spec["nombre"], wb.add_format({"bold": True, "font_size": 14}))
        for i, c in enumerate(resumen.columns):
            ws.write(2, i, c, cab)
        ws.set_column(0, 0, 40)
        ws.set_column(1, 1, 18)
        cal = pd.DataFrame(calidad.get("resultados", []))
        if len(cal):
            cal.to_excel(w, sheet_name="Calidad", index=False)
            for i, c in enumerate(cal.columns):
                w.sheets["Calidad"].write(0, i, c, cab)
            w.sheets["Calidad"].set_column(0, 6, 22)
        if len(catalogo):
            catalogo.to_excel(w, sheet_name="Diccionario", index=False)
            for i, c in enumerate(catalogo.columns):
                w.sheets["Diccionario"].write(0, i, c, cab)
            w.sheets["Diccionario"].set_column(0, 9, 18)
        if ml:
            pd.DataFrame([{"métrica": k, "valor": v} for k, v in ml["metricas"].items()] +
                         [{"métrica": f"importancia · {k}", "valor": v} for k, v in ml["importancia"].items()]
                         ).to_excel(w, sheet_name="ML", index=False)
        for nombre, df in gold.items():
            df.head(5000).to_excel(w, sheet_name=nombre[:31], index=False)
    return ruta


def html_reporte(ruta: Path, spec: dict, kpis: list[dict], calidad: dict, imagenes: list[Path],
                 ml: dict | None, lang: str = "es") -> Path:
    import base64
    titulo = html.escape(spec.get("reporte", {}).get("titulo") or spec["nombre"])
    tarjetas = "".join(f'<div class="kpi"><div class="v">{html.escape(k["texto"])}</div><div class="l">{html.escape(k["nombre"])}</div></div>' for k in kpis)
    imgs = ""
    for p in imagenes:
        b64 = base64.b64encode(p.read_bytes()).decode()
        imgs += f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(p.stem)}"></figure>'
    fallidas = calidad.get("fallidas", [])
    filas_cal = "".join(f"<tr><td>{html.escape(r['regla'])}</td><td>{html.escape(r['dimension'])}</td><td>{html.escape(r['detalle'])}</td><td>{'crítica' if r['critico'] else 'informativa'}</td></tr>" for r in fallidas) or "<tr><td colspan=4>Sin hallazgos</td></tr>"
    ml_html = ""
    if ml:
        ml_html = "<h2>Modelo</h2><table><tr><th>métrica</th><th>valor</th></tr>" + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in ml["metricas"].items()) + "</table>"
    doc = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{titulo}</title>
<style>body{{font-family:Segoe UI,Inter,Arial,sans-serif;margin:0;background:#f8fafc;color:#111827}}
header{{background:linear-gradient(160deg,{BRAND['navy']},#0a1a2f);color:{BRAND['ink']};padding:28px 40px}}
header h1{{margin:0;font-size:24px}} header p{{margin:6px 0 0;color:{BRAND['muted']}}}
main{{padding:24px 40px;max-width:1200px}} .kpis{{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0}}
.kpi{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 20px;min-width:180px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi .v{{font-size:26px;font-weight:700;color:{BRAND['navy']}}} .kpi .l{{color:#6b7280;font-size:13px}}
table{{border-collapse:collapse;width:100%;background:#fff}} th{{background:{BRAND['navy']};color:#fff;text-align:left;padding:8px}} td{{padding:8px;border-bottom:1px solid #e5e7eb}}
figure{{margin:12px 0;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:10px;display:inline-block}} img{{max-width:100%}}
.badge{{display:inline-block;background:rgba(242,180,65,.15);border:1px solid rgba(242,180,65,.5);color:{BRAND['amber']};border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}}
</style></head><body><header><span class="badge">MV · Data Engineering</span><h1>{titulo}</h1><p>{html.escape(spec.get('descripcion') or '')}</p></header>
<main><h2>KPIs</h2><div class="kpis">{tarjetas}</div>
<h2>Calidad · puntaje {calidad.get('puntaje')} / 100 · {calidad.get('reglas')} reglas</h2>
<table><tr><th>regla</th><th>dimensión</th><th>detalle</th><th>tipo</th></tr>{filas_cal}</table>
{ml_html}<h2>Gráficos</h2>{imgs}</main></body></html>"""
    ruta.write_text(doc, encoding="utf-8")
    return ruta


def guardar_json(ruta: Path, obj) -> Path:
    ruta.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return ruta
