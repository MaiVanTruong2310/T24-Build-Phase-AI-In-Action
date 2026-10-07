from uuid import uuid4

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


def test_catalog_service_invalidation_clears_public_catalog_entries():
    from src.core.cache import get_catalog_cache

    cache = get_catalog_cache()
    key = cache_key("services:list", None, None, None, None, 0, 50)
    cache.set(key, [])
    try:
        CatalogService._invalidate_catalog_cache()
        assert cache.get(key) == (False, None)
    finally:
        cache.clear()
