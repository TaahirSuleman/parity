import { useEffect, useState } from "react";
import type { BBox, Finding, RunState, Step, TimelineRow } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";

interface Props {
  screenshotUrl: string | null;
  findings: Finding[];
  percepts: RunState["percepts"];
  selectedId: string | null;
  stage: string | null;
  model: string;
  timeline: TimelineRow[];
  steps?: Step[];
  stepIndex?: number | null; // the screen on show; boxes belong to it
  onStepChange?: (index: number) => void;
  onSelect: (id: string) => void;
  finished?: boolean;
}

export const screenName = (url: string) => (url.split("/").pop() || "page").replace(/\.html?$/, "").replace(/[-_]/g, " ");

function pct(b: BBox) {
  return { left: `${b.x_min / 10}%`, top: `${b.y_min / 10}%`, width: `${(b.x_max - b.x_min) / 10}%`, height: `${(b.y_max - b.y_min) / 10}%` };
}

export function stageBadge(stage: string | null, model: string, hasBoxes = false) {
  if (stage === "navigator") return <MetaBadge model={model} capability="computer use" />;
  if (stage === "seer") return <MetaBadge model={model} capability="grounding" />;
  if (stage === "comparator") return <MetaBadge model={model} capability="comparison" />;
  if (hasBoxes) return <span className="inline-flex items-center gap-2"><CodeBadge what="Chromium · screenshot" /><MetaBadge model={model} capability="grounding" /></span>;  // the boxes are the model's
  return <CodeBadge what="Chromium · screenshot" />;
}

export function SightedPanel({ screenshotUrl, findings, percepts, selectedId, stage, model, timeline, steps = [], stepIndex = null, onStepChange, onSelect, finished = false }: Props) {
  const [withheld, setWithheld] = useState(false);  // the image did not load: an anonymised sample keeps screenshots only where a finding was verified
  useEffect(() => setWithheld(false), [screenshotUrl]);
  const shown = stepIndex === null ? findings : findings.filter((f) => f.step_index === stepIndex);
  const last = steps.length ? steps[steps.length - 1].index : null;
  const shownPercepts = stepIndex === null || stepIndex === last ? percepts : [];
  return (
    <section className="surface flex flex-col min-h-0 overflow-auto" aria-labelledby="sighted-h">
      <div className="flex items-center justify-between px-3 py-2 border-b hairline">
        <h2 id="sighted-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Sighted</h2>
        {stageBadge(stage, model, findings.length > 0)}
      </div>
      {steps.length > 1 && (
        <div className="flex items-center gap-1 px-3 pt-2 flex-wrap" role="group" aria-label="Screens of the flow">
          {steps.map((s) => (
            <button key={s.index} type="button" className="btn-quiet text-xs" style={{ padding: "2px 8px" }} aria-pressed={s.index === stepIndex} onClick={() => onStepChange?.(s.index)}
              title={s.url}>
              {s.index + 1} · {screenName(s.url)}
            </button>
          ))}
        </div>
      )}
      <div className="relative m-3" style={{ aspectRatio: "16 / 9", background: "var(--surface-2)", borderRadius: 4, overflow: "hidden", flexShrink: 0 }}>
        {screenshotUrl && withheld ? (
          <div className="absolute inset-0 grid place-items-center muted text-center px-6">Screenshot withheld for this screen: a third-party page's pixels are kept only where a finding was verified.</div>
        ) : screenshotUrl ? (
          <img src={screenshotUrl} alt="The audited page as a sighted user sees it" className="block w-full h-full" style={{ objectFit: "contain" }} onError={() => setWithheld(true)} />
        ) : (
          <div className="absolute inset-0 grid place-items-center muted text-center px-6">
            {finished ? "No screen was captured on this run." : (
              <div className="flex flex-col items-center gap-3">
                <div>Run the audit to see the page</div>
                <ul className="m-0 p-0 text-xs text-left flex flex-col gap-1" style={{ listStyle: "none", maxWidth: 520 }} aria-label="Pipeline: who does what">
                  <li><strong>Muse Spark 1.3</strong> · Navigator (computer use), Seer (grounding), Comparator, Judge, Fixer: the model perceives and proposes.</li>
                  <li><strong>Code</strong> · Capture, Verifier, Re-audit, Human gate: deterministic checks decide what counts; a finding exists only after the Verifier.</li>
                  <li><strong>Gated tools</strong> · "audit this screen" and "finish the walk" are refused by code until their preconditions hold.</li>
                </ul>
              </div>
            )}
          </div>
        )}
        {shownPercepts.map((p, i) => <span key={`p${i}`} className="percept" style={pct(p.bbox)} aria-hidden="true" />)}
        {shown.map((f) => (
          <button
            key={f.id} type="button" className="box" style={pct(f.bbox)} data-selected={f.id === selectedId} onClick={() => onSelect(f.id)}
            aria-label={`Finding: sighted user sees ${f.sighted_text}`} aria-pressed={f.id === selectedId}
          >
            {f.id === selectedId && <span className="box-label">{f.sighted_text}</span>}
          </button>
        ))}
      </div>
      {timeline.length > 0 && (
        <ol className="mx-3 mb-3 mt-0 p-0 flex flex-col gap-1 overflow-y-auto" style={{ listStyle: "none", maxHeight: 160 }} aria-label="Agent timeline" tabIndex={0}>
          {timeline.map((row, i) => (
            <li key={i} className="flex items-baseline gap-2 mono text-xs">
              <span className="muted" style={{ minWidth: 28 }}>t{row.turn}</span>
              <span style={{ color: row.kind === "refused" || row.kind === "blocked" ? "var(--bad)" : "inherit" }}>{row.label}</span>
              {row.kind === "actions" && <MetaBadge model={model} capability="computer use" />}
              {row.kind === "tool_call" && <CodeBadge what="gated tool" />}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
