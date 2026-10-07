"""Tabular models for the student-week panel: L1 (LASSO) logistic regression, random forest, XGBoost.

Imbalance options: ``none``; ``weights`` (class weights / scale_pos_weight); ``smote`` (SMOTE on training rows
only, inside the pipeline, after median imputation — SMOTE cannot interpolate missing values, so XGBoost with
SMOTE loses its native missing-value handling). Every pipeline carries its own preprocessing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

TabularName = Literal["l1_logistic", "random_forest", "xgboost"]
Imbalance = Literal["none", "weights", "smote"]

# Minority:majority ratio after SMOTE. Full balancing would roughly double the training rows (memory);
# 1:4 already multiplies the minority of the rare withdrawal targets several times.
SMOTE_RATIO = 0.25
SMOTE_NEIGHBOURS = 5
XGB_EARLY_STOPPING_ROUNDS = 50
XGB_MAX_ROUNDS = 2000
XGB_SEARCH_SPACE: dict[str, tuple[float | int, ...]] = {
    "max_depth": (3, 4, 5, 6),
    "learning_rate": (0.03, 0.05, 0.1),
    "min_child_weight": (1, 5, 20),
    "subsample": (0.7, 0.8, 1.0),
    "colsample_bytree": (0.6, 0.8, 1.0),
    "reg_lambda": (1.0, 5.0),
}
L1_C_GRID: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0, 10.0)
RF_PARAMS: dict[str, Any] = {
    "n_estimators": 200,
    "min_samples_leaf": 50,
    "max_features": "sqrt",
    "max_samples": 0.5,
}


def _imputer() -> SimpleImputer:
    return SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)


def _smote(seed: int) -> SMOTE:
    return SMOTE(sampling_strategy=SMOTE_RATIO, k_neighbors=SMOTE_NEIGHBOURS, random_state=seed)


def build_tabular(
    name: TabularName,
    imbalance: Imbalance,
    *,
    params: Mapping[str, Any],
    y_train: np.ndarray,
    seed: int,
) -> Pipeline | ImbPipeline:
    """Unfitted pipeline. ``y_train`` only sizes the class weights."""
    positives = int(np.sum(y_train == 1))
    negatives = int(np.sum(y_train == 0))
    if positives == 0 or negatives == 0:
        raise ValueError("training labels must contain both classes")
    weighted = imbalance == "weights"
    if name == "l1_logistic":
        model: Any = LogisticRegression(
            C=float(params["C"]),
            l1_ratio=1.0,
            solver="saga",
            tol=1e-3,
            max_iter=500,
            class_weight="balanced" if weighted else None,
            random_state=seed,
        )
        steps: list[tuple[str, Any]] = [("impute", _imputer()), ("scale", StandardScaler())]
    elif name == "random_forest":
        model = RandomForestClassifier(
            **{**RF_PARAMS, **params},
            class_weight="balanced" if weighted else None,
            n_jobs=-1,
            random_state=seed,
        )
        steps = [("impute", _imputer())]
    elif name == "xgboost":
        model = XGBClassifier(
            **params,
            tree_method="hist",
            eval_metric="aucpr",
            scale_pos_weight=(negatives / positives) if weighted else 1.0,
            n_jobs=-1,
            random_state=seed,
        )
        steps = [("impute", _imputer())] if imbalance == "smote" else []
    else:
        raise ValueError(f"unknown model: {name}")
    if imbalance == "smote":
        return ImbPipeline([*steps, ("smote", _smote(seed)), ("model", model)])
    return Pipeline([*steps, ("model", model)])


def proba(model: Any, X: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict_proba(X)[:, 1], dtype=np.float64)


@dataclass(frozen=True)
class TuningResult:
    params: dict[str, Any]
    val_pr_auc: float
    trials: list[dict[str, Any]]


def xgb_search_settings(n: int, seed: int) -> list[dict[str, Any]]:
    """``n`` distinct random settings from XGB_SEARCH_SPACE (deterministic for a seed)."""
    rng = np.random.default_rng(seed)
    seen: set[tuple[Any, ...]] = set()
    settings: list[dict[str, Any]] = []
    while len(settings) < n:
        candidate = {k: v[int(rng.integers(len(v)))] for k, v in XGB_SEARCH_SPACE.items()}
        key = tuple(candidate.values())
        if key not in seen:
            seen.add(key)
            settings.append({k: (float(v) if isinstance(v, float) else int(v)) for k, v in candidate.items()})
    return settings


def tune_xgboost(
    X_tr: pd.DataFrame,
    y_tr: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    *,
    imbalance: Imbalance,
    n_settings: int,
    seed: int,
) -> TuningResult:
    """Random search; each setting is early-stopped on validation PR-AUC. The returned params include the
    number of boosting rounds, so a refit on other data needs no validation set."""
    trials: list[dict[str, Any]] = []
    weighted = imbalance == "weights"
    spw = float(np.sum(y_tr == 0) / np.sum(y_tr == 1)) if weighted else 1.0
    for setting in xgb_search_settings(n_settings, seed):
        model = XGBClassifier(
            **setting,
            n_estimators=XGB_MAX_ROUNDS,
            early_stopping_rounds=XGB_EARLY_STOPPING_ROUNDS,
            tree_method="hist",
            eval_metric="aucpr",
            scale_pos_weight=spw,
            n_jobs=-1,
            random_state=seed,
        ).fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        rounds = int(model.best_iteration) + 1
        score = float(
            average_precision_score(y_val, model.predict_proba(X_val, iteration_range=(0, rounds))[:, 1])
        )
        trials.append({**setting, "n_estimators": rounds, "val_pr_auc": score})
    best = max(trials, key=lambda t: t["val_pr_auc"])
    params = {k: v for k, v in best.items() if k != "val_pr_auc"}
    return TuningResult(params=params, val_pr_auc=float(best["val_pr_auc"]), trials=trials)


def tune_l1(
    X_tr: pd.DataFrame, y_tr: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray, *, seed: int
) -> tuple[TuningResult, Pipeline]:
    """Pick the L1 strength C on validation PR-AUC; returns the result and the fitted best pipeline."""
    trials: list[dict[str, Any]] = []
    best_pipe: Any = None
    best_score = -1.0
    for c in L1_C_GRID:
        pipe = build_tabular("l1_logistic", "none", params={"C": c}, y_train=y_tr, seed=seed).fit(X_tr, y_tr)
        score = float(average_precision_score(y_val, proba(pipe, X_val)))
        nonzero = int(np.count_nonzero(pipe.named_steps["model"].coef_))
        trials.append({"C": c, "val_pr_auc": score, "nonzero_coefficients": nonzero})
        if score > best_score:
            best_score, best_pipe = score, pipe
    best = max(trials, key=lambda t: t["val_pr_auc"])
    return TuningResult(
        params={"C": best["C"]}, val_pr_auc=float(best["val_pr_auc"]), trials=trials
    ), best_pipe
