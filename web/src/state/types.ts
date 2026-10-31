// Mirrors parity/store/models.py (spec docs/19 §5) and the SSE events (§8).

export type RunMode = "live" | "replay";
export type RunStatus = "queued" | "running" | "awaiting_review" | "done" | "failed";
export type FindingStatus = "verified" | "judged" | "fix_proposed" | "reaudited" | "approved" | "rejected";
export type Severity = "critical" | "serious" | "moderate" | "minor" | "needs_review";

export interface BBox { x_min: number; y_min: number; x_max: number; y_max: number }
export interface Element { backend_id: number; css_path: string; box_px?: [number, number, number, number] | null; outer_html?: string | null; dom_id?: string | null }
export interface Check { passed: boolean; detail: string }
export interface VerifierResult { passed: boolean; checks: Record<string, Check>; element?: Element | null; feedback?: string | null }
export interface WcagRef { sc: string; name: string }
export interface Judgement { is_barrier: boolean | null; severity: Severity; wcag: WcagRef[]; impact: string; model_meta: Record<string, unknown> }
export interface Fix { before_html: string; after_html: string; diff: string; explanation: string; model_meta: Record<string, unknown> }
export interface Reaudit { gap_closed: boolean; sr_name_before: string; sr_name_after: string; comparator_still_flags: boolean | null }
export interface Decision { decision: "approve" | "reject"; reason: string; decided_at: string }
export interface VoiceEvidence { clip_key: string; start_ms: number; end_ms: number; transcript: string; agrees: boolean }

export interface Finding {
  id: string; run_id: string; step_index: number; status: FindingStatus;
  sighted_text: string; sr_role: string; sr_name: string; why_it_matters: string;
  voice?: VoiceEvidence | null; bbox: BBox; element: Element; verifier: VerifierResult;
  judgement?: Judgement | null; fix?: Fix | null; reaudit?: Reaudit | null; decision?: Decision | null;
}
export interface Candidate { step_index: number; sighted_text: string; sr_quote: string; why_it_matters: string; bbox: BBox | null; attempt: number }
export interface Rejected { id: string; run_id: string; step_index: number; candidate: Candidate; verifier: VerifierResult }
export interface ModelCall {
  id: string; run_id: string; step_index?: number | null; stage: string; model: string; request_id: string; response_id: string;
  prompt_sha256: string; cache_hit: boolean; input_tokens: number; cached_tokens: number; output_tokens: number; total_tokens: number;
  latency_ms: number; cost_usd: number; http_status?: number | null; error?: string | null; attempt: number; at: string;
}
export interface Step { run_id: string; index: number; url: string; screenshot: string; ax_tree: string; axe: string; viewport: [number, number]; axe_violations: number; ax_nodes: number; captured_at: string }
export interface Run {
  id: string; mode: RunMode; flow_id: string; goal: string; target_url: string; status: RunStatus; started_at: string; finished_at?: string | null;
  axe_violations: number; findings_verified: number; findings_rejected: number; tokens: number; cost_usd: number; duration_ms: number; error?: string | null; replay_of?: string | null;
}

/** One SSE event as the API sends it: the event's data fields plus type, run_id and at. */
export interface ParityEvent { type: string; run_id: string; at: string; [key: string]: unknown }

/** A model call as carried by a `model.call` event. */
export interface CallEvent { stage: string; model: string; request_id: string; tokens: number; latency_ms: number; cost_usd: number; cache_hit: boolean; attempt: number; http_status?: number | null; error?: string | null; at: string }

export interface RunState {
  run: Run | null;
  steps: Step[];
  findings: Finding[];
  rejected: Rejected[];
  calls: CallEvent[];
  selectedFindingId: string | null;
  mode: RunMode;
  phase: "idle" | "running" | "finished" | "failed";
  stage: string | null; // last model-backed stage seen, for the sighted-panel badge
  percepts: { visible_text: string; kind: string; bbox: BBox }[];
  error: string | null;
}

export const MODEL_LABELS: Record<string, string> = {
  "muse-spark-1.3": "Muse Spark 1.3",
  "muse-spark-1.3-contributor": "Muse Spark 1.3",
  "muse-wonder-1.0": "Muse Wonder 1.0",
  "muse-voice-transcribe-1.0": "Muse Voice Transcribe",
};
export const CHECK_LABELS: Record<string, string> = {
  located: "located", sr_quote_exact: "exact quote", diverges: "diverges", not_axe: "not axe", unique: "unique",
};
