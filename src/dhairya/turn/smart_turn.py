"""Baseline: Pipecat's Smart Turn, the leading open turn-detection model.

Smart Turn listens to the audio of the turn so far and says whether the speaker
sounds finished. The model itself runs in bench/smart_turn_scores.py, which
writes its probability onto each segment event; this policy only reads that
number, so it stays pure like the others.
"""

from __future__ import annotations

from dhairya.entities.slots import Slot
from dhairya.turn.types import FINAL_KINDS, Decision, StreamEvent

PROBABILITY_KEY = "smart_turn_p"


class SmartTurnPolicy:
    """Ends the turn at a pause if Smart Turn says the speaker is finished.

    If it says "not finished", the turn still ends after fallback_s of silence,
    as in Pipecat, whose default is 3 seconds.
    """

    name = "smart_turn"

    def __init__(self, threshold: float = 0.5, fallback_s: float = 3.0, window_ms: int = 200):
        self._threshold = threshold
        self._fallback_s = max(0.0, fallback_s - window_ms / 1000)
        self.reset(None)

    def reset(self, expected: Slot | None) -> None:
        self._segments: list[str] = []
        self._end_at: float | None = None

    @property
    def heard(self) -> str:
        return " ".join(self._segments)

    def on_event(self, event: StreamEvent) -> Decision:
        if event.kind == "speech_start":
            self._end_at = None
        elif event.kind in FINAL_KINDS:
            self._segments.append(event.text)
            probability = event.raw.get(PROBABILITY_KEY)
            if probability is None:
                raise ValueError("segment event has no Smart Turn probability")
            if probability > self._threshold:
                return Decision.END_TURN
            self._end_at = event.t + self._fallback_s
        return Decision.WAIT

    def on_tick(self, t: float) -> Decision:
        if self._end_at is not None and t >= self._end_at:
            return Decision.END_TURN
        return Decision.WAIT
