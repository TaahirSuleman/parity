"""Comparator: Spark compares what a sighted user sees with the accessibility tree and proposes candidates.

Candidates are proposals only; the Verifier (code) decides. Two ablation switches drop the
screenshot or the tree so the eval can measure what each input contributes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from parity.meta.images import png_to_data_url
from parity.pipeline.seer import parse_bbox
from parity.pipeline.verifier import NOT_ANNOUNCED
from parity.store.models import AxNode, Candidate, Capture, Percept

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).resolve().parent.parent / "meta" / "prompts" / "comparator.txt").read_text()
# Containers announce themselves, not their contents; leave them out of the tree the model compares against.
TREE_SKIP_ROLES = {"banner", "main", "region", "navigation", "contentinfo", "complementary", "paragraph", "LabelText", "section"}


def _box_list(node: AxNode) -> list[int] | None:
    return [node.bbox.x_min, node.bbox.y_min, node.bbox.x_max, node.bbox.y_max] if node.bbox else None


def tree_block(capture: Capture) -> str:
    rows = [{"role": n.role, "name": n.name, "bbox": _box_list(n)} for n in capture.ax_nodes if n.role not in TREE_SKIP_ROLES]
    return json.dumps(rows, ensure_ascii=False)


def silent_block(capture: Capture) -> str:
    rows = [{"element": n.role.removeprefix("silent:"), "bbox": _box_list(n)} for n in capture.silent_nodes]
    return json.dumps(rows, ensure_ascii=False)


def percept_block(percepts: list[Percept]) -> str:
    rows = [{"visible_text": p.visible_text, "kind": p.kind, "bbox": [p.bbox.x_min, p.bbox.y_min, p.bbox.x_max, p.bbox.y_max]} for p in percepts]
    return json.dumps(rows, ensure_ascii=False)


def build_prompt(capture: Capture, percepts: list[Percept], feedback: list[str] | None, *, use_tree: bool, use_screenshot: bool = True) -> str:
    inputs: list[str] = []
    if use_screenshot:
        inputs.append("- a screenshot: what a sighted user sees;")
    if percepts:
        inputs.append("- WHAT A SIGHTED USER SEES: visible elements with their text and boxes (0-1000 grid), produced from the screenshot;")
    if use_tree:
        inputs.append("- the ACCESSIBILITY TREE: what a screen-reader user gets, as role + accessible name per element with boxes on the same grid;")
        inputs.append("- SILENT ELEMENTS: elements that render pixels but have no accessibility entry at all.")
        sr_instruction = ('copy the role and the accessible name EXACTLY as they appear in the ACCESSIBILITY TREE for that element. '
                          'If the element has no entry in the tree (it is silent), set both to "".')
    else:
        sr_instruction = ('the role and accessible name a screen reader would announce for that element as far as you can tell from the page; '
                          'set both to "" if nothing would be announced.')
    parts = [PROMPT.replace("{inputs}", "\n".join(inputs)).replace("{sr_instruction}", sr_instruction)]
    if percepts:
        parts.append("WHAT A SIGHTED USER SEES:\n" + percept_block(percepts))
    if use_tree:
        parts.append("ACCESSIBILITY TREE:\n" + tree_block(capture))
        parts.append("SILENT ELEMENTS:\n" + silent_block(capture))
    if feedback:
        parts.append("VERIFIER FEEDBACK on your previous attempt (fix these, keep the findings that were fine):\n- " + "\n- ".join(feedback))
    return "\n\n".join(parts)


def parse_candidates(text: str, step_index: int, attempt: int = 1) -> list[Candidate]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out: list[Candidate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sighted = str(item.get("what_sighted_user_sees") or "").strip()
        if not sighted:
            continue
        role = str(item.get("screen_reader_role") or "").strip()
        name = str(item.get("screen_reader_name") or "").strip()
        quote = NOT_ANNOUNCED if not role and not name else f'{role}, "{name}"'
        out.append(Candidate(
            step_index=step_index, sighted_text=sighted, sr_quote=quote,
            why_it_matters=str(item.get("why_it_matters") or "").strip(), bbox=parse_bbox(item.get("bbox")), attempt=attempt,
        ))
    return out


async def compare(
    client, capture: Capture, percepts: list[Percept], run_id: str, feedback: list[str] | None = None, *,
    model: str, effort: str = "medium", use_screenshot: bool = True, use_tree: bool = True,
) -> list[Candidate]:
    attempt = 2 if feedback else 1
    content: list[dict[str, Any]] = [{"type": "input_text", "text": build_prompt(capture, percepts, feedback, use_tree=use_tree, use_screenshot=use_screenshot)}]
    if use_screenshot:
        content.append({"type": "input_image", "image_url": png_to_data_url(capture.screenshot_png)})
    body = {
        "model": model, "reasoning": {"effort": effort}, "text": {"format": {"type": "json_object"}},
        "max_output_tokens": 6000, "input": [{"role": "user", "content": content}],
    }
    resp = await client.responses(body, stage="comparator", run_id=run_id, step_index=capture.step_index)
    candidates = parse_candidates(resp.text, capture.step_index, attempt)
    if not candidates:
        log.warning("comparator returned no parseable candidates (run %s step %d attempt %d)", run_id, capture.step_index, attempt)
    return candidates
