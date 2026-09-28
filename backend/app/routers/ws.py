from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..store import store
from ..ws_manager import manager

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/incidents")
async def incidents_feed(ws: WebSocket):
    """Live incident feed used by the dashboard and driver apps.

    On connect, the socket gets a snapshot of everything currently
    active, then receives ``incident.reported`` / ``incident.confirmed``
    / ``incident.cleared`` events as they happen.
    """
    await manager.connect(ws)
    try:
        snapshot = [i.model_dump(mode="json") for i in store.list()]
        await ws.send_json({"event": "snapshot", "incidents": snapshot})
        while True:
            # The dashboard doesn't need to send anything; we just keep
            # the connection open and let broadcasts flow one-way. A
            # driver app could send periodic location pings here instead.
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
