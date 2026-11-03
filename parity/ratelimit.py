"""Live-run rate limits (spec §15): a few runs per visitor per hour and a daily total for everyone.

Replay is never counted: it costs nothing and is the path judges are meant to take. The limiter is in-memory and
per process, which is exactly the deployment (one Cloud Run instance, one Live run at a time).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Literal

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


@dataclass(frozen=True)
class Closed:
    """A visitor-URL run refused by the day's caps (spec §19.3.3)."""

    scope: Literal["day", "origin"]
    retry_after_s: int
    allowed: bool = False

    @property
    def message(self) -> str:
        if self.scope == "day":
            return "closed for today: the day's budget for pages visitors choose is spent"
        return "this site has had its runs for today; try another page, or come back tomorrow"


def _site(origin: str) -> str:
    """The per-origin cap's key: the host without scheme or a leading www., so http://a, https://a and https://www.a are one site."""
    from urllib.parse import urlsplit

    from parity.pipeline.urlpolicy import fold_host

    host = fold_host(urlsplit(origin).hostname or origin) or origin.lower()
    return host[4:] if host.startswith("www.") else host


def _day_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass(frozen=True)
class ExternalBudget:
    """Caps on pages visitors choose, on top of the Live limits: per run (the runner ends the run at it), per UTC day for
    everyone, and per origin per day. The day's runs are read from the index, so they survive a restart."""

    run_usd: float
    daily_usd: float
    per_origin_per_day: int

    def run_exhausted(self, cost_usd: float) -> bool:
        return cost_usd >= self.run_usd

    async def _today(self, index: Any, now: datetime | None) -> list[Any]:
        return await index.external_runs_since(_day_start(now or datetime.now(UTC)))

    async def spent_today(self, index: Any, *, now: datetime | None = None) -> float:
        return float(sum(r.cost_usd for r in await self._today(index, now)))

    async def day_closed(self, index: Any, *, now: datetime | None = None) -> bool:
        return await self.spent_today(index, now=now) >= self.daily_usd

    async def check(self, index: Any, origin: str, *, now: datetime | None = None) -> Allowed | Closed:
        now = now or datetime.now(UTC)
        runs = await self._today(index, now)
        until_midnight = max(1, int((_day_start(now) + timedelta(days=1) - now.astimezone(UTC)).total_seconds()))
        if sum(r.cost_usd for r in runs) >= self.daily_usd:
            return Closed(scope="day", retry_after_s=until_midnight)
        if sum(1 for r in runs if _site(r.origin) == _site(origin)) >= self.per_origin_per_day:
            return Closed(scope="origin", retry_after_s=until_midnight)
        return Allowed()
