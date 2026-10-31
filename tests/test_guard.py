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
