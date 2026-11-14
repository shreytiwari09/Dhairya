"""The live demo server: a visitor's microphone to the same live loop the command line runs.

    uv run uvicorn dhairya.web.server:app --port 8000

It holds the Gnani key, so it rate-limits (see LiveLimits) and checks the browser's Origin.
It also serves the demo page, so one address is enough.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import secrets
import time
import wave
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dhairya.agent.session import PROMPTS, RATE, SLOTS, TTS_MODEL, VOICE, run_turn
from dhairya.config import LiveSettings, Settings, live_settings, settings
from dhairya.gnani.errors import GnaniAuthError, GnaniCreditError, GnaniError
from dhairya.gnani.tts import synthesize
from dhairya.turn.types import StreamEvent
from dhairya.web.frames import FrameBuffer
from dhairya.web.limits import LiveLimits
from dhairya.web.shadow import fixed_timer_rows

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("dhairya.web")
DEMO_DIR = Path(__file__).resolve().parents[3] / "demo"
TURN_TIMEOUT_S = 90.0  # a hung turn must not hold a caller slot
# The host's proxy drops WebSocket messages of about 100 KB and more, and a spoken line is larger,
# so audio is fetched over HTTP from a short-lived link and the socket carries only small messages.
AUDIO_TTL_S = 300.0
AUDIO_MAX_ITEMS = 60

MESSAGES = {
    "busy": "Someone else is talking to the live agent. Try again in a minute.",
    "limit_ip": "You have used your live calls for now. Try again in a while.",
    "limit_total": "The live agent has had its share of calls for today. Try again tomorrow.",
    "disabled": "Live mode is paused. The recorded calls above are real recordings.",
    "auth": "The live agent could not sign in to Gnani. The recorded calls above still work.",
    "credits": "The live agent is out of credits for now. The recorded calls above still work.",
    "server": "Something went wrong on the live agent's side. Please try once more.",
    "bad_slot": "That kind of value is not available.",
}


def wav_bytes(samples, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.astype("<i2").tobytes())
    return buf.getvalue()


def client_ip(ws: WebSocket) -> str:
    forwarded = ws.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (ws.client.host if ws.client else "unknown")


def origin_allowed(ws: WebSocket, allowed: tuple[str, ...]) -> bool:
    origin = ws.headers.get("origin", "").rstrip("/")
    if not origin:
        return False
    if origin in allowed:
        return True
    host = ws.headers.get("host", "")  # the page served by this server itself
    return bool(host) and origin.split("://", 1)[-1] == host


def create_app(
    cfg: Settings | None = None, live: LiveSettings | None = None, run=run_turn
) -> FastAPI:
    cfg = cfg or settings()
    live = live or live_settings()
    limits = LiveLimits(
        max_concurrent=live.max_concurrent,
        per_ip_hour=live.per_ip_hour,
        per_ip_day=live.per_ip_day,
        daily_total=live.daily_total,
    )
    app = FastAPI(title="Dhairya live demo", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware, allow_origins=list(live.allowed_origins), allow_methods=["GET"]
    )

    def available() -> bool:
        return live.enabled and bool(cfg.api_key) and not limits.paused

    clips: dict[str, tuple[float, bytes]] = {}

    def keep_clip(wav: bytes) -> str:
        now = time.monotonic()
        for key in [k for k, (born, _) in clips.items() if now - born > AUDIO_TTL_S]:
            del clips[key]
        while len(clips) >= AUDIO_MAX_ITEMS:
            del clips[min(clips, key=lambda k: clips[k][0])]
        key = secrets.token_urlsafe(12)
        clips[key] = (now, wav)
        return key

    @app.get("/api/live/audio/{key}.wav")
    async def audio(key: str) -> Response:
        found = clips.get(key)
        if found is None:
            raise HTTPException(status_code=404)
        return Response(found[1], media_type="audio/wav", headers={"Cache-Control": "no-store"})

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/api/live/status")
    async def status() -> dict:
        return {"enabled": available(), "slots": sorted(SLOTS), **limits.status()}

    @app.websocket("/ws/live")
    async def live_ws(ws: WebSocket, slot: str = "mobile") -> None:
        if not origin_allowed(ws, live.allowed_origins):
            await ws.close(code=1008)
            return
        await ws.accept()
        send_lock = asyncio.Lock()

        async def send(message: dict) -> None:
            async with send_lock:
                await ws.send_text(json.dumps(message, ensure_ascii=False))

        async def fail(code: str, why: str | None = None) -> None:
            await send({"type": "error", "code": code, "message": MESSAGES[why or code]})
            await ws.close()

        if slot not in SLOTS:
            return await fail("bad_slot")
        if not available():
            return await fail("disabled")
        reason = limits.try_start(client_ip(ws))
        if reason:
            return await fail("busy" if reason == "busy" else "limit", reason)
        try:
            await serve_turn(ws, slot, send, fail)
        finally:
            limits.finish()

    async def serve_turn(ws: WebSocket, slot: str, send, fail) -> None:
        accepting = False  # audio is used only while the agent is listening
        frames: asyncio.Queue = asyncio.Queue(maxsize=600)
        buffer = FrameBuffer()

        async def emit(message: dict) -> None:
            nonlocal accepting
            if message["type"] == "listening":
                accepting = True
            await send(message)

        async def speak(text: str, purpose: str) -> None:
            audio_url, seconds = None, 0.0
            try:
                samples, rate = await asyncio.to_thread(
                    synthesize, cfg, text, VOICE, sample_rate=RATE, model=TTS_MODEL
                )
                audio_url = f"/api/live/audio/{keep_clip(wav_bytes(samples, rate))}.wav"
                seconds = len(samples) / rate
            except GnaniCreditError:
                raise
            except Exception as exc:  # a speech failure shows the text instead
                log.warning("could not synthesise (%s); sending the text only", type(exc).__name__)
            await send(
                {
                    "type": "agent",
                    "purpose": purpose,
                    "text": text,
                    "audio": None,
                    "audio_url": audio_url,
                }
            )
            if purpose != "reply":  # the final read-back plays while the result card shows
                await asyncio.sleep(seconds + 0.25)  # the visitor hears it before we listen

        async def source():
            while True:
                yield await frames.get()

        async def reader() -> None:
            try:
                while True:
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    data = message.get("bytes")
                    if data is not None:
                        if accepting:
                            for frame in buffer.push(data):
                                if not frames.full():
                                    frames.put_nowait(frame)
                    elif message.get("text"):
                        try:
                            if json.loads(message["text"]).get("type") == "stop":
                                return
                        except ValueError:
                            pass
            except Exception:
                return

        log.info("turn start: %s", slot)
        await send({"type": "ready", "slot": slot, "prompt": PROMPTS[slot]})
        turn = asyncio.create_task(
            run(cfg, slot, source(), aloud=False, show=lambda _line: None, speak=speak, emit=emit)
        )
        watch = asyncio.create_task(reader())
        try:
            await asyncio.wait(
                {turn, watch}, timeout=TURN_TIMEOUT_S, return_when=asyncio.FIRST_COMPLETED
            )
            if not turn.done():
                log.info(
                    "turn cancelled: %s",
                    "timeout" if not watch.done() else "visitor left or stopped",
                )
                turn.cancel()
                if not watch.done():  # timed out, the visitor is still there
                    return await fail("server")
                return  # the visitor left or pressed stop
            result = turn.result()
        except GnaniAuthError:
            log.error("Gnani rejected the key")
            return await fail("auth")
        except GnaniCreditError:
            limits.paused = True  # stop spending the moment credits run out
            log.error("Gnani reports no credits; live mode paused")
            return await fail("credits")
        except GnaniError as exc:
            log.warning("live turn failed: %s", type(exc).__name__)
            return await fail("server")
        except Exception:
            log.exception("live turn crashed")
            return await fail("server")
        finally:
            watch.cancel()

        log.info("turn finished: %s", result.final_value is not None)
        events = [StreamEvent(t=e["t"], kind=e["kind"], text=e["text"]) for e in result.timeline]
        payload = asdict(result)
        payload["type"] = "result"
        payload["timers"] = fixed_timer_rows(events, SLOTS[slot], result.final_value)
        await send(payload)
        await ws.close()

    if DEMO_DIR.exists():
        app.mount("/", StaticFiles(directory=DEMO_DIR, html=True), name="demo")
    return app


app = create_app()


def main() -> None:
    import os

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
