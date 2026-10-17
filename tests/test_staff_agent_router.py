from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.agents.staff_agent_router import route_staff_request


def test_chitchat_routes_directly_and_prefers_vietnamese():
    route = route_staff_request("Xin chào")

    assert route.category == "chitchat"
    assert route.language == "vi"


@pytest.mark.parametrize("message", ["Chào em", "Xin chào chị", "Cảm ơn em nhé"])
def test_latest_social_message_overrides_stale_operational_context(message):
    route = route_staff_request(message, "Tra booking đã xác nhận hôm nay")

    assert route.category == "chitchat"
    assert route.tool_names == ()
    assert route.language == "vi"


def test_chitchat_honors_explicit_english_without_entering_agent_loop():
    route = route_staff_request("Hello, reply in English please")

    assert route.category == "chitchat"
    assert route.language == "en"
    assert "Hello!" in route.reply


def test_ambiguous_availability_asks_for_missing_time_without_tools():
    route = route_staff_request("Có bác sĩ tim mạch nào còn lịch trống?")

    assert route.category == "ambiguous"
    assert route.tool_names == ()
    assert "ngày" in route.reply


def test_clear_availability_uses_only_availability_tool():
    route = route_staff_request("Có bác sĩ khoa tim mạch nào còn lịch ngày mai tại cơ sở ABC?")

    assert route.category == "simple"
    assert route.tool_names == ("search_staff_availability",)


def test_multi_subject_patient_booking_request_uses_complex_tool_set():
    route = route_staff_request("Tra cứu hồ sơ bệnh nhân A và lịch khám của người này")

    assert route.category == "complex"
    assert "search_staff_patients" in route.tool_names
    assert "search_staff_bookings" in route.tool_names
    assert "query_staff_operations" not in route.tool_names


def test_query_fallback_is_selected_only_for_uncovered_operational_questions():
    route = route_staff_request("Liệt kê dịch vụ đang hoạt động ở cơ sở ABC")

    assert route.category == "simple"
    assert route.tool_names == ("query_staff_operations",)


def test_followup_can_reuse_safe_staff_conversation_context():
    route = route_staff_request("Mai Văn Trường", "Tra cứu hồ sơ bệnh nhân. Vui lòng cho biết tên.")

    assert route.category == "complex"
    assert "search_staff_patients" in route.tool_names
    assert "get_staff_patient_profile" in route.tool_names


def test_patient_profile_and_intake_case_request_requires_scope_confirmation():
    route = route_staff_request("Tra cứu hồ sơ bệnh nhân đi, hôm nay tiếp nhận các ca nào")

    assert route.category == "confirmation"
    assert route.tool_names == ()
    assert "điều phối/HITL" in route.reply
    assert "booking" in route.reply
    assert route.task_domains == ["patient_profile", "today_coordination_cases"]
    assert route.tasks == [
        {"id": "patient_profile", "domain": "patient_profile", "depends_on": []},
        {
            "id": "today_coordination_cases",
            "domain": "today_coordination_cases",
            "depends_on": [],
            "filters": {"received_today": True},
        },
    ]


def test_unqualified_intake_case_request_asks_only_which_record_type():
    route = route_staff_request("Tra cứu các ca tiếp nhận trong hôm nay")

    assert route.category == "ambiguous"
    assert route.reason_code == "intake_case_type_required"
    assert route.tool_names == ()
    assert "booking/lượt khám" in route.reply


def test_emergency_case_request_routes_to_saved_emergency_case_filter():
    route = route_staff_request("Tra cứu các ca cần cấp cứu")

    assert route.category == "simple"
    assert route.tool_names == ("search_staff_cases", "get_staff_case")
    assert route.tasks == [
        {
            "id": "coordination_cases",
            "domain": "coordination_cases",
            "depends_on": [],
            "filters": {"emergency_only": True},
        }
    ]

    today_route = route_staff_request("Tra cứu các ca cấp cứu hôm nay")
    assert today_route.tasks[0]["filters"] == {"received_today": True, "emergency_only": True}


