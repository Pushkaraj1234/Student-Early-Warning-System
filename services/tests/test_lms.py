"""LMS adapters (unit) and ingestion into engagement_events (local test database, SYNTHETIC data)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from sews_services.db import Connection
from sews_services.lms.adapters import CsvImportAdapter, MoodleLogAdapter
from sews_services.lms.base import LmsRecord, RejectedRecord, event_hash
from sews_services.lms.ingest import IngestError, ingest

from tests.conftest import ALPHA, CSV_INTEGRATION, INSTITUTION

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
HEADER = "event_id,user_key,course_code,event_type,occurred_at,event_count\n"


def _csv(*rows: str) -> str:
    return HEADER + "".join(r + "\n" for r in rows)


# ------------------------------------------------------------------ adapters (no database)
def test_csv_rows_are_normalised_and_bad_rows_rejected_with_codes_only() -> None:
    text = _csv(
        "e1,Student.Alpha@Synthetic.Example.com,syn-cs201,resource_view,2026-09-20T10:00:00+05:30,3",
        "e2,student.alpha@synthetic.example.com,,lms_login,2026-09-20T10:00:00+05:30,",
        "e3,student.alpha@synthetic.example.com,SYN-CS201,page_view,2026-09-20T10:00:00+05:30,1",
        "e4,student.alpha@synthetic.example.com,SYN-CS201,quiz_attempt,2026-09-20T10:00:00,1",
        "e5,student.alpha@synthetic.example.com,SYN-CS201,quiz_attempt,2030-01-01T00:00:00+00:00,1",
        "e6,student.alpha@synthetic.example.com,SYN-CS201,quiz_attempt,not-a-date,1",
        "e7,student.alpha@synthetic.example.com,SYN-CS201,quiz_attempt,2026-09-20T10:00:00+05:30,0",
        ",student.alpha@synthetic.example.com,SYN-CS201,quiz_attempt,2026-09-20T10:00:00+05:30,1",
    )
    out = list(CsvImportAdapter(text, now=NOW).records())
    first = out[0]
    assert isinstance(first, LmsRecord)
    assert first.user_key == "student.alpha@synthetic.example.com" and first.course_key == "SYN-CS201"
    assert first.occurred_at == datetime(2026, 9, 20, 4, 30, tzinfo=UTC) and first.event_count == 3
    assert isinstance(out[1], LmsRecord) and out[1].course_key is None and out[1].event_count == 1
    reasons = [r.reason for r in out[2:] if isinstance(r, RejectedRecord)]
    assert reasons == [
        "unmapped_event_type",
        "invalid_timestamp",
        "future_timestamp",
        "invalid_timestamp",
        "invalid_count",
        "missing_field",
    ]


def test_csv_with_wrong_header_is_refused() -> None:
    with pytest.raises(ValueError, match="header"):
        list(CsvImportAdapter("id,user,type\n1,a,b\n").records())


def test_moodle_mapping_reads_only_needed_columns() -> None:
    rows = [
        {
            "id": "10",
            "eventname": "\\mod_quiz\\event\\attempt_submitted",
            "userid": "7",
            "courseid": "5",
            "timecreated": "1790000000",
            "anonymous": "0",
            "other": "SECRET PAYLOAD",
            "ip": "10.0.0.1",
        },
        {
            "id": "11",
            "eventname": "\\core\\event\\user_loggedin",
            "userid": "7",
            "courseid": "1",
            "timecreated": "1790000000",
            "anonymous": "0",
        },
        {
            "id": "12",
            "eventname": "\\core\\event\\dashboard_viewed",
            "userid": "7",
            "courseid": "0",
            "timecreated": "1790000000",
            "anonymous": "0",
        },
        {
            "id": "13",
            "eventname": "\\mod_forum\\event\\post_created",
            "userid": "7",
            "courseid": "5",
            "timecreated": "1790000000",
            "anonymous": "1",
        },
    ]
    adapter = MoodleLogAdapter(
        rows, user_keys={"7": "student.alpha@synthetic.example.com"}, course_codes={"5": "SYN-CS201"}, now=NOW
    )
    out = list(adapter.records())
    assert len(out) == 3  # the anonymous event is dropped, not counted
    quiz, login, unmapped = out
    assert isinstance(quiz, LmsRecord) and quiz.event_type == "quiz_attempt" and quiz.course_key == "SYN-CS201"
    assert isinstance(login, LmsRecord) and login.event_type == "lms_login" and login.course_key is None
    assert isinstance(unmapped, RejectedRecord) and unmapped.reason == "unmapped_event_type"
    assert "SECRET" not in repr(out) and "10.0.0.1" not in repr(out)


def test_event_hash_is_namespaced_sha256() -> None:
    digest = event_hash("int-1", "e1")
    assert digest == hashlib.sha256(b"int-1:e1").hexdigest()
    assert digest != event_hash("int-2", "e1")


# ------------------------------------------------------------------ ingestion (database)
def _other_institution_student(conn: Connection) -> None:
    conn.execute(
        """insert into public.institutions (id, code, name)
             values ('b0000000-0000-4000-8000-000000000001', 'OTHER', 'Other Synthetic Institute')
             on conflict do nothing;
           insert into public.departments (id, institution_id, code, name)
             values ('b0000000-0000-4000-8000-000000000011', 'b0000000-0000-4000-8000-000000000001',
                     'CSE', 'Other CSE')
             on conflict do nothing;
           insert into public.programmes
                  (id, institution_id, department_id, code, name, degree_level, duration_semesters)
             values ('b0000000-0000-4000-8000-000000000021', 'b0000000-0000-4000-8000-000000000001',
                     'b0000000-0000-4000-8000-000000000011', 'BTECH', 'Other B.Tech', 'undergraduate', 8)
             on conflict do nothing;
           insert into public.students (id, institution_id, programme_id, roll_number, full_name, institutional_email,
                                        admission_year, current_semester)
             values ('b0000000-0000-4000-8000-000000000041', 'b0000000-0000-4000-8000-000000000001',
                     'b0000000-0000-4000-8000-000000000021', 'OTH001', 'Other Synthetic Student',
                     'other.student@synthetic.example.com', 2025, 3)
             on conflict do nothing;"""
    )
    conn.commit()


def _count(conn: Connection) -> int:
    row = conn.execute(
        "select count(*) as n from public.engagement_events where integration_id = %s", (CSV_INTEGRATION,)
    ).fetchone()
    assert row is not None
    return int(row["n"])


def test_ingest_inserts_deduplicates_and_scopes_to_the_institution(conn: Connection) -> None:
    _other_institution_student(conn)
    text = _csv(
        "ev-1,student.alpha@synthetic.example.com,SYN-CS201,resource_view,2026-09-20T10:00:00+05:30,2",
        "ev-2,SYN2025002,SYN-CS202,assignment_submission,2026-09-21T10:00:00+05:30,1",
        "ev-2,SYN2025002,SYN-CS202,assignment_submission,2026-09-21T10:00:00+05:30,1",  # duplicate in file
        "ev-3,other.student@synthetic.example.com,SYN-CS201,lms_login,2026-09-21T10:00:00+05:30,1",  # other inst.
        "ev-4,nobody@synthetic.example.com,SYN-CS201,lms_login,2026-09-21T10:00:00+05:30,1",
        "ev-5,student.alpha@synthetic.example.com,UNKNOWN-1,lms_login,2026-09-21T10:00:00+05:30,1",
        "ev-6,student.alpha@synthetic.example.com,SYN-CS201,page_view,2026-09-21T10:00:00+05:30,1",
    )
    stats = ingest(conn, integration_id=CSV_INTEGRATION, adapter=CsvImportAdapter(text, now=NOW))
    assert stats.as_dict() == {
        "received": 7,
        "inserted": 2,
        "duplicates": 1,
        "unresolved_student": 2,
        "unresolved_course": 1,
        "rejected": {"unmapped_event_type": 1},
    }
    assert _count(conn) == 2

    again = ingest(conn, integration_id=CSV_INTEGRATION, adapter=CsvImportAdapter(text, now=NOW))
    assert again.inserted == 0 and again.duplicates == 3  # re-import is idempotent
    assert _count(conn) == 2


def test_stored_rows_contain_no_raw_identifiers(conn: Connection) -> None:
    rows = conn.execute(
        "select to_jsonb(e) as j from public.engagement_events e where integration_id = %s",
        (CSV_INTEGRATION,),
    ).fetchall()
    assert rows
    for r in rows:
        text = str(r["j"])
        assert "ev-1" not in text and "ev-2" not in text and "@" not in text and "SYN2025002" not in text
        assert r["j"]["source"] == "import"
        assert len(r["j"]["external_event_hash"]) == 64
    alpha = [r["j"] for r in rows if r["j"]["student_id"] == ALPHA]
    assert alpha and alpha[0]["external_event_hash"] == event_hash(CSV_INTEGRATION, "ev-1")


def test_ingest_statistics_event_has_counts_only(conn: Connection) -> None:
    row = conn.execute(
        "select details from public.system_events where component = 'ingestion' order by occurred_at desc limit 1"
    ).fetchone()
    assert row is not None
    assert set(row["details"]) == {
        "stage",
        "received",
        "inserted",
        "duplicates",
        "unresolved_student",
        "unresolved_course",
        "rejected",
    }


def test_inactive_or_mismatched_integration_is_refused(conn: Connection) -> None:
    with pytest.raises(IngestError, match="provider"):
        ingest(conn, integration_id=CSV_INTEGRATION, adapter=MoodleLogAdapter([], user_keys={}, course_codes={}))
    conn.execute("update public.lms_integrations set status = 'paused' where id = %s", (CSV_INTEGRATION,))
    conn.commit()
    try:
        with pytest.raises(IngestError, match="not active"):
            ingest(conn, integration_id=CSV_INTEGRATION, adapter=CsvImportAdapter(_csv()))
    finally:
        conn.execute("update public.lms_integrations set status = 'active' where id = %s", (CSV_INTEGRATION,))
        conn.commit()
    assert INSTITUTION  # the seeded integration belongs to the synthetic institution
