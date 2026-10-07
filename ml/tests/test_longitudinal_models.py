"""v3 models and evaluation helpers: thresholds, alert policies, survival, causality of sequence models,
tabular pipelines and counterfactuals. Synthetic inputs only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from ml.evaluation.metrics import best_f1_threshold
from ml.longitudinal.alerts import (
    alert_flags,
    cost_threshold,
    fbeta_threshold,
    student_alert_table,
    student_metrics,
)
from ml.longitudinal.counterfactual import find_counterfactual
from ml.longitudinal.sequence import (
    Standardizer,
    build_sequence_model,
    predict_sequences,
    scatter_to_rows,
    to_sequences,
    train_sequence_model,
)
from ml.longitudinal.survival import concordance_index, kaplan_meier, risk_within, survival_at
from ml.longitudinal.tabular import build_tabular, proba, xgb_search_settings


def _scores(seed: int, n: int = 600) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n).astype(np.int64)
    return y, 1 / (1 + np.exp(-(2 * y - 1 + rng.normal(0, 1.5, n))))


# ------------------------------------------------------------------ thresholds and alerts
def test_fbeta_threshold_matches_f1_and_lowers_for_recall() -> None:
    y, p = _scores(1)
    assert fbeta_threshold(y, p, 1.0) == pytest.approx(best_f1_threshold(y, p))
    assert fbeta_threshold(y, p, 2.0) <= fbeta_threshold(y, p, 1.0)


def test_cost_threshold_by_hand() -> None:
    y = np.array([1, 1, 0, 0, 1, 0])
    p = np.array([0.9, 0.8, 0.7, 0.4, 0.3, 0.1])
    # cost_fn=1, cost_fp=1: flagging top 2 -> FN 1, FP 0 = cost 1 (best); threshold 0.8.
    assert cost_threshold(y, p, cost_fn=1, cost_fp=1) == 0.8
    # cost_fn=10: missing anyone is expensive -> flag down to 0.3 (FN 0, FP 2 = cost 2).
    assert cost_threshold(y, p, cost_fn=10, cost_fp=1) == 0.3
    # The highest risk is a negative and false alarms are very costly: flag nobody (threshold above all).
    y2, p2 = np.array([0, 1]), np.array([0.9, 0.8])
    assert cost_threshold(y2, p2, cost_fn=1, cost_fp=100) > 0.9


def _alert_frame() -> tuple[pd.DataFrame, np.ndarray]:
    frame = pd.DataFrame(
        {
            "context_id": ["M-2014J"] * 8,
            "student_id": ["a"] * 4 + ["b"] * 4,
            "week": [1, 2, 3, 4] * 2,
            "y_academic": [1.0] * 4 + [0.0] * 4,
            "withdraw_week": [6.0] * 4 + [np.nan] * 4,
            "course_end_week": [30.0] * 8,
        }
    )
    risk = np.array([0.2, 0.7, 0.8, 0.9, 0.7, 0.2, 0.7, 0.1])
    return frame.iloc[::-1].reset_index(drop=True), risk[::-1].copy()  # policies must not depend on row order


def test_alert_policies() -> None:
    frame, risk = _alert_frame()
    order = frame.sort_values(["student_id", "week"]).index.to_numpy()
    raw = alert_flags(frame, risk, 0.6, "raw")[order]
    consecutive = alert_flags(frame, risk, 0.6, "consecutive_2")[order]
    ewma = alert_flags(frame, risk, 0.6, "ewma")[order]
    assert raw.tolist() == [False, True, True, True, True, False, True, False]
    assert consecutive.tolist() == [False, False, True, True, False, False, False, False]
    # a: 0.2, 0.45, 0.625, 0.7625; b: 0.7, 0.45, 0.575, 0.3375
    assert ewma.tolist() == [False, False, True, True, True, False, False, False]


def test_student_alert_table_and_metrics() -> None:
    frame, risk = _alert_frame()
    table = student_alert_table(frame, alert_flags(frame, risk, 0.6, "raw")).set_index("student_id")
    assert (
        table.loc["a", "first_alert_week"] == 2 and table.loc["a", "lead_time_weeks"] == 4
    )  # withdraws week 6
    assert table.loc["b", "flips"] == 3  # on, off, on, off
    assert bool(table["lead_time_weeks"].isna()["b"])  # not adverse: no lead time
    m = student_metrics(table.reset_index())
    assert (m["recall"], m["false_alarm_rate"], m["precision"]) == (1.0, 1.0, 0.5)
    smoothed = student_metrics(student_alert_table(frame, alert_flags(frame, risk, 0.6, "consecutive_2")))
    assert smoothed["false_alarm_rate"] == 0.0 and smoothed["recall"] == 1.0


# ------------------------------------------------------------------ survival
def test_kaplan_meier_by_hand() -> None:
    durations = np.array([2.0, 3.0, 3.0, 5.0, 8.0])
    events = np.array([True, True, False, True, False])
    curve = kaplan_meier(durations, events)
    assert curve["time"].tolist() == [2.0, 3.0, 5.0]
    assert curve["survival"].tolist() == pytest.approx([4 / 5, 4 / 5 * 3 / 4, 4 / 5 * 3 / 4 * 1 / 2])
    assert survival_at(curve, 1.0) == 1.0 and survival_at(curve, 4.0) == pytest.approx(0.6)


def test_concordance_index() -> None:
    durations = np.array([1.0, 2.0, 3.0, 4.0])
    events = np.array([True, True, True, False])
    assert concordance_index(durations, events, np.array([4.0, 3.0, 2.0, 1.0])) == 1.0
    assert concordance_index(durations, events, np.array([1.0, 2.0, 3.0, 4.0])) == 0.0
    assert concordance_index(durations, events, np.ones(4)) == 0.5
    assert risk_within(np.array([0.0, 0.5]), 2).tolist() == [0.0, 0.75]


# ------------------------------------------------------------------ sequence models
@pytest.mark.parametrize("kind", ["gru", "lstm", "tcn"])
def test_sequence_models_are_causal(kind: str) -> None:
    torch.manual_seed(0)
    model = build_sequence_model(kind, width=5, hidden=8, dropout=0.0)  # type: ignore[arg-type]
    model.eval()
    x = torch.randn(3, 10, 5)
    changed = x.clone()
    changed[:, 6:, :] = torch.randn(3, 4, 5)
    with torch.no_grad():
        a, b = model(x), model(changed)
    assert torch.allclose(a[:, :6], b[:, :6])  # weeks before the change are unaffected
    assert not torch.allclose(a[:, 6:], b[:, 6:])


def _sequence_frame(seed: int, n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        weeks = int(rng.integers(3, 9))
        level = rng.normal()
        for w in range(1, weeks + 1):
            signal = level + rng.normal(0, 0.3)
            rows.append(
                {
                    "context_id": "M-2014J",
                    "student_id": f"s{i}",
                    "week": w,
                    "f1": signal,
                    "f2": np.nan if w == 1 else rng.normal(),
                    "y": float(level > 0),
                }
            )
    return pd.DataFrame(rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)


def test_sequences_round_trip_and_training_learns() -> None:
    train_frame, val_frame = _sequence_frame(1), _sequence_frame(2)
    std = Standardizer.fit(train_frame, ["f1", "f2"])
    assert std.width == 3  # f2 has missing values in training -> one indicator channel
    train, val = (to_sequences(f, "y", std, max_week=8) for f in (train_frame, val_frame))
    marker = np.arange(train.X.shape[0] * 8, dtype=np.float64).reshape(-1, 8)
    rows = scatter_to_rows(marker, train, len(train_frame))
    assert np.unique(rows).size == len(train_frame)  # every row mapped once
    model, log = train_sequence_model(
        "gru", train, hidden=8, dropout=0.1, seed=0, epochs=40, validation=val, batch_size=16
    )
    assert log.val_loss[log.best_epoch - 1] < log.val_loss[0]
    p = scatter_to_rows(predict_sequences(model, val), val, len(val_frame))
    y = val_frame["y"].to_numpy()
    assert p[y == 1].mean() > p[y == 0].mean() + 0.2
    mc = predict_sequences(model, val, mc_samples=5, seed=0)
    assert mc.shape == (5, *val.y.shape) and mc.std(axis=0).max() > 0


# ------------------------------------------------------------------ tabular
@pytest.mark.parametrize("imbalance", ["none", "weights", "smote"])
@pytest.mark.parametrize("name", ["l1_logistic", "random_forest", "xgboost"])
def test_tabular_pipelines_fit_with_missing_values(name: str, imbalance: str) -> None:
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"a": rng.normal(size=400), "b": rng.normal(size=400)})
    X.loc[::7, "b"] = np.nan
    y = (X["a"] + rng.normal(0, 0.5, 400) > 1.0).astype(np.int64).to_numpy()
    params = (
        {"C": 1.0} if name == "l1_logistic" else ({"n_estimators": 20} if name != "random_forest" else {})
    )
    pipe = build_tabular(name, imbalance, params=params, y_train=y, seed=0).fit(X, y)  # type: ignore[arg-type]
    p = proba(pipe, X)
    assert p[y == 1].mean() > p[y == 0].mean()
    assert ("smote" in pipe.named_steps) == (imbalance == "smote")


def test_xgb_search_settings_are_distinct_and_reproducible() -> None:
    a, b = xgb_search_settings(12, 5), xgb_search_settings(12, 5)
    assert a == b and len({tuple(s.values()) for s in a}) == 12


# ------------------------------------------------------------------ counterfactuals
def test_counterfactual_finds_fewest_improving_changes() -> None:
    def predict(frame: pd.DataFrame) -> np.ndarray:  # risk falls with activity and completion
        return np.asarray(
            0.9 - 0.004 * frame["clicks_this_week"] - 0.5 * frame["assignment_completion_rate"].fillna(0)
        )

    features = {"clicks_this_week": "increase", "assignment_completion_rate": "increase"}
    candidates = {"clicks_this_week": (20.0, 50.0, 100.0), "assignment_completion_rate": (0.5, 0.8, 1.0)}
    row = pd.DataFrame({"clicks_this_week": [10.0], "assignment_completion_rate": [0.2]})
    single = find_counterfactual(row, predict, 0.5, candidates, features)  # type: ignore[arg-type]
    assert single is not None and len(single.changes) == 1 and single.risk_after < 0.5
    hard = find_counterfactual(row, predict, 0.25, candidates, features)  # type: ignore[arg-type]
    assert hard is not None and len(hard.changes) == 2
    assert find_counterfactual(row, predict, 0.0, candidates, features) is None  # type: ignore[arg-type]
