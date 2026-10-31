import type { CallEvent } from "../state/types";
import { fmtCost } from "./Header";
import { MetaBadge } from "./MetaBadge";

export function TraceDrawer({ calls, open, onToggle }: { calls: CallEvent[]; open: boolean; onToggle: () => void }) {
  const tokens = calls.reduce((s, c) => s + c.tokens, 0);
  const cost = calls.reduce((s, c) => s + c.cost_usd, 0);
  return (
    <section className="surface trace" style={{ borderRadius: 0, borderWidth: "1px 0 0 0" }} aria-labelledby="trace-h">
      <button type="button" className="flex items-center gap-3 w-full px-4 py-2 text-left" style={{ background: "transparent", border: 0, cursor: "pointer" }} onClick={onToggle} aria-expanded={open} aria-controls="trace-table">
        <h2 id="trace-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Trace</h2>
        <span className="mono text-xs muted">{open ? "▾" : "▸"} {calls.length} model calls · {tokens.toLocaleString()} tokens · {fmtCost(cost)}</span>
        <span className="ml-auto text-xs muted">every call: model, request ID, tokens, latency, cost</span>
      </button>
      {open && (
        <div id="trace-table" className="px-4 pb-3 overflow-x-auto" style={{ maxHeight: 240, overflowY: "auto" }}>
          <table>
            <thead><tr><th>stage</th><th>model</th><th>request id</th><th>tokens</th><th>latency</th><th>cost</th><th>cache</th></tr></thead>
            <tbody>
              {calls.map((c, i) => (
                <tr key={`${c.request_id}-${i}`}>
                  <td>{c.stage}</td>
                  <td><MetaBadge model={c.model} capability={c.stage} /></td>
                  <td title={c.request_id}>{c.request_id.slice(0, 8) || "—"}</td>
                  <td>{c.tokens.toLocaleString()}</td>
                  <td>{c.latency_ms.toLocaleString()} ms</td>
                  <td>{fmtCost(c.cost_usd)}</td>
                  <td>{c.cache_hit ? "hit" : c.error ? <span style={{ color: "var(--bad)" }}>error</span> : "miss"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
