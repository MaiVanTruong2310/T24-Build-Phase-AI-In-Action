"""Client adapter for communicating with Zalo Bot Platform API."""

import httpx

from src.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

ZALO_BOT_API_BASE = "https://bot-api.zaloplatforms.com"


def split_message_chunks(text: str, max_chars: int = 1800) -> list[str]:
    """Split long text into readable chunks bounded by newlines or sentence ends."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # Look for natural split point within limit
        split_idx = -1
        # Priority 1: Paragraph break \n\n
        split_idx = remaining.rfind("\n\n", 0, max_chars)
        # Priority 2: Line break \n
        if split_idx == -1:
            split_idx = remaining.rfind("\n", 0, max_chars)
        # Priority 3: Sentence break (period/question/exclamation followed by space)
        if split_idx == -1:
            for sep in [". ", "? ", "! "]:
                idx = remaining.rfind(sep, 0, max_chars)
                if idx > split_idx:
                    split_idx = idx + 1
        # Fallback: whitespace
        if split_idx == -1:
            split_idx = remaining.rfind(" ", 0, max_chars)
        # Hard cut if no whitespace found
        if split_idx == -1:
            split_idx = max_chars

        chunk = remaining[:split_idx].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_idx:].strip()

    return chunks


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
        """Send a text message (auto-split if exceeding length limit) to a user on Zalo."""
        if not self.is_configured:
            logger.warning("Attempted to send Zalo message without token: chat_id=%s", chat_id)
            return {"ok": False, "description": "Zalo bot token not configured"}

        url = f"{self.base_url}/sendMessage"
        chunks = split_message_chunks(text, max_chars=1800)
        last_resp = {"ok": True}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for chunk in chunks:
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": parse_mode,
                    }
                    resp = await client.post(url, json=payload)
                    last_resp = resp.json()
                    if not last_resp.get("ok"):
                        logger.error("Failed to send Zalo message to %s: %s", chat_id, last_resp)
            return last_resp
        except Exception:
            logger.exception("Exception while sending Zalo message to %s", chat_id)
            return {"ok": False, "description": "HTTP request failed"}

