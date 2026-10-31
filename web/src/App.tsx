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
  const [flowId, setFlowId] = useState<string>("");
  const flow = flows.find((f) => f.id === flowId) ?? flows[0];

  useEffect(() => {
    Promise.all([getHealth().catch(() => null), getFlows().catch(() => [] as FlowInfo[])]).then(([h, fl]) => {
      setHealth(h);
      setFlows(fl);
      if (h) dispatch({ kind: "reset", mode: h.has_key && h.live_enabled && h.mode_default === "live" ? "live" : "replay" });
      // Default to the multi-page agent flow when a recorded replay exists for it; else the first flow with a replay.
      const replayable = fl.filter((f) => h?.replay_flows?.[f.id]);
      const preferred = replayable.find((f) => !f.single_page) ?? replayable[0] ?? fl[0];
      if (preferred) setFlowId(preferred.id);
    });
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
    const runId = state.run.id;
    decide(runId, id, decision, reason)
      .then((res) => dispatch({ kind: "event", ev: { type: "decision.recorded", run_id: runId, at: new Date().toISOString(), finding_id: id,
        decision: res.finding.decision, status: res.finding.status, run_status: res.run.status } }))  // the stream has closed by now
      .catch((e) => dispatch({ kind: "error", message: e instanceof ApiError ? e.detail : String(e) }));
  }, [state.run]);

  const lastStep = state.steps[state.steps.length - 1];
  const shot = state.run && lastStep ? screenshotUrl(state.run.id, lastStep.index) : null;
  const canLive = Boolean(health?.has_key && health?.live_enabled);
  return (
    <Workbench
      state={state} flows={flows} flowId={flow?.id ?? ""} onFlowChange={setFlowId} canLive={canLive} screenshotUrl={shot} model="muse-spark-1.3-contributor"
      onModeChange={(mode) => dispatch({ kind: "reset", mode })} onRun={onRun} onSelect={(id) => dispatch({ kind: "select", id })} onDecision={onDecision}
    />
  );
}
