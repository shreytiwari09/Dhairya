"""Dhairya's policy: the turn ends when the value is finished, not when the caller is quiet."""

from __future__ import annotations

from dhairya.entities.slots import Slot, SlotResult, SlotState
from dhairya.turn.types import FINAL_KINDS, Decision, StreamEvent

# Frozen policy settings (tuned on the 45-call pilot, then held fixed). The demo page reads
# these through demo/data.json so its rule text cannot drift from the code.
HOLD_CAP_S = 4.0
GRACE_MS = 600
LONG_GRACE_MS = 1500


class EntityAwarePolicy:
    """Waits while a dictated value is incomplete; answers at once when it is complete.

    - COMPLETE: end the turn now.
    - INCOMPLETE: wait. After hold_cap_s with no new speech, nudge the caller.
    - OPEN (valid but may continue): wait grace_ms, then end. If the form heard
      usually continues ("nau hazaar", with no unit word), wait long_grace_ms.
      Both graces are silence timers; the gain is that they apply only to
      open-ended values, and that a unit word ("rupaye") ends the turn at once.
    - No slot expected: behave as a fixed timer of fallback_ms.
    Speech resuming cancels any pending end.
    """

    name = "dhairya"

    def __init__(
        self,
        hold_cap_s: float = HOLD_CAP_S,
        grace_ms: int = GRACE_MS,
        long_grace_ms: int = LONG_GRACE_MS,
        fallback_ms: int = 700,
        window_ms: int = 200,
    ) -> None:
        self._hold_cap_s = hold_cap_s
        self._grace_s = max(0, grace_ms - window_ms) / 1000
        self._long_grace_s = max(0, long_grace_ms - window_ms) / 1000
        self._fallback_s = max(0, fallback_ms - window_ms) / 1000
        self.reset(None)

    def reset(self, expected: Slot | None) -> None:
        self._slot = expected
        self._segments: list[str] = []
        self._end_at: float | None = None
        self._nudge_at: float | None = None
        self.result: SlotResult | None = None

    @property
    def heard(self) -> str:
        return " ".join(self._segments)

    def on_event(self, event: StreamEvent) -> Decision:
        if event.kind == "speech_start":
            self._end_at = self._nudge_at = None
            return Decision.WAIT
        if event.kind not in FINAL_KINDS:
            return Decision.WAIT
        self._segments.append(event.text)
        if self._slot is None:
            self._end_at = event.t + self._fallback_s
            return Decision.WAIT
        self.result = self._slot.evaluate(self.heard)
        if self.result.state is SlotState.COMPLETE:
            return Decision.END_TURN
        if self.result.state is SlotState.OPEN:
            grace = self._long_grace_s if self.result.likely_more else self._grace_s
            self._end_at = event.t + grace
        else:
            self._nudge_at = event.t + self._hold_cap_s
        return Decision.WAIT

    def rearm(self, t: float) -> None:
        """After the agent has nudged the caller, give them a fresh hold cap from time t."""
        if self._nudge_at is not None:
            self._nudge_at = t + self._hold_cap_s

    def on_tick(self, t: float) -> Decision:
        if self._end_at is not None and t >= self._end_at:
            return Decision.END_TURN
        if self._nudge_at is not None and t >= self._nudge_at:
            return Decision.NUDGE
        return Decision.WAIT
