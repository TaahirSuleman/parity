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


async def test_boot_indexes_recovers_and_caps_replays_in_one_pass(tmp_path):
    """Boot on a bucket must not read every bundle twice, and Replay copies must not pile up: one pass indexes, fails the
    interrupted run with a terminal event, and evicts the oldest Replay copies beyond the cap."""
    from parity.store.blob import LocalBlobStore
    from parity.store.bundle import RunBundle
    from parity.store.index import RunIndex
    from parity.store.models import RunMode, RunStatus
    from tests.test_bundle import sample_run

    store = LocalBlobStore(tmp_path / "data")
    reads: list[str] = []
    original_get = store.get

    async def counted_get(key):
        reads.append(key)
        return await original_get(key)

    store.get = counted_get  # type: ignore[method-assign]
    bundle = RunBundle(store)
    live = sample_run("20261101-100000-live", RunStatus.running)
    await bundle.create(live)
    for i, stamp in enumerate(("20261101-110000", "20261101-120000", "20261101-130000")):
        r = sample_run(f"{stamp}-rep{i}", RunStatus.done)
        r.mode = RunMode.replay
        r.replay_of = "hero-checkout"
        await bundle.create(r)
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        result = await index.boot(bundle, replay_keep=2)
    finally:
        await index.close()
    run_json_reads = [k for k in reads if k.endswith("/run.json")]  # counted before the assertions below load bundles themselves
    evicted_reads = [k for k in reads if "/20261101-110000-rep0/" in k and not k.endswith("/run.json")]
    assert evicted_reads == [], evicted_reads  # an evicted copy costs one run.json read, nothing more
    assert result["recovered"] == ["20261101-100000-live"] and result["evicted"] == ["20261101-110000-rep0"] and result["indexed"] == 3
    ids = await bundle.list_run_ids()
    assert "20261101-110000-rep0" not in ids and {"20261101-120000-rep1", "20261101-130000-rep2", "20261101-100000-live"} <= set(ids)
    assert (await bundle.load("20261101-100000-live")).run.status == RunStatus.failed
    assert (await bundle.load("20261101-100000-live")).events[-1].type == "run.failed"
    assert len(run_json_reads) <= 4, run_json_reads  # each bundle's run.json read once


async def test_boot_rebuilds_the_index_from_scratch_and_orders_eviction_by_start_time(tmp_path):
    """Rows for bundles that are gone disappear at boot (they listed runs whose detail was 404), and the newest copies are decided
    by started_at, not by id (two ids minted in one second sort by their random suffix)."""
    from datetime import timedelta

    from parity.store.models import RunMode, now

    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    await index.upsert_run(sample_run("ghost-no-bundle", RunStatus.done))
    older, newer = sample_run("20261101-120000-ffff", RunStatus.done), sample_run("20261101-120000-0000", RunStatus.done)
    for run, age in ((older, 10), (newer, 5)):
        run.mode, run.replay_of, run.started_at = RunMode.replay, "hero-checkout", now() - timedelta(minutes=age)
        await bundle.create(run)
    try:
        result = await index.boot(bundle, replay_keep=1, replay_min_age_s=0)
        listed = {r.id for r in await index.list_runs()}
    finally:
        await index.close()
    assert result["evicted"] == ["20261101-120000-ffff"] and listed == {"20261101-120000-0000"}, (result, listed)


async def test_young_replay_copies_survive_the_cap_at_boot(tmp_path):
    """A judge still reviewing a finished Replay must not lose it because twenty others clicked: beyond the cap only copies older
    than replay_min_age_s are evicted."""
    from datetime import timedelta

    from parity.store.models import RunMode, now

    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    for rid, age_min in (("20261101-090000-aaaa", 180), ("20261101-115000-bbbb", 10), ("20261101-115500-cccc", 5)):
        run = sample_run(rid, RunStatus.done)
        run.mode, run.replay_of, run.started_at, run.finished_at = RunMode.replay, "hero-checkout", now() - timedelta(minutes=age_min), now() - timedelta(minutes=age_min)
        await bundle.create(run)
    try:
        result = await index.boot(bundle, replay_keep=1, replay_min_age_s=3600)
    finally:
        await index.close()
    assert result["evicted"] == ["20261101-090000-aaaa"], result
