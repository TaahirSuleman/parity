import json
from pathlib import Path

import pytest

from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle, keys
from parity.store.models import (
    BBox, Candidate, Capture, Check, Element, Event, Finding, FindingStatus, Judgement, ModelCall, Rejected, Run, RunMode, RunStatus, Severity, Step,
    VerifierResult, WcagRef,
)

FIXTURE = Path(__file__).parent / "fixtures" / "capture_checkout.json"


def sample_run(run_id="run1", status=RunStatus.running) -> Run:
    return Run(id=run_id, mode=RunMode.live, flow_id="checkout", goal="Pay", target_url="http://x/store/checkout.html", status=status)


def sample_finding(run_id="run1", fid="f-1") -> Finding:
    el = Element(backend_id=1, css_path="button#f5", dom_id="f5", outer_html='<button id="f5" aria-label="Submit">')
    checks = {k: Check(passed=True, detail="ok") for k in ("located", "sr_quote_exact", "diverges", "not_axe", "unique")}
    vr = VerifierResult(passed=True, checks=checks, element=el)
    judgement = Judgement(is_barrier=True, severity=Severity.serious, wcag=[WcagRef(sc="2.5.3", name="Label in Name")],
                          impact="A blind shopper cannot tell what the button will charge.", model_meta={"model": "muse-spark-1.3", "fallback": False})
    return Finding(id=fid, run_id=run_id, step_index=0, status=FindingStatus.judged, sighted_text="Pay R1,249", sr_role="button", sr_name="Submit",
                   why_it_matters="The price is only in pixels.", bbox=BBox(x_min=526, y_min=500, x_max=646, y_max=567), element=el, verifier=vr, judgement=judgement)


@pytest.fixture
def cap() -> Capture:
    c = Capture.model_validate_json(FIXTURE.read_text())
    c.screenshot_png = FIXTURE.with_suffix(".png").read_bytes()
    return c


async def test_bundle_layout(tmp_path, cap):
    bundle = RunBundle(LocalBlobStore(tmp_path))
    run = sample_run()
    await bundle.create(run)
    await bundle.write_step(Step(run_id=run.id, index=0, url=cap.url), cap)
    await bundle.write_finding(sample_finding())
    cand = Candidate(step_index=0, sighted_text="x", sr_quote="y")
    await bundle.write_rejected(Rejected(id="x-1", run_id=run.id, step_index=0, candidate=cand, verifier=VerifierResult(passed=False)))
    bundle.add_trace(run.id, ModelCall(id="c1", run_id=run.id, stage="seer", model="m"))
    bundle.add_event(run.id, Event(type="run.started", run_id=run.id))
    await bundle.flush(run.id)
    await bundle.write_run(run)
    listed = set(await bundle.store.list(f"runs/{run.id}/"))
    assert listed == {
        "runs/run1/run.json", "runs/run1/steps/0/step.json", "runs/run1/steps/0/screenshot.png", "runs/run1/steps/0/ax.json",
        "runs/run1/steps/0/axe.json", "runs/run1/findings/f-1.json", "runs/run1/rejected/x-1.json", "runs/run1/trace.jsonl", "runs/run1/events.jsonl",
    }
    assert keys.run("run1") == "runs/run1/run.json"
    loaded = await bundle.load(run.id)
    assert loaded.run == run and loaded.findings[0].id == "f-1" and loaded.rejected[0].id == "x-1"
    assert loaded.steps[0].screenshot == "steps/0/screenshot.png" and loaded.steps[0].ax_nodes == len(cap.ax_nodes)
    assert [e.type for e in loaded.events] == ["run.started"] and loaded.trace[0].stage == "seer"
    assert await bundle.read_screenshot(run.id, 0) == cap.screenshot_png
    assert await bundle.list_run_ids() == ["run1"]
    ax = json.loads(await bundle.store.get("runs/run1/steps/0/ax.json"))
    assert {"ax_nodes", "silent_nodes"} <= set(ax)


async def test_flush_rewrites_whole_event_log(tmp_path):
    bundle = RunBundle(LocalBlobStore(tmp_path))
    run = sample_run()
    await bundle.create(run)
    bundle.add_event(run.id, Event(type="a", run_id=run.id))
    bundle.add_event(run.id, Event(type="b", run_id=run.id))
    await bundle.flush(run.id)
    bundle.add_event(run.id, Event(type="c", run_id=run.id))
    await bundle.flush(run.id)
    lines = (await bundle.store.get("runs/run1/events.jsonl")).decode().splitlines()
    assert [json.loads(line)["type"] for line in lines] == ["a", "b", "c"]
    assert [e.type for e in await bundle.events(run.id)] == ["a", "b", "c"]


async def test_load_missing_run_raises(tmp_path):
    bundle = RunBundle(LocalBlobStore(tmp_path))
    with pytest.raises(KeyError):
        await bundle.load("nope")
