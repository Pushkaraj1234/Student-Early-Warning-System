"""Training tables from an institution's own past terms, built with the scoring job's feature code.

For each completed odd/even term and each decision point (day ``c`` of the term), every student enrolled in
the term gets the ``inst-fs-1.0.0`` feature vector as of ``t = term start + c days`` — computed by the same
``build_features`` the live scoring job uses, so training and scoring cannot drift apart — and the term's
academic label (sews_services.features.labels). Students whose label is still unknown are left out.

Availability by EVENT time (docs/ml/institutional-training.md). Live scoring decides what was known at ``t``
from ``recorded_at`` (when SEWS learned a fact); history imported in bulk has ``recorded_at`` = import time,
which would hide every past record. Training therefore replays each term by when things happened:
  attendance   known from local midnight of its attendance_date
  engagement   known when it occurred
  assessments  submissions at submitted_at, scores at graded_at; an excusal at the due date (no time stored)
  results      at published_at (prior-term GPA)
If live data is recorded late, live features lag the training features; monitoring compares the two.

Population of a term: students enrolled in one of its courses, whatever their status today (a student who
later withdrew must stay in the population, or the adverse outcomes would be filtered out). The schema has no
withdrawal date, so a student who had already withdrawn before ``t`` is still included — a known limitation.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd

from ml.data.contract import TARGET_COLUMN
from sews_services.db import Connection
from sews_services.features.institutional import (
    ACADEMIC_COLUMNS,
    ASSESSMENT_COLUMNS,
    ATTENDANCE_COLUMNS,
    DEFAULT_TZ,
    ENGAGEMENT_COLUMNS,
    FEATURES,
    InstitutionalData,
    assert_no_future_leakage,
    build_features,
    term_start_timestamp,
)
from sews_services.features.labels import academic_labels

TermName = Literal["odd", "even"]
TERM_ORDER: dict[str, int] = {"odd": 0, "even": 1}  # the odd semester (Jul-Dec) precedes the even one


@dataclass(frozen=True)
class Term:
    academic_year: str
    term: TermName
    starts_on: date
    ends_on: date

    @property
    def key(self) -> str:
        return f"{self.academic_year}-{self.term}"


def term_sort_key(key: str) -> tuple[int, int]:
    """Chronological order of term keys such as ``2025-26-odd`` (used by the out-of-time split)."""
    year, _, term = key.rpartition("-")
    return int(year[:4]), TERM_ORDER[term]


def completed_terms(conn: Connection, institution_id: str, today: date) -> list[Term]:
    rows = conn.execute(
        """select academic_year, term, starts_on, ends_on from public.academic_terms
           where institution_id = %s and term in ('odd', 'even') and ends_on < %s""",
        (institution_id, today),
    ).fetchall()
    terms = [Term(r["academic_year"], r["term"], r["starts_on"], r["ends_on"]) for r in rows]
    return sorted(terms, key=lambda t: term_sort_key(t.key))


def cutoff_timestamp(term: Term, cutoff_day: int, tz: ZoneInfo = DEFAULT_TZ) -> datetime:
    """``t`` for decision point ``cutoff_day``: the first ``cutoff_day`` full local days of the term are known."""
    return (term_start_timestamp(term.starts_on, tz) + timedelta(days=cutoff_day)).to_pydatetime()


def term_students(conn: Connection, institution_id: str, term: Term) -> tuple[str, ...]:
    """Students enrolled in at least one course of the term, whatever their status today."""
    rows = conn.execute(
        """select distinct sc.student_id::text as id from public.student_courses sc
           where sc.institution_id = %s and sc.academic_year = %s and (sc.semester %% 2 = 1) = %s
           order by 1""",
        (institution_id, term.academic_year, term.term == "odd"),
    ).fetchall()
    return tuple(r["id"] for r in rows)


def _local_midnight_utc(days: pd.Series, tz: ZoneInfo) -> pd.Series:
    return pd.to_datetime(days).dt.tz_localize(tz).dt.tz_convert("UTC")


def load_term_history(
    conn: Connection, institution_id: str, term: Term, tz: ZoneInfo = DEFAULT_TZ
) -> InstitutionalData:
    """Everything the features need for one past term, with availability by event time (module docstring)."""
    params: dict[str, Any] = {
        "inst": institution_id,
        "year": term.academic_year,
        "odd": term.term == "odd",
        "starts_on": term.starts_on,
        "ends_on": term.ends_on,
        "start_ts": term_start_timestamp(term.starts_on, tz).to_pydatetime(),
        "end_ts": term_start_timestamp(term.ends_on + timedelta(days=1), tz).to_pydatetime(),
    }
    students = term_students(conn, institution_id, term)
    params["students"] = list(students)

    def frame(sql: str, columns: list[str]) -> pd.DataFrame:
        return pd.DataFrame(conn.execute(sql, params).fetchall(), columns=columns)

    attendance = frame(
        """select ar.student_id::text as student_id, ar.attendance_date, ar.session_number, ar.status,
                  null::timestamptz as recorded_at
           from public.attendance_records ar
           where ar.student_id = any(%(students)s::uuid[])
             and ar.attendance_date between %(starts_on)s and %(ends_on)s""",
        ATTENDANCE_COLUMNS,
    )
    attendance["recorded_at"] = _local_midnight_utc(attendance["attendance_date"], tz)
    assessments = frame(
        """select sc.student_id::text as student_id, a.id::text as assignment_id, a.due_at, a.max_score,
                  sub.submitted_at, sub.score, sub.graded_at,
                  case when sub.status = 'excused' then a.due_at end as excused_at
           from public.student_courses sc
           join public.assignments a on a.course_id = sc.course_id and a.academic_year = sc.academic_year
           left join public.assignment_submissions sub on sub.assignment_id = a.id and sub.student_id = sc.student_id
           where sc.institution_id = %(inst)s and sc.academic_year = %(year)s
             and (sc.semester %% 2 = 1) = %(odd)s
             and a.due_at >= %(start_ts)s and a.due_at < %(end_ts)s""",
        ASSESSMENT_COLUMNS,
    )
    engagement = frame(
        """select e.student_id::text as student_id, e.event_type, e.event_count, e.occurred_at,
                  e.occurred_at as recorded_at
           from public.engagement_events e
           where e.student_id = any(%(students)s::uuid[])
             and e.occurred_at >= %(start_ts)s and e.occurred_at < %(end_ts)s""",
        ENGAGEMENT_COLUMNS,
    )
    academic = frame(
        """select r.student_id::text as student_id, r.sgpa, r.result_status, r.published_at
           from public.academic_records r
           where r.student_id = any(%(students)s::uuid[]) and r.published_at is not null""",
        ACADEMIC_COLUMNS,
    )
    return InstitutionalData(students, term.starts_on, attendance, assessments, engagement, academic)


@dataclass
class TermTables:
    """Rows per decision point, plus what the leakage guard and the label coverage check found."""

    tables: dict[int, pd.DataFrame]
    leakage: dict[int, dict[str, Any]]
    coverage: dict[str, dict[str, int]]


def build_training_tables(
    conn: Connection,
    institution_id: str,
    terms: Sequence[Term],
    cutoff_days: Sequence[int],
    tz: ZoneInfo = DEFAULT_TZ,
) -> TermTables:
    """Feature tables (ml/data/contract.py) for every term and decision point. The temporal leakage guard runs
    for every term and decision point and raises TemporalLeakageError on any leak (nothing is trained)."""
    parts: dict[int, list[pd.DataFrame]] = {c: [] for c in cutoff_days}
    leakage: dict[int, dict[str, Any]] = {
        c: {"passed": True, "terms": 0, "rows_compared": 0, "features_compared": len(FEATURES)} for c in cutoff_days
    }
    coverage: dict[str, dict[str, int]] = {}
    for term in terms:
        data = load_term_history(conn, institution_id, term, tz)
        labels = academic_labels(conn, data.student_ids, term.starts_on)
        coverage[term.key] = {"students": len(data.student_ids), "labelled": len(labels)}
        for c in cutoff_days:
            t = cutoff_timestamp(term, c, tz)
            assert_no_future_leakage(data, t, tz)
            leakage[c]["terms"] += 1
            leakage[c]["rows_compared"] += len(data.student_ids)
            features = build_features(data, t, tz)
            frame = features[features.index.isin(list(labels))].reset_index()
            frame.insert(1, "context_id", term.key)
            frame.insert(2, "prediction_date", pd.Timestamp(t).tz_convert("UTC").tz_localize(None))
            frame.insert(3, "cutoff_day", c)
            frame.insert(4, "split_group", term.key)
            frame[TARGET_COLUMN] = frame["student_id"].map(labels).astype("int64")
            parts[c].append(frame)
    tables = {
        c: pd.concat(p, ignore_index=True).astype({"cutoff_day": "int64"}) if p else pd.DataFrame()
        for c, p in parts.items()
    }
    return TermTables(tables=tables, leakage=leakage, coverage=coverage)


def dataset_version(tables: dict[int, pd.DataFrame]) -> str:
    """Content hash of the training tables (feature values, labels and term keys, row order normalised)."""
    digest = hashlib.sha256()
    for c in sorted(tables):
        frame = tables[c].sort_values(["context_id", "student_id"]).reset_index(drop=True)
        digest.update(f"cutoff={c};rows={len(frame)}\n".encode())
        digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
    return f"inst-{digest.hexdigest()[:16]}"
