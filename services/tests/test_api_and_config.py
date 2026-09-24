"""Inference API (auth, rate limits, validation, errors, logging) and configuration safety."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sews_services.api.app import create_app
from sews_services.config import ConfigError, Settings, load_settings
from sews_services.features.institutional import FEATURES

from ml.explainability.audiences import FEATURE_TEXT
from ml.models.registry import ModelRegistry
from tests.conftest import train_institutional_model

SECRET = "test-secret-for-local-tests-only-0123456789"
LOCAL_DB = "postgresql://postgres@localhost:54330/sews_services_test"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _settings(root: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "development",
        "database_url": LOCAL_DB,
        "model_registry_root": root,
        "allowed_provenance": frozenset({"synthetic"}),
        "jwt_secret": SECRET,
        "rate_limit_per_minute": 60,
    }
    values.update(overrides)
    return Settings(**values)


def _token(role: str = "service_role", *, secret: str = SECRET, exp_in: int = 300, **claims: Any) -> str:
    return jwt.encode({"role": role, "exp": int(time.time()) + exp_in, **claims}, secret, algorithm="HS256")


def _auth(token: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token or _token()}"}


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("api-registry")
    artifact = train_institutional_model(path, version="api-test-lr-1")
    ModelRegistry(path).set_active(artifact.metadata.model_version)
    return path


def _payload(student_id: str = "syn-subject-1", **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "student_id": student_id,
        "prediction_date": "2026-09-24",
        "features": {f: 0.5 for f in FEATURES},
        "top_k": 3,
    }
    body.update(overrides)
    return body


@pytest.fixture
def client(root: Path) -> TestClient:
    return TestClient(create_app(_settings(root)))


# ------------------------------------------------------------------ public endpoints
def test_health_and_version_need_no_auth(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/v1/version").json() == {"api_version": "1.0.0"}
    response = client.get("/health")
    assert response.headers["cache-control"] == "no-store" and response.headers["x-content-type-options"] == "nosniff"


# ------------------------------------------------------------------ authentication
@pytest.mark.parametrize(
    ("headers", "status", "code"),
    [
        ({}, 401, "missing_token"),
        ({"Authorization": "Basic abc"}, 401, "missing_token"),
        ({"Authorization": "Bearer not-a-jwt"}, 401, "invalid_token"),
        (_auth(_token(exp_in=-120)), 401, "token_expired"),
        (_auth(_token(secret="another-secret-that-is-long-enough-000")), 401, "invalid_token"),
        (_auth(_token(role="authenticated")), 403, "forbidden"),
        (_auth(_token(role="anon")), 403, "forbidden"),
    ],
)
def test_authentication_failures(client: TestClient, headers: dict[str, str], status: int, code: str) -> None:
    response = client.post("/v1/predictions", json=_payload(), headers=headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_unsigned_alg_none_token_is_refused(client: TestClient) -> None:
    unsigned = jwt.encode({"role": "service_role", "exp": int(time.time()) + 300}, key=None, algorithm="none")  # type: ignore[arg-type]
    response = client.post("/v1/predictions", json=_payload(), headers=_auth(unsigned))
    assert response.status_code == 401


def test_token_without_expiry_is_refused(client: TestClient) -> None:
    token = jwt.encode({"role": "service_role"}, SECRET, algorithm="HS256")
    assert client.post("/v1/predictions", json=_payload(), headers=_auth(token)).status_code == 401


def test_missing_auth_configuration_fails_closed(root: Path) -> None:
    client = TestClient(create_app(_settings(root, jwt_secret=None)))
    response = client.post("/v1/predictions", json=_payload(), headers=_auth())
    assert response.status_code == 503 and response.json()["error"]["code"] == "auth_not_configured"


# ------------------------------------------------------------------ predictions
def test_valid_prediction_follows_the_contract(client: TestClient) -> None:
    response = client.post("/v1/predictions", json=_payload(), headers=_auth())
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["api_version"] == "1.0.0" and data["target"] == "academic"
    assert data["model_version"] == "api-test-lr-1" and 0 <= data["risk_probability"] <= 1
    assert 1 <= len(data["top_factors"]) <= 3
    assert response.headers["x-request-id"]


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        (_payload(features={"attendance_rate_last_14d": 0.5}), 422, "missing_features"),
        (_payload(features={**{f: 0.5 for f in FEATURES}, "full_name": 1.0}), 422, "unknown_features"),
        (_payload(features={**{f: 0.5 for f in FEATURES}, "consecutive_absences": "3"}), 422, "invalid_type"),
        (_payload(model_version="no-such-model"), 404, "model_not_found"),
        (_payload(model_version="../../etc/passwd"), 422, "invalid_model_version"),
        (_payload(extra_field=1), 422, "invalid_request"),
        ([1, 2, 3], 422, "invalid_request"),
    ],
)
def test_prediction_errors_have_stable_codes(client: TestClient, body: Any, status: int, code: str) -> None:
    response = client.post("/v1/predictions", json=body, headers=_auth())
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert "Traceback" not in response.text and "0.5" not in str(error)  # no stack traces, no input values


def test_non_finite_json_numbers_are_rejected(client: TestClient) -> None:
    raw = '{"student_id": "s", "prediction_date": "2026-09-24", "features": {'
    raw += ", ".join(f'"{f}": NaN' if f == "attendance_rate_last_14d" else f'"{f}": 0.5' for f in FEATURES) + "}}"
    response = client.post("/v1/predictions", content=raw, headers={**_auth(), "Content-Type": "application/json"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "non_finite_value"


def test_malformed_json_wrong_type_and_oversized_bodies(client: TestClient) -> None:
    headers = {**_auth(), "Content-Type": "application/json"}
    assert client.post("/v1/predictions", content="{not json", headers=headers).status_code == 422
    text_headers = {**_auth(), "Content-Type": "text/plain"}
    assert client.post("/v1/predictions", content="{}", headers=text_headers).status_code == 415
    big = "x" * 20_000
    response = client.post("/v1/predictions", content=big, headers=headers)
    assert response.status_code == 413 and response.json()["error"]["code"] == "payload_too_large"


def test_outside_development_student_id_must_be_an_ml_subject_id(root: Path) -> None:
    client = TestClient(create_app(_settings(root, environment="staging")))
    bad = client.post("/v1/predictions", json=_payload(student_id="SYN2025001"), headers=_auth())
    assert bad.status_code == 422 and "ML subject id" in bad.json()["error"]["message"]
    good = client.post("/v1/predictions", json=_payload(student_id=str(uuid.uuid4())), headers=_auth())
    assert good.status_code == 200


def test_openapi_docs_only_in_development(root: Path) -> None:
    assert TestClient(create_app(_settings(root))).get("/openapi.json").status_code == 200
    staging = TestClient(create_app(_settings(root, environment="staging")))
    assert staging.get("/openapi.json").status_code == 404 and staging.get("/docs").status_code == 404


# ------------------------------------------------------------------ rate limiting
def test_rate_limit_per_caller_with_retry_after(root: Path) -> None:
    clock = FakeClock()
    client = TestClient(create_app(_settings(root, rate_limit_per_minute=3), clock=clock))
    a, b = _auth(_token(sub="job-a")), _auth(_token(sub="job-b"))
    codes = [client.post("/v1/predictions", json=_payload(), headers=a).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    limited = client.post("/v1/predictions", json=_payload(), headers=a)
    assert limited.json()["error"]["code"] == "rate_limited" and int(limited.headers["retry-after"]) >= 1
    assert client.post("/v1/predictions", json=_payload(), headers=b).status_code == 200  # separate bucket
    clock.now += 20  # one token refills every 20 s at 3/min
    assert client.post("/v1/predictions", json=_payload(), headers=a).status_code == 200


# ------------------------------------------------------------------ observability
def test_access_logs_and_metrics_contain_no_sensitive_data(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    token = _token()
    with caplog.at_level(logging.INFO, logger="sews.api"):
        client.post("/v1/predictions", json=_payload(student_id="very-identifying-subject"), headers=_auth(token))
        client.post("/v1/predictions", json=_payload(features={"attendance_rate_last_14d": 0.123456}), headers=_auth())
    text = " ".join(r.getMessage() for r in caplog.records)
    assert '"route": "/v1/predictions"' in text and "latency_ms" in text
    for secret_bit in ("very-identifying-subject", "0.123456", token, "attendance_rate_last_14d"):
        assert secret_bit not in text
    assert client.get("/v1/metrics").status_code == 401
    metrics = client.get("/v1/metrics", headers=_auth()).json()
    assert metrics["prediction_latency_ms"]["n"] >= 1
    assert "very-identifying-subject" not in str(metrics)


def test_every_institutional_feature_has_explanation_text() -> None:
    assert set(FEATURES) <= set(FEATURE_TEXT)


# ------------------------------------------------------------------ configuration safety
BASE_ENV = {"SEWS_ENV": "development", "SEWS_DATABASE_URL": LOCAL_DB}


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://postgres:x@db.rzekfmfuskknadrchkhg.supabase.co:5432/postgres",
        "postgresql://postgres.rzekfmfuskknadrchkhg:x@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
        "postgresql://user@10.0.0.5:5432/sews",
    ],
)
def test_development_refuses_any_hosted_database(url: str) -> None:
    with pytest.raises(ConfigError, match="local database"):
        load_settings({**BASE_ENV, "SEWS_DATABASE_URL": url})


def test_development_on_localhost_is_allowed_and_secrets_are_hidden() -> None:
    settings = load_settings({**BASE_ENV, "SEWS_JWT_SECRET": SECRET})
    assert settings.environment == "development"
    assert SECRET not in repr(settings) and "54330" not in repr(settings)


def test_staging_and_production_rules() -> None:
    hosted = "postgresql://postgres:x@db.stagingref000000000000.supabase.co:5432/postgres"
    prod = "postgresql://postgres:x@db.rzekfmfuskknadrchkhg.supabase.co:5432/postgres"
    common = {"SEWS_JWT_SECRET": SECRET, "SEWS_PRODUCTION_PROJECT_REF": "rzekfmfuskknadrchkhg"}
    assert load_settings({"SEWS_ENV": "staging", "SEWS_DATABASE_URL": hosted, **common}).environment == "staging"
    with pytest.raises(ConfigError, match="production database"):
        load_settings({"SEWS_ENV": "staging", "SEWS_DATABASE_URL": prod, **common})
    with pytest.raises(ConfigError, match="hosted database"):
        load_settings({"SEWS_ENV": "staging", "SEWS_DATABASE_URL": LOCAL_DB, **common})
    production = load_settings({"SEWS_ENV": "production", "SEWS_DATABASE_URL": prod, **common})
    assert production.allowed_provenance == frozenset({"institutional"})
    with pytest.raises(ConfigError, match="institutional"):
        load_settings(
            {
                "SEWS_ENV": "production",
                "SEWS_DATABASE_URL": prod,
                "SEWS_ALLOWED_PROVENANCE": "benchmark",
                **common,
            }
        )
    with pytest.raises(ConfigError, match="local database"):
        load_settings({"SEWS_ENV": "production", "SEWS_DATABASE_URL": LOCAL_DB, **common})


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"SEWS_ENV": "prod", "SEWS_DATABASE_URL": LOCAL_DB}, "SEWS_ENV"),
        ({"SEWS_ENV": "development"}, "SEWS_DATABASE_URL"),
        ({**BASE_ENV, "SEWS_ALLOWED_PROVENANCE": "made_up"}, "unknown"),
        ({**BASE_ENV, "SEWS_JWT_JWKS_URL": "http://insecure.example.com/jwks"}, "https"),
        ({**BASE_ENV, "SEWS_RATE_LIMIT_PER_MINUTE": "0"}, "out of range"),
        ({"SEWS_ENV": "staging", "SEWS_DATABASE_URL": "postgresql://u@db.stagingref.supabase.co/p"}, "JWT"),
    ],
)
def test_invalid_configuration_is_refused(env: dict[str, str], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_settings(env)
