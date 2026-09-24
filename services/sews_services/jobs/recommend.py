"""Recommendation job: gather each student's context, run the rule engine, store suggestions.

Suggestions are stored with source 'model_rule' and status 'recommended'. The database refuses any
other initial status for rule output, hides 'recommended' rows from students, and allows only one
open intervention per type per student (``on conflict ... do nothing`` makes re-runs idempotent).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from sews_services.db import Connection
from sews_services.features.institutional import DEFAULT_TZ, build_features, load_institutional_data
from sews_services.recommendations.engine import (
    COMPLETED_COOLDOWN_DAYS,
    DECLINE_RESPECT_DAYS,
    PredictionSignal,
    Recommendation,
    StudentContext,
    recommend,
)

CHECKIN_LOOKBACK_DAYS = 30

INSERT_SQL = """
insert into public.interventions
  (student_id, prediction_id, intervention_type, status, source, reason, priority, rule_id)
values (%s, %s, %s, 'recommended', 'model_rule', %s, %s, %s)
on conflict (student_id, intervention_type) where status in ('recommended', 'pending', 'accepted')
do nothing
returning id
"""


@dataclass
class RecommendStats:
    students: int = 0
    recommendations: int = 0
    already_open: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "students": self.students,
            "recommendations": self.recommendations,
            "already_open": self.already_open,
        }


def _contexts(
    conn: Connection, institution_id: str, now: datetime, features: pd.DataFrame
) -> dict[str, StudentContext]:
    params = {
        "inst": institution_id,
        "checkin_since": now - timedelta(days=CHECKIN_LOOKBACK_DAYS),
        "declined_since": now - timedelta(days=DECLINE_RESPECT_DAYS),
        "completed_since": now - timedelta(days=COMPLETED_COOLDOWN_DAYS),
    }
    predictions = {
        r["student_id"]: PredictionSignal(r["id"], r["target"], r["risk_level"], r["trajectory"])
        for r in conn.execute(
            """select distinct on (p.student_id) p.student_id::text as student_id, p.id::text as id, p.target,
                      p.risk_level, p.trajectory
               from public.risk_predictions p join public.students s on s.id = p.student_id
               where s.institution_id = %(inst)s and p.target = 'academic'
               order by p.student_id, p.prediction_date desc, p.scored_at desc""",
            params,
        ).fetchall()
    }
    checkins = {
        r["student_id"]: r
        for r in conn.execute(
            """select distinct on (c.student_id) c.student_id::text as student_id, c.support_needs, c.wants_contact
               from public.student_checkins c join public.students s on s.id = c.student_id
               where s.institution_id = %(inst)s and c.submitted_at >= %(checkin_since)s
               order by c.student_id, c.submitted_at desc""",
            params,
        ).fetchall()
    }
    open_types: dict[str, set[str]] = {}
    declined: dict[str, set[str]] = {}
    completed: dict[str, set[str]] = {}
    for r in conn.execute(
        """select i.student_id::text as student_id, i.intervention_type, i.status, i.responded_at, i.completed_at
           from public.interventions i join public.students s on s.id = i.student_id
           where s.institution_id = %(inst)s
             and (i.status in ('recommended', 'pending', 'accepted')
                  or (i.status = 'declined' and i.responded_at >= %(declined_since)s)
                  or (i.status = 'completed' and i.completed_at >= %(completed_since)s))""",
        params,
    ).fetchall():
        bucket = (
            open_types
            if r["status"] in ("recommended", "pending", "accepted")
            else declined
            if r["status"] == "declined"
            else completed
        )
        bucket.setdefault(r["student_id"], set()).add(r["intervention_type"])

    contexts: dict[str, StudentContext] = {}
    for sid in features.index:
        row = features.loc[sid]
        checkin = checkins.get(sid)
        contexts[sid] = StudentContext(
            prediction=predictions.get(sid),
            features={k: (None if pd.isna(v) else float(v)) for k, v in row.items()},
            checkin_needs=frozenset(checkin["support_needs"]) if checkin else frozenset(),
            wants_contact=bool(checkin["wants_contact"]) if checkin else False,
            open_types=frozenset(open_types.get(sid, set())),
            declined_recently=frozenset(declined.get(sid, set())),
            completed_recently=frozenset(completed.get(sid, set())),
        )
    return contexts


def store(conn: Connection, student_id: str, rec: Recommendation) -> bool:
    row = conn.execute(
        INSERT_SQL,
        (student_id, rec.prediction_id, rec.intervention_type, rec.reason, rec.priority, rec.rule_id),
    ).fetchone()
    return row is not None


def recommend_for_institution(
    conn: Connection, *, institution_id: str, now: datetime, tz: ZoneInfo = DEFAULT_TZ
) -> RecommendStats:
    features = build_features(load_institutional_data(conn, institution_id, now, tz), now, tz)
    stats = RecommendStats(students=len(features))
    for sid, ctx in _contexts(conn, institution_id, now, features).items():
        for rec in recommend(ctx):
            if store(conn, sid, rec):
                stats.recommendations += 1
            else:
                stats.already_open += 1
    conn.commit()
    return stats
