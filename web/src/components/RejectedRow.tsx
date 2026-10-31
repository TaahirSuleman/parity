import { CHECK_LABELS, type Rejected } from "../state/types";
import { CodeBadge } from "./MetaBadge";

export function RejectedRow({ rejected }: { rejected: Rejected }) {
  const failed = Object.entries(rejected.verifier.checks).filter(([, c]) => !c.passed).map(([n]) => CHECK_LABELS[n] ?? n);
  return (
    <div className="row-rejected" role="listitem" aria-label={`Rejected candidate: ${rejected.candidate.sighted_text}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs uppercase tracking-wider" style={{ color: "var(--bad)" }}>Rejected by the verifier</span>
        <CodeBadge what="code · verifier" />
      </div>
      <div className="mt-1">
        <span className="font-medium">{rejected.candidate.sighted_text}</span>
        <span className="muted"> · claimed </span>
        <span className="mono">{rejected.candidate.sr_quote}</span>
      </div>
      <div className="mono text-xs mt-1" style={{ color: "var(--bad)" }}>failed: {failed.join(", ") || "—"}</div>
      {rejected.verifier.feedback && <div className="text-xs muted mt-1">{rejected.verifier.feedback}</div>}
    </div>
  );
}
