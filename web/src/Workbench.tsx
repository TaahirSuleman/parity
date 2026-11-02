import { useState } from "react";
import { FindingsFeed } from "./components/FindingsFeed";
import { Header } from "./components/Header";
import { EvalTab, type EvalResults } from "./components/EvalTab";
import { ScreenReaderPanel } from "./components/ScreenReaderPanel";
import { SightedPanel } from "./components/SightedPanel";
import { TraceDrawer } from "./components/TraceDrawer";
import { UrlRun } from "./components/UrlRun";
import type { FlowOption } from "./components/Header";
import type { UrlRunRequest } from "./api";
import { isPublicRun, type RunMode, type RunState } from "./state/types";

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
  starting?: boolean; // a start request is in flight: the Run button is already taken
  urlMode?: boolean; // "Live on a page you choose" (spec §19.3.6)
  openUrl?: boolean;
  onUrlModeChange?: (on: boolean) => void;
  onUrlRun?: (req: UrlRunRequest) => void;
  suggestedUrls?: string[];
  closedToday?: boolean;
  urlRefusal?: string | null;
}

/** The whole workbench from props: the mock and the live app render this same component. */
export function Workbench({ state, flows, flowId, onFlowChange, canLive, screenshotUrl, model, onModeChange, onRun, onSelect, onDecision, stepIndex = null, onStepChange, view = "workbench", onViewChange, evalResults = null, onReplayRun, starting = false,
                            urlMode = false, openUrl = false, onUrlModeChange, onUrlRun, suggestedUrls = [], closedToday = false, urlRefusal = null }: Props) {
  const approved = state.findings.filter((f) => f.decision?.decision === "approve").length;  // by the human's decision, which no later event overwrites
  const pending = state.findings.filter((f) => f.fix && !f.decision).length;
  const [traceOpen, setTraceOpen] = useState(false);
  const selected = state.findings.find((f) => f.id === state.selectedFindingId) ?? null;
  const isPublic = isPublicRun(state.run);  // an anonymised sample: screenshots were withheld where nothing was verified
  const readOnly = isPublic || Boolean(state.run?.public) || Boolean(flows.find((f) => f.id === (state.run?.flow_id ?? flowId))?.public);  // a page we do not serve: no fix will follow (spec §17, §19.2, §19.3)
  const outcome = state.agent && !state.agent.finished ? state.agent.summary : null;  // a walk the site or the guard stopped
  const live = state.phase === "running" ? "Audit started: capturing the page and comparing what is seen with what is announced."
    : state.phase === "finished" ? `Audit finished: ${state.run?.findings_verified ?? 0} verified findings.`
    : state.phase === "failed" ? `Audit failed: ${state.error ?? "the run failed"}.` : "";
  return (
    <div className="flex flex-col workbench-root" style={{ height: "100vh" }}>
      <Header view={view} onViewChange={onViewChange} approved={approved} pending={pending} flows={flows} flowId={flowId} onFlowChange={onFlowChange} run={state.run} mode={state.mode} canLive={canLive} running={state.phase === "running" || starting} screens={state.steps.length} onModeChange={onModeChange} onRun={onRun}
        urlMode={urlMode} openUrl={openUrl} onUrlModeChange={onUrlModeChange} />
      {urlMode && view !== "eval" && <UrlRun suggested={suggestedUrls} closed={closedToday} running={state.phase === "running" || starting} refusal={urlRefusal} onRun={(req) => onUrlRun?.(req)} />}
      {view === "eval" ? (
        <main id="main" tabIndex={-1} className="flex-1 flex flex-col min-h-0 overflow-auto"><EvalTab results={evalResults} onReplay={(id) => onReplayRun?.(id)} /></main>
      ) : (
      <main id="main" tabIndex={-1} className="flex-1 workbench-grid">
        <SightedPanel screenshotUrl={screenshotUrl} findings={state.findings} percepts={state.percepts} selectedId={state.selectedFindingId} stage={state.stage} model={state.models.navigator ?? model} timeline={state.timeline}
          steps={state.steps} stepIndex={stepIndex} onStepChange={onStepChange} onSelect={onSelect} finished={state.phase === "finished"} isPublic={isPublic} />
        <FindingsFeed findings={state.findings} rejected={state.rejected} selectedId={state.selectedFindingId} phase={state.phase} error={state.error} onSelect={onSelect} onDecision={onDecision}
          flowName={flows.find((f) => f.id === flowId)?.name ?? "flow"} notice={state.notice ?? null} outcome={outcome} steps={state.steps}
          fixesExpected={state.phase === "running" && !readOnly} readOnly={readOnly} comparatorModel={state.models.comparator} />
        <ScreenReaderPanel finding={selected} voiceAccuracy={state.voice?.accuracy} />
        <p className="sr-only" aria-live="assertive" aria-atomic="true">{live}</p>
        {state.lastDecision && (
          <p className="sr-only" role="alert" key={`${state.lastDecision.finding_id}-${state.lastDecision.at}`}>
            {state.lastDecision.decision === "approve" ? "Approved" : "Rejected"} · {state.lastDecision.reason}
          </p>
        )}
      </main>
      )}
      <TraceDrawer calls={state.calls} open={traceOpen} onToggle={() => setTraceOpen((o) => !o)} />
    </div>
  );
}
