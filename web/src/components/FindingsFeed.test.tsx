import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import hero from "../fixtures/hero.json";
import type { Finding, Rejected } from "../state/types";
import { FindingsFeed } from "./FindingsFeed";

const findings = hero.findings as unknown as Finding[];
const rejected: Rejected[] = [{
  id: "x-r01", run_id: "x", step_index: 0,
  candidate: { step_index: 0, sighted_text: "Delivery Free", sr_quote: "not announced", why_it_matters: "", bbox: null, attempt: 1 },
  verifier: { passed: false, checks: { located: { passed: false, detail: "no box" } }, feedback: "give the box" },
}, {
  id: "x-r02", run_id: "x", step_index: 0,
  candidate: { step_index: 0, sighted_text: "Pay R1,249", sr_quote: 'button, "Submit"', why_it_matters: "", bbox: null, attempt: 2 },
  verifier: { passed: false, checks: { located: { passed: true, detail: "" }, unique: { passed: false, detail: "already reported" } }, feedback: "do not repeat" },
}];

describe("FindingsFeed without the Verifier", () => {
  it("shows what the run would have reported with the gate off, and marks the false ones", () => {
    render(<FindingsFeed findings={findings} rejected={rejected} selectedId={null} phase="finished" error={null} onSelect={() => {}} />);
    const toggle = screen.getByRole("switch", { name: /without the verifier/i });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText(/would report 8 findings/i)).toBeInTheDocument();
    expect(screen.getByText(/1 false report/i)).toBeInTheDocument();
    expect(screen.getByText(/1 duplicate/i)).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: /would be reported: Delivery Free/i })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: /duplicate: Pay R1,249/i })).toBeInTheDocument();
  });
});

describe("FindingsFeed selection, notices and outcomes", () => {
  it("scrolls the selected card into view when the selection changes", () => {
    const spy = vi.fn();
    Element.prototype.scrollIntoView = spy;
    const { rerender } = render(<FindingsFeed findings={findings} rejected={[]} selectedId={null} phase="finished" error={null} onSelect={() => {}} />);
    rerender(<FindingsFeed findings={findings} rejected={[]} selectedId={findings[2].id} phase="finished" error={null} onSelect={() => {}} />);
    expect(spy).toHaveBeenCalled();
  });

  it("shows a notice at the top as an alert instead of failing the run", () => {
    render(<FindingsFeed findings={findings} rejected={[]} selectedId={null} phase="finished" error={null} notice="The decision could not be saved: network error. Try again." onSelect={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/could not be saved/);
  });

  it("explains a walk the site stopped instead of saying no divergences were found", () => {
    render(<FindingsFeed findings={[]} rejected={[]} selectedId={null} phase="finished" error={null} outcome="blocked by site: bot challenge" onSelect={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent(/stopped the walk before any screen was audited/i);
    expect(screen.queryByText(/no divergences passed/i)).toBeNull();
  });
});
