"""Re-audit: the patched page is reloaded under its real URL and code decides whether the gap closed."""

import json

from parity.meta.fake import FakeMetaClient
from parity.pipeline.reaudit import reaudit
from parity.store.models import Fix

MODEL = "muse-spark-1.3-contributor"
GOOD_AFTER = '<button id="f5" class="btn">Pay R1,249</button>'
BAD_AFTER = '<button id="f5" class="btn" aria-label="Submit">Pay R1,249</button>'
HIDDEN_AFTER = '<button id="f5" class="btn" aria-hidden="true">Pay R1,249</button>'


def comparator_answer(findings: list[dict]) -> dict:
    return {"id": "resp_cmp", "_request_id": "req-cmp", "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"findings": findings})}]}],
            "usage": {"input_tokens": 10, "output_tokens": 5}}


def hero_flag(finding) -> dict:
    return {"what_sighted_user_sees": "Pay R1,249", "screen_reader_role": "button", "screen_reader_name": "Submit",
            "why_it_matters": "price hidden", "bbox": finding.bbox.model_dump()}


async def run(hero, page, store_url, tmp_path, after_html: str, comparator_findings: list[dict]):
    cap, finding = hero
    url = store_url + "checkout.html"
    await page.goto(url)
    html = await page.content()
    fix = Fix(before_html=finding.element.outer_html or "", after_html=after_html, diff="")
    fake = FakeMetaClient(tmp_path, stage_defaults={"comparator": comparator_answer(comparator_findings)})

    async def factory():
        return page

    result = await reaudit(fake, factory, html, url, fix, finding, run_id="r1", model=MODEL)
    return result, fake, url


async def test_reaudit_hero_gap_closed(hero, page, store_url, tmp_path):
    result, fake, url = await run(hero, page, store_url, tmp_path, GOOD_AFTER, [])
    assert result.gap_closed is True
    assert result.sr_name_before == "Submit" and result.sr_name_after == "Pay R1,249"
    assert result.comparator_still_flags is False
    assert len(fake.calls) == 1  # one comparator call as a second signal: no seer, no judge
    assert page.url == url  # reloaded under its real URL, so relative assets and links still resolve


async def test_reaudit_bad_fix_not_closed(hero, page, store_url, tmp_path):
    """A fix that keeps aria-label="Submit" leaves the name unchanged: not closed, and the comparator still flags it."""
    _, finding = hero
    result, _, _ = await run(hero, page, store_url, tmp_path, BAD_AFTER, [hero_flag(finding)])
    assert result.gap_closed is False and result.sr_name_after == "Submit"
    assert result.comparator_still_flags is True


async def test_reaudit_element_gone_from_tree_is_not_closed(hero, page, store_url, tmp_path):
    """A fix that hides the element from the tree is not a fix: no name is worse than a wrong one."""
    result, _, _ = await run(hero, page, store_url, tmp_path, HIDDEN_AFTER, [])
    assert result.gap_closed is False and result.sr_name_after == ""


async def test_reaudit_serves_the_patched_page_even_with_a_fragment_url(hero, page, store_url, tmp_path):
    """The agent clicks in-page anchors; a captured URL with #terms must still get the patched document."""
    cap, finding = hero
    url = store_url + "checkout.html#terms"
    await page.goto(url)
    html = await page.content()
    fix = Fix(before_html=finding.element.outer_html or "", after_html=GOOD_AFTER, diff="")
    fake = FakeMetaClient(tmp_path, stage_defaults={"comparator": comparator_answer([])})

    async def factory():
        return page

    result = await reaudit(fake, factory, html, url, fix, finding, run_id="r1", model=MODEL)
    assert result.gap_closed is True and result.sr_name_after == "Pay R1,249"


async def test_patched_page_cannot_reach_the_api(page, store_url):
    """Defence in depth: whatever a snippet smuggles past the validator, the re-audit page cannot call the API."""
    from parity.pipeline.reaudit import load_patched

    html = "<!doctype html><html><body><p>x</p><script>fetch('/api/health').then(r => { window.__api = r.status }).catch(() => { window.__api = 'blocked' })</script></body></html>"
    async with load_patched(page, store_url + "checkout.html", html):
        await page.wait_for_function("() => window.__api !== undefined")
        assert await page.evaluate("() => window.__api") == "blocked"
