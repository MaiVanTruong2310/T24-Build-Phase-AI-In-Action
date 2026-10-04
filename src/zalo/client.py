"""Client adapter for communicating with Zalo Bot Platform API."""

import httpx

from src.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

ZALO_BOT_API_BASE = "https://bot-api.zaloplatforms.com"


class ZaloBotClient:
    """HTTP client for Zalo Bot API endpoints."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or get_settings().zalo_bot_token
        self.base_url = f"{ZALO_BOT_API_BASE}/bot{self.token}"

    @property
    def is_configured(self) -> bool:
        """Check if bot token is provided."""
        return bool(self.token and self.token.strip())

    async def get_me(self) -> dict:
        """Get information about the current bot."""
        if not self.is_configured:
            return {"ok": False, "description": "Zalo bot token not configured"}
        url = f"{self.base_url}/getMe"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            return resp.json()

    async def set_webhook(self, webhook_url: str, secret_token: str | None = None) -> dict:
        """Register a Webhook URL with Zalo Bot Platform."""
        if not self.is_configured:
            return {"ok": False, "description": "Zalo bot token not configured"}
        url = f"{self.base_url}/setWebhook"
        payload = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            logger.info("Zalo setWebhook status=%s body=%s", resp.status_code, resp.text)
            return resp.json()

    async def delete_webhook(self) -> dict:
        """Remove currently configured Webhook."""
        if not self.is_configured:
            return {"ok": False, "description": "Zalo bot token not configured"}
        url = f"{self.base_url}/deleteWebhook"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url)
            return resp.json()

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "markdown",
    ) -> dict:
        """Send a text message to a user or group on Zalo."""
        if not self.is_configured:
            logger.warning("Attempted to send Zalo message without token: chat_id=%s", chat_id)
            return {"ok": False, "description": "Zalo bot token not configured"}

        url = f"{self.base_url}/sendMessage"
        # Truncate text if exceeds Zalo 2000 character limit
        safe_text = text[:1990] if len(text) > 2000 else text
        payload = {
            "chat_id": chat_id,
            "text": safe_text,
            "parse_mode": parse_mode,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if not data.get("ok"):
                    logger.error("Failed to send Zalo message to %s: %s", chat_id, data)
                return data
        except Exception:
            logger.exception("Exception while sending Zalo message to %s", chat_id)
            return {"ok": False, "description": "HTTP request failed"}
