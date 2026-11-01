import type { Finding, ParityEvent, Run, RunMode } from "./state/types";

export interface Health { ok: boolean; mode_default: RunMode; live_enabled: boolean; storage: string; runs_indexed: number; has_key: boolean; replay_runs: string[]; replay_flows: Record<string, string>; version: string }
export interface FlowInfo { id: string; name: string; start_url: string; goal: string; pages: string[]; single_page: boolean }

export interface ErrorBody { error?: string; retry_after_s?: number; suggestion?: string; detail?: string }

export class ApiError extends Error {
  constructor(public status: number, public detail: string, public body: ErrorBody = {}) {
    super(detail);
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    let body: ErrorBody = {};
    try {
      body = (await res.json()) as ErrorBody;
      detail = body.detail ?? body.error ?? detail;
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, String(detail), body);
  }
  return (await res.json()) as T;
}

export const getHealth = () => fetch("/api/health").then((r) => json<Health>(r));
export const getFlows = () => fetch("/api/flows").then((r) => json<FlowInfo[]>(r));
export const startRun = (flowId: string | null, mode: RunMode, replayOf?: string) =>
  fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(replayOf ? { mode: "replay", replay_of: replayOf } : { flow_id: flowId, mode }) }).then((r) =>
    json<{ run_id: string; mode: RunMode; replay_of?: string }>(r),
  );
export interface RunDetail { run: Run; findings: Finding[]; steps: unknown[]; rejected: unknown[]; trace: unknown[] }
export const getRun = (runId: string) => fetch(`/api/runs/${runId}`).then((r) => json<RunDetail>(r));
export const getEval = () => fetch("/api/eval").then((r) => (r.status === 404 ? null : json<import("./components/EvalTab").EvalResults>(r)));
export const decide = (runId: string, findingId: string, decision: "approve" | "reject", reason: string) =>
  fetch(`/api/runs/${runId}/findings/${findingId}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, reason }) }).then((r) => json<{ finding: Finding; run: Run }>(r));
export const screenshotUrl = (runId: string, index: number) => `/api/runs/${runId}/steps/${index}/screenshot.png`;

export const EVENT_TYPES = [
  "run.started", "nav.actions", "nav.blocked", "nav.safety_check", "agent.tool_call", "agent.refused", "agent.tool_error", "step.captured", "seer.done", "comparator.candidates", "comparator.unparseable",
  "verifier.result", "judge.result", "fixer.proposed", "fixer.rejected", "reaudit.result", "reaudit.failed", "model.call", "decision.recorded", "voice.transcribed", "run.finished", "run.failed",
];

/** Subscribe to a run's SSE stream. Returns a function that closes it. */
export function streamRun(runId: string, onEvent: (ev: ParityEvent) => void, onError: (message: string) => void): () => void {
  const source = new EventSource(`/api/runs/${runId}/events`);
  let seen = 0;
  for (const type of EVENT_TYPES) {
    source.addEventListener(type, (msg) => {
      seen += 1;
      const ev = JSON.parse((msg as MessageEvent).data) as ParityEvent;
      onEvent(ev);
      if (ev.type === "run.finished" || ev.type === "run.failed") source.close();
    });
  }
  source.onerror = () => {
    // EventSource reconnects on its own. A drop before the first event is the run still starting; only a
    // drop after events have flowed is worth telling the user about, and even then the run continues.
    if (source.readyState === EventSource.CLOSED || seen === 0) return;
    onError("The event stream was interrupted; reconnecting. The run continues on the server.");
  };
  return () => source.close();
}
