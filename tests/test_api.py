import json
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from parity.app import create_app
from parity.config import load_settings
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


@pytest_asyncio.fixture
async def api(tmp_path):
    await make_replay_bundle(tmp_path / "replay")
    settings = load_settings(env={
        "PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
        "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay"),
    })
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, app


def parse_sse(body: str) -> list[tuple[str, dict]]:
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


async def test_health_reports_storage_and_index(api):
    client, _ = api
    body = (await client.get("/api/health")).json()
    assert body["ok"] is True and body["storage"] == "local" and body["runs_indexed"] == 0
    assert body["mode_default"] == "replay" and body["has_key"] is False


async def test_flows_lists_checkout(api):
    client, _ = api
    flows = (await client.get("/api/flows")).json()
    assert [f["id"] for f in flows] == ["checkout"] and flows[0]["start_url"] == "/store/checkout.html"


async def test_post_replay_run_streams_hero(api):
    client, _ = api
    r = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    assert run_id != SRC and r.json()["mode"] == "replay" and r.json()["replay_of"] == SRC
    stream = await client.get(f"/api/runs/{run_id}/events")
    assert stream.status_code == 200 and stream.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(stream.text)
    types = [t for t, _ in events]
    assert types[0] == "run.started" and types[-1] == "run.finished"
    hero = next(d for t, d in events if t == "verifier.result")
    assert hero["finding"]["sighted_text"] == "Pay R1,249" and hero["finding"]["run_id"] == run_id
    assert all(d["run_id"] == run_id for _, d in events if d) and all(d["mode"] == "replay" for _, d in events if d)


async def test_events_after_finish_replays_history_then_closes(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    first = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    second = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert [t for t, _ in first] == [t for t, _ in second] and second[-1][0] == "run.finished"
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["status"] == "done" and detail["run"]["mode"] == "replay"


async def test_get_run_detail_includes_trace(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["id"] == run_id and detail["findings"][0]["sr_name"] == "Submit"
    assert detail["trace"][0]["stage"] == "comparator" and detail["trace"][0]["request_id"] == "req-1"
    assert detail["steps"][0]["screenshot"] == "steps/0/screenshot.png"
    listed = (await client.get("/api/runs")).json()
    assert [r["id"] for r in listed] == [run_id]


async def test_screenshot_png_content_type(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    r = await client.get(f"/api/runs/{run_id}/steps/0/screenshot.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert (await client.get(f"/api/runs/{run_id}/steps/9/screenshot.png")).status_code == 404


async def test_unknown_flow_404(api):
    client, _ = api
    assert (await client.post("/api/runs", json={"flow_id": "nope", "mode": "replay"})).status_code == 404
    assert (await client.get("/api/runs/nope")).status_code == 404
    assert (await client.get("/api/runs/nope/events")).status_code == 404


async def test_post_live_without_key_503(api):
    client, _ = api
    r = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    assert r.status_code == 503 and "MODEL_API_KEY" in r.json()["detail"]
