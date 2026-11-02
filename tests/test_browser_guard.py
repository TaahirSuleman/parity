"""The browser re-checks every request an external page makes (spec §19.3.1, Task 26F.2): a non-public address is aborted
whether it is a subresource or a redirect hop, the page is still captured, the abort is recorded; store runs are untouched."""

from __future__ import annotations

import time

import pytest

from parity import __version__
from parity.pipeline import browser
from parity.pipeline.browser import CRAWL_DELAY_S, LAUNCH_ARGS, RequestGuard, new_page
from parity.pipeline.capture import capture


def judge_for_fixture(host: str) -> bool:
    """The fixture pages live on localhost, which the policy refuses by name; everything else is judged by the real policy."""
    return True if host == "localhost" else browser.host_is_public(host)


async def _external(fixture_url, blocked: list, **kw):
    async def on_blocked(host: str, resource: str, reason: str) -> None:
        blocked.append((host, resource, reason))

    return await new_page(external=True, own_origin="https://parity.example", on_blocked=on_blocked, judge=judge_for_fixture, **kw)


async def test_private_subresource_is_aborted_and_the_page_still_captured(fixture_url):
    blocked: list = []
    page = await _external(fixture_url, blocked)
    try:
        await page.goto(f"{fixture_url}/private-img.html", wait_until="load")
        cap = await capture(page, 0)
    finally:
        await page.context.close()
    assert [b[0] for b in blocked] == ["127.0.0.1"] and blocked[0][1] == "image" and "not a public address" in blocked[0][2]
    assert "Fixture page" in cap.html and any(n.name == "Fine" for n in cap.ax_nodes)  # the page stood; only the image was refused


async def test_redirect_to_the_metadata_address_is_aborted(fixture_url):
    blocked: list = []
    page = await _external(fixture_url, blocked)
    try:
        await page.goto(f"{fixture_url}/bounce.html", wait_until="load")
        cap = await capture(page, 0)
    finally:
        await page.context.close()
    assert [b[0] for b in blocked] == ["169.254.169.254"]  # the first hop (localhost) was allowed; the redirect target was not
    assert "bounce" in cap.html


async def test_hosts_are_judged_once_per_run(fixture_url):
    judged: list[str] = []

    def judge(host: str) -> bool:
        judged.append(host)
        return host == "localhost"

    page = await new_page(external=True, own_origin="https://parity.example", judge=judge)
    try:
        await page.goto(f"{fixture_url}/private-img.html", wait_until="load")
        await page.goto(f"{fixture_url}/private-img.html", wait_until="load")
    finally:
        await page.context.close()
    assert sorted(judged) == ["127.0.0.1", "localhost"]  # each host once, however many requests it got


async def test_external_pages_announce_parity_and_the_policy_page(fixture_url):
    page = await _external(fixture_url, [])
    try:
        await page.goto(f"{fixture_url}/bounce.html", wait_until="load")
    finally:
        await page.context.close()
    assert fixture_url.agents[-1] == f"Parity/{__version__} (+https://parity.example/audit-policy)"


async def test_navigations_are_spaced_by_the_crawl_delay(fixture_url):
    page = await _external(fixture_url, [], delay_s=0.6)
    try:
        t0 = time.monotonic()
        await page.goto(f"{fixture_url}/bounce.html", wait_until="load")
        t1 = time.monotonic()
        await page.goto(f"{fixture_url}/private-img.html", wait_until="load")
        t2 = time.monotonic()
    finally:
        await page.context.close()
    assert t1 - t0 < 0.5 and t2 - t0 >= 0.6  # the first navigation is not delayed; the second starts no sooner than the delay after the first started
    assert CRAWL_DELAY_S == 1.0


async def test_store_runs_are_not_guarded(fixture_url, server_url):
    page = await new_page()
    try:
        await page.goto(f"{fixture_url}/private-img.html", wait_until="load")  # 127.0.0.1 and localhost both load: no guard, no delay
        assert await page.locator("#private").evaluate("img => img.complete") is True
        await page.goto(server_url + "/store/checkout.html", wait_until="load")
    finally:
        await page.context.close()
    assert "Parity" not in fixture_url.agents[-1]


def test_chromium_cannot_resolve_the_metadata_name():
    assert "--host-resolver-rules=MAP metadata.google.internal ~NOTFOUND" in LAUNCH_ARGS


async def test_guard_aborts_non_web_schemes_and_lets_data_urls_through(fixture_url):
    blocked: list = []
    page = await _external(fixture_url, blocked)
    try:
        await page.goto(f"{fixture_url}/bounce.html", wait_until="load")
        await page.evaluate("() => { const i = document.createElement('img'); i.src = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='; document.body.appendChild(i); }")
        await page.wait_for_timeout(100)
    finally:
        await page.context.close()
    assert [b[0] for b in blocked] == ["169.254.169.254"]  # the data: image never reached the guard's refusal path
