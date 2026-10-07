"""v3 student-week panel: hand-computed feature values, labels and the leakage guard. Synthetic data only."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.data.oulad import load_oulad
from ml.features.leakage import TemporalLeakageError
from ml.longitudinal import panel
from ml.longitudinal.panel import (
    TS_FEATURE_NAMES,
    assert_panel_no_leakage,
    build_panel,
    week_of_day,
)
from ml.tests.conftest import make_tables


def _row(frame: pd.DataFrame, student: int, week: int) -> pd.Series:
    match = frame[(frame["student_id"] == str(student)) & (frame["week"] == week)]
    assert len(match) == 1
    return match.iloc[0]


def test_week_of_day() -> None:
    assert week_of_day(np.array([-5, 0, 1, 7, 8, 14, 15])).tolist() == [0, 0, 1, 1, 2, 2, 3]


def test_activity_features_by_hand() -> None:
    # Student 1: 10 clicks every day in weeks 1-3, nothing in week 4. Student 2: active only in week 4.
    vle = [(1, d, 10) for d in range(1, 22)] + [(2, d, 5) for d in range(22, 29)]
    frame = build_panel(make_tables(vle=vle), weeks=[4], score_release_lag_days=14)
    s1 = _row(frame, 1, 4)
    assert s1["clicks_this_week"] == 0
    assert s1["active_days_this_week"] == 0
    assert s1["clicks_roll3w_mean"] == pytest.approx(140 / 3, rel=1e-6)
    assert s1["clicks_roll6w_mean"] == pytest.approx(210 / 4, rel=1e-6)
    assert s1["inactive_week_streak"] == 1
    assert s1["inactive_weeks_last_6w"] == 1
    assert s1["clicks_recent_vs_own_mean"] == pytest.approx(math.log1p(140 / 3) - math.log1p(70), rel=1e-5)
    assert s1["clicks_slope_6w"] == pytest.approx(math.log1p(70) * -1.5 / 5, rel=1e-5)
    # Weeks 2-3 match the running mean (statistic stays 0); week 4 drops to 0: z = log(71)/0.5, minus 0.5.
    assert s1["cusum_drop_stat"] == pytest.approx(math.log1p(70) / 0.5 - 0.5, rel=1e-5)
    assert s1["weeks_since_change_point"] == 0
    s2 = _row(frame, 2, 4)
    assert s2["clicks_this_week"] == 35
    assert s2["active_days_this_week"] == 7
    assert s2["inactive_week_streak"] == 0
    assert s2["cusum_drop_stat"] == 0
    assert np.isnan(s2["weeks_since_change_point"])


def test_assessment_features_by_hand() -> None:
    # Due days: assessment 1 = 20, 2 = 50, 3 = 90. Release lag 14 days.
    submissions = [
        (1, 1, 18.0, 80.0, 0),  # on time, released by day 32
        (2, 1, 55.0, 60.0, 0),  # 5 days late, released only on day 69
        (1, 2, 25.0, 40.0, 0),  # 5 days late, released by day 39
    ]
    frame = build_panel(make_tables(submissions=submissions), weeks=[8], score_release_lag_days=14)
    s1, s2 = _row(frame, 1, 8), _row(frame, 2, 8)
    assert s1["on_time_ratio_to_date"] == 0.5
    assert s2["on_time_ratio_to_date"] == 0.0
    assert s1["missed_due_last_4w"] == 0
    assert s2["missed_due_last_4w"] == 1  # assessment 2 (due day 50) not submitted
    assert s1["delay_change_recent"] == pytest.approx(5 - (-2))
    assert np.isnan(s2["delay_change_recent"])  # no submission in the last 4 weeks
    # Cohort mean for assessment 1 among released results = (80 + 40) / 2.
    assert s1["difficulty_adjusted_score"] == pytest.approx(20.0)
    assert s2["difficulty_adjusted_score"] == pytest.approx(-20.0)
    assert s1["score_rolling2_mean"] == pytest.approx(80.0)  # the day-55 score is not released yet
    assert np.isnan(s1["score_drop_from_best"]) and np.isnan(s1["score_volatility"])


def test_horizon_labels_and_unknown_withdrawal_time() -> None:
    tables = make_tables(
        registrations=[(1, -10.0, None), (3, -10.0, 40.0), (4, -10.0, None)],
        results={1: "Pass", 3: "Withdrawn", 4: "Withdrawn"},
    )
    frame = build_panel(tables, weeks=[4], score_release_lag_days=14)
    s3, s4, s1 = _row(frame, 3, 4), _row(frame, 4, 4), _row(frame, 1, 4)
    assert (s3["y_withdraw_1w"], s3["y_withdraw_4w"], s3["y_withdraw_8w"]) == (0.0, 1.0, 1.0)
    assert s3["withdraw_week"] == 6 and s3["y_academic"] == 1
    assert np.isnan(s4["y_withdraw_4w"]) and s4["y_academic"] == 1  # withdrawn, week unknown
    assert (s1["y_withdraw_4w"], s1["y_academic"]) == (0.0, 0.0)
    assert s1["course_end_week"] == math.ceil(200 / 7)
    # After withdrawing on day 40, student 3 is no longer in the panel.
    later = build_panel(tables, weeks=[6], score_release_lag_days=14)
    assert "3" not in set(later["student_id"])


def test_panel_on_synthetic_data_and_leakage_guard(synthetic_dir: Path) -> None:
    tables = load_oulad(synthetic_dir)
    frame = build_panel(tables, weeks=[2, 6, 12], score_release_lag_days=14)
    assert set(TS_FEATURE_NAMES) <= set(frame.columns)
    assert not frame.duplicated(["context_id", "student_id", "week"]).any()
    assert frame.groupby("week").size().is_monotonic_decreasing  # withdrawals leave the panel
    for week in (2, 6, 12):
        assert assert_panel_no_leakage(tables, week, score_release_lag_days=14) > 0


def test_leakage_guard_catches_a_future_feature(synthetic_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = panel.activity_feature_arrays

    def leaky(m: panel.WeeklyMatrices) -> dict[str, np.ndarray]:
        out = original(m)
        out["clicks_this_week"][:, :-1] = out["clicks_this_week"][:, 1:]  # reads the NEXT week
        return out

    monkeypatch.setattr(panel, "activity_feature_arrays", leaky)
    with pytest.raises(TemporalLeakageError, match="clicks_this_week"):
        assert_panel_no_leakage(load_oulad(synthetic_dir), 6, score_release_lag_days=14)
