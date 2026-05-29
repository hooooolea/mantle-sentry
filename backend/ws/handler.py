"""WebSocket handler — real-time push to connected clients."""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Connected clients
_clients: set[WebSocket] = set()


async def broadcast(message: dict):
    """Send message to all connected WebSocket clients."""
    dead = set()
    data = json.dumps(message, ensure_ascii=False)
    for ws in _clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        while True:
            # Keep alive — client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        _clients.discard(ws)
