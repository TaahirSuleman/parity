"""Public-site guard (spec §17): read-only by construction, robots.txt respected, bundles anonymised before they are shared."""

import json
from pathlib import Path

import pytest

from parity.pipeline.guard import Blocked, anonymise, guard_action, robots_allows
from parity.store.models import AxNode, BBox


def node(role: str, name: str) -> AxNode:
    return AxNode(backend_id=1, role=role, name=name, bbox=BBox(x_min=0, y_min=0, x_max=10, y_max=10))


def test_blocks_pay_click():
    for name in ("Pay R1,249", "Place order", "Buy now", "Subscribe", "Confirm", "Delete", "Sign up", "Checkout now", "SUBMIT"):
        verdict = guard_action({"type": "click", "x": 1, "y": 1}, node("button", name), None)
        assert isinstance(verdict, Blocked) and name.lower().split()[0] in verdict.reason.lower(), name


def test_allows_add_to_cart_click():
    assert guard_action({"type": "click", "x": 1, "y": 1}, node("button", "Add to cart"), None).allowed
    assert guard_action({"type": "click", "x": 1, "y": 1}, node("link", "Continue shopping"), None).allowed
    assert guard_action({"type": "scroll", "scroll_y": 300}, None, None).allowed
    assert guard_action({"type": "click", "x": 1, "y": 1}, None, None).allowed  # nothing known under the pointer: a plain click is fine


def test_blocks_password_typing():
    for field in ("password", "cc-number", "cc-csc", "email", "tel"):
        verdict = guard_action({"type": "type", "text": "x"}, node("textbox", "Card"), field)
        assert isinstance(verdict, Blocked) and field in verdict.reason, field
    assert guard_action({"type": "type", "text": "headphones"}, node("searchbox", "Search"), "search").allowed


def test_blocks_form_submit():
    assert isinstance(guard_action({"type": "keypress", "keys": ["Enter"]}, node("textbox", "Email"), "email"), Blocked)
    assert isinstance(guard_action({"type": "keypress", "keys": ["ENTER"]}, node("textbox", "Search"), "search"), Blocked)  # Enter in a field submits
    assert isinstance(guard_action({"type": "click", "x": 1, "y": 1}, node("button", "Search"), None, submits=True), Blocked)
    assert guard_action({"type": "keypress", "keys": ["PageDown"]}, None, None).allowed


def test_blocks_space_and_newline_submissions():
    """Space activates a focused button and a newline in typed text is Enter: both reach a form the same way Enter does."""
    assert isinstance(guard_action({"type": "keypress", "keys": ["SPACE"]}, node("button", "Place order"), None), Blocked)
    assert isinstance(guard_action({"type": "keypress", "keys": [" "]}, node("button", "Next page"), None), Blocked)
    assert isinstance(guard_action({"type": "type", "text": "hi\n"}, node("textbox", "Search"), "text"), Blocked)
    assert isinstance(guard_action({"type": "type", "text": "hi\r"}, node("textbox", "Search"), "text"), Blocked)
    assert guard_action({"type": "type", "text": "hi there"}, node("textbox", "Search"), "text").allowed
    assert guard_action({"type": "keypress", "keys": ["SPACE"]}, None, None).allowed  # nothing focused: Space scrolls


def test_every_field_type_token_is_checked():
    """The field type carries both the type attribute and the autocomplete tokens; one blocked token is enough."""
    assert isinstance(guard_action({"type": "type", "text": "x"}, node("textbox", ""), "password off"), Blocked)
    assert isinstance(guard_action({"type": "type", "text": "x"}, node("textbox", ""), "email username"), Blocked)
    assert isinstance(guard_action({"type": "type", "text": "x"}, node("textbox", ""), "text section-blue shipping cc-number"), Blocked)
    assert guard_action({"type": "type", "text": "x"}, node("textbox", ""), "text off").allowed


def test_blocks_clicks_into_frames():
    """What is inside an embedded frame is not inspected, so it is not clicked."""
    verdict = guard_action({"type": "click", "x": 1, "y": 1}, node("iframe", ""), None)
    assert isinstance(verdict, Blocked) and "frame" in verdict.reason
    assert isinstance(guard_action({"type": "type", "text": "x"}, node("iframe", ""), None), Blocked)  # a focused field inside a frame


