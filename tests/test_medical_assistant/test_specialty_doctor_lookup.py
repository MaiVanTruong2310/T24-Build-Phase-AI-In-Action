"""Gợi ý chuyên khoa → tìm khoa trong danh mục để lấy bác sĩ (DB giả lập, không cần mạng)."""

import pytest

from src.medical_assistant.domain.doctor_schedule_service import DoctorScheduleService

CATALOG = {
    "Tai mũi họng": 20,
    "Women's Health Center": 40,
    "Breast Center": 30,
    "Răng - Hàm - Mặt": 15,
    "Mắt": 25,
    "Thần kinh": 10,
    "Ngoại Thần kinh": 30,
    "Nội Thần kinh": 8,
    "Hô hấp": 12,
    "Nhi Hô hấp": 25,
    "Nội Hô hấp": 9,
    "Nội Thận - Tiết niệu": 7,
    "Neurology": 5,
    "Tiêu hóa - Gan mật": 6,
    "Ngoại Tiêu hoá": 30,
}


class FakeClient:
    def __init__(self):
        self.ids = {name: f"id-{i}" for i, name in enumerate(CATALOG)}

    def select(self, table, params=None):
        params = params or {}
        if table == "specialties":
            term = params["name"].removeprefix("ilike.*").removesuffix("*").lower()
            return [{"id": self.ids[n], "code": n, "name": n} for n in CATALOG if term in n.lower()]
        if table == "doctor_specialties":
            spec_id = params["specialty_id"].removeprefix("eq.")
            name = next(n for n, i in self.ids.items() if i == spec_id)
            return [{"doctor_id": k} for k in range(CATALOG[name])]
        return []


def _top(query: str, k: int = 3) -> list[str]:
    return [s["name"] for s in DoctorScheduleService(client=FakeClient()).find_candidate_specialties(query)[:k]]


def test_ent_does_not_pull_womens_or_breast_center():
    assert _top("Tai - Mũi - Họng") == ["Tai mũi họng"]


def test_dental_is_not_routed_to_ophthalmology():
    top = _top("Răng Hàm Mặt")
    assert top[0] == "Răng - Hàm - Mặt" and "Mắt" not in top


def test_urology_does_not_match_neurology():
    assert "Neurology" not in _top("Thận - Tiết niệu")


@pytest.mark.parametrize(
    ("query", "first"),
    [("Thần kinh", "Thần kinh"), ("Nội hô hấp", "Nội Hô hấp"), ("Tiêu hóa - Gan mật", "Tiêu hóa - Gan mật")],
)
def test_exact_medical_specialty_beats_surgical_or_bigger(query, first):
    assert _top(query)[0] == first


def test_adult_query_excludes_pediatric_subspecialty():
    assert "Nhi Hô hấp" not in _top("Nội hô hấp")


def test_pediatric_query_keeps_pediatric_subspecialty_first():
    assert _top("Nhi Hô hấp")[0] == "Nhi Hô hấp"
