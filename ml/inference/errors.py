"""Structured inference errors. Messages never echo raw input values."""

from __future__ import annotations

from typing import Any, Literal

ErrorCode = Literal[
    "invalid_request",
    "empty_input",
    "missing_features",
    "unknown_features",
    "invalid_type",
    "non_finite_value",
    "invalid_model_version",
    "model_not_found",
    "model_unavailable",
    "model_not_permitted",
    "internal_error",
]


class InferenceError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.details: dict[str, Any] = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}
