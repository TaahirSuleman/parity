"""Re-audit: reload the patched page and decide in code whether the gap closed (spec §6, D4).

The hosted store never changes. The patched HTML is served to the browser at the page's real URL
by route interception, captured again, and the fixed element's new accessible name is compared
with the sighted text. The comparator runs once more as a second signal only; it does not decide.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from playwright.async_api import Page, Route

from parity.pipeline.capture import capture
from parity.pipeline.comparator import compare
from parity.pipeline.fixer import apply_fix
from parity.pipeline.verifier import locate, normalise
from parity.store.models import AxNode, Capture, Finding, Fix, Reaudit

log = logging.getLogger(__name__)
PageFactory = Callable[[], Awaitable[Page]]


def same_element(node: AxNode | None, finding: Finding) -> bool:
    if node is None:
        return False
    el = finding.element
    return (bool(el.css_path) and node.css_path == el.css_path) or (bool(el.dom_id) and node.dom_id == el.dom_id)


def name_after(cap: Capture, finding: Finding) -> str:
    """The fixed element's accessible name on the patched page; "" if it left the tree."""
    node = next((n for n in cap.ax_nodes if same_element(n, finding)), None)
    return node.name if node else ""


def gap_closed(sighted: str, new_name: str) -> bool:
    s, n = normalise(sighted), normalise(new_name)
    return bool(n) and (s in n or n == s)


async def load_patched(page: Page, url: str, patched_html: str) -> None:
    """Serve the patched document at its real URL, so relative assets and links keep resolving."""

    async def fulfil(route: Route) -> None:
        await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=patched_html)

    await page.route(url, fulfil)
    try:
        await page.goto(url, wait_until="load")
    finally:
        await page.unroute(url, fulfil)


async def reaudit(client, page_factory: PageFactory, page_html: str, url: str, fix: Fix, finding: Finding, run_id: str,
                  *, model: str, effort: str = "medium") -> Reaudit:
    patched = apply_fix(page_html, finding.element, fix.after_html)
    page = await page_factory()
    await load_patched(page, url, patched)
    cap = await capture(page, finding.step_index)
    new_name = name_after(cap, finding)
    candidates = await compare(client, cap, [], run_id, model=model, effort=effort)
    still_flags = any(
        same_element(locate(c.bbox, cap.ax_nodes), finding) or normalise(c.sighted_text) == normalise(finding.sighted_text)
        for c in candidates
    )
    return Reaudit(gap_closed=gap_closed(finding.sighted_text, new_name), sr_name_before=finding.sr_name,
                   sr_name_after=new_name, comparator_still_flags=still_flags)
