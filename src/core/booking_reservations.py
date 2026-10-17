"""Redis cache for pending booking reservations and schedule drafts."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import get_settings

logger = logging.getLogger(__name__)
_client: Redis | None = None

_RESERVE_SCRIPT = """
local version = redis.call('GET', KEYS[2])
local seed_count = tonumber(ARGV[7])
if version ~= ARGV[1] then
  redis.call('DEL', KEYS[1])
  for i = 1, seed_count do
    redis.call('ZADD', KEYS[1], ARGV[7 + (i * 2) - 1], ARGV[7 + (i * 2)])
  end
  redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[6])
end
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[2])
if redis.call('ZSCORE', KEYS[1], ARGV[3]) then
  redis.call('SET', KEYS[3], ARGV[5], 'EX', ARGV[6])
  return 1
end
local capacity_index = 8 + (seed_count * 2)
if redis.call('ZCARD', KEYS[1]) + tonumber(ARGV[4]) >= tonumber(ARGV[capacity_index]) then
  return 0
end
redis.call('ZADD', KEYS[1], ARGV[capacity_index + 1], ARGV[3])
redis.call('SET', KEYS[3], ARGV[5], 'EX', ARGV[6])
redis.call('SET', KEYS[4], ARGV[5], 'EX', ARGV[6])
redis.call('EXPIRE', KEYS[1], ARGV[6])
redis.call('EXPIRE', KEYS[2], ARGV[6])
return 1
"""

_REQUEST_TIME_SCRIPT = """
local overlapping = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[3])
for _, booking_id in ipairs(overlapping) do
  local ends_at = redis.call('HGET', KEYS[2], booking_id)
  if ends_at and tonumber(ends_at) > tonumber(ARGV[2]) then
    return 0
  end
end
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
redis.call('HSET', KEYS[2], ARGV[4], ARGV[3])
redis.call('SET', KEYS[3], ARGV[5], 'EX', ARGV[6])
redis.call('SET', KEYS[4], ARGV[5], 'EX', ARGV[6])
redis.call('EXPIRE', KEYS[1], ARGV[6])
redis.call('EXPIRE', KEYS[2], ARGV[6])
return 1
"""

_REQUEST_TIME_CHECK_SCRIPT = """
local overlapping = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[2])
for _, booking_id in ipairs(overlapping) do
  local ends_at = redis.call('HGET', KEYS[2], booking_id)
  if ends_at and tonumber(ends_at) > tonumber(ARGV[1]) then
    return 1
  end
