"""REST routes (spec docs/19 §7). State lives on app.state (see parity.app)."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import re
from typing import Annotated, Literal

from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from pydantic import BaseModel, Field, ValidationError, field_validator

from parity import replay
from parity.api.sse import sse_response
from parity.flows import Flow, available_flows
from parity.pipeline.gate import ConflictError, decide
from parity.pipeline.runner import VisitorRequest, run_flow
from parity.pipeline.urlpolicy import MAX_URL_LEN, READ_ONLY_GOAL, Refusal, check_url, landing_refusal
from parity.ratelimit import Closed
from parity.store.bundle import keys
from parity.store.models import Run, RunMode, now
from parity.verifier_off import verifier_off

POLICY_CONCURRENCY = 4  # URL-policy lookups (DNS, robots.txt) in flight at once; as many more may wait, the rest are answered 429
POLICY_TIMEOUT_S = 20.0  # one URL-policy check (DNS and robots.txt) may take this long; past it the address is refused, the thread is not awaited

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
UNREADABLE = "a stored record for this run is unreadable; see the server log"


ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]*$"
ID_MAX = 80


def _checked_id(value: str) -> str:
    """Run and finding ids are validated before they reach storage: a 2,000-character or NUL-bearing id is 'unknown', not an
    OSError from os.stat (which was a 500 that reset the connection)."""
    if len(value) > ID_MAX or not re.fullmatch(ID_PATTERN, value):
        raise HTTPException(404, "unknown run")
    return value


def _run_id(run_id: str) -> str:
    return _checked_id(run_id)


def _finding_id(finding_id: str) -> str:
    return _checked_id(finding_id)


RunId = Annotated[str, Depends(_run_id)]
FindingId = Annotated[str, Depends(_finding_id)]
StepIndex = Annotated[int, Path(ge=0, le=999)]


HINT_MAX = 120
HINT_TAGS = re.compile(r"<[^>]*>")
HINT_OTHER = re.compile(r"[^A-Za-z0-9 .,;:'!?()&/-]")


class RunRequest(BaseModel):
    flow_id: str | None = None
    mode: RunMode = RunMode.replay
    pace_ms: int = Field(default=replay.DEFAULT_PACE_MS, ge=0, le=5000)
    replay_of: str | None = Field(default=None, max_length=ID_MAX, pattern=ID_PATTERN)  # a recorded run id (public samples)
    # "Live on a page you choose" (spec §19.3.2): the visitor's URL, how many screens, their affirmation, an optional hint
    url: str | None = Field(default=None, max_length=MAX_URL_LEN)
    screens: Literal[1, 3] = 1
    consent: bool = False
    hint: str | None = Field(default=None, max_length=HINT_MAX)


def clean_hint(hint: str | None) -> str:
    """Letters, digits and basic punctuation only, whitespace collapsed: tags, control and invisible characters are dropped."""
    if not hint:
        return ""
    return re.sub(r"\s+", " ", HINT_OTHER.sub("", HINT_TAGS.sub("", hint))).strip()


def public_origin(request: Request, trust_proxy: bool) -> str:
    """The address the world reaches this app at: linked from the user agent on external pages, refused by the URL policy as our own."""
    host = request.headers.get("host") or request.url.netloc
    scheme = (request.headers.get("x-forwarded-proto") if trust_proxy else None) or request.url.scheme
    return f"{scheme}://{host}"


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def _real_text(cls, value: str) -> str:
        try:
            value.encode("utf-8")  # a lone surrogate is valid Python text but cannot be stored or sent back
        except UnicodeEncodeError:
            raise ValueError("reason contains characters that are not valid text") from None
        return value


class FocusEntry(BaseModel):
    """One focus or VoiceOver-cursor stop posted by scripts/vo_focus_logger.js during a recording (spec §16; dev only)."""

    t_ms: int = Field(ge=0)  # epoch ms on the recording Mac: the clock the captions poller and the WAV's start share
    dom_id: str = Field(min_length=1, max_length=300)
    event: Literal["focusin", "activedescendant"] = "focusin"


FOCUSLOG_MAX = 10_000


@router.get("/health")
async def health(request: Request) -> dict:
    st = request.app.state
    return {
        "ok": True, "mode_default": st.settings.default_mode, "live_enabled": st.settings.live_enabled,
        "storage": "gcs" if st.settings.gcs_bucket else "local", "runs_indexed": await st.index.count_runs(),
        "has_key": st.settings.has_key, "models_ok": bool(getattr(st, "models_ok", False)), "replay_runs": st.replay_ids, "replay_flows": st.replay_for_flow, "version": request.app.version,
        "open_url": bool(st.settings.open_url and st.settings.live_enabled and st.client is not None), "suggested_urls": list(st.settings.suggested_urls),
        "external_closed_today": bool(st.settings.open_url and await st.budget.day_closed(st.index)),
    }


@router.get("/flows")
async def flows(request: Request) -> list[dict]:
    return [{"id": f.id, "name": f.name, "start_url": f.start_url, "goal": f.goal, "pages": list(f.pages), "single_page": f.single_page,
             "public": f.public, "attribution": f.attribution} for f in available_flows(request.app.state.settings.external_flows).values()]


@router.post("/runs", status_code=202)
async def start_run(req: RunRequest, request: Request) -> dict:
    st = request.app.state
    if req.url is not None:
        return await _start_url_run(req, request)
    if req.replay_of and req.mode != RunMode.replay:
        raise HTTPException(422, "replay_of selects a recorded run; it needs mode=replay")
    if req.replay_of:
        if req.replay_of not in st.replay_ids:
            raise HTTPException(404, f"no recorded run {req.replay_of!r}")
        run = await replay.start(req.replay_of, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=req.pace_ms, replay_keep=st.settings.replay_keep,
                                 replay_min_age_s=st.settings.replay_min_age_s, tasks=st.tasks)
        return {"run_id": run.id, "mode": run.mode, "replay_of": req.replay_of}
    flow = available_flows(st.settings.external_flows).get(req.flow_id or "")
    if flow is None:
        raise HTTPException(404, f"unknown flow {(req.flow_id or '')[:40]!r}")  # never echo a body back whole
    if req.mode == RunMode.replay:
        source_id = st.replay_for_flow.get(flow.id)
        if source_id is None:
            raise HTTPException(404, f"no replay bundle recorded for flow {flow.id!r}")
        run = await replay.start(source_id, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=req.pace_ms, replay_keep=st.settings.replay_keep,
                                 replay_min_age_s=st.settings.replay_min_age_s, tasks=st.tasks)
        return {"run_id": run.id, "mode": run.mode, "replay_of": source_id}
    if not st.settings.live_enabled:
        raise HTTPException(403, "Live mode is disabled on this server; use Replay")
    if st.client is None:
        raise HTTPException(503, "Live mode needs MODEL_API_KEY on the server; use Replay")
    ip = client_ip(request, st.settings.trust_proxy)
    verdict = st.limiter.check(ip)
    if not verdict.allowed:
        return _too_many(verdict.message, verdict.retry_after_s)
    return await _launch_live(st, flow, ip, {"own_origin": public_origin(request, st.settings.trust_proxy)})


async def _start_url_run(req: RunRequest, request: Request) -> dict:
    """Live on a page the visitor chose (spec §19.3.2): the switch, the affirmation, the policy, the caps, then the usual Live gates.
    No answer ever carries the URL back; a refusal is one sentence."""
    st = request.app.state
    settings = st.settings
    if not settings.open_url:
        raise HTTPException(403, "pages you choose are not offered on this server")
    if req.mode != RunMode.live:
        raise HTTPException(422, "a page you choose runs Live: set mode=live")
    if not req.consent:
        raise HTTPException(422, "confirm that the page is public and that you may audit it")
    if not settings.live_enabled:
        raise HTTPException(403, "Live mode is disabled on this server; use Replay")
    if st.client is None:
        raise HTTPException(503, "Live mode needs MODEL_API_KEY on the server; use Replay")
    ip = client_ip(request, settings.trust_proxy)
    verdict = st.limiter.check(ip)  # a look, not a count: a refused address must not spend one of the visitor's runs
    if not verdict.allowed:
        return _too_many(verdict.message, verdict.retry_after_s)
    if await st.budget.day_closed(st.index):  # an index read, answered before any lookup leaves this process
        raise HTTPException(503, Closed(scope="day", retry_after_s=1).message)
    own = public_origin(request, settings.trust_proxy)
    look = st.lookups.take(ip)  # a lookup is outbound work a refusal still costs: counted per visitor (review I4)
    if not look.allowed:
        return _too_many("too many addresses from your connection this hour; try again later", look.retry_after_s)
    if st.policy_gate.locked() and st.policy_waiting >= POLICY_CONCURRENCY:  # a full gate answers now instead of queueing every visitor behind one slow host
        return _too_many("the field is busy checking other addresses; try again in a few seconds", 5)
    st.policy_waiting += 1
    try:
        async with st.policy_gate:  # DNS and robots.txt block in a thread: a few at a time, however many addresses arrive at once
            try:
                target = await asyncio.wait_for(asyncio.to_thread(check_url, req.url or "", own_origin=own, deny=settings.url_deny, resolver=st.resolver, robots=st.robots), POLICY_TIMEOUT_S)
            except TimeoutError:
                raise HTTPException(422, "This address could not be checked in time; try again.") from None
    finally:
        st.policy_waiting -= 1
    if isinstance(target, Refusal):
        raise HTTPException(422, target.message)
    closed = await st.budget.check(st.index, target.origin)
    if isinstance(closed, Closed):
        if closed.scope == "day":
            raise HTTPException(503, closed.message)
        return _too_many(closed.message, closed.retry_after_s)
    hint = clean_hint(req.hint)
    goal = READ_ONLY_GOAL + (f" The visitor says the page is about: <page_data>{hint}</page_data>" if hint else "")
    flow = Flow(id=f"url-{hashlib.sha256(target.origin.encode()).hexdigest()[:8]}", name=f"Page: {target.host}", start_url=target.url, goal=goal,
                pages=(urlparse(target.url).path or "/",), single_page=req.screens == 1, public=True,
                attribution=f"{target.host} · audited read-only at a visitor's request")
    extra = {
        "own_origin": own, "visitor": VisitorRequest(origin=target.origin, consent_at=now(), screens=req.screens), "cost_cap_usd": settings.external_run_usd,
        "timeout_s": settings.external_timeout_s * (2 if req.screens == 3 else 1), "max_turns": 6 if req.screens == 1 else 12, "max_screens": req.screens,
        "landing": lambda url: landing_refusal(url, deny=settings.url_deny, robots=st.robots),  # the deny list and robots.txt where the page landed
    }
    return await _launch_live(st, flow, ip, extra)


async def _launch_live(st, flow: Flow, ip: str, extra: dict) -> dict | JSONResponse:
    """Take the one Live slot and this visitor's run, mint the id and start the task; any failure on the way gives the slot back."""
    if st.live_lock.locked():
        # A holder that has already published its terminal event is only mid-teardown: wait for the
        # slot instead of refusing, so "Run" works the moment a viewer sees the previous run end.
        finishing = st.last_live_run is not None and st.bus.is_finished(st.last_live_run)
        if not finishing:
            return _too_many("a Live run is already in progress; try again shortly, or watch a Replay (no model calls, no limit)", 60)
        try:
            await asyncio.wait_for(st.live_lock.acquire(), timeout=10)  # a purchase run's teardown (a last bundle load and flush on GCS) outlasts 2 s
        except TimeoutError:
            return _too_many("a Live run is already in progress; try again shortly, or watch a Replay (no model calls, no limit)", 60)
    else:
        await st.live_lock.acquire()  # the slot is taken here, synchronously, so a double click cannot queue two runs
    try:  # from here the slot is ours until the run's task owns it: any failure on the way (a bucket error minting the id) must give it back
        verdict = st.limiter.take(ip)  # counted once the slot is ours; a refusal here is a race between two of this visitor's clicks
        if not verdict.allowed:
            st.live_lock.release()
            return _too_many(verdict.message, verdict.retry_after_s)
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""
        run_id = await replay.fresh_run_id(st.bundle)
        st.last_live_run = run_id
        st.bus.open(run_id)  # subscribers that connect before run.started attach live instead of reading an empty log
        task = asyncio.create_task(_live(st, flow, run_id, ip_hash, extra), name=f"live-{run_id}")
    except BaseException:
        st.live_lock.release()
        raise
    st.tasks.add(task)  # cancelled and awaited at shutdown, so a redeploy leaves run.failed behind, not a run that is `running` for ever
    task.add_done_callback(st.tasks.discard)
    return {"run_id": run_id, "mode": "live"}


