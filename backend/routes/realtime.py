"""
Realtime alert WebSocket and HTTP POST endpoints. Development only.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()
active_connections: list[WebSocket] = []


@router.post("/internal/alert")
async def post_alert(request: Request) -> dict:
    """Accept AlertPayload JSON, broadcast to WebSocket clients."""
    payload = await request.json()
    try:
        msg = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in active_connections:
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.warning("Send to WebSocket failed: %s", e)
                dead.append(ws)
        for ws in dead:
            if ws in active_connections:
                active_connections.remove(ws)
    except Exception as e:
        logger.warning("Broadcast alert failed: %s", e)
    return {"ok": True}


@router.post("/internal/frame")
async def post_frame(request: Request) -> dict:
    """Accept frame JSON, broadcast to WebSocket clients."""
    payload = await request.json()
    try:
        msg = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in active_connections:
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.warning("Send to WebSocket failed: %s", e)
                dead.append(ws)
        for ws in dead:
            if ws in active_connections:
                active_connections.remove(ws)
    except Exception as e:
        logger.warning("Broadcast frame failed: %s", e)
    return {"ok": True}


@router.get("/config/thresholds")
async def get_thresholds() -> dict:
    """Return alert_thresholds.json for UI gauge color bands."""
    path = Path(__file__).resolve().parent.parent / "config" / "alert_thresholds.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


@router.websocket("/ws/realtime-alerts")
async def websocket_realtime(websocket: WebSocket) -> None:
    """WebSocket endpoint for browsers. On connect append; on disconnect remove."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
