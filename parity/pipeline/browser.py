"""One Chromium per process, fixed 1280×720 viewport (computer-use coordinates depend on it).

An external page (a site we do not serve, spec §19.3.1) gets its own context: a user agent that names Parity and links the
policy page, and a request guard that judges every request the page makes, redirect hops included, aborting any whose host
is not public. Hosts are judged once per page (one run), at most MAX_HOSTS_PER_RUN of them, and main-frame navigations are
spaced by a crawl delay. WebSockets never leave a routed context (the test holds it; an explicit route_web_socket handler left a
task the event loop's teardown could not cancel); service workers are blocked by the context.

Playwright does not route a redirect hop (Chromium follows it inside the intercepted request, and a fulfilled 3xx is followed
the same way: verified 2 Nov), so a 3xx never reaches Chromium (review C1, 3 Nov). The guard fetches every request itself with
redirects off. A subresource's chain is walked hop by hop, each host judged, and the browser is answered with the final hop. A
main-frame navigation that redirects is answered with a small page of ours that carries the judged location and refreshes to
it, so each hop is a new routed navigation judged afresh; ``settle_redirects`` waits those pages out after a navigation. The
server therefore sees exactly one fetch per hop, from the guard, never a second one from the browser.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from html import escape
from urllib.parse import urljoin, urlsplit

from playwright.async_api import Browser, Page, Playwright, Request, Route, async_playwright
from playwright.async_api import Error as PlaywrightError

from parity import __version__
from parity.pipeline.urlpolicy import Refusal, is_public_ip, resolve_public

log = logging.getLogger(__name__)
VIEWPORT = {"width": 1280, "height": 720}
LAUNCH_ARGS = ["--host-resolver-rules=MAP metadata.google.internal ~NOTFOUND"]  # the cloud metadata name never resolves in Chromium, whatever DNS says
CRAWL_DELAY_S = 1.0  # between main-frame navigations on a site we do not serve
PASS_THROUGH = ("data", "blob", "about")  # no host, no network
MAX_REDIRECTS = 10
MAX_HOSTS_PER_RUN = 100  # distinct hosts judged on one run: a page naming thousands is not thousands of blocking lookups
REDIRECT_MARKER = "parity-redirect"  # the <meta name> of the guard's own redirect page
BlockedHook = Callable[[str, str, str], Awaitable[None]]  # (host, resource type, reason)
Judge = Callable[[str], bool]  # host -> public?

_playwright: Playwright | None = None
_browser: Browser | None = None
_loop: asyncio.AbstractEventLoop | None = None
_lock: asyncio.Lock | None = None


def user_agent(own_origin: str = "") -> str:
    return f"Parity/{__version__}" + (f" (+{own_origin.rstrip('/')}/audit-policy)" if own_origin else "")


def host_is_public(host: str) -> bool:
    """The policy for one request's host: an IP literal is judged as it is, a name by every address it resolves to (blocking DNS)."""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return not isinstance(resolve_public(host), Refusal)
    return is_public_ip(host)


