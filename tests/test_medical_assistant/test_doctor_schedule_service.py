from src.medical_assistant.domain.doctor_schedule_service import DoctorScheduleService


class EmptyDatabaseClient:
    def select(self, table, params=None):
        return []


def test_crawled_doctor_fallback_is_sourced_and_has_no_fake_slots():
    svc = DoctorScheduleService(client=EmptyDatabaseClient())
    docs = svc.get_available_doctors_and_slots(specialty_name="Tiêu hóa - Gan mật", limit_doctors=3, slots_per_doctor=2)

    assert len(docs) == 3
    assert all(doc["data_source"] == "vinmec_crawl" for doc in docs)
    assert all(doc["schedule_verified"] is False for doc in docs)
    assert all(doc["available_slots"] == [] for doc in docs)
    assert all(doc["source_url"].startswith("https://www.vinmec.com/") for doc in docs)
    assert {doc["full_name"] for doc in docs}.isdisjoint({"ThS.BS Lê Thị Mai", "PGS.TS Vũ Văn Khiêm"})


def test_doctor_information_followup_uses_schedule_search_intent():
    from src.medical_assistant.domain.guardrail_service import ClinicalGuardrailService

    intent = ClinicalGuardrailService().check_intent(
        "Cho tôi xin thông tin của các bác sĩ trong khoa này",
        current_department="Tiêu hóa - Gan mật",
    )
    assert intent["intent"] == "VIEW_SCHEDULE"
    assert intent["doctor_info_only"] is True
