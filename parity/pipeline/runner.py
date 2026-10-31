"""Runner: owns a run from start to finish and writes the bundle after every stage."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from playwright.async_api import Page

from parity.agent.loop import AgentMode, AgentResult, result_dict, run_agent
from parity.api.events import EventBus
from parity.config import Settings
from parity.flows import Flow
from parity.meta.client import MetaError, TraceRouter
from parity.pipeline import browser
from parity.pipeline.audit import Ablation, RunContext, audit_view
from parity.pipeline.gate import fix_findings, is_pending, run_lock
from parity.store.bundle import RunBundle
from parity.store.models import Run, RunMode, RunStatus, now

log = logging.getLogger(__name__)
PageFactory = Callable[[], Awaitable[Page]]


def new_run_id() -> str:
    return f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"


async def run_flow(
    settings: Settings, client, bus: EventBus, bundle: RunBundle, index, flow: Flow, *, base_url: str,
    mode: RunMode = RunMode.live, run_id: str | None = None, client_ip_hash: str = "", ablation: Ablation | None = None,
    page_factory: PageFactory = browser.new_page, max_turns: int = 12, agent_mode: AgentMode = "tools",
) -> Run:
    """Own one run end to end: single page → audit_view directly; multi-page → the auditor agent."""
    run = Run(
        id=run_id or new_run_id(), mode=mode, flow_id=flow.id, goal=flow.goal, target_url=base_url.rstrip("/") + flow.start_url,
        status=RunStatus.running, client_ip_hash=client_ip_hash,
    )
    ctx = RunContext(settings=settings, client=client, bus=bus, bundle=bundle, index=index, run=run, base_url=base_url, ablation=ablation or Ablation())
    await bundle.create(run)
    await ctx._index_safe("upsert_run", run)
    router = getattr(client, "trace", None)
    if isinstance(router, TraceRouter):
        router.bind(run.id, ctx.record_call)
    await ctx.emit("run.started", {"flow_id": flow.id, "flow_name": flow.name, "goal": flow.goal, "mode": mode, "target_url": run.target_url,
                                   "single_page": flow.single_page, "agent_mode": None if flow.single_page else agent_mode,
                                   "model": settings.model_for("comparator"), "judge_model": settings.model_for("judge"),
                                   "navigator_model": None if flow.single_page else settings.model_for("navigator")})
    t0 = time.perf_counter()
    page: Page | None = None
    agent: AgentResult | None = None
    try:
        page = await page_factory()
        ctx.page = page
        await page.goto(run.target_url, wait_until="load")
        if flow.single_page:
            summary = await audit_view(ctx, page, 0, reason="single-page flow")
            verified = [b.__dict__ for b in summary.verified]
        else:
            agent = await run_agent(ctx, page, flow, max_turns=max_turns, mode=agent_mode)
            verified = [{"id": f.id, "sighted": f.sighted_text, "screen_reader": f"{f.sr_role}, \"{f.sr_name}\""} for f in ctx.findings]
        final_url = page.url  # where the walk ended, before re-audits reuse the page

        async def same_page() -> Page:
            return page

        fixes = await fix_findings(ctx, same_page)
        pending = await _settle(ctx, t0)  # final state on disk BEFORE the terminal event: readers reacting to it see the final status
        await ctx.emit("run.finished", {
            "status": run.status, "findings_verified": run.findings_verified, "findings_rejected": run.findings_rejected,
            "axe_violations": run.axe_violations, "tokens": run.tokens, "cost_usd": run.cost_usd, "verified": verified,
            "fixes_proposed": fixes, "pending": pending, "agent": result_dict(agent) if agent else None, "final_url": final_url, "duration_ms": run.duration_ms,
        })
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
        await bundle.flush(run.id)
    return run


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
