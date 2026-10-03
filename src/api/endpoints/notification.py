"""Authenticated in-app notification endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.api.dependencies import get_current_user
from src.api.response import success_response
from src.core.security import decode_access_token
from src.db.dependencies import get_db_session
from src.db.session import get_session_factory
from src.models.user import User
from src.realtime.notifications import notification_manager
from src.repositories.user import UserRepository
from src.schemas.common import ApiResponse
from src.schemas.notification import NotificationResponse
from src.services.cookie_session import ACCESS_COOKIE
from src.services.notification import NotificationService, notification_response

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.websocket("/ws")
async def notification_websocket(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    """Authenticate a notification socket with a bearer token or access cookie."""
    try:
        token = token or websocket.cookies.get(ACCESS_COOKIE)
        if not token:
            raise ValueError("missing access token")
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
        async with get_session_factory()() as session:
            user = await UserRepository(session).get_by_id(user_id)
            if user is None or user.status != "active":
                raise ValueError("inactive user")
    except Exception:
        await websocket.close(code=1008)
        return

    await notification_manager.connect(user_id, websocket)
    try:
        while True:
            # Receiving also detects a closed browser tab promptly. The
            # client can send an optional keepalive message at any time.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        notification_manager.disconnect(user_id, websocket)


def get_notification_service(session: AsyncSession = Depends(get_db_session)) -> NotificationService:
    """Build the notification service for the current request."""
    return NotificationService(session)


@router.get("", response_model=ApiResponse[list[NotificationResponse]])
async def list_notifications(
    unread_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> ApiResponse[list[NotificationResponse]]:
    """List visible notifications for the authenticated user."""
    values = await service.list_for_user(current_user.id, unread_only=unread_only, offset=offset, limit=limit)
    return success_response([notification_response(value) for value in values], "Notifications retrieved")


@router.post("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> ApiResponse[NotificationResponse]:
    """Mark one owned notification as read."""
    value = await service.mark_read(current_user.id, notification_id)
    return success_response(notification_response(value), "Notification marked as read")


@router.post("/read-all", response_model=ApiResponse[dict[str, int]])
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> ApiResponse[dict[str, int]]:
    """Mark all visible notifications as read."""
    count = await service.mark_all_read(current_user.id)
    return success_response({"updated": count}, "Notifications marked as read")
