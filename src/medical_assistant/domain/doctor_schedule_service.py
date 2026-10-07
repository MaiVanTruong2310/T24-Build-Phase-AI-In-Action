"""Doctor discovery backed by Supabase and the verified Vinmec crawl.

The service never fabricates clinicians or appointment slots. Supabase is the
only source of availability. When operational tables are empty/unavailable,
the crawler dataset may still be used to show sourced doctor profiles, but the
result explicitly carries ``schedule_verified=False`` and no slot IDs.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = UTC
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

from src.medical_assistant.db.supabase_client import get_supabase_client
from src.medical_assistant.domain.facility_linking import facility_key, normalize_text

logger = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))
DOCTORS_DATASET = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "crawled"
    / "doctors"
    / "processed"
    / "jsonl"
    / "vinmec_professionals_vi.jsonl"
)

SPECIALTY_ALIAS_MAP = {
    "thần kinh": ["thần kinh", "nội thần kinh", "ngoại thần kinh", "neurology"],
    "tiêu hóa": ["tiêu hóa", "tiêu hoá", "nội tiêu hóa", "ngoại tiêu hóa", "gastroenterology", "gan mật"],
    "tim mạch": ["tim mạch", "nội tim mạch", "can thiệp tim mạch", "cardiology"],
    "nhi": ["nhi", "nội nhi", "ngoại nhi", "sơ sinh", "pediatrics"],
    "sản": ["sản", "phụ khoa", "sản phụ khoa", "hỗ trợ sinh sản", "womens health"],
    "xương khớp": ["xương khớp", "chấn thương chỉnh hình", "orthopedics", "y học thể thao"],
    "cấp cứu": ["cấp cứu", "hồi sức", "emergency"],
    "tai mũi họng": ["tai mũi họng", "ent"],
    "da liễu": ["da liễu", "dermatology"],
    "hô hấp": ["hô hấp", "nội hô hấp", "phổi", "respiratory"],
    "mắt": ["mắt", "nhãn khoa", "ophthalmology"],
    "sức khỏe tổng quát": ["sức khỏe tổng quát", "tổng quát", "health screening", "đa khoa"],
}


class _UnavailableDatabaseClient:
    """Offline client used when Supabase credentials are not configured."""

    def select(self, table: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return []


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(text.replace("đ", "d").replace("-", " ").split())


def _specialty_terms(name: str | None) -> list[str]:
    raw_name = str(name or "").strip()
    folded = _fold(raw_name)
    code_aliases = {
        "tieu_hoa": "tieu hoa",
        "than_kinh": "than kinh",
        "tim_mach": "tim mach",
        "tai_mui_hong": "tai mui hong",
        "xuong_khop": "xuong khop",
        "ho_hap": "ho hap",
        "tong_quat": "suc khoe tong quat",
        "da_khoa": "suc khoe tong quat",
    }
    folded = code_aliases.get(folded, folded)
    terms: set[str] = set()
    if raw_name:
        terms.add(raw_name.lower())
    if folded:
        terms.add(folded)

    for key, aliases in SPECIALTY_ALIAS_MAP.items():
        all_aliases = [key, *aliases]
        folded_aliases = [_fold(a) for a in all_aliases]
        matched = False
        if folded in folded_aliases:
            matched = True
        else:
            for fa in folded_aliases:
                if len(fa) <= 3:
                    if re.search(rf"\b{re.escape(fa)}\b", folded):
                        # Guard against "mat" matching "gan mat" or "tieu hoa"
                        if fa == "mat" and ("gan" in folded or "tieu hoa" in folded):
                            continue
                        matched = True
                        break
                elif fa in folded:
                    matched = True
                    break
        if matched:
            terms.update(all_aliases)
            terms.update(folded_aliases)

    return sorted((term for term in terms if len(term) >= 2), key=len, reverse=True)


def _experience_years(value: Any) -> int:
    values = value if isinstance(value, list) else [value]
    for item in values:
        match = re.search(r"\b(\d{1,2})\s*năm\b", str(item or ""), flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def format_utc_to_vn_time(utc_iso_str: str) -> str:
    try:
        parsed = datetime.fromisoformat(utc_iso_str.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        local = parsed.astimezone(VN_TZ)
        period = "Sáng" if local.hour < 12 else "Chiều"
        return f"{local.strftime('%H:%M')} ({period}) ngày {local.strftime('%d/%m/%Y')}"
    except Exception:
        return str(utc_iso_str).replace("T", " ")[:16]


@lru_cache(maxsize=1)
def _load_crawled_doctors() -> tuple[dict[str, Any], ...]:
    if not DOCTORS_DATASET.exists():
        logger.warning("Doctor crawler dataset is missing: %s", DOCTORS_DATASET)
        return ()
    records: list[dict[str, Any]] = []
    with DOCTORS_DATASET.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return tuple(records)


class DoctorScheduleService:
    def __init__(self, client: Any | None = None):
        if client is not None:
            self.client = client
            return
        try:
            self.client = get_supabase_client()
        except ValueError:
            # Local development and degraded deployments can still expose
            # sourced doctor profiles; only live availability is disabled.
            self.client = _UnavailableDatabaseClient()

    def find_candidate_specialties(self, query_name: str) -> list[dict[str, Any]]:
        """Find matching specialty rows ranked by the number of approved doctors."""
        candidate_specialties: list[dict[str, Any]] = []
        seen_ids = set()
        for term in _specialty_terms(query_name):
            try:
                rows = self.client.select(
                    "specialties",
                    params={"select": "id,code,name", "name": f"ilike.*{term}*", "limit": 10},
                )
                for row in rows:
                    if row["id"] not in seen_ids:
                        seen_ids.add(row["id"])
                        candidate_specialties.append(row)
            except Exception as exc:
                logger.warning("Supabase specialty lookup failed: %s", type(exc).__name__)
        if not candidate_specialties:
            return []

        # Count doctors for each candidate specialty to rank them
        scored: list[tuple[int, dict[str, Any]]] = []
        for spec in candidate_specialties[:12]:
            try:
                relations = self.client.select(
                    "doctor_specialties",
                    params={
                        "select": "doctor_id",
                        "specialty_id": f"eq.{spec['id']}",
                        "review_status": "eq.approved",
                        "limit": 100,
                    },
                )
                scored.append((len(relations), spec))
            except Exception:
                scored.append((0, spec))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [pair[1] for pair in scored]

    def find_specialty_by_name(self, query_name: str) -> dict[str, Any] | None:
        candidates = self.find_candidate_specialties(query_name)
        return candidates[0] if candidates else None

    def find_facility(self, query: str | None) -> dict[str, Any] | None:
        """Resolve a facility UUID, code, or display name to one active row."""
        raw = str(query or "").strip()
        if not raw:
            return None
        try:
            UUID(raw)
        except ValueError:
            pass
        else:
            rows = self.client.select(
                "facilities",
                params={"select": "id,code,name,address", "id": f"eq.{raw}", "status": "eq.active", "limit": 1},
            )
            if rows:
                return rows[0]

        rows = self.client.select(
            "facilities",
            params={"select": "id,code,name,address", "status": "eq.active", "limit": 200},
        )
        folded = normalize_text(raw)
        exact = [row for row in rows if folded in {normalize_text(row.get("code")), normalize_text(row.get("name"))}]
        if exact:
            return exact[0]
        requested_key = facility_key(raw)
        if requested_key:
            matches = [row for row in rows if facility_key(row.get("name")) == requested_key]
            if matches:
                matches.sort(key=lambda row: str(row.get("code") or "").startswith("VINMEC_"))
                return matches[0]
        contains = [row for row in rows if folded and folded in normalize_text(row.get("name"))]
        return contains[0] if len(contains) == 1 else None

    def _database_doctors(
        self,
        specialty_name: str | None,
        limit_doctors: int,
        slots_per_doctor: int,
        requested_days: int | None,
        preferred_period: str | None,
        facility: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        candidates = self.find_candidate_specialties(specialty_name or "")
        if not candidates:
            return []
        primary_specialty = candidates[0]
        spec_ids = [c["id"] for c in candidates[:3]]
        relations = self.client.select(
            "doctor_specialties",
            params={
                "select": "doctor_id",
                "specialty_id": f"in.({','.join(spec_ids)})",
                "review_status": "eq.approved",
                "limit": max(20, limit_doctors * 5),
            },
        )
        doctor_ids = list(dict.fromkeys(str(row["doctor_id"]) for row in relations if row.get("doctor_id")))
        facility_departments: dict[str, str] = {}
        if facility:
            facility_relations = self.client.select(
                "doctor_facilities",
                params={
                    "select": "doctor_id,department",
                    "facility_id": f"eq.{facility['id']}",
                    "status": "eq.active",
                    "limit": max(100, limit_doctors * 20),
                },
            )
            facility_ids = {str(row["doctor_id"]) for row in facility_relations if row.get("doctor_id")}
            doctor_ids = [doctor_id for doctor_id in doctor_ids if doctor_id in facility_ids]
            facility_departments = {
                str(row["doctor_id"]): str(row.get("department") or "")
                for row in facility_relations
                if row.get("doctor_id")
            }
        if not doctor_ids:
            return []
        doctors = self.client.select(
            "doctors",
            params={
                "select": "id,full_name,title,years_of_experience,languages,source_url",
                "id": "in.(" + ",".join(doctor_ids) + ")",
                "status": "eq.active",
                "review_status": "eq.approved",
                "booking_enabled": "eq.true",
                "limit": limit_doctors,
            },
        )
        if not doctors:
            return []

        days = max(1, min(requested_days or 7, 30))
        now = datetime.now(UTC)
        schedule_params = {
            "select": "id,doctor_id,facility_id,starts_at,ends_at,status",
            "doctor_id": "in.(" + ",".join(str(row["id"]) for row in doctors) + ")",
            "status": "eq.available",
            "starts_at": f"gte.{now.isoformat()}",
            "order": "starts_at.asc",
            "limit": max(30, limit_doctors * slots_per_doctor * 3),
        }
        if facility:
            schedule_params["facility_id"] = f"eq.{facility['id']}"
        schedules = self.client.select(
            "doctor_schedules",
            params=schedule_params,
        )
        latest = now + timedelta(days=days)
        slots_by_doctor: dict[str, list[dict[str, Any]]] = {}
        for slot in schedules:
            raw_start = str(slot.get("starts_at") or "")
            try:
                starts_at = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
            except ValueError:
                continue
            if starts_at > latest:
                continue
            local_hour = starts_at.astimezone(VN_TZ).hour
            if preferred_period == "morning" and local_hour >= 12:
                continue
            if preferred_period in {"afternoon", "evening"} and local_hour < 12:
                continue
            doctor_slots = slots_by_doctor.setdefault(str(slot.get("doctor_id")), [])
            if len(doctor_slots) < slots_per_doctor:
                doctor_slots.append(
                    {
                        "schedule_id": str(slot["id"]),
                        "starts_at": format_utc_to_vn_time(raw_start),
                        "ends_at": str(slot.get("ends_at") or ""),
                        "verified": True,
                    }
                )

        return [
            {
                **doctor,
                "specialties": [primary_specialty.get("name")],
                "overview": "",
                "workplace": facility.get("name", "") if facility else "",
                "department": facility_departments.get(str(doctor["id"]), ""),
                "data_source": "supabase",
                "schedule_verified": bool(slots_by_doctor.get(str(doctor["id"]))),
                "available_slots": slots_by_doctor.get(str(doctor["id"]), []),
            }
            for doctor in doctors
        ]

    def _crawled_doctors(
        self, specialty_name: str | None, limit_doctors: int, facility_query: str | None = None
    ) -> list[dict[str, Any]]:
        terms = _specialty_terms(specialty_name)
        if not terms:
            return []
        requested_facility_key = facility_key(facility_query) if facility_query else None
        scored: list[tuple[int, int, dict[str, Any]]] = []
        query_is_pediatric = any(term in {"nhi", "noi nhi", "ngoai nhi", "pediatrics"} for term in terms)
        for record in _load_crawled_doctors():
            specialties = record.get("specialties") or []
            positions = record.get("positions") or []
            sections = record.get("sections") or {}
            workplaces = record.get("workplace") or sections.get("Nơi làm việc") or []
            if isinstance(workplaces, str):
                workplaces = [workplaces]
            if requested_facility_key and not any(
                facility_key(workplace) == requested_facility_key for workplace in workplaces
            ):
                continue
            searchable = _fold(" ".join([*specialties, *positions, str(record.get("overview") or "")]))
            specialty_text = _fold(specialties)
            score = sum(4 if term in specialty_text else 1 for term in terms if term in searchable)
            if not score:
                continue
            if not query_is_pediatric and "nhi" in specialty_text:
                score -= 3
            source_url = str(record.get("source_url") or "")
            if "vinmec.com" not in source_url.lower():
                continue
            years = _experience_years(record.get("years_of_experience"))
            scored.append((score, years, record))
        scored.sort(key=lambda item: (item[0], item[1], bool(item[2].get("profile_id"))), reverse=True)

        results: list[dict[str, Any]] = []
        for _, years, record in scored[:limit_doctors]:
            sections = record.get("sections") or {}
            workplaces = record.get("workplace") or sections.get("Nơi làm việc") or []
            if isinstance(workplaces, str):
                workplaces = [workplaces]
            if requested_facility_key:
                workplaces = [
                    workplace for workplace in workplaces if facility_key(workplace) == requested_facility_key
                ]
            credentials = record.get("credentials") or []
            positions = record.get("positions") or []
            title = ", ".join(credentials) or (positions[0] if positions else "Bác sĩ chuyên khoa")
            identifier = str(record.get("profile_id") or record.get("source_url"))
            results.append(
                {
                    "id": f"crawl-{identifier}",
                    "full_name": record.get("name") or "Bác sĩ chuyên khoa",
                    "title": title,
                    "years_of_experience": years,
                    "languages": [record.get("language") or "vi"],
                    "specialties": record.get("specialties") or [],
                    "workplace": workplaces[0] if workplaces else "",
                    "overview": str(record.get("overview") or "").strip(),
                    "source_url": record.get("source_url"),
                    "image_url": record.get("image_url"),
                    "data_source": "vinmec_crawl",
                    "schedule_verified": False,
                    "available_slots": [],
                }
            )
        return results

    def get_available_doctors_and_slots(
        self,
        specialty_name: str | None = None,
        limit_doctors: int = 3,
        slots_per_doctor: int = 2,
        requested_days: int | None = None,
        preferred_period: str | None = None,
        facility_id: str | None = None,
    ) -> list[dict[str, Any]]:
        facility = None
        try:
            facility = self.find_facility(facility_id) if facility_id else None
            doctors = (
                []
                if facility_id and not facility
                else self._database_doctors(
                    specialty_name,
                    limit_doctors,
                    slots_per_doctor,
                    requested_days,
                    preferred_period,
                    facility,
                )
            )
            if doctors:
                return doctors
        except Exception as exc:
            logger.warning("Supabase doctor/schedule lookup failed; using sourced crawl: %s", type(exc).__name__)
        facility_query = str((facility or {}).get("name") or facility_id or "") or None
        return self._crawled_doctors(specialty_name, limit_doctors, facility_query)

    def hold_slot(self, slot_id: str, available_doctors: list[dict[str, Any]] | None = None) -> bool:
        """Legacy compatibility: never report an in-memory hold as a DB booking."""
        del slot_id, available_doctors
        return False


_doctor_schedule_service: DoctorScheduleService | None = None


def get_doctor_schedule_service() -> DoctorScheduleService:
    global _doctor_schedule_service
    if _doctor_schedule_service is None:
        _doctor_schedule_service = DoctorScheduleService()
    return _doctor_schedule_service


async def fetch_available_doctors_slots(
    specialty_name: str | None,
    requested_days: int | None = None,
    preferred_period: str | None = None,
    facility_id: str | None = None,
    limit_doctors: int = 3,
    slots_per_doctor: int = 2,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Truy vấn danh sách bác sĩ và slot rảnh từ Supabase/service một cách an toàn.

    Returns:
        tuple (available_slots, data_unavailable, data_unavailable_reason)
    """
    import asyncio

    try:
        doctor_service = get_doctor_schedule_service()
    except ValueError as exc:
        logger.warning("Supabase schedule service not configured: %s", exc)
        return [], True, "DATABASE_NOT_CONFIGURED"
    except Exception as exc:
        logger.warning("Supabase schedule service initialization failed: %s (%s)", type(exc).__name__, exc)
        return [], True, f"INIT_ERROR: {type(exc).__name__}"

    try:
        doctors_with_slots = await asyncio.to_thread(
            doctor_service.get_available_doctors_and_slots,
            specialty_name=specialty_name,
            limit_doctors=limit_doctors,
            slots_per_doctor=slots_per_doctor,
            requested_days=requested_days,
            preferred_period=preferred_period,
            facility_id=facility_id,
        )
        return doctors_with_slots, False, None
    except Exception as exc:
        logger.error(
            "Querying doctor slots failed for specialty '%s': %s (%s)",
            specialty_name,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return [], True, f"QUERY_ERROR: {type(exc).__name__}"


_TURN_SLOT_CACHE: dict[tuple[str, int, str | None, str | None], tuple[list[dict[str, Any]], bool, str | None]] = {}


def clear_turn_slot_cache() -> None:
    """Xóa cache slot lượt hội thoại (phục vụ test)."""
    _TURN_SLOT_CACHE.clear()


async def fetch_available_doctors_slots_cached(
    state: dict[str, Any] | None = None,
    specialty_name: str | None = None,
    requested_days: int | None = None,
    preferred_period: str | None = None,
    facility_id: str | None = None,
    limit_doctors: int = 3,
    slots_per_doctor: int = 2,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Truy vấn slot có cache theo thread_id + lượt trong state.

    Đảm bảo trong 1 lượt hội thoại, analyze_node, find_doctors_node và respond_node
    chỉ gọi truy vấn DB duy nhất một lần.
    """
    state_dict = state or {}
    meta = state_dict.get("metadata") or {}

    # 1. Nếu state đã có kết quả trong cùng lượt -> trả về ngay
    if meta.get("slots_fetched_in_turn") and state_dict.get("available_slots") is not None:
        return (
            state_dict.get("available_slots") or [],
            bool(meta.get("data_unavailable")),
            meta.get("data_unavailable_reason"),
        )

    # 2. Kiểm tra bộ nhớ cache theo thread_id và turn
    thread_id = (
        state_dict.get("session_id")
        or state_dict.get("thread_id")
        or meta.get("session_id")
        or meta.get("thread_id")
        or "default_session"
    )
    turn = (
        state_dict.get("probing_turn")
        or len([m for m in (state_dict.get("messages") or []) if isinstance(m, dict) and m.get("role") == "user"])
        or 0
    )
    cache_key = (str(thread_id), int(turn), specialty_name, facility_id)
    if cache_key in _TURN_SLOT_CACHE:
        return _TURN_SLOT_CACHE[cache_key]

    # 3. Thực hiện truy vấn thực tế
    res = await fetch_available_doctors_slots(
        specialty_name=specialty_name,
        requested_days=requested_days,
        preferred_period=preferred_period,
        facility_id=facility_id,
        limit_doctors=limit_doctors,
        slots_per_doctor=slots_per_doctor,
    )
    _TURN_SLOT_CACHE[cache_key] = res
    return res

