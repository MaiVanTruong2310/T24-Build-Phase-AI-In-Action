"""Realtime cho điều phối viên ↔ bệnh nhân: vé WebSocket và hai kênh (staff, phiên chat của bệnh nhân).

Dữ liệu ca/tin nhắn nằm ở Workbench (`coordination_cases`); REST thao tác ca ở `/staff/workbench`.
Các REST `/staff/chat-takeover/cases*` cũ (lớp tương thích, frontend không còn gọi) đã gỡ.
Đường dẫn `/staff/chat-takeover/...` giữ nguyên để không phải đổi client WebSocket.
"""

import re

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.api.dependencies import get_current_user
from src.api.response import success_response
from src.db.session import get_auth_session_factory, get_session_factory
from src.models.user import User
from src.models.workbench import CoordinationCase, CoordinatorMember
from src.realtime.chat_takeover import chat_takeover_manager, takeover_tickets
from src.repositories.user import UserRepository
from src.schemas.common import ApiResponse
from src.services.cookie_session import ACCESS_COOKIE
from src.services.supabase_auth import authenticated_profile
from src.services.workbench import owner_key

router = APIRouter(prefix="/staff/chat-takeover", tags=["chat-takeover"])

# Cookie khách đặt ở middleware (src/main.py): 64 ký tự hex.
GUEST_COOKIE = "coordination_guest"
_GUEST_TOKEN = re.compile(r"[0-9a-f]{64}")


@router.get("/ticket", response_model=ApiResponse[dict[str, str]])
async def get_takeover_ticket(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict[str, str]]:
    """Issue an opaque, short-lived ticket for the WebSocket handshake."""
    return success_response({"token": takeover_tickets.issue(current_user.id)}, "Takeover ticket issued")


async def authenticate_socket(websocket: WebSocket) -> User | None:
    """Resolve the socket user from a takeover ticket or the Supabase session cookie.

    ``?token=`` carries an opaque ticket minted by ``GET /staff/chat-takeover/ticket``;
    the ``p124_access`` cookie carries the Supabase access token and is verified
    against Supabase Auth like every HTTP request.
    """
    ticket = websocket.query_params.get("token")
    if ticket:
        user_id = takeover_tickets.redeem(ticket)
        if user_id is None:
            return None
        async with get_auth_session_factory()() as session:
            user = await UserRepository(session).get_by_id(user_id)
            await session.commit()
            if user is None or user.status != "active":
                return None
            return user

    access_token = websocket.cookies.get(ACCESS_COOKIE)
    if not access_token:
        return None
    try:
        async with get_auth_session_factory()() as session:
            return await authenticated_profile(access_token, session)
    except Exception:
        return None


async def staff_access(user_id) -> bool:
    """Chỉ điều phối viên đang được bật quyền mới nghe kênh staff."""
    async with get_session_factory()() as session:
        member = await session.get(CoordinatorMember, user_id)
        await session.commit()
    return bool(member and member.enabled)


@router.websocket("/ws/staff")
async def staff_socket(websocket: WebSocket) -> None:
    user = await authenticate_socket(websocket)
    if user is None or user.role != "staff" or not await staff_access(user.id):
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


async def owns_session(session_id: str, user: User, guest_token: str | None = None) -> bool:
    """Phiên chưa có ca nào (vừa mở chat) hoặc mọi ca của phiên thuộc về người này.

    Tính cả ca người này tạo lúc còn là khách trên cùng trình duyệt (cookie khách), để chat khách rồi đăng nhập
    giữa chừng không mất realtime. Trước đây mọi tài khoản đăng nhập đều nghe được bất kỳ session_id nào.
    """
    own_keys = [owner_key(user, None)]
    if guest_token and _GUEST_TOKEN.fullmatch(guest_token):
        own_keys.append(owner_key(None, guest_token))
    async with get_session_factory()() as session:
        foreign_case = await session.scalar(
            select(CoordinationCase.id)
            .where(
                CoordinationCase.session_id == session_id,
                CoordinationCase.owner_key.not_in(own_keys),
                or_(CoordinationCase.patient_id.is_(None), CoordinationCase.patient_id != user.id),
                or_(CoordinationCase.requested_by_user_id.is_(None), CoordinationCase.requested_by_user_id != user.id),
            )
            .limit(1)
        )
        await session.commit()
    return foreign_case is None


@router.websocket("/ws/{session_id}")
async def patient_socket(session_id: str, websocket: WebSocket) -> None:
    user = await authenticate_socket(websocket)
    if user is None or not await owns_session(session_id, user, websocket.cookies.get(GUEST_COOKIE)):
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
