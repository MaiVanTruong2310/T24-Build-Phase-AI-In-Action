import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat đồng bộ với AI agent có quản lý ngữ cảnh qua session_id (thread_id)."""
    try:
        config = {"configurable": {"thread_id": request.session_id}}
        result = await agent.ainvoke(
            {"query": request.message, "user_id": request.user_id, "enable_citation": request.enable_citation},
            config=config,
        )

        meta = result.get("metadata", {})
        token_usage = result.get("token_usage") or meta.get("token_usage")
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
            session_id=request.session_id,
            ats_level=result.get("ats_level"),
            max_booking_days=result.get("max_booking_days"),
            quick_replies=meta.get("quick_replies", []),
            is_emergency=result.get("is_emergency", False),
            token_usage=token_usage,
            workflow_status=result.get("workflow_status"),
            booking_intake=meta.get("booking_intake"),
            suggested_department=result.get("suggested_department_name"),
            candidate_specialties=result.get("candidate_specialties") or meta.get("candidate_specialties", []),
            conflict_reason=result.get("conflict_reason") or meta.get("conflict_reason"),
            acuity_status=result.get("acuity_status") or meta.get("acuity_status"),
            disposition=result.get("disposition") or meta.get("disposition"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat thời gian thực sử dụng Server-Sent Events (SSE).
    - Stream token phản hồi ngay lập tức cho client.
    - Duy trì state và conversation history theo session_id (thread_id).
    - Truyền metadata (quick_replies, ats_level, max_booking_days, token_usage) ở cuối stream.
    """
    async def event_generator():
        try:
            config = {"configurable": {"thread_id": request.session_id}}

            # 1. Bắn event khởi động phiên
            yield f"data: {json.dumps({'type': 'init', 'session_id': request.session_id})}\n\n"

            # 2. Thực thi Agent
            result = await agent.ainvoke(
                {"query": request.message, "user_id": request.user_id, "enable_citation": request.enable_citation},
                config=config,
            )

            response_text = result.get("response", "")
            meta = result.get("metadata", {})
            quick_replies = meta.get("quick_replies", [])
            ats_level = result.get("ats_level")
            max_booking_days = result.get("max_booking_days")
            is_emergency = result.get("is_emergency", False)
            token_usage = result.get("token_usage") or meta.get("token_usage")

            # 3. Stream phản hồi dạng text chunk (giả lập streaming mượt mà cho UI)
            # Với LLM stream trực tiếp thì event on_chat_model_stream sẽ emit từng token
            words = response_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                payload = json.dumps({"type": "token", "content": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0.015)  # Hiệu ứng gõ mượt 15ms

            # 4. Bắn event metadata (chuyên khoa, quick replies, ATS level, token_usage, analysis)
            meta_payload = json.dumps({
                "type": "metadata",
                "analysis": result.get("analysis", ""),
                "ats_level": ats_level,
                "max_booking_days": max_booking_days,
                "is_emergency": is_emergency,
                "quick_replies": quick_replies,
                "suggested_department": result.get("suggested_department_name"),
                "token_usage": token_usage,
                "workflow_status": result.get("workflow_status"),
                "booking_intake": meta.get("booking_intake"),
                "candidate_specialties": result.get("candidate_specialties") or meta.get("candidate_specialties", []),
                "conflict_reason": result.get("conflict_reason") or meta.get("conflict_reason"),
                "acuity_status": result.get("acuity_status") or meta.get("acuity_status"),
                "disposition": result.get("disposition") or meta.get("disposition"),
            }, ensure_ascii=False)
            yield f"data: {meta_payload}\n\n"

            # 5. Kết thúc stream chuẩn SSE
            yield "data: [DONE]\n\n"

        except Exception as err:
            err_payload = json.dumps({"type": "error", "message": str(err)}, ensure_ascii=False)
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no"  # Chống Nginx buffer làm chậm SSE
        }
    )


@router.post("/booking-requests", response_model=BookingIntakeResponse, status_code=201)
async def create_booking_request(request: BookingIntakeRequest) -> BookingIntakeResponse:
    """Create a durable HITL request; never claim success before DB insertion."""
    if not request.consent_to_contact:
        raise HTTPException(status_code=422, detail="Cần đồng ý để điều phối viên liên hệ.")

    config = {"configurable": {"thread_id": request.session_id}}
    snapshot = await agent.aget_state(config)
    state = dict(snapshot.values or {})
    if not state:
        raise HTTPException(status_code=409, detail="Phiên tư vấn không còn hiệu lực. Vui lòng trao đổi lại với trợ lý.")
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
                (item for item in doctor.get("available_slots", []) if str(item.get("schedule_id")) == request.selected_slot_id),
                None,
            )
            if slot:
                chosen_doctor, chosen_slot = doctor, slot
                break
        if chosen_slot is None or not chosen_slot.get("verified"):
            raise HTTPException(status_code=400, detail="Khung giờ này chưa được database xác minh hoặc không còn trong phiên.")

    context = {
        "user_id": state.get("user_id"),
        "specialty_code": state.get("suggested_department_code"),
        "specialty_name": state.get("suggested_department_name"),
        "doctor_id": chosen_doctor.get("id") if chosen_doctor else None,
        "doctor_name": chosen_doctor.get("full_name") if chosen_doctor else None,
        "schedule_id": chosen_slot.get("schedule_id") if chosen_slot else None,
        "symptoms_summary": " | ".join(state.get("collected_details") or [])[:2000] or None,
    }
    try:
        result = BookingRequestService().submit(request, context)
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
        "features": ["session_memory", "sse_streaming", "ats_triage"]
    }
