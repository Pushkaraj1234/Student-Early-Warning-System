"""SHAP explanations mapped back to the model's input features.

Each factor is reported as: feature (machine key), contribution (SHAP value), direction
(increases_risk / decreases_risk) and rank (1 = largest |contribution|). Units depend on the
model (see ml.models.factory.EXPLANATION_UNITS). Contributions explain the UNCALIBRATED model
output; calibration is monotonic, so it does not change which factors matter or their sign.

SHAP values describe how the model used each input for this prediction. They are
associations, not causes, and this module never produces free-text explanations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
import shap
from numpy.typing import NDArray
from sklearn.pipeline import Pipeline

from ml.models.artifact import ModelArtifact
from ml.models.factory import ModelName

Direction = Literal["increases_risk", "decreases_risk"]
FloatMatrix = NDArray[np.float64]


@dataclass(frozen=True)
class FactorContribution:
    feature: str
    contribution: float
    direction: Direction
    rank: int
    feature_value: float | None


class ModelExplainer:
    """Per-prediction SHAP contributions for the three supported model types."""

    @classmethod
    def from_artifact(cls, artifact: ModelArtifact) -> ModelExplainer:
        return cls(
            artifact.pipeline,
            model_name=artifact.metadata.model_name,
            feature_names=artifact.feature_names,
            background_means=artifact.background_means,
        )

    def __init__(
        self,
        pipeline: Pipeline,
        *,
        model_name: ModelName,
        feature_names: tuple[str, ...],
        background_means: NDArray[np.float64] | None,
    ) -> None:
        self._features = feature_names
        self._name = model_name
        steps = pipeline.named_steps
        self._imputer = steps.get("impute")
        self._scaler = steps.get("scale")
        model = steps["model"]
        self._model = model
        self._explainer: Any
        if self._name in ("xgboost", "random_forest"):
            self._explainer = shap.TreeExplainer(model)
        elif self._name == "logistic_regression":
            if background_means is None:
                raise ValueError("logistic regression requires background_means for SHAP")
            masker = shap.maskers.Independent(np.asarray(background_means).reshape(1, -1))
            self._explainer = shap.LinearExplainer(model, masker)
        else:
            raise ValueError(f"unsupported model for explanations: {self._name}")

    def _transform(self, X: pd.DataFrame) -> FloatMatrix:
        frame = X.loc[:, list(self._features)].astype(float)
        if self._imputer is None:
            return frame.to_numpy(dtype=np.float64)
        z = self._imputer.transform(frame)
        if self._scaler is not None:
            z = self._scaler.transform(z)
        return np.asarray(z, dtype=np.float64)

    def _model_input(self, X: pd.DataFrame) -> Any:
        # XGBoost is fitted on a DataFrame; keep feature names so the booster sees the same schema.
        if self._imputer is None:
            return X.loc[:, list(self._features)].astype(float)
        return self._transform(X)

    @property
    def expected_value(self) -> float:
        ev = np.asarray(self._explainer.expected_value, dtype=np.float64).ravel()
        return float(ev[-1])  # positive class for per-class outputs

    def model_output(self, X: pd.DataFrame) -> NDArray[np.float64]:
        """The model quantity the contributions add up to (log-odds or probability)."""
        if self._name == "random_forest":
            return np.asarray(self._model.predict_proba(self._transform(X))[:, 1], dtype=np.float64)
        if self._name == "xgboost":
            return np.asarray(self._model.predict(self._model_input(X), output_margin=True), dtype=np.float64)
        return np.asarray(self._model.decision_function(self._transform(X)), dtype=np.float64)

    def contributions(self, X: pd.DataFrame) -> FloatMatrix:
        """Array (n_rows, n_features) of contributions in original feature order."""
        raw = self._explainer.shap_values(self._model_input(X))
        if isinstance(raw, list):  # older SHAP: one array per class
            raw = raw[-1]
        values: FloatMatrix = np.asarray(raw, dtype=np.float64)
        if values.ndim == 3:  # (rows, features, classes)
            values = values[:, :, -1]
        n = len(self._features)
        base: FloatMatrix = values[:, :n].copy()
        if self._imputer is not None and getattr(self._imputer, "indicator_", None) is not None:
            # Fold missing-indicator columns back into the feature they describe.
            indicator_features = np.asarray(self._imputer.indicator_.features_, dtype=np.int64)
            base[:, indicator_features] += values[:, n : n + indicator_features.size]
        if base.shape != (len(X), n):
            raise RuntimeError("unexpected SHAP output shape")
        return base

    def top_factors(self, X_row: pd.DataFrame, k: int) -> list[FactorContribution]:
        """Top-k factors for a single row, largest |contribution| first. Zero contributions
        are omitted: a feature that did not move the prediction is not a factor."""
        if len(X_row) != 1:
            raise ValueError("top_factors expects exactly one row")
        if k < 1:
            raise ValueError("k must be >= 1")
        contrib = self.contributions(X_row)[0]
        raw_values = X_row.loc[:, list(self._features)].astype(float).to_numpy()[0]
        order = np.argsort(-np.abs(contrib), kind="stable")
        factors: list[FactorContribution] = []
        for idx in order:
            value = float(contrib[idx])
            if value == 0.0 or not np.isfinite(value):
                continue
            raw = float(raw_values[idx])
            factors.append(
                FactorContribution(
                    feature=self._features[idx],
                    contribution=value,
                    direction="increases_risk" if value > 0 else "decreases_risk",
                    rank=len(factors) + 1,
                    feature_value=raw if np.isfinite(raw) else None,
                )
            )
            if len(factors) == k:
                break
        return factors

    def mean_abs_contribution(self, X: pd.DataFrame) -> dict[str, float]:
        """Global importance: mean |contribution| per feature over ``X``."""
        values = np.abs(self.contributions(X)).mean(axis=0)
        return {f: float(v) for f, v in zip(self._features, values, strict=True)}
