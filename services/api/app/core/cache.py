from __future__ import annotations

import hashlib
import json
from time import monotonic
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings

_client: redis.Redis | None = None
_redis_available: bool | None = None

# in memory fallback if redis is not available
_mem_cache: dict[str, tuple[float, Any]] = {}
_MEM_MAX_ENTRIES = 512


def _make_key(prefix: str, data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"


async def _get_redis() -> redis.Redis | None:
    global _client, _redis_available
    if _redis_available is False:
        return None
    if _client is None:
        _client = redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        await _client.ping()
        _redis_available = True
        return _client
    except Exception:
        _redis_available = False
        return None


async def cache_get(prefix: str, key_data: Any) -> Any | None:
    key = _make_key(prefix, key_data)

    r = await _get_redis()
    if r is not None:
        try:
            val = await r.get(key)
            if val is not None:
                return json.loads(val)
        except Exception:
            pass

    # fallback to memory
    entry = _mem_cache.get(key)
    if entry and entry[0] > monotonic():
        return entry[1]
    return None


async def cache_set(prefix: str, key_data: Any, value: Any, ttl_seconds: int = 3600) -> None:
    key = _make_key(prefix, key_data)

    r = await _get_redis()
    if r is not None:
        try:
            await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception:
            pass

    # always store in memory too
    _mem_cache[key] = (monotonic() + ttl_seconds, value)
    if len(_mem_cache) > _MEM_MAX_ENTRIES:
        oldest = sorted(_mem_cache, key=lambda k: _mem_cache[k][0])
        for k in oldest[:len(_mem_cache) - _MEM_MAX_ENTRIES]:
            _mem_cache.pop(k, None)
