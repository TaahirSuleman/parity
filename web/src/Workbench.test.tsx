import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { initialState } from "./state/reducer";
import type { RunState } from "./state/types";
import { Workbench } from "./Workbench";

const flows = [{ id: "checkout", name: "Checkout page", single_page: true }];
const running: RunState = { ...initialState, phase: "running", run: { id: "r1", mode: "replay", flow_id: "checkout", goal: "", target_url: "", status: "running", started_at: "2026-11-01T12:00:00Z", axe_violations: 0, findings_verified: 0, findings_rejected: 0, tokens: 0, cost_usd: 0, duration_ms: 0 } };

describe("Workbench announcements", () => {
  it("tells assistive tech that the audit has started, not only that it finished", () => {
    const { container } = render(<Workbench state={running} flows={flows} flowId="checkout" onFlowChange={() => {}} canLive={false} screenshotUrl={null} model="m" onModeChange={() => {}} onRun={() => {}} onSelect={() => {}} />);
    const live = container.querySelector("[aria-live=polite]");
    expect(live?.textContent).toMatch(/audit started/i);
  });
});

describe("Workbench (stress pass)", () => {
  it("counts approvals by the human's decision, announces a failure, and lets focus land on the main region", async () => {
    const hero = (await import("./fixtures/hero.json")).default as unknown as { events: import("./state/types").ParityEvent[] };
    const { reduce } = await import("./state/reducer");
    const finished = hero.events.reduce(reduce, initialState);
    const f = finished.findings.find((x) => x.fix)!;
    const state: RunState = { ...finished, findings: finished.findings.map((x) => (x.id === f.id ? { ...x, status: "reaudited", decision: { decision: "approve", reason: "ok", decided_at: "t" } } : x)) };
    const { container, unmount } = render(<Workbench state={state} flows={flows} flowId="checkout" onFlowChange={() => {}} canLive={false} screenshotUrl={null} model="m" onModeChange={() => {}} onRun={() => {}} onSelect={() => {}} />);
    expect(container.textContent).toMatch(/1 approved/);
    expect(container.querySelector("main")?.getAttribute("tabindex")).toBe("-1");
    unmount();
    const failed: RunState = { ...running, phase: "failed", error: "interrupted by restart", run: { ...running.run!, status: "failed" } };
    const second = render(<Workbench state={failed} flows={flows} flowId="checkout" onFlowChange={() => {}} canLive={false} screenshotUrl={null} model="m" onModeChange={() => {}} onRun={() => {}} onSelect={() => {}} />);
    expect(second.container.querySelector("[aria-live=polite]")?.textContent).toMatch(/audit failed/i);
  });
});
