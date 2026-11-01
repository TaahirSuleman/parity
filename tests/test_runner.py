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
    assert run.status == RunStatus.awaiting_review, run.error  # the hero fix is proposed and re-audited; a human decides
    assert run.axe_violations == 0 and run.findings_verified >= 1 and run.tokens > 0 and run.duration_ms > 0
    loaded = await bundle.load(run.id)
    hero = [f for f in loaded.findings if f.element.dom_id == "f5"]
    assert len(hero) == 1 and hero[0].sr_name == "Submit" and hero[0].sighted_text == "Pay R1,249"
    assert hero[0].judgement is not None and hero[0].status == "reaudited"
    assert hero[0].fix is not None and "Pay R1,249" in hero[0].fix.after_html and hero[0].reaudit is not None and hero[0].reaudit.gap_closed is True
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


async def test_final_run_state_is_written_before_the_terminal_event(tmp_path, server_url, page):
    """A reader that reacts to run.finished (the recorder, the UI's detail fetch) must see the final run.json."""
    async def page_factory():
        return page

    async with harness(tmp_path, {}) as (settings, client, bus, bundle, index):
        seen: list[str] = []

        async def watch(run_id: str):
            async for ev in bus.subscribe(run_id):
                if ev.type in ("run.finished", "run.failed"):
                    seen.append((await bundle.load(run_id)).run.status)

        import asyncio

        bus.open("fixed-id")
        watcher = asyncio.create_task(watch("fixed-id"))
        run = await run_single_page(settings, client, bus, bundle, index, FLOWS["checkout"], base_url=server_url, page_factory=page_factory, run_id="fixed-id")
        await asyncio.wait_for(watcher, 10)
    assert run.status == RunStatus.awaiting_review and seen == ["awaiting_review"]


async def test_comparator_retry_does_not_count_repeats_as_rejected(tmp_path, server_url, page):
    """Attempt 2 re-proposing an element already verified in attempt 1 is dropped silently, not shown as a red row."""
    import json as _json

    from parity.meta.fake import FakeMetaClient
    from parity.store.models import Capture

    cap = Capture.model_validate_json(Path(__file__).parent.joinpath("fixtures", "capture_checkout.json").read_text())
    f5 = next(n for n in cap.ax_nodes if n.dom_id == "f5")
    hero = {"what_sighted_user_sees": "Pay R1,249", "screen_reader_role": "button", "screen_reader_name": "Submit", "why_it_matters": "price hidden", "bbox": f5.bbox.model_dump()}
    nowhere = {"what_sighted_user_sees": "ghost", "screen_reader_role": "button", "screen_reader_name": "x", "why_it_matters": "x", "bbox": {"x_min": 1, "y_min": 1, "x_max": 2, "y_max": 2}}

    def answer(findings):
        return {"id": "r", "_request_id": "req", "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": _json.dumps({"findings": findings})}]}], "usage": {"input_tokens": 1, "output_tokens": 1}}

    async def factory():
        return page

    defaults = stage_defaults()
    client = FakeMetaClient(META, stage_defaults=defaults, script={"comparator": [answer([hero, nowhere]), answer([hero, nowhere])]})
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data")})
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        run = await run_single_page(settings, client, bundle=bundle, bus=EventBus(bundle), index=index, flow=FLOWS["checkout"], base_url=server_url, page_factory=factory)
    finally:
        await index.close()
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error
    assert run.findings_verified == 1 and run.findings_rejected == 1  # the ghost once, never the hero twice


async def test_judge_calls_run_concurrently(tmp_path, server_url, page):
    """Judging is per finding and independent: six findings must not take six judge latencies."""
    import asyncio as aio
    import time as _time

    from parity.meta.fake import FakeMetaClient

    class SlowJudge(FakeMetaClient):
        async def responses(self, body, *, stage, run_id, step_index=None):
            if stage == "judge":
                await aio.sleep(0.4)
            return await super().responses(body, stage=stage, run_id=run_id, step_index=step_index)

    async def factory():
        return page

    client = SlowJudge(META, stage_defaults=stage_defaults())
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data")})
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        t0 = _time.perf_counter()
        run = await run_single_page(settings, client, bundle=bundle, bus=EventBus(bundle), index=index, flow=FLOWS["checkout"], base_url=server_url,
                                    page_factory=factory, ablation=__import__("parity.pipeline.audit", fromlist=["Ablation"]).Ablation(run_fixes=False))
        elapsed = _time.perf_counter() - t0
        judged = len([f for f in (await bundle.load(run.id)).findings if f.judgement])
    finally:
        await index.close()
    assert judged >= 4, judged
    assert elapsed < 0.4 * judged * 0.75, f"{judged} judge calls took {elapsed:.1f}s: sequential"


async def test_unparseable_comparator_answer_is_retried_once(tmp_path, server_url, page):
    """An answer that is not JSON is not 'no findings': the comparator is asked again and the event says so."""
    import json as _json

    from parity.meta.fake import FakeMetaClient
    from parity.store.models import Capture

    cap = Capture.model_validate_json(Path(__file__).parent.joinpath("fixtures", "capture_checkout.json").read_text())
    f5 = next(n for n in cap.ax_nodes if n.dom_id == "f5")
    hero = {"what_sighted_user_sees": "Pay R1,249", "screen_reader_role": "button", "screen_reader_name": "Submit", "why_it_matters": "price hidden", "bbox": f5.bbox.model_dump()}

    def answer(text):
        return {"id": "r", "_request_id": "req", "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}], "usage": {"input_tokens": 1, "output_tokens": 1}}

    async def factory():
        return page

    client = FakeMetaClient(META, stage_defaults=stage_defaults(), script={"comparator": [answer("I ran out of tokens while thinking"), answer(_json.dumps({"findings": [hero]}))]})
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data")})
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        run = await run_single_page(settings, client, bundle=bundle, bus=EventBus(bundle), index=index, flow=FLOWS["checkout"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    finally:
        await index.close()
    assert run.findings_verified == 1, run.error
    types = [e.type for e in loaded.events]
    assert "comparator.unparseable" in types and types.count("comparator.candidates") == 2
    prompts = [c["input"][0]["content"][0]["text"] for c in client.calls if "ACCESSIBILITY TREE:" in c["input"][0]["content"][0].get("text", "")]
    assert len(prompts) >= 2 and prompts[0] != prompts[1] and "not valid JSON" in prompts[1]  # a different request: not a cache replay of the bad answer


async def test_cancelled_run_is_recorded_as_failed(tmp_path, server_url):
    """A server shutdown (Cloud Run redeploy) cancels the task mid-run: the bundle must say failed with a terminal event, not done."""
    import asyncio

    started = asyncio.Event()

    async def factory():
        started.set()
        await asyncio.sleep(3600)  # a model call or page load that never returns before the shutdown

    async with harness(tmp_path, {}) as (settings, client, bus, bundle, index):
        task = asyncio.create_task(run_single_page(settings, client, bundle=bundle, bus=bus, index=index, flow=FLOWS["checkout"], base_url=server_url, page_factory=factory))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        runs = await bundle.list_run_ids()
        loaded = await bundle.load(runs[0])
    assert loaded.run.status == RunStatus.failed and "cancel" in (loaded.run.error or "").lower()
    assert loaded.events[-1].type == "run.failed"
