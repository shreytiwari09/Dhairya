"""Raw WebSocket client for Prisma realtime speech-to-text.

Gnani's Python SDK does not expose the silence settings, so this talks to the
socket directly. Audio is sent at real-time pace in 1,024-byte frames, as the
docs require; bursting degrades the server's voice detection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Sequence

import numpy as np
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from dhairya.config import STREAM_FRAME_SAMPLES, Settings
from dhairya.gnani.errors import GnaniStreamClosed, error_for
from dhairya.turn.types import StreamEvent

log = logging.getLogger(__name__)
STREAM_PATH = "/stt/v3/stream"


async def run_stream(
    cfg: Settings,
    samples: np.ndarray,
    rate: int,
    *,
    language_code: str = "hi-IN",
    fmt: str = "verbatim",
    min_silence_ms: int = 300,
    tail_silence_s: float = 2.5,
    drain_s: float = 2.0,
    commit_at: Sequence[float] = (),
    partials: bool = False,
    extra_headers: dict[str, str] | None = None,
    model: str | None = None,
) -> list[StreamEvent]:
    """Play audio through the stream and return every server event with its time.

    tail_silence_s of silence is sent after the audio so the last segment closes.
    The stream takes exactly one language (found by the probe; the docs say up to
    four). partials=True sends the undocumented x-partials header: the server then
    emits partial_transcript events while the caller speaks, and the closing event
    is named final_transcript instead of transcript.
    commit_at lists times (seconds into the audio) at which to send a commit frame.
    """
    headers = {
        "x-api-key-id": cfg.api_key,
        "model": model or cfg.stt_model,
        "language_code": language_code,
        "format": fmt,
        "x-sample-rate": str(rate),
        "x-min-silence-ms": str(min_silence_ms),
        **({"x-partials": "true"} if partials else {}),
        **(extra_headers or {}),
    }
    tail = np.zeros(int(tail_silence_s * rate), dtype=np.int16)
    audio = np.concatenate([samples.astype(np.int16), tail])
    pad = (-len(audio)) % STREAM_FRAME_SAMPLES
    if pad:
        audio = np.concatenate([audio, np.zeros(pad, dtype=np.int16)])
    frame_s = STREAM_FRAME_SAMPLES / rate
    events: list[StreamEvent] = []

    try:
        async with connect(cfg.ws_base + STREAM_PATH, additional_headers=headers) as ws:
            t0 = time.monotonic()

            async def receive() -> None:
                try:
                    async for message in ws:
                        if isinstance(message, bytes):
                            continue
                        payload = json.loads(message)
                        events.append(
                            StreamEvent(
                                t=time.monotonic() - t0,
                                kind=str(payload.get("type", "unknown")),
                                text=str(payload.get("text", "")),
                                raw=payload,
                            )
                        )
                except ConnectionClosed:
                    pass

            receiver = asyncio.create_task(receive())
            commits = sorted(commit_at)
            for i in range(len(audio) // STREAM_FRAME_SAMPLES):
                due = t0 + i * frame_s
                wait = due - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                while commits and commits[0] <= i * frame_s:
                    commits.pop(0)
                    await ws.send(json.dumps({"type": "commit"}))
                frame = audio[i * STREAM_FRAME_SAMPLES : (i + 1) * STREAM_FRAME_SAMPLES]
                await ws.send(frame.astype("<i2").tobytes())
            await asyncio.sleep(drain_s)
            await ws.close()
            await receiver
    except InvalidStatus as exc:
        body = exc.response.body.decode("utf-8", "replace") if exc.response.body else ""
        raise error_for(exc.response.status_code, body) from exc
    except ConnectionClosed as exc:
        raise GnaniStreamClosed(str(exc)) from exc
    return events
