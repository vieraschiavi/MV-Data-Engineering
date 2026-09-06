# © 2026 Martín Viera. Todos los derechos reservados.
"""Métodos de proyección de una serie, uno por familia, para que el backtest
los enfrente entre sí.

Son la adaptación de los catorce métodos del motor de proyecciones de cobranzas
(el que replica el Shiny de R) a este pipeline, con dos cambios de fondo:

1. **Sin nombres de segmento adentro.** El motor original lleva una tabla de
   pesos por segmento (`"Jurídica/Extrajudicial_TotalCobrado": [...]`). Eso
   anda perfecto en esa empresa y no anda en ninguna otra: un cliente nuevo no
   tiene esos estados. Acá los pesos NO se escriben: los mide el backtest de
   origen móvil, por segmento, en cada corrida (`proyeccion.ensemble`).
2. **Sin el mes del calendario adentro.** Los métodos originales razonan con
   «mismo mes del año»; acá razonan con «misma posición del ciclo», así el
   mismo código sirve para series mensuales (ciclo 12), diarias (ciclo 7) o
   trimestrales (ciclo 4).

Cada método predice UN período y el envoltorio los encadena: para el segundo
período la predicción del primero ya es historia. Es como proyecta el motor
original y es lo que se mide después en el backtest.
"""
from __future__ import annotations

import numpy as np

# Barandas heredadas del motor original: una proyección de cobranzas no puede
# irse a la mitad ni al doble del nivel reciente de un mes al otro. Cortan las
# extrapolaciones absurdas de los métodos con tendencia.
PISO_VS_RECIENTE = 0.5
TECHO_VS_RECIENTE = 1.5
VENTANA_RECIENTE = 6


def _pesos_exp(n: int, span: float = 1.5) -> np.ndarray:
    """Pesos que crecen hacia el presente: lo de hace tres ciclos pesa menos
    que lo del ciclo pasado."""
    if n <= 0:
        return np.ones(0)
    w = np.exp(np.linspace(-span, 0.0, n))
    return w / w.sum()


def _reciente(v: np.ndarray) -> float:
    return float(np.mean(v[-min(VENTANA_RECIENTE, len(v)):]))


def _acotar(pred: float, v: np.ndarray) -> float:
    """La baranda del motor original, explícita y en un solo lugar."""
    r = _reciente(v)
    if r <= 0:
        return float(pred)
    return float(min(max(pred, r * PISO_VS_RECIENTE), r * TECHO_VS_RECIENTE))


def _mismo_ciclo(n: int, objetivo: int, m: int) -> list[int]:
    """Índices de la historia que caen en la misma posición del ciclo que el
    período a predecir (el «mismo mes del año», generalizado)."""
    if m <= 1:
        return []
    return [i for i in range(n) if i % m == objetivo % m]


# --------------------------------------------------------------- los métodos
def _yoy(v: np.ndarray, k: int, m: int) -> float:
    """Mismo período del ciclo anterior, corregido por cuánto viene creciendo
    la serie. Es el método que más peso se lleva en cobranzas."""
    n = len(v)
    idx = _mismo_ciclo(n, k, m)
    crec = None
    if n >= m + 1:
        razones = [v[i] / v[i - m] for i in range(max(m, n - 6), n) if v[i - m] > 0]
        if razones:
            crec = float(np.dot(razones, _pesos_exp(len(razones))))
    if len(idx) >= 2:
        vals = v[idx]
        factores = [vals[j] / vals[j - 1] if vals[j - 1] > 0 else 1.0 for j in range(1, len(vals))]
        propio = float(np.dot(factores, _pesos_exp(len(factores)))) if factores else 1.0
        mezcla = 0.45 * propio + 0.55 * crec if crec is not None else propio
        return float(vals[-1] * min(max(mezcla, 0.75), 1.30))
    if len(idx) == 1:
        return float(v[idx[0]] * (min(max(crec, 0.80), 1.20) if crec is not None else 1.0))
    return _reciente(v)


def _mom(v: np.ndarray, k: int, m: int) -> float:
    """Del último período al siguiente, con el salto típico entre esas dos
    posiciones del ciclo (el «de diciembre a enero siempre cae»)."""
    n = len(v)
    razones = [v[i] / v[i - 1] for i in _mismo_ciclo(n, k, m) if i >= 1 and v[i - 1] > 0]
    if not razones:
        return _yoy(v, k, m)
    r = float(np.dot(razones, _pesos_exp(len(razones))))
    return float(v[-1] * min(max(r, 0.65), 1.35))


def _theta(v: np.ndarray, k: int, m: int) -> float:
    """Suavizado con tendencia amortiguada y un factor por posición del ciclo.
    Método clásico de competencia de pronóstico, robusto en series cortas."""
    n = len(v)
    if n < max(6, m):
        return _reciente(v)
    nivel, tend = float(v[0]), 0.0
    for x in v[1:]:
        nuevo = 0.15 * x + 0.85 * (nivel + tend)
        tend = 0.10 * (nuevo - nivel) + 0.90 * tend
        nivel = nuevo
    pred = nivel + tend * 0.80
    idx = _mismo_ciclo(n, k, m)
    if len(idx) >= 2:
        prom_ciclo = float(np.dot(v[idx], _pesos_exp(len(idx), 1.0)))
        prom = float(np.mean(v[-min(18, n):]))
        if prom > 0:
            pred *= min(max(prom_ciclo / prom, 0.85), 1.15)
    r = _reciente(v)
    if r > 0 and (pred > r * 1.3 or pred < r * 0.7):
        pred = 0.6 * pred + 0.4 * r                    # se acerca al nivel reciente si se despegó
    return _acotar(pred, v)


