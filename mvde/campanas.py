# © 2026 Martín Viera. Todos los derechos reservados.
"""Efectividad de campañas: ¿vendió más, o vendió antes?

Qué contesta
------------
Para cada **edición** de cada campaña, y por segmento:

  · unidades, precio, rentabilidad y stock **durante** la campaña,
  · contra el **baseline** (los días normales de antes),
  · contra la **misma campaña en sus ediciones anteriores**,
  · y contra lo que pasó **después**, que es la pregunta que casi nadie hace.

Las cinco trampas que este módulo existe para no pisar
------------------------------------------------------
0. **El baseline solo no alcanza: hay que controlar la estacionalidad.** Comparar
   la ventana de campaña contra los 28 días previos le atribuye a la campaña
   todo lo que pasó en esa ventana, empezando por la época del año. Medido en la
   demo: Black Friday daba «incremental» con margen positivo porque su ventana de
   arrastre cae en diciembre. El control está en los propios datos — **los SKU que
   NO entraron en la campaña**— y la comparación es de diferencias en diferencias:

       lift = (campaña durante / campaña baseline) ÷ (control durante / control baseline)

   Eso descuenta cualquier cosa que haya movido a los dos grupos por igual: la
   estación, el clima, el día de pago, la macro. Lo que NO descuenta, y por eso
   se reporta aparte, es la **sustitución**: si el control CAYÓ durante la
   campaña, parte del volumen no es nuevo, es robado de otra góndola, y el
   indicador queda marcado `posible_sustitucion`.

1. **La semana previa no es baseline.** El anuncio ya salió y el que puede
   esperar, espera. Tomarla como referencia hunde el baseline e infla el lift.
   Por eso hay `blackout_dias`: esos días quedan fuera de las dos ventanas.

2. **Adelantar no es vender.** Una campaña que vende el triple durante y la
   mitad las tres semanas siguientes no vendió más: vendió antes. Se mide la
   ventana de **arrastre** y el incremental se calcula sobre las dos ventanas
   juntas, contra el contrafáctico «el ritmo del baseline sigue igual».

3. **Más unidades puede ser peor negocio.** El veredicto se decide por
   **margen en plata**, no por unidades: si el margen incremental es negativo,
   la campaña vendió más y ganó menos, y eso hay que decirlo con esas palabras.

4. **El descuento se mide contra el precio de antes, no contra el de lista.**
   Si el precio subió en la semana previa, parte del «30 % off» es fabricado.
   Se calcula el descuento **real** (contra el precio de la ventana limpia) y el
   **aparente** (contra el precio inmediatamente anterior), y la diferencia se
   reporta como `puntos_inflados`.

Y dos cosas que se declaran en vez de esconderse
------------------------------------------------
· **El stock censura.** Un SKU que quebró a mitad de campaña tiene unidades que
  son un PISO, no una medición. Queda marcado `medicion_censurada` y sale del
  like-for-like en vez de contaminarlo.
· **Los cortes del RFM son relativos.** Los quintiles se recalculan en cada
  corrida, así que «Campeones creció 12 %» puede ser el corte moviéndose y no
  la gente cambiando. `cortes` se devuelve siempre para poder fijarlo, y
  mientras no se fije, la comparación entre corridas no es válida.

YAML `campanas`
---------------
    campanas:
      tabla: fact_venta | sql: "SELECT ... FROM gold...."
      fecha: fecha_key
      producto: dim_producto_key
      cliente: dim_cliente_key            # opcional: habilita RFM y cohortes
      medidas: {unidades: unidades, importe: importe, costo: costo}
      segmento: [region]                  # opcional
      calendario:
        tabla: campanas                   # campana, edicion, desde, hasta
        campana: campana · edicion: edicion · desde: desde · hasta: hasta
        alcance_tabla: campana_skus       # opcional: campana, edicion, producto
      ventana: {baseline_dias: 28, arrastre_dias: 28, blackout_dias: 7}
      stock: {tabla: stock_diario, columna: unidades_disponibles}
      rfm: {ventana_dias: 365, cortes: null}
      cohortes: {granularidad: mensual, periodos: 6}
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Valores por omisión de las ventanas, en días.
BASELINE_DIAS = 28
ARRASTRE_DIAS = 28
BLACKOUT_DIAS = 7
# Por encima de esto, el precio de la ventana previa se considera inflado
# respecto de la ventana limpia: 3 % aguanta un redondeo o un ajuste de lista.
TOLERANCIA_INFLADO = 0.03
# Cuánto se le permite CAER al control antes de dejar de ser control.
#
# La guarda es asimétrica a propósito, y el motivo es el mecanismo: la campaña
# puede hundir al control robándole demanda (sustitución), pero no puede
# hacerlo subir. Entonces una CAÍDA grande dice «este grupo está contaminado
# por el tratamiento» y lo invalida como control; una SUBA grande dice
# «diciembre», que es justo lo que el dif-en-dif existe para descontar.
#
# Medido en la demo: con un control que caía 65 % el lift corregido daba
# 1451 %, un número que no es un número. Y con un control que SUBÍA 50 % en
# diciembre, descartarlo devolvía a Black Friday el «incremental» falso que el
# método había corregido. Pasado el umbral por abajo se vuelve al baseline y
# se dice por escrito.
CONTROL_MAX_CAIDA_PCT = 25.0
# Por debajo de esto, la caída del control durante la campaña se marca como
# sustitución: volumen que salió de otra góndola, no venta nueva.
SUSTITUCION_PCT = -5.0
# Una cohorte con menos clientes que esto da retenciones de 100 % que son un
# artefacto del tamaño. Medido en la demo: la cohorte de Black Friday tenía 2
# clientes y retenía «100 %» en los seis períodos. El número viaja igual, pero
# marcado, porque un porcentaje sin su denominador se cita como si fuera real.
COHORTE_MINIMA = 15
# Los 11 segmentos RFM, por (R, F) en quintiles. M entra en el desempate de
# «No los puedo perder» y en el orden de prioridad, no en la etiqueta.
SEGMENTOS_RFM = (
    "Campeones", "Leales", "Potenciales", "Nuevos", "Prometedores",
    "Necesitan atención", "A punto de dormirse", "En riesgo",
    "No los puedo perder", "Hibernando", "Perdidos",
)


class CampanaError(RuntimeError):
    """Configuración o datos que no permiten medir. Falla ruidoso: una campaña
    mal medida es peor que una campaña sin medir."""


# ------------------------------------------------------------------ ayudas
def _a_fecha(s: pd.Series) -> pd.Series:
    """Fechas desde lo que venga: `date`, texto, o el `fecha_key` entero
    yyyymmdd que usa el modelo estrella de gold."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
    return pd.to_datetime(s, errors="coerce")


