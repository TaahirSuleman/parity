import { ApiError, type RunDetail } from "../api";
import type { Finding, ParityEvent, Run } from "./types";

export interface DecisionApi {
  decide: (runId: string, findingId: string, decision: "approve" | "reject", reason: string) => Promise<{ finding: Finding; run: Run }>;
  getRun: (runId: string) => Promise<RunDetail>;
}

export function decisionEvent(runId: string, finding: Finding, run: Run): ParityEvent {
  return { type: "decision.recorded", run_id: runId, at: new Date().toISOString(), finding_id: finding.id, decision: finding.decision, status: finding.status, run_status: run.status };
}

/**
 * The SSE stream closes at run.finished, so a decision is applied from the route's own response.
 * A 409 means the finding was decided already (another viewer, or a double click): refetch and apply
 * what was recorded instead of showing the run as failed.
 */
export async function submitDecision(
  api: DecisionApi, runId: string, findingId: string, decision: "approve" | "reject", reason: string,
  onEvent: (ev: ParityEvent) => void, onError: (message: string) => void,
): Promise<void> {
  try {
    const res = await api.decide(runId, findingId, decision, reason);
    onEvent(decisionEvent(runId, res.finding, res.run));
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      try {
        const detail = await api.getRun(runId);
        const recorded = detail.findings.find((f) => f.id === findingId);
        if (recorded?.decision) {
          onEvent(decisionEvent(runId, recorded, detail.run));
          return;
        }
      } catch {
        /* fall through to the error below */
      }
    }
    onError(e instanceof ApiError ? e.detail : String(e));
  }
}
