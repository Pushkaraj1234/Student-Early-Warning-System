"""Services test fixtures. ALL DATA IS SYNTHETIC (supabase/seed.sql plus rows created by tests).

Integration tests run against a throwaway database on the LOCAL test cluster (loopback only),
rebuilt per test module from the Supabase shim, every migration and the synthetic seed.
Environment: PGBIN (psql directory), PGHOST (localhost), PGPORT (54330), PGUSER (postgres).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from sews_services.config import Settings
from sews_services.db import Connection, connect
from sews_services.features.institutional import FEATURE_VERSION, FEATURES

from ml.models.artifact import ModelArtifact, ModelMetadata, RiskThresholds
from ml.models.factory import build_pipeline
from ml.models.registry import ModelRegistry

ROOT = Path(__file__).resolve().parents[2]
PGBIN = Path(os.environ.get("PGBIN", "C:/Program Files/PostgreSQL/18/bin"))
PGHOST = os.environ.get("PGHOST", "localhost")
PGPORT = os.environ.get("PGPORT", "54330")
PGUSER = os.environ.get("PGUSER", "postgres")
DB_NAME = "sews_services_test"

INSTITUTION = "a0000000-0000-4000-8000-000000000001"
ALPHA = "a0000000-0000-4000-8000-000000000041"
BETA = "a0000000-0000-4000-8000-000000000042"
GAMMA = "a0000000-0000-4000-8000-000000000043"
CSV_INTEGRATION = "a0000000-0000-4000-8000-000000000051"


def _psql(*args: str, db: str = "postgres") -> None:
    subprocess.run(  # noqa: S603 - fixed local binary and arguments
        [
            str(PGBIN / "psql"),
            "-X",
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            db,
            *args,
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "PGOPTIONS": "-c client_min_messages=warning"},
    )


def rebuild_database() -> str:
    _psql("-c", f"drop database if exists {DB_NAME} with (force);", "-c", f"create database {DB_NAME};")
    _psql("-c", f'alter database {DB_NAME} set search_path = "$user", public, extensions;')
    files = [
        ROOT / "scripts/db/supabase_local_shim.sql",
        *sorted((ROOT / "supabase/migrations").glob("*.sql")),
        ROOT / "supabase/seed.sql",
    ]
    for f in files:
        _psql("--single-transaction", "-f", str(f), db=DB_NAME)
    return f"postgresql://{PGUSER}@{PGHOST}:{PGPORT}/{DB_NAME}"


@pytest.fixture(scope="module")
def db_url() -> str:
    return rebuild_database()


@pytest.fixture
def conn(db_url: str) -> Iterator[Connection]:
    connection = connect(db_url)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def dev_settings(db_url: str, registry_root: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "development",
        "database_url": db_url,
        "model_registry_root": registry_root,
        "allowed_provenance": frozenset({"benchmark", "synthetic", "institutional"}),
        "jwt_secret": "test-secret-for-local-tests-only-0123456789",
    }
    values.update(overrides)
    return Settings(**values)


def train_institutional_model(root: Path, version: str = "test-inst-lr-1", seed: int = 0) -> ModelArtifact:
    """A tiny logistic regression on SYNTHETIC institutional feature vectors (not a real model)."""
    rng = np.random.default_rng(seed)
    n = 400
    ranges = {  # plausible value ranges so the synthetic model sees realistic scales
        "attendance_trend": (-0.2, 0.2),
        "consecutive_absences": (0, 10),
        "assessments_due_to_date": (0, 10),
        "submissions_last_30d": (0, 10),
        "mean_released_score_pct": (0, 100),
        "last_released_score_pct": (0, 100),
        "score_trend_per_30d": (-30, 30),
        "engagement_events_last_7d": (0, 30),
        "engagement_events_last_14d": (0, 60),
        "engagement_events_last_30d": (0, 120),
        "engagement_active_days_14d": (0, 14),
        "engagement_trend": (-5, 5),
        "quiz_attempts_last_30d": (0, 20),
        "days_since_last_engagement": (0, 30),
        "prior_term_gpa": (4, 10),
    }
    X = pd.DataFrame({f: rng.uniform(*ranges.get(f, (0.0, 1.0)), n) for f in FEATURES}, columns=list(FEATURES))
    X.loc[rng.uniform(size=n) < 0.2, "prior_term_gpa"] = np.nan
    y = (1.0 - X["attendance_rate_last_14d"] + rng.normal(0, 0.15, n) > 0.35).astype(np.int64).to_numpy()
    pipe = build_pipeline("logistic_regression", "none", y_train=y, seed=seed).fit(X, y)
    z = pipe.named_steps["scale"].transform(pipe.named_steps["impute"].transform(X))
    meta = ModelMetadata(
        model_version=version,
        model_name="logistic_regression",
        feature_version=FEATURE_VERSION,
        feature_names=FEATURES,
        dataset_name="SYNTHETIC-INSTITUTIONAL",
        dataset_version="synthetic-inst-0",
        data_provenance="synthetic",
        cutoff_day=1,
        target="academic",
        target_definition="synthetic test target",
        training_timestamp=datetime(2026, 9, 1, tzinfo=UTC),
        split={"train": ["synthetic"], "validation": ["synthetic"], "test": ["synthetic"]},
        imbalance_strategy="none",
        hyperparameters={},
        calibration_method="none",
        risk_thresholds=RiskThresholds(watch=0.3, elevated=0.5, high=0.7),
        decision_threshold=0.5,
        explanation_units="log-odds (uncalibrated model)",
        metrics={"validation": {"pr_auc": 0.9}, "test": {"pr_auc": 0.9}},
        random_seed=seed,
        library_versions={},
        git_commit=None,
    )
    artifact = ModelArtifact(
        pipeline=pipe,
        calibrator=pipe,
        metadata=meta,
        background_means=np.asarray(z, dtype=np.float64).mean(axis=0),
    )
    artifact.save(root / version)
    return artifact


def register(conn: Connection, artifact: ModelArtifact, *, status: str = "development") -> str:
    m = artifact.metadata
    row = conn.execute(
        """insert into public.model_registry
             (model_name, version, target, dataset_version, feature_version, data_provenance, training_timestamp,
              validation_metrics, artifact_sha256)
           values ('test-inst', %s, %s, %s, %s, %s, %s, '{"validation": {"pr_auc": 0.9}}'::jsonb, %s)
           returning id::text as id""",
        (
            m.model_version,
            m.target,
            m.dataset_version,
            m.feature_version,
            m.data_provenance,
            m.training_timestamp,
            m.model_sha256,
        ),
    ).fetchone()
    assert row is not None
    if status != "development":
        conn.execute("update public.model_registry set status = %s where id = %s", (status, row["id"]))
    conn.commit()
    return str(row["id"])


@pytest.fixture(scope="module")
def registry_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("registry")


@pytest.fixture(scope="module")
def registry(registry_root: Path) -> ModelRegistry:
    return ModelRegistry(registry_root)
