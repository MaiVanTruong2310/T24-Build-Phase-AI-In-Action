"""Tests for Zalo Bot schemas, webhook endpoint, and service."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_zalo_bot_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/zalo/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "is_configured" in data
        assert "mode" in data


@pytest.mark.asyncio
async def test_zalo_webhook_receives_text_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "ok": True,
            "result": {
                "event_name": "message.text.received",
                "message": {
                    "from": {
                        "id": "user_zalo_123",
                        "display_name": "Nguyen Van A",
                        "is_bot": False,
                    },
                    "chat": {
                        "id": "chat_zalo_123",
                        "chat_type": "PRIVATE",
                    },
                    "text": "/start",
                    "message_id": "msg_001",
                    "date": 1750000000,
                },
            },
        }
        from src.config import get_settings

        settings = get_settings()
        headers = {}
        if settings.zalo_bot_secret_token:
            headers["x-bot-api-secret-token"] = settings.zalo_bot_secret_token

        resp = await client.post("/api/v1/zalo/webhook", json=payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json().get("ok") is True


@pytest.mark.asyncio
async def test_zalo_webhook_secret_token_rejection(monkeypatch):
    from src.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "zalo_bot_secret_token", "super_secret_token_123")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"ok": True, "result": {"event_name": "message.text.received"}}

        # Without or invalid header -> 403
        resp = await client.post(
            "/api/v1/zalo/webhook",
            json=payload,
            headers={"x-bot-api-secret-token": "wrong_token"},
        )
        assert resp.status_code == 403

        # With correct header -> 200
        resp_valid = await client.post(
            "/api/v1/zalo/webhook",
            json=payload,
            headers={"x-bot-api-secret-token": "super_secret_token_123"},
        )
        assert resp_valid.status_code == 200
