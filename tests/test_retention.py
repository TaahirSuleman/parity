"""Retention for pages visitors choose (spec §19.3.4, Task 26F.4): page content goes after 24 hours, a summary stays, an
evicted run answers 410, store runs and young runs are untouched, and eviction runs at boot and hourly."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

import httpx
import pytest_asyncio

from parity.replay import evict_external
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.store.models import Capture, Event, ModelCall, Run, RunMode, RunStatus, Step, now
from tests.helpers import FIXTURE
from tests.test_bundle import sample_finding


@pytest_asyncio.fixture
async def store(tmp_path):
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    yield bundle, index
    await index.close()


async def seed_run(bundle: RunBundle, index: RunIndex | None, run_id: str, *, age_s: int, source: str = "visitor-url", origin: str = "https://a.example") -> Run:
    """A finished run with everything a bundle holds: a step (screenshot, tree, axe, source), a finding, a trace row, events."""
    t = now() - timedelta(seconds=age_s)
    visitor = source == "visitor-url"
    run = Run(id=run_id, mode=RunMode.live, flow_id="url-aaaaaaaa" if visitor else "checkout", goal="read", target_url=f"{origin}/secret-page", status=RunStatus.done,
              started_at=t - timedelta(seconds=120), finished_at=t, duration_ms=120000, findings_verified=1, findings_rejected=1, axe_violations=2,
              tokens=1500, cost_usd=0.12, source=source, origin=origin if visitor else "", consent_at=t - timedelta(seconds=130) if visitor else None,
              screens=1 if visitor else None)
    await bundle.create(run)
    cap = Capture.model_validate_json(FIXTURE.read_text())
    cap.screenshot_png = FIXTURE.with_suffix(".png").read_bytes()
    cap.html = "<html><body>secret page text</body></html>"
    cap.url = run.target_url
    await bundle.write_step(Step(run_id=run_id, index=0, url=cap.url), cap)
    await bundle.write_finding(sample_finding(run_id, f"{run_id}-f01"))
    bundle.add_trace(run_id, ModelCall(id=f"{run_id}-c1", run_id=run_id, stage="comparator", model="muse-spark-1.3-contributor", total_tokens=1500, cost_usd=0.12, request_id="req-1"))
    bundle.add_event(run_id, Event(type="run.started", run_id=run_id, data={"flow_id": run.flow_id, "public": visitor, "goal": "read secret page text"}))
    bundle.add_event(run_id, Event(type="run.finished", run_id=run_id, data={"status": "done", "findings_verified": 1,
                                                                            "agent": {"turns": 0, "finished": False, "finish_forced": False, "summary": "blocked by site: bot challenge"}}))
    await bundle.flush(run_id)
    if index is not None:
        await index.upsert_run(run)
    return run


async def test_evict_external_removes_page_content_after_24h_and_keeps_summary(store):
    bundle, index = store
    await seed_run(bundle, index, "v-old", age_s=25 * 3600)
    before = await bundle.store.list("runs/v-old/")
    assert any(k.endswith("screenshot.png") for k in before) and any(k.endswith("source.html") for k in before) and any(k.endswith("events.jsonl") for k in before)
    assert await evict_external(bundle, index, max_age_s=86_400) == ["v-old"]
    assert await bundle.store.list("runs/v-old/") == ["runs/v-old/summary.json"]
    summary = json.loads(await bundle.store.get("runs/v-old/summary.json"))
    assert summary["id"] == "v-old" and summary["origin"] == "https://a.example" and summary["status"] == "done" and summary["outcome"] == "blocked by site: bot challenge"
    assert summary["findings_verified"] == 1 and summary["findings_rejected"] == 1 and summary["axe_violations"] == 2 and summary["screens"] == 1
    assert summary["cost_usd"] == 0.12 and summary["duration_ms"] == 120000 and summary["consent_at"] and summary["started_at"] and summary["evicted_at"]
    assert "secret" not in json.dumps(summary)  # neither the page's text nor its path survives
    assert await index.get_run("v-old") is None
    assert await evict_external(bundle, index, max_age_s=86_400) == []  # a summary-only bundle is not a run any more


async def test_evict_external_leaves_young_and_store_runs(store):
    bundle, index = store
    await seed_run(bundle, index, "v-young", age_s=3600)
    await seed_run(bundle, index, "s-old", age_s=48 * 3600, source="flow")
    assert await evict_external(bundle, index, max_age_s=86_400) == []
    assert len(await bundle.store.list("runs/v-young/")) > 1 and len(await bundle.store.list("runs/s-old/")) > 1
    assert await index.get_run("v-young") is not None and await index.get_run("s-old") is not None


async def test_evicted_run_answers_410(api):
    client, app = api
    await seed_run(app.state.bundle, app.state.index, "v-old", age_s=25 * 3600)
    assert (await client.get("/api/runs/v-old")).status_code == 200
    assert await evict_external(app.state.bundle, app.state.index) == ["v-old"]
    r = await client.get("/api/runs/v-old")
    assert r.status_code == 410 and r.json()["detail"] == "This audit has expired: pages you choose are kept for 24 hours."
    assert (await client.get("/api/runs/v-old/events")).status_code == 404
    assert (await client.get("/api/runs/v-old/steps/0/screenshot.png")).status_code == 404
    assert (await client.get("/api/runs/never-was")).status_code == 404  # only an evicted run is "expired"
    assert (await client.post("/api/runs", json={"mode": "replay", "replay_of": "v-old"})).status_code == 404  # never a replay source
    assert "v-old" not in (await client.get("/api/health")).json()["replay_runs"]


async def test_eviction_runs_at_boot_and_is_scheduled_hourly(tmp_path):
    from parity.app import EXTERNAL_EVICT_INTERVAL_S, create_app
    from parity.config import load_settings
    from tests.helpers import make_replay_bundle

    await make_replay_bundle(tmp_path / "replay")
    data = RunBundle(LocalBlobStore(tmp_path / "data"))
    await seed_run(data, None, "v-old", age_s=25 * 3600)
    await seed_run(data, None, "v-young", age_s=60)
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
                                  "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay")})
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        assert await data.store.list("runs/v-old/") == ["runs/v-old/summary.json"]  # evicted during boot
        assert len(await data.store.list("runs/v-young/")) > 1
        assert app.state.sweep.get_name() == "evict-external" and not app.state.sweep.done() and EXTERNAL_EVICT_INTERVAL_S == 3600
        assert app.state.sweep not in app.state.tasks  # st.tasks is runs in flight: nothing waits an hour for the sweep
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/runs/v-old")).status_code == 410
            assert (await client.get("/api/health")).json()["runs_indexed"] == 1  # the young visitor run; the evicted one is no run
