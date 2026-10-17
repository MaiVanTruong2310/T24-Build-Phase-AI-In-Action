"""Redis-first pending reservation count tests."""

from uuid import uuid4

import pytest

from src.core import booking_reservations


class WarmRedis:
    async def get(self, _key):
        return "3"

    async def zremrangebyscore(self, *_args):
        return 0

    async def zcard(self, _key):
        return 2


class MissRedis:
    async def get(self, _key):
        return None


@pytest.mark.asyncio
async def test_pending_count_uses_warm_redis_without_database_seed(monkeypatch):
    async def redis_client():
        return WarmRedis()

    monkeypatch.setattr(booking_reservations, "_redis", redis_client)

    assert await booking_reservations.pending_count(uuid4(), 3) == 2


@pytest.mark.asyncio
async def test_pending_count_requests_database_seed_on_cache_miss(monkeypatch):
    async def redis_client():
        return MissRedis()

    monkeypatch.setattr(booking_reservations, "_redis", redis_client)

    assert await booking_reservations.pending_count(uuid4(), 3) is None
