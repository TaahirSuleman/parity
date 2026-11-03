import { useEffect, useState } from "react";
import { isPublicRun, type Run, type RunMode } from "../state/types";

export interface FlowOption { id: string; name: string; single_page: boolean; public?: boolean; attribution?: string; start_url?: string }

/** The host of a page the visitor chose, from the run record; null for any other run. */
export function visitorHost(run: Run | null): string | null {
  if (run?.source !== "visitor-url" || !run.origin) return null;
  try { return new URL(run.origin).hostname; } catch { return null; }
}

/** The site of any run on a page we do not serve (a visitor's page, a W3C flow, in Live or Replay), from the run record itself. */
export function publicHost(run: Run | null): string | null {
  if (!run?.public || !run.origin) return null;
  try { return new URL(run.origin).hostname; } catch { return null; }
}

/** The host an external flow audits ("www.w3.org"), or null for a store flow. */
export function externalHost(flow: FlowOption | undefined): string | null {
  if (!flow?.public || !flow.start_url) return null;
  try { return new URL(flow.start_url).hostname; } catch { return null; }
}

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
  urlMode?: boolean; // "Live on a page you choose" is selected: the panel below holds the address and the button
  openUrl?: boolean; // the server offers the field (open, a key present, not closed for today)
  onUrlModeChange?: (on: boolean) => void;
  closedToday?: boolean; // the day's budget for pages visitors choose is spent: the pill stays, disabled and explained
}

export function fmtCost(usd: number): string {
  return usd < 0.01 ? `$${usd.toFixed(4)}` : `$${usd.toFixed(2)}`;  // cents everywhere a judge compares costs; under a cent the digits are the information
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

export function Header({ flows, flowId, onFlowChange, run, mode, canLive, running, screens, onModeChange, onRun, approved = 0, pending = 0, view = "workbench", onViewChange, urlMode = false, openUrl = false, onUrlModeChange, closedToday = false }: Props) {
  const axe = run?.axe_violations ?? 0;
  const elapsed = useElapsed(run?.started_at, running && !!run);
  const isPublic = isPublicRun(run);
  const audited = screens === undefined || screens > 0;
  const replay = run?.mode === "replay";
  const current = flows.find((f) => f.id === flowId);
  const visitor = visitorHost(run);  // a page the visitor chose: named from the run, never from the picker
  const host = visitor ?? publicHost(run) ?? (urlMode ? null : externalHost(current));  // a page we do not serve: the header names its site, never the store; the run on screen outranks the picker
  const attribution = run?.public ? run.attribution || null : !urlMode && externalHost(current) ? current?.attribution || null : null;
  const chooseMode = (next: RunMode) => { onUrlModeChange?.(false); onModeChange(next); };
  const external = flows.filter((f) => f.public);
  const store = flows.filter((f) => !f.public);
  const option = (f: FlowOption) => <option key={f.id} value={f.id}>{f.name}{f.single_page ? "" : " (agent)"}</option>;
  const time = !run ? "—" : running ? (replay ? "replaying…" : fmtDuration(elapsed)) : run.duration_ms > 0 ? (replay ? `recorded ${fmtDuration(run.duration_ms)}` : fmtDuration(run.duration_ms)) : "—";
  return (
    <header className="surface" style={{ borderRadius: 0, borderWidth: "0 0 1px 0" }}>
      <div className="flex items-center gap-4 px-4 py-2.5 flex-wrap">
        <div className="flex items-baseline gap-2 flex-wrap">
          <h1 className="font-semibold tracking-tight m-0" style={{ fontSize: 15 }}>Parity</h1>
          <span className="muted">·</span>
          {isPublic ? (
            <span title="A public site audited read-only from the command line and anonymised">{siteLabel(run)} · read-only sample</span>
          ) : urlMode || visitor ? (
            <span>{host ?? "a page you choose"}</span>
          ) : (
            <>
              <span>{host ?? "ShopRight"} ·</span>
              <label className="sr-only" htmlFor="flow-select">Flow</label>
              <select id="flow-select" className="btn-quiet" style={{ padding: "3px 8px" }} value={flowId} onChange={(e) => onFlowChange(e.target.value)} disabled={running}>
                {external.length === 0 ? flows.map(option) : (
                  <>
                    <optgroup label="ShopRight demo store">{store.map(option)}</optgroup>
                    <optgroup label="External page (W3C demo, read-only)">{external.map(option)}</optgroup>
                  </>
                )}
              </select>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="pill" role="group" aria-label="Run mode">
            <button type="button" aria-pressed={mode === "replay" && !urlMode} onClick={() => chooseMode("replay")} title="Replay: a recorded run plays back; no model calls, no limit">Replay</button>
            <button type="button" aria-pressed={mode === "live" && !urlMode} onClick={() => chooseMode("live")} disabled={!canLive} title={canLive ? "Live: real model calls on the selected page; a few runs per visitor per hour" : "Live needs a model key on the server; Replay works without one"}>
              Live (rate-limited)
            </button>
            {openUrl && (
              <button type="button" aria-pressed={urlMode} onClick={() => onUrlModeChange?.(true)} disabled={!canLive || running || closedToday}
                title={closedToday ? "Closed for today: the day's budget for pages visitors choose is spent; the store flows and Replay still work" : "Live on a page you choose: a public address, audited read-only as a visitor would see it; one screen by default; no fixes; kept for 24 hours"}>
                Live on a page you choose
              </button>
            )}
          </div>
          <span className="muted text-xs">{urlMode ? "real model calls on the page you choose, read-only; a few runs per visitor per hour" : mode === "replay" ? "a recorded run, no model calls" : flows.find((f) => f.id === flowId)?.single_page === false ? "real model calls; the agent walk takes about 10 minutes; a few runs per visitor per hour" : "real model calls; a few runs per visitor per hour"}</span>
        </div>
        {!urlMode && (
          <button type="button" className="btn-primary" onClick={() => { if (!running) onRun(); }} aria-disabled={running} data-running={running}>
            {running ? "Auditing…" : "Run the audit"}
          </button>
        )}
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
      {attribution && !isPublic && (
        <p className="muted text-xs m-0 px-4 pb-2" data-testid="attribution">{attribution}</p>
      )}
      {running && <div className="progress" aria-hidden="true" />}
    </header>
  );
}
