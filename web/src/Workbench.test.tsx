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
