import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from src.agents.staff_agent import StaffAgentGraph
from src.agents.staff_agent_router import StaffRoute
from src.models.user import User
from src.services import staff_agent as staff_agent_module
from src.services.staff_agent import StaffAgentService


def _tool_call(round_number: int) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "lookup",
                "args": {"round_number": round_number},
                "id": f"lookup-{round_number}",
                "type": "tool_call",
            }
        ],
    )


class _SequentialModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.seen_messages = []

    def bind_tools(self, _tools):
        return self

    async def ainvoke(self, messages):
        self.seen_messages.append(messages)
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_simple_staff_route_can_continue_after_an_incomplete_tool_result(monkeypatch):
    calls = []
    model = _SequentialModel([_tool_call(1), _tool_call(2), AIMessage(content="Đã kiểm tra đủ dữ liệu.")])

    @tool
    async def lookup(round_number: int) -> str:
        """Return one part of a mocked lookup result."""
        calls.append(round_number)
        return json.dumps({"round": round_number, "items": ["record"]})

    service = StaffAgentService(AsyncMock(), llm=model)
    service.repository.get_staff_facility_scope = AsyncMock(return_value=[])
    monkeypatch.setattr(staff_agent_module, "get_settings", lambda: SimpleNamespace(database_url=""))
    monkeypatch.setattr(staff_agent_module, "build_staff_tools", lambda *args, **kwargs: [lookup])
    monkeypatch.setattr("src.agents.staff_agent.get_route", AsyncMock(return_value=None))
    monkeypatch.setattr("src.agents.staff_agent.set_route", AsyncMock())

    states = []
    answer = await service._run_agent(
        User(id=uuid4(), role="staff"),
        [],
        states,
        route=StaffRoute(
            "simple",
            "single_lookup",
            ("lookup",),
            tasks=[{"id": "bookings", "domain": "bookings", "depends_on": []}],
        ),
    )

    assert calls == [1, 2]
    assert answer == "Đã kiểm tra đủ dữ liệu."
    assert len(states) == 2
    assert "check whether it answers every material criterion" in str(model.seen_messages[1])


@pytest.mark.asyncio
async def test_staff_reasoning_executes_no_more_than_four_tool_rounds(monkeypatch):
    calls = []
    model = _SequentialModel([*(_tool_call(number) for number in range(1, 6)), AIMessage(content="Đã dừng an toàn.")])

    @tool
    async def lookup(round_number: int) -> str:
        """Return a mocked lookup result."""
        calls.append(round_number)
        return json.dumps({"round": round_number, "items": []})

    monkeypatch.setattr("src.agents.staff_agent.get_route", AsyncMock(return_value=None))
    monkeypatch.setattr("src.agents.staff_agent.set_route", AsyncMock())
    graph = StaffAgentGraph(model, [lookup])

    answer, states = await graph.ainvoke([])

    assert calls == [1, 2, 3, 4]
    assert len(states) == 4
    assert answer == "Đã dừng an toàn."
