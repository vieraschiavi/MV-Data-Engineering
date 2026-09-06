# © 2026 Martín Viera. Todos los derechos reservados.
"""Proyección de series de tiempo con backtest honesto, y TimesFM como backend
opcional.

La pregunta que este módulo contesta no es «¿puedo correr un modelo grande?»
sino «¿le gana al tonto?». El tonto es la **estacional ingenua**: repetir lo
que pasó el mismo mes del año pasado. En series mensuales de negocio, con doce
o veinticuatro puntos, ese tonto le gana seguido a modelos enormes. Por eso
acá el backtest no es un adorno del final: es lo que elige el modelo, y todo
backend se reporta con su mejora (o su pérdida) contra esa referencia.

**Backtest de origen móvil (rolling origin).** Se corta la serie en varios
puntos del pasado; en cada corte se entrena SOLO con lo anterior al corte y se
predice el horizonte siguiente, que se compara con lo que realmente pasó.
Nunca entra un dato posterior al corte: eso es lo que separa un backtest de
una demostración.

**TimesFM** (Google Research) entra como un backend más, opcional:

- Necesita `torch` y bajar el checkpoint de Hugging Face. No está en
  `requirements.txt` a propósito: son gigabytes que la mayoría de los
  proyectos no necesita.
- **Licencia**: el código es Apache-2.0 y los pesos **hasta la 2.5 también**,
  pero los de la 3.0 salen bajo `timesfm-non-commercial-license-v1.0`, que
  prohíbe el uso comercial y en producción. Este módulo usa 2.5 por defecto y
  se niega a cargar los pesos 3.0 salvo que se declare explícitamente que el
  uso es de investigación (`permitir_no_comercial=True`).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import metodos_serie

log = logging.getLogger("mvde")

# Cuántos períodos tiene un ciclo, según la frecuencia de la serie.
ESTACIONALIDAD = {"diaria": 7, "semanal": 52, "mensual": 12, "trimestral": 4, "anual": 1}
METRICAS = ("mae", "rmse", "smape", "mape")
REFERENCIA = "naive_estacional"

# Pesos de TimesFM cuya licencia permite uso comercial y en producción
# (Apache-2.0, igual que el código). Verificado en el README del repo oficial.
PESOS_COMERCIALES = {
    "google/timesfm-2.5-200m-pytorch", "google/timesfm-2.5-200m-flax",
    "google/timesfm-2.5-200m-transformers", "google/timesfm-2.0-500m-pytorch",
    "google/timesfm-2.0-500m-jax", "google/timesfm-1.0-200m-pytorch", "google/timesfm-1.0-200m",
}
# Los de la 3.0 son `timesfm-non-commercial-license-v1.0`: investigación sí,
# producción no. Cargarlos sin querer en un despliegue de cliente es un
# problema legal, no un detalle técnico.
PESOS_NO_COMERCIALES = {"google/timesfm-3.0-pytorch"}
CHECKPOINT_DEFECTO = "google/timesfm-2.5-200m-pytorch"


# ------------------------------------------------------------------ la serie
def _fechas(col: pd.Series) -> pd.Series:
    """Las tablas de hechos de gold no guardan la fecha: guardan `fecha_key`,
    un entero AAAAMMDD. Interpretarlo como número de nanosegundos da 1970 y
    arruina la serie en silencio, así que se convierte por formato."""
    if pd.api.types.is_numeric_dtype(col):
        n = pd.to_numeric(col, errors="coerce")
        if n.dropna().between(19000101, 29991231).all() and not n.dropna().empty:
            return pd.to_datetime(n.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
    return pd.to_datetime(col, errors="coerce")


def serie(df: pd.DataFrame, fecha: str, valor: str, frecuencia: str = "mensual",
          agregacion: str = "sum") -> pd.DataFrame:
    """De una tabla de hechos a una serie regular, un renglón por período.

    Completa los períodos sin datos con 0: un mes sin ventas es un cero, no un
    agujero, y saltearlo desplaza toda la estacionalidad."""
    if fecha not in df.columns or valor not in df.columns:
        raise ValueError(f"la serie necesita «{fecha}» y «{valor}» en la tabla")
    regla = {"diaria": "D", "semanal": "W", "mensual": "MS", "trimestral": "QS", "anual": "YS"}
    if frecuencia not in regla:
        raise ValueError(f"frecuencia «{frecuencia}» desconocida; válidas: {sorted(regla)}")
    d = pd.DataFrame({"fecha": _fechas(df[fecha]),
                      "valor": pd.to_numeric(df[valor], errors="coerce")}).dropna(subset=["fecha"])
    if d.empty:
        raise ValueError(f"«{fecha}» no tiene fechas válidas")
    s = d.set_index("fecha")["valor"].resample(regla[frecuencia]).agg(agregacion).fillna(0.0)
    return pd.DataFrame({"periodo": s.index, "valor": s.to_numpy(dtype=float)})


# ------------------------------------------------------------------ backends
def _naive(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
    return np.repeat(historia[-1], horizonte)


def _naive_estacional(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
    """El mismo período del ciclo anterior. Es la referencia contra la que se
    mide todo lo demás."""
    if m <= 1 or len(historia) < m:
        return _naive(historia, horizonte, m)
    ciclo = historia[-m:]
    return np.array([ciclo[i % m] for i in range(horizonte)], dtype=float)


def _media_movil(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
    ventana = min(len(historia), max(3, m))
    return np.repeat(float(np.mean(historia[-ventana:])), horizonte)


def _drift(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
    """Último valor más la pendiente promedio de toda la historia."""
    if len(historia) < 2:
        return _naive(historia, horizonte, m)
    pendiente = (historia[-1] - historia[0]) / (len(historia) - 1)
    return historia[-1] + pendiente * np.arange(1, horizonte + 1)


# Cuántos ciclos mira la regresión hacia atrás. La tendencia que importa para
# predecir la semana que viene es la de los últimos meses, no la del año
# entero: con toda la historia, una serie con estacionalidad anual arrastra la
# recta de la temporada alta a la baja y proyecta un desplome que no existe.
CICLOS_TENDENCIA = 8


def _tendencia_estacional(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
    """Regresión con tendencia lineal LOCAL y una variable por posición del
    ciclo. Es lo mínimo que captura «crece y además tiene estacionalidad»."""
    n = len(historia)
    if m <= 1 or n < 2 * m:
        return _drift(historia, horizonte, m)
    from sklearn.linear_model import LinearRegression
    corte = max(0, n - CICLOS_TENDENCIA * m)       # ventana local, y el desfase se mantiene con t % m
    y = historia[corte:]
    t = np.arange(corte, n)
    est = np.zeros((len(y), m))
    est[np.arange(len(y)), t % m] = 1.0
    X = np.column_stack([t, est[:, 1:]])           # se omite una para no duplicar el intercepto
    modelo = LinearRegression().fit(X, y)
    tf = np.arange(n, n + horizonte)
    estf = np.zeros((horizonte, m))
    estf[np.arange(horizonte), tf % m] = 1.0
    return modelo.predict(np.column_stack([tf, estf[:, 1:]]))


# Rejilla de suavizados que se prueba dentro de la historia de cada corte.
# Chica a propósito: con doce o veinticuatro puntos, buscar fino es ajustar
# ruido. Nunca ve un dato posterior al corte.
_ALFAS = (0.1, 0.3, 0.5, 0.8)
_BETAS = (0.0, 0.05, 0.2)
_GAMMAS = (0.0, 0.1, 0.3)


def _hw_ajuste(y: np.ndarray, m: int, alfa: float, beta: float, gamma: float):
    """Holt-Winters aditivo, escrito a mano sobre numpy.

    Está acá y no vía statsmodels porque agregar una dependencia de ese porte
    para veinte líneas de recursión no se justifica: el motor ya arrastra
    pandas, numpy y scikit-learn."""
    nivel = float(np.mean(y[:m]))
    tendencia = float((np.mean(y[m:2 * m]) - np.mean(y[:m])) / m) if len(y) >= 2 * m else 0.0
    estacional = [float(v - nivel) for v in y[:m]]
    sse = 0.0
    for i in range(m, len(y)):
        s_i = estacional[i - m]
        pred = nivel + tendencia + s_i
        sse += (y[i] - pred) ** 2
        nivel_previo = nivel
        nivel = alfa * (y[i] - s_i) + (1 - alfa) * (nivel + tendencia)
        tendencia = beta * (nivel - nivel_previo) + (1 - beta) * tendencia
        estacional.append(gamma * (y[i] - nivel) + (1 - gamma) * s_i)
    return nivel, tendencia, estacional, sse


def _holt_winters(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
    """Nivel, tendencia y estacionalidad que se actualizan en cada período.
    Es el caballo de batalla de las series de negocio y la referencia que
    cualquier modelo grande tiene que superar para justificarse."""
    n = len(historia)
    if m <= 1 or n < 2 * m + 1:
        return _naive_estacional(historia, horizonte, m)
    mejor, mejor_sse = None, np.inf
    for alfa in _ALFAS:
        for beta in _BETAS:
            for gamma in _GAMMAS:
                ajuste = _hw_ajuste(historia, m, alfa, beta, gamma)
                if np.isfinite(ajuste[3]) and ajuste[3] < mejor_sse:
                    mejor, mejor_sse = ajuste, ajuste[3]
    if mejor is None:
        return _naive_estacional(historia, horizonte, m)
    nivel, tendencia, estacional, _ = mejor
    return np.array([nivel + tendencia * (h + 1) + estacional[len(estacional) - m + (h % m)]
                     for h in range(horizonte)], dtype=float)


BACKENDS_BASE = {
    "naive": _naive,
    "naive_estacional": _naive_estacional,
    "media_movil": _media_movil,
    "drift": _drift,
    "tendencia_estacional": _tendencia_estacional,
    "holt_winters": _holt_winters,
    # Los ocho métodos portados del motor de proyecciones de cobranzas
    # (YoY, MoM, Theta, reversión a la media, tendencia amortiguada, ciclo con
    # decaimiento, pendiente del ciclo, factor anual). Compiten de igual a
    # igual: acá ninguno entra por decreto.
    **metodos_serie.BACKENDS,
}

# El ensemble no es un método más: se arma DESPUÉS del backtest, ponderando a
# cada método por lo que acertó. Por eso vive aparte de BACKENDS_BASE.
ENSEMBLE = "ensemble"


# ------------------------------------------------------------------ TimesFM
def timesfm_disponible() -> tuple[bool, str]:
    """(disponible, motivo). El motivo se muestra tal cual en la app."""
    try:
        import timesfm  # noqa: F401
    except ImportError:
        return False, "falta el paquete `timesfm` (pip install timesfm[torch])"
    try:
        import torch  # noqa: F401
    except ImportError:
        return False, "falta `torch` (pip install torch)"
    return True, "disponible"


def backend_timesfm(checkpoint: str = CHECKPOINT_DEFECTO, contexto_maximo: int = 512,
                    permitir_no_comercial: bool = False):
    """Devuelve un backend TimesFM listo para el backtest.

    Carga el checkpoint UNA vez y lo reusa en todos los orígenes del backtest:
    bajar y compilar el modelo en cada corte multiplica por N el tiempo sin
    cambiar un solo número del resultado."""
    if checkpoint in PESOS_NO_COMERCIALES and not permitir_no_comercial:
        raise RuntimeError(
            f"Los pesos «{checkpoint}» son `timesfm-non-commercial-license-v1.0`: "
            "prohíben el uso comercial y en producción. Para vender o desplegar en un "
            f"cliente usá «{CHECKPOINT_DEFECTO}» (Apache-2.0). Si esto es investigación, "
            "pasá permitir_no_comercial=True y dejalo escrito en el proyecto.")
    if checkpoint not in PESOS_COMERCIALES and checkpoint not in PESOS_NO_COMERCIALES:
        log.warning("MVDE: checkpoint «%s» desconocido; verificá su licencia antes de producción", checkpoint)
    ok, motivo = timesfm_disponible()
    if not ok:
        raise RuntimeError(f"TimesFM no está instalado: {motivo}")

    import timesfm
    modelo = timesfm.TimesFM_2p5_200M_torch.from_pretrained(checkpoint)
    compilado = {"horizonte": None}

    def predecir(historia: np.ndarray, horizonte: int, m: int) -> np.ndarray:
        if compilado["horizonte"] != horizonte:
            modelo.compile(timesfm.ForecastConfig(
                max_context=contexto_maximo, max_horizon=horizonte,
                normalize_inputs=True, use_continuous_quantile_head=True))
            compilado["horizonte"] = horizonte
        punto, _cuantiles = modelo.forecast(horizonte, inputs=[np.asarray(historia, dtype=np.float32)])
        return np.asarray(punto[0], dtype=float)[:horizonte]

    return predecir


# ------------------------------------------------------------------ métricas
def _metricas(real: np.ndarray, pred: np.ndarray) -> dict:
    real, pred = np.asarray(real, dtype=float), np.asarray(pred, dtype=float)
    err = pred - real
    fuera = {"mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2)))}
    # sMAPE aguanta ceros; MAPE no, así que sólo se reporta cuando se puede.
    denom = (np.abs(real) + np.abs(pred)) / 2
    fuera["smape"] = float(np.mean(np.where(denom == 0, 0.0, np.abs(err) / np.where(denom == 0, 1, denom))) * 100)
    fuera["mape"] = float(np.mean(np.abs(err[real != 0] / real[real != 0])) * 100) if (real != 0).all() else None
    return fuera


# ------------------------------------------------------------------ backtest
def origenes_posibles(n: int, horizonte: int, m: int, minimo_historia: int | None = None) -> int:
    """Cuántos cortes de backtest entran en la serie sin dejar la primera
    ventana de entrenamiento demasiado corta."""
    minimo = minimo_historia if minimo_historia is not None else max(2 * m, horizonte + 2)
    return max(0, n - horizonte - minimo + 1)


def backtest(valores, horizonte: int = 3, estacionalidad: int = 12, origenes: int = 6,
             backends: dict | None = None, minimo_historia: int | None = None,
             con_ensemble: bool = True) -> dict:
    """Origen móvil: en cada corte se entrena con el pasado y se mide contra el
    futuro real. Devuelve una fila por backend con sus métricas promedio y la
    mejora contra la estacional ingenua."""
    v = np.asarray(valores, dtype=float)
    n = len(v)
    usables = origenes_posibles(n, horizonte, estacionalidad, minimo_historia)
    if usables <= 0:
        raise ValueError(
            f"la serie tiene {n} períodos y no alcanza para un backtest de horizonte {horizonte} "
            f"con estacionalidad {estacionalidad}: hacen falta al menos "
            f"{(minimo_historia if minimo_historia is not None else max(2 * estacionalidad, horizonte + 2)) + horizonte}. "
            "Con menos, cualquier número que se reporte es ruido.")
    usados = min(origenes, usables)
    cortes = [n - horizonte - k for k in range(usados - 1, -1, -1)]
    backends = backends or dict(BACKENDS_BASE)

    filas, detalle = [], []
    for nombre, fn in backends.items():
        por_corte, errores = [], []
        for corte in cortes:
            historia, real = v[:corte], v[corte:corte + horizonte]
            try:
                pred = np.asarray(fn(historia, horizonte, estacionalidad), dtype=float)
            except Exception as exc:  # noqa: BLE001 - un backend que falla no tumba el backtest
                errores.append(f"{type(exc).__name__}: {exc}")
                continue
            if len(pred) != horizonte or not np.all(np.isfinite(pred)):
                errores.append(f"devolvió {len(pred)} valores o no finitos")
                continue
            m_corte = _metricas(real, pred)
            por_corte.append(m_corte)
            detalle.append({"backend": nombre, "corte": int(corte), "desde": int(corte - len(historia)),
                            "real": real.tolist(), "pred": pred.tolist(), **m_corte})
        if not por_corte:
            filas.append({"backend": nombre, "origenes": 0, "error": errores[0] if errores else "sin resultados"})
            continue
        prom = {k: (float(np.mean([c[k] for c in por_corte if c[k] is not None]))
                    if any(c[k] is not None for c in por_corte) else None) for k in METRICAS}
        filas.append({"backend": nombre, "origenes": len(por_corte), **prom,
                      **({"error": errores[0]} if errores else {})})

    bt = {"horizonte": horizonte, "estacionalidad": estacionalidad, "periodos": n,
          "origenes": usados, "origenes_posibles": usables, "cortes": cortes,
          "resultados": filas, "detalle": detalle, "referencia": REFERENCIA, "pesos_ensemble": {}}
    if con_ensemble and len(cortes) >= 2:
        fila_ens, pesos, detalle_ens = _ensemble_backtest(bt)
        if fila_ens:
            filas.append(fila_ens)
            detalle.extend(detalle_ens)                # así el ensemble también tiene bandas y real vs proyectado
            bt["pesos_ensemble"] = {k: round(v, 4) for k, v in sorted(pesos.items(), key=lambda x: -x[1])}

    ref = next((f for f in filas if f["backend"] == REFERENCIA and f.get("mae") is not None), None)
    for f in filas:
        f["mejora_vs_referencia_pct"] = (
            round(100 * (ref["mae"] - f["mae"]) / ref["mae"], 1)
            if ref and f.get("mae") is not None and ref["mae"] > 0 else None)
    return bt


def _pesos_inverso(maes: dict, potencia: float = 1.0) -> dict:
    """Peso por método: cuanto menos se equivocó, más pesa. Es la misma idea de
    `1/MAPE` del motor original, con una diferencia que importa: acá los
    números salen del backtest de ESTA serie, no de una tabla escrita a mano
    con los segmentos de una empresa."""
    validos = {k: max(float(v), 1e-9) for k, v in maes.items() if v is not None and np.isfinite(v)}
    if not validos:
        return {}
    inv = {k: (1.0 / v) ** potencia for k, v in validos.items()}
    total = sum(inv.values())
    return {k: v / total for k, v in inv.items()}


def _ensemble_backtest(bt: dict, metrica: str = "mae") -> tuple[dict | None, dict, list[dict]]:
    """Evalúa el ensemble SIN hacerse trampa: en cada corte los pesos salen
    únicamente de los cortes anteriores.

    Ponderar con el resultado del mismo corte que se está midiendo infla la
    precisión y es el error más común al vender un ensemble. Por eso el primer
    corte no se usa: todavía no hay pasado con qué ponderar."""
    por_corte: dict[int, dict[str, dict]] = {}
    for d in bt["detalle"]:
        por_corte.setdefault(d["corte"], {})[d["backend"]] = d
    cortes = sorted(por_corte)
    filas, previos = [], []
    for j, corte in enumerate(cortes):
        if j == 0:
            continue
        maes = {}
        for b in por_corte[corte]:
            errs = [por_corte[c][b]["mae"] for c in cortes[:j] if b in por_corte[c]]
            if errs:
                maes[b] = float(np.mean(errs))
        pesos = _pesos_inverso(maes)
        if not pesos:
            continue
        real = np.asarray(por_corte[corte][next(iter(pesos))]["real"], dtype=float)
        pred = np.zeros(len(real))
        for b, w in pesos.items():
            pred = pred + w * np.asarray(por_corte[corte][b]["pred"], dtype=float)
        m_corte = _metricas(real, pred)
        filas.append({"backend": ENSEMBLE, "corte": corte, "real": real.tolist(),
                      "pred": pred.tolist(), **m_corte})
        previos.append(m_corte)
    if not previos:
        return None, {}, []
    prom = {k: (float(np.mean([c[k] for c in previos if c[k] is not None]))
                if any(c[k] is not None for c in previos) else None) for k in METRICAS}
    # Los pesos que se usan para proyectar el futuro sí miran todos los cortes:
    # ahí ya no se está midiendo nada, se está eligiendo con todo lo que hay.
    finales = _pesos_inverso({f["backend"]: f.get(metrica) for f in bt["resultados"]
                              if f["backend"] != ENSEMBLE})
    return ({"backend": ENSEMBLE, "origenes": len(previos), **prom,
             "pesos": {k: round(v, 4) for k, v in sorted(finales.items(), key=lambda x: -x[1])}},
            finales, filas)


def bandas(bt: dict, backend: str, nivel: float = 0.8) -> list[dict]:
    """Niveles de desvío por paso del horizonte, medidos — no supuestos.

    Se toma el error relativo que ese método tuvo en cada corte del backtest,
    paso por paso (el mes 1 se falla menos que el mes 6), y se reportan sus
    percentiles. No hay campana de Gauss acá: si la serie falló feo tres veces,
    la banda es ancha, y eso es exactamente lo que hay que mostrarle a quien
    mira la proyección."""
    if not 0 < nivel < 1:
        raise ValueError("el nivel de la banda va entre 0 y 1 (0.8 = 80 %)")
    q_bajo, q_alto = (1 - nivel) / 2, 1 - (1 - nivel) / 2
    por_paso: dict[int, list[float]] = {}
    for d in bt["detalle"]:
        if d["backend"] != backend:
            continue
        for h, (real, pred) in enumerate(zip(d["real"], d["pred"])):
            if real:                                   # el error relativo no existe contra un cero
                por_paso.setdefault(h, []).append((pred - real) / abs(real))
    fuera = []
    for h in range(bt["horizonte"]):
        errs = np.array(por_paso.get(h, []), dtype=float)
        if len(errs) < 2:
            fuera.append({"paso": h + 1, "n": int(len(errs)), "bajo": None, "alto": None, "sesgo": None})
            continue
        fuera.append({"paso": h + 1, "n": int(len(errs)),
                      "bajo": float(np.quantile(errs, q_bajo)), "alto": float(np.quantile(errs, q_alto)),
                      "sesgo": float(np.median(errs)),
                      "mae_rel": float(np.mean(np.abs(errs)))})
    return fuera


def aplicar_bandas(pred: np.ndarray, bandas_: list[dict]) -> pd.DataFrame:
    """La proyección con su piso y su techo. El error medido se resta, no se
    suma: si el método viene tirando 8 % alto, la banda baja va 8 % abajo."""
    bajo, alto = [], []
    for i, v in enumerate(pred):
        b = bandas_[i] if i < len(bandas_) else {}
        bajo.append(v / (1 + b["alto"]) if b.get("alto") is not None and 1 + b["alto"] > 0 else None)
        alto.append(v / (1 + b["bajo"]) if b.get("bajo") is not None and 1 + b["bajo"] > 0 else None)
    return pd.DataFrame({"valor": pred, "banda_baja": bajo, "banda_alta": alto})


def real_vs_proyectado(bt: dict, backend: str, periodos: pd.Series | None = None) -> pd.DataFrame:
    """Lo que el método habría dicho en cada corte contra lo que realmente pasó.

    Es el gráfico que convence: no es la proyección al futuro (que nadie puede
    verificar todavía), es el pronóstico de un pasado que ya se conoce."""
    filas = []
    for d in sorted((x for x in bt["detalle"] if x["backend"] == backend), key=lambda x: x["corte"]):
        for h, (real, pred) in enumerate(zip(d["real"], d["pred"])):
            i = d["corte"] + h
            filas.append({"corte": d["corte"], "paso": h + 1, "indice": i,
                          "periodo": periodos.iloc[i] if periodos is not None and i < len(periodos) else None,
                          "real": float(real), "proyectado": float(pred),
                          "desvio": float(pred - real),
                          "desvio_pct": float(100 * (pred - real) / real) if real else None})
    return pd.DataFrame(filas)


def elegir(bt: dict, metrica: str = "mae") -> dict:
    """El mejor backend, y si le gana o no a la estacional ingenua.

    Si nadie le gana al tonto, lo dice: en ese caso lo honesto es proyectar con
    la referencia y no con un modelo que agrega complejidad sin agregar
    precisión."""
    if metrica not in METRICAS:
        raise ValueError(f"métrica «{metrica}» desconocida; válidas: {sorted(METRICAS)}")
    validos = [f for f in bt["resultados"] if f.get(metrica) is not None]
    if not validos:
        raise ValueError("ningún backend produjo una proyección utilizable")
    mejor = min(validos, key=lambda f: f[metrica])
    referencia = next((f for f in validos if f["backend"] == REFERENCIA), None)
    gana = bool(referencia and mejor["backend"] != REFERENCIA and mejor[metrica] < referencia[metrica])
    return {"backend": mejor["backend"], "metrica": metrica, "valor": mejor[metrica],
            "referencia": REFERENCIA,
            "valor_referencia": referencia[metrica] if referencia else None,
            "mejora_pct": mejor.get("mejora_vs_referencia_pct"),
            "le_gana_a_la_referencia": gana,
            "comparacion": sorted(validos, key=lambda f: f[metrica])}


def proyectar(valores, horizonte: int, backend: str, estacionalidad: int = 12,
              backends: dict | None = None, pesos: dict | None = None) -> np.ndarray:
    """El pronóstico final, con toda la historia disponible."""
    fns = backends or dict(BACKENDS_BASE)
    v = np.asarray(valores, dtype=float)
    if backend == ENSEMBLE:
        if not pesos:
            raise ValueError("el ensemble necesita los pesos que midió el backtest")
        # Se renormaliza: los pesos que se guardan vienen redondeados para
        # mostrarlos, y un 0,02 % de escala perdida no tiene por qué llegar al
        # número que después se planifica.
        total = sum(pesos.values())
        salida = np.zeros(horizonte)
        for b, w in pesos.items():
            salida = salida + (w / total) * np.asarray(fns[b](v, horizonte, estacionalidad), dtype=float)
        return salida
    if backend not in fns:
        raise ValueError(f"backend «{backend}» no registrado; hay: {sorted(fns)}")
    return np.asarray(fns[backend](v, horizonte, estacionalidad), dtype=float)


def periodos_futuros(ultimo: pd.Timestamp, horizonte: int, frecuencia: str = "mensual") -> list[pd.Timestamp]:
    paso = {"diaria": pd.DateOffset(days=1), "semanal": pd.DateOffset(weeks=1),
            "mensual": pd.DateOffset(months=1), "trimestral": pd.DateOffset(months=3),
            "anual": pd.DateOffset(years=1)}[frecuencia]
    return [pd.Timestamp(ultimo) + paso * (i + 1) for i in range(horizonte)]


# ------------------------------------------------------------------ todo junto
# Cuántos días cubre cada paso del horizonte, para hablar en el idioma del
# negocio: en cobranzas nadie pide «6 períodos», pide 30/60/90/120/150/180 días.
DIAS_POR_PERIODO = {"diaria": 1, "semanal": 7, "mensual": 30, "trimestral": 90, "anual": 365}
MINIMO_PERIODOS = 24


AVISO_NO_COMERCIAL = (
    "ATENCIÓN · esta corrida usó pesos «{checkpoint}» bajo "
    "timesfm-non-commercial-license-v1.0: investigación sí, uso comercial y en "
    "producción NO. Esta salida no se entrega a un cliente ni se despliega. "
    "Para eso hay que volver a correr con un checkpoint Apache-2.0 "
    "(por ejemplo «{comercial}»).")


def _backends_de(cfg: dict) -> tuple[dict, list[str]]:
    """Los métodos que van a competir, más TimesFM si el YAML lo pide y se puede."""
    backends, notas = dict(BACKENDS_BASE), []
    if not cfg.get("timesfm"):
        return backends, notas
    tf = cfg["timesfm"] if isinstance(cfg["timesfm"], dict) else {}
    checkpoint = tf.get("checkpoint", CHECKPOINT_DEFECTO)
    try:
        backends["timesfm"] = backend_timesfm(checkpoint, int(tf.get("contexto_maximo", 512)),
                                              bool(tf.get("permitir_no_comercial", False)))
        notas.append(f"TimesFM en el backtest con {checkpoint}")
        if checkpoint in PESOS_NO_COMERCIALES:
            # Prender el permiso es una decisión legítima para investigar, pero
            # tiene que dejar rastro: seis meses después nadie se acuerda de qué
            # checkpoint corrió, y la salida se ve idéntica a una comercial.
            aviso = AVISO_NO_COMERCIAL.format(checkpoint=checkpoint, comercial=CHECKPOINT_DEFECTO)
            notas.append(aviso)
            log.warning("MVDE: %s", aviso)
    except RuntimeError as exc:
        # No poder correr TimesFM no puede dejar sin proyección al proyecto.
        notas.append(f"TimesFM no entró al backtest: {exc}")
        log.warning("MVDE: %s", notas[-1])
    return backends, notas


def _una_serie(s: pd.DataFrame, cfg: dict, backends: dict, m: int, etiqueta: str) -> dict:
    """Backtest → elección → bandas → proyección, para UNA serie.

    Cada segmento pasa por acá por separado: la mora temprana y la cartera
    jurídica no se comportan igual, así que no tienen por qué proyectarse con
    el mismo modelo."""
    horizonte = int(cfg.get("horizonte", 3))
    frecuencia = cfg.get("frecuencia", "mensual")
    v = s["valor"].to_numpy()
    bt = backtest(v, horizonte, m, int(cfg.get("origenes", 6)), backends)
    eleccion = elegir(bt, cfg.get("metrica", "mae"))
    backend = eleccion["backend"]
    pred = proyectar(v, horizonte, backend, m, backends, bt.get("pesos_ensemble"))
    bandas_ = bandas(bt, backend, float(cfg.get("banda", 0.8)))
    con_banda = aplicar_bandas(pred, bandas_)
    futuros = periodos_futuros(s["periodo"].iloc[-1], horizonte, frecuencia)
    dias = DIAS_POR_PERIODO.get(frecuencia, 30)
    salida = pd.concat([
        s.assign(segmento=etiqueta, backend="", tipo="historia", banda_baja=None, banda_alta=None, paso=None, dias=None),
        pd.DataFrame({"periodo": futuros, "valor": con_banda["valor"],
                      "banda_baja": con_banda["banda_baja"], "banda_alta": con_banda["banda_alta"],
                      "segmento": etiqueta, "backend": backend, "tipo": "proyeccion",
                      "paso": range(1, horizonte + 1), "dias": [(i + 1) * dias for i in range(horizonte)]}),
    ], ignore_index=True)
    fila = next(f for f in bt["resultados"] if f["backend"] == backend)
    metricas = {k: (round(fila[k], 4) if fila.get(k) is not None else None) for k in METRICAS}
    metricas["origenes_backtest"] = fila["origenes"]
    metricas[f"mejora_vs_{REFERENCIA}_pct"] = eleccion["mejora_pct"]
    return {"segmento": etiqueta, "modelo": backend, "metricas": metricas, "periodos": len(s),
            "eleccion": eleccion, "backtest": bt, "bandas": bandas_,
            "porque": _porque(eleccion, bt, bandas_),
            "serie": salida,
            "comparacion": real_vs_proyectado(bt, backend, s["periodo"]).assign(segmento=etiqueta)}


def _porque(eleccion: dict, bt: dict, bandas_: list[dict]) -> str:
    """La frase que contesta «¿por qué este modelo y no otro?», con los números
    del backtest adentro. Es lo que se pega al lado del gráfico."""
    top = eleccion["comparacion"][:3]
    contra = ", ".join(f"{f['backend']} {round(f[eleccion['metrica']], 2)}" for f in top[1:]) or "—"
    ult = next((b for b in reversed(bandas_) if b.get("alto") is not None), None)
    banda = (f"; al paso {ult['paso']} el desvío medido va de {round(100 * ult['bajo'], 1)} % a "
             f"{round(100 * ult['alto'], 1)} %") if ult else ""
    veredicto = (f"le gana a la referencia «{eleccion['referencia']}» por {eleccion['mejora_pct']} %"
                 if eleccion["le_gana_a_la_referencia"] else
                 f"no le gana a la referencia «{eleccion['referencia']}», que es con la que se proyecta")
    return (f"Ganó «{eleccion['backend']}» con {eleccion['metrica']} {round(eleccion['valor'], 2)} en "
            f"{bt['origenes']} cortes de backtest, contra {contra}; {veredicto}{banda}.")


def correr(df: pd.DataFrame, cfg: dict) -> dict:
    """Serie → backtest → elección → proyección con bandas, por segmento y para
    el total. Es lo que llama la etapa ML cuando el YAML declara `ml.tipo: serie`."""
    frecuencia = cfg.get("frecuencia", "mensual")
    m = int(cfg.get("estacionalidad") or ESTACIONALIDAD.get(frecuencia, 12))
    minimo = int(cfg.get("minimo_periodos", MINIMO_PERIODOS))
    backends, notas = _backends_de(cfg)
    cols_seg = cfg.get("segmento")
    cols_seg = [cols_seg] if isinstance(cols_seg, str) else list(cols_seg or [])
    faltan = [c for c in cols_seg if c not in df.columns]
    if faltan:
        raise ValueError(f"la columna de segmento {faltan} no está en la tabla")

    total = _una_serie(serie(df, cfg["fecha"], cfg["valor"], frecuencia, cfg.get("agregacion", "sum")),
                       cfg, backends, m, cfg.get("etiqueta_total", "TOTAL"))
    segmentos, omitidos = [], []
    if cols_seg:
        # Un segmento sin valor en una de las columnas (TipoCliente vacío para
        # los estados que no lo usan) no puede quedar como «Estado · nan».
        partes = df[cols_seg].astype("string").fillna("")
        clave = partes.apply(lambda f: " · ".join(x for x in f if x and x.lower() not in {"nan", "n/a", "none"}) or "—", axis=1)
        for etiqueta, g in df.groupby(clave, sort=True):
            try:
                s = serie(g, cfg["fecha"], cfg["valor"], frecuencia, cfg.get("agregacion", "sum"))
            except ValueError as exc:
                omitidos.append(f"{etiqueta}: {exc}")
                continue
            if len(s) < minimo:
                omitidos.append(f"{etiqueta}: {len(s)} períodos, menos que el mínimo de {minimo}")
                continue
            try:
                segmentos.append(_una_serie(s, cfg, backends, m, str(etiqueta)))
            except ValueError as exc:                  # historia corta para el horizonte pedido
                omitidos.append(f"{etiqueta}: {exc}")
    if omitidos:
        notas.append(f"{len(omitidos)} segmento(s) sin proyección por historia insuficiente: " + "; ".join(omitidos[:3]))

    tf = cfg.get("timesfm") if isinstance(cfg.get("timesfm"), dict) else {}
    no_comercial = bool(tf) and tf.get("checkpoint") in PESOS_NO_COMERCIALES and "timesfm" in backends
    e = total["eleccion"]
    if not e["le_gana_a_la_referencia"]:
        notas.append(f"en el total ningún modelo le gana a «{e['referencia']}»: se proyecta con la referencia")
    todos = [total, *segmentos]
    return {"tipo": "serie", "modelo": total["modelo"], "metricas": total["metricas"], "importancia": {},
            "licencia_no_comercial": no_comercial,
            "frecuencia": frecuencia, "horizonte": int(cfg.get("horizonte", 3)), "estacionalidad": m,
            "periodos": total["periodos"], "backtest": total["backtest"], "eleccion": e,
            "bandas": total["bandas"], "porque": total["porque"], "notas": notas,
            "pesos_ensemble": total["backtest"].get("pesos_ensemble", {}),
            "segmentos": [{k: x[k] for k in ("segmento", "modelo", "metricas", "periodos", "porque")}
                          | {"gana": x["eleccion"]["le_gana_a_la_referencia"],
                             "mejora_pct": x["eleccion"]["mejora_pct"], "bandas": x["bandas"]}
                          for x in todos],
            "serie": pd.concat([x["serie"] for x in todos], ignore_index=True),
            "comparacion": pd.concat([x["comparacion"] for x in todos], ignore_index=True)}
