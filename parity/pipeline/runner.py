"""Runner: owns a run from start to finish and writes the bundle after every stage."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from parity.agent.loop import AgentMode, AgentResult, result_dict, run_agent, wall_reason
from parity.api.events import EventBus
from parity.config import Settings
from parity.flows import Flow
from parity.meta.client import MetaError, TraceRouter
from parity.pipeline import browser
from parity.pipeline.audit import Ablation, RunContext, audit_view
from parity.pipeline import gate as gate_stage
from parity.pipeline.gate import fix_findings, is_pending, run_lock
from parity.pipeline.guard import robots_allows
from parity.store.bundle import RunBundle
from parity.store.models import Run, RunMode, RunStatus, now

log = logging.getLogger(__name__)
PageFactory = Callable[..., Awaitable[Page]]  # called bare for the store; with external=True, own_origin and on_blocked for a page we do not serve


@dataclass(frozen=True)
class VisitorRequest:
    """A page a visitor chose (spec §19.3.2): what the run record keeps beyond the flow."""

    origin: str
    consent_at: datetime
    screens: int


def new_run_id() -> str:
    return f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{secrets.token_hex(4)}"  # 16 bits collided in 0.55% of 30-id bursts and merged two bundles


async def run_flow(
    settings: Settings, client, bus: EventBus, bundle: RunBundle, index, flow: Flow, *, base_url: str,
    mode: RunMode = RunMode.live, run_id: str | None = None, client_ip_hash: str = "", ablation: Ablation | None = None,
    page_factory: PageFactory = browser.new_page, max_turns: int = 12, agent_mode: AgentMode = "tools", public: bool = False, own_origin: str = "",
    visitor: VisitorRequest | None = None, cost_cap_usd: float | None = None, timeout_s: int | None = None, max_screens: int | None = None,
) -> Run:
    """Own one run end to end: single page → audit_view directly; multi-page → the auditor agent."""
    public = public or flow.public  # a flow on a page we do not serve is guarded whatever the caller passed (spec §17, §19.2)
    run = Run(
        id=run_id or new_run_id(), mode=mode, flow_id=flow.id, goal=flow.goal, target_url=flow.target_url(base_url),
        status=RunStatus.running, client_ip_hash=client_ip_hash,
        source="visitor-url" if visitor else "flow", origin=visitor.origin if visitor else "", consent_at=visitor.consent_at if visitor else None,
        screens=visitor.screens if visitor else None,
    )
    ctx = RunContext(settings=settings, client=client, bus=bus, bundle=bundle, index=index, run=run, base_url=base_url, ablation=ablation or Ablation(), public=public,
                     cost_cap_usd=cost_cap_usd)
    deadline_s = timeout_s or settings.run_timeout_s
    await bundle.create(run)
    await ctx._index_safe("upsert_run", run)
    router = getattr(client, "trace", None)
    if isinstance(router, TraceRouter):
        router.bind(run.id, ctx.record_call)
    await ctx.emit("run.started", {"flow_id": flow.id, "flow_name": flow.name, "goal": flow.goal, "mode": mode, "target_url": run.target_url,
                                   "single_page": flow.single_page, "agent_mode": None if flow.single_page else agent_mode,
                                   "public": public, "attribution": flow.attribution,
                                   "model": settings.model_for("comparator"), "judge_model": settings.model_for("judge"),
                                   "navigator_model": None if flow.single_page else settings.model_for("navigator")})
    t0 = time.perf_counter()
    page: Page | None = None
    agent: AgentResult | None = None
    try:
      async with asyncio.timeout(deadline_s):
          if public and flow.origin:  # a page we do not serve: every request is re-checked and the user agent names Parity (spec §19.3.1)
              page = await page_factory(external=True, own_origin=own_origin, on_blocked=_request_blocked(ctx))
          else:
              page = await page_factory()
          ctx.page = page
          if public and not robots_allows(run.target_url):
              await ctx.emit("nav.blocked", {"turn": 0, "url": run.target_url, "reason": "robots.txt disallows the start URL; nothing was fetched"})
              agent = AgentResult(0, False, False, "stopped: robots.txt disallows the start URL")
              verified = []
          elif outcome := await _open(ctx, page, run.target_url, public):  # a public page that did not answer, was aborted, or is a wall
              agent = AgentResult(0, False, False, outcome)
              verified = []
          elif flow.single_page:
              summary = await audit_view(ctx, page, 0, reason="single-page flow")
              verified = [b.__dict__ for b in summary.verified]
              if ctx.over_budget:
                  agent = AgentResult(0, False, False, "cost cap reached")
          else:
              agent = await run_agent(ctx, page, flow, max_turns=max_turns, mode=agent_mode, max_screens=max_screens)
              verified = [{"id": f.id, "sighted": f.sighted_text, "screen_reader": f"{f.sr_role}, \"{f.sr_name}\""} for f in ctx.findings]
          final_url = page.url  # where the walk ended, before re-audits reuse the page

          async def same_page() -> Page:
              return page

          # a public site is never patched or re-fetched (§17); nothing new starts past 80% of the deadline, so the run ends inside it
          fixes = await fix_findings(ctx, same_page, deadline=t0 + settings.run_timeout_s * gate_stage.FIX_BUDGET_FRACTION) if ctx.ablation.run_fixes and not public else 0
          pending = await _settle(ctx, t0)  # final state on disk BEFORE the terminal event: readers reacting to it see the final status
          await ctx.emit("run.finished", {
              "status": run.status, "findings_verified": run.findings_verified, "findings_rejected": run.findings_rejected,
              "axe_violations": run.axe_violations, "tokens": run.tokens, "cost_usd": run.cost_usd, "verified": verified,
              "fixes_proposed": fixes, "pending": pending, "agent": result_dict(agent) if agent else None, "final_url": final_url, "duration_ms": run.duration_ms,
          })
    except TimeoutError:
        run.status = RunStatus.failed
        run.error = f"run deadline of {deadline_s} s exceeded"
        log.error("run %s failed: %s", run.id, run.error)
        await _close(ctx, t0)
        await ctx.emit("run.failed", {"error": run.error})
    except asyncio.CancelledError:  # a server shutdown mid-run (a redeploy): the bundle says so instead of settling as done
        run.status = RunStatus.failed
        run.error = "cancelled: the server shut down during the run"
        log.error("run %s failed: %s", run.id, run.error)
        await asyncio.shield(_close(ctx, t0))
        await asyncio.shield(ctx.emit("run.failed", {"error": run.error}))
        raise
    except MetaError as exc:
        run.status = RunStatus.failed
        run.error = f"Meta API error {exc.status}: {exc} (request_id {exc.request_id}, attempts {exc.attempts})"
        log.error("run %s failed: %s", run.id, run.error)
        await _close(ctx, t0)
        await ctx.emit("run.failed", {"error": run.error})
    except Exception as exc:  # the bundle must still be written and the stream must end
        run.status = RunStatus.failed
        run.error = f"{type(exc).__name__}: {exc}"
        log.exception("run %s failed", run.id)
        await _close(ctx, t0)
        await ctx.emit("run.failed", {"error": run.error})
    finally:
        if run.finished_at is None:
            await _close(ctx, t0)
        if isinstance(router, TraceRouter):
            router.unbind(run.id)
        if page is not None:
            try:
                await page.context.close()
            except Exception:
                pass
        if run.status == RunStatus.failed:
            await ctx.save_run()
        else:
            await _settle(ctx, t0)  # the last word on the status: a decision may have landed since the terminal event
        async with run_lock(run.id):  # a decision recorded during the last write must not be overwritten by it
            await bundle.flush(run.id)
        bundle.forget(run.id)  # the bundle is the record now; the buffers would otherwise grow with every run
        bus.forget(run.id)
    return run


async def _open(ctx: RunContext, page: Page, url: str, public: bool) -> str | None:
    """Navigate to the start URL. On a page we do not serve, a refused connection, a navigation the request guard aborted
    and a bot wall are outcomes the run ends with (spec §17, §19.3), never failures of ours; nothing reaches a model."""
    try:
        await page.goto(url, wait_until="load")
    except PlaywrightError as exc:
        if not public:
            raise
        first = str(exc).splitlines()[0]
        code = re.search(r"net::ERR_[A-Z_]+", first)
        if code and code.group(0) == "net::ERR_BLOCKED_BY_CLIENT":
            reason = "This address is not public."
        else:
            reason = f"the site did not answer: {code.group(0) if code else 'timed out' if 'Timeout' in first else 'navigation failed'}"
        await ctx.emit("nav.blocked", {"turn": 0, "reason": reason})
        return reason
    if public and (wall := await wall_reason(page)):
        await ctx.emit("nav.blocked", {"turn": 0, "url": page.url, "reason": wall})
        return wall
    return None


def _request_blocked(ctx: RunContext):
    """The request guard's report of an aborted request, as a nav.blocked event on the run (the host, never the whole URL)."""

    async def hook(host: str, resource: str, reason: str) -> None:
        await ctx.emit("nav.blocked", {"turn": getattr(ctx.agent, "turn", 0), "host": host, "resource": resource, "reason": f"request to {host} aborted: {reason}"})

    return hook


async def _close(ctx: RunContext, t0: float) -> None:
    """Stamp the end of the run and write it, bundle first then index."""
    ctx.run.finished_at = now()
    ctx.run.duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
    await ctx.save_run()


async def _settle(ctx: RunContext, t0: float) -> int:
    """Under the run's lock: pending is read back from the bundle (a human may have decided fixes while the run
    was still going), the status follows, and the run is written. Returns the number of pending fixes."""
    async with run_lock(ctx.run.id):
        pending = [f for f in (await ctx.bundle.load(ctx.run.id)).findings if is_pending(f)]
        ctx.run.status = RunStatus.awaiting_review if pending else RunStatus.done
        await _close(ctx, t0)
    return len(pending)


async def run_single_page(settings: Settings, client, bus: EventBus, bundle: RunBundle, index, flow: Flow, **kwargs) -> Run:
    """Phase 1 entry point, kept for callers and tests: a run_flow on a single-page flow."""
    return await run_flow(settings, client, bus, bundle, index, flow, **kwargs)
