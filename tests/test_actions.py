import logging

from parity.config import load_settings
from parity.pipeline.actions import ALLOWED, chord, execute, is_allowed_target


def test_keypress_chord_joined():
    assert chord(["ctrl", "a"]) == "ControlOrMeta+a"  # select-all is Meta+a on macOS, Control+a elsewhere
    assert chord(["CMD", "Shift", "z"]) == "Meta+Shift+z"
    assert chord(["ENTER"]) == "Enter" and chord(["x"]) == "x"


def test_target_origin_blocked():
    settings = load_settings(env={"PARITY_LIVE_TARGET_ORIGINS": "self"})
    base = "http://127.0.0.1:8080"
    assert is_allowed_target(base + "/store/cart.html", settings, base) is True
    assert is_allowed_target("https://evil.example/", settings, base) is False
    assert is_allowed_target("about:blank", settings, base) is True
    open_settings = load_settings(env={"PARITY_LIVE_TARGET_ORIGINS": "https://shop.example,https://docs.example"})
    assert is_allowed_target("https://shop.example/checkout", open_settings, base) is True
    assert is_allowed_target("https://other.example/", open_settings, base) is False


async def test_execute_rejects_unknown_action(page, store_url, caplog):
    await page.goto(store_url + "product.html")
    with caplog.at_level(logging.WARNING):
        assert await execute(page, {"type": "launch_missiles"}) is False
        assert await execute(page, {"type": "click"}) is False  # missing coordinates
    assert "launch_missiles" in caplog.text
    assert page.url.endswith("product.html")
    assert {"click", "double_click", "type", "keypress", "scroll", "wait", "screenshot"} == ALLOWED


async def test_execute_click_type_and_chord_on_real_page(page, store_url):
    await page.goto(store_url + "checkout.html")
    box = await page.locator("#card").bounding_box()
    assert await execute(page, {"type": "click", "x": box["x"] + 10, "y": box["y"] + 10}) is True
    assert await execute(page, {"type": "keypress", "keys": ["ctrl", "a"]}) is True
    assert await execute(page, {"type": "type", "text": "4111 1111 1111 1111"}) is True
    assert await page.input_value("#card") == "4111 1111 1111 1111"
    assert await execute(page, {"type": "wait"}) is True
    assert await execute(page, {"type": "screenshot"}) is True


def test_key_names_with_underscores_or_spaces_are_normalised():
    """Spark writes Page_Down / Arrow Down; Playwright wants PageDown / ArrowDown."""
    from parity.pipeline.actions import chord

    assert chord(["Page_Down"]) == "PageDown"
    assert chord(["page_up"]) == "PageUp"
    assert chord(["Arrow Down"]) == "ArrowDown"
    assert chord(["CTRL", "a"]) == "ControlOrMeta+a"


async def test_settle_waits_for_a_guarded_page_to_fill_itself_in(fixture_url):
    """Review of the render wait: a later screen of a page we do not serve may render from scripts too, so settle waits for its words
    (bounded) when the page carries the guard; a store page, which is static, is not slowed."""
    from parity.pipeline.actions import settle
    from parity.pipeline.browser import new_page

    page = await new_page(external=True, own_origin="https://parity.example", judge=lambda host: host in ("localhost", "127.0.0.1"), delay_s=0)
    try:
        await page.goto(f"{fixture_url}/late.html", wait_until="load")
        await settle(page)
        assert await page.evaluate("() => document.body.innerText.length") >= 40
    finally:
        await page.context.close()
