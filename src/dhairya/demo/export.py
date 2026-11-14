"""Export a static JSON file and audio for the replay demo page. Free and offline.

    uv run python -m dhairya.demo.export

Writes demo/data.json and demo/audio/<id>.wav. The calls shown are held-out
ones where a short fixed timer cuts the caller off and Dhairya does not.
"""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from dhairya.bench.metrics import CallScore, Summary, summarise
from dhairya.bench.record import WINDOW_MS
from dhairya.bench.render import DEV_PER_CATEGORY, audio_dir, select
from dhairya.bench.replay import (
    HORIZON_AFTER_SPEECH_S,
    SLOTS,
    TIMERS_MS,
    attach_smart_turn,
    load_traces,
    score_all,
    score_phone,
)
from dhairya.bench.scripts import load, scripts_path
from dhairya.config import ROOT, Settings, settings
from dhairya.entities.slots import Slot
from dhairya.gnani.audio import wav_to_pcm
from dhairya.turn.entity_aware import GRACE_MS, HOLD_CAP_S, LONG_GRACE_MS, EntityAwarePolicy
from dhairya.turn.fixed_timer import FixedTimerPolicy
from dhairya.turn.replay import replay
from dhairya.turn.smart_turn import SmartTurnPolicy
from dhairya.turn.types import FINAL_KINDS, Decision, StreamEvent, TurnPolicy

PEAKS = 240
CATEGORIES = ["mobile", "otp", "amount", "date"]
PER_CATEGORY = 3
MIN_LONG_PAUSE_S = 0.8
STT_MODEL = "prisma-v3.0"
TTS_MODEL = "timbre-v2.5"
POLICY_ORDER = [f"fixed_{ms}ms" for ms in TIMERS_MS] + ["smart_turn", "dhairya"]
LANE_ORDER = ["fixed_500ms", "fixed_1500ms", "smart_turn", "dhairya"]


def demo_dir() -> Path:
    return ROOT / "demo"


def policy_label(name: str) -> str:
    if name == "smart_turn":
        return "Smart Turn v3.2"
    if name == "dhairya":
        return "Dhairya"
    return f"Fixed timer {name.removeprefix('fixed_').removesuffix('ms')} ms"


def waveform_peaks(samples: np.ndarray, n: int = PEAKS) -> list[float]:
    """Max absolute amplitude of n equal chunks, scaled so the loudest is 1.0."""
    if len(samples) == 0:
        return [0.0] * n
    magnitude = np.abs(samples.astype(np.int32))
    chunks = np.array_split(magnitude, n)
    peaks = np.array([chunk.max() if chunk.size else 0 for chunk in chunks], dtype=float)
    top = peaks.max()
    if top <= 0:
        return [0.0] * n
    return [round(float(p), 3) for p in peaks / top]


def to_events(trace: dict) -> list[StreamEvent]:
    return [
        StreamEvent(e["t"], e["kind"], e.get("text", ""), e.get("raw", {})) for e in trace["events"]
    ]


def build_lane(policy: TurnPolicy, label: str, trace: dict, slot: Slot) -> dict:
    """Replay one policy over one trace and describe what it did, step by step."""
    speech_end = trace["speech_end"]
    outcome = replay(policy, to_events(trace), slot, speech_end + HORIZON_AFTER_SPEECH_S)
    ended = outcome.decision is Decision.END_TURN
    cut_in = ended and outcome.t < speech_end
    steps: list[dict] = []
    segments: list[str] = []
    for event in sorted(trace["events"], key=lambda e: e["t"]):
        if event["kind"] not in FINAL_KINDS or event["t"] > outcome.t:
            continue
        text = event.get("text", "")
        segments.append(text)
        heard = " ".join(segments)
        result = slot.evaluate(heard)
        steps.append(
            {
                "t": round(event["t"], 3),
                "text": text,
                "heard": heard,
                "value": result.value,
                "progress": result.progress,
                "state": result.state.value,
            }
        )
    value = slot.evaluate(outcome.heard).value
    return {
        "label": label,
        "steps": steps,
        "decision": outcome.decision.value,
        "decision_t": round(outcome.t, 3),
        "cut_in": cut_in,
        "value": value,
        "correct": value == trace["script"]["truth"],
        "delay_s": round(outcome.t - speech_end, 3) if ended and not cut_in else None,
    }


def live_traces(cfg: Settings) -> dict[int, dict[str, dict]]:
    """Live fixed-timer recordings, by timer setting and then by script id."""
    return {ms: {t["script"]["id"]: t for t in load_traces(cfg, ms)} for ms in (500, 1500)}


def lane_inputs(
    cfg: Settings, trace: dict, live_by_ms: dict[int, dict[str, dict]]
) -> dict[str, tuple[TurnPolicy, dict]] | None:
    """Policy and trace for each lane, or None if a recording or Smart Turn score is missing."""
    script_id = trace["script"]["id"]
    live = {ms: by_id.get(script_id) for ms, by_id in live_by_ms.items()}
    if any(t is None for t in live.values()):
        return None
    with_smart_turn = attach_smart_turn(cfg, trace)
    if with_smart_turn is None:
        return None
    return {
        "fixed_500ms": (FixedTimerPolicy(500, window_ms=500), live[500]),
        "fixed_1500ms": (FixedTimerPolicy(1500, window_ms=1500), live[1500]),
        "smart_turn": (SmartTurnPolicy(window_ms=WINDOW_MS), with_smart_turn),
        "dhairya": (EntityAwarePolicy(window_ms=WINDOW_MS), trace),
    }


def build_lanes(inputs: dict[str, tuple[TurnPolicy, dict]], slot: Slot) -> dict[str, dict]:
    return {
        name: build_lane(inputs[name][0], policy_label(name), inputs[name][1], slot)
        for name in LANE_ORDER
    }


