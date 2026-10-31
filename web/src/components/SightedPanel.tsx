import type { BBox, Finding, RunState } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";

interface Props {
  screenshotUrl: string | null;
  findings: Finding[];
  percepts: RunState["percepts"];
  selectedId: string | null;
  stage: string | null;
  model: string;
  onSelect: (id: string) => void;
}

function pct(b: BBox) {
  return { left: `${b.x_min / 10}%`, top: `${b.y_min / 10}%`, width: `${(b.x_max - b.x_min) / 10}%`, height: `${(b.y_max - b.y_min) / 10}%` };
}

export function stageBadge(stage: string | null, model: string) {
  if (stage === "navigator") return <MetaBadge model={model} capability="computer use" />;
  if (stage === "seer") return <MetaBadge model={model} capability="grounding" />;
  if (stage === "comparator") return <MetaBadge model={model} capability="comparison" />;
  return <CodeBadge what="Chromium · screenshot" />;
}

export function SightedPanel({ screenshotUrl, findings, percepts, selectedId, stage, model, onSelect }: Props) {
  return (
    <section className="surface flex flex-col min-h-0" aria-labelledby="sighted-h">
      <div className="flex items-center justify-between px-3 py-2 border-b hairline">
        <h2 id="sighted-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Sighted</h2>
        {stageBadge(stage, model)}
      </div>
      <div className="relative m-3" style={{ aspectRatio: "16 / 9", background: "var(--surface-2)", borderRadius: 4, overflow: "hidden" }}>
        {screenshotUrl ? (
          <img src={screenshotUrl} alt="The audited page as a sighted user sees it" className="block w-full h-full" />
        ) : (
          <div className="absolute inset-0 grid place-items-center muted">Run the audit to see the page</div>
        )}
        {percepts.map((p, i) => <span key={`p${i}`} className="percept" style={pct(p.bbox)} aria-hidden="true" />)}
        {findings.map((f) => (
          <button
            key={f.id} type="button" className="box" style={pct(f.bbox)} data-selected={f.id === selectedId} onClick={() => onSelect(f.id)}
            aria-label={`Finding: sighted user sees ${f.sighted_text}`} aria-pressed={f.id === selectedId}
          >
            {f.id === selectedId && <span className="box-label">{f.sighted_text}</span>}
          </button>
        ))}
      </div>
    </section>
  );
}
