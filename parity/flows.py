"""Demo flows on the bundled ShopRight store, and the external pages a judge can run read-only (spec §19.2)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Flow:
    id: str
    name: str
    start_url: str  # a path under the app's own origin, or an absolute URL on a site we do not serve
    goal: str
    pages: tuple[str, ...]
    single_page: bool = True
    public: bool = False  # a page we do not serve: the read-only guard is on and nothing is fixed or re-audited (spec §17, §19.2)
    attribution: str = ""  # whose page it is, shown under the header and carried in the bundle

    @property
    def origin(self) -> str:
        """scheme://host of an absolute start URL (an external page); "" for a store path served by the app itself."""
        parts = urlsplit(self.start_url)
        return f"{parts.scheme}://{parts.netloc}" if parts.scheme in ("http", "https") and parts.netloc else ""

    def target_url(self, base_url: str) -> str:
        """Where the run starts: the absolute start URL as it is, or the store path under ``base_url``."""
        return self.start_url if self.origin else base_url.rstrip("/") + self.start_url


FLOWS: dict[str, Flow] = {
    "checkout": Flow(
        id="checkout", name="Checkout page", start_url="/store/checkout.html", goal="Pay for the order",
        pages=("checkout.html",), single_page=True,
    ),
    "purchase": Flow(
        id="purchase", name="Purchase flow",  start_url="/store/product.html",
        goal="Buy the noise-cancelling headphones and pay with card 4111 1111 1111 1111, expiry 10/28. The cart may already hold other items: leave them exactly as they are and go straight to checkout. Stop when the order is confirmed.",
        pages=("product.html", "cart.html", "checkout.html", "confirm.html"), single_page=False,
    ),
}

# The W3C WAI "Before and After Demonstration": four pages built to show barriers, with W3C's own numbered annotations
# (doc 18 §11, doc 19 §19.1). Live on www.w3.org; robots.txt allows /WAI/demos/; W3C document licence (copyright line kept).
BAD_BEFORE = "https://www.w3.org/WAI/demos/bad/before"
W3C_ATTRIBUTION = ("Page by W3C WAI, \"Before and After Demonstration\" (BAD), Copyright © 2012 W3C® (MIT, ERCIM, Keio), "
                   "used under the W3C document licence; audited read-only, nothing is changed on it")

EXTERNAL_FLOWS: dict[str, Flow] = {
    "bad-home": Flow(
        id="bad-home", name="W3C demo: home", start_url=f"{BAD_BEFORE}/home.html",
        goal="Read the home page as a visitor would, to see what is on it and where it leads. Do not follow any link.",
        pages=("home.html",), single_page=True, public=True, attribution=W3C_ATTRIBUTION,
    ),
    "bad-news": Flow(
        id="bad-news", name="W3C demo: news", start_url=f"{BAD_BEFORE}/news.html",
        goal="Read the news page as a visitor would, to find the latest news item. Do not follow any link.",
        pages=("news.html",), single_page=True, public=True, attribution=W3C_ATTRIBUTION,
    ),
    "bad-tickets": Flow(
        id="bad-tickets", name="W3C demo: tickets", start_url=f"{BAD_BEFORE}/tickets.html",
        goal="Look over the ticket page as a visitor choosing a ticket. Do not order, fill in or submit anything.",
        pages=("tickets.html",), single_page=True, public=True, attribution=W3C_ATTRIBUTION,
    ),
    "bad-survey": Flow(
        id="bad-survey", name="W3C demo: survey", start_url=f"{BAD_BEFORE}/survey.html",
        goal="Look over the survey as a visitor deciding whether to answer it. Do not fill in or submit anything.",
        pages=("survey.html",), single_page=True, public=True, attribution=W3C_ATTRIBUTION,
    ),
}


def available_flows(external: bool) -> dict[str, Flow]:
    """The flows the API offers: the store, then the external pages when PARITY_EXTERNAL_FLOWS is on."""
    return {**FLOWS, **EXTERNAL_FLOWS} if external else dict(FLOWS)
