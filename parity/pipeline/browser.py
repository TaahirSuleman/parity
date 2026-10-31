"""One Chromium per process, fixed 1280×720 viewport (computer-use coordinates depend on it)."""

from __future__ import annotations

import asyncio

from playwright.async_api import Browser, Page, Playwright, async_playwright

VIEWPORT = {"width": 1280, "height": 720}

_playwright: Playwright | None = None
_browser: Browser | None = None
_loop: asyncio.AbstractEventLoop | None = None
_lock: asyncio.Lock | None = None


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
            _browser = await _playwright.chromium.launch()
        return _browser


async def new_page() -> Page:
    browser = await get_browser()
    context = await browser.new_context(viewport=VIEWPORT, bypass_csp=True)  # axe is injected into any page
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
