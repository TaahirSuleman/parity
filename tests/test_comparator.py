import json
from pathlib import Path

import pytest

from parity.meta.fake import FakeMetaClient
from parity.pipeline.comparator import compare, parse_candidates
from parity.pipeline.verifier import NOT_ANNOUNCED
from parity.store.models import BBox, Capture, Percept

FIXTURE = Path(__file__).parent / "fixtures" / "capture_checkout.json"


def response_with(payload: dict) -> dict:
    return {"id": "resp_fake", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(payload)}]}], "usage": {"input_tokens": 10, "output_tokens": 5}}


@pytest.fixture
def cap() -> Capture:
    c = Capture.model_validate_json(FIXTURE.read_text())
    c.screenshot_png = (FIXTURE.with_suffix(".png")).read_bytes()
    return c


GOOD = {"findings": [{"what_sighted_user_sees": "Pay R1,249", "screen_reader_role": "button", "screen_reader_name": "Submit", "why_it_matters": "price hidden", "bbox": {"x_min": 526, "y_min": 500, "x_max": 646, "y_max": 567}}]}


def test_parse_candidates_valid():
    [c] = parse_candidates(json.dumps(GOOD), step_index=3)
    assert c.sighted_text == "Pay R1,249" and c.sr_quote == 'button, "Submit"'
    assert c.bbox == BBox(x_min=526, y_min=500, x_max=646, y_max=567) and c.step_index == 3


def test_parse_candidates_not_announced():
    payload = {"findings": [{"what_sighted_user_sees": "R1,249.00", "screen_reader_role": "", "screen_reader_name": "", "bbox": {"x_min": 1, "y_min": 1, "x_max": 2, "y_max": 2}}]}
    [c] = parse_candidates(json.dumps(payload), step_index=0)
    assert c.sr_quote == NOT_ANNOUNCED


def test_parse_candidates_garbage_returns_empty():
    assert parse_candidates("not json at all", step_index=0) == []
    assert parse_candidates(json.dumps({"findings": "nope"}), step_index=0) == []
    mixed = {"findings": [{"bbox": "bad"}, GOOD["findings"][0], {"what_sighted_user_sees": "x", "screen_reader_role": "link", "screen_reader_name": "y"}]}
    parsed = parse_candidates(json.dumps(mixed), step_index=0)
    assert [c.sighted_text for c in parsed] == ["Pay R1,249", "x"]
    assert parsed[1].bbox is None


async def test_compare_includes_feedback_in_prompt(cap, tmp_path):
    fake = FakeMetaClient(tmp_path, default=response_with(GOOD))
    out = await compare(fake, cap, [], run_id="r1", feedback=["quote the exact role and accessible name"], model="m")
    text = fake.calls[0]["input"][0]["content"][0]["text"]
    assert "quote the exact role and accessible name" in text and "VERIFIER FEEDBACK" in text
    assert out and out[0].attempt == 2


async def test_compare_default_includes_tree_and_image(cap, tmp_path):
    fake = FakeMetaClient(tmp_path, default=response_with(GOOD))
    await compare(fake, cap, [Percept(step_index=0, visible_text="Pay R1,249", kind="button", bbox=BBox(x_min=526, y_min=500, x_max=646, y_max=567))], run_id="r1", model="m")
    body = fake.calls[0]
    text = body["input"][0]["content"][0]["text"]
    assert "ACCESSIBILITY TREE" in text and '"Submit"' in text and "Pay R1,249" in text
    assert body["input"][0]["content"][1]["type"] == "input_image"
    assert body["model"] == "m" and body["text"] == {"format": {"type": "json_object"}} and body["reasoning"] == {"effort": "medium"}


async def test_compare_no_tree_omits_ax(cap, tmp_path):
    fake = FakeMetaClient(tmp_path, default=response_with(GOOD))
    await compare(fake, cap, [], run_id="r1", model="m", use_tree=False, use_screenshot=False)
    body = fake.calls[0]
    text = body["input"][0]["content"][0]["text"]
    assert "ACCESSIBILITY TREE" not in text
    assert all(part["type"] != "input_image" for part in body["input"][0]["content"])


async def test_seer_percepts_clamped(cap, tmp_path):
    from parity.pipeline.seer import see

    payload = {"percepts": [{"visible_text": "Pay R1,249", "kind": "button", "bbox": {"x_min": 526, "y_min": 500, "x_max": 1200, "y_max": 567}}, {"visible_text": "50% OFF TODAY", "kind": "banner", "bbox": {"x_min": 1, "y_min": 1, "x_max": 2, "y_max": 2}}, {"nonsense": True}]}
    fake = FakeMetaClient(tmp_path, default=response_with(payload))
    percepts = await see(fake, cap, run_id="r1", model="m")
    assert [p.visible_text for p in percepts] == ["Pay R1,249", "50% OFF TODAY"]
    assert percepts[0].bbox.x_max == 1000 and percepts[1].kind == "other"
    assert fake.calls[0]["input"][0]["content"][1]["type"] == "input_image"
    assert "object grounding expert" in fake.calls[0]["input"][0]["content"][0]["text"]
