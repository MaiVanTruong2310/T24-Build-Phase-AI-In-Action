"""
Find Doctors Node.
Fetches real doctors and open appointment slots from Supabase database
when triage is complete and non-emergency.
"""

from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.doctor_schedule_service import get_doctor_schedule_service


async def find_doctors_node(state: AgentState) -> dict:
    """
    Truy vấn bác sĩ và lịch trống từ Supabase nếu bệnh nhân không trong tình trạng cấp cứu
    và đã hoàn thành bước phân loại/làm rõ triệu chứng.
    """
    is_emergency = state.get("is_emergency", False)
    meta = state.get("metadata", {})
    needs_more_probing = meta.get("needs_more_probing", False)

    # Nếu cấp cứu hoặc đang trong vòng lặp hỏi bệnh -> Không truy vấn lịch
    if is_emergency or needs_more_probing:
        return {"available_slots": []}

    specialty_name = state.get("suggested_department_name")

    requested_days = state.get("max_booking_days")
    preferred_period = meta.get("time_preference")
    facility_id = meta.get("facility_preference")

    try:
        doctor_service = get_doctor_schedule_service()
    except ValueError:
        # The chat API must remain available in local/test environments where
        # Supabase is intentionally not configured. Availability simply stays
        # unverified until a database connection is provided.
        return {"available_slots": []}

    doctors_with_slots = doctor_service.get_available_doctors_and_slots(
        specialty_name=specialty_name,
        limit_doctors=3,
        slots_per_doctor=2,
        requested_days=requested_days,
        preferred_period=preferred_period,
        facility_id=facility_id
    )

    return {
        "available_slots": doctors_with_slots,
    }
