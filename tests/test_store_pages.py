from pathlib import Path

import httpx

AXE = Path(__file__).resolve().parents[1] / "parity" / "vendor" / "axe.min.js"
HERO_IDS = ["f1", "f2", "f4", "f5", "f6", "c1", "c2", "card"]


async def test_checkout_has_zero_axe_violations(page, store_url):
    await page.goto(store_url + "checkout.html")
    await page.add_script_tag(path=str(AXE))
    result = await page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    assert [v["id"] for v in result["violations"]] == []


async def test_checkout_hero_ids_exist(page, store_url):
    await page.goto(store_url + "checkout.html")
    present = await page.evaluate("ids => ids.filter(i => document.getElementById(i) !== null)", HERO_IDS)
    assert present == HERO_IDS
    assert await page.inner_text("#f5") == ""  # the label is pixels: an image saying "Pay R1,249"
    assert await page.get_attribute("#f5", "aria-label") == "Submit"


async def test_checkout_pays_when_expiry_fixed(page, store_url):
    await page.goto(store_url + "checkout.html")
    await page.fill("#exp", "10/28")
    await page.click("#f5")
    assert await page.is_visible("#done")


def test_health_ok(server_url):
    body = httpx.get(server_url + "/api/health").json()
    assert body["ok"] is True
    assert body["mode_default"] == "replay"
    assert body["live_enabled"] is True
