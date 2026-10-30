"""One Chromium per process, fixed 1280×720 viewport (computer-use coordinates depend on it)."""

from __future__ import annotations

import asyncio

from playwright.async_api import Browser, Page, Playwright, async_playwright

VIEWPORT = {"width": 1280, "height": 720}

_playwright: Playwright | None = None
_browser: Browser | None = None
_lock = asyncio.Lock()


async def get_browser() -> Browser:
    global _playwright, _browser
    async with _lock:
        if _browser is None or not _browser.is_connected():
            _playwright = _playwright or await async_playwright().start()
            _browser = await _playwright.chromium.launch()
        return _browser


async def new_page() -> Page:
    browser = await get_browser()
    context = await browser.new_context(viewport=VIEWPORT)
    return await context.new_page()


async def shutdown() -> None:
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None
