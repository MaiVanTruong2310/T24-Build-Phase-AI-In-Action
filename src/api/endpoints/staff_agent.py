"""Staff-only assistant API."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_staff
from src.api.response import success_response
from src.db.dependencies import get_auth_db_session, get_db_session
from src.models.user import User
from src.schemas.common import ApiResponse
from src.schemas.staff_agent import (
    StaffAgentActionRequest,
    StaffAgentActionResponse,
    StaffAgentChatRequest,
    StaffAgentChatResponse,
)
from src.services.staff_agent import StaffAgentService

router = APIRouter(prefix="/staff/assistant", tags=["staff-assistant"])


def get_staff_agent_service(
    session: AsyncSession = Depends(get_db_session),
    patient_session: AsyncSession = Depends(get_auth_db_session),
) -> StaffAgentService:
    return StaffAgentService(session, patient_session=patient_session)


@router.post("/chat", response_model=ApiResponse[StaffAgentChatResponse])
async def staff_assistant_chat(
    request: StaffAgentChatRequest,
    staff: User = Depends(require_staff),
    service: StaffAgentService = Depends(get_staff_agent_service),
) -> ApiResponse[StaffAgentChatResponse]:
    """Answer a staff question using private, read-only staff tools."""
    response = await service.chat(staff, request)
    return success_response(response, "Staff assistant replied")


@router.post("/chat/stream")
async def staff_assistant_chat_stream(
    request: StaffAgentChatRequest,
    staff: User = Depends(require_staff),
    service: StaffAgentService = Depends(get_staff_agent_service),
) -> StreamingResponse:
    """Stream staff assistant replies with real-time SSE events."""
    return StreamingResponse(
        service.chat_stream(staff, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/confirm", response_model=ApiResponse[StaffAgentActionResponse])
async def confirm_staff_assistant_action(
    request: StaffAgentActionRequest,
    staff: User = Depends(require_staff),
    service: StaffAgentService = Depends(get_staff_agent_service),
) -> ApiResponse[StaffAgentActionResponse]:
    response = await service.confirm_action(staff, request)
    return success_response(response, "Booking review completed")


@router.post("/chat/cancel", response_model=ApiResponse[StaffAgentActionResponse])
async def cancel_staff_assistant_action(
    request: StaffAgentActionRequest,
    staff: User = Depends(require_staff),
    service: StaffAgentService = Depends(get_staff_agent_service),
) -> ApiResponse[StaffAgentActionResponse]:
    response = await service.cancel_action(staff, request)
    return success_response(response, "Booking review proposal cancelled")
