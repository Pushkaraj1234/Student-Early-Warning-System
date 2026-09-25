"""Service settings, read from environment variables (or the platform's secret store).

Secrets are never logged, printed or written to files: ``Settings.__repr__`` hides them.

Environment separation (docs/architecture/environments.md):
  development  database must be on a loopback host (local Supabase / local Postgres). A development
               process can therefore never reach a hosted (staging or production) database.
  staging      hosted database that is NOT the production project.
  production   hosted production database; only models trained on institutional data may score.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

Environment = Literal["development", "staging", "production"]
ENVIRONMENTS: tuple[Environment, ...] = ("development", "staging", "production")
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class ConfigError(ValueError):
    """Invalid or unsafe configuration. Messages never include secret values."""


@dataclass(frozen=True)
class Settings:
    environment: Environment
    database_url: str = field(repr=False)
    model_registry_root: Path
    allowed_provenance: frozenset[str]
    jwt_secret: str | None = field(default=None, repr=False)
    jwt_jwks_url: str | None = None
    jwt_audience: str | None = None
    api_allowed_roles: frozenset[str] = frozenset({"service_role"})
    rate_limit_per_minute: int = 60
    max_body_bytes: int = 16_384


def database_host(database_url: str) -> str:
    try:
        host = urlsplit(database_url).hostname
    except ValueError as exc:
        raise ConfigError("SEWS_DATABASE_URL is not a valid URL") from exc
    if not host:
        raise ConfigError("SEWS_DATABASE_URL has no host")
    return host.lower()


def check_environment_safety(
    environment: Environment,
    database_url: str,
    *,
    production_project_ref: str | None,
    allowed_provenance: frozenset[str],
) -> None:
    host = database_host(database_url)
    if environment == "development" and host not in LOOPBACK_HOSTS:
        raise ConfigError("development must use a local database (loopback host); hosted databases are refused")
    if environment == "staging":
        if host in LOOPBACK_HOSTS:
            raise ConfigError("staging must use its own hosted database, not a local one")
        if production_project_ref and production_project_ref.lower() in host:
            raise ConfigError("staging must not use the production database")
    if environment == "production":
        if host in LOOPBACK_HOSTS:
            raise ConfigError("production must not use a local database")
        if allowed_provenance != frozenset({"institutional"}):
            raise ConfigError("production may only allow models trained on institutional data")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if env is None else env
    environment = source.get("SEWS_ENV", "")
    if environment not in ENVIRONMENTS:
        raise ConfigError("SEWS_ENV must be one of development, staging, production")
    database_url = source.get("SEWS_DATABASE_URL", "")
    if not database_url:
        raise ConfigError("SEWS_DATABASE_URL is required")
    default_provenance = "institutional" if environment == "production" else "benchmark,synthetic,institutional"
    provenance = frozenset(
        p.strip() for p in source.get("SEWS_ALLOWED_PROVENANCE", default_provenance).split(",") if p.strip()
    )
    if not provenance or not provenance <= {"benchmark", "synthetic", "institutional"}:
        raise ConfigError("SEWS_ALLOWED_PROVENANCE contains unknown values")
    check_environment_safety(
        environment,
        database_url,
        production_project_ref=source.get("SEWS_PRODUCTION_PROJECT_REF"),
        allowed_provenance=provenance,
    )
    jwt_secret = source.get("SEWS_JWT_SECRET") or None
    jwks_url = source.get("SEWS_JWT_JWKS_URL") or None
    if environment != "development" and not (jwt_secret or jwks_url):
        raise ConfigError("SEWS_JWT_SECRET or SEWS_JWT_JWKS_URL is required outside development")
    if jwks_url and not jwks_url.startswith("https://"):
        raise ConfigError("SEWS_JWT_JWKS_URL must use https")
    try:
        rate = int(source.get("SEWS_RATE_LIMIT_PER_MINUTE", "60"))
        max_body = int(source.get("SEWS_MAX_BODY_BYTES", "16384"))
    except ValueError as exc:
        raise ConfigError("rate limit and body size must be integers") from exc
    if not 1 <= rate <= 10_000 or not 1_024 <= max_body <= 1_048_576:
        raise ConfigError("rate limit or body size out of range")
    return Settings(
        environment=environment,
        database_url=database_url,
        model_registry_root=Path(source.get("SEWS_MODEL_REGISTRY_ROOT", "ml/artifacts")),
        allowed_provenance=provenance,
        jwt_secret=jwt_secret,
        jwt_jwks_url=jwks_url,
        jwt_audience=source.get("SEWS_JWT_AUDIENCE") or None,
        rate_limit_per_minute=rate,
        max_body_bytes=max_body,
    )
