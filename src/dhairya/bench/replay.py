"""Run every policy over the saved traces. Free and offline.

uv run python -m dhairya.bench.replay
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, fields
from pathlib import Path

from dhairya.bench.metrics import CallScore
from dhairya.bench.record import WINDOW_MS, trace_dir
from dhairya.config import Settings, settings
from dhairya.entities.slots import AmountSlot, DateSlot, MobileSlot, OtpSlot, Slot
from dhairya.turn.entity_aware import EntityAwarePolicy
from dhairya.turn.fixed_timer import FixedTimerPolicy
from dhairya.turn.replay import replay
from dhairya.turn.smart_turn import PROBABILITY_KEY, SmartTurnPolicy
from dhairya.turn.types import FINAL_KINDS, Decision, StreamEvent, TurnPolicy

TIMERS_MS = [300, 500, 700, 1000, 1500, 2000]
SLOTS: dict[str, Slot] = {
    "mobile": MobileSlot(),
    "otp4": OtpSlot(length=4),
    "otp6": OtpSlot(length=6),
    "amount": AmountSlot(),
    "date": DateSlot(),
}
# Long enough for the 2000 ms timer and Dhairya's hold cap to act after the last event.
HORIZON_AFTER_SPEECH_S = 8.0


def policies() -> list[TurnPolicy]:
    timers: list[TurnPolicy] = [FixedTimerPolicy(ms, window_ms=WINDOW_MS) for ms in TIMERS_MS]
    return [*timers, EntityAwarePolicy(window_ms=WINDOW_MS)]


def load_traces(cfg: Settings, window_ms: int = WINDOW_MS, condition: str = "clean") -> list[dict]:
    traces = []
    for path in sorted(trace_dir(cfg, window_ms, condition).glob("*.json")):
        trace = json.loads(path.read_text())
        if "error" not in trace:
            traces.append(trace)
    return traces


def score_call(policy: TurnPolicy, trace: dict) -> CallScore:
    script = trace["script"]
    slot = SLOTS[script["slot"]]
    events = [
        StreamEvent(e["t"], e["kind"], e.get("text", ""), e.get("raw", {})) for e in trace["events"]
    ]
    speech_end = trace["speech_end"]
    out = replay(policy, events, slot, speech_end + HORIZON_AFTER_SPEECH_S)
    ended = out.decision is Decision.END_TURN
    cut_in = ended and out.t < speech_end
    value = slot.evaluate(out.heard).value
    return CallScore(
        script_id=script["id"],
        category=script["category"],
        variant=script["variant"],
        voice=script["voice"],
        policy=policy.name,
        decision=out.decision.value,
        cut_in=cut_in,
        delay_s=round(out.t - speech_end, 3) if ended and not cut_in else None,
        correct=value == script["truth"],
        heard_value=value,
    )


def score_replayed(cfg: Settings) -> list[CallScore]:
    """Every policy, fixed timers included, replayed over the short-window recording."""
    traces = load_traces(cfg)
    return [score_call(policy, trace) for policy in policies() for trace in traces]


def score_all(cfg: Settings) -> tuple[list[CallScore], set[int]]:
    """Scores for the report, plus the timer settings that come from live runs.

    A fixed timer is scored from its own live recording when one covers at least
    95% of the calls; the replay is the fallback. Dhairya always runs over the
    short-window recording, which is the setting it uses in a real call.
    """
    traces = load_traces(cfg)
    scores: list[CallScore] = []
    live: set[int] = set()
    for ms in TIMERS_MS:
        own = score_live_timer(cfg, ms)
        if len(own) >= 0.95 * len(traces):
            scores += own
            live.add(ms)
        else:
            policy = FixedTimerPolicy(ms, window_ms=WINDOW_MS)
            scores += [score_call(policy, trace) for trace in traces]
    with_smart_turn = [t for t in (attach_smart_turn(cfg, trace) for trace in traces) if t]
    if len(with_smart_turn) >= 0.95 * len(traces):
        smart_turn = SmartTurnPolicy(window_ms=WINDOW_MS)
        scores += [score_call(smart_turn, trace) for trace in with_smart_turn]
    dhairya = EntityAwarePolicy(window_ms=WINDOW_MS)
    scores += [score_call(dhairya, trace) for trace in traces]
    return scores, live


def attach_smart_turn(cfg: Settings, trace: dict) -> dict | None:
    """Copy of the trace with Smart Turn's probability on each segment event, if scored."""
    path = cfg.data_dir / "smart_turn" / f"{trace['script']['id']}.json"
    if not path.exists():
        return None
    probabilities = iter(json.loads(path.read_text()))
    events = []
    for event in trace["events"]:
        if event["kind"] in FINAL_KINDS:
            event = event | {"raw": event.get("raw", {}) | {PROBABILITY_KEY: next(probabilities)}}
        events.append(event)
    return trace | {"events": events}


def score_live_timer(cfg: Settings, window_ms: int, condition: str = "clean") -> list[CallScore]:
    """Calls recorded with the server's own window set to window_ms.

    The first finished segment is the end of the turn, exactly as an agent
    using that silence setting would experience it. No replay involved.
    """
    policy = FixedTimerPolicy(window_ms, window_ms=window_ms)
    return [score_call(policy, trace) for trace in load_traces(cfg, window_ms, condition)]


PHONE_TIMERS_MS = [500, 1500]


def score_phone(cfg: Settings) -> list[CallScore]:
    """The phone-line condition: two fixed timers from their own live runs, and Dhairya."""
    traces = load_traces(cfg, WINDOW_MS, "phone8k")
    if not traces:
        return []
    scores: list[CallScore] = []
    for ms in PHONE_TIMERS_MS:
        scores += score_live_timer(cfg, ms, "phone8k")
    dhairya = EntityAwarePolicy(window_ms=WINDOW_MS)
    return scores + [score_call(dhairya, trace) for trace in traces]


def write_csv(scores: list[CallScore], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in fields(CallScore)])
        writer.writeheader()
        writer.writerows(asdict(s) for s in scores)


def main() -> None:
    cfg = settings()
    scores, _ = score_all(cfg)
    write_csv(scores, cfg.results_dir / "scores.csv")
    print(f"{len(scores)} scores written to {cfg.results_dir / 'scores.csv'}")


if __name__ == "__main__":
    main()
