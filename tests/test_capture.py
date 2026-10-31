import pytest
import pytest_asyncio

from parity.pipeline.capture import capture, to_grid
from parity.store.models import BBox

FILTERED = {"generic", "none", "StaticText", "InlineTextBox", "LineBreak", "RootWebArea"}


@pytest_asyncio.fixture
async def checkout(page, store_url):
    await page.goto(store_url + "checkout.html")
    return await capture(page, step_index=0)


async def test_ax_contains_submit_button(checkout):
    hits = [n for n in checkout.ax_nodes if n.role == "button" and n.name == "Submit" and n.dom_id == "f5"]
    assert len(hits) == 1
    node = hits[0]
    assert node.css_path == "button#f5"
    assert node.outer_html and node.outer_html.startswith('<button id="f5"')
    assert node.box_px and node.bbox


async def test_canvas_price_has_no_ax_name(checkout):
    """The total is drawn on a canvas: it is a silent node, and no accessibility node carries it."""
    canvas = [n for n in checkout.silent_nodes if n.dom_id == "f2"]
    assert len(canvas) == 1 and canvas[0].role == "silent:canvas" and canvas[0].bbox
    assert not [n for n in checkout.ax_nodes if n.dom_id == "f2"]
    from parity.pipeline.verifier import iou

    assert not [n for n in checkout.ax_nodes if n.bbox and iou(n.bbox, canvas[0].bbox) > 0 and "1,249" in n.name]


async def test_boxes_on_grid(checkout):
    boxed = [n for n in checkout.ax_nodes if n.bbox]
    assert boxed
    for n in boxed:
        assert 0 <= n.bbox.x_min < n.bbox.x_max <= 1000
        assert 0 <= n.bbox.y_min < n.bbox.y_max <= 1000


async def test_axe_violations_empty(checkout):
    assert checkout.axe_violations == []


async def test_filtered_roles(checkout):
    assert not {n.role for n in checkout.ax_nodes} & FILTERED
    assert {"button", "link", "textbox", "heading", "image", "text"} <= {n.role for n in checkout.ax_nodes}
    # Static text is announced too; it is kept as role "text" so silence claims over real text are rejected.
    assert any(n.role == "text" and n.name == "Delivery" and n.bbox for n in checkout.ax_nodes)


async def test_screenshot_and_metadata(checkout, store_url):
    assert checkout.screenshot_png[:8] == b"\x89PNG\r\n\x1a\n"
    assert checkout.url == store_url + "checkout.html"
    assert checkout.viewport == (1280, 720) and checkout.step_index == 0


async def test_capture_keeps_page_html(checkout):
    """The rendered page source rides with the capture: the fixer patches it and the re-audit reloads it."""
    assert "<html" in checkout.html and 'id="f5"' in checkout.html
    f5 = next(n for n in checkout.ax_nodes if n.dom_id == "f5")
    assert f5.outer_html and f5.outer_html.startswith('<button id="f5"')  # the DOM copy; the source is located by id, not by this text


def test_to_grid():
    assert to_grid((0, 0, 1280, 720), (1280, 720)) == BBox(x_min=0, y_min=0, x_max=1000, y_max=1000)
    assert to_grid((128, 72, 640, 360), (1280, 720)) == BBox(x_min=100, y_min=100, x_max=500, y_max=500)


async def test_capture_html_is_the_served_source(checkout):
    """The patch base is the document as served, byte for byte, not the browser's re-serialised DOM."""
    from pathlib import Path

    assert checkout.html == (Path(__file__).resolve().parents[1] / "store" / "checkout.html").read_text()


async def test_text_node_dom_id_is_the_containing_elements_id(page, store_url):
    from parity.pipeline.capture import capture

    await page.goto(store_url + "product.html")
    cap = await capture(page, 0)
    was = [n for n in cap.ax_nodes if n.role == "text" and n.name.strip() == "R1,599.00"]
    assert was and was[0].dom_id == "was-price"


async def test_css_drawn_content_without_text_is_a_silent_node(page, store_url):
    """A star rating drawn by ::before (icon fonts, background images) renders pixels but reaches no screen reader:
    it must be in silent_nodes so the comparator's box can be located and the gap verified."""
    from parity.pipeline.capture import capture

    await page.goto(store_url + "product.html")
    cap = await capture(page, 0)
    assert "rating-css" in {n.dom_id for n in cap.silent_nodes}
    assert "rating-css" not in {n.dom_id for n in cap.ax_nodes}
