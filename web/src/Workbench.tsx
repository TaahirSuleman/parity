import { useState } from "react";
import { FindingsFeed } from "./components/FindingsFeed";
import { Header } from "./components/Header";
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
  onDecision?: (id: string, decision: "approve" | "reject", reason: string) => void;
}

/** The whole workbench from props: the mock and the live app render this same component. */
export function Workbench({ state, flows, flowId, onFlowChange, canLive, screenshotUrl, model, onModeChange, onRun, onSelect, onDecision }: Props) {
  const approved = state.findings.filter((f) => f.status === "approved").length;
  const pending = state.findings.filter((f) => f.fix && !f.decision).length;
  const [traceOpen, setTraceOpen] = useState(false);
  const selected = state.findings.find((f) => f.id === state.selectedFindingId) ?? null;
  return (
    <div className="h-full flex flex-col" style={{ minHeight: "100vh" }}>
      <Header approved={approved} pending={pending} flows={flows} flowId={flowId} onFlowChange={onFlowChange} run={state.run} mode={state.mode} canLive={canLive} running={state.phase === "running"} onModeChange={onModeChange} onRun={onRun} />
      <main className="flex-1 grid gap-3 p-3 min-h-0" style={{ gridTemplateColumns: "minmax(0, 5fr) minmax(0, 4fr) minmax(0, 3fr)" }}>
        <SightedPanel screenshotUrl={screenshotUrl} findings={state.findings} percepts={state.percepts} selectedId={state.selectedFindingId} stage={state.stage} model={state.models.navigator ?? model} timeline={state.timeline} onSelect={onSelect} />
        <FindingsFeed findings={state.findings} rejected={state.rejected} selectedId={state.selectedFindingId} phase={state.phase} error={state.error} onSelect={onSelect} onDecision={onDecision} />
        <ScreenReaderPanel finding={selected} />
        <p className="sr-only" aria-live="polite">{state.phase === "finished" ? `Audit finished: ${state.run?.findings_verified ?? 0} verified findings.` : ""}</p>
      </main>
      <TraceDrawer calls={state.calls} open={traceOpen} onToggle={() => setTraceOpen((o) => !o)} />
    </div>
  );
}
