"""Validación de JWT contra el JWKS de Keycloak (las convenciones internas de API §4).

`/v1/score` exige rol `service` (viene de payments-api). `/v1/rules` acepta cualquier
token válido del realm. `/health` y `/metrics` son públicos y no pasan por acá.
"""
from __future__ import annotations

import httpx
from fastapi import HTTPException, Request
from jose import jwt
from jose.exceptions import JOSEError

from app.settings import settings


def _unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"error": {"code": code, "message": message}})


class _JWKSClient:
    """Cachea el JWKS del issuer configurado. Un cliente por proceso alcanza: las
    keys de Keycloak rotan poco y el pod se recicla en cada deploy."""

    def __init__(self, issuer: str):
        self._jwks_url = f"{issuer}/protocol/openid-connect/certs"
        self._cache: dict | None = None

    def get_jwks(self) -> dict:
        if self._cache is None:
            resp = httpx.get(self._jwks_url, timeout=5.0)
            resp.raise_for_status()
            self._cache = resp.json()
        return self._cache


_jwks_client: _JWKSClient | None = None


def _get_jwks_client() -> _JWKSClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = _JWKSClient(settings.keycloak_issuer)
    return _jwks_client


def _decode_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JOSEError as exc:
        raise _unauthorized("invalid_token", str(exc)) from exc

    jwks = _get_jwks_client().get_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if key is None:
        raise _unauthorized("invalid_token", "kid desconocido")

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[header.get("alg", "RS256")],
            issuer=settings.keycloak_issuer,
            options={"verify_aud": False},
        )
    except JOSEError as exc:
        raise _unauthorized("invalid_token", str(exc)) from exc


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise _unauthorized("unauthorized", "falta Authorization: Bearer")
    return header.split(" ", 1)[1].strip()


def require_token(request: Request) -> dict:
    """Cualquier token válido del realm (usado por /v1/rules)."""
    token = _extract_bearer(request)
    return _decode_token(token)


def require_service_role(request: Request) -> dict:
    """Token válido y con rol `service` en realm_access.roles (usado por /v1/score)."""
    claims = require_token(request)
    roles = claims.get("realm_access", {}).get("roles", [])
    if "service" not in roles:
        raise _unauthorized("unauthorized", "requiere rol service")
    return claims
