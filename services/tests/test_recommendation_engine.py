"""Rule engine: invalid recommendations, missing context, conflicting signals, duplicates, and the
explicit-only / never-automatic rules. Pure unit tests (no database)."""

from __future__ import annotations

import math
from typing import Any

import pytest
from sews_services.recommendations.engine import (
    RULES,
    InvalidRecommendationError,
    PredictionSignal,
    Recommendation,
    StudentContext,
    recommend,
    validate,
)

HIGH = PredictionSignal("p-1", "academic", "high", "stable")


def _types(ctx: StudentContext) -> list[str]:
    return [r.intervention_type for r in recommend(ctx)]


# ---------------------------------------------------------------- invalid recommendations
@pytest.mark.parametrize(
    "rec",
    [
        Recommendation("not_a_type", "A valid reason.", "medium", "attendance.below_requirement"),  # type: ignore[arg-type]
        Recommendation("wellbeing_referral", "A valid reason.", "medium", "attendance.below_requirement"),
        Recommendation("academic_counselling", "A valid reason.", "medium", "attendance.below_requirement"),
        Recommendation("study_planning", "A valid reason.", "urgent", "engagement.inactive"),  # type: ignore[arg-type]
        Recommendation("study_planning", "  ", "medium", "engagement.inactive"),
        Recommendation("study_planning", "x" * 501, "medium", "engagement.inactive"),
        Recommendation("study_planning", "A valid reason.", "medium", "Not A Rule"),
        Recommendation("study_planning", "A valid reason.", "medium", "made.up.rule"),
        Recommendation(
            "study_planning", "A valid reason.", "medium", "engagement.inactive", requires_human_review=False
        ),
    ],
)
def test_invalid_recommendations_are_rejected(rec: Recommendation) -> None:
    with pytest.raises(InvalidRecommendationError):
        validate(rec)


def test_every_output_is_valid_and_needs_review() -> None:
    ctx = StudentContext(
        prediction=PredictionSignal("p-2", "academic", "elevated", "rapidly_increasing"),
        features={
            "attendance_rate_last_14d": 0.5,
            "consecutive_absences": 4,
            "missed_submission_rate": 0.6,
            "assessments_due_to_date": 5,
            "mean_score_pct": None,
            "mean_released_score_pct": 35.0,
            "days_since_last_engagement": 20,
        },
        checkin_needs=frozenset({"financial_difficulty", "workload", "academic_difficulty"}),
        wants_contact=True,
    )
    recs = recommend(ctx)
    assert recs, "expected recommendations"
    for r in recs:
        assert validate(r) is r and r.requires_human_review
        assert r.rule_id in RULES
    assert len({r.intervention_type for r in recs}) == len(recs)  # one per type


# ---------------------------------------------------------------- missing context
def test_no_context_means_no_recommendations() -> None:
    assert recommend(StudentContext()) == []


@pytest.mark.parametrize("missing", [None, math.nan])
def test_missing_values_are_not_treated_as_bad(missing: float | None) -> None:
    features = {
        "attendance_rate_last_14d": missing,
        "missed_submission_rate": missing,
        "assessments_due_to_date": missing,
        "mean_released_score_pct": missing,
        "score_trend_per_30d": missing,
        "days_since_last_engagement": missing,
    }
    assert recommend(StudentContext(features=features)) == []


def test_no_lms_activity_at_all_is_not_evidence() -> None:
    # days_since_last_engagement is undefined when there was never any activity this term
    ctx = StudentContext(features={"engagement_events_last_30d": 0.0, "days_since_last_engagement": None})
    assert recommend(ctx) == []


def test_single_assessment_due_is_not_enough() -> None:
    ctx = StudentContext(features={"missed_submission_rate": 1.0, "assessments_due_to_date": 1})
    assert recommend(ctx) == []


def test_prediction_without_features_still_reaches_a_mentor() -> None:
    assert _types(StudentContext(prediction=HIGH)) == ["mentor_meeting"]


def test_non_academic_targets_do_not_trigger_the_risk_rule() -> None:
    ctx = StudentContext(prediction=PredictionSignal("p-3", "engagement", "high", "stable"))
    assert recommend(ctx) == []


