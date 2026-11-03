"""Allow-listed executor for the agent's computer-use actions. The model chooses; this code acts."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from parity.config import Settings
from parity.pipeline import browser

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
# A page we do not serve may paint a loading screen at load and fill itself in from scripts (www.takealot.com, found by the hosted
# verification of 26F.6, 3 Nov): before its first capture it gets a bounded wait for its words, and one that never shows any is reported, not audited.
RENDER_WAIT_S = 20.0
RENDER_SETTLE_S = 5.0  # a later screen of a guarded walk: the same wait, shorter, and never the run's to end
RENDER_STILL_S = 3.0  # once the floor is cleared, at most this long for the words to hold still (a ticker never does)
RENDER_MIN_TEXT = 40  # visible characters that make a page a page rather than a spinner
RENDER_MIN_ELEMENTS = 50  # or this many elements: an image-led page has few words
RENDER_POLL_MS = 500
WEB_PAGE_TYPES = ("text/html", "application/xhtml+xml")
NOT_WEB_PAGE = "the address is not a web page: {}"
# the visible words and the elements, read through open shadow roots as the wall probe reads them (a web-components site keeps its words there)
_RENDERED_JS = """() => {
  const visible = (n) => { const r = n.getBoundingClientRect(); const cs = getComputedStyle(n); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none"; };
  let text = 0, elements = 0;
  const take = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT); let n;
    while ((n = walker.nextNode())) {
      if (n.nodeType === Node.ELEMENT_NODE) { elements += 1; if (n.shadowRoot) take(n.shadowRoot); continue; }
      const p = n.parentElement || (n.parentNode && n.parentNode.host);
      if (!p || ["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(p.tagName)) continue;
      const s = n.textContent.replace(/\\s+/g, " ").trim();
      if (s && visible(p)) text += s.length;
    }
  };
  try { if (document.body) take(document.body); } catch (e) {}
  return { text, elements, type: document.contentType || "" };
}"""


async def wait_rendered(page: Page, timeout_s: float = RENDER_WAIT_S) -> str | None:
    """Wait, bounded, until the page shows words (or many elements) and their count is the same on two polls, or has held the floor
    for RENDER_STILL_S; None once it has rendered, else one sentence saying it never did, or that the address is not a web page.
    Returns at once when the guard has aborted a navigation the page started: settle_redirects names that."""
    deadline = time.monotonic() + timeout_s
    last: tuple[int, int] | None = None
    shown_at: float | None = None
    while True:
        guard = getattr(page, "parity_guard", None)
        if guard is not None and guard.nav_abort:
            return None
        try:
            now = await page.evaluate(_RENDERED_JS)
        except Exception:  # mid-navigation: nothing to measure yet
            now = {"text": 0, "elements": 0, "type": ""}
        kind = str(now.get("type") or "")
        if kind and kind not in WEB_PAGE_TYPES:
            return NOT_WEB_PAGE.format(kind)
        measure = (int(now.get("text") or 0), int(now.get("elements") or 0))
        shown = measure[0] >= RENDER_MIN_TEXT or measure[1] >= RENDER_MIN_ELEMENTS
        t = time.monotonic()
        if shown:
            shown_at = shown_at if shown_at is not None else t
            if measure == last or t - shown_at >= RENDER_STILL_S:
                return None
        else:
            shown_at = None  # the page emptied again (a navigation mid-wait): the next document gets its own stillness clock
        last = measure
        if t >= deadline:
            return None if shown else f"the page showed no content after {int(round(timeout_s))} s: a loading screen at most"
        await page.wait_for_timeout(RENDER_POLL_MS)


def _key_name(key: str) -> str:
    """Page_Down, page down, ARROW_LEFT -> PageDown, ArrowLeft; single characters and mapped modifiers pass through."""
    raw = str(key)
    if raw.upper() in KEY_MAP:
        return KEY_MAP[raw.upper()]
    parts = [p for p in re.split(r"[\s_]+", raw) if p]
    if len(parts) > 1 or (len(raw) > 1 and raw.islower() and raw.isalpha() and raw not in ("enter", "tab", "escape", "space", "backspace", "delete", "home", "end")):
        return "".join(p[:1].upper() + p[1:] for p in parts)
    if len(raw) > 1 and raw.isalpha() and raw.islower():
        return raw[:1].upper() + raw[1:]
    return raw


def chord(keys: list[str]) -> str:
    """Spark sends a chord as a list (["ctrl", "a"]); Playwright wants "Control+a"."""
    return "+".join(_key_name(k) for k in keys)


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
    if not isinstance(action, dict):
        log.warning("agent sent a malformed action %r; dropped", type(action).__name__)
        return False
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
    except PlaywrightError as exc:
        if page.is_closed() or "closed" in str(exc).lower():
            raise
        log.warning("%s action %r rejected by the browser: %s", kind, action, str(exc).splitlines()[0])
        return False


async def settle(page: Page) -> None:
    try:
        await page.wait_for_load_state("load", timeout=5000)
        await browser.settle_redirects(page)  # a guarded page's redirect hops are navigations of their own (a refused hop is already reported)
        if getattr(page, "parity_guard", None) is not None:  # a later screen of a page we do not serve may fill itself in from scripts, too
            await wait_rendered(page, RENDER_SETTLE_S)  # its verdict is not the walk's to act on: the screen is the model's to judge
    except Exception:
        pass
    await page.wait_for_timeout(SETTLE_MS)
