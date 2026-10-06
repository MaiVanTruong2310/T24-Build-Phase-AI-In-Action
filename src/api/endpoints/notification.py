"""Authenticated in-app notification endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.schemas.common import ApiResponse
from src.schemas.notification import NotificationResponse
from src.services.cookie_session import ACCESS_COOKIE
from src.utils.response_mappers import notification_response
from src.services.notification import NotificationService, notification_response

router = APIRouter(prefix="/notifications", tags=["notifications"])


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
    """List delivered notifications for the authenticated user."""
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
    """Mark all delivered notifications as read."""
    count = await service.mark_all_read(current_user.id)
    return success_response({"updated": count}, "Notifications marked as read")
