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


async def test_popup_requests_are_guarded_too(fixture_url):
    """Review C1: a page may open a window; its requests go through the same guard (a page-level route would not see them)."""
    blocked: list = []
    page = await _external(fixture_url, blocked)
    try:
        await page.goto(f"{fixture_url}/popup.html", wait_until="load")
        async with page.context.expect_page() as popup_info:
            await page.click("#open")
        popup = await popup_info.value
        await popup.wait_for_timeout(500)
    finally:
        await page.context.close()
    assert [b[0] for b in blocked] == ["127.0.0.1"] and blocked[0][1] == "document"


async def test_service_workers_are_blocked_on_external_pages(fixture_url):
    """Review C1: a service worker's requests are routed by no handler, so an external context blocks workers: one that phones home
    on install never reaches the server. A store context lets it run (the control that proves the fixture works)."""
    register = "() => navigator.serviceWorker.register('/sw.js').then(() => 'registered', (e) => 'rejected: ' + e.name)"
    page = await _external(fixture_url, [])
    try:
        await page.goto(f"{fixture_url}/sw.html", wait_until="load")
        outcome = await page.evaluate(register)
        await page.wait_for_timeout(1000)
    finally:
        await page.context.close()
    assert "/sw-ping" not in fixture_url.requests, outcome
    control = await new_page()
    try:
        await control.goto(f"{fixture_url}/sw.html", wait_until="load")
        assert await control.evaluate(register) == "registered"
        await control.wait_for_function("() => navigator.serviceWorker.controller !== null || true")
        await control.wait_for_timeout(1000)
    finally:
        await control.context.close()
    assert "/sw-ping" in fixture_url.requests  # the same worker, allowed, did phone home


async def test_public_capture_never_fetches_the_page_a_second_time(fixture_url, server_url):
    """Review C2: served_source re-fetches the page outside the guard (and followed redirects); on a page we do not serve the
    capture keeps the rendered DOM instead, since there is no fixer to need the served source."""
    from parity.pipeline.capture import capture

    page = await _external(fixture_url, [])
    try:
        await page.goto(f"{fixture_url}/bounce.html", wait_until="load")
        before = fixture_url.requests.count("/bounce.html")
        cap = await capture(page, 0, public=True)
    finally:
        await page.context.close()
    assert fixture_url.requests.count("/bounce.html") == before and "Fixture page with a bounce" in cap.html
    store = await new_page()
    try:
        await store.goto(server_url + "/store/checkout.html", wait_until="load")
        cap = await capture(store, 0)
    finally:
        await store.context.close()
    assert 'id="f5"' in cap.html  # the store keeps the served source: the fixer patches it


async def test_a_flood_of_refused_requests_is_reported_once(fixture_url):
    """Review I3: twenty refused requests to one address are one nav.blocked report (with the count kept), not twenty events."""
    blocked: list = []

    async def on_blocked(host: str, resource: str, reason: str) -> None:
        blocked.append(host)

    guard = RequestGuard(on_blocked=on_blocked, judge=judge_for_fixture)
    page = await new_page(external=True, own_origin="https://parity.example", guard=guard)
    try:
        await page.goto(f"{fixture_url}/flood.html", wait_until="load")
        await page.wait_for_function("() => window.done === true", timeout=15000)
    finally:
        await page.context.close()
    assert blocked == ["127.0.0.1"] and guard.counts[("127.0.0.1", "not a public address")] == 20


# QA gate before the 6c merge (the fresh backend review): a 3xx never reaches Chromium, so the browser's own traversal cannot
# land anywhere the guard did not judge; the guard's answer is the only fetch the server ever sees from a run.


