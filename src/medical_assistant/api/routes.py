import asyncio
import json
import logging
import time
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.db.dependencies import get_auth_db_session
from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.booking_request_service import (
    BookingPersistenceError,
)
from src.medical_assistant.domain.schemas import (
    BookingIntakeRequest,
    BookingIntakeResponse,
    ChatRequest,
    ChatResponse,
)
from src.models.user import User
from src.services.chat_history import STATE_FIELDS, ChatHistoryService, graph_thread, health_record
from src.services.chat_takeover import ChatTakeoverService, case_payload, message_payload

router = APIRouter()
logger = logging.getLogger(__name__)


def chat_agent_input(request: ChatRequest) -> dict:
    payload = {"query": request.message, "user_id": request.user_id, "enable_citation": request.enable_citation}
    # Keep identity separate from clinical history. Omission preserves checkpoint memory.
    if request.patient_profile:
        profile = request.patient_profile.model_dump(exclude_none=True)
        payload.update(
            patient_profile=profile,
            patient_name=profile.get("name"),
            patient_phone=profile.get("phone"),
            patient_dob=profile.get("date_of_birth"),
            patient_gender=profile.get("gender"),
        )
    return payload


async def optional_chat_user(http_request: Request, session: AsyncSession = Depends(get_auth_db_session)):
    from src.services.cookie_session import request_token

    token = request_token(http_request)
    if not token:
        if http_request.headers.get("x-session-expected") == "1":
            raise HTTPException(401, "Cần gia hạn phiên đăng nhập.")
        return None
    return await get_current_user(token, session)


def public_result(result, session_id, elapsed_ms: float | None = None):
    meta = result.get("metadata") or {}
    payload = {
        key: result.get(key)
        for key in (
            "ats_level",
            "max_booking_days",
            "workflow_status",
            "conflict_reason",
            "acuity_status",
            "disposition",
        )
    }
    payload.update(
        response=result.get("response", ""),
        analysis="",
        session_id=session_id,
        is_emergency=bool(result.get("is_emergency")),
        token_usage=result.get("token_usage") or meta.get("token_usage"),
        elapsed_ms=elapsed_ms or result.get("elapsed_ms") or meta.get("elapsed_ms"),
        quick_replies=meta.get("quick_replies", []),
        booking_intake=meta.get("booking_intake"),
        suggested_department=result.get("suggested_department_name"),
        candidate_specialties=result.get("candidate_specialties") or meta.get("candidate_specialties", []),
    )
    return ChatResponse(**payload).model_dump(mode="json")


async def prepare_turn(request, user, session):
    started = time.perf_counter()
    subject = user
    selected_profile = None
    if user:
        from src.db.session import get_session_factory
        from src.services.patient_profiles import resolve_patient
        from src.models.patient_profile import PatientProfile
        from sqlalchemy import select
        async with get_session_factory()() as profile_db:
            if request.patient_profile_id is None:
                request.patient_profile_id = (await profile_db.execute(select(PatientProfile.id).where(PatientProfile.linked_user_id == user.id))).scalar_one_or_none()
            subject, selected_profile = await resolve_patient(profile_db, user, request.patient_profile_id)
    elif request.patient_profile_id:
        raise HTTPException(403, "Cần đăng nhập để chọn hồ sơ người thân.")
    service = ChatHistoryService(session)
    turn = await service.begin_turn(user, request) if user else None
    payload = chat_agent_input(request)
    payload["user_id"] = str(user.id) if user else None
    payload["session_id"] = request.session_id
    if user:
        checkpoint = turn.get("checkpoint", {})
        defaults = {key: None for key in STATE_FIELDS}
        defaults.update(
            messages=[],
            symptoms=[],
            clinical_facts={},
            collected_details=[],
            metadata={},
            language="vi",
            probing_turn=0,
            active_probing_categories=[],
            probing_by_complaint={},
            available_slots=[],
            candidate_specialties=[],
            routing_candidates=[],
            is_emergency=False,
            workflow_status="IDLE",
        )
        payload = {**defaults, **checkpoint, **payload, "error": None}
        dob_str = str(subject.date_of_birth) if subject.date_of_birth else None
        profile_dict = {
            "name": subject.full_name or "",
            "phone": user.phone or "",
        }
        if dob_str:
            profile_dict["date_of_birth"] = dob_str
        if selected_profile:
            profile_dict["phone"] = selected_profile.contact_phone or user.phone or ""
        if getattr(subject, "gender", None):
            profile_dict["gender"] = subject.gender
        payload.update(
            patient_profile=profile_dict,
            patient_name=subject.full_name,
            patient_phone=profile_dict["phone"],
            patient_dob=dob_str,
            patient_gender=subject.gender,
            patient_email=getattr(user, "email", None),
            is_authenticated=True,
            patient_health_record=health_record(subject),
        )
        # Nạp Cross-session Memory (Hồ sơ dài hạn & Open Loops)
        from src.medical_assistant.domain.patient_memory_service import get_patient_memory_service

        try:
            mem_svc = get_patient_memory_service()
            payload["patient_memory_profile"] = await mem_svc.get_patient_profile(subject.id)
            payload["active_open_loops"] = await mem_svc.get_active_open_loops(subject.id)
        except Exception as exc:
            logger.warning("Could not load cross-session memory: %s", exc)
            payload["patient_memory_profile"] = []
            payload["active_open_loops"] = []
    else:
        payload["patient_health_record"] = None
        payload["is_authenticated"] = False
        payload["patient_memory_profile"] = []
        payload["active_open_loops"] = []
    payload["clinical_subject_id"] = str(subject.id) if subject else None
    logger.info("chat.prepare elapsed_ms=%.0f", (time.perf_counter() - started) * 1000)
    return payload, turn, service


