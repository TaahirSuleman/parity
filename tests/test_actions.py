import logging

from parity.config import load_settings
from parity.pipeline.actions import ALLOWED, SNAP_PX, chord, execute, is_allowed_target, snap_click, snap_point


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


# The recorded purchase walks of 4 Nov missed the store's buttons by a few pixels and spent turns re-clicking: Add to cart at
# y=493–495 against a box of 446–488 (attempts 2 and 3), Checkout at y=494–495 and 18 px left (attempt 1), Pay 12 px right
# (attempt 2). A click on nothing clickable within SNAP_PX of a control is moved to that control's centre by code.
ADD_TO_CART = ((187, 446, 300, 488), "#p4")
CHECKOUT = ((187, 446, 291, 488), "#k5")
PAY = ((673, 360, 827, 408), "#f5")


def test_snap_moves_a_near_miss_to_the_centre_of_the_control():
    assert SNAP_PX == 20
    assert snap_point(237, 494, False, [ADD_TO_CART]) == {"from": [237, 494], "to": [243.5, 467], "target": "#p4"}  # 6 px below
    assert snap_point(211, 495, False, [CHECKOUT]) == {"from": [211, 495], "to": [239, 467], "target": "#k5"}  # 7 px below
    assert snap_point(839, 383, False, [PAY]) == {"from": [839, 383], "to": [750, 384], "target": "#f5"}  # 12 px right
    assert snap_point(169, 467, False, [CHECKOUT]) == {"from": [169, 467], "to": [239, 467], "target": "#k5"}  # 18 px left


def test_snap_leaves_a_hit_and_a_far_miss_alone():
    assert snap_point(243, 467, True, [ADD_TO_CART]) is None  # the raw point already hits a control
    assert snap_point(243, 513, False, [ADD_TO_CART]) is None  # 25 px below: not a near miss
    assert snap_point(243, 508, False, [ADD_TO_CART]) is not None  # 20 px: the edge of the rule


def test_snap_picks_the_nearest_control_by_edge_distance():
    other = ((310, 446, 400, 488), "#share")  # 10 px right of the point, against Add to cart 6 px below it
    assert snap_point(300, 494, False, [other, ADD_TO_CART])["target"] == "#p4"


async def test_snap_click_reads_the_page_and_moves_the_action(page, store_url):
    await page.goto(store_url + "product.html")
    box = await page.locator("#p4").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    moved, snap = await snap_click(page, {"type": "click", "x": 237, "y": 494})  # 6 px below the button, as attempt 2 clicked
    assert snap == {"from": [237.0, 494.0], "to": [cx, cy], "target": "#p4"} and moved == {"type": "click", "x": cx, "y": cy}
    same, none = await snap_click(page, {"type": "click", "x": 243, "y": 467})
    assert none is None and same == {"type": "click", "x": 243, "y": 467}
    kept, none = await snap_click(page, {"type": "keypress", "keys": ["Tab"]})
    assert none is None and kept == {"type": "keypress", "keys": ["Tab"]}
