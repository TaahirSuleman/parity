"""Defects a judge could hit on the demo path (pre-stretch QA gate, 2 Nov): the Live slot leaking on a storage error, a replay that
never sends its terminal event when the final write fails, and the replayed run.started not naming its source."""
import asyncio
from pathlib import Path

import httpx

from parity import replay
from parity.api.events import EventBus
from parity.meta.fake import FakeMetaClient
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from tests.test_api import _app_with

REPLAY_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "replay"


async def test_live_slot_is_released_when_the_start_fails_after_taking_it(tmp_path):
    """A storage error between taking the Live slot and starting the run (fresh_run_id reads the bucket) answered 500 and kept the slot:
    every later Live click got 429 'already in progress' until a restart."""
    app = await _app_with(tmp_path)
    async with app.router.lifespan_context(app):
        app.state.client = FakeMetaClient(tmp_path / "none")
        real_exists, calls = app.state.bundle.exists, []

        async def exists_once_broken(run_id: str) -> bool:
            calls.append(run_id)
            if len(calls) == 1:
                raise RuntimeError("bucket unavailable")
            return await real_exists(run_id)

        app.state.bundle.exists = exists_once_broken
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
            first = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
            assert first.status_code == 500
            second = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
            assert second.status_code == 202, second.text
            events = (await client.get(f"/api/runs/{second.json()['run_id']}/events")).text
            assert "run.finished" in events or "run.failed" in events


async def _collect(bus: EventBus, run_id: str, timeout: float = 3.0) -> list:
    seen = []

    async def go():
        async for ev in bus.subscribe(run_id):
            seen.append(ev)
            if ev.type in ("run.finished", "run.failed"):
                return

    await asyncio.wait_for(go(), timeout)
    return seen


async def test_replay_sends_a_terminal_event_even_when_its_final_write_fails(tmp_path):
    """If the final write raised, no terminal event reached subscribers: the page stayed on 'Auditing…' while run.json said otherwise."""
    source = RunBundle(LocalBlobStore(REPLAY_ROOT))
    dest = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.sqlite")
    await index.init()
    bus = EventBus(dest)
    real_write_run, failures = dest.write_run, []

    async def write_run_broken_once(run):
        if not failures and run.status.value in ("awaiting_review", "done"):
            failures.append(run.id)
            raise OSError("bucket write failed")
        return await real_write_run(run)

    dest.write_run = write_run_broken_once
    tasks: set[asyncio.Task] = set()
    try:
        run = await replay.start("hero-checkout", source, bus, dest, index, pace_ms=0, tasks=tasks)
        seen = await _collect(bus, run.id)
        assert failures, "the broken write was never exercised"
        assert seen[-1].type in ("run.finished", "run.failed"), [e.type for e in seen][-3:]
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await index.close()


async def test_replayed_run_started_names_the_recorded_run(tmp_path):
    """The header's tooltip read 'Replay of recorded run ' with nothing after it: the replayed run.started carried no replay_of."""
    source = RunBundle(LocalBlobStore(REPLAY_ROOT))
    dest = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.sqlite")
    await index.init()
    bus = EventBus(dest)
    tasks: set[asyncio.Task] = set()
    try:
        run = await replay.start("hero-checkout", source, bus, dest, index, pace_ms=0, tasks=tasks)
        seen = await _collect(bus, run.id)
        assert seen[0].type == "run.started" and seen[0].data.get("replay_of") == "hero-checkout", seen[0].data
    finally:
        await asyncio.gather(*tasks, return_exceptions=True)
        await index.close()
