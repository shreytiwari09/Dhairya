"""Shared records for stream events, decisions and policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from dhairya.entities.slots import Slot

# Event kinds that carry a finished segment's text. With partial results on,
# Prisma names the closing event final_transcript instead of transcript.
FINAL_KINDS = ("transcript", "final_transcript")


@dataclass(frozen=True)
class StreamEvent:
    """One message from Prisma's realtime stream.

    t is seconds on the client monotonic clock, measured from the first audio
    frame sent. Audio is sent at real-time pace, so t is also a position in the
    audio plus network and processing delay.
    """

    t: float
    kind: str  # connected | speech_start | processing | transcript | error | ...
    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


class Decision(Enum):
    WAIT = "wait"
    END_TURN = "end_turn"
    NUDGE = "nudge"  # hold cap reached: prompt the caller instead of waiting on


class TurnPolicy(Protocol):
    """Decides when the caller's turn is over.

    Pure: no network, clock or disk. Time reaches it only through event
    timestamps and on_tick, so the same code runs live and over saved traces.
    """

    name: str

    def reset(self, expected: Slot | None) -> None: ...

    def on_event(self, event: StreamEvent) -> Decision: ...

    def on_tick(self, t: float) -> Decision: ...

    @property
    def heard(self) -> str: ...