class RequestGuard:
    """``page.route("**/*", guard)``: every request's host is judged once (a non-public verdict aborts the request and is
    reported through ``on_blocked``), and main-frame navigations wait out ``delay_s`` since the previous one."""

    def __init__(self, *, on_blocked: BlockedHook | None = None, judge: Judge | None = None, delay_s: float = CRAWL_DELAY_S,
                 max_hosts: int = MAX_HOSTS_PER_RUN) -> None:
        self.on_blocked = on_blocked
        self.judge = judge or host_is_public
        self.delay_s = delay_s
        self.max_hosts = max_hosts
        self.verdicts: dict[str, asyncio.Future[bool]] = {}  # one judgement per host, however many requests ask at once
        self.blocked: list[tuple[str, str]] = []  # each (host, reason) once, in order of first sight
        self.counts: Counter[tuple[str, str]] = Counter()  # how many requests each (host, reason) refused: a flood is one report
        self.nav_abort: tuple[str, str] | None = None  # the main-frame navigation in flight was aborted: (host, reason), for settle_redirects
        self._last_nav: float | None = None
        self._nav_hops = 0  # consecutive main-frame redirects: a loop ends as "too many redirects"

    async def __call__(self, route: Route, request: Request) -> None:
        url = request.url
        scheme = url.partition(":")[0].lower()
        if scheme in PASS_THROUGH:
            await route.continue_()
            return
        host = (urlsplit(url).hostname or "").lower() if scheme in ("http", "https") else ""
        if not host:
            await self._abort(route, request, scheme, "not a web address")
            return
        main = _main_navigation(request)
        if main:
            self.nav_abort = None
        if refusal := await self._admit(host):
            await self._abort(route, request, "(many)" if refusal.startswith("more than") else host, refusal)
            return
        if main:
            await self._pace()
        try:
            response = await route.fetch(max_redirects=0)
            if main:  # a redirect becomes a page of ours that navigates to the judged hop: the next hop is a routed navigation of its own
                location = _redirect_target(response)
                if location is None:
                    self._nav_hops = 0
                    await route.fulfill(response=response)
                    return
                self._nav_hops += 1
                if self._nav_hops > MAX_REDIRECTS:
                    self._nav_hops = 0
                    await self._abort(route, request, host, "too many redirects")
                    return
                if not await self._admit_hop(route, request, location):
                    return
                await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=redirect_page(location))
                return
            hop = response
            for _ in range(MAX_REDIRECTS):  # a subresource: walk the chain, judge every hop, answer with the last one
                location = _redirect_target(hop)
                if location is None:
                    break
                if not await self._admit_hop(route, request, location):
                    return
                hop = await route.fetch(url=location, max_redirects=0)
            else:
                await self._abort(route, request, host, "too many redirects")
                return
        except Exception as exc:  # the page is gone, or the fetch itself failed: the browser gets the failure, not a hang
            log.debug("request guard could not fetch %s: %s", host, str(exc).splitlines()[0])
            try:
                await route.abort("failed")
            except Exception:
                pass
            return
        await route.fulfill(response=hop)

    async def _admit(self, host: str) -> str | None:
        """None when the host may be fetched; else the reason it may not."""
        if host not in self.verdicts and len(self.verdicts) >= self.max_hosts:
            return f"more than {self.max_hosts} hosts on one run"
        return None if await self._public(host) else "not a public address"

    async def _admit_hop(self, route: Route, request: Request, location: str) -> bool:
        next_scheme, next_host = location.partition(":")[0].lower(), (urlsplit(location).hostname or "").lower()
        if next_scheme not in ("http", "https") or not next_host:
            await self._abort(route, request, next_host or next_scheme, "redirect to a non-web address")
            return False
        if refusal := await self._admit(next_host):
            await self._abort(route, request, "(many)" if refusal.startswith("more than") else next_host, "redirect to a non-public address" if refusal.startswith("not") else refusal)
            return False
        return True

    async def _public(self, host: str) -> bool:
        verdict = self.verdicts.get(host)
        if verdict is None:
            verdict = asyncio.ensure_future(asyncio.to_thread(self._judge, host))
            self.verdicts[host] = verdict
        return await verdict

    def _judge(self, host: str) -> bool:
        try:
            return bool(self.judge(host))
        except Exception as exc:  # a resolver error is a refusal, never an allowance
            log.warning("request guard could not judge a host: %s; refused", str(exc).splitlines()[0])  # the host itself only at DEBUG: logs outlive the run
            log.debug("the host that could not be judged: %s", host)
            return False

    async def _pace(self) -> None:
        now = time.monotonic()
        if self._last_nav is not None:
            wait = self._last_nav + self.delay_s - now
            if wait > 0:
                await asyncio.sleep(wait)
        self._last_nav = time.monotonic()

    async def _abort(self, route: Route, request: Request, host: str, reason: str) -> None:
        first = (host, reason) not in self.counts
        self.counts[(host, reason)] += 1
        if _main_navigation(request):
            self.nav_abort = (host, reason)
        try:
            await route.abort("blockedbyclient")
        except Exception as exc:  # the page may be gone already
            log.debug("abort of a blocked request failed: %s", exc)
        if first:  # a page that retries a refused address a thousand times is one report, not a thousand events
            self.blocked.append((host, reason))
            if self.on_blocked is not None:
                await self.on_blocked(host, request.resource_type, reason)


def _redirect_target(response) -> str | None:
    """The absolute URL a 3xx answer points at, or None for any other answer."""
    if not (300 <= response.status < 400):
        return None
    location = response.headers.get("location")
    return urljoin(response.url, location) if location else None


