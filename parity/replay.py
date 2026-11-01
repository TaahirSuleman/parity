"""Replay mode: copy a recorded bundle under a new run id and republish its events with pacing.

No model calls, no key. Ids inside the bundle embed the source run id, so a textual rewrite of
``source_id -> new_id`` keeps every cross-reference (finding ids, event payloads) consistent.
"""

from __future__ import annotations

import asyncio
import logging

from parity.api.events import EventBus
from parity.pipeline.runner import new_run_id
from parity.store.bundle import RunBundle, keys
from parity.store.models import Event, Finding, ModelCall, Rejected, Run, RunMode, RunStatus, Step, now

log = logging.getLogger(__name__)
DEFAULT_PACE_MS = 250


def _rewrite(text: str, source_id: str, new_id: str) -> str:
    return text.replace(source_id, new_id)


async def start(
    source_id: str, source: RunBundle, bus: EventBus, bundle: RunBundle, index, *, pace_ms: int = DEFAULT_PACE_MS, run_id: str | None = None,
) -> Run:
    """Copy the source bundle into ``bundle`` under a new id and schedule the paced event replay."""
    loaded = await source.load(source_id)
    new_id = run_id or new_run_id()
    run = Run.model_validate_json(_rewrite(loaded.run.model_dump_json(), source_id, new_id))
    final_status = run.status
    run.mode = RunMode.replay
    run.replay_of = source_id
    run.status = RunStatus.running
    run.started_at = now()
    run.finished_at = None
    await bundle.create(run)
    for step in loaded.steps:
        n = step.index
        new_step = Step.model_validate_json(_rewrite(step.model_dump_json(), source_id, new_id))
        if await source.store.exists(keys.screenshot(source_id, n)):  # an anonymised sample keeps a screenshot only where a finding was verified (§17)
            await bundle.store.put(keys.screenshot(new_id, n), await source.store.get(keys.screenshot(source_id, n)), "image/png")
        for key_fn in (keys.ax, keys.axe, keys.source):  # the step's source is the patch base for decisions on the replayed run
            if await source.store.exists(key_fn(source_id, n)):
                key = key_fn(new_id, n)
                await bundle.store.put(key, await source.store.get(key_fn(source_id, n)), "text/html; charset=utf-8" if key.endswith(".html") else "application/json")
        await bundle.store.put(keys.step(new_id, n), new_step.model_dump_json(indent=1).encode(), "application/json")
    for finding in loaded.findings:
        await bundle.write_finding(Finding.model_validate_json(_rewrite(finding.model_dump_json(), source_id, new_id)))
    for rejected in loaded.rejected:
        await bundle.write_rejected(Rejected.model_validate_json(_rewrite(rejected.model_dump_json(), source_id, new_id)))
    for call in loaded.trace:
        bundle.add_trace(new_id, ModelCall.model_validate_json(_rewrite(call.model_dump_json(), source_id, new_id)))
    for key in await source.store.list(f"runs/{source_id}/agent/"):
        data = await source.store.get(key)
        rel = key[len(f"runs/{source_id}/"):]
        if rel.endswith(".json"):
            data = _rewrite(data.decode(), source_id, new_id).encode()
        await bundle.store.put(f"runs/{new_id}/{rel}", data, "application/json" if rel.endswith(".json") else "image/png")
    if await source.store.exists(keys.patch(source_id)):
        await bundle.store.put(keys.patch(new_id), await source.store.get(keys.patch(source_id)), "text/x-diff")
    await bundle.flush(new_id)
    try:
        await index.upsert_run(run)
    except Exception as exc:
        log.warning("index upsert failed for replay %s: %s", new_id, exc)

    events = [Event.model_validate_json(_rewrite(e.model_dump_json(), source_id, new_id)) for e in loaded.events]
    bus.open(new_id)  # subscribers that connect before the first replayed event attach live
    asyncio.create_task(_publish(run, final_status, events, bus, bundle, index, pace_ms), name=f"replay-{new_id}")
    return run


async def _publish(run: Run, final_status: RunStatus, events: list[Event], bus: EventBus, bundle: RunBundle, index, pace_ms: int) -> None:
    async def finalize() -> None:
        from parity.pipeline.gate import is_pending, run_lock  # local import: gate imports the pipeline

        async with run_lock(run.id):
            if final_status == RunStatus.failed:
                run.status = RunStatus.failed
            else:  # judges may decide while the replay is still pacing out events
                pending = [f for f in (await bundle.load(run.id)).findings if is_pending(f)]
                run.status = RunStatus.awaiting_review if pending else RunStatus.done
            run.finished_at = now()
            await bundle.write_run(run)
        try:
            await index.upsert_run(run)
        except Exception as exc:
            log.warning("index upsert failed for replay %s: %s", run.id, exc)

    finalized = False
    try:
        for i, event in enumerate(events):
            event.run_id = run.id
            event.at = now()
            event.data = {**event.data, "run_id": run.id, "mode": "replay"}
            bundle.add_event(run.id, event)
            if event.type in ("run.finished", "run.failed") and not finalized:
                await finalize()  # final state on disk before the terminal event reaches subscribers
                finalized = True
            bus.publish(run.id, event)
            if pace_ms and i < len(events) - 1:
                await asyncio.sleep(pace_ms / 1000)
    finally:
        if not finalized:
            await finalize()
        await bundle.flush(run.id)
        bundle.forget(run.id)  # as for a live run: the bundle is the record; late subscribers read it
        bus.forget(run.id)
