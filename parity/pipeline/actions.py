"""Allow-listed executor for the agent's computer-use actions. The model chooses; this code acts."""

from __future__ import annotations

import asyncio
import io
import logging
import math
import re
import time
from collections import Counter
from urllib.parse import urlsplit

from PIL import Image
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
# Click snap (4 Nov): the recorded purchase walks clicked the store's buttons 6 px below, 12 px right and 18 px left of their
# boxes and spent turns re-clicking. A click that lands on nothing clickable within SNAP_PX of a control is moved to that
# control's centre by code, before the public-site guard judges it, and the correction is logged in nav.actions.
SNAP_PX = 20
INTERACTIVE = "button, a[href], input, select, textarea, summary, [role=button], [role=link], [role=checkbox], [role=radio], [role=menuitem], [role=tab]"
_SNAP_JS = """([x, y, sel]) => {
  const el = document.elementFromPoint(x, y);
  const hit = !!(el && el.closest && el.closest(sel));
  const label = (n) => n.id ? "#" + n.id : ((n.getAttribute("aria-label") || n.innerText || n.textContent || n.tagName).replace(/\\s+/g, " ").trim().slice(0, 40));
  const boxes = [];
  for (const n of document.querySelectorAll(sel)) {
    const r = n.getBoundingClientRect(); if (r.width <= 0 || r.height <= 0) continue;
    const cs = getComputedStyle(n); if (cs.visibility === "hidden" || cs.display === "none") continue;
    boxes.push([[r.left, r.top, r.right, r.bottom], label(n)]);
  }
  return { hit, boxes };
}"""
# A page we do not serve may paint a loading screen at load and fill itself in from scripts (www.takealot.com, found by the hosted
# verification of 26F.6, 3 Nov): before its first capture it gets a bounded wait for its words, and one that never shows any is reported, not audited.
RENDER_WAIT_S = 20.0
RENDER_SETTLE_S = 5.0  # a later screen of a guarded walk: the same wait, shorter, and never the run's to end
RENDER_STILL_S = 3.0  # once the floor is cleared, at most this long for the words to hold still (a ticker never does)
RENDER_MIN_TEXT = 40  # visible characters that make a page a page rather than a spinner
RENDER_MIN_ELEMENTS = 50  # or this many elements: an image-led page has few words
RENDER_POLL_MS = 500
# A built tree must show as ink: www.flysafair.co.za (3 Nov) keeps a loader over the page while its content arrives, so a capture's screenshot was a grey
# field with the cookie banner (2 % of a thumbnail off its dominant colour) while its tree held 257 nodes; the sparsest real page seen (a bot wall) is 17 %.
RENDER_PAINT_ELEMENTS = 50
RENDER_PAINT_INK = 0.05
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


async def ink(png: bytes) -> float:
    """The share of a 160×90 thumbnail of the screenshot that is not its dominant colour: a loader overlay or a blank page is near zero."""
    small = Image.open(io.BytesIO(png)).convert("RGB").resize((160, 90))
    data = small.tobytes()
    counts = Counter(data[i:i + 3] for i in range(0, len(data), 3))
    return 1 - counts.most_common(1)[0][1] / (160 * 90)


async def wait_rendered(page: Page, timeout_s: float = RENDER_WAIT_S) -> str | None:
    """Wait, bounded, until the page shows words (or many elements), their count is the same on two polls or has held the floor for
    RENDER_STILL_S, and a big tree shows as ink in the screenshot; None once it has rendered, else one sentence saying it never did, or
    that the address is not a web page.
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
        painted: bool | None = None
        if shown:
            shown_at = shown_at if shown_at is not None else t
            if measure == last or t - shown_at >= RENDER_STILL_S:
                painted = measure[1] < RENDER_PAINT_ELEMENTS or await ink(await page.screenshot()) >= RENDER_PAINT_INK
                if painted:
                    return None
                # a built page nothing of which shows: a loader over it; keep waiting for it to lift
        else:
            shown_at = None  # the page emptied again (a navigation mid-wait): the next document gets its own stillness clock
        last = measure
        if t >= deadline:
            return None if shown and painted is not False else f"the page showed no content after {int(round(timeout_s))} s: a loading screen at most"
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


Box = tuple[float, float, float, float]


def snap_point(x: float, y: float, hit: bool, candidates: list[tuple[Box, str]], pad: float = SNAP_PX) -> dict | None:
    """The correction for a click at (x, y): None when the point already hits a control or no control's box, grown by ``pad``
    on each side, contains it; else {from, to, target} for the nearest such control by edge distance, ``to`` its centre."""
    if hit:
        return None
    best: tuple[float, Box, str] | None = None
    for (left, top, right, bottom), name in candidates:
        if not (left - pad <= x <= right + pad and top - pad <= y <= bottom + pad):
            continue
        d = math.hypot(max(left - x, 0, x - right), max(top - y, 0, y - bottom))
        if best is None or d < best[0]:
            best = (d, (left, top, right, bottom), name)
    if best is None:
        return None
    _, (left, top, right, bottom), name = best
    return {"from": [x, y], "to": [(left + right) / 2, (top + bottom) / 2], "target": name}


async def snap_click(page: Page, action: dict) -> tuple[dict, dict | None]:
    """A click or double-click, moved to the nearest control when it would land on nothing clickable within SNAP_PX of one:
    (the action to run, the correction or None). Anything else, or a page that cannot be read, comes back unchanged."""
    if not isinstance(action, dict) or action.get("type") not in ("click", "double_click"):
        return action, None
    try:
        x, y = float(action["x"]), float(action["y"])
        info = await page.evaluate(_SNAP_JS, [x, y, INTERACTIVE])
    except Exception:
        return action, None
    boxes = [((float(b[0]), float(b[1]), float(b[2]), float(b[3])), str(name)) for b, name in (info or {}).get("boxes") or []]
    snap = snap_point(x, y, bool((info or {}).get("hit")), boxes)
    if snap is None:
        return action, None
    return {**action, "x": snap["to"][0], "y": snap["to"][1]}, snap


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
