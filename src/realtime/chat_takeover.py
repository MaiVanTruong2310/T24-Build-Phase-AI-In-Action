"""In-process WebSocket fan-out for takeover rooms and the staff queue."""

from __future__ import annotations

import secrets
import time
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ChatTakeoverConnectionManager:
    """Keep authenticated sockets grouped by chat session or staff queue."""

    def __init__(self) -> None:
        self._session_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._staff_connections: set[WebSocket] = set()

    async def connect_session(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._session_connections[session_id].add(websocket)

    async def connect_staff(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._staff_connections.add(websocket)

    def disconnect_session(self, session_id: str, websocket: WebSocket) -> None:
        connections = self._session_connections.get(session_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._session_connections.pop(session_id, None)

    def disconnect_staff(self, websocket: WebSocket) -> None:
        self._staff_connections.discard(websocket)

    async def publish_session(self, session_id: str, payload: dict) -> None:
        await self._publish(tuple(self._session_connections.get(session_id, ())), payload, session_id=session_id)

    async def publish_staff(self, payload: dict) -> None:
        await self._publish(tuple(self._staff_connections), payload)

    async def _publish(
        self, connections: tuple[WebSocket, ...], payload: dict, *, session_id: str | None = None
    ) -> None:
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                if session_id is not None:
                    self.disconnect_session(session_id, websocket)
                else:
                    self.disconnect_staff(websocket)


chat_takeover_manager = ChatTakeoverConnectionManager()


class TakeoverTicketStore:
    """Short-lived opaque tickets for the WebSocket handshake.

    A browser cannot set an Authorization header on a WebSocket handshake, so the
    authenticated HTTP endpoint issues a ticket that the socket passes back as
    ``?token=``. The ticket is opaque and stored server-side: a locally signed JWT
    would be forgeable by anyone holding the shared signing secret, which is the
    trust this store removes. Tickets are reusable within their TTL so a client can
    reconnect, and they are useless as an HTTP bearer token.

    State is per process, matching the in-process connection manager above.
    """

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._tickets: dict[str, tuple[UUID, float]] = {}

    def issue(self, user_id: UUID) -> str:
        """Mint a ticket bound to one user and drop the expired ones."""
        self._purge()
        token = secrets.token_urlsafe(32)
        self._tickets[token] = (user_id, time.monotonic() + self._ttl_seconds)
        return token

    def redeem(self, token: str) -> UUID | None:
        """Return the bound user id, or None when the ticket is unknown or expired."""
        entry = self._tickets.get(token)
        if entry is None:
            return None
        user_id, expires_at = entry
        if expires_at <= time.monotonic():
            self._tickets.pop(token, None)
            return None
        return user_id

    def _purge(self) -> None:
        now = time.monotonic()
        for token in [token for token, (_, expires_at) in self._tickets.items() if expires_at <= now]:
            self._tickets.pop(token, None)


takeover_tickets = TakeoverTicketStore()
