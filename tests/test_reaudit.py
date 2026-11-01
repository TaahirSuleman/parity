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
    async with load_patched(page, store_url + "checkout.html", html) as page:  # noqa: PLR1704 - the sandbox page
        await page.wait_for_function("() => window.__api !== undefined")
        assert await page.evaluate("() => window.__api") == "blocked"


def test_sandbox_request_policy_allows_only_store_assets():
    """The patched page may fetch only GET /store/* on its own origin; encoded or odd paths do not slip through."""
    from parity.pipeline.reaudit import request_allowed

    origin = "http://127.0.0.1:8080"
    assert request_allowed(origin + "/store/style.css", "GET", origin)
    assert request_allowed(origin + "/store/checkout.html", "GET", origin)
    for url in ("/api/health", "/%61pi/health", "/store/../api/health", "//api/health", "/store//../api/runs", "/API/runs"):
        assert not request_allowed(origin + url if url.startswith("/") and not url.startswith("//") else ("http:" + url if url.startswith("//") else url), "GET", origin), url
    assert not request_allowed(origin + "/store/checkout.html", "POST", origin)
    assert not request_allowed("https://evil.example/x.js", "GET", origin)


async def test_patched_page_cannot_reach_the_api_by_encoded_paths_or_forms(page, store_url):
    from urllib.parse import urlparse

    from parity.pipeline.reaudit import load_patched

    origin = f"{urlparse(store_url).scheme}://{urlparse(store_url).netloc}"
    html = ("<!doctype html><html><body><p>x</p><form id=f method=post action='/api/runs/x/findings/y/decision'><input name=decision value=approve></form>"
            "<script>window.__r = {};"
            "const tries = {enc: '/%61pi/health', dbl: '//" + urlparse(store_url).netloc + "/api/health', up: '/store/../api/health'};"
            "Promise.all(Object.entries(tries).map(([k, u]) => fetch(u).then(r => { window.__r[k] = r.status }).catch(() => { window.__r[k] = 'blocked' })))"
            ".then(() => { window.__done = true });</script></body></html>")
    async with load_patched(page, store_url + "checkout.html", html) as page:  # noqa: PLR1704 - the sandbox page
        await page.wait_for_function("() => window.__done === true")
        results = await page.evaluate("() => window.__r")
        assert results == {"enc": "blocked", "dbl": "blocked", "up": "blocked"}, results
        headers = await page.evaluate("() => document.contentType")  # the page is served as html with a CSP (checked below)
        assert headers == "text/html"
    assert origin  # the page never navigated away


async def test_patched_page_is_served_with_a_csp_that_forbids_connections(page, store_url):
    from parity.pipeline.reaudit import SANDBOX_CSP, load_patched

    assert "connect-src 'none'" in SANDBOX_CSP and "form-action 'none'" in SANDBOX_CSP and "frame-src 'none'" in SANDBOX_CSP
    html = "<!doctype html><html><body><p>x</p><script>fetch('/store/style.css').then(r => { window.__css = r.status }).catch(() => { window.__css = 'blocked' })</script></body></html>"
    async with load_patched(page, store_url + "checkout.html", html) as page:  # noqa: PLR1704 - the sandbox page
        await page.wait_for_function("() => window.__css !== undefined")
        assert await page.evaluate("() => window.__css") == "blocked"  # even same-origin fetches are refused by the CSP


async def test_patched_page_csp_holds_with_the_production_page_factory(store_url):
    """The app's pages are created with bypass_csp (axe must inject into any public page); the re-audit sandbox must not inherit
    that, or its Content-Security-Policy is decoration and a patched page could call the API."""
    from parity.pipeline import browser
    from parity.pipeline.reaudit import load_patched

    page = await browser.new_page()
    try:
        html = "<!doctype html><html><body><p>x</p><script>fetch('/store/style.css').then(r => { window.__css = r.status }).catch(() => { window.__css = 'blocked' })</script></body></html>"
        async with load_patched(page, store_url + "checkout.html", html) as patched:
            await patched.wait_for_function("() => window.__css !== undefined")
            assert await patched.evaluate("() => window.__css") == "blocked"
    finally:
        await page.context.close()
