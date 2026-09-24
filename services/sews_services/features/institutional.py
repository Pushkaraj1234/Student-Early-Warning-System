"""Institutional as-of feature set ``inst-fs-1.0.0`` (docs/ml/data-dictionary.md, "Institutional").

Every feature is computed AS OF a timestamp ``t`` using only information that existed at ``t``:
  attendance   attendance_date <= t (local date) AND recorded_at <= t
  assessments  due_at <= t for "due"; submitted_at <= t for submissions; graded_at <= t for scores
               (a grade released after t is excluded even if the work was submitted earlier)
  engagement   occurred_at <= t AND recorded_at <= t
  prior GPA    published_at <= t
"Current semester" = the academic_terms row containing t (from local midnight of its first day).
Windows are 7/14/30 days ending at t and are also clipped to the current semester.

Not computed (no source in the current schema; never fabricated): assessment weights
(weighted_score_to_date) and attempt numbers (prior_attempts).

Identity data never enters the feature table: rows are keyed by student id only for joining, and
the scoring job replaces that key with the ML subject id before anything is stored or scored.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from sews_services.db import Connection

FEATURE_VERSION = "inst-fs-1.0.0"
FEATURES: tuple[str, ...] = (
    "attendance_rate_to_date",
    "attendance_rate_last_7d",
    "attendance_rate_last_14d",
    "attendance_rate_last_30d",
    "attendance_trend",
    "consecutive_absences",
    "assessments_due_to_date",
    "missed_submission_rate",
    "late_submission_rate",
    "submissions_last_30d",
    "mean_released_score_pct",
    "last_released_score_pct",
    "score_trend_per_30d",
    "engagement_events_last_7d",
    "engagement_events_last_14d",
    "engagement_events_last_30d",
    "engagement_active_days_14d",
    "engagement_trend",
    "quiz_attempts_last_30d",
    "days_since_last_engagement",
    "prior_term_gpa",
)
DEFAULT_TZ = ZoneInfo("Asia/Kolkata")
MIN_TREND_WEEKS = 3


class TemporalLeakageError(RuntimeError):
    """A feature changed after removing information from after ``t``."""


class NoActiveTermError(LookupError):
    """No (or more than one) academic term contains the scoring date."""


@dataclass(frozen=True)
class InstitutionalData:
    student_ids: tuple[str, ...]
    term_start: date
    attendance: pd.DataFrame  # student_id, attendance_date, session_number, status, recorded_at
    assessments: (
        pd.DataFrame
    )  # student_id, assignment_id, due_at, max_score, submitted_at, score, graded_at, excused_at
    engagement: pd.DataFrame  # student_id, event_type, event_count, occurred_at, recorded_at
    academic: pd.DataFrame  # student_id, sgpa, result_status, published_at


ATTENDANCE_COLUMNS = ["student_id", "attendance_date", "session_number", "status", "recorded_at"]
ASSESSMENT_COLUMNS = [
    "student_id",
    "assignment_id",
    "due_at",
    "max_score",
    "submitted_at",
    "score",
    "graded_at",
    "excused_at",
]
ENGAGEMENT_COLUMNS = ["student_id", "event_type", "event_count", "occurred_at", "recorded_at"]
ACADEMIC_COLUMNS = ["student_id", "sgpa", "result_status", "published_at"]


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2 or np.ptp(x) == 0:
        return float("nan")
    return float(np.polyfit(x.astype(float), y.astype(float), 1)[0])


def _local_date(ts: pd.Series, tz: ZoneInfo) -> pd.Series:
    return pd.to_datetime(ts, utc=True).dt.tz_convert(tz).dt.date


def term_start_timestamp(term_start: date, tz: ZoneInfo = DEFAULT_TZ) -> pd.Timestamp:
    """Local midnight of the first term day, in UTC."""
    return pd.Timestamp(datetime.combine(term_start, datetime.min.time()), tz=tz).tz_convert("UTC")


def truncate_at(data: InstitutionalData, t: datetime, tz: ZoneInfo = DEFAULT_TZ) -> InstitutionalData:
    """Remove every piece of information that did not exist at ``t`` (used by the leakage guard)."""
    day = t.astimezone(tz).date()
    att = data.attendance
    att = att[(att["attendance_date"] <= day) & (pd.to_datetime(att["recorded_at"], utc=True) <= t)]
    ass = data.assessments.copy()
    for col, extra in (("submitted_at", []), ("graded_at", ["score"]), ("excused_at", [])):
        late = pd.to_datetime(ass[col], utc=True) > t
        for c in (col, *extra):
            ass[c] = ass[c].where(~late)
    eng = data.engagement
    eng = eng[(pd.to_datetime(eng["occurred_at"], utc=True) <= t) & (pd.to_datetime(eng["recorded_at"], utc=True) <= t)]
    aca = data.academic
    aca = aca[pd.to_datetime(aca["published_at"], utc=True) <= t]
    return replace(data, attendance=att, assessments=ass, engagement=eng, academic=aca)


# The builder's own as-of view. The leakage guard deliberately calls ``truncate_at`` directly, so a
# builder that stopped filtering (e.g. this alias replaced by an identity function) is detected.
_as_of_view = truncate_at


def build_features(data: InstitutionalData, t: datetime, tz: ZoneInfo = DEFAULT_TZ) -> pd.DataFrame:
    """One row per student id (index), columns = FEATURES; NaN where a feature is undefined."""
    if t.tzinfo is None:
        raise ValueError("t must be timezone-aware")
    data = _as_of_view(data, t, tz)  # the builder itself only ever sees information available at t
    day = t.astimezone(tz).date()
    out = pd.DataFrame(index=pd.Index(data.student_ids, name="student_id"), columns=list(FEATURES), dtype=float)

    # ---------------------------------------------------------------- attendance
    att = data.attendance[data.attendance["attendance_date"] >= data.term_start].copy()
    att = att[att["status"] != "excused"]
    att["attended"] = att["status"].isin(["present", "late"]).astype(float)
    for sid, g in att.groupby("student_id"):
        if sid not in out.index:
            continue
        out.loc[sid, "attendance_rate_to_date"] = g["attended"].mean()
        for n in (7, 14, 30):
            w = g[g["attendance_date"] > day - timedelta(days=n)]
            out.loc[sid, f"attendance_rate_last_{n}d"] = w["attended"].mean() if len(w) else np.nan
        weeks = g.assign(week=[(d - data.term_start).days // 7 for d in g["attendance_date"]])
        weekly = weeks.groupby("week")["attended"].mean()
        if len(weekly) >= MIN_TREND_WEEKS:
            out.loc[sid, "attendance_trend"] = _slope(weekly.index.to_numpy(), weekly.to_numpy())
        ordered = g.sort_values(["attendance_date", "session_number"])["status"].tolist()
        run = 0
        for status in reversed(ordered):
            if status != "absent":
                break
            run += 1
        out.loc[sid, "consecutive_absences"] = run

    # --------------------------------------------------------------- assessments
    ass = data.assessments.copy()
    for col in ("due_at", "submitted_at", "graded_at", "excused_at"):
        ass[col] = pd.to_datetime(ass[col], utc=True)
    term_start_ts = term_start_timestamp(data.term_start, tz)
    ass = ass[ass["due_at"] >= term_start_ts]
    due = ass[(ass["due_at"] <= t) & ass["excused_at"].isna()]
    for sid, g in due.groupby("student_id"):
        if sid in out.index:
            out.loc[sid, "assessments_due_to_date"] = len(g)
            out.loc[sid, "missed_submission_rate"] = float(g["submitted_at"].isna().mean())
    subs = ass[ass["submitted_at"].notna()]
    for sid, g in subs.groupby("student_id"):
        if sid in out.index:
            out.loc[sid, "late_submission_rate"] = float((g["submitted_at"] > g["due_at"]).mean())
            out.loc[sid, "submissions_last_30d"] = int((g["submitted_at"] > t - timedelta(days=30)).sum())
    enrolled_with_work = out.index.isin(ass["student_id"].unique())
    out.loc[enrolled_with_work & out["assessments_due_to_date"].isna(), "assessments_due_to_date"] = 0
    out.loc[enrolled_with_work & out["submissions_last_30d"].isna(), "submissions_last_30d"] = 0
    released = ass[ass["graded_at"].notna() & ass["score"].notna()].copy()
    released["pct"] = released["score"].astype(float) / released["max_score"].astype(float) * 100.0
    for sid, g in released.groupby("student_id"):
        if sid not in out.index:
            continue
        g = g.sort_values("graded_at")
        out.loc[sid, "mean_released_score_pct"] = g["pct"].mean()
        out.loc[sid, "last_released_score_pct"] = g["pct"].iloc[-1]
        days = ((g["graded_at"] - g["graded_at"].iloc[0]).dt.total_seconds() / 86_400).to_numpy()
        out.loc[sid, "score_trend_per_30d"] = _slope(days, g["pct"].to_numpy()) * 30

    # ---------------------------------------------------------------- engagement
    eng = data.engagement.copy()
    eng["occurred_at"] = pd.to_datetime(eng["occurred_at"], utc=True)
    eng = eng[eng["occurred_at"] >= term_start_ts]
    complete_weeks = ((day - data.term_start).days + 1) // 7
    for n in (7, 14, 30):
        out[f"engagement_events_last_{n}d"] = 0.0
    out["quiz_attempts_last_30d"] = 0.0
    out["engagement_active_days_14d"] = 0.0
    for sid, g in eng.groupby("student_id"):
        if sid not in out.index:
            continue
        for n in (7, 14, 30):
            out.loc[sid, f"engagement_events_last_{n}d"] = g.loc[
                g["occurred_at"] > t - timedelta(days=n), "event_count"
            ].sum()
        recent = g[g["occurred_at"] > t - timedelta(days=14)]
        out.loc[sid, "engagement_active_days_14d"] = len(set(_local_date(recent["occurred_at"], tz)))
        quiz = g[(g["event_type"] == "quiz_attempt") & (g["occurred_at"] > t - timedelta(days=30))]
        out.loc[sid, "quiz_attempts_last_30d"] = quiz["event_count"].sum()
        out.loc[sid, "days_since_last_engagement"] = (t - g["occurred_at"].max()).total_seconds() / 86_400
    if complete_weeks >= MIN_TREND_WEEKS:
        event_weeks = np.array(
            [(d - data.term_start).days // 7 for d in _local_date(eng["occurred_at"], tz)], dtype=int
        )
        in_complete = eng.assign(week=event_weeks)
        in_complete = in_complete[in_complete["week"] < complete_weeks]
        weekly_events = in_complete.pivot_table(
            index="student_id", columns="week", values="event_count", aggfunc="sum", fill_value=0
        ).reindex(index=out.index, columns=range(complete_weeks), fill_value=0)
        x = np.arange(complete_weeks)
        out["engagement_trend"] = [_slope(x, row) for row in weekly_events.to_numpy(dtype=float)]

    # -------------------------------------------------------------- prior GPA
    aca = data.academic[data.academic["result_status"].isin(["pass", "fail"]) & data.academic["sgpa"].notna()]
    aca = aca.assign(published_at=pd.to_datetime(aca["published_at"], utc=True))
    for sid, g in aca.groupby("student_id"):
        if sid in out.index:
            out.loc[sid, "prior_term_gpa"] = float(g.sort_values("published_at")["sgpa"].iloc[-1])

    return out.astype(float)


def assert_no_future_leakage(data: InstitutionalData, t: datetime, tz: ZoneInfo = DEFAULT_TZ) -> None:
    full = build_features(data, t, tz)
    cut = build_features(truncate_at(data, t, tz), t, tz)
    leaking = [c for c in FEATURES if not np.allclose(full[c].to_numpy(), cut[c].to_numpy(), atol=1e-9, equal_nan=True)]
    if leaking:
        raise TemporalLeakageError(f"features use information after {t.isoformat()}: {leaking}")


def load_institutional_data(
    conn: Connection, institution_id: str, t: datetime, tz: ZoneInfo = DEFAULT_TZ
) -> InstitutionalData:
    """Read what the features need, already restricted to information available at ``t``."""
    day = t.astimezone(tz).date()
    terms = conn.execute(
        "select starts_on from public.academic_terms where institution_id = %s and starts_on <= %s and ends_on >= %s",
        (institution_id, day, day),
    ).fetchall()
    if len(terms) != 1:
        raise NoActiveTermError("exactly one academic term must contain the scoring date")
    term_start: date = terms[0]["starts_on"]
    params = {
        "inst": institution_id,
        "t": t,
        "day": day,
        "term_start": term_start,
        "term_start_ts": term_start_timestamp(term_start, tz).to_pydatetime(),
    }
    students = tuple(
        r["id"]
        for r in conn.execute(
            "select id::text as id from public.students where institution_id = %(inst)s and status = 'active' "
            "order by id",
            params,
        ).fetchall()
    )

    def frame(sql: str, columns: list[str]) -> pd.DataFrame:
        return pd.DataFrame(conn.execute(sql, params).fetchall(), columns=columns)

    attendance = frame(
        """select ar.student_id::text as student_id, ar.attendance_date, ar.session_number, ar.status, ar.recorded_at
           from public.attendance_records ar join public.students s on s.id = ar.student_id
           where s.institution_id = %(inst)s and ar.attendance_date between %(term_start)s and %(day)s
             and ar.recorded_at <= %(t)s""",
        ATTENDANCE_COLUMNS,
    )
    assessments = frame(
        """select sc.student_id::text as student_id, a.id::text as assignment_id, a.due_at, a.max_score,
                  case when sub.submitted_at <= %(t)s then sub.submitted_at end as submitted_at,
                  case when sub.graded_at <= %(t)s then sub.score end as score,
                  case when sub.graded_at <= %(t)s then sub.graded_at end as graded_at,
                  case when sub.status = 'excused' and sub.updated_at <= %(t)s then sub.updated_at end as excused_at
           from public.student_courses sc
           join public.assignments a on a.course_id = sc.course_id and a.academic_year = sc.academic_year
           left join public.assignment_submissions sub on sub.assignment_id = a.id and sub.student_id = sc.student_id
           where sc.institution_id = %(inst)s and sc.status in ('enrolled', 'completed')
             and a.due_at >= %(term_start_ts)s""",
        ASSESSMENT_COLUMNS,
    )
    engagement = frame(
        """select e.student_id::text as student_id, e.event_type, e.event_count, e.occurred_at, e.recorded_at
           from public.engagement_events e join public.students s on s.id = e.student_id
           where s.institution_id = %(inst)s and e.occurred_at >= %(term_start_ts)s
             and e.occurred_at <= %(t)s and e.recorded_at <= %(t)s""",
        ENGAGEMENT_COLUMNS,
    )
    academic = frame(
        """select r.student_id::text as student_id, r.sgpa, r.result_status, r.published_at
           from public.academic_records r join public.students s on s.id = r.student_id
           where s.institution_id = %(inst)s and r.published_at <= %(t)s""",
        ACADEMIC_COLUMNS,
    )
    return InstitutionalData(students, term_start, attendance, assessments, engagement, academic)
