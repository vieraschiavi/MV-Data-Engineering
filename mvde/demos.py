# © 2026 Martín Viera. Todos los derechos reservados.
"""Demos incluidas, 100 % sintéticas y con semilla fija.

  cobranzas: una financiera — clientes, cuotas y pagos, con mora y default.
  ventas:    consumo masivo — productos, sucursales y ventas diarias.

`crear(nombre, carpeta)` escribe los CSV y el `proyecto.yaml` listos para
`python -m mvde correr`. Cada demo ejercita cosas distintas del motor.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import proyecto

NOMBRES = ["cobranzas", "ventas"]


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
                                         "clientes.default_proximo_mes": "1 si no paga la cuota del mes siguiente", "cuotas.monto_pagado": "Pagado en el mes (moneda local)"}},
        "ml": {"sql": "SELECT r.default_proximo_mes, d.edad, d.educacion, d.sucursal, d.limite_credito, d.sexo, "
                      "SUM(CASE WHEN f.en_mora THEN 1 ELSE 0 END) meses_en_mora, MAX(f.meses_atraso) max_atraso, "
                      "SUM(f.monto_pagado)/NULLIF(SUM(f.monto_cuota),0) pct_pagado, "
                      "MAX(CASE WHEN f.fecha_key >= 20251001 THEN f.meses_atraso ELSE 0 END) atraso_ult_trim "
                      "FROM gold.fact_cliente_riesgo r JOIN gold.dim_cliente d USING (dim_cliente_key) "
                      "JOIN gold.fact_cuota f USING (dim_cliente_key) GROUP BY 1,2,3,4,5,6",
               "target": "default_proximo_mes", "tipo": "clasificacion"},
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
        "gobernanza": {"dueno": "BI Comercial", "descripciones": {"ventas.importe": "Unidades × precio unitario con descuento"}},
        "ml": {"tabla": "fact_venta", "target": "importe", "tipo": "regresion", "fecha": None, "excluir": ["precio_unitario"]},
        "reporte": {"titulo": "Ventas · tablero comercial", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Ventas"},
    }


def crear(nombre: str, carpeta: Path) -> Path:
    if nombre not in NOMBRES:
        raise ValueError(f"demo desconocida; válidas: {NOMBRES}")
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    spec = _cobranzas(carpeta) if nombre == "cobranzas" else _ventas(carpeta)
    spec = proyecto.normalizar(spec)
    return proyecto.guardar(spec, carpeta / "proyecto.yaml")
