import pytest

from src.medical_assistant.agent.graph import agent


@pytest.mark.asyncio
async def test_schedule_followup_preserves_ent_and_requested_two_day_window():
    config = {"configurable": {"thread_id": "test_schedule_followup_ent_two_days"}}

    first = await agent.ainvoke(
        {"query": "Tôi bị ho nhiều và rát họng"},
        config=config,
    )
    assert first["suggested_department_name"] == "Tai - Mũi - Họng"

    asked = await agent.ainvoke(
        {"query": "Bạn xem lịch khám trong 2 ngày tới"},
        config=config,
    )
    # Chưa có nơi khám → hỏi khu vực trước khi tra lịch, giữ nguyên khoa và khung 2 ngày.
    assert asked["workflow_status"] == "FACILITY_CHOICE_REQUIRED"
    assert asked["suggested_department_name"] == "Tai - Mũi - Họng"

    second = await agent.ainvoke(
        {"query": "Cơ sở nào cũng được"},
        config=config,
    )

    assert second["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    assert second["suggested_department_name"] == "Tai - Mũi - Họng"
    assert second["max_booking_days"] == 2
    assert second["metadata"]["schedule_lookup_requested"] is True
    assert second["available_slots"]
    assert all("vinmec.com" in doctor["source_url"] for doctor in second["available_slots"])
    # Test đọc lịch thật (Supabase): có hay không có lịch đã xác minh trong 2 ngày tùy dữ liệu lúc chạy.
    if any(doctor["available_slots"] for doctor in second["available_slots"]):
        assert "đã kiểm tra lịch khám còn trống" in second["response"]
    else:
        assert "Bác sĩ phù hợp có hồ sơ nguồn" in second["response"]
        assert "chưa có lịch trống được xác minh" in second["response"]
    assert "Tai - Mũi - Họng" in second["response"]
