"""The human gate (spec §6, D4).

After the walk, code proposes a fix and re-audits it for every finding the judge called a barrier;
then nothing moves a finding to approved or rejected except a recorded decision. Approving means
recording the decision and exporting a .patch: the hosted store never changes.

"Pending" has one definition, used by the runner, the decision route and the workbench card: a
finding with a proposed fix and no decision. The re-audit is evidence for the human, not a gate.
"""

from __future__ import annotations

import asyncio
import time
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from playwright.async_api import Page

from parity.meta.client import MetaError
from parity.pipeline.fixer import FixNotApplied, FixRejected, combine_patch, locate_in_source, patch_path, propose_fix
from parity.pipeline.reaudit import reaudit
from parity.store.models import Decision, Event, Finding, FindingStatus, Run, RunStatus, Step

log = logging.getLogger(__name__)
PageFactory = Callable[[], Awaitable[Page]]
FIXER_CONCURRENCY = 4
_locks: dict[tuple[int, str], asyncio.Lock] = {}


class ConflictError(Exception):
    """The decision cannot apply: the finding is already decided, or there is no fix to approve."""


def is_pending(finding: Finding) -> bool:
    return finding.fix is not None and finding.decision is None


def run_lock(run_id: str) -> asyncio.Lock:
    """One lock per run (and loop): decisions and the runner's final status never race on the bundle."""
    key = (id(asyncio.get_running_loop()), run_id)
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


async def save_merged(ctx, finding: Finding) -> None:
    """Write the finding without clobbering a decision a human recorded while this stage was running."""
    async with run_lock(ctx.run.id):
        current = await ctx.bundle.read_finding(ctx.run.id, finding.id)
        if current is not None and current.decision is not None:
            finding.decision, finding.status = current.decision, current.status
        await ctx.save_finding(finding)


FIX_BUDGET_FRACTION = 0.8  # no fix or re-audit starts after this share of the run deadline: the run finishes with what it has
BUDGET_REASON = "run time budget used up before this could start (the walk's evidence stands; approve or reject what was proposed)"


