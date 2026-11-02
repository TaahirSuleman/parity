"""Replay mode: copy a recorded bundle under a new run id and republish its events with pacing.

No model calls, no key. Ids inside the bundle embed the source run id, so a textual rewrite of
``source_id -> new_id`` keeps every cross-reference (finding ids, event payloads) consistent.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from parity.api.events import EventBus
from parity.pipeline.runner import new_run_id
from parity.store.blob import gather_bounded
from parity.store.bundle import RunBundle, keys
from parity.store.models import Event, Finding, ModelCall, Rejected, Run, RunMode, RunStatus, Step, now

log = logging.getLogger(__name__)
DEFAULT_PACE_MS = 250
EXTERNAL_RETENTION_S = 86_400  # pages visitors chose are kept for 24 hours (spec §19.3.4)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
EXPIRED = "This audit has expired: pages you choose are kept for 24 hours."


def _rewrite(text: str, source_id: str, new_id: str) -> str:
    return text.replace(source_id, new_id)


async def fresh_run_id(bundle: RunBundle) -> str:
    """A new run id that no bundle holds yet: a collision would merge two runs into one bundle."""
    for _ in range(16):
        run_id = new_run_id()
        if not await bundle.exists(run_id):
            return run_id
    raise RuntimeError("could not mint a free run id")


async def evict_replay_copies(bundle: RunBundle, index, keep: int, bus: EventBus | None = None, min_age_s: int = 0) -> list[str]:
    """Delete the oldest Replay copies beyond ``keep`` (the index knows which runs are replays, so no bundle is read).

    A replay that is still streaming is never evicted, whatever its age: twenty judges clicking at once must not delete the
    first judge's run from under its own publisher (screenshots 404, the detail route 404, the replay task dies on a KeyError).
    Nor is a copy younger than ``min_age_s``: a judge still reviewing a finished Replay must not lose it to other judges' clicks.
    """
    rows = await index.replay_copies_oldest_first()
    if bus is not None:
        rows = [row for row in rows if not (bus.knows(row[0]) and not bus.is_finished(row[0]))]
    cutoff = now() - timedelta(seconds=min_age_s)
    gone: list[str] = []
    for run_id, started_at, finished_at in rows[: max(0, len(rows) - keep)]:
        if min_age_s and (finished_at or started_at) > cutoff:
            continue
        try:
            await bundle.delete_run(run_id)
            await index.delete_run(run_id)
            gone.append(run_id)
        except Exception as exc:
            log.warning("could not evict replay copy %s: %s", run_id, exc)
    return gone


async def evict_external(bundle: RunBundle, index, max_age_s: int = EXTERNAL_RETENTION_S) -> list[str]:
    """Retention for pages visitors chose, enforced rather than promised (spec §19.3.4): every file holding page content
    (screenshots, trees, axe results, page source, findings, rejected rows, events, the trace, run.json) goes from bundles
    with ``source == "visitor-url"`` whose run ended more than ``max_age_s`` ago; ``summary.json`` stays (origin, outcome,
    counts, cost, seconds, consent) so the day's spend and the stats survive. The index row goes with the run: a summary is
    not a run. A run still going is never touched."""
    cutoff = now() - timedelta(seconds=max_age_s)
    gone: list[str] = []
    for run in await index.external_runs_since(EPOCH):
        if run.status in (RunStatus.running, RunStatus.queued) or (run.finished_at or run.started_at) > cutoff:
            continue
        try:
            outcome = run.status.value
            for event in await bundle.events(run.id):
                if event.type == "run.finished" and isinstance(event.data.get("agent"), dict) and event.data["agent"].get("summary"):
                    outcome = str(event.data["agent"]["summary"])
            summary = {
                "id": run.id, "source": run.source, "origin": run.origin, "status": run.status.value, "outcome": outcome,
                "findings_verified": run.findings_verified, "findings_rejected": run.findings_rejected, "axe_violations": run.axe_violations,
                "tokens": run.tokens, "cost_usd": run.cost_usd, "duration_ms": run.duration_ms, "screens": run.screens,
                "consent_at": run.consent_at.isoformat() if run.consent_at else None, "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None, "evicted_at": now().isoformat(),
            }
            await bundle.delete_run(run.id)
            await bundle.store.put(keys.summary(run.id), json.dumps(summary, indent=1).encode(), "application/json")
            await index.delete_run(run.id)
            gone.append(run.id)
        except Exception as exc:
            log.warning("could not evict visitor run %s: %s", run.id, exc)
    return gone


async def start(
    source_id: str, source: RunBundle, bus: EventBus, bundle: RunBundle, index, *, pace_ms: int = DEFAULT_PACE_MS, run_id: str | None = None,
    replay_keep: int | None = None, replay_min_age_s: int = 0, tasks: set[asyncio.Task] | None = None,
) -> Run:
    """Copy the source bundle into ``bundle`` under a new id and schedule the paced event replay. With ``replay_keep`` the
    oldest copies beyond it are evicted first, so boot cost stays bounded however often judges click Replay."""
    if replay_keep is not None:
        await evict_replay_copies(bundle, index, max(0, replay_keep - 1), bus, replay_min_age_s)
    loaded = await source.load(source_id)
    new_id = run_id or await fresh_run_id(bundle)
    run = Run.model_validate_json(_rewrite(loaded.run.model_dump_json(), source_id, new_id))
    final_status = run.status
    run.mode = RunMode.replay
    run.replay_of = source_id
    run.status = RunStatus.running
    run.started_at = now()
    run.finished_at = None
    await bundle.create(run)

    async def copy_object(src: str, dst: str, content_type: str) -> None:
        if await source.store.exists(src):
            await bundle.store.put(dst, await source.store.get(src), content_type)

    async def copy_agent_file(key: str) -> None:
        data = await source.store.get(key)
        rel = key[len(f"runs/{source_id}/"):]
        if rel.endswith(".json"):
            data = _rewrite(data.decode(), source_id, new_id).encode()
        await bundle.store.put(f"runs/{new_id}/{rel}", data, "application/json" if rel.endswith(".json") else "image/png")

    jobs = []  # every object is independent, so they are copied together: one round trip each on GCS, dozens per run (2 Nov: 5.9 s in sequence)
    for step in loaded.steps:
        n = step.index
        new_step = Step.model_validate_json(_rewrite(step.model_dump_json(), source_id, new_id))
        jobs.append(copy_object(keys.screenshot(source_id, n), keys.screenshot(new_id, n), "image/png"))  # an anonymised sample keeps a screenshot only where a finding was verified (§17)
        for key_fn in (keys.ax, keys.axe, keys.source):  # the step's source is the patch base for decisions on the replayed run
            key = key_fn(new_id, n)
            jobs.append(copy_object(key_fn(source_id, n), key, "text/html; charset=utf-8" if key.endswith(".html") else "application/json"))
        jobs.append(bundle.store.put(keys.step(new_id, n), new_step.model_dump_json(indent=1).encode(), "application/json"))
    jobs += [bundle.write_finding(Finding.model_validate_json(_rewrite(f.model_dump_json(), source_id, new_id))) for f in loaded.findings]
    jobs += [bundle.write_rejected(Rejected.model_validate_json(_rewrite(r.model_dump_json(), source_id, new_id))) for r in loaded.rejected]
    for call in loaded.trace:
        bundle.add_trace(new_id, ModelCall.model_validate_json(_rewrite(call.model_dump_json(), source_id, new_id)))
    jobs += [copy_agent_file(key) for key in await source.store.list(f"runs/{source_id}/agent/")]
    jobs.append(copy_object(keys.patch(source_id), keys.patch(new_id), "text/x-diff"))
    await gather_bounded(jobs)
    await bundle.flush(new_id)
    try:
        await index.upsert_run(run)
    except Exception as exc:
        log.warning("index upsert failed for replay %s: %s", new_id, exc)

    events = [Event.model_validate_json(_rewrite(e.model_dump_json(), source_id, new_id)) for e in loaded.events]
    bus.open(new_id)  # subscribers that connect before the first replayed event attach live
    task = asyncio.create_task(_publish(run, final_status, events, bus, bundle, index, pace_ms), name=f"replay-{new_id}")
    if tasks is not None:  # the app cancels and awaits these at shutdown; uvicorn alone would leave them to die mid-write
        tasks.add(task)
        task.add_done_callback(tasks.discard)
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
            event.data = {**event.data, "run_id": run.id, "mode": "replay", **({"replay_of": run.replay_of} if event.type == "run.started" else {})}
            bundle.add_event(run.id, event)
            if event.type in ("run.finished", "run.failed") and not finalized:
                await finalize()  # final state on disk before the terminal event reaches subscribers
                finalized = True
            bus.publish(run.id, event)
            if pace_ms and i < len(events) - 1:
                await asyncio.sleep(pace_ms / 1000)
    except asyncio.CancelledError:  # a server shutdown (a redeploy) mid-replay: the record says so instead of staying `running` for ever
        if not finalized:
            run.status, run.error, run.finished_at = RunStatus.failed, "cancelled: the server shut down during the replay; start it again", now()
            failed = Event(type="run.failed", run_id=run.id, data={"error": run.error, "run_id": run.id, "mode": "replay"})
            bundle.add_event(run.id, failed)
            await asyncio.shield(bundle.write_run(run))
            try:
                await asyncio.shield(index.upsert_run(run))
            except Exception as exc:
                log.warning("index upsert failed for replay %s: %s", run.id, exc)
            bus.publish(run.id, failed)
            finalized = True
        raise
    finally:
        from parity.pipeline.gate import run_lock

        try:
            if not finalized:
                await finalize()
        except Exception as exc:  # the final write failed: subscribers still get a terminal event, or the page stays on "Auditing…" for ever
            log.warning("replay %s could not be finalised: %s", run.id, exc)
        if not bus.is_finished(run.id):
            run.status, run.error, run.finished_at = RunStatus.failed, "the replay could not be written to storage; start it again", now()
            failed = Event(type="run.failed", run_id=run.id, data={"error": run.error, "run_id": run.id, "mode": "replay"})
            bundle.add_event(run.id, failed)
            try:
                await bundle.write_run(run)
            except Exception as exc:
                log.warning("replay %s: the failure record could not be written either: %s", run.id, exc)
            bus.publish(run.id, failed)
        async with run_lock(run.id):  # a decision recorded during the last write must not be overwritten by it
            try:
                await bundle.flush(run.id)
            except Exception as exc:
                log.warning("replay %s: the event log could not be flushed: %s", run.id, exc)
        bundle.forget(run.id)  # as for a live run: the bundle is the record; late subscribers read it
        bus.forget(run.id)
