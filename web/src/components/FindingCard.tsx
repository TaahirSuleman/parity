import { useState } from "react";
import { CHECK_LABELS, type Finding } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";
import { srQuote } from "./ScreenReaderPanel";

interface Props {
  finding: Finding;
  selected: boolean;
  onSelect: (id: string) => void;
  onDecision?: (id: string, decision: "approve" | "reject", reason: string) => void | Promise<void>;
}

function suggestedReason(finding: Finding): string {
  if (!finding.reaudit) return "";
  return finding.reaudit.gap_closed
    ? `Re-audit: gap closed, the screen reader now says "${finding.reaudit.sr_name_after}"`
    : `Re-audit: gap still open, the screen reader still says "${finding.reaudit.sr_name_after || "nothing"}"`;
}

export function FindingCard({ finding, selected, onSelect, onDecision }: Props) {
  const j = finding.judgement;
  const quote = srQuote(finding);
  const [typed, setTyped] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const reason = typed ?? suggestedReason(finding); // suggested from the re-audit, editable, required
  // Pending means a fix without a decision (same rule as the server): the re-audit is evidence, not a gate.
  const canDecide = Boolean(finding.fix && !finding.decision && onDecision);
  const ready = canDecide && reason.trim().length > 0 && !busy;
  const reasonId = `reason-${finding.id}`;
  const act = (decision: "approve" | "reject") => {
    if (!onDecision || busy) return;
    setBusy(true);
    Promise.resolve(onDecision(finding.id, decision, reason.trim())).finally(() => setBusy(false));
  };
  return (
    <article>
      <button type="button" className="card" aria-pressed={selected} onClick={() => onSelect(finding.id)}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-wider muted">Sighted user sees</div>
            <div className="font-semibold" style={{ fontSize: 16 }}>{finding.sighted_text}</div>
          </div>
          {j && (j.is_barrier === false
            ? <span className="sev sev-needs_review" title="The judge did not consider this a barrier. The evidence is still verified; a human decides.">not a barrier · review</span>
            : <span className={`sev sev-${j.severity}`}>{j.severity.replace("_", " ")}</span>)}
        </div>
        <div className="mt-2">
          <div className="text-xs uppercase tracking-wider muted">Screen reader gets</div>
          <div className="mono" style={{ fontSize: 15 }}>{quote ?? <span className="sr-silent">— not announced —</span>}</div>
        </div>
        <ul className="checks" aria-label="Verifier checks">
          {Object.entries(finding.verifier.checks).map(([name, c]) => (
            <li key={name} data-passed={c.passed} aria-label={`${CHECK_LABELS[name] ?? name}: ${c.passed ? "passed" : "failed"}`} title={c.detail}>
              <span aria-hidden="true">{c.passed ? "✓" : "✗"}</span> {CHECK_LABELS[name] ?? name}
            </li>
          ))}
          <li><CodeBadge what="code · verifier" /></li>
        </ul>
        {j && (
          <div className="mt-2 flex items-center gap-2 flex-wrap text-sm">
            {j.wcag.length > 0 ? (
              <span>{j.wcag.map((w) => `WCAG ${w.sc}${w.name ? ` ${w.name}` : ""}`).join(" · ")}</span>
            ) : (
              <span className="muted">{j.is_barrier === null ? "Judge could not decide: needs human review" : j.is_barrier === false ? "Judge: not a barrier in context. Review the evidence and decide." : "No WCAG criterion cited"}</span>
            )}
            <MetaBadge model={String(j.model_meta?.model ?? "muse-spark-1.3")} capability="judge" />
          </div>
        )}
        {finding.reaudit && (
          <div className="mt-2 text-sm">
            <span className="text-xs uppercase tracking-wider muted mr-2">Re-audit</span>
            <span className="mono">"{finding.reaudit.sr_name_before}" → "{finding.reaudit.sr_name_after}"</span>
            <span className="ml-2" style={{ color: finding.reaudit.gap_closed ? "var(--ok)" : "var(--bad)" }}>{finding.reaudit.gap_closed ? "gap closed" : "gap still open"}</span>
            <span className="ml-2"><CodeBadge what="code · re-audit" /></span>
          </div>
        )}
        {finding.decision && (
          <div className="mt-2 text-sm" style={{ color: finding.decision.decision === "approve" ? "var(--ok)" : "var(--bad)" }}>
            {finding.decision.decision === "approve" ? "Approved" : "Rejected"} · {finding.decision.reason}
          </div>
        )}
      </button>
      {finding.fix && (
        <section className="px-1 pt-2 text-sm" aria-label="Proposed fix">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs uppercase tracking-wider muted">Proposed fix</span>
            <MetaBadge model={String(finding.fix.model_meta?.model ?? "muse-spark-1.3")} capability="fixer" />
          </div>
          {finding.fix.explanation && <p className="m-0 mt-1">{finding.fix.explanation}</p>}
          <details className="mt-1">
            <summary className="cursor-pointer muted">Diff</summary>
            <pre className="diff mono">{finding.fix.diff}</pre>
          </details>
        </section>
      )}
      {!finding.fix && finding.fix_note && <p className="muted text-xs px-1 pt-2 m-0">No fix proposed: {finding.fix_note}</p>}
      {finding.fix && !finding.reaudit && finding.reaudit_note && <p className="muted text-xs px-1 pt-1 m-0">Re-audit did not run: {finding.reaudit_note}</p>}
      {selected && !finding.decision && (
        <div className="flex items-center gap-2 px-1 py-2 flex-wrap">
          <label className="sr-only" htmlFor={reasonId}>Reason</label>
          <input id={reasonId} className="btn-quiet fix-reason" value={reason} onChange={(e) => setTyped(e.target.value)} placeholder="Reason for the decision" disabled={!canDecide} />
          <button type="button" className="btn-quiet" disabled={!ready} onClick={() => act("approve")} title={canDecide ? "Approve the proposed fix" : "Approve becomes available once a fix has been proposed"}>
            Approve fix
          </button>
          <button type="button" className="btn-quiet" disabled={!ready} onClick={() => act("reject")} title={canDecide ? "Reject the proposed fix" : "Reject becomes available once a fix has been proposed"}>
            Reject
          </button>
          {!finding.fix && !finding.fix_note && <span className="muted text-xs">A fix and its re-audit follow once the judge is done.</span>}
        </div>
      )}
    </article>
  );
}
