"""The human gate: fixer + re-audit after the walk, and decisions that move findings and write the patch."""

import pytest

from parity.api.events import EventBus
from parity.flows import FLOWS
from parity.pipeline.gate import ConflictError, decide
from parity.pipeline.runner import run_flow
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.store.models import Element, FindingStatus, RunStatus
from tests.helpers import SRC, make_replay_bundle
from tests.test_runner import harness


async def test_run_proposes_fixes_reaudits_and_awaits_review(tmp_path, server_url, page):
    """After the walk: fixer -> re-audit for each barrier, then the run waits for a human."""

    async def factory():
        return page

    async with harness(tmp_path, {}) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["checkout"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.awaiting_review, run.error
    hero = next(f for f in loaded.findings if f.element.dom_id == "f5")
    assert hero.fix and "Pay R1,249" in hero.fix.after_html and hero.fix.diff.startswith("--- a/store/checkout.html")
    assert hero.reaudit and hero.reaudit.gap_closed is True and hero.reaudit.sr_name_after == "Pay R1,249"
    assert hero.status == FindingStatus.reaudited
    types = [e.type for e in loaded.events]
    assert types.index("fixer.proposed") > types.index("judge.result") and "reaudit.result" in types
    # the recorded fixer answer is a <button>: on every other element it changes the tag, so it is refused and never applied
    others = [f for f in loaded.findings if f.element.dom_id != "f5"]
    assert all(f.fix is None and f.status == FindingStatus.judged for f in others)
    assert len([e for e in loaded.events if e.type == "fixer.rejected"]) == len(others)
    finished = next(e for e in loaded.events if e.type == "run.finished").data
    assert finished["status"] == "awaiting_review" and finished["fixes_proposed"] == 1


async def gate(tmp_path):
    root = tmp_path / "data"
    await make_replay_bundle(root)
    bundle = RunBundle(LocalBlobStore(root))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    await index.rebuild(bundle)
    return bundle, index, EventBus(bundle)


async def test_decide_approve_writes_patch_and_finishes_run(tmp_path):
    bundle, index, bus = await gate(tmp_path)
    try:
        finding, run = await decide(bundle, index, bus, SRC, f"{SRC}-f01", "approve", "Looks right")
        assert finding.status == FindingStatus.approved and finding.decision and finding.decision.reason == "Looks right"
        assert run.status == RunStatus.done  # nothing left to review
        patch = await bundle.read_patch(SRC)
        assert patch and "+++ b/store/checkout.html" in patch and 'class="btn">Pay R1,249</button>' in patch  # rebuilt from the served source
        _apply_check(tmp_path, patch)
        events = await bundle.events(SRC)  # persisted in the bundle, not only pushed to the bus
        assert events[-1].type == "decision.recorded" and events[-1].data["run_status"] == "done"
        assert (await bundle.load(SRC)).run.status == RunStatus.done
        assert (await index.get_run(SRC)).status == RunStatus.done
        assert (await bus.history(SRC))[-1].type == "decision.recorded"
    finally:
        await index.close()


async def test_decide_requires_reason_and_a_fix_to_approve(tmp_path):
    bundle, index, bus = await gate(tmp_path)
    try:
        with pytest.raises(ValueError):
            await decide(bundle, index, bus, SRC, f"{SRC}-f01", "approve", "   ")
        with pytest.raises(KeyError):
            await decide(bundle, index, bus, SRC, "nope", "approve", "x")
        with pytest.raises(KeyError):
            await decide(bundle, index, bus, "no-run", f"{SRC}-f01", "approve", "x")
        plain = (await bundle.load(SRC)).findings[0].model_copy(update={"id": f"{SRC}-f02", "fix": None, "reaudit": None, "status": FindingStatus.judged})
        await bundle.write_finding(plain)
        with pytest.raises(ConflictError):  # nothing to approve
            await decide(bundle, index, bus, SRC, plain.id, "approve", "x")
        rejected, _ = await decide(bundle, index, bus, SRC, plain.id, "reject", "not a barrier here")
        assert rejected.status == FindingStatus.rejected
        with pytest.raises(ConflictError):  # decided once
            await decide(bundle, index, bus, SRC, plain.id, "reject", "again")
    finally:
        await index.close()


async def test_patch_contains_only_approved(tmp_path):
    bundle, index, bus = await gate(tmp_path)
    try:
        first = (await bundle.load(SRC)).findings[0]
        second = first.model_copy(update={"id": f"{SRC}-f02", "element": Element(backend_id=2, css_path="#f6", dom_id="f6"),
                                          "fix": first.fix.model_copy(update={"after_html": '<button id="f6" class="icon" aria-label="Delete">🗑️</button>'})})
        await bundle.write_finding(second)
        _, run = await decide(bundle, index, bus, SRC, first.id, "approve", "yes")
        assert run.status == RunStatus.awaiting_review  # one fix still undecided
        _, run = await decide(bundle, index, bus, SRC, second.id, "reject", "no")
        assert run.status == RunStatus.done
        patch = await bundle.read_patch(SRC)
        assert "Pay R1,249" in patch and 'aria-label="Delete"' not in patch  # the rejected fix is not exported
        _apply_check(tmp_path, patch)
    finally:
        await index.close()


async def test_fixer_errors_do_not_fail_the_run(tmp_path, server_url, page):
    """Any failure inside the fixer stage is recorded per finding; the walk's verified findings still ship."""

    async def factory():
        return page

    async with harness(tmp_path, {"errors": {"fixer": RuntimeError("fixer exploded")}}) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["checkout"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.done and run.error is None  # no fix proposed, so nothing to review
    assert loaded.findings and all(f.fix is None and f.status == FindingStatus.judged for f in loaded.findings)
    rejected = [e for e in loaded.events if e.type == "fixer.rejected"]
    assert rejected and "fixer exploded" in rejected[0].data["reason"]
    assert loaded.events[-1].type == "run.finished" and loaded.events[-1].data["fixes_proposed"] == 0


# --- review fix pass: decisions are serialised, pending means "fix without a decision", patches combine ---
import asyncio
import shutil
import subprocess

from tests.test_fixer import ROOT, SOURCE


def _apply_check(tmp_path, patch: str) -> None:
    (tmp_path / "apply" / "store").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "store" / "checkout.html", tmp_path / "apply" / "store" / "checkout.html")
    (tmp_path / "apply" / "fix.patch").write_text(patch)
    res = subprocess.run(["git", "apply", "--check", "fix.patch"], cwd=tmp_path / "apply", capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


async def test_concurrent_approvals_keep_both_fixes_in_one_applicable_patch(tmp_path):
    bundle, index, bus = await gate(tmp_path)
    try:
        first = (await bundle.load(SRC)).findings[0]
        second = first.model_copy(update={"id": f"{SRC}-f02", "element": Element(backend_id=2, css_path="#f6", dom_id="f6"),
                                          "fix": first.fix.model_copy(update={"after_html": '<button id="f6" class="icon" aria-label="Delete">🗑️</button>'})})
        await bundle.write_finding(second)
        results = await asyncio.gather(decide(bundle, index, bus, SRC, first.id, "approve", "a"), decide(bundle, index, bus, SRC, second.id, "approve", "b"))
        assert {r[1].status for r in results} and (await bundle.load(SRC)).run.status == RunStatus.done
        patch = await bundle.read_patch(SRC)
        assert "Pay R1,249" in patch and 'aria-label="Delete"' in patch and patch.count("+++ b/store/checkout.html") == 1
        _apply_check(tmp_path, patch)
    finally:
        await index.close()


async def test_same_finding_decided_twice_concurrently_yields_one_decision(tmp_path):
    bundle, index, bus = await gate(tmp_path)
    try:
        outcomes = await asyncio.gather(decide(bundle, index, bus, SRC, f"{SRC}-f01", "approve", "a"),
                                        decide(bundle, index, bus, SRC, f"{SRC}-f01", "reject", "b"), return_exceptions=True)
        assert sum(isinstance(o, ConflictError) for o in outcomes) == 1 and sum(not isinstance(o, Exception) for o in outcomes) == 1
        assert [e.type for e in await bundle.events(SRC)].count("decision.recorded") == 1
    finally:
        await index.close()


async def test_a_fix_whose_reaudit_failed_can_still_be_decided(tmp_path):
    from parity.pipeline.gate import is_pending

    bundle, index, bus = await gate(tmp_path)
    try:
        f = (await bundle.load(SRC)).findings[0].model_copy(update={"reaudit": None, "status": FindingStatus.fix_proposed})
        await bundle.write_finding(f)
        assert is_pending(f) is True
        decided, run = await decide(bundle, index, bus, SRC, f.id, "approve", "the before/after is convincing enough")
        assert decided.status == FindingStatus.approved and run.status == RunStatus.done
    finally:
        await index.close()


async def test_run_status_counts_decisions_made_during_the_run(tmp_path, server_url, page):
    """Approving while the run is still fixing other findings must not leave it awaiting review."""

    async def factory():
        return page

    run_id = "midrun-decision"
    async with harness(tmp_path, {}) as (settings, client, bus, bundle, index):
        bus.open(run_id)
        task = asyncio.create_task(run_flow(settings, client, bus, bundle, index, FLOWS["checkout"], base_url=server_url, page_factory=factory, run_id=run_id))
        decided = []
        async for ev in bus.subscribe(run_id):
            if ev.type == "reaudit.result":
                decided.append((await decide(bundle, index, bus, run_id, ev.data["finding_id"], "approve", "mid-run"))[0].id)
            if ev.type in ("run.finished", "run.failed"):
                break
        run = await task
        loaded = await bundle.load(run.id)
        indexed = await index.get_run(run.id)
    assert decided, "no re-audit happened"
    # The persisted run is the truth: whichever of the runner's final settle and the last decision ran second
    # saw no pending fix and wrote "done". The in-memory object and the run.finished payload may predate it.
    assert loaded.run.status == RunStatus.done, loaded.run.error
    assert indexed.status == RunStatus.done
    assert all(f.decision is not None for f in loaded.findings if f.fix is not None)


async def test_patch_excludes_a_fix_it_cannot_place_and_still_applies(tmp_path):
    """One unplaceable fix must not cost the file its combined patch; the patch stays applicable."""
    bundle, index, bus = await gate(tmp_path)
    try:
        first = (await bundle.load(SRC)).findings[0]
        ghost = first.model_copy(update={"id": f"{SRC}-f02", "element": Element(backend_id=3, css_path="div#nope > p:nth-of-type(1)", outer_html="<p>x</p>"),
                                         "fix": first.fix.model_copy(update={"after_html": "<p>y</p>"})})
        await bundle.write_finding(ghost)
        await decide(bundle, index, bus, SRC, first.id, "approve", "a")
        _, run = await decide(bundle, index, bus, SRC, ghost.id, "approve", "b")
        patch = await bundle.read_patch(SRC)
        assert "Pay R1,249" in patch and "<p>y</p>" not in patch and patch.count("+++ b/") == 1
        _apply_check(tmp_path, patch)
        events = await bundle.events(SRC)
        assert events[-1].data["patch_excluded"] == [ghost.id]
    finally:
        await index.close()
