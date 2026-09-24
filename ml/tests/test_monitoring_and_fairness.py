"""Drift monitoring, subgroup disparity summaries and JSON cleaning."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ml.evaluation.metrics import DISPARITY_METRICS, disparity_summary, subgroup_metrics
from ml.monitoring.drift import (
    clean_for_json,
    feature_drift,
    monitoring_snapshot,
    outcome_drift,
    performance_drop,
    prediction_drift,
    psi,
)


def _rng() -> np.random.Generator:
    return np.random.default_rng(7)


def test_psi_is_near_zero_for_the_same_distribution() -> None:
    rng = _rng()
    value = psi(rng.normal(size=5000), rng.normal(size=5000))
    assert value is not None and value < 0.02


def test_psi_detects_a_shift() -> None:
    rng = _rng()
    value = psi(rng.normal(size=5000), rng.normal(loc=1.0, size=5000))
    assert value is not None and value > 0.25


def test_psi_ignores_missing_values_and_handles_constants() -> None:
    assert psi(np.array([np.nan, np.nan]), np.array([1.0])) is None
    same = psi(np.zeros(100), np.zeros(100))
    assert same is not None and same < 1e-6
    changed = psi(np.zeros(100), np.ones(100))
    assert changed is not None and changed > 0.25


def test_feature_drift_reports_psi_and_missingness_alerts() -> None:
    rng = _rng()
    ref = pd.DataFrame({"a": rng.normal(size=2000), "b": rng.normal(size=2000)})
    cur = pd.DataFrame({"a": rng.normal(loc=2.0, size=2000), "b": rng.normal(size=2000)})
    cur.loc[:399, "b"] = np.nan  # 20% newly missing
    stats, alerts = feature_drift(ref, cur, ["a", "b"])
    assert [s["feature"] for s in stats] == ["a", "b"]
    kinds = {(a.alert_type, a.subject, a.severity) for a in alerts}
    assert ("feature_drift", "a", "critical") in kinds
    assert ("missingness_drift", "b", "critical") in kinds
    assert not any(a.alert_type == "feature_drift" and a.subject == "b" for a in alerts)


@pytest.mark.parametrize(
    ("ref", "cur", "severity"),
    [(0.30, 0.31, None), (0.30, 0.36, "warning"), (0.30, 0.45, "critical")],
)
def test_outcome_drift_thresholds(ref: float, cur: float, severity: str | None) -> None:
    alerts = outcome_drift(ref, cur)
    assert [a.severity for a in alerts] == ([] if severity is None else [severity])


def test_performance_drop_only_alerts_on_a_drop() -> None:
    assert performance_drop(0.70, 0.80) == []
    assert [a.severity for a in performance_drop(0.70, 0.64)] == ["warning"]
    assert [a.severity for a in performance_drop(0.70, 0.55)] == ["critical"]


def test_prediction_drift_returns_value_and_alerts() -> None:
    rng = _rng()
    value, alerts = prediction_drift(rng.uniform(size=3000), rng.uniform(size=3000) ** 3)
    assert value is not None and value > 0.25
    assert alerts and alerts[0].alert_type == "prediction_drift"


def test_monitoring_snapshot_is_aggregate_only() -> None:
    features = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]})
    levels = ["stable", "stable", "high", "high"]
    snap = monitoring_snapshot(np.array([0.1, 0.2, 0.8, 0.9]), levels, features, ["x"])
    assert snap["n_predictions"] == 4
    assert snap["level_distribution"] == {"stable": 2, "high": 2}
    assert snap["feature_stats"]["x"]["missing_rate"] == 0.25
    assert set(snap) == {"n_predictions", "level_distribution", "probability_quantiles", "feature_stats"}
    with pytest.raises(ValueError):
        monitoring_snapshot(np.array([]), [], features.head(0), ["x"])


def test_clean_for_json_replaces_non_finite_values() -> None:
    cleaned = clean_for_json({"a": math.nan, "b": [math.inf, 1.0], "c": {"d": -math.inf}})
    assert cleaned == {"a": None, "b": [None, 1.0], "c": {"d": None}}


def _group_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = 400
    y = np.tile([1, 0, 0, 0], n // 4).astype(np.int64)
    groups = np.array(["A"] * (n // 2) + ["B"] * (n // 2))
    # group A is scored well, group B close to chance
    p = np.where(groups == "A", np.where(y == 1, 0.8, 0.2), _rng().uniform(size=n))
    return y, p, groups


def test_subgroup_metrics_include_fnr_and_calibration() -> None:
    y, p, groups = _group_data()
    rows = subgroup_metrics(y, p, groups, threshold=0.5)
    a = next(r for r in rows if r["group"] == "A")
    assert a["false_negative_rate"] == pytest.approx(1 - a["recall"])
    assert a["calibration_gap"] == pytest.approx(a["mean_predicted"] - a["prevalence"])
    assert 0 <= a["ece"] <= 1


def test_disparity_summary_reports_largest_gap() -> None:
    y, p, groups = _group_data()
    summary = disparity_summary(subgroup_metrics(y, p, groups, threshold=0.5))
    assert set(summary) == set(DISPARITY_METRICS)
    assert summary["recall"]["max_group"] == "A" and summary["recall"]["gap"] > 0
    assert summary["false_negative_rate"]["max_group"] == "B"


def test_disparity_summary_skips_small_groups() -> None:
    y, p, groups = _group_data()
    groups = groups.astype(object)
    groups[:5] = "tiny"
    rows = subgroup_metrics(y, p, groups, threshold=0.5)
    assert next(r for r in rows if r["group"] == "tiny")["insufficient_data"] is True
    only_one = disparity_summary([r for r in rows if r["group"] in {"A", "tiny"}])
    assert all(v["gap"] is None for v in only_one.values())
