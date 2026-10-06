from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, StateGraph

from src.medical_assistant.agent.nodes.analyze_node import analyze_node
from src.medical_assistant.agent.nodes.critic_node import critic_node
from src.medical_assistant.agent.nodes.doctor_node import find_doctors_node
from src.medical_assistant.agent.nodes.respond_node import respond_node
from src.medical_assistant.agent.state import AgentState


def route_after_critic(state: AgentState) -> str:
    """Route after clinical critic inspection.
    Supports Reflexion loop (Shinn et al., 2023):
    - If critic requests revision ('REVISE') and loop limit not reached -> re-enters 'analyze'
    - Otherwise -> routes to 'find_doctors' or 'respond' via should_continue
    """
    if state.get("error"):
        return END
    if state.get("critic_status") == "REVISE" and (state.get("reflection_count") or 0) < 1:
        return "analyze"
    return should_continue(state)


def should_continue(state: AgentState) -> str:
    """Route based on whether an error occurred, emergency, FAQ hit, or needs more probing."""
    if state.get("error"):
        return END
    # Nếu là Cấp cứu, câu hỏi thường gặp (FAQ), Guardrail an toàn hoặc đang trong vòng lặp hỏi làm rõ (Probing)
    # -> Bỏ qua truy vấn bác sĩ, nhảy thẳng tới respond để tiết kiệm thời gian & tài nguyên
    status = state.get("workflow_status")
    if state.get("is_emergency") or status in (
        "FAQ_ANSWERED",
        "VISIT_PURPOSE_CLARIFICATION",
        "GUARDRAIL_MEDICATION",
        "GUARDRAIL_DIAGNOSIS",
        "DEPARTMENT_INFO",
        "FACILITY_INFO",
        "FACILITY_DOCTORS",
        "FACILITY_BOOKING_START",
        "HOLD_BOOKING",
        "BOOKING_CONTACT_REQUIRED",
        "SECURITY_BLOCKED",
        "TRIAGED_AWAITING_SCHEDULE",
        "SAFETY_REVIEW",
        "HUMAN_HELP_REQUESTED",
        "LANGUAGE_CHANGED",
        "OUT_OF_SCOPE",
        "SOCIAL_REDIRECT",
        "THIRD_PARTY_HEALTH_GUIDANCE",
    ):
        return "respond"
    meta = state.get("metadata", {})
    if meta.get("needs_more_probing"):
        return "respond"
    return "find_doctors"



# Checkpointer lưu trữ trạng thái phiên theo thread_id
# Chuẩn bị sẵn để dễ dàng thay thế bằng PostgresSaver khi scale 10.000 users
checkpointer = MemorySaver(
    serde=JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("src.medical_assistant.domain.disease_triage", "ATSLevel"),
            ("src.medical_assistant.domain.disease_triage", "UrgencyTier"),
        ]
    )
)


def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("analyze", analyze_node)
    graph.add_node("critic", critic_node)
    graph.add_node("find_doctors", find_doctors_node)
    graph.add_node("respond", respond_node)

    # Add edges with Reflexion loop
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "critic")
    graph.add_conditional_edges("critic", route_after_critic)
    graph.add_edge("find_doctors", "respond")
    graph.add_edge("respond", END)

    # Compile đồ thị với checkpointer
    return graph.compile(checkpointer=checkpointer)


agent = build_graph()
