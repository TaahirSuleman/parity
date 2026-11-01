import type { CallEvent, Finding, ParityEvent, Rejected, Run, RunMode, RunState, Step, TimelineRow } from "./types";

export const initialState: RunState = {
  run: null, timeline: [], agent: null, models: { navigator: null, comparator: "muse-spark-1.3-contributor", judge: "muse-spark-1.3" }, steps: [], findings: [], rejected: [], calls: [], selectedFindingId: null, mode: "replay", phase: "idle", stage: null, percepts: [], error: null,
};

export function resetFor(mode: RunMode): RunState {
  return { ...initialState, mode };
}

export function select(state: RunState, id: string | null): RunState {
  return { ...state, selectedFindingId: id };
}

const SEVERITY_RANK: Record<string, number> = { critical: 4, serious: 3, moderate: 2, minor: 1, needs_review: 0 };

const CONTROL_ROLES = new Set(["button", "link", "textbox", "searchbox", "checkbox", "radio", "combobox", "switch", "tab", "menuitem", "slider", "spinbutton"]);

/** The finding to open on: the strongest barrier whose fix the re-audit closed; among equals, one on a control (an action a user
 * takes) over an image or a bare text, one whose visible label and name disagree (Label in Name) over the rest, and the later
 * screen (the flow's goal) over an earlier one. */
export function pickHero(findings: Finding[]): Finding | undefined {
  const score = (f: Finding) =>
    (f.reaudit?.gap_closed ? 10 : 0) + (f.judgement?.is_barrier === false ? -5 : 0) + (SEVERITY_RANK[f.judgement?.severity ?? ""] ?? 0)
    + (CONTROL_ROLES.has(f.sr_role ?? "") ? 3 : 0) + (f.judgement?.wcag?.some((w) => w.sc === "2.5.3") ? 1 : 0) + (f.step_index ?? 0) * 0.01;
  return [...findings].sort((a, b) => score(b) - score(a))[0];
}

/** Switching mode resets the workbench, except when the pressed mode is clicked again or a run is going. */
export function shouldReset(state: RunState, mode: RunMode): boolean {
  return mode !== state.mode && state.phase !== "running";
}

function patchFinding(state: RunState, id: string, patch: Partial<Finding>): RunState {
  return { ...state, findings: state.findings.map((f) => (f.id === id ? { ...f, ...patch } : f)) };
}

