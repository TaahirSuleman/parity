"""Live-run rate limits (spec §15): a few runs per visitor per hour and a daily total for everyone.

Replay is never counted: it costs nothing and is the path judges are meant to take. The limiter is in-memory and
per process, which is exactly the deployment (one Cloud Run instance, one Live run at a time).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Literal

HOUR_S = 3600
DAY_S = 86400


@dataclass(frozen=True)
class Allowed:
    allowed: bool = True
    retry_after_s: int = 0


@dataclass(frozen=True)
class Denied:
    retry_after_s: int
    scope: Literal["ip", "global"]
    allowed: bool = False

    @property
    def message(self) -> str:
        if self.scope == "ip":
            return f"you have used this hour's Live runs; try again in {self.retry_after_s} s, or watch a Replay (no model calls, no limit)"
        return f"today's Live runs are used up for everyone; try again in {self.retry_after_s} s, or watch a Replay (no model calls, no limit)"


Verdict = Allowed | Denied


class RateLimiter:
    """Sliding windows of start times: ``check`` looks, ``take`` looks and records."""

    def __init__(self, per_ip_per_hour: int, global_per_day: int, clock: Callable[[], float] = time.monotonic):
        self.per_ip_per_hour = per_ip_per_hour
        self.global_per_day = global_per_day
        self.clock = clock
        self._per_ip: dict[str, deque[float]] = {}
        self._global: deque[float] = deque()

    def _prune(self, window: deque[float], span: float, now: float) -> None:
        while window and now - window[0] >= span:
            window.popleft()

    def check(self, ip: str) -> Verdict:
        now = self.clock()
        self._prune(self._global, DAY_S, now)
        if len(self._global) >= self.global_per_day:
            return Denied(retry_after_s=max(1, int(DAY_S - (now - self._global[0]))), scope="global")
        mine = self._per_ip.setdefault(ip or "unknown", deque())
        self._prune(mine, HOUR_S, now)
        if len(mine) >= self.per_ip_per_hour:
            return Denied(retry_after_s=max(1, int(HOUR_S - (now - mine[0]))), scope="ip")
        return Allowed()

    def take(self, ip: str) -> Verdict:
        verdict = self.check(ip)
        if verdict.allowed:
            now = self.clock()
            self._global.append(now)
            self._per_ip.setdefault(ip or "unknown", deque()).append(now)
        return verdict
