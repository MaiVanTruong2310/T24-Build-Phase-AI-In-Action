"""list_facilities(specialty=...): chỉ trả về cơ sở thực sự có khoa (suy từ nơi làm việc của bác sĩ).

Lỗi gốc (14/10/2026): "cơ sở nào có trung tâm chăm sóc sức khỏe tinh thần tại Hà Nội" → bot liệt kê cả 6 cơ sở Hà Nội
rồi tự nhận "chưa rõ cơ sở nào có", trong khi dữ liệu bác sĩ cho thấy chỉ Times City có.
"""

from unittest.mock import patch

import pytest

import src.medical_assistant.agent.tools.facility_tools as ft

FACILITIES = [
    {
        "id": "1",
        "name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        "address": "Số 458 Minh Khai, Phường Vĩnh Tuy, Hà Nội",
    },
    {
        "id": "2",
        "name": "Phòng khám Đa khoa Quốc tế Vinmec Times City",
        "address": "Số 458 Minh Khai, P. Vĩnh Tuy, Hà Nội",
    },
    {
        "id": "3",
        "name": "Bệnh viện Đa khoa Quốc tế Vinmec Smart City",
        "address": "Số 2A, đường Tây Mỗ, phường Tây Mỗ, Hà Nội",
    },
    {"id": "4", "name": "Bệnh viện Đa khoa Quốc tế Vinmec Central Park", "address": "208 Nguyễn Hữu Cảnh, Hồ Chí Minh"},
    {"id": "5", "name": "Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng", "address": "30 tháng 4, Đà Nẵng"},
]
DEPARTMENTS = [
    {
        "department": "Trung tâm Chăm sóc Sức khỏe Tinh Thần",
        "facilities": {"name": "Vinmec Times City International Hospital"},
    },
    {"department": "Trung tâm Thần kinh", "facilities": {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City"}},
    {"department": "Khoa Nhi - Sơ sinh", "facilities": {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Smart City"}},
    {"department": "Khoa Răng Hàm Mặt", "facilities": {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Smart City"}},
    {
        "department": "Đơn vị Sức khỏe Tâm thần - Khoa khám bệnh & Nội khoa",
        "facilities": {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Central Park"},
    },
    {"department": "Truyền nhiễm", "facilities": {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng"}},
]


@pytest.fixture(autouse=True)
def fake_data():
    with (
        patch.object(ft.FacilityService, "fetch_active_facilities", return_value=FACILITIES),
        patch.object(ft.FacilityService, "_get_client", return_value=None),
        patch.object(ft, "_department_rows", return_value=DEPARTMENTS),
    ):
        yield


def _names(**kw):
    return [f["name"] for f in ft.list_facilities.invoke(kw).get("facilities", [])]


@pytest.mark.parametrize("spec", ["trung tâm chăm sóc sức khỏe tinh thần", "sức khỏe tinh thần", "tâm lý"])
def test_mental_health_in_hanoi_is_only_times_city_hospital(spec):
    assert _names(region="Hà Nội", specialty=spec) == ["Bệnh viện Đa khoa Quốc tế Vinmec Times City"]


def test_tam_than_matches_mental_health_not_neurology():
    # "trung tâm thần kinh" bỏ dấu chứa "tam than" — không được khớp
    names = _names(specialty="tam than")
    assert "Bệnh viện Đa khoa Quốc tế Vinmec Central Park" in names
    assert (
        "Bệnh viện Đa khoa Quốc tế Vinmec Times City" in names
    )  # nhờ Trung tâm Sức khỏe Tinh thần, không nhờ Thần kinh
    r = ft.list_facilities.invoke({"specialty": "tam than"})
    times = next(f for f in r["facilities"] if "Times City" in f["name"])
    assert times["matched_departments"] == ["Trung tâm Chăm sóc Sức khỏe Tinh Thần"]


def test_single_syllable_specialty_needs_unit_word():
    # "Nhi" không được khớp "Truyền nhiễm"
    assert _names(specialty="Nhi") == ["Bệnh viện Đa khoa Quốc tế Vinmec Smart City"]


def test_unknown_specialty_returns_not_found_instead_of_all_facilities():
    r = ft.list_facilities.invoke({"region": "Hà Nội", "specialty": "khoa bay vào vũ trụ"})
    assert r["found"] is False and r["facilities"] == []


def test_specialty_missing_in_region_says_where_it_exists():
    r = ft.list_facilities.invoke({"region": "Đà Nẵng", "specialty": "sức khỏe tinh thần"})
    assert r["found"] is False
    assert set(r["specialty_available_at"]) == {
        "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        "Bệnh viện Đa khoa Quốc tế Vinmec Central Park",
    }


def test_without_specialty_behaviour_unchanged():
    assert len(_names(region="Hà Nội")) == 3


# ------------------------------------------------------------------ lọc theo phường/đường lấy từ địa chỉ cơ sở
def test_ward_from_facility_addresses_filters_list():
    from src.medical_assistant.agent.nodes import info_fallback

    folded = info_fallback._fold("Ở khu vực vĩnh tuy Hà nội có những cơ sở y tế nào?")
    assert info_fallback.detect_locality(folded) == "vinh tuy"
    text, tool, data = info_fallback.answer_info_without_llm("Ở khu vực vĩnh tuy Hà nội có những cơ sở y tế nào?")
    assert tool == "list_facilities" and [f["name"] for f in data["facilities"]] == [
        "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        "Phòng khám Đa khoa Quốc tế Vinmec Times City",
    ]


def test_numbers_in_addresses_do_not_become_localities():
    from src.medical_assistant.agent.nodes import info_fallback

    assert info_fallback._locality_terms("Đường 30 tháng 4, Tầng 2, Khu dân cư số 4, Phường Hòa Cường") == {"hoa cuong"}
    assert info_fallback.detect_locality(info_fallback._fold("cơ sở nào khám ngày 30 tháng 4")) is None
