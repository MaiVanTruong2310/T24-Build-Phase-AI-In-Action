"""Pydantic schemas for Zalo Bot API & Webhook events."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ZaloUser(BaseModel):
    id: str
    display_name: str | None = None
    is_bot: bool = False


class ZaloChat(BaseModel):
    id: str
    chat_type: Literal["PRIVATE", "GROUP"] | str = "PRIVATE"


class ZaloMessage(BaseModel):
    from_user: ZaloUser = Field(alias="from")
    chat: ZaloChat
    message_id: str | None = None
    date: int | None = None
    text: str | None = None
    photo: str | None = None
    caption: str | None = None
    sticker: str | None = None
    voice_url: str | None = None

    model_config = {"populate_by_name": True}


class ZaloWebhookResult(BaseModel):
    event_name: str
    message: ZaloMessage | None = None


class ZaloWebhookPayload(BaseModel):
    ok: bool = True
    result: ZaloWebhookResult | None = None


class ZaloSendMessageRequest(BaseModel):
    chat_id: str
    text: str
    parse_mode: Literal["markdown", "html"] | None = "markdown"
    text_styles: list[dict[str, Any]] | None = None
