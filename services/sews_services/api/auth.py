"""Bearer-token verification for the inference API.

The API is an internal service: callers are backend jobs holding a Supabase-issued JWT whose
``role`` claim is allowed (default: ``service_role``). End users never call it; the mobile app reads
stored predictions through RLS instead.

Verification: signature (HS256 with the project's legacy JWT secret, or RS256/ES256 keys from the
project's JWKS endpoint), ``exp`` required, optional audience, 30 s leeway. The algorithm is pinned
by configuration, never taken from the token alone ("alg: none" and algorithm confusion are refused).
Error messages never include the token or its claims.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt

ASYMMETRIC_ALGORITHMS = ("RS256", "ES256")
LEEWAY_SECONDS = 30


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


class TokenVerifier:
    def __init__(
        self,
        *,
        secret: str | None,
        jwks_url: str | None,
        audience: str | None,
        allowed_roles: frozenset[str],
    ) -> None:
        self._secret = secret
        self._jwks = jwt.PyJWKClient(jwks_url, cache_keys=True) if jwks_url else None
        self._audience = audience
        self._roles = allowed_roles

    def verify(self, authorization: str | None) -> Principal:
        if self._secret is None and self._jwks is None:
            raise AuthError(503, "auth_not_configured", "authentication is not configured")
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError(401, "missing_token", "a bearer token is required")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            alg = jwt.get_unverified_header(token).get("alg")
            if self._jwks is not None and alg in ASYMMETRIC_ALGORITHMS:
                key: object = self._jwks.get_signing_key_from_jwt(token).key
            elif self._secret is not None and alg == "HS256":
                key = self._secret
            else:
                raise AuthError(401, "invalid_token", "the token could not be verified")
            claims = jwt.decode(
                token,
                key,  # type: ignore[arg-type]
                algorithms=[str(alg)],
                audience=self._audience,
                options={"require": ["exp"], "verify_aud": self._audience is not None},
                leeway=LEEWAY_SECONDS,
            )
        except AuthError:
            raise
        except jwt.ExpiredSignatureError as exc:
            raise AuthError(401, "token_expired", "the token has expired") from exc
        except (jwt.PyJWTError, ValueError) as exc:
            raise AuthError(401, "invalid_token", "the token could not be verified") from exc
        role = claims.get("role")
        if role not in self._roles:
            raise AuthError(403, "forbidden", "this token is not allowed to use the inference API")
        return Principal(subject=str(claims.get("sub") or role), role=str(role))
