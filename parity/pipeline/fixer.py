"""Fixer: Spark proposes a patched element; code validates it, splices it into the served page source
and computes the diff (spec §6, D4).

The model never edits the page. It answers with one replacement snippet for the flagged element;
code parses the snippet (one balanced root, same tag and id, no script, handlers or active URLs),
locates the element in the document as served (by id, so the browser's re-serialised DOM never
has to match the source text), splices it once and writes a git-style unified diff that applies to
the file it names. The re-audit decides whether the gap actually closed.
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
from parity.pipeline.capture import MAX_OUTER_HTML
from parity.store.models import Capture, Element, Finding, Fix

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).resolve().parent.parent / "meta" / "prompts" / "fixer.txt").read_text()
MAX_OUTPUT_TOKENS = 6000
MAX_FIX_HTML = 4000  # an element larger than this is not patched: the model would have to invent what it cannot see
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
DENIED_TAGS = {"script", "iframe", "frame", "frameset", "object", "embed", "base", "meta", "link", "style", "form", "template", "noscript"}
URL_ATTRS = {"href", "src", "action", "formaction", "data", "poster", "cite", "background", "ping", "xlink:href"}
ACTIVE_SCHEMES = ("javascript:", "vbscript:", "data:text/html", "data:text/javascript", "data:application")


class FixNotApplied(Exception):
    """The element could not be located exactly once in the page source."""


class FixRejected(Exception):
    """The model's snippet failed validation, or the element cannot be patched safely."""


# --- the page source: where is each element? -------------------------------------------------------