/** Pure: one SSE event in, the next RunState out. Unknown event types leave the state unchanged. */
export function reduce(state: RunState, ev: ParityEvent): RunState {
  const run = state.run;
  switch (ev.type) {
    case "run.started": {
      const mode = (ev.mode as RunMode) ?? state.mode;
      const started: Run = {
        id: ev.run_id, mode, flow_id: String(ev.flow_id ?? ""), goal: String(ev.goal ?? ""), target_url: String(ev.target_url ?? ""),
        status: "running", started_at: ev.at, finished_at: null, axe_violations: 0, findings_verified: 0, findings_rejected: 0,
        tokens: 0, cost_usd: 0, duration_ms: 0, error: null, replay_of: (ev.replay_of as string | undefined) ?? null,
      };
      const models = {
        navigator: (ev.navigator_model as string | null | undefined) ?? null,
        comparator: String(ev.model ?? initialState.models.comparator), judge: String(ev.judge_model ?? initialState.models.judge),
      };
      return { ...resetFor(mode), run: started, phase: "running", models };
    }
    case "nav.actions": {
      const actions = (ev.actions as string[] | undefined) ?? [];
      return { ...state, stage: "navigator", timeline: [...state.timeline, { turn: Number(ev.turn ?? 0), kind: "actions", label: `computer: ${actions.join(", ") || "no actions"}`, at: ev.at }] };
    }
    case "nav.safety_check": {
      const codes = (ev.codes as string[] | undefined) ?? [];
      const reason = typeof ev.reason === "string" && ev.reason ? ev.reason : "on the store";  // the event says why it was acknowledged (store, or the public-site guard)
      const row: TimelineRow = { turn: Number(ev.turn ?? 0), kind: "actions", at: ev.at, label: `safety check acknowledged (${reason}): ${codes.join(", ")}` };
      return { ...state, timeline: [...state.timeline, row] };
    }
    case "nav.blocked":
      return { ...state, timeline: [...state.timeline, { turn: Number(ev.turn ?? 0), kind: "blocked", label: `blocked: ${String(ev.reason ?? "")}`, at: ev.at }] };
    case "agent.tool_call": {
      const args = (ev.args as Record<string, unknown> | undefined) ?? {};
      const reason = typeof args.reason === "string" ? args.reason : typeof args.summary === "string" ? args.summary : "";
      return { ...state, timeline: [...state.timeline, { turn: Number(ev.turn ?? 0), kind: "tool_call", label: `${String(ev.tool)}${reason ? `: ${reason}` : ""}`, at: ev.at }] };
    }
    case "agent.refused":
      return { ...state, timeline: [...state.timeline, { turn: Number(ev.turn ?? 0), kind: "refused", label: `${String(ev.tool)} refused: ${String(ev.feedback ?? "")}`, at: ev.at }] };
    case "agent.tool_error":
      return { ...state, timeline: [...state.timeline, { turn: Number(ev.turn ?? 0), kind: "error", label: `${String(ev.tool)} error: ${String(ev.error ?? "")}`, at: ev.at }] };
    case "step.captured": {
      if (!run) return state;
      const index = Number(ev.index ?? 0);
      const step: Step = {
        run_id: ev.run_id, index, url: String(ev.url ?? ""), screenshot: `steps/${index}/screenshot.png`, ax_tree: `steps/${index}/ax.json`,
        axe: `steps/${index}/axe.json`, viewport: [1280, 720], axe_violations: Number(ev.axe_violations ?? 0), ax_nodes: Number(ev.ax_nodes ?? 0), captured_at: ev.at,
      };
      return { ...state, steps: [...state.steps.filter((s) => s.index !== index), step].sort((a, b) => a.index - b.index), percepts: [], run: { ...run, axe_violations: run.axe_violations + step.axe_violations } };
    }
    case "seer.done":
      return { ...state, stage: "seer", percepts: (ev.percepts as RunState["percepts"] | undefined) ?? [] };
    case "comparator.candidates":
      return { ...state, stage: "comparator" };
    case "comparator.unparseable":
      return { ...state, timeline: [...state.timeline, { turn: 0, kind: "error", label: "comparator: the answer was not readable JSON; asked again", at: ev.at }] };
    case "verifier.result": {
      if (!run) return state;
      if (ev.passed === true && ev.finding) {
        const finding = ev.finding as Finding;
        const findings = [...state.findings.filter((f) => f.id !== finding.id), finding];
        return {
          ...state, findings, stage: "verifier", run: { ...run, findings_verified: findings.length },
          selectedFindingId: state.selectedFindingId ?? finding.id,
        };
      }
      const rejected: Rejected = {
        id: String(ev.rejected_id ?? `${ev.run_id}-r${state.rejected.length + 1}`), run_id: ev.run_id, step_index: Number(ev.index ?? 0),
        candidate: ev.candidate as Rejected["candidate"],
        verifier: { passed: false, checks: (ev.checks as Rejected["verifier"]["checks"]) ?? {}, feedback: (ev.feedback as string | null) ?? null },
      };
      const all = [...state.rejected.filter((r) => r.id !== rejected.id), rejected];
      return { ...state, rejected: all, stage: "verifier", run: { ...run, findings_rejected: all.length } };
    }
    case "judge.result":
      return { ...patchFinding(state, String(ev.finding_id), { judgement: ev.judgement as Finding["judgement"], status: "judged" }), stage: "judge" };
    case "fixer.proposed":
      return { ...patchFinding(state, String(ev.finding_id), { fix: ev.fix as Finding["fix"], status: "fix_proposed" }), stage: "fixer" };
    case "reaudit.result":
      return { ...patchFinding(state, String(ev.finding_id), { reaudit: ev.reaudit as Finding["reaudit"], status: "reaudited" }), stage: "reaudit" };
    case "fixer.rejected":
      return { ...patchFinding(state, String(ev.finding_id), { fix_note: String(ev.reason ?? "") }), stage: "fixer" };
    case "reaudit.failed":
      return { ...patchFinding(state, String(ev.finding_id), { reaudit_note: String(ev.reason ?? "") }), stage: "reaudit" };
    case "decision.recorded": {
      const decision = ev.decision as Finding["decision"];
      const next = patchFinding(state, String(ev.finding_id), { decision, status: decision?.decision === "approve" ? "approved" : "rejected" });
      const runStatus = ev.run_status as Run["status"] | undefined;
      return runStatus && next.run ? { ...next, run: { ...next.run, status: runStatus } } : next;
    }
    case "model.call": {
      const call: CallEvent = {
        stage: String(ev.stage ?? ""), model: String(ev.model ?? ""), request_id: String(ev.request_id ?? ""), tokens: Number(ev.tokens ?? 0),
        latency_ms: Number(ev.latency_ms ?? 0), cost_usd: Number(ev.cost_usd ?? 0), cache_hit: Boolean(ev.cache_hit), attempt: Number(ev.attempt ?? 1),
        http_status: (ev.http_status as number | null | undefined) ?? null, error: (ev.error as string | null | undefined) ?? null, at: ev.at,
      };
      return {
        ...state, calls: [...state.calls, call], stage: call.stage,
        run: run ? { ...run, tokens: run.tokens + call.tokens, cost_usd: run.cost_usd + call.cost_usd } : run,
      };
    }
    case "run.finished": {
      if (!run) return state;
      const duration = Number(ev.duration_ms ?? Math.max(0, new Date(ev.at).getTime() - new Date(run.started_at).getTime()));  // the recorded run's time, not the replay's
      const agent = (ev.agent as RunState["agent"] | undefined) ?? null;
      const outcome = agent
        ? [{ turn: agent.turns, kind: "outcome" as const, at: ev.at, label: outcomeLabel(agent) }]
        : [];
      return {
        ...state, phase: "finished", stage: null, agent, timeline: [...state.timeline, ...outcome],
        selectedFindingId: pickHero(state.findings)?.id ?? state.selectedFindingId,
        run: {
          ...run, status: (ev.status as Run["status"]) ?? "done", finished_at: ev.at, duration_ms: duration,
          findings_verified: Number(ev.findings_verified ?? run.findings_verified), findings_rejected: Number(ev.findings_rejected ?? run.findings_rejected),
          axe_violations: Number(ev.axe_violations ?? run.axe_violations), tokens: Number(ev.tokens ?? run.tokens), cost_usd: Number(ev.cost_usd ?? run.cost_usd),
        },
      };
    }
    case "run.failed":
      return { ...state, phase: "failed", stage: null, error: String(ev.error ?? "run failed"), run: run ? { ...run, status: "failed", finished_at: ev.at, error: String(ev.error ?? "") } : run };
    default:
      return state;
  }
}

/** The walk's outcome line. A walk the site or the guard stopped is its own reason; only a walk that used its turns up "did not finish". */
export function outcomeLabel(agent: NonNullable<RunState["agent"]>): string {
  if (agent.finished) return agent.finish_forced ? `finished (forced after refusals): ${agent.summary}` : `finished: ${agent.summary}`;
  const summary = agent.summary || "no summary";
  if (agent.turns === 0 || /^(blocked by site|stopped)/i.test(summary)) return summary;
  return `did not finish within ${agent.turns} turns: ${summary}`;
}
