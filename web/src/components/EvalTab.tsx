import { CodeBadge, MetaBadge } from "./MetaBadge";
import { fmtCost, fmtDuration } from "./Header";

interface Total { recall: number; precision: number; fp_on_clean: number; n: number; n_labels: number; cost_usd: number; seconds: number }
interface JudgeRow { agreement: number; needs_review_rate: number; cost_per_finding: number; n: number }
interface SweepRow { recall: number; precision: number; cost_usd: number; seconds: number }
export interface PublicSample { name: string; run_id: string; pages: number; verified: number; rejected: number; status?: string; note?: string }
/** The W3C BAD benchmark block (doc 19 §19.1): recall over the barriers in Parity's scope by kind, precision against the repaired pages. */
export interface External {
  model?: string; runs: number; n_in_scope: number; out_of_scope_count: number; n_clean: number;
  in_scope_recall: number; precision: number; n: number; fp_on_after_pages: number; out_of_scope_hits: number; unlabelled_on_before: number;
  axe_recall: number; axe?: { violations?: number; out_of_scope?: string[] }; cost_usd: number; seconds: number; attribution?: string;
  recall_beyond_axe?: number; union_recall?: number; n_beyond_axe?: number;
}
/** A row of the per-stage sweep. Which fields are set depends on the stage (eval/model_sweep.py); `failed` replaces them all. */
export interface StageRow {
  model: string; effort: string; runs?: number; is_default?: boolean; unpriced?: boolean; failed?: string;
  recall?: number; precision?: number; f1?: number; fp_on_clean?: number; cost_default_judge_usd?: number; seconds?: number;
  n?: number; agreement?: number; needs_review_rate?: number; cost_per_finding?: number;
  gap_closed_rate?: number; rejected?: number; cost_per_fix?: number;
  screens?: number; turns?: number; refusals?: number; safety_checks?: number; cost_usd_stage?: number;
}
export interface StageBest { model: string | null; effort: string | null; reason: string; margin: string; clears_bar: boolean; runs: number }
export interface ModelSweep { stages?: Record<string, { rows?: StageRow[] }>; best?: Record<string, StageBest> }
export interface EvalResults {
  updated_at?: string; model?: string; judge_model?: string; n_faults?: number; n_clean?: number; runs?: number;
  configs?: Record<string, { runs?: number; total: Total }>;
  axe?: { recall?: number; violations?: number };
  judge?: Record<string, JudgeRow>;
  effort_sweep?: Record<string, SweepRow>;
  standard_tier_check?: { model: string } & SweepRow;
  public?: PublicSample[];
  external?: External;
  model_sweep?: ModelSweep;
}

const CONFIG_LABELS: Record<string, string> = { full: "Parity (full)", screenshot_only: "screenshot only", tree_only: "tree only", no_grounding: "no grounding" };
const pct = (x: number | undefined) => (x === undefined || x === null ? "—" : `${Math.round(100 * x)}%`);
const fmtWhen = (iso: string | undefined) => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : `${d.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC" })} UTC`;
};

/** What the ablation numbers say, and nothing more: which configurations recall less than full Parity, and which do not. */
export function ablationSentence(keys: string[], configs: Record<string, { total: Total }>, fullRecall: number): string {
  const lower = keys.filter((k) => configs[k].total.recall < fullRecall).map((k) => CONFIG_LABELS[k] ?? k);
  const notLower = keys.filter((k) => configs[k].total.recall >= fullRecall).map((k) => CONFIG_LABELS[k] ?? k);
  const parts: string[] = [];
  if (lower.length) parts.push(`Lower recall than full Parity: ${lower.join(", ")}.`);
  if (notLower.length) parts.push(`Not lower: ${notLower.join(", ")}.`);
  return parts.join(" ");
}

function HowItWorks() {
  return (
    <section className="surface p-4" aria-labelledby="eval-arch-h">
      <h2 id="eval-arch-h" className="m-0" style={{ fontSize: 16 }}>How Parity works, in ten seconds</h2>
      <img src="/architecture.png" alt="Parity's pipeline: per screen, the Navigator walks, Capture records, the Seer grounds, the Comparator compares and the Verifier checks; per verified finding, the Judge rates, the Fixer proposes, the Re-audit confirms and a human decides" className="block w-full mt-2" style={{ maxWidth: 1100, height: "auto", border: "1px solid var(--line)", borderRadius: 6 }} />
      <p className="text-sm mt-2 mb-0 muted">Blue boxes are Meta models (Muse Spark 1.3); grey boxes are deterministic code. A finding exists only after the Verifier's six checks; a patch is exported only after a human approves each fix.</p>
    </section>
  );
}

