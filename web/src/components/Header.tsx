import type { Run, RunMode } from "../state/types";

export interface FlowOption { id: string; name: string; single_page: boolean }

interface Props {
  flows: FlowOption[];
  flowId: string;
  onFlowChange: (id: string) => void;
  run: Run | null;
  approved?: number; // fixes approved by a human
  pending?: number; // fixes still waiting for a decision
  mode: RunMode;
  canLive: boolean;
  running: boolean;
  onModeChange: (mode: RunMode) => void;
  onRun: () => void;
}

export function fmtCost(usd: number): string {
  return usd < 0.1 ? `$${usd.toFixed(4)}` : `$${usd.toFixed(2)}`;
}
export function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`;
  const m = Math.floor(ms / 60000);
  return `${m} m ${Math.round((ms - m * 60000) / 1000)} s`;
}

export function Header({ flows, flowId, onFlowChange, run, mode, canLive, running, onModeChange, onRun, approved = 0, pending = 0 }: Props) {
  const axe = run?.axe_violations ?? 0;
  return (
    <header className="surface" style={{ borderRadius: 0, borderWidth: "0 0 1px 0" }}>
      <div className="flex items-center gap-4 px-4 py-2.5 flex-wrap">
        <div className="flex items-baseline gap-2">
          <h1 className="font-semibold tracking-tight m-0" style={{ fontSize: 15 }}>Parity</h1>
          <span className="muted">·</span>
          <span>ShopRight ·</span>
          <label className="sr-only" htmlFor="flow-select">Flow</label>
          <select id="flow-select" className="btn-quiet" style={{ padding: "3px 8px" }} value={flowId} onChange={(e) => onFlowChange(e.target.value)} disabled={running}>
            {flows.map((f) => <option key={f.id} value={f.id}>{f.name}{f.single_page ? "" : " (agent)"}</option>)}
          </select>
        </div>
        <div className="pill" role="group" aria-label="Run mode">
          <button type="button" aria-pressed={mode === "replay"} onClick={() => onModeChange("replay")}>Replay</button>
          <button type="button" aria-pressed={mode === "live"} onClick={() => onModeChange("live")} disabled={!canLive} title={canLive ? "Live: real model calls" : "Live needs MODEL_API_KEY on the server"}>
            Live
          </button>
        </div>
        <button type="button" className="btn-primary" onClick={onRun} disabled={running}>
          {running ? "Auditing…" : "Run the audit"}
        </button>
        <div className="ml-auto flex items-center gap-5 flex-wrap">
          <span className="counter" title="axe-core 4.14 violations on the audited screens">
            <span className="muted">axe-core</span> <strong>{axe}</strong> <span className="muted">{axe === 1 ? "violation" : "violations"}</span>
          </span>
          <span className="counter" title="Findings that passed the Verifier · candidates it rejected">
            <span className="muted">Parity</span> <strong style={{ color: "var(--ok)" }}>{run?.findings_verified ?? 0}</strong> <span className="muted">verified</span>{" · "}
            <strong style={{ color: "var(--bad)" }}>{run?.findings_rejected ?? 0}</strong> <span className="muted">rejected</span>
          </span>
          <span className="counter mono muted" title="Model cost and wall time for this run">
            {fmtCost(run?.cost_usd ?? 0)} · {run?.mode === "replay" && run.duration_ms > 0 ? `recorded ${fmtDuration(run.duration_ms)}` : fmtDuration(run?.duration_ms ?? 0)}
          </span>
          {run?.mode === "replay" && <span className="badge" title={`Replay of recorded run ${run.replay_of ?? ""}`}>replay</span>}
          {run?.status === "awaiting_review" && <span className="badge warn" title="Proposed fixes wait for a human decision">awaiting review</span>}
          {approved + pending > 0 && <span className="counter" title="Fixes approved · fixes waiting for a decision">{`${approved} approved · ${pending} to review`}</span>}
          {run && approved > 0 && <a className="btn-quiet" style={{ padding: "3px 8px", textDecoration: "none" }} href={`/api/runs/${run.id}/patch`} download={`parity-${run.id}.patch`} title="The approved fixes as one git patch">Download fix.patch</a>}
        </div>
      </div>
      {running && <div className="progress" aria-hidden="true" />}
    </header>
  );
}
