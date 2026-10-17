"""Persist clinical chat and enforce human control at the server boundary."""

import json
import re
import time

from fastapi import HTTPException

from src.core.cache import invalidate_redis_api_cache
from src.medical_assistant.infrastructure.turn_timing import record_ms
from src.models.user import User
from src.services import workbench as svc
from src.services.chat_takeover import publish_workbench_case_update, publish_workbench_message


def staff_visible(case) -> bool:
    """Ca đã vào hàng đợi điều phối (yêu cầu hỗ trợ, cấp cứu hoặc người đang tiếp quản)."""
    return case.control == "human" or case.status != "observing" or case.priority == 0


DIAGNOSIS_PATTERN = re.compile(
    r"(?:bạn|bác|anh|chị|em|bệnh nhân)\s+(?:chắc chắn\s+)?(?:đã\s+)?(?:bị|mắc|được chẩn đoán)\s+"
    r"(?:bệnh|ung thư|đột quỵ|nhồi máu|tiểu đường|viêm)"
)
DOSAGE_PATTERN = re.compile(r"(?:uống|tiêm|dùng)\s+.{0,50}\d+\s*(?:mg|viên|ml)\b")
# Câu hỏi khai thác bệnh sử/thuốc đang dùng ("đã được chẩn đoán ... chưa?", "đang uống thuốc 500mg nào?") được phép.
QUESTION_ENDING = re.compile(r"(?:\?|\b(?:chưa|không|chăng|nào|gì|sao|nhỉ)\s*[.!]*)\s*$")


def validate_guidance(body):
    # Restrict explicit diagnoses/prescriptions; clinical navigation and history-taking questions remain allowed.
    for clause in re.split(r"(?<=[.!?\n])", body.casefold()):
        if not clause.strip() or QUESTION_ENDING.search(clause.strip()):
            continue
        if DIAGNOSIS_PATTERN.search(clause) or DOSAGE_PATTERN.search(clause):
            raise HTTPException(
                422, "Chỉ tư vấn điều hướng; không kết luận bệnh hoặc kê liều thuốc trong hội thoại này."
            )


async def before_turn(db, request, user, guest):
    alert_event = None
    async with db.begin():
        step = time.perf_counter()
        case = await svc.ensure_chat_case(db, request, user, guest)
        record_ms("db:ensure_chat_case", step)
        step = time.perf_counter()
        local_actor = await db.get(User, user.id) if user else None
        record_ms("db:get_user", step)
        step = time.perf_counter()
        # Đang có bác sĩ tiếp quản: tin nhắn gửi cho bác sĩ, hiện cả trong khung điều phối của bệnh nhân.
        channel = "coordinator_chat" if case.control == "human" else "ai_chat"
        message = await svc.add_message(
            db, case, request.request_id, "patient", request.message, local_actor, channel=channel
        )
        record_ms("db:add_message", step)
        # Safety rules still run during takeover; emergencies never wait for staff.
        from src.medical_assistant.domain.triage_service import get_triage_service

        step = time.perf_counter()
        triage = get_triage_service().evaluate_symptoms(request.message)
        record_ms("cpu:triage_rules", step)
        # Khớp MƠ HỒ (thiếu dấu, chữ đa nghĩa) không chặn ở đây: agent nhờ LLM khôi phục dấu / hỏi xác nhận,
        # tránh đẩy ca ưu tiên 0 lên bàn điều phối cho câu thường gõ không dấu.
        emergency = getattr(triage, "is_emergency", False) and getattr(triage, "match_confidence", "") != "ambiguous"
        if emergency:
            new_emergency = not bool((case.ai_snapshot or {}).get("is_emergency"))
            await svc.release_hold(db, case)
            case.priority = 0
            case.ai_snapshot = svc.mark_emergency(
                case.ai_snapshot,
                emergency_warning=triage.patient_guidance,
                ats_level=triage.ats_level.value,
                max_booking_days=0,
            )
            if case.status in {"observing", "contacting", "waiting_patient"}:
                case.status = "new" if not case.assigned_to else "emergency_active"
            await svc.reset_due(db, case)
            svc.bump(case)
            if new_emergency:
                alert_event = svc.event(
                    db,
                    case,
                    None,
                    "emergency_detected",
                    request.message,
                    details={"alert_reason": triage.patient_guidance},
                )
        result = (
            case.id,
            case.control,
            triage if emergency else None,
            {"handover_summary": case.ai_snapshot.get("handover_summary"), "checkpoint": case.checkpoint},
        )
    await invalidate_redis_api_cache("workbench-cases")
    # Phát sau khi commit để bàn điều phối thấy ngay cảnh báo cấp cứu / tin nhắn mới của ca đang trong hàng đợi.
    if emergency:
        await publish_workbench_case_update(case)
    elif staff_visible(case) and getattr(message, "_created_by_request", True):
        await publish_workbench_message(case, message)
    if alert_event is not None:
        from src.services.staff_alerts import publish_staff_assistant_alert

        await publish_staff_assistant_alert(alert_event, case)
    return result


async def after_turn(db, case_id, request, response, state):
    from sqlalchemy import select

    from src.models.workbench import CoordinationCase as Case

    alert_events = []
    final_response = response
    async with db.begin():
        case = (await db.execute(select(Case).where(Case.id == case_id).with_for_update())).scalar_one()
        if case.control == "human" and not state.get("is_emergency"):
            return waiting_response(request.session_id)
        safe_state = json.loads(json.dumps(state, ensure_ascii=False, default=str))
        alert_events.extend(await svc.capture_chat(db, case, request, response, safe_state) or [])
        if case.plan.get("specialty_id") and not state.get("is_emergency"):
            from uuid import UUID

            from src.medical_assistant.domain.language_service import canonicalize_specialty_code
            from src.models.specialty import Specialty

            approved = await db.get(Specialty, UUID(case.plan["specialty_id"]))
            if approved:
                approved_code = canonicalize_specialty_code(approved.code or approved.name)
                ai_code = canonicalize_specialty_code(
                    state.get("suggested_department_code") or state.get("suggested_department_name")
                )
                if approved_code and ai_code and approved_code != ai_code:
                    case.control = "human"
                    case.priority = min(case.priority, 1)
                    alert_events.append(
                        svc.event(
                            db,
                            case,
                            None,
                            "routing_conflict",
                            f"AI đề xuất ({ai_code}) khác phương án điều phối đã thống nhất ({approved_code}).",
                        )
                    )
                    final_response = waiting_response(request.session_id)
    await invalidate_redis_api_cache("workbench-cases")
    # capture_chat có thể vừa đưa ca vào hàng đợi (yêu cầu hỗ trợ/cấp cứu/xung đột định tuyến): báo bàn điều phối.
    if staff_visible(case):
        await publish_workbench_case_update(case)
    from src.services.staff_alerts import publish_staff_assistant_alert

    for alert_event in alert_events:
        await publish_staff_assistant_alert(alert_event, case)
    return final_response


def waiting_response(session_id):
    return {
        "response": "Tin nhắn đã được chuyển đến bác sĩ điều phối. Bạn sẽ nhận phản hồi trong cuộc hội thoại này.",
        "analysis": "",
        "session_id": session_id,
        "workflow_status": "HUMAN_TAKEOVER",
        "is_emergency": False,
        "quick_replies": [],
        "candidate_specialties": [],
    }
