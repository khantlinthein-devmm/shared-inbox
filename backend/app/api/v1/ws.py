import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/api/v1/ws")
async def agent_socket(websocket: WebSocket, token: str = "") -> None:
    """Live WebSocket for agents/admins.

    Auth is performed via `?token=<jwt>` query parameter (the browser WebSocket
    API cannot set Authorization headers). Reject the connection on failure.
    """
    payload = decode_token(token) if token else None
    if payload is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    user_id = int(payload["sub"])
    role = payload.get("role", "")
    user_name = payload.get("name", "")

    await manager.connect(websocket, user_id, role, user_name)
    logger.info("WS connected: user_id=%s role=%s", user_id, role)
    try:
        while True:
            data = await websocket.receive_text()
            if data == '{"type":"ping"}':
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        logger.info("WS disconnected: user_id=%s", user_id)