class _Index(HTMLParser):
    """Spans of every element in a document, by source offset, plus the start offsets of every id."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = [0] + [i + 1 for i, c in enumerate(source) if c == "\n"]
        self.spans: dict[int, int] = {}
        self.ids: dict[str, list[int]] = {}
        self.tags: dict[int, str] = {}
        self._open: list[tuple[int, str]] = []

    def _offset(self) -> int:
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start = self._offset()
        self.tags[start] = tag
        for name, value in attrs:
            if name == "id" and value:
                self.ids.setdefault(value, []).append(start)
        if tag in VOID:
            self.spans[start] = start + len(self.get_starttag_text() or "")
        else:
            self._open.append((start, tag))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start = self._offset()
        self.tags[start] = tag
        for name, value in attrs:
            if name == "id" and value:
                self.ids.setdefault(value, []).append(start)
        self.spans[start] = start + len(self.get_starttag_text() or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID or not any(t == tag for _, t in self._open):
            return
        close = self._offset()
        end = self.source.find(">", close)
        end = len(self.source) if end < 0 else end + 1
        while self._open:  # HTML is lenient: an end tag closes any elements left open inside it
            start, open_tag = self._open.pop()
            self.spans[start] = end
            if open_tag == tag:
                break

    def finish(self) -> None:
        self.close()
        for start, _ in self._open:
            self.spans[start] = len(self.source)
        self._open.clear()


def index_source(source: str) -> _Index:
    idx = _Index(source)
    idx.feed(source)
    idx.finish()
    return idx


def locate_in_source(source: str, element: Element) -> tuple[int, int] | None:
    """(start, end) of the element in the served source: by id when it is unique, else by exact serialised HTML."""
    if element.dom_id:
        idx = index_source(source)
        starts = idx.ids.get(element.dom_id, [])
        if len(starts) != 1 or starts[0] not in idx.spans:
            return None
        return starts[0], idx.spans[starts[0]]
    if element.outer_html and source.count(element.outer_html) == 1:
        start = source.index(element.outer_html)
        return start, start + len(element.outer_html)
    return None


def apply_fix(page_html: str, element: Element, after_html: str) -> str:
    loc = locate_in_source(page_html, element)
    if loc is None:
        raise FixNotApplied(f"element {element.dom_id or element.css_path!r} not found exactly once in the page source")
    return page_html[:loc[0]] + after_html + page_html[loc[1]:]


def combine_patch(base: str, fixes: list[tuple[Element, str]], path: str) -> str:
    """All approved fixes for one file, spliced into one base and diffed once, so the patch applies as a whole."""
    located: list[tuple[int, int, str]] = []
    for element, after_html in fixes:
        loc = locate_in_source(base, element)
        if loc is None:
            raise FixNotApplied(f"element {element.dom_id or element.css_path!r} not found exactly once in the page source")
        located.append((loc[0], loc[1], after_html))
    located.sort()
    for (_, end_a, _), (start_b, _, _) in zip(located, located[1:]):
        if start_b < end_a:
            raise FixNotApplied("two fixes overlap in the page source")
    patched = base
    for start, end, after_html in reversed(located):  # splice from the end so earlier offsets stay valid
        patched = patched[:start] + after_html + patched[end:]
    return unified_diff(base, patched, path)


def unified_diff(before: str, after: str, path: str) -> str:
    """A git-style patch (a/ b/ prefixes), honest about a missing newline at the end of the file."""
    lines = list(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"))
    out: list[str] = []
    for i, line in enumerate(lines):
        if i >= 2 and not line.endswith("\n"):
            out.append(line + "\n\\ No newline at end of file\n")
        else:
            out.append(line)
    return "".join(out)


def patch_path(url: str) -> str:
    """Repo-relative file the patch applies to; the demo store is served from store/ (also for file:// captures)."""
    path = urlparse(url).path
    if "/store/" in path:
        return "store/" + path.split("/store/", 1)[1]
    return path.lstrip("/") or "index.html"


# --- the snippet: is it one honest element? ---------------------------------------------------------

class _Snippet(HTMLParser):
    """One snippet, parsed: its root element, every element's attributes, and anything outside the root."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: str | None = None
        self.root_attrs: dict[str, str | None] = {}
        self.elements: list[tuple[str, list[tuple[str, str | None]]]] = []
        self.problems: list[str] = []
        self._depth = 0
        self._closed = False

    def _enter(self, tag: str, attrs: list[tuple[str, str | None]], void: bool) -> None:
        if self._closed:
            self.problems.append("content after the root element")
        if self.root is None:
            self.root, self.root_attrs = tag, dict(attrs)
            if void:
                self._closed = True
        elif not void:
            pass
        self.elements.append((tag, attrs))
        if not void:
            self._depth += 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._enter(tag, attrs, tag in VOID)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._enter(tag, attrs, True)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        self._depth -= 1
        if self._depth < 0:
            self.problems.append("stray end tag")
        elif self._depth == 0:
            self._closed = True

    def handle_data(self, data: str) -> None:
        if data.strip() and (self.root is None or self._closed):
            self.problems.append("text outside the root element")

    def finish(self) -> None:
        self.close()
        if self.root is None:
            self.problems.append("no element")
        elif not self._closed or self._depth != 0:
            self.problems.append("unclosed element")


def parse_snippet(html: str) -> _Snippet:
    snippet = _Snippet()
    snippet.feed(html or "")
    snippet.finish()
    return snippet


def _active_url(value: str | None) -> bool:
    cleaned = re.sub(r"[\s\x00-\x1f]+", "", value or "").lower()
    return cleaned.startswith(ACTIVE_SCHEMES)


def validate_snippet(before_html: str, after_html: str) -> None:
    """The snippet must be one balanced element of the same tag and id, with no behaviour smuggled in."""
    if not after_html.strip():
        raise FixRejected("empty snippet")
    before, after = parse_snippet(before_html), parse_snippet(after_html)
    if after.problems:
        raise FixRejected(f"snippet is not one element: {after.problems[0]}")
    if before.root != after.root:
        raise FixRejected(f"snippet changes the element's tag from <{before.root}> to <{after.root}>")
    if before.root_attrs.get("id") and after.root_attrs.get("id") != before.root_attrs["id"]:
        raise FixRejected(f"snippet is for element #{after.root_attrs.get('id') or '?'}, not #{before.root_attrs['id']}")
    kept_handlers = {(n, v) for _, attrs in before.elements for n, v in attrs if n.startswith("on")}
    ids = [v for _, attrs in after.elements for n, v in attrs if n == "id"]
    if len(ids) != len(set(ids)):
        raise FixRejected("snippet repeats an id")
    for tag, attrs in after.elements:
        if tag in DENIED_TAGS:
            raise FixRejected(f"snippet adds a <{tag}> element")
        for name, value in attrs:
            if name.startswith("on") and (name, value) not in kept_handlers:
                raise FixRejected(f"snippet adds an inline handler ({name})")
            if name == "srcdoc":
                raise FixRejected("snippet uses srcdoc")
            if name in URL_ATTRS and _active_url(value):
                raise FixRejected(f"snippet points {name} at an active URL")


# --- the model call ----------------------------------------------------------------------------------

def parse_fix(text: str) -> tuple[str, str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FixRejected(f"answer is not JSON: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("after_html"), str):
        raise FixRejected("answer has no after_html")
    return data["after_html"].strip(), str(data.get("explanation") or "").strip()


def evidence_block(finding: Finding, before_html: str) -> str:
    b = finding.bbox
    sr = f'{finding.sr_role}, "{finding.sr_name}"' if finding.sr_role or finding.sr_name else "nothing (no accessibility node)"
    lines = [
        f"What a sighted user sees: {finding.sighted_text}",
        f"What the screen reader announces: {sr}",
        f"Element box on the 0-1000 grid: [{b.x_min}, {b.y_min}, {b.x_max}, {b.y_max}]",
        f"Element HTML (complete, as served):\n{before_html}",
    ]
    if finding.why_it_matters:
        lines.append(f"Why the comparator flagged it: {finding.why_it_matters}")
    if finding.judgement and finding.judgement.impact:
        lines.append(f"Judge's note on the impact: {finding.judgement.impact}")
    return "\n".join(lines)


async def propose_fix(client, finding: Finding, capture: Capture, run_id: str, *, model: str, effort: str = "medium") -> Fix:
    source = capture.html or ""
    loc = locate_in_source(source, finding.element) if source else None
    if loc is not None:
        before_html = source[loc[0]:loc[1]]
    else:
        before_html = finding.element.outer_html or ""
        if not before_html:
            raise FixRejected("the finding's element has no HTML to patch")
        if len(before_html) >= MAX_OUTER_HTML:
            raise FixRejected("the element's HTML was truncated at capture and it was not found in the page source; not patched")
    if len(before_html) > MAX_FIX_HTML:
        raise FixRejected(f"the element's HTML is {len(before_html)} characters, above {MAX_FIX_HTML}; too large to patch safely")

    text = PROMPT + "\n\nEVIDENCE:\n" + evidence_block(finding, before_html)
    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    if capture.screenshot_png:
        content.append({"type": "input_image", "image_url": png_to_data_url(capture.screenshot_png)})
    body = {"model": model, "reasoning": {"effort": effort}, "text": {"format": {"type": "json_object"}},
            "max_output_tokens": MAX_OUTPUT_TOKENS, "input": [{"role": "user", "content": content}]}
    resp = await client.responses(body, stage="fixer", run_id=run_id, step_index=finding.step_index)
    after_html, explanation = parse_fix(resp.text)
    validate_snippet(before_html, after_html)
    path = patch_path(capture.url)
    if loc is not None:
        diff = unified_diff(source, source[:loc[0]] + after_html + source[loc[1]:], path)
    else:  # element only: labelled so nobody mistakes it for a file patch
        diff = unified_diff(before_html, after_html, f"{path} (element {finding.element.dom_id or finding.element.css_path} only; page source unavailable)")
    status = str(resp.raw.get("status") or "completed")
    if status != "completed":
        log.warning("fixer response %s for finding %s: %s", status, finding.id, resp.raw.get("incomplete_details"))
    return Fix(before_html=before_html, after_html=after_html, diff=diff, explanation=explanation,
               model_meta={"model": model, "request_id": resp.request_id, "response_id": resp.response_id, "status": status})
