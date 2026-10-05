"""Small bounded TTL caches used for read-heavy API resources.

The cache intentionally stores API-safe values rather than SQLAlchemy ORM
instances. ORM objects are tied to a request-scoped session and must never be
reused across requests.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from threading import Lock
from time import monotonic
from typing import Any
from uuid import UUID

from src.config import get_settings


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
