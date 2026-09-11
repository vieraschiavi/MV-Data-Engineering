# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 8 · ML (opcional): clasificación o regresión con corte honesto, más
el scoring de un segundo conjunto (backtest a ciegas / cartera a priorizar)
y, para cobranzas, la salida al estilo MV Kobra AI: probpago, decil,
segmento de propensión, estrategia de negociación, valor esperado y prioridad.

YAML `ml`:
  tabla: fact_x  |  sql: "SELECT ... FROM gold..."      set de entrenamiento
  target: col · tipo: auto|clasificacion|regresion · fecha: col|null · test: 0.2
  excluir: [cols que no son features: fugas, ids]
  tabla_score: fact_y | sql_score: "SELECT ..."          conjunto a scorear (opcional)
  id: columna identificadora que viaja a la salida (opcional)
  cobranzas: {monto: col, dias_mora: col}                salida estilo Kobra (opcional)

Corte en TRES partes (entrenamiento 60 / selección 20 / holdout 20), como
en el AutoML de Kobra: el número que se reporta sale del holdout, que no se
usó para elegir nada, y se informa la brecha selección→holdout.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

_LEAK_CORR = 0.98


def _preparar(df: pd.DataFrame, cfg: dict, columnas: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    target = cfg.get("target")
    excluir = set(cfg.get("excluir") or []) | ({target} if target else set()) | ({cfg["id"]} if cfg.get("id") else set())
    X = df.drop(columns=[c for c in df.columns if c in excluir or c.endswith("_key") or c.endswith("_hash")], errors="ignore")
    fechas = [c for c in X.columns if pd.api.types.is_datetime64_any_dtype(X[c])]
    for c in fechas:
        X[c + "_mes"] = X[c].dt.month
        X[c + "_dsem"] = X[c].dt.dayofweek
    X = X.drop(columns=fechas)
    notas: list[str] = []
    if columnas is None and target in df.columns:
        yn = pd.to_numeric(df[target], errors="coerce")
        fuga = []
        for c in X.columns:
            if pd.api.types.is_numeric_dtype(X[c]) and yn.notna().all() and X[c].nunique() > 1:
                corr = abs(np.corrcoef(pd.to_numeric(X[c], errors="coerce").fillna(0), yn)[0, 1])
                if corr > _LEAK_CORR:
                    fuga.append(c)
        if fuga:
            X = X.drop(columns=fuga)
            notas.append(f"fuga: quitadas {fuga} (correlación > {_LEAK_CORR} con el target)")
    cats = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c]) and not pd.api.types.is_bool_dtype(X[c])]
    for c in cats:
        top = X[c].astype(str).value_counts().index[:30]
        X[c] = X[c].astype(str).where(X[c].astype(str).isin(top), "OTROS")
    X = pd.get_dummies(X, columns=cats, dummy_na=False, dtype=float)
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
    if columnas is not None:                      # el set a scorear se alinea a las columnas del entrenamiento
        X = X.reindex(columns=columnas, fill_value=0)
    return X, notas


def _huella(df: pd.DataFrame) -> np.ndarray:
    """Un número estable por fila, que depende del CONTENIDO y no del orden en
    que llegó.

    Hace falta para desempatar: un set armado con SQL sale de DuckDB sin orden
    garantizado (no hay `ORDER BY`), y el orden cambia entre corridas. Si el
    desempate depende de cómo vino el DataFrame, el corte 60/20/20 cae en otro
    lado cada vez: otro holdout, otra tasa base, otro AUC y hasta otro modelo
    ganador. Medido: la misma demo daba AUC 0,6902 con Regresión logística y
    0,7109 con Random Forest sobre datos idénticos.

    Lo que esto NO da, y conviene tener claro antes de comparar dos corridas:
    estabilidad frente al ESQUEMA. La huella sale de la fila entera como texto,
    así que agregar o quitar una columna —incluso una que después no se usa como
    feature— le cambia el hash a todas las filas y reparte otro holdout, con
    otra tasa base. Dos corridas con distinta lista de columnas no son
    comparables, y la diferencia de AUC entre ellas no dice si el cambio sirvió.
    Para medir el efecto de sacar una feature hay que fijar el corte una vez y
    reusarlo; queda anotado en `notas` de cada corrida."""
    texto = df.astype(str).agg("\x1f".join, axis=1)
    return np.array([int(hashlib.blake2b(t.encode(), digest_size=8).hexdigest(), 16) for t in texto])


