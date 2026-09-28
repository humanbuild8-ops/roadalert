"""Tracks connected dashboards/driver apps and broadcasts incident events.

In production this would sit behind the Alert & Route Engine described in
the architecture slide, fanning out only to the drivers a routing query
matches. For this demo it broadcasts to every connected socket, which is
enough to drive the live dashboard in ``/frontend``.
"""
from typing import List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