async def _live(st, flow, run_id: str, ip_hash: str, extra: dict) -> None:
    try:
        # an external page runs at its own origin behind the read-only guard (spec §19.2); the store runs under the app's own address
        await run_flow(st.settings, st.client, st.bus, st.bundle, st.index, flow, base_url=flow.origin or st.self_base_url, run_id=run_id, client_ip_hash=ip_hash,
                       public=flow.public, **extra)
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


@router.get("/runs/{run_id}")
async def run_detail(run_id: RunId, request: Request) -> dict:
    try:
        loaded = await request.app.state.bundle.load(run_id)
    except KeyError:
        if await request.app.state.bundle.store.exists(keys.summary(run_id)):  # a visitor-URL run past its 24 hours (spec §19.3.4)
            raise HTTPException(410, replay.EXPIRED) from None
        raise HTTPException(404, "unknown run") from None
    return {
        "run": public_run(loaded.run), "steps": [s.model_dump(mode="json") for s in loaded.steps],
        "findings": [f.model_dump(mode="json") for f in loaded.findings], "rejected": [r.model_dump(mode="json") for r in loaded.rejected],
        "trace": [c.model_dump(mode="json") for c in loaded.trace],
    }


@router.get("/runs/{run_id}/events")
async def run_events(run_id: RunId, request: Request):
    st = request.app.state
    if not st.bus.knows(run_id) and not await st.bundle.exists(run_id):
        raise HTTPException(404, "unknown run")
    return sse_response(st.bus, run_id)


