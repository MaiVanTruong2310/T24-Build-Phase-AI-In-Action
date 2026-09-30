import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.doctor_schedule_service import DoctorScheduleService
from src.medical_assistant.domain.guardrail_service import ClinicalGuardrailService


def test_department_comparison_is_detected_and_grounded():
    service = ClinicalGuardrailService()
    intent = service.check_intent(
        "Thế khoa tiêu hóa của mình có ưu điểm gì hơn so với các bệnh viện khác",
        current_department="TIEU_HOA",
        language="vi",
    )

    assert intent["intent"] == "DEPARTMENT_INFO"
    assert intent["department_query"] == "tiêu hóa"
    assert intent["comparison_requested"] is True

    response, _ = service.get_department_info_response(
        intent["department_query"], language="vi", comparison_requested=True
    )
    lowered = response.lower()
    assert "chưa có dữ liệu đối chiếu" in lowered
    assert "vinmec.com" in lowered
    assert "mũi nhọn" not in lowered


def test_schedule_code_alias_and_slot_hold_validation():
    class EmptyDatabaseClient:
        def select(self, table, params=None):
            return []

    service = DoctorScheduleService(client=EmptyDatabaseClient())
    doctors = service.get_available_doctors_and_slots(
        specialty_name="TIEU_HOA", preferred_period="afternoon", slots_per_doctor=2
    )

    assert doctors
    assert all(doctor["data_source"] == "vinmec_crawl" for doctor in doctors)
    assert all("vinmec.com" in doctor["source_url"] for doctor in doctors)
    slots = [slot for doctor in doctors for slot in doctor["available_slots"]]
    assert not slots
    assert service.hold_slot("deadbeef", doctors) is False


@pytest.mark.asyncio
async def test_nearest_facility_query_does_not_depend_on_clinical_department_state():
    result = await agent.ainvoke(
        {"query": "Bệnh viện gần Hồ Hoàn Kiếm nhất"},
        config={"configurable": {"thread_id": "facility-hoan-kiem-no-clinical-context"}},
    )

    assert result["workflow_status"] == "FACILITY_INFO"
    assert result["response"]


def test_specific_department_info_request_is_detected():
    intent = ClinicalGuardrailService().check_intent(
        "Thế cho tôi xin thông tin cụ thể của khoa tiêu hóa đi",
        current_department="TIEU_HOA",
        language="vi",
    )
    assert intent["intent"] == "DEPARTMENT_INFO"
    assert intent["department_query"] == "tiêu hóa"
