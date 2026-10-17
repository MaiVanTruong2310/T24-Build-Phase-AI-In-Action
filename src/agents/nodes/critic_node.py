"""
Critic & Evaluator Node for Medical Reflexion Loop (Shinn et al., 2023)
Orchestration Layer: Chịu trách nhiệm điều phối StateGraph, ủy quyền kiểm toán lâm sàng
cho ClinicalCriticService độc lập (Domain Layer) và áp dụng EvaluatorVerdict.
"""

from __future__ import annotations

from typing import Any

from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.clinical_critic_service import get_clinical_critic_service


async def critic_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or state.get("user_input", "")
    workflow_status = state.get("workflow_status", "")
    reflection_count = state.get("reflection_count") or 0
    language = state.get("language") or "vi"

    # 1. Bỏ qua nếu đã lặp Reflexion tối đa (ngăn chặn loop vô hạn)
    if reflection_count >= 1:
        return {
            "critic_status": "APPROVED",
            "reflection_count": reflection_count,
        }

    # 2. Bỏ qua các trạng thái không lâm sàng hoặc đã chặn an toàn từ trước
    if workflow_status in {"SECURITY_BLOCKED", "FAQ_ANSWERED", "OUT_OF_SCOPE", "SOCIAL_REDIRECT"}:
        return {
            "critic_status": "APPROVED",
            "reflection_count": reflection_count,
        }

    # 3. Chuyển giao việc thẩm định độc lập (Blind Audit) cho ClinicalCriticService (Domain Layer)
    critic_service = get_clinical_critic_service()
    verdict = critic_service.audit_analysis(query=query, current_state=state, language=language)

    # 4. Xử lý kết quả phán quyết Pydantic EvaluatorVerdict
    if verdict.verdict in {"REVISED_BY_REFLEXION", "REVISE"}:
        meta = {
            **(state.get("metadata") or {}),
            **(verdict.corrections.get("metadata") or {}),
            "reflexion_critique": verdict.actionable_feedback,
            "reflexion_applied": True,
            "reflexion_verdict": verdict.model_dump(),
        }

        # Cập nhật Short-term Reflection Memory (Trong cùng session LangGraph)
        current_mem = list(state.get("reflection_memory") or [])
        if verdict.reflection_item:
            current_mem.append(verdict.reflection_item)

            # Lưu trữ Long-term Memory (Supabase Database Persistence)
            from src.medical_assistant.domain.reflection_memory_service import (
                ReflectionMemoryItem,
                get_reflection_memory_service,
            )

            try:
                item_obj = ReflectionMemoryItem(**verdict.reflection_item)
                get_reflection_memory_service().persist_reflection_to_db(
                    item=item_obj,
                    session_id=str(state.get("booking_id") or state.get("thread_id") or "session_default"),
                    user_id=state.get("user_id"),
                )
            except Exception:
                pass

        # Action Space Pruning: Chặn đường chọn lại chuyên khoa và hành động đã thất bại
        failed_dept = state.get("suggested_department_name")
        failed_code = state.get("suggested_department_code")
        pruned_depts = list(state.get("pruned_departments") or [])
        if (
            failed_dept
            and failed_dept != verdict.corrections.get("suggested_department_name")
            and failed_dept not in pruned_depts
        ):
            pruned_depts.append(failed_dept)
        if (
            failed_code
            and failed_code != verdict.corrections.get("suggested_department_code")
            and failed_code not in pruned_depts
        ):
            pruned_depts.append(failed_code)

        failed_act = state.get("workflow_status")
        pruned_acts = list(state.get("pruned_actions") or [])
        if (
            failed_act
            and failed_act in {"TRIAGED_AWAITING_SCHEDULE", "TRIAGED_READY_FOR_BOOKING"}
            and verdict.corrections.get("workflow_status") == "EMERGENCY"
        ):
            for act in [
                "search_available_slot",
                "hold_slot",
                "start_facility_booking",
                "suggest_specialty",
                "book_appointment_directly",
            ]:
                if act not in pruned_acts:
                    pruned_acts.append(act)

        return {
            **verdict.corrections,
            "critic_critique": verdict.actionable_feedback,
            "critic_status": verdict.verdict,
            "reflection_count": reflection_count + 1,
            "reflection_memory": current_mem,
            "pruned_departments": pruned_depts,
            "pruned_actions": pruned_acts,
            "metadata": meta,
        }

    return {
        "critic_status": "APPROVED",
        "critic_critique": None,
        "reflection_count": reflection_count,
    }
