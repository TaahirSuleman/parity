import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvalTab } from "./EvalTab";

const results = {
  updated_at: "2026-11-01T10:00:00Z", model: "muse-spark-1.3-contributor", judge_model: "muse-spark-1.3", n_faults: 37, n_clean: 20, runs: 3,
  configs: {
    full: { runs: 3, total: { recall: 0.81, precision: 0.93, fp_on_clean: 0.3, n: 31, n_labels: 37, cost_usd: 0.12, seconds: 160 } },
    screenshot_only: { runs: 3, total: { recall: 0.4, precision: 0.6, fp_on_clean: 1, n: 20, n_labels: 37, cost_usd: 0.1, seconds: 150 } },
    tree_only: { runs: 3, total: { recall: 0.3, precision: 0.7, fp_on_clean: 0, n: 15, n_labels: 37, cost_usd: 0.05, seconds: 90 } },
    no_grounding: { runs: 3, total: { recall: 0.6, precision: 0.8, fp_on_clean: 0.7, n: 26, n_labels: 37, cost_usd: 0.09, seconds: 140 } },
  },
  axe: { recall: 0, violations: 0 },
  judge: { "muse-spark-1.3": { agreement: 0.95, needs_review_rate: 0.03, cost_per_finding: 0.01, n: 31 }, "muse-wonder-1.0": { agreement: 0.97, needs_review_rate: 0.0, cost_per_finding: 0.04, n: 31 } },
  effort_sweep: { low: { recall: 0.7, precision: 0.9, cost_usd: 0.08, seconds: 100 }, medium: { recall: 0.81, precision: 0.93, cost_usd: 0.12, seconds: 160 }, high: { recall: 0.83, precision: 0.92, cost_usd: 0.2, seconds: 260 } },
  public: [{ name: "Site A", run_id: "public-a", pages: 2, verified: 3, rejected: 1 }, { name: "Site B", run_id: "public-b", pages: 7, verified: 0, rejected: 9, status: "failed", note: "the model API returned 400 on turn 8" }],
};

describe("EvalTab", () => {
  it("shows Parity vs axe-core, the ablation strip, the judge rows and the real-world sample with a Replay action", () => {
    const opened: string[] = [];
    render(<EvalTab results={results} onReplay={(id) => opened.push(id)} />);
    expect(screen.getByRole("heading", { name: /parity vs axe-core/i })).toBeInTheDocument();
    const full = screen.getByRole("row", { name: /parity \(full\)/i });
    expect(full).toHaveTextContent("81%");
    expect(full).toHaveTextContent("93%");
    expect(screen.getByRole("row", { name: /axe-core/i })).toHaveTextContent("0%");
    expect(screen.getByText(/37 seeded faults/)).toBeInTheDocument();
    expect(screen.getByText(/1 Nov 2026/)).toBeInTheDocument(); // a date a judge can read, not an ISO timestamp
    expect(screen.queryByText(/2026-11-01T10:00:00Z/)).toBeNull();
    expect(full).toHaveTextContent("31 per run · 37 labels"); // n is verified findings per run, not labels found
    for (const label of ["screenshot only", "tree only", "no grounding"]) expect(screen.getByText(label)).toBeInTheDocument();
    const strip = screen.getByLabelText("Ablation strip");
    expect(strip).toHaveTextContent("Lower recall than full Parity: screenshot only, tree only, no grounding.");
    expect(strip).not.toHaveTextContent(/verifier/i); // the Verifier is on in every configuration: the ablations say nothing about it
    expect(screen.getByRole("row", { name: /wonder/i })).toHaveTextContent("97%");
    fireEvent.click(screen.getByRole("button", { name: /replay site a/i }));
    expect(opened).toEqual(["public-a"]);
    expect(screen.getByText(/returned 400 on turn 8/)).toBeInTheDocument();
    expect(screen.getByText(/7 screens · 0 verified · 9 rejected · failed/)).toBeInTheDocument();
    expect(screen.getAllByText(/MUSE SPARK/).length).toBeGreaterThan(0); // every number is attributed to its Meta model
    expect(screen.queryByText(/complian/i)).toBeNull();
  });

  it("carries a ten-second architecture card and says what recall and precision mean", () => {
    render(<EvalTab results={results} onReplay={() => {}} />);
    expect(screen.getByRole("img", { name: /pipeline/i })).toHaveAttribute("src", "/architecture.png");
    expect(screen.getByText(/Recall: the share of/)).toBeInTheDocument();
    expect(screen.getByText(/Precision: the share of/)).toBeInTheDocument();
  });

  it("reads the ablation sentence from the numbers, not from a script", () => {
    const flat = { ...results, configs: { ...results.configs, no_grounding: { runs: 3, total: { ...results.configs.no_grounding.total, recall: 0.81 } } } };
    render(<EvalTab results={flat} onReplay={() => {}} />);
    const strip = screen.getByLabelText("Ablation strip");
    expect(strip).toHaveTextContent("Lower recall than full Parity: screenshot only, tree only. Not lower: no grounding.");
  });

  it("says so when there are no results yet", () => {
    render(<EvalTab results={null} onReplay={() => {}} />);
    expect(screen.getByText(/no eval results/i)).toBeInTheDocument();
  });
});

