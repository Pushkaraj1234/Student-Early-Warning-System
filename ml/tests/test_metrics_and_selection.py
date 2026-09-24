"""Metric correctness and selection-rule tests."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import average_precision_score

from ml.evaluation.metrics import (
    best_f1_threshold,
    bootstrap_ci,
    calibration_table,
    evaluate,
    expected_calibration_error,
    subgroup_metrics,
    threshold_metrics,
    top_fraction_metrics,
)
from ml.training.selection import Candidate, StrategyResult, choose_imbalance_strategy, select_model

Y = np.array([0, 0, 1, 1, 0, 1, 0, 1], dtype=np.int64)
P = np.array([0.1, 0.4, 0.35, 0.8, 0.2, 0.9, 0.6, 0.7], dtype=np.float64)


def test_threshold_metrics_confusion_matrix_by_hand() -> None:
    m = threshold_metrics(Y, P, 0.5)
    # predicted positive: 0.8, 0.9, 0.6, 0.7 -> tp = 3 (0.8, 0.9, 0.7), fp = 1 (0.6)
    assert m["confusion_matrix"] == {"tn": 3, "fp": 1, "fn": 1, "tp": 3}
    assert m["precision"] == pytest.approx(0.75)
    assert m["recall"] == pytest.approx(0.75)
    assert m["per_class"]["0"]["support"] == 4
    assert m["false_positive_rate"] == pytest.approx(0.25)


def test_top_fraction_uses_highest_scores() -> None:
    m = top_fraction_metrics(Y, P, 0.25)  # top 2 of 8: 0.9, 0.8 -> both positive
    assert m["flagged"] == 2
    assert m["precision"] == 1.0
    assert m["recall"] == 0.5


def test_calibration_metrics() -> None:
    perfect_y = np.array([0, 1] * 50, dtype=np.int64)
    perfect_p = np.full(100, 0.5)
    assert expected_calibration_error(perfect_y, perfect_p) == pytest.approx(0.0)
    over = np.full(100, 0.9)
    assert expected_calibration_error(perfect_y, over) == pytest.approx(0.4)
    table = calibration_table(Y, P, n_bins=2)
    assert sum(int(r["count"]) for r in table) == len(Y)


def test_evaluate_reports_required_metrics_and_no_accuracy() -> None:
    m = evaluate(Y, P, threshold=0.5, top_fractions=[0.25])
    for key in ("roc_auc", "pr_auc", "brier", "ece", "at_threshold", "calibration_table", "top_fraction"):
        assert key in m
    assert "accuracy" not in m
    assert m["pr_auc"] == pytest.approx(average_precision_score(Y, P))


def test_best_f1_threshold_is_a_score_value() -> None:
    t = best_f1_threshold(Y, P)
    assert t in set(P.tolist())


def test_bootstrap_is_deterministic_and_brackets_the_estimate() -> None:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400).astype(np.int64)
    p = np.clip(y * 0.3 + rng.uniform(0, 0.7, 400), 0, 1)
    clusters = np.repeat(np.arange(200), 2).astype(str)
    fn = {"pr_auc": lambda a, b: float(average_precision_score(a, b))}
    a = bootstrap_ci(y, p, clusters, fn, iterations=100, seed=1)
    b = bootstrap_ci(y, p, clusters, fn, iterations=100, seed=1)
    assert a == b
    point = average_precision_score(y, p)
    assert a["pr_auc"]["low"] <= point <= a["pr_auc"]["high"]


def test_subgroups_below_minimum_size_report_no_metrics() -> None:
    groups = np.array(["a"] * 4 + ["b"] * 4)
    rows = subgroup_metrics(Y, P, groups, threshold=0.5, min_size=100)
    assert all(r["insufficient_data"] for r in rows)
    assert all("recall" not in r for r in rows)


@pytest.mark.parametrize(
    ("y", "p"),
    [
        (np.array([0, 1], dtype=np.int64), np.array([0.5, np.nan])),
        (np.array([0, 2], dtype=np.int64), np.array([0.5, 0.5])),
        (np.array([0, 1], dtype=np.int64), np.array([0.5, 1.5])),
        (np.array([], dtype=np.int64), np.array([], dtype=np.float64)),
    ],
)
def test_invalid_metric_inputs_are_rejected(y: np.ndarray, p: np.ndarray) -> None:
    with pytest.raises(ValueError):
        evaluate(y, p, threshold=0.5, top_fractions=[0.1])


# ------------------------------------------------------------------ selection rules


def test_unweighted_training_preferred_when_balancing_barely_helps() -> None:
    strategy, why = choose_imbalance_strategy(
        [
            StrategyResult("none", 0.700, 0.80, 0.18),
            StrategyResult("balanced", 0.703, 0.80, 0.20),
        ]
    )
    assert strategy == "none"
    assert "distorts" in why


def test_balancing_chosen_when_it_clearly_helps() -> None:
    strategy, _ = choose_imbalance_strategy(
        [
            StrategyResult("none", 0.60, 0.80, 0.18),
            StrategyResult("balanced", 0.65, 0.82, 0.20),
        ]
    )
    assert strategy == "balanced"


def test_selection_prefers_interpretable_model_within_tolerance() -> None:
    chosen, why = select_model(
        [
            Candidate("xgboost", 0.750, 0.170, 0.002),
            Candidate("random_forest", 0.748, 0.171, 0.003),
            Candidate("logistic_regression", 0.742, 0.175, 0.0),
        ],
        tolerance=0.01,
    )
    assert chosen == "logistic_regression"
    assert "most interpretable" in why


def test_selection_does_not_pick_a_clearly_worse_model() -> None:
    chosen, _ = select_model(
        [
            Candidate("xgboost", 0.80, 0.16, 0.002),
            Candidate("logistic_regression", 0.70, 0.18, 0.0),
        ],
        tolerance=0.01,
    )
    assert chosen == "xgboost"
