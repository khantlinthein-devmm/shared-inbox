from typing import Any, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class WsSession:
    """A single connected agent/admin WebSocket session."""

    __slots__ = ("websocket", "user_id", "role", "user_name")

    def __init__(self, websocket: WebSocket, user_id: int, role: str, user_name: str) -> None:
        self.websocket = websocket
        self.user_id = user_id
        self.role = role
        self.user_name = user_name

    @property
    def is_alive(self) -> bool:
        return self.websocket.client_state == WebSocketState.CONNECTED


class WebSocketManager:
    """Server-to-client broadcaster for live dashboard updates."""

    def __init__(self) -> None:
        self._sessions: list[WsSession] = []

    @property
    def agent_count(self) -> int:
        return len(self._sessions)

    async def connect(self, websocket: WebSocket, user_id: int, role: str, user_name: str) -> None:
        await websocket.accept()
        self._sessions.append(WsSession(websocket, user_id, role, user_name))

    def disconnect(self, websocket: WebSocket) -> None:
        self._sessions = [s for s in self._sessions if s.websocket is not websocket]

    async def send_to_session(self, session: WsSession, data: dict[str, Any]) -> None:
        await session.websocket.send_json(data)

    async def broadcast_to_agents(self, data: dict[str, Any]) -> int:
        """Push a payload to every live agent/admin session. Returns sent count."""
        sent = 0
        for session in list(self._sessions):
            try:
                if session.is_alive:
                    await session.websocket.send_json(data)
                    sent += 1
            except Exception:
                self.disconnect(session.websocket)
        return sent


manager = WebSocketManager()