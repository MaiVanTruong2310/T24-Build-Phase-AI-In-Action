"""Tra cứu thông tin bệnh viện / bác sĩ / chuyên khoa khi LLM tắt — hồi quy 2026-10-10."""

from unittest.mock import MagicMock, patch

import pytest

from src.medical_assistant.agent.nodes.analyze_node import _pick_listed_doctor
from src.medical_assistant.agent.nodes.router_node import _rule_based_fallback_route, route_intent_node
from src.medical_assistant.domain.booking_slot_service import extract_booking_entities
from src.medical_assistant.domain.cache_service import get_cache_service

OFFLINE = RuntimeError("Offline test mode - LLM network disabled")


@pytest.mark.parametrize(
    ("query", "route"),
    [
        # "bảo hiểm" chứa "hi", "thoại" chứa "ho": không được khớp chuỗi con.
        ("Vinmec có nhận bảo hiểm y tế không?", "info_lookup"),
        ("Số điện thoại cấp cứu của Vinmec là gì?", "info_lookup"),
        ("Tôi bị ho", "clinical_triage"),
        ("hi", "chitchat"),
    ],
)
def test_fallback_route_matches_whole_words(query, route):
    assert _rule_based_fallback_route(query, None)[0] == route


@pytest.mark.parametrize(
    ("query", "key"),
    [
        ("Vinmec có nhận bảo hiểm y tế không?", "INSURANCE"),
        ("Does Vinmec accept insurance?", "INSURANCE"),
        ("Số điện thoại cấp cứu của Vinmec là gì?", "EMERGENCY_CONTACT"),
        ("Vinmec Times City làm việc mấy giờ?", "WORKING_HOURS_HOTLINE"),
    ],
)
def test_faq_cache_answers_info_questions(query, key):
    hit = get_cache_service().check_cache(query, language="vi")
    assert hit is not None and hit[2] == key


def test_emergency_contact_faq_points_to_115():
    response, _, _ = get_cache_service().check_cache("Số điện thoại cấp cứu là gì?", language="vi")
    assert "115" in response


@pytest.mark.parametrize(
    ("query", "doctor"),
    [
        ("Bác sĩ Nguyễn Vĩnh Toàn làm ở cơ sở nào?", "Nguyễn Vĩnh Toàn"),
        ("Tôi muốn đặt lịch với bác sĩ Nguyễn Vĩnh Toàn", "Nguyễn Vĩnh Toàn"),
        ("đặt lịch với bác sĩ tim mạch", None),
        ("Đặt lịch với bác sĩ đầu tiên giúp tôi", None),
        ("bác sĩ nào giỏi", None),
    ],
)
def test_doctor_name_extraction_stops_at_verbs_and_skips_specialties(query, doctor):
    assert extract_booking_entities(query, {}).get("doctor_preference") == doctor


LISTED = [
    {"full_name": "Nguyễn Vĩnh Toàn", "specialty": "Tai mũi họng", "workplace": "Vinmec Times City"},
    {"full_name": "Trần Thị B", "specialty": "Tai mũi họng", "workplace": "Vinmec Central Park"},
]


@pytest.mark.parametrize(
    ("query", "name"),
    [
        ("Đặt lịch với bác sĩ đầu tiên giúp tôi", "Nguyễn Vĩnh Toàn"),
        ("cho tôi gặp bác sĩ thứ 2", "Trần Thị B"),
        ("bác sĩ số 3", None),
        ("đặt lịch khám tai mũi họng", None),
    ],
)
def test_pick_listed_doctor_by_ordinal(query, name):
    picked = _pick_listed_doctor(query, LISTED)
    assert (picked or {}).get("full_name") == name


def test_info_fallback_looks_up_named_doctor():
    from src.medical_assistant.agent.nodes import info_fallback

    fake = MagicMock()
    fake.invoke.return_value = {
        "found": True,
        "doctors": [
            {"full_name": "Nguyễn Vĩnh Toàn", "specialties": ["Tai mũi họng"], "workplace": "Vinmec Times City"}
        ],
    }
    with patch.object(info_fallback, "search_doctors", fake):
        text, tool, _ = info_fallback.answer_info_without_llm("Bác sĩ Nguyễn Vĩnh Toàn làm ở cơ sở nào?")
    assert tool == "search_doctors"
    assert fake.invoke.call_args.args[0]["name"] == "Nguyễn Vĩnh Toàn"
    assert "Times City" in text


@pytest.mark.asyncio
async def test_view_schedule_request_routes_to_booking():
    with patch("src.medical_assistant.agent.nodes.router_node.get_llm", side_effect=OFFLINE):
        result = await route_intent_node({"query": "Cho tôi xem lịch trống khoa Thần kinh tuần này"})
    assert result["intent_route"] == "booking"
