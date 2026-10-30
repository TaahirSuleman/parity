"""Deterministic capture of one screen: screenshot, Chrome accessibility tree with boxes, axe-core.

No model is involved. The AX tree is what a screen reader gets; the screenshot is what a
sighted user sees. Both are taken before axe-core is injected, so the page is unmodified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.async_api import CDPSession, Page

from parity.store.models import AxeViolation, AxNode, BBox, Capture

AXE_PATH = Path(__file__).resolve().parent.parent / "vendor" / "axe.min.js"
FILTERED_ROLES = {"generic", "none", "presentation", "StaticText", "InlineTextBox", "LineBreak", "RootWebArea"}
# Roles kept even when they have no accessible name (an unnamed control or image is itself evidence).
KEEP_UNNAMED = {
    "button", "link", "textbox", "searchbox", "image", "checkbox", "radio", "combobox", "listbox",
    "option", "menuitem", "slider", "spinbutton", "switch", "tab", "heading", "canvas", "figure", "graphics-document",
}
MAX_OUTER_HTML = 2000

_ELEMENT_INFO_JS = """
function () {
  const el = this;
  const tag = el.tagName ? el.tagName.toLowerCase() : "";
  function pathOf(node) {
    if (!node || node.nodeType !== 1) return "";
    const t = node.tagName.toLowerCase();
    if (node.id) return t + "#" + CSS.escape(node.id);
    if (t === "body" || t === "html") return t;
    let i = 1, sib = node;
    while ((sib = sib.previousElementSibling)) if (sib.tagName === node.tagName) i++;
    const parent = pathOf(node.parentElement);
    return (parent ? parent + " > " : "") + t + ":nth-of-type(" + i + ")";
  }
  return { outerHTML: (el.outerHTML || "").slice(0, %d), id: el.id || null, cssPath: pathOf(el), tag: tag };
}
""" % MAX_OUTER_HTML


def to_grid(px_box: tuple[int, int, int, int], viewport: tuple[int, int]) -> BBox:
    w, h = viewport
    x0, y0, x1, y1 = px_box
    return BBox(
        x_min=round(x0 * 1000 / w), y_min=round(y0 * 1000 / h), x_max=round(x1 * 1000 / w), y_max=round(y1 * 1000 / h)
    )


async def _box_px(cdp: CDPSession, backend_id: int) -> tuple[int, int, int, int] | None:
    try:
        model = await cdp.send("DOM.getBoxModel", {"backendNodeId": backend_id})
    except Exception:
        return None
    q = model["model"]["border"]  # x1,y1, x2,y2, x3,y3, x4,y4
    xs, ys = q[0::2], q[1::2]
    box = (round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys)))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return box


async def _element_info(cdp: CDPSession, backend_id: int) -> dict[str, Any]:
    try:
        resolved = await cdp.send("DOM.resolveNode", {"backendNodeId": backend_id})
        result = await cdp.send(
            "Runtime.callFunctionOn",
            {"objectId": resolved["object"]["objectId"], "functionDeclaration": _ELEMENT_INFO_JS, "returnByValue": True},
        )
        return result["result"].get("value") or {}
    except Exception:
        return {}


async def _ax_nodes(cdp: CDPSession, viewport: tuple[int, int]) -> list[AxNode]:
    tree = await cdp.send("Accessibility.getFullAXTree")
    nodes: list[AxNode] = []
    for raw in tree.get("nodes", []):
        if raw.get("ignored"):
            continue
        role = (raw.get("role") or {}).get("value") or ""
        name = (raw.get("name") or {}).get("value") or ""
        backend_id = raw.get("backendDOMNodeId")
        if role in FILTERED_ROLES or backend_id is None:
            continue
        if not name and role not in KEEP_UNNAMED:
            continue
        box_px = await _box_px(cdp, backend_id)
        info = await _element_info(cdp, backend_id)
        if box_px is None and not info:
            continue
        nodes.append(
            AxNode(
                backend_id=backend_id, role=role, name=name, css_path=info.get("cssPath", ""), box_px=box_px,
                bbox=to_grid(box_px, viewport) if box_px else None, outer_html=info.get("outerHTML"),
                dom_id=info.get("id"),
            )
        )
    return nodes


async def _backend_id_for(cdp: CDPSession, root_id: int, selector: str) -> int | None:
    try:
        found = await cdp.send("DOM.querySelector", {"nodeId": root_id, "selector": selector})
        if not found.get("nodeId"):
            return None
        described = await cdp.send("DOM.describeNode", {"nodeId": found["nodeId"]})
        return described["node"].get("backendNodeId")
    except Exception:
        return None


async def _axe(page: Page, cdp: CDPSession) -> list[AxeViolation]:
    if await page.evaluate("typeof window.axe === 'undefined'"):
        await page.add_script_tag(path=str(AXE_PATH))
    result = await page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    root = (await cdp.send("DOM.getDocument", {"depth": 0}))["root"]["nodeId"]
    violations: list[AxeViolation] = []
    for v in result.get("violations", []):
        targets: list[str] = []
        backend_ids: list[int] = []
        for node in v.get("nodes", []):
            target = node.get("target") or []
            selector = target[0] if target else ""
            if isinstance(selector, list):
                selector = selector[-1] if selector else ""
            if not selector:
                continue
            targets.append(selector)
            backend_id = await _backend_id_for(cdp, root, selector)
            if backend_id is not None:
                backend_ids.append(backend_id)
        violations.append(AxeViolation(id=v["id"], impact=v.get("impact"), targets=targets, backend_ids=backend_ids))
    return violations


async def capture(page: Page, step_index: int) -> Capture:
    size = page.viewport_size or {"width": 1280, "height": 720}
    viewport = (size["width"], size["height"])
    screenshot = await page.screenshot()
    cdp = await page.context.new_cdp_session(page)
    try:
        await cdp.send("DOM.enable")
        ax_nodes = await _ax_nodes(cdp, viewport)
        axe_violations = await _axe(page, cdp)
    finally:
        await cdp.detach()
    return Capture(
        step_index=step_index, url=page.url, viewport=viewport, screenshot_png=screenshot, ax_nodes=ax_nodes,
        axe_violations=axe_violations,
    )