def _col(df: pd.DataFrame, nombre: str | None, de_que: str) -> str:
    if not nombre:
        raise CampanaError(f"falta declarar {de_que} en `campanas`")
    if nombre not in df.columns:
        raise CampanaError(f"la columna «{nombre}» ({de_que}) no está en el set: {sorted(df.columns)[:12]}")
    return nombre


def _div(a, b):
    """División que devuelve None en vez de inf o NaN: un ratio sin
    denominador no es cero, es «no se puede calcular»."""
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if b == 0 or not np.isfinite(b) or not np.isfinite(a):
        return None
    return a / b


def _pct(nuevo, viejo):
    """Variación porcentual, o None si no hay contra qué comparar."""
    r = _div(nuevo, viejo)
    return None if r is None else round((r - 1) * 100, 2)


def _r(x, n=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


# ------------------------------------------------------------------ ventanas
def ventanas(desde: pd.Timestamp, hasta: pd.Timestamp, cfg: dict) -> dict:
    """Las tres ventanas de una edición, más el blackout que queda afuera.

    El blackout es la parte que importa entender: son los días previos al
    arranque que NO se usan como baseline porque ya están contaminados por el
    anuncio. Si se usan, el baseline baja y el lift sube sin que haya pasado
    nada en la realidad.
    """
    v = cfg.get("ventana") or {}
    base_d = int(v.get("baseline_dias", BASELINE_DIAS))
    arr_d = int(v.get("arrastre_dias", ARRASTRE_DIAS))
    black_d = int(v.get("blackout_dias", BLACKOUT_DIAS))
    fin_base = desde - pd.Timedelta(days=black_d + 1)
    return {
        "baseline": (fin_base - pd.Timedelta(days=base_d - 1), fin_base),
        "blackout": (desde - pd.Timedelta(days=black_d), desde - pd.Timedelta(days=1)) if black_d else None,
        "durante": (desde, hasta),
        "arrastre": (hasta + pd.Timedelta(days=1), hasta + pd.Timedelta(days=arr_d)) if arr_d else None,
    }


def _dias(rango) -> int:
    return 0 if rango is None else int((rango[1] - rango[0]).days) + 1


def _en(df: pd.DataFrame, col: str, rango) -> pd.DataFrame:
    if rango is None:
        return df.iloc[0:0]
    return df[(df[col] >= rango[0]) & (df[col] <= rango[1])]


# ------------------------------------------------------------------ medidas
def _medir(df: pd.DataFrame, m: dict, dias: int, cliente: str | None) -> dict:
    """Las cuatro medidas de una ventana, en total y por día.

    Por día es lo que hace comparables ventanas de distinto largo: un baseline
    de 28 días contra una campaña de 10 contra una edición anterior de 14. En
    totales no se comparan, y comparar totales es el error más común del
    análisis de campañas.
    """
    u = float(df[m["unidades"]].sum()) if len(df) else 0.0
    imp = float(df[m["importe"]].sum()) if len(df) else 0.0
    costo = float(df[m["costo"]].sum()) if (m.get("costo") and len(df)) else None
    margen = None if costo is None else imp - costo
    return {
        "dias": dias,
        "filas": int(len(df)),
        "unidades": _r(u),
        "unidades_dia": _r(_div(u, dias), 3),
        "importe": _r(imp),
        "importe_dia": _r(_div(imp, dias), 2),
        "precio_medio": _r(_div(imp, u), 4),
        "costo": _r(costo),
        "margen": _r(margen),
        "margen_dia": _r(_div(margen, dias), 2) if margen is not None else None,
        "margen_pct": _r(None if margen is None else _div(margen, imp) and _div(margen, imp) * 100),
        "clientes": int(df[cliente].nunique()) if (cliente and len(df)) else None,
    }


# ------------------------------------------------------------------ panel
def _preparar(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    m = dict(cfg.get("medidas") or {})
    f = _col(df, cfg.get("fecha"), "la columna de fecha (`fecha`)")
    m["unidades"] = _col(df, m.get("unidades"), "la medida de unidades (`medidas.unidades`)")
    m["importe"] = _col(df, m.get("importe"), "la medida de importe (`medidas.importe`)")
    if m.get("costo") and m["costo"] not in df.columns:
        raise CampanaError(f"la columna de costo «{m['costo']}» no está en el set: sin ella no hay rentabilidad")
    d = df.copy()
    d["_fecha"] = _a_fecha(d[f])
    sin = int(d["_fecha"].isna().sum())
    if sin:
        d = d[d["_fecha"].notna()]
    if d.empty:
        raise CampanaError("después de convertir fechas no quedó ninguna fila con fecha válida")
    return d, {"medidas": m, "fechas_invalidas": sin}


def _calendario(cal: pd.DataFrame, c: dict) -> pd.DataFrame:
    """El calendario de campañas, normalizado y ordenado por arranque.

    El orden importa: la «edición anterior» de una campaña es la anterior por
    fecha de arranque, no la que figura antes en la tabla ni la del número más
    chico. Un identificador de edición como «2025-Q1» no ordena solo.
    """
    col = {k: _col(cal, c.get(k), f"`calendario.{k}`") for k in ("campana", "edicion", "desde", "hasta")}
    out = cal[[col["campana"], col["edicion"], col["desde"], col["hasta"]]].copy()
    out.columns = ["campana", "edicion", "desde", "hasta"]
    out["desde"] = _a_fecha(out["desde"])
    out["hasta"] = _a_fecha(out["hasta"])
    malas = out[out["desde"].isna() | out["hasta"].isna() | (out["hasta"] < out["desde"])]
    if len(malas):
        raise CampanaError(f"{len(malas)} edición(es) con fechas inválidas o `hasta` anterior a `desde`: "
                           f"{malas[['campana', 'edicion']].to_dict('records')[:3]}")
    out = out.sort_values(["campana", "desde"]).reset_index(drop=True)
    out["edicion_nro"] = out.groupby("campana").cumcount() + 1
    out["dias"] = (out["hasta"] - out["desde"]).dt.days + 1
    return out


def _alcance(cfg: dict, tablas: dict, producto: str | None) -> pd.DataFrame | None:
    """Qué productos entraban en cada edición, si el proyecto lo declara.

    Sin esto el módulo mide la venta TOTAL en la ventana, que no es lo mismo:
    incluye lo que se vendió al margen de la campaña. Se puede trabajar sin el
    alcance, pero queda escrito en las notas que la medición es de la ventana
    y no de la campaña.
    """
    c = cfg.get("calendario") or {}
    nombre = c.get("alcance_tabla")
    if not nombre:
        return None
    t = tablas.get(nombre)
    if t is None:
        raise CampanaError(f"`calendario.alcance_tabla` apunta a «{nombre}», que no existe")
    col_prod = c.get("alcance_producto") or producto
    faltan = [x for x in (c.get("campana"), c.get("edicion"), col_prod) if x and x not in t.columns]
    if faltan:
        raise CampanaError(f"la tabla de alcance «{nombre}» no tiene {faltan}")
    out = t[[c["campana"], c["edicion"], col_prod]].copy()
    out.columns = ["campana", "edicion", "producto"]
    return out.drop_duplicates()


# ------------------------------------------------------------------ efecto
def _veredicto(ef: dict, hay_margen: bool) -> tuple[str, str]:
    """Qué pasó, en una frase que se pueda leer en una reunión.

    El orden de las preguntas no es arbitrario: primero si se puede comparar,
    después si el negocio ganó plata, después si el volumen es nuevo o
    adelantado, y sólo al final si además se lo sacó a otra góndola. Una campaña
    que sube unidades y baja margen absoluto NO es un éxito, y el veredicto
    tiene que decirlo antes de que alguien muestre el gráfico de unidades.
    """
    if not ef["comparable"]:
        return "no_comparable", "sin baseline suficiente para comparar: no se puede afirmar nada del efecto"
    inc_u = ef.get("incremental_unidades")
    inc_m = ef.get("incremental_margen")
    if hay_margen and inc_m is not None and inc_m < 0:
        durante = ef.get("incremental_margen_durante")
        if inc_u is not None and inc_u > 0 and durante is not None and durante < 0:
            return "vendio_mas_gano_menos", (
                f"vendió {_r(inc_u, 0)} unidades incrementales y dejó {_r(inc_m, 0)} de margen: "
                f"ya en la ventana de campaña el margen quedó {_r(durante, 0)} abajo del contrafáctico, "
                "o sea que el descuento se comió más de lo que trajo el volumen")
        if inc_u is not None and inc_u > 0:
            # Durante la campaña el margen dio bien; lo que lo hundió fue lo que
            # pasó después. La acción es distinta: no hay que tocar el descuento,
            # hay que espaciar la campaña o acotar el abastecimiento.
            return "margen_lo_come_la_resaca", (
                f"durante la campaña el margen quedó {_r(durante, 0)} respecto del contrafáctico, pero en los "
                f"días siguientes se perdió más: el incremental de la ventana completa es {_r(inc_m, 0)}. "
                "El problema no es el descuento, es la caída posterior")
        return "peor", "menos unidades y menos margen que el contrafáctico"
    if inc_u is not None and inc_u <= 0:
        return "adelanto", ("no hubo venta incremental en la ventana completa: lo que subió durante la campaña "
                            "bajó después, o sea que se adelantó venta que ya iba a ocurrir")
    if ef.get("control_descartado"):
        return "incremental_sin_control", (
            "incremental contra el baseline, pero sin control válido: " + ef["porque_control_descartado"])
    if ef.get("posible_sustitucion"):
        return "incremental_con_sustitucion", (
            f"incremental, pero el control cayó {abs(ef['control_durante_pct'])} % durante la campaña: "
            "parte del volumen salió de otros productos, no es venta nueva")
    if ef.get("arrastre_unidades_pct") is not None and ef["arrastre_unidades_pct"] < -15:
        return "incremental_con_arrastre", (
            f"incremental, pero con caída de {abs(ef['arrastre_unidades_pct'])} % después: "
            "parte del volumen es adelantamiento y hay que descontarlo del próximo plan")
    return "incremental", "vendió por encima del contrafáctico y lo sostuvo después"


def _efecto_de(trat: dict, ctrl: dict | None, hay_margen: bool) -> dict:
    """Compara las ventanas de una edición contra el contrafáctico.

    El contrafáctico NO es «el baseline sigue igual»: es «el baseline se mueve
    como se movió el grupo de control». La diferencia importa. En la demo, la
    ventana de arrastre de Black Friday cae en diciembre; contra un baseline
    plano la campaña parece haber dejado +42.640 de margen, y contra el control
    —que también subió en diciembre— deja mucho menos. Lo que se le atribuía a
    la campaña era la Navidad.

    Sin grupo de control (proyecto sin `alcance_tabla`) se cae al baseline plano
    y el resultado queda marcado `metodo: "baseline"`, que es lo mismo que decir
    «este número no descuenta la estación».
    """
    b, d, a = trat["baseline"], trat["durante"], trat.get("arrastre")
    comparable = bool(b["filas"]) and b["unidades_dia"] not in (None, 0)
    con_control = bool(ctrl and ctrl["baseline"]["filas"] and ctrl["baseline"]["unidades_dia"])

    def factor(ventana: str, campo: str = "unidades_dia"):
        """Cuánto se movió el control en esa ventana respecto de su baseline."""
        if not con_control:
            return 1.0
        v = ctrl.get(ventana) or {}
        f = _div(v.get(campo), ctrl["baseline"].get(campo))
        return 1.0 if f is None else f

    ef = {
        "metodo": "dif-en-dif" if con_control else "baseline",
        "dias_campana": d["dias"],
        "unidades_dia_baseline": b["unidades_dia"],
        "unidades_dia_campana": d["unidades_dia"],
        "unidades_dia_arrastre": (a or {}).get("unidades_dia"),
        # El bruto se conserva porque es el número que todo el mundo trae a la
        # reunión, y verlo al lado del corregido es la mitad de la explicación.
        "lift_bruto_pct": _pct(d["unidades_dia"], b["unidades_dia"]),
        "precio_baseline": b["precio_medio"],
        "precio_campana": d["precio_medio"],
        "delta_precio_pct": _pct(d["precio_medio"], b["precio_medio"]),
        "margen_pct_baseline": b["margen_pct"],
        "margen_pct_campana": d["margen_pct"],
        "delta_margen_pp": (None if (b["margen_pct"] is None or d["margen_pct"] is None)
                            else _r(d["margen_pct"] - b["margen_pct"])),
        "arrastre_unidades_pct": _pct((a or {}).get("unidades_dia"), b["unidades_dia"]),
        "clientes_campana": d["clientes"],
        "comparable": comparable,
        "control_durante_pct": (None if not con_control else _r((factor("durante") - 1) * 100)),
        "control_arrastre_pct": (None if not con_control or not a else _r((factor("arrastre") - 1) * 100)),
        "control_unidades_dia_baseline": (None if not ctrl else ctrl["baseline"]["unidades_dia"]),
    }
    # Sustitución: si el control CAYÓ mientras la campaña subía, parte del
    # volumen vino de la góndola de al lado. El dif-en-dif no lo descuenta —al
    # contrario, lo cuenta a favor— así que hay que decirlo.
    ef["posible_sustitucion"] = bool(con_control and ef["control_durante_pct"] is not None
                                     and ef["control_durante_pct"] < SUSTITUCION_PCT)
    # La guarda: un control que se movió demasiado no es un control. Saber
    # cuándo el propio método no aplica vale más que el número que devuelve.
    if con_control and (ef["control_durante_pct"] or 0) < -CONTROL_MAX_CAIDA_PCT:
        con_control = False
        ef["metodo"] = "baseline"
        ef["control_descartado"] = True
        ef["porque_control_descartado"] = (
            f"el control CAYÓ {abs(ef['control_durante_pct'])} % durante la campaña, más que el "
            f"{CONTROL_MAX_CAIDA_PCT} % admitido: eso no lo puede causar la estación, lo causa la campaña "
            "robándole demanda, así que el grupo dejó de ser control. El efecto se mide contra el baseline "
            "plano, que NO descuenta la estacionalidad")
    else:
        ef["control_descartado"] = False
    if comparable:
        cf_u_d = b["unidades_dia"] * factor("durante")
        ef["contrafactico_unidades_dia"] = _r(cf_u_d, 3)
        ef["lift_pct"] = _pct(d["unidades_dia"], cf_u_d)
        inc = (d["unidades_dia"] - cf_u_d) * d["dias"]
        if a and a["dias"]:
            cf_u_a = b["unidades_dia"] * factor("arrastre")
            inc += ((a["unidades_dia"] or 0) - cf_u_a) * a["dias"]
        ef["incremental_unidades"] = _r(inc, 1)
        if hay_margen and b["margen_dia"] is not None and d["margen_dia"] is not None:
            cf_m_d = b["margen_dia"] * factor("durante", "margen_dia")
            inc_durante = (d["margen_dia"] - cf_m_d) * d["dias"]
            # Los dos por separado: el de la campaña dice si el descuento cerró,
            # y el de la ventana completa dice si el negocio cerró.
            ef["incremental_margen_durante"] = _r(inc_durante)
            inc_m = inc_durante
            if a and a["dias"] and a["margen_dia"] is not None:
                cf_m_a = b["margen_dia"] * factor("arrastre", "margen_dia")
                inc_m += (a["margen_dia"] - cf_m_a) * a["dias"]
                ef["incremental_margen_arrastre"] = _r(inc_m - inc_durante)
            ef["incremental_margen"] = _r(inc_m)
            ef["contrafactico_margen_dia"] = _r(cf_m_d)
    ef["veredicto"], ef["porque"] = _veredicto(ef, hay_margen)
    return ef


# ------------------------------------------------------------------ precio
def _precio_por_producto(d: pd.DataFrame, m: dict, producto: str, rango) -> pd.Series:
    """Precio implícito por producto: importe / unidades. No el precio de lista.

    Se usa la mediana ponderada implícita (suma sobre suma) y no el promedio de
    precios unitarios, porque el promedio simple le da el mismo peso a una
    venta de 1 unidad que a una de 400."""
    v = _en(d, "_fecha", rango)
    if v.empty:
        return pd.Series(dtype=float)
    g = v.groupby(producto).agg(imp=(m["importe"], "sum"), u=(m["unidades"], "sum"))
    g = g[g["u"] > 0]
    return (g["imp"] / g["u"]).rename("precio")


def _precios(d: pd.DataFrame, m: dict, producto: str, cal: pd.DataFrame, cfg: dict,
             alcance: pd.DataFrame | None) -> pd.DataFrame:
    """Descuento REAL contra la ventana limpia, y aparente contra la previa.

    La diferencia entre los dos es la parte del descuento que se fabricó
    subiendo el precio antes de bajarlo. No es una sospecha teórica: es una
    práctica común y se mide con dos restas.
    """
    filas = []
    for _, e in cal.iterrows():
        w = ventanas(e["desde"], e["hasta"], cfg)
        ref = _precio_por_producto(d, m, producto, w["baseline"])
        prev = _precio_por_producto(d, m, producto, w["blackout"])
        camp = _precio_por_producto(d, m, producto, w["durante"])
        skus = set(camp.index)
        if alcance is not None:
            decl = set(alcance[(alcance["campana"] == e["campana"]) & (alcance["edicion"] == e["edicion"])]["producto"])
            skus &= decl
        for sku in sorted(skus):
            p_ref, p_prev, p_camp = ref.get(sku), prev.get(sku), camp.get(sku)
            real = None if p_ref is None else _pct(p_camp, p_ref)
            apar = None if p_prev is None else _pct(p_camp, p_prev)
            inflado = bool(p_ref is not None and p_prev is not None
                           and p_prev > p_ref * (1 + TOLERANCIA_INFLADO))
            filas.append({
                "campana": e["campana"], "edicion": e["edicion"], "producto": sku,
                "precio_referencia": _r(p_ref, 4), "precio_previo": _r(p_prev, 4), "precio_campana": _r(p_camp, 4),
                "descuento_real_pct": None if real is None else _r(-real),
                "descuento_aparente_pct": None if apar is None else _r(-apar),
                "puntos_inflados": (None if (real is None or apar is None) else _r(real - apar)),
                "precio_inflado_antes": inflado,
                "suba_previa_pct": None if not inflado else _pct(p_prev, p_ref),
            })
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ stock
def _stock(cfg: dict, tablas: dict, cal: pd.DataFrame, producto: str) -> pd.DataFrame:
    """Días de quiebre por producto y edición, y qué mediciones quedan censuradas.

    Un SKU sin stock no dejó de venderse porque la campaña no funcionara: dejó
    de venderse porque no había. Sus unidades son un piso y no se pueden
    comparar contra nada.
    """
    s = cfg.get("stock") or {}
    nombre = s.get("tabla")
    if not nombre:
        return pd.DataFrame()
    t = tablas.get(nombre)
    if t is None:
        raise CampanaError(f"`stock.tabla` apunta a «{nombre}», que no existe")
    col_p = s.get("producto") or producto
    col_f = s.get("fecha") or "fecha"
    col_u = s.get("columna")
    for c, de in ((col_p, "el producto"), (col_f, "la fecha"), (col_u, "las unidades disponibles")):
        if not c or c not in t.columns:
            raise CampanaError(f"la tabla de stock «{nombre}» no tiene {de} («{c}»)")
    st = t[[col_p, col_f, col_u]].copy()
    st.columns = ["producto", "_fecha", "disponible"]
    st["_fecha"] = _a_fecha(st["_fecha"])
    filas = []
    for _, e in cal.iterrows():
        v = _en(st, "_fecha", (e["desde"], e["hasta"]))
        if v.empty:
            continue
        g = v.groupby("producto").agg(
            dias_con_dato=("_fecha", "nunique"),
            dias_sin_stock=("disponible", lambda x: int((pd.to_numeric(x, errors="coerce").fillna(0) <= 0).sum())),
            disponible_medio=("disponible", "mean")).reset_index()
        g["campana"], g["edicion"] = e["campana"], e["edicion"]
        g["dias_campana"] = int(e["dias"])
        g["cobertura_pct"] = ((1 - g["dias_sin_stock"] / g["dias_con_dato"].clip(lower=1)) * 100).round(2)
        g["medicion_censurada"] = g["dias_sin_stock"] > 0
        g["disponible_medio"] = g["disponible_medio"].round(2)
        filas.append(g)
    if not filas:
        return pd.DataFrame()
    cols = ["campana", "edicion", "producto", "dias_campana", "dias_con_dato",
            "dias_sin_stock", "cobertura_pct", "disponible_medio", "medicion_censurada"]
    return pd.concat(filas, ignore_index=True)[cols]


# ------------------------------------------------------------------ vs edición anterior
def _vs_ediciones(d: pd.DataFrame, m: dict, producto: str, cal: pd.DataFrame, cfg: dict,
                  alcance: pd.DataFrame | None, stock: pd.DataFrame, cliente: str | None) -> pd.DataFrame:
    """La misma campaña contra sus dos ediciones anteriores.

    Tres decisiones que hacen la diferencia entre un número y un número que se
    puede defender:

    1. **Por día.** La edición pasada duró 14 días y esta 10: los totales no se
       comparan. Todo va normalizado por día de campaña.
    2. **Like-for-like.** Sólo los productos que estuvieron en las DOS ediciones
       y que no quebraron stock en ninguna. Se informa `cobertura_lfl_pct`
       —cuánta de la venta queda dentro del subconjunto— para que nadie lea el
       LFL como si fuera el total.
    3. **El resto es mezcla.** La diferencia entre el cambio total y el
       like-for-like es efecto de haber cambiado el surtido, no de que la
       campaña funcionara distinto. Sale como `efecto_mezcla_pp`.
    """
    censurados = set()
    if len(stock):
        cens = stock[stock["medicion_censurada"]]
        censurados = set(zip(cens["campana"], cens["edicion"], cens["producto"]))

    def skus_de(e) -> set:
        if alcance is None:
            v = _en(d, "_fecha", (e["desde"], e["hasta"]))
            return set(v[producto].unique())
        return set(alcance[(alcance["campana"] == e["campana"]) & (alcance["edicion"] == e["edicion"])]["producto"])

    def medir(e, solo: set | None) -> dict:
        v = _en(d, "_fecha", (e["desde"], e["hasta"]))
        if solo is not None:
            v = v[v[producto].isin(solo)]
        return _medir(v, m, int(e["dias"]), cliente)

    filas = []
    for campana, g in cal.groupby("campana", sort=False):
        g = g.sort_values("desde").reset_index(drop=True)
        for i in range(len(g)):
            act = g.loc[i]
            for salto, etiqueta in ((1, "anterior"), (2, "anterior_anterior")):
                j = i - salto
                if j < 0:
                    continue
                ref = g.loc[j]
                tot_a, tot_r = medir(act, None), medir(ref, None)
                # like-for-like: en las dos ediciones y sin quiebre en ninguna
                comunes = skus_de(act) & skus_de(ref)
                comunes -= {p for p in comunes
                            if (campana, act["edicion"], p) in censurados
                            or (campana, ref["edicion"], p) in censurados}
                lfl_a = medir(act, comunes) if comunes else None
                lfl_r = medir(ref, comunes) if comunes else None
                var_tot = _pct(tot_a["unidades_dia"], tot_r["unidades_dia"])
                var_lfl = None if not comunes else _pct(lfl_a["unidades_dia"], lfl_r["unidades_dia"])
                filas.append({
                    "campana": campana, "edicion": act["edicion"], "contra": ref["edicion"], "relacion": etiqueta,
                    "dias": int(act["dias"]), "dias_contra": int(ref["dias"]),
                    # unidades
                    "unidades_dia": tot_a["unidades_dia"], "unidades_dia_contra": tot_r["unidades_dia"],
                    "var_unidades_pct": var_tot,
                    # precio
                    "precio_medio": tot_a["precio_medio"], "precio_medio_contra": tot_r["precio_medio"],
                    "var_precio_pct": _pct(tot_a["precio_medio"], tot_r["precio_medio"]),
                    # rentabilidad
                    "margen_pct": tot_a["margen_pct"], "margen_pct_contra": tot_r["margen_pct"],
                    "delta_margen_pp": (None if (tot_a["margen_pct"] is None or tot_r["margen_pct"] is None)
                                        else _r(tot_a["margen_pct"] - tot_r["margen_pct"])),
                    "margen_dia": tot_a["margen_dia"], "margen_dia_contra": tot_r["margen_dia"],
                    "var_margen_pct": _pct(tot_a["margen_dia"], tot_r["margen_dia"]),
                    # like-for-like y mezcla
                    "skus": len(skus_de(act)), "skus_contra": len(skus_de(ref)), "skus_lfl": len(comunes),
                    "cobertura_lfl_pct": (None if not comunes
                                          else _r(_div(lfl_a["unidades"], tot_a["unidades"]) and
                                                  _div(lfl_a["unidades"], tot_a["unidades"]) * 100)),
                    "var_unidades_lfl_pct": var_lfl,
                    "efecto_mezcla_pp": (None if (var_tot is None or var_lfl is None) else _r(var_tot - var_lfl)),
                    "clientes": tot_a["clientes"], "clientes_contra": tot_r["clientes"],
                    "skus_excluidos_por_stock": len([p for p in (skus_de(act) & skus_de(ref))
                                                     if (campana, act["edicion"], p) in censurados
                                                     or (campana, ref["edicion"], p) in censurados]),
                })
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ RFM
def _etiqueta_rfm(r: int, f: int) -> str:
    """R y F en quintiles (1 = peor, 5 = mejor) a uno de los 11 segmentos.

    R ya viene invertido: recencia chica (compró hace poco) es R alto.
    """
    if r >= 4 and f >= 4:
        return "Campeones"
    if r >= 3 and f >= 4:
        return "Leales"
    if r >= 4 and f == 3:
        return "Potenciales"
    if r == 5 and f <= 2:
        return "Nuevos"
    if r >= 4 and f <= 2:
        return "Prometedores"
    if r == 3 and f == 3:
        return "Necesitan atención"
    if r == 3 and f <= 2:
        return "A punto de dormirse"
    if r == 2 and f >= 3:
        return "En riesgo"
    if r == 1 and f >= 4:
        return "No los puedo perder"
    if r == 2 and f <= 2:
        return "Hibernando"
    return "Perdidos"


def _quintil(s: pd.Series, cortes: list | None, invertir: bool = False) -> tuple[pd.Series, list]:
    """Quintiles con cortes explícitos y devueltos.

    Si `cortes` viene, se usan: eso es lo que hace comparables dos corridas. Si
    no viene, se calculan de esta corrida y se devuelven — y hasta que alguien
    los fije en el YAML, la comparación entre corridas mide el corte moviéndose
    tanto como la gente cambiando.
    """
    x = pd.to_numeric(s, errors="coerce")
    if cortes is None:
        qs = [x.quantile(q) for q in (0.2, 0.4, 0.6, 0.8)]
        cortes = [float(v) for v in pd.unique(pd.Series(qs).dropna())]
    bordes = [-np.inf, *sorted(cortes), np.inf]
    etiquetas = list(range(1, len(bordes)))
    q = pd.cut(x, bins=bordes, labels=etiquetas, include_lowest=True, duplicates="drop").astype("Int64")
    if invertir:
        q = (len(etiquetas) + 1) - q
    return q.fillna(1).astype(int), [float(c) for c in sorted(cortes)]


def _rfm(d: pd.DataFrame, m: dict, cliente: str, cfg: dict, corte_fecha: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    r = cfg.get("rfm") or {}
    dias = int(r.get("ventana_dias", 365))
    desde = corte_fecha - pd.Timedelta(days=dias - 1)
    v = d[(d["_fecha"] >= desde) & (d["_fecha"] <= corte_fecha)]
    if v.empty:
        return pd.DataFrame(), {"error": "la ventana del RFM no tiene ninguna venta"}
    g = v.groupby(cliente).agg(
        ultima_compra=("_fecha", "max"),
        frecuencia=("_fecha", "nunique"),
        monetario=(m["importe"], "sum"),
        unidades=(m["unidades"], "sum")).reset_index()
    g["recencia_dias"] = (corte_fecha - g["ultima_compra"]).dt.days
    dados = r.get("cortes") or {}
    g["R"], cr = _quintil(g["recencia_dias"], dados.get("recencia"), invertir=True)
    g["F"], cf = _quintil(g["frecuencia"], dados.get("frecuencia"))
    g["M"], cm = _quintil(g["monetario"], dados.get("monetario"))
    g["segmento_rfm"] = [_etiqueta_rfm(int(a), int(b)) for a, b in zip(g["R"], g["F"])]
    g["rfm"] = g["R"].astype(str) + g["F"].astype(str) + g["M"].astype(str)
    g["monetario"] = g["monetario"].round(2)
    g = g.rename(columns={cliente: "cliente"})
    meta = {
        "ventana_dias": dias,
        "corte_fecha": str(corte_fecha.date()),
        "clientes": int(len(g)),
        "cortes": {"recencia": cr, "frecuencia": cf, "monetario": cm},
        "cortes_fijados": bool(dados),
        "nota_cortes": ("Cortes FIJADOS desde el YAML: dos corridas son comparables."
                        if dados else
                        "Cortes calculados de esta corrida. Para comparar con otra corrida hay que fijarlos en "
                        "`campanas.rfm.cortes`; si no, parte del movimiento entre segmentos es el corte moviéndose."),
    }
    return g, meta


def _rfm_alcance(d: pd.DataFrame, m: dict, cliente: str, rfm: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    """¿A quién le llegó cada edición? Campaña × segmento RFM.

    Esto es lo que vuelve «segmentada» a una campaña: no que se haya declarado
    un público, sino poder mostrar a quién le vendió de verdad.
    """
    if rfm.empty:
        return pd.DataFrame()
    mapa = rfm.set_index("cliente")["segmento_rfm"]
    filas = []
    for _, e in cal.iterrows():
        v = _en(d, "_fecha", (e["desde"], e["hasta"])).copy()
        if v.empty:
            continue
        v["segmento_rfm"] = v[cliente].map(mapa).fillna("Sin clasificar")
        g = v.groupby("segmento_rfm").agg(
            clientes=(cliente, "nunique"),
            unidades=(m["unidades"], "sum"),
            importe=(m["importe"], "sum"),
            **({"costo": (m["costo"], "sum")} if m.get("costo") else {})).reset_index()
        g["campana"], g["edicion"] = e["campana"], e["edicion"]
        tot = g["importe"].sum()
        g["participacion_importe_pct"] = ((g["importe"] / tot * 100).round(2) if tot else None)
        if m.get("costo"):
            g["margen"] = (g["importe"] - g["costo"]).round(2)
            g["margen_pct"] = ((g["margen"] / g["importe"].replace(0, np.nan)) * 100).round(2)
        g["importe"] = g["importe"].round(2)
        filas.append(g)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


# ------------------------------------------------------------------ cohortes
def _cohortes(d: pd.DataFrame, m: dict, cliente: str, cfg: dict, cal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retención por cohorte de primera compra, y si la campaña trae clientes que vuelven.

    Dos avisos que viajan en los datos:

    · **Madurez.** Las últimas cohortes tuvieron menos tiempo para retener, así
      que su curva está truncada. Comparar la cohorte de hace dos meses con la
      de hace dos años sin marcarlo es comparar una película con su primer
      minuto. Sale `periodos_observables` y `madura`.
    · **Origen.** Se separan los clientes cuya PRIMERA compra cayó dentro de una
      campaña de los que entraron fuera. Si los de campaña retienen mucho peor,
      la campaña compra volumen y no clientes — y eso cambia por completo
      cuánto vale una campaña de captación.
    """
    c = cfg.get("cohortes") or {}
    gran = str(c.get("granularidad", "mensual")).lower()
    freq = {"mensual": "MS", "semanal": "W-MON", "trimestral": "QS"}.get(gran)
    if freq is None:
        raise CampanaError(f"`cohortes.granularidad` «{gran}» no es mensual, semanal ni trimestral")
    max_p = int(c.get("periodos", 6))

    v = d[[cliente, "_fecha", m["unidades"], m["importe"]]].copy()
    v["periodo"] = v["_fecha"].dt.to_period({"MS": "M", "W-MON": "W", "QS": "Q"}[freq]).dt.start_time
    primera = v.groupby(cliente)["periodo"].min().rename("cohorte")
    primera_fecha = v.groupby(cliente)["_fecha"].min().rename("primera_fecha")
    v = v.join(primera, on=cliente).join(primera_fecha, on=cliente)
    paso = {"MS": "M", "W-MON": "W", "QS": "Q"}[freq]
    v["nro"] = ((v["periodo"].dt.to_period(paso) - v["cohorte"].dt.to_period(paso)).apply(lambda x: x.n))
    ultimo = v["periodo"].max()

    tam = v.groupby("cohorte")[cliente].nunique().rename("clientes_cohorte")
    ret = (v[v["nro"].between(0, max_p)]
           .groupby(["cohorte", "nro"])
           .agg(clientes=(cliente, "nunique"), unidades=(m["unidades"], "sum"), importe=(m["importe"], "sum"))
           .reset_index().join(tam, on="cohorte"))
    ret["retencion_pct"] = (ret["clientes"] / ret["clientes_cohorte"] * 100).round(2)
    ret["periodos_observables"] = ret["cohorte"].map(
        lambda x: int((ultimo.to_period(paso) - x.to_period(paso)).n))
    ret["madura"] = ret["periodos_observables"] >= max_p
    ret["muestra_chica"] = ret["clientes_cohorte"] < COHORTE_MINIMA
    ret["importe"] = ret["importe"].round(2)
    ret["cohorte"] = ret["cohorte"].dt.date.astype(str)

    # Origen: primera compra dentro de una campaña o fuera de toda campaña.
    rangos = [(r["desde"], r["hasta"], r["campana"]) for _, r in cal.iterrows()]

    def origen(f):
        for a, b, nombre in rangos:
            if a <= f <= b:
                return f"campaña: {nombre}"
        return "fuera de campaña"

    pf = v.groupby(cliente)["primera_fecha"].min()
    ori = pf.map(origen).rename("origen")
    v2 = v.join(ori, on=cliente)
    tam2 = v2.groupby("origen")[cliente].nunique().rename("clientes_origen")
    og = (v2[v2["nro"].between(0, max_p)]
          .groupby(["origen", "nro"])
          .agg(clientes=(cliente, "nunique"), importe=(m["importe"], "sum"))
          .reset_index().join(tam2, on="origen"))
    og["retencion_pct"] = (og["clientes"] / og["clientes_origen"] * 100).round(2)
    og["muestra_chica"] = og["clientes_origen"] < COHORTE_MINIMA
    og["importe"] = og["importe"].round(2)
    return ret, og


# ------------------------------------------------------------------ entrada
def correr(df: pd.DataFrame, cfg: dict, tablas: dict | None = None) -> dict:
    """Corre el análisis completo y devuelve tablas + resumen.

    `tablas` es el diccionario de tablas disponibles (gold y silver): de ahí
    salen el calendario de campañas, el alcance y el stock.
    """
    tablas = tablas or {}
    d, prep = _preparar(df, cfg)
    m = prep["medidas"]
    notas: list[str] = []
    if prep["fechas_invalidas"]:
        notas.append(f"{prep['fechas_invalidas']} fila(s) sin fecha válida quedaron fuera del análisis")

    c = cfg.get("calendario") or {}
    cal_tabla = tablas.get(c.get("tabla"))
    if cal_tabla is None:
        raise CampanaError("`campanas.calendario.tabla` es obligatorio: sin calendario de campañas no hay qué medir")
    cal = _calendario(cal_tabla, c)

    producto = cfg.get("producto")
    if producto:
        producto = _col(d, producto, "la columna de producto (`producto`)")
    cliente = cfg.get("cliente")
    if cliente:
        cliente = _col(d, cliente, "la columna de cliente (`cliente`)")
    hay_margen = bool(m.get("costo"))
    if not hay_margen:
        notas.append("sin `medidas.costo`: no se puede medir rentabilidad, y el veredicto se decide por unidades")

    alcance = _alcance(cfg, tablas, producto) if producto else None
    if alcance is None:
        notas.append("sin `calendario.alcance_tabla` pasan dos cosas, las dos a favor de la campaña: se mide la "
                     "venta TOTAL de la ventana y no sólo la de los productos en campaña, y no hay grupo de "
                     "control, así que el efecto NO descuenta la estacionalidad (`metodo: baseline`)")
    stock = _stock(cfg, tablas, cal, producto) if producto else pd.DataFrame()
    if stock.empty and (cfg.get("stock") or {}).get("tabla"):
        notas.append("la tabla de stock no tiene datos en las ventanas de campaña")

    segmentos = [s for s in (cfg.get("segmento") or []) if s in d.columns]
    faltantes = [s for s in (cfg.get("segmento") or []) if s not in d.columns]
    if faltantes:
        raise CampanaError(f"segmento(s) declarado(s) que no están en el set: {faltantes}")

    # ---- panel y efecto, total y por segmento ----
    panel_filas, efecto_filas = [], []
    for _, e in cal.iterrows():
        w = ventanas(e["desde"], e["hasta"], cfg)
        cortes = [("TOTAL", "TOTAL", d)]
        for s in segmentos:
            for valor, sub in d.groupby(s, sort=False):
                cortes.append((s, str(valor), sub))
        decl = None
        if alcance is not None and producto:
            decl = set(alcance[(alcance["campana"] == e["campana"])
                               & (alcance["edicion"] == e["edicion"])]["producto"])
        for dim, valor, base in cortes:
            # Dos grupos: los SKU de la campaña y los que quedaron afuera. El
            # segundo es el control que descuenta la estacionalidad, y sólo
            # existe si el proyecto declaró el alcance de la campaña.
            if decl:
                trat_base = base[base[producto].isin(decl)]
                ctrl_base = base[~base[producto].isin(decl)]
            else:
                trat_base, ctrl_base = base, None
            paneles, paneles_ctrl = {}, ({} if ctrl_base is not None else None)
            for nombre in ("baseline", "blackout", "durante", "arrastre"):
                rango = w[nombre]
                dias_v = _dias(rango)
                med = _medir(_en(trat_base, "_fecha", rango), m, dias_v, cliente)
                paneles[nombre] = med
                grupos = [("campaña", med)]
                if ctrl_base is not None:
                    med_c = _medir(_en(ctrl_base, "_fecha", rango), m, dias_v, cliente)
                    paneles_ctrl[nombre] = med_c
                    grupos.append(("control", med_c))
                for grupo, valores in grupos:
                    panel_filas.append({"campana": e["campana"], "edicion": e["edicion"],
                                        "dimension": dim, "valor": valor, "grupo": grupo, "ventana": nombre,
                                        "desde": None if rango is None else str(rango[0].date()),
                                        "hasta": None if rango is None else str(rango[1].date()), **valores})
            ef = _efecto_de(paneles, paneles_ctrl, hay_margen)
            efecto_filas.append({"campana": e["campana"], "edicion": e["edicion"],
                                 "dimension": dim, "valor": valor,
                                 "desde": str(e["desde"].date()), "hasta": str(e["hasta"].date()), **ef})

    panel = pd.DataFrame(panel_filas)
    efecto = pd.DataFrame(efecto_filas)
    vs_ed = _vs_ediciones(d, m, producto, cal, cfg, alcance, stock, cliente) if producto else pd.DataFrame()
    precios = _precios(d, m, producto, cal, cfg, alcance) if producto else pd.DataFrame()

    rfm, rfm_meta, rfm_alc = pd.DataFrame(), {}, pd.DataFrame()
    cohortes, cohortes_origen = pd.DataFrame(), pd.DataFrame()
    if cliente:
        rfm, rfm_meta = _rfm(d, m, cliente, cfg, d["_fecha"].max())
        rfm_alc = _rfm_alcance(d, m, cliente, rfm, cal)
        cohortes, cohortes_origen = _cohortes(d, m, cliente, cfg, cal)
    else:
        notas.append("sin `cliente`: no se calculan RFM ni cohortes")

    # ---- lo que hay que mirar primero ----
    solo_total = efecto[efecto["dimension"] == "TOTAL"] if len(efecto) else efecto
    alertas = []
    if len(solo_total):
        for _, r in solo_total.iterrows():
            if r["veredicto"] in ("adelanto", "vendio_mas_gano_menos", "peor", "no_comparable"):
                alertas.append({"campana": r["campana"], "edicion": r["edicion"],
                                "veredicto": r["veredicto"], "porque": r["porque"]})
    if len(precios):
        # Una alerta por EDICIÓN, no por SKU: 62 líneas diciendo lo mismo es la
        # forma más rápida de que nadie lea las alertas.
        infl = precios[precios["precio_inflado_antes"]]
        for (camp, ed), g in infl.groupby(["campana", "edicion"]):
            alertas.append({
                "campana": camp, "edicion": ed, "veredicto": "descuento_inflado",
                "porque": (f"{len(g)} SKU con el precio subido antes de la campaña (mediana +"
                           f"{_r(g['suba_previa_pct'].median())} %): el descuento real es "
                           f"{_r(g['descuento_real_pct'].median())} % y no {_r(g['descuento_aparente_pct'].median())} %, "
                           f"o sea {_r(g['puntos_inflados'].median())} puntos fabricados. Ejemplos: "
                           + ", ".join(g["producto"].head(3)))})
    if len(cohortes_origen):
        chicas = cohortes_origen[cohortes_origen["muestra_chica"]]["origen"].unique()
        if len(chicas):
            alertas.append({"campana": "—", "edicion": "—", "veredicto": "cohorte_muestra_chica",
                            "porque": f"{len(chicas)} origen(es) con menos de {COHORTE_MINIMA} clientes "
                                      f"({', '.join(map(str, chicas[:3]))}): su retención puede dar 100 % por el "
                                      "tamaño y no por el comportamiento — no comparar sin mirar el denominador"})
    if len(stock):
        cens = stock[stock["medicion_censurada"]]
        if len(cens):
            alertas.append({"campana": "—", "edicion": "—", "veredicto": "medicion_censurada",
                            "porque": f"{len(cens)} producto(s)-edición con quiebre de stock durante la campaña: "
                                      "sus unidades son un piso y quedaron fuera del like-for-like"})

    resumen = {
        "campanas": int(cal["campana"].nunique()),
        "ediciones": int(len(cal)),
        "con_edicion_anterior": int(len(vs_ed[vs_ed["relacion"] == "anterior"])) if len(vs_ed) else 0,
        "segmentos": segmentos,
        "rentabilidad_medida": hay_margen,
        "ventana": {"baseline_dias": _dias(ventanas(cal.iloc[0]["desde"], cal.iloc[0]["hasta"], cfg)["baseline"]),
                    "blackout_dias": _dias(ventanas(cal.iloc[0]["desde"], cal.iloc[0]["hasta"], cfg)["blackout"]),
                    "arrastre_dias": _dias(ventanas(cal.iloc[0]["desde"], cal.iloc[0]["hasta"], cfg)["arrastre"])},
        "rfm": rfm_meta,
        "alertas": alertas,
        "notas": notas,
    }
    return {
        "resumen": resumen,
        "tablas": {
            "campanas_panel": panel,
            "campanas_efecto": efecto,
            "campanas_vs_edicion": vs_ed,
            "campanas_precio": precios,
            "campanas_stock": stock,
            "campanas_rfm": rfm,
            "campanas_rfm_alcance": rfm_alc,
            "campanas_cohortes": cohortes,
            "campanas_cohortes_origen": cohortes_origen,
        },
    }
