"""Validated configuration for institutional training (default file: ml/configs/institutional_v1.json).

The model-selection settings (models, imbalance strategies, calibration, thresholds, bootstrap, seeds) are the
same fields benchmark training uses (ml.training.config.ModelSelectionConfig), so both are evaluated alike.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field, field_validator

from ml.training.config import ModelSelectionConfig

DEFAULT_CONFIG = Path("ml/configs/institutional_v1.json")


class InstitutionalTrainingConfig(ModelSelectionConfig):
    run_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,24}$")
    # Decision points: days after the start of the term.
    cutoff_days: tuple[int, ...] = Field(min_length=1)
    # A completed term is used only if at least this share of its students has a known label (results published).
    min_label_coverage: float = Field(gt=0, le=1)

    @field_validator("cutoff_days")
    @classmethod
    def _positive_unique(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(v < 1 for v in value) or len(set(value)) != len(value):
            raise ValueError("cutoff_days must be unique positive integers")
        return tuple(sorted(value))


def load_training_config(path: Path) -> InstitutionalTrainingConfig:
    with path.open(encoding="utf-8") as handle:
        return InstitutionalTrainingConfig.model_validate(json.load(handle))
