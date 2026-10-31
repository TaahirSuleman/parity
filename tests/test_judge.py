import json
import pytest

from parity.meta.client import MetaError
from parity.meta.fake import FakeMetaClient
from parity.pipeline.judge import judge
from parity.store.models import Severity

def response_with(payload) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {"id": "resp_fake", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}], "usage": {"input_tokens": 10, "output_tokens": 5}}


GOOD = {"is_barrier": True, "severity": "critical", "wcag": [{"sc": "2.5.3", "name": "Label in Name"}, {"sc": "4.1.2", "name": "Name, Role, Value"}], "impact": "A blind shopper cannot tell what the button will charge."}


async def test_judge_hero_is_barrier(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with(GOOD))
    j = await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    assert j.is_barrier is True and j.severity == Severity.critical
    assert j.wcag and j.wcag[0].sc == "2.5.3"
    assert j.model_meta["model"] == "muse-spark-1.3" and j.model_meta["fallback"] is False
    text = fake.calls[0]["input"][0]["content"][0]["text"]
    assert "Pay R1,249" in text and "Submit" in text and fake.calls[0]["text"] == {"format": {"type": "json_object"}}


async def test_judge_not_a_barrier_is_a_verdict(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with({**GOOD, "is_barrier": False, "severity": "minor"}))
    j = await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    assert j.is_barrier is False and j.severity == Severity.minor


async def test_judge_unparseable_needs_review(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with("I think it's probably a barrier"))
    j = await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    assert j.is_barrier is None and j.severity == Severity.needs_review


async def test_judge_list_instead_of_bool_needs_review(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with({**GOOD, "is_barrier": ["yes"], "severity": "made-up"}))
    j = await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    assert j.is_barrier is None and j.severity == Severity.needs_review


async def test_wonder_error_falls_back_to_spark(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with(GOOD), errors={"muse-wonder-1.0": MetaError("boom", status=500, request_id="req-w", attempts=3)})
    j = await judge(fake, finding, cap, run_id="r1", model="muse-wonder-1.0")
    assert [c["model"] for c in fake.calls] == ["muse-wonder-1.0", "muse-spark-1.3"]
    assert j.is_barrier is True and j.model_meta["fallback"] is True and j.model_meta["model"] == "muse-spark-1.3"


async def test_spark_error_propagates(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, errors={"muse-spark-1.3": MetaError("boom", status=500, request_id="req-s", attempts=3)})
    with pytest.raises(MetaError):
        await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")


async def test_judge_incomplete_response_needs_review_and_records_status(hero, tmp_path):
    cap, finding = hero
    incomplete = {"id": "resp_inc", "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"},
                  "output": [{"type": "reasoning", "content": []}], "usage": {"input_tokens": 1500, "output_tokens": 1500}}
    fake = FakeMetaClient(tmp_path, default=incomplete)
    j = await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    assert j.is_barrier is None and j.severity == Severity.needs_review
    assert j.model_meta["status"] == "incomplete" and j.model_meta["incomplete_reason"] == "max_output_tokens"
    assert fake.calls[0]["max_output_tokens"] >= 4000


async def test_judge_sees_the_accessibility_tree(hero, tmp_path):
    """The judge must weigh the finding against the whole screen's announcements, not the screenshot alone."""
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with(GOOD))
    await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    text = fake.calls[0]["input"][0]["content"][0]["text"]
    assert "ACCESSIBILITY TREE" in text and '"Card number"' in text and '"Save for later"' in text


async def test_malformed_wcag_fails_closed(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with({"is_barrier": True, "severity": "serious", "wcag": 5, "impact": "x"}))
    j = await judge(fake, finding, cap, run_id="r1", model="muse-spark-1.3")
    assert j.severity == Severity.needs_review or j.wcag == []
