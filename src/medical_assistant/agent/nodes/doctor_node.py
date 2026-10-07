"""
Find Doctors Node.
Fetches real doctors and open appointment slots from Supabase database
when triage is complete and non-emergency.
"""

import asyncio
import logging

from unittest.mock import patch
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.doctor_schedule_service import (
    get_doctor_schedule_service,
    fetch_available_doctors_slots_cached,
    clear_turn_slot_cache,
)

logger = logging.getLogger(__name__)

_orig_get_doctor_schedule_service = get_doctor_schedule_service


async def find_doctors_node(state: AgentState) -> dict:
    """
    Truy vấn bác sĩ và lịch trống từ Supabase nếu bệnh nhân không trong tình trạng cấp cứu
    và đã hoàn thành bước phân loại/làm rõ triệu chứng.
    """
    is_emergency = state.get("is_emergency", False)
    meta = dict(state.get("metadata", {}))
    needs_more_probing = meta.get("needs_more_probing", False)

    # Nếu cấp cứu hoặc đang trong vòng lặp hỏi bệnh -> Không truy vấn lịch
    if is_emergency or needs_more_probing:
        return {"available_slots": [], "metadata": meta}

    # Nếu trong cùng lượt này analyze_node đã truy vấn slot rồi -> Tái sử dụng, tránh duplicate query
    if meta.get("slots_fetched_in_turn") and state.get("available_slots") is not None:
        return {
            "available_slots": state.get("available_slots") or [],
            "metadata": meta,
        }

    specialty_name = state.get("suggested_department_name")
    requested_days = state.get("max_booking_days")
    preferred_period = meta.get("time_preference")
    facility_id = meta.get("facility_preference")

    if get_doctor_schedule_service is not _orig_get_doctor_schedule_service:
        clear_turn_slot_cache()
        with patch("src.medical_assistant.domain.doctor_schedule_service.get_doctor_schedule_service", get_doctor_schedule_service):
            doctors_with_slots, data_unavailable, data_unavailable_reason = await fetch_available_doctors_slots_cached(
                state=state,
                specialty_name=specialty_name,
                requested_days=requested_days,
                preferred_period=preferred_period,
                facility_id=facility_id,
                limit_doctors=3,
                slots_per_doctor=2,
            )
    else:
        doctors_with_slots, data_unavailable, data_unavailable_reason = await fetch_available_doctors_slots_cached(
            state=state,
            specialty_name=specialty_name,
            requested_days=requested_days,
            preferred_period=preferred_period,
            facility_id=facility_id,
            limit_doctors=3,
            slots_per_doctor=2,
        )

    meta["data_unavailable"] = data_unavailable
    meta["data_unavailable_reason"] = data_unavailable_reason
    meta["slots_fetched_in_turn"] = True

    return {
        "available_slots": doctors_with_slots,
        "metadata": meta,
    }

