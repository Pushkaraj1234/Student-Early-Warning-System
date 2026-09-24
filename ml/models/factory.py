"""Model pipelines. Every pipeline contains its own preprocessing, so a saved model can never
be separated from the preprocessing it was trained with."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ModelName = Literal["logistic_regression", "random_forest", "xgboost"]
ImbalanceStrategy = Literal["none", "balanced"]

# Lower = easier for a mentor or reviewer to understand. Used as a selection tie-breaker.
INTERPRETABILITY_RANK: dict[ModelName, int] = {"logistic_regression": 1, "xgboost": 2, "random_forest": 3}

# Units of the per-feature contributions produced by ml.explainability for each model.
EXPLANATION_UNITS: dict[ModelName, str] = {
    "logistic_regression": "log-odds (SHAP, linear)",
    "random_forest": "probability (SHAP, tree)",
    "xgboost": "log-odds (SHAP, tree)",
}


def build_pipeline(
    name: ModelName, strategy: ImbalanceStrategy, *, y_train: np.ndarray, seed: int
) -> Pipeline:
    """Build an unfitted pipeline. ``y_train`` is used only to size class weights."""
    positives = int(np.sum(y_train == 1))
    negatives = int(np.sum(y_train == 0))
    if positives == 0 or negatives == 0:
        raise ValueError("training labels must contain both classes")

    if name == "logistic_regression":
        return Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=5000,
                        class_weight="balanced" if strategy == "balanced" else None,
                        random_state=seed,
                    ),
                ),
            ]
        )
    if name == "random_forest":
        return Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=20,
                        max_features="sqrt",
                        class_weight="balanced" if strategy == "balanced" else None,
                        n_jobs=-1,
                        random_state=seed,
                    ),
                ),
            ]
        )
    if name == "xgboost":
        # XGBoost handles missing values natively; no imputation step.
        return Pipeline(
            [
                (
                    "model",
                    XGBClassifier(
                        n_estimators=400,
                        learning_rate=0.05,
                        max_depth=4,
                        min_child_weight=5,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        reg_lambda=1.0,
                        tree_method="hist",
                        eval_metric="aucpr",
                        scale_pos_weight=(negatives / positives) if strategy == "balanced" else 1.0,
                        n_jobs=-1,
                        random_state=seed,
                    ),
                ),
            ]
        )
    raise ValueError(f"unknown model: {name}")


def model_hyperparameters(pipeline: Pipeline) -> dict[str, Any]:
    """JSON-serialisable hyperparameters of the final estimator."""
    params = pipeline.named_steps["model"].get_params()
    return {k: v for k, v in sorted(params.items()) if isinstance(v, str | int | float | bool) or v is None}
