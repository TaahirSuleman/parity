import { useState } from "react";
import { FindingsFeed } from "./components/FindingsFeed";
import { Header } from "./components/Header";
import { EvalTab, type EvalResults } from "./components/EvalTab";
import { ScreenReaderPanel } from "./components/ScreenReaderPanel";
import { SightedPanel } from "./components/SightedPanel";
import { TraceDrawer } from "./components/TraceDrawer";
import type { FlowOption } from "./components/Header";
import type { RunMode, RunState } from "./state/types";

interface Props {
  state: RunState;
  flows: FlowOption[];
  flowId: string;
  onFlowChange: (id: string) => void;
  canLive: boolean;
  screenshotUrl: string | null;
  model: string;
  onModeChange: (mode: RunMode) => void;
  onRun: () => void;
  onSelect: (id: string) => void;
  onDecision?: (id: string, decision: "approve" | "reject", reason: string) => void | Promise<void>;
  stepIndex?: number | null;
  onStepChange?: (index: number) => void;
  view?: "workbench" | "eval";
  onViewChange?: (view: "workbench" | "eval") => void;
  evalResults?: EvalResults | null;
  onReplayRun?: (runId: string) => void;
}

/** The whole workbench from props: the mock and the live app render this same component. */
export function Workbench({ state, flows, flowId, onFlowChange, canLive, screenshotUrl, model, onModeChange, onRun, onSelect, onDecision, stepIndex = null, onStepChange, view = "workbench", onViewChange, evalResults = null, onReplayRun }: Props) {
  const approved = state.findings.filter((f) => f.status === "approved").length;
  const pending = state.findings.filter((f) => f.fix && !f.decision).length;
  const [traceOpen, setTraceOpen] = useState(false);
  const selected = state.findings.find((f) => f.id === state.selectedFindingId) ?? null;
  return (
    <div className="flex flex-col" style={{ height: "100vh" }}>
      <Header view={view} onViewChange={onViewChange} approved={approved} pending={pending} flows={flows} flowId={flowId} onFlowChange={onFlowChange} run={state.run} mode={state.mode} canLive={canLive} running={state.phase === "running"} onModeChange={onModeChange} onRun={onRun} />
      {view === "eval" ? (
        <main className="flex-1 flex flex-col min-h-0 overflow-auto"><EvalTab results={evalResults} onReplay={(id) => onReplayRun?.(id)} /></main>
      ) : (
      <main className="flex-1 workbench-grid">
        <SightedPanel screenshotUrl={screenshotUrl} findings={state.findings} percepts={state.percepts} selectedId={state.selectedFindingId} stage={state.stage} model={state.models.navigator ?? model} timeline={state.timeline}
          steps={state.steps} stepIndex={stepIndex} onStepChange={onStepChange} onSelect={onSelect} />
        <FindingsFeed findings={state.findings} rejected={state.rejected} selectedId={state.selectedFindingId} phase={state.phase} error={state.error} onSelect={onSelect} onDecision={onDecision}
          flowName={flows.find((f) => f.id === flowId)?.name ?? "flow"} />
        <ScreenReaderPanel finding={selected} />
        <p className="sr-only" aria-live="polite">{state.phase === "finished" ? `Audit finished: ${state.run?.findings_verified ?? 0} verified findings.` : ""}</p>
      </main>
      )}
      <TraceDrawer calls={state.calls} open={traceOpen} onToggle={() => setTraceOpen((o) => !o)} />
    </div>
  );
}
