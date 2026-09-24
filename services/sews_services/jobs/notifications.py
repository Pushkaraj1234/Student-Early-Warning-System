"""Push-delivery worker for public.notifications.

A push message carries ONLY the notification id and its generic ``preview`` (one of three fixed,
non-sensitive strings enforced by the database). Titles and bodies stay in the app behind RLS.

Delivery state machine (columns delivery_status / delivery_attempts / last_delivery_error / delivered_at):
    pending --sent--> sent (delivered_at set)
    pending --no device token / invalid token--> skipped
    pending --provider unavailable / rate limited--> pending (retried) ... after MAX_ATTEMPTS -> failed
Error values come from a fixed list (never provider error text, which may echo personal data).

No push provider is configured in this repository (no FCM/APNs credentials, no device-token store),
so the default provider reports ``no_device_token`` and notifications are marked ``skipped``; they
remain visible in the app's notification list and through Realtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from sews_services.db import Connection, record_system_event

DeliveryError = Literal["no_device_token", "provider_unavailable", "invalid_token", "rate_limited", "unknown"]
RETRYABLE: frozenset[str] = frozenset({"provider_unavailable", "rate_limited", "unknown"})
MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class PushMessage:
    notification_id: str
    recipient_id: str
    preview: str


@dataclass(frozen=True)
class DeliveryResult:
    sent: bool
    error: DeliveryError | None = None


class PushProvider(Protocol):
    def send(self, message: PushMessage) -> DeliveryResult: ...


class NoPushProvider:
    """Default: no push channel is configured."""

    def send(self, message: PushMessage) -> DeliveryResult:
        return DeliveryResult(sent=False, error="no_device_token")


@dataclass
class DeliveryStats:
    processed: int = 0
    sent: int = 0
    skipped: int = 0
    retrying: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "processed": self.processed,
            "sent": self.sent,
            "skipped": self.skipped,
            "retrying": self.retrying,
            "failed": self.failed,
        }


def deliver_pending(conn: Connection, provider: PushProvider, *, batch_size: int = 100) -> DeliveryStats:
    stats = DeliveryStats()
    rows = conn.execute(
        """select id::text as id, recipient_id::text as recipient_id, preview, delivery_attempts
           from public.notifications where delivery_status = 'pending'
           order by created_at limit %s for update skip locked""",
        (batch_size,),
    ).fetchall()
    for r in rows:
        stats.processed += 1
        try:
            result = provider.send(PushMessage(r["id"], r["recipient_id"], r["preview"]))
        except Exception:  # a provider bug must not stop the batch or leak details
            result = DeliveryResult(sent=False, error="unknown")
        attempts = r["delivery_attempts"] + 1
        if result.sent:
            status, error = "sent", None
            stats.sent += 1
        elif result.error in RETRYABLE and attempts < MAX_ATTEMPTS:
            status, error = "pending", result.error
            stats.retrying += 1
        elif result.error in RETRYABLE:
            status, error = "failed", result.error
            stats.failed += 1
        else:
            status, error = "skipped", result.error or "unknown"
            stats.skipped += 1
        conn.execute(
            """update public.notifications
               set delivery_status = %s, delivery_attempts = %s, last_delivery_error = %s,
                   delivered_at = case when %s = 'sent' then now() else null end
               where id = %s""",
            (status, attempts, error, status, r["id"]),
        )
    if stats.failed:
        record_system_event(conn, "notifications", "notification_failure", "warning", stats.as_dict())
    conn.commit()
    return stats
