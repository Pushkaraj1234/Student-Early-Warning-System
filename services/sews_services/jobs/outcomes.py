"""Descriptive before/after indicators for interventions (method ``outcomes-1.0.0``).

For each COMPLETED intervention (anchor = completed_at) and each DECLINED intervention
(anchor = responded_at, kept as a descriptive comparison group):
    baseline window  = the 28 days before the offer (offered_at, or created_at if never offered)
    follow-up window = the 28 days after the anchor, computed only once that window has ended
Indicators: attendance_rate; assignment_completion_rate (assignments due in the window that were
submitted by the window's end); mean_score_pct (graded in the window); risk_probability (academic).
A value is NULL when the window has no data; it is never imputed.

These numbers are DESCRIPTIVE. Differences between the windows are not evidence that an
intervention caused them: there is no control group, students choose whether to accept, and
regression to the mean, term timing and other support all influence the follow-up window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sews_services.db import Connection
from sews_services.features.institutional import DEFAULT_TZ

METHOD_VERSION = "outcomes-1.0.0"
WINDOW_DAYS = 28

INDICATOR_SQL: dict[str, str] = {
    "attendance_rate": """
        select avg(case when status in ('present', 'late') then 1.0 else 0.0 end) as v
        from public.attendance_records
        where student_id = %(student)s and status <> 'excused'
          and attendance_date between %(start)s and %(end)s""",
    "assignment_completion_rate": """
        select avg(case when sub.submitted_at is not null
                             and (sub.submitted_at at time zone %(tz)s)::date <= %(end)s
                        then 1.0 else 0.0 end) as v
        from public.student_courses sc
        join public.assignments a on a.course_id = sc.course_id and a.academic_year = sc.academic_year
        left join public.assignment_submissions sub on sub.assignment_id = a.id and sub.student_id = sc.student_id
        where sc.student_id = %(student)s and coalesce(sub.status, '') <> 'excused'
          and (a.due_at at time zone %(tz)s)::date between %(start)s and %(end)s""",
    "mean_score_pct": """
        select avg(sub.score / a.max_score * 100.0) as v
        from public.assignment_submissions sub join public.assignments a on a.id = sub.assignment_id
        where sub.student_id = %(student)s and sub.score is not null
          and (sub.graded_at at time zone %(tz)s)::date between %(start)s and %(end)s""",
    "risk_probability": """
        select avg(risk_probability) as v from public.risk_predictions
        where student_id = %(student)s and target = 'academic'
          and prediction_date between %(start)s and %(end)s""",
}


@dataclass
class OutcomeStats:
    interventions: int = 0
    measures_written: int = 0
    not_yet_due: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "interventions": self.interventions,
            "measures_written": self.measures_written,
            "not_yet_due": self.not_yet_due,
        }


def windows(offered: date, anchor: date) -> tuple[date, date, date, date]:
    baseline_end = offered - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=WINDOW_DAYS - 1)
    follow_start = anchor + timedelta(days=1)
    follow_end = follow_start + timedelta(days=WINDOW_DAYS - 1)
    return baseline_start, baseline_end, follow_start, follow_end


def compute_outcomes(conn: Connection, *, now: datetime, tz: ZoneInfo = DEFAULT_TZ) -> OutcomeStats:
    today = now.astimezone(tz).date()
    stats = OutcomeStats()
    rows = conn.execute(
        """select id::text as id, student_id::text as student_id, status, created_at, offered_at, completed_at,
                  responded_at
           from public.interventions
           where status = 'completed' or (status = 'declined' and responded_at is not null)"""
    ).fetchall()
    for r in rows:
        stats.interventions += 1
        anchor_ts = r["completed_at"] if r["status"] == "completed" else r["responded_at"]
        offered_ts = r["offered_at"] or r["created_at"]
        b_start, b_end, f_start, f_end = windows(offered_ts.astimezone(tz).date(), anchor_ts.astimezone(tz).date())
        if f_end >= today:
            stats.not_yet_due += 1
            continue
        for indicator, sql in INDICATOR_SQL.items():
            common = {"student": r["student_id"], "tz": str(tz)}
            base = conn.execute(sql, {**common, "start": b_start, "end": b_end}).fetchone()
            follow = conn.execute(sql, {**common, "start": f_start, "end": f_end}).fetchone()
            cur = conn.execute(
                """insert into public.intervention_outcome_measures
                     (intervention_id, indicator, baseline_value, followup_value, baseline_start, baseline_end,
                      followup_start, followup_end, method_version)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   on conflict (intervention_id, indicator, method_version) do nothing""",
                (
                    r["id"],
                    indicator,
                    base["v"] if base else None,
                    follow["v"] if follow else None,
                    b_start,
                    b_end,
                    f_start,
                    f_end,
                    METHOD_VERSION,
                ),
            )
            stats.measures_written += cur.rowcount
    conn.commit()
    return stats
