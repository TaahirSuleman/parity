"""Browser smoke test: the built SPA, served by FastAPI, replays the hero run end to end."""

from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "parity" / "static" / "index.html"
pytestmark = pytest.mark.skipif(not STATIC.exists(), reason="web/ not built (run `make build-web`)")


async def test_replay_shows_hero_card(page, server_url):
    await page.goto(server_url + "/")
    await page.get_by_role("button", name="Replay").click()
    await page.get_by_role("button", name="Run the audit").click()
    card = page.get_by_role("button", name="Pay R1,249").first
    await card.wait_for(timeout=30000)
    await card.click()
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('0 violations')", timeout=30000)
    assert 'button, "Submit"' in await page.locator("section[aria-labelledby='sr-h']").inner_text()
    assert "MUSE SPARK 1.3" in await page.locator("main").inner_text()
    header = await page.locator("header").inner_text()
    assert "verified" in header and "replay" in header.lower()


@pytest.mark.parametrize("state", ["idle", "running", "hero"])
async def test_workbench_itself_is_axe_clean(page, server_url, state):
    from tests.test_store_pages import AXE

    await page.goto(server_url + f"/?mock={state}")
    await page.get_by_role("heading", name="Parity").wait_for()
    await page.wait_for_timeout(400)  # let the 150 ms card fade-in finish; axe reads computed colours mid-animation otherwise
    await page.add_script_tag(path=str(AXE))
    result = await page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    assert [(v["id"], [n["target"] for n in v["nodes"]]) for v in result["violations"]] == []
