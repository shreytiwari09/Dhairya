"""One live turn: ask for a value, listen, wait properly, double-check, read back.

    uv run python -m dhairya.agent.session --slot mobile                 # speak into the microphone
    uv run python -m dhairya.agent.session --slot mobile --file call.wav # a recording as the caller

The file mode feeds a recording at real-time pace through the same live loop,
which is how the loop is tested without a person at the microphone.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from dhairya.config import STREAM_FRAME_SAMPLES, Settings, settings
from dhairya.entities.slots import AmountSlot, DateSlot, MobileSlot, OtpSlot, Slot, SlotState
from dhairya.entities.speak import spoken_value
from dhairya.gnani.audio import wav_to_pcm
from dhairya.gnani.errors import GnaniError
from dhairya.gnani.live import open_stream
from dhairya.gnani.stt_rest import transcribe
from dhairya.gnani.tts import synthesize
from dhairya.turn.entity_aware import EntityAwarePolicy
from dhairya.turn.fixed_timer import FixedTimerPolicy
from dhairya.turn.types import Decision, StreamEvent, TurnPolicy

log = logging.getLogger(__name__)
RATE = 16000
WINDOW_MS = 200  # best stream setting found by the probe
VOICE, TTS_MODEL = "Nalini", "timbre-v2.5"
MAX_NUDGES = 2
MAX_TURN_S = 40.0
REST_LIMIT_S = 30  # Prisma REST takes at most 30 s of audio

SLOTS: dict[str, Slot] = {
    "mobile": MobileSlot(),
    "otp4": OtpSlot(length=4),
    "otp6": OtpSlot(length=6),
    "amount": AmountSlot(),
    "date": DateSlot(),
}
PROMPTS = {
    "mobile": "अपना मोबाइल नंबर बताइए।",
    "otp4": "चार अंकों का ओटीपी बताइए।",
    "otp6": "छह अंकों का ओटीपी बताइए।",
    "amount": "कितनी राशि भेजनी है?",
    "date": "किस तारीख को?",
}
NUDGE = "जी, आगे बोलिए।"

Frames = AsyncIterator[np.ndarray]
Say = Callable[[str], "asyncio.Future[None] | asyncio.Task[None] | object"]
Speak = Callable[[str, str], Awaitable[None]]  # (text, purpose) -> plays or sends the line
Emit = Callable[[dict], Awaitable[None]]  # structured events for a UI


@dataclass
class TurnResult:
    slot: str
    decision: str
    decided_t: float
    heard: str
    streamed_value: str | None
    second_pass_value: str | None
    final_value: str | None
    agreed: bool  # the stream and the second pass gave the same value
    reply: str
    nudges: int
    notes: list[str] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    extra_digits: int = 0  # digits heard beyond what the slot needed, left out of the value


async def frames_from_file(path: Path) -> Frames:
    """A recording as the caller: real-time pace, then silence, as a caller who has finished."""
    samples, rate = wav_to_pcm(path.read_bytes())
    if rate != RATE:
        raise ValueError(f"{path.name} is {rate} Hz; the live loop expects {RATE} Hz")
    started = time.monotonic()
    i = 0
    while True:
        chunk = samples[i * STREAM_FRAME_SAMPLES : (i + 1) * STREAM_FRAME_SAMPLES]
        frame = np.zeros(STREAM_FRAME_SAMPLES, dtype=np.int16)
        frame[: len(chunk)] = chunk
        wait = started + i * STREAM_FRAME_SAMPLES / RATE - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        yield frame
        i += 1


async def frames_from_mic() -> Frames:
    import sounddevice as sd  # imported here so tests and file mode need no audio device

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

    def on_audio(indata, _frames, _time, status) -> None:
        if status:
            log.warning("microphone: %s", status)
        loop.call_soon_threadsafe(queue.put_nowait, indata[:, 0].copy())

    with sd.InputStream(
        samplerate=RATE,
        channels=1,
        dtype="int16",
        blocksize=STREAM_FRAME_SAMPLES,
        callback=on_audio,
    ):
        while True:
            yield await queue.get()


async def speak_aloud(cfg: Settings, text: str) -> None:
    """Timbre says the text through the speakers. Falls back to printing it."""
    try:
        import sounddevice as sd

        samples, rate = await asyncio.to_thread(
            synthesize, cfg, text, VOICE, sample_rate=RATE, model=TTS_MODEL
        )
        await asyncio.to_thread(lambda: (sd.play(samples, rate), sd.wait()))
    except Exception as exc:  # TTS or audio-device failure must not end the call
        log.warning("could not speak (%s); showing the text instead", exc)
        print(f"  agent (text only): {text}")


async def listen(
    cfg: Settings,
    source: Frames,
    slot: Slot,
    policy: TurnPolicy,
    nudge: Callable[[], asyncio.Future[None] | object],
    show: Callable[[str], None],
    emit: Emit | None = None,
) -> tuple[Decision, float, np.ndarray, list[StreamEvent], int, list[str]]:
    """Stream the caller's audio until the policy ends the turn."""
    heard_audio: list[np.ndarray] = []
    events: list[StreamEvent] = []
    notes: list[str] = []
    outcome: dict = {}
    done = asyncio.Event()
    muted = False
    nudges = 0
    active = policy
    active.reset(slot)

    def finish(decision: Decision, t: float) -> None:
        if not done.is_set():
            outcome.update(decision=decision, t=t)
            done.set()

    def decide(call: Callable[[TurnPolicy], Decision]) -> Decision:
        nonlocal active
        try:
            return call(active)
        except Exception as exc:  # a policy bug must not hang the call: fall back to a timer
            notes.append(f"policy failed ({exc}); fell back to a 1000 ms timer")
            fallback = FixedTimerPolicy(1000, window_ms=WINDOW_MS)
            fallback.reset(slot)
            for past in events:
                fallback.on_event(past)
            active = fallback
            return Decision.WAIT

    async def tell(message: dict) -> None:
        if emit is not None:
            await emit(message)

    async with open_stream(cfg, RATE, min_silence_ms=WINDOW_MS) as stream:
        await tell({"type": "listening"})

        async def pump() -> None:
            async for frame in source:
                if done.is_set():
                    return
                if muted:  # the agent is talking: keep the stream fed, but not with its own voice
                    frame = np.zeros_like(frame)
                heard_audio.append(frame)
                await stream.send(frame.astype("<i2").tobytes())

        async def hear() -> None:
            async for event in stream.events():
                events.append(event)
                if event.kind == "error":
                    notes.append(f"stream error: {event.raw.get('message', event.raw)}")
                decision = decide(lambda p, e=event: p.on_event(e))
                if event.kind == "speech_start":
                    await tell({"type": "speech_start", "t": round(event.t, 3)})
                if event.text:
                    state = slot.evaluate(active.heard)
                    show(f"  {event.t:5.2f}s heard “{event.text}” → {state.progress}")
                    await tell(
                        {
                            "type": "heard",
                            "t": round(event.t, 3),
                            "text": event.text,
                            "progress": state.progress,
                            "value": state.value,
                        }
                    )
                if decision is not Decision.WAIT:
                    finish(decision, event.t)
                    return

        async def clock() -> None:
            nonlocal muted, nudges
            while not done.is_set():
                await asyncio.sleep(0.02)
                t = stream.now()
                if t > MAX_TURN_S:
                    notes.append("turn hit the time limit")
                    finish(Decision.NUDGE, t)
                    return
                decision = decide(lambda p, now=t: p.on_tick(now))
                if decision is Decision.NUDGE and nudges < MAX_NUDGES:
                    nudges += 1
                    show(f"  {t:5.2f}s nothing new: asking the caller to go on")
                    muted = True
                    await tell({"type": "nudge", "t": round(t, 3)})
                    await nudge()
                    muted = False
                    if hasattr(active, "rearm"):
                        active.rearm(stream.now())
                elif decision is not Decision.WAIT:
                    finish(decision, t)
                    return

        tasks = [asyncio.create_task(job()) for job in (pump, hear, clock)]
        await done.wait()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    audio = np.concatenate(heard_audio) if heard_audio else np.zeros(0, dtype=np.int16)
    notes.append(f"policy: {active.name}")
    return outcome["decision"], outcome["t"], audio, events, nudges, notes


