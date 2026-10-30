"""audit_view: the one unit that turns a screen into findings (spec docs/19 §18.3).

capture → seer → comparator (≤ 2 tries with verifier feedback) → verifier → judge. Findings are
persisted only here. The P1 runner calls it directly; in P2 it becomes the agent's tool unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page

from parity.api.events import EventBus
from parity.config import Settings
from parity.pipeline.capture import capture
from parity.pipeline.comparator import compare
from parity.pipeline.judge import judge
from parity.pipeline.seer import see
from parity.pipeline.verifier import NOT_ANNOUNCED, normalise, verify
from parity.store.bundle import RunBundle
from parity.store.models import Capture, Event, Finding, FindingStatus, ModelCall, Rejected, Run, Step

log = logging.getLogger(__name__)
MAX_COMPARATOR_ATTEMPTS = 2


@dataclass(frozen=True)
class Ablation:
    use_screenshot: bool = True
    use_tree: bool = True
    use_grounding: bool = True  # False: skip the Seer (no percept list)


@dataclass
class FindingBrief:
    id: str
    sighted: str
    screen_reader: str


@dataclass
class AuditSummary:
    verified: list[FindingBrief]
    rejected: int
    axe_violations: int


@dataclass
class RunContext:
    settings: Settings
    client: Any
    bus: EventBus
    bundle: RunBundle
    index: Any
    run: Run
    base_url: str
    ablation: Ablation = field(default_factory=Ablation)
    findings: list[Finding] = field(default_factory=list)
    rejected: list[Rejected] = field(default_factory=list)

    async def emit(self, type: str, data: dict[str, Any] | None = None) -> Event:
        event = Event(type=type, run_id=self.run.id, data=data or {})
        self.bundle.add_event(self.run.id, event)
        self.bus.publish(self.run.id, event)
        return event

    async def record_call(self, call: ModelCall) -> None:
        """TraceSink for this run: bundle, cost totals, index, event."""
        self.bundle.add_trace(self.run.id, call)
        self.run.tokens += call.total_tokens
        self.run.cost_usd = round(self.run.cost_usd + call.cost_usd, 8)
        await self._index_safe("insert_call", call)
        await self.emit("model.call", {
            "stage": call.stage, "model": call.model, "request_id": call.request_id, "tokens": call.total_tokens,
            "latency_ms": call.latency_ms, "cost_usd": call.cost_usd, "cache_hit": call.cache_hit, "attempt": call.attempt,
            "http_status": call.http_status, "error": call.error,
        })

    async def save_finding(self, finding: Finding) -> None:
        await self.bundle.write_finding(finding)
        await self._index_safe("upsert_finding", finding)

    async def save_run(self) -> None:
        await self.bundle.write_run(self.run)
        await self._index_safe("upsert_run", self.run)

    async def _index_safe(self, method: str, obj: Any) -> None:
        try:
            await getattr(self.index, method)(obj)
        except Exception as exc:  # the index is a cache; a failed index write never fails the run
            log.warning("index %s failed (%s); bundle is written, index can be rebuilt", method, exc)


def _sr_role_name(result_element, capture: Capture, quote: str) -> tuple[str, str]:
    if normalise(quote) == NOT_ANNOUNCED or result_element is None:
        return "", ""
    for node in capture.ax_nodes:
        if node.backend_id == result_element.backend_id:
            return node.role, node.name
    return "", ""


def brief(finding: Finding) -> FindingBrief:
    sr = f'{finding.sr_role}, "{finding.sr_name}"' if finding.sr_role or finding.sr_name else NOT_ANNOUNCED
    return FindingBrief(id=finding.id, sighted=finding.sighted_text, screen_reader=sr)


async def audit_view(ctx: RunContext, page: Page, step_index: int, reason: str) -> AuditSummary:
    settings, run = ctx.settings, ctx.run
    cap = await capture(page, step_index)
    step = Step(run_id=run.id, index=step_index, url=cap.url, viewport=cap.viewport)
    await ctx.bundle.write_step(step, cap)
    run.axe_violations += len(cap.axe_violations)
    await ctx.emit("step.captured", {"index": step_index, "url": cap.url, "axe_violations": len(cap.axe_violations), "ax_nodes": len(cap.ax_nodes), "reason": reason})

    percepts = []
    if ctx.ablation.use_grounding and ctx.ablation.use_screenshot:
        percepts = await see(ctx.client, cap, run.id, model=settings.model_for("seer"))
    await ctx.emit("seer.done", {"index": step_index, "percepts": [p.model_dump(mode="json") for p in percepts]})

    new_findings: list[Finding] = []
    rejected_here = 0
    feedback: list[str] | None = None
    for attempt in range(1, MAX_COMPARATOR_ATTEMPTS + 1):
        candidates = await compare(
            ctx.client, cap, percepts, run.id, feedback, model=settings.model_for("comparator"),
            use_screenshot=ctx.ablation.use_screenshot, use_tree=ctx.ablation.use_tree,
        )
        await ctx.emit("comparator.candidates", {"index": step_index, "n": len(candidates), "attempt": attempt})
        failures: list[str] = []
        for cand in candidates:
            result = verify(cand, cap, ctx.findings)
            if result.passed and result.element is not None:
                role, name = _sr_role_name(result.element, cap, cand.sr_quote)
                finding = Finding(
                    id=f"{run.id}-f{len(ctx.findings) + 1:02d}", run_id=run.id, step_index=step_index, status=FindingStatus.verified,
                    sighted_text=cand.sighted_text, sr_role=role, sr_name=name, why_it_matters=cand.why_it_matters,
                    bbox=cand.bbox, element=result.element, verifier=result,
                )
                ctx.findings.append(finding)
                new_findings.append(finding)
                await ctx.save_finding(finding)
                await ctx.emit("verifier.result", {"index": step_index, "passed": True, "finding_id": finding.id, "attempt": attempt,
                                                   "finding": finding.model_dump(mode="json")})
            else:
                rejected = Rejected(id=f"{run.id}-r{len(ctx.rejected) + 1:02d}", run_id=run.id, step_index=step_index, candidate=cand, verifier=result)
                ctx.rejected.append(rejected)
                rejected_here += 1
                await ctx.bundle.write_rejected(rejected)
                await ctx.emit("verifier.result", {"index": step_index, "passed": False, "rejected_id": rejected.id, "attempt": attempt,
                                                   "candidate": cand.model_dump(mode="json"), "checks": {k: v.model_dump() for k, v in result.checks.items()},
                                                   "feedback": result.feedback})
                if result.feedback:
                    failures.append(result.feedback)
        if not failures:
            break
        feedback = list(dict.fromkeys(failures))

    for finding in new_findings:
        judgement = await judge(ctx.client, finding, cap, run.id, model=settings.model_for("judge"))
        finding.judgement = judgement
        finding.status = FindingStatus.judged
        await ctx.save_finding(finding)
        await ctx.emit("judge.result", {"finding_id": finding.id, "judgement": judgement.model_dump(mode="json")})

    run.findings_verified = len(ctx.findings)
    run.findings_rejected = len(ctx.rejected)
    await ctx.save_run()
    await ctx.bundle.flush(run.id)
    return AuditSummary(verified=[brief(f) for f in new_findings], rejected=rejected_here, axe_violations=len(cap.axe_violations))
