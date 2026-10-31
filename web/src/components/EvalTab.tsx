import { CodeBadge, MetaBadge } from "./MetaBadge";
import { fmtCost, fmtDuration } from "./Header";

interface Total { recall: number; precision: number; fp_on_clean: number; n: number; n_labels: number; cost_usd: number; seconds: number }
interface JudgeRow { agreement: number; needs_review_rate: number; cost_per_finding: number; n: number }
interface SweepRow { recall: number; precision: number; cost_usd: number; seconds: number }
export interface PublicSample { name: string; run_id: string; pages: number; verified: number; rejected: number }
export interface EvalResults {
  updated_at?: string; model?: string; judge_model?: string; n_faults?: number; n_clean?: number; runs?: number;
  configs?: Record<string, { runs?: number; total: Total }>;
  axe?: { recall?: number; violations?: number };
  judge?: Record<string, JudgeRow>;
  effort_sweep?: Record<string, SweepRow>;
  standard_tier_check?: { model: string } & SweepRow;
  public?: PublicSample[];
}

const CONFIG_LABELS: Record<string, string> = { full: "Parity (full)", screenshot_only: "screenshot only", tree_only: "tree only", no_grounding: "no grounding" };
const pct = (x: number | undefined) => (x === undefined || x === null ? "—" : `${Math.round(100 * x)}%`);

export function EvalTab({ results, onReplay }: { results: EvalResults | null; onReplay: (runId: string) => void }) {
  if (!results) {
    return (
      <section className="surface p-5 m-3" aria-labelledby="eval-h">
        <h2 id="eval-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Eval</h2>
        <p className="muted">No eval results yet. Run <code className="mono">python -m eval.harness --ablations</code> to produce them.</p>
      </section>
    );
  }
  const model = results.model ?? "muse-spark-1.3-contributor";
  const configs = results.configs ?? {};
  const order = ["full", "screenshot_only", "tree_only", "no_grounding"].filter((k) => configs[k]);
  const full = configs.full?.total;
  return (
    <div className="m-3 flex flex-col gap-3 overflow-auto" style={{ minHeight: 0 }}>
      <section className="surface p-4" aria-labelledby="eval-main-h">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 id="eval-main-h" className="m-0" style={{ fontSize: 16 }}>Parity vs axe-core, same labels</h2>
          <MetaBadge model={model} capability="seer · comparator" />
          <CodeBadge what="code · verifier" />
          <span className="muted text-xs ml-auto">{results.n_faults ?? "?"} seeded faults · {results.n_clean ?? "?"} clean controls · {results.runs ?? configs.full?.runs ?? 1} run(s) per page · {results.updated_at ?? ""}</span>
        </div>
        <table className="eval mt-3">
          <thead><tr><th scope="col">System</th><th scope="col">Recall</th><th scope="col">Precision</th><th scope="col">Findings</th><th scope="col">FP on clean</th><th scope="col">Cost / page set</th><th scope="col">Time</th></tr></thead>
          <tbody>
            {order.map((k) => {
              const t = configs[k].total;
              return (
                <tr key={k} data-config={k}>
                  <th scope="row">{CONFIG_LABELS[k] ?? k}</th>
                  <td>{pct(t.recall)}</td><td>{pct(t.precision)}</td><td>{Math.round(t.n)} / {t.n_labels}</td><td>{t.fp_on_clean.toFixed(1)}</td><td>{fmtCost(t.cost_usd)}</td><td>{fmtDuration(Math.round(t.seconds * 1000))}</td>
                </tr>
              );
            })}
            <tr data-config="axe">
              <th scope="row">axe-core 4.14</th>
              <td>{pct(results.axe?.recall ?? 0)}</td><td>—</td><td>{results.axe?.violations ?? 0} violations</td><td>—</td><td>$0</td><td>—</td>
            </tr>
          </tbody>
        </table>
        {full && order.length > 1 && (
          <p className="text-sm mt-2 mb-0" aria-label="Ablation strip">
            Ablations: {order.filter((k) => k !== "full").map((k) => `${CONFIG_LABELS[k]} recall ${pct(configs[k].total.recall)}`).join(" · ")} — full Parity {pct(full.recall)}.
            Taking away the screenshot, the tree or the grounding step costs recall; the Verifier keeps precision.
          </p>
        )}
      </section>
      {results.judge && Object.keys(results.judge).length > 0 && (
        <section className="surface p-4" aria-labelledby="eval-judge-h">
          <h2 id="eval-judge-h" className="m-0" style={{ fontSize: 16 }}>Judge comparison, same verified findings</h2>
          <table className="eval mt-3">
            <thead><tr><th scope="col">Judge</th><th scope="col">Agreement with labels</th><th scope="col">Needs review</th><th scope="col">Cost per finding</th><th scope="col">n</th></tr></thead>
            <tbody>
              {Object.entries(results.judge).map(([jm, v]) => (
                <tr key={jm}><th scope="row"><MetaBadge model={jm} capability="judge" /></th><td>{pct(v.agreement)}</td><td>{pct(v.needs_review_rate)}</td><td>{fmtCost(v.cost_per_finding)}</td><td>{v.n}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {results.effort_sweep && (
        <section className="surface p-4" aria-labelledby="eval-effort-h">
          <h2 id="eval-effort-h" className="m-0" style={{ fontSize: 16 }}>Reasoning effort, seer and comparator</h2>
          <table className="eval mt-3">
            <thead><tr><th scope="col">Effort</th><th scope="col">Recall</th><th scope="col">Precision</th><th scope="col">Cost</th><th scope="col">Time</th></tr></thead>
            <tbody>
              {Object.entries(results.effort_sweep).map(([eff, v]) => (
                <tr key={eff}><th scope="row">{eff}</th><td>{pct(v.recall)}</td><td>{pct(v.precision)}</td><td>{fmtCost(v.cost_usd)}</td><td>{fmtDuration(Math.round(v.seconds * 1000))}</td></tr>
              ))}
            </tbody>
          </table>
          {results.standard_tier_check && <p className="text-sm muted mb-0">Standard tier ({results.standard_tier_check.model}): recall {pct(results.standard_tier_check.recall)}, precision {pct(results.standard_tier_check.precision)} — the same model as the contributor tier.</p>}
        </section>
      )}
      <section className="surface p-4" aria-labelledby="eval-public-h">
        <h2 id="eval-public-h" className="m-0" style={{ fontSize: 16 }}>Real-world sample, read-only and anonymised</h2>
        {(results.public ?? []).length === 0 ? (
          <p className="muted text-sm mb-0">No public-site runs recorded yet.</p>
        ) : (
          <ul className="m-0 mt-2 p-0" style={{ listStyle: "none" }}>
            {(results.public ?? []).map((s) => (
              <li key={s.run_id} className="flex items-center gap-3 py-1 text-sm">
                <span style={{ minWidth: 70 }}>{s.name}</span>
                <span className="muted">{s.pages} screen{s.pages === 1 ? "" : "s"} · {s.verified} verified · {s.rejected} rejected</span>
                <button type="button" className="btn-quiet text-xs ml-auto" onClick={() => onReplay(s.run_id)}>Replay {s.name}</button>
              </li>
            ))}
          </ul>
        )}
        <p className="text-xs muted mb-0 mt-2">Findings are evidence, not a conformance claim; a human approves every fix.</p>
      </section>
    </div>
  );
}