def is_showcase(lanes: dict[str, dict], pauses_s: Sequence[float]) -> bool:
    """A short timer cuts in, Dhairya waits and gets it right, and the call has a real pause."""
    dhairya = lanes["dhairya"]
    return bool(
        lanes["fixed_500ms"]["cut_in"]
        and dhairya["decision"] == Decision.END_TURN.value
        and not dhairya["cut_in"]
        and dhairya["correct"]
        and any(p >= MIN_LONG_PAUSE_S for p in pauses_s)
    )


def row(summary: Summary) -> dict:
    cut_lo, cut_hi = summary.cut_in_ci
    ok_lo, ok_hi = summary.correct_ci
    n = summary.n or 1

    def opt(value: float | None) -> float | None:
        return None if value is None else round(value, 3)

    return {
        "policy": summary.policy,
        "label": policy_label(summary.policy),
        "n": summary.n,
        "cut_ins": summary.cut_ins,
        "cut_in_rate": round(summary.cut_ins / n, 4),
        "cut_in_ci": [round(cut_lo, 4), round(cut_hi, 4)],
        "correct": summary.correct,
        "correct_rate": round(summary.correct / n, 4),
        "correct_ci": [round(ok_lo, 4), round(ok_hi, 4)],
        "delay_p50": opt(summary.delay_p50),
        "delay_p95": opt(summary.delay_p95),
        "nudges": summary.nudges,
    }


def result_rows(scores: Sequence[CallScore]) -> list[dict]:
    """One row per policy present in the scores, in display order."""
    by_policy: dict[str, list[CallScore]] = defaultdict(list)
    for score in scores:
        by_policy[score.policy].append(score)
    ordered = [p for p in POLICY_ORDER if p in by_policy]
    ordered += sorted(set(by_policy) - set(POLICY_ORDER))
    return [row(summarise(p, by_policy[p])) for p in ordered]


def build_results(scores: Sequence[CallScore], dev_ids: set[str]) -> dict:
    held_out = [s for s in scores if s.script_id not in dev_ids]
    development = [s for s in scores if s.script_id in dev_ids]
    return {
        "held_out": {
            "rows": result_rows(held_out),
            "by_category": {
                c: result_rows([s for s in held_out if s.category == c]) for c in CATEGORIES
            },
        },
        "development": {"rows": result_rows(development)},
    }


def pick(candidates: Sequence[dict], per_category: int = PER_CATEGORY) -> list[dict]:
    """Up to per_category per category: two-group calls first, then shortest."""
    chosen: list[dict] = []
    for category in CATEGORIES:
        pool = [c for c in candidates if c["category"] == category]
        pool.sort(key=lambda c: (len(c["groups"]) != 2, c["duration_s"]))
        chosen += pool[:per_category]
    return chosen


def build_call(trace: dict, lanes: dict[str, dict], samples: np.ndarray, rate: int) -> dict:
    script = trace["script"]
    return {
        "id": script["id"],
        "category": script["category"],
        "slot": script["slot"],
        "truth": script["truth"],
        "voice": script["voice"],
        "groups": script["groups"],
        "pauses_s": script["pauses_s"],
        "group_bounds": [[round(a, 3), round(b, 3)] for a, b in trace["group_bounds"]],
        "speech_end": round(trace["speech_end"], 3),
        "duration_s": round(len(samples) / rate, 3),
        "audio": f"audio/{script['id']}.wav",
        "peaks": waveform_peaks(samples, PEAKS),
        "lanes": lanes,
    }


def main() -> None:
    cfg = settings()
    dev_ids = {s.id for s in select(load(scripts_path()), DEV_PER_CATEGORY)}
    traces = load_traces(cfg)
    held_out = [t for t in traces if t["script"]["id"] not in dev_ids]

    live = live_traces(cfg)
    candidates: list[dict] = []
    for trace in held_out:
        script = trace["script"]
        if not any(p >= MIN_LONG_PAUSE_S for p in script["pauses_s"]):
            continue
        wav = audio_dir(cfg) / f"{script['id']}.wav"
        inputs = lane_inputs(cfg, trace, live)
        if inputs is None or not wav.exists():
            continue
        lanes = build_lanes(inputs, SLOTS[script["slot"]])
        if not is_showcase(lanes, script["pauses_s"]):
            continue
        samples, rate = wav_to_pcm(wav.read_bytes())
        candidates.append(build_call(trace, lanes, samples, rate))

    calls = pick(candidates)
    out = demo_dir()
    (out / "audio").mkdir(parents=True, exist_ok=True)
    for call in calls:
        shutil.copyfile(audio_dir(cfg) / f"{call['id']}.wav", out / call["audio"])

    scores, _ = score_all(cfg)
    data = {
        "meta": {
            "stt_model": STT_MODEL,
            "tts_model": TTS_MODEL,
            "window_ms": WINDOW_MS,
            "calls_total": len(traces),
            "held_out": len(held_out),
            "hold_cap_s": HOLD_CAP_S,
            "grace_ms": GRACE_MS,
            "long_grace_ms": LONG_GRACE_MS,
        },
        "calls": calls,
        "results": build_results(scores, dev_ids),
    }
    phone = [x for x in score_phone(cfg) if x.script_id not in dev_ids]
    if phone:
        # Same held-out calls, delivered as an 8 kHz G.711 mu-law phone line would deliver them.
        data["results"]["phone8k"] = {"rows": result_rows(phone)}
    path = out / "data.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    counts = ", ".join(f"{c}: {sum(x['category'] == c for x in calls)}" for c in CATEGORIES)
    print(f"Exported {len(calls)} calls ({counts}) to {path}")


if __name__ == "__main__":
    main()
