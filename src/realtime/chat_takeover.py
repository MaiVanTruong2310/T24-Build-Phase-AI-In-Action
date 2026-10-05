"""In-process WebSocket fan-out for takeover rooms and the staff queue."""

from __future__ import annotations

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


def user_id_from_payload(payload: dict) -> UUID:
    return UUID(str(payload["sub"]))
