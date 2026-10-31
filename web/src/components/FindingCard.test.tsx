import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import hero from "../fixtures/hero.json";
import type { Finding } from "../state/types";
import { FindingCard } from "./FindingCard";

const finding = hero.findings.find((f) => f.element.dom_id === "f5") as unknown as Finding;

describe("FindingCard", () => {
  it("shows the sighted text, the exact screen-reader quote, five green ticks and the model badge", () => {
    render(<FindingCard finding={finding} selected={true} onSelect={() => {}} />);
    expect(screen.getByText("Pay R1,249")).toBeInTheDocument();
    expect(screen.getByText('button, "Submit"')).toBeInTheDocument();
    const ticks = screen.getAllByRole("listitem", { name: /passed/i });
    expect(ticks).toHaveLength(5);
    expect(screen.getAllByText(/MUSE SPARK 1\.3/)[0]).toBeInTheDocument();
    expect(screen.getByText(/2\.5\.3/)).toBeInTheDocument();
    expect(screen.getByText(/serious/i)).toBeInTheDocument();
  });

  it("marks the card selected for assistive tech", () => {
    render(<FindingCard finding={finding} selected={true} onSelect={() => {}} />);
    expect(screen.getByRole("button", { name: /Pay R1,249/ })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("FindingCard verdicts and badges", () => {
  it("surfaces a 'not a barrier' verdict for human review instead of hiding it as minor", () => {
    const dismissed = { ...finding, judgement: { ...finding.judgement!, is_barrier: false, severity: "minor" as const, wcag: [] } };
    render(<FindingCard finding={dismissed} selected={false} onSelect={() => {}} />);
    expect(screen.getByText("not a barrier · review")).toBeInTheDocument();
    expect(screen.getByText(/Judge: not a barrier in context/)).toBeInTheDocument();
    expect(screen.queryByText("minor")).not.toBeInTheDocument();
  });

  it("shows the model tier in the badge", () => {
    const contributor = { ...finding, judgement: { ...finding.judgement!, model_meta: { model: "muse-spark-1.3-contributor" } } };
    render(<FindingCard finding={contributor} selected={false} onSelect={() => {}} />);
    expect(screen.getAllByText(/CONTRIBUTOR/).length).toBeGreaterThan(0);
  });
});

describe("FindingCard fix and decision", () => {
  const fixed: Finding = {
    ...finding, status: "reaudited",
    fix: {
      before_html: '<button id="f5" aria-label="Submit"></button>', after_html: '<button id="f5" class="btn">Pay R1,249</button>',
      diff: '--- a/store/checkout.html\n+++ b/store/checkout.html\n@@ -31,1 +31,1 @@\n-      <button id="f5" aria-label="Submit">\n+      <button id="f5" class="btn">Pay R1,249</button>\n',
      explanation: "Real text instead of an image with a generic aria-label.", model_meta: { model: "muse-spark-1.3-contributor" },
    },
    reaudit: { gap_closed: true, sr_name_before: "Submit", sr_name_after: "Pay R1,249", comparator_still_flags: false },
  };

  it("shows the proposed fix as a diff with the fixer badge and the re-audit verdict", () => {
    render(<FindingCard finding={fixed} selected={false} onSelect={() => {}} />);
    expect(screen.getByText(/gap closed/)).toBeInTheDocument();
    expect(screen.getByText(/\+\s+<button id="f5" class="btn">Pay R1,249<\/button>/)).toBeInTheDocument();
    expect(screen.getByText(/Real text instead of an image/)).toBeInTheDocument();
    expect(screen.getByText(/fixer/i)).toBeInTheDocument();
  });

  it("records a reason with the decision: suggested from the re-audit, editable, required", () => {
    const seen: unknown[] = [];
    render(<FindingCard finding={fixed} selected={true} onSelect={() => {}} onDecision={(id, d, r) => seen.push([id, d, r])} />);
    const approve = screen.getByRole("button", { name: /approve fix/i });
    const reason = screen.getByLabelText(/reason/i) as HTMLInputElement;
    expect(reason.value).toMatch(/gap closed/i);
    expect(approve).toBeEnabled();
    fireEvent.change(reason, { target: { value: "   " } });
    expect(approve).toBeDisabled();
    expect(screen.getByRole("button", { name: /^reject/i })).toBeDisabled();
    fireEvent.change(reason, { target: { value: "Price is now announced" } });
    fireEvent.click(approve);
    expect(seen).toEqual([[fixed.id, "approve", "Price is now announced"]]);
  });

  it("explains why a finding has no fix when the fixer refused", () => {
    render(<FindingCard finding={{ ...finding, fix: null, reaudit: null, fix_note: "snippet changes the element's tag from <img> to <button>" }} selected={true} onSelect={() => {}} />);
    expect(screen.getByText(/no fix proposed/i)).toBeInTheDocument();
  });

  it("shows a recorded decision and no further decision controls", () => {
    const decided: Finding = { ...fixed, status: "approved", decision: { decision: "approve", reason: "ok", decided_at: "2026-10-31T00:00:00Z" } };
    render(<FindingCard finding={decided} selected={true} onSelect={() => {}} onDecision={() => {}} />);
    expect(screen.getByText(/Approved · ok/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve fix/i })).toBeNull();
  });
});
