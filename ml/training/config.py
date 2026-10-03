"""Validated training configuration (loaded from a JSON file such as ml/configs/oulad_v1.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ml.features.definitions import FEATURE_SETS, FEATURE_VERSION
from ml.models.factory import ImbalanceStrategy, ModelName
from ml.training.splits import TemporalSplit

Target = Literal["academic", "dropout", "course_failure", "engagement"]

Provenance = Literal["benchmark", "synthetic", "institutional"]


class DatasetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["OULAD"]
    path: Path
    provenance: Provenance
    description: str = Field(min_length=10)


class SplitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    train: tuple[str, ...]
    validation: tuple[str, ...]
    test: tuple[str, ...]

    def to_split(self) -> TemporalSplit:
        return TemporalSplit(train=self.train, validation=self.validation, test=self.test)


class CalibrationCheckConfig(BaseModel):
    """Out-of-time check deciding whether calibration is applied: fit the model on ``train``, the
    calibrator on ``calibrate``, compare raw vs calibrated Brier and ECE on ``evaluate``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    train: tuple[str, ...]
    calibrate: tuple[str, ...]
    evaluate: tuple[str, ...]

    def to_split(self) -> TemporalSplit:
        return TemporalSplit(train=self.train, validation=self.calibrate, test=self.evaluate)


class RiskLevelQuantiles(BaseModel):
    """Validation-set quantiles of calibrated probability that open each risk level."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    watch: float = Field(gt=0, lt=1)
    elevated: float = Field(gt=0, lt=1)
    high: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def _increasing(self) -> RiskLevelQuantiles:
        if not self.watch < self.elevated < self.high:
            raise ValueError("risk level quantiles must satisfy watch < elevated < high")
        return self


class ModelSelectionConfig(BaseModel):
    """How candidate models are trained, compared, calibrated and selected, independent of the data
    source. Shared by benchmark training (TrainingConfig) and institutional training
    (services/sews_services/training)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # A (target, cutoff) is trained only if every split has at least this many positives AND negatives;
    # otherwise it is skipped and the reason recorded ("where data suffices").
    min_class_count_per_split: int = Field(default=20, ge=5)
    models: tuple[ModelName, ...] = Field(min_length=1)
    imbalance_strategies: tuple[ImbalanceStrategy, ...] = Field(min_length=1)
    calibration_method: Literal["sigmoid", "isotonic"]
    risk_level_quantiles: RiskLevelQuantiles
    top_fractions: tuple[float, ...] = Field(min_length=1)
    selection_tolerance_pr_auc: float = Field(ge=0, le=0.1)
    stability_seeds: tuple[int, ...] = Field(min_length=2)
    bootstrap_iterations: int = Field(ge=50, le=10000)
    random_seed: int

    @field_validator("top_fractions")
    @classmethod
    def _fractions(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(not 0 < v < 1 for v in value):
            raise ValueError("top_fractions must be in (0, 1)")
        return value


class TrainingConfig(ModelSelectionConfig):
    run_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,40}$")
    dataset: DatasetConfig
    feature_version: str = FEATURE_VERSION
    targets: tuple[Target, ...] = ("academic",)
    primary_target: Target = "academic"
    calibration_check: CalibrationCheckConfig | None = None
    cutoff_days: tuple[int, ...] = Field(min_length=1)
    primary_cutoff_day: int
    score_release_lag_days: int = Field(ge=0, le=90)
    split: SplitConfig
    output_dir: Path
    report_dir: Path

    @field_validator("cutoff_days")
    @classmethod
    def _positive_unique(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(v < 1 for v in value) or len(set(value)) != len(value):
            raise ValueError("cutoff_days must be unique positive integers")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _primary_in_cutoffs(self) -> TrainingConfig:
        if self.primary_cutoff_day not in self.cutoff_days:
            raise ValueError("primary_cutoff_day must be one of cutoff_days")
        self.split.to_split().validate()
        if self.feature_version not in FEATURE_SETS:
            raise ValueError(f"unknown feature_version: {self.feature_version}")
        if len(set(self.targets)) != len(self.targets) or self.primary_target not in self.targets:
            raise ValueError("targets must be unique and include primary_target")
        if self.calibration_check is not None:
            self.calibration_check.to_split().validate()
        return self


def load_config(path: Path) -> TrainingConfig:
    with path.open(encoding="utf-8") as handle:
        return TrainingConfig.model_validate(json.load(handle))