async def run_turn(request, user, payload, turn, service, guest_token=""):
    started = time.perf_counter()
    # A completed turn is terminal for this request. Return the durable result
    # before touching the optional history service (retries may not have one).
    if turn and turn.get("cached"):
        return turn["cached"]
    from src.db.session import get_session_factory
    from src.services.coordinator_chat import after_turn, before_turn, waiting_response

    try:
        if user:
            takeover = ChatTakeoverService(service.session)
            active_case = await takeover.active_case_for_patient(user.id, request.session_id)
            if active_case is not None:
                await takeover.record_patient_message(
                    user.id,
                    request.session_id,
                    request.message,
                    str(request.request_id),
                )
                response = public_result(
                    {
                        "response": "Tin nhắn của bạn đã được chuyển tới nhân viên y tế đang tiếp nhận ca. Vui lòng chờ phản hồi trực tiếp.",
                        "workflow_status": "HUMAN_HELP_REQUESTED",
                    },
                    request.session_id,
                )
                await service.complete(turn, response, turn.get("checkpoint", {}))
                return response
        started = time.perf_counter()
        result = await agent.ainvoke(
            payload, config={"configurable": {"thread_id": graph_thread(request.session_id, user)}}
        )
        agent_finished = time.perf_counter()
        response = public_result(result, request.session_id)
        try:
            async with get_session_factory()() as coordination_db:
                case_id, control, emergency, state_context = await before_turn(
                    coordination_db, request, user, guest_token
                )
        except SQLAlchemyError as exc:
            # Coordination is an optional orchestration layer.  A deployment
            # whose coordination migration is pending must still be able to
            # serve the medical assistant conversation itself.
            logger.warning("coordination before_turn unavailable; continuing with AI flow: %s", type(exc).__name__)
            case_id, control, emergency, state_context = None, "ai", None, {}
        if not user:
            payload = {**(state_context.get("checkpoint") or {}), **payload, "error": None}
        payload["guest_token"] = guest_token
        payload["session_id"] = request.session_id
        if user:
            payload["user_id"] = payload.get("clinical_subject_id") or str(user.id)
        if turn and turn.get("cached"):
            return turn["cached"]
        if emergency:
            result = {
                **payload,
                "is_emergency": True,
                "ats_level": emergency.ats_level.value,
                "max_booking_days": 0,
                "urgency_tier": emergency.urgency_tier.value,
                "workflow_status": "EMERGENCY",
                "emergency_warning": emergency.patient_guidance,
                "response": emergency.patient_guidance,
            }
        elif control == "human":
            response = waiting_response(request.session_id)
            if user and turn:
                await service.complete(turn, response, payload)
            return response
        else:
            if state_context.get("handover_summary"):
                payload["metadata"] = {
                    **(payload.get("metadata") or {}),
                    "coordinator_handover_summary": state_context["handover_summary"],
                }
            result = await agent.ainvoke(
                payload, config={"configurable": {"thread_id": graph_thread(request.session_id, user, guest_token)}}
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        result["elapsed_ms"] = elapsed_ms
        response = public_result(result, request.session_id, elapsed_ms=elapsed_ms)
        if not response["response"].strip():
            raise RuntimeError("Empty agent response")
        if case_id is not None:
            try:
                async with get_session_factory()() as coordination_db:
                    response = await after_turn(coordination_db, case_id, request, response, result)
            except SQLAlchemyError as exc:
                logger.warning("coordination after_turn unavailable; returning AI response: %s", type(exc).__name__)
        if user:
            await service.complete(turn, response, result)
            await ChatTakeoverService(service.session).ensure_case_from_result(
                user,
                request.session_id,
                request.message,
                response,
            )
        logger.info(
            "chat.completed agent_ms=%.0f archive_ms=%.0f",
            (agent_finished - started) * 1000,
            (time.perf_counter() - agent_finished) * 1000,
        )
        if user:
            # Persist cross-session facts only after the turn has been archived.
            try:
                from src.medical_assistant.domain.patient_memory_service import get_patient_memory_service

                mem_svc = get_patient_memory_service()
                fac = result.get("facility_preference")
                if fac:
                    await mem_svc.save_patient_fact(
                        user_id=__import__("uuid").UUID(payload.get("clinical_subject_id") or str(user.id)),
                        category="facility_preference",
                        fact_key="preferred_facility",
                        fact_value={"name": fac},
                        provenance="patient_reported",
                        source_session_id=request.session_id,
                    )
                if result.get("workflow_status") == "HOLD_BOOKING" and result.get("selected_slot"):
                    await mem_svc.create_open_loop(
                        user_id=__import__("uuid").UUID(payload.get("clinical_subject_id") or str(user.id)),
                        loop_type="slot_hold_unconfirmed",
                        payload=result.get("selected_slot") or {},
                        due_minutes=15,
                    )
            except Exception as exc:
                logger.warning("Could not persist cross-session memory after turn: %s", exc)
        return response
    except BaseException:
        if turn and not turn.get("cached"):
            with suppress(Exception):
                await service.fail(turn)
        raise


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    user=Depends(optional_chat_user),
    session: AsyncSession = Depends(get_auth_db_session),
):
    payload, turn, service = await prepare_turn(request, user, session)
    try:
        return await run_turn(request, user, payload, turn, service, http_request.state.coordination_guest)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("medical_assistant.chat failed")
        raise HTTPException(503, "Không thể hoàn tất hoặc lưu hội thoại lúc này. Vui lòng thử lại.") from exc


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    user=Depends(optional_chat_user),
    session: AsyncSession = Depends(get_auth_db_session),
):
    payload, turn, service = await prepare_turn(request, user, session)

    async def event_generator():
        task = None
        try:
            yield f"data: {json.dumps({'type': 'init', 'session_id': request.session_id})}\n\n"
            task = asyncio.create_task(
                run_turn(request, user, payload, turn, service, http_request.state.coordination_guest)
            )
            while not task.done():
                if await http_request.is_disconnected():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                    return
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=5)
                except TimeoutError:
                    yield ": keep-alive\n\n"
            result = await task
            # The complete turn is durable before any answer is sent to the client.
            for word in result["response"].splitlines(keepends=True):
                yield f"data: {json.dumps({'type': 'token', 'content': word}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'metadata', **{k: v for k, v in result.items() if k not in ('response', 'analysis', 'session_id')}}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("medical_assistant.chat_stream failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Không thể hoàn tất hoặc lưu hội thoại. Vui lòng thử lại.'}, ensure_ascii=False)}\n\n"
        finally:
            if task and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            elif task is None and turn and not turn.get("cached"):
                with suppress(Exception):
                    await service.fail(turn)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/conversations")
