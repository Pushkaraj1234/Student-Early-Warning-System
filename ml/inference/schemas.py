"""Explicit inference API contract.

Request:  student_id, prediction_date, features {name: number | null}, optional model_version, top_k
Response: api_version, prediction_id, model_version, target, risk_probability, risk_level, top_factors,
          plus lineage (feature_version, dataset_version, data_provenance, explanation_units).

API_VERSION follows semantic versioning and must match ``inference_api`` in
public.get_platform_versions(); a breaking contract change requires a new major version.

``null`` is the only way to say "this feature is not available at prediction time".
NaN, +/-infinity, booleans and strings are rejected.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ml.models.artifact import MODEL_VERSION_PATTERN, Provenance, RiskLevel

API_VERSION: Literal["1.0.0"] = "1.0.0"


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    student_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    prediction_date: date
    features: dict[str, Any]
    model_version: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class Factor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str
    contribution: float
    direction: Literal["increases_risk", "decreases_risk"]
    rank: int = Field(ge=1)
    feature_value: float | None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    api_version: Literal["1.0.0"] = API_VERSION
    prediction_id: UUID
    student_id: str
    prediction_date: date
    model_version: str = Field(pattern=MODEL_VERSION_PATTERN)
    target: Literal["academic", "dropout", "course_failure", "engagement"]
    feature_version: str
    dataset_version: str
    data_provenance: Provenance
    risk_probability: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    top_factors: list[Factor]
    explanation_units: str
