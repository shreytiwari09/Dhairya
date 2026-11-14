"""Baseline: the turn ends after a fixed length of silence, whatever was said."""

from __future__ import annotations

from dhairya.entities.slots import Slot
from dhairya.turn.types import FINAL_KINDS, Decision, StreamEvent


class FixedTimerPolicy:
    """Ends the turn once silence reaches silence_ms.

    The stream is recorded with a short server window (window_ms). A segment's
    text arriving means window_ms of silence has already passed, so the policy
    waits the remainder and cancels if speech resumes first. This reproduces a
    server window of silence_ms without a separate recording per setting.
    """

    def __init__(self, silence_ms: int, window_ms: int = 200) -> None:
        if silence_ms < window_ms:
            raise ValueError("silence_ms cannot be shorter than the recording window")
        self.name = f"fixed_{silence_ms}ms"
        self._remainder_s = (silence_ms - window_ms) / 1000
        self.reset(None)

    def reset(self, expected: Slot | None) -> None:
        self._segments: list[str] = []
        self._fire_at: float | None = None

    @property
    def heard(self) -> str:
        return " ".join(self._segments)

    def on_event(self, event: StreamEvent) -> Decision:
        if event.kind == "speech_start":
            self._fire_at = None
        elif event.kind in FINAL_KINDS:
            self._segments.append(event.text)
            self._fire_at = event.t + self._remainder_s
            if self._remainder_s == 0:
                return Decision.END_TURN
        return Decision.WAIT

    def on_tick(self, t: float) -> Decision:
        if self._fire_at is not None and t >= self._fire_at:
            return Decision.END_TURN
        return Decision.WAIT
