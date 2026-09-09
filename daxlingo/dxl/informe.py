# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · El informe del dataset, escrito solo.

Toma lo que el programa ya sabe —el catálogo, los hallazgos del analizador,
el perfilado de los datos crudos, el diagrama del modelo, las medidas y el
reporte— y lo escribe como un documento: auditoría del dataset, modelo
relacional, Power Query tabla por tabla, las medidas agrupadas por carpeta,
el tablero página por página, y qué conviene hacer ahora. Un archivo HTML
solo, que se abre en cualquier navegador, se manda por mail y se imprime a
PDF sin nada instalado.

Dos reglas que hacen que este informe sirva y no sea relleno:

**Lo importante va en color, y el color significa algo.** Rojo es «esto
está mal y hay que arreglarlo», ámbar «revisalo», verde «esto está bien y
también hay que decirlo» y azul es contexto. El color sale de la severidad
que ya calculó el analizador, no de cuánto quiero llamar la atención.

**Lo que no se sabe, no se escribe.** Si el modelo no trae los datos —un
.pbix del que solo se pudo leer el reporte— la sección de perfilado dice
que no hay datos para perfilar, en vez de inventar una distribución. Cada
número de este documento sale de algo que se leyó.
"""
from __future__ import annotations

import html
import re
from datetime import date

from . import analizador, kpis as _kpis, mapa, reporte as _reporte
from . import dataset, evidencia
from .catalogo import Catalogo, TIPOS_NUMERICOS, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

# La caja de color según lo que pasó. Sale de la severidad del analizador —
# el color no es decoración, es la conclusión.
_CAJA = {"alta": "dang", "media": "warn", "baja": "info"}

# Paleta por defecto: la misma del producto. Si viene una marca, manda esa.
_PALETA = {"primario": "#1e3a8a", "tinta": "#12203c", "acento": "#8bc34a",
           "sobre_primario": "#FFFFFF"}


_RE_HEX = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def _es_hex(valor) -> bool:
    """Un color de verdad, y nada más. Lo que se interpola en el CSS no
    puede venir sin revisar."""
    return isinstance(valor, str) and bool(_RE_HEX.match(valor.strip()))


def _esc(texto) -> str:
    return html.escape(str(texto if texto is not None else ""))


def _n(valor) -> str:
    """Un número con separador de miles a la española: 1.234.567."""
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return _esc(valor)


def _n1(valor) -> str:
    """Con un decimal. Para promedios chicos, redondear a entero borra el
    dato: «6,6 visitas por médico» contra «7,3» es toda la conclusión, y
    como enteros las dos son 6 y 7 sin que se vea la diferencia."""
    try:
        return f"{float(valor):,.1f}".replace(",", "·").replace(
            ".", ",").replace("·", ".")
    except (TypeError, ValueError):
        return _esc(valor)


# ==========================================================================
# La hoja de estilo — inline, porque el archivo tiene que viajar solo
# ==========================================================================
def _estilos(paleta: dict) -> str:
    return f"""
