"""Scores for one policy over a set of calls."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CallScore:
    """How one policy did on one call."""

    script_id: str
    category: str
    variant: str
    voice: str
    policy: str
    decision: str  # end_turn | nudge | wait
    cut_in: bool  # ended the turn before the caller finished speaking
    delay_s: float | None  # caller's last sample to the decision; None if cut in or never ended
    correct: bool  # captured value equals the truth
    heard_value: str | None


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated percentile, q in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q / 100
    low = math.floor(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


@dataclass(frozen=True)
class Summary:
    policy: str
    n: int
    cut_ins: int
    correct: int
    nudges: int
    delay_p50: float | None
    delay_p95: float | None

    @property
    def cut_in_ci(self) -> tuple[float, float]:
        return wilson(self.cut_ins, self.n)

    @property
    def correct_ci(self) -> tuple[float, float]:
        return wilson(self.correct, self.n)


def summarise(policy: str, scores: Sequence[CallScore]) -> Summary:
    delays = [s.delay_s for s in scores if s.delay_s is not None]
    return Summary(
        policy=policy,
        n=len(scores),
        cut_ins=sum(s.cut_in for s in scores),
        correct=sum(s.correct for s in scores),
        nudges=sum(s.decision == "nudge" for s in scores),
        delay_p50=percentile(delays, 50),
        delay_p95=percentile(delays, 95),
    )
