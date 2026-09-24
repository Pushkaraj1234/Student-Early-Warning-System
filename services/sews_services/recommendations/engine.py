"""Transparent, rule-based intervention recommendations (V3). Rules version ``rules-1.0.0``.

Inputs: the latest prediction (level, trajectory, factors), institutional as-of features, the
student's most recent check-in (only what the student explicitly reported), and existing
interventions. Output: zero or more recommendations (type, reason, priority, rule id).

Guarantees (tested in services/tests/test_recommendation_engine.py):
  * Every output needs HUMAN REVIEW: it is stored with status 'recommended' and is invisible to the
    student until a mentor approves it (enforced by the database).
  * Missing data is never treated as bad data: a rule whose inputs are missing does not fire.
  * Financial-support referral fires ONLY when the student explicitly reported financial difficulty.
  * Wellbeing referral and academic counselling are never recommended automatically; nothing is
    inferred about mental health from academic activity.
  * No duplicates: one recommendation per type; types already open, declined in the last 30 days
    or completed in the last 14 days are skipped (declines are respected).
  * Conflicting signals lower the priority and say so in the reason instead of being hidden.
Thresholds (e.g. 75% attendance, the common UGC attendance requirement; 40% as a pass mark) are
provisional defaults that each institution must confirm; they are listed in RULES below.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, get_args

InterventionType = Literal[
    "mentor_meeting",
    "academic_counselling",
    "attendance_follow_up",
    "assignment_support",
    "peer_tutoring",
    "wellbeing_referral",
    "study_planning",
    "academic_tutoring",
    "financial_support_referral",
]
ALL_TYPES: frozenset[str] = frozenset(get_args(InterventionType))
NEVER_AUTOMATIC: frozenset[str] = frozenset({"wellbeing_referral", "academic_counselling"})
Priority = Literal["low", "medium", "high"]
PRIORITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
Trajectory = Literal["insufficient_history", "improving", "stable", "increasing", "rapidly_increasing"]
RULES_VERSION = "rules-1.0.0"
RULE_ID_RE = re.compile(r"^[a-z0-9_.-]{1,64}$")

ATTENDANCE_REQUIRED = 0.75
ATTENDANCE_SEVERE = 0.60
MISSED_SUBMISSIONS = 0.30
MISSED_SUBMISSIONS_SEVERE = 0.50
MIN_ASSESSMENTS_DUE = 2
PASS_MARK_PCT = 40.0
FALLING_SCORE_PER_30D = -10.0
INACTIVE_DAYS = 14
DECLINE_RESPECT_DAYS = 30
COMPLETED_COOLDOWN_DAYS = 14

RULES: dict[str, str] = {
    "attendance.below_requirement": f"attendance in the last 14 days < {ATTENDANCE_REQUIRED:.0%} "
    f"(high if < {ATTENDANCE_SEVERE:.0%} or >= 3 consecutive absences) -> attendance_follow_up",
    "assignments.missed": f"share of due assignments not submitted >= {MISSED_SUBMISSIONS:.0%} with >= "
    f"{MIN_ASSESSMENTS_DUE} due (high if >= {MISSED_SUBMISSIONS_SEVERE:.0%}) -> assignment_support",
    "grades.below_pass": f"mean released score < {PASS_MARK_PCT:.0f}% -> academic_tutoring (high)",
    "grades.falling": f"score trend <= {FALLING_SCORE_PER_30D:.0f} points per 30 days -> academic_tutoring (medium)",
    "engagement.inactive": f"no learning-platform activity for >= {INACTIVE_DAYS} days after earlier "
    "activity this term -> study_planning (medium)",
    "risk.high_or_rising": "academic risk level high, or elevated and rapidly increasing -> mentor_meeting",
    "checkin.contact_requested": "student asked to be contacted in a check-in -> mentor_meeting (medium)",
    "checkin.financial_difficulty": "student reported financial difficulty -> financial_support_referral (medium)",
    "checkin.academic_difficulty": "student reported academic or course difficulty -> academic_tutoring (low)",
    "checkin.study_skills": "student reported workload, time-management or study challenges -> study_planning (low)",
}


class InvalidRecommendationError(ValueError):
    """A recommendation violates the output contract (a bug; never stored)."""


@dataclass(frozen=True)
class PredictionSignal:
    prediction_id: str
    target: str
    risk_level: Literal["stable", "watch", "elevated", "high"]
    trajectory: Trajectory


@dataclass(frozen=True)
class StudentContext:
    prediction: PredictionSignal | None = None
    features: Mapping[str, float | None] = field(default_factory=dict)
    checkin_needs: frozenset[str] = frozenset()
    wants_contact: bool = False
    open_types: frozenset[str] = frozenset()
    declined_recently: frozenset[str] = frozenset()
    completed_recently: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Recommendation:
    intervention_type: InterventionType
    reason: str
    priority: Priority
    rule_id: str
    prediction_id: str | None = None
    requires_human_review: bool = True


def validate(rec: Recommendation) -> Recommendation:
    if rec.intervention_type not in ALL_TYPES:
        raise InvalidRecommendationError("unknown intervention type")
    if rec.intervention_type in NEVER_AUTOMATIC:
        raise InvalidRecommendationError("this intervention type is never recommended automatically")
    if rec.priority not in PRIORITY_RANK:
        raise InvalidRecommendationError("invalid priority")
    if not 3 <= len(rec.reason.strip()) <= 500:
        raise InvalidRecommendationError("reason must be 3-500 characters")
    if not RULE_ID_RE.fullmatch(rec.rule_id) or rec.rule_id not in RULES:
        raise InvalidRecommendationError("unknown rule id")
    if not rec.requires_human_review:
        raise InvalidRecommendationError("automatic recommendations always require human review")
    return rec


def _value(features: Mapping[str, float | None], key: str) -> float | None:
    v = features.get(key)
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def _lower(priority: Priority) -> Priority:
    return "low" if priority in ("low", "medium") else "medium"


def _feature_rules(f: Mapping[str, float | None]) -> list[Recommendation]:
    out: list[Recommendation] = []
    att = _value(f, "attendance_rate_last_14d")
    if att is not None and att < ATTENDANCE_REQUIRED:
        absences = _value(f, "consecutive_absences") or 0.0
        severe = att < ATTENDANCE_SEVERE or absences >= 3
        out.append(
            Recommendation(
                "attendance_follow_up",
                f"Attendance in the last 14 days was {att:.0%}, below the {ATTENDANCE_REQUIRED:.0%} requirement.",
                "high" if severe else "medium",
                "attendance.below_requirement",
            )
        )
    missed, due = _value(f, "missed_submission_rate"), _value(f, "assessments_due_to_date")
    if missed is not None and due is not None and due >= MIN_ASSESSMENTS_DUE and missed >= MISSED_SUBMISSIONS:
        out.append(
            Recommendation(
                "assignment_support",
                f"{missed:.0%} of the {int(due)} assignments due so far this semester have not been submitted.",
                "high" if missed >= MISSED_SUBMISSIONS_SEVERE else "medium",
                "assignments.missed",
            )
        )
    mean_score, trend = _value(f, "mean_released_score_pct"), _value(f, "score_trend_per_30d")
    if mean_score is not None and mean_score < PASS_MARK_PCT:
        out.append(
            Recommendation(
                "academic_tutoring",
                f"The average released score this semester is {mean_score:.0f}%, below {PASS_MARK_PCT:.0f}%.",
                "high",
                "grades.below_pass",
            )
        )
    elif trend is not None and trend <= FALLING_SCORE_PER_30D:
        out.append(
            Recommendation(
                "academic_tutoring",
                f"Released scores have fallen by about {abs(trend):.0f} points per month this semester.",
                "medium",
                "grades.falling",
            )
        )
    # days_since_last_engagement is defined only if there was activity earlier this term; a student
    # with no activity at all may simply be in a course that does not use the LMS - not evidence.
    idle = _value(f, "days_since_last_engagement")
    if idle is not None and idle >= INACTIVE_DAYS:
        out.append(
            Recommendation(
                "study_planning",
                f"No learning-platform activity for {int(idle)} days after earlier activity this semester.",
                "medium",
                "engagement.inactive",
            )
        )
    return out


def _conflict(f: Mapping[str, float | None]) -> bool:
    """Observed signals look fine while the model estimate is high."""
    att = _value(f, "attendance_rate_last_14d")
    missed = _value(f, "missed_submission_rate")
    score = _value(f, "mean_released_score_pct")
    known = [v for v in (att, missed, score) if v is not None]
    return (
        len(known) >= 2
        and (att is None or att >= 0.90)
        and (missed is None or missed == 0.0)
        and (score is None or score >= 60.0)
    )


def recommend(ctx: StudentContext) -> list[Recommendation]:
    candidates = _feature_rules(ctx.features)

    p = ctx.prediction
    if p is not None and p.target == "academic":
        high = p.risk_level == "high"
        rising = p.risk_level == "elevated" and p.trajectory == "rapidly_increasing"
        if high or rising:
            priority: Priority = "high" if high else "medium"
            reason = (
                "The academic early-warning estimate is high."
                if high
                else "The academic early-warning estimate is elevated and rising quickly."
            )
            if p.trajectory == "improving":
                priority = _lower(priority)
                reason += " It is currently improving."
            if _conflict(ctx.features):
                priority = _lower(priority)
                reason += " Attendance, submissions and scores look fine, so signals are mixed: review first."
            candidates.append(
                Recommendation("mentor_meeting", reason, priority, "risk.high_or_rising", p.prediction_id)
            )

    if ctx.wants_contact:
        candidates.append(
            Recommendation(
                "mentor_meeting",
                "The student asked to be contacted in a check-in.",
                "medium",
                "checkin.contact_requested",
            )
        )
    needs = ctx.checkin_needs
    if "financial_difficulty" in needs:
        candidates.append(
            Recommendation(
                "financial_support_referral",
                "The student reported financial difficulty in a check-in.",
                "medium",
                "checkin.financial_difficulty",
            )
        )
    if needs & {"academic_difficulty", "course_difficulty"}:
        candidates.append(
            Recommendation(
                "academic_tutoring",
                "The student reported academic or course difficulty in a check-in.",
                "low",
                "checkin.academic_difficulty",
            )
        )
    if needs & {"workload", "time_management", "study_challenges"}:
        candidates.append(
            Recommendation(
                "study_planning",
                "The student reported workload, time-management or study challenges in a check-in.",
                "low",
                "checkin.study_skills",
            )
        )

    # one per type: keep the highest priority; mention the other reasons
    merged: dict[str, Recommendation] = {}
    for rec in candidates:
        current = merged.get(rec.intervention_type)
        if current is None:
            merged[rec.intervention_type] = rec
            continue
        best, other = (
            (rec, current) if PRIORITY_RANK[rec.priority] > PRIORITY_RANK[current.priority] else (current, rec)
        )
        reason = f"{best.reason} Also: {other.reason}"
        merged[rec.intervention_type] = Recommendation(
            best.intervention_type,
            reason[:500],
            best.priority,
            best.rule_id,
            best.prediction_id or other.prediction_id,
        )

    skip = ctx.open_types | ctx.declined_recently | ctx.completed_recently
    result = [validate(r) for t, r in merged.items() if t not in skip]
    return sorted(result, key=lambda r: (-PRIORITY_RANK[r.priority], r.intervention_type))
