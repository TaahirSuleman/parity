import { useEffect, useState } from "react";
import { isPublicRun, type Run, type RunMode } from "../state/types";

export interface FlowOption { id: string; name: string; single_page: boolean }

interface Props {
  flows: FlowOption[];
  flowId: string;
  onFlowChange: (id: string) => void;
  run: Run | null;
  approved?: number; // fixes approved by a human
  view?: "workbench" | "eval";
  onViewChange?: (view: "workbench" | "eval") => void;
  pending?: number; // fixes still waiting for a decision
  mode: RunMode;
  canLive: boolean;
  running: boolean;
  screens?: number; // screens captured so far: with none, there is no axe count to show
  onModeChange: (mode: RunMode) => void;
  onRun: () => void;
}

export function fmtCost(usd: number): string {
  return usd < 0.1 ? `$${usd.toFixed(4)}` : `$${usd.toFixed(2)}`;
}
export function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`;
  const total = Math.round(ms / 1000);
  const m = Math.floor(total / 60);
  return `${m} m ${total - m * 60} s`;
}

/** What the header calls the site on screen: our store, or an anonymised public sample ("Site A"). */
export function siteLabel(run: Run | null): string {
  if (isPublicRun(run)) return /^(Site [A-Z])\b/.exec(run!.goal)?.[1] ?? "Public site";
  return "ShopRight";
}

/** Wall time since the run started, ticking once a second while it runs; 0 when it is not running. */
function useElapsed(startedAt: string | undefined, running: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running, startedAt]);
  return running && startedAt ? Math.max(0, now - new Date(startedAt).getTime()) : 0;
}

export function Header({ flows, flowId, onFlowChange, run, mode, canLive, running, screens, onModeChange, onRun, approved = 0, pending = 0, view = "workbench", onViewChange }: Props) {
  const axe = run?.axe_violations ?? 0;
  const elapsed = useElapsed(run?.started_at, running && !!run);
  const isPublic = isPublicRun(run);
  const audited = screens === undefined || screens > 0;
  const replay = run?.mode === "replay";
  const time = !run ? "—" : running ? (replay ? "replaying…" : fmtDuration(elapsed)) : run.duration_ms > 0 ? (replay ? `recorded ${fmtDuration(run.duration_ms)}` : fmtDuration(run.duration_ms)) : "—";
  return (
    <header className="surface" style={{ borderRadius: 0, borderWidth: "0 0 1px 0" }}>
      <div className="flex items-center gap-4 px-4 py-2.5 flex-wrap">
        <div className="flex items-baseline gap-2 flex-wrap">
          <h1 className="font-semibold tracking-tight m-0" style={{ fontSize: 15 }}>Parity</h1>
          <span className="muted">·</span>
          {isPublic ? (
            <span title="A public site audited read-only from the command line and anonymised; the hosted app never audits third-party sites">{siteLabel(run)} · read-only sample</span>
          ) : (
            <>
              <span>ShopRight ·</span>
              <label className="sr-only" htmlFor="flow-select">Flow</label>
              <select id="flow-select" className="btn-quiet" style={{ padding: "3px 8px" }} value={flowId} onChange={(e) => onFlowChange(e.target.value)} disabled={running}>
                {flows.map((f) => <option key={f.id} value={f.id}>{f.name}{f.single_page ? "" : " (agent)"}</option>)}
              </select>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="pill" role="group" aria-label="Run mode">
            <button type="button" aria-pressed={mode === "replay"} onClick={() => onModeChange("replay")} title="Replay: a recorded run plays back; no model calls, no limit">Replay</button>
            <button type="button" aria-pressed={mode === "live"} onClick={() => onModeChange("live")} disabled={!canLive} title={canLive ? "Live: real model calls against the demo store; a few runs per visitor per hour" : "Live needs a model key on the server; Replay works without one"}>
              Live (rate-limited)
            </button>
          </div>
          <span className="muted text-xs">{mode === "replay" ? "a recorded run, no model calls" : "real model calls; a few runs per visitor per hour"}</span>
        </div>
        <button type="button" className="btn-primary" onClick={() => { if (!running) onRun(); }} aria-disabled={running} data-running={running}>
          {running ? "Auditing…" : "Run the audit"}
        </button>
        {onViewChange && (
          <button type="button" className="btn-quiet" aria-pressed={view === "eval"} onClick={() => onViewChange(view === "eval" ? "workbench" : "eval")} title="Recall and precision against the seeded labels, the ablations, the judge comparison and the real-world sample">
            Eval
          </button>
        )}
        <div className="ml-auto flex items-center gap-5 flex-wrap">
          {(!run || audited) && (
            <span className="counter" title="axe-core 4.14 violations on the audited screens">
              <span className="muted">axe-core</span> <strong>{run ? axe : "—"}</strong> <span className="muted">{axe === 1 ? "violation" : "violations"}</span>
            </span>
          )}
          <span className="counter" title="Findings that passed the Verifier · candidates it rejected">
            <span className="muted">Parity</span> <strong style={{ color: "var(--ok)" }}>{run ? run.findings_verified : "—"}</strong> <span className="muted">verified</span>{" · "}
            <strong style={{ color: "var(--bad)" }}>{run ? run.findings_rejected : "—"}</strong> <span className="muted">rejected by the Verifier</span>
          </span>
          <span className="counter mono muted" title="Model cost and wall time for this run">
            {run ? `${fmtCost(run.cost_usd)} · ${time}` : "— · —"}
          </span>
          {run?.mode === "replay" && <span className="badge" title={`Replay of recorded run ${run.replay_of ?? ""}`}>replay</span>}
          {run?.status === "awaiting_review" && <span className="badge warn" title="Proposed fixes wait for a human decision">awaiting review</span>}
          {run?.status === "failed" && <span className="badge" style={{ borderColor: "var(--bad)", color: "var(--bad)" }} title={run.error ?? "the run failed"}>failed</span>}
          {approved + pending > 0 && <span className="counter" title="Fixes approved · fixes waiting for a decision">{`${approved} approved · ${pending} to review`}</span>}
          {run && approved > 0 && <a className="btn-quiet" style={{ padding: "3px 8px", textDecoration: "none" }} href={`/api/runs/${run.id}/patch`} download={`parity-${run.id}.patch`} title="The approved fixes as one git patch">Download fix.patch</a>}
        </div>
      </div>
      {running && <div className="progress" aria-hidden="true" />}
    </header>
  );
}
