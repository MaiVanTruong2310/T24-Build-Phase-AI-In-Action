import pytest
from src.medical_assistant.agent.graph import agent


@pytest.mark.asyncio
async def test_vague_query_clarifies_visit_purpose():
    """Verify that a vague, under-specified query asks for clarification instead of guessing."""
    result = await agent.ainvoke(
        {"query": "Tôi muốn đi khám bệnh ở Hà Nội"},
        config={"configurable": {"thread_id": "test-vague-query-clarify"}},
    )
    # Must clarify purpose or show facility options without guessing random specialty
    assert result["workflow_status"] in {"VISIT_PURPOSE_CLARIFICATION", "FACILITY_INFO"}
    assert result.get("suggested_department_code") is None or result.get("suggested_department_code") in {"SUC_KHOE_TONG_QUAT"}
    assert "response" in result
    assert len(result["response"]) > 0


@pytest.mark.asyncio
async def test_booking_slot_extraction_pipeline():
    """Verify that booking preferences (facility, date, period) are cleanly grounded."""
    result = await agent.ainvoke(
        {"query": "Tôi muốn khám ở Phòng khám Đa khoa Quốc tế Vinmec Ocean Park trong ngày mai ca sáng"},
        config={"configurable": {"thread_id": "test-booking-slots-pipeline"}},
    )
    assert result.get("facility_preference") == "Phòng khám ĐKQT Vinmec Ocean Park (Hà Nội)"
    assert result.get("preferred_period") == "morning"
    assert result.get("preferred_date") is not None
