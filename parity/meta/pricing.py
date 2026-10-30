"""Price table for Meta models (USD per 1M tokens: uncached input, cached input, output).

Source: dev.meta.ai pricing, captured 27 Oct 2026 (docs/hackathon/00-constitution.md, Article VI).
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

PRICES: dict[str, tuple[float, float, float]] = {
    "muse-spark-1.3": (1.25, 0.15, 4.25),
    "muse-spark-1.3-contributor": (0.10, 0.002, 0.20),
    "muse-spark-1.2": (1.25, 0.15, 4.25),
    "muse-spark-1.2-contributor": (0.10, 0.002, 0.20),
    "muse-wonder-1.0": (4.00, 0.20, 20.00),
}
ASR_USD_PER_HOUR = 0.18


def cost_usd(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
    """Cost of one call. ``input_tokens`` counts uncached input only; ``cached_tokens`` the cached prefix."""
    prices = PRICES.get(model)
    if prices is None:
        log.warning("no price for model %s; counting $0", model)
        return 0.0
    p_in, p_cached, p_out = prices
    return (input_tokens * p_in + cached_tokens * p_cached + output_tokens * p_out) / 1_000_000


def asr_cost_usd(audio_ms: int) -> float:
    return round(audio_ms / 3_600_000 * ASR_USD_PER_HOUR, 6)
