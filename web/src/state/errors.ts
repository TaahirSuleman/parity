import { ApiError } from "../api";

export interface StartMessage { kind: "notice" | "error"; text: string }

/** What to say when a run could not start. A 429 (the Live slot or the visitor's limit) is a notice with the way in, never a failed run. */
export function startRunMessage(e: unknown): StartMessage {
  if (e instanceof ApiError && e.status === 429) {
    const wait = e.body.retry_after_s ? ` Try again in ${e.body.retry_after_s} s,` : " Try again shortly,";
    return { kind: "notice", text: `Live is busy or rate-limited: ${e.body.error ?? e.detail}.${wait} or watch a Replay (a recorded run: no model calls, no limit).` };
  }
  if (e instanceof ApiError) return { kind: "error", text: `${e.detail} (HTTP ${e.status})` };
  return { kind: "error", text: String(e) };
}
