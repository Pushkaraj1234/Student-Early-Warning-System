"""Ingest normalised LMS records into public.engagement_events.

* Only the integration's own institution is searched when matching students and courses.
* A user key that matches no student, or more than one, is counted as unresolved and dropped.
* Provider event ids are stored only as a namespaced SHA-256 hash; re-imports are de-duplicated by the
  (integration_id, external_event_hash) unique index.
* The returned statistics and any system event contain counts only - never keys or identifiers.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sews_services.db import Connection, record_system_event
from sews_services.lms.base import LmsAdapter, LmsRecord, event_hash

BATCH_SIZE = 500

INSERT_SQL = """
insert into public.engagement_events
  (student_id, course_id, event_type, event_count, source, occurred_at, integration_id, external_event_hash)
select s, c, t, n, %(source)s, o, %(integration_id)s::uuid, h
from unnest(%(students)s::uuid[], %(courses)s::uuid[], %(types)s::text[], %(counts)s::int[],
            %(occurred)s::timestamptz[], %(hashes)s::text[]) as x(s, c, t, n, o, h)
on conflict (integration_id, external_event_hash)
  where integration_id is not null and external_event_hash is not null
do nothing
"""


class IngestError(RuntimeError):
    """The integration cannot be used (unknown, inactive or provider mismatch)."""


@dataclass
class IngestStats:
    received: int = 0
    inserted: int = 0
    duplicates: int = 0
    unresolved_student: int = 0
    unresolved_course: int = 0
    rejected: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        return {
            "received": self.received,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "unresolved_student": self.unresolved_student,
            "unresolved_course": self.unresolved_course,
            "rejected": dict(self.rejected),
        }


def _student_index(conn: Connection, institution_id: str) -> dict[str, str | None]:
    """lower(e-mail) and lower(roll number) -> student id; None marks an ambiguous key."""
    index: dict[str, str | None] = {}
    rows = conn.execute(
        "select id::text as id, institutional_email, roll_number from public.students where institution_id = %s",
        (institution_id,),
    ).fetchall()
    for row in rows:
        for key in {row["institutional_email"].lower(), row["roll_number"].lower()}:
            index[key] = None if key in index and index[key] != row["id"] else row["id"]
    return index


def ingest(conn: Connection, *, integration_id: str, adapter: LmsAdapter) -> IngestStats:
    integration = conn.execute(
        "select institution_id::text as institution_id, provider, status from public.lms_integrations where id = %s",
        (integration_id,),
    ).fetchone()
    if integration is None or integration["status"] != "active":
        raise IngestError("integration is unknown or not active")
    if integration["provider"] != adapter.provider:
        raise IngestError("adapter provider does not match the integration")
    institution_id = integration["institution_id"]
    students = _student_index(conn, institution_id)
    courses = {
        r["code"].upper(): r["id"]
        for r in conn.execute(
            "select id::text as id, code from public.courses where institution_id = %s", (institution_id,)
        ).fetchall()
    }
    source = "import" if adapter.provider == "csv_import" else "lms"
    stats = IngestStats()
    seen: set[str] = set()
    batch: list[tuple[str, str | None, LmsRecord, str]] = []

    def flush() -> None:
        if not batch:
            return
        cur = conn.execute(
            INSERT_SQL,
            {
                "source": source,
                "integration_id": integration_id,
                "students": [b[0] for b in batch],
                "courses": [b[1] for b in batch],
                "types": [b[2].event_type for b in batch],
                "counts": [b[2].event_count for b in batch],
                "occurred": [b[2].occurred_at for b in batch],
                "hashes": [b[3] for b in batch],
            },
        )
        stats.inserted += cur.rowcount
        stats.duplicates += len(batch) - cur.rowcount
        batch.clear()

    try:
        for item in adapter.records():
            stats.received += 1
            if not isinstance(item, LmsRecord):
                stats.rejected[item.reason] += 1
                continue
            student_id = students.get(item.user_key)
            if student_id is None:
                stats.unresolved_student += 1
                continue
            course_id: str | None = None
            if item.course_key is not None:
                course_id = courses.get(item.course_key)
                if course_id is None:
                    stats.unresolved_course += 1
                    continue
            digest = event_hash(integration_id, item.external_event_id)
            if digest in seen:
                stats.duplicates += 1
                continue
            seen.add(digest)
            batch.append((student_id, course_id, item, digest))
            if len(batch) >= BATCH_SIZE:
                flush()
        flush()
    except Exception:
        conn.rollback()
        record_system_event(
            conn,
            "ingestion",
            "ingestion_error",
            "error",
            {"stage": "insert", **stats.as_dict()},
            institution_id,
        )
        conn.commit()
        raise
    if stats.unresolved_student or stats.rejected:
        record_system_event(
            conn,
            "ingestion",
            "ingestion_error",
            "warning",
            {"stage": "normalise", **stats.as_dict()},
            institution_id,
        )
    conn.commit()
    return stats
