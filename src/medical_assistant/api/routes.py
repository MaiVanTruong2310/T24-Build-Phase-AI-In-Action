import asyncio
import json
import logging
import re
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
)
from src.medical_assistant.domain.schemas import (
    BookingIntakeRequest,
    BookingIntakeResponse,
    ChatRequest,
    ChatResponse,
)
from src.medical_assistant.infrastructure.llm import llm_usage_sink
from src.medical_assistant.infrastructure.turn_timing import notify_progress, turn_progress, turn_timings
from src.models.user import User
from src.services.chat_history import STATE_FIELDS, ChatHistoryService, graph_thread, health_record

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
        timings_ms=result.get("timings_ms"),
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
        from sqlalchemy import select

        from src.db.session import get_session_factory
        from src.models.patient_profile import PatientProfile
        from src.services.patient_profiles import resolve_patient

        async with get_session_factory()() as profile_db:
            if request.patient_profile_id is None:
                request.patient_profile_id = (
                    await profile_db.execute(select(PatientProfile.id).where(PatientProfile.linked_user_id == user.id))
                ).scalar_one_or_none()
            subject, selected_profile = await resolve_patient(profile_db, user, request.patient_profile_id)
    elif request.patient_profile_id:
        raise HTTPException(403, "Cần đăng nhập để chọn hồ sơ người thân.")
    service = ChatHistoryService(session)
    memory_profile: list = []
    open_loops: list = []
    if user:
        # begin_turn (phiên auth của request) và 2 truy vấn bộ nhớ dài hạn (mỗi cái tự mở phiên riêng) độc lập
        # nhau → chạy song song thay vì nối tiếp, bớt vài vòng truy vấn DB mỗi lượt.
        from src.medical_assistant.domain.patient_memory_service import get_patient_memory_service

        async def load_memory() -> tuple[list, list]:
            try:
                mem_svc = get_patient_memory_service()
                return tuple(  # type: ignore[return-value]
                    await asyncio.gather(
                        mem_svc.get_patient_profile(subject.id), mem_svc.get_active_open_loops(subject.id)
                    )
                )
            except Exception as exc:
                logger.warning("Could not load cross-session memory: %s", exc)
                return [], []

        turn, (memory_profile, open_loops) = await asyncio.gather(service.begin_turn(user, request), load_memory())
    else:
        turn = None
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
        # Cross-session Memory (Hồ sơ dài hạn & Open Loops) đã nạp song song ở trên.
        payload["patient_memory_profile"] = memory_profile
        payload["active_open_loops"] = open_loops
    else:
        payload["patient_health_record"] = None
        payload["is_authenticated"] = False
        payload["patient_memory_profile"] = []
        payload["active_open_loops"] = []
    payload["clinical_subject_id"] = str(subject.id) if subject else None
    logger.info("chat.prepare elapsed_ms=%.0f", (time.perf_counter() - started) * 1000)
    return payload, turn, service


