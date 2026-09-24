"""Feature set definition (versioned).

Every feature is computed AS OF the prediction cutoff using only records dated on or before
it (see ml.features.oulad_features). Changing any definition requires a new FEATURE_VERSION.

Attendance is intentionally absent: OULAD contains no attendance records, and the pipeline
never fabricates them. VLE engagement is a different signal and is not a substitute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FEATURE_VERSION_V1 = "oulad-fs-1.0.0"
FEATURE_VERSION_V2 = "oulad-fs-2.0.0"
# Default feature set for new training runs.
FEATURE_VERSION = FEATURE_VERSION_V2

FeatureFamily = Literal["engagement", "quiz", "assignment", "academic", "prior"]


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    family: FeatureFamily
    description: str


FEATURES_V1: tuple[FeatureSpec, ...] = (
    # --- engagement (VLE activity) ---------------------------------------------------------
    FeatureSpec("clicks_to_date", "engagement", "Total VLE clicks from registration up to the cutoff."),
    FeatureSpec("active_days_to_date", "engagement", "Distinct days with any VLE activity up to the cutoff."),
    FeatureSpec("clicks_last_7d", "engagement", "VLE clicks in the 7 days ending at the cutoff."),
    FeatureSpec("clicks_last_14d", "engagement", "VLE clicks in the 14 days ending at the cutoff."),
    FeatureSpec("clicks_last_30d", "engagement", "VLE clicks in the 30 days ending at the cutoff."),
    FeatureSpec(
        "clicks_trend_7d",
        "engagement",
        "(clicks in last 7 days - clicks in the 7 days before) / 7: change in daily clicks.",
    ),
    FeatureSpec(
        "clicks_trend_14d", "engagement", "(clicks in last 14 days - clicks in the 14 days before) / 14."
    ),
    FeatureSpec(
        "clicks_trend_30d", "engagement", "(clicks in last 30 days - clicks in the 30 days before) / 30."
    ),
    FeatureSpec(
        "clicks_change_from_baseline",
        "engagement",
        "Mean daily clicks in the last 14 days minus the student's own mean daily clicks from "
        "day 0 to 14 days before the cutoff. Missing if that baseline is shorter than 7 days.",
    ),
    FeatureSpec(
        "days_since_last_activity",
        "engagement",
        "Days between the last VLE activity and the cutoff. Missing if never active.",
    ),
    # --- assignments -----------------------------------------------------------------------
    FeatureSpec(
        "assessments_due_to_date",
        "assignment",
        "Non-exam assessments of the presentation due on or before the cutoff.",
    ),
    FeatureSpec(
        "assignment_completion_rate",
        "assignment",
        "Share of due assessments submitted by the cutoff. Missing if none due yet.",
    ),
    FeatureSpec(
        "late_submission_rate",
        "assignment",
        "Share of submissions made by the cutoff that were after the due date. Missing if none.",
    ),
    FeatureSpec(
        "mean_submission_delay_days",
        "assignment",
        "Mean (submission day - due day) of submissions made by the cutoff; negative = early.",
    ),
    # --- academic performance -------------------------------------------------------------
    FeatureSpec(
        "mean_score_to_date",
        "academic",
        "Mean score (0-100) of results available by the cutoff (submission + assumed release lag).",
    ),
    FeatureSpec("last_score", "academic", "Most recent score available by the cutoff."),
    FeatureSpec(
        "course_relative_score",
        "academic",
        "mean_score_to_date minus the mean of the same measure over the student's cohort.",
    ),
    # --- prior record & registration (known at registration) -------------------------------
    FeatureSpec("num_of_prev_attempts", "prior", "Previous attempts at this module."),
    FeatureSpec("studied_credits", "prior", "Credits the student is studying in total."),
    FeatureSpec("registration_lead_days", "prior", "Days between registration and the presentation start."),
    FeatureSpec(
        "banked_assessment_count", "prior", "Assessment results carried over from a previous attempt."
    ),
)

# V2 adds windows and trends for quiz / forum / content activity, recent assignment behaviour and
# grade trends. "Current semester" = presentation start to cutoff (the *_to_date features).
FEATURES_V2_EXTRA: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        "active_days_last_14d", "engagement", "Distinct active days in the 14 days ending at the cutoff."
    ),
    FeatureSpec(
        "quiz_clicks_to_date", "quiz", "Quiz activity (quiz, externalquiz) from registration to the cutoff."
    ),
    FeatureSpec("quiz_clicks_last_7d", "quiz", "Quiz activity in the last 7 days."),
    FeatureSpec("quiz_clicks_last_14d", "quiz", "Quiz activity in the last 14 days."),
    FeatureSpec("quiz_clicks_last_30d", "quiz", "Quiz activity in the last 30 days."),
    FeatureSpec("quiz_trend_14d", "quiz", "(quiz clicks last 14 days - the 14 days before) / 14."),
    FeatureSpec("forum_clicks_to_date", "engagement", "Forum/collaboration activity to the cutoff."),
    FeatureSpec("forum_clicks_last_14d", "engagement", "Forum/collaboration activity in the last 14 days."),
    FeatureSpec("forum_trend_14d", "engagement", "(forum clicks last 14 days - the 14 days before) / 14."),
    FeatureSpec("content_clicks_last_14d", "engagement", "Content/resource activity in the last 14 days."),
    FeatureSpec(
        "content_trend_14d", "engagement", "(content clicks last 14 days - the 14 days before) / 14."
    ),
    FeatureSpec(
        "submissions_last_30d", "assignment", "Own submissions made in the 30 days ending at the cutoff."
    ),
    FeatureSpec(
        "completion_rate_last_30d",
        "assignment",
        "Share of assessments due in the last 30 days that were submitted by the cutoff.",
    ),
    FeatureSpec(
        "score_trend_per_30d",
        "academic",
        "Least-squares slope of released scores against submission day, per 30 days (>= 2 scores).",
    ),
    FeatureSpec(
        "score_change_from_first", "academic", "Latest released score minus the first (>= 2 scores)."
    ),
    FeatureSpec(
        "clicks_last_7d_vs_30d_rate",
        "engagement",
        "Mean daily clicks in the last 7 days minus mean daily clicks in the last 30 days.",
    ),
)
FEATURES_V2: tuple[FeatureSpec, ...] = FEATURES_V1 + FEATURES_V2_EXTRA

FEATURE_SETS: dict[str, tuple[FeatureSpec, ...]] = {
    FEATURE_VERSION_V1: FEATURES_V1,
    FEATURE_VERSION_V2: FEATURES_V2,
}


def feature_names(version: str) -> tuple[str, ...]:
    if version not in FEATURE_SETS:
        raise ValueError(f"unknown feature version: {version}")
    return tuple(spec.name for spec in FEATURE_SETS[version])


FEATURES = FEATURES_V2
FEATURE_NAMES: tuple[str, ...] = feature_names(FEATURE_VERSION)

TREND_WINDOWS_DAYS: tuple[int, ...] = (7, 14, 30)
BASELINE_RECENT_DAYS = 14
BASELINE_MIN_DAYS = 7
