"""Scoring job: institutional as-of features -> registered model -> stored prediction + factors.

Safety checks, in order (any failure stops the run before a single prediction is written):
  1. A model-registry row in status 'production' for the target and institution (or a global one).
     Development databases may name a non-production registry version explicitly; the database gate
     accepts it only when the session says ``sews.environment = development``.
  2. The artifact's SHA-256 equals the registry row's ``artifact_sha256`` (the file that was
     approved is the file that scores).
  3. The artifact's training provenance is allowed in this environment (production: institutional).
  4. The artifact's feature version equals the institutional feature builder's version.
  5. The temporal leakage guard passes for the scoring timestamp.
Then, per student (each in its own savepoint): ML subject id, feature snapshot (no identity keys),
inference with the ML subject id (the model never sees who the student is), prediction + factors.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from ml.inference.errors import InferenceError
from ml.inference.service import InferenceService
from ml.models.artifact import ArtifactError
from ml.models.registry import ModelRegistry
from sews_services.config import Settings
from sews_services.db import Connection, record_system_event, set_session_environment
from sews_services.features.institutional import (
    DEFAULT_TZ,
    FEATURE_VERSION,
    assert_no_future_leakage,
    build_features,
    load_institutional_data,
)


class ScoringRefusedError(RuntimeError):
    """The run was refused before any prediction was written (reason in the message, no identifiers)."""


@dataclass
class ScoringStats:
    model_version: str
    students: int = 0
    scored: int = 0
    already_scored: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "students": self.students,
            "scored": self.scored,
            "already_scored": self.already_scored,
            "failed": self.failed,
        }


def resolve_registry_model(
    conn: Connection, settings: Settings, *, institution_id: str, target: str, model_version: str | None
) -> dict[str, Any]:
    if model_version is None:
        row = conn.execute(
            """select * from public.model_registry
               where target = %s and status = 'production' and (institution_id = %s or institution_id is null)
               order by institution_id nulls last limit 1""",
            (target, institution_id),
        ).fetchone()
        if row is None:
            raise ScoringRefusedError("no production model is registered for this target and institution")
        return dict(row)
    row = conn.execute("select * from public.model_registry where version = %s", (model_version,)).fetchone()
    if row is None:
        raise ScoringRefusedError("the requested model version is not registered")
    if row["status"] != "production" and not (
        settings.environment == "development" and row["status"] in ("development", "validated", "staging")
    ):
        raise ScoringRefusedError("the requested model is not approved for live predictions")
    if row["target"] != target:
        raise ScoringRefusedError("the requested model predicts a different target")
    if row["institution_id"] is not None and str(row["institution_id"]) != institution_id:
        raise ScoringRefusedError("the requested model belongs to another institution")
    return dict(row)


def _json_features(values: dict[str, float]) -> str:
    return json.dumps({k: (None if math.isnan(v) else v) for k, v in values.items()})


def score_institution(
    conn: Connection,
    settings: Settings,
    registry: ModelRegistry,
    *,
    institution_id: str,
    as_of: datetime,
    target: str = "academic",
    model_version: str | None = None,
    tz: ZoneInfo = DEFAULT_TZ,
) -> ScoringStats:
    set_session_environment(conn, settings.environment)
    row = resolve_registry_model(
        conn, settings, institution_id=institution_id, target=target, model_version=model_version
    )
    version = row["version"]
    try:
        artifact = registry.load(version)
    except (ArtifactError, LookupError, ValueError) as exc:
        raise ScoringRefusedError("the registered model artifact could not be loaded or verified") from exc
    meta = artifact.metadata
    if not row["artifact_sha256"] or row["artifact_sha256"] != meta.model_sha256:
        raise ScoringRefusedError("the artifact does not match the hash recorded in the model registry")
    if meta.data_provenance not in settings.allowed_provenance:
        raise ScoringRefusedError("the model's training-data provenance is not allowed in this environment")
    if meta.feature_version != FEATURE_VERSION:
        raise ScoringRefusedError("the model was not trained on the institutional feature set")

    data = load_institutional_data(conn, institution_id, as_of, tz)
    assert_no_future_leakage(data, as_of, tz)  # raises TemporalLeakageError: nothing is written
    features = build_features(data, as_of, tz)
    missing = [f for f in meta.feature_names if f not in features.columns]
    if missing:
        raise ScoringRefusedError("the feature builder does not produce every model feature")

    service = InferenceService(registry, allowed_provenance=settings.allowed_provenance)
    prediction_date = as_of.astimezone(tz).date()
    stats = ScoringStats(model_version=version, students=len(features))
    try:
        _score_rows(conn, service, features, meta, row, version, target, as_of, prediction_date, stats)
    except psycopg.Error:
        conn.rollback()  # nothing from this run is kept
        record_system_event(conn, "scoring", "database_error", "error", stats.as_dict(), institution_id)
        conn.commit()
        raise
    if stats.failed:
        record_system_event(conn, "scoring", "prediction_failure", "error", stats.as_dict(), institution_id)
    conn.commit()
    return stats


def _score_rows(
    conn: Connection,
    service: InferenceService,
    features: Any,
    meta: Any,
    row: dict[str, Any],
    version: str,
    target: str,
    as_of: datetime,
    prediction_date: Any,
    stats: ScoringStats,
) -> None:
    for student_id, values in features.iterrows():
        try:
            with conn.transaction():
                ml_id = conn.execute("select private.ml_subject_id_for(%s) as id", (student_id,)).fetchone()
                if ml_id is None:
                    raise ScoringRefusedError("could not obtain an ML subject id")
                vector = {name: float(values[name]) for name in meta.feature_names}
                conn.execute(
                    """insert into private.feature_snapshots (ml_subject_id, as_of, feature_version, features)
                       values (%s, %s, %s, %s::jsonb) on conflict do nothing""",
                    (ml_id["id"], as_of, meta.feature_version, _json_features(vector)),
                )
                response = service.predict(
                    {
                        "student_id": str(ml_id["id"]),
                        "prediction_date": prediction_date.isoformat(),
                        "features": {k: (None if math.isnan(v) else v) for k, v in vector.items()},
                        "model_version": version,
                        "top_k": 5,
                    }
                )
                inserted = conn.execute(
                    """insert into public.risk_predictions
                         (student_id, prediction_date, risk_probability, risk_level, model_version, feature_version,
                          dataset_version, data_provenance, target, model_registry_id, scored_at)
                       values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       on conflict (student_id, prediction_date, model_version, target) do nothing
                       returning id""",
                    (
                        student_id,
                        prediction_date,
                        round(response.risk_probability, 5),
                        response.risk_level,
                        version,
                        meta.feature_version,
                        meta.dataset_version,
                        meta.data_provenance,
                        target,
                        row["id"],
                        as_of,
                    ),
                ).fetchone()
                if inserted is None:
                    stats.already_scored += 1
                    continue
                for f in response.top_factors:
                    conn.execute(
                        """insert into public.risk_factors
                             (prediction_id, rank, feature, feature_value, contribution, direction)
                           values (%s, %s, %s, %s, %s, %s)""",
                        (inserted["id"], f.rank, f.feature, f.feature_value, f.contribution, f.direction),
                    )
                stats.scored += 1
        except InferenceError:
            stats.failed += 1
