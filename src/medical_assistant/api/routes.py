import asyncio
import json
import logging
import time
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.db.dependencies import get_auth_db_session
from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.booking_request_service import (
    BookingPersistenceError,
    BookingRequestService,
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
        profile = request.patient_profile.model_dump()
        payload.update(patient_profile=profile, patient_name=profile["name"], patient_phone=profile["phone"])
    return payload


async def optional_chat_user(http_request: Request, session: AsyncSession = Depends(get_auth_db_session)):
    from src.services.cookie_session import request_token

    token = request_token(http_request)
    if not token:
        if http_request.headers.get("x-session-expected") == "1":
            raise HTTPException(401, "Cần gia hạn phiên đăng nhập.")
        return None
    return await get_current_user(token, session)


def public_result(result, session_id):
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
        quick_replies=meta.get("quick_replies", []),
        booking_intake=meta.get("booking_intake"),
        suggested_department=result.get("suggested_department_name"),
        candidate_specialties=result.get("candidate_specialties") or meta.get("candidate_specialties", []),
    )
    return ChatResponse(**payload).model_dump(mode="json")


async def prepare_turn(request, user, session):
    started = time.perf_counter()
    service = ChatHistoryService(session)
    turn = await service.begin_turn(user, request) if user else None
    payload = chat_agent_input(request)
    payload["user_id"] = str(user.id) if user else None
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
        payload.update(
            patient_profile={"name": user.full_name or "", "phone": user.phone or ""},
            patient_name=user.full_name,
            patient_phone=user.phone,
            patient_health_record=health_record(user),
        )
    else:
        payload["patient_health_record"] = None
    logger.info("chat.prepare elapsed_ms=%.0f", (time.perf_counter() - started) * 1000)
    return payload, turn, service


async def run_turn(request, user, payload, turn, service):
    if turn and turn.get("cached"):
        return turn["cached"]
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
        if not response["response"].strip():
            raise RuntimeError("Empty agent response")
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
        return response
    except BaseException:
        if turn:
            with suppress(Exception):
                await service.fail(turn)
        raise


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, user=Depends(optional_chat_user), session: AsyncSession = Depends(get_auth_db_session)
):
    payload, turn, service = await prepare_turn(request, user, session)
    try:
        return await run_turn(request, user, payload, turn, service)
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
            task = asyncio.create_task(run_turn(request, user, payload, turn, service))
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
):
    return await ChatHistoryService(session).list_conversations(user.id, limit, offset)


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
    user=Depends(optional_chat_user),
    session: AsyncSession = Depends(get_auth_db_session),
) -> BookingIntakeResponse:
    """Create a durable HITL request; never claim success before DB insertion."""
    if not request.consent_to_contact:
        raise HTTPException(status_code=422, detail="Cần đồng ý để điều phối viên liên hệ.")

    config = {"configurable": {"thread_id": graph_thread(request.session_id, user)}}
    snapshot = await agent.aget_state(config)
    state = dict(snapshot.values or {})
    if not state and user:
        state = await ChatHistoryService(session).checkpoint(user.id, request.session_id)
    if not state:
        raise HTTPException(
            status_code=409, detail="Phiên tư vấn không còn hiệu lực. Vui lòng trao đổi lại với trợ lý."
        )
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
        if chosen_doctor is None:
            raise HTTPException(status_code=400, detail="Bác sĩ được chọn không thuộc kết quả của phiên hiện tại.")
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
        if chosen_slot is None or not chosen_slot.get("verified"):
            raise HTTPException(
                status_code=400, detail="Khung giờ này chưa được database xác minh hoặc không còn trong phiên."
            )

    context = {
        "user_id": str(user.id) if user else None,
        "specialty_code": state.get("suggested_department_code"),
        "specialty_name": state.get("suggested_department_name"),
        "doctor_id": chosen_doctor.get("id") if chosen_doctor else None,
        "doctor_name": chosen_doctor.get("full_name") if chosen_doctor else None,
        "schedule_id": chosen_slot.get("schedule_id") if chosen_slot else None,
        "symptoms_summary": " | ".join(state.get("collected_details") or [])[:2000] or None,
    }
    try:
        result = await asyncio.to_thread(BookingRequestService().submit, request, context)
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