:root{{--navy:{paleta['tinta']};--navy2:{paleta['primario']};
--green:{paleta['acento']};--bg:#f4f6fa;--card:#fff;--line:#dfe4ee;
--txt:#1c2536;--mut:#5d6880;--amber:#d98c0c;--red:#c0392b;
--sobre:{paleta['sobre_primario']}}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:'Segoe UI',Inter,system-ui,sans-serif;
background:var(--bg);color:var(--txt);line-height:1.62;font-size:15.2px}}
header{{background:linear-gradient(135deg,var(--navy),var(--navy2));
color:var(--sobre);padding:32px 24px 28px}}
header .in{{max-width:1180px;margin:0 auto}}
header h1{{margin:0 0 6px;font-size:29px;letter-spacing:-.3px}}
header p{{margin:0;color:#c3cde0;font-size:14.2px}}
.hdrk{{display:flex;gap:20px;flex-wrap:wrap;margin-top:16px}}
.hdrk div{{background:rgba(255,255,255,.10);
border:1px solid rgba(255,255,255,.18);border-radius:10px;padding:9px 15px}}
.hdrk b{{display:block;font-size:11px;letter-spacing:1px;color:#a9bcdd;
text-transform:uppercase}}
.hdrk span{{font-size:16px;font-weight:700}}
nav.idx{{position:sticky;top:0;z-index:40;background:#fff;
border-bottom:1px solid var(--line);padding:9px 16px;display:flex;gap:6px;
flex-wrap:wrap;justify-content:center;box-shadow:0 2px 8px rgba(18,32,60,.05)}}
nav.idx a{{font-size:12.6px;color:var(--navy2);text-decoration:none;
padding:4px 10px;border-radius:7px;background:#eef3fc;font-weight:600}}
nav.idx a:hover{{background:var(--navy2);color:var(--sobre)}}
.wrap{{max-width:1180px;margin:0 auto;padding:26px 20px 90px}}
section{{background:var(--card);border:1px solid var(--line);
border-radius:14px;padding:24px 26px;margin-bottom:20px;scroll-margin-top:58px}}
h2{{margin:0 0 6px;font-size:21px;color:var(--navy);display:flex;
align-items:center;gap:11px}}
h2 .n{{background:var(--navy2);color:var(--sobre);width:31px;height:31px;
border-radius:9px;display:inline-flex;align-items:center;
justify-content:center;font-size:15px;flex:none}}
h3{{margin:26px 0 10px;font-size:16.6px;color:var(--navy2);
border-bottom:2px solid #eef3fc;padding-bottom:5px}}
h4{{margin:18px 0 7px;font-size:14.6px;color:var(--navy)}}
.lead{{color:var(--mut);font-size:14.6px;margin:0 0 8px}}
.tw{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:13.6px;margin:11px 0 16px}}
th{{background:var(--navy);color:#fff;text-align:left;padding:9px 11px;
font-weight:600;font-size:12.8px}}
td{{padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:nth-child(even) td{{background:#fafbfe}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
pre{{background:#0f1b31;color:#e3ecfa;padding:14px 16px;border-radius:10px;
overflow-x:auto;font-size:12.9px;line-height:1.58;margin:0 0 12px;
border-left:4px solid var(--green);white-space:pre}}
code{{background:#eef1f7;padding:1.5px 6px;border-radius:5px;
font-family:Consolas,monospace;font-size:12.8px;color:#0f2c5c}}
pre code{{background:none;color:inherit;padding:0}}
.box{{padding:13px 16px;border-radius:10px;margin:13px 0;font-size:14.3px;
border-left:4px solid}}
.box b{{display:block;margin-bottom:2px}}
.info{{background:#eef3fc;border-color:var(--navy2)}}
.ok{{background:#f2f8e9;border-color:var(--green)}}
.warn{{background:#fdf6e6;border-color:var(--amber)}}
.dang{{background:#fdecea;border-color:var(--red)}}
.pill{{display:inline-block;padding:2px 9px;border-radius:999px;
font-size:11.5px;font-weight:700;letter-spacing:.3px}}
.p-alta{{background:#fdecea;color:var(--red)}}
.p-media{{background:#fdf6e6;color:var(--amber)}}
.p-baja{{background:#eef3fc;color:var(--navy2)}}
.p-ok{{background:#f2f8e9;color:#4a7c14}}
.salud{{display:flex;align-items:center;gap:14px;margin:6px 0 14px}}
.salud .barra{{flex:1;height:12px;border-radius:999px;background:#e7ebf3;
overflow:hidden}}
.salud .barra i{{display:block;height:100%;border-radius:999px}}
.salud .num{{font-size:26px;font-weight:800;color:var(--navy)}}
.mini{{font-size:12.6px;color:var(--mut)}}
figure{{margin:12px 0;overflow-x:auto}}
footer{{max-width:1180px;margin:0 auto;padding:0 20px 40px;
color:var(--mut);font-size:12.6px}}
@media print{{
  nav.idx{{display:none}} body{{background:#fff}}
  section{{break-inside:avoid;box-shadow:none}}
}}
"""


# ==========================================================================
# Piezas
# ==========================================================================
def _caja(clase: str, titulo: str, cuerpo: str) -> str:
    return (f'<div class="box {clase}"><b>{_esc(titulo)}</b>'
            f'{cuerpo}</div>')


def _tabla(encabezados: list[str], filas: list[list], numericas=()) -> str:
    if not filas:
        return ""
    th = "".join(
        f'<th class="num">{_esc(h)}</th>' if i in numericas
        else f"<th>{_esc(h)}</th>" for i, h in enumerate(encabezados))
    cuerpo = []
    for f in filas:
        tds = "".join(
            f'<td class="num">{c}</td>' if i in numericas else f"<td>{c}</td>"
            for i, c in enumerate(f))
        cuerpo.append(f"<tr>{tds}</tr>")
    return (f'<div class="tw"><table><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(cuerpo)}</tbody></table></div>')


def _seccion(num: str, titulo: str, ancla: str, cuerpo: str) -> str:
    return (f'<section id="{ancla}"><h2><span class="n">{_esc(num)}</span>'
            f"{_esc(titulo)}</h2>{cuerpo}</section>")


# Cuántos objetos se nombran dentro de una caja. Un informe que dice «hay
# una medida con este problema» y no cuál obliga a volver a la app: la
# lista es la mitad útil del hallazgo. Con 40 medidas iguales, la lista
# completa tampoco sirve — se corta y se dice cuántas faltan.
_MAX_OBJETOS = 12


def _hallazgo(grupo: dict, idioma: str) -> str:
    """Una caja de hallazgo: la regla, qué pasa, EN QUÉ objetos, y el
    arreglo. El color sale de la severidad que calculó el analizador."""
    d = analizador.describir(grupo, idioma)
    objetos = grupo.get("objetos") or []
    lista = ", ".join(_esc(o) for o in objetos[:_MAX_OBJETOS])
    if len(objetos) > _MAX_OBJETOS:
        lista += " " + _esc(traducir("inf_y_mas", idioma).format(
            n=len(objetos) - _MAX_OBJETOS))
    cuerpo = (f'<span class="pill p-{grupo["severidad"]}">'
              f'{_esc(grupo["regla"])}</span> '
              f'<span class="mini">{_esc(analizador.area(grupo["regla"], idioma))}'
              f"</span><br>{_esc(d['detalle'])}<br>"
              + (f'<code>{lista}</code><br>' if lista else "")
              + f"<b style=\"font-weight:600\">{_esc(d['arreglo'])}</b>")
    return _caja(_CAJA.get(grupo["severidad"], "info"), d["titulo"], cuerpo)


def _color_salud(valor: int) -> str:
    if valor >= 85:
        return "#4a7c14"
    if valor >= 60:
        return "#d98c0c"
    return "#c0392b"


# ==========================================================================
# 1 · Resumen y salud
# ==========================================================================
def _resumen(cat: Catalogo, hallazgos: list[dict], idioma: str) -> str:
    if cat.parcial:
        # De un .pbix solo se puede leer el reporte: el modelo viaja en un
        # binario propietario. Sin medidas ni relaciones que revisar, casi
        # ninguna regla se dispara y la salud sale ALTÍSIMA — 95/100 al
        # lado de «0 tablas». Un archivo que no se pudo analizar no tiene
        # nota: decir que no se pudo es la única respuesta honesta.
        return _caja("warn", traducir("inf_parcial_t", idioma),
                     _esc(traducir("inf_parcial", idioma)))
    salud = analizador.puntaje(hallazgos)
    por_sev = {"alta": 0, "media": 0, "baja": 0}
    for h in hallazgos:
        por_sev[h["severidad"]] = por_sev.get(h["severidad"], 0) + 1

    partes = [
        f'<div class="salud"><span class="num" '
        f'style="color:{_color_salud(salud)}">{salud}</span>'
        f'<div class="barra"><i style="width:{salud}%;'
        f'background:{_color_salud(salud)}"></i></div>'
        f'<span class="mini">/ 100</span></div>']

    if not hallazgos:
        partes.append(_caja("ok", traducir("inf_sin_hallazgos_t", idioma),
                            traducir("inf_sin_hallazgos", idioma)))
    else:
        if por_sev["alta"]:
            partes.append(_caja(
                "dang", traducir("inf_criticos_t", idioma),
                traducir("inf_criticos", idioma).format(n=por_sev["alta"])))
        if por_sev["media"]:
            partes.append(_caja(
                "warn", traducir("inf_medios_t", idioma),
                traducir("inf_medios", idioma).format(n=por_sev["media"])))
        if por_sev["baja"] and not por_sev["alta"] and not por_sev["media"]:
            partes.append(_caja(
                "info", traducir("inf_bajos_t", idioma),
                traducir("inf_bajos", idioma).format(n=por_sev["baja"])))

    # Qué mide cada área, para que el número no sea un veredicto opaco.
    areas: dict[str, int] = {}
    for h in hallazgos:
        a = analizador.area(h["regla"], idioma)
        areas[a] = areas.get(a, 0) + 1
    if areas:
        partes.append(_tabla(
            [traducir("inf_col_area", idioma),
             traducir("inf_col_hallazgos", idioma)],
            [[_esc(a), _n(c)] for a, c in sorted(areas.items(),
                                                 key=lambda x: -x[1])],
            numericas={1}))
    return "".join(partes)


# ==========================================================================
# 2 · Auditoría del dataset
# ==========================================================================
def _clase_tabla(cat: Catalogo, t: dict, idioma: str) -> str:
    if t["es_calendario"]:
        return traducir("inf_calendario", idioma)
    muchos = {_norm(r["desde_tabla"]) for r in cat.relaciones}
    uno = {_norm(r["hacia_tabla"]) for r in cat.relaciones}
    n = _norm(t["nombre"])
    if n in muchos:
        return traducir("inf_hecho", idioma)
    if n in uno:
        return traducir("inf_dimension", idioma)
    if not t["columnas"] and t["medidas"]:
        return traducir("inf_tabla_medidas", idioma)
    return traducir("inf_suelta", idioma)


def _filas_de(meta: dict | None, nombre: str) -> int | None:
    for t in (meta or {}).get("tablas", []):
        if _norm(t["nombre"]) == _norm(nombre):
            return t.get("filas")
    return None


def _auditoria(cat: Catalogo, meta: dict | None, idioma: str,
               datos: dict | None = None) -> str:
    partes = [f'<p class="lead">{_esc(traducir("inf_audit_lead", idioma))}</p>']
    filas = []
    for t in cat.tablas:
        if t["interna"]:
            continue
        nf = _filas_de(meta, t["nombre"])
        filas.append([
            f'<b>{_esc(t["nombre"])}</b>',
            _esc(_clase_tabla(cat, t, idioma)),
            _n(len(t["columnas"])), _n(len(t["medidas"])),
            _n(nf) if nf is not None else "—",
        ])
    partes.append(_tabla(
        [traducir("inf_col_tabla", idioma), traducir("inf_col_papel", idioma),
         traducir("inf_col_columnas", idioma),
         traducir("inf_col_medidas", idioma),
         traducir("inf_col_filas", idioma)],
        filas, numericas={2, 3, 4}))

    # ---- Las trampas: lo que el analizador encontró, con su color ----
    partes.append(f"<h3>{_esc(traducir('inf_trampas', idioma))}</h3>")
    hallazgos = analizador.analizar(cat)
    if not hallazgos:
        partes.append(_caja("ok", traducir("inf_limpio_t", idioma),
                            traducir("inf_limpio", idioma)))
    else:
        for grupo in analizador.agrupar(hallazgos):
            partes.append(_hallazgo(grupo, idioma))

    # ---- Integridad referencial: lo primero que mira quien audita ----
    partes.append(f"<h3>{_esc(traducir('inf_integridad', idioma))}</h3>")
    partes.append(_integridad(cat, datos, idioma))

    # ---- Perfilado real, si hay datos ----
    partes.append(f"<h3>{_esc(traducir('inf_perfilado', idioma))}</h3>")
    perfil = _perfilado(meta, idioma) or _perfilado(
        _meta_de_empotrado(cat, datos or {}), idioma)
    partes.append(perfil or _caja(
        "info", traducir("inf_sin_datos_t", idioma),
        traducir("inf_sin_datos", idioma)))
    return "".join(partes)


def _integridad(cat: Catalogo, datos: dict, idioma: str) -> str:
    """Cuántas claves del lado muchos no existen del lado uno.

    Es lo primero que mira alguien que audita un tablero y lo último que
    aparece en los informes generados. Una relación con huérfanos no da
    error: manda esas filas a un miembro «en blanco» que nadie mira, y el
    total del informe queda por debajo del real sin que nada lo avise.
    Que esté limpia también hay que decirlo — es la mitad del valor de
    haberlo comprobado.
    """
    filas_ok = evidencia.integridad(cat, datos)
    if not filas_ok:
        return _caja("info", traducir("inf_int_sin_t", idioma),
                     traducir("inf_int_sin", idioma))
    filas, sucias = [], 0
    for r in filas_ok:
        if not r["limpia"]:
            sucias += 1
        marca = ("p-ok" if r["limpia"] else "p-alta")
        etiqueta = traducir("inf_int_limpia" if r["limpia"]
                            else "inf_int_revisar", idioma)
        filas.append([
            _esc(r["desde"]), _esc(r["hacia"]), _n(r["filas"]),
            _n(r["huerfanos"]), _n(r["vacios"]), _n(r["repetidas_uno"]),
            f'<span class="pill {marca}">{_esc(etiqueta)}</span>'])
    cabeza = _caja(
        "dang" if sucias else "ok",
        traducir("inf_int_mal_t" if sucias else "inf_int_bien_t",
                 idioma).format(n=sucias, total=len(filas_ok)),
        traducir("inf_int_mal" if sucias else "inf_int_bien", idioma))
    return cabeza + _tabla(
        [traducir("inf_int_muchos", idioma),
         traducir("inf_int_uno", idioma),
         traducir("inf_col_filas", idioma),
         traducir("inf_int_huerfanos", idioma),
         traducir("inf_int_vacios", idioma),
         traducir("inf_int_repetidas", idioma),
         traducir("inf_col_estado", idioma)], filas, numericas={2, 3, 4, 5})


def _meta_de_empotrado(cat: Catalogo, datos: dict) -> dict:
    """Un `dataset_meta` armado con las filas que viajan en el archivo.

    Un .pbit autocontenido SÍ lleva los datos: decirle al usuario «cargá
    el Excel de origen» cuando las filas están adentro del archivo que
    está mirando era pedirle algo que no hace falta.
    """
    tablas = []
    for nombre, (cols, filas) in (datos or {}).items():
        t = cat.tabla(nombre)
        if not t or t["interna"]:
            continue
        por_nombre = {_norm(c["nombre"]): c for c in t["columnas"]}
        tablas.append({
            "nombre": nombre, "datos": filas,
            "columnas": [{"nombre": c,
                          "tipo": (por_nombre.get(_norm(c)) or {}).get(
                              "tipo", "string")} for c in cols]})
    return {"tablas": tablas}


def _perfilado(meta: dict | None, idioma: str) -> str:
    """Distribuciones REALES de las columnas, contadas sobre las filas que
    se leyeron. Sin datos crudos no hay perfilado y se dice: inventar una
    distribución es peor que no tenerla."""
    tablas = (meta or {}).get("tablas") or []
    if not tablas:
        return ""
    partes = []
    for t in tablas:
        datos = t.get("datos")
        if not datos:
            continue
        filas = []
        for i, c in enumerate(t["columnas"]):
            valores = [f[i] for f in datos if i < len(f)]
            llenos = [v for v in valores if str(v).strip()]
            distintos = len({str(v).strip() for v in llenos})
            vacios = len(valores) - len(llenos)
            muestra = " · ".join(sorted({str(v)[:18] for v in llenos})[:3])
            filas.append([
                f'<b>{_esc(c["nombre"])}</b>', _esc(c["tipo"]),
                _n(distintos),
                (f'<span class="pill p-media">{_n(vacios)}</span>'
                 if vacios else _n(0)),
                f'<span class="mini">{_esc(muestra)}</span>'])
        if filas:
            partes.append(f'<h4>{_esc(t["nombre"])} '
                          f'<span class="mini">· {_n(len(datos))} '
                          f'{_esc(traducir("inf_filas_leidas", idioma))}'
                          f"</span></h4>")
            partes.append(_tabla(
                [traducir("inf_col_columna", idioma),
                 traducir("inf_col_tipo", idioma),
                 traducir("inf_col_distintos", idioma),
                 traducir("inf_col_vacios", idioma),
                 traducir("inf_col_muestra", idioma)],
                filas, numericas={2, 3}))
    return "".join(partes)


# ==========================================================================
# 3 · El modelo relacional
# ==========================================================================
def _modelo(cat: Catalogo, idioma: str) -> str:
    partes = [f'<p class="lead">{_esc(traducir("inf_modelo_lead", idioma))}</p>']
    # El diagrama va como FUENTE Graphviz, escapada. `mapa.construir`
    # devuelve DOT, no SVG: pegarlo crudo dentro de un <figure> no dibujaba
    # nada y, peor, metía en el documento markup que vino del archivo del
    # usuario. Como texto se copia y se pega en cualquier visor de Graphviz.
    try:
        dot = mapa.construir(cat)
    except Exception:      # noqa: BLE001 — el diagrama es un plus, no el eje
        dot = ""
    if dot:
        partes.append(f'<p class="mini">'
                      f'{_esc(traducir("inf_diagrama", idioma))}</p>')
        partes.append(f"<pre><code>{_esc(_acortar(dot))}</code></pre>")
    filas = []
    for r in cat.relaciones:
        activa = r.get("activa", True)
        direccion = r.get("direccion", "")
        filas.append([
            f'{_esc(r["desde_tabla"])}[{_esc(r["desde_col"])}]',
            f'{_esc(r["hacia_tabla"])}[{_esc(r["hacia_col"])}]',
            "*→1",
            (f'<span class="pill p-ok">{_esc(traducir("inf_activa", idioma))}'
             f"</span>" if activa else
             f'<span class="pill p-media">'
             f'{_esc(traducir("inf_inactiva", idioma))}</span>'),
            _esc(direccion or "→"),
        ])
    if filas:
        partes.append(_tabla(
            [traducir("inf_col_muchos", idioma),
             traducir("inf_col_uno", idioma),
             traducir("inf_col_card", idioma),
             traducir("inf_col_estado", idioma),
             traducir("inf_col_filtro", idioma)], filas))
    elif len([t for t in cat.tablas if not t["interna"]]) > 1:
        partes.append(_caja("dang", traducir("inf_sin_rel_t", idioma),
                            traducir("inf_sin_rel", idioma)))
    else:
        # Una sola tabla no tiene con qué relacionarse: no es un defecto.
        partes.append(_caja("info", traducir("inf_una_tabla_t", idioma),
                            traducir("inf_una_tabla", idioma)))
    partes.append(_forma_del_modelo(cat, idioma))
    partes.append(_decisiones(cat, idioma))
    return "".join(partes)


def _forma_del_modelo(cat: Catalogo, idioma: str) -> str:
    """Estrella o copo de nieve, con el diagnóstico de ESTE modelo.

    No es una discusión académica: la forma decide cuántos saltos tiene
    que dar un filtro para llegar al hecho, y cada salto es más lento y
    una oportunidad más de que el filtro no llegue. Se dice cuál de las
    dos es este modelo y por qué, con las tablas contadas.
    """
    hechos, dims = set(), set()
    for r in cat.relaciones:
        hechos.add(_norm(r["desde_tabla"]))
        dims.add(_norm(r["hacia_tabla"]))
    # Una dimensión que además cuelga de otra dimensión es el eslabón que
    # convierte la estrella en copo de nieve.
    encadenadas = sorted(
        {r["desde_tabla"] for r in cat.relaciones
         if _norm(r["desde_tabla"]) in dims})
    partes = [f'<h3>{_esc(traducir("inf_forma_t", idioma))}</h3>',
              f'<p>{_esc(traducir("inf_forma_lead", idioma))}</p>',
              _tabla([traducir("inf_forma_col_que", idioma),
                      traducir("inf_forma_col_estrella", idioma),
                      traducir("inf_forma_col_copo", idioma)],
                     [[_esc(traducir(f"inf_forma_f{i}_{c}", idioma))
                       for c in ("que", "estrella", "copo")]
                      for i in range(1, 5)])]
    if encadenadas:
        partes.append(_caja(
            "aviso", traducir("inf_forma_copo_t", idioma),
            traducir("inf_forma_copo", idioma).format(
                tablas=", ".join(f"«{_esc(t)}»" for t in encadenadas))))
    else:
        partes.append(_caja(
            "ok", traducir("inf_forma_estrella_t", idioma),
            traducir("inf_forma_estrella", idioma).format(
                hechos=len(hechos - dims), dims=len(dims))))
    return "".join(partes)


def _decisiones(cat: Catalogo, idioma: str) -> str:
    """Por qué el modelo está como está, objeto por objeto.

    Listar las columnas ocultas y las relaciones inactivas sin explicarlas
    obliga al que lee a adivinar si son decisiones o descuidos — y en la
    duda las «arregla», que es lo peor que puede pasar.
    """
    lista = evidencia.decisiones(cat)
    if not lista:
        return ""
    filas = [[f'<b>{_esc(d["objeto"])}</b>', _esc(d["que"]),
              _esc(d["porque"]),
              f'<span class="mini">{_esc(d["si_se_deshace"])}</span>']
             for d in lista[:30]]
    aviso = ""
    if len(lista) > 30:
        aviso = (f'<p class="mini">'
                 f'{_esc(traducir("inf_dec_mas", idioma).format(n=len(lista) - 30))}'
                 f"</p>")
    return (f'<h3>{_esc(traducir("inf_dec_t", idioma))}</h3>'
            f'<p class="lead">{_esc(traducir("inf_dec_lead", idioma))}</p>'
            + _tabla([traducir("inf_dec_objeto", idioma),
                      traducir("inf_dec_que", idioma),
                      traducir("inf_dec_porque", idioma),
                      traducir("inf_dec_si", idioma)], filas) + aviso)


# ==========================================================================
# Cifras de control y concentración
# ==========================================================================
def _control(cat: Catalogo, datos: dict, idioma: str) -> str:
    """El valor real de cada medida que se puede reproducir sin motor DAX.

    Es la tabla contra la que se valida un tablero: si una tarjeta sin
    filtros no da este número, sobra o falta un filtro. Las medidas con
    CALCULATE, inteligencia de tiempo o razones no están, y se dice: «no
    la pude calcular» es información, un valor aproximado es una mentira
    con formato de dato.
    """
    partes = [f'<p class="lead">{_esc(traducir("inf_ctl_lead", idioma))}</p>']
    cifras = evidencia.cifras_control(cat, datos)
    if not cifras:
        partes.append(_caja("info", traducir("inf_ctl_sin_t", idioma),
                            traducir("inf_ctl_sin", idioma)))
        return "".join(partes)
    filas = [[f'<b>{_esc(c["medida"])}</b>',
              _esc(traducir(f'inf_ctl_{c["clase"]}', idioma)),
              _n(round(c["valor"], 2))] for c in cifras]
    partes.append(_tabla(
        [traducir("inf_col_medidas", idioma),
         traducir("inf_ctl_como", idioma),
         traducir("inf_ctl_valor", idioma)], filas, numericas={2}))
    total = len(cat.medidas())
    partes.append(_caja(
        "info", traducir("inf_ctl_alcance_t", idioma),
        traducir("inf_ctl_alcance", idioma).format(
            n=len(cifras), total=total, resto=total - len(cifras))))
    # Dos medidas que dan el MISMO número no son un detalle de estilo: es
    # el camino más corto a que dos páginas del informe se contradigan.
    for g in evidencia.medidas_gemelas(cifras):
        partes.append(_caja(
            "aviso", traducir("inf_ctl_gemelas_t", idioma),
            traducir("inf_ctl_gemelas", idioma).format(
                medidas=", ".join(f"«{_esc(x)}»" for x in g["medidas"]),
                valor=_n(round(g["valor"], 2)))))
    conc = _concentracion(cat, datos, idioma)
    if conc:
        partes.append(conc)
    cru = _cruce(cat, datos, idioma)
    if cru:
        partes.append(cru)
    return "".join(partes)


def _mejor_cruce(cat: Catalogo, datos: dict):
    """La dimensión que mejor responde «¿el esfuerzo rinde?».

    Gana la que tiene una desalineación real —el grupo que menos produce
    recibe tanto o más esfuerzo que el que más— y, entre ésas, la de
    mayor brecha. Si ninguna la tiene, se muestra igual el cruce de la
    que más varía: que el esfuerzo esté bien puesto también es una
    conclusión.
    """
    mejor, mejor_veces, respaldo = None, 0.0, None
    for tabla, c in cat.columnas(solo_visibles=True):
        if not _es_dimension_informe(tabla, c, cat):
            continue
        res = evidencia.cruce(cat, datos, (tabla, c["nombre"]))
        if not res:
            continue
        respaldo = respaldo or res
        d = evidencia.desalineacion(res)
        if d and d["veces"] > mejor_veces:
            mejor, mejor_veces = (res, d), d["veces"]
    return mejor or ((respaldo, None) if respaldo else None)


def _es_dimension_informe(tabla: str, c: dict, cat: Catalogo) -> bool:
    from .tablero import _es_dimension
    return _es_dimension(tabla, c, cat)


def _cruce(cat: Catalogo, datos: dict, idioma: str) -> str:
    """Todo lo que le pasa a un mismo miembro, en una sola tabla.

    Un informe puede tener una página de visitas, otra de recetas y otra
    de digital y no responder la única pregunta que decide un
    presupuesto: si el esfuerzo está puesto donde rinde. Los totales por
    grupo no alcanzan —el grupo más grande siempre parece el mejor—, así
    que todo va dividido por la cantidad de miembros.
    """
    elegido = _mejor_cruce(cat, datos)
    if not elegido:
        return ""
    res, desal = elegido
    encabezados = [_esc(res["dimension"]),
                   traducir("inf_cru_miembros", idioma)]
    por_cada = traducir("inf_cru_cada", idioma)
    encabezados += [f'{c["hechos"]} {por_cada}' for c in res["columnas"]]
    filas = []
    for g in res["grupos"]:
        n = res["miembros"].get(g, 0) or 1
        fila = [_esc(g), _n(n)]
        fila += [_n1(c["por_grupo"].get(g, 0.0) / n)
                 for c in res["columnas"]]
        filas.append(fila)
    numericas = set(range(1, len(encabezados)))
    caja = ""
    if desal:
        detalle = " · ".join(
            traducir("inf_cru_esfuerzo", idioma).format(
                hechos=e["hechos"], peor=f'{e["en_el_peor"]:,.1f}',
                mejor=f'{e["en_el_mejor"]:,.1f}')
            for e in desal["esfuerzos"])
        caja = _caja("dang", traducir("inf_cru_mal_t", idioma),
                     _esc(traducir("inf_cru_mal", idioma).format(
                         mejor=desal["mejor"], peor=desal["peor"],
                         veces=f'{desal["veces"]:.1f}',
                         resultado=desal["resultado"],
                         rinde_mejor=f'{desal["rinde_mejor"]:,.0f}',
                         rinde_peor=f'{desal["rinde_peor"]:,.0f}')
                         + " " + detalle))
    else:
        caja = _caja("ok", traducir("inf_cru_bien_t", idioma),
                     _esc(traducir("inf_cru_bien", idioma)))
    return (f'<h3>{_esc(traducir("inf_cru_t", idioma))}</h3>'
            f'<p class="lead">{_esc(traducir("inf_cru_lead", idioma))}</p>'
            + caja + _tabla(encabezados, filas, numericas=numericas))


# Debajo de esto, un «top 10» es la lista entera y el porcentaje da 100 %.
MINIMO_PARETO = 8


def _columnas_de_negocio(cat: Catalogo) -> set[tuple[str, str]]:
    """Las columnas que alguna medida SUMA: el valor del negocio.

    Es el criterio más honesto para elegir qué medir en el Pareto. Sin
    él, la heurística agarraba la columna numérica de mayor suma —que en
    un calendario es el AÑO— y salía «concentración del año por mes»,
    un dato cierto que no significa nada.
    """
    salida = set()
    for m in cat.medidas():
        for clase, patron in evidencia._PATRONES:
            mm = patron.match((m.get("expresion") or "").strip())
            if mm and clase in ("suma", "promedio"):
                salida.add((_norm(mm.group(1).strip()),
                            _norm(mm.group(2).strip())))
            if mm:
                break
    return salida


def _mejor_corte(cat: Catalogo, datos: dict) -> tuple | None:
    """La dimensión y la columna de valor con las que armar el Pareto.

    Se prefiere, en este orden: una columna que alguna medida suma, un
    corte con suficientes miembros para que el porcentaje signifique
    algo, y el mayor volumen. La dimensión puede estar en otra tabla: se
    resuelve con un salto de relación, que es lo que hace que el corte
    útil —ventas por producto— gane sobre el que estaba a mano.
    """
    negocio = _columnas_de_negocio(cat)
    cal = cat.tabla_fechas()
    nombre_cal = _norm(cal["nombre"]) if cal else ""
    mejor = None
    for tabla, (_cols, _filas) in (datos or {}).items():
        t = cat.tabla(tabla)
        if not t or t["interna"] or _norm(tabla) == nombre_cal:
            continue
        numericas = [c["nombre"] for c in t["columnas"]
                     if c["tipo"] in TIPOS_NUMERICOS and not c.get("oculta")]
        # Candidatas a eje: las de la propia tabla y las de las
        # dimensiones a un salto.
        ejes = [(tabla, c["nombre"]) for c in t["columnas"]
                if c["tipo"] == "string" and not c.get("oculta")]
        for r in cat.relaciones:
            if _norm(r["desde_tabla"]) != _norm(tabla) \
                    or not r.get("activa", True):
                continue
            td = cat.tabla(r["hacia_tabla"])
            if not td or _norm(td["nombre"]) == nombre_cal:
                continue
            ejes += [(td["nombre"], c["nombre"]) for c in td["columnas"]
                     if c["tipo"] == "string" and not c.get("oculta")]
        ejes = [(tb, cn) for tb, cn in ejes
                if not re.search(r"(^id$|id$|codigo|code|nombre|name)", cn,
                                 re.IGNORECASE)]
        for num in numericas:
            if re.search(r"(orden|order|anio|año|year|numero|number)", num,
                         re.IGNORECASE):
                continue
            suma = sum(evidencia._numeros(
                evidencia._columna(datos, tabla, num)))
            if suma <= 0:
                continue
            es_negocio = (_norm(tabla), _norm(num)) in negocio
            for tb, cn in ejes:
                miembros = len({str(v) for v in
                                (evidencia._columna(datos, tb, cn) or [])})
                # Con cuatro miembros el «top 10» son los cuatro y da
                # 100 %: cierto y vacío. Se prefiere el corte con
                # suficientes miembros para que la concentración
                # signifique algo.
                puntaje = (1 if es_negocio else 0,
                           1 if miembros >= MINIMO_PARETO else 0, suma)
                if mejor is None or puntaje > mejor[0]:
                    mejor = (puntaje, (tb, cn), (tabla, num))
    return (mejor[1], mejor[2]) if mejor else None


def _concentracion(cat: Catalogo, datos: dict, idioma: str) -> str:
    corte = _mejor_corte(cat, datos)
    if not corte:
        return ""
    res = evidencia.concentracion(cat, datos, corte[0], corte[1])
    if not res or res["miembros"] < 2:
        return ""
    filas = [[_esc(t["clave"]), _n(round(t["valor"], 2)),
              f'{t["parte"] * 100:.1f} %'] for t in res["top"]]
    return (f'<h3>{_esc(traducir("inf_conc_t", idioma))}</h3>'
            + _caja("info", traducir("inf_conc_titulo", idioma),
                    traducir("inf_conc", idioma).format(
                        n=len(res["top"]), parte=f'{res["parte_top"] * 100:.1f}',
                        miembros=res["miembros"], dimension=res["dimension"],
                        valor=res["valor"]))
            + _tabla([_esc(res["dimension"]), _esc(res["valor"]),
                      traducir("inf_conc_parte", idioma)],
                     filas, numericas={1, 2}))


# ==========================================================================
# 4 · Power Query
# ==========================================================================
def _powerquery(modelo: dict, idioma: str) -> str:
    partes = [f'<p class="lead">'
              f'{_esc(traducir("inf_pq_lead", idioma))}</p>']
    hubo = False
    for t in modelo.get("model", {}).get("tables", []):
        if t.get("name", "").startswith(("LocalDateTable_",
                                         "DateTableTemplate_")):
            continue
        for p in t.get("partitions", []):
            fuente = p.get("source", {})
            expr = fuente.get("expression")
            if not expr:
                continue
            texto = "\n".join(expr) if isinstance(expr, list) else str(expr)
            tipo = fuente.get("type", "?")
            hubo = True
            partes.append(f'<h4>{_esc(t["name"])} '
                          f'<span class="mini">· {_esc(tipo)}</span></h4>')
            # Una consulta con los datos adentro puede tener 340.000
            # caracteres de base64: pegarla entera vuelve el informe
            # inusable y no aporta nada.
            partes.append(f"<pre><code>{_esc(_acortar(texto))}</code></pre>")
    if not hubo:
        partes.append(_caja("info", traducir("inf_sin_pq_t", idioma),
                            traducir("inf_sin_pq", idioma)))
    return "".join(partes)


_LARGO_MAXIMO = 2600


def _acortar(texto: str) -> str:
    """Recorta el chorizo de base64 de una consulta con datos adentro, sin
    tocar el resto de los pasos."""
    texto = re.sub(r'"[A-Za-z0-9+/=]{200,}"', '"…"', texto)
    if len(texto) <= _LARGO_MAXIMO:
        return texto
    return texto[:_LARGO_MAXIMO] + "\n…"


# ==========================================================================
# 5 · Las medidas
# ==========================================================================
def _medidas(cat: Catalogo, idioma: str) -> str:
    medidas = cat.medidas()
    if not medidas:
        return _caja("warn", traducir("inf_sin_medidas_t", idioma),
                     traducir("inf_sin_medidas", idioma))
    partes = [f'<p class="lead">'
              f'{traducir("inf_medidas_lead", idioma).format(n=len(medidas))}'
              f"</p>"]
    carpetas: dict[str, list[dict]] = {}
    for m in medidas:
        carpetas.setdefault(m.get("carpeta") or
                            traducir("inf_sin_carpeta", idioma), []).append(m)
    for carpeta in sorted(carpetas):
        partes.append(f"<h3>{_esc(carpeta)}</h3>")
        filas = []
        for m in sorted(carpetas[carpeta], key=lambda x: _norm(x["nombre"])):
            filas.append([
                f'<b>{_esc(m["nombre"])}</b>'
                + (f'<br><span class="mini">{_esc(m["descripcion"])}</span>'
                   if m.get("descripcion") else ""),
                f'<code>{_esc(m.get("formato") or "—")}</code>',
                f'<pre style="margin:0"><code>'
                f'{_esc(_acortar(m.get("expresion", "")))}</code></pre>',
            ])
        partes.append(_tabla(
            [traducir("inf_col_medida", idioma),
             traducir("inf_col_formato", idioma), "DAX"], filas))
    partes.append(_modificadores(cat, idioma))
    return "".join(partes)


# Los cuatro modificadores de contexto de filtro, en el orden en que hay
# que elegirlos: primero qué total querés, después cómo lo pedís.
_MODIFICADORES = ("all", "allselected", "allexcept", "keepfilters")


def _modificadores(cat: Catalogo, idioma: str) -> str:
    """Qué hace cada modificador de filtro y cuándo se usa cada uno.

    Es la pregunta que más se repite al leer un DAX ajeno —«¿por qué acá
    dice ALL y allá ALLSELECTED?»— y la que más errores silenciosos
    genera: los cuatro devuelven un número creíble y sólo uno responde la
    pregunta que se hizo. Cada fila lleva su ejemplo, y se marca cuáles
    usa ESTE modelo para que la explicación no quede en abstracto.
    """
    usados = set()
    for m in cat.medidas():
        expr = (m.get("expresion") or "").upper()
        for clave in _MODIFICADORES:
            # ALLSELECTED y ALLEXCEPT contienen «ALL»: se busca la palabra
            # con su paréntesis para no contar una dentro de la otra.
            if f"{clave.upper()} (" in expr or f"{clave.upper()}(" in expr:
                usados.add(clave)
    filas = []
    for clave in _MODIFICADORES:
        marca = (f'<span class="pill p-ok">'
                 f'{_esc(traducir("inf_mod_usado", idioma))}</span>'
                 if clave in usados else "")
        filas.append([
            f'<code>{_esc(traducir(f"inf_mod_{clave}_fn", idioma))}</code>'
            f" {marca}",
            _esc(traducir(f"inf_mod_{clave}_cuando", idioma)),
            f'<pre style="margin:0"><code>'
            f'{_esc(traducir(f"inf_mod_{clave}_ej", idioma))}</code></pre>',
            _esc(traducir(f"inf_mod_{clave}_da", idioma)),
        ])
    return "".join([
        f'<h3>{_esc(traducir("inf_mod_t", idioma))}</h3>',
        f'<p>{_esc(traducir("inf_mod_lead", idioma))}</p>',
        _tabla([traducir("inf_mod_col_fn", idioma),
                traducir("inf_mod_col_cuando", idioma),
                traducir("inf_mod_col_ej", idioma),
                traducir("inf_mod_col_da", idioma)], filas),
        _caja("info", traducir("inf_mod_regla_t", idioma),
              traducir("inf_mod_regla", idioma)),
    ])


# ==========================================================================
# 6 · El tablero
# ==========================================================================
def _tablero(layout: dict | None, idioma: str) -> str:
    if not layout:
        return _caja("info", traducir("inf_sin_reporte_t", idioma),
                     traducir("inf_sin_reporte", idioma))
    partes = []
    for s in layout.get("sections", []):
        visuales: dict[str, int] = {}
        for vc in s.get("visualContainers", []):
            sv = _reporte._json(vc.get("config", "{}")) or {}
            tipo = ((sv.get("singleVisual") or {}).get("visualType")
                    or (((sv.get("singleVisualGroup") or {}).get("displayName"))
                        or "?"))
            visuales[tipo] = visuales.get(tipo, 0) + 1
        detalle = " · ".join(f"{n}× {t}" for t, n in
                             sorted(visuales.items(), key=lambda x: -x[1]))
        partes.append(f'<h4>{_esc(s.get("displayName", s.get("name", "?")))}'
                      f'</h4><p class="mini">{_esc(detalle or "—")}</p>')
    # Los hallazgos del REPORTE (RP*) los describe `analizador.describir`,
    # igual que en pantalla: `reporte` no tiene `describir`, y el `hasattr`
    # que lo consultaba convertía el bloque entero en una rama muerta —
    # se corría el análisis y se descartaba el resultado.
    for grupo in analizador.agrupar(_reporte.analizar(layout)):
        partes.append(_hallazgo(grupo, idioma))
    return "".join(partes)


# ==========================================================================
# 7 · Qué conviene hacer ahora
# ==========================================================================
def _conclusiones(cargado: dict, cat: Catalogo, datos: dict,
                  hallazgos: list[dict], idioma: str) -> str:
    """Lo que los números dicen, en el idioma de quien decide.

    El informe ya traía todo lo necesario para escribir esto y no lo
    escribía: dejaba las tablas y que cada uno sacara su conclusión. Cada
    línea de acá sale de un número MEDIDO más arriba en el documento —si
    el número no está, la línea no se escribe.
    """
    from . import analitica

    lineas = []
    exp = analitica.explicar(cargado, idioma)
    if exp and not exp.get("sin_propia"):
        pp = exp["delta_pp"]
        lineas.append((
            "dang" if pp < -0.05 else ("ok" if pp > 0.05 else "info"),
            traducir("inf_con_share", idioma).format(
                propia=exp["propia"], propio=exp["crec_propio"] * 100,
                mercado=exp["crec_mercado"] * 100, pp=pp)))
    corte = _mejor_corte(cat, datos)
    conc = evidencia.concentracion(cat, datos, *corte) if corte else None
    if conc and conc["miembros"] >= MINIMO_PARETO:
        lineas.append(("info", traducir("inf_con_conc", idioma).format(
            n=len(conc["top"]), parte=f'{conc["parte_top"] * 100:.1f}',
            miembros=conc["miembros"], dimension=conc["dimension"])))
    elegido = _mejor_cruce(cat, datos)
    desal = evidencia.desalineacion(elegido[0]) if elegido else None
    if desal:
        lineas.append(("dang", traducir("inf_con_cruce", idioma).format(
            mejor=desal["mejor"], peor=desal["peor"],
            veces=f'{desal["veces"]:.1f}')))
    integ = evidencia.integridad(cat, datos)
    if integ:
        sucias = [r for r in integ if not r["limpia"]]
        lineas.append((
            "dang" if sucias else "ok",
            traducir("inf_con_int_mal" if sucias else "inf_con_int_bien",
                     idioma).format(n=len(sucias), total=len(integ))))
    altas = [h for h in hallazgos if h["severidad"] == "alta"]
    if altas:
        lineas.append(("dang", traducir("inf_con_altas", idioma).format(
            n=len(altas))))
    if not lineas:
        return ""
    return (f'<h3>{_esc(traducir("inf_con_t", idioma))}</h3>'
            + "".join(_caja(c, traducir("inf_con_cada", idioma).format(i=i),
                            _esc(txt))
                      for i, (c, txt) in enumerate(lineas, 1)))


def _recomendaciones(cat: Catalogo, hallazgos: list[dict],
                     idioma: str, cargado: dict | None = None,
                     datos: dict | None = None) -> str:
    partes = [_conclusiones(cargado or {}, cat, datos or {}, hallazgos,
                            idioma) if cargado is not None else "",
              f'<p class="lead">'
              f'{_esc(traducir("inf_reco_lead", idioma))}</p>']
    orden = {"alta": 0, "media": 1, "baja": 2}
    grupos = sorted(analizador.agrupar(hallazgos),
                    key=lambda h: (orden.get(h["severidad"], 3), h["regla"]))
    filas = []
    for i, g in enumerate(grupos[:12], 1):
        d = analizador.describir(g, idioma)
        filas.append([
            _n(i),
            f'<span class="pill p-{g["severidad"]}">{_esc(g["regla"])}</span>',
            _esc(analizador.area(g["regla"], idioma)),
            f'<b>{_esc(d["titulo"])}</b><br>'
            f'<span class="mini">{_esc(d["arreglo"])}</span>',
            (f'<span class="pill p-ok">'
             f'{_esc(traducir("inf_auto", idioma))}</span>'
             if g.get("auto") else "—"),
        ])
    if filas:
        partes.append(_tabla(
            ["#", traducir("inf_col_regla", idioma),
             traducir("inf_col_area", idioma),
             traducir("inf_col_que", idioma),
             traducir("inf_col_solo", idioma)], filas, numericas={0}))
    # Los KPIs que el modelo pide y todavía no tiene.
    faltantes = _kpis.sugerir(cat, idioma)
    if faltantes:
        partes.append(_caja(
            "info", traducir("inf_kpis_t", idioma),
            traducir("inf_kpis", idioma).format(
                n=len(faltantes),
                lista=", ".join(_esc(k["nombre"]) for k in faltantes[:8]))))
    if not filas and not faltantes:
        partes.append(_caja("ok", traducir("inf_nada_que_hacer_t", idioma),
                            traducir("inf_nada_que_hacer", idioma)))
    return "".join(partes)


# ==========================================================================
# 8 · Por qué se movió el share
# ==========================================================================
def _barras(miembros: list[dict], idioma: str) -> str:
    """El gráfico de contribuciones: cuánto aporta cada segmento al total.

    Es un SVG escrito a mano, sin ninguna librería: el informe tiene que
    abrir sin internet. Cada barra sale del mismo número que está en la
    tabla de abajo — el dibujo no es una versión libre de los datos.
    """
    if not miembros:
        return ""
    valores = [m["total"] * 100 for m in miembros]
    tope = max(abs(v) for v in valores) or 1.0
    alto_fila, ancho, medio = 26, 720, 300
    alto = alto_fila * len(miembros) + 16
    filas = []
    for i, m in enumerate(miembros):
        v = m["total"] * 100
        y = 8 + i * alto_fila
        largo = abs(v) / tope * (ancho - medio - 90)
        x = medio if v >= 0 else medio - largo
        color = "#4a7c14" if v >= 0 else "#c0392b"
        etiqueta = _esc(str(m["miembro"])[:26])
        filas.append(
            f'<text x="{medio - 12}" y="{y + 14}" text-anchor="end" '
            f'font-size="12" fill="#1c2536">{etiqueta}</text>'
            f'<rect x="{x:.1f}" y="{y + 4}" width="{largo:.1f}" height="15" '
            f'rx="3" fill="{color}"/>'
            f'<text x="{(x + largo + 6) if v >= 0 else (x - 6):.1f}" '
            f'y="{y + 16}" font-size="11.5" font-weight="700" '
            f'text-anchor="{"start" if v >= 0 else "end"}" fill="{color}">'
            f'{v:+.2f}</text>')
    return (f'<figure><svg viewBox="0 0 {ancho} {alto}" width="100%" '
            f'height="{alto}" role="img">'
            f'<line x1="{medio}" y1="0" x2="{medio}" y2="{alto}" '
            f'stroke="#dfe4ee" stroke-width="1"/>'
            f'{"".join(filas)}</svg></figure>')


def _porque(cargado: dict, idioma: str) -> str:
    from . import analitica
    exp = analitica.explicar(cargado, idioma)
    if exp is None:
        return _caja("info", traducir("inf_pq_sin_datos_t", idioma),
                     _esc(traducir("inf_pq_sin_datos", idioma)))
    if exp.get("sin_propia"):
        return _caja("warn", traducir("inf_pq_sin_propia_t", idioma),
                     _esc(traducir("inf_pq_sin_propia", idioma).format(
                         columna=exp["columna"],
                         n=len(exp["corporaciones"]),
                         lista=", ".join(exp["corporaciones"][:6]))))

    partes = [f'<p class="lead">{_esc(traducir("inf_pq_lead2", idioma))}</p>']
    pp = exp["delta_pp"]
    partes.append(_caja(
        "dang" if pp < -0.05 else ("ok" if pp > 0.05 else "info"),
        traducir("inf_pq_titular", idioma).format(
            propia=exp["propia"], propio=exp["crec_propio"] * 100,
            mercado=exp["crec_mercado"] * 100, pp=pp),
        _esc(traducir("inf_pq_periodo", idioma).format(
            previo=exp["previo"], actual=exp["actual"],
            meses=exp["meses"]))))

    principal = exp["dimensiones"][0] if exp["dimensiones"] else None
    if principal:
        des = principal["desempeno"] * 100
        mez = principal["mezcla"] * 100
        brecha = principal["brecha"] * 100
        partes.append(_tabla(
            ["", traducir("inf_pq_col_aporte", idioma), ""],
            [[f'<b>{_esc(traducir("inf_pq_desempeno", idioma))}</b>',
              f"{des:+.2f} pp",
              f'<span class="mini">'
              f'{_esc(traducir("inf_pq_explica_desempeno", idioma))}</span>'],
             [f'<b>{_esc(traducir("inf_pq_mezcla", idioma))}</b>',
              f"{mez:+.2f} pp",
              f'<span class="mini">'
              f'{_esc(traducir("inf_pq_explica_mezcla", idioma))}</span>']],
            numericas={1}))
        # El veredicto: cuál de las dos mitades manda. Es LA conclusión.
        if abs(mez) > abs(des):
            partes.append(_caja(
                "warn", traducir("inf_pq_veredicto_mezcla", idioma),
                _esc(traducir("inf_pq_veredicto_mezcla_txt", idioma).format(
                    brecha=brecha, mezcla=mez, desempeno=des))))
        else:
            partes.append(_caja(
                "warn", traducir("inf_pq_veredicto_desempeno", idioma),
                _esc(traducir("inf_pq_veredicto_desempeno_txt",
                              idioma).format(
                    brecha=brecha, desempeno=des, mezcla=mez))))
        partes.append(f'<p class="mini">'
                      f'{_esc(traducir("inf_pq_identidad", idioma).format(suma=des + mez, real=brecha, residuo=principal["residuo"] * 100))}</p>')

    for d in exp["dimensiones"][:2]:
        partes.append(f"<h3>{_esc(d['dimension'])}</h3>")
        partes.append(f'<p class="lead">'
                      f'{_esc(traducir("inf_pq_grafico", idioma).format(dim=d["dimension"], pp=exp["delta_pp"]))}</p>')
        if not d["compite"]:
            partes.append(_caja("info", traducir("inf_pq_no_compite", idioma),
                                ""))
        from . import analitica as _an
        vistos = d["miembros"][:_an.MAX_MIEMBROS]
        partes.append(_barras(vistos, idioma))
        partes.append(_tabla(
            [traducir("inf_pq_col_miembro", idioma),
             traducir("inf_pq_col_aporte", idioma),
             traducir("inf_pq_desempeno", idioma),
             traducir("inf_pq_mezcla", idioma),
             traducir("inf_pq_col_peso", idioma),
             traducir("inf_pq_col_crec", idioma),
             traducir("inf_pq_col_crec_mkt", idioma)],
            [[f'<b>{_esc(m["miembro"])}</b>',
              f'{m["total"] * 100:+.2f}', f'{m["desempeno"] * 100:+.2f}',
              f'{m["mezcla"] * 100:+.2f}', f'{m["peso"] * 100:.1f} %',
              f'{m["crec_propio"] * 100:+.1f} %',
              f'{m["crec_mercado"] * 100:+.1f} %'] for m in vistos],
            numericas={1, 2, 3, 4, 5, 6}))

    pr = exp.get("precio")
    if pr:
        partes.append(f"<h3>{_esc(traducir('inf_pq_precio_t', idioma))}</h3>")
        partes.append(_caja(
            "warn" if pr["var_precio"] < -0.005 else "info",
            traducir("inf_pq_precio_t", idioma),
            _esc(traducir("inf_pq_precio", idioma).format(
                unidades=pr["var_unidades"] * 100,
                valor=exp["crec_propio"] * 100,
                p0=pr["precio_previo"], p1=pr["precio_actual"],
                var=pr["var_precio"] * 100,
                vol=pr["efecto_volumen"], pre=pr["efecto_precio"],
                delta=pr["delta_valor"]))))

    ops = analitica.oportunidades(exp, idioma)
    if ops:
        partes.append(
            f"<h3>{_esc(traducir('inf_pq_oportunidades', idioma))}</h3>")
        for o in ops[:6]:
            clase = {"precio": "warn", "desempeno": "dang",
                     "mezcla": "warn", "fuerte": "ok"}.get(o["tipo"], "info")
            partes.append(_caja(clase, o["titulo"], _esc(o["texto"])))
    return "".join(partes)


# ==========================================================================
# El documento
# ==========================================================================
def generar(cargado: dict, idioma: str = IDIOMA_DEFECTO,
            marca: dict | None = None, titulo: str = "") -> str:
    """El informe completo, como un HTML autocontenido.

    `cargado` es lo que devuelve `modelo.cargar` / `dataset.cargar`: se usan
    `modelo`, `layout` y `dataset_meta` (este último, cuando está, permite
    perfilar los datos de verdad en vez de describir solo la estructura).
    """
    modelo = cargado.get("modelo") or {}
    cat = Catalogo.desde_modelo(modelo) if modelo.get("model") \
        else Catalogo.desde_layout(cargado.get("layout") or {})
    layout = cargado.get("layout") or {}
    # La MISMA cuenta que muestra la pestaña Analizador: modelo + reporte.
    # Con solo el modelo, el documento que se manda por mail decía 76/100 y
    # la pantalla del que lo generó, 54/100 — sin nada que explicara la
    # diferencia, y siendo el número más visible del documento.
    hallazgos = (analizador.analizar(cat, _reporte.tablas_usadas(layout))
                 + _reporte.analizar(layout))
    meta = cargado.get("dataset_meta")
    # Las FILAS que viajan adentro del archivo. Es lo que permite medir
    # —huérfanos, cifras de control, concentración— en un .pbit
    # autocontenido, sin pedirle al usuario el Excel de origen que quizá
    # ya no tenga a mano.
    datos = dataset.datos_del_modelo(modelo)
    paleta = dict(_PALETA)
    if marca:
        # Solo colores hex, y validados: la paleta se interpola dentro del
        # <style>, así que un valor con `}</style><script>` saldría entero
        # al documento. Hoy los dos únicos productores son el lector del
        # logo y el color_picker —ambos dan hex— pero `generar()` es una
        # función pública y el agujero no depende de quién la llame.
        paleta.update({k: v for k, v in marca.items()
                       if k in paleta and _es_hex(v)})

    nombre = titulo or modelo.get("name") or cargado.get("origen") or "Dataset"
    visibles = [t for t in cat.tablas if not t["interna"]]
    numericas = sum(1 for _t, c in cat.columnas()
                    if c["tipo"] in TIPOS_NUMERICOS)
    salud = analizador.puntaje(hallazgos)

    secciones = [
        ("1", traducir("inf_s_resumen", idioma), "resumen",
         _resumen(cat, hallazgos, idioma)),
        ("2", traducir("inf_s_auditoria", idioma), "auditoria",
         _auditoria(cat, meta, idioma, datos)),
        ("3", traducir("inf_s_modelo", idioma), "modelo",
         _modelo(cat, idioma)),
        ("4", traducir("inf_s_pq", idioma), "pq", _powerquery(modelo, idioma)),
        ("5", traducir("inf_s_medidas", idioma), "medidas",
         _medidas(cat, idioma)),
        ("6", traducir("inf_s_tablero", idioma), "tablero",
         _tablero(cargado.get("layout"), idioma)),
        ("7", traducir("inf_s_control", idioma), "control",
         _control(cat, datos, idioma)),
        ("8", traducir("inf_s_porque", idioma), "porque",
         _porque(cargado, idioma)),
        ("9", traducir("inf_s_reco", idioma), "reco",
         _recomendaciones(cat, hallazgos, idioma, cargado, datos)),
    ]
    indice = "".join(f'<a href="#{a}">{_esc(num)} · {_esc(t)}</a>'
                     for num, t, a, _c in secciones)
    cuerpo = "".join(_seccion(n, t, a, c) for n, t, a, c in secciones)

    tarjetas = [
        (traducir("inf_k_tablas", idioma), _n(len(visibles))),
        (traducir("inf_k_medidas", idioma), _n(len(cat.medidas()))),
        (traducir("inf_k_relaciones", idioma), _n(len(cat.relaciones))),
        (traducir("inf_k_numericas", idioma), _n(numericas)),
        (traducir("inf_k_salud", idioma),
         "—" if cat.parcial else f"{salud}/100"),
    ]
    hdrk = "".join(f"<div><b>{_esc(k)}</b><span>{v}</span></div>"
                   for k, v in tarjetas)

    return f"""<!doctype html>
<html lang="{_esc(idioma)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(traducir("inf_titulo", idioma).format(nombre=nombre))}</title>
<style>{_estilos(paleta)}</style></head><body>
<header><div class="in">
<h1>{_esc(traducir("inf_titulo", idioma).format(nombre=nombre))}</h1>
<p>{_esc(traducir("inf_subtitulo", idioma).format(
    fecha=date.today().isoformat()))}</p>
<div class="hdrk">{hdrk}</div></div></header>
<nav class="idx">{indice}</nav>
<div class="wrap">{cuerpo}</div>
<footer>{_esc(traducir("inf_pie", idioma))}</footer>
</body></html>"""


# ==========================================================================
# Preguntarle al informe
# ==========================================================================
# Cuántas filas de evidencia se juntan como máximo. La respuesta se apoya
# en hechos MEDIDOS; mandarle el modelo entero a la IA no la hace más
# precisa, la hace más cara y más propensa a inventar.
_MAX_EVIDENCIA = 40


# Palabras que no dicen nada de lo que se pregunta. Sin esta lista, «por»,
# «las», «con» o «una» matchean media docena de nombres y empujan fuera del
# corte a la evidencia que sí responde.
_VACIAS = frozenset("""
que qué cual cuál cuáles como cómo donde dónde cuando cuándo cuanto cuánto
cuantos cuántos cuantas cuántas por para con sin del las los una uno unos
unas este esta esto estos estas ese esa eso mas más pero sus sui tiene
tienen hay son está están fue ser hacer todo toda todos todas the and for
with from what which where when how many much does have has are was were
""".split())


# Palabras que delatan una pregunta de CAUSA, no de estructura. Cuando
# alguna aparece, la descomposición del share entra primero en la
# evidencia: es lo único que responde un «por qué».
#
# Solo términos CAUSALES o de movimiento. Los sustantivos del dominio
# —«mercado», «share», «precio», «competencia»— quedaron afuera a
# propósito: «qué columnas tiene la tabla Mercado» es una pregunta de
# estructura, y disparaba el análisis entero por nombrar una tabla.
_PORQUE = frozenset("""
porque porqué razon razones causa causas motivo motivos explicacion
explica explicar crecimos crecio crece crecimiento caimos cayo cae bajamos
bajo baja perdimos perdio pierde perdiendo ganamos gano brecha desempeno
mezcla why reason cause explain explanation grew fell dropped losing lost
gap underperform
""".split())


def _claves(pregunta: str) -> set[str]:
    return {p for p in re.split(r"\W+", _norm(pregunta))
            if len(p) > 2 and p not in _VACIAS}


def _buscar(cargado: dict, pregunta: str,
            idioma: str) -> tuple[list[str], list[str], int]:
    """Los hechos del modelo que tienen que ver con la pregunta.

    Devuelve `(evidencia, resumen, descartadas)`: la evidencia son líneas
    verificables —cada una sale de algo que se leyó—, el resumen es el
    contexto fijo, y `descartadas` cuántas quedaron afuera del tope.

    La evidencia se ordena por lo que RESPONDE, no por el orden en que se
    recorre el modelo. Con el perfilado al final, un modelo con 60 medidas
    homónimas llenaba las 40 líneas con medidas idénticas y dejaba afuera
    el conteo de vacíos que el programa había medido de verdad — y a la IA
    le llegaba, además, la afirmación de que eso era todo lo que se sabía.
    """
    modelo = cargado.get("modelo") or {}
    cat = Catalogo.desde_modelo(modelo) if modelo.get("model") \
        else Catalogo.desde_layout(cargado.get("layout") or {})
    _lay = cargado.get("layout") or {}
    hallazgos = (analizador.analizar(cat, _reporte.tablas_usadas(_lay))
                 + _reporte.analizar(_lay))
    palabras = _claves(pregunta)

    resumen = [
        traducir("inf_ev_resumen", idioma).format(
            tablas=len([t for t in cat.tablas if not t["interna"]]),
            medidas=len(cat.medidas()),
            relaciones=len(cat.relaciones),
            salud=analizador.puntaje(hallazgos)),
    ]
    for g in analizador.agrupar(hallazgos)[:6]:
        d = analizador.describir(g, idioma)
        resumen.append(f'{g["regla"]} ({g["severidad"]}): {d["titulo"]} — '
                       f'{len(g["objetos"])}×')

    # (prioridad, texto). Prioridad baja = entra primero. El perfilado es
    # lo único que trae NÚMEROS medidos, así que va adelante.
    candidatas: list[tuple[int, str]] = []

    # La explicación de por qué se movió el share entra con la prioridad
    # más alta cuando la pregunta va por ahí. Sin esto, a un «por qué
    # crecimos menos que el mercado» le llegaban nombres de medidas y la
    # IA tenía que inventar la causa o decir que no sabía — teniendo el
    # programa la descomposición exacta calculada.
    if palabras & _PORQUE:
        from . import analitica
        exp = analitica.explicar(cargado, idioma)
        if exp and not exp.get("sin_propia"):
            resumen.append(traducir("inf_ev_brecha", idioma).format(
                propia=exp["propia"], propio=exp["crec_propio"] * 100,
                mercado=exp["crec_mercado"] * 100, pp=exp["delta_pp"],
                previo=exp["previo"], actual=exp["actual"],
                meses=exp["meses"]))
            for d in exp["dimensiones"][:1]:
                resumen.append(traducir("inf_ev_efectos", idioma).format(
                    dim=d["dimension"], desempeno=d["desempeno"] * 100,
                    mezcla=d["mezcla"] * 100))
                for mi in d["miembros"][:6] + d["miembros"][-3:]:
                    candidatas.append((-100, traducir(
                        "inf_ev_segmento", idioma).format(
                            miembro=mi["miembro"], dim=d["dimension"],
                            pp=mi["total"] * 100, peso=mi["peso"] * 100,
                            propio=mi["crec_propio"] * 100,
                            mercado=mi["crec_mercado"] * 100)))
            pr = exp.get("precio")
            if pr:
                resumen.append(traducir("inf_ev_precio", idioma).format(
                    var=pr["var_precio"] * 100,
                    unidades=pr["var_unidades"] * 100,
                    vol=pr["efecto_volumen"], pre=pr["efecto_precio"]))

    def puntos(texto: str) -> int:
        return len(palabras & _claves(texto))

    for t in (cargado.get("dataset_meta") or {}).get("tablas", []):
        datos = t.get("datos")
        if not datos:
            continue
        p_tabla = puntos(t["nombre"])
        for i, c in enumerate(t["columnas"]):
            p = p_tabla + puntos(c["nombre"])
            if not p:
                continue
            valores = [f[i] for f in datos if i < len(f)]
            llenos = [v for v in valores if str(v).strip()]
            candidatas.append((0 - p, traducir(
                "inf_ev_perfil", idioma).format(
                    tabla=t["nombre"], columna=c["nombre"],
                    filas=len(valores),
                    distintos=len({str(v) for v in llenos}),
                    vacios=len(valores) - len(llenos))))
    for m in cat.medidas():
        p = puntos(m["nombre"]) + puntos(m.get("descripcion") or "")
        if p:
            candidatas.append((10 - p, traducir(
                "inf_ev_medida", idioma).format(
                    nombre=m["nombre"], formato=m.get("formato") or "—",
                    dax=_acortar(m.get("expresion", ""))[:400])))
    for t in cat.tablas:
        p = 0 if t["interna"] else puntos(t["nombre"])
        if p:
            candidatas.append((5 - p, traducir(
                "inf_ev_tabla", idioma).format(
                    nombre=t["nombre"], papel=_clase_tabla(cat, t, idioma),
                    columnas=", ".join(c["nombre"]
                                       for c in t["columnas"][:14]))))
    for tabla, col in cat.columnas():
        p = puntos(col["nombre"])
        if p:
            candidatas.append((8 - p, traducir(
                "inf_ev_columna", idioma).format(
                    tabla=tabla, columna=col["nombre"], tipo=col["tipo"])))

    candidatas.sort(key=lambda x: x[0])
    vistas, evidencia = set(), []
    for _p, texto in candidatas:
        if texto in vistas:
            continue
        vistas.add(texto)
        evidencia.append(texto)
    return (evidencia[:_MAX_EVIDENCIA], resumen,
            max(len(evidencia) - _MAX_EVIDENCIA, 0))


def responder(cargado: dict, pregunta: str, idioma: str = IDIOMA_DEFECTO,
              proveedor: str = "", api_key: str | None = None) -> dict:
    """Contesta una pregunta sobre el modelo, apoyada en lo que se midió.

    La IA —cuando hay clave— redacta; los números los pone el programa. Sin
    clave se contesta igual, con la evidencia cruda: más seco, misma
    verdad. Nunca se responde con algo que no esté en la evidencia, y
    cuando la evidencia no alcanza, se dice.

    Devuelve `{"respuesta", "evidencia", "con_ia"}`.
    """
    evidencia, resumen, descartadas = _buscar(cargado, pregunta, idioma)
    lineas = resumen + evidencia
    if descartadas:
        # Decirlo, y decírselo también a la IA: el prompt afirmaba que la
        # evidencia era TODO lo que se había medido, y podía estar cortada.
        lineas.append(traducir("inf_ev_cortada", idioma).format(
            n=descartadas))

    if proveedor:
        from . import proveedores_ia
        if proveedores_ia.hay_clave(proveedor, api_key):
            sistema = traducir("inf_ia_sistema", idioma)
            contexto = "\n".join(f"- {x}" for x in lineas)
            try:
                texto = proveedores_ia.consultar(
                    [{"role": "user",
                      "content": traducir("inf_ia_prompt", idioma).format(
                          pregunta=pregunta, contexto=contexto)}],
                    sistema=sistema, proveedor=proveedor, api_key=api_key)
                return {"respuesta": texto, "evidencia": lineas,
                        "con_ia": True}
            except Exception as exc:      # noqa: BLE001 — se muestra el motivo
                return {"respuesta": traducir("inf_ia_falla", idioma).format(
                    motivo=str(exc)[:200]) + "\n\n"
                    + _local(lineas, evidencia, idioma),
                    "evidencia": lineas, "con_ia": False}
    return {"respuesta": _local(lineas, evidencia, idioma),
            "evidencia": lineas, "con_ia": False}


def _local(lineas: list[str], evidencia: list[str], idioma: str) -> str:
    """La respuesta sin IA: los hechos, ordenados. No pretende redactar.

    Lo que decide si hubo respuesta es la EVIDENCIA, no el total de líneas:
    el resumen del modelo va siempre, así que contarlo haría que cualquier
    pregunta —incluso una que no tiene nada que ver con el archivo— pareciera
    contestada.
    """
    if not evidencia:
        return traducir("inf_sin_respuesta", idioma)
    return (traducir("inf_local_intro", idioma) + "\n\n"
            + "\n".join(f"- {x}" for x in lineas))
