import json
from pathlib import Path

import pytest

from parity.api.events import EventBus
from parity.config import load_settings
from parity.flows import FLOWS
from parity.meta.client import MetaError, TraceRouter
from parity.meta.fake import FakeMetaClient
from parity.pipeline.audit import RunContext
from parity.pipeline.runner import run_single_page
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.store.models import RunStatus
from tests.test_bundle import sample_finding, sample_run

META = Path(__file__).parent / "fixtures" / "meta"


def stage_defaults() -> dict[str, dict]:
    manifest = json.loads((META / "manifest.json").read_text())
    return {stage: json.loads((META / name).read_text()) for stage, name in manifest.items()}


import contextlib


@contextlib.asynccontextmanager
async def harness(tmp_path, client_kwargs):
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data")})
    router = TraceRouter()
    client = FakeMetaClient(META, trace=router, stage_defaults=stage_defaults(), **client_kwargs)
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        yield settings, client, EventBus(bundle), bundle, index
    finally:
        await index.close()


async def test_runner_hero_end_to_end(tmp_path, server_url, page):
    async def page_factory():
        return page

    async with harness(tmp_path, {}) as (settings, client, bus, bundle, index):
        run = await run_single_page(settings, client, bus, bundle, index, FLOWS["checkout"], base_url=server_url, page_factory=page_factory)
        calls = await index.calls_for(run.id)
        listed = await index.list_runs()
    assert run.status == RunStatus.done, run.error
    assert run.axe_violations == 0 and run.findings_verified >= 1 and run.tokens > 0 and run.duration_ms > 0
    loaded = await bundle.load(run.id)
    hero = [f for f in loaded.findings if f.element.dom_id == "f5"]
    assert len(hero) == 1 and hero[0].sr_name == "Submit" and hero[0].sighted_text == "Pay R1,249"
    assert hero[0].judgement is not None and hero[0].status == "judged"
    types = [e.type for e in loaded.events if e.type != "model.call"]
    assert types[:4] == ["run.started", "step.captured", "seer.done", "comparator.candidates"]
    assert "verifier.result" in types and "judge.result" in types and types[-1] == "run.finished"
    assert any(e.type == "model.call" and e.data["stage"] == "comparator" for e in loaded.events)
    assert len(loaded.trace) >= 3 and listed[0].id == run.id
    assert await bundle.read_screenshot(run.id, 0)
    assert [c.stage for c in calls][:2] == ["seer", "comparator"]


async def test_runner_meta_error_marks_failed(tmp_path, server_url, page):
    err = MetaError("server_error", status=500, request_id="req-500", attempts=3)
    async def page_factory():
        return page

    async with harness(tmp_path, {"errors": {"comparator": err}}) as (settings, client, bus, bundle, index):
        run = await run_single_page(settings, client, bus, bundle, index, FLOWS["checkout"], base_url=server_url, page_factory=page_factory)
    assert run.status == RunStatus.failed and "req-500" in (run.error or "")
    loaded = await bundle.load(run.id)
    assert loaded.run.status == RunStatus.failed and loaded.run.error == run.error
    assert [c.stage for c in loaded.trace] == ["seer"]
    assert [e.type for e in loaded.events][-1] == "run.failed"


async def test_index_failure_does_not_fail_write(tmp_path):
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data")})
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))

    class BrokenIndex:
        async def upsert_finding(self, finding):
            raise RuntimeError("disk full")

        async def upsert_run(self, run):
            raise RuntimeError("disk full")

        async def insert_call(self, call):
            raise RuntimeError("disk full")

    run = sample_run("r1")
    await bundle.create(run)
    ctx = RunContext(settings=settings, client=None, bus=EventBus(bundle), bundle=bundle, index=BrokenIndex(), run=run, base_url="http://x")
    await ctx.save_finding(sample_finding("r1", "f-1"))
    await ctx.save_run()
    assert (await bundle.load("r1")).findings[0].id == "f-1"


async def test_unknown_flow_raises():
    with pytest.raises(KeyError):
        FLOWS["nope"]
