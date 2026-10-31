import { CHECK_LABELS, type Finding } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";
import { srQuote } from "./ScreenReaderPanel";

interface Props {
  finding: Finding;
  selected: boolean;
  onSelect: (id: string) => void;
  onDecision?: (id: string, decision: "approve" | "reject", reason: string) => void;
}

export function FindingCard({ finding, selected, onSelect, onDecision }: Props) {
  const j = finding.judgement;
  const quote = srQuote(finding);
  const canDecide = Boolean(finding.fix && finding.reaudit && !finding.decision && onDecision);
  return (
    <article>
      <button type="button" className="card" aria-pressed={selected} onClick={() => onSelect(finding.id)}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-wider muted">Sighted user sees</div>
            <div className="font-semibold" style={{ fontSize: 16 }}>{finding.sighted_text}</div>
          </div>
          {j && <span className={`sev sev-${j.severity}`}>{j.severity.replace("_", " ")}</span>}
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
              <span className="muted">{j.is_barrier === null ? "Judge could not decide: needs human review" : "No WCAG criterion cited"}</span>
            )}
            <MetaBadge model={String(j.model_meta?.model ?? "muse-spark-1.3")} capability="judge" />
          </div>
        )}
        {finding.reaudit && (
          <div className="mt-2 text-sm">
            <span className="text-xs uppercase tracking-wider muted mr-2">Re-audit</span>
            <span className="mono">"{finding.reaudit.sr_name_before}" → "{finding.reaudit.sr_name_after}"</span>
            <span className="ml-2" style={{ color: finding.reaudit.gap_closed ? "var(--ok)" : "var(--bad)" }}>{finding.reaudit.gap_closed ? "gap closed" : "gap still open"}</span>
          </div>
        )}
        {finding.decision && (
          <div className="mt-2 text-sm" style={{ color: finding.decision.decision === "approve" ? "var(--ok)" : "var(--bad)" }}>
            {finding.decision.decision === "approve" ? "Approved" : "Rejected"} · {finding.decision.reason}
          </div>
        )}
      </button>
      {selected && (
        <div className="flex items-center gap-2 px-1 py-2">
          <button type="button" className="btn-quiet" disabled={!canDecide} onClick={() => onDecision?.(finding.id, "approve", "Fix verified by re-audit")} title={canDecide ? "Approve the proposed fix" : "Approve becomes available once a fix has been proposed and re-audited"}>
            Approve fix
          </button>
          <button type="button" className="btn-quiet" disabled={!canDecide} onClick={() => onDecision?.(finding.id, "reject", "Not a barrier in context")} title={canDecide ? "Reject the proposed fix" : "Reject becomes available once a fix has been proposed and re-audited"}>
            Reject
          </button>
          {!finding.fix && <span className="muted text-xs">A fix proposal and re-audit follow in the next phase.</span>}
        </div>
      )}
    </article>
  );
}
