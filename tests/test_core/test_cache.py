from uuid import uuid4

import pytest

from src.core.cache import TTLCache, cache_key
from src.services.catalog import CatalogService


def test_ttl_cache_returns_hits_and_expires_values():
    now = [100.0]
    cache = TTLCache(ttl_seconds=10, max_entries=10, clock=lambda: now[0])
    key = cache_key("services:detail", uuid4())

    cache.set(key, {"id": "service-1"})
    assert cache.get(key) == (True, {"id": "service-1"})

    now[0] = 110.0
    assert cache.get(key) == (False, None)
    assert cache.stats().hits == 1
    assert cache.stats().misses == 1


def test_ttl_cache_evicts_oldest_entry_when_full():
    cache = TTLCache(ttl_seconds=60, max_entries=2)
    cache.set(("one",), 1)
    cache.set(("two",), 2)
    cache.set(("three",), 3)

    assert cache.get(("one",)) == (False, None)
    assert cache.get(("two",)) == (True, 2)
    assert cache.get(("three",)) == (True, 3)
    assert cache.stats().evictions == 1


@pytest.mark.asyncio
async def test_catalog_service_invalidation_clears_public_catalog_entries(monkeypatch):
    import src.services.catalog as catalog_service
    from src.core.cache import get_catalog_cache

    async def no_redis_invalidation(*_families):
        return None

    monkeypatch.setattr(catalog_service, "invalidate_redis_api_cache", no_redis_invalidation)

    cache = get_catalog_cache()
    key = cache_key("services:list", None, None, None, None, 0, 50)
    cache.set(key, [])
    try:
        await CatalogService._invalidate_catalog_cache()
        assert cache.get(key) == (False, None)
    finally:
        cache.clear()