def redirect_page(location: str) -> str:
    """The guard's answer to a main-frame 3xx: a page that names the judged location and refreshes to it."""
    target = escape(location, quote=True)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="{REDIRECT_MARKER}" content="{target}">'
            f'<meta http-equiv="refresh" content="0;url={target}"><title>Redirecting</title></head><body></body></html>')


async def settle_redirects(page: Page, timeout_s: float = 30.0) -> None:
    """After a navigation on a guarded page: wait out the guard's redirect pages until a real document is up. Raises a
    PlaywrightError naming net::ERR_BLOCKED_BY_CLIENT when the guard aborted a hop, or net::ERR_TOO_MANY_REDIRECTS when the
    hops do not settle. A page without the guard returns at once."""
    guard = getattr(page, "parity_guard", None)
    if guard is None:
        return
    deadline = time.monotonic() + timeout_s
    while True:
        if guard.nav_abort is not None:  # the latest main-frame navigation was aborted: Chromium shows its error page, not the marker
            host, reason = guard.nav_abort
            code = "net::ERR_TOO_MANY_REDIRECTS" if reason == "too many redirects" else "net::ERR_BLOCKED_BY_CLIENT"
            raise PlaywrightError(f"{code} ({reason}: {host})")
        try:
            on_marker = await page.evaluate(f"() => !!document.querySelector('meta[name={REDIRECT_MARKER}]')")
        except PlaywrightError:  # the document is being replaced: a hop is landing
            on_marker = True
        if not on_marker:
            try:
                await page.wait_for_load_state("load", timeout=5000)
            except PlaywrightError:
                pass
            return
        if time.monotonic() > deadline:
            raise PlaywrightError("net::ERR_TOO_MANY_REDIRECTS (the redirects did not settle)")
        await asyncio.sleep(0.05)


def _main_navigation(request: Request) -> bool:
    try:
        return request.is_navigation_request() and request.frame.parent_frame is None
    except Exception:  # a request with no frame (a worker): not a navigation
        return False


async def get_browser() -> Browser:
    """The shared browser, bound to the running loop; a new loop (tests, reloads) gets a fresh one."""
    global _playwright, _browser, _loop, _lock
    loop = asyncio.get_running_loop()
    if _loop is not loop:
        _playwright, _browser, _loop, _lock = None, None, loop, asyncio.Lock()
    assert _lock is not None
    async with _lock:
        if _browser is None or not _browser.is_connected():
            _playwright = _playwright or await async_playwright().start()
            _browser = await _playwright.chromium.launch(args=LAUNCH_ARGS)
        return _browser


async def new_page(external: bool = False, *, own_origin: str = "", on_blocked: BlockedHook | None = None, judge: Judge | None = None,
                   delay_s: float = CRAWL_DELAY_S, guard: RequestGuard | None = None, max_hosts: int = MAX_HOSTS_PER_RUN) -> Page:
    """A page in its own context. ``external`` is a site we do not serve: Parity's user agent and the request guard on the whole
    context (a page-level route would not see a popup's requests), with service workers blocked (no route ever sees theirs)."""
    browser = await get_browser()
    if not external:
        context = await browser.new_context(viewport=VIEWPORT, bypass_csp=True)  # axe is injected into any page
        return await context.new_page()
    context = await browser.new_context(viewport=VIEWPORT, bypass_csp=True, user_agent=user_agent(own_origin), service_workers="block")
    guard = guard or RequestGuard(on_blocked=on_blocked, judge=judge, delay_s=delay_s, max_hosts=max_hosts)
    await context.route("**/*", guard)  # a routed context never opens a WebSocket either (Chromium's fetch interception swallows the upgrade; held by a test)
    page = await context.new_page()
    page.parity_guard = guard  # type: ignore[attr-defined]  # settle_redirects reads the guard's verdict on the navigation in flight
    return page


async def shutdown() -> None:
    """Close the shared browser. One owned by another loop (a server thread) is closed over there,
    best effort, never awaited here: awaiting another loop's browser deadlocks this one."""
    global _playwright, _browser, _loop, _lock
    if _loop is not None and _loop is not asyncio.get_running_loop():
        browser, owner = _browser, _loop
        _playwright, _browser, _loop, _lock = None, None, None, None
        if browser is not None and not owner.is_closed():
            asyncio.run_coroutine_threadsafe(browser.close(), owner)
        return
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None
    _loop, _lock = None, None
