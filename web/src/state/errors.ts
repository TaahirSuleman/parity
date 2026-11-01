import { ApiError } from "../api";

export interface StartMessage { kind: "notice" | "error"; text: string }

export function fmtWait(seconds: number): string {
  if (seconds >= 3600) return `about ${Math.max(1, Math.round(seconds / 3600))} h`;
  if (seconds >= 90) return `about ${Math.round(seconds / 60)} min`;
  return `${Math.max(1, Math.round(seconds))} s`;
}

/** What to say when a run could not start. A 429 (the Live slot or the visitor's limit) is a notice with the way in, never a failed run.
 * The server names the limit; this is the one place that writes the retry time and the Replay suggestion. */
export function startRunMessage(e: unknown): StartMessage {
  if (e instanceof ApiError && e.status === 429) {
    const what = (e.body.error ?? e.detail).replace(/[.\s]+$/, "");
    const wait = e.body.retry_after_s ? `Try again in ${fmtWait(e.body.retry_after_s)}` : "Try again shortly";
    return { kind: "notice", text: `Live is busy or rate-limited: ${what}. ${wait}, or watch a Replay (a recorded run: no model calls, no limit).` };
  }
  if (e instanceof ApiError) return { kind: "error", text: `${e.detail} (HTTP ${e.status})` };
  return { kind: "error", text: String(e) };
}