def _cortes(df: pd.DataFrame, cfg: dict, notas: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    huella = _huella(df)
    if cfg.get("fecha") and cfg["fecha"] in df.columns:
        fechas = pd.to_datetime(df[cfg["fecha"]]).values
        # lexsort ordena por la ÚLTIMA clave primero: fecha manda, la huella
        # desempata. Así el corte es el mismo venga el set de donde venga.
        orden = np.lexsort((huella, fechas))
        notas.append(f"corte temporal por {cfg['fecha']}: entreno con el pasado, selecciono y mido con el futuro")
    else:
        orden = np.argsort(huella, kind="stable")
        notas.append("sin columna de fecha: corte por huella de contenido (reproducible entre corridas "
                     "del MISMO set; agregar o quitar una columna reparte otro holdout, así que dos "
                     "corridas con distinta lista de columnas no se comparan entre sí)")
    n = len(df)
    a, b = int(n * 0.6), int(n * 0.8)
    return orden[:a], orden[a:b], orden[b:]


def _modelos(tipo: str) -> dict:
    """Los candidatos. Los lineales van CON escalado y los de árbol sin él.

    Por qué el escalado no es cosmético en los lineales: lbfgs no converge con
    features de escalas mezcladas (un límite de crédito en el orden de 1e6 al
    lado de dummies 0/1) y se corta en `max_iter`, así que compite contra los
    árboles con coeficientes a medio ajustar. Medido en la demo `kash`: sin
    escalar largaba un `ConvergenceWarning`; con escalado no. El AUC casi no se
    movió (0,8831 → 0,8833 en selección) y el ganador NO cambió — el escalado no
    está acá para subir el puntaje, sino para que el modelo termine de ajustar.

    Lo segundo que arregla es la importancia: para un lineal se reporta
    `|coef_|`, y sin escalar los coeficientes de dos features con escalas
    distintas no son comparables entre sí, así que la tabla de importancia
    estaba ordenada por la unidad de cada columna tanto como por su efecto.

    Y la penalización de Ridge castiga coeficientes: sin escalar, cada feature
    recibe una regularización distinta según en qué unidad venga medida.
    """
    from sklearn.ensemble import (GradientBoostingClassifier, GradientBoostingRegressor,
                                  RandomForestClassifier, RandomForestRegressor)
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if tipo == "clasificacion":
        return {"Regresión logística": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
                "Random Forest": RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=42, n_jobs=-1),
                "Gradient Boosting": GradientBoostingClassifier(n_estimators=150, max_depth=3, random_state=42)}
    return {"Ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
            "Random Forest": RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=42, n_jobs=-1),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=42)}


def _medir(tipo: str, y, p) -> dict:
    from sklearn.metrics import (accuracy_score, average_precision_score, f1_score, mean_absolute_error,
                                 r2_score, roc_auc_score)
    if tipo == "clasificacion":
        y = np.asarray(y).astype(int)
        binario = len(np.unique(y)) == 2
        m = {"auc": round(float(roc_auc_score(y, p)), 4) if binario else None,
             "auc_pr": round(float(average_precision_score(y, p)), 4) if binario else None,
             "f1": round(float(f1_score(y, (p >= 0.5).astype(int))), 4) if binario else None,
             "accuracy": round(float(accuracy_score(y, (p >= 0.5).astype(int))), 4) if binario else None,
             "tasa_base": round(float(y.mean()), 4)}
        if binario and len(y) >= 20:
            te = pd.DataFrame({"y": y, "p": p})
            te["decil"] = pd.qcut(te["p"].rank(method="first"), 10, labels=False) + 1
            top = te.loc[te["decil"] == 10, "y"].mean()
            m["lift_decil10"] = round(float(top / y.mean()), 2) if y.mean() > 0 else None
        return m
    y = np.asarray(y).astype(float)
    mape = float(np.mean(np.abs((y - p) / np.where(y == 0, np.nan, y))) * 100) if (y != 0).any() else None
    return {"r2": round(float(r2_score(y, p)), 4), "mae": round(float(mean_absolute_error(y, p)), 4),
            "mape": round(mape, 2) if mape is not None and not np.isnan(mape) else None}


def _predecir(m, X, tipo: str) -> np.ndarray:
    return m.predict_proba(X)[:, 1] if tipo == "clasificacion" and hasattr(m, "predict_proba") else m.predict(X)


def kobra_style(scores: pd.DataFrame, monto: pd.Series, dias_mora: pd.Series) -> pd.DataFrame:
    """Salida de cartera al estilo MV Kobra AI (mismos umbrales que su negociador):
    decil, segmento de propensión, estrategia, descuento, cuotas, valor esperado y prioridad."""
    out = scores.copy()
    p = out["probpago"].values
    out["decil"] = pd.qcut(out["probpago"].rank(method="first"), 10, labels=False) + 1
    out["segmento_propension"] = pd.cut(out["probpago"], bins=[-0.01, 0.35, 0.65, 1.01], labels=["Baja", "Media", "Alta"]).astype(str)
    monto = pd.to_numeric(monto, errors="coerce").fillna(0).values
    dias = pd.to_numeric(dias_mora, errors="coerce").fillna(0).values

    def decidir(pr, d, m):
        if pr >= 0.65:
            return ("Recordatorio suave", 0.00, 1) if d <= 30 else ("Pago total con 5 %", 0.05, 1)
        if pr >= 0.35:
            return ("Plan de cuotas", 0.10, 3) if d <= 90 else ("Plan de cuotas con quita", 0.20, 6)
        if d <= 90:
            return ("Quita agresiva", 0.30, 1)
        if m >= 500_000:
            return ("Derivación", 0.15, 12)
        return ("Descuento máximo", 0.45, 1)

    dec = [decidir(pr, d, m) for pr, d, m in zip(p, dias, monto)]
    out["estrategia"] = [x[0] for x in dec]
    out["descuento_recomendado"] = [x[1] for x in dec]
    out["plan_cuotas"] = [x[2] for x in dec]
    out["monto_referencia"] = monto
    out["dias_mora"] = dias
    out["valor_esperado_recupero"] = out["probpago"] * monto * (1 - out["descuento_recomendado"])
    out["prioridad"] = out["valor_esperado_recupero"].rank(ascending=False, method="first").astype(int)
    return out