describe("EvalTab wording for a newcomer (cold-judge review, 2 Nov)", () => {
  it("says the seeded faults were built to pass axe-core and names the columns plainly", () => {
    render(<EvalTab results={results} onReplay={() => {}} />);
    expect(screen.getByText(/seeded faults built to pass axe-core/)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "False alarms on clean" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Cost \/ 3 pages/ })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Time \/ 3 pages/ })).toBeInTheDocument();
    expect(screen.getByText(/a patch is exported only after a human approves/)).toBeInTheDocument();
  });
});

describe("EvalTab external pages (W3C BAD, Phase 6b)", () => {
  const external = {
    model: "muse-spark-1.3-contributor", runs: 2, n_in_scope: 14, out_of_scope_count: 21, n_clean: 35,
    in_scope_recall: 0.5, precision: 0.8, n: 20, fp_on_after_pages: 1.5, out_of_scope_hits: 2, unlabelled_on_before: 6,
    axe_recall: 0.21, axe: { violations: 40, out_of_scope: ["home-09"] }, cost_usd: 1.4, seconds: 900,
    recall_beyond_axe: 0.45, union_recall: 0.64, n_beyond_axe: 11,
    attribution: "W3C WAI Before and After Demonstration, Copyright © 2012 W3C® (MIT, ERCIM, Keio), W3C Document License; audited read-only",
  };

  it("renders the external row with its subset note", () => {
    render(<EvalTab results={{ ...results, external }} onReplay={() => {}} />);
    const section = screen.getByRole("region", { name: /external pages \(W3C BAD\)/i });
    const full = within(section).getByRole("row", { name: /parity \(full\)/i });
    expect(full).toHaveTextContent("50%");
    expect(full).toHaveTextContent("80%");
    expect(full).toHaveTextContent("20 per run");
    expect(within(section).getByRole("row", { name: /^axe-core 4\.14/i })).toHaveTextContent("21%");
    expect(within(section).getByRole("columnheader", { name: /beyond axe-core/i })).toBeInTheDocument();
    expect(full).toHaveTextContent("45%");
    const note = screen.getByLabelText("External scope note");
    expect(note).toHaveTextContent(/11 of the 14 in-scope barriers are ones axe-core does not report/);
    expect(note).toHaveTextContent(/together they reach 64%/);
    expect(note).toHaveTextContent("14 of W3C's 35 numbered barriers");
    expect(note).toHaveTextContent(/counted, never claimed/);
    expect(note).toHaveTextContent(/W3C Document License/);
    expect(within(section).getByText(/2 runs per page/)).toBeInTheDocument();
    expect(within(section).getAllByText(/MUSE SPARK/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/complian/i)).toBeNull();
  });

  it("says 'not run' and claims nothing when the external block is absent", () => {
    render(<EvalTab results={results} onReplay={() => {}} />);
    expect(screen.getByText(/External pages \(W3C BAD\): not run yet/)).toBeInTheDocument();
    expect(screen.getAllByRole("row", { name: /parity \(full\)/i })).toHaveLength(1);
  });
});

describe("EvalTab public samples with the W3C demo pages (Task 26E.5)", () => {
  it("names the W3C pages among the read-only samples and no longer calls the whole list anonymised", () => {
    const results = { public: [
      { name: "Site A", run_id: "public-a", pages: 2, verified: 6, rejected: 0, status: "done" },
      { name: "W3C demo: home", run_id: "bad-home", pages: 1, verified: 3, rejected: 2, status: "done", note: "W3C's own demonstration page, named with its notice" },
    ] } as unknown as import("./EvalTab").EvalResults;
    render(<EvalTab results={results} onReplay={() => {}} />);
    expect(screen.getByRole("heading", { name: /Real-world sample/ })).toHaveTextContent(/Sites A and B anonymised; the W3C demo pages named/);
    expect(screen.getByRole("button", { name: "Replay W3C demo: home" })).toBeInTheDocument();
  });
});

