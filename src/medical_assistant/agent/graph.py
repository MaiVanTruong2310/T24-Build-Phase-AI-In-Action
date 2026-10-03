from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.medical_assistant.agent.nodes.doctor_node import find_doctors_node
from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.agent.state import AgentState


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
checkpointer = MemorySaver()


def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("analyze", analyze_node)
    graph.add_node("find_doctors", find_doctors_node)
    graph.add_node("respond", respond_node)

    # Add edges
    graph.set_entry_point("analyze")
    graph.add_conditional_edges("analyze", should_continue)
    graph.add_edge("find_doctors", "respond")
    graph.add_edge("respond", END)

    # Compile đồ thị với checkpointer
    return graph.compile(checkpointer=checkpointer)


agent = build_graph()
