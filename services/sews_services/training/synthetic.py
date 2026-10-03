"""SYNTHETIC multi-term history for proving institutional training end to end. Development only.

``python -m sews_services.training.synthetic --students 400 --seed 7`` (SEWS_ENV=development, loopback
database). Creates a separate institution, "SEWS Synthetic History Institute (demo data)" (code SYNTH-HIST),
with one cohort followed through four completed semesters (results published) and the current one (in
progress, no results). Nothing here describes a real person, institution or outcome; every model trained
on it must be registered with data_provenance = 'synthetic', which the database never lets reach production.

How the data is generated: each student has a persistent ability, a per-term shock and a per-term drift
(behaviour deteriorating or improving over the term). Attendance, submissions, scores and LMS activity follow
from them, and so does the outcome (withdrawal, or F in one or both courses), with noise. A model therefore
finds real but imperfect signal — and finds more of it later in the term, as the drift shows.
"""

from __future__ import annotations

import argparse
import math
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from sews_services.config import ConfigError, load_settings
from sews_services.db import Connection, connect
from sews_services.features.institutional import DEFAULT_TZ

INSTITUTION_CODE = "SYNTH-HIST"
COURSES_PER_TERM = 2
COURSE_CREDITS = 4
ASSIGNMENT_DAYS = (21, 42, 63, 84)  # due days after the term start
ASSIGNMENT_MAX_SCORE = 20
GRADING_DELAY_DAYS = 7
RESULTS_DELAY_DAYS = 30  # results are published this long after the term ends
LATE_SHARE = 0.15
WITHDRAW_THRESHOLD = 2.2  # on the adverse score: about 6% of students per term
FAIL_THRESHOLD = 1.1  # about 20% of the remaining students fail at least one course
FAIL_BOTH_MARGIN = 0.6
QUIZ_DAY_PROBABILITY = 0.12
UNSCORED_COURSE_PCT = 35.0  # a passing student with no graded work is placed just under the pass mark
GRADES = ((90, "O"), (80, "A+"), (70, "A"), (60, "B+"), (55, "B"), (50, "C"), (40, "P"))
GRADE_POINTS = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "P": 4, "F": 0}
PASS_MARK = 40.0


class SyntheticRefusedError(RuntimeError):
    pass


@dataclass(frozen=True)
class TermPlan:
    academic_year: str
    term: str
    semester: int
    starts_on: date
    ends_on: date
    completed: bool


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _uuid(rng: np.random.Generator) -> str:
    return str(uuid.UUID(bytes=rng.bytes(16), version=4))


def _at(day: date, hour: int, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time(hour), tz).astimezone(UTC)


def term_plan(today: date) -> list[TermPlan]:
    """Four completed semesters and the current odd semester of the academic year containing ``today``."""
    year = today.year if today.month >= 7 else today.year - 1

    def label(y: int) -> str:
        return f"{y}-{(y + 1) % 100:02d}"

    plans = []
    for i, y in enumerate((year - 2, year - 1)):
        plans.append(TermPlan(label(y), "odd", 2 * i + 1, date(y, 7, 20), date(y, 12, 4), True))
        plans.append(TermPlan(label(y), "even", 2 * i + 2, date(y + 1, 1, 5), date(y + 1, 5, 15), True))
    plans.append(TermPlan(label(year), "odd", 5, date(year, 7, 15), date(year, 12, 10), False))
    return plans


def _weekdays(start: date, end: date) -> Iterator[date]:
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _last_day(end: date, start: date, withdrawal: int | None) -> date:
    """Last day with activity: the end of the data, or the withdrawal day."""
    return end if withdrawal is None else min(end, start + timedelta(days=withdrawal))


def _grade(pct: float) -> str:
    return next((g for limit, g in GRADES if pct >= limit), "F")


