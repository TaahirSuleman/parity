import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, decide, getEval, getFlows, getHealth, getRun, screenshotUrl, startRun, streamRun, type FlowInfo, type Health } from "./api";
import type { EvalResults } from "./components/EvalTab";
import { reconcileDecisions, submitDecision } from "./state/decisions";
import { startRunMessage } from "./state/errors";
import { runIdFromLocation, withRunParam } from "./state/location";
import { shouldReset } from "./state/reducer";
import { initialState, reduce, resetFor, select } from "./state/reducer";
import type { ParityEvent, RunMode, RunState } from "./state/types";
import { Workbench } from "./Workbench";

type Action = { kind: "event"; ev: ParityEvent } | { kind: "select"; id: string } | { kind: "reset"; mode: RunMode } | { kind: "error"; message: string } | { kind: "notice"; message: string | null };

function appReducer(state: RunState, action: Action): RunState {
  switch (action.kind) {
    case "event":  // a decision, an end or a failure settles whatever the notice was about ("reconnecting…" must not outlive run.failed)
      return { ...reduce(state, action.ev), notice: ["decision.recorded", "run.finished", "run.failed"].includes(action.ev.type) ? null : state.notice };
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
  const startingRef = useRef(false);  // a start request in flight: a second click (or a slow first one) must not start a second run
  const [starting, setStarting] = useState(false);
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
    document.title = state.phase === "running" ? "Parity · auditing…" : state.phase === "finished" ? `Parity · ${state.run?.findings_verified ?? 0} findings` : state.phase === "failed" ? "Parity · run failed" : "Parity";
  }, [state.phase, state.run?.findings_verified]);

  useEffect(() => {
    Promise.all([getHealth().catch(() => null), getFlows().catch(() => null)]).then(([h, flOrNull]) => {
      setHealth(h);
      const fl = flOrNull ?? [];
      setFlows(fl);
      if (flOrNull === null) dispatch({ kind: "notice", message: "The list of flows could not be loaded from the server; reload the page to try again." });
      if (h) dispatch({ kind: "reset", mode: h.has_key && h.live_enabled && h.mode_default === "live" ? "live" : "replay" });
      // Default to the single-page checkout replay: it reaches the hero finding in seconds and always carries it; the
      // multi-page agent walk (longer, and its findings vary with where the agent scrolls) is one pick away.
      const replayable = fl.filter((f) => h?.replay_flows?.[f.id]);
      const preferred = replayable.find((f) => f.single_page) ?? replayable[0] ?? fl[0];
      if (preferred) setFlowId(preferred.id);
      const linked = runIdFromLocation(window.location.pathname, window.location.search);
      if (linked) {  // a shared or reloaded run: its history streams back in, once the server confirms it still has the run
        getRun(linked).then(() => {
          closeRef.current?.();
          closeRef.current = follow(linked);
        }, (e: unknown) => dispatch({ kind: "notice", message: e instanceof ApiError && e.status === 404
          ? "The linked run is not on this server any more: Replay copies are kept for a limited time. Start a new Replay."
          : `The linked run could not be loaded: ${e instanceof ApiError ? e.detail : String(e)}.` }));
      }
    });
    return () => closeRef.current?.();
  }, [follow]);

  const focusMain = () => requestAnimationFrame(() => document.getElementById("main")?.focus());  // the Eval view may unmount under the button
  const begin = useCallback(async (start: () => Promise<{ run_id: string }>, mode: RunMode) => {
    if (startingRef.current || state.phase === "running") return;  // one run at a time: a double click, or a click while a slow start is pending
    startingRef.current = true;
    setStarting(true);
    closeRef.current?.();
    setStepOverride(null);
    setView("workbench");
    dispatch({ kind: "reset", mode });
    try {
      const { run_id } = await start();
      window.history.replaceState(null, "", withRunParam(window.location.search, run_id) || window.location.pathname);
      closeRef.current = follow(run_id);
      focusMain();
    } catch (e) {
      const m = startRunMessage(e);
      dispatch(m.kind === "notice" ? { kind: "notice", message: m.text } : { kind: "error", message: m.text });
    } finally {
      startingRef.current = false;
      setStarting(false);
    }
  }, [state.phase, follow]);

  const onRun = useCallback(() => {
    if (!flow) {
      dispatch({ kind: "notice", message: "The list of flows has not loaded yet; wait a moment or reload the page." });
      return;
    }
    void begin(() => startRun(flow.id, state.mode), state.mode);
  }, [flow, state.mode, begin]);

  const onViewChange = useCallback((next: "workbench" | "eval") => {
    setView(next);
    if (next === "eval" && evalResults === undefined) getEval().then(setEvalResults).catch(() => setEvalResults(null));
  }, [evalResults]);

  const onReplayRun = useCallback((runId: string) => void begin(() => startRun(null, "replay", runId), "replay"), [begin]);  // a recorded public sample, from the Eval tab

  const onDecision = useCallback((id: string, decision: "approve" | "reject", reason: string) => {
    if (!state.run) return Promise.resolve();
    return submitDecision({ decide, getRun }, state.run.id, id, decision, reason, (ev) => dispatch({ kind: "event", ev }),
      (message) => dispatch({ kind: "notice", message: /unknown run/i.test(message)
        ? "This run is not on the server any more (Replay copies are kept for a limited time), so the decision could not be saved. Start a new Replay."
        : `The decision could not be saved: ${message}. The run is unchanged; try again.` }),
      (message) => dispatch({ kind: "notice", message }));
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
      view={view} onViewChange={onViewChange} evalResults={evalResults ?? null} onReplayRun={onReplayRun} starting={starting}
    />
  );
}
