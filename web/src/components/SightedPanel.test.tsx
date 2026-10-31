import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import hero from "../fixtures/hero.json";
import type { Finding, Step } from "../state/types";
import { SightedPanel } from "./SightedPanel";

const base = hero.findings[0] as unknown as Finding;
const onStep0 = { ...base, id: "s0", step_index: 0, sighted_text: "Heart icon" };
const onStep2 = { ...base, id: "s2", step_index: 2, sighted_text: "Pay R1,249" };
const steps = [0, 1, 2].map((i) => ({ run_id: "r", index: i, url: `/store/p${i}.html`, screenshot: "", ax_tree: "", axe: "", viewport: [1280, 720], axe_violations: 0, ax_nodes: 1, captured_at: "" })) as Step[];

describe("SightedPanel steps", () => {
  it("draws only the boxes of the step on screen and names the step strip", () => {
    const seen: number[] = [];
    render(<SightedPanel screenshotUrl="/shot2.png" findings={[onStep0, onStep2]} percepts={[]} selectedId="s2" stage={null} model="m" timeline={[]}
      steps={steps} stepIndex={2} onStepChange={(i) => seen.push(i)} onSelect={() => {}} />);
    expect(screen.getByRole("button", { name: /Pay R1,249/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Heart icon/ })).toBeNull();
    const strip = screen.getByRole("group", { name: /screens/i });
    const stepButtons = strip.querySelectorAll("button");
    expect(stepButtons).toHaveLength(3);
    expect(stepButtons[2]).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(stepButtons[0]);
    expect(seen).toEqual([0]);
  });
});

describe("SightedPanel withheld screenshot", () => {
  it("says the screenshot was withheld when the image cannot be loaded, instead of a broken image", () => {
    render(<SightedPanel screenshotUrl="/api/runs/r/steps/0/screenshot.png" findings={[]} percepts={[]} selectedId={null} stage={null} model="m" timeline={[]}
      steps={steps} stepIndex={0} onStepChange={() => {}} onSelect={() => {}} />);
    fireEvent.error(screen.getByRole("img", { name: /audited page/i }));
    expect(screen.getByText(/screenshot withheld/i)).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /audited page/i })).toBeNull();
  });
});
