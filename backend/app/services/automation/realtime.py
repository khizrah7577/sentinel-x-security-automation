"""In-process WebSocket fan-out for real-time dashboard notifications."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, default=str)
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(data)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    def broadcast_sync(self, payload: dict[str, Any]) -> None:
        """Schedule broadcast from sync SQLAlchemy code paths."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(payload))
            else:
                loop.run_until_complete(self.broadcast(payload))
        except RuntimeError:
            # No loop in this thread — drop; clients will poll REST
            logger.debug("No event loop for WS broadcast; payload queued via REST only")


hub = NotificationHub()