def entrenar(df: pd.DataFrame, cfg: dict, df_score: pd.DataFrame | None = None) -> dict:
    X, notas = _preparar(df, cfg)
    y = df[cfg["target"]]
    tipo = cfg.get("tipo", "auto")
    if tipo == "auto":
        tipo = "clasificacion" if (y.nunique() <= 10 and not pd.api.types.is_float_dtype(y)) or y.dtype == bool else "regresion"
    y = y.astype(int) if tipo == "clasificacion" else y.astype(float)
    tr, sel, ho = _cortes(df, cfg, notas)
    Xtr, ytr = X.iloc[tr], y.iloc[tr]
    candidatos = _modelos(tipo)
    tabla = []
    ajustados = {}
    for nombre, m in candidatos.items():
        m.fit(Xtr, ytr)
        ajustados[nombre] = m
        met_sel = _medir(tipo, y.iloc[sel], _predecir(m, X.iloc[sel], tipo))
        tabla.append({"modelo": nombre, **{f"sel_{k}": v for k, v in met_sel.items()}})
    clave = "sel_auc" if tipo == "clasificacion" else "sel_r2"
    mejor = max(tabla, key=lambda r: (r.get(clave) if r.get(clave) is not None else -1e9))["modelo"]
    m = ajustados[mejor]
    met_ho = _medir(tipo, y.iloc[ho], _predecir(m, X.iloc[ho], tipo))
    met_sel = next(r for r in tabla if r["modelo"] == mejor)
    brecha = None
    if tipo == "clasificacion" and met_sel.get("sel_auc") is not None and met_ho.get("auc") is not None:
        brecha = round(met_sel["sel_auc"] - met_ho["auc"], 4)
    elif tipo == "regresion" and met_sel.get("sel_r2") is not None:
        brecha = round(met_sel["sel_r2"] - met_ho["r2"], 4)
    notas.append(f"mejor modelo por selección: {mejor}; brecha selección→holdout {brecha}")
    imp = None
    # Los lineales van dentro de un Pipeline con el escalador: el estimador real
    # es el último paso, y sin desenvolverlo `importancia` sale vacía.
    nucleo = m[-1] if hasattr(m, "steps") else m
    if hasattr(nucleo, "feature_importances_"):
        imp = pd.Series(nucleo.feature_importances_, index=X.columns)
    elif hasattr(nucleo, "coef_"):
        imp = pd.Series(np.abs(np.ravel(nucleo.coef_)), index=X.columns)
    importancia = {k: round(float(v), 4) for k, v in imp.sort_values(ascending=False).head(15).items()} if imp is not None else {}

    # Scoring: el propio set (para el tablero) o el conjunto a scorear.
    objetivo = df_score if df_score is not None else df
    Xs, _ = _preparar(objetivo, cfg, columnas=list(X.columns))
    scores = pd.DataFrame({"fila": np.arange(len(objetivo)), "probpago" if tipo == "clasificacion" else "prediccion": _predecir(m, Xs, tipo)})
    if cfg.get("id") and cfg["id"] in objetivo.columns:
        scores.insert(0, cfg["id"], objetivo[cfg["id"]].values)
    for k in [c for c in objetivo.columns if c.endswith("_key") and c not in scores.columns]:
        scores[k] = objetivo[k].values
    if cfg.get("cobranzas") and tipo == "clasificacion":
        cb = cfg["cobranzas"]
        scores = kobra_style(scores, objetivo.get(cb.get("monto"), pd.Series(0, index=objetivo.index)),
                             objetivo.get(cb.get("dias_mora"), pd.Series(0, index=objetivo.index)))
        notas.append("salida de cartera al estilo MV Kobra AI: decil, segmento, estrategia, valor esperado, prioridad")
    return {
        "tipo": tipo, "modelo": mejor, "filas_train": int(len(tr)), "filas_seleccion": int(len(sel)), "filas_holdout": int(len(ho)),
        "filas_scoreadas": int(len(scores)), "metricas": met_ho, "brecha_seleccion_holdout": brecha,
        # Qué vio el modelo, completo y no sólo el top 15 de `importancia`: es lo
        # que permite revisar después si entró una columna que no debía entrar.
        "features": list(X.columns),
        "comparacion": tabla, "importancia": importancia, "notas": notas, "scores": scores,
    }
