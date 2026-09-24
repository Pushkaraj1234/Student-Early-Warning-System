"""Runtime temporal-leakage guard.

For a cutoff ``t`` the features built from the FULL dataset must be identical to the features built
from the dataset truncated to information available on or before ``t`` (``ml.data.oulad.truncate_at``).
Any difference means a feature used future information; training must stop.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ml.data.contract import KEY_COLUMNS
from ml.data.oulad import OuladTables, truncate_at
from ml.features.definitions import feature_names
from ml.features.oulad_features import build_oulad_features


class TemporalLeakageError(RuntimeError):
    """Raised when a feature changes after removing information from after the cutoff."""


@dataclass(frozen=True)
class LeakageCheck:
    cutoff_day: int
    rows_compared: int
    features_compared: int


def assert_no_future_leakage(
    tables: OuladTables, cutoff_day: int, *, score_release_lag_days: int, feature_version: str
) -> LeakageCheck:
    names = list(feature_names(feature_version))
    full = build_oulad_features(
        tables, cutoff_day, score_release_lag_days=score_release_lag_days, feature_version=feature_version
    )
    truncated = build_oulad_features(
        truncate_at(tables, cutoff_day),
        cutoff_day,
        score_release_lag_days=score_release_lag_days,
        feature_version=feature_version,
    )
    keys = list(KEY_COLUMNS)
    full = full.sort_values(keys).reset_index(drop=True)
    truncated = truncated.sort_values(keys).reset_index(drop=True)
    if not full[keys].equals(truncated[keys]):
        raise TemporalLeakageError(f"population at day {cutoff_day} depends on future information")
    leaking = [
        name
        for name in names
        if not np.allclose(
            full[name].to_numpy(float), truncated[name].to_numpy(float), rtol=0, atol=1e-9, equal_nan=True
        )
    ]
    if leaking:
        raise TemporalLeakageError(f"features use information after day {cutoff_day}: {leaking}")
    return LeakageCheck(cutoff_day=cutoff_day, rows_compared=len(full), features_compared=len(names))
