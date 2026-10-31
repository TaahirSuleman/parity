"""REST routes (spec docs/19 §7). State lives on app.state (see parity.app)."""

from __future__ import annotations

import asyncio
import hashlib
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from parity import replay
from parity.api.sse import sse_response
from parity.flows import FLOWS
from parity.pipeline.runner import run_flow
from parity.store.models import RunMode
from parity.verifier_off import verifier_off

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class RunRequest(BaseModel):
    flow_id: str
    mode: RunMode = RunMode.replay
    pace_ms: int = Field(default=replay.DEFAULT_PACE_MS, ge=0, le=5000)


@router.get("/health")
async def health(request: Request) -> dict:
    st = request.app.state
    return {
        "ok": True, "mode_default": st.settings.default_mode, "live_enabled": st.settings.live_enabled,
        "storage": "gcs" if st.settings.gcs_bucket else "local", "runs_indexed": await st.index.count_runs(),
        "has_key": st.settings.has_key, "replay_runs": st.replay_ids, "replay_flows": st.replay_for_flow, "version": request.app.version,
    }


@router.get("/flows")
async def flows() -> list[dict]:
    return [{"id": f.id, "name": f.name, "start_url": f.start_url, "goal": f.goal, "pages": list(f.pages), "single_page": f.single_page} for f in FLOWS.values()]


@router.post("/runs", status_code=202)
async def start_run(req: RunRequest, request: Request) -> dict:
    st = request.app.state
    flow = FLOWS.get(req.flow_id)
    if flow is None:
        raise HTTPException(404, f"unknown flow {req.flow_id!r}")
    if req.mode == RunMode.replay:
        source_id = st.replay_for_flow.get(flow.id)
        if source_id is None:
            raise HTTPException(404, f"no replay bundle recorded for flow {flow.id!r}")
        run = await replay.start(source_id, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=req.pace_ms)
        return {"run_id": run.id, "mode": run.mode, "replay_of": source_id}
    if not st.settings.live_enabled:
        raise HTTPException(403, "Live mode is disabled on this server; use Replay")
    if st.client is None:
        raise HTTPException(503, "Live mode needs MODEL_API_KEY on the server; use Replay")
    if st.live_lock.locked():
        # A holder that has already published its terminal event is only mid-teardown: wait for the
        # slot instead of refusing, so "Run" works the moment a viewer sees the previous run end.
        finishing = st.last_live_run is not None and st.bus.is_finished(st.last_live_run)
        if not finishing:
            raise HTTPException(429, "a Live run is already in progress; try again shortly or use Replay", headers={"Retry-After": "60"})
        try:
            await asyncio.wait_for(st.live_lock.acquire(), timeout=2)
        except TimeoutError:
            raise HTTPException(429, "a Live run is already in progress; try again shortly or use Replay", headers={"Retry-After": "60"}) from None
    else:
        await st.live_lock.acquire()  # the slot is taken here, synchronously, so a double click cannot queue two runs
    ip = request.client.host if request.client else ""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""
    run_id = replay.new_run_id()
    st.last_live_run = run_id
    st.bus.open(run_id)  # subscribers that connect before run.started attach live instead of reading an empty log
    asyncio.create_task(_live(st, flow, run_id, ip_hash), name=f"live-{run_id}")
    return {"run_id": run_id, "mode": "live"}


async def _live(st, flow, run_id: str, ip_hash: str) -> None:
    try:
        await run_flow(st.settings, st.client, st.bus, st.bundle, st.index, flow, base_url=st.self_base_url, run_id=run_id, client_ip_hash=ip_hash)
    except Exception:  # run_flow records failures itself; this guards the task
        log.exception("live run %s crashed outside the runner", run_id)
    finally:
        st.live_lock.release()


@router.get("/runs")
async def list_runs(request: Request, limit: int = 50) -> list[dict]:
    return [r.model_dump(mode="json") for r in await request.app.state.index.list_runs(limit)]


@router.get("/runs/{run_id}")
async def run_detail(run_id: str, request: Request) -> dict:
    try:
        loaded = await request.app.state.bundle.load(run_id)
    except KeyError:
        raise HTTPException(404, "unknown run") from None
    return {
        "run": loaded.run.model_dump(mode="json"), "steps": [s.model_dump(mode="json") for s in loaded.steps],
        "findings": [f.model_dump(mode="json") for f in loaded.findings], "rejected": [r.model_dump(mode="json") for r in loaded.rejected],
        "trace": [c.model_dump(mode="json") for c in loaded.trace],
    }


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request):
    st = request.app.state
    if not st.bus.knows(run_id) and not await st.bundle.exists(run_id):
        raise HTTPException(404, "unknown run")
    return sse_response(st.bus, run_id)


@router.get("/runs/{run_id}/steps/{n}/screenshot.png")
async def screenshot(run_id: str, n: int, request: Request) -> Response:
    try:
        png = await request.app.state.bundle.read_screenshot(run_id, n)
    except FileNotFoundError:
        raise HTTPException(404, "no screenshot") from None
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.get("/runs/{run_id}/verifier-off")
async def run_verifier_off(run_id: str, request: Request) -> dict:
    """What this run would have reported with the Verifier bypassed. Post hoc, no model calls."""
    try:
        report = await verifier_off(request.app.state.bundle, run_id)
    except KeyError:
        raise HTTPException(404, "unknown run") from None
    return report.model_dump(mode="json")
