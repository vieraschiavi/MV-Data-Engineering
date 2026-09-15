# © 2026 Martín Viera. Todos los derechos reservados.
"""Demo de campañas: retail sintético armado para que el motor tenga algo que encontrar.

Los cuatro comportamientos están inyectados A PROPÓSITO y son verdaderos por
construcción, así los tests pueden afirmarlos en vez de esperar que aparezcan:

  1. **Precios Redondos** — 5 ediciones de la misma campaña, así hay «anterior»
     y «anterior anterior». La de 2025-05 lleva el **precio inflado** en el
     blackout (sube 14 % y después «baja» 25 %: el descuento real es mucho menor
     que el aparente). La de 2025-09 dura 10 días en vez de 14 —para que
     comparar totales dé mal y por día dé bien— y tiene **quiebre de stock** en
     dos SKU.
  2. **Vuelta a Clases** — 2 ediciones, 21 días, incremental sano y sostenido:
     el caso de control contra el que se leen los otros tres.
  3. **Semana del Cliente** — 7 días con un pico grande y una caída larga
     después: **adelanta venta** en vez de crearla, y el incremental de la
     ventana completa da negativo.
  4. **Black Friday** — 5 días con 45 % de descuento sobre un costo del 62 %
     del precio de lista: **vende más unidades y deja menos margen en plata**.

Y los clientes que entran POR una campaña recompran menos que los que entran
solos: es lo que hace que la curva de cohortes por origen se separe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Cada campaña con su comportamiento. Los tres parámetros se eligieron para que
# la demo se parezca a una campaña de verdad, y no para que los números queden
# lindos:
#
#   `trafico`     cuánto sube el total de operaciones del comercio. Una campaña
#                 mueve la aguja del tráfico, no la triplica: 1,25–1,40.
#   `share`       qué proporción de las operaciones cae en los SKU de la campaña
#                 durante la ventana. Arriba de su participación natural
#                 (SKU en campaña / 40) pero dejándole aire al resto: si la
#                 campaña se come todo, el grupo de control deja de ser control
#                 y el dif-en-dif se rompe. Eso ya pasó en esta demo: con un
#                 share de 0,80 el control caía 65 % y el lift corregido daba
#                 1451 %.
#   `post_share`  la participación de esos SKU en los 28 días siguientes. Abajo
#                 de la natural = la gente se abasteció, o sea adelantamiento —
#                 y cae sólo sobre los SKU promocionados, que es donde pasa de
#                 verdad, no sobre todo el comercio.
CAMPANAS = [
    # campana, edicion, desde, hasta, trafico, share, post_share, desc
    ("Precios Redondos", "2024-05", "2024-05-06", "2024-05-19", 1.30, 0.60, 0.43, 0.20),
    ("Precios Redondos", "2024-09", "2024-09-02", "2024-09-15", 1.30, 0.61, 0.43, 0.20),
    ("Precios Redondos", "2025-01", "2025-01-06", "2025-01-19", 1.32, 0.62, 0.42, 0.22),
    ("Precios Redondos", "2025-05", "2025-05-05", "2025-05-18", 1.30, 0.60, 0.43, 0.25),
    ("Precios Redondos", "2025-09", "2025-09-01", "2025-09-10", 1.34, 0.62, 0.43, 0.22),
    ("Vuelta a Clases",  "2024",    "2024-02-12", "2024-03-03", 1.26, 0.43, 0.29, 0.15),
    ("Vuelta a Clases",  "2025",    "2025-02-10", "2025-03-02", 1.28, 0.44, 0.29, 0.15),
    # 7 días de pico y 28 de resaca SOBRE LOS SKU PROMOCIONADOS: el incremental
    # de la ventana completa da negativo y el veredicto tiene que decir «adelantó».
    ("Semana del Cliente", "2024", "2024-10-07", "2024-10-13", 1.35, 0.70, 0.30, 0.30),
    ("Semana del Cliente", "2025", "2025-10-06", "2025-10-12", 1.35, 0.70, 0.31, 0.30),
    # 45 % de descuento contra un costo del 62 %: cada unidad deja margen negativo.
    ("Black Friday", "2024", "2024-11-25", "2024-11-29", 1.40, 0.56, 0.38, 0.45),
    ("Black Friday", "2025", "2025-11-24", "2025-11-28", 1.42, 0.57, 0.38, 0.45),
]
# La edición donde el precio se sube antes de bajarlo.
INFLADO = ("Precios Redondos", "2025-05")
SUBA_PREVIA = 0.14
# La edición con quiebre de stock, y en qué SKU.
QUIEBRE = ("Precios Redondos", "2025-09")
SKUS_QUIEBRE = ("SKU007", "SKU013")
# Costo como fracción del precio de lista: deja ~38 % de margen a precio pleno.
COSTO_SOBRE_LISTA = 0.62


def _catalogo(rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = 40
    lista = np.round(rng.uniform(150, 2400, n) / 10) * 10
    productos = pd.DataFrame({
        "sku": [f"SKU{i:03d}" for i in range(1, n + 1)],
        "producto": [f"Producto {i:02d}" for i in range(1, n + 1)],
        "categoria": rng.choice(["Bebidas", "Almacén", "Limpieza", "Perfumería", "Bazar"], n),
        "precio_lista": lista,
        "costo_unitario": np.round(lista * COSTO_SOBRE_LISTA, 2),
    })
    m = 260
    clientes = pd.DataFrame({
        "id_cliente": [f"C{i:04d}" for i in range(1, m + 1)],
        "ciudad": rng.choice(["Montevideo", "Canelones", "Maldonado", "Salto", "Colonia"], m,
                             p=[0.45, 0.2, 0.15, 0.1, 0.1]),
        "region": None,
    })
    clientes["region"] = clientes["ciudad"].map(
        {"Montevideo": "Sur", "Canelones": "Sur", "Maldonado": "Este", "Salto": "Litoral", "Colonia": "Litoral"})
    return productos, clientes


def _skus_de(campana: str, productos: pd.DataFrame, rng) -> list[str]:
    """Qué SKU entran en cada campaña. El surtido se solapa pero no coincide:
    así el like-for-like tiene sentido y el efecto mezcla no es cero."""
    cuantos = {"Precios Redondos": 18, "Vuelta a Clases": 12, "Semana del Cliente": 22, "Black Friday": 16}[campana]
    return sorted(rng.choice(productos["sku"].to_numpy(), cuantos, replace=False).tolist())


def generar(carpeta: Path, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    productos, clientes = _catalogo(rng)
    precio = dict(zip(productos["sku"], productos["precio_lista"]))
    costo = dict(zip(productos["sku"], productos["costo_unitario"]))
    region = dict(zip(clientes["id_cliente"], clientes["region"]))

    cal = pd.DataFrame(CAMPANAS, columns=["campana", "edicion", "desde", "hasta",
                                          "trafico", "share", "post_share", "desc"])
    cal["desde"] = pd.to_datetime(cal["desde"])
    cal["hasta"] = pd.to_datetime(cal["hasta"])

    # El surtido por campaña se sortea una vez y se reusa entre ediciones, con
    # una rotación chica por edición para que el surtido no sea idéntico.
    base_skus = {c: _skus_de(c, productos, rng) for c in cal["campana"].unique()}
    alcance = []
    for _, e in cal.iterrows():
        s = list(base_skus[e["campana"]])
        fuera = [x for x in productos["sku"] if x not in s]
        rotan = rng.choice(len(s), 2, replace=False)
        for k, idx in enumerate(rotan):
            s[idx] = fuera[k]
        alcance += [{"campana": e["campana"], "edicion": e["edicion"], "sku": x} for x in sorted(set(s))]
    alcance = pd.DataFrame(alcance)

    dias = pd.date_range("2024-01-01", "2025-12-31", freq="D")

    # --- estado por cliente: cuándo entra y cuánto recompra --------------
    alta = {}
    for i, cid in enumerate(clientes["id_cliente"]):
        # 60 % están desde el arranque; el resto entra escalonado a lo largo de
        # los dos años, y una parte justo dentro de una campaña.
        if i < int(len(clientes) * 0.6):
            alta[cid] = dias[0]
        else:
            alta[cid] = dias[int(rng.integers(30, len(dias) - 60))]
    en_campana = {}
    for cid, f in alta.items():
        dentro = ((cal["desde"] <= f) & (cal["hasta"] >= f)).any()
        en_campana[cid] = bool(dentro)
    # El que entra por una campaña recompra menos: ése es el hallazgo de la
    # curva de cohortes por origen, y acá queda inyectado a propósito.
    actividad = {cid: float(rng.uniform(0.25, 1.0) * (0.45 if en_campana[cid] else 1.0))
                 for cid in clientes["id_cliente"]}

    def campana_de(f):
        m = cal[(cal["desde"] <= f) & (cal["hasta"] >= f)]
        return None if m.empty else m.iloc[0]

    def resaca_de(f):
        """Si el día cae en los 28 posteriores a una edición, devuelve esa
        edición: sus SKU van a estar por debajo de su participación natural."""
        for _, e in cal.iterrows():
            if e["hasta"] < f <= e["hasta"] + pd.Timedelta(days=28):
                return e
        return None

    def inflado_en(f):
        """¿El día cae en el blackout (7 días previos) de la edición inflada?"""
        e = cal[(cal["campana"] == INFLADO[0]) & (cal["edicion"] == INFLADO[1])].iloc[0]
        return e["desde"] - pd.Timedelta(days=7) <= f < e["desde"]

    skus_ed = {(e["campana"], e["edicion"]): set(alcance[(alcance["campana"] == e["campana"])
                                                         & (alcance["edicion"] == e["edicion"])]["sku"])
               for _, e in cal.iterrows()}
    todos = productos["sku"].to_numpy()
    skus_inflados = skus_ed[INFLADO]

    filas = []
    for f in dias:
        estacional = 1 + 0.18 * np.sin(2 * np.pi * (f.dayofyear / 365.0))
        finde = 1.25 if f.dayofweek >= 5 else 1.0
        e = campana_de(f)
        resaca = None if e is not None else resaca_de(f)
        trafico = float(e["trafico"]) if e is not None else 1.0
        n = int(max(4, rng.poisson(26 * estacional * finde * trafico)))
        vivos = [c for c in clientes["id_cliente"] if alta[c] <= f]
        if not vivos:
            continue
        pesos = np.array([actividad[c] for c in vivos], dtype=float)
        pesos = pesos / pesos.sum()
        compradores = rng.choice(vivos, size=min(n, len(vivos)), replace=False, p=pesos)
        # Qué SKU están «en foco» hoy y con qué participación.
        if e is not None:
            foco, share = sorted(skus_ed[(e["campana"], e["edicion"])]), float(e["share"])
            desc_foco = float(e["desc"])
        elif resaca is not None:
            foco, share = sorted(skus_ed[(resaca["campana"], resaca["edicion"])]), float(resaca["post_share"])
            desc_foco = 0.0
        else:
            foco, share, desc_foco = [], 0.0, 0.0
        fuera = [x for x in todos if x not in set(foco)] if foco else list(todos)
        for cid in compradores:
            if foco and rng.random() < share:
                sku, desc = str(rng.choice(foco)), desc_foco
            else:
                sku = str(rng.choice(fuera if fuera else todos))
                desc = float(rng.choice([0.0, 0.0, 0.0, 0.05, 0.10]))
            # Quiebre de stock: el SKU no se vende en la segunda mitad de esa edición.
            if e is not None and (e["campana"], e["edicion"]) == QUIEBRE and sku in SKUS_QUIEBRE:
                if f >= e["desde"] + pd.Timedelta(days=5):
                    continue
            p_lista = float(precio[sku])
            if inflado_en(f) and sku in skus_inflados:
                p_lista = round(p_lista * (1 + SUBA_PREVIA), 2)   # la suba antes de la «baja»
            u = int(max(1, rng.poisson(2.2 if desc > 0.15 else 1.5)))
            p_unit = round(p_lista * (1 - desc), 2)
            filas.append((f, cid, sku, region[cid], u, p_unit,
                          round(u * p_unit, 2), round(u * float(costo[sku]), 2), round(desc, 3)))

    ventas = pd.DataFrame(filas, columns=["fecha", "id_cliente", "sku", "region", "unidades",
                                          "precio_unitario", "importe", "costo", "descuento"])

    # --- stock diario: lleno salvo el quiebre inyectado ------------------
    e_q = cal[(cal["campana"] == QUIEBRE[0]) & (cal["edicion"] == QUIEBRE[1])].iloc[0]
    st = []
    for sku in productos["sku"]:
        base = int(rng.integers(60, 400))
        for f in dias:
            disp = base + int(rng.integers(-20, 20))
            if sku in SKUS_QUIEBRE and e_q["desde"] + pd.Timedelta(days=5) <= f <= e_q["hasta"]:
                disp = 0
            st.append((sku, f, max(0, disp)))
    stock = pd.DataFrame(st, columns=["sku", "fecha", "unidades_disponibles"])

    cal_out = cal[["campana", "edicion", "desde", "hasta"]].copy()
    productos.to_csv(carpeta / "productos.csv", index=False)
    clientes.to_csv(carpeta / "clientes.csv", index=False)
    ventas.to_parquet(carpeta / "ventas.parquet", index=False)
    cal_out.to_csv(carpeta / "campanas.csv", index=False)
    alcance.to_csv(carpeta / "campana_skus.csv", index=False)
    stock.to_parquet(carpeta / "stock_diario.parquet", index=False)

    return {
        "nombre": "Campañas demo",
        "descripcion": (
            "DEMO CON DATOS 100 % SINTÉTICOS. Retail: 40 SKU, 260 clientes, dos años de venta diaria y "
            "11 ediciones de 4 campañas. Cuatro comportamientos inyectados a propósito para que el motor los "
            "encuentre: una campaña que sólo adelanta venta, una que vende más y deja menos margen, una edición "
            "con el precio inflado antes del descuento y otra con quiebre de stock que censura la medición."),
        "idioma": "es",
        "fuentes": [
            {"nombre": "productos", "tipo": "csv", "ruta": "productos.csv"},
            {"nombre": "clientes", "tipo": "csv", "ruta": "clientes.csv"},
            {"nombre": "ventas", "tipo": "parquet", "ruta": "ventas.parquet"},
            {"nombre": "campanas", "tipo": "csv", "ruta": "campanas.csv"},
            {"nombre": "campana_skus", "tipo": "csv", "ruta": "campana_skus.csv"},
            {"nombre": "stock_diario", "tipo": "parquet", "ruta": "stock_diario.parquet"},
        ],
        "silver": {
            "ventas": {"tipos": "auto", "fechas": ["fecha"],
                       "derivar": {"margen": "df['importe'] - df['costo']"}},
            "campanas": {"tipos": "auto", "fechas": ["desde", "hasta"]},
            "stock_diario": {"tipos": "auto", "fechas": ["fecha"]},
        },
        "calidad": {"criticos_cortan": True, "reglas": [
            {"tabla": "productos", "columna": "sku", "tipo": "unico", "critico": True},
            {"tabla": "clientes", "columna": "id_cliente", "tipo": "unico", "critico": True},
            {"tabla": "ventas", "columna": "sku", "tipo": "referencia", "a": "productos.sku", "critico": True},
            {"tabla": "ventas", "columna": "importe", "tipo": "positivo", "critico": True},
            {"tabla": "ventas", "columna": "unidades", "tipo": "positivo", "critico": True},
            {"tabla": "ventas", "columna": "descuento", "tipo": "rango", "min": 0, "max": 0.5, "critico": False},
            # El margen puede dar negativo: Black Friday descuenta por debajo del
            # costo a propósito. La regla es informativa y existe para que el
            # hallazgo APAREZCA en la entrega en vez de pasar inadvertido.
            {"tabla": "ventas", "columna": "margen", "tipo": "no_negativo", "critico": False},
            {"tabla": "campanas", "columna": "campana", "tipo": "no_nulo", "critico": True},
        ]},
        "modelo": {
            "dimensiones": [
                {"nombre": "dim_producto", "desde": "productos", "clave": "sku", "scd": 1},
                {"nombre": "dim_cliente", "desde": "clientes", "clave": "id_cliente", "scd": 1},
            ],
            "hechos": [{"nombre": "fact_venta", "desde": "ventas", "fecha": "fecha",
                        "claves": {"sku": "dim_producto", "id_cliente": "dim_cliente"},
                        "medidas": ["unidades", "importe", "costo", "margen"]}],
            "calendario": "auto",
        },
        "kpis": [
            {"nombre": "Importe vendido", "tabla": "fact_venta", "columna": "importe", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Unidades", "tabla": "fact_venta", "columna": "unidades", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Margen", "tabla": "fact_venta", "columna": "margen", "agregacion": "sum", "formato": "#,0"},
            {"nombre": "Margen %", "tipo": "ratio",
             "numerador": {"tabla": "fact_venta", "columna": "margen", "agregacion": "sum"},
             "denominador": {"tabla": "fact_venta", "columna": "importe", "agregacion": "sum"}, "formato": "0.0%"},
            {"nombre": "Clientes", "tabla": "fact_venta", "columna": "dim_cliente_key", "agregacion": "count_distinct", "formato": "#,0"},
        ],
        "gobernanza": {"dueno": "BI Comercial", "descripciones": {
            "sku": "Código del producto", "precio_lista": "Precio de lista vigente, sin descuento",
            "costo_unitario": "Costo unitario de reposición",
            "id_cliente": "Identificador del cliente", "region": "Región comercial del cliente",
            "unidades": "Unidades vendidas en la operación",
            "importe": "Importe neto cobrado (unidades × precio con descuento)",
            "costo": "Costo total de las unidades vendidas",
            "margen": "Importe menos costo. Puede ser negativo si se vendió por debajo del costo",
            "descuento": "Descuento aplicado, en tanto por uno (0,25 = 25 %)",
            "campana": "Nombre de la campaña; se repite entre ediciones",
            "edicion": "Identificador de la edición de la campaña",
            "desde": "Primer día de la edición", "hasta": "Último día de la edición",
            "unidades_disponibles": "Stock disponible del SKU ese día. 0 = quiebre"}},
        # El análisis de campañas: las cuatro medidas, contra el baseline y
        # contra las ediciones anteriores de la misma campaña.
        "campanas": {
            # Sobre gold, con JOIN a las dimensiones: el hecho guarda las claves
            # subrogadas (`dim_producto_key`) y el calendario de campañas habla
            # de `sku`. Traducir acá es más honesto que pedirle al calendario
            # que conozca las claves internas del modelo.
            "sql": "SELECT f.fecha_key, p.sku, c.id_cliente, f.region, "
                   "f.unidades, f.importe, f.costo "
                   "FROM gold.fact_venta f "
                   "JOIN gold.dim_producto p USING (dim_producto_key) "
                   "JOIN gold.dim_cliente c USING (dim_cliente_key)",
            "fecha": "fecha_key",
            "producto": "sku",
            "cliente": "id_cliente",
            "medidas": {"unidades": "unidades", "importe": "importe", "costo": "costo"},
            "segmento": ["region"],
            "calendario": {"tabla": "campanas", "campana": "campana", "edicion": "edicion",
                           "desde": "desde", "hasta": "hasta",
                           "alcance_tabla": "campana_skus", "alcance_producto": "sku"},
            "ventana": {"baseline_dias": 28, "arrastre_dias": 28, "blackout_dias": 7},
            "stock": {"tabla": "stock_diario", "producto": "sku", "fecha": "fecha",
                      "columna": "unidades_disponibles"},
            "rfm": {"ventana_dias": 365},
            "cohortes": {"granularidad": "mensual", "periodos": 6},
        },
        "frescura": {"cada": "diaria", "tablas": {"productos": {"cada": "semanal"}, "clientes": {"cada": "semanal"}}},
        "reporte": {"titulo": "Comercial · efectividad de campañas", "graficos": "auto"},
        "powerbi": {"generar": True, "nombre": "Campanas"},
        "automatizacion": {"hora": "05:30", "reintentos": 3},
    }
