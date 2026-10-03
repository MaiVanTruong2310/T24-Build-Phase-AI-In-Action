from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """State schema cho LangGraph y tế VMEC-01.

    Mỗi node đọc và cập nhật các trường trong state này.
    """

    # Quản lý tin nhắn & lượt hội thoại
    query: str
    analysis: str
    user_id: str
    patient_name: str | None
    patient_phone: str | None
    patient_dob: str | None
    patient_gender: str | None
    patient_email: str | None
    facility_preference: str | None
    preferred_date: str | None
    preferred_period: str | None
    is_authenticated: bool | None
    patient_health_record: dict[str, Any] | None
    patient_profile: dict[str, str] | None
    messages: list[dict[str, str]]
    user_input: str
    language: str | None  # 'vi' hoặc 'en'
    enable_citation: bool | None

    # Thông tin triệu chứng & Y tế
    symptoms: list[str]
    is_emergency: bool
    emergency_warning: str | None
    ats_level: int | None
    urgency_tier: str | None
    max_booking_days: int | None
    acuity_status: str | None
    disposition: str | None
    probing_turn: int | None
    active_probing_category: str | None
    active_probing_categories: list[str]
    probing_by_complaint: dict[str, dict[str, Any]]
    collected_details: list[str] | None
    clinical_facts: dict[str, Any] | None

    # Định hướng chuyên khoa & Bác sĩ
    suggested_department_code: str | None
    suggested_department_name: str | None
    candidate_specialties: list[dict[str, Any]]
    routing_candidates: list[dict[str, Any]]
    conflict_reason: str | None
    recommended_doctor_id: str | None

    # Slot khám & Giữ chỗ
    available_slots: list[dict[str, Any]]
    selected_slot: dict[str, Any] | None
    booking_id: str | None
    booking_code: str | None

    # Trạng thái quy trình & HITL
    # IDLE | EMERGENCY | TRIAGED | SLOT_HELD | WAITING_RECEPTION_APPROVAL | CONFIRMED | REJECTED
    workflow_status: str

    # Trả lời & Disclaimer
    response: str
    disclaimer: str
    error: str | None
    token_usage: dict[str, Any]
    metadata: dict[str, Any]
