"""Concrete LMS adapters.

Implemented:
  * CsvImportAdapter  - the documented SEWS CSV format (any LMS that can export a report).
  * MoodleLogAdapter  - rows of Moodle's standard log store (logstore_standard_log) plus user and
                        course lookups. The event-name mapping below must be checked against the
                        institution's Moodle version before production use.

Not implemented (no verified API access yet): Canvas, Google Classroom, Blackboard. Institutions using
them can export to the CSV format. No adapter is guessed.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator, Mapping
from datetime import UTC, datetime
from io import StringIO

from sews_services.lms.base import LmsRecord, Provider, RejectedRecord, validate_record

CSV_COLUMNS = ("event_id", "user_key", "course_code", "event_type", "occurred_at")
MAX_CSV_BYTES = 20 * 1024 * 1024


class CsvImportAdapter:
    """CSV with header ``event_id,user_key,course_code,event_type,occurred_at[,event_count]``.
    ``event_type`` must already be canonical; ``occurred_at`` is ISO 8601 with a UTC offset."""

    provider: Provider = "csv_import"

    def __init__(self, text: str, *, now: datetime | None = None) -> None:
        if len(text.encode()) > MAX_CSV_BYTES:
            raise ValueError("CSV import is larger than the 20 MB limit")
        self._text = text
        self._now = now

    def records(self) -> Iterator[LmsRecord | RejectedRecord]:
        reader = csv.DictReader(StringIO(self._text))
        header = tuple(reader.fieldnames or ())
        if header[: len(CSV_COLUMNS)] != CSV_COLUMNS or not set(header) <= {*CSV_COLUMNS, "event_count"}:
            raise ValueError("CSV header does not match the SEWS import format")
        for row in reader:
            try:
                occurred = datetime.fromisoformat(row["occurred_at"]) if row["occurred_at"] else None
            except ValueError:
                yield RejectedRecord("invalid_timestamp")
                continue
            try:
                count = int(row.get("event_count") or 1)
            except ValueError:
                yield RejectedRecord("invalid_count")
                continue
            yield validate_record(
                row["event_id"],
                row["user_key"],
                row["course_code"] or None,
                row["event_type"],
                occurred,
                count,
                now=self._now,
            )


# Moodle event class -> canonical type. Anything else is rejected as unmapped (never guessed).
MOODLE_EVENT_MAP: dict[str, str] = {
    "\\core\\event\\user_loggedin": "lms_login",
    "\\mod_resource\\event\\course_module_viewed": "resource_view",
    "\\mod_page\\event\\course_module_viewed": "resource_view",
    "\\mod_url\\event\\course_module_viewed": "resource_view",
    "\\mod_folder\\event\\course_module_viewed": "resource_view",
    "\\mod_book\\event\\course_module_viewed": "resource_view",
    "\\mod_book\\event\\chapter_viewed": "resource_view",
    "\\mod_assign\\event\\course_module_viewed": "assignment_view",
    "\\mod_assign\\event\\submission_status_viewed": "assignment_view",
    "\\mod_assign\\event\\assessable_submitted": "assignment_submission",
    "\\mod_quiz\\event\\attempt_submitted": "quiz_attempt",
    "\\mod_forum\\event\\post_created": "forum_activity",
    "\\mod_forum\\event\\discussion_created": "forum_activity",
    "\\mod_forum\\event\\discussion_viewed": "forum_activity",
}


class MoodleLogAdapter:
    """Reads ONLY id, eventname, userid, courseid, timecreated and anonymous from each log row.
    The ``other``, ``ip`` and ``relateduserid`` columns are never read."""

    provider: Provider = "moodle"

    def __init__(
        self,
        rows: Iterable[Mapping[str, str]],
        *,
        user_keys: Mapping[str, str],
        course_codes: Mapping[str, str],
        now: datetime | None = None,
    ) -> None:
        self._rows = rows
        self._users = user_keys  # Moodle user id -> institutional e-mail / roll number
        self._courses = course_codes  # Moodle course id -> course code (shortname)
        self._now = now

    def records(self) -> Iterator[LmsRecord | RejectedRecord]:
        for row in self._rows:
            if row.get("anonymous") == "1":
                continue  # anonymous events cannot be attributed and are not ingested
            event_type = MOODLE_EVENT_MAP.get(row.get("eventname", ""))
            if event_type is None:
                yield RejectedRecord("unmapped_event_type")
                continue
            try:
                occurred = datetime.fromtimestamp(int(row.get("timecreated", "")), tz=UTC)
            except (ValueError, OverflowError, OSError):
                yield RejectedRecord("invalid_timestamp")
                continue
            course = row.get("courseid", "")
            yield validate_record(
                row.get("id"),
                self._users.get(row.get("userid", "")),
                self._courses.get(course) if course not in ("", "0", "1") else None,  # 0/1 = site level
                event_type,
                occurred,
                now=self._now,
            )
