from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import AppUser


_JWT_LEEWAY_SECONDS = 30
_JWKS_CACHE_TTL_SECONDS = 300
_JWKS_CACHE: dict[str, tuple[float, dict[str, dict[str, Any]]]] = {}
_BEARER_AUTH = HTTPBearer(auto_error=False)
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


class AuthTokenError(ValueError):
    """Raised when Clerk token validation fails."""


@dataclass(frozen=True)
class AuthContext:
    subject: str
    claims: dict[str, Any]


def _normalize_issuer(issuer: str) -> str:
    return issuer.rstrip("/")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _parse_jwt(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    segments = token.split(".")
    if len(segments) != 3:
        raise AuthTokenError("Token must have 3 segments")

    header_raw, payload_raw, signature_raw = segments
    try:
        header = json.loads(_base64url_decode(header_raw))
        payload = json.loads(_base64url_decode(payload_raw))
        signature = _base64url_decode(signature_raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthTokenError("Token is not valid base64url JSON") from exc

    signing_input = f"{header_raw}.{payload_raw}".encode("utf-8")
    return header, payload, signature, signing_input


def _build_jwks_url(settings: Settings) -> str:
    if settings.clerk_jwks_url:
        return settings.clerk_jwks_url
    return f"{_normalize_issuer(settings.clerk_issuer_url)}/.well-known/jwks.json"


async def _load_jwks(settings: Settings) -> dict[str, dict[str, Any]]:
    issuer = _normalize_issuer(settings.clerk_issuer_url)
    cached = _JWKS_CACHE.get(issuer)
    now = monotonic()
    if cached and cached[0] > now:
        return cached[1]

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_build_jwks_url(settings))
        response.raise_for_status()
        payload = response.json()

    keys = payload.get("keys")
    if not isinstance(keys, list):
        raise AuthTokenError("Clerk JWKS payload is invalid")

    keys_by_kid: dict[str, dict[str, Any]] = {}
    for key in keys:
        if not isinstance(key, dict):
            continue
        kid = str(key.get("kid") or "").strip()
        if not kid:
            continue
        if key.get("kty") != "RSA":
            continue
        if not key.get("n") or not key.get("e"):
            continue
        keys_by_kid[kid] = key

    if not keys_by_kid:
        raise AuthTokenError("No usable Clerk JWKS RSA keys were found")

    _JWKS_CACHE[issuer] = (now + _JWKS_CACHE_TTL_SECONDS, keys_by_kid)
    return keys_by_kid


def _verify_rs256_signature(
    *,
    signing_input: bytes,
    signature: bytes,
    key: dict[str, Any],
) -> bool:
    try:
        modulus = int.from_bytes(_base64url_decode(str(key["n"])), byteorder="big")
        exponent = int.from_bytes(_base64url_decode(str(key["e"])), byteorder="big")
    except (KeyError, ValueError, TypeError):
        return False

    if modulus <= 0 or exponent <= 0:
        return False

    modulus_len = (modulus.bit_length() + 7) // 8
    if len(signature) != modulus_len:
        return False

    decrypted = pow(
        int.from_bytes(signature, byteorder="big"),
        exponent,
        modulus,
    ).to_bytes(modulus_len, byteorder="big")

    digest_info = _SHA256_DIGEST_INFO_PREFIX + sha256(signing_input).digest()
    padding_len = modulus_len - len(digest_info) - 3
    if padding_len < 8:
        return False

    expected = b"\x00\x01" + (b"\xff" * padding_len) + b"\x00" + digest_info
    return decrypted == expected


def _validate_claims(payload: dict[str, Any], settings: Settings) -> str:
    token_issuer = str(payload.get("iss") or "")
    expected_issuer = _normalize_issuer(settings.clerk_issuer_url)
    if _normalize_issuer(token_issuer) != expected_issuer:
        raise AuthTokenError("Token issuer does not match configured Clerk issuer")

    subject = str(payload.get("sub") or "").strip()
    if not subject:
        raise AuthTokenError("Token is missing a subject")

    now = time.time()
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise AuthTokenError("Token is missing exp claim")
    if now - _JWT_LEEWAY_SECONDS >= float(exp):
        raise AuthTokenError("Token has expired")

    nbf = payload.get("nbf")
    if nbf is not None:
        if not isinstance(nbf, (int, float)):
            raise AuthTokenError("Token nbf claim is invalid")
        if now + _JWT_LEEWAY_SECONDS < float(nbf):
            raise AuthTokenError("Token is not valid yet")

    iat = payload.get("iat")
    if iat is not None:
        if not isinstance(iat, (int, float)):
            raise AuthTokenError("Token iat claim is invalid")
        if float(iat) > now + _JWT_LEEWAY_SECONDS:
            raise AuthTokenError("Token iat claim is in the future")

    audience = settings.clerk_jwt_audience
    if audience:
        token_audience = payload.get("aud")
        if isinstance(token_audience, str):
            matches_audience = token_audience == audience
        elif isinstance(token_audience, list):
            matches_audience = audience in token_audience
        else:
            matches_audience = False
        if not matches_audience:
            raise AuthTokenError("Token audience does not match configured audience")

    return subject


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def verify_clerk_token(token: str, settings: Settings) -> AuthContext:
    header, payload, signature, signing_input = _parse_jwt(token)

    if header.get("alg") != "RS256":
        raise AuthTokenError("Only RS256 Clerk tokens are supported")

    kid = str(header.get("kid") or "").strip()
    if not kid:
        raise AuthTokenError("Token is missing key id (kid)")

    keys_by_kid = await _load_jwks(settings)
    signing_key = keys_by_kid.get(kid)
    if signing_key is None:
        # Force one refresh before giving up in case Clerk has rotated keys.
        _JWKS_CACHE.pop(_normalize_issuer(settings.clerk_issuer_url), None)
        keys_by_kid = await _load_jwks(settings)
        signing_key = keys_by_kid.get(kid)
        if signing_key is None:
            raise AuthTokenError("Token key id is not present in Clerk JWKS")

    if not _verify_rs256_signature(
        signing_input=signing_input,
        signature=signature,
        key=signing_key,
    ):
        raise AuthTokenError("Token signature validation failed")

    subject = _validate_claims(payload, settings)
    return AuthContext(subject=subject, claims=payload)


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER_AUTH),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        # let unauthenticated requests through in dev so the app works without clerk
        if settings.environment == "development":
            return AuthContext(subject="demo-user", claims={})
        raise _unauthorized("Missing bearer token")

    try:
        return await verify_clerk_token(credentials.credentials, settings)
    except (AuthTokenError, httpx.HTTPError) as exc:
        raise _unauthorized(str(exc)) from exc


async def get_current_app_user(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> AppUser:
    stmt = select(AppUser).where(AppUser.clerk_user_id == auth.subject)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        user = AppUser(clerk_user_id=auth.subject)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
