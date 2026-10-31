"""Fixer: Spark proposes a patched element; code validates it, applies it once and computes the diff (spec §6, D4).

The model never edits the page. It answers with one replacement snippet for the flagged element;
code checks the snippet keeps the tag and adds no script, splices it into the captured page source
exactly once and writes the unified diff. The re-audit decides whether the gap actually closed.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from parity.meta.images import png_to_data_url
from parity.pipeline.judge import evidence_block
from parity.store.models import Capture, Element, Finding, Fix

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).resolve().parent.parent / "meta" / "prompts" / "fixer.txt").read_text()
MAX_OUTPUT_TOKENS = 6000
FORBIDDEN = re.compile(r"<script\b|\son[a-z]+\s*=|javascript:", re.IGNORECASE)


class FixNotApplied(Exception):
    """The element's outer HTML was not found exactly once in the page source."""


class FixRejected(Exception):
    """The model's snippet failed validation: tag changed, script added, or no usable answer."""


class _FirstTag(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.first: str | None = None

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if self.first is None:
            self.first = tag

    def handle_startendtag(self, tag: str, attrs: Any) -> None:
        self.handle_starttag(tag, attrs)


def first_tag(html: str) -> str | None:
    parser = _FirstTag()
    parser.feed(html or "")
    parser.close()
    return parser.first


def validate_snippet(before_html: str, after_html: str) -> None:
    """The snippet must still be the same kind of element and must not smuggle in behaviour."""
    if not after_html.strip():
        raise FixRejected("empty snippet")
    if FORBIDDEN.search(after_html):
        raise FixRejected("snippet adds script or an inline event handler")
    before_tag, after_tag = first_tag(before_html), first_tag(after_html)
    if after_tag is None:
        raise FixRejected("snippet is not an HTML element")
    if before_tag != after_tag:
        raise FixRejected(f"snippet changes the element's tag from <{before_tag}> to <{after_tag}>")


def apply_fix(page_html: str, element: Element, after_html: str) -> str:
    before = element.outer_html or ""
    found = page_html.count(before) if before else 0
    if found != 1:
        raise FixNotApplied(f"element HTML found {found} times in the page source, expected exactly once")
    return page_html.replace(before, after_html, 1)


def unified_diff(before: str, after: str, path: str) -> str:
    """A git-style patch (a/ b/ prefixes) between two versions of one file."""
    before, after = (s if s.endswith("\n") else s + "\n" for s in (before, after))
    lines = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}")
    return "".join(lines)


def patch_path(url: str) -> str:
    """Repo-relative file the patch applies to; the demo store is served from store/ (also for file:// captures)."""
    path = urlparse(url).path
    if "/store/" in path:
        return "store/" + path.split("/store/", 1)[1]
    return path.lstrip("/") or "index.html"


def parse_fix(text: str) -> tuple[str, str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FixRejected(f"answer is not JSON: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("after_html"), str):
        raise FixRejected("answer has no after_html")
    return data["after_html"].strip(), str(data.get("explanation") or "").strip()


async def propose_fix(client, finding: Finding, capture: Capture, run_id: str, *, model: str, effort: str = "medium") -> Fix:
    before_html = finding.element.outer_html or ""
    if not before_html:
        raise FixRejected("the finding's element has no HTML to patch")
    text = PROMPT + "\n\nEVIDENCE:\n" + evidence_block(finding)
    if finding.judgement and finding.judgement.impact:
        text += f"\nJudge's note on the impact: {finding.judgement.impact}"
    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    if capture.screenshot_png:
        content.append({"type": "input_image", "image_url": png_to_data_url(capture.screenshot_png)})
    body = {"model": model, "reasoning": {"effort": effort}, "text": {"format": {"type": "json_object"}},
            "max_output_tokens": MAX_OUTPUT_TOKENS, "input": [{"role": "user", "content": content}]}
    resp = await client.responses(body, stage="fixer", run_id=run_id, step_index=finding.step_index)
    after_html, explanation = parse_fix(resp.text)
    validate_snippet(before_html, after_html)
    path = patch_path(capture.url)
    if capture.html:
        diff = unified_diff(capture.html, apply_fix(capture.html, finding.element, after_html), path)
    else:  # no page source captured: the diff covers the element alone
        diff = unified_diff(before_html, after_html, path)
    status = str(resp.raw.get("status") or "completed")
    if status != "completed":
        log.warning("fixer response %s for finding %s: %s", status, finding.id, resp.raw.get("incomplete_details"))
    return Fix(before_html=before_html, after_html=after_html, diff=diff, explanation=explanation,
               model_meta={"model": model, "request_id": resp.request_id, "response_id": resp.response_id, "status": status})
