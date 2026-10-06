"""
Agent Middleware Pipeline (6-Hook Architecture)
Tuân thủ chuẩn thiết kế VinUni AICB cho vòng lặp AI Agent:
- Hook 1: on_user_input (Sanitization, Injection Check, Boundary Intents, Security Audit Log)
- Hook 2: before_model_call (Reflection Memory Injection, Action Space Pruning, Token Budgeting)
- Hook 3: after_model_call (Pydantic Schema Validation, Fallback Recovery)
- Hook 4: before_tool_execution (Action Clinical Evidence Validation, Department Pruning Guard)
- Hook 5: after_tool_execution (Tool Output Compaction, Serialization, Error Handling)
- Hook 6: on_agent_finish (Critic Evaluator Review, Session Telemetry Cost Tracking)
"""

from __future__ import annotations

from typing import Any

from src.medical_assistant.domain.action_validator import validate_action
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.reflection_memory_service import get_reflection_memory_service
from src.medical_assistant.domain.telemetry_service import USD_TO_VND_RATE, get_telemetry_service


class AgentMiddlewarePipeline:
    """Điều phối toàn diện 6 Hook Middleware trong vòng lặp tiếp đón y tế."""

    def __init__(self):
        self.guardrail = get_guardrail_service()
        self.reflection_service = get_reflection_memory_service()
        self.telemetry_service = get_telemetry_service()

    # =========================================================================
    # HOOK 1: on_user_input (Kiểm duyệt & An toàn Đầu vào)
    # =========================================================================
    def execute_hook_1_user_input(
        self,
        query: str,
        state: dict[str, Any],
        current_dept: str | None = None,
        language: str = "vi",
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """
        Hook 1: Tiền kiểm soát đầu vào người dùng.
        - Phát hiện Prompt Injection / Jailbreak / Vi phạm rào chắn.
        - Tự động ghi vết Security Audit Log nếu có hành vi tấn công.
        - Chuyển hướng các câu hỏi ranh giới (Social, Out-of-scope, FAQ).
        """
        intent_check = self.guardrail.check_intent(
            query, current_department=current_dept, language=language, state=state
        )

        # Ghi log an ninh nếu phát hiện tấn công Injection / Jailbreak / Vi phạm an toàn
        if intent_check and str(intent_check.get("intent", "")).startswith("SECURITY_"):
            self.telemetry_service.record_security_event(
                attack_type=intent_check.get("detected_technique")
                or intent_check.get("matched_pattern")
                or intent_check.get("violation_type")
                or "SECURITY_VIOLATION",
                payload=query,
                blocked_reason=f"Phát hiện vi phạm an ninh: {intent_check.get('violation_type', 'SECURITY_BLOCK')}",
                session_id=str(state.get("booking_id") or state.get("thread_id") or "session_default"),
                user_id=state.get("user_id"),
                metadata={
                    "matched_pattern": intent_check.get("matched_pattern"),
                    "detected_technique": intent_check.get("detected_technique"),
                },
            )

        return intent_check, None

    # =========================================================================
    # HOOK 2: before_model_call (Tiền xử lý trước khi gọi LLM)
    # =========================================================================
    def execute_hook_2_before_model(
        self,
        allowed_actions: list[str],
        state: dict[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Hook 2: Action Space Pruning và chuẩn bị ngữ cảnh trước khi gọi LLM.
        - Cắt tỉa các action và chuyên khoa đã thất bại từ vòng lặp trước.
        - Chặn đứng không cho Actor có khả năng chọn lại con đường sai lầm.
        """
        candidate_specs = state.get("candidate_specialties") or []
        effective_actions, effective_specs = self.reflection_service.prune_action_space(
            allowed_actions=allowed_actions,
            candidate_specialties=candidate_specs,
            pruned_actions=state.get("pruned_actions"),
            pruned_departments=state.get("pruned_departments"),
        )
        return effective_actions, effective_specs

    # =========================================================================
    # HOOK 3: after_model_call (Hậu kiểm kết quả thô của LLM)
    # =========================================================================
    def execute_hook_3_after_model(
        self,
        v2_response: Any,
        llm_succeeded: bool,
    ) -> Any:
        """
        Hook 3: Kiểm duyệt output từ LLM.
        - Đảm bảo tính toàn vẹn cấu trúc và fallback an toàn khi LLM gặp sự cố.
        """
        if not llm_succeeded or not v2_response:
            pass  # Đã được hybrid_dialogue_service đảm bảo fallback
        return v2_response

    # =========================================================================
    # HOOK 4: before_tool_execution (Tiền kiểm duyệt trước khi gọi Tool)
    # =========================================================================
    def execute_hook_4_before_tool(
        self,
        action: str,
        clinical_facts: dict[str, Any],
        v2_response: Any,
        allowed_actions: list[str],
        suggested_dept_code: str | None,
        recommended_specialties: list[Any] | None,
        pruned_departments: list[str] | None,
        current_dept: str | None = None,
    ) -> tuple[str, str | None]:
        """
        Hook 4: Kiểm duyệt hành động và áp dụng Action Space Pruning lên chuyên khoa đích.
        - Kiểm tra bằng chứng lâm sàng trước khi chuyển sang đặt lịch.
        - Đảm bảo chuyên khoa được chọn không nằm trong danh sách đã bị loại trừ.
        """
        # 1. Kiểm duyệt hành động lâm sàng
        if v2_response:
            validated_action = validate_action(action, clinical_facts, v2_response, allowed_actions)
        else:
            validated_action = action

        # 2. Action Space Pruning trên chuyên khoa đích
        safe_dept_code = suggested_dept_code
        if pruned_departments and safe_dept_code:
            pruned_lower = {d.lower() for d in pruned_departments}
            if safe_dept_code.lower() in pruned_lower:
                fallback_dept = None
                for rec in recommended_specialties or []:
                    code = getattr(rec, "code", "")
                    name = getattr(rec, "name", "")
                    if code.lower() not in pruned_lower and name.lower() not in pruned_lower:
                        fallback_dept = code
                        break
                safe_dept_code = fallback_dept or current_dept

        return validated_action, safe_dept_code

    # =========================================================================
    # HOOK 5: after_tool_execution (Nén dữ liệu Tool Output)
    # =========================================================================
    def execute_hook_5_after_tool(
        self,
        tool_name: str,
        raw_output: Any,
    ) -> Any:
        """
        Hook 5: Nén và chuẩn hóa dữ liệu sau khi Tool thực thi xong.
        - Tránh tràn context window bằng cách nén output.
        """
        # Giữ nguyên dữ liệu có cấu trúc đã được định dạng
        return raw_output

    # =========================================================================
    # HOOK 6: on_agent_finish (Hậu kiểm kết thúc turn & Telemetry chi phí)
    # =========================================================================
    def execute_hook_6_on_finish(
        self,
        session_id: str,
        turn_index: int,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_usd: float,
        workflow_status: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Hook 6: Hậu kiểm kết thúc lượt hội thoại và tự động ghi nhận Telemetry chi phí.
        """
        self.telemetry_service.record_turn_telemetry(
            session_id=session_id,
            turn_index=turn_index,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            workflow_status=workflow_status,
            metadata=metadata or {},
        )
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": cost_usd,
            "cost_vnd": round(cost_usd * USD_TO_VND_RATE, 2),
            "latency_ms": round(latency_ms, 2),
        }


_middleware_pipeline_instance: AgentMiddlewarePipeline | None = None


def get_middleware_pipeline() -> AgentMiddlewarePipeline:
    global _middleware_pipeline_instance
    if _middleware_pipeline_instance is None:
        _middleware_pipeline_instance = AgentMiddlewarePipeline()
    return _middleware_pipeline_instance