async def test_a_main_frame_redirect_is_followed_hop_by_hop_through_the_guard(fixture_url):
    """Review C1: /flip answers 200 to its first request and a redirect to 127.0.0.1/secret to the second. The old guard pre-walked the
    chain and then handed Chromium the 302, whose unrouted follow fetched /flip a second time and landed on the loopback page."""
    import urllib.request

    from parity.pipeline.browser import settle_redirects

    urllib.request.urlopen(f"{fixture_url}/flip-reset")
    fixture_url.requests.clear()
    blocked: list = []
    page = await _external(fixture_url, blocked, delay_s=0)
    try:
        await page.goto(f"{fixture_url}/start-flip", wait_until="load")
        await settle_redirects(page)
        assert page.url == f"{fixture_url}/flip"
        assert "flip first answer" in await page.content()
    finally:
        await page.context.close()
    assert fixture_url.requests.count("/flip") == 1, fixture_url.requests
    assert "/secret" not in fixture_url.requests
    assert blocked == []


async def test_a_subresource_redirect_is_fetched_once_by_the_guard(fixture_url):
    """A redirecting image: the guard walks the chain and answers the browser with the final hop, so nothing is refetched unguarded."""
    fixture_url.requests.clear()
    blocked: list = []
    page = await _external(fixture_url, blocked, delay_s=0)
    try:
        await page.goto(f"{fixture_url}/flip-img.html", wait_until="load")
        await capture(page, 0)
    finally:
        await page.context.close()
    assert fixture_url.requests.count("/flip-img") == 1 and fixture_url.requests.count("/img-final") == 1, fixture_url.requests


async def test_a_redirect_loop_ends_as_an_aborted_navigation(fixture_url):
    from playwright.async_api import Error as PlaywrightError

    from parity.pipeline.browser import settle_redirects

    blocked: list = []
    page = await _external(fixture_url, blocked, delay_s=0)
    try:
        with pytest.raises(PlaywrightError):
            await page.goto(f"{fixture_url}/loop", wait_until="load")
            await settle_redirects(page)
    finally:
        await page.context.close()
    assert ("localhost", "too many redirects") in [(b[0], b[2]) for b in blocked]


async def test_a_websocket_from_an_external_page_never_reaches_the_server(fixture_url):
    """Review M9: Chromium's fetch interception on a routed context swallows the WebSocket upgrade; this test holds that behaviour
    (an explicit route_web_socket handler was tried and left a task the loop's teardown could not cancel: a hang after this test)."""
    fixture_url.requests.clear()
    blocked: list = []
    page = await _external(fixture_url, blocked, delay_s=0)
    try:
        await page.goto(f"{fixture_url}/ws.html", wait_until="load")
        await page.wait_for_function("() => window.done !== undefined", timeout=5000)
        assert await page.evaluate("window.done") in ("error", "closed")
    finally:
        await page.context.close()
    assert "/ws" not in fixture_url.requests


async def test_a_run_judges_at_most_a_hundred_hosts(fixture_url):
    """Review M6: a page naming thousands of hosts is not thousands of blocking lookups; past the bound the rest are refused, reported once.
    The bound is injected (five here; MAX_HOSTS_PER_RUN in a run): eight failing fetches prove the rule where 120 at once starve the driver."""
    from parity.pipeline.browser import new_page

    judged: list[str] = []
    blocked: list = []

    async def on_blocked(host: str, resource: str, reason: str) -> None:
        blocked.append((host, reason))

    def judge(host: str) -> bool:
        judged.append(host)
        return host == "localhost"  # the page itself; every image host is refused, so no fetch leaves the process (deterministic, no DNS)

    page = await new_page(external=True, own_origin="https://parity.example", on_blocked=on_blocked, judge=judge, delay_s=0, max_hosts=5)
    try:
        await page.goto(f"{fixture_url}/many-hosts.html", wait_until="load")
    finally:
        await page.context.close()
    assert len(set(judged)) == 5  # localhost and the first four image hosts
    assert blocked.count(("(many)", "more than 5 hosts on one run")) == 1
    assert sum(1 for host, reason in blocked if reason == "not a public address") == 4
