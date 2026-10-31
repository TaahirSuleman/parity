"""End-to-end integration: the served app, SSE under stress, boot recovery, the Live slot.

This layer exercises the wiring the hosted demo relies on — uvicorn, real Chromium, the REST
routes, the event bus, the runner and the bundle store together. The model is always a recorded
fake: no network, no spend. Every later phase adds its integration tests here first (TDD).
"""

import asyncio
import socket
import threading
import time

import httpx
import pytest

from parity.meta.fake import FakeMetaClient
from tests.helpers import make_replay_bundle, parse_sse
from tests.test_runner import META, stage_defaults


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """The real app on a real port with PORT set, so Live runs navigate to the port actually bound."""
    import uvicorn

    from parity.app import create_app
    from parity.config import load_settings

    root = tmp_path_factory.mktemp("parity-live")
    asyncio.run(make_replay_bundle(root / "replay"))
    port = _free_port()
    settings = load_settings(env={
        "PARITY_DATA_DIR": str(root / "data"), "PARITY_CACHE_DIR": str(root / "cache"),
        "PARITY_INDEX_PATH": str(root / "index.db"), "PARITY_REPLAY_DIR": str(root / "replay"),
        "PORT": str(port),
    })
    app = create_app(settings)
    app.state.client = FakeMetaClient(META, trace=app.state.trace, stage_defaults=stage_defaults())
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn did not start"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


async def _drain_sse(client: httpx.AsyncClient, url: str) -> list[tuple[str, dict]]:
    lines = []
    async with client.stream("GET", url) as stream:
        async for line in stream.aiter_lines():
            lines.append(line)
    return parse_sse("\n".join(lines))


async def test_live_checkout_end_to_end_through_the_served_app(live_server):
    """POST /runs live → agentless pipeline on the real store → SSE to run.finished → bundle readable."""
    async with httpx.AsyncClient(base_url=live_server, timeout=120) as client:
        r = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]
        events = await _drain_sse(client, f"/api/runs/{run_id}/events")
        types = [t for t, _ in events]
        assert types[0] == "run.started" and types[-1] == "run.finished", types
        finished = events[-1][1]
        assert finished["findings_verified"] >= 1 and finished["axe_violations"] == 0
        assert any(t == "verifier.result" and d["finding"]["sighted_text"] == "Pay R1,249" for t, d in events)

        detail = (await client.get(f"/api/runs/{run_id}")).json()
        assert detail["run"]["status"] == "awaiting_review" and detail["run"]["mode"] == "live"
        assert detail["findings"] and detail["trace"] and detail["steps"]
        hero = next(f for f in detail["findings"] if f["element"]["dom_id"] == "f5")
        assert hero["fix"] and hero["reaudit"]["gap_closed"] is True and hero["status"] == "reaudited"
        # the human gate: approving the one fix finishes the run and exports the patch
        r = await client.post(f"/api/runs/{run_id}/findings/{hero['id']}/decision", json={"decision": "approve", "reason": "Re-audit shows the price is announced"})
        assert r.status_code == 200 and r.json()["run"]["status"] == "done"
        patch = await client.get(f"/api/runs/{run_id}/patch")
        assert patch.status_code == 200 and "+++ b/store/checkout.html" in patch.text
        assert (await client.get(f"/api/runs/{run_id}")).json()["run"]["status"] == "done"
        assert (await client.get(f"/api/runs/{run_id}/verifier-off")).status_code == 200
        shot = await client.get(f"/api/runs/{run_id}/steps/0/screenshot.png")
        assert shot.status_code == 200 and shot.content[:4] == b"\x89PNG"

        # the Live slot was released by the finished run: a second run starts and finishes too
        second = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
        assert second.status_code == 202, second.text
        events2 = await _drain_sse(client, f"/api/runs/{second.json()['run_id']}/events")
        assert [t for t, _ in events2][-1] == "run.finished"
        listed = (await client.get("/api/runs")).json()
        assert {run_id, second.json()["run_id"]} <= {r["id"] for r in listed}


async def test_boot_recovery_fails_interrupted_runs(tmp_path):
    """A run left `running` by a crash comes back failed after a restart, visible through the API."""
    from parity.app import create_app
    from parity.config import load_settings
    from parity.store.blob import LocalBlobStore
    from parity.store.bundle import RunBundle
    from parity.store.models import RunStatus
    from tests.test_bundle import sample_run

    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    run = sample_run("crashed-run", RunStatus.running)
    await bundle.create(run)
    await bundle.flush("crashed-run")

    settings = load_settings(env={
        "PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
        "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay"),
    })
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            listed = (await client.get("/api/runs")).json()
            assert [r["id"] for r in listed] == ["crashed-run"]
            assert listed[0]["status"] == "failed" and "interrupted" in listed[0]["error"]
            detail = (await client.get("/api/runs/crashed-run")).json()
            assert detail["run"]["status"] == "failed"


async def test_sse_reconnect_mid_run_replays_full_history(api):
    """A viewer who drops mid-run and reconnects sees the whole run, start to finish."""
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 150})).json()["run_id"]
    seen = 0
    async with client.stream("GET", f"/api/runs/{run_id}/events") as stream:
        async for line in stream.aiter_lines():
            if line.startswith("event:"):
                seen += 1
                if seen >= 2:
                    break  # drop the connection while the run is still pacing out events
    full = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    types = [t for t, _ in full]
    assert seen == 2 and types[0] == "run.started" and types[-1] == "run.finished" and len(types) == 8


