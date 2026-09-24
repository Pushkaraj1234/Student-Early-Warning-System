"""V2 temporal features, V3 targets and the runtime leakage guard (synthetic data)."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from ml.data.oulad import load_oulad, truncate_at
from ml.features.definitions import FEATURE_VERSION_V1, FEATURE_VERSION_V2, feature_names
from ml.features.leakage import TemporalLeakageError, assert_no_future_leakage
from ml.features.oulad_features import build_oulad_features
from ml.tests.conftest import make_tables

LAG = 14


def _row(df: pd.DataFrame, student: int) -> pd.Series:
    return df[df["student_id"] == str(student)].iloc[0]


VLE = [(1, 40, 4), (1, 55, 10), (1, 70, 5)]
SUBS = [(1, 1, 18.0, 80.0, 0), (2, 1, 52.0, 60.0, 0), (3, 1, 55.0, 90.0, 0)]


def test_v2_windows_and_trends_by_hand() -> None:
    r = _row(build_oulad_features(make_tables(vle=VLE, submissions=SUBS), 60, score_release_lag_days=LAG), 1)
    assert r["active_days_last_14d"] == 1
    assert r["content_clicks_last_14d"] == 10
    assert r["content_trend_14d"] == pytest.approx((10 - 4) / 14)
    assert r["submissions_last_30d"] == 2  # days 52 and 55
    assert r["completion_rate_last_30d"] == 1.0  # assessment 2 (due 50) submitted
    assert r["clicks_last_7d_vs_30d_rate"] == pytest.approx(10 / 7 - 14 / 30)
    assert math.isnan(r["score_trend_per_30d"])  # only one score released by day 60


def test_grade_trend_uses_only_released_scores() -> None:
    tables = make_tables(submissions=SUBS)
    at_66 = _row(build_oulad_features(tables, 66, score_release_lag_days=LAG), 1)
    # released: day 18 (80), day 52 (60) → slope -20 over 34 days → per 30 days
    assert at_66["score_trend_per_30d"] == pytest.approx(-20 / 34 * 30)
    assert at_66["score_change_from_first"] == -20
    at_70 = _row(build_oulad_features(tables, 70, score_release_lag_days=LAG), 1)
    assert at_70["score_change_from_first"] == 10  # day-55 score (90) released on day 69


def test_v1_feature_set_is_still_available() -> None:
    df = build_oulad_features(
        make_tables(vle=VLE), 60, score_release_lag_days=LAG, feature_version=FEATURE_VERSION_V1
    )
    assert set(feature_names(FEATURE_VERSION_V1)) <= set(df.columns)
    assert "quiz_clicks_to_date" not in df.columns


def test_quiz_and_forum_activity_are_separated(synthetic_dir: Path) -> None:
    df = build_oulad_features(load_oulad(synthetic_dir), 60, score_release_lag_days=LAG)
    assert (df["quiz_clicks_to_date"] + df["forum_clicks_to_date"] <= df["clicks_to_date"] + 1e-9).all()


@pytest.mark.parametrize(
    ("target", "results", "expected"),
    [
        ("academic", {1: "Fail", 2: "Withdrawn"}, [1, 1]),
        ("dropout", {1: "Fail", 2: "Withdrawn"}, [0, 1]),
        ("course_failure", {1: "Fail", 2: "Withdrawn"}, [1, 0]),
    ],
)
def test_outcome_targets(target: str, results: dict[int, str], expected: list[int]) -> None:
    regs = [(1, -10.0, None), (2, -5.0, 100.0)]
    df = build_oulad_features(
        make_tables(registrations=regs, results=results), 60, score_release_lag_days=LAG, target=target
    )
    assert df.sort_values("student_id")["target"].tolist() == expected


def test_engagement_target_uses_the_next_14_days_only() -> None:
    df = build_oulad_features(
        make_tables(vle=[(1, 70, 5), (2, 80, 5)]), 60, score_release_lag_days=LAG, target="engagement"
    )
    assert df.sort_values("student_id")["target"].tolist() == [0, 1]  # day 80 is beyond 60 + 14


def test_features_do_not_depend_on_the_target() -> None:
    tables = make_tables(vle=VLE, submissions=SUBS)
    a = build_oulad_features(tables, 60, score_release_lag_days=LAG, target="academic")
    b = build_oulad_features(tables, 60, score_release_lag_days=LAG, target="engagement")
    names = list(feature_names(FEATURE_VERSION_V2))
    pd.testing.assert_frame_equal(a[names], b[names])


def test_truncation_removes_only_future_information() -> None:
    tables = make_tables(vle=VLE, submissions=SUBS, registrations=[(1, -10.0, 100.0), (2, -5.0, None)])
    cut = truncate_at(tables, 60)
    assert cut.student_vle_daily["date"].max() <= 60
    assert cut.student_assessment["date_submitted"].max() <= 60
    assert cut.registration["date_unregistration"].isna().all()


def test_leakage_guard_passes_for_the_real_feature_builder(synthetic_dir: Path) -> None:
    check = assert_no_future_leakage(
        load_oulad(synthetic_dir), 60, score_release_lag_days=LAG, feature_version=FEATURE_VERSION_V2
    )
    assert check.rows_compared > 0
    assert check.features_compared == len(feature_names(FEATURE_VERSION_V2))


def test_leakage_guard_detects_a_leaky_feature(synthetic_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_builder = build_oulad_features

    def leaky_builder(tables, cutoff_day, **kwargs):  # type: ignore[no-untyped-def]
        df = real_builder(tables, cutoff_day, **kwargs)
        total = tables.student_vle_daily.groupby("id_student")["sum_click"].sum()  # ALL days: leaks
        df["clicks_to_date"] = df["student_id"].astype(int).map(total).fillna(0).astype(float)
        return df

    monkeypatch.setattr("ml.features.leakage.build_oulad_features", leaky_builder)
    with pytest.raises(TemporalLeakageError, match="clicks_to_date"):
        assert_no_future_leakage(
            load_oulad(synthetic_dir), 60, score_release_lag_days=LAG, feature_version=FEATURE_VERSION_V2
        )
