"""Fixer: the model proposes a patched element; code validates it, applies it once and computes the diff."""

import json
import re
from pathlib import Path

import pytest

from parity.meta.fake import FakeMetaClient
from parity.pipeline.fixer import FixNotApplied, FixRejected, apply_fix, propose_fix, unified_diff
from parity.store.models import Element
from tests.test_runner import META, stage_defaults

BEFORE = '<button id="f5" class="btn" aria-label="Submit"><img alt="" src="x.svg"></button>'
AFTER = '<button id="f5" class="btn">Pay R1,249</button>'
MODEL = "muse-spark-1.3-contributor"


def element(outer_html: str = BEFORE) -> Element:
    return Element(backend_id=1, css_path="#f5", outer_html=outer_html, dom_id="f5")


def response_with(payload) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {"id": "resp_fix", "_request_id": "req-fix", "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}], "usage": {"input_tokens": 10, "output_tokens": 5}}


def test_apply_fix_replaces_once():
    page = f"<main><p>a</p>{BEFORE}<p>b</p></main>"
    assert apply_fix(page, element(), AFTER) == f"<main><p>a</p>{AFTER}<p>b</p></main>"


def test_apply_fix_raises_when_absent():
    with pytest.raises(FixNotApplied):
        apply_fix("<main><p>nothing here</p></main>", element(), AFTER)
    with pytest.raises(FixNotApplied):  # twice is as bad as never: the patch would be ambiguous
        apply_fix(f"<main>{BEFORE}{BEFORE}</main>", element(), AFTER)


def test_patch_path_is_repo_relative():
    from parity.pipeline.fixer import patch_path

    assert patch_path("http://127.0.0.1:8080/store/checkout.html") == "store/checkout.html"
    assert patch_path("file:///Users/me/parity/store/checkout.html") == "store/checkout.html"  # recorded captures
    assert patch_path("https://example.com/shop/cart") == "shop/cart" and patch_path("https://example.com/") == "index.html"


def test_unified_diff_is_a_git_style_patch():
    diff = unified_diff(f"<main>\n{BEFORE}\n</main>\n", f"<main>\n{AFTER}\n</main>\n", "store/checkout.html")
    assert diff.startswith("--- a/store/checkout.html\n+++ b/store/checkout.html\n")
    assert f"-{BEFORE}" in diff and f"+{AFTER}" in diff


async def test_fix_hero_removes_aria_label_or_sets_matching_name(hero, page, store_url):
    """Recorded Spark answer on the hero: the patched button's accessible name is the visible price."""
    cap, finding = hero
    await page.goto(store_url + "checkout.html")
    cap.html = await page.content()
    fake = FakeMetaClient(META, stage_defaults=stage_defaults())
    fix = await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)
    assert fix.before_html == finding.element.outer_html and fix.after_html != fix.before_html
    assert fix.diff.startswith("--- a/store/checkout.html\n+++ b/store/checkout.html\n")
    assert re.search(r'^-\s*<button id="f5" class="btn" aria-label="Submit"', fix.diff, re.M) and re.search(r"^\+.*Pay R1,249", fix.diff, re.M)
    assert fix.model_meta["model"] == MODEL and fix.model_meta["request_id"]
    body = fake.calls[-1]
    assert body["text"] == {"format": {"type": "json_object"}} and "Pay R1,249" in body["input"][0]["content"][0]["text"]
    await page.set_content(apply_fix(cap.html, finding.element, fix.after_html))
    assert await page.get_by_role("button", name=re.compile(r"Pay R1,249")).count() == 1


async def test_fix_rejected_when_tag_changes(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with({"after_html": '<a id="f5" href="#">Pay R1,249</a>', "explanation": "link"}))
    with pytest.raises(FixRejected):
        await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)


async def test_fix_rejected_when_snippet_adds_script_or_is_unparseable(hero, tmp_path):
    cap, finding = hero
    for answer in ('<button id="f5" onclick="x()">Pay</button>', '<button id="f5">Pay<script>1</script></button>'):
        fake = FakeMetaClient(tmp_path, default=response_with({"after_html": answer, "explanation": ""}))
        with pytest.raises(FixRejected):
            await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)
    fake = FakeMetaClient(tmp_path, default=response_with("not json at all"))
    with pytest.raises(FixRejected):
        await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)
