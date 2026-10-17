import asyncio

from langchain_core.messages import AIMessage

from src.agents.staff_agent import StaffAgentGraph
from src.agents.staff_agent_planner import GoalTaskAssessment, StaffGoalPlan, plan_staff_goal
from src.agents.staff_agent_router import route_staff_request, route_staff_request_with_planner


class _StructuredPlanner:
    def __init__(self, result):
        self.result = result

    async def ainvoke(self, _messages):
        return self.result


class _Planner:
    def __init__(self, result):
        self.result = result

    def with_structured_output(self, _schema):
        return _StructuredPlanner(self.result)


def _plan(*, goal="Find doctors for the requested specialty", domains=("doctors",), question=None):
    return StaffGoalPlan(
        goal=goal,
        tasks=[GoalTaskAssessment(domain=domain) for domain in domains],
        completion_criteria=["Return matching doctors from the tool result"],
        clarification_question=question,
    )


def test_single_domain_route_carries_goal_and_completion_criteria():
    base_route = route_staff_request("Tra cứu bác sĩ tim mạch")
    route = asyncio.run(
        route_staff_request_with_planner("Tra cứu bác sĩ tim mạch", llm=_Planner(_plan()), route=base_route)
    )

    assert route.category == "simple"
    assert route.tool_names == base_route.tool_names
    assert route.goal_plan == {
        "goal": "Find doctors for the requested specialty",
        "completion_criteria": ["Return matching doctors from the tool result"],
        "domains": ["doctors"],
    }


def test_unclear_goal_asks_before_any_tool_is_routed():
    base_route = route_staff_request("Tra cứu bác sĩ tim mạch")
    route = asyncio.run(
        route_staff_request_with_planner(
            "Tra cứu bác sĩ tim mạch",
            llm=_Planner(_plan(question="Bạn muốn tìm bác sĩ nào hoặc theo tiêu chí nào?")),
            route=base_route,
        )
    )

    assert route.category == "ambiguous"
    assert route.reason_code == "goal_clarification"
    assert route.tool_names == ()
    assert "tiêu chí" in route.reply


def test_plan_cannot_add_a_domain_or_tool():
    base_route = route_staff_request("Tra cứu bác sĩ tim mạch")
    invalid = _plan(domains=("doctors", "patient_profile"))
    route = asyncio.run(
        route_staff_request_with_planner("Tra cứu bác sĩ tim mạch", llm=_Planner(invalid), route=base_route)
    )

    assert route.tool_names == base_route.tool_names
    assert route.goal_plan is None


def test_model_extra_tool_fields_are_rejected():
    base_route = route_staff_request("Tra cứu bác sĩ tim mạch")
    malformed = {
        "goal": "Find doctors in the requested specialty",
        "tasks": [{"domain": "doctors", "is_executable": True, "tool": "search_staff_patients"}],
        "completion_criteria": ["List matching doctors"],
    }
    route = asyncio.run(
        route_staff_request_with_planner("Tra cứu bác sĩ tim mạch", llm=_Planner(malformed), route=base_route)
    )

    assert route.tool_names == base_route.tool_names
    assert route.goal_plan is None


def test_planner_failure_falls_back_to_the_deterministic_route():
    class BrokenPlanner:
        def with_structured_output(self, _schema):
            raise RuntimeError("provider unavailable")

    base_route = route_staff_request("Tra cứu bác sĩ tim mạch")
    route = asyncio.run(
        route_staff_request_with_planner("Tra cứu bác sĩ tim mạch", llm=BrokenPlanner(), route=base_route)
    )

    assert route.category == base_route.category
    assert route.tool_names == base_route.tool_names
    assert route.goal_plan is None


def test_booking_review_does_not_call_goal_planner():
    class MustNotRunPlanner:
        def with_structured_output(self, _schema):
            raise AssertionError("write-capable proposal route must bypass goal planning")

    message = "Duyệt booking 12345678-1234-1234-1234-123456789012"
    base_route = route_staff_request(message)
    route = asyncio.run(route_staff_request_with_planner(message, llm=MustNotRunPlanner(), route=base_route))

    assert "prepare_booking_review" in route.tool_names
    assert route.goal_plan is None


def test_incomplete_deterministic_task_cannot_be_marked_executable_by_llm():
    class ExecutablePatientPlan:
        def with_structured_output(self, _schema):
            return _StructuredPlanner(
                StaffGoalPlan(
                    goal="Find the requested patient record and cases",
                    tasks=[
                        GoalTaskAssessment(domain="patient_profile"),
                        GoalTaskAssessment(domain="today_coordination_cases"),
                    ],
                    completion_criteria=["Return the requested record and cases"],
                )
            )

    result = asyncio.run(
        plan_staff_goal(
            "Tra cứu hồ sơ bệnh nhân đi, hôm nay tiếp nhận các ca nào",
            ["patient_profile", "today_coordination_cases"],
            ExecutablePatientPlan(),
        )
    )

    assert result is not None
    assert not next(task for task in result.tasks if task.domain == "patient_profile").is_executable


def test_answer_generation_receives_goal_and_completion_criteria():
    class Model:
        seen = []

        def bind_tools(self, _tools):
            return self

        async def ainvoke(self, messages):
            self.seen.append(messages)
            return AIMessage(content="Found matching doctors.")

    model = Model()
    goal_plan = {
        "goal": "Find doctors available for the requested specialty",
        "completion_criteria": ["List only records returned by the search tool"],
        "domains": ["doctors"],
    }
    answer, states = asyncio.run(StaffAgentGraph(model, []).ainvoke([], goal_plan=goal_plan))

    assert answer == "Found matching doctors."
    assert states == []
    assert "Find doctors available" in str(model.seen[0])
    assert "List only records returned" in str(model.seen[0])
