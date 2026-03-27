from __future__ import annotations

import json
import random
import time
from functools import lru_cache
from hashlib import sha256
from typing import Any

import pytest

from app.api.deps import auth as auth_dep
from app.core.config import Settings


_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _b64url_encode(raw: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    import base64

    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _is_probable_prime(n: int) -> bool:
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)
    for prime in small_primes:
        if n == prime:
            return True
        if n % prime == 0:
            return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for witness in (2, 3, 5, 7, 11, 13, 17):
        if witness >= n:
            continue
        x = pow(witness, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False

    return True


def _generate_prime(bits: int, rng: random.Random) -> int:
    while True:
        candidate = rng.getrandbits(bits)
        candidate |= 1
        candidate |= (1 << (bits - 1))
        if _is_probable_prime(candidate):
            return candidate


@lru_cache(maxsize=8)
def _rsa_keypair(seed: int) -> tuple[int, int, int]:
    rng = random.Random(seed)
    e = 65537
    while True:
        p = _generate_prime(256, rng)
        q = _generate_prime(256, rng)
        if p == q:
            continue
        phi = (p - 1) * (q - 1)
        if phi % e == 0:
            continue
        d = pow(e, -1, phi)
        return p * q, e, d


def _jwk_for_public_key(n: int, e: int, kid: str) -> dict[str, str]:
    return {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": kid,
        "n": _b64url_encode(n.to_bytes((n.bit_length() + 7) // 8, "big")),
        "e": _b64url_encode(e.to_bytes((e.bit_length() + 7) // 8, "big")),
    }


def _sign_rs256(message: bytes, d: int, n: int) -> bytes:
    digest_info = _DIGEST_INFO_PREFIX + sha256(message).digest()
    modulus_len = (n.bit_length() + 7) // 8
    padding_len = modulus_len - len(digest_info) - 3
    assert padding_len >= 8
    encoded_message = b"\x00\x01" + (b"\xff" * padding_len) + b"\x00" + digest_info
    signature_int = pow(int.from_bytes(encoded_message, "big"), d, n)
    return signature_int.to_bytes(modulus_len, "big")


def _build_jwt(payload: dict[str, Any], kid: str, *, n: int, d: int) -> str:
    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    header_segment = _b64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature_segment = _b64url_encode(_sign_rs256(signing_input, d, n))
    return f"{header_segment}.{payload_segment}.{signature_segment}"


class _MockResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _MockAsyncClient:
    def __init__(self, payloads: list[dict[str, Any]], calls: list[str]) -> None:
        self._payloads = payloads
        self._calls = calls

    async def __aenter__(self) -> "_MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str) -> _MockResponse:
        self._calls.append(url)
        index = min(len(self._calls) - 1, len(self._payloads) - 1)
        return _MockResponse(self._payloads[index])


def _mock_jwks(monkeypatch: pytest.MonkeyPatch, payloads: list[dict[str, Any]]) -> list[str]:
    calls: list[str] = []

    def _factory(**kwargs: Any) -> _MockAsyncClient:
        _ = kwargs
        return _MockAsyncClient(payloads, calls)

    monkeypatch.setattr(auth_dep.httpx, "AsyncClient", _factory)
    return calls


def _settings(*, audience: str | None = None) -> Settings:
    return auth_dep.get_settings().model_copy(
        update={
            "clerk_issuer_url": "https://issuer.example",
            "clerk_jwks_url": "https://issuer.example/.well-known/jwks.json",
            "clerk_jwt_audience": audience,
        }
    )


@pytest.fixture(autouse=True)
def _clear_jwks_cache() -> None:
    auth_dep._JWKS_CACHE.clear()


@pytest.mark.asyncio
async def test_verify_clerk_token_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    n, e, d = _rsa_keypair(101)
    kid = "kid-101"
    _mock_jwks(monkeypatch, [{"keys": [_jwk_for_public_key(n, e, kid)]}])

    now = int(time.time())
    payload = {
        "iss": "https://issuer.example",
        "sub": "user_123",
        "exp": now + 3600,
        "iat": now,
        "aud": "afterhours-app",
    }
    token = _build_jwt(payload, kid, n=n, d=d)

    context = await auth_dep.verify_clerk_token(
        token,
        _settings(audience="afterhours-app"),
    )

    assert context.subject == "user_123"
    assert context.claims["aud"] == "afterhours-app"


@pytest.mark.asyncio
async def test_verify_clerk_token_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    n_good, e_good, _ = _rsa_keypair(202)
    n_bad, _, d_bad = _rsa_keypair(303)
    kid = "kid-202"
    _mock_jwks(monkeypatch, [{"keys": [_jwk_for_public_key(n_good, e_good, kid)]}])

    now = int(time.time())
    payload = {
        "iss": "https://issuer.example",
        "sub": "user_123",
        "exp": now + 3600,
        "iat": now,
    }
    token = _build_jwt(payload, kid, n=n_bad, d=d_bad)

    with pytest.raises(auth_dep.AuthTokenError, match="signature validation failed"):
        await auth_dep.verify_clerk_token(token, _settings())


@pytest.mark.asyncio
async def test_verify_clerk_token_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    n, e, d = _rsa_keypair(404)
    kid = "kid-404"
    _mock_jwks(monkeypatch, [{"keys": [_jwk_for_public_key(n, e, kid)]}])

    now = int(time.time())
    payload = {
        "iss": "https://issuer.example",
        "sub": "user_123",
        "exp": now - 120,
        "iat": now - 3600,
    }
    token = _build_jwt(payload, kid, n=n, d=d)

    with pytest.raises(auth_dep.AuthTokenError, match="expired"):
        await auth_dep.verify_clerk_token(token, _settings())


@pytest.mark.asyncio
async def test_verify_clerk_token_rejects_wrong_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    n, e, d = _rsa_keypair(505)
    kid = "kid-505"
    _mock_jwks(monkeypatch, [{"keys": [_jwk_for_public_key(n, e, kid)]}])

    now = int(time.time())
    payload = {
        "iss": "https://wrong.example",
        "sub": "user_123",
        "exp": now + 3600,
        "iat": now,
    }
    token = _build_jwt(payload, kid, n=n, d=d)

    with pytest.raises(auth_dep.AuthTokenError, match="issuer"):
        await auth_dep.verify_clerk_token(token, _settings())


@pytest.mark.asyncio
async def test_verify_clerk_token_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    n, e, d = _rsa_keypair(606)
    kid = "kid-606"
    _mock_jwks(monkeypatch, [{"keys": [_jwk_for_public_key(n, e, kid)]}])

    now = int(time.time())
    payload = {
        "iss": "https://issuer.example",
        "sub": "user_123",
        "exp": now + 3600,
        "iat": now,
        "aud": "another-audience",
    }
    token = _build_jwt(payload, kid, n=n, d=d)

    with pytest.raises(auth_dep.AuthTokenError, match="audience"):
        await auth_dep.verify_clerk_token(token, _settings(audience="afterhours-app"))


@pytest.mark.asyncio
async def test_verify_clerk_token_handles_jwks_key_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    n1, e1, _ = _rsa_keypair(701)
    n2, e2, d2 = _rsa_keypair(702)
    kid1 = "kid-old"
    kid2 = "kid-new"
    calls = _mock_jwks(
        monkeypatch,
        [
            {"keys": [_jwk_for_public_key(n1, e1, kid1)]},
            {"keys": [_jwk_for_public_key(n2, e2, kid2)]},
        ],
    )

    now = int(time.time())
    payload = {
        "iss": "https://issuer.example",
        "sub": "rotated_user",
        "exp": now + 3600,
        "iat": now,
    }
    token = _build_jwt(payload, kid2, n=n2, d=d2)

    context = await auth_dep.verify_clerk_token(token, _settings())

    assert context.subject == "rotated_user"
    assert len(calls) == 2


def test_rs256_helper_sanity_check() -> None:
    n, e, d = _rsa_keypair(999)
    message = b"header.payload"
    signature = _sign_rs256(message, d, n)

    em = pow(int.from_bytes(signature, "big"), e, n).to_bytes((n.bit_length() + 7) // 8, "big")
    assert em.startswith(b"\x00\x01\xff")
    assert em.endswith(_DIGEST_INFO_PREFIX + sha256(message).digest())
