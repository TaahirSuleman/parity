import { useState } from "react";
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
  const [verifierOff, setVerifierOff] = useState(false);
  const items: ({ kind: "f"; v: Finding } | { kind: "r"; v: Rejected })[] = [
    ...findings.map((v) => ({ kind: "f" as const, v })),
    ...rejected.map((v) => ({ kind: "r" as const, v })),
  ].sort((a, b) => a.v.id.localeCompare(b.v.id));
  const reported = findings.length + rejected.length;
  const kindOf = (r: Rejected) => {
    const failed = Object.entries(r.verifier.checks).filter(([, c]) => !c.passed).map(([n]) => n);
    if (failed.some((n) => n === "located" || n === "sr_quote_exact" || n === "diverges")) return "false";
    if (failed.includes("unique")) return "duplicate";
    if (failed.includes("not_axe")) return "already_in_axe";
    return "false";
  };
  const falseCount = rejected.filter((r) => kindOf(r) === "false").length;
  const dupCount = rejected.filter((r) => kindOf(r) === "duplicate").length;
  const axeCount = rejected.filter((r) => kindOf(r) === "already_in_axe").length;
  return (
    <section className="surface flex flex-col min-h-0" aria-labelledby="findings-h">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b hairline flex-wrap">
        <h2 id="findings-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Findings</h2>
        <span className="mono text-xs muted">{findings.length} verified · {rejected.length} rejected</span>
        <button
          type="button" role="switch" aria-checked={verifierOff} className="btn-quiet text-xs" style={{ padding: "2px 8px" }}
          onClick={() => setVerifierOff((v) => !v)} title="Show what this run would report if the Verifier did not gate findings"
        >
          Without the Verifier
        </button>
      </div>
      {verifierOff && (
        <p className="m-0 px-3 py-2 text-sm" style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--line)" }} role="status">
          With the gate off this run would report {reported} finding{reported === 1 ? "" : "s"}: {falseCount} false report{falseCount === 1 ? "" : "s"} (the evidence did not hold), {dupCount} duplicate{dupCount === 1 ? "" : "s"}{axeCount ? `, ${axeCount} already reported by axe-core` : ""}.
        </p>
      )}
      {items.length === 0 && (
        <p className="muted m-0 p-5" role="status">
          {phase === "idle" && "No findings yet. Run the audit to walk the checkout."}
          {phase === "running" && "Capturing the page and comparing what is seen with what is announced…"}
          {phase === "finished" && "No divergences passed the verifier on this run."}
          {phase === "failed" && (error ?? "The run failed.")}
        </p>
      )}
      <div className="flex flex-col gap-2 p-3 overflow-y-auto" role="list" aria-live="polite" aria-relevant="additions" hidden={items.length === 0}>
        {items.map((it) =>
          it.kind === "f" ? (
            <div key={it.v.id} role="listitem">
              <FindingCard finding={it.v} selected={it.v.id === selectedId} onSelect={onSelect} onDecision={onDecision} />
            </div>
          ) : (
            <RejectedRow key={it.v.id} rejected={it.v} asReported={verifierOff} kind={kindOf(it.v)} />
          ),
        )}
        {phase === "failed" && items.length > 0 && <p className="m-0 p-2" style={{ color: "var(--bad)" }}>{error}</p>}
      </div>
    </section>
  );
}
