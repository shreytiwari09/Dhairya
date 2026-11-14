"""The live demo server: limits, frame rebuffering, the fixed-timer replay and the socket protocol.

No network and no key: the turn itself is replaced by a stand-in.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from dhairya.agent.session import TurnResult
from dhairya.config import LiveSettings, Settings
from dhairya.entities.slots import MobileSlot
from dhairya.turn.types import StreamEvent
from dhairya.web.frames import FrameBuffer
from dhairya.web.limits import DAY_S, HOUR_S, LiveLimits
from dhairya.web.server import create_app
from dhairya.web.shadow import TIMERS_MS, fixed_timer_rows


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def limits(clock: Clock, **kw) -> LiveLimits:
    args = dict(max_concurrent=2, per_ip_hour=3, per_ip_day=5, daily_total=8, clock=clock)
    args.update(kw)
    return LiveLimits(**args)


def test_limits_allow_then_refuse_a_visitor_over_the_hourly_cap() -> None:
    clock = Clock()
    lim = limits(clock, max_concurrent=10)
    for _ in range(3):
        assert lim.try_start("a") is None
        lim.finish()
    assert lim.try_start("a") == "limit_ip"
    assert lim.try_start("b") is None  # another visitor is unaffected


def test_hourly_cap_clears_after_an_hour_but_the_daily_cap_does_not() -> None:
    clock = Clock()
    lim = limits(clock, max_concurrent=10, per_ip_hour=2, per_ip_day=3)
    for _ in range(2):
        assert lim.try_start("a") is None
        lim.finish()
    assert lim.try_start("a") == "limit_ip"
    clock.now += HOUR_S + 1
    assert lim.try_start("a") is None  # the hour has passed; this is the third of the day
    lim.finish()
    clock.now += HOUR_S + 1
    assert lim.try_start("a") == "limit_ip"  # the day cap of three is reached
    clock.now += DAY_S
    assert lim.try_start("a") is None


def test_concurrent_callers_are_capped_and_freed() -> None:
    clock = Clock()
    lim = limits(clock, max_concurrent=2)
    assert lim.try_start("a") is None
    assert lim.try_start("b") is None
    assert lim.try_start("c") == "busy"
    assert lim.status()["busy"] is True
    lim.finish()
    assert lim.try_start("c") is None


def test_daily_total_stops_everyone_and_status_counts_down() -> None:
    clock = Clock()
    lim = limits(clock, max_concurrent=100, per_ip_hour=100, per_ip_day=100, daily_total=3)
    for i in range(3):
        assert lim.try_start(f"ip{i}") is None
        lim.finish()
    assert lim.status()["turns_left_today"] == 0
    assert lim.try_start("new") == "limit_total"


def test_frame_buffer_cuts_exact_frames_across_odd_chunks() -> None:
    buf = FrameBuffer(frame_bytes=8)
    data = bytes(range(20))
    frames = buf.push(data[:5]) + buf.push(data[5:13]) + buf.push(data[13:])
    assert [f.tolist() for f in frames] == [
        np.frombuffer(data[0:8], dtype="<i2").tolist(),
        np.frombuffer(data[8:16], dtype="<i2").tolist(),
    ]
    assert len(buf.push(bytes(4))) == 1  # the 4 left over plus 4 more makes a frame


def ev(t: float, kind: str, text: str = "") -> StreamEvent:
    return StreamEvent(t=t, kind=kind, text=text)


def test_fixed_timer_rows_show_who_cut_in_on_a_pause_in_the_middle() -> None:
    # Five digits, a 0.8 s pause, five more. A timer shorter than the pause ends the turn early.
    events = [
        ev(0.0, "speech_start"),
        ev(1.6, "transcript", "सात शून्य नौ दो छह"),
        ev(2.0, "speech_start"),
        ev(3.8, "transcript", "शून्य शून्य दो छह सात"),
    ]
    rows = {r["ms"]: r for r in fixed_timer_rows(events, MobileSlot(), "7092600267")}
    assert set(rows) == set(TIMERS_MS)
    assert rows[300]["cut_in"] is True and rows[300]["value"] == "70926"
    assert rows[500]["cut_in"] is True
    # speech resumed 0.4 s after the first segment, so a 1 s timer is still waiting when it does
    assert rows[1000]["right"] is True and rows[1000]["value"] == "7092600267"
    assert rows[2000]["right"] is True and rows[2000]["cut_in"] is False


def settings(key: str = "test-key") -> Settings:
    root = Path("/nonexistent")
    return Settings(key, "https://x", "m", "t", root, root)


def live(**kw) -> LiveSettings:
    args = dict(
        enabled=True,
        max_concurrent=2,
        per_ip_hour=5,
        per_ip_day=10,
        daily_total=50,
        allowed_origins=("https://ok.example",),
    )
    args.update(kw)
    return LiveSettings(**args)


async def fake_run(cfg, slot, source, *, aloud, show, speak=None, emit=None):
    await speak("नमस्ते", "prompt")
    await emit({"type": "listening"})
    await emit({"type": "heard", "t": 1.0, "text": "सात", "progress": "incomplete", "value": "7"})
    return TurnResult(
        slot=slot,
        decision="end_turn",
        decided_t=2.0,
        heard="सात",
        streamed_value="7",
        second_pass_value=None,
        final_value="7",
        agreed=False,
        reply="सात। सही है?",
        nudges=0,
        timeline=[{"t": 1.0, "kind": "transcript", "text": "सात"}],
    )


def messages(ws) -> list[dict]:
    out = []
    while True:
        try:
            out.append(json.loads(ws.receive_text()))
        except Exception:
            return out


def test_socket_runs_a_turn_and_ends_with_a_result(monkeypatch) -> None:
    async def no_tts(*_a, **_k):
        raise RuntimeError("no network in tests")

    monkeypatch.setattr(
        "dhairya.web.server.synthesize", lambda *a, **k: (_ for _ in ()).throw(RuntimeError())
    )
    app = create_app(settings(), live(), run=fake_run)
    client = TestClient(app)
    with client.websocket_connect(
        "/ws/live?slot=mobile", headers={"origin": "https://ok.example"}
    ) as ws:
        got = messages(ws)
    kinds = [m["type"] for m in got]
    assert kinds[0] == "ready" and kinds[-1] == "result"
    assert "agent" in kinds and "listening" in kinds and "heard" in kinds
    agent = next(m for m in got if m["type"] == "agent")
    assert agent["audio"] is None  # speech failed: the text still arrives
    assert len(got[-1]["timers"]) == len(TIMERS_MS)


def test_socket_refuses_an_unknown_origin_and_a_missing_one() -> None:
    client = TestClient(create_app(settings(), live(), run=fake_run))
    for headers in ({"origin": "https://evil.example"}, {}):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/live", headers=headers):
                pass


def test_socket_says_why_it_will_not_start() -> None:
    client = TestClient(create_app(settings(), live(per_ip_hour=0), run=fake_run))
    with client.websocket_connect("/ws/live", headers={"origin": "https://ok.example"}) as ws:
        first = json.loads(ws.receive_text())
    assert first["type"] == "error" and first["code"] == "limit"

    client = TestClient(create_app(settings(), live(), run=fake_run))
    with client.websocket_connect(
        "/ws/live?slot=nope", headers={"origin": "https://ok.example"}
    ) as ws:
        assert json.loads(ws.receive_text())["code"] == "bad_slot"

    client = TestClient(create_app(settings(key=""), live(), run=fake_run))
    with client.websocket_connect("/ws/live", headers={"origin": "https://ok.example"}) as ws:
        assert json.loads(ws.receive_text())["code"] == "disabled"


def test_status_reports_availability_and_allows_the_page_origin() -> None:
    client = TestClient(create_app(settings(), live(), run=fake_run))
    resp = client.get("/api/live/status", headers={"origin": "https://ok.example"})
    body = resp.json()
    assert body["enabled"] is True and body["turns_left_today"] == 50
    assert resp.headers["access-control-allow-origin"] == "https://ok.example"
    off = TestClient(create_app(settings(), replace(live(), enabled=False), run=fake_run))
    assert off.get("/api/live/status").json()["enabled"] is False
    assert client.get("/health").json() == {"ok": True}


def test_agent_audio_is_a_short_http_link_not_a_big_socket_message(monkeypatch) -> None:
    samples = np.zeros(16000, dtype=np.int16)
    monkeypatch.setattr("dhairya.web.server.synthesize", lambda *a, **k: (samples, 16000))
    client = TestClient(create_app(settings(), live(), run=fake_run))
    with client.websocket_connect(
        "/ws/live?slot=mobile", headers={"origin": "https://ok.example"}
    ) as ws:
        got = messages(ws)
    agent = next(m for m in got if m["type"] == "agent")
    assert agent["audio"] is None and agent["audio_url"].startswith("/api/live/audio/")
    assert len(json.dumps(agent)) < 1000  # the socket message stays small
    clip = client.get(agent["audio_url"])
    assert clip.status_code == 200 and clip.content[:4] == b"RIFF"
    assert client.get("/api/live/audio/nope.wav").status_code == 404
