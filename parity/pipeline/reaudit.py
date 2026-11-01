"""Re-audit: reload the patched page and decide in code whether the gap closed (spec §6, D4).

The hosted store never changes. The patched source is served to the browser at the page's real URL
by route interception (fragment-insensitive, and the page is confirmed served), captured again, and
the fixed element's new accessible name is compared with the sighted text. While the patched page
is open it cannot reach the API: whatever a snippet might smuggle past the validator stays inert.
The comparator runs once more as a second signal only; it does not decide.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
import posixpath
from urllib.parse import unquote, urlparse

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


def _without_fragment(url: str) -> str:
    return url.split("#", 1)[0]


SANDBOX_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
               "font-src 'self' data:; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'")


def request_allowed(url: str, method: str, origin: str) -> bool:
    """The patched page may load only GET /store/* from its own origin: decoded, normalised, case-sensitive."""
    parsed, home = urlparse(url), urlparse(origin)
    if method.upper() != "GET" or (parsed.scheme, parsed.netloc) != (home.scheme, home.netloc):
        return False
    raw = parsed.path
    if "//" in raw or ".." in raw:
        return False
    path = raw
    for _ in range(3):  # decode until stable: /%2561pi -> /%61pi -> /api
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    path = posixpath.normpath(path)
    return path.startswith("/store/") and ".." not in path and path == raw


@contextlib.asynccontextmanager
async def load_patched(page: Page, url: str, patched_html: str) -> AsyncIterator[Page]:
    """Serve the patched document at its real URL (relative assets keep resolving) with the API unreachable."""
    document = _without_fragment(url)
    served = 0

    async def fulfil(route: Route) -> None:
        nonlocal served
        served += 1
        await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=patched_html, headers={"Content-Security-Policy": SANDBOX_CSP})

    origin = f"{urlparse(document).scheme}://{urlparse(document).netloc}"

    async def police(route: Route) -> None:
        req = route.request
        if _without_fragment(req.url) == document and req.method.upper() == "GET":
            await fulfil(route)
        elif request_allowed(req.url, req.method, origin):
            await route.continue_()
        else:
            await route.abort("blockedbyclient")

    # The app's pages bypass CSP so axe can be injected into any public page; the sandbox must not inherit that, or the
    # Content-Security-Policy above is decoration. The patched page lives in a context of its own, closed afterwards.
    browser = page.context.browser
    context = await browser.new_context(viewport=page.viewport_size or {"width": 1280, "height": 720}) if browser is not None else None
    sandbox = await context.new_page() if context is not None else page
    await sandbox.route("**/*", police)
    try:
        if _without_fragment(sandbox.url) == document:
            await sandbox.goto("about:blank")  # a same-document (fragment) navigation makes no request, so nothing would be served
        await sandbox.goto(document, wait_until="load")
        if served == 0:
            raise RuntimeError(f"the patched page was not served for {url}; the re-audit would have read the live page")
        yield sandbox
    finally:
        await sandbox.unroute("**/*", police)
        if context is not None:
            await context.close()


async def reaudit(client, page_factory: PageFactory, page_html: str, url: str, fix: Fix, finding: Finding, run_id: str,
                  *, model: str, effort: str = "low") -> Reaudit:
    patched = apply_fix(page_html, finding.element, fix.after_html)
    page = await page_factory()
    async with load_patched(page, url, patched) as sandbox:
        cap = await capture(sandbox, finding.step_index)
        new_name = name_after(cap, finding)
        candidates = await compare(client, cap, [], run_id, model=model, effort=effort)
    still_flags = any(
        same_element(locate(c.bbox, cap.ax_nodes), finding) or normalise(c.sighted_text) == normalise(finding.sighted_text)
        for c in candidates
    )
    return Reaudit(gap_closed=gap_closed(finding.sighted_text, new_name), sr_name_before=finding.sr_name,
                   sr_name_after=new_name, comparator_still_flags=still_flags)
