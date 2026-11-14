"""Who may start a live turn, and how many. Pure: the clock is passed in, so tests never wait."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

HOUR_S = 3600.0
DAY_S = 86400.0


class LiveLimits:
    """Concurrent callers, per-visitor hourly and daily turns, and a daily total for everyone.

    try_start returns None when the turn may begin (and counts it), else why it may not:
    "busy", "limit_ip" or "limit_total". Call finish() when a started turn ends.
    """

    def __init__(
        self,
        *,
        max_concurrent: int,
        per_ip_hour: int,
        per_ip_day: int,
        daily_total: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.per_ip_hour = per_ip_hour
        self.per_ip_day = per_ip_day
        self.daily_total = daily_total
        self._clock = clock
        self._active = 0
        self._all: deque[float] = deque()
        self._by_ip: dict[str, deque[float]] = defaultdict(deque)
        self.paused = False  # set when Gnani says the credits are gone

    def _prune(self, now: float) -> None:
        while self._all and self._all[0] <= now - DAY_S:
            self._all.popleft()
        for ip in list(self._by_ip):
            q = self._by_ip[ip]
            while q and q[0] <= now - DAY_S:
                q.popleft()
            if not q:
                del self._by_ip[ip]

    def try_start(self, ip: str) -> str | None:
        now = self._clock()
        self._prune(now)
        if self._active >= self.max_concurrent:
            return "busy"
        if len(self._all) >= self.daily_total:
            return "limit_total"
        q = self._by_ip[ip]
        last_hour = sum(1 for stamp in q if stamp > now - HOUR_S)
        if last_hour >= self.per_ip_hour or len(q) >= self.per_ip_day:
            return "limit_ip"
        q.append(now)
        self._all.append(now)
        self._active += 1
        return None

    def finish(self) -> None:
        self._active = max(0, self._active - 1)

    def status(self) -> dict:
        self._prune(self._clock())
        left = max(0, self.daily_total - len(self._all))
        return {"busy": self._active >= self.max_concurrent, "turns_left_today": left}