def test_challenge_reason_recognises_bot_walls_and_logins():
    """CAPTCHAs, bot challenges and login walls end a public run with reason 'blocked by site' (spec §17); a shop page with a
    password field in its header is not a login wall."""
    from parity.pipeline.guard import challenge_reason

    assert challenge_reason("Just a moment...", "https://shop.example/", []) == "blocked by site: bot challenge"
    assert challenge_reason("Shop", "https://shop.example/", ["iframe[src*='challenges.cloudflare.com']"]) == "blocked by site: bot challenge"
    assert challenge_reason("Shop", "https://shop.example/", [".g-recaptcha"]) == "blocked by site: CAPTCHA"
    assert challenge_reason("Attention Required! | Cloudflare", "https://shop.example/", []) == "blocked by site: bot challenge"
    assert challenge_reason("Sign in to your account", "https://shop.example/login", ["input[type=password]"]) == "blocked by site: login"
    assert challenge_reason("Shop", "https://shop.example/account/login", ["input[type=password]"]) == "blocked by site: login"
    assert challenge_reason("Wireless headphones | Shop", "https://shop.example/p/1", ["input[type=password]"]) is None
    assert challenge_reason("Wireless headphones | Shop", "https://shop.example/p/1", []) is None


PROBE_HTML = """<html><body style="margin:0">
<button id="a" title="More info" style="position:absolute;left:10px;top:10px;width:120px;height:30px">Buy now</button>
<span id="lbl" style="position:absolute;left:400px;top:400px">Place order</span>
<button id="b" aria-labelledby="lbl" style="position:absolute;left:10px;top:60px;width:120px;height:30px"><span>&#x2192;</span></button>
<input id="pw" type="password" autocomplete="off" style="position:absolute;left:10px;top:110px">
<input id="em" type="email" autocomplete="username" style="position:absolute;left:10px;top:150px">
<button id="c" type="button" style="position:absolute;left:10px;top:190px;width:120px;height:30px">Place order</button>
<form id="f" action="/s" style="position:absolute;left:10px;top:240px"><input id="q" type="text" name="q"></form>
<div id="d" onclick="1" style="position:absolute;left:10px;top:290px;width:160px;height:30px"><span>Place</span> <span>order</span></div>
<iframe srcdoc="<button>Pay</button>" style="position:absolute;left:10px;top:340px;width:200px;height:60px"></iframe>
<button id="img" style="position:absolute;left:10px;top:420px;width:120px;height:30px"><img alt="Confirm purchase" src="data:,"></button>
<a id="ok" href="#next" style="position:absolute;left:10px;top:470px;width:120px;height:30px;display:block">Next page</a>
</body></html>"""


async def test_inspect_target_reads_every_name_source(page):
    """The guard sees what a user would act on: the title, aria-labelledby text, split text in an onclick div, an image's alt,
    the type attribute AND the autocomplete tokens, Space on a focused control, a newline in typed text, a frame."""
    from parity.agent.loop import inspect_target

    await page.set_content(PROBE_HTML)

    async def centre(selector):
        box = await page.locator(selector).first.bounding_box()
        return {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}

    async def verdict(action):
        target, field_type, submits = await inspect_target(page, action)
        return guard_action(action, target, field_type, submits=submits)

    for sel in ("#a", "#b", "#d span", "#img", "iframe"):
        assert isinstance(await verdict({"type": "click", **await centre(sel)}), Blocked), sel
    assert (await verdict({"type": "click", **await centre("#ok")})).allowed
    await page.focus("#pw")
    assert isinstance(await verdict({"type": "type", "text": "x"}), Blocked)
    await page.focus("#em")
    assert isinstance(await verdict({"type": "type", "text": "x"}), Blocked)
    await page.focus("#c")
    assert isinstance(await verdict({"type": "keypress", "keys": ["SPACE"]}), Blocked)
    await page.focus("#q")
    assert isinstance(await verdict({"type": "type", "text": "hi\n"}), Blocked)
    assert (await verdict({"type": "type", "text": "hi"})).allowed


async def test_inspect_target_fails_closed():
    """When the page cannot be inspected (mid-navigation, a detached frame) the guard does not guess: the action is refused."""
    from parity.agent.loop import InspectionFailed, inspect_target

    class Broken:
        async def evaluate(self, *a, **k):
            raise RuntimeError("Execution context was destroyed")

    with pytest.raises(InspectionFailed):
        await inspect_target(Broken(), {"type": "click", "x": 1, "y": 1})


def test_robots_disallow_stops_run():
    body = "User-agent: *\nDisallow: /private/\nDisallow: /cart\n"
    assert robots_allows("https://shop.example/product/1", fetch=lambda url: body) is True
    assert robots_allows("https://shop.example/cart", fetch=lambda url: body) is False
    assert robots_allows("https://shop.example/private/x", fetch=lambda url: body) is False
    assert robots_allows("https://shop.example/anything", fetch=lambda url: None) is True  # no robots.txt: allowed

    def boom(url):
        raise OSError("network")

    assert robots_allows("https://shop.example/anything", fetch=boom) is True  # unreachable robots.txt does not block (logged)


