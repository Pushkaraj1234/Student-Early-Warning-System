"""Temporal-leakage and definition tests for the as-of feature builder (hand-built data)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from ml.data.contract import validate_feature_table
from ml.features.definitions import FEATURE_NAMES
from ml.features.oulad_features import build_oulad_features
from ml.tests.conftest import make_tables

LAG = 14


def _row(df: pd.DataFrame, student: int) -> pd.Series:
    rows = df[df["student_id"] == str(student)]
    assert len(rows) == 1
    return rows.iloc[0]


def _features(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[:, list(FEATURE_NAMES)].reset_index(drop=True)


BASE_VLE = [(1, 40, 4), (1, 55, 10)]
BASE_SUBMISSIONS = [
    (1, 1, 18.0, 80.0, 0),  # due 20, early, score released by day 32
    (2, 1, 52.0, 60.0, 0),  # due 50, 2 days late, score released day 66
    (3, 1, 55.0, 90.0, 0),  # due 90, submitted early
]


def test_engagement_windows_trends_and_baseline() -> None:
    df = build_oulad_features(make_tables(vle=BASE_VLE), 60, score_release_lag_days=LAG)
    r = _row(df, 1)
    assert r["clicks_to_date"] == 14
    assert r["active_days_to_date"] == 2
    assert r["clicks_last_7d"] == 10
    assert r["clicks_last_14d"] == 10
    assert r["clicks_last_30d"] == 14
    assert r["clicks_trend_7d"] == pytest.approx(10 / 7)
    assert r["clicks_trend_14d"] == pytest.approx((10 - 4) / 14)
    assert r["clicks_trend_30d"] == pytest.approx(14 / 30)
    assert r["clicks_change_from_baseline"] == pytest.approx(10 / 14 - 4 / 47)
    assert r["days_since_last_activity"] == 5


def test_inactive_student_has_zero_clicks_and_missing_recency() -> None:
    df = build_oulad_features(make_tables(vle=BASE_VLE), 60, score_release_lag_days=LAG)
    r = _row(df, 2)
    assert r["clicks_to_date"] == 0
    assert r["clicks_trend_7d"] == 0
    assert math.isnan(r["days_since_last_activity"])


def test_assignment_and_score_features() -> None:
    df = build_oulad_features(make_tables(submissions=BASE_SUBMISSIONS), 60, score_release_lag_days=LAG)
    r = _row(df, 1)
    assert r["assessments_due_to_date"] == 2
    assert r["assignment_completion_rate"] == 1.0
    assert r["late_submission_rate"] == pytest.approx(1 / 3)
    assert r["mean_submission_delay_days"] == pytest.approx((-2 + 2 - 35) / 3)
    assert r["mean_score_to_date"] == 80.0  # the day-52 score is not released until day 66
    assert r["last_score"] == 80.0
    assert r["course_relative_score"] == 0.0
    r2 = _row(df, 2)
    assert r2["assignment_completion_rate"] == 0.0
    assert math.isnan(r2["late_submission_rate"])
    assert math.isnan(r2["mean_score_to_date"])
    assert math.isnan(r2["course_relative_score"])


def test_scores_become_available_only_after_release_lag() -> None:
    tables = make_tables(submissions=BASE_SUBMISSIONS)
    assert _row(build_oulad_features(tables, 65, score_release_lag_days=LAG), 1)["mean_score_to_date"] == 80
    assert _row(build_oulad_features(tables, 66, score_release_lag_days=LAG), 1)["mean_score_to_date"] == 70


def test_future_vle_activity_does_not_change_features() -> None:
    before = build_oulad_features(make_tables(vle=BASE_VLE), 60, score_release_lag_days=LAG)
    future = [*BASE_VLE, (1, 61, 100), (1, 120, 500), (2, 61, 7)]
    after = build_oulad_features(make_tables(vle=future), 60, score_release_lag_days=LAG)
    pd.testing.assert_frame_equal(_features(before), _features(after))


def test_future_submissions_and_scores_do_not_change_features() -> None:
    before = build_oulad_features(make_tables(submissions=BASE_SUBMISSIONS), 60, score_release_lag_days=LAG)
    future = [*BASE_SUBMISSIONS, (2, 2, 61.0, 100.0, 0), (3, 2, 95.0, 100.0, 0)]
    after = build_oulad_features(make_tables(submissions=future), 60, score_release_lag_days=LAG)
    pd.testing.assert_frame_equal(_features(before), _features(after))


def test_final_outcome_only_affects_the_target() -> None:
    passed = build_oulad_features(
        make_tables(vle=BASE_VLE, results={1: "Pass", 2: "Pass"}), 60, score_release_lag_days=LAG
    )
    failed = build_oulad_features(
        make_tables(vle=BASE_VLE, results={1: "Fail", 2: "Pass"}), 60, score_release_lag_days=LAG
    )
    pd.testing.assert_frame_equal(_features(passed), _features(failed))
    assert _row(passed, 1)["target"] == 0
    assert _row(failed, 1)["target"] == 1


def test_later_unregistration_does_not_change_features() -> None:
    regs_none = [(1, -10.0, None), (2, -5.0, None)]
    regs_late = [(1, -10.0, 100.0), (2, -5.0, None)]
    a = build_oulad_features(
        make_tables(vle=BASE_VLE, registrations=regs_none), 60, score_release_lag_days=LAG
    )
    b = build_oulad_features(
        make_tables(vle=BASE_VLE, registrations=regs_late, results={1: "Withdrawn", 2: "Pass"}),
        60,
        score_release_lag_days=LAG,
    )
    pd.testing.assert_frame_equal(_features(a), _features(b))
    assert _row(b, 1)["target"] == 1


def test_population_excludes_students_withdrawn_or_not_yet_registered() -> None:
    regs = [(1, -10.0, None), (2, -5.0, 30.0), (3, 70.0, None)]
    results = {1: "Pass", 2: "Withdrawn", 3: "Pass"}
    tables = make_tables(registrations=regs, results=results)
    at_20 = build_oulad_features(tables, 20, score_release_lag_days=LAG)
    at_60 = build_oulad_features(tables, 60, score_release_lag_days=LAG)
    at_80 = build_oulad_features(tables, 80, score_release_lag_days=LAG)
    assert set(at_20["student_id"]) == {"1", "2"}
    assert set(at_60["student_id"]) == {"1"}
    assert set(at_80["student_id"]) == {"1", "3"}


def test_banked_results_are_prior_record_only() -> None:
    subs = [(1, 2, -10.0, 70.0, 1)]
    r = _row(build_oulad_features(make_tables(submissions=subs), 60, score_release_lag_days=LAG), 2)
    assert r["banked_assessment_count"] == 1
    assert r["assignment_completion_rate"] == 0.0
    assert math.isnan(r["mean_score_to_date"])


def test_output_satisfies_contract_and_uses_nominal_date() -> None:
    df = build_oulad_features(
        make_tables(vle=BASE_VLE, submissions=BASE_SUBMISSIONS), 60, score_release_lag_days=LAG
    )
    validate_feature_table(df, FEATURE_NAMES)
    assert (df["prediction_date"] == pd.Timestamp("2014-11-30")).all()  # 2014-10-01 + 60 days
    assert (df["cutoff_day"] == 60).all()


def test_no_outcome_or_demographic_columns_are_features() -> None:
    forbidden = {
        "final_result",
        "date_unregistration",
        "gender",
        "region",
        "highest_education",
        "imd_band",
        "age_band",
        "disability",
        "target",
    }
    assert not forbidden & set(FEATURE_NAMES)
    assert not any(name.startswith("audit_") for name in FEATURE_NAMES)


@pytest.mark.parametrize(("cutoff", "lag"), [(0, 14), (30, -1)])
def test_invalid_arguments_are_rejected(cutoff: int, lag: int) -> None:
    with pytest.raises(ValueError):
        build_oulad_features(make_tables(), cutoff, score_release_lag_days=lag)
