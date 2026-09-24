"""Inference service: validate input, score with a versioned artifact, explain with SHAP.

Validation order (first failure wins): request shape -> empty features -> unknown features ->
missing features -> value types -> finiteness -> model resolution. Every failure raises an
:class:`InferenceError` with a stable code; :meth:`InferenceService.predict_safe` turns any
outcome into a JSON-serialisable envelope.

Provenance guard: a deployment that scores real students must be constructed with
``allowed_provenance={"institutional"}`` so that benchmark- or synthetic-trained models are
refused (error ``model_not_permitted``).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Collection, Mapping
from typing import Any
from uuid import uuid4

import pandas as pd
from pydantic import ValidationError

from ml.explainability.shap_explainer import ModelExplainer
from ml.inference.errors import InferenceError
from ml.inference.schemas import Factor, PredictionRequest, PredictionResponse
from ml.models.artifact import ArtifactError, ModelArtifact
from ml.models.registry import InvalidModelVersionError, ModelNotFoundError, ModelRegistry

logger = logging.getLogger(__name__)

ALL_PROVENANCE = frozenset({"benchmark", "synthetic", "institutional"})


def _validation_details(exc: ValidationError) -> list[dict[str, Any]]:
    # Deliberately omit the offending input values.
    return [
        {"field": ".".join(str(p) for p in err["loc"]), "type": err["type"], "message": err["msg"]}
        for err in exc.errors()
    ]


def validate_features(features: Mapping[str, Any], expected: tuple[str, ...]) -> dict[str, float]:
    """Return {feature: float} with NaN for explicit nulls, or raise InferenceError."""
    if not features:
        raise InferenceError("empty_input", "no features were provided")
    expected_set = set(expected)
    unknown = sorted(k for k in features if k not in expected_set)
    if unknown:
        raise InferenceError(
            "unknown_features", "request contains features the model does not use", {"features": unknown}
        )
    missing = sorted(f for f in expected if f not in features)
    if missing:
        raise InferenceError(
            "missing_features", "request is missing required features", {"features": missing}
        )
    wrong_type = sorted(
        name
        for name, value in features.items()
        if value is not None and (isinstance(value, bool) or not isinstance(value, int | float))
    )
    if wrong_type:
        raise InferenceError(
            "invalid_type", "feature values must be numbers or null", {"features": wrong_type}
        )
    non_finite = sorted(
        name for name, value in features.items() if value is not None and not math.isfinite(float(value))
    )
    if non_finite:
        raise InferenceError(
            "non_finite_value",
            "feature values must be finite (use null for missing)",
            {"features": non_finite},
        )
    return {name: (math.nan if features[name] is None else float(features[name])) for name in expected}


class InferenceService:
    def __init__(
        self, registry: ModelRegistry, *, allowed_provenance: Collection[str] = ALL_PROVENANCE
    ) -> None:
        unknown = set(allowed_provenance) - ALL_PROVENANCE
        if not allowed_provenance or unknown:
            raise ValueError(f"invalid allowed_provenance: {sorted(unknown) or 'empty'}")
        self._registry = registry
        self._allowed_provenance = frozenset(allowed_provenance)
        self._explainers: dict[str, ModelExplainer] = {}

    def _resolve(self, model_version: str | None) -> ModelArtifact:
        try:
            version = model_version if model_version is not None else self._registry.active_version()
        except (ModelNotFoundError, InvalidModelVersionError) as exc:
            raise InferenceError("model_unavailable", "no active model is available") from exc
        try:
            artifact = self._registry.load(version)
        except InvalidModelVersionError as exc:
            raise InferenceError("invalid_model_version", "model_version is not a valid identifier") from exc
        except ModelNotFoundError as exc:
            if model_version is None:
                raise InferenceError("model_unavailable", "the active model could not be found") from exc
            raise InferenceError(
                "model_not_found", "the requested model version does not exist", {"model_version": version}
            ) from exc
        except (ArtifactError, OSError, EOFError, ValueError) as exc:
            logger.exception("failed to load model artifact %s", version)
            raise InferenceError(
                "model_unavailable", "the model artifact could not be loaded", {"model_version": version}
            ) from exc
        if artifact.metadata.data_provenance not in self._allowed_provenance:
            raise InferenceError(
                "model_not_permitted",
                "this model's training-data provenance is not permitted here",
                {"model_version": version, "data_provenance": artifact.metadata.data_provenance},
            )
        return artifact

    def predict(self, payload: Mapping[str, Any]) -> PredictionResponse:
        if not isinstance(payload, Mapping):
            raise InferenceError("invalid_request", "request body must be an object")
        try:
            request = PredictionRequest.model_validate(dict(payload))
        except ValidationError as exc:
            raise InferenceError(
                "invalid_request", "request failed validation", {"errors": _validation_details(exc)}
            ) from exc
        if not request.features:
            raise InferenceError("empty_input", "no features were provided")

        artifact = self._resolve(request.model_version)
        values = validate_features(request.features, artifact.feature_names)
        X = pd.DataFrame([values], columns=list(artifact.feature_names), dtype=float)

        probability = float(artifact.predict_proba(X)[0])
        if not math.isfinite(probability):
            raise InferenceError("internal_error", "the model produced an invalid probability")
        probability = min(1.0, max(0.0, probability))

        meta = artifact.metadata
        explainer = self._explainers.get(meta.model_version)
        if explainer is None:
            explainer = ModelExplainer.from_artifact(artifact)
            self._explainers[meta.model_version] = explainer
        factors = explainer.top_factors(X, request.top_k)

        return PredictionResponse(
            prediction_id=uuid4(),
            student_id=request.student_id,
            prediction_date=request.prediction_date,
            model_version=meta.model_version,
            target=meta.target,
            feature_version=meta.feature_version,
            dataset_version=meta.dataset_version,
            data_provenance=meta.data_provenance,
            risk_probability=probability,
            risk_level=meta.risk_thresholds.level(probability),
            top_factors=[
                Factor(
                    feature=f.feature,
                    contribution=f.contribution,
                    direction=f.direction,
                    rank=f.rank,
                    feature_value=f.feature_value,
                )
                for f in factors
            ],
            explanation_units=meta.explanation_units,
        )

    def predict_safe(self, payload: Any) -> dict[str, Any]:
        """Never raises: returns {"ok": true, "data": ...} or {"ok": false, "error": ...}."""
        try:
            return {"ok": True, "data": self.predict(payload).model_dump(mode="json")}
        except InferenceError as exc:
            return {"ok": False, "error": exc.to_dict()}
        except Exception:
            logger.exception("unexpected inference failure")
            return {"ok": False, "error": InferenceError("internal_error", "unexpected error").to_dict()}
