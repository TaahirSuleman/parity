import logging

from parity.meta.pricing import asr_cost_usd, cost_usd


def test_cost_spark13():
    assert cost_usd("muse-spark-1.3", 1_000_000, 0, 0) == 1.25


def test_cost_mixes_cached_and_output():
    cost = cost_usd("muse-spark-1.3-contributor", 1_000_000, 1_000_000, 1_000_000)
    assert round(cost, 6) == round(0.10 + 0.002 + 0.20, 6)


def test_unknown_model_costs_zero_and_warns(caplog):
    with caplog.at_level(logging.WARNING):
        assert cost_usd("muse-unknown", 1000, 0, 0) == 0.0
    assert "muse-unknown" in caplog.text


def test_asr_cost_per_hour():
    assert asr_cost_usd(3_600_000) == 0.18