# ---------------------------------------------------------------- conflicting signals
def test_conflicting_signals_lower_priority_and_say_so() -> None:
    fine = {"attendance_rate_last_14d": 0.95, "missed_submission_rate": 0.0, "mean_released_score_pct": 82.0}
    (rec,) = recommend(StudentContext(prediction=HIGH, features=fine))
    assert rec.intervention_type == "mentor_meeting"
    assert rec.priority == "medium"
    assert "signals are mixed" in rec.reason


def test_improving_trajectory_lowers_priority() -> None:
    (rec,) = recommend(StudentContext(prediction=PredictionSignal("p-4", "academic", "high", "improving")))
    assert rec.priority == "medium" and "improving" in rec.reason


def test_student_request_overrides_a_low_estimate() -> None:
    ctx = StudentContext(prediction=PredictionSignal("p-5", "academic", "stable", "stable"), wants_contact=True)
    (rec,) = recommend(ctx)
    assert rec.intervention_type == "mentor_meeting" and rec.rule_id == "checkin.contact_requested"


# ---------------------------------------------------------------- duplicates
def test_same_type_from_several_rules_is_merged_keeping_highest_priority() -> None:
    ctx = StudentContext(prediction=HIGH, wants_contact=True)
    (rec,) = recommend(ctx)
    assert rec.priority == "high" and rec.rule_id == "risk.high_or_rising"
    assert "asked to be contacted" in rec.reason
    assert rec.prediction_id == "p-1"


@pytest.mark.parametrize("field", ["open_types", "declined_recently", "completed_recently"])
def test_existing_open_declined_or_recent_interventions_are_not_repeated(field: str) -> None:
    existing: dict[str, Any] = {field: frozenset({"attendance_follow_up"})}
    ctx = StudentContext(features={"attendance_rate_last_14d": 0.5}, **existing)
    assert recommend(ctx) == []


# ---------------------------------------------------------------- explicit-only / never automatic
def test_financial_referral_requires_an_explicit_report() -> None:
    worst = {
        "attendance_rate_last_14d": 0.1,
        "missed_submission_rate": 1.0,
        "assessments_due_to_date": 6,
        "mean_released_score_pct": 5.0,
        "days_since_last_engagement": 40,
    }
    assert "financial_support_referral" not in _types(StudentContext(prediction=HIGH, features=worst))
    assert "financial_support_referral" in _types(StudentContext(checkin_needs=frozenset({"financial_difficulty"})))


def test_no_signal_ever_produces_wellbeing_or_counselling() -> None:
    every_need = frozenset(
        {
            "academic_difficulty",
            "workload",
            "time_management",
            "course_difficulty",
            "financial_difficulty",
            "study_challenges",
        }
    )
    worst = {"attendance_rate_last_14d": 0.0, "consecutive_absences": 20, "days_since_last_engagement": 60}
    types = _types(StudentContext(prediction=HIGH, features=worst, checkin_needs=every_need, wants_contact=True))
    assert "wellbeing_referral" not in types and "academic_counselling" not in types


def test_attendance_thresholds() -> None:
    def priority(rate: float, absences: float = 0) -> str | None:
        recs = recommend(StudentContext(features={"attendance_rate_last_14d": rate, "consecutive_absences": absences}))
        return recs[0].priority if recs else None

    assert priority(0.80) is None
    assert priority(0.70) == "medium"
    assert priority(0.55) == "high"
    assert priority(0.70, absences=3) == "high"


def test_reasons_do_not_contain_identifiers_or_diagnoses() -> None:
    ctx = StudentContext(
        prediction=HIGH,
        features={
            "attendance_rate_last_14d": 0.5,
            "missed_submission_rate": 0.5,
            "assessments_due_to_date": 4,
        },
        checkin_needs=frozenset({"financial_difficulty", "workload"}),
    )
    text = " ".join(r.reason for r in recommend(ctx)).lower()
    for word in ("depress", "anxiety", "mental", "stress", "@", "roll"):
        assert word not in text
