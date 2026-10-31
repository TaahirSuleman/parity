from pathlib import Path

import httpx
import pytest

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


PAGES = ["product.html", "cart.html", "checkout.html", "confirm.html"]


@pytest.mark.parametrize("page_name", PAGES)
async def test_every_store_page_has_zero_axe_violations(page, store_url, page_name):
    await page.goto(store_url + page_name)
    await page.add_script_tag(path=str(AXE))
    result = await page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    assert [(v["id"], [n["target"] for n in v["nodes"]]) for v in result["violations"]] == []


async def test_purchase_flow_reaches_confirmation(page, store_url):
    await page.goto(store_url + "product.html")
    await page.get_by_role("button", name="Add to cart").click()
    await page.wait_for_url("**/cart.html")
    await page.get_by_role("link", name="Checkout").click()
    await page.wait_for_url("**/checkout.html")
    await page.fill("#card", "4111 1111 1111 1111")
    await page.click("#f5")
    await page.wait_for_url("**/confirm.html")
    assert "Order confirmed" in await page.inner_text("h1")


async def test_checkout_pay_with_invalid_card_stays_on_page(page, store_url):
    """The seeded fault: a bad card only gets a red border, no text, and nothing happens on pay."""
    await page.goto(store_url + "checkout.html")
    await page.click("#f5")
    await page.wait_for_timeout(200)
    assert page.url.endswith("checkout.html")
    assert "err" in (await page.get_attribute("#card", "class") or "")


def test_purchase_flow_registered():
    from parity.flows import FLOWS

    flow = FLOWS["purchase"]
    assert flow.start_url == "/store/product.html" and flow.single_page is False
    assert flow.pages == ("product.html", "cart.html", "checkout.html", "confirm.html")
    assert "4111 1111 1111 1111" in flow.goal and "10/28" in flow.goal


def test_health_ok(server_url):
    body = httpx.get(server_url + "/api/health").json()
    assert body["ok"] is True
    assert body["mode_default"] == "replay"
    assert body["live_enabled"] is True