def test_explicit_claim_and_case_booking_requests_route_to_proposal_tools():
    claim = route_staff_request("Tiếp nhận ca điều phối 123")
    assert "search_staff_cases" in claim.tool_names
    assert "prepare_case_claim" in claim.tool_names

    booking = route_staff_request("Tạo booking cho case 123 với bác sĩ tim mạch ngày mai")
    assert "get_staff_case" in booking.tool_names
    assert "search_staff_availability" in booking.tool_names
    assert "prepare_case_booking" in booking.tool_names


def test_case_claim_and_booking_request_starts_with_claim_proposal():
    route = route_staff_request(
        "Duyệt ca này và đặt lịch cho bệnh nhân",
        "Chi tiết ca thứ nhất đang được tư vấn: bệnh nhân Mai Văn Trường.",
    )

    assert route.reason_code == "claim_case_before_booking"
    assert route.tool_names == ("search_staff_cases", "get_staff_case", "prepare_case_claim")
    assert route.tasks == [
        {
            "id": "coordination_cases",
            "domain": "coordination_cases",
            "depends_on": [],
            "filters": {"continue_to_booking": True},
        }
    ]


@pytest.mark.parametrize(
    "message",
    [
        "Có các ca nào đang được tư vấn?",
        "Các ca agent đang tư vấn hiện nay là gì?",
    ],
)
def test_agent_consultation_cases_route_to_scoped_case_lookup(message):
    route = route_staff_request(message)

    assert route.category == "simple"
    assert route.tool_names == ("search_staff_cases", "get_staff_case")
    assert route.tasks == [
        {
            "id": "coordination_cases",
            "domain": "coordination_cases",
            "depends_on": [],
            "filters": {"agent_consulting": True},
        }
    ]


def test_submitted_exam_form_routes_to_consultation_cases_only():
    route = route_staff_request("Liệt kê các ca bệnh nhân đã gửi phiếu khám")

    assert route.reason_code == "submitted_exam_form_case_lookup"
    assert route.tool_names == ("search_staff_cases", "get_staff_case")
    assert route.tasks[0]["filters"] == {"submitted_exam_forms": True}


def test_explicit_new_booking_request_does_not_inherit_old_assistant_intents():
    route = route_staff_request(
        "Tra cứu booking trong hôm nay",
        "Bạn muốn tra hồ sơ bệnh nhân và các ca điều phối/HITL hôm nay?",
    )

    assert route.category == "simple"
    assert route.tool_names == ("search_staff_bookings", "get_staff_booking")


def test_unrelated_doctor_and_case_request_auto_executes_when_fully_specified():
    route = route_staff_request("Tra cứu bác sĩ và các case đang quá SLA")

    # TASK-071 allows explicitly requested, fully specified read lookups to execute.
    assert route.category == "complex"
    assert "search_staff_doctors" in route.tool_names
    assert "search_staff_cases" in route.tool_names
    assert set(route.task_domains) == {"doctors", "coordination_cases"}
    assert all(not task["depends_on"] for task in route.tasks)


def test_patient_profiles_for_today_visits_are_dependent_tasks_without_confirmation():
    route = route_staff_request("Tra cứu hồ sơ bệnh nhân đến thăm khám hôm nay")

    assert route.category == "complex"
    assert route.tool_names == (
        "search_staff_patients",
        "get_staff_patient_profile",
        "search_staff_bookings",
        "get_staff_booking",
    )
    assert route.tasks == [
        {
            "id": "bookings",
            "domain": "bookings",
            "depends_on": [],
            "filters": {
                "booking_date_field": "created_at",
                "booking_date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat(),
            },
        },
        {"id": "patient_profile", "domain": "patient_profile", "depends_on": ["bookings"]},
    ]


def test_planner_refuses_more_than_four_lookup_domains():
    route = route_staff_request("Tra hồ sơ bệnh nhân, booking, case quá SLA, bác sĩ tim mạch và quy trình nội bộ")

    assert route.category == "unsupported"
    assert route.tool_names == ()
