import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.websocket import disconnect
from app.ws.manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = Query(..., description="Primary channel, e.g. event:1:feed"),
):
    """
    WebSocket endpoint with Redis-backed pub/sub fan-out.

    Client messages:
    - `{"type":"ping","timestamp":123}` → pong
    - `{"type":"subscribe","channels":["event:1:wall"]}`
    - `{"type":"unsubscribe","channels":["event:1:wall"]}`

    Server sends periodic `ping`; client should reply with `pong` or `ping`.
    """
    connection_id = uuid.uuid4().hex
    await ws_manager.register(websocket, channel, connection_id)
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_client_message(connection_id, raw)
    except WebSocketDisconnect:
        disconnect(connection_id)
    except Exception:
        disconnect(connection_id)
        raise
