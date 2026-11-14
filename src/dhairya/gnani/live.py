"""An open Prisma realtime stream that audio is fed into frame by frame.

run_stream in stream.py plays a finished recording; this is for a live turn,
where the audio does not exist yet and the turn ends when a policy says so.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from dhairya.config import Settings
from dhairya.gnani.errors import error_for
from dhairya.gnani.stream import STREAM_PATH
from dhairya.turn.types import StreamEvent


class LiveStream:
    def __init__(self, ws: ClientConnection) -> None:
        self._ws = ws
        self._t0: float | None = None

    def now(self) -> float:
        """Seconds since the first audio frame was sent; 0 before that."""
        return 0.0 if self._t0 is None else time.monotonic() - self._t0

    async def send(self, frame: bytes) -> None:
        if self._t0 is None:
            self._t0 = time.monotonic()
        await self._ws.send(frame)

    async def commit(self) -> None:
        await self._ws.send(json.dumps({"type": "commit"}))

    async def events(self) -> AsyncIterator[StreamEvent]:
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    continue
                payload = json.loads(message)
                yield StreamEvent(
                    t=self.now(),
                    kind=str(payload.get("type", "unknown")),
                    text=str(payload.get("text", "")),
                    raw=payload,
                )
        except ConnectionClosed:
            return


@asynccontextmanager
async def open_stream(
    cfg: Settings,
    rate: int,
    *,
    language_code: str = "hi-IN",
    fmt: str = "verbatim",
    min_silence_ms: int = 200,
) -> AsyncIterator[LiveStream]:
    headers = {
        "x-api-key-id": cfg.api_key,
        "model": cfg.stt_model,
        "language_code": language_code,
        "format": fmt,
        "x-sample-rate": str(rate),
        "x-min-silence-ms": str(min_silence_ms),
    }
    try:
        async with connect(cfg.ws_base + STREAM_PATH, additional_headers=headers) as ws:
            yield LiveStream(ws)
    except InvalidStatus as exc:
        body = exc.response.body.decode("utf-8", "replace") if exc.response.body else ""
        raise error_for(exc.response.status_code, body) from exc