async def run_turn(request, user, payload, turn, service, guest_token="", request_started: float | None = None):
    # request_started: mốc nhận request (gồm cả prepare_turn) để độ trễ hiển thị khớp thời gian người dùng chờ.
    started = time.perf_counter()
    request_started = request_started or started
    if turn and turn.get("cached"):
        return turn["cached"]
    step_timings: dict[str, float] = {}
    turn_timings.set(step_timings)  # before_turn và các node cộng dồn thời gian từng bước vào đây
    from src.db.session import get_session_factory
    from src.services.coordinator_chat import after_turn, before_turn, waiting_response

    try:
        async with get_session_factory()() as coordination_db:
            case_id, control, emergency, state_context = await before_turn(coordination_db, request, user, guest_token)
        before_ms = round((time.perf_counter() - started) * 1000, 1)
        graph_ms = 0.0
        if not user:
            payload = {**(state_context.get("checkpoint") or {}), **payload, "error": None}
        payload["guest_token"] = guest_token
        payload["session_id"] = request.session_id
        if user:
            payload["user_id"] = payload.get("clinical_subject_id") or str(user.id)
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
            llm_usage_sink.set([])  # gom usage thật của lượt này (xem respond_node)
            graph_started = time.perf_counter()
            result = await agent.ainvoke(
                payload, config={"configurable": {"thread_id": graph_thread(request.session_id, user, guest_token)}}
            )
            graph_ms = round((time.perf_counter() - graph_started) * 1000, 1)
        elapsed_ms = round((time.perf_counter() - request_started) * 1000, 1)
        result["elapsed_ms"] = elapsed_ms
        # Tách thời gian: ghi DB đầu lượt (before_turn) vs chạy graph (LLM + node) để biết chậm ở đâu.
        result["timings_ms"] = {"db_before_turn": before_ms, "agent_graph": graph_ms, **step_timings}
        logger.info("chat.timing elapsed_ms=%.0f %s", elapsed_ms, result["timings_ms"])
        response = public_result(result, request.session_id, elapsed_ms=elapsed_ms)
        if not response["response"].strip():
            raise RuntimeError("Empty agent response")
        notify_progress("saving")
        after_started = time.perf_counter()
        async with get_session_factory()() as coordination_db:
            response = await after_turn(coordination_db, case_id, request, response, result)
        step_timings["db:after_turn"] = round((time.perf_counter() - after_started) * 1000, 1)
        if user:
            complete_started = time.perf_counter()
            await service.complete(turn, response, result)
            step_timings["db:complete_turn"] = round((time.perf_counter() - complete_started) * 1000, 1)
            # Tự động đồng bộ hóa Cross-session Memory & Open Loops
            memory_started = time.perf_counter()
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
            step_timings["db:memory"] = round((time.perf_counter() - memory_started) * 1000, 1)
        total_ms = round((time.perf_counter() - request_started) * 1000, 1)
        if isinstance(response, dict) and "elapsed_ms" in response:
            response["elapsed_ms"] = total_ms  # thời gian thật tới khi câu trả lời sẵn sàng gửi
        logger.info("chat.timing_total total_ms=%.0f %s", total_ms, step_timings)
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
    request_started = time.perf_counter()

    def sse(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def event_generator():
        task = None
        turn = service = None
        # Gửi tín hiệu ngay (trước cả prepare_turn) để người dùng thấy phản hồi tức thì thay vì màn hình chờ trống.
        yield sse({"type": "init", "session_id": request.session_id})
        yield sse({"type": "status", "stage": "preparing"})
        try:
            payload, turn, service = await prepare_turn(request, user, session)
        except HTTPException as exc:
            yield sse({"type": "error", "message": str(exc.detail)})
            return
        except Exception:
            logger.exception("medical_assistant.chat_stream prepare failed")
            yield sse({"type": "error", "message": "Không thể hoàn tất hoặc lưu hội thoại. Vui lòng thử lại."})
            return

        # Các node graph báo giai đoạn qua turn_progress → đẩy ra client dưới dạng sự kiện "status".
        progress: asyncio.Queue[str] = asyncio.Queue()
        turn_progress.set(progress.put_nowait)
        try:
            task = asyncio.create_task(
                run_turn(
                    request,
                    user,
                    payload,
                    turn,
                    service,
                    http_request.state.coordination_guest,
                    request_started=request_started,
                )
            )
            last_beat = time.perf_counter()
            while not task.done():
                if await http_request.is_disconnected():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                    return
                getter = asyncio.ensure_future(progress.get())
                await asyncio.wait({task, getter}, timeout=1, return_when=asyncio.FIRST_COMPLETED)
                if getter.done():
                    yield sse({"type": "status", "stage": getter.result()})
                    last_beat = time.perf_counter()
                else:
                    getter.cancel()
                    if time.perf_counter() - last_beat >= 5:
                        yield ": keep-alive\n\n"
                        last_beat = time.perf_counter()
            result = await task
            # Câu trả lời chỉ được gửi sau khi đã qua critic (an toàn lâm sàng) và after_turn (điều phối viên
            # có thể đã tiếp quản) và đã lưu bền vững — không stream thẳng token chưa kiểm duyệt từ LLM.
            for chunk in re.findall(r"\S+\s*|\s+", result["response"]):
                yield sse({"type": "token", "content": chunk})
            yield sse(
                {
                    "type": "metadata",
                    **{k: v for k, v in result.items() if k not in ("response", "analysis", "session_id")},
                }
            )
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("medical_assistant.chat_stream failed")
            yield sse({"type": "error", "message": "Không thể hoàn tất hoặc lưu hội thoại. Vui lòng thử lại."})
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
async def agent_status(request: Request):
    """Kiểm tra trạng thái agent và sức khỏe các LLM providers."""
    llm_health = getattr(request.app.state, "llm_health", None)
    if llm_health is None:
        try:
            from src.medical_assistant.infrastructure.llm import get_llm

            llm_inst = get_llm()
            if hasattr(llm_inst, "acheck_health"):
                llm_health = await llm_inst.acheck_health()
        except Exception as exc:
            llm_health = {"error": str(exc)}
    return {
        "status": "ready",
        "agent": "LangGraph Clinical Triage Agent v1.0",
        "features": ["session_memory", "sse_streaming", "ats_triage"],
        "llm_health": llm_health,
    }


@router.get("/admin/metrics/daily")
async def daily_metrics(date: str | None = Query(None, description="Ngày cần xem thống kê (YYYY-MM-DD)")):
    """Thống kê tỷ lệ fallback/clarify/data_unavailable theo ngày từ structured telemetry log."""
    from src.medical_assistant.infrastructure.telemetry_logger import get_daily_telemetry_metrics

    return get_daily_telemetry_metrics(target_date=date)
