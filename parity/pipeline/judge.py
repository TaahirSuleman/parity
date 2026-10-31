"""Judge: a separate model call rates a verified finding. Fails closed.

An unparseable answer, or an ``is_barrier`` that is not a strict bool, becomes ``needs_review``
for a human. The model never sees labels; it sees the verified evidence only.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from parity.meta.client import MetaError
from parity.meta.images import png_to_data_url
from parity.pipeline.comparator import tree_block
from parity.store.models import Capture, Finding, Judgement, Severity, WcagRef

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).resolve().parent.parent / "meta" / "prompts" / "judge.txt").read_text()
FALLBACK_MODEL = "muse-spark-1.3"
# Reasoning tokens count against this budget; 1500 was exhausted by reasoning alone with no answer left.
MAX_OUTPUT_TOKENS = 6000
VALID_SEVERITIES = {s.value for s in Severity} - {Severity.needs_review.value}


def evidence_block(finding: Finding) -> str:
    b = finding.bbox
    sr = f'{finding.sr_role}, "{finding.sr_name}"' if finding.sr_role or finding.sr_name else "nothing (no accessibility node)"
    lines = [
        f"What a sighted user sees: {finding.sighted_text}",
        f"What the screen reader announces: {sr}",
        f"Element box on the 0-1000 grid: [{b.x_min}, {b.y_min}, {b.x_max}, {b.y_max}]",
        f"Element HTML: {(finding.element.outer_html or '')[:600]}",
    ]
    if finding.why_it_matters:
        lines.append(f"Why the comparator flagged it: {finding.why_it_matters}")
    return "\n".join(lines)


def parse_judgement(text: str) -> Judgement:
    needs_review = Judgement(is_barrier=None, severity=Severity.needs_review)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return needs_review
    if not isinstance(data, dict) or not isinstance(data.get("is_barrier"), bool):
        return needs_review
    severity = str(data.get("severity") or "").strip().lower()
    if severity not in VALID_SEVERITIES:
        return needs_review
    wcag: list[WcagRef] = []
    for item in data.get("wcag") or []:
        if isinstance(item, dict) and item.get("sc"):
            wcag.append(WcagRef(sc=str(item["sc"]).strip(), name=str(item.get("name") or "").strip()))
    return Judgement(is_barrier=data["is_barrier"], severity=Severity(severity), wcag=wcag, impact=str(data.get("impact") or "").strip())


async def judge(client, finding: Finding, capture: Capture, run_id: str, *, model: str, effort: str = "medium") -> Judgement:
    text = (PROMPT + "\n\nEVIDENCE:\n" + evidence_block(finding)
            + "\n\nACCESSIBILITY TREE of the whole screen (role, name, box on the 0-1000 grid), so you can judge what else a screen-reader user gets:\n"
            + tree_block(capture))
    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    if capture.screenshot_png:
        content.append({"type": "input_image", "image_url": png_to_data_url(capture.screenshot_png)})

    async def call(model_id: str):
        body = {"model": model_id, "reasoning": {"effort": effort}, "text": {"format": {"type": "json_object"}},
                "max_output_tokens": MAX_OUTPUT_TOKENS, "input": [{"role": "user", "content": content}]}
        return await client.responses(body, stage="judge", run_id=run_id, step_index=finding.step_index)

    fallback = False
    try:
        resp = await call(model)
        used = model
    except MetaError as exc:
        if model == FALLBACK_MODEL:
            raise
        log.warning("judge model %s failed (request %s); falling back to %s", model, exc.request_id, FALLBACK_MODEL)
        resp = await call(FALLBACK_MODEL)
        used, fallback = FALLBACK_MODEL, True
    judgement = parse_judgement(resp.text)
    if judgement.severity == Severity.needs_review:
        log.warning("judge answer unparseable or unsure for finding %s; needs human review", finding.id)
    status = str(resp.raw.get("status") or "completed")
    if status != "completed":
        log.warning("judge response %s for finding %s: %s", status, finding.id, resp.raw.get("incomplete_details"))
    judgement.model_meta = {"model": used, "fallback": fallback, "request_id": resp.request_id, "response_id": resp.response_id,
                            "status": status, "incomplete_reason": (resp.raw.get("incomplete_details") or {}).get("reason")}
    return judgement
