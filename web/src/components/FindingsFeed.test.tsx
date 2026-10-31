import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import hero from "../fixtures/hero.json";
import type { Finding, Rejected } from "../state/types";
import { FindingsFeed } from "./FindingsFeed";

const findings = hero.findings as unknown as Finding[];
const rejected: Rejected[] = [{
  id: "x-r01", run_id: "x", step_index: 0,
  candidate: { step_index: 0, sighted_text: "Delivery Free", sr_quote: "not announced", why_it_matters: "", bbox: null, attempt: 1 },
  verifier: { passed: false, checks: { located: { passed: false, detail: "no box" } }, feedback: "give the box" },
}];

describe("FindingsFeed without the Verifier", () => {
  it("shows what the run would have reported with the gate off, and marks the false ones", () => {
    render(<FindingsFeed findings={findings} rejected={rejected} selectedId={null} phase="finished" error={null} onSelect={() => {}} />);
    const toggle = screen.getByRole("switch", { name: /without the verifier/i });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText(/would report 7 findings/i)).toBeInTheDocument();
    expect(screen.getByText(/1 of them failed a verifier check/i)).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: /would be reported: Delivery Free/i })).toBeInTheDocument();
  });
});
