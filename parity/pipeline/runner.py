"""Runner: owns a run from start to finish and writes the bundle after every stage."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from playwright.async_api import Page

from parity.api.events import EventBus
from parity.config import Settings
from parity.flows import Flow
from parity.meta.client import MetaError, TraceRouter
from parity.pipeline import browser
from parity.pipeline.audit import Ablation, RunContext, audit_view
from parity.store.bundle import RunBundle
from parity.store.models import Run, RunMode, RunStatus, now

log = logging.getLogger(__name__)
PageFactory = Callable[[], Awaitable[Page]]


def new_run_id() -> str:
    return f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"


async def run_single_page(
    settings: Settings, client, bus: EventBus, bundle: RunBundle, index, flow: Flow, *, base_url: str,
    mode: RunMode = RunMode.live, run_id: str | None = None, client_ip_hash: str = "", ablation: Ablation | None = None,
    page_factory: PageFactory = browser.new_page,
) -> Run:
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
                                   "model": settings.model_for("comparator"), "judge_model": settings.model_for("judge")})
    t0 = time.perf_counter()
    page: Page | None = None
    try:
        page = await page_factory()
        await page.goto(run.target_url, wait_until="load")
        summary = await audit_view(ctx, page, 0, reason="single-page flow")
        run.status = RunStatus.done
        await ctx.emit("run.finished", {
            "status": run.status, "findings_verified": run.findings_verified, "findings_rejected": run.findings_rejected,
            "axe_violations": run.axe_violations, "tokens": run.tokens, "cost_usd": run.cost_usd,
            "verified": [b.__dict__ for b in summary.verified],
        })
    except MetaError as exc:
        run.status = RunStatus.failed
        run.error = f"Meta API error {exc.status}: {exc} (request_id {exc.request_id}, attempts {exc.attempts})"
        log.error("run %s failed: %s", run.id, run.error)
        await ctx.emit("run.failed", {"error": run.error})
    except Exception as exc:  # the bundle must still be written and the stream must end
        run.status = RunStatus.failed
        run.error = f"{type(exc).__name__}: {exc}"
        log.exception("run %s failed", run.id)
        await ctx.emit("run.failed", {"error": run.error})
    finally:
        run.finished_at = now()
        run.duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
        if isinstance(router, TraceRouter):
            router.unbind(run.id)
        if page is not None:
            try:
                await page.context.close()
            except Exception:
                pass
        await ctx.save_run()
        await bundle.flush(run.id)
    return run
