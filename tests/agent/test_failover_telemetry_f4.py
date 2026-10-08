"""Tests verifying Prompt F4 Telemetry, Failover Winner Metadata, and info_agent resilience.

Covers requirements from context_agent/plan2.md (Prompt F4):
1) Lỗi tool: khi tool ném exception, kết quả {found: false, data_unavailable: true, error} có trong collected_results.
2) Failover: test giả lập primary 400 + backup thành công -> fallback_used = True, provider_index = 1.
3) workflow_status: khi LLM lỗi/timeout đặt 'INFO_UNAVAILABLE'.
4) quick_replies: sinh theo kết quả tra cứu hiện tại, không kế thừa metadata cũ.
5) Disclaimer: chỉ gắn khi tra cứu bệnh học, không gắn khi tra cứu bác sĩ/cơ sở thuần túy.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.medical_assistant.agent.nodes.info_agent_node import (
    _run_react_loop,
    info_agent_node,
)
from src.medical_assistant.infrastructure.llm import FailoverChatModel


@pytest.mark.asyncio
async def test_failover_primary_400_backup_succeeds_flags_fallback_used():
    """Yêu cầu 2: Giả lập Primary 400 và Backup thành công -> fallback_used=True, provider_index=1."""
    # Mock Primary ném lỗi 400 Bad Request
    mock_primary = MagicMock()
    mock_primary.model_name = "mock-primary-model"
    exc_400 = RuntimeError("400 Bad Request: Invalid parameter")
    setattr(exc_400, "status_code", 400)
    mock_primary.ainvoke = AsyncMock(side_effect=exc_400)

    # Mock Backup thành công
    mock_backup = MagicMock()
    mock_backup.model_name = "mock-backup-model"
    success_ai_msg = AIMessage(content="Dạ, bác sĩ Nguyễn Đình Dũng chuyên khoa Tim mạch ạ.")
    mock_backup.ainvoke = AsyncMock(return_value=success_ai_msg)

    failover_model = FailoverChatModel(
        primary=mock_primary,
        fallbacks=[mock_backup],
        cooldown_seconds=10.0,
        total_timeout_seconds=5.0,
    )

    # Thực hiện ainvoke
    res = await failover_model.ainvoke("Tra cứu bác sĩ")
    assert res.content == success_ai_msg.content

    winner = failover_model.get_last_winner()
    assert winner["provider_index"] == 1
    assert winner["model_name"] == "mock-backup-model"
    assert winner["is_primary"] is False
    assert winner["providers_attempted"] >= 1


@pytest.mark.asyncio
async def test_tool_exception_appends_data_unavailable_to_collected_results():
    """Yêu cầu 1: Khi tool ném exception, collected_results phải chứa data_unavailable=True."""
    mock_tool = MagicMock()
    mock_tool.name = "broken_tool"
    mock_tool.invoke = MagicMock(side_effect=RuntimeError("Database socket hung up"))

    tools_map = {"broken_tool": mock_tool}

    # Model gọi broken_tool ở turn 1, sau đó trả lời ở turn 2
    ai_call_tool = AIMessage(
        content="",
        tool_calls=[{"name": "broken_tool", "args": {"name": "test"}, "id": "call_1"}],
    )
    ai_final = AIMessage(content="Hệ thống đang bảo trì dữ liệu ạ.")

    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(side_effect=[ai_call_tool, ai_final])

    messages = []
    final_text, tools_called, collected_results, tool_errors, _ = await _run_react_loop(
        mock_model, tools_map, messages, max_turns=3
    )

    assert len(collected_results) == 1
    res_data = collected_results[0]["data"]
    assert res_data["found"] is False
    assert res_data["data_unavailable"] is True
    assert "Database socket hung up" in res_data["error"]
    assert len(tool_errors) == 1


@pytest.mark.asyncio
async def test_workflow_status_sets_info_unavailable_on_llm_failure():
    """Yêu cầu 4: Nếu LLM lỗi/timeout đặt 'INFO_UNAVAILABLE'."""
    mock_failing_llm = MagicMock()
    mock_failing_llm.bind_tools.return_value.ainvoke = AsyncMock(
        side_effect=RuntimeError("All LLM providers exhausted")
    )

    state = {
        "query": "Tra cứu thông tin bác sĩ tiêu hóa",
        "messages": [],
    }

    output = await info_agent_node(state, llm=mock_failing_llm)

    assert output["workflow_status"] == "INFO_UNAVAILABLE"
    assert output["metadata"]["workflow_status"] == "INFO_UNAVAILABLE"
    assert output["metadata"]["llm_succeeded"] is False
    assert output["metadata"]["data_unavailable"] is True


@pytest.mark.asyncio
async def test_quick_replies_not_inherited_from_stale_metadata():
    """Yêu cầu 5: quick_replies sinh theo kết quả hiện tại, không kế thừa metadata cũ."""
    mock_llm = MagicMock()
    mock_llm.get_last_winner.return_value = {"provider_index": 0, "is_primary": True}
    mock_llm.bind_tools.return_value.ainvoke = AsyncMock(
        return_value=AIMessage(content="Dạ, em xin gửi thông tin bác sĩ.")
    )

    # State có quick_replies rác từ lượt trước
    stale_state = {
        "query": "Bác sĩ Nguyễn Đình Dũng",
        "metadata": {
            "quick_replies": ["STALE_REPLY_1", "STALE_REPLY_2"],
            "intent_route": "old_intent",
        },
        "messages": [],
    }

    output = await info_agent_node(stale_state, llm=mock_llm)

    replies = output["metadata"]["quick_replies"]
    # Tuyệt đối không được kế thừa reply cũ
    assert "STALE_REPLY_1" not in replies
    assert "STALE_REPLY_2" not in replies
    # Metadata merge không chứa intent cũ
    assert "intent_route" not in output["metadata"]


@pytest.mark.asyncio
async def test_disclaimer_omitted_for_non_pathology_lookups():
    """Yêu cầu 6: Disclaimer chỉ gắn khi dùng search_disease_knowledge hoặc nội dung bệnh học."""
    mock_llm = MagicMock()
    mock_llm.get_last_winner.return_value = {"provider_index": 0, "is_primary": True}
    mock_llm.bind_tools.return_value.ainvoke = AsyncMock(
        return_value=AIMessage(content="Dạ, Bệnh viện Vinmec Times City ở 458 Minh Khai, Hà Nội ạ.")
    )

    # Câu hỏi địa chỉ thuần túy
    facility_state = {
        "query": "Địa chỉ Bệnh viện Vinmec Times City ở đâu?",
        "messages": [],
    }

    output = await info_agent_node(facility_state, llm=mock_llm)

    # Không được gắn disclaimer y tế cho câu hỏi địa chỉ
    assert "Khuyến cáo y tế" not in output["response"]
    assert "Medical Disclaimer" not in output["response"]


@pytest.mark.asyncio
async def test_failover_provider_401_updates_last_winner_and_telemetry(caplog):
    """Prompt G4: Mock provider 0 ném 401, provider 1 thành công.
    - get_last_winner() trả provider_index=1, providers_attempted=2.
    - info_agent_node nhận winner_info đúng -> fallback_used=True.
    - TURN_TELEMETRY log ghi nhận fallback_used=true.
    """
    import json
    import logging

    caplog.set_level(logging.INFO)

    # 1. Setup FailoverChatModel với Primary 401 và Backup thành công
    mock_primary = MagicMock()
    mock_primary.model_name = "deepseek-chat"
    exc_401 = RuntimeError("401 Unauthorized: Invalid API key")
    setattr(exc_401, "status_code", 401)
    mock_primary.ainvoke = AsyncMock(side_effect=exc_401)
    mock_primary.bind_tools = MagicMock(return_value=mock_primary)

    mock_backup = MagicMock()
    mock_backup.model_name = "openrouter-backup"
    success_msg = AIMessage(content="Bệnh viện Vinmec Times City tọa lạc tại 458 Minh Khai, Hà Nội.")
    mock_backup.ainvoke = AsyncMock(return_value=success_msg)
    mock_backup.bind_tools = MagicMock(return_value=mock_backup)

    failover_model = FailoverChatModel(
        primary=mock_primary,
        fallbacks=[mock_backup],
        cooldown_seconds=10.0,
        total_timeout_seconds=5.0,
    )

    # 2. Gọi trực tiếp failover_model để kiểm tra get_last_winner()
    res = await failover_model.ainvoke("Địa chỉ viện")
    assert res.content == success_msg.content

    winner = failover_model.get_last_winner()
    assert winner["provider_index"] == 1
    assert winner["providers_attempted"] == 2
    assert winner["model"] == "openrouter-backup"
    assert winner["model_name"] == "openrouter-backup"
    assert winner["is_primary"] is False

    # 3. Gọi info_agent_node với failover model và kiểm tra fallback_used
    state = {
        "query": "Địa chỉ cơ sở Times City",
        "messages": [],
    }
    output = await info_agent_node(state, llm=failover_model)

    assert output["metadata"]["fallback_used"] is True
    assert output["metadata"]["llm_succeeded"] is True

    # 4. Xác nhận TURN_TELEMETRY log ghi đúng fallback_used=true
    telemetry_logs = [record.message for record in caplog.records if "TURN_TELEMETRY:" in record.message]
    assert len(telemetry_logs) >= 1

    telemetry_json = json.loads(telemetry_logs[-1].split("TURN_TELEMETRY: ")[1])
    assert telemetry_json["fallback_used"] is True
    assert telemetry_json["route"] == "info_agent"
    assert telemetry_json["llm_succeeded"] is True