@router.get("/runs/{run_id}/steps/{n}/screenshot.png")
async def screenshot(run_id: RunId, n: StepIndex, request: Request) -> Response:
    bundle = request.app.state.bundle
    try:
        png = await bundle.read_screenshot(run_id, n)
    except FileNotFoundError:
        raise HTTPException(404, "no screenshot") from None
    try:  # a visitor's page is kept 24 hours; no shared cache may keep its screenshot longer (review M4)
        shared = Run.model_validate_json(await bundle.store.get(keys.run(run_id))).source != "visitor-url"
    except Exception:
        shared = False
    cache = "public, max-age=31536000, immutable" if shared else "private, max-age=3600"
    return Response(content=png, media_type="image/png", headers={"Cache-Control": cache})


@router.get("/runs/{run_id}/verifier-off")
async def run_verifier_off(run_id: RunId, request: Request) -> dict:
    """What this run would have reported with the Verifier bypassed. Post hoc, no model calls."""
    try:
        report = await verifier_off(request.app.state.bundle, run_id)
    except KeyError:
        raise HTTPException(404, "unknown run") from None
    return report.model_dump(mode="json")


@router.post("/runs/{run_id}/findings/{finding_id}/decision")
async def record_decision(run_id: RunId, finding_id: FindingId, req: DecisionRequest, request: Request) -> dict:
    """The human gate: the only way a finding becomes approved or rejected (spec D4)."""
    st = request.app.state
    try:
        finding, run = await decide(st.bundle, st.index, st.bus, run_id, finding_id, req.decision, req.reason)
    except KeyError:
        raise HTTPException(404, "unknown run or finding") from None
    except ValidationError:  # a ValueError too, but a server-side one: a stored record no longer parses
        log.exception("decision on %s: a stored record is unreadable", run_id)
        raise HTTPException(500, UNREADABLE) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"finding": finding.model_dump(mode="json"), "run": public_run(run)}


