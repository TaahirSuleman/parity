"""REST routes (spec docs/19 §7). State lives on app.state (see parity.app)."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
from typing import Literal

from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from parity import replay
from parity.api.sse import sse_response
from parity.flows import FLOWS
from parity.pipeline.gate import ConflictError, decide
from parity.pipeline.runner import run_flow
from parity.store.models import RunMode
from parity.verifier_off import verifier_off

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class RunRequest(BaseModel):
    flow_id: str | None = None
    mode: RunMode = RunMode.replay
    pace_ms: int = Field(default=replay.DEFAULT_PACE_MS, ge=0, le=5000)
    replay_of: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]*$")  # a recorded run id (public samples)


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=1, max_length=2000)


@router.get("/health")
async def health(request: Request) -> dict:
    st = request.app.state
    return {
        "ok": True, "mode_default": st.settings.default_mode, "live_enabled": st.settings.live_enabled,
        "storage": "gcs" if st.settings.gcs_bucket else "local", "runs_indexed": await st.index.count_runs(),
        "has_key": st.settings.has_key, "models_ok": bool(getattr(st, "models_ok", False)), "replay_runs": st.replay_ids, "replay_flows": st.replay_for_flow, "version": request.app.version,
    }


@router.get("/flows")
async def flows() -> list[dict]:
    return [{"id": f.id, "name": f.name, "start_url": f.start_url, "goal": f.goal, "pages": list(f.pages), "single_page": f.single_page} for f in FLOWS.values()]


@router.post("/runs", status_code=202)
async def start_run(req: RunRequest, request: Request) -> dict:
    st = request.app.state
    if req.replay_of and req.mode != RunMode.replay:
        raise HTTPException(422, "replay_of selects a recorded run; it needs mode=replay")
    if req.replay_of:
        if req.replay_of not in st.replay_ids:
            raise HTTPException(404, f"no recorded run {req.replay_of!r}")
        run = await replay.start(req.replay_of, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=req.pace_ms, replay_keep=st.settings.replay_keep)
        return {"run_id": run.id, "mode": run.mode, "replay_of": req.replay_of}
    flow = FLOWS.get(req.flow_id or "")
    if flow is None:
        raise HTTPException(404, f"unknown flow {req.flow_id!r}")
    if req.mode == RunMode.replay:
        source_id = st.replay_for_flow.get(flow.id)
        if source_id is None:
            raise HTTPException(404, f"no replay bundle recorded for flow {flow.id!r}")
        run = await replay.start(source_id, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=req.pace_ms, replay_keep=st.settings.replay_keep)
        return {"run_id": run.id, "mode": run.mode, "replay_of": source_id}
    if not st.settings.live_enabled:
        raise HTTPException(403, "Live mode is disabled on this server; use Replay")
    if st.client is None:
        raise HTTPException(503, "Live mode needs MODEL_API_KEY on the server; use Replay")
    ip = client_ip(request, st.settings.trust_proxy)
    verdict = st.limiter.check(ip)
    if not verdict.allowed:
        return _too_many(verdict.message, verdict.retry_after_s)
    if st.live_lock.locked():
        # A holder that has already published its terminal event is only mid-teardown: wait for the
        # slot instead of refusing, so "Run" works the moment a viewer sees the previous run end.
        finishing = st.last_live_run is not None and st.bus.is_finished(st.last_live_run)
        if not finishing:
            return _too_many("a Live run is already in progress; try again shortly, or watch a Replay (no model calls, no limit)", 60)
        try:
            await asyncio.wait_for(st.live_lock.acquire(), timeout=2)
        except TimeoutError:
            return _too_many("a Live run is already in progress; try again shortly, or watch a Replay (no model calls, no limit)", 60)
    else:
        await st.live_lock.acquire()  # the slot is taken here, synchronously, so a double click cannot queue two runs
    verdict = st.limiter.take(ip)  # counted once the slot is ours; a refusal here is a race between two of this visitor's clicks
    if not verdict.allowed:
        st.live_lock.release()
        return _too_many(verdict.message, verdict.retry_after_s)
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


def client_ip(request: Request, trust_proxy: bool) -> str:
    """The visitor's address for the per-IP limit. Behind Google's front end the address it saw is APPENDED to X-Forwarded-For,
    so the right-most hop is the one it vouches for and anything to the left is what the client typed; a direct client's header
    is ignored altogether. A hop that is not an IP address falls back to the socket peer."""
    if trust_proxy:
        hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
        if hops:
            try:
                return str(ipaddress.ip_address(hops[-1]))
            except ValueError:
                pass
    return request.client.host if request.client else ""


def _too_many(message: str, retry_after_s: int) -> JSONResponse:
    """429 as the UI reads it: what happened, when to retry, and that Replay is the way in (spec §15)."""
    body = {"error": message, "retry_after_s": int(retry_after_s), "suggestion": "replay", "detail": message}
    return JSONResponse(body, status_code=429, headers={"Retry-After": str(int(retry_after_s))})


def public_run(run) -> dict:
    """What anyone may see about a run: no visitor hash, no internal host."""
    data = run.model_dump(mode="json", exclude={"client_ip_hash"})
    data["target_url"] = urlparse(run.target_url).path or run.target_url
    return data


@router.get("/runs")
async def list_runs(request: Request, limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    return [public_run(r) for r in await request.app.state.index.list_runs(limit)]


@router.get("/runs/{run_id}")
async def run_detail(run_id: str, request: Request) -> dict:
    try:
        loaded = await request.app.state.bundle.load(run_id)
    except KeyError:
        raise HTTPException(404, "unknown run") from None
    return {
        "run": public_run(loaded.run), "steps": [s.model_dump(mode="json") for s in loaded.steps],
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


@router.post("/runs/{run_id}/findings/{finding_id}/decision")
async def record_decision(run_id: str, finding_id: str, req: DecisionRequest, request: Request) -> dict:
    """The human gate: the only way a finding becomes approved or rejected (spec D4)."""
    st = request.app.state
    try:
        finding, run = await decide(st.bundle, st.index, st.bus, run_id, finding_id, req.decision, req.reason)
    except KeyError:
        raise HTTPException(404, "unknown run or finding") from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"finding": finding.model_dump(mode="json"), "run": public_run(run)}


@router.get("/runs/{run_id}/patch")
async def run_patch(run_id: str, request: Request) -> Response:
    """fix.patch: the approved fixes only, as one git-style patch."""
    st = request.app.state
    if not await st.bundle.exists(run_id):
        raise HTTPException(404, "unknown run")
    patch = await st.bundle.read_patch(run_id)
    if not patch:
        raise HTTPException(404, "no approved fixes yet")
    return Response(content=patch, media_type="text/x-diff", headers={"Content-Disposition": f'attachment; filename="parity-{run_id}.patch"'})


@router.get("/eval")
async def eval_results(request: Request) -> dict:
    """The one number set (eval/results/latest.json) plus the anonymised public sample (public.json)."""
    import json

    eval_dir = request.app.state.settings.eval_dir
    latest = eval_dir / "latest.json"
    if not latest.exists():
        raise HTTPException(404, "no eval results yet: run `python -m eval.harness`")
    body = json.loads(latest.read_text())
    public = eval_dir / "public.json"
    body["public"] = json.loads(public.read_text()) if public.exists() else []
    return body
