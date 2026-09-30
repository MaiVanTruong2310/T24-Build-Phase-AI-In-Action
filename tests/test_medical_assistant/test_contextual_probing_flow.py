import pytest

from src.medical_assistant.agent.graph import agent


@pytest.mark.asyncio
async def test_describe_more_button_continues_constipation_probing_without_specialty_drift():
    config = {"configurable": {"thread_id": "test_constipation_describe_more"}}

    first = await agent.ainvoke(
        {"query": "Tôi bị táo bón và nóng trong người, tôi có bị bệnh gì nghiêm trọng không?"},
        config=config,
    )
    assert first["suggested_department_name"] == "Tiêu hóa - Gan mật"
    assert first["active_probing_category"] == "TAO_BON"

    second = await agent.ainvoke({"query": "Mô tả thêm triệu chứng"}, config=config)

    assert second["workflow_status"] == "PROBING_IN_PROGRESS"
    assert second["suggested_department_name"] == "Tiêu hóa - Gan mật"
    assert second["active_probing_category"] == "TAO_BON"
    assert second["metadata"]["needs_more_probing"] is True
    assert "tình trạng này bắt đầu từ bao lâu" in second["response"]
    assert "Tai - Mũi - Họng" not in second["response"]
    assert not second.get("available_slots")
    assert "Mô tả thêm triệu chứng" not in second["collected_details"]