async def test_anonymise_removes_host(tmp_path):
    from tests.helpers import SRC, make_replay_bundle

    await make_replay_bundle(tmp_path / "data")
    src = tmp_path / "data" / "runs" / SRC
    host = "shop-real-example.co.za"
    # plant the host where a real run would carry it: run.json, step urls, events, conversation, source
    for rel in ("run.json", "steps/0/step.json", "events.jsonl"):
        p = src / rel
        p.write_text(p.read_text().replace("127.0.0.1:8080", host).replace("http://x/", f"https://{host}/"))
    (src / "agent").mkdir(exist_ok=True)
    (src / "agent" / "conversation.json").write_text(json.dumps({"run_id": SRC, "turns": [{"input": f"Go to https://{host}/product and look"}]}))
    (src / "steps" / "0" / "source.html").write_text(f'<html><head><title>Real Shop</title></head><body><a href="https://{host}/cart">x</a></body></html>')
    (src / "steps" / "1").mkdir()
    (src / "steps" / "1" / "screenshot.png").write_bytes(b"\x89PNG fake")  # a step with no verified finding: its screenshot goes
    (src / "steps" / "1" / "step.json").write_text(json.dumps({"run_id": SRC, "index": 1, "url": f"https://{host}/cart", "screenshot": "steps/1/screenshot.png", "ax_tree": "", "axe": "", "viewport": [1280, 720], "axe_violations": 0, "ax_nodes": 1, "captured_at": "2026-10-31T00:00:00Z"}))

    out = anonymise(src, tmp_path / "out" / "public-a", letter="A", host=host)
    texts = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert texts, "nothing written"
    assert not any(host.encode() in b for b in texts.values()), [k for k, b in texts.items() if host.encode() in b]
    assert not any(b"Real Shop" in b for b in texts.values())
    assert "steps/0/screenshot.png" in texts and "steps/1/screenshot.png" not in texts  # kept only where a finding was verified
    run = json.loads(texts["run.json"])
    assert run["id"] == "public-a" and run["target_url"].startswith("https://site-a.invalid/") and "Site A" in json.dumps(run)
    assert run["flow_id"] == "public"  # one flow id for every sample: Replay opens them by run id


async def test_anonymise_drops_agent_screenshots_and_brand_names(tmp_path):
    """The host string is not the only way a bundle names a site: the brand appears in headings, text nodes and the agent's
    own screenshots. Brand names are scrubbed everywhere and the agent directory is not copied at all."""
    from tests.helpers import SRC, make_replay_bundle

    await make_replay_bundle(tmp_path / "data")
    src = tmp_path / "data" / "runs" / SRC
    (src / "agent").mkdir(exist_ok=True)
    (src / "agent" / "0123456789abcdef.png").write_bytes(b"\x89PNG fake home page with the logo")
    (src / "agent" / "conversation.json").write_text(json.dumps({"run_id": SRC, "turns": [{"input": "png:0123456789abcdef", "output": "Real Shop Ltd sells books"}]}))
    ax = src / "steps" / "0" / "ax.json"
    ax.write_text(ax.read_text().replace('"name": "Submit"', '"name": "Real Shop Ltd | Submit"', 1))
    with (src / "events.jsonl").open("a") as fh:
        fh.write(json.dumps({"type": "agent.tool_call", "run_id": SRC, "data": {"summary": "Reached the REAL SHOP LTD checkout"}}) + "\n")

    out = anonymise(src, tmp_path / "out" / "public-a", letter="A", host="shop-real-example.co.za", names=["Real Shop Ltd"])
    files = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert not any(k.startswith("agent/") for k in files), [k for k in files if k.startswith("agent/")]
    assert not any(b"real shop" in b.lower() for b in files.values()), [k for k, b in files.items() if b"real shop" in b.lower()]
    assert b"Site A | Submit" in files["steps/0/ax.json"]  # the brand is replaced, not the line


