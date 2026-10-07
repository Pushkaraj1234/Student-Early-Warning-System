"""Validated configuration for the v3 longitudinal experiment (ml/configs/longitudinal_v3.json)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ml.data.oulad import presentation_sort_key
from ml.longitudinal.panel import PANEL_MAX_WEEK
from ml.longitudinal.sequence import SequenceKind
from ml.training.config import DatasetConfig, SplitConfig


def _precedes(earlier: tuple[str, ...], later: tuple[str, ...]) -> bool:
    return max(map(presentation_sort_key, earlier)) < min(map(presentation_sort_key, later))


class FoldConfig(BaseModel):
    """One rolling-origin fold: every training presentation precedes every test presentation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    train: tuple[str, ...] = Field(min_length=1)
    test: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered(self) -> FoldConfig:
        if not _precedes(self.train, self.test):
            raise ValueError("every training presentation must precede every test presentation")
        return self


class SequenceGrid(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kinds: tuple[SequenceKind, ...] = Field(min_length=1)
    hidden: tuple[int, ...] = Field(min_length=1)
    dropout: tuple[float, ...] = Field(min_length=1)
    max_epochs: int = Field(ge=1, le=200)
    patience: int = Field(ge=1, le=20)


class LongitudinalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,40}$")
    dataset: DatasetConfig
    first_week: int = Field(ge=1)
    last_week: int = Field(le=PANEL_MAX_WEEK)
    score_release_lag_days: int = Field(ge=0, le=90)
    split: SplitConfig
    rolling_origin: tuple[FoldConfig, ...] = Field(min_length=1)
    lomo_train: tuple[str, ...] = Field(min_length=1)
    lomo_test: tuple[str, ...] = Field(min_length=1)
    leakage_check_weeks: tuple[int, ...] = Field(min_length=1)
    xgb_search_settings: int = Field(ge=1, le=100)
    sequence_grid: SequenceGrid
    mc_dropout_samples: int = Field(ge=2, le=200)
    cost_ratios: tuple[float, ...] = Field(min_length=1)
    primary_cost_ratio: float = Field(gt=0)
    risk_level_quantiles: tuple[float, float, float]
    counterfactual_week: int = Field(ge=1)
    counterfactual_sample: int = Field(ge=1, le=5000)
    explain_sample: int = Field(ge=100, le=20000)
    bootstrap_resamples: int = Field(ge=50, le=10000)
    random_seed: int
    cache_dir: Path
    output_dir: Path
    report_dir: Path

    @property
    def weeks(self) -> tuple[int, ...]:
        return tuple(range(self.first_week, self.last_week + 1))

    @model_validator(mode="after")
    def _consistent(self) -> LongitudinalConfig:
        if self.first_week > self.last_week:
            raise ValueError("first_week must not exceed last_week")
        self.split.to_split().validate()
        if not _precedes(self.lomo_train, self.lomo_test):
            raise ValueError("every lomo_train presentation must precede every lomo_test presentation")
        if any(
            not self.first_week <= w <= self.last_week
            for w in (*self.leakage_check_weeks, self.counterfactual_week)
        ):
            raise ValueError("leakage_check_weeks and counterfactual_week must lie within the panel weeks")
        if self.primary_cost_ratio not in self.cost_ratios:
            raise ValueError("primary_cost_ratio must be one of cost_ratios")
        q = self.risk_level_quantiles
        if not 0 < q[0] < q[1] < q[2] < 1:
            raise ValueError("risk_level_quantiles must be increasing in (0, 1)")
        return self


def load_longitudinal_config(path: Path) -> LongitudinalConfig:
    with path.open(encoding="utf-8") as handle:
        return LongitudinalConfig.model_validate(json.load(handle))
