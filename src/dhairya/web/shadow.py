"""The same call replayed through fixed silence timers: what an ordinary agent would have done.

Pure. Uses the stream events of the visitor's own turn; no new calls are made.
"""

from __future__ import annotations

from collections.abc import Sequence

from dhairya.entities.slots import Slot
from dhairya.turn.fixed_timer import FixedTimerPolicy
from dhairya.turn.replay import replay
from dhairya.turn.types import Decision, StreamEvent

TIMERS_MS = (300, 500, 700, 1000, 1500, 2000)


def fixed_timer_rows(
    events: Sequence[StreamEvent],
    slot: Slot,
    final_value: str | None,
    *,
    window_ms: int = 200,
    tail_s: float = 5.0,
) -> list[dict]:
    """One row per timer: when it would end the turn, what it had, and whether that was whole."""
    last = max((e.t for e in events), default=0.0)
    rows = []
    for ms in TIMERS_MS:
        out = replay(FixedTimerPolicy(ms, window_ms=window_ms), events, slot, last + tail_s)
        ended = out.decision is not Decision.WAIT
        value = slot.evaluate(out.heard).value if ended else None
        right = ended and final_value is not None and value == final_value
        rows.append(
            {
                "ms": ms,
                "ended_t": round(out.t, 3) if ended else None,
                "value": value,
                "cut_in": ended and not right,
                "right": right,
            }
        )
    return rows
