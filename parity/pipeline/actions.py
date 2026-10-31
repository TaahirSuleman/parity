"""Allow-listed executor for the agent's computer-use actions. The model chooses; this code acts."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlsplit

from playwright.async_api import Page

from parity.config import Settings

log = logging.getLogger(__name__)

ALLOWED = {"click", "double_click", "type", "keypress", "scroll", "wait", "screenshot"}
KEY_MAP = {
    # ControlOrMeta: Spark says "ctrl" for select-all and copy; on macOS that key is Meta. Playwright maps it per platform.
    "CTRL": "ControlOrMeta", "CONTROL": "ControlOrMeta", "CMD": "Meta", "META": "Meta", "COMMAND": "Meta", "SHIFT": "Shift", "ALT": "Alt",
    "OPTION": "Alt", "ENTER": "Enter", "RETURN": "Enter", "BACKSPACE": "Backspace", "DELETE": "Delete", "TAB": "Tab", "ESC": "Escape",
    "ESCAPE": "Escape", "HOME": "Home", "END": "End", "PAGEUP": "PageUp", "PAGEDOWN": "PageDown", "UP": "ArrowUp", "DOWN": "ArrowDown",
    "LEFT": "ArrowLeft", "RIGHT": "ArrowRight", "SPACE": " ",
}
SETTLE_MS = 300


def chord(keys: list[str]) -> str:
    """Spark sends a chord as a list (["ctrl", "a"]); Playwright wants "Control+a"."""
    return "+".join(KEY_MAP.get(str(k).upper(), str(k)) for k in keys)


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def is_allowed_target(url: str, settings: Settings, base_url: str) -> bool:
    """Live runs may only navigate within the allowed origins ("self" = the server's own origin)."""
    if url.startswith("about:") or url.startswith("data:"):
        return True
    allowed = {_origin(base_url)} if settings.live_target_origins.strip() == "self" else {
        _origin(o.strip()) for o in settings.live_target_origins.split(",") if o.strip()
    }
    return _origin(url) in allowed


async def execute(page: Page, action: dict) -> bool:
    """Run one action. Returns False (and logs) for anything outside the allow-list or malformed."""
    kind = action.get("type")
    if kind not in ALLOWED:
        log.warning("agent asked for a disallowed action %r; dropped", kind)
        return False
    try:
        if kind in ("click", "double_click"):
            x, y = float(action["x"]), float(action["y"])
            if kind == "click":
                await page.mouse.click(x, y, button=action.get("button", "left"))
            else:
                await page.mouse.dblclick(x, y)
        elif kind == "type":
            await page.keyboard.type(str(action.get("text", "")))
        elif kind == "keypress":
            await page.keyboard.press(chord(action.get("keys") or []))
        elif kind == "scroll":
            await page.mouse.move(float(action.get("x", 640)), float(action.get("y", 360)))
            await page.mouse.wheel(float(action.get("scroll_x", 0)), float(action.get("scroll_y", 0)))
        elif kind == "wait":
            await asyncio.sleep(min(float(action.get("seconds", 1)), 5))
        elif kind == "screenshot":
            pass  # the loop always answers with a fresh screenshot
        return True
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("malformed %s action %r: %s", kind, action, exc)
        return False


async def settle(page: Page) -> None:
    try:
        await page.wait_for_load_state("load", timeout=5000)
    except Exception:
        pass
    await page.wait_for_timeout(SETTLE_MS)
