"""In-process WebSocket fan-out for durable notification events."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class NotificationConnectionManager:
    """Keep one or more authenticated notification sockets per user."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    async def publish(self, user_id: UUID, payload: dict) -> None:
        for websocket in tuple(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(user_id, websocket)


notification_manager = NotificationConnectionManager()
