import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, decide, getFlows, getHealth, screenshotUrl, startRun, streamRun, type FlowInfo, type Health } from "./api";
import { initialState, reduce, resetFor, select } from "./state/reducer";
import type { ParityEvent, RunMode, RunState } from "./state/types";
import { Workbench } from "./Workbench";

type Action = { kind: "event"; ev: ParityEvent } | { kind: "select"; id: string } | { kind: "reset"; mode: RunMode } | { kind: "error"; message: string };

function appReducer(state: RunState, action: Action): RunState {
  switch (action.kind) {
    case "event":
      return reduce(state, action.ev);
    case "select":
      return select(state, action.id);
    case "reset":
      return resetFor(action.mode);
    case "error":
      return { ...state, phase: "failed", error: action.message };
  }
}

export default function App() {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const [health, setHealth] = useState<Health | null>(null);
  const [flows, setFlows] = useState<FlowInfo[]>([]);
  const closeRef = useRef<(() => void) | null>(null);
  const flow = flows[0];

  useEffect(() => {
    getHealth().then((h) => {
      setHealth(h);
      dispatch({ kind: "reset", mode: h.has_key && h.live_enabled && h.mode_default === "live" ? "live" : "replay" });
    }).catch(() => setHealth(null));
    getFlows().then(setFlows).catch(() => setFlows([]));
    return () => closeRef.current?.();
  }, []);

  const onRun = useCallback(async () => {
    if (!flow) return;
    closeRef.current?.();
    const mode = state.mode;
    dispatch({ kind: "reset", mode });
    try {
      const { run_id } = await startRun(flow.id, mode);
      closeRef.current = streamRun(run_id, (ev) => dispatch({ kind: "event", ev }), (message) => dispatch({ kind: "error", message }));
    } catch (e) {
      const message = e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : String(e);
      dispatch({ kind: "error", message });
    }
  }, [flow, state.mode]);

  const onDecision = useCallback((id: string, decision: "approve" | "reject", reason: string) => {
    if (!state.run) return;
    decide(state.run.id, id, decision, reason).catch((e) => dispatch({ kind: "error", message: e instanceof ApiError ? e.detail : String(e) }));
  }, [state.run]);

  const lastStep = state.steps[state.steps.length - 1];
  const shot = state.run && lastStep ? screenshotUrl(state.run.id, lastStep.index) : null;
  const canLive = Boolean(health?.has_key && health?.live_enabled);
  return (
    <Workbench
      state={state} flowName={flow?.name ?? "Checkout"} canLive={canLive} screenshotUrl={shot} model="muse-spark-1.3-contributor"
      onModeChange={(mode) => dispatch({ kind: "reset", mode })} onRun={onRun} onSelect={(id) => dispatch({ kind: "select", id })} onDecision={onDecision}
    />
  );
}
