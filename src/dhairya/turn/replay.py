"""Run a policy over a recorded list of stream events."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from dhairya.entities.slots import Slot
from dhairya.turn.types import Decision, StreamEvent, TurnPolicy

TICK_S = 0.02


@dataclass(frozen=True)
class Outcome:
    decision: Decision  # WAIT means the policy never decided within the horizon
    t: float  # when it decided, seconds from audio start
    heard: str  # text the policy had when it decided


def replay(
    policy: TurnPolicy,
    events: Sequence[StreamEvent],
    expected: Slot | None,
    horizon_s: float,
) -> Outcome:
    """Feed events in time order with ticks between them; stop at the first decision."""
    policy.reset(expected)
    pending = sorted(events, key=lambda e: e.t)
    i = 0
    t = 0.0
    while t <= horizon_s:
        while i < len(pending) and pending[i].t <= t:
            event = pending[i]
            i += 1
            decision = policy.on_event(event)
            if decision is not Decision.WAIT:
                return Outcome(decision, event.t, policy.heard)
        decision = policy.on_tick(t)
        if decision is not Decision.WAIT:
            return Outcome(decision, t, policy.heard)
        t = round(t + TICK_S, 6)
    return Outcome(Decision.WAIT, horizon_s, policy.heard)
