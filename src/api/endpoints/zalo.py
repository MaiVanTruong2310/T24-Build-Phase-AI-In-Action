"""API endpoints for Zalo Bot Webhook integration."""

from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from src.config import get_settings
from src.core.logging import get_logger
from src.zalo.client import ZaloBotClient
from src.zalo.schemas import ZaloWebhookPayload
from src.zalo.service import ZaloBotService

logger = get_logger(__name__)

router = APIRouter(prefix="/zalo", tags=["zalo"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_zalo_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_bot_api_secret_token: str | None = Header(default=None, alias="x-bot-api-secret-token"),
):
    """Receive and process incoming events from Zalo Bot Platform via Webhook."""
    settings = get_settings()

    # Validate secret token if configured
    if settings.zalo_bot_secret_token:
        if x_bot_api_secret_token != settings.zalo_bot_secret_token:
            logger.warning("Rejected Zalo webhook with invalid secret token")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid secret token",
            )

    # Webhook phải luôn trả 2xx nhanh khi đã qua kiểm tra secret: request rỗng / cấu trúc lạ (testWebhook của Zalo,
    # loại sự kiện mới) từng nhận 400 → Zalo báo webhook lỗi. Không đọc được thì ghi log (không ghi nội dung) và bỏ qua.
    try:
        payload = ZaloWebhookPayload.model_validate_json((await request.body()) or b"{}")
    except ValueError as exc:
        logger.info("Ignored unparseable Zalo webhook payload (%s)", type(exc).__name__)
        return {"ok": True, "message": "Event ignored"}

    # Process event asynchronously in the background to ensure immediate HTTP 200 response (< 5s requirement)
    # Không ghi nội dung tin nhắn / tên người gửi vào log (dữ liệu sức khỏe cá nhân)
    result = payload.result
    logger.info(
        "Received Zalo webhook event=%s message_id=%s",
        (result.event_name if result else payload.event_name),
        ((result.message if result else payload.message) or SimpleNamespace(message_id=None)).message_id,
    )
    service = ZaloBotService()
    background_tasks.add_task(service.handle_webhook_event, payload)

    return {"ok": True, "message": "Event queued successfully"}


@router.get("/status")
async def get_zalo_bot_status():
    """Check configuration status of Zalo Bot."""
    settings = get_settings()
    client = ZaloBotClient()
    bot_info = None

    if client.is_configured:
        try:
            bot_info = await client.get_me()
        except Exception as e:
            bot_info = {"error": str(e)}

    return {
        "is_configured": client.is_configured,
        "mode": settings.zalo_bot_mode,
        "webhook_url": settings.zalo_webhook_url or None,
        "secret_token_configured": bool(settings.zalo_bot_secret_token),
        "bot_info": bot_info,
    }


@router.get("/setup-webhook", operation_id="setup_zalo_webhook_get")
@router.post("/setup-webhook", operation_id="setup_zalo_webhook_post")
async def setup_zalo_webhook():
    """Trigger registration of the configured Webhook URL with Zalo Bot Platform."""
    settings = get_settings()
    if not settings.zalo_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZALO_WEBHOOK_URL is not set in environment settings",
        )

    client = ZaloBotClient()
    if not client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZALO_BOT_TOKEN is not set in environment settings",
        )

    result = await client.set_webhook(
        webhook_url=settings.zalo_webhook_url,
        secret_token=settings.zalo_bot_secret_token or None,
    )
    return result
