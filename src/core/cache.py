"""Small bounded TTL caches used for read-heavy API resources.

The cache intentionally stores API-safe values rather than SQLAlchemy ORM
instances. ORM objects are tied to a request-scoped session and must never be
reused across requests.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from threading import Lock
from time import monotonic
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheStats:
    """Point-in-time cache counters useful for diagnostics and tests."""

    entries: int
    hits: int
    misses: int
    evictions: int


@dataclass(frozen=True)
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe, bounded in-process TTL cache with LRU eviction."""

    def __init__(
        self,
        *,
        ttl_seconds: int,
        max_entries: int,
        enabled: bool = True,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.enabled = enabled
        self._clock = clock
        self._entries: OrderedDict[Hashable, _CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: Hashable) -> tuple[bool, Any]:
        """Return ``(hit, value)`` and remove expired entries eagerly."""
        if not self.enabled:
            return False, None

        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.expires_at <= self._clock():
                if entry is not None:
                    del self._entries[key]
                self._misses += 1
                return False, None
            self._entries.move_to_end(key)
            self._hits += 1
            return True, entry.value

    def set(self, key: Hashable, value: Any) -> None:
        """Store a value until its TTL expires, evicting the least-used item."""
        if not self.enabled:
            return

        with self._lock:
            self._entries.pop(key, None)
            self._entries[key] = _CacheEntry(value=value, expires_at=self._clock() + self.ttl_seconds)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
                self._evictions += 1

    def clear(self) -> None:
        """Invalidate all cached values."""
        with self._lock:
            self._entries.clear()

    def stats(self) -> CacheStats:
        """Return cache counters without exposing internal values."""
        with self._lock:
            return CacheStats(
                entries=len(self._entries),
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
            )


def _normalize(value: Any) -> Hashable:
    """Convert common query parameter types into a stable hashable value."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _normalize(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_normalize(item) for item in value)
    return value


def cache_key(namespace: str, *parts: Any) -> tuple[Hashable, ...]:
    """Build a stable key that includes the resource and every query filter."""
    return (namespace, *(_normalize(part) for part in parts))


_catalog_cache: TTLCache | None = None
_redis_client: Redis | None = None


async def _get_redis_client() -> Redis | None:
    """Return the shared Redis client when the API cache is configured."""
    global _redis_client
    url = get_settings().redis_url
    if not url:
        return None
    if _redis_client is None:
        _redis_client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    return _redis_client


def _redis_api_cache_keys(namespace: str, params: Any, generation: str = "0") -> tuple[str, str]:
    payload = json.dumps(_normalize(params), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    prefix = f"api-cache:{namespace}"
    return f"{prefix}:generation", f"{prefix}:{generation}:{digest}"


async def get_redis_api_cache(namespace: str, params: Any) -> tuple[bool, Any, str | None]:
    """Read a partitioned API response and its namespace generation."""
    if not get_settings().catalog_cache_enabled:
        return False, None, None
    try:
        client = await _get_redis_client()
        if client is None:
            return False, None, None
        generation_key, _ = _redis_api_cache_keys(namespace, params)
        generation = await client.get(generation_key) or "0"
        _, value_key = _redis_api_cache_keys(namespace, params, generation)
        value = await client.get(value_key)
        return (value is not None, json.loads(value) if value is not None else None, generation)
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("Redis API cache read failed: %s", type(exc).__name__)
        return False, None, None


async def set_redis_api_cache(namespace: str, params: Any, value: Any, generation: str) -> None:
    """Store a response only while its namespace generation remains current."""
    if not get_settings().catalog_cache_enabled:
        return
    try:
        client = await _get_redis_client()
        if client is None:
            return
        settings = get_settings()
        generation_key, value_key = _redis_api_cache_keys(namespace, params, generation)
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        await client.eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] or (not redis.call('GET', KEYS[1]) and ARGV[1] == '0') then "
            "redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3]); return 1 else return 0 end",
            2,
            generation_key,
            value_key,
            generation,
            payload,
            settings.catalog_cache_ttl_seconds,
        )
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("Redis API cache write failed: %s", type(exc).__name__)


async def invalidate_redis_api_cache(*namespaces: str) -> None:
    """Advance namespace generations so existing values become unreachable."""
    if not get_settings().catalog_cache_enabled:
        return
    try:
        client = await _get_redis_client()
        if client is None:
            return
        if not namespaces:
            return
        async with client.pipeline(transaction=True) as pipeline:
            for namespace in namespaces:
                generation_key, _ = _redis_api_cache_keys(namespace, ())
                pipeline.incr(generation_key)
            await pipeline.execute()
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("Redis API cache invalidation failed: %s", type(exc).__name__)


async def close_redis_api_cache() -> None:
    """Close the shared list cache connection during application shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def get_catalog_cache() -> TTLCache:
    """Return the process-wide cache configured for public catalog reads."""
    global _catalog_cache
    if _catalog_cache is None:
        settings = get_settings()
        _catalog_cache = TTLCache(
            enabled=settings.catalog_cache_enabled,
            ttl_seconds=settings.catalog_cache_ttl_seconds,
            max_entries=settings.catalog_cache_max_entries,
        )
    return _catalog_cache


def invalidate_catalog_cache() -> None:
    """Invalidate catalog reads after a successful catalog mutation."""
    get_catalog_cache().clear()


def set_cache_headers(response: Any, *, hit: bool) -> None:
    """Expose cache behavior and browser TTL for operational verification."""
    cache = get_catalog_cache()
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    if cache.enabled:
        response.headers["Cache-Control"] = f"private, max-age={cache.ttl_seconds}"