async def run_turn(
    cfg: Settings,
    slot_name: str,
    source: Frames,
    *,
    aloud: bool,
    show: Callable[[str], None],
    speak: Speak | None = None,
    emit: Emit | None = None,
) -> TurnResult:
    slot = SLOTS[slot_name]
    policy = EntityAwarePolicy(window_ms=WINDOW_MS)

    async def say(text: str, purpose: str = "prompt") -> None:
        show(f"  agent: {text}")
        if speak is not None:  # a web session plays the line in the visitor's browser
            await speak(text, purpose)
        elif aloud:
            await speak_aloud(cfg, text)

    await say(PROMPTS[slot_name], "prompt")
    decision, t, audio, events, nudges, notes = await listen(
        cfg, source, slot, policy, lambda: say(NUDGE, "nudge"), show, emit
    )
    heard = " ".join(e.text for e in events if e.text)
    streamed = slot.evaluate(heard)
    if emit is not None:
        await emit(
            {
                "type": "decided",
                "t": round(t, 3),
                "decision": decision.value,
                "value": streamed.value,
            }
        )
    show(f"  {t:5.2f}s turn closed ({decision.value}); streamed value {streamed.value}")

    # Second pass: the whole turn through REST in Transcribe mode, read by the same slot.
    log.info("second pass: %.1f s of audio", len(audio) / RATE)
    second_value = None
    second_extra = 0
    try:
        clip = audio[-REST_LIMIT_S * RATE :]
        response = await asyncio.to_thread(
            transcribe, cfg, clip, RATE, language_code="hi-IN", fmt="transcribe"
        )
        second = slot.evaluate(str(response.get("transcript", "")))
        if second.state is not SlotState.INCOMPLETE:
            second_value = second.value
            second_extra = second.extra
        show(f"         second pass heard “{response.get('transcript', '')}” → {second.value}")
    except GnaniError as exc:
        notes.append(f"second pass failed ({exc}); using the streamed value")

    agreed = second_value is not None and second_value == streamed.value
    final = second_value if second_value is not None else streamed.value
    extra = second_extra if second_value is not None else streamed.extra
    if final is not None and extra > 0:
        notes.append(f"{extra} extra digit(s) heard and not used")
    if final is None:
        reply = "माफ़ कीजिए, मुझे सुनाई नहीं दिया। कृपया दोबारा बताइए।"
    elif second_value is None and streamed.state is SlotState.INCOMPLETE:
        # Never read back half a value as if it were whole.
        reply = f"मुझे सिर्फ़ {spoken_value(slot_name, final)} सुनाई दिया। कृपया पूरा दोबारा बताइए।"
    elif extra > 0:
        reply = (
            f"मुझे {extra} अंक ज़्यादा सुनाई दिए। "
            f"मैंने {spoken_value(slot_name, final)} लिया है। क्या यह सही है?"
        )
    elif agreed:
        reply = f"{spoken_value(slot_name, final)}। सही है?"
    else:
        reply = f"मैंने सुना {spoken_value(slot_name, final)}। क्या यह सही है?"
    log.info("reading back")
    await say(reply, "reply")

    return TurnResult(
        slot=slot_name,
        decision=decision.value,
        decided_t=round(t, 3),
        heard=heard,
        streamed_value=streamed.value,
        second_pass_value=second_value,
        final_value=final,
        agreed=agreed,
        reply=reply,
        nudges=nudges,
        notes=notes,
        timeline=[{"t": round(e.t, 3), "kind": e.kind, "text": e.text} for e in events],
        extra_digits=extra if final is not None else 0,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--slot", choices=sorted(SLOTS), default="mobile")
    parser.add_argument("--file", type=Path, help="a 16 kHz mono WAV to use as the caller")
    parser.add_argument(
        "--silent", action="store_true", help="print the agent's lines; do not speak"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    cfg = settings()
    if not cfg.api_key:
        print("GNANI_API_KEY is empty. Add your key to the .env file, then run again.")
        raise SystemExit(2)
    source = frames_from_file(args.file) if args.file else frames_from_mic()
    aloud = not args.silent and args.file is None
    print(f"Dhairya live turn: {args.slot}" + (f" (caller: {args.file.name})" if args.file else ""))
    result = asyncio.run(run_turn(cfg, args.slot, source, aloud=aloud, show=print))

    out = cfg.data_dir / "live"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"turn-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=1))
    print(
        f"Saved {result.final_value!r}; stream and second pass agreed: {result.agreed}. Log: {path}"
    )
    for note in result.notes:
        print(f"  note: {note}")


if __name__ == "__main__":
    main()
