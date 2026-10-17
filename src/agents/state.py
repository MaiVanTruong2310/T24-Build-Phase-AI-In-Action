from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """State schema toàn diện cho LangGraph Agent (VCare Production).

    Hỗ trợ đầy đủ luồng xử lý:
    - User input / Conversation turns
    - Triage triệu chứng & ATS Level
    - Adaptive Fact-Aware Probing
    - Gợi ý chuyên khoa & Tìm kiếm bác sĩ
    - Quản lý bộ nhớ phiên (SOAP Notes, Cross-session memory)
    - Reflexion loop & Clinical Critic
    """

    # 1. Quản lý tin nhắn & lượt hội thoại
    query: str
    user_input: str
    messages: list[dict[str, str]]
    user_id: str
    session_id: str
    response: str
    analysis: str
    disclaimer: str
    token_usage: dict[str, Any]
    context: str
    error: str | None
    language: str | None  # 'vi' hoặc 'en'
    metadata: dict[str, Any]

    # 2. Thông tin bệnh nhân & hồ sơ
    patient_name: str | None
    patient_phone: str | None
    patient_dob: str | None
    patient_gender: str | None
    patient_email: str | None
    is_authenticated: bool | None
    patient_health_record: dict[str, Any] | None
    patient_profile: dict[str, str] | None
    patient_memory_profile: list[dict[str, Any]] | None
    active_open_loops: list[dict[str, Any]] | None
    durable_soap_note: str | None
    enable_citation: bool | None

    # 3. Thông tin triệu chứng & Phân loại lâm sàng (Triage)
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

    # 4. Định hướng chuyên khoa & Đặt lịch
    suggested_department_code: str | None
    suggested_department_name: str | None
    candidate_specialties: list[dict[str, Any]]
    routing_candidates: list[dict[str, Any]]
    conflict_reason: str | None
    recommended_doctor_id: str | None
    doctor_preference: str | None
    doctor_name: str | None
    facility_preference: str | None
    preferred_date: str | None
    preferred_period: str | None
    booking_confirmed: bool | None
    available_slots: list[dict[str, Any]]
    selected_slot: dict[str, Any] | None
    booking_id: str | None
    booking_code: str | None
    booking_intake: dict[str, Any] | None

    # 5. Phản tư lâm sàng (Reflexion loop)
    critic_status: str | None  # 'PASS' | 'REVISE'
    critic_feedback: str | None
    critic_reason: str | None
    critic_suggested_department: str | None
    critic_evidence_snippets: list[str] | None
    critic_evidence_count: int | None
    reflection_count: int | None
    workflow_status: str | None