async def fix_findings(ctx, page_factory: PageFactory, *, deadline: float | None = None, clock=time.perf_counter) -> int:
    """fixer (concurrently) then re-audit (one page, in order) for each barrier. Returns how many fixes
    were proposed. Never fails the run: the walk's evidence stands even if this stage cannot run for one finding,
    and nothing new starts past ``deadline`` (a perf_counter time), so a long walk ends inside the run's budget
    instead of being failed by it."""
    settings, run = ctx.settings, ctx.run
    barriers = [f for f in ctx.findings if f.judgement and f.judgement.is_barrier is True]
    gate = asyncio.Semaphore(FIXER_CONCURRENCY)
    over_budget = (lambda: deadline is not None and clock() > deadline)

    async def propose(finding: Finding):
        cap = ctx.captures.get(finding.step_index)
        if cap is None:
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": "no capture kept for this screen"})
            return finding, None
        try:
            async with gate:
                if over_budget():
                    await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": BUDGET_REASON})
                    return finding, None
                return finding, await propose_fix(ctx.client, finding, cap, run.id, model=settings.model_for("fixer"))
        except (FixRejected, FixNotApplied) as exc:
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": str(exc)})
        except MetaError as exc:
            log.warning("fixer failed for %s: %s (request %s)", finding.id, exc, exc.request_id)
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": f"Meta API error {exc.status} (request_id {exc.request_id})"})
        except Exception as exc:  # a bug or an infrastructure error in this stage must not hide the verified findings
            log.exception("fixer crashed for %s", finding.id)
            await ctx.emit("fixer.rejected", {"finding_id": finding.id, "reason": f"{type(exc).__name__}: {exc}"})
        return finding, None

    proposed = 0
    for finding, fix in await asyncio.gather(*(propose(f) for f in barriers)):
        if fix is None:
            continue
        finding.fix = fix
        finding.status = FindingStatus.fix_proposed
        await save_merged(ctx, finding)
        await ctx.emit("fixer.proposed", {"finding_id": finding.id, "diff": fix.diff, "fix": fix.model_dump(mode="json")})
        proposed += 1
        cap = ctx.captures[finding.step_index]
        if over_budget():
            await ctx.emit("reaudit.failed", {"finding_id": finding.id, "reason": BUDGET_REASON})
            continue
        try:
            result = await reaudit(ctx.client, page_factory, cap.html, cap.url, fix, finding, run.id, model=settings.model_for("comparator"))
        except Exception as exc:  # a re-audit that cannot run leaves the fix unverified; the card says so
            log.exception("re-audit failed for %s", finding.id)
            await ctx.emit("reaudit.failed", {"finding_id": finding.id, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        finding.reaudit = result
        finding.status = FindingStatus.reaudited
        await save_merged(ctx, finding)
        await ctx.emit("reaudit.result", {"finding_id": finding.id, "gap_closed": result.gap_closed, "before": result.sr_name_before,
                                          "after": result.sr_name_after, "reaudit": result.model_dump(mode="json")})
    return proposed


async def build_patch(bundle, run_id: str, findings: list[Finding], steps: list[Step]) -> tuple[str, list[str]]:
    """One combined diff per file from the served source, so the approved fixes apply together. A fix that cannot
    be placed in the source (or has no source) is left out, and named, rather than making the patch unusable."""
    approved = [f for f in findings if f.status == FindingStatus.approved and f.fix is not None]
    url_of = {s.index: s.url for s in steps}
    by_path: dict[str, list[Finding]] = defaultdict(list)
    for f in approved:
        by_path[patch_path(url_of.get(f.step_index, ""))].append(f)
    parts: list[str] = []
    excluded: list[str] = []
    for path, group in by_path.items():
        base = await bundle.read_source(run_id, group[0].step_index)
        if not base:
            excluded.extend(f.id for f in group)
            continue
        placeable = [f for f in group if locate_in_source(base, f.element) is not None]
        excluded.extend(f.id for f in group if f not in placeable)
        if not placeable:
            continue
        try:
            parts.append(combine_patch(base, [(f.element, f.fix.after_html) for f in placeable], path))
        except FixNotApplied as exc:  # overlapping fixes: keep the first, drop the rest of the overlap
            log.warning("patch for %s: %s; exporting the fixes one by one", path, exc)
            kept: list[Finding] = []
            for f in placeable:
                try:
                    combine_patch(base, [(x.element, x.fix.after_html) for x in [*kept, f]], path)
                    kept.append(f)
                except FixNotApplied:
                    excluded.append(f.id)
            if kept:
                parts.append(combine_patch(base, [(f.element, f.fix.after_html) for f in kept], path))
    if excluded:
        log.warning("fix.patch for %s leaves out %s: not placeable in the served source", run_id, excluded)
    return "".join(parts), excluded


async def decide(bundle, index, bus, run_id: str, finding_id: str, decision: str, reason: str) -> tuple[Finding, Run]:
    """Record a human decision; rebuild fix.patch from the approved fixes; finish the run when nothing is pending.
    Serialised per run: two decisions never race on the bundle."""
    reason = (reason or "").strip()
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be approve or reject")
    if not reason:
        raise ValueError("a reason is required")
    async with run_lock(run_id):
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
        patch, excluded = await build_patch(bundle, run_id, findings, loaded.steps)
        if patch:
            await bundle.write_patch(run_id, patch)
        run = loaded.run
        pending = [f for f in findings if is_pending(f)]
        if run.status == RunStatus.awaiting_review and not pending:
            run.status = RunStatus.done
            await bundle.write_run(run)
        if index is not None:
            try:
                await index.upsert_finding(finding)
                await index.upsert_run(run)
            except Exception:  # the bundle is the truth; the index is rebuilt at boot
                log.exception("index update failed for decision on %s", finding_id)
        event = Event(type="decision.recorded", run_id=run_id, data={
            "finding_id": finding.id, "decision": finding.decision.model_dump(mode="json"), "status": finding.status,
            "run_status": run.status, "approved": len(approved), "pending": len(pending), "patch_excluded": excluded,
        })
        await bundle.append_event(run_id, event)
        if bus is not None and bus.knows(run_id):  # a run this process streamed: live viewers and in-memory history get it too
            bus.publish(run_id, event)
        return finding, run
