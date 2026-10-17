"""WebSocket bệnh nhân /staff/chat-takeover/ws/{session}: chỉ chủ phiên nghe được tin nhắn điều phối."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from src.api.endpoints import chat_takeover

GUEST = "a" * 64


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.statements = []
        self.commit = AsyncMock()

    async def scalar(self, statement):
        self.statements.append(statement)
        return self.result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


def _install(monkeypatch, result):
    session = FakeSession(result)
    monkeypatch.setattr(chat_takeover, "get_session_factory", lambda: lambda: session)
    return session


def _sql(session):
    return str(session.statements[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
@pytest.mark.parametrize(("foreign_case", "allowed"), [(None, True), (uuid4(), False)])
async def test_owns_session(monkeypatch, foreign_case, allowed):
    session = _install(monkeypatch, foreign_case)
    user = SimpleNamespace(id=uuid4())

    assert await chat_takeover.owns_session("web-abc", user) is allowed
    assert f"user:{user.id}" in _sql(session)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_case_created_as_guest_counts_as_own(monkeypatch):
    """Chat khách rồi đăng nhập giữa chừng: ca khách (cùng cookie) vẫn là của người này → không chặn realtime."""
    session = _install(monkeypatch, None)

    await chat_takeover.owns_session("web-abc", SimpleNamespace(id=uuid4()), GUEST)

    assert "guest:" + hashlib.sha256(GUEST.encode()).hexdigest() in _sql(session)


@pytest.mark.asyncio
async def test_malformed_guest_cookie_is_ignored(monkeypatch):
    session = _install(monkeypatch, None)

    await chat_takeover.owns_session("web-abc", SimpleNamespace(id=uuid4()), "not-a-token")

    assert "guest:" not in _sql(session)


class FakeSocket:
    def __init__(self, cookies=None):
        self.closed_with = None
        self.cookies = cookies or {}

    async def close(self, code):
        self.closed_with = code


@pytest.mark.asyncio
async def test_patient_socket_rejects_other_users_session(monkeypatch):
    monkeypatch.setattr(chat_takeover, "authenticate_socket", AsyncMock(return_value=SimpleNamespace(id=uuid4())))
    owns = AsyncMock(return_value=False)
    monkeypatch.setattr(chat_takeover, "owns_session", owns)
    connect = AsyncMock()
    monkeypatch.setattr(chat_takeover.chat_takeover_manager, "connect_session", connect)
    socket = FakeSocket({chat_takeover.GUEST_COOKIE: GUEST})

    await chat_takeover.patient_socket("web-someone-else", socket)

    assert socket.closed_with == 1008
    connect.assert_not_awaited()
    assert owns.await_args.args[2] == GUEST  # cookie khách được chuyển vào kiểm tra chủ phiên
