# © 2026 Martín Viera. Todos los derechos reservados.
"""Etapa 8 · ML (opcional): clasificación o regresión sobre una tabla gold o
silver, con corte temporal honesto cuando hay fecha, chequeo de fuga y
puntajes escritos como tabla gold `ml_scores`.

YAML `ml`: {tabla: fact_x | sql: "SELECT ... FROM gold...", target: col, fecha: col|null,
            tipo: auto|clasificacion|regresion, excluir: [cols], test: 0.2}
Con `sql` el set de entrenamiento se arma en el almacén (joins, agregados);
es lo normal cuando el target vive en una tabla y el comportamiento en otra.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _preparar(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    target = cfg["target"]
    excluir = set(cfg.get("excluir") or []) | {target}
    X = df.drop(columns=[c for c in df.columns if c in excluir or c.endswith("_key") or c.endswith("_hash")], errors="ignore")
    fechas = [c for c in X.columns if pd.api.types.is_datetime64_any_dtype(X[c])]
    for c in fechas:
        X[c + "_mes"] = X[c].dt.month
        X[c + "_dsem"] = X[c].dt.dayofweek
    X = X.drop(columns=fechas)
    y = df[target]
    notas = []
    # Fuga: una columna que replica al target casi perfectamente no es una feature.
    fuga = []
    yn = pd.to_numeric(y, errors="coerce")
    for c in X.columns:
        if pd.api.types.is_numeric_dtype(X[c]) and yn.notna().all():
            corr = abs(np.corrcoef(pd.to_numeric(X[c], errors="coerce").fillna(0), yn)[0, 1]) if X[c].nunique() > 1 else 0
            if corr > 0.98:
                fuga.append(c)
    if fuga:
        X = X.drop(columns=fuga)
        notas.append(f"fuga: quitadas {fuga}")
    cats = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c]) and not pd.api.types.is_bool_dtype(X[c])]
    for c in cats:
        top = X[c].astype(str).value_counts().index[:30]
        X[c] = X[c].astype(str).where(X[c].astype(str).isin(top), "OTROS")
    X = pd.get_dummies(X, columns=cats, dummy_na=False, dtype=float)
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
    return X, y, notas


def entrenar(df: pd.DataFrame, cfg: dict) -> dict:
    from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.metrics import (mean_absolute_error, r2_score, roc_auc_score, f1_score, accuracy_score)

    X, y, notas = _preparar(df, cfg)
    tipo = cfg.get("tipo", "auto")
    if tipo == "auto":
        tipo = "clasificacion" if (y.nunique() <= 10 and not pd.api.types.is_float_dtype(y)) or y.dtype == bool else "regresion"
    test = float(cfg.get("test", 0.2))
    if cfg.get("fecha") and cfg["fecha"] in df.columns:
        orden = np.argsort(pd.to_datetime(df[cfg["fecha"]]).values, kind="stable")
        notas.append(f"corte temporal por {cfg['fecha']}: entreno con el pasado, pruebo con el futuro")
    else:
        rng = np.random.default_rng(42)
        orden = rng.permutation(len(df))
        notas.append("sin fecha: corte aleatorio con semilla 42")
    corte = int(len(df) * (1 - test))
    tr, te = orden[:corte], orden[corte:]
    Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]
    if tipo == "clasificacion":
        ytr, yte = ytr.astype(int), yte.astype(int)
        m = GradientBoostingClassifier(random_state=42, n_estimators=150, max_depth=3)
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1] if len(np.unique(ytr)) == 2 else m.predict(Xte)
        metricas = {"auc": round(float(roc_auc_score(yte, p)), 4) if len(np.unique(yte)) == 2 else None,
                    "f1": round(float(f1_score(yte, (p >= 0.5).astype(int) if len(np.unique(ytr)) == 2 else p, average="binary" if len(np.unique(ytr)) == 2 else "macro")), 4),
                    "accuracy": round(float(accuracy_score(yte, (p >= 0.5).astype(int) if len(np.unique(ytr)) == 2 else p)), 4),
                    "tasa_base": round(float(ytr.mean()), 4)}
        scores = m.predict_proba(X)[:, 1] if len(np.unique(ytr)) == 2 else m.predict(X)
    else:
        m = GradientBoostingRegressor(random_state=42, n_estimators=150, max_depth=3)
        m.fit(Xtr, ytr.astype(float))
        p = m.predict(Xte)
        yt = yte.astype(float)
        mape = float(np.mean(np.abs((yt - p) / np.where(yt == 0, np.nan, yt))) * 100) if (yt != 0).any() else None
        metricas = {"r2": round(float(r2_score(yt, p)), 4), "mae": round(float(mean_absolute_error(yt, p)), 4),
                    "mape": round(mape, 2) if mape is not None and not np.isnan(mape) else None}
        scores = m.predict(X)
    imp = pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False)
    return {
        "tipo": tipo, "filas_train": int(len(tr)), "filas_test": int(len(te)), "metricas": metricas,
        "importancia": {k: round(float(v), 4) for k, v in imp.head(15).items()},
        "notas": notas,
        "scores": pd.DataFrame({"fila": np.arange(len(df)), "score": scores}),
    }
