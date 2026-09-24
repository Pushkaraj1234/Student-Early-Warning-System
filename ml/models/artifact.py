"""Versioned model artifact: fitted pipeline (with preprocessing) + probability calibrator +
metadata. Saved as ``model.joblib`` plus ``metadata.json``; the metadata records the SHA-256
of ``model.joblib`` and loading refuses a file whose hash does not match.

joblib files are pickles and execute code when loaded: only load artifacts produced by this
pipeline, from a directory you control. The hash check detects corruption/tampering after
training; it is not a substitute for controlling who can write the artifact directory.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.pipeline import Pipeline

from ml.models.factory import ImbalanceStrategy, ModelName

MODEL_VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
MODEL_VERSION_RE = re.compile(MODEL_VERSION_PATTERN)
MODEL_FILE = "model.joblib"
METADATA_FILE = "metadata.json"

RiskLevel = Literal["stable", "watch", "elevated", "high"]
Provenance = Literal["benchmark", "synthetic", "institutional"]


class ArtifactError(RuntimeError):
    """Raised when an artifact is missing, corrupt or inconsistent."""


class RiskThresholds(BaseModel):
    """Calibrated-probability cut points (lower bounds) of each risk level above 'stable'."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    watch: float = Field(ge=0, le=1)
    elevated: float = Field(ge=0, le=1)
    high: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _increasing(self) -> RiskThresholds:
        if not self.watch < self.elevated < self.high:
            raise ValueError("thresholds must satisfy watch < elevated < high")
        return self

    def level(self, probability: float) -> RiskLevel:
        if probability >= self.high:
            return "high"
        if probability >= self.elevated:
            return "elevated"
        if probability >= self.watch:
            return "watch"
        return "stable"


class ModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    model_version: str = Field(pattern=MODEL_VERSION_PATTERN)
    model_name: ModelName
    feature_version: str = Field(pattern=MODEL_VERSION_PATTERN)
    feature_names: tuple[str, ...] = Field(min_length=1)
    dataset_name: str
    dataset_version: str = Field(pattern=MODEL_VERSION_PATTERN)
    data_provenance: Provenance
    cutoff_day: int = Field(ge=1)
    target_definition: str
    training_timestamp: datetime
    split: dict[str, list[str]]
    imbalance_strategy: ImbalanceStrategy
    hyperparameters: dict[str, Any]
    calibration_method: Literal["sigmoid", "isotonic", "none"]
    # V3+: which target the model predicts, and the evidence for applying (or not) calibration.
    target: Literal["academic", "dropout", "course_failure", "engagement"] = "academic"
    calibration_decision: dict[str, Any] = Field(default_factory=dict)
    leakage_check: dict[str, Any] = Field(default_factory=dict)
    risk_thresholds: RiskThresholds
    decision_threshold: float = Field(ge=0, le=1)
    explanation_units: str
    metrics: dict[str, Any]
    random_seed: int
    library_versions: dict[str, str]
    git_commit: str | None
    model_sha256: str = Field(default="", pattern=r"^([0-9a-f]{64})?$")

    @model_validator(mode="after")
    def _checks(self) -> ModelMetadata:
        if self.training_timestamp.tzinfo is None:
            raise ValueError("training_timestamp must be timezone-aware (UTC)")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names must be unique")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelArtifact:
    """A trained, calibrated model together with everything needed to use it correctly."""

    def __init__(
        self,
        *,
        pipeline: Pipeline,
        calibrator: Any,
        metadata: ModelMetadata,
        background_means: NDArray[np.float64] | None,
    ) -> None:
        self.pipeline = pipeline
        self.calibrator = calibrator
        self.metadata = metadata
        self.background_means = background_means

    @property
    def feature_names(self) -> tuple[str, ...]:
        return self.metadata.feature_names

    def _frame(self, X: pd.DataFrame) -> pd.DataFrame:
        missing = [f for f in self.feature_names if f not in X.columns]
        if missing:
            raise ArtifactError(f"input is missing features: {missing}")
        return X.loc[:, list(self.feature_names)].astype(float)

    def predict_raw(self, X: pd.DataFrame) -> NDArray[np.float64]:
        """Uncalibrated model probability of the adverse outcome."""
        return np.asarray(self.pipeline.predict_proba(self._frame(X))[:, 1], dtype=np.float64)

    def predict_proba(self, X: pd.DataFrame) -> NDArray[np.float64]:
        """Probability of the adverse outcome — calibrated only when calibration was shown to help
        (metadata.calibration_method == 'none' means the calibrator is the fitted pipeline itself)."""
        return np.asarray(self.calibrator.predict_proba(self._frame(X))[:, 1], dtype=np.float64)

    def save(self, directory: Path) -> ModelMetadata:
        """Write the artifact; returns the metadata including the model file hash."""
        directory.mkdir(parents=True, exist_ok=False)
        model_path = directory / MODEL_FILE
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "calibrator": self.calibrator,
                "background_means": self.background_means,
                "feature_names": self.feature_names,
            },
            model_path,
        )
        self.metadata = self.metadata.model_copy(update={"model_sha256": _sha256(model_path)})
        (directory / METADATA_FILE).write_text(self.metadata.model_dump_json(indent=2), encoding="utf-8")
        return self.metadata

    @classmethod
    def load(cls, directory: Path) -> ModelArtifact:
        metadata_path = directory / METADATA_FILE
        model_path = directory / MODEL_FILE
        if not metadata_path.is_file() or not model_path.is_file():
            raise ArtifactError(f"artifact files not found in {directory}")
        try:
            metadata = ModelMetadata.model_validate(json.loads(metadata_path.read_text(encoding="utf-8")))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid metadata in {metadata_path}: {exc}") from exc
        if not metadata.model_sha256 or _sha256(model_path) != metadata.model_sha256:
            raise ArtifactError(f"model file hash mismatch in {directory}")
        bundle = joblib.load(model_path)
        if not isinstance(bundle, dict) or tuple(bundle.get("feature_names", ())) != metadata.feature_names:
            raise ArtifactError("model bundle does not match its metadata")
        return cls(
            pipeline=bundle["pipeline"],
            calibrator=bundle["calibrator"],
            metadata=metadata,
            background_means=bundle["background_means"],
        )