async def conversations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_auth_db_session),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    patient_profile_id: __import__("uuid").UUID | None = None,
):
    return await ChatHistoryService(session).list_conversations(user.id, limit, offset, patient_profile_id)


@router.delete("/chat/conversations/{session_id}")
async def delete_conversation(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_auth_db_session),
):
    await ChatHistoryService(session).delete_conversation(user, session_id)
    return {"deleted": True}


@router.get("/chat/conversations/{session_id}")
async def conversation_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_auth_db_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await ChatHistoryService(session).history(user.id, session_id, limit, offset)


@router.get("/chat/conversations/{session_id}/takeover")
async def takeover_conversation(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_auth_db_session),
):
    """Return the authenticated patient's takeover state and staff messages."""
    service = ChatTakeoverService(session)
    case = await service.get_case_for_patient(user.id, session_id)
    if case is None:
        return {"case": None, "messages": []}
    messages = await service.repository.list_messages(case.id, 200)
    return {"case": case_payload(case), "messages": [message_payload(message) for message in messages]}


@router.post("/booking-requests", response_model=BookingIntakeResponse, status_code=201)
async def create_booking_request(
    request: BookingIntakeRequest,
    http_request: Request,
    user=Depends(optional_chat_user),
    session: AsyncSession = Depends(get_auth_db_session),
) -> BookingIntakeResponse:
    """Create a durable HITL request; never claim success before DB insertion."""
    if not request.consent_to_contact:
        raise HTTPException(status_code=422, detail="Cần đồng ý để điều phối viên liên hệ.")

    config = {
        "configurable": {"thread_id": graph_thread(request.session_id, user, http_request.state.coordination_guest)}
    }
    snapshot = await agent.aget_state(config)
    state = dict(snapshot.values or {})
    if not state and user:
        state = await ChatHistoryService(session).checkpoint(user.id, request.session_id)
    if not state:
        state = {
            "suggested_department_name": request.specialty_name or "Tư vấn tổng quát",
            "is_emergency": False,
            "available_slots": [],
            "collected_details": [request.patient_notes] if request.patient_notes else [],
        }
    if state.get("is_emergency"):
        raise HTTPException(status_code=409, detail="Ca có dấu hiệu cấp cứu không được chuyển sang đặt lịch thường.")

    available_doctors = state.get("available_slots") or []
    chosen_doctor = None
    chosen_slot = None
    if request.preferred_doctor_id:
        chosen_doctor = next(
            (doctor for doctor in available_doctors if str(doctor.get("id")) == request.preferred_doctor_id),
            None,
        )
    if request.selected_slot_id:
        for doctor in available_doctors:
            slot = next(
                (
                    item
                    for item in doctor.get("available_slots", [])
                    if str(item.get("schedule_id")) == request.selected_slot_id
                ),
                None,
            )
            if slot:
                chosen_doctor, chosen_slot = doctor, slot
                break

    _context = {
        "user_id": str(user.id) if user else None,
        "specialty_code": request.specialty_code or state.get("suggested_department_code"),
        "specialty_name": request.specialty_name or state.get("suggested_department_name") or "Chuyên khoa phù hợp",
        "doctor_id": chosen_doctor.get("id") if chosen_doctor else None,
        "doctor_name": chosen_doctor.get("full_name") if chosen_doctor else None,
        "schedule_id": chosen_slot.get("schedule_id") if chosen_slot else None,
        "symptoms_summary": (request.patient_notes or " | ".join(state.get("collected_details") or []))[:2000] or None,
    }
    try:
        from src.db.session import get_session_factory
        from src.services.workbench import intake

        await session.commit()
        async with get_session_factory()() as coordination_db, coordination_db.begin():
            case = await intake(coordination_db, request, user, http_request.state.coordination_guest, state)
            result = {
                "request_id": str(case.id),
                "request_code": "YC-" + str(case.id).split("-")[0].upper(),
                "status": "PENDING_CONTACT",
            }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BookingPersistenceError as exc:
        raise HTTPException(
            status_code=503,
            detail="Yêu cầu chưa được lưu. Vui lòng thử lại hoặc liên hệ trực tiếp bệnh viện.",
        ) from exc

    return BookingIntakeResponse(
        saved=True,
        **result,
        message=(
            "Yêu cầu đã được lưu vào hàng đợi điều phối. "
            "Điều phối viên sẽ liên hệ để xác minh thông tin và chốt lịch; đây chưa phải lịch khám đã xác nhận."
        ),
    )


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {
        "status": "ready",
        "agent": "LangGraph Clinical Triage Agent v1.0",
        "features": ["session_memory", "sse_streaming", "ats_triage"],
    }
