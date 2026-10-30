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
