from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, StateGraph

from src.medical_assistant.agent.nodes.analyze_node import analyze_node
from src.medical_assistant.agent.nodes.critic_node import critic_node
from src.medical_assistant.agent.nodes.doctor_node import find_doctors_node
from src.medical_assistant.agent.nodes.info_agent_node import info_agent_node
from src.medical_assistant.agent.nodes.respond_node import respond_node
from src.medical_assistant.agent.nodes.router_node import route_intent_node
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.config import is_info_agent_enabled
from src.medical_assistant.infrastructure.turn_timing import timed_node


def route_after_intent(state: AgentState) -> str:
    """Điều hướng ban đầu sau khi phân loại ý định (Intent Routing).

    - info_lookup hoặc confidence < 0.6 -> info_agent_node
    - chitchat -> respond_node (trả lời xã giao nhanh, bảo toàn episode lâm sàng)
    - clinical_triage / booking / emergency -> analyze_node
    """
    dest = state.get("route_destination") or "analyze"
    if dest == "info_agent" and is_info_agent_enabled():
        return "info_agent"
    if dest == "chitchat":
        return "respond"
    return "analyze"


def route_after_critic(state: AgentState) -> str:
    """Route after clinical critic inspection.
    Supports Reflexion loop (Shinn et al., 2023):
    - If critic requests revision ('REVISE') and loop limit not reached -> re-enters 'analyze'
    - Otherwise -> routes to 'find_doctors', 'info_agent' or 'respond' via should_continue
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

    status = state.get("workflow_status")

    # Nếu bật Info Agent và status là câu hỏi thông tin hoặc clarify mục đích khám không có triệu chứng
    # -> Điều hướng sang info_agent để LLM tự do tra cứu công cụ và trả lời grounded
    if is_info_agent_enabled():
        if status in ("DEPARTMENT_INFO", "FACILITY_INFO", "FACILITY_DOCTORS"):
            return "info_agent"

    # Nếu là Cấp cứu, câu hỏi thường gặp (FAQ), Guardrail an toàn hoặc đang trong vòng lặp hỏi làm rõ (Probing)
    # -> Bỏ qua truy vấn bác sĩ, nhảy thẳng tới respond để tiết kiệm thời gian & tài nguyên
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

    # Thêm các nodes vào đồ thị
    graph.add_node("route_intent", timed_node("route_intent", route_intent_node))
    graph.add_node("analyze", timed_node("analyze", analyze_node))
    graph.add_node("critic", timed_node("critic", critic_node))
    graph.add_node("find_doctors", timed_node("find_doctors", find_doctors_node))
    graph.add_node("info_agent", timed_node("info_agent", info_agent_node))
    graph.add_node("respond", timed_node("respond", respond_node))

    # Cấu hình điểm khởi đầu và rẽ nhánh thông minh
    graph.set_entry_point("route_intent")
    graph.add_conditional_edges("route_intent", route_after_intent)

    graph.add_edge("analyze", "critic")
    graph.add_conditional_edges("critic", route_after_critic)
    graph.add_edge("find_doctors", "respond")
    graph.add_edge("info_agent", END)
    graph.add_edge("respond", END)

    # Compile đồ thị với checkpointer
    return graph.compile(checkpointer=checkpointer)


agent = build_graph()
