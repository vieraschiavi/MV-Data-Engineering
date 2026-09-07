# © 2026 Martín Viera. Todos los derechos reservados.
"""Demos incluidas, 100 % sintéticas y con semilla fija.

  cobranzas: una financiera — clientes, cuotas y pagos, con mora y default.
  ventas:    consumo masivo — productos, sucursales y ventas diarias.
  conaprole: cooperativa láctea — remisión de leche por productor y mes, con
             calidad de laboratorio, liquidación por sólidos y proyección de
             la zafra. Pensada para mostrarle el producto a una industria
             láctea; los datos NO son de ninguna empresa (ver `_conaprole`).

`crear(nombre, carpeta)` escribe los CSV y el `proyecto.yaml` listos para
`python -m mvde correr`. Cada demo ejercita cosas distintas del motor.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import proyecto

NOMBRES = ["cobranzas", "ventas", "kash", "cartera", "conaprole"]


def _cobranzas(carpeta: Path, n_clientes: int = 4000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    ids = np.arange(1, n_clientes + 1)
    clientes = pd.DataFrame({
        "id_cliente": ids,
        "sexo": rng.choice([1, 2], n_clientes, p=[0.45, 0.55]),
        "educacion": rng.choice([1, 2, 3, 4, 0], n_clientes, p=[0.3, 0.45, 0.2, 0.04, 0.01]),
        "edad": np.clip(rng.gamma(9, 4, n_clientes) + 18, 21, 79).astype(int),
        "sucursal": rng.choice(["Centro", "Norte", "Sur", "Este", "Oeste"], n_clientes),
        "limite_credito": (np.round(np.exp(rng.normal(np.log(120_000), 0.6, n_clientes)) / 5000) * 5000).astype(int),
        "email": [f"cliente{i}@ejemplo.test" for i in ids],
    })
    riesgo = rng.normal(0, 1, n_clientes) - 0.3 * (np.log(clientes["limite_credito"]) - np.log(120_000)) - 0.1 * (clientes["edad"] - 35) / 10
    meses = pd.date_range("2025-01-01", periods=12, freq="MS")
    filas = []
    for i, r in enumerate(riesgo):
        atraso = 0
        p_caer = 1 / (1 + np.exp(-(-2.2 + 0.9 * r)))
        cuota = float(clientes.loc[i, "limite_credito"]) * rng.uniform(0.02, 0.06)
        for m in meses:
            u = rng.random()
            if atraso >= 1:
                atraso = atraso + 1 if u < 0.6 else 0
            elif u < p_caer:
                atraso = 1
            pagado = 0.0 if atraso >= 1 and rng.random() < 0.7 else cuota * (rng.uniform(0.9, 1.05) if atraso == 0 else rng.uniform(0.0, 0.5))
            canal = rng.choice(["Débito", "Web", "Sucursal", "Call center"], p=[0.4, 0.3, 0.2, 0.1])
            filas.append((int(clientes.loc[i, "id_cliente"]), m, round(cuota, 2), round(pagado, 2), int(min(atraso, 9)), canal))
    cuotas = pd.DataFrame(filas, columns=["id_cliente", "fecha_vencimiento", "monto_cuota", "monto_pagado", "meses_atraso", "canal"])
    ultimo = cuotas.sort_values("fecha_vencimiento").groupby("id_cliente")["meses_atraso"].last()
    logit = -2.0 + 0.5 * riesgo + 0.8 * np.clip(ultimo.reindex(ids).values, 0, 4)
    clientes["default_proximo_mes"] = (rng.random(n_clientes) < 1 / (1 + np.exp(-logit))).astype(int)
    # Defectos inyectados a propósito, para que el gate tenga algo que decir (no críticos).
    cuotas.loc[rng.choice(len(cuotas), 25, replace=False), "monto_pagado"] = -1.0
    clientes.to_csv(carpeta / "clientes.csv", index=False)
    cuotas.to_csv(carpeta / "cuotas.csv", index=False, date_format="%Y-%m-%d")
    return {
        "nombre": "Cobranzas demo",
        "descripcion": "Financiera sintética: 4.000 clientes, 12 meses de cuotas y pagos, mora y default. Datos 100 % sintéticos.",
        "idioma": "es",
        "fuentes": [
            {"nombre": "clientes", "tipo": "csv", "ruta": "clientes.csv"},
            {"nombre": "cuotas", "tipo": "csv", "ruta": "cuotas.csv"},
        ],
        "silver": {
            "clientes": {"tipos": "auto",
                         "decodificar": {"sexo": {"1": "Masculino", "2": "Femenino"},
                                         "educacion": {"1": "Posgrado", "2": "Universidad", "3": "Secundaria", "4": "Otros", "_otros": "Desconocido"}},
                         "deduplicar": ["id_cliente"],
                         "derivar": {"banda_limite": "np.where(df['limite_credito'] < 50000, '<50k', np.where(df['limite_credito'] < 150000, '50k-150k', '150k+'))"}},
            "cuotas": {"tipos": "auto", "fechas": ["fecha_vencimiento"],
                       "derivar": {"en_mora": "meses_atraso >= 1", "saldo_impago": "monto_cuota - monto_pagado.clip(lower=0)"}},
        },
        "calidad": {"criticos_cortan": True, "reglas": [
            {"tabla": "clientes", "columna": "id_cliente", "tipo": "unico", "critico": True},
            {"tabla": "clientes", "columna": "edad", "tipo": "rango", "min": 18, "max": 100, "critico": True},
            {"tabla": "clientes", "columna": "limite_credito", "tipo": "positivo", "critico": True},
            {"tabla": "clientes", "columna": "educacion", "tipo": "valores", "valores": ["Posgrado", "Universidad", "Secundaria", "Otros", "Desconocido"], "critico": False},
            {"tabla": "cuotas", "columna": "id_cliente", "tipo": "referencia", "a": "clientes.id_cliente", "critico": True},
            {"tabla": "cuotas", "columna": "monto_pagado", "tipo": "no_negativo", "critico": False},
            {"tabla": "cuotas", "columna": "meses_atraso", "tipo": "rango", "min": 0, "max": 9, "critico": True},
            {"tabla": "cuotas", "tipo": "filas_min", "valor": 40000, "critico": True},
        ]},
        "modelo": {
            "dimensiones": [{"nombre": "dim_cliente", "desde": "clientes", "clave": "id_cliente",
                             "atributos": ["sexo", "educacion", "edad", "sucursal", "limite_credito", "banda_limite"], "scd": 2}],
            "hechos": [{"nombre": "fact_cuota", "desde": "cuotas", "fecha": "fecha_vencimiento", "claves": {"id_cliente": "dim_cliente"},
                        "medidas": ["monto_cuota", "monto_pagado", "saldo_impago"]},
                       {"nombre": "fact_cliente_riesgo", "desde": "clientes", "claves": {"id_cliente": "dim_cliente"}, "medidas": ["default_proximo_mes"]}],
            "calendario": "auto",
        },
        "vistas": {
            "v_mora_mensual": "SELECT c.anio_mes, COUNT(*) cuotas, SUM(CASE WHEN f.en_mora THEN 1 ELSE 0 END) en_mora, ROUND(100.0*SUM(CASE WHEN f.en_mora THEN 1 ELSE 0 END)/COUNT(*),2) tasa_mora_pct, SUM(f.monto_pagado) pagado, SUM(f.monto_cuota) facturado FROM gold.fact_cuota f JOIN gold.dim_calendario c USING (fecha_key) GROUP BY 1 ORDER BY 1",
            "v_default_por_sucursal": "SELECT d.sucursal, COUNT(*) clientes, SUM(r.default_proximo_mes) cant_default, ROUND(100.0*SUM(r.default_proximo_mes)/COUNT(*),2) tasa_default_pct FROM gold.fact_cliente_riesgo r JOIN gold.dim_cliente d USING (dim_cliente_key) WHERE d.is_current GROUP BY 1 ORDER BY 4 DESC",
        },
        "kpis": [
            {"nombre": "Clientes", "tabla": "fact_cliente_riesgo", "agregacion": "count", "formato": "#,0"},
            {"nombre": "Tasa de default %", "tipo": "ratio", "numerador": {"tabla": "fact_cliente_riesgo", "columna": "default_proximo_mes", "agregacion": "sum"},
             "denominador": {"tabla": "fact_cliente_riesgo", "agregacion": "count"}, "formato": "0.0%"},
            {"nombre": "Monto facturado", "tabla": "fact_cuota", "columna": "monto_cuota", "agregacion": "sum", "formato": "#,0", "por": "canal"},
            {"nombre": "Saldo impago", "tabla": "fact_cuota", "columna": "saldo_impago", "agregacion": "sum", "formato": "#,0", "por": "dim_cliente.sucursal"},
            {"nombre": "Monto cobrado", "tabla": "fact_cuota", "columna": "monto_pagado", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "% Cobrado", "tipo": "ratio", "numerador": {"tabla": "fact_cuota", "columna": "monto_pagado", "agregacion": "sum"},
             "denominador": {"tabla": "fact_cuota", "columna": "monto_cuota", "agregacion": "sum"}, "formato": "0.0%"},
            {"nombre": "Cuotas en mora %", "tipo": "sql", "sql": "SELECT AVG(CASE WHEN en_mora THEN 1.0 ELSE 0.0 END) FROM gold.fact_cuota", "formato": "0.0%"},
        ],
        "gobernanza": {"dueno": "BI Cobranzas", "pii": ["clientes.email"],
                       "descripciones": {"clientes.id_cliente": "Identificador del cliente", "cuotas.meses_atraso": "0 = al día, 1..9 meses de atraso",
                                         "id_cliente": "Identificador del cliente",
                                         "sexo": "Sexo del titular (1/2), como viene del sistema de origen",
                                         "educacion": "Nivel educativo declarado (0 = sin dato)",
                                         "edad": "Edad del titular en años",
                                         "sucursal": "Sucursal que originó el crédito",
                                         "limite_credito": "Límite de crédito asignado, en pesos",
                                         "email": "Correo de contacto del titular",
                                         "fecha_vencimiento": "Fecha de vencimiento de la cuota",
                                         "monto_cuota": "Importe de la cuota que vence",
                                         "canal": "Canal por el que se cobró o se intentó cobrar",
                                         "clientes.default_proximo_mes": "1 si no paga la cuota del mes siguiente", "cuotas.monto_pagado": "Pagado en el mes (moneda local)"}},
        "ml": {"sql": "SELECT r.default_proximo_mes, d.edad, d.educacion, d.sucursal, d.limite_credito, d.sexo, "
                      "SUM(CASE WHEN f.en_mora THEN 1 ELSE 0 END) meses_en_mora, MAX(f.meses_atraso) max_atraso, "
                      "SUM(f.monto_pagado)/NULLIF(SUM(f.monto_cuota),0) pct_pagado, "
                      "MAX(CASE WHEN f.fecha_key >= 20251001 THEN f.meses_atraso ELSE 0 END) atraso_ult_trim "
                      "FROM gold.fact_cliente_riesgo r JOIN gold.dim_cliente d USING (dim_cliente_key) "
                      "JOIN gold.fact_cuota f USING (dim_cliente_key) GROUP BY 1,2,3,4,5,6",
               "target": "default_proximo_mes", "tipo": "clasificacion"},
        # El maestro de clientes se refresca todos los días; las cuotas son mensuales.
        "frescura": {"cada": "diaria", "tablas": {"cuotas": {"cada": "mensual"}, "fact_cuota": {"cada": "mensual"}}},
        "reporte": {"titulo": "Cobranzas · tablero de mora y default", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Cobranzas"},
        "automatizacion": {"hora": "05:00", "reintentos": 3},
    }


def _ventas(carpeta: Path, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    productos = pd.DataFrame({
        "sku": [f"SKU{i:03d}" for i in range(1, 61)],
        "producto": [f"Producto {i}" for i in range(1, 61)],
        "categoria": rng.choice(["Bebidas", "Lácteos", "Limpieza", "Snacks", "Cuidado personal"], 60),
        "precio_lista": np.round(rng.uniform(80, 900, 60), 2),
    })
    sucursales = pd.DataFrame({"id_sucursal": range(1, 9), "sucursal": [f"Sucursal {c}" for c in "ABCDEFGH"],
                               "region": rng.choice(["Norte", "Centro", "Sur"], 8)})
    dias = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    filas = []
    for d in dias:
        estacional = 1 + 0.25 * np.sin(2 * np.pi * (d.dayofyear / 365)) + (0.3 if d.dayofweek >= 5 else 0)
        for s in sucursales["id_sucursal"]:
            for sku in rng.choice(productos["sku"], 12, replace=False):
                precio = float(productos.loc[productos.sku == sku, "precio_lista"].iloc[0])
                desc = rng.choice([0, 0, 0, 0.1, 0.2])
                unidades = int(max(1, rng.poisson(6 * estacional)))
                filas.append((d, int(s), sku, unidades, round(precio * (1 - desc), 2), desc))
    ventas = pd.DataFrame(filas, columns=["fecha", "id_sucursal", "sku", "unidades", "precio_unitario", "descuento"])
    ventas["importe"] = (ventas["unidades"] * ventas["precio_unitario"]).round(2)
    ventas = pd.concat([ventas, ventas.sample(60, random_state=1)])  # duplicados a propósito
    productos.to_excel(carpeta / "productos.xlsx", index=False)
    sucursales.to_csv(carpeta / "sucursales.csv", index=False, sep=";")
    ventas.to_parquet(carpeta / "ventas.parquet", index=False)
    return {
        "nombre": "Ventas demo",
        "descripcion": "Consumo masivo sintético: 60 productos, 8 sucursales, un año de ventas diarias. Tres formatos de origen (Excel, CSV con punto y coma, Parquet).",
        "idioma": "es",
        "fuentes": [
            {"nombre": "productos", "tipo": "excel", "ruta": "productos.xlsx"},
            {"nombre": "sucursales", "tipo": "csv", "ruta": "sucursales.csv"},
            {"nombre": "ventas", "tipo": "parquet", "ruta": "ventas.parquet"},
        ],
        "silver": {"ventas": {"tipos": "auto", "deduplicar": ["fecha", "id_sucursal", "sku"], "filtrar": "unidades > 0"}},
        "calidad": {"criticos_cortan": True, "reglas": [
            {"tabla": "productos", "columna": "sku", "tipo": "unico", "critico": True},
            {"tabla": "sucursales", "columna": "id_sucursal", "tipo": "unico", "critico": True},
            {"tabla": "ventas", "columna": "sku", "tipo": "referencia", "a": "productos.sku", "critico": True},
            {"tabla": "ventas", "columna": "id_sucursal", "tipo": "referencia", "a": "sucursales.id_sucursal", "critico": True},
            {"tabla": "ventas", "columna": "importe", "tipo": "positivo", "critico": True},
            {"tabla": "ventas", "columna": "descuento", "tipo": "rango", "min": 0, "max": 0.5, "critico": False},
            {"tabla": "ventas", "tipo": "expresion", "expresion": "importe == (unidades * precio_unitario).round(2)", "critico": False},
        ]},
        "modelo": {
            "dimensiones": [{"nombre": "dim_producto", "desde": "productos", "clave": "sku", "scd": 1},
                            {"nombre": "dim_sucursal", "desde": "sucursales", "clave": "id_sucursal", "scd": 1}],
            "hechos": [{"nombre": "fact_venta", "desde": "ventas", "fecha": "fecha",
                        "claves": {"sku": "dim_producto", "id_sucursal": "dim_sucursal"}, "medidas": ["unidades", "importe"]}],
            "calendario": "auto",
        },
        "vistas": {"v_ventas_mes_region": "SELECT c.anio_mes, s.region, SUM(f.importe) importe, SUM(f.unidades) unidades FROM gold.fact_venta f JOIN gold.dim_calendario c USING (fecha_key) JOIN gold.dim_sucursal s USING (dim_sucursal_key) GROUP BY 1,2 ORDER BY 1,2"},
        "kpis": [
            {"nombre": "Importe vendido", "tabla": "fact_venta", "columna": "importe", "agregacion": "sum", "formato": "#,0", "por": "dim_sucursal.sucursal"},
            {"nombre": "Unidades", "tabla": "fact_venta", "columna": "unidades", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Ticket promedio", "tipo": "ratio", "numerador": {"tabla": "fact_venta", "columna": "importe", "agregacion": "sum"},
             "denominador": {"tabla": "fact_venta", "agregacion": "count"}, "formato": "#,0.00"},
            {"nombre": "Productos vendidos", "tabla": "fact_venta", "columna": "dim_producto_key", "agregacion": "count_distinct", "formato": "#,0"},
        ],
        "gobernanza": {"dueno": "BI Comercial", "descripciones": {
            "importe": "Unidades × precio unitario con descuento",
            "fecha": "Fecha de la venta", "id_sucursal": "Identificador de la sucursal que vendió",
            "sku": "Código del producto vendido", "unidades": "Unidades vendidas en la operación",
            "precio_unitario": "Precio de lista por unidad, antes del descuento",
            "descuento": "Descuento aplicado, en tanto por uno (0,1 = 10 %)",
            "sucursal": "Nombre de la sucursal", "region": "Región comercial de la sucursal",
            "producto": "Nombre del producto", "categoria": "Categoría comercial del producto",
            "precio_lista": "Precio de lista vigente del producto, sin descuento"}},
        # Proyección de la venta diaria: lo que pide comercial. El backtest de
        # origen móvil decide con qué modelo se proyecta y deja escrito si le
        # gana o no a repetir la semana pasada.
        "ml": {"tipo": "serie", "tabla": "fact_venta", "fecha": "fecha_key", "valor": "importe",
               "frecuencia": "diaria", "horizonte": 14, "origenes": 12},
        "frescura": {"cada": "diaria", "tablas": {"productos": {"cada": "semanal"}, "sucursales": {"cada": "mensual"}}},
        "reporte": {"titulo": "Ventas · tablero comercial", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Ventas"},
    }




# ---------------------------------------------------------------------------
# Kash: una financiera de cobranzas, con el ESQUEMA REAL de un backtest a
# ciegas (train + score de la misma fecha) y datos 100 % sintéticos.
#
# El esquema y las proporciones salen de estadísticas AGREGADAS de un archivo
# real (mezcla de estados y subestados, bandas de score, distribución de días
# de atraso y de cuota, tasa de meses con pago); ninguna fila real viaja en
# este repositorio. Para correr el mismo YAML con los archivos reales, basta
# apuntar `fuentes[].ruta` a ellos: el esquema es el mismo.
# ---------------------------------------------------------------------------

_KASH_SUBESTADOS = {
    "Jurídica": [("Incobrables", 0.45), ("Mora Tardía - Estudio", 0.43), ("Extrajudicial", 0.06),
                 ("Extrajudicial SOMA", 0.012), ("Suspensión SC", 0.01), ("Mora Tardía - Juicio", 0.004),
                 ("Renuncia", 0.004), ("Venta", 0.002), ("Normal", 0.028)],
    "Comercial": [("Normal", 0.62), ("Mora Temprana", 0.30), ("Negociación", 0.08)],
    "Cobranza": [("Normal", 0.35), ("Mora Temprana", 0.35), ("Negociación", 0.30)],
    "Contaduría": [("Normal", 1.0)],
}
_KASH_P_PAGO_SUB = {"Normal": 0.87, "Mora Temprana": 0.95, "Negociación": 0.84, "Extrajudicial": 0.67,
                    "Extrajudicial SOMA": 0.53, "Mora Tardía - Estudio": 0.09, "Mora Tardía - Juicio": 0.09,
                    "Incobrables": 0.007, "Suspensión SC": 0.05, "Renuncia": 0.0, "Venta": 0.0}
_KASH_SCORE_AJUSTE = {"A": 1.35, "B": 1.05, "C": 0.85, "D": 0.95, "E": 0.7, "F": 0.5, "F-": 0.55, "SIN_SCORE": 0.9}


def _kash_universo(rng, n: int) -> pd.DataFrame:
    estados = rng.choice(["Jurídica", "Comercial", "Cobranza", "Contaduría"], n, p=[0.646, 0.209, 0.142, 0.003])
    subs = []
    for e in estados:
        opciones, pesos = zip(*_KASH_SUBESTADOS[e])
        pesos = np.array(pesos) / sum(pesos)
        subs.append(rng.choice(opciones, p=pesos))
    score = rng.choice(["SIN_SCORE", "C", "A", "B", "F-", "D", "E", "F"], n,
                       p=[0.472, 0.122, 0.12, 0.114, 0.057, 0.049, 0.036, 0.03])
    dias = np.where(np.isin(subs, ["Normal", "Mora Temprana", "Negociación"]), rng.integers(0, 120, n),
                    np.where(np.isin(subs, ["Extrajudicial", "Extrajudicial SOMA"]), rng.integers(120, 900, n),
                             rng.integers(700, 6000, n)))
    cuota = np.where(rng.random(n) < 0.54, 0.0, np.round(np.exp(rng.normal(np.log(4400), 0.6, n)), 2))
    return pd.DataFrame({"IdCliente": np.sort(rng.choice(np.arange(10, 60_000), n, replace=False)),
                         "CuotaEfectivaRef": cuota, "DiasAtraso_Actual": dias, "Estado": estados,
                         "SubEstado": subs, "ScoreCash": score})


def _kash_meses(rng, base: pd.DataFrame, p_pago: np.ndarray, n_meses: int = 12) -> pd.DataFrame:
    """12 columnas Monto_Mk (pagado en el mes k) y 12 Pago_Mk (1 si Monto_Mk > 0)."""
    n = len(base)
    persist = rng.beta(2, 2, n)                    # cuánto se parece cada mes al anterior
    out = base.copy()
    prev = rng.random(n) < p_pago
    for k in range(1, n_meses + 1):
        cambia = rng.random(n) > persist
        pago = np.where(cambia, rng.random(n) < p_pago, prev)
        monto = np.where(pago, np.round(np.exp(rng.normal(np.log(7700), 0.75, n)), 6), 0.0)
        out[f"Monto_M{k}"] = monto
        prev = pago
    for k in range(1, n_meses + 1):
        out[f"Pago_M{k}"] = (out[f"Monto_M{k}"] > 0).astype(int)
    out["NMesesConPago_12M"] = out[[f"Pago_M{k}" for k in range(1, n_meses + 1)]].sum(axis=1)
    return out


def _kash(carpeta: Path, n: int = 6000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    base = _kash_universo(rng, n)
    p = np.array([_KASH_P_PAGO_SUB[s] * _KASH_SCORE_AJUSTE[sc] for s, sc in zip(base["SubEstado"], base["ScoreCash"])])
    p = np.clip(p * rng.uniform(0.8, 1.2, n), 0.0, 0.98)
    train = _kash_meses(rng, base, p)
    # Ventana de validación (3 meses futuros): el target del backtest.
    val = np.zeros(n, dtype=int)
    shock = rng.normal(0, 0.18, n)                # lo que el pasado no explica: cambios de situación, gestión, azar
    for _ in range(3):
        val += (rng.random(n) < np.clip(0.55 * p + 0.35 * (train["NMesesConPago_12M"] / 12) + shock - 0.08, 0.02, 0.97)).astype(int)
    train["NMesesConPago_VAL"] = val
    train["NMesesConPago_TRAIN"] = train[[f"Pago_M{k}" for k in range(4, 13)]].sum(axis=1)
    train["Formato"] = "PIVOT"
    # Score: mismo universo tres meses después, sin la ventana de validación (es lo que hay que predecir).
    score = _kash_meses(np.random.default_rng(seed + 1), base, p)
    score["DiasAtraso_Actual"] = np.where(score["DiasAtraso_Actual"] > 0, score["DiasAtraso_Actual"] + 90, 0)
    score["Formato"] = "PIVOT"
    cols = ["IdCliente", "CuotaEfectivaRef", "DiasAtraso_Actual", "Estado", "SubEstado", "ScoreCash"] + \
           [f"Monto_M{k}" for k in range(1, 13)] + [f"Pago_M{k}" for k in range(1, 13)]
    train = train[cols + ["NMesesConPago_12M", "NMesesConPago_VAL", "NMesesConPago_TRAIN", "Formato"]]
    score = score[cols + ["NMesesConPago_12M", "Formato"]]
    # Mismo formato que el archivo real: separador `;`, BOM de Excel.
    train.to_csv(carpeta / "BACKTEST_TRAIN.csv", index=False, sep=";", encoding="utf-8-sig")
    score.to_csv(carpeta / "BACKTEST_SCORE.csv", index=False, sep=";", encoding="utf-8-sig")
    meses = pd.date_range("2025-06-01", periods=12, freq="MS").strftime("%Y-%m-%d").tolist()
    return {
        "nombre": "Kash demo",
        "descripcion": "Financiera de cobranzas: backtest a ciegas con train (12 meses de pagos + ventana futura) y score de la misma fecha. Esquema real, datos 100 % sintéticos.",
        "idioma": "es",
        "fuentes": [
            {"nombre": "kash_train", "tipo": "csv", "ruta": "BACKTEST_TRAIN.csv", "opciones": {"sep": ";"}},
            {"nombre": "kash_train_meses", "tipo": "csv", "ruta": "BACKTEST_TRAIN.csv", "opciones": {"sep": ";"}},
            {"nombre": "kash_score", "tipo": "csv", "ruta": "BACKTEST_SCORE.csv", "opciones": {"sep": ";"}},
        ],
        "silver": {
            "kash_train": {"tipos": "auto", "quitar": ["Formato"], "deduplicar": ["IdCliente"],
                           "derivar": {"pago_val": "NMesesConPago_VAL > 0",
                                       "tramo_atraso": "np.where(df['DiasAtraso_Actual'] <= 90, '0-90', np.where(df['DiasAtraso_Actual'] <= 365, '91-365', np.where(df['DiasAtraso_Actual'] <= 730, '366-730', '730+')))"}},
            "kash_train_meses": {"tipos": "auto", "quitar": ["Formato"],
                                 "despivotear": {"id": ["IdCliente", "SubEstado"], "periodo": "mes",
                                                 "grupos": {"monto_pagado": {m: f"Monto_M{k}" for k, m in enumerate(meses, 1)},
                                                            "pago": {m: f"Pago_M{k}" for k, m in enumerate(meses, 1)}}},
                                 "fechas": ["mes"]},
            "kash_score": {"tipos": "auto", "quitar": ["Formato"], "deduplicar": ["IdCliente"],
                           "derivar": {"monto_ref": "np.where(df['CuotaEfectivaRef'] > 0, df['CuotaEfectivaRef'], df[[f'Monto_M{k}' for k in range(1, 13)]].replace(0, np.nan).mean(axis=1).fillna(0))",
                                       "tramo_atraso": "np.where(df['DiasAtraso_Actual'] <= 90, '0-90', np.where(df['DiasAtraso_Actual'] <= 365, '91-365', np.where(df['DiasAtraso_Actual'] <= 730, '366-730', '730+')))"}},
        },
        "calidad": {"criticos_cortan": True, "reglas": [
            {"tabla": "kash_train", "columna": "IdCliente", "tipo": "unico", "critico": True},
            {"tabla": "kash_score", "columna": "IdCliente", "tipo": "unico", "critico": True},
            {"tabla": "kash_train", "columna": "DiasAtraso_Actual", "tipo": "no_negativo", "critico": True},
            {"tabla": "kash_train", "columna": "ScoreCash", "tipo": "valores", "valores": ["A", "B", "C", "D", "E", "F", "F-", "SIN_SCORE"], "critico": True},
            {"tabla": "kash_train", "columna": "NMesesConPago_12M", "tipo": "rango", "min": 0, "max": 12, "critico": True},
            {"tabla": "kash_train", "tipo": "expresion", "expresion": "NMesesConPago_12M == Pago_M1 + Pago_M2 + Pago_M3 + Pago_M4 + Pago_M5 + Pago_M6 + Pago_M7 + Pago_M8 + Pago_M9 + Pago_M10 + Pago_M11 + Pago_M12", "critico": True},
            {"tabla": "kash_score", "columna": "IdCliente", "tipo": "referencia", "a": "kash_train.IdCliente", "critico": False},
            {"tabla": "kash_train_meses", "columna": "monto_pagado", "tipo": "no_negativo", "critico": True},
            {"tabla": "kash_train", "tipo": "filas_min", "valor": 1000, "critico": True},
        ]},
        "modelo": {
            "dimensiones": [{"nombre": "dim_cliente", "desde": "kash_score", "clave": "IdCliente",
                             "atributos": ["Estado", "SubEstado", "ScoreCash", "tramo_atraso"], "scd": 2}],
            "hechos": [{"nombre": "fact_pago_mes", "desde": "kash_train_meses", "fecha": "mes", "claves": {"IdCliente": "dim_cliente"}, "medidas": ["monto_pagado", "pago"]},
                       {"nombre": "fact_cliente_train", "desde": "kash_train", "claves": {"IdCliente": "dim_cliente"}},
                       {"nombre": "fact_cliente_score", "desde": "kash_score", "claves": {"IdCliente": "dim_cliente"}}],
            "calendario": "auto",
        },
        "vistas": {
            "v_pago_mensual": "SELECT c.anio_mes, COUNT(*) clientes, SUM(f.pago) con_pago, ROUND(100.0*SUM(f.pago)/COUNT(*),2) pct_con_pago, ROUND(SUM(f.monto_pagado),0) monto_pagado FROM gold.fact_pago_mes f JOIN gold.dim_calendario c USING (fecha_key) GROUP BY 1 ORDER BY 1",
            "v_tasa_pago_subestado": "SELECT d.SubEstado, COUNT(*) clientes, ROUND(100.0*AVG(CASE WHEN t.pago_val THEN 1 ELSE 0 END),2) tasa_pago_val_pct FROM gold.fact_cliente_train t JOIN gold.dim_cliente d USING (dim_cliente_key) WHERE d.is_current GROUP BY 1 ORDER BY 3 DESC",
        },
        "kpis": [
            {"nombre": "Clientes a scorear", "tabla": "fact_cliente_score", "agregacion": "count", "formato": "#,0"},
            {"nombre": "Tasa de pago histórica %", "tipo": "sql", "sql": "SELECT AVG(CASE WHEN pago_val THEN 1.0 ELSE 0.0 END) FROM gold.fact_cliente_train", "formato": "0.0%"},
            {"nombre": "Monto pagado 12M", "tabla": "fact_pago_mes", "columna": "monto_pagado", "agregacion": "sum", "formato": "#,0", "por": "dim_cliente.SubEstado"},
            {"nombre": "Meses con pago promedio", "tabla": "fact_cliente_train", "columna": "NMesesConPago_12M", "agregacion": "avg", "formato": "#,0.00"},
            {"nombre": "ProbPago promedio %", "tabla": "ml_scores", "columna": "probpago", "agregacion": "avg", "formato": "0.0%", "por": "segmento_propension"},
            {"nombre": "Valor esperado de recupero", "tabla": "ml_scores", "columna": "valor_esperado_recupero", "agregacion": "sum", "formato": "#,0", "por": "estrategia"},
        ],
        "gobernanza": {"dueno": "BI Cobranzas", "pii": [],
                       # Las series mensuales se documentan con un bucle: doce
                       # descripciones escritas a mano serían doce lugares donde
                       # equivocarse al agregar el mes trece.
                       "descripciones": {**{f"Monto_M{k}": f"Monto pagado en el mes {k} de la ventana de 12 meses" for k in range(1, 13)},
                                         **{f"Pago_M{k}": f"1 si hubo algún pago en el mes {k} de la ventana, 0 si no" for k in range(1, 13)},
                                         "IdCliente": "Identificador del socio",
                                         "Estado": "Estado de gestión del socio a la fecha de corte",
                                         "SubEstado": "Subestado dentro del estado de gestión",
                                         "ScoreCash": "Score interno de riesgo del socio",
                                         "CuotaEfectivaRef": "Cuota de referencia usada para dimensionar la deuda",
                                         "DiasAtraso_Actual": "Días de atraso a la fecha de corte",
                                         "NMesesConPago_12M": "Meses con pago en los 12 meses previos al corte",
                                         "NMesesConPago_TRAIN": "Meses con pago en la ventana de entrenamiento",
                                         "mes": "Mes de la serie despivoteada",
                                         "monto_pagado": "Monto pagado en ese mes",
                                         "pago": "1 si hubo pago en ese mes, 0 si no",
                                         "kash_train.NMesesConPago_VAL": "Meses con pago en la ventana futura (3 meses): el target del backtest",
                                         "kash_train.pago_val": "1 si el cliente pagó al menos un mes de la ventana futura",
                                         "kash_train.ScoreCash": "Banda de score interno A (mejor) a F- y SIN_SCORE",
                                         "kash_train.DiasAtraso_Actual": "Días de atraso a la fecha de corte"}},
        "ml": {"tabla": "fact_cliente_train", "tabla_score": "fact_cliente_score", "target": "pago_val", "tipo": "clasificacion",
               "excluir": ["NMesesConPago_VAL", "NMesesConPago_TRAIN", "monto_ref"], "id": "dim_cliente_key",
               "cobranzas": {"monto": "monto_ref", "dias_mora": "DiasAtraso_Actual"}},
        # El backtest se arma una vez por mes con la foto de cierre.
        "frescura": {"cada": "mensual"},
        "reporte": {"titulo": "Kash · ProbPago, backtest a ciegas y cartera priorizada", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Kash"},
        "automatizacion": {"hora": "05:00", "reintentos": 3},
    }


# ---------------------------------------------------------------------------
# Demo «cartera»: la cobranza mensual abierta por estado de gestión, que es la
# forma en que una financiera mira su cartera. Replica el ESQUEMA de un tablero
# real de cobranzas (estados de gestión, monto a cobrar vencido / del mes /
# acumulado, cobrado, socios) con 36 meses de historia — lo mínimo para que un
# backtest de origen móvil con horizonte de seis meses tenga algo que decir.
# Los datos son 100 % sintéticos: cada estado tiene su nivel, su tendencia y su
# estacionalidad propias, generados con semilla fija.
ESTADOS_CARTERA = [
    # (estado, nivel mensual, tendencia mensual, amplitud estacional, ruido, tipos de cliente)
    ("Comercial/Normal", 450_000_000, -0.0015, 0.05, 0.04, [""]),
    ("Cobranza/Mora Temprana", 230_000_000, 0.0020, 0.09, 0.06, [""]),
    ("Cobranza/Negociación", 40_000_000, 0.0035, 0.12, 0.10, ["Puro", "Impuro"]),
    ("Jurídica/Extrajudicial", 28_000_000, -0.0010, 0.15, 0.12, [""]),
    ("Jurídica/Mora Tardía", 22_000_000, -0.0025, 0.18, 0.16, [""]),
    ("Comercial/Suspensión", 5_500_000, 0.0040, 0.22, 0.20, [""]),
    ("Contaduría/Fallecido", 2_300_000, 0.0005, 0.30, 0.35, [""]),
]


def _cartera(carpeta: Path, meses: int = 36, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    periodos = pd.date_range("2023-06-01", periods=meses, freq="MS")
    filas = []
    for estado, nivel, tend, amp, ruido, tipos in ESTADOS_CARTERA:
        for tipo in tipos:
            base = nivel / len(tipos)
            for k, f in enumerate(periodos):
                # Estacionalidad de cobranza uruguaya: enero y julio levantan
                # por el aguinaldo, febrero cae por licencias.
                est = amp * np.sin(2 * np.pi * (f.month - 3) / 12) + (0.06 if f.month in (1, 7) else 0.0)
                cobrado = base * (1 + tend) ** k * (1 + est) * (1 + rng.normal(0, ruido))
                vencido = cobrado * rng.uniform(0.2, 0.5)
                del_mes = cobrado * rng.uniform(0.7, 1.1)
                socios = int(max(1, cobrado / rng.uniform(6_000, 12_000)))
                filas.append((f.date().isoformat(), f.year, f.month, estado, tipo or "N/A",
                              round(del_mes, 2), round(vencido, 2), round(del_mes + vencido, 2),
                              round(max(cobrado, 0), 2), socios, int(socios * rng.uniform(0.6, 0.95))))
    cartera = pd.DataFrame(filas, columns=["fecha_obs", "anio", "mes", "estado", "tipo_cliente",
                                           "monto_a_cobrar_del_mes", "monto_a_cobrar_vencido",
                                           "monto_a_cobrar_acumulado", "total_cobrado",
                                           "socios_a_cobrar", "socios_cobrados"])
    # Defecto inyectado a propósito: dos meses cargados dos veces (el gate lo ve).
    cartera = pd.concat([cartera, cartera.sample(2, random_state=seed)], ignore_index=True)
    cartera.to_csv(carpeta / "cartera_mensual.csv", index=False, sep=";", decimal=",")
    return {
        "nombre": "Cartera demo",
        "descripcion": "Cobranza mensual por estado de gestión: 36 meses, 7 estados (uno abierto por tipo de "
                       "cliente). Proyección a 6 meses con backtest de origen móvil y banda de desvío por "
                       "segmento. Datos 100 % sintéticos.",
        "idioma": "es",
        "fuentes": [{"nombre": "cartera", "tipo": "csv", "ruta": "cartera_mensual.csv",
                     "opciones": {"sep": ";", "decimal": ","}}],
        "silver": {"cartera": {"tipos": "auto", "fechas": ["fecha_obs"],
                               "deduplicar": ["fecha_obs", "estado", "tipo_cliente"],
                               "derivar": {"pct_cobrado": "total_cobrado / monto_a_cobrar_acumulado * 100",
                                           "area_gestion": "df['estado'].str.split('/').str[0]"}}},
        "calidad": {"minimo": 80, "reglas": [
            {"tabla": "cartera", "columna": "total_cobrado", "tipo": "no_negativo", "critico": True},
            {"tabla": "cartera", "columna": "estado", "tipo": "no_nulo", "critico": True},
            {"tabla": "cartera", "columna": "pct_cobrado", "tipo": "rango", "min": 0, "max": 300, "critico": False},
        ]},
        "modelo": {
            "dimensiones": [{"nombre": "dim_estado", "desde": "cartera", "clave": "estado",
                             "atributos": ["area_gestion"], "scd": 1}],
            "hechos": [{"nombre": "fact_cartera", "desde": "cartera", "fecha": "fecha_obs",
                        "claves": {"estado": "dim_estado"},
                        "medidas": ["total_cobrado", "monto_a_cobrar_vencido", "monto_a_cobrar_acumulado",
                                    "socios_a_cobrar", "socios_cobrados"],
                        }],
            "calendario": "auto",
        },
        "vistas": {"v_cobranza_mes_estado": "SELECT c.anio_mes, d.estado, SUM(f.total_cobrado) cobrado, "
                                            "SUM(f.monto_a_cobrar_vencido) vencido FROM gold.fact_cartera f "
                                            "JOIN gold.dim_calendario c USING (fecha_key) "
                                            "JOIN gold.dim_estado d USING (dim_estado_key) GROUP BY 1,2 ORDER BY 1,2"},
        "kpis": [
            {"nombre": "Total cobrado", "tabla": "fact_cartera", "columna": "total_cobrado", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Monto vencido", "tabla": "fact_cartera", "columna": "monto_a_cobrar_vencido", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Socios cobrados", "tabla": "fact_cartera", "columna": "socios_cobrados", "agregacion": "sum", "formato": "#,0"},
        ],
        "gobernanza": {"dueno": "Coordinación de BI · Cobranzas",
                       "descripciones": {
                           "fecha_obs": "Fecha de observación: primer día del mes al que corresponde el corte",
                           "anio": "Año del corte", "mes": "Mes del corte (1-12)",
                           "estado": "Estado de gestión de la cartera (área / situación del socio)",
                           "tipo_cliente": "Subclasificación del socio dentro del estado; «N/A» cuando el estado no la usa",
                           "monto_a_cobrar_del_mes": "Cuotas que vencen en el mes, sin arrastre",
                           "monto_a_cobrar_vencido": "Saldo vencido pendiente al cierre del mes",
                           "monto_a_cobrar_acumulado": "Del mes más el vencido: el total exigible",
                           "total_cobrado": "Cobranza del mes por estado de gestión",
                           "socios_a_cobrar": "Socios con algo exigible en el mes",
                           "socios_cobrados": "Socios que pagaron algo en el mes"}},
        # Proyección a seis meses (30/60/90/120/150/180 días), un modelo por
        # estado elegido por backtest, con la banda de desvío que ese modelo
        # tuvo en los cortes anteriores.
        # El set sale del almacén con SQL para recuperar el nombre del estado
        # (en el hecho quedó como clave subrogada): se proyecta un modelo por
        # estado × tipo de cliente, más el total.
        "ml": {"tipo": "serie",
               "sql": "SELECT f.fecha_key, d.estado, f.tipo_cliente, f.total_cobrado "
                      "FROM gold.fact_cartera f JOIN gold.dim_estado d USING (dim_estado_key)",
               "fecha": "fecha_key", "valor": "total_cobrado",
               "frecuencia": "mensual", "horizonte": 6, "origenes": 7, "banda": 0.8,
               "segmento": ["estado", "tipo_cliente"], "minimo_periodos": 24},
        "frescura": {"cada": "mensual"},
        "reporte": {"titulo": "Cartera · cobranza por estado", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Cartera"},
    }



# ---------------------------------------------------------------------------
# Cooperativa láctea (demo pensada para presentarle el producto a Conaprole)
#
# ADVERTENCIA QUE NO SE SACA: los datos son 100 % SINTÉTICOS, generados acá con
# semilla fija. NO provienen de Conaprole ni de ninguna otra empresa, y las
# cifras no representan su operación. La demo sirve para mostrar QUÉ hace el
# producto sobre el proceso de una industria láctea, no para decir nada sobre
# el negocio de nadie. Si en una reunión alguien pregunta "¿de dónde salieron
# estos números?", la respuesta es "los generamos nosotros para la demo".
#
# Por qué la REMISIÓN y no otra cosa: es el proceso que cruza todas las áreas
# que un relevamiento tiene que entrevistar —productores, laboratorio de
# calidad, logística de recolección, plantas y comercial— así que una sola
# demo toca a todos los interlocutores. Y tiene las tres cosas que el motor
# muestra bien: calidad de dato con reglas de negocio reales (un recuento de
# células somáticas imposible no es un outlier, es un dato mal cargado),
# estacionalidad fuerte y liquidación con fórmula.
#
# Estacionalidad del hemisferio sur: pico de producción en primavera
# (octubre-diciembre, cuando la pastura rinde) y piso en invierno
# (junio-julio). Es al revés que las demos del hemisferio norte, y es lo que
# hace que una proyección "de manual" falle si no la modela.
SECCIONALES = [
    # (seccional, productores, litros/día por tambo, tendencia anual, sesgo de calidad)
    ("San José",      110, 2_950, -0.012,  0.00),
    ("Florida",        86, 3_400, -0.008,  0.03),
    ("Colonia",        74, 3_150, -0.015, -0.02),
    ("Canelones",      68, 2_100, -0.028, -0.05),   # tambos chicos, más presión
    ("Soriano",        42, 4_200,  0.006,  0.04),
    ("Durazno",        26, 2_600, -0.010,  0.01),
]
TIPOS_TAMBO = ["Familiar", "Empresarial", "Mixto"]


def _conaprole(carpeta: Path, meses: int = 36, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    periodos = pd.date_range("2023-01-01", periods=meses, freq="MS")

    # --- Padrón de productores ------------------------------------------
    prods = []
    pid = 1000
    for seccional, cantidad, litros_dia, tend, sesgo in SECCIONALES:
        for _ in range(cantidad):
            pid += 1
            tipo = rng.choice(TIPOS_TAMBO, p=[0.55, 0.20, 0.25])
            escala = {"Familiar": 0.55, "Mixto": 1.0, "Empresarial": 2.3}[tipo]
            vacas = int(max(18, rng.normal(litros_dia * escala / 19, 14)))
            prods.append((pid, seccional, tipo, vacas,
                          int(vacas * rng.uniform(1.1, 2.4)),          # hectáreas
                          int(rng.integers(1968, 2021))))              # año de ingreso
    productores = pd.DataFrame(prods, columns=["id_productor", "seccional", "tipo_tambo",
                                               "vacas_masa", "hectareas", "anio_ingreso"])
    # Defecto a propósito: seis productores sin seccional cargada. Es el caso
    # real de un alta hecha a mano que nunca se completó, y hace que toda la
    # zona quede mal atribuida en el tablero sin que nadie lo note.
    productores.loc[productores.sample(6, random_state=seed).index, "seccional"] = ""

    # --- Remisión mensual por productor ---------------------------------
    filas = []
    litros_base = dict((s[0], s[2]) for s in SECCIONALES)
    tend_sec = dict((s[0], s[3]) for s in SECCIONALES)
    sesgo_sec = dict((s[0], s[4]) for s in SECCIONALES)
    for _, pr in productores.iterrows():
        sec = pr["seccional"] or "San José"
        escala = {"Familiar": 0.55, "Mixto": 1.0, "Empresarial": 2.3}[pr["tipo_tambo"]]
        base_mes = litros_base[sec] * escala * 30 / 1000.0                  # miles de litros/mes
        propio = rng.normal(1.0, 0.13)
        for k, f in enumerate(periodos):
            # Zafra: pico en primavera (mes 11), piso en invierno (mes 6).
            zafra = 1 + 0.22 * np.sin(2 * np.pi * (f.month - 8) / 12)
            deriva = (1 + tend_sec[sec]) ** (k / 12)
            litros = base_mes * propio * zafra * deriva * (1 + rng.normal(0, 0.05))
            if litros <= 0:
                continue
            # Sólidos: la grasa sube en invierno (menos volumen, más concentrado).
            grasa = np.clip(rng.normal(3.72 - 0.28 * (zafra - 1) * 4, 0.16), 2.8, 5.2)
            proteina = np.clip(rng.normal(3.28 - 0.14 * (zafra - 1) * 4, 0.11), 2.6, 4.2)
            # Calidad: RCS (células somáticas, miles/ml) y UFC (bacteriología).
            # Empeoran en verano por calor y en tambos chicos.
            calor = 1 + 0.18 * np.sin(2 * np.pi * (f.month - 11) / 12)
            rcs = np.clip(rng.lognormal(np.log(255 * calor * (1 - sesgo_sec[sec])), 0.34), 60, 1_900)
            ufc = np.clip(rng.lognormal(np.log(28 * calor), 0.62), 3, 900)
            temp = np.clip(rng.normal(3.6, 0.7), 1.0, 8.5)
            filas.append((f.date().isoformat(), int(pr["id_productor"]), round(litros, 1),
                          round(grasa, 2), round(proteina, 2), round(rcs, 0), round(ufc, 0), round(temp, 1)))
    rem = pd.DataFrame(filas, columns=["mes", "id_productor", "miles_litros", "grasa_pct",
                                       "proteina_pct", "rcs_miles_ml", "ufc_miles_ml", "temp_recibo_c"])

    # Defectos inyectados a propósito, los tres que aparecen de verdad en una
    # cadena de laboratorio + recolección:
    #   1. un lote de recuentos imposibles (coma corrida en la carga),
    #   2. temperaturas fuera de la cadena de frío,
    #   3. un mes cargado dos veces.
    idx = rem.sample(40, random_state=seed).index
    rem.loc[idx, "rcs_miles_ml"] = rem.loc[idx, "rcs_miles_ml"] * 10
    idx2 = rem.sample(25, random_state=seed + 1).index
    rem.loc[idx2, "temp_recibo_c"] = np.round(rng.uniform(9.0, 14.0, size=len(idx2)), 1)
    dup = rem[rem["mes"] == periodos[18].date().isoformat()]
    rem = pd.concat([rem, dup], ignore_index=True)

    productores.to_csv(carpeta / "productores.csv", index=False)
    rem.to_csv(carpeta / "remision_mensual.csv", index=False, sep=";", decimal=",")

    return {
        "nombre": "Conaprole · demo",
        "descripcion": (
            "DEMO CON DATOS 100 % SINTÉTICOS — no provienen de Conaprole ni de ninguna empresa. "
            "Remisión de leche de una cooperativa láctea: 406 productores en 6 seccionales, 36 meses, "
            "calidad de laboratorio (células somáticas, bacteriología, cadena de frío), liquidación por "
            "kilos de sólidos con bonificación por calidad, y proyección de la zafra a 3 meses con "
            "backtest de origen móvil y banda de desvío por seccional."),
        "idioma": "es",
        "fuentes": [
            {"nombre": "productores", "tipo": "csv", "ruta": "productores.csv"},
            {"nombre": "remision", "tipo": "csv", "ruta": "remision_mensual.csv",
             "opciones": {"sep": ";", "decimal": ","}},
        ],
        "silver": {
            "productores": {"tipos": "auto", "deduplicar": ["id_productor"],
                            "derivar": {
                                # La escala del tambo es la variable que más se
                                # usa para segmentar en una cooperativa: define
                                # con quién se habla y qué se le puede ofrecer.
                                "escala_tambo": "np.where(df['vacas_masa'] < 60, 'Chico (<60)', "
                                                "np.where(df['vacas_masa'] < 150, 'Mediano (60-150)', 'Grande (150+)'))",
                                "antiguedad_anios": "2026 - df['anio_ingreso']"}},
            "remision": {"tipos": "auto", "fechas": ["mes"],
                         # El mismo productor no puede tener dos remisiones del
                         # mismo mes: si aparecen, es recarga del archivo.
                         "deduplicar": ["mes", "id_productor"],
                         "derivar": {
                             "kg_solidos": "df['miles_litros'] * 1000 * (df['grasa_pct'] + df['proteina_pct']) / 100",
                             # Bandas de bonificación por calidad. Es la regla
                             # que hay que confirmar con el cliente en el
                             # relevamiento: acá va una versión de ejemplo.
                             "categoria_calidad": "np.where((df['rcs_miles_ml'] <= 200) & (df['ufc_miles_ml'] <= 30), 'A', "
                                                  "np.where((df['rcs_miles_ml'] <= 400) & (df['ufc_miles_ml'] <= 80), 'B', "
                                                  "np.where(df['rcs_miles_ml'] <= 700, 'C', 'Fuera de banda')))",
                             "bonificacion_pct": "np.select("
                                                 "[df['rcs_miles_ml'] <= 200, df['rcs_miles_ml'] <= 400, df['rcs_miles_ml'] <= 700], "
                                                 "[6.0, 2.5, 0.0], default=-4.0)",
                             "fuera_cadena_frio": "df['temp_recibo_c'] > 6.0"}},
        },
        # `minimo: 70` y no 80: la demo TIENE defectos inyectados a propósito y
        # saca 75. Con 80 el gate corta en la etapa 4 y no se llega a mostrar
        # el modelo, la proyección ni el .pbit. Subirlo a 80 en vivo, correr de
        # nuevo y ver el pipeline frenarse es, de hecho, la mejor forma de
        # explicar para qué sirve el gate: la regla es tuya, el corte es real.
        "calidad": {"minimo": 70, "criticos_cortan": True, "reglas": [
            {"tabla": "productores", "columna": "id_productor", "tipo": "unico", "critico": True},
            {"tabla": "productores", "columna": "seccional", "tipo": "no_nulo", "critico": False},
            {"tabla": "productores", "columna": "vacas_masa", "tipo": "positivo", "critico": True},
            {"tabla": "remision", "columna": "id_productor", "tipo": "referencia", "a": "productores.id_productor", "critico": True},
            {"tabla": "remision", "columna": "miles_litros", "tipo": "positivo", "critico": True},
            # Un recuento de células somáticas por encima de 1.500 mil/ml no es
            # un tambo con problemas: es un dato mal cargado. El límite legal de
            # aptitud está muy por debajo, y una vaca que lo supere de verdad no
            # está en producción.
            {"tabla": "remision", "columna": "rcs_miles_ml", "tipo": "rango", "min": 20, "max": 1500, "critico": False},
            {"tabla": "remision", "columna": "grasa_pct", "tipo": "rango", "min": 2.5, "max": 6.0, "critico": True},
            {"tabla": "remision", "columna": "proteina_pct", "tipo": "rango", "min": 2.4, "max": 4.5, "critico": True},
            # Cadena de frío: la leche se recibe entre 2 y 6 °C.
            {"tabla": "remision", "columna": "temp_recibo_c", "tipo": "rango", "min": 1.0, "max": 6.0, "critico": False},
            {"tabla": "remision", "columna": "categoria_calidad", "tipo": "valores",
             "valores": ["A", "B", "C", "Fuera de banda"], "critico": False},
        ]},
        "modelo": {
            "dimensiones": [{"nombre": "dim_productor", "desde": "productores", "clave": "id_productor",
                             "atributos": ["seccional", "tipo_tambo", "escala_tambo", "vacas_masa",
                                           "hectareas", "antiguedad_anios"], "scd": 2}],
            "hechos": [{"nombre": "fact_remision", "desde": "remision", "fecha": "mes",
                        "claves": {"id_productor": "dim_productor"},
                        "medidas": ["miles_litros", "kg_solidos", "bonificacion_pct",
                                    "rcs_miles_ml", "ufc_miles_ml"]}],
            "calendario": "auto",
        },
        "vistas": {
            "v_remision_mes_seccional":
                "SELECT c.anio_mes, d.seccional, SUM(f.miles_litros) miles_litros, "
                "SUM(f.kg_solidos) kg_solidos, COUNT(DISTINCT f.dim_productor_key) productores "
                "FROM gold.fact_remision f JOIN gold.dim_calendario c USING (fecha_key) "
                "JOIN gold.dim_productor d USING (dim_productor_key) GROUP BY 1,2 ORDER BY 1,2",
            "v_calidad_por_escala":
                "SELECT d.escala_tambo, ROUND(AVG(f.rcs_miles_ml),0) rcs_prom, "
                "ROUND(AVG(f.ufc_miles_ml),0) ufc_prom, ROUND(AVG(f.bonificacion_pct),2) bonif_prom_pct, "
                "COUNT(DISTINCT d.dim_productor_key) productores "
                "FROM gold.fact_remision f JOIN gold.dim_productor d USING (dim_productor_key) "
                "WHERE d.is_current GROUP BY 1 ORDER BY 4 DESC",
        },
        "kpis": [
            {"nombre": "Miles de litros remitidos", "tabla": "fact_remision", "columna": "miles_litros", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Kilos de sólidos", "tabla": "fact_remision", "columna": "kg_solidos", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Productores activos", "tabla": "fact_remision", "columna": "dim_productor_key", "agregacion": "count_distinct", "formato": "#,0"},
            {"nombre": "RCS promedio (miles/ml)", "tabla": "fact_remision", "columna": "rcs_miles_ml", "agregacion": "avg", "formato": "#,0"},
            {"nombre": "Bonificación promedio %", "tabla": "fact_remision", "columna": "bonificacion_pct", "agregacion": "avg", "formato": "0.0"},
            # Sobre gold, no sobre silver: el almacén sólo publica gold, y una
            # consulta a `silver.remision` deja el KPI en «—». La banda A se
            # recalcula acá con los umbrales, porque la categoría es texto y no
            # viaja como medida del hecho.
            {"nombre": "Remisión en categoría A %", "tipo": "sql",
             "sql": "SELECT AVG(CASE WHEN rcs_miles_ml <= 200 AND ufc_miles_ml <= 30 THEN 1.0 ELSE 0.0 END) "
                    "FROM gold.fact_remision", "formato": "0.0%"},
        ],
        "gobernanza": {
            "dueno": "Analista de Negocio / Datos · proyecto Conaprole",
            "descripciones": {
                "id_productor": "Número de productor remitente en el padrón de la cooperativa",
                "seccional": "Seccional de recolección a la que pertenece el tambo",
                "tipo_tambo": "Forma de explotación declarada: Familiar, Empresarial o Mixto",
                "vacas_masa": "Vacas en ordeñe (masa) declaradas por el productor",
                "hectareas": "Superficie afectada al tambo",
                "anio_ingreso": "Año de ingreso del productor a la cooperativa",
                "escala_tambo": "Segmento por tamaño de rodeo, derivado de vacas_masa",
                "antiguedad_anios": "Años desde el ingreso a la cooperativa",
                "mes": "Mes de remisión (primer día del mes)",
                "miles_litros": "Litros remitidos en el mes, en miles",
                "grasa_pct": "Materia grasa, % sobre volumen (promedio ponderado del mes)",
                "proteina_pct": "Proteína, % sobre volumen (promedio ponderado del mes)",
                "rcs_miles_ml": "Recuento de células somáticas, en miles por ml. Indicador de sanidad de ubre",
                "ufc_miles_ml": "Unidades formadoras de colonia, en miles por ml. Indicador de higiene de ordeñe",
                "temp_recibo_c": "Temperatura de la leche al recibo, en °C. La cadena de frío es 2 a 6 °C",
                "kg_solidos": "Kilos de sólidos útiles (grasa + proteína): la base real de la liquidación",
                "categoria_calidad": "Banda de calidad A/B/C según células somáticas y bacteriología",
                "bonificacion_pct": "Bonificación (o castigo) sobre el precio, en %, según la banda de calidad",
                "fuera_cadena_frio": "Verdadero si la leche se recibió por encima de 6 °C"}},
        # Proyección de la zafra: tres meses por seccional, más el total.
        # Cada seccional elige su modelo por backtest y se reporta contra la
        # estacional ingenua — con esta estacionalidad, un modelo que no la
        # capture pierde contra repetir el año anterior, y eso hay que poder
        # mostrarlo en pantalla.
        "ml": {"tipo": "serie",
               "sql": "SELECT f.fecha_key, d.seccional, f.miles_litros "
                      "FROM gold.fact_remision f JOIN gold.dim_productor d USING (dim_productor_key)",
               "fecha": "fecha_key", "valor": "miles_litros",
               "frecuencia": "mensual", "horizonte": 3, "origenes": 6, "banda": 0.8,
               "segmento": ["seccional"], "minimo_periodos": 24},
        "frescura": {"cada": "mensual"},
        "reporte": {"titulo": "Conaprole · remisión, calidad y proyección de zafra", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Conaprole"},
        "automatizacion": {"hora": "06:00", "reintentos": 3},
    }


def crear(nombre: str, carpeta: Path) -> Path:
    if nombre not in NOMBRES:
        raise ValueError(f"demo desconocida; válidas: {NOMBRES}")
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    spec = {"cobranzas": _cobranzas, "ventas": _ventas, "kash": _kash, "cartera": _cartera,
        "conaprole": _conaprole}[nombre](carpeta)
    spec = proyecto.normalizar(spec)
    return proyecto.guardar(spec, carpeta / "proyecto.yaml")