const TabHeading = () => <h2 id="eval-h" className="text-xs uppercase tracking-wider muted font-medium m-0 px-1">About &amp; Evals</h2>;

const money = (r: StageRow, x: number | undefined, places = 2) => (r.unpriced ? "price unknown" : x === undefined ? "—" : `$${x.toFixed(places)}`);
const num = (x: number | undefined, places = 1) => (x === undefined ? "—" : x.toFixed(places));
const nRuns = (r: StageRow) => `n = ${r.runs ?? 0}`;
const nItems = (r: StageRow) => `n = ${r.n ?? 0}`;
const DETECTION: [string, (r: StageRow) => string][] = [["n", nRuns], ["Recall", (r) => pct(r.recall)], ["Precision", (r) => pct(r.precision)], ["F1", (r) => num(r.f1, 2)], ["False alarms on clean", (r) => num(r.fp_on_clean)], ["Cost / 3 pages", (r) => money(r, r.cost_default_judge_usd)], ["Time / 3 pages", (r) => (r.seconds === undefined ? "—" : fmtDuration(Math.round(r.seconds * 1000)))]];
const STAGE_COLUMNS: Record<string, [string, (r: StageRow) => string][]> = {
  comparator: DETECTION,
  seer: DETECTION,
  judge: [["n findings", nItems], ["Agreement with labels", (r) => pct(r.agreement)], ["Needs review", (r) => pct(r.needs_review_rate)], ["Cost per finding", (r) => money(r, r.cost_per_finding, 4)]],
  fixer: [["n barriers", nItems], ["Gaps closed", (r) => pct(r.gap_closed_rate)], ["Fixes rejected", (r) => String(r.rejected ?? "—")], ["Cost per fix", (r) => money(r, r.cost_per_fix, 4)]],
  navigator: [["n", nRuns], ["Screens of 4", (r) => num(r.screens)], ["Turns", (r) => num(r.turns)], ["Refusals", (r) => num(r.refusals)], ["Safety checks", (r) => num(r.safety_checks)], ["Navigator cost", (r) => money(r, r.cost_usd_stage, 3)]],
};

