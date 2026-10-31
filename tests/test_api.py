import json

import httpx
import pytest
import pytest_asyncio

from tests.helpers import SRC, parse_sse


async def test_health_reports_storage_and_index(api):
    client, _ = api
    body = (await client.get("/api/health")).json()
    assert body["ok"] is True and body["storage"] == "local" and body["runs_indexed"] == 0
    assert body["mode_default"] == "replay" and body["has_key"] is False
    assert body["replay_flows"] == {"checkout": "hero-src"}


async def test_flows_lists_checkout(api):
    client, _ = api
    flows = (await client.get("/api/flows")).json()
    assert [f["id"] for f in flows] == ["checkout", "purchase"] and flows[0]["start_url"] == "/store/checkout.html"
    assert flows[1]["single_page"] is False and len(flows[1]["pages"]) == 4


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
    assert detail["run"]["status"] == "awaiting_review" and detail["run"]["mode"] == "replay"


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


async def test_verifier_off_route(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")
    r = await client.get(f"/api/runs/{run_id}/verifier-off")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id and body["reported"] == 1 and body["verified"] == 1 and body["rejected_by_verifier"] == 0
    assert (await client.get("/api/runs/nope/verifier-off")).status_code == 404


async def test_second_live_post_gets_429_while_first_runs(api, tmp_path):
    """The Live slot is taken in the handler, not later in the task, so a double click cannot queue two runs."""
    from parity.meta.fake import FakeMetaClient

    client, app = api
    app.state.client = FakeMetaClient(tmp_path / "none")  # a live run will fail fast (no fixtures), which is fine here
    first = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    second = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    assert first.status_code == 202 and second.status_code == 429 and "Retry-After" in second.headers
    run_id = first.json()["run_id"]
    stream = await client.get(f"/api/runs/{run_id}/events")  # connected right after the POST: must not 404 and must not be empty
    events = parse_sse(stream.text)
    assert events and events[0][0] == "run.started" and events[-1][0] in ("run.finished", "run.failed")
    app.state.client = None


async def test_replay_writes_final_state_before_terminal_event(api):
    import asyncio

    client, app = api
    st = app.state
    from parity import replay as replay_mod

    run = await replay_mod.start(SRC, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=0)
    seen = []
    async for ev in st.bus.subscribe(run.id):
        if ev.type == "run.finished":
            seen.append((await st.bundle.load(run.id)).run.status)
    await asyncio.sleep(0)
    assert seen == ["awaiting_review"]


async def replayed_run(client) -> str:
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")  # drain: the replay has finished
    return run_id


async def test_decision_requires_reason(api):
    client, _ = api
    run_id = await replayed_run(client)
    url = f"/api/runs/{run_id}/findings/{run_id}-f01/decision"
    assert (await client.post(url, json={"decision": "approve", "reason": "   "})).status_code == 422
    assert (await client.post(url, json={"decision": "maybe", "reason": "x"})).status_code == 422
    assert (await client.post(f"/api/runs/{run_id}/findings/nope/decision", json={"decision": "approve", "reason": "x"})).status_code == 404
    assert (await client.post(f"/api/runs/nope/findings/x/decision", json={"decision": "approve", "reason": "x"})).status_code == 404
    assert (await client.get(f"/api/runs/{run_id}/patch")).status_code == 404  # nothing approved yet


async def test_decision_records_and_patch_contains_only_approved(api):
    client, _ = api
    run_id = await replayed_run(client)
    fid = f"{run_id}-f01"
    r = await client.post(f"/api/runs/{run_id}/findings/{fid}/decision", json={"decision": "approve", "reason": "Looks right"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["finding"]["status"] == "approved" and body["finding"]["decision"]["reason"] == "Looks right"
    assert body["run"]["status"] == "done"  # nothing left to review
    patch = await client.get(f"/api/runs/{run_id}/patch")
    assert patch.status_code == 200 and patch.headers["content-type"].startswith("text/x-diff")
    assert "+++ b/store/checkout.html" in patch.text and "Pay R1,249" in patch.text
    events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert events[-1][0] == "decision.recorded" and events[-1][1]["decision"]["decision"] == "approve" and events[-1][1]["run_status"] == "done"
    assert (await client.post(f"/api/runs/{run_id}/findings/{fid}/decision", json={"decision": "reject", "reason": "changed my mind"})).status_code == 409
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["status"] == "done" and detail["findings"][0]["status"] == "approved"
    assert [r["status"] for r in (await client.get("/api/runs")).json() if r["id"] == run_id] == ["done"]


async def test_rejected_fix_leaves_no_patch(api):
    client, _ = api
    run_id = await replayed_run(client)
    r = await client.post(f"/api/runs/{run_id}/findings/{run_id}-f01/decision", json={"decision": "reject", "reason": "Not a barrier in context"})
    assert r.status_code == 200 and r.json()["finding"]["status"] == "rejected" and r.json()["run"]["status"] == "done"
    assert (await client.get(f"/api/runs/{run_id}/patch")).status_code == 404