describe("About & Evals: the tab's name and its order", () => {
  it("names the tab and opens with how Parity works, above the numbers", () => {
    render(<EvalTab results={results} onReplay={() => {}} />);
    expect(screen.getByRole("heading", { name: "About & Evals" })).toHaveAttribute("id", "eval-h");
    const ids = screen.getAllByRole("heading").map((h) => h.id);
    expect(ids.slice(0, 3)).toEqual(["eval-h", "eval-arch-h", "eval-main-h"]);
    const levels = screen.getAllByRole("heading").map((h) => h.tagName);
    expect(new Set(levels)).toEqual(new Set(["H2"]));
  });

  it("still says how Parity works when no results are published", () => {
    render(<EvalTab results={null} onReplay={() => {}} />);
    expect(screen.getByRole("heading", { name: "About & Evals" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /How Parity works/ })).toBeInTheDocument();
    expect(screen.getByText(/no eval results/i)).toBeInTheDocument();
  });
});

describe("EvalTab per-stage model sweep", () => {
  const detection = { model: "muse-spark-1.3-contributor", effort: "medium", runs: 3, is_default: true, recall: 0.85, precision: 0.99, f1: 0.91, fp_on_clean: 0, cost_default_judge_usd: 0.37, seconds: 495 };
  const model_sweep = {
    stages: {
      comparator: { rows: [detection, { ...detection, model: "muse-wonder-1.0", is_default: false, runs: 1, recall: 0.7, precision: 0.9, f1: 0.79, cost_default_judge_usd: 0.9 }, { ...detection, model: "muse-spark-1.1", is_default: false, runs: 1, unpriced: true }, { model: "muse-spark-1.2-contributor", effort: "medium", failed: "HTTP 400" }] },
      judge: { rows: [{ model: "muse-spark-1.3", effort: "medium", n: 33, is_default: true, agreement: 0.94, needs_review_rate: 0, cost_per_finding: 0.0108 }] },
      fixer: { rows: [{ model: "muse-spark-1.3-contributor", effort: "medium", n: 12, is_default: true, gap_closed_rate: 0.75, rejected: 1, cost_per_fix: 0.001 }] },
      navigator: { rows: [{ model: "muse-spark-1.3-contributor", effort: "low", runs: 2, is_default: true, screens: 4, turns: 9.5, refusals: 0, safety_checks: 1, cost_usd_stage: 0.02 }] },
    },
    best: {
      comparator: { stage: "comparator", model: "muse-spark-1.3-contributor", effort: "medium", reason: "today's default holds", margin: "+0 recall", clears_bar: false, runs: 3 },
      judge: { stage: "judge", model: "muse-spark-1.3", effort: "medium", reason: "the highest agreement", margin: "", clears_bar: false, runs: 1 },
    },
  };
  const swept = { ...results, model_sweep } as unknown as import("./EvalTab").EvalResults;

  it("renders a table per stage, marks the best row in words and discloses n", () => {
    render(<EvalTab results={swept} onReplay={() => {}} />);
    const section = screen.getByRole("region", { name: /model and effort, per stage/i });
    expect(within(section).getAllByRole("table")).toHaveLength(4);
    const comparator = within(section).getByRole("table", { name: /comparator/i });
    const best = within(comparator).getByRole("row", { name: /best.*muse-spark-1\.3-contributor/i });
    expect(within(best).getByText("85%")).toBeInTheDocument();
    expect(within(best).getByText("$0.37")).toBeInTheDocument();
    expect(within(best).getByText("n = 3")).toBeInTheDocument();
    expect(within(within(comparator).getByRole("row", { name: /muse-wonder-1\.0/ })).getByText("n = 1")).toBeInTheDocument();
    expect(within(section).getByText(/one run is a sample/i)).toBeInTheDocument();
    expect(within(section).getByText(/today's default holds/)).toBeInTheDocument();
  });

  it("says a price is unknown rather than $0, and shows a failed row as failed", () => {
    render(<EvalTab results={swept} onReplay={() => {}} />);
    const comparator = screen.getByRole("table", { name: /comparator/i });
    expect(within(within(comparator).getByRole("row", { name: /muse-spark-1\.1/ })).getByText("price unknown")).toBeInTheDocument();
    expect(within(within(comparator).getByRole("row", { name: /muse-spark-1\.2-contributor/ })).getByText(/failed: HTTP 400/)).toBeInTheDocument();
  });

  it("carries the SAM note when the block has one", () => {
    const withSam = { ...results, model_sweep: { ...model_sweep, sam_note: "replayed on box prompts" } } as unknown as import("./EvalTab").EvalResults;
    render(<EvalTab results={withSam} onReplay={() => {}} />);
    expect(screen.getByRole("note", { name: /SAM 3\.1 note/ })).toHaveTextContent(/replayed on box prompts/);
  });

  it("shows no sweep section when the block is absent", () => {
    render(<EvalTab results={results} onReplay={() => {}} />);
    expect(screen.queryByRole("region", { name: /model and effort, per stage/i })).toBeNull();
  });
});
