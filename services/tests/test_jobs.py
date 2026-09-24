"""Backend jobs against the local test database (SYNTHETIC data only):
scoring (model gate, integrity, provenance, feature version, snapshots), recommendations, outcome
measures, monitoring (snapshots, drift alerts) and notification delivery state."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from sews_services.db import Connection, connect, set_session_environment
from sews_services.features.institutional import FEATURES
from sews_services.jobs.monitoring import monitor_window
from sews_services.jobs.notifications import (
    MAX_ATTEMPTS,
    DeliveryResult,
    NoPushProvider,
    PushMessage,
    deliver_pending,
)
from sews_services.jobs.outcomes import compute_outcomes
from sews_services.jobs.recommend import recommend_for_institution
from sews_services.jobs.scoring import ScoringRefusedError, score_institution

from ml.models.artifact import ModelArtifact
from ml.models.registry import ModelRegistry
from tests.conftest import (
    ALPHA,
    BETA,
    GAMMA,
    INSTITUTION,
    dev_settings,
    register,
    train_institutional_model,
)

NOW = datetime.now(UTC)
IDENTITY_KEYS = {
    "full_name",
    "name",
    "email",
    "institutional_email",
    "phone",
    "roll_number",
    "user_id",
    "student_id",
}
PREVIEWS = {
    "You have a new update in SEWS.",
    "You have a new message in SEWS.",
    "A support option is available in SEWS.",
}


@pytest.fixture(scope="module")
def model(db_url: str, registry_root: Path) -> dict[str, Any]:
    artifact = train_institutional_model(registry_root)
    with connect(db_url) as c:
        model_id = register(c, artifact)
    return {"artifact": artifact, "id": model_id, "version": artifact.metadata.model_version}


@pytest.fixture(scope="module")
def scored(db_url: str, registry_root: Path, registry: ModelRegistry, model: dict[str, Any]) -> Any:
    with connect(db_url) as c:
        return score_institution(
            c,
            dev_settings(db_url, registry_root),
            registry,
            institution_id=INSTITUTION,
            as_of=NOW,
            model_version=model["version"],
        )


# ------------------------------------------------------------------ scoring: refusals first
def test_no_production_model_means_no_scoring(
    conn: Connection, db_url: str, registry_root: Path, registry: ModelRegistry, model: dict[str, Any]
) -> None:
    staging = dev_settings(db_url, registry_root, environment="staging")
    with pytest.raises(ScoringRefusedError, match="no production model"):
        score_institution(conn, staging, registry, institution_id=INSTITUTION, as_of=NOW)


def test_development_model_is_refused_outside_development(
    conn: Connection, db_url: str, registry_root: Path, registry: ModelRegistry, model: dict[str, Any]
) -> None:
    staging = dev_settings(db_url, registry_root, environment="staging")
    with pytest.raises(ScoringRefusedError, match="not approved"):
        score_institution(
            conn, staging, registry, institution_id=INSTITUTION, as_of=NOW, model_version=model["version"]
        )


def test_disallowed_provenance_is_refused(
    conn: Connection, db_url: str, registry_root: Path, registry: ModelRegistry, model: dict[str, Any]
) -> None:
    only_institutional = dev_settings(db_url, registry_root, allowed_provenance=frozenset({"institutional"}))
    with pytest.raises(ScoringRefusedError, match="provenance"):
        score_institution(
            conn,
            only_institutional,
            registry,
            institution_id=INSTITUTION,
            as_of=NOW,
            model_version=model["version"],
        )


def test_artifact_hash_must_match_the_registry(
    conn: Connection, db_url: str, registry_root: Path, registry: ModelRegistry
) -> None:
    artifact = train_institutional_model(registry_root, version="test-inst-tampered", seed=1)
    model_id = register(conn, artifact)
    conn.execute("update public.model_registry set artifact_sha256 = %s where id = %s", ("0" * 64, model_id))
    conn.commit()
    with pytest.raises(ScoringRefusedError, match="hash"):
        score_institution(
            conn,
            dev_settings(db_url, registry_root),
            registry,
            institution_id=INSTITUTION,
            as_of=NOW,
            model_version="test-inst-tampered",
        )


def test_model_for_another_feature_set_is_refused(
    conn: Connection, db_url: str, registry_root: Path, registry: ModelRegistry, model: dict[str, Any]
) -> None:
    base: ModelArtifact = model["artifact"]
    meta = base.metadata.model_copy(update={"model_version": "test-oulad-like", "feature_version": "oulad-fs-2.0.0"})
    other = ModelArtifact(
        pipeline=base.pipeline,
        calibrator=base.calibrator,
        metadata=meta,
        background_means=base.background_means,
    )
    other.save(registry_root / "test-oulad-like")
    register(conn, other)
    with pytest.raises(ScoringRefusedError, match="institutional feature set"):
        score_institution(
            conn,
            dev_settings(db_url, registry_root),
            registry,
            institution_id=INSTITUTION,
            as_of=NOW,
            model_version="test-oulad-like",
        )


def test_refused_runs_wrote_nothing(conn: Connection, model: dict[str, Any]) -> None:
    row = conn.execute(
        "select count(*) as n from public.risk_predictions where model_registry_id <> "
        "'a0000000-0000-4000-8000-000000000061'"
    ).fetchone()
    assert row is not None and row["n"] == 0


def test_database_gate_blocks_a_non_production_model_without_the_development_setting(
    conn: Connection, model: dict[str, Any]
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation, match="model_not_approved_for_live_predictions"):
        conn.execute(
            """insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
                 model_version, feature_version, dataset_version, data_provenance, model_registry_id)
               values (%s, current_date, 0.5, 'watch', 'x', 'x', 'x', 'synthetic', %s)""",
            (ALPHA, model["id"]),
        )


# ------------------------------------------------------------------ scoring: success path
def test_scoring_writes_predictions_factors_and_identity_free_snapshots(
    conn: Connection, scored: Any, model: dict[str, Any]
) -> None:
    assert scored.as_dict() == {
        "model_version": model["version"],
        "students": 3,
        "scored": 3,
        "already_scored": 0,
        "failed": 0,
    }
    preds = conn.execute(
        """select id, student_id::text as student_id, model_version, feature_version, target, trajectory,
                  data_provenance
           from public.risk_predictions where model_registry_id = %s""",
        (model["id"],),
    ).fetchall()
    assert {p["student_id"] for p in preds} == {ALPHA, BETA, GAMMA}
    for p in preds:
        assert p["model_version"] == model["version"] and p["feature_version"] == "inst-fs-1.0.0"
        assert p["target"] == "academic" and p["data_provenance"] == "synthetic"
        assert p["trajectory"] == "insufficient_history"
        factors = conn.execute(
            "select rank, feature, direction, contribution from public.risk_factors "
            "where prediction_id = %s order by rank",
            (p["id"],),
        ).fetchall()
        assert 1 <= len(factors) <= 5 and all(f["feature"] in FEATURES for f in factors)
    snaps = conn.execute(
        """select fs.features, m.student_id::text as student_id, fs.ml_subject_id::text as ml_id
           from private.feature_snapshots fs join private.ml_subject_map m using (ml_subject_id)"""
    ).fetchall()
    assert len(snaps) == 3
    for s in snaps:
        assert set(s["features"]) == set(FEATURES)
        assert not IDENTITY_KEYS & set(s["features"])
        assert s["ml_id"] != s["student_id"]  # random ML ids, not institutional ids
        assert s["student_id"] not in json.dumps(s["features"])


def test_rescoring_the_same_day_is_idempotent(
    db_url: str, registry_root: Path, registry: ModelRegistry, model: dict[str, Any], scored: Any
) -> None:
    with connect(db_url) as c:
        again = score_institution(
            c,
            dev_settings(db_url, registry_root),
            registry,
            institution_id=INSTITUTION,
            as_of=NOW,
            model_version=model["version"],
        )
    assert again.scored == 0 and again.already_scored == 3


def test_beta_scores_higher_than_alpha(conn: Connection, scored: Any, model: dict[str, Any]) -> None:
    rows = {
        r["student_id"]: float(r["risk_probability"])
        for r in conn.execute(
            "select student_id::text as student_id, risk_probability from public.risk_predictions "
            "where model_registry_id = %s",
            (model["id"],),
        ).fetchall()
    }
    # the synthetic test model keys on 14-day attendance; the seed gives Beta the lowest attendance
    assert rows[BETA] > rows[ALPHA]


# ------------------------------------------------------------------ recommendations
def test_recommendation_job_stores_reviewable_rule_output_idempotently(conn: Connection, scored: Any) -> None:
    before = conn.execute("select count(*) as n from public.interventions").fetchone()
    stats = recommend_for_institution(conn, institution_id=INSTITUTION, now=NOW)
    assert stats.students == 3 and stats.recommendations >= 1
    rows = conn.execute(
        """select student_id::text as student_id, intervention_type, status, source, created_by, rule_id, reason,
                  priority
           from public.interventions where source = 'model_rule' and rule_id is not null
             and created_at >= now() - interval '1 minute'"""
    ).fetchall()
    assert rows
    for r in rows:
        assert r["status"] == "recommended" and r["created_by"] is None
        assert r["intervention_type"] not in {"wellbeing_referral", "academic_counselling"}
        assert 3 <= len(r["reason"]) <= 500 and r["priority"] in {"low", "medium", "high"}
    beta_types = {r["intervention_type"] for r in rows if r["student_id"] == BETA}
    assert "attendance_follow_up" in beta_types or "attendance_follow_up" in {
        t["intervention_type"]
        for t in conn.execute(
            "select intervention_type from public.interventions where student_id = %s "
            "and status in ('recommended', 'pending', 'accepted')",
            (BETA,),
        ).fetchall()
    }
    open_dupes = conn.execute(
        """select student_id, intervention_type, count(*) from public.interventions
           where status in ('recommended', 'pending', 'accepted')
           group by 1, 2 having count(*) > 1"""
    ).fetchall()
    assert open_dupes == []
    again = recommend_for_institution(conn, institution_id=INSTITUTION, now=NOW)
    assert again.recommendations == 0
    after = conn.execute("select count(*) as n from public.interventions").fetchone()
    assert before is not None and after is not None
    assert after["n"] == before["n"] + stats.recommendations


def test_financial_referral_only_after_an_explicit_checkin(conn: Connection, scored: Any) -> None:
    def has_referral() -> bool:
        row = conn.execute(
            "select count(*) as n from public.interventions where student_id = %s "
            "and intervention_type = 'financial_support_referral'",
            (GAMMA,),
        ).fetchone()
        return row is not None and row["n"] > 0

    recommend_for_institution(conn, institution_id=INSTITUTION, now=NOW)
    assert not has_referral()
    conn.execute(
        "insert into public.student_checkins (student_id, support_needs) values (%s, %s)",
        (GAMMA, ["financial_difficulty"]),
    )
    conn.commit()
    recommend_for_institution(conn, institution_id=INSTITUTION, now=datetime.now(UTC))
    assert has_referral()


# ------------------------------------------------------------------ outcomes
def test_outcome_measures_are_descriptive_windows(conn: Connection) -> None:
    row = conn.execute(
        """insert into public.interventions (student_id, intervention_type, status, source, reason)
           values (%s, 'peer_tutoring', 'pending', 'admin', 'Synthetic outcome test.') returning id""",
        (BETA,),
    ).fetchone()
    assert row is not None
    conn.execute("update public.interventions set status = 'accepted' where id = %s", (row["id"],))
    conn.execute(
        "update public.interventions set status = 'completed', outcome = 'not_assessed' where id = %s",
        (row["id"],),
    )
    conn.commit()
    early = compute_outcomes(conn, now=NOW)
    assert early.not_yet_due >= 1
    later = NOW + timedelta(days=60)
    stats = compute_outcomes(conn, now=later)
    assert stats.measures_written >= 4
    measures = {
        m["indicator"]: m
        for m in conn.execute(
            "select * from public.intervention_outcome_measures where intervention_id = %s", (row["id"],)
        ).fetchall()
    }
    assert set(measures) == {
        "attendance_rate",
        "assignment_completion_rate",
        "mean_score_pct",
        "risk_probability",
    }
    att = measures["attendance_rate"]
    assert att["baseline_value"] is not None  # the seed has attendance in the 28 days before the offer
    assert att["followup_value"] is None  # nothing recorded after completion: NULL, never imputed
    assert att["followup_start"] > att["baseline_end"]
    assert compute_outcomes(conn, now=later).measures_written == 0  # idempotent


# ------------------------------------------------------------------ monitoring
def test_monitoring_snapshot_and_prediction_drift_alert(conn: Connection, scored: Any, model: dict[str, Any]) -> None:
    today = NOW.date()
    reference_day = date(2026, 8, 3)
    set_session_environment(conn, "development")
    for sid in (ALPHA, BETA, GAMMA):
        conn.execute(
            """insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
                 model_version, feature_version, dataset_version, data_provenance, model_registry_id)
               values (%s, %s, 0.01, 'stable', 'x', 'x', 'x', 'synthetic', %s)""",
            (sid, reference_day, model["id"]),
        )
    conn.commit()
    result = monitor_window(
        conn, model_registry_id=model["id"], window=(today, today), reference=(reference_day, reference_day)
    )
    assert result.snapshot_id is not None and result.n_predictions == 3
    assert any(a.alert_type == "prediction_drift" and a.severity == "critical" for a in result.alerts)
    snap = conn.execute(
        "select * from public.model_monitoring_snapshots where id = %s", (result.snapshot_id,)
    ).fetchone()
    assert snap is not None
    assert set(snap["feature_stats"]) == set(FEATURES)
    assert not IDENTITY_KEYS & set(snap["feature_stats"]) and snap["labels_available"] == 0
    stored = conn.execute(
        "select alert_type, status from public.drift_alerts where monitoring_snapshot_id = %s",
        (result.snapshot_id,),
    ).fetchall()
    assert len(stored) == len(result.alerts) and all(a["status"] == "open" for a in stored)
    event = conn.execute(
        "select details from public.system_events where component = 'monitoring' order by occurred_at desc limit 1"
    ).fetchone()
    assert event is not None and set(event["details"]) == {"alerts", "critical", "window_end"}
    repeat = monitor_window(
        conn, model_registry_id=model["id"], window=(today, today), reference=(reference_day, reference_day)
    )
    assert repeat.snapshot_id is None and repeat.alerts == []  # a window is monitored once


def test_monitoring_an_empty_window_writes_nothing(conn: Connection, model: dict[str, Any]) -> None:
    result = monitor_window(conn, model_registry_id=model["id"], window=(date(2020, 1, 1), date(2020, 1, 7)))
    assert result.snapshot_id is None and result.n_predictions == 0


# ------------------------------------------------------------------ notifications
def _recipient(conn: Connection) -> str:
    conn.execute(
        """insert into auth.users (id, email, email_confirmed_at, raw_user_meta_data, raw_app_meta_data, aud, role)
           values ('c0000000-0000-4000-8000-000000000001', 'notify.test@synthetic.example.com', now(), '{}', '{}',
                   'authenticated', 'authenticated') on conflict do nothing"""
    )
    conn.commit()
    return "c0000000-0000-4000-8000-000000000001"


def _notify(conn: Connection, recipient: str, n: int = 1) -> list[str]:
    ids = []
    for _ in range(n):
        row = conn.execute(
            """insert into public.notifications (recipient_id, notification_type, title, body, preview)
               values (%s, 'system', 'Private title', 'Private body with details', 'You have a new update in SEWS.')
               returning id::text as id""",
            (recipient,),
        ).fetchone()
        assert row is not None
        ids.append(row["id"])
    conn.commit()
    return ids


class RecordingProvider:
    def __init__(self, result: DeliveryResult) -> None:
        self.result = result
        self.messages: list[PushMessage] = []

    def send(self, message: PushMessage) -> DeliveryResult:
        self.messages.append(message)
        return self.result


def test_default_provider_marks_notifications_skipped(conn: Connection) -> None:
    ids = _notify(conn, _recipient(conn), n=2)
    stats = deliver_pending(conn, NoPushProvider(), batch_size=1000)
    assert stats.processed >= 2 and stats.skipped == stats.processed
    for nid in ids:
        r = conn.execute("select * from public.notifications where id = %s", (nid,)).fetchone()
        assert r is not None and r["delivery_status"] == "skipped" and r["last_delivery_error"] == "no_device_token"
        assert r["delivery_attempts"] == 1 and r["delivered_at"] is None
    assert deliver_pending(conn, NoPushProvider()).processed == 0  # skipped rows are not retried


def test_successful_delivery_sends_only_the_generic_preview(conn: Connection) -> None:
    (nid,) = _notify(conn, _recipient(conn))
    provider = RecordingProvider(DeliveryResult(sent=True))
    assert deliver_pending(conn, provider).sent == 1
    (message,) = provider.messages
    assert message.preview in PREVIEWS and "Private" not in repr(message)
    row = conn.execute("select * from public.notifications where id = %s", (nid,)).fetchone()
    assert row is not None and row["delivery_status"] == "sent" and row["delivered_at"] is not None


def test_retryable_failures_retry_then_fail(conn: Connection) -> None:
    (nid,) = _notify(conn, _recipient(conn))
    provider = RecordingProvider(DeliveryResult(sent=False, error="provider_unavailable"))
    for attempt in range(1, MAX_ATTEMPTS + 1):
        deliver_pending(conn, provider)
        row = conn.execute("select * from public.notifications where id = %s", (nid,)).fetchone()
        assert row is not None and row["delivery_attempts"] == attempt
        assert row["delivery_status"] == ("pending" if attempt < MAX_ATTEMPTS else "failed")
        assert row["last_delivery_error"] == "provider_unavailable" and row["delivered_at"] is None
    event = conn.execute(
        "select details from public.system_events where component = 'notifications' order by occurred_at desc limit 1"
    ).fetchone()
    assert event is not None and event["details"]["failed"] == 1


def test_provider_exception_is_contained(conn: Connection) -> None:
    (nid,) = _notify(conn, _recipient(conn))

    class Broken:
        def send(self, message: PushMessage) -> DeliveryResult:
            raise RuntimeError("provider said: token for notify.test@synthetic.example.com rejected")

    deliver_pending(conn, Broken())
    row = conn.execute("select * from public.notifications where id = %s", (nid,)).fetchone()
    assert row is not None and row["last_delivery_error"] == "unknown" and row["delivery_status"] == "pending"