def _reversion(v: np.ndarray, k: int, m: int) -> float:
    """Vuelve a la media, con el sesgo de la posición del ciclo. Sirve para
    series que oscilan alrededor de un nivel y no tienen tendencia real."""
    n = len(v)
    if n < 3:
        return float(np.mean(v))
    global_, reciente = float(np.mean(v)), _reciente(v)
    pred = 0.60 * global_ + 0.40 * reciente
    idx = _mismo_ciclo(n, k, m)
    if len(idx) >= 2 and global_ > 0:
        prom_ciclo = float(np.dot(v[idx], _pesos_exp(len(idx), 0.8)))
        pred *= min(max(prom_ciclo / global_, 0.80), 1.20)
    return _acotar(pred, v)


def _tendencia_amortiguada(v: np.ndarray, k: int, m: int) -> float:
    """Holt con amortiguación (phi = 0,85): la tendencia se va apagando en vez
    de dispararse. Es la diferencia entre proyectar y extrapolar."""
    n = len(v)
    if n < 3:
        return float(np.mean(v))
    alfa, beta, phi = 0.20, 0.10, 0.85
    nivel, tend = float(v[0]), float(v[1] - v[0])
    for x in v[1:]:
        nuevo = alfa * x + (1 - alfa) * (nivel + phi * tend)
        tend = beta * (nuevo - nivel) + (1 - beta) * phi * tend
        nivel = nuevo
    pred = nivel + tend * phi * (1 - phi) / (1 - phi)   # un paso amortiguado
    idx = _mismo_ciclo(n, k, m)
    if len(idx) >= 2:
        prom_ciclo = float(np.dot(v[idx], _pesos_exp(len(idx), 0.5)))
        prom = float(np.mean(v[-min(2 * m if m > 1 else 12, n):]))
        if prom > 0:
            pred *= min(max(prom_ciclo / prom, 0.85), 1.15)
    return _acotar(pred, v)


def _ciclo_con_decaimiento(v: np.ndarray, k: int, m: int) -> float:
    """El mismo período del ciclo anterior por el factor de crecimiento típico
    de ESA posición, descartando los saltos atípicos."""
    n = len(v)
    idx = _mismo_ciclo(n, k, m)
    if not idx:
        return _reciente(v)
    if len(idx) < 2:
        return float(v[idx[0]])
    vals = v[idx]
    f = np.array([vals[j] / vals[j - 1] if vals[j - 1] > 0 else 1.0 for j in range(1, len(vals))])
    if len(f) >= 3:                                    # se recortan las colas: un mes raro no fija el futuro
        f = f[(f >= max(0.5, np.percentile(f, 5))) & (f <= min(2.0, np.percentile(f, 95)))]
    else:
        f = f[(f > 0.5) & (f < 2.0)]
    factor = float(np.dot(f, _pesos_exp(len(f)))) if len(f) else 1.0
    return _acotar(vals[-1] * factor, v)


def _pendiente_del_ciclo(v: np.ndarray, k: int, m: int) -> float:
    """Recta sobre los valores de esa misma posición del ciclo: «cada enero
    cobramos un 4 % más que el enero anterior»."""
    n = len(v)
    idx = _mismo_ciclo(n, k, m)
    if len(idx) < 2:
        return _yoy(v, k, m)
    y = v[idx]
    x = np.arange(len(y))
    try:
        pred = float(np.polyval(np.polyfit(x, y, 1), len(y)))
    except (np.linalg.LinAlgError, ValueError):
        pred = float(np.mean(y))
    pred = 0.60 * pred + 0.40 * float(np.dot(y, _pesos_exp(len(y), 0.5)))
    return _acotar(pred, v)


def _factor_anual(v: np.ndarray, k: int, m: int) -> float:
    """Mismo período del ciclo anterior escalado por cuánto creció el ciclo
    COMPLETO: absorbe mejor un cambio de nivel del negocio entero."""
    n = len(v)
    idx = _mismo_ciclo(n, k, m)
    if not idx or n < m + 1:
        return _yoy(v, k, m)
    if n >= 2 * m:
        prev = float(np.sum(v[-2 * m:-m]))
        factor = float(np.sum(v[-m:])) / prev if prev > 0 else 1.0
    else:
        n_ant = n - m
        prev = float(np.sum(v[:n_ant])) / n_ant if n_ant > 0 else 0.0
        factor = (float(np.sum(v[-m:])) / m) / prev if prev > 0 else 1.0
    return _acotar(v[idx[-1]] * min(max(factor, 0.80), 1.25), v)


UN_PASO = {
    "yoy": _yoy,
    "mom": _mom,
    "theta": _theta,
    "reversion_media": _reversion,
    "tendencia_amortiguada": _tendencia_amortiguada,
    "ciclo_decaimiento": _ciclo_con_decaimiento,
    "pendiente_ciclo": _pendiente_del_ciclo,
    "factor_anual": _factor_anual,
}


def _recursivo(fn):
    """Un método de un paso, encadenado a lo largo del horizonte: la predicción
    del período 1 es historia para el período 2, igual que en el motor original."""
    def predecir(historia, horizonte: int, m: int):
        v = np.asarray(historia, dtype=float)
        n0 = len(v)
        salida = []
        for h in range(horizonte):
            p = float(fn(v, n0 + h, m))
            if not np.isfinite(p):
                p = _reciente(v)
            salida.append(p)
            v = np.append(v, p)
        return np.array(salida, dtype=float)
    return predecir


# Los backends listos para el backtest, con la misma firma que los básicos.
BACKENDS = {nombre: _recursivo(fn) for nombre, fn in UN_PASO.items()}
