import { MODEL_LABELS } from "../state/types";

export function MetaBadge({ model, capability }: { model: string; capability: string }) {
  const label = MODEL_LABELS[model] ?? model;
  return (
    <span className="badge model" title={`${label} · ${capability} (Meta model: ${model})`}>
      {label.toUpperCase()} · {capability.toUpperCase()}
    </span>
  );
}

export function CodeBadge({ what }: { what: string }) {
  return <span className="badge" title="Deterministic step: code, not a model">{what.toUpperCase()}</span>;
}
