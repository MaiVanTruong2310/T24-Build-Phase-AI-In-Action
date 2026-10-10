"""Persist clinical chat and enforce human control at the server boundary."""

import json
import re
import time

from fastapi import HTTPException

from src.medical_assistant.infrastructure.turn_timing import record_ms
from src.models.user import User
from src.services import workbench as svc


def validate_guidance(body):
    # Restrict explicit diagnoses/prescriptions; clinical navigation remains allowed.
    text = body.casefold()
    if re.search(
        r"(?:bạn|bác|anh|chị|em|bệnh nhân)\s+(?:chắc chắn\s+)?(?:đã\s+)?(?:bị|mắc|được chẩn đoán)\s+(?:bệnh|ung thư|đột quỵ|nhồi máu|tiểu đường|viêm)",
        text,
    ) or re.search(r"(?:uống|tiêm|dùng)\s+.{0,50}\d+\s*(?:mg|viên|ml)\b", text):
        raise HTTPException(422, "Chỉ tư vấn điều hướng; không kết luận bệnh hoặc kê liều thuốc trong hội thoại này.")


async def before_turn(db, request, user, guest):
    async with db.begin():
        step = time.perf_counter()
        case = await svc.ensure_chat_case(db, request, user, guest)
        record_ms("db:ensure_chat_case", step)
        step = time.perf_counter()
        local_actor = await db.get(User, user.id) if user else None
        record_ms("db:get_user", step)
        step = time.perf_counter()
        await svc.add_message(db, case, request.request_id, "patient", request.message, local_actor, channel="ai_chat")
        record_ms("db:add_message", step)
        # Safety rules still run during takeover; emergencies never wait for staff.
        from src.medical_assistant.domain.triage_service import get_triage_service

        step = time.perf_counter()
        triage = get_triage_service().evaluate_symptoms(request.message)
        record_ms("cpu:triage_rules", step)
        emergency = getattr(triage, "is_emergency", False)
        if emergency:
            await svc.release_hold(db, case)
            case.priority = 0
            case.ai_snapshot = {
                **case.ai_snapshot,
                "is_emergency": True,
                "emergency_warning": triage.patient_guidance,
                "ats_level": triage.ats_level.value,
                "max_booking_days": 0,
            }
            if case.status in {"observing", "contacting", "waiting_patient"}:
                case.status = "new" if not case.assigned_to else "emergency_active"
            svc.bump(case)
            svc.event(db, case, None, "emergency_detected", request.message)
        return (
            case.id,
            case.control,
            triage if emergency else None,
            {"handover_summary": case.ai_snapshot.get("handover_summary"), "checkpoint": case.checkpoint},
        )


async def after_turn(db, case_id, request, response, state):
    from sqlalchemy import select

    from src.models.workbench import CoordinationCase as Case

    async with db.begin():
        case = (await db.execute(select(Case).where(Case.id == case_id).with_for_update())).scalar_one()
        if case.control == "human" and not state.get("is_emergency"):
            return waiting_response(request.session_id)
        safe_state = json.loads(json.dumps(state, ensure_ascii=False, default=str))
        await svc.capture_chat(db, case, request, response, safe_state)
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
                    svc.event(
                        db,
                        case,
                        None,
                        "routing_conflict",
                        f"AI đề xuất ({ai_code}) khác phương án điều phối đã thống nhất ({approved_code}).",
                    )
                    return waiting_response(request.session_id)
    return response


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
