"""Shared test helpers."""

import json
from pathlib import Path

from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.models import Capture, Event, ModelCall, RunMode, RunStatus, Step
from tests.test_bundle import sample_finding, sample_run

FIXTURE = Path(__file__).parent / "fixtures" / "capture_checkout.json"
SRC = "hero-src"


async def make_replay_bundle(root: Path) -> None:
    """A small but complete bundle: one step, the hero finding, a trace row and the event log."""
    bundle = RunBundle(LocalBlobStore(root))
    run = sample_run(SRC, RunStatus.done)
    run.mode = RunMode.live
    run.findings_verified, run.axe_violations, run.tokens, run.cost_usd = 1, 0, 1234, 0.0021
    await bundle.create(run)
    cap = Capture.model_validate_json(FIXTURE.read_text())
    cap.screenshot_png = FIXTURE.with_suffix(".png").read_bytes()
    await bundle.write_step(Step(run_id=SRC, index=0, url=cap.url), cap)
    finding = sample_finding(SRC, f"{SRC}-f01")
    await bundle.write_finding(finding)
    bundle.add_trace(SRC, ModelCall(id=f"{SRC}-c1", run_id=SRC, stage="comparator", model="muse-spark-1.3-contributor", total_tokens=1234, cost_usd=0.0021, request_id="req-1"))
    for ev in (
        Event(type="run.started", run_id=SRC, data={"flow_id": "checkout", "mode": "live"}),
        Event(type="step.captured", run_id=SRC, data={"index": 0, "axe_violations": 0}),
        Event(type="model.call", run_id=SRC, data={"stage": "comparator", "tokens": 1234}),
        Event(type="verifier.result", run_id=SRC, data={"passed": True, "finding_id": finding.id, "finding": finding.model_dump(mode="json")}),
        Event(type="run.finished", run_id=SRC, data={"findings_verified": 1}),
    ):
        bundle.add_event(SRC, ev)
    await bundle.flush(SRC)




def parse_sse(body: str) -> list[tuple[str, dict]]:
    """SSE body -> [(event type, data)], tolerant of \r\n and comment pings."""
    events = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        etype, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                etype = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if etype:
            events.append((etype, data))
    return events