/** The per-stage sweep: one table a stage, the best row marked in words as well as weight, n on every row. */
export function ModelSweepSection({ sweep }: { sweep: ModelSweep }) {
  const stages = Object.entries(sweep.stages ?? {}).filter(([stage, entry]) => STAGE_COLUMNS[stage] && (entry.rows ?? []).length > 0);
  if (stages.length === 0) return null;
  return (
    <section className="surface p-4" aria-labelledby="eval-sweep-h">
      <h2 id="eval-sweep-h" className="m-0" style={{ fontSize: 16 }}>Model and effort, per stage</h2>
      <p className="text-sm mt-2 mb-0 muted">One stage changed at a time, every other stage at today's default, on the same labels and findings; one run is a sample, so n is on every row. Cost / 3 pages is projected at the default judge.</p>
      {stages.map(([stage, entry]) => {
        const best = sweep.best?.[stage];
        const columns = STAGE_COLUMNS[stage];
        return (
          <div key={stage} className="mt-3 overflow-x-auto">
            <table className="eval" data-stage={stage}>
              <caption className="text-left text-sm font-medium pb-1">{stage[0].toUpperCase() + stage.slice(1)}</caption>
              <thead><tr><th scope="col">Model</th><th scope="col">Effort</th>{columns.map(([label]) => <th key={label} scope="col">{label}</th>)}</tr></thead>
              <tbody>
                {(entry.rows ?? []).map((r) => {
                  const isBest = best !== undefined && r.model === best.model && r.effort === best.effort && !r.failed;
                  return (
                    <tr key={`${r.model}:${r.effort}`} data-best={isBest || undefined} style={isBest ? { fontWeight: 700 } : undefined}>
                      <th scope="row" className="mono" style={{ fontWeight: "inherit" }}>{isBest && <span>best: </span>}{r.model}{r.is_default && <span className="muted"> (default)</span>}</th>
                      <td>{r.effort}</td>
                      {r.failed ? <td colSpan={columns.length}>failed: {r.failed}</td> : columns.map(([label, cell]) => <td key={label}>{cell(r)}</td>)}
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {best?.model && <p className="text-xs muted mt-1 mb-0">{best.reason}{best.margin ? ` ${best.margin}.` : ""}</p>}
          </div>
        );
      })}
    </section>
  );
}

export function EvalTab({ results, onReplay }: { results: EvalResults | null; onReplay: (runId: string) => void }) {
  if (!results) {
    return (
      <div className="m-3 flex flex-col gap-3 overflow-auto" style={{ minHeight: 0 }}>
        <TabHeading />
        <HowItWorks />
        <p className="muted m-0 px-1">No eval results are published on this server yet.</p>
      </div>
    );
  }
  const model = results.model ?? "muse-spark-1.3-contributor";
  const configs = results.configs ?? {};
  const order = ["full", "screenshot_only", "tree_only", "no_grounding"].filter((k) => configs[k]);
  const full = configs.full?.total;
  return (
    <div className="m-3 flex flex-col gap-3 overflow-auto" style={{ minHeight: 0 }}>
      <TabHeading />
      <HowItWorks />
      <section className="surface p-4" aria-labelledby="eval-main-h">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 id="eval-main-h" className="m-0" style={{ fontSize: 16 }}>Parity vs axe-core, same labels</h2>
          <MetaBadge model={model} capability="seer · comparator" />
          <CodeBadge what="code · verifier" />
          <span className="muted text-xs ml-auto">{results.n_faults ?? "?"} seeded faults built to pass axe-core · {results.n_clean ?? "?"} clean controls · {results.runs ?? configs.full?.runs ?? 1} {(results.runs ?? configs.full?.runs ?? 1) === 1 ? "run" : "runs"} per page · {fmtWhen(results.updated_at)}</span>
        </div>
        <table className="eval mt-3">
          <thead><tr><th scope="col">System</th><th scope="col">Recall</th><th scope="col">Precision</th><th scope="col">Verified findings</th><th scope="col">False alarms on clean</th><th scope="col">Cost / 3 pages</th><th scope="col">Time / 3 pages</th></tr></thead>
          <tbody>
            {order.map((k) => {
              const t = configs[k].total;
              return (
                <tr key={k} data-config={k}>
                  <th scope="row">{CONFIG_LABELS[k] ?? k}</th>
                  <td>{pct(t.recall)}</td><td>{pct(t.precision)}</td><td>{Math.round(t.n)} per run · {t.n_labels} labels</td><td>{t.fp_on_clean.toFixed(1)}</td><td>{fmtCost(t.cost_usd)}</td><td>{fmtDuration(Math.round(t.seconds * 1000))}</td>
                </tr>
              );
            })}
            <tr data-config="axe">
              <th scope="row">axe-core 4.14</th>
              <td>{pct(results.axe?.recall ?? 0)}</td><td>—</td><td>{results.axe?.violations ?? 0} violations</td><td>—</td><td>$0</td><td>—</td>
            </tr>
          </tbody>
        </table>
        <p className="text-sm mt-2 mb-0 muted">Recall: the share of the seeded faults a run found. Precision: the share of a run's verified findings that landed on a seeded fault (a verified finding on a clean control, or on nothing labelled, counts against it).</p>
        {full && order.length > 1 && (
          <p className="text-sm mt-2 mb-0" role="note" aria-label="Ablation strip">
            Ablations: {order.filter((k) => k !== "full").map((k) => `${CONFIG_LABELS[k]} recall ${pct(configs[k].total.recall)}`).join(" · ")} — full Parity {pct(full.recall)}.{" "}
            {ablationSentence(order.filter((k) => k !== "full"), configs, full.recall)}
          </p>
        )}
      </section>
      {results.external ? (
        <section className="surface p-4" aria-labelledby="eval-external-h">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 id="eval-external-h" className="m-0" style={{ fontSize: 16 }}>External pages (W3C BAD), labels we did not write</h2>
            <MetaBadge model={results.external.model ?? model} capability="seer · comparator" />
            <CodeBadge what="code · verifier" />
            <span className="muted text-xs ml-auto">8 pages on www.w3.org, read-only · {results.external.runs} {results.external.runs === 1 ? "run" : "runs"} per page</span>
          </div>
          <table className="eval mt-3">
            <thead><tr><th scope="col">System</th><th scope="col">In-scope recall</th><th scope="col">Beyond axe-core</th><th scope="col">Precision</th><th scope="col">Verified findings</th><th scope="col">On repaired pages</th><th scope="col">On out-of-scope barriers</th><th scope="col">Cost / 8 pages</th><th scope="col">Time / 8 pages</th></tr></thead>
            <tbody>
              <tr data-config="external-full">
                <th scope="row">Parity (full)</th>
                <td>{pct(results.external.in_scope_recall)}</td><td>{pct(results.external.recall_beyond_axe)}</td><td>{pct(results.external.precision)}</td><td>{Math.round(results.external.n)} per run · {results.external.n_in_scope} in-scope labels</td>
                <td>{results.external.fp_on_after_pages.toFixed(1)}</td><td>{results.external.out_of_scope_hits.toFixed(1)}</td><td>{fmtCost(results.external.cost_usd)}</td><td>{fmtDuration(Math.round(results.external.seconds * 1000))}</td>
              </tr>
              <tr data-config="external-axe">
                <th scope="row">axe-core 4.14</th>
                <td>{pct(results.external.axe_recall)}</td><td>—</td><td>—</td><td>{results.external.axe?.violations ?? 0} violations</td><td>—</td><td>{(results.external.axe?.out_of_scope ?? []).length}</td><td>$0</td><td>—</td>
              </tr>
            </tbody>
          </table>
          <p className="text-sm mt-2 mb-0 muted" role="note" aria-label="External scope note">
            Subset stated: {results.external.n_in_scope} of W3C's {results.external.n_in_scope + results.external.out_of_scope_count} numbered barriers on the four "before" pages are in Parity's scope by kind
            (text alternatives, names, link text, unlabelled controls); the other {results.external.out_of_scope_count} (structure, presentation, keyboard) are counted, never claimed.
            Precision counts a finding on an in-scope barrier as right and every finding on a repaired "after" page as wrong; findings on elements W3C did not annotate
            ({results.external.unlabelled_on_before.toFixed(1)} per run) are reported, not scored.
            {results.external.n_beyond_axe !== undefined && (
              <> The Verifier drops what axe-core already reports, by design: {results.external.n_beyond_axe} of the {results.external.n_in_scope} in-scope barriers are ones axe-core does not report, and "Beyond axe-core" is Parity's recall on those; together they reach {pct(results.external.union_recall)}.</>
            )} {results.external.attribution ?? "W3C WAI Before and After Demonstration, W3C Document License; audited read-only"}.
          </p>
        </section>
      ) : (
        <p className="muted text-sm m-0 px-1">External pages (W3C BAD): not run yet; no number is claimed.</p>
      )}
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
      {results.model_sweep && <ModelSweepSection sweep={results.model_sweep} />}
      <section className="surface p-4" aria-labelledby="eval-public-h">
        <h2 id="eval-public-h" className="m-0" style={{ fontSize: 16 }}>Real-world sample, read-only (Sites A and B anonymised; the W3C demo pages named)</h2>
        {(results.public ?? []).length === 0 ? (
          <p className="muted text-sm mb-0">No public-site runs recorded yet.</p>
        ) : (
          <ul className="m-0 mt-2 p-0" style={{ listStyle: "none" }}>
            {(results.public ?? []).map((s) => (
              <li key={s.run_id} className="flex items-center gap-3 py-1 text-sm">
                <span style={{ minWidth: 70 }}>{s.name}</span>
                <span className="muted">{s.pages} screen{s.pages === 1 ? "" : "s"} · {s.verified} verified · {s.rejected} rejected{s.status && s.status !== "done" && s.status !== "awaiting_review" ? ` · ${s.status}` : ""}</span>
                {s.note && <span className="text-xs muted">({s.note})</span>}
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
