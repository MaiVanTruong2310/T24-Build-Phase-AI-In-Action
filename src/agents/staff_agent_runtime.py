"""Per-invocation database context for staff agent tools."""

from __future__ import annotations

from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession

_session: ContextVar[AsyncSession | None] = ContextVar("staff_agent_tool_session", default=None)


def current_session(fallback: AsyncSession) -> AsyncSession:
    return _session.get() or fallback


def set_session(session: AsyncSession):
    return _session.set(session)


def reset_session(token) -> None:
    _session.reset(token)
