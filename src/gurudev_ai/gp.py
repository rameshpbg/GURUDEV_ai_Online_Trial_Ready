"""Nested-validation predictive workflow; only the initial GP baseline is implemented."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.model_selection import KFold, GroupKFold, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

@dataclass
class GPResult:
    metrics: dict
    predictions: pd.DataFrame
    final_model: object
    parameters: dict
    fold_details: list


def _pipeline():
    # All preprocessing happens inside the CV pipeline, preventing train/test leakage.
    return Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
        ("filter", VarianceThreshold(threshold=0)),
        ("scale", StandardScaler()),
        ("model", Ridge()),
    ])


def _grid():
    return [
        {"model": [Ridge()], "model__alpha": [0.1, 1.0, 10.0]},
        {"model": [ElasticNet(max_iter=10000, random_state=42)], "model__alpha": [0.1, 1.0, 10.0], "model__l1_ratio": [0.2, 0.8]},
    ]


def _splits(groups, n_samples: int, seed: int, outer=True):
    n_splits = 4 if outer else 3
    if groups is None:
        return KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return GroupKFold(n_splits=min(n_splits, len(set(groups))))


def _metrics(actual, predicted):
    correlation = float(np.corrcoef(actual, predicted)[0, 1]) if (np.std(actual) > 0 and np.std(predicted) > 0) else None
    if correlation is not None and not np.isfinite(correlation):
        correlation = None
    return {
        "RMSE": round(float(np.sqrt(mean_squared_error(actual, predicted))), 6),
        "MAE": round(float(mean_absolute_error(actual, predicted)), 6),
        "R2": round(float(r2_score(actual, predicted)), 6),
        "Pearson_r": round(correlation, 6) if correlation is not None else None,
    }


def train_nested(dataset, seed: int = 42) -> GPResult:
    X, y = dataset.X, dataset.y
    groups = dataset.groups
    g = groups.to_numpy() if groups is not None else None
    outer = _splits(g, len(X), seed, outer=True)
    folds = outer.split(X, y, g) if g is not None else outer.split(X, y)
    preds = np.full(len(y), np.nan)
    assigned = np.zeros(len(y), dtype=int)
    details = []
    for fold, (tr, te) in enumerate(folds, 1):
        train_groups = g[tr] if g is not None else None
        inner = _splits(train_groups, len(tr), seed + fold, outer=False)
        search = GridSearchCV(_pipeline(), _grid(), cv=inner, scoring="neg_root_mean_squared_error", n_jobs=1, refit=True)
        if g is not None:
            search.fit(X.iloc[tr], y.iloc[tr], groups=train_groups)
        else:
            search.fit(X.iloc[tr], y.iloc[tr])
        predicted = search.predict(X.iloc[te])
        preds[te] = predicted
        assigned[te] += 1
        details.append({"fold": fold, "train_n": len(tr), "test_n": len(te),
                        "selected_model": type(search.best_estimator_.named_steps["model"]).__name__,
                        "inner_best_neg_rmse": round(float(search.best_score_), 6)})
    if not np.isfinite(preds).all() or (assigned != 1).any():
        raise RuntimeError("Cross-validation invariant failed: each sample must have exactly one out-of-fold prediction")
    final_inner = _splits(g, len(y), seed + 99, outer=False)
    final = GridSearchCV(_pipeline(), _grid(), cv=final_inner, scoring="neg_root_mean_squared_error", n_jobs=1, refit=True)
    if g is not None:
        final.fit(X, y, groups=g)
    else:
        final.fit(X, y)
    chosen = final.best_estimator_
    parameters = {"selected_model": type(chosen.named_steps["model"]).__name__,
                  "selected_parameters": {k: (type(v).__name__ if k == "model" else v) for k, v in final.best_params_.items()},
                  "outer_folds": len(details), "inner_folds": 3,
                  "seed": seed, "validation": "nested_group_cv" if g is not None else "nested_random_cv"}
    result_df = pd.DataFrame({"sample_id": dataset.ids, "observed": y.to_numpy(),
                              "predicted_oof": preds})
    return GPResult(metrics=_metrics(y.to_numpy(), preds), predictions=result_df,
                    final_model=chosen, parameters=parameters, fold_details=details)