async def test_anonymise_masks_the_kept_screenshot_outside_the_finding_boxes(tmp_path):
    """A kept screenshot shows the evidence and nothing else: pixels outside the verified findings' boxes are painted over."""
    from io import BytesIO

    from PIL import Image

    from tests.helpers import SRC, make_replay_bundle

    await make_replay_bundle(tmp_path / "data")
    src = tmp_path / "data" / "runs" / SRC
    before = Image.open(src / "steps" / "0" / "screenshot.png").convert("RGB")
    out = anonymise(src, tmp_path / "out" / "public-a", letter="A", host="shop-real-example.co.za")
    after = Image.open(BytesIO((out / "steps" / "0" / "screenshot.png").read_bytes())).convert("RGB")
    assert after.size == before.size
    # the hero finding's box is (526,500)-(646,567) on the 0-1000 grid of a 1280x720 screenshot: (673,360)-(827,408) in pixels
    assert after.getpixel((750, 384)) == before.getpixel((750, 384))  # inside the finding: untouched
    assert after.getpixel((20, 20)) != before.getpixel((20, 20)) and after.getpixel((20, 20)) == after.getpixel((1200, 700))  # outside: one flat colour


def test_blocks_every_spelling_of_enter_and_unnamed_buttons_on_a_public_site():
    """The executor maps "\\n", "numpad enter", "Shift+Enter" and friends to Enter, so the guard must refuse them the same way;
    a button the accessibility tree cannot name (an icon, a CSS ::before label) is an unknown step, refused rather than guessed."""
    for keys in (["\n"], ["\r"], ["numpad enter"], ["numpad_enter"], ["Shift+Enter"], ["NumpadEnter"], ["shift", "enter"]):
        assert isinstance(guard_action({"type": "keypress", "keys": keys}, node("textbox", "Search"), "search"), Blocked), keys
    assert guard_action({"type": "keypress", "keys": ["shift", "Tab"]}, node("textbox", "Search"), "search").allowed
    assert isinstance(guard_action({"type": "click", "x": 1, "y": 1}, node("button", ""), None), Blocked)
    assert guard_action({"type": "click", "x": 1, "y": 1}, node("link", ""), None).allowed  # a link only navigates
    assert guard_action({"type": "click", "x": 1, "y": 1}, node("img", ""), None).allowed


def test_irreversible_labels_cover_the_common_checkout_words():
    for name in ("Complete purchase", "Place your order", "Order now", "Donate", "Pay​now", "Book now", "Register", "Send message", "Purchase"):
        assert isinstance(guard_action({"type": "click", "x": 1, "y": 1}, node("button", name), None), Blocked), name
    for name in ("Add to cart", "Continue shopping", "Apply filters", "Cancel", "Show more", "Search"):
        assert guard_action({"type": "click", "x": 1, "y": 1}, node("button", name), None).allowed, name


async def test_anonymise_relabels_the_start_event_as_well_as_run_json(tmp_path):
    """run.json said flow_id "public" but the run.started event still carried "public-<host>" and the bare goal: the workbench
    reads the event, so Site A played under the store's own header ("ShopRight · Checkout page")."""
    src = tmp_path / "20261031-225149-ab12"
    src.mkdir()
    (src / "run.json").write_text(json.dumps({"id": src.name, "flow_id": "public-shop.example", "goal": "Open the first book.", "status": "done"}))
    (src / "events.jsonl").write_text(json.dumps({"type": "run.started", "run_id": src.name, "at": "t", "data": {"flow_id": "public-shop.example", "flow_name": "Public: shop.example", "goal": "Open the first book.", "mode": "live", "target_url": "https://shop.example/"}}) + "\n"
                                      + json.dumps({"type": "run.finished", "run_id": src.name, "at": "t", "data": {}}) + "\n")
    dest = anonymise(src, tmp_path / "public-a", letter="A", host="shop.example")
    started = json.loads((dest / "events.jsonl").read_text().splitlines()[0])
    assert started["data"]["flow_id"] == "public" and started["data"]["flow_name"] == "Site A" and started["data"]["goal"] == "Site A: Open the first book."
    assert "shop.example" not in (dest / "events.jsonl").read_text()
    assert json.loads((dest / "run.json").read_text())["goal"] == "Site A: Open the first book."


def test_guard_edge_spellings_from_the_fuzz():
    """A zero-width character inside a word, `keys` given as one string, an NBSP in a challenge title, and a /users/sign_in path."""
    from parity.pipeline.guard import challenge_reason

    assert isinstance(guard_action({"type": "click", "x": 1, "y": 1}, node("button", "P​ay now"), None), Blocked)
    assert isinstance(guard_action({"type": "keypress", "keys": "Enter"}, node("textbox", "Card"), "cc-number"), Blocked)
    assert challenge_reason("Just\xa0a moment...", "https://x/", []) == "blocked by site: bot challenge"
    assert challenge_reason("Shop", "https://x/users/sign_in", ["input[type=password]"]) == "blocked by site: login"
