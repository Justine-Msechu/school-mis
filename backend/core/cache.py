"""
Redis cache — thin wrapper with graceful no-op fallback.

If REDIS_URL is not set or Redis is unreachable, every function silently
does nothing so callers never need a try/except.

Usage:
    from backend.core.cache import cache_get, cache_set, cache_bust

    cached = cache_get(key)
    if cached is not None:
        return cached
    result = expensive_query()
    cache_set(key, result, ttl=120)
    return result

Cache-key convention (multi-tenant safe):
    school:{school_id}:dash:stats:{user_id}          TTL 60 s
    school:{school_id}:rpt:{name}:{...params}        TTL 120–300 s
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

log = logging.getLogger(__name__)

_client: Any = None          # redis.Redis or None
_unavailable_until: float = 0.0   # backoff timestamp
_RETRY_AFTER = 30.0                # seconds before re-attempting a failed connect


def _get() -> Any:
    """Return live Redis client or None (with exponential-ish backoff on failures)."""
    global _client, _unavailable_until

    if _client is not None:
        return _client

    if time.monotonic() < _unavailable_until:
        return None

    try:
        import redis  # type: ignore[import]
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        c = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        c.ping()
        _client = c
        log.info("Redis cache connected: %s", url.split("@")[-1])
        return _client
    except Exception as exc:
        _unavailable_until = time.monotonic() + _RETRY_AFTER
        log.debug("Redis unavailable (retry in %ss): %s", _RETRY_AFTER, exc)
        return None


def cache_get(key: str) -> Any:
    r = _get()
    if r is None:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    r = _get()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    r = _get()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass


def cache_bust(pattern: str) -> None:
    """Delete all keys matching a glob pattern (e.g. 'school:7:rpt:*')."""
    r = _get()
    if r is None:
        return
    try:
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass
