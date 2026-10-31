import { fireEvent, render, screen } from "@testing-library/react";
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
    for (const label of ["screenshot only", "tree only", "no grounding"]) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /wonder/i })).toHaveTextContent("97%");
    fireEvent.click(screen.getByRole("button", { name: /replay site a/i }));
    expect(opened).toEqual(["public-a"]);
    expect(screen.getByText(/returned 400 on turn 8/)).toBeInTheDocument();
    expect(screen.getByText(/7 screens · 0 verified · 9 rejected · failed/)).toBeInTheDocument();
    expect(screen.getAllByText(/MUSE SPARK/).length).toBeGreaterThan(0); // every number is attributed to its Meta model
    expect(screen.queryByText(/complian/i)).toBeNull();
  });

  it("says so when there are no results yet", () => {
    render(<EvalTab results={null} onReplay={() => {}} />);
    expect(screen.getByText(/no eval results/i)).toBeInTheDocument();
  });
});
