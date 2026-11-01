import { useRef, useState } from "react";
import { CHECK_LABELS, type Finding } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";
import { srQuote } from "./ScreenReaderPanel";

interface Props {
  finding: Finding;
  selected: boolean;
  onSelect: (id: string) => void;
  onDecision?: (id: string, decision: "approve" | "reject", reason: string) => void | Promise<void>;
  screenLabel?: string; // "screen 3 · checkout" when the run has several screens
  fixesExpected?: boolean; // false once no fix will follow (run over, or a read-only public sample)
  comparatorModel?: string; // the model that re-ran the comparison on the patched page
}

function suggestedReason(finding: Finding): string {
  if (!finding.reaudit) return "";
  const after = finding.reaudit.sr_name_after || "nothing";
  return finding.reaudit.gap_closed
    ? `Re-audit: gap closed, the screen reader now says "${after}"`
    : `Re-audit: name rule still open, the screen reader now says "${after}"`;
}

export function FindingCard({ finding, selected, onSelect, onDecision, screenLabel, fixesExpected = true, comparatorModel = "muse-spark-1.3-contributor" }: Props) {
  const j = finding.judgement;
  const quote = srQuote(finding);
  const [typed, setTyped] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const reason = typed ?? suggestedReason(finding); // suggested from the re-audit, editable, required
  // Pending means a fix without a decision (same rule as the server): the re-audit is evidence, not a gate.
  const canApprove = Boolean(finding.fix && !finding.decision && onDecision);
  const canReject = Boolean(!finding.decision && onDecision); // a verified finding with no fix can still be dismissed by a human
  const canDecide = canApprove || canReject;
  const hasReason = reason.trim().length > 0 && !busy;
  const reasonId = `reason-${finding.id}`;
  const headingId = `finding-${finding.id}`;
  const selectRef = useRef<HTMLButtonElement>(null);
  const act = (decision: "approve" | "reject") => {
    if (!onDecision || busy) return;
    setBusy(true);
    Promise.resolve(onDecision(finding.id, decision, reason.trim())).finally(() => {
      setBusy(false);
      selectRef.current?.focus(); // the decision controls go away; keep focus on this finding
    });
  };
  return (
    <article id={`card-${finding.id}`} className="card" data-selected={selected} aria-labelledby={headingId} onClick={() => onSelect(finding.id)}>
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-wider muted">Sighted user sees{screenLabel ? ` · ${screenLabel}` : ""}</div>
            <h3 id={headingId} className="font-semibold m-0" style={{ fontSize: 16 }}>
              <button ref={selectRef} type="button" className="card-select" aria-pressed={selected} onClick={(e) => { e.stopPropagation(); onSelect(finding.id); }}>{finding.sighted_text}</button>
            </h3>
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
        <details className="check-details text-xs muted mt-1" onClick={(e) => e.stopPropagation()}>
          <summary className="cursor-pointer">Check details</summary>
          <ul className="m-0 mt-1 pl-4">
            {Object.entries(finding.verifier.checks).map(([name, c]) => (
              <li key={name}><span className="mono">{CHECK_LABELS[name] ?? name}</span> — {c.detail}</li>
            ))}
          </ul>
        </details>
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
            {finding.reaudit.gap_closed
              ? <span className="ml-2" style={{ color: "var(--ok)" }}>gap closed</span>
              : finding.reaudit.comparator_still_flags === false
                ? <span className="ml-2" style={{ color: "var(--warn)" }} title="The strict rule wants the visible text inside the new name; for an icon the visible text names a picture, so the comparator's verdict is the one to weigh.">
                    name rule: still open — the visible text "{finding.sighted_text}" cannot match the new name; the comparator no longer flags it
                  </span>
                : <span className="ml-2" style={{ color: "var(--bad)" }}>name rule: still open</span>}
            <span className="ml-2"><CodeBadge what="code · re-audit" /></span>
            {finding.reaudit.comparator_still_flags !== null && (
              <span className="ml-2 inline-flex items-center gap-2">
                <span style={{ color: finding.reaudit.comparator_still_flags ? "var(--bad)" : "var(--ok)" }}>
                  {finding.reaudit.comparator_still_flags ? "comparator: still flags it" : "comparator: no longer flags it"}
                </span>
                <MetaBadge model={comparatorModel} capability="comparison" />
              </span>
            )}
          </div>
        )}
        {finding.decision && (
          <div className="mt-2 text-sm" role="status" style={{ color: finding.decision.decision === "approve" ? "var(--ok)" : "var(--bad)" }}>
            {finding.decision.decision === "approve" ? "Approved" : "Rejected"} · {finding.decision.reason}
          </div>
        )}
      </div>
      {finding.fix && (
        <div className="px-1 pt-2 text-sm">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs uppercase tracking-wider muted">Proposed fix</span>
            <MetaBadge model={String(finding.fix.model_meta?.model ?? "muse-spark-1.3")} capability="fixer" />
          </div>
          {finding.fix.explanation && <p className="m-0 mt-1">{finding.fix.explanation}</p>}
          <details className="mt-1">
            <summary className="cursor-pointer muted">Diff</summary>
            <pre className="diff mono" tabIndex={0} role="region" aria-label={`Unified diff for ${finding.sighted_text}`}>
              {finding.fix.diff.split("\n").map((line, i) => (
                <span key={i} className={line.startsWith("+") && !line.startsWith("+++") ? "diff-add" : line.startsWith("-") && !line.startsWith("---") ? "diff-del" : undefined}>{line}{"\n"}</span>
              ))}
            </pre>
          </details>
        </div>
      )}
      {!finding.fix && finding.fix_note && <p className="muted text-xs px-1 pt-2 m-0">No fix proposed: {finding.fix_note}</p>}
      {finding.fix && !finding.reaudit && finding.reaudit_note && <p className="muted text-xs px-1 pt-1 m-0">Re-audit did not run: {finding.reaudit_note}</p>}
      {selected && !finding.decision && (
        <div className="flex items-center gap-2 px-1 py-2 flex-wrap">
          <label className="sr-only" htmlFor={reasonId}>Reason</label>
          <input id={reasonId} className="btn-quiet fix-reason" value={reason} onChange={(e) => setTyped(e.target.value)} onFocus={(e) => e.currentTarget.select()}
            placeholder="Reason for the decision" disabled={!canDecide} />  {/* the suggestion is selected on focus: typing replaces it, a click mid-sentence does not splice into it */}
          <button type="button" className="btn-quiet" disabled={!(canApprove && hasReason)} onClick={() => act("approve")} title={canApprove ? "Approve the proposed fix" : "Approve needs a proposed fix"}>
            Approve fix
          </button>
          <button type="button" className="btn-quiet" disabled={!(canReject && hasReason)} onClick={() => act("reject")} title={finding.fix ? "Reject the proposed fix" : "Dismiss this finding (no fix was proposed)"}>
            Reject
          </button>
          {!finding.fix && !finding.fix_note && (fixesExpected
            ? <span className="muted text-xs">A fix and its re-audit follow once the judge is done.</span>
            : <span className="muted text-xs">No fix was proposed for this finding.</span>)}
        </div>
      )}
    </article>
  );
}
