"""Demo flows on the bundled ShopRight store."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Flow:
    id: str
    name: str
    start_url: str
    goal: str
    pages: tuple[str, ...]
    single_page: bool = True


FLOWS: dict[str, Flow] = {
    "checkout": Flow(
        id="checkout", name="Checkout page", start_url="/store/checkout.html", goal="Pay for the order",
        pages=("checkout.html",), single_page=True,
    ),
}
