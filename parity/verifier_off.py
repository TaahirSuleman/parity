"""Verifier on vs off, post hoc (spec docs/19 §18.2): what a run would have reported with the gate bypassed.

Computed from the bundle alone: every candidate the comparator proposed counts as "reported"; the
ones the Verifier rejected are the false reports it prevented. No model calls.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from parity.store.bundle import RunBundle
from parity.store.models import BBox


FALSE_CHECKS = {"located", "sr_quote_exact", "diverges"}


def classify(checks_failed: list[str]) -> str:
    """false: the evidence itself failed; duplicate: only `unique` failed; already_in_axe: only `not_axe` failed."""
    failed = set(checks_failed)
    if failed & FALSE_CHECKS:
        return "false"
    if failed == {"unique"} or failed == {"unique", "not_axe"}:
        return "duplicate"
    if failed == {"not_axe"}:
        return "already_in_axe"
    return "false"


class CandidateRow(BaseModel):
    step_index: int
    sighted_text: str
    sr_quote: str
    bbox: BBox | None = None
    verifier_passed: bool
    kind: str = "verified"  # verified | false | duplicate | already_in_axe
    checks_failed: list[str] = Field(default_factory=list)
    feedback: str | None = None
    finding_id: str | None = None
    rejected_id: str | None = None


class VerifierOffReport(BaseModel):
    run_id: str
    reported: int  # with the Verifier bypassed: every comparator candidate
    verified: int  # what the Verifier let through
    rejected_by_verifier: int
    false_reports: int = 0  # rejections whose evidence failed (located / exact quote / diverges)
    duplicates: int = 0  # re-proposals of an element already reported
    already_in_axe: int = 0  # elements axe-core already reports
    false_vs_labels: int | None = None  # filled by the eval harness when labels exist (P4)
    candidates: list[CandidateRow] = Field(default_factory=list)


async def verifier_off(bundle: RunBundle, run_id: str, client=None) -> VerifierOffReport:
    """Re-score the stored candidates with the Verifier bypassed and persist verifier_off.json.

    ``client`` is accepted only so callers can prove no model call is made: it is never used.
    """
    loaded = await bundle.load(run_id)  # KeyError for an unknown run
    rows: list[CandidateRow] = []
    for f in loaded.findings:
        quote = f'{f.sr_role}, "{f.sr_name}"' if f.sr_role or f.sr_name else "not announced"
        rows.append(CandidateRow(step_index=f.step_index, sighted_text=f.sighted_text, sr_quote=quote, bbox=f.bbox, verifier_passed=True, finding_id=f.id))
    for r in loaded.rejected:
        failed = [name for name, check in r.verifier.checks.items() if not check.passed]
        rows.append(CandidateRow(
            step_index=r.step_index, sighted_text=r.candidate.sighted_text, sr_quote=r.candidate.sr_quote, bbox=r.candidate.bbox,
            verifier_passed=False, kind=classify(failed), checks_failed=failed, feedback=r.verifier.feedback, rejected_id=r.id,
        ))
    rows.sort(key=lambda c: (c.step_index, c.finding_id or c.rejected_id or ""))
    kinds = [c.kind for c in rows]
    report = VerifierOffReport(
        run_id=run_id, reported=len(rows), verified=len(loaded.findings), rejected_by_verifier=len(loaded.rejected),
        false_reports=kinds.count("false"), duplicates=kinds.count("duplicate"), already_in_axe=kinds.count("already_in_axe"), candidates=rows,
    )
    await bundle.store.put(f"runs/{run_id}/verifier_off.json", report.model_dump_json(indent=1).encode(), "application/json")
    return report
