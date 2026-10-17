"""Short-lived, isolated caches for staff agent routing and allowlisted profiles."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from redis.asyncio import Redis

from src.config import get_settings

PROFILE_SCHEMA_VERSION = "v1"
CASE_RESULT_SCHEMA_VERSION = "v1"
CASE_LOOKUP_TEMPLATES = {
    "today": {"received_today": True},
    "emergency": {"emergency_only": True},
    "today_emergency": {"received_today": True, "emergency_only": True},
}


@lru_cache
def _redis() -> Redis | None:
    settings = get_settings()
    url = settings.staff_agent_cache_redis_url
    if not url:
        return None
    try:
        parsed = urlsplit(url)
        booking = urlsplit(settings.redis_url) if settings.redis_url else None
        if booking and parsed.hostname == booking.hostname:
            cache_port = parsed.port or (6380 if parsed.scheme == "rediss" else 6379)
            booking_port = booking.port or (6380 if booking.scheme == "rediss" else 6379)
            if cache_port == booking_port:
                return None
        if settings.app_env == "production" and (
            parsed.scheme != "rediss" or not parsed.username or not parsed.password
        ):
            return None
        return Redis.from_url(url, decode_responses=True, socket_timeout=0.15, socket_connect_timeout=0.15)
    except Exception:
        return None


def _digest(value: str) -> str:
    key = get_settings().staff_agent_cache_hmac_key.encode()
    if not key:
        return ""
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def profile_cache_keys(patient_id: UUID, staff_id: UUID, facility_scope: str) -> tuple[str, str] | None:
    if len(get_settings().staff_agent_cache_hmac_key) < 32:
        return None
    patient = _digest(str(patient_id))
    scope = _digest(facility_scope)
    access = _digest(f"{staff_id}:{facility_scope}")
    return (
        f"staff-agent:profile:{PROFILE_SCHEMA_VERSION}:{patient}:{access}:{scope}",
        f"staff-agent:profile-version:{patient}",
    )


def case_result_cache_key(staff_id: UUID, facility_scope: str, case_type: str, limit: int) -> str | None:
    if len(get_settings().staff_agent_cache_hmac_key) < 32 or case_type not in {
        "agent_consulting",
        "submitted_exam_forms",
    }:
        return None
    access = _digest(f"{staff_id}:{facility_scope}:{case_type}:{limit}")
    return f"staff-agent:case-results:{CASE_RESULT_SCHEMA_VERSION}:{access}"


async def cached_case_results(staff_id: UUID, facility_scope: str, case_type: str, limit: int) -> dict[str, Any] | None:
    key = case_result_cache_key(staff_id, facility_scope, case_type, limit)
    client = _redis()
    if not key or client is None:
        return None
    try:
        value = json.loads(await client.get(key) or "null")
        return value if isinstance(value, dict) and isinstance(value.get("items"), list) else None
    except Exception:
        return None


async def store_case_results(
    staff_id: UUID, facility_scope: str, case_type: str, limit: int, value: dict[str, Any]
) -> None:
    key = case_result_cache_key(staff_id, facility_scope, case_type, limit)
    client = _redis()
    if not key or client is None:
        return
    try:
        await client.set(
            key,
            json.dumps(value, ensure_ascii=False, default=str),
            ex=get_settings().staff_agent_case_cache_ttl_seconds,
        )
    except Exception:
        return


async def invalidate_profile(patient_id: UUID) -> None:
    client = _redis()
    key = (
        f"staff-agent:profile-version:{_digest(str(patient_id))}"
        if len(get_settings().staff_agent_cache_hmac_key) >= 32
        else None
    )
    if not client or not key:
        return
    try:
        await client.incr(key)
        await client.expire(key, 120)
    except Exception:
        return


async def cached_profile(patient_id: UUID, staff_id: UUID, facility_scope: str) -> dict[str, Any] | None:
    keys = profile_cache_keys(patient_id, staff_id, facility_scope)
    client = _redis()
    if not keys or client is None:
        return None
    try:
        raw = await client.get(keys[0])
        if not raw:
            return None
        entry = json.loads(raw)
        version = await client.get(keys[1]) or "0"
        return entry["value"] if entry.get("version") == version else None
    except Exception:
        return None


async def profile_version(patient_id: UUID) -> str | None:
    client = _redis()
    if client is None or len(get_settings().staff_agent_cache_hmac_key) < 32:
        return None
    try:
        return await client.get(f"staff-agent:profile-version:{_digest(str(patient_id))}") or "0"
    except Exception:
        return None


async def store_profile(
    patient_id: UUID, staff_id: UUID, facility_scope: str, value: dict[str, Any], version: str | None
) -> None:
    keys = profile_cache_keys(patient_id, staff_id, facility_scope)
    client = _redis()
    if not keys or client is None or version is None:
        return
    try:
        await client.set(
            keys[0],
            json.dumps({"version": version, "value": value}),
            ex=get_settings().staff_agent_profile_cache_ttl_seconds,
        )
    except Exception:
        return


def routing_fingerprint(message: str) -> str | None:
    """Return a deterministic safe intent signature; uncertain/clinical input is skipped."""
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    if re.search(
        r"\d|@|\+|\b(?:benh nhan|ho so|trieu chung|chan doan|thuoc|booking|lich kham benh nhan)\b", normalized
    ):
        return None
    words = re.findall(r"[a-z]{2,}", normalized)
    if not words or len(words) > 40:
        return None
    safe_terms = {"bac si", "chuyen khoa", "co so", "lich trong", "lich", "khoa", "case", "sla", "quy trinh", "dich vu"}
    intent_words = sorted(set(words) & {part for term in safe_terms for part in term.split()})
    if len(intent_words) < 2:
        return None
    return hashlib.sha256(("staff-route-v1:" + " ".join(intent_words)).encode()).hexdigest()


async def get_route(fingerprint: str) -> str | None:
    client = _redis()
    if not client:
        return None
    try:
        return await client.get(f"staff-agent:route:v1:{fingerprint}")
    except Exception:
        return None


async def set_route(fingerprint: str, template: str) -> None:
    client = _redis()
    if not client:
        return
    try:
        await client.set(f"staff-agent:route:v1:{fingerprint}", template, ex=300)
    except Exception:
        return


async def get_case_lookup_template(name: str) -> dict[str, bool] | None:
    expected = CASE_LOOKUP_TEMPLATES.get(name)
    client = _redis()
    if expected is None or client is None:
        return None
    try:
        raw = await client.get(f"staff-agent:case-lookup:v1:{name}")
        if raw != json.dumps(expected, sort_keys=True, separators=(",", ":")):
            return None
        return dict(expected)
    except Exception:
        return None


async def set_case_lookup_template(name: str) -> None:
    expected = CASE_LOOKUP_TEMPLATES.get(name)
    client = _redis()
    if expected is None or client is None:
        return
    try:
        await client.set(
            f"staff-agent:case-lookup:v1:{name}",
            json.dumps(expected, sort_keys=True, separators=(",", ":")),
            ex=300,
        )
    except Exception:
        return


async def close_staff_agent_cache() -> None:
    client = _redis()
    if client is not None:
        await client.aclose()
    _redis.cache_clear()
