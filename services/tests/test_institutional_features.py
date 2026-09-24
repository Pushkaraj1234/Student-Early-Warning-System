"""Institutional as-of features: hand-computed values, as-of rules and the leakage guard.
All rows are SYNTHETIC and built in memory."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
import sews_services.features.institutional as inst
from sews_services.features.institutional import (
    ACADEMIC_COLUMNS,
    ASSESSMENT_COLUMNS,
    ATTENDANCE_COLUMNS,
    ENGAGEMENT_COLUMNS,
    FEATURES,
    InstitutionalData,
    TemporalLeakageError,
    assert_no_future_leakage,
    build_features,
    truncate_at,
)

IST = ZoneInfo("Asia/Kolkata")
TERM_START = date(2026, 7, 20)
T = datetime(2026, 9, 24, 12, 0, tzinfo=IST)


def ist(y: int, m: int, d: int, h: int = 10) -> datetime:
    return datetime(y, m, d, h, 0, tzinfo=IST)


def utc(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, 30, tzinfo=UTC)


def _data() -> InstitutionalData:
    att = [
        ("s1", date(2026, 9, 1), 1, "present", ist(2026, 9, 1, 18)),
        ("s1", date(2026, 9, 10), 1, "excused", ist(2026, 9, 10, 18)),
        ("s1", date(2026, 9, 15), 1, "absent", ist(2026, 9, 15, 18)),
        ("s1", date(2026, 9, 20), 1, "late", ist(2026, 9, 20, 18)),
        ("s1", date(2026, 9, 22), 1, "absent", ist(2026, 9, 22, 18)),
        ("s1", date(2026, 9, 23), 1, "absent", ist(2026, 9, 23, 18)),
        ("s1", date(2026, 9, 24), 1, "absent", ist(2026, 9, 25, 9)),  # recorded after t
        ("s1", date(2026, 9, 26), 1, "present", ist(2026, 9, 26, 18)),  # future session
    ]
    nat = pd.NaT
    ass = [
        ("s1", "a1", utc(2026, 8, 10), 20.0, utc(2026, 8, 9), 15.0, utc(2026, 8, 12), nat),
        ("s1", "a2", utc(2026, 9, 1), 20.0, utc(2026, 9, 3), 10.0, utc(2026, 9, 26), nat),  # graded after t
        ("s1", "a3", utc(2026, 9, 20), 20.0, nat, math.nan, nat, nat),
        ("s1", "a4", utc(2026, 9, 22), 20.0, utc(2026, 9, 25), math.nan, nat, nat),  # submitted after t
        ("s1", "a5", utc(2026, 10, 1), 20.0, nat, math.nan, nat, nat),  # not yet due
        ("s1", "a6", utc(2026, 7, 1), 20.0, nat, math.nan, nat, nat),  # previous term
    ]
    eng = [
        ("s1", "resource_view", 3, ist(2026, 9, 23), ist(2026, 9, 23, 11)),
        ("s1", "quiz_attempt", 2, ist(2026, 9, 20), ist(2026, 9, 20, 11)),
        ("s1", "lms_login", 1, ist(2026, 9, 1), ist(2026, 9, 1, 11)),
        ("s1", "forum_activity", 1, ist(2026, 8, 1), ist(2026, 8, 1, 11)),
        ("s1", "resource_view", 1, ist(2026, 9, 24, 11), ist(2026, 9, 24, 11)),
        ("s1", "resource_view", 5, ist(2026, 9, 24, 13), ist(2026, 9, 24, 13)),  # after t
        ("s1", "resource_view", 7, ist(2026, 9, 22), ist(2026, 9, 25, 9)),  # recorded after t
    ]
    aca = [
        ("s1", 7.5, "pass", utc(2026, 6, 1)),
        ("s1", 8.0, "pass", utc(2026, 10, 1)),  # published after t
        ("s1", None, "pending", utc(2026, 7, 1)),
    ]
    return InstitutionalData(
        student_ids=("s1", "s2"),
        term_start=TERM_START,
        attendance=pd.DataFrame(att, columns=ATTENDANCE_COLUMNS),
        assessments=pd.DataFrame(ass, columns=ASSESSMENT_COLUMNS),
        engagement=pd.DataFrame(eng, columns=ENGAGEMENT_COLUMNS),
        academic=pd.DataFrame(aca, columns=ACADEMIC_COLUMNS),
    )


@pytest.fixture
def features() -> pd.DataFrame:
    frame: pd.DataFrame = build_features(_data(), T, IST)
    return frame


def test_attendance_features_by_hand(features: pd.DataFrame) -> None:
    s1 = features.loc["s1"]
    assert s1["attendance_rate_to_date"] == pytest.approx(2 / 5)  # P, A, L, A, A (excused/late-recorded/future out)
    assert s1["attendance_rate_last_7d"] == pytest.approx(1 / 3)
    assert s1["attendance_rate_last_14d"] == pytest.approx(1 / 4)
    assert s1["attendance_rate_last_30d"] == pytest.approx(2 / 5)
    assert s1["consecutive_absences"] == 2
    expected = np.polyfit([6, 8, 9], [1.0, 0.5, 0.0], 1)[0]
    assert s1["attendance_trend"] == pytest.approx(expected)


def test_assessment_features_by_hand(features: pd.DataFrame) -> None:
    s1 = features.loc["s1"]
    assert s1["assessments_due_to_date"] == 4
    assert s1["missed_submission_rate"] == pytest.approx(0.5)  # a3 never, a4 only after t
    assert s1["late_submission_rate"] == pytest.approx(0.5)  # a2 late of {a1, a2}
    assert s1["submissions_last_30d"] == 1
    assert s1["mean_released_score_pct"] == pytest.approx(75.0)  # a2's grade is released after t
    assert s1["last_released_score_pct"] == pytest.approx(75.0)
    assert pd.isna(features.loc["s1", "score_trend_per_30d"])  # one released score


def test_engagement_features_by_hand(features: pd.DataFrame) -> None:
    s1 = features.loc["s1"]
    assert s1["engagement_events_last_7d"] == 6
    assert s1["engagement_events_last_14d"] == 6
    assert s1["engagement_events_last_30d"] == 7
    assert s1["engagement_active_days_14d"] == 3
    assert s1["quiz_attempts_last_30d"] == 2
    assert s1["days_since_last_engagement"] == pytest.approx(1 / 24)
    weekly = [0, 1, 0, 0, 0, 0, 1, 0, 2]  # 9 complete weeks; the current partial week is excluded
    assert s1["engagement_trend"] == pytest.approx(np.polyfit(range(9), weekly, 1)[0])


def test_prior_gpa_uses_only_published_results(features: pd.DataFrame) -> None:
    assert features.loc["s1", "prior_term_gpa"] == 7.5


def test_student_without_data_is_missing_not_zero(features: pd.DataFrame) -> None:
    s2 = features.loc["s2"]
    for name in (
        "attendance_rate_to_date",
        "consecutive_absences",
        "missed_submission_rate",
        "mean_released_score_pct",
        "days_since_last_engagement",
        "prior_term_gpa",
    ):
        assert pd.isna(features.loc["s2", name]), name
    assert s2["engagement_events_last_30d"] == 0  # event counts are genuinely zero


def test_output_has_exactly_the_versioned_features(features: pd.DataFrame) -> None:
    assert tuple(features.columns) == FEATURES
    assert list(features.index) == ["s1", "s2"]


def test_features_do_not_change_when_future_rows_are_removed() -> None:
    data = _data()
    pd.testing.assert_frame_equal(build_features(data, T, IST), build_features(truncate_at(data, T, IST), T, IST))
    assert_no_future_leakage(data, T, IST)


def test_leakage_guard_detects_a_builder_that_stops_filtering(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inst, "_as_of_view", lambda data, t, tz: data)
    with pytest.raises(TemporalLeakageError, match="attendance_rate_to_date"):
        assert_no_future_leakage(_data(), T, IST)


def test_naive_timestamp_is_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_features(_data(), datetime(2026, 9, 24, 12, 0), IST)
