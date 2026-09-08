# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Estadísticas del modelo y diferencias entre dos versiones.

Son las dos funciones por las que la gente abre Bravo («Analyze model»:
qué pesa, qué columna no usa nadie) y ALM Toolkit («Compare»: qué cambió
entre el modelo de antes y el de después), hechas adentro del programa
sobre lo que ya sabe leer: el catálogo, el reporte y las filas que
viajan empotradas.

Nada de esto pide un servidor de Analysis Services. Lo que no se puede
saber sin uno —el tamaño real en memoria de cada columna— no se inventa:
se cuenta lo que hay (filas, valores distintos) y se dice que es una
estimación.
"""
from __future__ import annotations

import csv
import io

from .catalogo import Catalogo, _norm
from .modelo import expr_texto


def _filas(tabla_tmsl: dict) -> tuple[list[str], list[list]] | None:
    from .dataset import filas_embebidas
    return filas_embebidas(tabla_tmsl)


def resumen_tablas(cat: Catalogo, modelo: dict) -> list[dict]:
    """Por tabla: columnas, medidas, relaciones, filas empotradas y la
    cardinalidad (valores distintos) de sus columnas más pesadas."""
    tmsl = {_norm(t.get("name", "")): t
            for t in modelo.get("model", {}).get("tables", [])}
    salida = []
    for t in cat.tablas:
        if t.get("interna"):
            continue
        crudo = tmsl.get(_norm(t["nombre"]), {})
        datos = _filas(crudo)
        filas = len(datos[1]) if datos else None
        pesadas: list[tuple[str, int]] = []
        if datos:
            cols, valores = datos
            for i, c in enumerate(cols):
                distintos = len({str(f[i]) for f in valores if i < len(f)})
                pesadas.append((c, distintos))
            pesadas.sort(key=lambda par: -par[1])
        rels = sum(1 for r in cat.relaciones
                   if _norm(t["nombre"]) in (_norm(r["desde_tabla"]),
                                             _norm(r["hacia_tabla"])))
        salida.append({
            "tabla": t["nombre"],
            "columnas": len(t["columnas"]),
            "medidas": len(t["medidas"]),
            "relaciones": rels,
            "filas": filas,
            "pesadas": pesadas[:3],
        })
    return salida


def _campos_del_reporte(layout: dict | None) -> set[tuple[str, str]]:
    """`(tabla, columna)` que algún visual o filtro del reporte usa."""
    from .verificacion import _campos_del_filtro, _campos_visual
    import json

    usados: set[tuple[str, str]] = set()
    for pag in (layout or {}).get("sections", []) or []:
        for vc in pag.get("visualContainers", []) or []:
            try:
                sv = json.loads(vc["config"])["singleVisual"]
            except Exception:                          # noqa: BLE001
                continue
            medidas, categorias = _campos_visual(sv)
            for tabla, campo in medidas + categorias:
                usados.add((_norm(tabla), _norm(campo)))
            for f in (sv.get("filters") or []) if isinstance(
                    sv.get("filters"), list) else []:
                for tabla, campo in _campos_del_filtro(f):
                    usados.add((_norm(tabla), _norm(campo)))
        try:
            filtros = json.loads(pag.get("filters") or "[]")
        except Exception:                              # noqa: BLE001
            filtros = []
        for f in filtros if isinstance(filtros, list) else []:
            for tabla, campo in _campos_del_filtro(f):
                usados.add((_norm(tabla), _norm(campo)))
    return usados


def columnas_sin_uso(cat: Catalogo, modelo: dict,
                     layout: dict | None = None) -> list[dict]:
    """Columnas que nadie usa: ni una medida, ni una relación, ni un orden,
    ni una jerarquía, ni un visual del reporte.

    Es lo primero que Bravo marca al analizar un modelo, y con razón: cada
    columna que viaja sin que nadie la lea es memoria y tiempo de refresco
    tirados. Se acusa solo con evidencia: si no hay reporte cargado, las
    columnas visibles se consideran «posiblemente usadas» y no entran.
    """
    dax = " ".join(_norm(m.get("expresion", "")) for m in cat.medidas())
    dax += " ".join(_norm(c.get("expresion", "") or "")
                    for t in cat.tablas for c in t["columnas"])
    en_rel = {(_norm(r[a]), _norm(r[b])) for r in cat.relaciones
              for a, b in (("desde_tabla", "desde_col"),
                           ("hacia_tabla", "hacia_col"))}
    del_reporte = _campos_del_reporte(layout) if layout else None
    orden: set[tuple[str, str]] = set()
    jerarquias: set[tuple[str, str]] = set()
    for t in modelo.get("model", {}).get("tables", []):
        tn = _norm(t.get("name", ""))
        for c in t.get("columns", []):
            if c.get("sortByColumn"):
                orden.add((tn, _norm(c["sortByColumn"])))
        for h in t.get("hierarchies", []):
            for n in h.get("levels", []):
                jerarquias.add((tn, _norm(n.get("column", ""))))
    salida = []
    for t in cat.tablas:
        if t.get("interna"):
            continue
        tn = _norm(t["nombre"])
        for c in t["columnas"]:
            cn = _norm(c["nombre"])
            clave = (tn, cn)
            if clave in en_rel or clave in orden or clave in jerarquias:
                continue
            if f"[{cn}]" in dax:
                continue
            if del_reporte is None:
                if not c.get("oculta"):
                    continue          # sin reporte no se acusa lo visible
            elif clave in del_reporte:
                continue
            salida.append({"tabla": t["nombre"], "columna": c["nombre"],
                           "oculta": bool(c.get("oculta"))})
    return salida


def diferencias(antes: dict, despues: dict) -> dict:
    """Qué cambió entre dos modelos: tablas, columnas, medidas y
    relaciones agregadas, quitadas o modificadas. Es el «Compare» de ALM
    Toolkit, sobre los dos .bim que este programa ya sabe exportar."""
    def _tablas(m):
        return {t.get("name", ""): t for t in
                m.get("model", {}).get("tables", [])}

    def _medidas(m):
        return {(t.get("name", ""), me.get("name", "")):
                expr_texto(me.get("expression")).strip()
                for t in m.get("model", {}).get("tables", [])
                for me in t.get("measures", [])}

    def _columnas(m):
        return {(t.get("name", ""), c.get("name", "")):
                (c.get("dataType"), bool(c.get("isHidden")),
                 c.get("formatString"))
                for t in m.get("model", {}).get("tables", [])
                for c in t.get("columns", [])}

    def _rels(m):
        return {(r.get("fromTable"), r.get("fromColumn"),
                 r.get("toTable"), r.get("toColumn")):
                (r.get("isActive", True), r.get("crossFilteringBehavior"))
                for r in m.get("model", {}).get("relationships", [])}

    ta, td = set(_tablas(antes)), set(_tablas(despues))
    ma, md = _medidas(antes), _medidas(despues)
    ca, cd = _columnas(antes), _columnas(despues)
    ra, rd = _rels(antes), _rels(despues)
    return {
        "tablas": {"agregadas": sorted(td - ta), "quitadas": sorted(ta - td)},
        "medidas": {
            "agregadas": sorted(set(md) - set(ma)),
            "quitadas": sorted(set(ma) - set(md)),
            "modificadas": sorted(k for k in set(ma) & set(md)
                                  if ma[k] != md[k]),
        },
        "columnas": {
            "agregadas": sorted(set(cd) - set(ca)),
            "quitadas": sorted(set(ca) - set(cd)),
            "modificadas": sorted(k for k in set(ca) & set(cd)
                                  if ca[k] != cd[k]),
        },
        "relaciones": {
            "agregadas": sorted(set(rd) - set(ra), key=str),
            "quitadas": sorted(set(ra) - set(rd), key=str),
            "modificadas": sorted((k for k in set(ra) & set(rd)
                                   if ra[k] != rd[k]), key=str),
        },
    }


def total_diferencias(d: dict) -> int:
    return sum(len(v) for grupo in d.values() for v in grupo.values())


def csv_de_tabla(modelo: dict, tabla: str) -> str | None:
    """Las filas empotradas de una tabla, como CSV. `None` si la tabla no
    lleva datos adentro. Es el «Export data» de Bravo."""
    for t in modelo.get("model", {}).get("tables", []):
        if _norm(t.get("name", "")) != _norm(tabla):
            continue
        datos = _filas(t)
        if not datos:
            return None
        cols, filas = datos
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        w.writerows(filas)
        return buf.getvalue()
    return None
