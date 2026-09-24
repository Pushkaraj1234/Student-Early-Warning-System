"""Vendor-neutral LMS ingestion model.

An adapter turns one provider's export or API response into :class:`LmsRecord` values that carry
ONLY what SEWS needs: a provider event id (hashed before storage), the keys used to match the student
and course, a canonical event type, a timestamp and a count. Raw payloads, free text, IP addresses,
user agents and provider user ids are never kept; the student/course keys are used for matching and
then discarded.

Canonical event types (public.engagement_events.event_type):
    lms_login, resource_view, assignment_view, assignment_submission, quiz_attempt, forum_activity
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

CanonicalEventType = Literal[
    "lms_login", "resource_view", "assignment_view", "assignment_submission", "quiz_attempt", "forum_activity"
]
CANONICAL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "lms_login",
        "resource_view",
        "assignment_view",
        "assignment_submission",
        "quiz_attempt",
        "forum_activity",
    }
)
Provider = Literal["moodle", "canvas", "google_classroom", "blackboard", "csv_import"]
RejectReason = Literal["unmapped_event_type", "missing_field", "invalid_timestamp", "future_timestamp", "invalid_count"]
MAX_CLOCK_SKEW = timedelta(minutes=5)


@dataclass(frozen=True)
class LmsRecord:
    external_event_id: str
    user_key: str  # institutional e-mail or roll number known to the LMS; used for matching only
    course_key: str | None  # course code; None for platform-wide events such as logins
    event_type: CanonicalEventType
    occurred_at: datetime
    event_count: int = 1


@dataclass(frozen=True)
class RejectedRecord:
    reason: RejectReason  # a code only: rejected content is never retained or logged


class LmsAdapter(Protocol):
    provider: Provider

    def records(self) -> Iterator[LmsRecord | RejectedRecord]: ...


def event_hash(integration_id: str, external_event_id: str) -> str:
    """SHA-256 of the provider event id, namespaced by integration (dedupe without storing the id)."""
    return hashlib.sha256(f"{integration_id}:{external_event_id}".encode()).hexdigest()


def validate_record(
    external_event_id: str | None,
    user_key: str | None,
    course_key: str | None,
    event_type: str | None,
    occurred_at: datetime | None,
    event_count: int = 1,
    *,
    now: datetime | None = None,
) -> LmsRecord | RejectedRecord:
    if not external_event_id or not user_key:
        return RejectedRecord("missing_field")
    if event_type not in CANONICAL_EVENT_TYPES:
        return RejectedRecord("unmapped_event_type")
    if occurred_at is None or occurred_at.tzinfo is None:
        return RejectedRecord("invalid_timestamp")
    if occurred_at > (now or datetime.now(UTC)) + MAX_CLOCK_SKEW:
        return RejectedRecord("future_timestamp")
    if not 1 <= event_count <= 10_000:
        return RejectedRecord("invalid_count")
    return LmsRecord(
        external_event_id=external_event_id,
        user_key=user_key.strip().lower(),
        course_key=course_key.strip().upper() if course_key else None,
        event_type=event_type,  # type: ignore[arg-type]
        occurred_at=occurred_at.astimezone(UTC),
        event_count=event_count,
    )
