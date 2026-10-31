import { CHECK_LABELS, type Rejected } from "../state/types";
import { CodeBadge } from "./MetaBadge";

const KIND_LABEL: Record<string, string> = { false: "false", duplicate: "duplicate", already_in_axe: "already in axe-core" };

export function RejectedRow({ rejected, asReported = false, kind = "false" }: { rejected: Rejected; asReported?: boolean; kind?: string }) {
  const failed = Object.entries(rejected.verifier.checks).filter(([, c]) => !c.passed).map(([n]) => CHECK_LABELS[n] ?? n);
  const label = asReported
    ? (kind === "false" ? `Would be reported: ${rejected.candidate.sighted_text}` : `Would be reported as a ${KIND_LABEL[kind] ?? kind}: ${rejected.candidate.sighted_text}`)
    : `Rejected candidate: ${rejected.candidate.sighted_text}`;
  return (
    <div className="row-rejected" role="listitem" aria-label={label} data-as-reported={asReported}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs uppercase tracking-wider" style={{ color: "var(--bad)" }}>{asReported ? `Would be reported without the verifier · ${KIND_LABEL[kind] ?? kind}` : "Rejected by the verifier"}</span>
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