async def test_twenty_concurrent_subscribers_see_identical_streams(api):
    """Several judges watching one run (the demo) all get the same events."""
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 100})).json()["run_id"]
    bodies = await asyncio.gather(*(client.get(f"/api/runs/{run_id}/events") for _ in range(20)))
    streams = [[t for t, _ in parse_sse(b.text)] for b in bodies]
    assert streams[0][-1] == "run.finished" and len(streams[0]) == 8
    assert all(s == streams[0] for s in streams)


async def test_two_concurrent_replay_runs_stay_isolated(api):
    """Two runs at once: each stream carries only its own run's events."""
    client, _ = api
    ids = []
    for _ in range(2):
        ids.append((await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 100})).json()["run_id"])
    assert ids[0] != ids[1]
    bodies = await asyncio.gather(*(client.get(f"/api/runs/{rid}/events") for rid in ids))
    for rid, body in zip(ids, bodies):
        events = parse_sse(body.text)
        assert [t for t, _ in events][-1] == "run.finished"
        assert all(d["run_id"] == rid for _, d in events if d)


async def test_live_slot_frees_after_a_failed_run(api, tmp_path):
    """A failed Live run must release the slot, or one crash locks the hosted demo until restart."""
    client, app = api
    app.state.client = FakeMetaClient(tmp_path / "none")  # no fixtures and no served port: fails fast
    first = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    assert first.status_code == 202
    events = parse_sse((await client.get(f"/api/runs/{first.json()['run_id']}/events")).text)
    assert events[-1][0] == "run.failed"
    second = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    assert second.status_code == 202, "the slot was not released by the failed run"
    events2 = parse_sse((await client.get(f"/api/runs/{second.json()['run_id']}/events")).text)
    assert events2[-1][0] == "run.failed"
    app.state.client = None


async def test_browser_shutdown_from_another_loop_returns_quickly():
    """A browser launched on one loop (the server thread) must not deadlock shutdown() on another."""
    import threading

    from parity.pipeline import browser

    ready, stop = threading.Event(), threading.Event()

    def spin():
        async def boot():
            page = await browser.new_page()
            await page.context.close()
            ready.set()
            while not stop.is_set():  # keep the loop alive, like a running server
                await asyncio.sleep(0.05)

        asyncio.run(boot())

    thread = threading.Thread(target=spin, daemon=True)
    thread.start()
    assert ready.wait(30), "the server-thread browser never came up"
    try:
        await asyncio.wait_for(browser.shutdown(), timeout=5)  # hung forever before the fix
    finally:
        stop.set()
        thread.join(timeout=10)


async def test_decision_on_a_replay_run_through_the_served_app(live_server):
    """What a judge does: watch the replay, approve the fix, download the patch."""
    async with httpx.AsyncClient(base_url=live_server, timeout=60) as client:
        run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
        events = await _drain_sse(client, f"/api/runs/{run_id}/events")
        assert events[-1][0] == "run.finished" and events[-1][1]["status"] == "awaiting_review"
        r = await client.post(f"/api/runs/{run_id}/findings/{run_id}-f01/decision", json={"decision": "approve", "reason": "ok"})
        assert r.status_code == 200, r.text
        history = await _drain_sse(client, f"/api/runs/{run_id}/events")
        assert history[-1][0] == "decision.recorded" and history[-1][1]["finding_id"] == f"{run_id}-f01"
        assert (await client.get(f"/api/runs/{run_id}/patch")).status_code == 200


async def test_committed_replay_bundles_load_and_replay(tmp_path):
    """The judges' primary path: the bundles committed under fixtures/replay are discovered at boot and replay cleanly."""
    from pathlib import Path

    from parity.app import create_app
    from parity.config import load_settings

    settings = load_settings(env={
        "PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"), "PARITY_INDEX_PATH": str(tmp_path / "index.db"),
        "PARITY_REPLAY_DIR": str(Path(__file__).resolve().parents[1] / "fixtures" / "replay"),
    })
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            health = (await client.get("/api/health")).json()
            assert health["replay_flows"] == {"checkout": "hero-checkout", "purchase": "hero-purchase"}
            expected = {"checkout": (6, 1), "purchase": (11, 2)}  # verified, rejected (honest counts: repeats are no longer red rows)
            for flow, (verified, rejected) in expected.items():
                run_id = (await client.post("/api/runs", json={"flow_id": flow, "mode": "replay", "pace_ms": 0})).json()["run_id"]
                events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
                assert events[0][0] == "run.started" and events[-1][0] == "run.finished", flow
                assert events[-1][1]["status"] == "awaiting_review" and events[-1][1]["findings_verified"] == verified
                detail = (await client.get(f"/api/runs/{run_id}")).json()
                assert len(detail["findings"]) == verified and len(detail["rejected"]) == rejected and detail["steps"]
                assert all(f["fix"] is None or f["fix"]["diff"].startswith("--- a/store/") for f in detail["findings"])
                hero = next((f for f in detail["findings"] if f["element"]["dom_id"] == "f5"), None)
                assert hero and hero["fix"] and hero["reaudit"]["gap_closed"] is True, flow
                assert (await client.get(f"/api/runs/{run_id}/steps/0/screenshot.png")).status_code == 200
                # a completed agent turn is not an error: the trace must only carry real failures (HTTP status / transport)
                assert all(c["error"] is None or c["http_status"] is None or c["http_status"] >= 400 for c in detail["trace"]), flow
