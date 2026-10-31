import type { ParityEvent, RunMode } from "./state/types";

export interface Health { ok: boolean; mode_default: RunMode; live_enabled: boolean; storage: string; runs_indexed: number; has_key: boolean; replay_runs: string[]; version: string }
export interface FlowInfo { id: string; name: string; start_url: string; goal: string; pages: string[]; single_page: boolean }

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, String(detail));
  }
  return (await res.json()) as T;
}

export const getHealth = () => fetch("/api/health").then((r) => json<Health>(r));
export const getFlows = () => fetch("/api/flows").then((r) => json<FlowInfo[]>(r));
export const startRun = (flowId: string, mode: RunMode) =>
  fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ flow_id: flowId, mode }) }).then((r) =>
    json<{ run_id: string; mode: RunMode; replay_of?: string }>(r),
  );
export const decide = (runId: string, findingId: string, decision: "approve" | "reject", reason: string) =>
  fetch(`/api/runs/${runId}/findings/${findingId}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, reason }) }).then((r) => json<unknown>(r));
export const screenshotUrl = (runId: string, index: number) => `/api/runs/${runId}/steps/${index}/screenshot.png`;

export const EVENT_TYPES = [
  "run.started", "nav.actions", "nav.blocked", "agent.tool_call", "agent.refused", "step.captured", "seer.done", "comparator.candidates",
  "verifier.result", "judge.result", "fixer.proposed", "reaudit.result", "model.call", "decision.recorded", "voice.transcribed", "run.finished", "run.failed",
];

/** Subscribe to a run's SSE stream. Returns a function that closes it. */
export function streamRun(runId: string, onEvent: (ev: ParityEvent) => void, onError: (message: string) => void): () => void {
  const source = new EventSource(`/api/runs/${runId}/events`);
  for (const type of EVENT_TYPES) {
    source.addEventListener(type, (msg) => {
      const ev = JSON.parse((msg as MessageEvent).data) as ParityEvent;
      onEvent(ev);
      if (ev.type === "run.finished" || ev.type === "run.failed") source.close();
    });
  }
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) return;
    onError("The event stream was interrupted; the run continues on the server.");
  };
  return () => source.close();
}
