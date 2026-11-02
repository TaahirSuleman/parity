"""One Chromium per process, fixed 1280×720 viewport (computer-use coordinates depend on it).

An external page (a site we do not serve, spec §19.3.1) gets its own context: a user agent that names Parity and links the
policy page, and a request guard that judges every request the page makes, redirect hops included, aborting any whose host
is not public. Hosts are judged once per page (one run) and main-frame navigations are spaced by a crawl delay.

Playwright does not route a redirect hop (Chromium follows it inside the intercepted request, and a fulfilled 3xx is followed
the same way: verified 2 Nov), so the guard fetches every request itself with redirects off, walks a redirect chain hop by
hop judging each host, and only then hands the browser the first response. A chain is therefore fetched twice; a hop to a
non-public address is never fetched at all.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin, urlsplit

from playwright.async_api import Browser, Page, Playwright, Request, Route, async_playwright

from parity import __version__
from parity.pipeline.urlpolicy import Refusal, is_public_ip, resolve_public

log = logging.getLogger(__name__)
VIEWPORT = {"width": 1280, "height": 720}
LAUNCH_ARGS = ["--host-resolver-rules=MAP metadata.google.internal ~NOTFOUND"]  # the cloud metadata name never resolves in Chromium, whatever DNS says
CRAWL_DELAY_S = 1.0  # between main-frame navigations on a site we do not serve
PASS_THROUGH = ("data", "blob", "about")  # no host, no network
MAX_REDIRECTS = 10
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

    def __init__(self, *, on_blocked: BlockedHook | None = None, judge: Judge | None = None, delay_s: float = CRAWL_DELAY_S) -> None:
        self.on_blocked = on_blocked
        self.judge = judge or host_is_public
        self.delay_s = delay_s
        self.verdicts: dict[str, asyncio.Future[bool]] = {}  # one judgement per host, however many requests ask at once
        self.blocked: list[tuple[str, str]] = []  # each (host, reason) once, in order of first sight
        self.counts: Counter[tuple[str, str]] = Counter()  # how many requests each (host, reason) refused: a flood is one report
        self._last_nav: float | None = None

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
        if not await self._public(host):
            await self._abort(route, request, host, "not a public address")
            return
        if _main_navigation(request):
            await self._pace()
        try:
            response = await route.fetch(max_redirects=0)
            hop = response
            for _ in range(MAX_REDIRECTS):  # judge every hop before the browser learns of the first
                location = _redirect_target(hop)
                if location is None:
                    break
                next_scheme, next_host = location.partition(":")[0].lower(), (urlsplit(location).hostname or "").lower()
                if next_scheme not in ("http", "https") or not next_host:
                    await self._abort(route, request, next_host or next_scheme, "redirect to a non-web address")
                    return
                if not await self._public(next_host):
                    await self._abort(route, request, next_host, "redirect to a non-public address")
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
        await route.fulfill(response=response)

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
            log.warning("request guard could not judge %s: %s; refused", host, exc)
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
                   delay_s: float = CRAWL_DELAY_S, guard: RequestGuard | None = None) -> Page:
    """A page in its own context. ``external`` is a site we do not serve: Parity's user agent and the request guard on the whole
    context (a page-level route would not see a popup's requests), with service workers blocked (no route ever sees theirs)."""
    browser = await get_browser()
    if not external:
        context = await browser.new_context(viewport=VIEWPORT, bypass_csp=True)  # axe is injected into any page
        return await context.new_page()
    context = await browser.new_context(viewport=VIEWPORT, bypass_csp=True, user_agent=user_agent(own_origin), service_workers="block")
    await context.route("**/*", guard or RequestGuard(on_blocked=on_blocked, judge=judge, delay_s=delay_s))
    return await context.new_page()


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
