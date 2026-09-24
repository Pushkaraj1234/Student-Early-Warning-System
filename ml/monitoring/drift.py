"""Model monitoring: distribution drift, missingness, prediction/outcome shifts, performance drops.

Thresholds are conventional heuristics, not validated SEWS-specific limits (docs/ml/monitoring.md):
  PSI                      warning >= 0.10, critical >= 0.25   (common population-stability rule of thumb)
  missing-rate change      warning >= 0.05, critical >= 0.15   (absolute change in the share missing)
  outcome-rate change      warning >= 0.05, critical >= 0.10   (absolute change in prevalence)
  PR-AUC drop              warning >= 0.05, critical >= 0.10   (absolute drop vs the validation value)
Snapshots contain aggregates only — never student identifiers.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray

AlertType = Literal[
    "feature_drift", "missingness_drift", "prediction_drift", "outcome_drift", "performance_drop"
]
Severity = Literal["warning", "critical"]

PSI_WARNING, PSI_CRITICAL = 0.10, 0.25
MISSING_WARNING, MISSING_CRITICAL = 0.05, 0.15
RATE_WARNING, RATE_CRITICAL = 0.05, 0.10
PERFORMANCE_WARNING, PERFORMANCE_CRITICAL = 0.05, 0.10


@dataclass(frozen=True)
class DriftAlert:
    alert_type: AlertType
    subject: str
    statistic: Literal["psi", "missing_rate_change", "rate_change", "metric_drop"]
    value: float
    threshold: float
    severity: Severity

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _severity(value: float, warning: float, critical: float) -> tuple[Severity, float] | None:
    if value >= critical:
        return "critical", critical
    if value >= warning:
        return "warning", warning
    return None


def psi(
    reference: NDArray[np.float64], current: NDArray[np.float64], bins: int = 10, eps: float = 1e-4
) -> float | None:
    """Population stability index over reference-quantile bins (NaNs ignored). None if undefined."""
    ref = reference[np.isfinite(reference)]
    cur = current[np.isfinite(current)]
    if ref.size == 0 or cur.size == 0:
        return None
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if edges.size < 2:  # constant reference: compare "equal to it" vs "different"
        ref_p = np.array([1.0, 0.0])
        same = float(np.mean(cur == edges[0]))
        cur_p = np.array([same, 1.0 - same])
    else:
        inner = edges[1:-1]
        ref_p = np.bincount(np.searchsorted(inner, ref, side="right"), minlength=inner.size + 1) / ref.size
        cur_p = np.bincount(np.searchsorted(inner, cur, side="right"), minlength=inner.size + 1) / cur.size
    ref_p = np.clip(ref_p, eps, None)
    cur_p = np.clip(cur_p, eps, None)
    return float(np.sum((cur_p - ref_p) * np.log(cur_p / ref_p)))


def feature_drift(
    reference: pd.DataFrame, current: pd.DataFrame, features: Sequence[str]
) -> tuple[list[dict[str, Any]], list[DriftAlert]]:
    stats: list[dict[str, Any]] = []
    alerts: list[DriftAlert] = []
    for name in features:
        ref = reference[name].to_numpy(dtype=float)
        cur = current[name].to_numpy(dtype=float)
        value = psi(ref, cur)
        missing_change = abs(float(np.isnan(cur).mean()) - float(np.isnan(ref).mean()))
        stats.append({"feature": name, "psi": value, "missing_rate_change": missing_change})
        if value is not None and (sev := _severity(value, PSI_WARNING, PSI_CRITICAL)):
            alerts.append(DriftAlert("feature_drift", name, "psi", value, sev[1], sev[0]))
        if sev := _severity(missing_change, MISSING_WARNING, MISSING_CRITICAL):
            alerts.append(
                DriftAlert("missingness_drift", name, "missing_rate_change", missing_change, sev[1], sev[0])
            )
    return stats, alerts


def prediction_drift(
    reference: NDArray[np.float64], current: NDArray[np.float64]
) -> tuple[float | None, list[DriftAlert]]:
    value = psi(reference, current)
    if value is not None and (sev := _severity(value, PSI_WARNING, PSI_CRITICAL)):
        return value, [DriftAlert("prediction_drift", "prediction", "psi", value, sev[1], sev[0])]
    return value, []


def outcome_drift(reference_rate: float, current_rate: float) -> list[DriftAlert]:
    change = abs(current_rate - reference_rate)
    if sev := _severity(change, RATE_WARNING, RATE_CRITICAL):
        return [DriftAlert("outcome_drift", "outcome", "rate_change", change, sev[1], sev[0])]
    return []


def performance_drop(reference: float, current: float, metric: str = "pr_auc") -> list[DriftAlert]:
    drop = reference - current
    if sev := _severity(drop, PERFORMANCE_WARNING, PERFORMANCE_CRITICAL):
        return [DriftAlert("performance_drop", metric, "metric_drop", drop, sev[1], sev[0])]
    return []


def monitoring_snapshot(
    probabilities: NDArray[np.float64],
    levels: Sequence[str],
    features: pd.DataFrame,
    feature_names: Sequence[str],
) -> dict[str, Any]:
    """Aggregate-only snapshot matching public.model_monitoring_snapshots."""
    if probabilities.size == 0:
        raise ValueError("snapshot requires at least one prediction")
    level_counts = pd.Series(list(levels)).value_counts()
    feature_stats: dict[str, dict[str, float | None]] = {}
    for name in feature_names:
        col = features[name].to_numpy(dtype=float)
        finite = col[np.isfinite(col)]
        feature_stats[name] = {
            "missing_rate": float(np.isnan(col).mean()),
            "mean": float(finite.mean()) if finite.size else None,
            "std": float(finite.std()) if finite.size else None,
            "p10": float(np.quantile(finite, 0.1)) if finite.size else None,
            "p50": float(np.quantile(finite, 0.5)) if finite.size else None,
            "p90": float(np.quantile(finite, 0.9)) if finite.size else None,
        }
    return {
        "n_predictions": int(probabilities.size),
        "level_distribution": {str(k): int(v) for k, v in level_counts.items()},
        "probability_quantiles": {
            f"p{int(q * 100)}": float(np.quantile(probabilities, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)
        },
        "feature_stats": feature_stats,
    }


def clean_for_json(value: Any) -> Any:
    """Replace NaN/inf with None so reports are valid JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean_for_json(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [clean_for_json(v) for v in value]
    return value