def generate(
    conn: Connection, *, students: int, seed: int, today: date, tz: ZoneInfo = DEFAULT_TZ
) -> dict[str, int | str]:
    if conn.execute("select 1 from public.institutions where code = %s", (INSTITUTION_CODE,)).fetchone():
        raise SyntheticRefusedError(f"institution {INSTITUTION_CODE} already exists; rebuild the local database")
    rng = np.random.default_rng(seed)
    inst, dept, prog = _uuid(rng), _uuid(rng), _uuid(rng)
    plans = term_plan(today)
    conn.execute(
        "insert into public.institutions (id, code, name) values (%s, %s, %s)",
        (inst, INSTITUTION_CODE, "SEWS Synthetic History Institute (demo data)"),
    )
    conn.execute(
        "insert into public.departments (id, institution_id, code, name) values (%s, %s, 'SYN', %s)",
        (dept, inst, "Synthetic Department (demo data)"),
    )
    conn.execute(
        """insert into public.programmes (id, institution_id, department_id, code, name, degree_level,
                                          duration_semesters)
           values (%s, %s, %s, 'SYN-BTECH', 'Synthetic B.Tech (demo data)', 'undergraduate', 8)""",
        (prog, inst, dept),
    )
    courses: dict[int, list[str]] = {}
    for p in plans:
        conn.execute(
            """insert into public.academic_terms (institution_id, academic_year, term, starts_on, ends_on)
               values (%s, %s, %s, %s, %s)""",
            (inst, p.academic_year, p.term, p.starts_on, p.ends_on),
        )
        courses[p.semester] = []
        for k in range(1, COURSES_PER_TERM + 1):
            cid = _uuid(rng)
            courses[p.semester].append(cid)
            conn.execute(
                """insert into public.courses (id, institution_id, department_id, programme_id, code, title, credits,
                                               semester_number)
                   values (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    cid,
                    inst,
                    dept,
                    prog,
                    f"SYH-S{p.semester}-C{k}",
                    f"Synthetic course {p.semester}.{k}",
                    COURSE_CREDITS,
                    p.semester,
                ),
            )

    ids = [_uuid(rng) for _ in range(students)]
    index_of = {sid: k for k, sid in enumerate(ids)}
    ability = rng.normal(0.0, 1.0, students)
    active = np.ones(students, dtype=bool)
    last_semester = np.ones(students, dtype=int)
    cgpa_points = np.zeros(students)
    cgpa_credits = np.zeros(students)
    with (
        conn.cursor() as cur,
        cur.copy(
            "copy public.students (id, institution_id, programme_id, roll_number, full_name, institutional_email,"
            " admission_year, current_semester, status) from stdin"
        ) as copy,
    ):
        for n, sid in enumerate(ids, start=1):
            copy.write_row(
                (
                    sid,
                    inst,
                    prog,
                    f"SYH{n:04d}",
                    f"Synthetic History Student {n:04d}",
                    f"syh{n:04d}@synthetic.example.com",
                    plans[0].starts_on.year,
                    1,
                    "active",
                )
            )

    counts = {"students": students, "attendance": 0, "submissions": 0, "engagement": 0, "withdrawn": 0, "failed": 0}
    yesterday = today - timedelta(days=1)
    for p in plans:
        enrolled = [int(i) for i in np.flatnonzero(active)]
        last_semester[enrolled] = p.semester
        assignments = {
            cid: [(_uuid(rng), p.starts_on + timedelta(days=d)) for d in ASSIGNMENT_DAYS] for cid in courses[p.semester]
        }
        for cid, items in assignments.items():
            for n, (aid, due_day) in enumerate(items, start=1):
                conn.execute(
                    """insert into public.assignments (id, institution_id, course_id, academic_year, title, max_score,
                                                       due_at)
                       values (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        aid,
                        inst,
                        cid,
                        p.academic_year,
                        f"Synthetic assignment {n}",
                        ASSIGNMENT_MAX_SCORE,
                        _at(due_day, 18, tz),
                    ),
                )
        length = (p.ends_on - p.starts_on).days
        end_of_data = p.ends_on if p.completed else min(p.ends_on, yesterday)
        enrolments: list[tuple[str, str, str]] = []  # (student_course_id, student_id, course_id)
        failed_courses: dict[int, int] = {}
        behaviour: dict[int, tuple[float, float, int | None]] = {}  # index -> (z, drift, withdrawal day)
        for i in enrolled:
            z = -ability[i] + rng.normal(0.0, 0.6)
            drift = rng.normal(0.0, 0.5)
            adverse = z + 0.8 * drift + rng.normal(0.0, 0.7)
            withdrawal = int(rng.integers(30, length - 20)) if p.completed and adverse > WITHDRAW_THRESHOLD else None
            behaviour[i] = (z, drift, withdrawal)
            if withdrawal is None:
                failed_courses[i] = (
                    0 if adverse <= FAIL_THRESHOLD else (2 if adverse > FAIL_THRESHOLD + FAIL_BOTH_MARGIN else 1)
                )
            for cid in courses[p.semester]:
                enrolments.append((_uuid(rng), ids[i], cid))

        with (
            conn.cursor() as cur,
            cur.copy(
                "copy public.student_courses (id, institution_id, student_id, course_id, academic_year, semester,"
                " status) from stdin"
            ) as copy,
        ):
            for scid, sid, cid in enrolments:
                copy.write_row((scid, inst, sid, cid, p.academic_year, p.semester, "enrolled"))

        with (
            conn.cursor() as cur,
            cur.copy(
                "copy public.attendance_records (student_course_id, student_id, course_id, attendance_date, status)"
                " from stdin"
            ) as copy,
        ):
            for scid, sid, cid in enrolments:
                i = index_of[sid]
                z, drift, _ = behaviour[i]
                for day in _weekdays(p.starts_on, _last_day(end_of_data, p.starts_on, behaviour[i][2])):
                    progress = (day - p.starts_on).days / length
                    if rng.uniform() < _sigmoid(2.2 - 1.3 * z - 2.0 * drift * progress):
                        status = "late" if rng.uniform() < 0.05 else "present"
                    else:
                        status = "excused" if rng.uniform() < 0.05 else "absent"
                    copy.write_row((scid, sid, cid, day, status))
                    counts["attendance"] += 1

        course_pct: dict[tuple[int, str], list[float]] = {}
        with (
            conn.cursor() as cur,
            cur.copy(
                "copy public.assignment_submissions (assignment_id, student_id, status, submitted_at, score, graded_at)"
                " from stdin"
            ) as copy,
        ):
            for _scid, sid, cid in enrolments:
                i = index_of[sid]
                z, drift, _ = behaviour[i]
                for aid, due_day in assignments[cid]:
                    if due_day > _last_day(end_of_data, p.starts_on, behaviour[i][2]):
                        continue
                    progress = (due_day - p.starts_on).days / length
                    if rng.uniform() >= _sigmoid(2.0 - 1.4 * z - 2.0 * drift * progress):
                        continue  # not submitted: no row, counted as missed
                    late = rng.uniform() < LATE_SHARE
                    submitted_day = due_day + timedelta(days=int(rng.integers(1, 4))) if late else due_day
                    pct = float(np.clip(rng.normal(70 - 12 * z - 16 * drift * progress, 10), 0, 100))
                    course_pct.setdefault((i, cid), []).append(pct)
                    graded_day = due_day + timedelta(days=GRADING_DELAY_DAYS)
                    graded = _at(graded_day, 17, tz) if graded_day <= end_of_data else None
                    score = round(pct / 100 * ASSIGNMENT_MAX_SCORE, 2) if graded else None
                    copy.write_row(
                        (aid, sid, "late" if late else "submitted", _at(submitted_day, 12, tz), score, graded)
                    )
                    counts["submissions"] += 1

        with (
            conn.cursor() as cur,
            cur.copy(
                "copy public.engagement_events (student_id, event_type, event_count, source, occurred_at) from stdin"
            ) as copy,
        ):
            for i in enrolled:
                z, drift, _ = behaviour[i]
                day = p.starts_on
                while day <= _last_day(end_of_data, p.starts_on, behaviour[i][2]):
                    progress = (day - p.starts_on).days / length
                    logins = int(rng.poisson(math.exp(0.8 - 0.6 * z - 1.0 * drift * progress)))
                    if logins:
                        copy.write_row((ids[i], "lms_login", logins, "lms", _at(day, 20, tz)))
                        counts["engagement"] += 1
                    if rng.uniform() < QUIZ_DAY_PROBABILITY * _sigmoid(1.0 - z):
                        copy.write_row((ids[i], "quiz_attempt", 1, "lms", _at(day, 21, tz)))
                        counts["engagement"] += 1
                    day += timedelta(days=1)

        if not p.completed:
            continue
        published = _at(p.ends_on + timedelta(days=RESULTS_DELAY_DAYS), 16, tz)
        for i in enrolled:
            if behaviour[i][2] is not None:
                conn.execute(
                    "update public.student_courses set status = 'withdrawn'"
                    " where student_id = %s and academic_year = %s and semester = %s",
                    (ids[i], p.academic_year, p.semester),
                )
                conn.execute("update public.students set status = 'withdrawn' where id = %s", (ids[i],))
                active[i] = False
                counts["withdrawn"] += 1
                continue
            failed = failed_courses[i]
            points = []
            for k, cid in enumerate(courses[p.semester]):
                scores = course_pct.get((i, cid), [])
                pct = float(np.mean(scores)) if scores else UNSCORED_COURSE_PCT
                grade = "F" if k < failed else _grade(max(pct, PASS_MARK))
                points.append(GRADE_POINTS[grade])
                conn.execute(
                    """update public.student_courses set status = 'completed', marks = %s, grade = %s,
                              result_published_at = %s
                       where student_id = %s and course_id = %s and academic_year = %s""",
                    (round(pct, 2), grade, published, ids[i], cid, p.academic_year),
                )
            sgpa = float(np.mean(points))
            cgpa_points[i] += sgpa * COURSE_CREDITS * COURSES_PER_TERM
            cgpa_credits[i] += COURSE_CREDITS * COURSES_PER_TERM
            conn.execute(
                """insert into public.academic_records (student_id, academic_year, semester, sgpa, cgpa,
                                                        credits_registered, credits_earned, result_status,
                                                        published_at)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    ids[i],
                    p.academic_year,
                    p.semester,
                    round(sgpa, 2),
                    round(cgpa_points[i] / cgpa_credits[i], 2),
                    COURSE_CREDITS * COURSES_PER_TERM,
                    COURSE_CREDITS * sum(1 for x in points if x > 0),
                    "fail" if failed else "pass",
                    published,
                ),
            )
            counts["failed"] += 1 if failed else 0
    for i in range(students):
        conn.execute("update public.students set current_semester = %s where id = %s", (int(last_semester[i]), ids[i]))
    conn.commit()
    result: dict[str, int | str] = {"institution_id": inst, **counts}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate SYNTHETIC multi-term history (development only).")
    parser.add_argument("--students", type=int, default=400)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    if not 50 <= args.students <= 5000:
        parser.error("--students must be between 50 and 5000")
    try:
        settings = load_settings(require_api_auth=False)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    if settings.environment != "development":
        print("refused: synthetic history may only be generated in development (local database)", file=sys.stderr)
        return 3
    with connect(settings.database_url) as conn:
        try:
            result = generate(conn, students=args.students, seed=args.seed, today=datetime.now(DEFAULT_TZ).date())
        except SyntheticRefusedError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 3
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
