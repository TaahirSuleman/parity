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

describe("Task 24: the idle state frames the product", () => {
  it("says what Parity is and that Replay is a recorded run with no model calls", () => {
    render(<FindingsFeed findings={[]} rejected={[]} selectedId={null} phase="idle" error={null} onSelect={() => {}} flowName="Checkout page" />);
    const framing = screen.getByText(/Run the audit to start/); // a plain paragraph since the VoiceOver pass: a flow change must not re-read it
    expect(framing).toHaveTextContent(/sighted .* screen-reader/i);
    expect(framing).toHaveTextContent(/Replay.*recorded run.*no model calls/i);
  });

  it("is one sentence of at most 40 words: VoiceOver reads it on load and the user asked for a short one (docs/24 Question A)", () => {
    render(<FindingsFeed findings={[]} rejected={[]} selectedId={null} phase="idle" error={null} onSelect={() => {}} flowName="Checkout page" />);
    const text = screen.getByText(/Run the audit to start/).textContent ?? "";
    expect(text.trim().split(/\s+/).length).toBeLessThanOrEqual(40);
    expect(text.trim().match(/[.!?](\s|$)/g)?.length ?? 0).toBe(1);
  });
});

describe("FindingsFeed notices (stress pass)", () => {
  it("scrolls a new notice into view: on a phone the feed sits below the screenshot and a 429 was out of sight", async () => {
    const { FindingsFeed } = await import("./FindingsFeed");
    const { render } = await import("@testing-library/react");
    const { vi } = await import("vitest");
    const spy = vi.fn();
    Element.prototype.scrollIntoView = spy;
    render(<FindingsFeed findings={[]} rejected={[]} selectedId={null} phase="idle" error={null} onSelect={() => {}} notice="Live is busy or rate-limited: try again in 30 min." />);
    expect(spy).toHaveBeenCalled();
  });
});

describe("live regions after the VoiceOver pass (docs/24 1.1, 10.1)", () => {
  it("keeps the idle framing out of the live region so changing the flow does not re-read it, while the running message stays live", () => {
    const idle = render(<FindingsFeed findings={[]} rejected={[]} selectedId={null} phase="idle" error={null} onSelect={() => {}} flowName="Checkout page" />);
    expect(screen.getByText(/Run the audit to start/)).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
    idle.unmount();
    render(<FindingsFeed findings={[]} rejected={[]} selectedId={null} phase="running" error={null} onSelect={() => {}} flowName="Checkout page" />);
    expect(screen.getByRole("status")).toHaveTextContent(/Capturing the page/);
  });
});
