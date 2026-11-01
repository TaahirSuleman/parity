import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, decide, getEval, getFlows, getHealth, getRun, screenshotUrl, startRun, streamRun, type FlowInfo, type Health } from "./api";
import type { EvalResults } from "./components/EvalTab";
import { reconcileDecisions, submitDecision } from "./state/decisions";
import { runIdFromSearch, withRunParam } from "./state/location";
import { shouldReset } from "./state/reducer";
import { initialState, reduce, resetFor, select } from "./state/reducer";
import type { ParityEvent, RunMode, RunState } from "./state/types";
import { Workbench } from "./Workbench";

type Action = { kind: "event"; ev: ParityEvent } | { kind: "select"; id: string } | { kind: "reset"; mode: RunMode } | { kind: "error"; message: string } | { kind: "notice"; message: string | null };

function appReducer(state: RunState, action: Action): RunState {
  switch (action.kind) {
    case "event":
      return { ...reduce(state, action.ev), notice: action.ev.type === "decision.recorded" ? null : state.notice };
    case "select":
      return select(state, action.id);
    case "reset":
      return resetFor(action.mode);
    case "error":
      return { ...state, phase: "failed", error: action.message };
    case "notice":
      return { ...state, notice: action.message };
  }
}

export default function App() {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const [health, setHealth] = useState<Health | null>(null);
  const [flows, setFlows] = useState<FlowInfo[]>([]);
  const closeRef = useRef<(() => void) | null>(null);
  const [flowId, setFlowId] = useState<string>("");
  const [stepOverride, setStepOverride] = useState<number | null>(null); // a screen picked on the step strip
  const [view, setView] = useState<"workbench" | "eval">("workbench");
  const [evalResults, setEvalResults] = useState<EvalResults | null | undefined>(undefined);
  const flow = flows.find((f) => f.id === flowId) ?? flows[0];
  // One subscription shape for every stream: events in; a notice (not a failure) when the stream drops; and when the run
  // finishes, the decisions the server holds (made after the stream closed, or before a reload) are applied.
  const follow = useCallback((runId: string) => streamRun(runId, (ev) => {
    dispatch({ kind: "event", ev });
    if (ev.type === "run.finished") void reconcileDecisions({ getRun }, runId, (d) => dispatch({ kind: "event", ev: d }));
  }, (message) => dispatch({ kind: "notice", message })), []);
  useEffect(() => {  // the header names the run on screen: a reloaded or linked run selects its own flow
    const id = state.run?.flow_id;
    if (id && flows.some((f) => f.id === id)) setFlowId(id);
  }, [state.run?.flow_id, flows]);

  useEffect(() => {
    Promise.all([getHealth().catch(() => null), getFlows().catch(() => [] as FlowInfo[])]).then(([h, fl]) => {
      setHealth(h);
      setFlows(fl);
      if (h) dispatch({ kind: "reset", mode: h.has_key && h.live_enabled && h.mode_default === "live" ? "live" : "replay" });
      // Default to the single-page checkout replay: it reaches the hero finding in seconds and always carries it; the
      // multi-page agent walk (longer, and its findings vary with where the agent scrolls) is one pick away.
      const replayable = fl.filter((f) => h?.replay_flows?.[f.id]);
      const preferred = replayable.find((f) => f.single_page) ?? replayable[0] ?? fl[0];
      if (preferred) setFlowId(preferred.id);
      const linked = runIdFromSearch(window.location.search);
      if (linked) {  // a shared or reloaded run: its history streams back in
        closeRef.current?.();
        closeRef.current = follow(linked);
      }
    });
    return () => closeRef.current?.();
  }, [follow]);

  const onRun = useCallback(async () => {
    if (!flow) return;
    closeRef.current?.();
    const mode = state.mode;
    setStepOverride(null);
    dispatch({ kind: "reset", mode });
    try {
      const { run_id } = await startRun(flow.id, mode);
      window.history.replaceState(null, "", withRunParam(window.location.search, run_id) || window.location.pathname);
      closeRef.current = follow(run_id);
    } catch (e) {
      const message = e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : String(e);
      dispatch({ kind: "error", message });
    }
  }, [flow, state.mode, follow]);

  const onViewChange = useCallback((next: "workbench" | "eval") => {
    setView(next);
    if (next === "eval" && evalResults === undefined) getEval().then(setEvalResults).catch(() => setEvalResults(null));
  }, [evalResults]);

  const onReplayRun = useCallback(async (runId: string) => {  // a recorded public sample, opened from the Eval tab
    closeRef.current?.();
    setStepOverride(null);
    setView("workbench");
    dispatch({ kind: "reset", mode: "replay" });
    try {
      const { run_id } = await startRun(null, "replay", runId);
      window.history.replaceState(null, "", withRunParam(window.location.search, run_id) || window.location.pathname);
      closeRef.current = follow(run_id);
    } catch (e) {
      dispatch({ kind: "error", message: e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : String(e) });
    }
  }, [follow]);

  const onDecision = useCallback((id: string, decision: "approve" | "reject", reason: string) => {
    if (!state.run) return Promise.resolve();
    return submitDecision({ decide, getRun }, state.run.id, id, decision, reason, (ev) => dispatch({ kind: "event", ev }),
      (message) => dispatch({ kind: "notice", message: `The decision could not be saved: ${message}. The run is unchanged; try again.` }));
  }, [state.run]);

  const lastStep = state.steps[state.steps.length - 1];
  const selectedFinding = state.findings.find((f) => f.id === state.selectedFindingId);
  const stepIndex = stepOverride ?? (state.phase === "running" ? lastStep?.index : selectedFinding?.step_index ?? lastStep?.index) ?? null;
  const shot = state.run && stepIndex !== null ? screenshotUrl(state.run.id, stepIndex) : null;
  const canLive = Boolean(health?.has_key && health?.live_enabled);
  return (
    <Workbench
      state={state} flows={flows} flowId={flow?.id ?? ""} onFlowChange={setFlowId} canLive={canLive} screenshotUrl={shot} model={state.models.navigator ?? state.models.comparator}
      onModeChange={(mode) => { if (!shouldReset(state, mode)) return; closeRef.current?.(); dispatch({ kind: "reset", mode }); }} onRun={onRun}
      onSelect={(id) => { setStepOverride(null); dispatch({ kind: "select", id }); }} onDecision={onDecision} stepIndex={stepIndex} onStepChange={setStepOverride}
      view={view} onViewChange={onViewChange} evalResults={evalResults ?? null} onReplayRun={onReplayRun}
    />
  );
}
