import { render, screen } from "@testing-library/react";
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
    expect(screen.getByText(/MUSE SPARK 1\.3/)).toBeInTheDocument();
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
    expect(screen.getByText(/CONTRIBUTOR/)).toBeInTheDocument();
  });
});
