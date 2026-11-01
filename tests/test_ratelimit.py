"""Live-run rate limits (spec §15): per visitor per hour and for everyone per day; Replay is never counted."""

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
