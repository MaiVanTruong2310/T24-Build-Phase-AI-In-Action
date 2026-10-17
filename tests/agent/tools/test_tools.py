"""Comprehensive unit tests for read-only medical assistant tools."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.medical_assistant.agent.tools import (
    ALL_TOOLS,
    get_department_info,
    get_doctor_detail,
    get_doctor_slots,
    list_facilities,
    search_disease_knowledge,
    search_doctors,
)


class TestMedicalTools(unittest.TestCase):
    FACILITIES = [
        {
            "id": "times-city",
            "name": "Vinmec Times City",
            "address": "458 Minh Khai, Hai Ba Trung, Ha Noi",
            "phone": "1900",
        },
        {"id": "central-park", "name": "Vinmec Central Park", "address": "Ho Chi Minh City", "phone": "1900"},
    ]

    def mock_facilities(self, service_cls):
        service = service_cls.return_value
        service.fetch_active_facilities.return_value = self.FACILITIES
        service._find_detail_metadata.return_value = {}
        return service

    def test_all_tools_exported(self):
        self.assertEqual(len(ALL_TOOLS), 6)
        names = {t.name for t in ALL_TOOLS}
        expected = {
            "search_doctors",
            "get_doctor_detail",
            "get_doctor_slots",
            "get_department_info",
            "search_disease_knowledge",
            "list_facilities",
        }
        self.assertEqual(names, expected)

    # =========================================================================
    # 1. search_doctors
    # =========================================================================
    def test_search_doctors_crawled_by_specialty(self):
        # Tim mạch luôn có bác sĩ trong dataset
        result = search_doctors.invoke({"specialty": "Tim mạch", "limit": 3})
        self.assertTrue(result["found"])
        self.assertGreaterEqual(result["count"], 1)
        self.assertLessEqual(result["count"], 3)
        self.assertIn("source", result)
        doc = result["doctors"][0]
        self.assertIn("full_name", doc)
        self.assertIn("title", doc)
        self.assertIn("experience_display", doc)

    def test_search_doctors_with_min_experience(self):
        result = search_doctors.invoke({"specialty": "Nhi", "min_experience_years": 10, "limit": 2})
        if result["found"]:
            for doc in result["doctors"]:
                if doc.get("years_of_experience") is not None:
                    self.assertGreaterEqual(doc["years_of_experience"], 10)

    def test_search_doctors_not_found(self):
        result = search_doctors.invoke({"name": "TenBacSiKhongTonTai12345XYZ"})
        self.assertFalse(result["found"])
        self.assertEqual(result["count"], 0)
        self.assertIn("reason", result)

    def test_search_doctors_limit_capping(self):
        result = search_doctors.invoke({"specialty": "Tiêu hóa", "limit": 5})
        if result["found"]:
            self.assertLessEqual(len(result["doctors"]), 5)

    # =========================================================================
    # 2. get_doctor_detail
    # =========================================================================
    def test_get_doctor_detail_crawl_record(self):
        # Tra cứu bác sĩ từ crawl data
        search_res = search_doctors.invoke({"specialty": "Thần kinh", "limit": 1})
        self.assertTrue(search_res["found"])
        doc_id = search_res["doctors"][0]["id"]

        detail = get_doctor_detail.invoke({"doctor_id": doc_id})
        self.assertTrue(detail["found"])
        self.assertEqual(detail["doctor_id"], doc_id)
        self.assertIn("full_name", detail)
        self.assertIn("source", detail)

    def test_get_doctor_detail_not_found(self):
        detail = get_doctor_detail.invoke({"doctor_id": "crawl-non-existent-99999"})
        self.assertFalse(detail["found"])
        self.assertIn("reason", detail)

    def test_get_doctor_detail_empty_id(self):
        detail = get_doctor_detail.invoke({"doctor_id": ""})
        self.assertFalse(detail["found"])

    # =========================================================================
    # 3. get_doctor_slots
    # =========================================================================
    def test_get_doctor_slots_crawl_doctor_returns_contact_notice(self):
        # Bác sĩ crawl chưa có online slot
        res = get_doctor_slots.invoke({"doctor_id": "crawl-profile-12345"})
        self.assertFalse(res["found"])
        self.assertIn("reason", res)
        self.assertEqual(res["slots"], [])

    def test_get_doctor_slots_supabase_mock(self):
        mock_client = MagicMock()
        mock_client.select.return_value = [
            {
                "id": "slot-uuid-1",
                "doctor_id": "00000000-0000-0000-0000-000000000001",
                "status": "available",
                "starts_at": "2026-10-15T02:00:00Z",  # 09:00 GMT+7
                "ends_at": "2026-10-15T02:30:00Z",
                "facility_id": "fac-1",
            },
            {
                "id": "slot-uuid-2",
                "doctor_id": "00000000-0000-0000-0000-000000000001",
                "status": "available",
                "starts_at": "2026-10-15T07:00:00Z",  # 14:00 GMT+7
                "ends_at": "2026-10-15T07:30:00Z",
                "facility_id": "fac-1",
            },
        ]

        with patch("src.medical_assistant.agent.tools.doctor_tools.get_doctor_schedule_service") as mock_svc_getter:
            mock_svc = MagicMock()
            mock_svc.client = mock_client
            mock_svc_getter.return_value = mock_svc

            res = get_doctor_slots.invoke(
                {
                    "doctor_id": "00000000-0000-0000-0000-000000000001",
                    "from_date": "2026-10-15",
                    "days": 7,
                    "period": "morning",
                }
            )
            self.assertTrue(res["found"])
            self.assertEqual(res["count"], 1)
            self.assertIn("09:00", res["slots"][0]["starts_at"])
            self.assertIn("Sáng", res["slots"][0]["starts_at"])
            self.assertEqual(res["slots"][0]["slot_id"], "slot-uuid-1")

    # =========================================================================
    # 4. get_department_info
    # =========================================================================
    def test_get_department_info_success(self):
        res = get_department_info.invoke({"department_key": "TIM_MACH"})
        self.assertTrue(res["found"])
        self.assertIn("department_name", res)
        self.assertIn("summary", res)
        self.assertIn("source", res)

    def test_get_department_info_empty(self):
        res = get_department_info.invoke({"department_key": ""})
        self.assertFalse(res["found"])

    # =========================================================================
    # 5. search_disease_knowledge
    # =========================================================================
    def test_search_disease_knowledge_found(self):
        res = search_disease_knowledge.invoke({"query": "dạ dày", "limit": 2})
        self.assertTrue(res["found"])
        self.assertGreaterEqual(res["count"], 1)
        self.assertLessEqual(res["count"], 2)
        d = res["diseases"][0]
        self.assertIn("disease_name", d)
        self.assertIn("primary_specialty_name", d)
        self.assertIn("ats_level", d)
        self.assertIn("disclaimer", res)

    def test_search_disease_knowledge_not_found(self):
        res = search_disease_knowledge.invoke({"query": "benhxyzkhongcochutnao9999"})
        self.assertFalse(res["found"])
        self.assertIn("reason", res)

    # =========================================================================
    # 6. list_facilities
    # =========================================================================
    @patch("src.medical_assistant.agent.tools.facility_tools.FacilityService")
    def test_list_facilities_all(self, service_cls):
        self.mock_facilities(service_cls)
        res = list_facilities.invoke({})
        self.assertTrue(res["found"])
        self.assertGreaterEqual(res["count"], 1)
        fac = res["facilities"][0]
        self.assertIn("name", fac)
        self.assertIn("address", fac)
        self.assertIn("facility_type", fac)

    @patch("src.medical_assistant.agent.tools.facility_tools.FacilityService")
    def test_list_facilities_filter_hanoi(self, service_cls):
        self.mock_facilities(service_cls)
        res = list_facilities.invoke({"region": "Ha Noi"})
        self.assertTrue(res["found"])
        for fac in res["facilities"]:
            self.assertTrue("ha noi" in fac["address"].lower() or "ha noi" in fac["name"].lower())

    @patch("src.medical_assistant.agent.tools.facility_tools.FacilityService")
    def test_list_facilities_filter_times_city(self, service_cls):
        self.mock_facilities(service_cls)
        res = list_facilities.invoke({"name": "Times City"})
        self.assertTrue(res["found"])
        self.assertTrue(any("times city" in fac["name"].lower() for fac in res["facilities"]))

    @patch("src.medical_assistant.agent.tools.facility_tools.FacilityService")
    def test_list_facilities_not_found(self, service_cls):
        self.mock_facilities(service_cls)
        res = list_facilities.invoke({"region": "DiaDanhKhongTonTai12345"})
        self.assertFalse(res["found"])
        self.assertEqual(res["count"], 0)


if __name__ == "__main__":
    unittest.main()
