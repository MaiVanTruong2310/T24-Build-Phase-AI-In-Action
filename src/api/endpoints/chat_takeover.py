"""Staff and patient realtime APIs for human-in-the-loop chat takeover."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.api.dependencies import require_staff
from src.api.response import success_response
from src.core.security import decode_access_token
from src.db.dependencies import get_db_session
from src.db.session import get_auth_session_factory, get_session_factory
from src.models.user import User
from src.realtime.chat_takeover import chat_takeover_manager, user_id_from_payload
from src.repositories.user import UserRepository
from src.schemas.chat_takeover import (
    ChatTakeoverCaseDetail,
    ChatTakeoverCaseResponse,
    ChatTakeoverMessageCreate,
    ChatTakeoverMessageResponse,
)
from src.schemas.common import ApiResponse
from src.services.chat_takeover import ChatTakeoverService, case_payload, message_payload
from src.services.cookie_session import ACCESS_COOKIE

router = APIRouter(prefix="/staff/chat-takeover", tags=["chat-takeover"])


def get_takeover_service(session: AsyncSession = Depends(get_db_session)) -> ChatTakeoverService:
    return ChatTakeoverService(session)


def case_response(case) -> ChatTakeoverCaseResponse:
    return ChatTakeoverCaseResponse.model_validate(case_payload(case))


def message_response(message_payload_value: dict) -> ChatTakeoverMessageResponse:
    return ChatTakeoverMessageResponse.model_validate(message_payload_value)


@router.get("/cases", response_model=ApiResponse[list[ChatTakeoverCaseResponse]])
async def list_cases(
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_staff),
    service: ChatTakeoverService = Depends(get_takeover_service),
) -> ApiResponse[list[ChatTakeoverCaseResponse]]:
    cases = await service.list_cases(status, offset, limit, current_user.id)
    return success_response([case_response(case) for case in cases], "Takeover cases retrieved")


@router.get("/cases/{case_id}", response_model=ApiResponse[ChatTakeoverCaseDetail])
async def get_case(
    case_id: UUID,
    current_user: User = Depends(require_staff),
    service: ChatTakeoverService = Depends(get_takeover_service),
) -> ApiResponse[ChatTakeoverCaseDetail]:
    case = await service.get_case(case_id, current_user.id)
    messages = await service.history(case)
    return success_response(
        ChatTakeoverCaseDetail(
            case=case_response(case),
            messages=[message_response(message) for message in messages],
        ),
        "Takeover case retrieved",
    )


@router.post("/cases/{case_id}/claim", response_model=ApiResponse[ChatTakeoverCaseResponse])
async def claim_case(
    case_id: UUID,
    current_user: User = Depends(require_staff),
    service: ChatTakeoverService = Depends(get_takeover_service),
) -> ApiResponse[ChatTakeoverCaseResponse]:
    return success_response(case_response(await service.claim(case_id, current_user.id)), "Takeover case claimed")


@router.post("/cases/{case_id}/release", response_model=ApiResponse[ChatTakeoverCaseResponse])
async def release_case(
    case_id: UUID,
    current_user: User = Depends(require_staff),
    service: ChatTakeoverService = Depends(get_takeover_service),
) -> ApiResponse[ChatTakeoverCaseResponse]:
    return success_response(case_response(await service.release(case_id, current_user.id)), "Takeover case released")


@router.post("/cases/{case_id}/resolve", response_model=ApiResponse[ChatTakeoverCaseResponse])
async def resolve_case(
    case_id: UUID,
    current_user: User = Depends(require_staff),
    service: ChatTakeoverService = Depends(get_takeover_service),
) -> ApiResponse[ChatTakeoverCaseResponse]:
    return success_response(case_response(await service.resolve(case_id, current_user.id)), "Takeover case resolved")


@router.post("/cases/{case_id}/messages", response_model=ApiResponse[ChatTakeoverMessageResponse])
async def send_message(
    case_id: UUID,
    request: ChatTakeoverMessageCreate,
    current_user: User = Depends(require_staff),
    service: ChatTakeoverService = Depends(get_takeover_service),
) -> ApiResponse[ChatTakeoverMessageResponse]:
    message = await service.send_staff_message(case_id, current_user.id, request.content, request.client_message_id)
    return success_response(message_response(message_payload(message)), "Takeover message sent")


async def authenticate_socket(websocket: WebSocket) -> User | None:
    token = websocket.query_params.get("token") or websocket.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = user_id_from_payload(payload)
        async with get_auth_session_factory()() as session:
            user = await UserRepository(session).get_by_id(user_id)
            await session.commit()
            if user is None or user.status != "active":
                return None
            return user
    except Exception:
        return None


@router.websocket("/ws/staff")
async def staff_socket(websocket: WebSocket) -> None:
    user = await authenticate_socket(websocket)
    if user is None or user.role != "staff":
        await websocket.close(code=1008)
        return
    async with get_session_factory()() as session:
        if not await ChatTakeoverService(session).staff_access(user.id):
            await websocket.close(code=1008)
            return
    await chat_takeover_manager.connect_staff(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        chat_takeover_manager.disconnect_staff(websocket)


@router.websocket("/ws/{session_id}")
async def patient_socket(session_id: str, websocket: WebSocket) -> None:
    user = await authenticate_socket(websocket)
    if user is None:
        await websocket.close(code=1008)
        return
    async with get_session_factory()() as session:
        case = await ChatTakeoverService(session).get_case_for_patient(user.id, session_id)
    if case is None:
        await websocket.close(code=1008)
        return
    await chat_takeover_manager.connect_session(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        chat_takeover_manager.disconnect_session(session_id, websocket)
