from types import SimpleNamespace

import pytest
from redis.exceptions import RedisError

import src.core.cache as cache


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.keys = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def incr(self, key):
        self.keys.append(key)

    async def execute(self):
        for key in self.keys:
            self.redis.values[key] = str(int(self.redis.values.get(key, "0")) + 1)


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def eval(self, _script, _numkeys, generation_key, value_key, generation, value, _ttl):
        if self.values.get(generation_key, "0") == generation:
            self.values[value_key] = value
            return "OK"
        return 0

    def pipeline(self, transaction=True):
        assert transaction is True
        return FakePipeline(self)


@pytest.mark.asyncio
async def test_redis_api_cache_round_trip_partition_and_invalidation(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(
        cache, "get_settings", lambda: SimpleNamespace(catalog_cache_enabled=True, catalog_cache_ttl_seconds=30)
    )

    async def get_redis():
        return redis

    monkeypatch.setattr(cache, "_get_redis_client", get_redis)
    params = ("user-1", {"offset": 0, "status": "pending_approval"})

    assert await cache.get_redis_api_cache("staff-bookings", params) == (False, None, "0")
    await cache.set_redis_api_cache("staff-bookings", params, {"items": []}, "0")
    hit, value, generation = await cache.get_redis_api_cache("staff-bookings", params)
    assert (hit, value, generation) == (True, {"items": []}, "0")
    assert (await cache.get_redis_api_cache("staff-bookings", ("user-2", params[1])))[0] is False

    await cache.invalidate_redis_api_cache("staff-bookings")
    assert (await cache.get_redis_api_cache("staff-bookings", params))[0] is False


@pytest.mark.asyncio
async def test_redis_api_cache_does_not_store_after_generation_changes(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(
        cache, "get_settings", lambda: SimpleNamespace(catalog_cache_enabled=True, catalog_cache_ttl_seconds=30)
    )

    async def get_redis():
        return redis

    monkeypatch.setattr(cache, "_get_redis_client", get_redis)
    _hit, _value, generation = await cache.get_redis_api_cache("catalog", ("doctors", ()))
    await cache.invalidate_redis_api_cache("catalog")
    await cache.set_redis_api_cache("catalog", ("doctors", ()), ["stale"], generation)
    hit, _, _ = await cache.get_redis_api_cache("catalog", ("doctors", ()))
    assert hit is False


@pytest.mark.asyncio
async def test_redis_api_cache_errors_degrade_to_database_miss(monkeypatch):
    monkeypatch.setattr(cache, "get_settings", lambda: SimpleNamespace(catalog_cache_enabled=True))

    async def broken_redis():
        raise RedisError("unavailable")

    monkeypatch.setattr(cache, "_get_redis_client", broken_redis)
    assert await cache.get_redis_api_cache("catalog", ("doctors", ())) == (False, None, None)