end
return 0
"""


async def _redis() -> Redis | None:
    """Create the shared Redis client only when configured."""
    global _client
    url = get_settings().redis_url
    if not url:
        return None
    if _client is None:
        _client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    return _client


def _keys(schedule_id: UUID, booking_id: UUID) -> tuple[str, str, str]:
    return (
        f"booking:reservations:schedule:{schedule_id}",
        f"booking:reservations:version:{schedule_id}",
        f"booking:draft:{booking_id}",
    )


async def cache_schedule(value: object, *, expires_at: datetime | None = None) -> bool:
    """Cache every staff or patient schedule by its schedule ID."""
    client = await _redis()
    if client is None:
        return False
    fields = (
        "id",
        "doctor_id",
        "facility_id",
        "service_id",
        "starts_at",
        "ends_at",
        "capacity",
        "status",
        "busy_reason",
        "note",
        "version",
        "source_system",
        "external_schedule_id",
        "created_by",
        "updated_by",
        "cancellation_reason",
        "created_at",
        "updated_at",
    )
    raw = value if isinstance(value, dict) else {field: getattr(value, field, None) for field in fields}
    record = {
        field: item.isoformat() if isinstance(item, datetime) else str(item) if isinstance(item, UUID) else item
        for field, item in raw.items()
    }
    try:
        ttl = max(60, int((expires_at - datetime.now(UTC)).total_seconds()) + 3600) if expires_at else None
        await client.set(f"schedule:{record['id']}", json.dumps(record, separators=(",", ":")), ex=ttl)
        return True
    except (RedisError, TypeError, KeyError) as exc:
        logger.warning("schedule cache write failed", extra={"error_type": type(exc).__name__})
        return False


async def reserve_schedule(
    *,
    schedule_id: UUID,
    booking_id: UUID,
    capacity: int,
    schedule_version: int,
    active_holds: int,
    pending: list[tuple[UUID, datetime]],
    expires_at: datetime,
    draft: dict,
) -> bool | None:
    """Reserve capacity atomically; ``None`` means Redis is unavailable/unconfigured."""
    client = await _redis()
    if client is None:
        return None
    reservation_key, version_key, draft_key = _keys(schedule_id, booking_id)
    ttl = max(60, int((expires_at - datetime.now(UTC)).total_seconds()) + 3600)
    seed = [(max(0, int(expiry.timestamp())), str(value)) for value, expiry in pending if expiry > datetime.now(UTC)]
    args: list[str | int] = [
        str(schedule_version),
        int(datetime.now(UTC).timestamp()),
        str(booking_id),
        active_holds,
        json.dumps(draft, separators=(",", ":")),
        ttl,
        len(seed),
    ]
    args.extend(item for score, member in seed for item in (score, member))
    args.extend((capacity, int(expires_at.timestamp())))
    try:
        result = await client.eval(
            _RESERVE_SCRIPT, 4, reservation_key, version_key, draft_key, f"schedule:{draft['id']}", *args
        )
    except RedisError as exc:
        logger.warning("booking reservation cache unavailable", extra={"error_type": type(exc).__name__})
        return None
    return bool(result)


async def save_draft(booking_id: UUID, draft: dict, expires_at: datetime) -> bool:
    """Cache a requested-time appointment draft without patient identifiers."""
    client = await _redis()
    if client is None:
        return False
    ttl = max(60, int((expires_at - datetime.now(UTC)).total_seconds()) + 3600)
    try:
        payload = json.dumps(draft, separators=(",", ":"))
        await client.set(f"booking:draft:{booking_id}", payload, ex=ttl)
        await client.set(f"schedule:{draft['id']}", payload, ex=ttl)
        return True
    except (RedisError, TypeError, KeyError) as exc:
        logger.warning("booking draft cache unavailable", extra={"error_type": type(exc).__name__})
        return False


async def reserve_requested_time(
    *, booking_id: UUID, doctor_id: UUID, starts_at: datetime, ends_at: datetime, draft: dict, expires_at: datetime
) -> bool | None:
    """Reserve a requested-time appointment interval in Redis without PII."""
    client = await _redis()
    if client is None:
        return None
    interval_key = f"booking:requested:doctor:{doctor_id}"
    end_key = f"booking:requested:ends:{doctor_id}"
    draft_key = f"booking:draft:{booking_id}"
    ttl = max(60, int((expires_at - datetime.now(UTC)).total_seconds()) + 3600)
    try:
        result = await client.eval(
            _REQUEST_TIME_SCRIPT,
            4,
            interval_key,
            end_key,
            draft_key,
            f"schedule:{draft['id']}",
            int(datetime.now(UTC).timestamp()),
            int(starts_at.timestamp()),
            int(ends_at.timestamp()),
            str(booking_id),
            json.dumps(draft, separators=(",", ":")),
            ttl,
        )
    except RedisError as exc:
        logger.warning("requested-time reservation cache unavailable", extra={"error_type": type(exc).__name__})
        return None
    return bool(result)


async def requested_time_conflict(doctor_id: UUID, starts_at: datetime, ends_at: datetime) -> bool | None:
    """Check Redis-held requested intervals; ``None`` means use database fallback."""
    client = await _redis()
    if client is None:
        return None
    try:
        result = await client.eval(
            _REQUEST_TIME_CHECK_SCRIPT,
            2,
            f"booking:requested:doctor:{doctor_id}",
            f"booking:requested:ends:{doctor_id}",
            int(starts_at.timestamp()),
            int(ends_at.timestamp()),
        )
    except RedisError as exc:
        logger.warning("requested-time conflict check unavailable", extra={"error_type": type(exc).__name__})
        return None
    return bool(result)


async def get_draft(booking_id: UUID) -> dict | None:
    """Return a cached schedule draft, if it remains available."""
    client = await _redis()
    if client is None:
        return None
    try:
        value = await client.get(f"booking:draft:{booking_id}")
        return json.loads(value) if value else None
    except (RedisError, ValueError) as exc:
        logger.warning("booking draft cache read failed", extra={"error_type": type(exc).__name__})
        return None


async def release(
    booking_id: UUID,
    schedule_id: UUID | None,
    schedule_version: int | None = None,
    doctor_id: UUID | None = None,
) -> None:
    """Release a pending reservation and its draft after a durable decision."""
    client = await _redis()
    if client is None:
        return
    try:
        await client.delete(f"booking:draft:{booking_id}")
        if doctor_id is not None:
            await client.zrem(f"booking:requested:doctor:{doctor_id}", str(booking_id))
            await client.hdel(f"booking:requested:ends:{doctor_id}", str(booking_id))
        if schedule_id is not None:
            reservation_key, version_key, _ = _keys(schedule_id, booking_id)
            async with client.pipeline(transaction=True) as pipe:
                pipe.zrem(reservation_key, str(booking_id))
                if schedule_version is not None:
                    pipe.set(version_key, str(schedule_version), ex=25 * 60 * 60)
                await pipe.execute()
    except RedisError as exc:
        logger.warning("booking reservation release deferred to cache expiry", extra={"error_type": type(exc).__name__})


async def pending_count(
    schedule_id: UUID, schedule_version: int, pending: list[tuple[UUID, datetime]] | None = None
) -> int | None:
    """Read Redis first; ``None`` means Redis unavailable or cache needs a DB seed."""
    client = await _redis()
    if client is None:
        return None
    key = f"booking:reservations:schedule:{schedule_id}"
    version_key = f"booking:reservations:version:{schedule_id}"
    try:
        version = await client.get(version_key)
        if version != str(schedule_version):
            if pending is None:
                return None
            seed = [
                (max(0, int(expiry.timestamp())), str(value)) for value, expiry in pending if expiry > datetime.now(UTC)
            ]
            async with client.pipeline(transaction=True) as pipe:
                pipe.delete(key)
                if seed:
                    pipe.zadd(key, dict((member, score) for score, member in seed))
                pipe.set(version_key, str(schedule_version), ex=25 * 60 * 60)
                pipe.expire(key, 25 * 60 * 60)
                await pipe.execute()
        await client.zremrangebyscore(key, "-inf", int(datetime.now(UTC).timestamp()))
        return int(await client.zcard(key))
    except RedisError as exc:
        logger.warning("booking reservation count cache unavailable", extra={"error_type": type(exc).__name__})
        return None


async def close_booking_reservation_cache() -> None:
    """Close the shared Redis connection pool during application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
