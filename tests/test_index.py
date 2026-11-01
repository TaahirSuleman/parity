from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.store.models import ModelCall, RunStatus
from tests.test_bundle import sample_finding, sample_run


import pytest_asyncio


@pytest_asyncio.fixture
async def store(tmp_path):
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    yield bundle, index
    await index.close()


async def test_index_rebuild_matches_bundles(store):
    bundle, index = store
    for rid in ("r1", "r2"):
        run = sample_run(rid, RunStatus.done)
        await bundle.create(run)
        await bundle.write_finding(sample_finding(rid, f"{rid}-f"))
        bundle.add_trace(rid, ModelCall(id=f"{rid}-c", run_id=rid, stage="seer", model="m", total_tokens=10, cost_usd=0.01))
        await bundle.flush(rid)
    assert await index.list_runs() == []
    count = await index.rebuild(bundle)
    runs = await index.list_runs()
    assert count == 2 and sorted(r.id for r in runs) == ["r1", "r2"]
    assert [f.id for f in await index.findings_for("r1")] == ["r1-f"]
    assert [c.id for c in await index.calls_for("r2")] == ["r2-c"]
    # rebuild is idempotent
    assert await index.rebuild(bundle) == 2 and len(await index.list_runs()) == 2


async def test_upsert_run_updates_in_place(store):
    _, index = store
    run = sample_run("r1")
    await index.upsert_run(run)
    run.status = RunStatus.done
    run.cost_usd = 0.02
    await index.upsert_run(run)
    [stored] = await index.list_runs()
    assert stored.status == RunStatus.done and stored.cost_usd == 0.02


async def test_recover_interrupted_marks_failed(store):
    bundle, index = store
    await bundle.create(sample_run("stuck", RunStatus.running))
    await bundle.create(sample_run("queued", RunStatus.queued))
    await bundle.create(sample_run("fine", RunStatus.done))
    recovered = await index.recover_interrupted(bundle)
    assert sorted(recovered) == ["queued", "stuck"]
    stuck = (await bundle.load("stuck")).run
    assert stuck.status == RunStatus.failed and stuck.error == "interrupted by restart" and stuck.finished_at is not None
    assert (await bundle.load("fine")).run.status == RunStatus.done
    assert {r.id: r.status for r in await index.list_runs()}["stuck"] == RunStatus.failed


async def test_recovery_skips_an_unreadable_bundle(tmp_path):
    """One corrupt run.json must not stop the server from booting."""
    from parity.store.blob import LocalBlobStore
    from parity.store.bundle import RunBundle
    from parity.store.index import RunIndex
    from parity.store.models import RunStatus
    from tests.test_bundle import sample_run

    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    await bundle.create(sample_run("good-run", RunStatus.running))
    (tmp_path / "data" / "runs" / "bad-run").mkdir(parents=True)
    (tmp_path / "data" / "runs" / "bad-run" / "run.json").write_text("{not json")
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        recovered = await index.recover_interrupted(bundle)
        assert recovered == ["good-run"]
        assert await index.rebuild(bundle) >= 1
    finally:
        await index.close()


async def test_recovery_leaves_a_terminal_event(store):
    """A run cut off by a restart must end its event log with run.failed, or a browser opening its link streams the history
    and then reconnects forever waiting for an end that never comes."""
    from parity.store.models import Event

    bundle, index = store
    await bundle.create(sample_run("stuck", RunStatus.running))
    bundle.add_event("stuck", Event(type="run.started", run_id="stuck", data={"flow_id": "checkout"}))
    await bundle.flush("stuck")
    await index.recover_interrupted(bundle)
    events = (await bundle.load("stuck")).events
    assert events[-1].type == "run.failed" and "interrupted by restart" in str(events[-1].data.get("error"))
    # a bundle with no event log at all gets the same terminal line
    await bundle.create(sample_run("silent", RunStatus.running))
    await index.recover_interrupted(bundle)
    assert [e.type for e in (await bundle.load("silent")).events] == ["run.failed"]
