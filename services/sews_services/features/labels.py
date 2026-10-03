"""Academic outcome labels from published results — one definition for monitoring and training.

Target ``academic`` for a student in a term (odd/even semester; summer terms are not labelled):
  1  the student withdrew from, or received F/Ab in, any course of that term;
  0  every course of that term has a published result (or was withdrawn) and none is adverse;
  unknown otherwise — never guessed.
Used by the monitoring job (label-time performance, docs/ml/monitoring.md) and by institutional training
(docs/ml/institutional-training.md), so a model is evaluated on exactly the outcome it was trained on.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sews_services.db import Connection

LABEL_SQL = """
select sc.student_id::text as student_id,
       bool_or(sc.status = 'withdrawn' or (sc.result_published_at is not null and sc.grade in ('F', 'Ab')))
         as adverse,
       bool_and(sc.status = 'withdrawn' or sc.result_published_at is not null) as all_known
from public.student_courses sc
join public.academic_terms t
  on t.institution_id = sc.institution_id and t.academic_year = sc.academic_year
 and t.term in ('odd', 'even') and (sc.semester %% 2 = 1) = (t.term = 'odd')
where sc.student_id = any(%(students)s::uuid[]) and %(day)s between t.starts_on and t.ends_on
group by sc.student_id
"""


def academic_labels(conn: Connection, student_ids: Sequence[str], day: date) -> dict[str, float]:
    """Label of each student for the term containing ``day``; students with an unknown label are absent."""
    rows = conn.execute(LABEL_SQL, {"students": list(student_ids), "day": day}).fetchall()
    return {r["student_id"]: float(r["adverse"]) for r in rows if r["adverse"] or r["all_known"]}
