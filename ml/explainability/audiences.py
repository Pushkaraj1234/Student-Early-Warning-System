"""Audience-specific explanations of one prediction (V3).

student  Non-stigmatising and supportive. No probability, no risk label, no model jargon and no
         feature values. At most three THEMES the student can act on, taken only from factors that
         raised the estimate. Prior-history factors (previous attempts, credits, registration timing,
         carried-over results, previous GPA) are never shown to students because the student cannot
         act on them. Always says the estimate is automated, not a judgement, and points to the mentor.
mentor   Technical. Probability, risk level, target, model version, and every returned factor with its
         label, value, SHAP contribution, direction and units, plus caveats (associations, not causes;
         data provenance; human review).
admin    Governance. Lineage (model, feature and dataset versions, provenance, calibration decision,
         explanation units), whether the provenance allows live use, and factor keys only (no values).

No explanation mentions protected attributes (they are never model inputs) or mental health, and no
text claims a cause.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from ml.inference.schemas import PredictionResponse
from ml.models.artifact import ModelMetadata

Audience = Literal["student", "mentor", "admin"]
StudentTheme = Literal[
    "attendance", "learning_activity", "assessments", "results", "practice_quizzes", "discussion"
]

THEME_TEXT: dict[StudentTheme, tuple[str, str]] = {
    "attendance": (
        "Class attendance",
        "Attending regularly makes it easier to keep up. If something is making it hard to attend, "
        "your mentor can help.",
    ),
    "learning_activity": (
        "Regular time on the course site",
        "Short, regular sessions with the course materials can make it easier to keep up.",
    ),
    "assessments": (
        "Assignment submissions",
        "Planning around upcoming deadlines, or asking your mentor for help with a study plan, can make "
        "submissions easier.",
    ),
    "results": (
        "Recent assessment results",
        "Going through your feedback, or asking about tutoring, can help with the next assessment.",
    ),
    "practice_quizzes": (
        "Practice quizzes",
        "Practice quizzes are a low-pressure way to check your understanding.",
    ),
    "discussion": (
        "Course discussions",
        "Course forums are a good place to ask questions and learn from others.",
    ),
}

STUDENT_HEADLINES = {
    "on_track": "You're keeping up well. Keep going.",
    "attention": "A few areas could use some attention. Support is available, and your mentor can help "
    "you plan next steps.",
}
STUDENT_NOTE = (
    "This is an automated estimate based on your course activity. It is not a judgement about you or "
    "your abilities, and it changes as you keep going."
)
MAX_STUDENT_THEMES = 3

# feature key -> (mentor label, student theme or None = never shown to students)
FEATURE_TEXT: dict[str, tuple[str, StudentTheme | None]] = {
    # institutional feature set (docs/ml/data-dictionary.md)
    "attendance_rate_to_date": ("Attendance rate this term", "attendance"),
    "attendance_rate_last_14d": ("Attendance rate, last 14 days", "attendance"),
    "attendance_trend": ("Change in weekly attendance", "attendance"),
    "consecutive_absences": ("Consecutive absences", "attendance"),
    "missed_submission_rate": ("Share of assignments not submitted", "assessments"),
    "mean_released_score_pct": ("Mean released score (%)", "results"),
    "weighted_score_to_date": ("Weighted score to date", "results"),
    "engagement_active_days_14d": ("Active learning days, last 14 days", "learning_activity"),
    "engagement_trend": ("Change in learning activity", "learning_activity"),
    "prior_term_gpa": ("Previous semester GPA", None),
    "prior_attempts": ("Previous attempts at this course", None),
    # institutional feature set inst-fs-1.0.0 (services/sews_services/features/institutional.py)
    "attendance_rate_last_7d": ("Attendance rate, last 7 days", "attendance"),
    "attendance_rate_last_30d": ("Attendance rate, last 30 days", "attendance"),
    "last_released_score_pct": ("Most recent released score (%)", "results"),
    "engagement_events_last_7d": ("Learning-platform events, last 7 days", "learning_activity"),
    "engagement_events_last_14d": ("Learning-platform events, last 14 days", "learning_activity"),
    "engagement_events_last_30d": ("Learning-platform events, last 30 days", "learning_activity"),
    "quiz_attempts_last_30d": ("Quiz attempts, last 30 days", "practice_quizzes"),
    "days_since_last_engagement": ("Days since last learning-platform activity", "learning_activity"),
    # benchmark (OULAD) feature sets v1 + v2
    "clicks_to_date": ("VLE clicks to date", "learning_activity"),
    "active_days_to_date": ("Active VLE days to date", "learning_activity"),
    "clicks_last_7d": ("VLE clicks, last 7 days", "learning_activity"),
    "clicks_last_14d": ("VLE clicks, last 14 days", "learning_activity"),
    "clicks_last_30d": ("VLE clicks, last 30 days", "learning_activity"),
    "clicks_trend_7d": ("Change in daily clicks (7-day windows)", "learning_activity"),
    "clicks_trend_14d": ("Change in daily clicks (14-day windows)", "learning_activity"),
    "clicks_trend_30d": ("Change in daily clicks (30-day windows)", "learning_activity"),
    "clicks_change_from_baseline": ("Recent daily clicks vs own baseline", "learning_activity"),
    "days_since_last_activity": ("Days since last VLE activity", "learning_activity"),
    "active_days_last_14d": ("Active VLE days, last 14 days", "learning_activity"),
    "content_clicks_last_14d": ("Course-content clicks, last 14 days", "learning_activity"),
    "content_trend_14d": ("Change in course-content clicks (14-day windows)", "learning_activity"),
    "clicks_last_7d_vs_30d_rate": ("Daily clicks, last 7 days vs last 30 days", "learning_activity"),
    "quiz_clicks_to_date": ("Quiz activity to date", "practice_quizzes"),
    "quiz_clicks_last_7d": ("Quiz activity, last 7 days", "practice_quizzes"),
    "quiz_clicks_last_14d": ("Quiz activity, last 14 days", "practice_quizzes"),
    "quiz_clicks_last_30d": ("Quiz activity, last 30 days", "practice_quizzes"),
    "quiz_trend_14d": ("Change in quiz activity (14-day windows)", "practice_quizzes"),
    "forum_clicks_to_date": ("Forum/collaboration activity to date", "discussion"),
    "forum_clicks_last_14d": ("Forum/collaboration activity, last 14 days", "discussion"),
    "forum_trend_14d": ("Change in forum activity (14-day windows)", "discussion"),
    "assessments_due_to_date": ("Assessments due to date", None),
    "assignment_completion_rate": ("Share of due assessments submitted", "assessments"),
    "late_submission_rate": ("Share of submissions made late", "assessments"),
    "mean_submission_delay_days": ("Mean submission delay (days; negative = early)", "assessments"),
    "submissions_last_30d": ("Submissions, last 30 days", "assessments"),
    "completion_rate_last_30d": ("Share of assessments due in last 30 days submitted", "assessments"),
    "mean_score_to_date": ("Mean released score to date", "results"),
    "last_score": ("Most recent released score", "results"),
    "course_relative_score": ("Mean score relative to course cohort", "results"),
    "score_trend_per_30d": ("Score trend (points per 30 days)", "results"),
    "score_change_from_first": ("Latest minus first released score", "results"),
    "num_of_prev_attempts": ("Previous attempts at this module", None),
    "studied_credits": ("Credits being studied", None),
    "registration_lead_days": ("Days registered before the start", None),
    "banked_assessment_count": ("Results carried over from an earlier attempt", None),
}


def mentor_label(feature: str) -> str:
    """Unknown keys are shown as-is rather than guessed."""
    return FEATURE_TEXT.get(feature, (feature, None))[0]


def student_theme(feature: str) -> StudentTheme | None:
    return FEATURE_TEXT.get(feature, (feature, None))[1]


@dataclass(frozen=True)
class StudentFocusArea:
    title: str
    suggestion: str


@dataclass(frozen=True)
class StudentExplanation:
    audience: Literal["student"]
    headline: str
    focus_areas: tuple[StudentFocusArea, ...]
    note: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MentorFactor:
    rank: int
    feature: str
    label: str
    value: float | None
    contribution: float
    direction: Literal["increases_risk", "decreases_risk"]


@dataclass(frozen=True)
class MentorExplanation:
    audience: Literal["mentor"]
    target: str
    target_definition: str
    model_version: str
    risk_probability: float
    risk_level: str
    explanation_units: str
    factors: tuple[MentorFactor, ...]
    caveats: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdminExplanation:
    audience: Literal["admin"]
    model_version: str
    model_name: str
    target: str
    feature_version: str
    dataset_name: str
    dataset_version: str
    data_provenance: str
    training_timestamp: str
    calibration_method: str
    calibration_reason: str
    explanation_units: str
    factor_features: tuple[str, ...]
    provenance_permits_live_use: bool
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_same_model(response: PredictionResponse, metadata: ModelMetadata) -> None:
    if response.model_version != metadata.model_version:
        raise ValueError("prediction and model metadata refer to different model versions")


def for_student(response: PredictionResponse, metadata: ModelMetadata) -> StudentExplanation:
    _check_same_model(response, metadata)
    if response.risk_level == "stable":
        return StudentExplanation("student", STUDENT_HEADLINES["on_track"], (), STUDENT_NOTE)
    themes: list[StudentTheme] = []
    for factor in sorted(response.top_factors, key=lambda f: f.rank):
        theme = student_theme(factor.feature)
        if factor.direction == "increases_risk" and theme is not None and theme not in themes:
            themes.append(theme)
        if len(themes) == MAX_STUDENT_THEMES:
            break
    areas = tuple(StudentFocusArea(*THEME_TEXT[t]) for t in themes)
    return StudentExplanation("student", STUDENT_HEADLINES["attention"], areas, STUDENT_NOTE)


def for_mentor(response: PredictionResponse, metadata: ModelMetadata) -> MentorExplanation:
    _check_same_model(response, metadata)
    caveats = [
        "Contributions show how the model used each input for this prediction. They are associations, "
        "not causes.",
        f"Contribution units: {metadata.explanation_units}.",
        "Review the student's situation before acting; the estimate does not decide any action.",
    ]
    if metadata.data_provenance != "institutional":
        caveats.append(
            f"This model was trained on {metadata.data_provenance} data ({metadata.dataset_name}); it is not "
            "validated for this institution and must not drive decisions on its own."
        )
    if metadata.calibration_method == "none":
        caveats.append(
            "Probabilities are uncalibrated (calibration did not improve reliability out of time)."
        )
    factors = tuple(
        MentorFactor(
            rank=f.rank,
            feature=f.feature,
            label=mentor_label(f.feature),
            value=f.feature_value,
            contribution=f.contribution,
            direction=f.direction,
        )
        for f in sorted(response.top_factors, key=lambda f: f.rank)
    )
    return MentorExplanation(
        audience="mentor",
        target=metadata.target,
        target_definition=metadata.target_definition,
        model_version=metadata.model_version,
        risk_probability=response.risk_probability,
        risk_level=response.risk_level,
        explanation_units=metadata.explanation_units,
        factors=factors,
        caveats=tuple(caveats),
    )


def for_admin(response: PredictionResponse, metadata: ModelMetadata) -> AdminExplanation:
    _check_same_model(response, metadata)
    reason = str(metadata.calibration_decision.get("reason", "no calibration decision recorded"))
    return AdminExplanation(
        audience="admin",
        model_version=metadata.model_version,
        model_name=metadata.model_name,
        target=metadata.target,
        feature_version=metadata.feature_version,
        dataset_name=metadata.dataset_name,
        dataset_version=metadata.dataset_version,
        data_provenance=metadata.data_provenance,
        training_timestamp=metadata.training_timestamp.isoformat(),
        calibration_method=metadata.calibration_method,
        calibration_reason=reason,
        explanation_units=metadata.explanation_units,
        factor_features=tuple(f.feature for f in sorted(response.top_factors, key=lambda f: f.rank)),
        provenance_permits_live_use=metadata.data_provenance == "institutional",
        notes=(
            "Live predictions additionally require status 'production' in public.model_registry "
            "(enforced by the database).",
            "Protected attributes are not model inputs; subgroup differences are in the evaluation report.",
        ),
    )


def explain(
    audience: Audience, response: PredictionResponse, metadata: ModelMetadata
) -> StudentExplanation | MentorExplanation | AdminExplanation:
    if audience == "student":
        return for_student(response, metadata)
    if audience == "mentor":
        return for_mentor(response, metadata)
    if audience == "admin":
        return for_admin(response, metadata)
    raise ValueError(f"unknown audience: {audience}")
