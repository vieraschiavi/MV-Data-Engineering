# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 10 · DAX: la biblioteca de medidas generada desde los KPIs del YAML.

Patrones fijos: DIVIDE para todo cociente, KEEPFILTERS en predicados,
REMOVEFILTERS para comparar contra el total, DATEADD sobre dim_calendario
para el mes anterior (si hay calendario). Sale como texto (`measures.dax`)
con el formato que entiende MV DAX Lab y el generador de .pbit.
"""
from __future__ import annotations

_AGG = {"sum": "SUM", "avg": "AVERAGE", "min": "MIN", "max": "MAX"}


def _nombre_medida(nombre: str) -> str:
    return nombre.replace("[", "(").replace("]", ")").strip()


def _expr_agg(k: dict) -> str:
    agg = k.get("agregacion", "sum")
    tabla, col = k["tabla"], k.get("columna")
    if agg == "count":
        return f"COUNTROWS ( {tabla} )"
    if agg == "count_distinct":
        return f"DISTINCTCOUNT ( {tabla}[{col}] )"
    return f"{_AGG.get(agg, 'SUM')} ( {tabla}[{col}] )"


def _formato(k: dict) -> str:
    f = k.get("formato") or "#,0"
    return "0.0%" if f.endswith("%") else f


def generar(spec: dict, gold_tablas: list[str]) -> tuple[str, list[dict]]:
    kpis = spec.get("kpis") or []
    hay_calendario = "dim_calendario" in gold_tablas
    medidas: list[dict] = []
    lineas = ["// Biblioteca DAX generada por MV Data Engineering desde el YAML del proyecto.",
              "// Un bloque `Nombre = expresión` por medida; el comentario de arriba es la descripción.", ""]
    for k in kpis:
        nombre = _nombre_medida(k["nombre"])
        tipo = k.get("tipo", "agregacion")
        if tipo == "sql":
            continue  # un KPI escrito en SQL no tiene traducción automática a DAX
        if tipo == "ratio":
            n, d = k["numerador"], k["denominador"]
            expr = f"DIVIDE ( {_expr_agg(n)}, {_expr_agg(d)} )"
            tabla = n["tabla"]
        else:
            expr = _expr_agg(k)
            tabla = k["tabla"]
        if tabla not in gold_tablas:
            continue
        if tipo == "ratio":
            desc = f"{k['numerador'].get('agregacion', 'sum')} de {k['numerador'].get('columna') or 'filas'} sobre {k['denominador'].get('agregacion', 'sum')} de {k['denominador'].get('columna') or 'filas'}"
        elif k.get("agregacion", "sum") == "count":
            desc = f"Cantidad de filas de {tabla}"
        else:
            desc = f"{k.get('agregacion', 'sum')} de {tabla}[{k.get('columna', '')}]"
        medidas.append({"nombre": nombre, "tabla": tabla, "expresion": expr, "formato": _formato(k),
                        "descripcion": k.get("descripcion") or desc})
        if k.get("filtro"):
            medidas.append({"nombre": f"{nombre} (filtrado)", "tabla": tabla, "formato": _formato(k),
                            "expresion": f"CALCULATE ( [{nombre}], KEEPFILTERS ( {k['filtro']} ) )",
                            "descripcion": f"{nombre} con el filtro {k['filtro']} intersectado con el del visual"})
        medidas.append({"nombre": f"{nombre} total", "tabla": tabla, "formato": _formato(k),
                        "expresion": f"CALCULATE ( [{nombre}], REMOVEFILTERS () )",
                        "descripcion": f"{nombre} del total, ignorando los filtros del visual (para comparar)"})
        if tipo == "ratio":
            medidas.append({"nombre": f"{nombre} vs total pp", "tabla": tabla, "formato": "0.0",
                            "expresion": f"( [{nombre}] - [{nombre} total] ) * 100",
                            "descripcion": f"Diferencia de {nombre} contra el total, en puntos porcentuales"})
        else:
            medidas.append({"nombre": f"{nombre} % del total", "tabla": tabla, "formato": "0.0%",
                            "expresion": f"DIVIDE ( [{nombre}], [{nombre} total] )",
                            "descripcion": f"Participación de {nombre} sobre el total"})
        if hay_calendario:
            medidas.append({"nombre": f"{nombre} mes anterior", "tabla": tabla, "formato": _formato(k),
                            "expresion": f"CALCULATE ( [{nombre}], DATEADD ( dim_calendario[fecha], -1, MONTH ) )",
                            "descripcion": f"{nombre} del mes anterior (dim_calendario marcada como tabla de fechas)"})
            medidas.append({"nombre": f"{nombre} var. mensual %", "tabla": tabla, "formato": "0.0%",
                            "expresion": f"DIVIDE ( [{nombre}] - [{nombre} mes anterior], [{nombre} mes anterior] )",
                            "descripcion": f"Variación de {nombre} contra el mes anterior"})
    tabla_actual = None
    for m in medidas:
        if m["tabla"] != tabla_actual:
            lineas.append(f"-- table: {m['tabla']}")
            lineas.append("")
            tabla_actual = m["tabla"]
        lineas.append(f"// {m['descripcion']}")
        lineas.append(f"{m['nombre']} = {m['expresion']}")
        lineas.append("")
    return "\n".join(lineas), medidas