@router.get("/runs/{run_id}/patch")
async def run_patch(run_id: RunId, request: Request) -> Response:
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
    try:
        body = json.loads(latest.read_text(encoding="utf-8"))
        public = eval_dir / "public.json"
        extra = json.loads(public.read_text(encoding="utf-8")) if public.exists() else []
        if not isinstance(body, dict) or not isinstance(extra, list):
            raise ValueError("latest.json must hold an object and public.json a list")
    except (OSError, ValueError) as exc:  # an operator's file, not a visitor's input: log it, and the Eval tab shows "no results"
        log.warning("eval results unreadable: %s", exc)
        raise HTTPException(404, "eval results unreadable: see the server log") from None
    body["public"] = extra
    return body


def _focuslog(request: Request) -> list[dict]:
    st = request.app.state
    if not st.settings.voice_focuslog:
        raise HTTPException(404, "the voice recording kit is off (PARITY_VOICE_FOCUSLOG=1 enables it for a local recording)")
    return st.voice_focuslog


@router.post("/voice/focuslog")
async def voice_focuslog_add(entry: FocusEntry, request: Request) -> dict:
    log = _focuslog(request)
    log.append(entry.model_dump())
    del log[:-FOCUSLOG_MAX]
    return {"count": len(log)}


@router.get("/voice/focuslog")
async def voice_focuslog_list(request: Request) -> dict:
    return {"entries": list(_focuslog(request))}


@router.delete("/voice/focuslog")
async def voice_focuslog_clear(request: Request) -> dict:
    log = _focuslog(request)
    cleared = len(log)
    log.clear()
    return {"cleared": cleared}
