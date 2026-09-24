"""SEWS inference API (internal, service-to-service).

Endpoints
    GET  /health           liveness, no auth, no details
    GET  /v1/version       API version, no auth
    POST /v1/predictions   score one feature vector (auth + rate limit), contract in ml/inference/schemas.py
    GET  /v1/metrics       request counts and latency percentiles (auth)

Protections: bearer JWT with an allowed role; token-bucket rate limit per caller; request-body size
limit; strict JSON validation with stable error codes; no stack traces or input values in responses;
access logs contain only request id, method, route, status and latency (never bodies, headers,
query strings or identifiers); OpenAPI docs disabled outside development.
Outside development, ``student_id`` must be an ML subject id (UUID), never an institutional id.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from ml.inference.schemas import API_VERSION
from ml.inference.service import InferenceService
from ml.models.registry import ModelRegistry
from sews_services.api.auth import AuthError, TokenVerifier
from sews_services.config import Settings

logger = logging.getLogger("sews.api")

ERROR_STATUS: dict[str, int] = {
    "invalid_request": 422,
    "empty_input": 422,
    "missing_features": 422,
    "unknown_features": 422,
    "invalid_type": 422,
    "non_finite_value": 422,
    "invalid_model_version": 422,
    "model_not_found": 404,
    "model_not_permitted": 403,
    "model_unavailable": 503,
    "internal_error": 500,
}


def _error(status: int, code: str, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": {"code": code, "message": message, "details": {}}},
        status_code=status,
        headers=headers,
    )


class RateLimiter:
    """Token bucket per caller: ``per_minute`` requests, refilled continuously. Bounded memory."""

    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic, max_keys: int = 10_000) -> None:
        self._rate = per_minute / 60.0
        self._capacity = float(per_minute)
        self._clock = clock
        self._max_keys = max_keys
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = self._clock()
        with self._lock:
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._rate)
            if tokens >= 1.0:
                self._buckets[key] = (tokens - 1.0, now)
                allowed, retry = True, 0
            else:
                self._buckets[key] = (tokens, now)
                allowed, retry = False, int(np.ceil((1.0 - tokens) / self._rate))
            if len(self._buckets) > self._max_keys:
                self._buckets.pop(next(iter(self._buckets)))
            return allowed, retry


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._latencies: deque[float] = deque(maxlen=1000)

    def record(self, route: str, status: int, latency_ms: float) -> None:
        with self._lock:
            key = f"{route} {status // 100}xx"
            self._counts[key] = self._counts.get(key, 0) + 1
            if route == "/v1/predictions":
                self._latencies.append(latency_ms)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            lat = np.array(self._latencies, dtype=float)
            return {
                "requests": dict(self._counts),
                "prediction_latency_ms": (
                    {
                        "n": int(lat.size),
                        "p50": float(np.percentile(lat, 50)),
                        "p95": float(np.percentile(lat, 95)),
                    }
                    if lat.size
                    else {"n": 0}
                ),
            }


def create_app(
    settings: Settings,
    *,
    registry: ModelRegistry | None = None,
    verifier: TokenVerifier | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    dev = settings.environment == "development"
    app = FastAPI(
        title="SEWS inference API",
        version=API_VERSION,
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
    )
    service = InferenceService(
        registry or ModelRegistry(settings.model_registry_root),
        allowed_provenance=settings.allowed_provenance,
    )
    auth = verifier or TokenVerifier(
        secret=settings.jwt_secret,
        jwks_url=settings.jwt_jwks_url,
        audience=settings.jwt_audience,
        allowed_roles=settings.api_allowed_roles,
    )
    limiter = RateLimiter(settings.rate_limit_per_minute, clock)
    metrics = Metrics()

    @app.middleware("http")
    async def observe(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        declared = request.headers.get("content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > settings.max_body_bytes):
            response: Response = _error(413, "payload_too_large", "request body is too large")
        else:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("unhandled error request_id=%s", request_id)
                response = _error(500, "internal_error", "unexpected error")
        latency_ms = (time.perf_counter() - started) * 1000
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        metrics.record(route_path, response.status_code, latency_ms)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "route": route_path,
                    "status": response.status_code,
                    "latency_ms": round(latency_ms, 1),
                }
            )
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _error(exc.status_code, code, "request could not be served")

    def authenticate(request: Request) -> JSONResponse | str:
        try:
            principal = auth.verify(request.headers.get("authorization"))
        except AuthError as exc:
            return _error(exc.status, exc.code, exc.message)
        allowed, retry = limiter.allow(f"{principal.role}:{principal.subject}")
        if not allowed:
            return _error(429, "rate_limited", "too many requests", {"Retry-After": str(max(1, retry))})
        return principal.subject

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/version")
    async def version() -> dict[str, str]:
        return {"api_version": API_VERSION}

    @app.get("/v1/metrics")
    async def get_metrics(request: Request) -> Any:
        who = authenticate(request)
        if isinstance(who, JSONResponse):
            return who
        return metrics.snapshot()

    @app.post("/v1/predictions")
    async def predict(request: Request) -> Any:
        who = authenticate(request)
        if isinstance(who, JSONResponse):
            return who
        body = await request.body()
        if len(body) > settings.max_body_bytes:
            return _error(413, "payload_too_large", "request body is too large")
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            return _error(415, "unsupported_media_type", "use application/json")
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error(422, "invalid_request", "request body is not valid JSON")
        if not dev and isinstance(payload, dict):
            try:
                uuid.UUID(str(payload.get("student_id", "")))
            except ValueError:
                return _error(422, "invalid_request", "student_id must be an ML subject id")
        result = service.predict_safe(payload)
        if result["ok"]:
            return result
        return JSONResponse(result, status_code=ERROR_STATUS.get(result["error"]["code"], 500))

    return app
