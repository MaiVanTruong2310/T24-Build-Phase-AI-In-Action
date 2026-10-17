"""Luồng nhắn tin Zalo: chào /start, chống xử lý trùng, tin không phải chữ, đẩy tin điều phối viên & trạng thái lịch."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.zalo import notify
from src.zalo import service as zsvc
from src.zalo.schemas import ZaloWebhookPayload


class FakeClient:
    is_configured = True

    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.actions: list[str] = []

    async def send_message(self, chat_id, text, parse_mode="markdown"):
        self.sent.append((chat_id, text))
        return {"ok": True}

    async def send_chat_action(self, chat_id, action="typing"):
        self.actions.append(action)
        return {"ok": True}


def _payload(text="xin chào", event="message.text.received", message_id=None):
    return ZaloWebhookPayload.model_validate(
        {
            "ok": True,
            "result": {
                "event_name": event,
                "message": {
                    "from": {"id": "u1", "display_name": "Lan", "is_bot": False},
                    "chat": {"id": "chat1", "chat_type": "PRIVATE"},
                    "text": text,
                    "message_id": message_id or uuid4().hex,
                },
            },
        }
    )


@pytest.mark.asyncio
async def test_start_sends_clean_vietnamese_welcome():
    client = FakeClient()
    await zsvc.ZaloBotService(client).handle_webhook_event(_payload("/start"))
    (_, text), *_ = client.sent
    assert "Xin chào **Lan**" in text and "Ã" not in text and "VCare+" in text


@pytest.mark.asyncio
async def test_duplicate_message_id_is_processed_once():
    client = FakeClient()
    svc = zsvc.ZaloBotService(client)
    p = _payload("/start", message_id="dup-1")
    await svc.handle_webhook_event(p)
    second = await svc.handle_webhook_event(p)
    assert len(client.sent) == 1 and second["status"] == "duplicate"


@pytest.mark.asyncio
@pytest.mark.parametrize("event", ["message.image.received", "message.sticker.received", "message.voice.received"])
async def test_media_messages_get_text_only_notice(event):
    client = FakeClient()
    await zsvc.ZaloBotService(client).handle_webhook_event(_payload(event=event))
    assert len(client.sent) == 1 and "tin nhắn chữ" in client.sent[0][1] and "115" in client.sent[0][1]


def test_zalo_session_id_is_stable_and_safe():
    assert zsvc.zalo_session_id("abc123") == "zalo_abc123"
    assert zsvc.zalo_session_id("a b/c") == "zalo_a_b_c"


# ------------------------------------------------------------------ đẩy hoạt động Workbench về Zalo
def _case(status="contacting", session_id="zalo_chat1"):
    return SimpleNamespace(id=uuid4(), session_id=session_id, patient_id=None, booking_id=None, status=status)


@pytest.mark.asyncio
async def test_coordinator_message_is_forwarded_to_zalo():
    deliver = AsyncMock()
    with patch.object(notify, "_deliver", deliver), patch.object(notify.ZaloBotClient, "is_configured", True):
        msg = SimpleNamespace(sender="coordinator", body="Chào chị, em là điều phối viên.")
        notify.schedule_case_notification(_case(), "contacting", msg)
        await asyncio.sleep(0)
    kwargs = deliver.await_args.kwargs
    assert kwargs["coordinator_text"] == "Chào chị, em là điều phối viên." and kwargs["status"] is None


@pytest.mark.asyncio
async def test_status_change_to_confirmed_notifies_once():
    deliver = AsyncMock()
    with patch.object(notify, "_deliver", deliver), patch.object(notify.ZaloBotClient, "is_configured", True):
        notify.schedule_case_notification(_case(status="confirmed"), "deposit_verified")
        notify.schedule_case_notification(_case(status="confirmed"), "confirmed")  # không đổi trạng thái
        notify.schedule_case_notification(_case(status="planned"), "contacting")  # trạng thái nội bộ
        await asyncio.sleep(0)
    assert deliver.await_count == 1 and deliver.await_args.kwargs["status"] == "confirmed"


def test_notification_is_skipped_when_zalo_not_configured():
    with patch.object(notify, "_deliver") as deliver, patch.object(notify.ZaloBotClient, "is_configured", False):
        notify.schedule_case_notification(_case(status="confirmed"), "new")
    deliver.assert_not_called()


def test_notification_errors_never_propagate_to_workbench():
    with patch.object(notify, "_schedule", side_effect=RuntimeError("boom")):
        notify.schedule_case_notification(_case(status="confirmed"), "new")  # không ném lỗi


class _FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDB:
    def __init__(self, chat_id):
        self.chat_id = chat_id

    async def execute(self, _stmt):
        return _FakeResult(self.chat_id)

    async def get(self, *_a, **_k):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_deliver_sends_coordinator_text_and_status_to_mapped_chat():
    client = FakeClient()
    with (
        patch("src.db.session.get_session_factory", return_value=lambda: _FakeDB("chat1")),
        patch.object(notify, "ZaloBotClient", return_value=client),
    ):
        await notify._deliver(
            case_id=uuid4(),
            session_id="zalo_chat1",
            patient_id=None,
            booking_id=None,
            status="cancelled",
            coordinator_text="Lịch bác sĩ đã kín, em hủy giúp chị nhé.",
        )
    texts = [t for _, t in client.sent]
    assert any("Điều phối viên" in t and "đã kín" in t for t in texts)
    assert any("đã được hủy" in t for t in texts)


@pytest.mark.asyncio
async def test_deliver_skips_unknown_chat():
    client = FakeClient()
    with (
        patch("src.db.session.get_session_factory", return_value=lambda: _FakeDB(None)),
        patch.object(notify, "ZaloBotClient", return_value=client),
    ):
        await notify._deliver(
            case_id=uuid4(),
            session_id="zalo_spoofed",
            patient_id=None,
            booking_id=None,
            status="confirmed",
            coordinator_text="x",
        )
    assert client.sent == []


def _session():
    return SimpleNamespace(commit=AsyncMock())


# ------------------------------------------------------------------ lượt hội thoại với agent
@pytest.mark.asyncio
async def test_agent_turn_shows_typing_and_formats_reply():
    client = FakeClient()
    result = {
        "response": "Dạ, triệu chứng đau họng 3 ngày nên khám Tai Mũi Họng ạ.",
        "is_emergency": False,
        "quick_replies": ["Tìm bác sĩ", "Đặt lịch"],
        "suggested_department": "Tai - Mũi - Họng",
    }
    mapping = SimpleNamespace(zalo_display_name="Lan", phone=None, user_id=None)
    with (
        patch.object(zsvc, "prepare_turn", AsyncMock(return_value=({}, None, None))),
        patch.object(zsvc, "run_turn", AsyncMock(return_value=result)) as run,
    ):
        await zsvc.ZaloBotService(client)._handle_agent_chat_turn(_session(), "chat1", "Lan", mapping, None, "đau họng")
    assert client.actions == ["typing"]
    request = run.await_args.args[0]
    assert request.session_id == "zalo_chat1"
    text = client.sent[0][1]
    assert "Tai Mũi Họng" in text and "Chuyên khoa đề xuất" in text and "• Đặt lịch" in text


@pytest.mark.asyncio
async def test_agent_failure_sends_apology_instead_of_silence():
    client = FakeClient()
    mapping = SimpleNamespace(zalo_display_name="Lan", phone=None, user_id=None)
    with patch.object(zsvc, "prepare_turn", AsyncMock(side_effect=RuntimeError("db down"))):
        await zsvc.ZaloBotService(client)._handle_agent_chat_turn(_session(), "chat1", "Lan", mapping, None, "đau họng")
    assert len(client.sent) == 1 and "thử lại" in client.sent[0][1]


def test_emergency_reply_always_has_115():
    text = zsvc.ZaloBotService(FakeClient())._format_agent_response(
        {"response": "Có dấu hiệu đột quỵ.", "is_emergency": True, "ats_level": 2}
    )
    assert "115" in text and "Có dấu hiệu đột quỵ." in text


# ------------------------------------------------------------------ webhook luôn trả 2xx sau khi qua kiểm tra secret
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"content": b""},  # testWebhook của Zalo / ping rỗng
        {"content": b"ping", "headers": {"content-type": "text/plain"}},
        {"json": {"ok": True, "result": {"event_name": "message.text.received", "message": {"text": "x"}}}},
        {"json": {"ok": True, "result": {"event_name": "x", "message": {"from": {"id": 1}, "chat": {"id": 2}}}}},
    ],
)
async def test_webhook_never_returns_4xx_for_odd_payloads(monkeypatch, kwargs):
    from httpx import ASGITransport, AsyncClient

    from src.config import get_settings
    from src.main import app

    monkeypatch.setattr(get_settings(), "zalo_bot_secret_token", "s3cret")
    monkeypatch.setattr(zsvc.ZaloBotService, "handle_webhook_event", AsyncMock(return_value={"ok": True}))
    headers = {"x-bot-api-secret-token": "s3cret", **kwargs.pop("headers", {})}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/zalo/webhook", headers=headers, **kwargs)
        assert resp.status_code == 200
        wrong = await client.post("/api/v1/zalo/webhook", headers={"x-bot-api-secret-token": "sai"}, content=b"")
        assert wrong.status_code == 403  # secret sai vẫn bị chặn


def test_numeric_ids_are_coerced_to_str():
    p = ZaloWebhookPayload.model_validate(
        {"ok": True, "result": {"event_name": "x", "message": {"from": {"id": 1}, "chat": {"id": 2}, "message_id": 3}}}
    )
    assert (
        p.result.message.chat.id == "2" and p.result.message.from_user.id == "1" and p.result.message.message_id == "3"
    )


@pytest.mark.asyncio
async def test_agent_turn_closes_open_transaction_before_prepare_turn():
    """Người đã liên kết tài khoản: begin_turn dùng session.begin() → phải commit transaction tự mở trước đó."""
    order = []
    session = SimpleNamespace(commit=AsyncMock(side_effect=lambda: order.append("commit")))

    async def prepare(*_args):
        order.append("prepare_turn")
        return {}, None, None

    mapping = SimpleNamespace(zalo_display_name="Lan", phone="0912345678", user_id=uuid4())
    user = SimpleNamespace(full_name="Lan", phone="0912345678")
    with (
        patch.object(zsvc, "prepare_turn", prepare),
        patch.object(zsvc, "run_turn", AsyncMock(return_value={"response": "Dạ."})),
    ):
        await zsvc.ZaloBotService(FakeClient())._handle_agent_chat_turn(session, "c1", "Lan", mapping, user, "chào")
    assert order == ["commit", "prepare_turn"]
