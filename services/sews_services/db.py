"""Database helpers for backend jobs.

Jobs connect with a server-side role (service_role on hosted Supabase; a local superuser in
development). That role bypasses RLS, so every job scopes its own queries by institution and never
exposes rows to clients; clients only ever read through RLS.
"""

from __future__ import annotations

import json
from typing import Any, Literal

import psycopg
from psycopg.rows import DictRow, dict_row

from sews_services.config import Environment

Component = Literal["api", "scoring", "notifications", "ingestion", "database", "monitoring"]
EventType = Literal[
    "prediction_failure",
    "model_failure",
    "notification_failure",
    "database_error",
    "ingestion_error",
    "latency_breach",
    "drift_alert",
]
Severity = Literal["info", "warning", "error", "critical"]

Connection = psycopg.Connection[DictRow]


def connect(database_url: str) -> Connection:
    return psycopg.connect(database_url, row_factory=dict_row, application_name="sews-services")


def set_session_environment(conn: Connection, environment: Environment) -> None:
    """Development databases may score with non-production (demo/synthetic) registry models; the
    prediction gate in the database only honours this setting for non-production statuses."""
    if environment == "development":
        conn.execute("select set_config('sews.environment', 'development', false)")


def record_system_event(
    conn: Connection,
    component: Component,
    event_type: EventType,
    severity: Severity,
    details: dict[str, Any],
    institution_id: str | None = None,
) -> None:
    """Aggregate, non-identifying details only (the database rejects identity keys)."""
    conn.execute(
        "insert into public.system_events (component, event_type, severity, institution_id, details) "
        "values (%s, %s, %s, %s, %s::jsonb)",
        (component, event_type, severity, institution_id, json.dumps(details)),
    )
