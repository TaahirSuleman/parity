"""Seer: Spark grounding over the screenshot, listing what a sighted user perceives (with boxes)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from parity.meta.images import png_to_data_url
from parity.store.models import BBox, Capture, Percept

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).resolve().parent.parent / "meta" / "prompts" / "seer.txt").read_text()
KINDS = {"button", "link", "text", "image", "price", "error", "icon", "field", "heading", "other"}


def parse_bbox(raw: Any) -> BBox | None:
    if not isinstance(raw, dict):
        return None
    try:
        return BBox(**{k: int(raw[k]) for k in ("x_min", "y_min", "x_max", "y_max")})
    except (KeyError, TypeError, ValueError):
        return None


def parse_percepts(text: str, step_index: int) -> list[Percept]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = data.get("percepts") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out: list[Percept] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        bbox = parse_bbox(item.get("bbox"))
        visible = str(item.get("visible_text") or "").strip()
        if bbox is None or not visible:
            continue
        kind = str(item.get("kind") or "other").strip().lower()
        out.append(Percept(step_index=step_index, visible_text=visible, kind=kind if kind in KINDS else "other", bbox=bbox))
    return out


async def see(client, capture: Capture, run_id: str, *, model: str, effort: str = "medium") -> list[Percept]:
    body = {
        "model": model,
        "reasoning": {"effort": effort},
        "text": {"format": {"type": "json_object"}},
        "max_output_tokens": 6000,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": PROMPT},
            {"type": "input_image", "image_url": png_to_data_url(capture.screenshot_png)},
        ]}],
    }
    resp = await client.responses(body, stage="seer", run_id=run_id, step_index=capture.step_index)
    percepts = parse_percepts(resp.text, capture.step_index)
    if not percepts:
        log.warning("seer returned no parseable percepts (run %s step %d)", run_id, capture.step_index)
    return percepts
