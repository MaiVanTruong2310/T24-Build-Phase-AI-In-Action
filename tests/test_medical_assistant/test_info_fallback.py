"""Tra cứu cơ sở / bác sĩ không cần LLM + chỉ gợi ý bác sĩ (không gợi ý điều dưỡng, dược sĩ)."""

from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes import info_fallback
from src.medical_assistant.domain.doctor_schedule_service import is_physician

FACILITIES = {
    "found": True,
    "facilities": [
        {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City", "address": "Số 458 Minh Khai", "phone": "024"},
        {"name": "Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng", "address": "Đường 30 tháng 4", "phone": "0236"},
    ],
}


class _Tool:
    def __init__(self, fn):
        self.fn = fn
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return self.fn(args)


@pytest.fixture
def tools():
    facilities = _Tool(lambda args: FACILITIES)
    doctors = _Tool(lambda args: {"found": True, "doctors": [{"full_name": "BS A", "title": "Bác sĩ"}]})
    with (
        patch.object(info_fallback, "list_facilities", facilities),
        patch.object(info_fallback, "search_doctors", doctors),
    ):
        yield facilities, doctors


def test_facility_address_question_is_answered_from_db(tools):
    facilities, _ = tools
    text, tool, _ = info_fallback.answer_info_without_llm("Địa chỉ Vinmec Times City ở đâu?")
    assert tool == "list_facilities" and "458 Minh Khai" in text
    assert facilities.calls[-1]["name"] == "Times City"


def test_region_question_passes_region(tools):
    facilities, _ = tools
    info_fallback.answer_info_without_llm("Ở TP.HCM có bệnh viện Vinmec nào không?")
    assert facilities.calls[-1]["region"] == "hồ chí minh"


@pytest.mark.parametrize(
    ("query", "specialty"),
    [
        ("Cho em xem bác sĩ nhi ở Vinmec Times City", "Nhi khoa"),
        ("bác sĩ khám mắt ở Vinmec Đà Nẵng", "Mắt (Nhãn khoa)"),
        ("Bác sĩ nào khám tim mạch giỏi?", "Trung tâm Tim mạch"),
    ],
)
def test_doctor_question_detects_specialty(tools, query, specialty):
    _, doctors = tools
    _, tool, _ = info_fallback.answer_info_without_llm(query)
    assert tool == "search_doctors" and doctors.calls[-1]["specialty"] == specialty


def test_unrelated_question_returns_none(tools):
    assert info_fallback.answer_info_without_llm("hôm nay thời tiết thế nào") is None


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Bác sĩ chuyên khoa II", True),
        ("Thạc sĩ, Bác sĩ nội trú", True),
        ("Điều dưỡng", False),
        ("Cử nhân, Dược sĩ", False),
        ("Thạc sĩ, Kỹ thuật viên", False),
        (["Phó giáo sư", "Tiến sĩ"], True),
    ],
)
def test_is_physician(title, expected):
    assert is_physician(title) is expected
