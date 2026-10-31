import type { Finding, Rejected, RunState } from "../state/types";
import { FindingCard } from "./FindingCard";
import { RejectedRow } from "./RejectedRow";

interface Props {
  findings: Finding[];
  rejected: Rejected[];
  selectedId: string | null;
  phase: RunState["phase"];
  error: string | null;
  onSelect: (id: string) => void;
  onDecision?: (id: string, decision: "approve" | "reject", reason: string) => void;
}

export function FindingsFeed({ findings, rejected, selectedId, phase, error, onSelect, onDecision }: Props) {
  const items: ({ kind: "f"; v: Finding } | { kind: "r"; v: Rejected })[] = [
    ...findings.map((v) => ({ kind: "f" as const, v })),
    ...rejected.map((v) => ({ kind: "r" as const, v })),
  ].sort((a, b) => a.v.id.localeCompare(b.v.id));
  return (
    <section className="surface flex flex-col min-h-0" aria-labelledby="findings-h">
      <div className="flex items-center justify-between px-3 py-2 border-b hairline">
        <h2 id="findings-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Findings</h2>
        <span className="mono text-xs muted">{findings.length} verified · {rejected.length} rejected</span>
      </div>
      <div className="flex flex-col gap-2 p-3 overflow-y-auto" role="list" aria-live="polite" aria-relevant="additions">
        {items.length === 0 && (
          <p className="muted m-0 p-2">
            {phase === "idle" && "No findings yet. Run the audit to walk the checkout."}
            {phase === "running" && "Capturing the page and comparing what is seen with what is announced…"}
            {phase === "finished" && "No divergences passed the verifier on this run."}
            {phase === "failed" && (error ?? "The run failed.")}
          </p>
        )}
        {items.map((it) =>
          it.kind === "f" ? (
            <div key={it.v.id} role="listitem">
              <FindingCard finding={it.v} selected={it.v.id === selectedId} onSelect={onSelect} onDecision={onDecision} />
            </div>
          ) : (
            <RejectedRow key={it.v.id} rejected={it.v} />
          ),
        )}
        {phase === "failed" && items.length > 0 && <p className="m-0 p-2" style={{ color: "var(--bad)" }}>{error}</p>}
      </div>
    </section>
  );
}
