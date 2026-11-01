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
        """The limit that was hit, and nothing more: the UI adds the retry time and the Replay suggestion once."""
        return "you have used this hour's Live runs" if self.scope == "ip" else "today's Live runs are used up for everyone"


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
        """Looks without allocating: a refused or probing request must not grow the limiter (forged addresses are free to send)."""
        now = self.clock()
        self._prune(self._global, DAY_S, now)
        if self.global_per_day <= 0 or len(self._global) >= self.global_per_day:  # a limit of 0 is "Live is off today"
            return Denied(retry_after_s=max(1, int(DAY_S - (now - self._global[0]))) if self._global else DAY_S, scope="global")
        mine = self._per_ip.get(ip or "unknown")
        if mine is not None:
            self._prune(mine, HOUR_S, now)
            if not mine:
                del self._per_ip[ip or "unknown"]
                mine = None
        if len(mine or ()) >= self.per_ip_per_hour:  # a limit of 0 refuses everyone, without ever allocating
            return Denied(retry_after_s=max(1, int(HOUR_S - (now - mine[0]))) if mine else HOUR_S, scope="ip")
        return Allowed()

    def take(self, ip: str) -> Verdict:
        verdict = self.check(ip)
        if verdict.allowed:
            now = self.clock()
            self._global.append(now)
            self._per_ip.setdefault(ip or "unknown", deque()).append(now)
        return verdict
