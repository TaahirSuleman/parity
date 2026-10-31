"""The human gate (spec §6, D4).

After the walk, code proposes a fix and re-audits it for every finding the judge called a barrier;
then nothing moves a finding to approved or rejected except a recorded decision. Approving means
recording the decision and exporting a .patch: the hosted store never changes.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from playwright.async_api import Page

from parity.meta.client import MetaError
from parity.pipeline.fixer import FixNotApplied, FixRejected, propose_fix
from parity.pipeline.reaudit import reaudit
from parity.store.models import Decision, Event, Finding, FindingStatus, Run, RunStatus

log = logging.getLogger(__name__)
PageFactory = Callable[[], Awaitable[Page]]


class ConflictError(Exception):
    """The decision cannot apply: the finding is already decided, or there is no fix to approve."""


async def fix_findings(ctx, page_factory: PageFactory) -> int:
    """fixer -> re-audit for each barrier. Returns how many fixes were proposed. Never fails the run:
    the walk's evidence stands even if the fixer or the re-audit cannot run for one finding."""
    settings, run = ctx.settings, ctx.run
    proposed = 0
    for finding in ctx.findings:
        if not (finding.judgement and finding.judgement.is_barrier is True):
            continue
        cap = ctx.captures.get(finding.step_index)
        if cap is None:
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": "no capture kept for this screen"})
            continue
        try:
            fix = await propose_fix(ctx.client, finding, cap, run.id, model=settings.model_for("fixer"))
        except (FixRejected, FixNotApplied) as exc:
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": str(exc)})
            continue
        except MetaError as exc:
            log.warning("fixer failed for %s: %s (request %s)", finding.id, exc, exc.request_id)
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": f"Meta API error {exc.status} (request_id {exc.request_id})"})
            continue
        except Exception as exc:  # a bug or an infrastructure error in this stage must not hide the verified findings
            log.exception("fixer crashed for %s", finding.id)
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        finding.fix = fix
        finding.status = FindingStatus.fix_proposed
        await ctx.save_finding(finding)
        await ctx.emit("fixer.proposed", {"finding_id": finding.id, "diff": fix.diff, "fix": fix.model_dump(mode="json")})
        proposed += 1
        try:
            result = await reaudit(ctx.client, page_factory, cap.html, cap.url, fix, finding, run.id, model=settings.model_for("comparator"))
        except Exception as exc:  # a re-audit that cannot run leaves the fix unverified; the card says so
            log.exception("re-audit failed for %s", finding.id)
            await ctx.emit("reaudit.failed", {"finding_id": finding.id, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        finding.reaudit = result
        finding.status = FindingStatus.reaudited
        await ctx.save_finding(finding)
        await ctx.emit("reaudit.result", {"finding_id": finding.id, "gap_closed": result.gap_closed, "before": result.sr_name_before,
                                          "after": result.sr_name_after, "reaudit": result.model_dump(mode="json")})
    return proposed


async def decide(bundle, index, bus, run_id: str, finding_id: str, decision: str, reason: str) -> tuple[Finding, Run]:
    """Record a human decision; rebuild fix.patch from the approved fixes; finish the run when nothing is pending."""
    reason = (reason or "").strip()
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be approve or reject")
    if not reason:
        raise ValueError("a reason is required")
    loaded = await bundle.load(run_id)  # KeyError for an unknown run
    finding = next((f for f in loaded.findings if f.id == finding_id), None)
    if finding is None:
        raise KeyError(finding_id)
    if finding.decision is not None:
        raise ConflictError(f"finding {finding_id} was already {finding.status}")
    if decision == "approve" and finding.fix is None:
        raise ConflictError("there is no proposed fix to approve")

    finding.decision = Decision(decision=decision, reason=reason)
    finding.status = FindingStatus.approved if decision == "approve" else FindingStatus.rejected
    await bundle.write_finding(finding)
    findings = [finding if f.id == finding.id else f for f in loaded.findings]
    approved = [f for f in findings if f.status == FindingStatus.approved and f.fix is not None]
    patch = "".join(f.fix.diff for f in approved)
    if patch:
        await bundle.write_patch(run_id, patch)
    run = loaded.run
    pending = [f for f in findings if f.fix is not None and f.decision is None]
    if run.status == RunStatus.awaiting_review and not pending:
        run.status = RunStatus.done
        await bundle.write_run(run)
    if index is not None:
        await index.upsert_finding(finding)
        await index.upsert_run(run)
    event = Event(type="decision.recorded", run_id=run_id, data={
        "finding_id": finding.id, "decision": finding.decision.model_dump(mode="json"), "status": finding.status,
        "run_status": run.status, "approved": len(approved), "pending": len(pending),
    })
    await bundle.append_event(run_id, event)
    if bus is not None and bus.knows(run_id):  # a run this process streamed: live viewers and in-memory history get it too
        bus.publish(run_id, event)
    return finding, run
