"""Live-run rate limits (spec §15): per visitor per hour and for everyone per day; Replay is never counted."""

import pytest

from parity.ratelimit import Denied, RateLimiter


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_per_ip_limit():
    clock = Clock()
    rl = RateLimiter(per_ip_per_hour=3, global_per_day=40, clock=clock)
    for _ in range(3):
        assert rl.take("1.1.1.1").allowed
    denied = rl.take("1.1.1.1")
    assert isinstance(denied, Denied) and denied.scope == "ip" and denied.retry_after_s == 3600
    assert rl.take("2.2.2.2").allowed  # another visitor is unaffected
    clock.t = 1800
    assert rl.take("1.1.1.1").retry_after_s == 1800  # the oldest run ages out at the hour mark
    clock.t = 3601
    assert rl.take("1.1.1.1").allowed


def test_global_limit():
    clock = Clock()
    rl = RateLimiter(per_ip_per_hour=100, global_per_day=5, clock=clock)
    for i in range(5):
        assert rl.take(f"10.0.0.{i}").allowed
    denied = rl.take("10.0.0.9")
    assert isinstance(denied, Denied) and denied.scope == "global" and denied.retry_after_s == 86400
    clock.t = 86400
    assert rl.take("10.0.0.9").allowed


def test_check_looks_without_counting():
    rl = RateLimiter(per_ip_per_hour=1, global_per_day=10, clock=Clock())
    assert rl.check("a").allowed and rl.check("a").allowed
    assert rl.take("a").allowed
    assert isinstance(rl.check("a"), Denied) and isinstance(rl.take("a"), Denied)


def test_unknown_visitor_is_one_bucket():
    rl = RateLimiter(per_ip_per_hour=2, global_per_day=10, clock=Clock())
    assert rl.take("").allowed and rl.take("").allowed and isinstance(rl.take(""), Denied)


def test_check_never_allocates_state():
    """Refused or probing requests must not grow the limiter: 2,000 forged hops left 8 MB of keys in review."""
    rl = RateLimiter(per_ip_per_hour=1, global_per_day=10, clock=Clock())
    for i in range(100):
        rl.check(f"10.0.{i // 256}.{i % 256}" + "x" * 50)
    assert rl._per_ip == {}
    rl.take("1.1.1.1")
    assert set(rl._per_ip) == {"1.1.1.1"}


def test_denied_message_states_the_limit_only():
    """The UI writes the retry time and the Replay suggestion once; the server's text must not repeat them."""
    rl = RateLimiter(per_ip_per_hour=0, global_per_day=10, clock=Clock())
    d = rl.take("a")
    assert isinstance(d, Denied) and "Replay" not in d.message and "try again" not in d.message.lower()


def test_a_zero_or_negative_global_limit_refuses_without_crashing():
    """PARITY_LIVE_GLOBAL_PER_DAY=0 is how an operator turns Live off for the day; it used to raise IndexError (a 500) instead of a 429."""
    for limit in (0, -1):
        limiter = RateLimiter(per_ip_per_hour=3, global_per_day=limit)
        verdict = limiter.check("1.2.3.4")
        assert not verdict.allowed and verdict.scope == "global" and verdict.retry_after_s >= 1
        assert not limiter.take("1.2.3.4").allowed


class FakeIndex:
    """What ExternalBudget reads: the visitor-URL runs started since a moment."""

    def __init__(self, runs):
        self.runs = runs

    async def external_runs_since(self, since):
        return [r for r in self.runs if r.started_at >= since]


def _visitor_run(origin: str, cost: float, at):
    from parity.store.models import Run, RunMode

    return Run(id=f"r-{origin[8:]}-{at:%d%H%M}", mode=RunMode.live, flow_id="url-x", source="visitor-url", origin=origin, cost_usd=cost, started_at=at)


async def test_per_origin_per_day():
    """Spec §19.3.3: a few visitor-URL runs per origin per UTC day, read from the index; yesterday's do not count."""
    from datetime import UTC, datetime, timedelta

    from parity.ratelimit import Closed, ExternalBudget

    day = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    a = "https://a.example"
    runs = [_visitor_run(a, 0.4, day - timedelta(hours=1)), _visitor_run(a, 0.3, day - timedelta(hours=2)), _visitor_run(a, 0.2, day - timedelta(hours=3)),
            _visitor_run(a, 0.5, day - timedelta(days=1, hours=1))]
    budget = ExternalBudget(run_usd=0.5, daily_usd=5.0, per_origin_per_day=3)
    verdict = await budget.check(FakeIndex(runs), a, now=day)
    assert isinstance(verdict, Closed) and verdict.scope == "origin" and verdict.retry_after_s == 15 * 3600  # until midnight UTC
    assert "today" in verdict.message and "a.example" not in verdict.message
    assert (await budget.check(FakeIndex(runs), "https://b.example", now=day)).allowed
    assert (await budget.check(FakeIndex(runs[1:]), a, now=day)).allowed  # two today so far: a third is fine


async def test_daily_cap_closes_the_field_for_everyone():
    from datetime import UTC, datetime, timedelta

    from parity.ratelimit import Closed, ExternalBudget

    day = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
    runs = [_visitor_run("https://a.example", 0.6, day - timedelta(hours=1)), _visitor_run("https://b.example", 0.45, day - timedelta(hours=2))]
    budget = ExternalBudget(run_usd=0.5, daily_usd=1.0, per_origin_per_day=3)
    verdict = await budget.check(FakeIndex(runs), "https://c.example", now=day)
    assert isinstance(verdict, Closed) and verdict.scope == "day" and verdict.message == "closed for today: the day's budget for pages visitors choose is spent"
    assert await budget.spent_today(FakeIndex(runs), now=day) == pytest.approx(1.05)
    assert await budget.day_closed(FakeIndex(runs), now=day) is True and await budget.day_closed(FakeIndex(runs[:1]), now=day) is False
    assert budget.run_exhausted(0.5) and budget.run_exhausted(0.51) and not budget.run_exhausted(0.49)
