"""The Verifier: the only door a finding can pass through. Code, no model.

Five named checks. A candidate becomes a Finding only when all pass. Failed checks produce
feedback written as instructions the comparator can act on; feedback never contains the
accessible names it should have quoted, so the model cannot be handed the answer.
"""

from __future__ import annotations

import re

from parity.store.models import AxNode, BBox, Candidate, Capture, Check, Finding, VerifierResult

NOT_ANNOUNCED = "not announced"
IOU_MIN = 0.2
CENTRE_TOLERANCE = 15
ROLE_ALIASES = {"img": "image", "graphic": "image", "text field": "textbox", "text box": "textbox", "edit": "textbox"}
CHECKS = ("located", "sr_quote_exact", "diverges", "not_axe", "unique")


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().casefold()


def _letters(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", (s or "").casefold())


def announced_in_full(sighted: str, capture: Capture) -> bool:
    """True when the tree's text, read in order, contains everything the sighted text says (a fragment was flagged)."""
    whole = _letters(" ".join(n.name for n in capture.ax_nodes if n.name))
    return bool(_letters(sighted)) and _letters(sighted) in whole


def iou(a: BBox, b: BBox) -> float:
    ix = max(0, min(a.x_max, b.x_max) - max(a.x_min, b.x_min))
    iy = max(0, min(a.y_max, b.y_max) - max(a.y_min, b.y_min))
    inter = ix * iy
    union = a.area + b.area - inter
    return inter / union if union else 0.0


def _centre_inside(bbox: BBox, node: BBox, tol: int = CENTRE_TOLERANCE) -> bool:
    cx, cy = bbox.centre
    return node.x_min - tol <= cx <= node.x_max + tol and node.y_min - tol <= cy <= node.y_max + tol


def locate(bbox: BBox | None, nodes: list[AxNode]) -> AxNode | None:
    """The one node the box points at: best IoU ≥ IOU_MIN, else the smallest node containing the centre."""
    if bbox is None or bbox.area == 0:
        return None
    boxed = [n for n in nodes if n.bbox is not None]
    best = max(boxed, key=lambda n: iou(bbox, n.bbox), default=None)
    if best is not None and iou(bbox, best.bbox) >= IOU_MIN:
        return best
    containing = [n for n in boxed if _centre_inside(bbox, n.bbox)]
    return min(containing, key=lambda n: n.bbox.area, default=None)


MAX_QUOTE_CHARS = 1000


def parse_quote(quote: str) -> tuple[str, str]:
    """'button, "Submit"' -> ('button', 'submit'), both normalised. Role aliases folded."""
    q = (quote or "").strip()[:MAX_QUOTE_CHARS]  # a role and a name are never this long; past it the role regex backtracks quadratically
    m = re.match(r'^\s*([A-Za-z][\w\- ]*?)\s*[,:]\s*(.*)$', q)
    if m:
        role, name = m.group(1), m.group(2)
    else:
        role, name = "", q
    name = name.strip()
    wrapped = re.match(r'^(["“”\'])(.*)(["“”\'])$', name, re.S)
    if wrapped:  # one pair of quote marks around the name; a quote mark inside it (Monitor 27") belongs to the name
        name = wrapped.group(2)
    elif name[:1] in '"“”\'':
        name = name[1:]  # a missing closing quote is forgiven
    name = name.strip()
    role_n = normalise(role)
    return ROLE_ALIASES.get(role_n, role_n), normalise(name)


def verify(candidate: Candidate, capture: Capture, prior: list[Finding]) -> VerifierResult:
    checks: dict[str, Check] = {}
    feedback: list[str] = []
    wants_silence = normalise(candidate.sr_quote) == NOT_ANNOUNCED
    pool = capture.silent_nodes if wants_silence else capture.ax_nodes

    node = locate(candidate.bbox, pool)
    if candidate.bbox is None:
        checks["located"] = Check(passed=False, detail="no box given")
        feedback.append("give the box of the element on the 0-1000 grid (x_min, y_min, x_max, y_max)")
    elif node is None:
        checks["located"] = Check(passed=False, detail="no element at that box")
        feedback.append("the box does not land on an element; tighten it around the exact element you mean")
    else:
        checks["located"] = Check(passed=True, detail=f"{node.role} at {node.css_path}")

    if wants_silence:
        # Announced elements *at* the box: a good overlap, or an element whose centre lies inside the box.
        # Containers around the box (regions, main) do not count; they announce themselves, not the pixels inside.
        announced = [
            n for n in capture.ax_nodes
            if n.bbox and candidate.bbox and n.name and (iou(candidate.bbox, n.bbox) >= IOU_MIN or _centre_inside(n.bbox, candidate.bbox, 0))
        ]
        if announced:
            checks["sr_quote_exact"] = Check(passed=False, detail="an announced element overlaps that box")
            feedback.append("an element inside that box is announced; quote its exact role and accessible name instead of 'not announced'")
        else:
            checks["sr_quote_exact"] = Check(passed=True, detail="no accessibility node with a name at that box")
        checks["diverges"] = Check(passed=bool(normalise(candidate.sighted_text)), detail="visible content has no announcement")
        if not normalise(candidate.sighted_text):
            feedback.append("describe what a sighted user sees at that box")
    else:
        role, name = parse_quote(candidate.sr_quote)
        if node is None:
            checks["sr_quote_exact"] = Check(passed=False, detail="nothing to compare: no element located")
        elif role == normalise(node.role) and name == normalise(node.name):
            checks["sr_quote_exact"] = Check(passed=True, detail="quote equals the accessibility tree entry")
        else:
            checks["sr_quote_exact"] = Check(passed=False, detail="quote differs from the accessibility tree entry")
            feedback.append("quote the exact role and accessible name of the element inside the box, as given in the accessibility tree")
        if node is not None and normalise(candidate.sighted_text) == normalise(node.name):
            checks["diverges"] = Check(passed=False, detail="visible text equals the accessible name")
            feedback.append("the visible text and the accessible name are the same; this is not a divergence, drop it")
        elif node is not None and normalise(node.role) == "text" and normalise(node.name) in normalise(candidate.sighted_text) and announced_in_full(candidate.sighted_text, capture):
            checks["diverges"] = Check(passed=False, detail="the visible text is announced in full by the surrounding text; this node is a fragment of it")
            feedback.append("the screen reader reads that sentence in full; a text fragment inside it is not a divergence, drop it")
        else:
            checks["diverges"] = Check(passed=True, detail="visible text differs from the accessible name")

    if node is not None and any(node.backend_id in v.backend_ids or node.css_path in v.targets for v in capture.axe_violations):
        checks["not_axe"] = Check(passed=False, detail="axe-core already reports this element")
        feedback.append("axe-core already reports this element; only report what rule engines miss")
    else:
        checks["not_axe"] = Check(passed=True, detail="not an axe-core target")

    if node is not None and any(
        f.element.backend_id == node.backend_id or (node.css_path and f.element.css_path == node.css_path) for f in prior
    ):
        checks["unique"] = Check(passed=False, detail="this element already has a finding in this run")
        feedback.append("this element is already reported; do not repeat it")
    else:
        checks["unique"] = Check(passed=True, detail="first finding on this element")

    passed = all(c.passed for c in checks.values())
    return VerifierResult(
        passed=passed, checks=checks, element=node.to_element() if node else None,
        feedback=None if passed else "; ".join(dict.fromkeys(feedback)),
    )
