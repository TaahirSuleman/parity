import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Header } from "./Header";

const flows = [
  { id: "checkout", name: "Checkout page", start_url: "/store/checkout.html", goal: "Pay", pages: ["checkout.html"], single_page: true },
  { id: "purchase", name: "Purchase flow", start_url: "/store/product.html", goal: "Buy", pages: ["product.html", "cart.html", "checkout.html", "confirm.html"], single_page: false },
];

describe("Header flow picker", () => {
  it("lets the user pick the flow and reports the choice", () => {
    const onFlowChange = vi.fn();
    render(<Header flows={flows} flowId="purchase" run={null} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} onFlowChange={onFlowChange} />);
    const select = screen.getByRole("combobox", { name: /flow/i });
    expect(select).toHaveValue("purchase");
    fireEvent.change(select, { target: { value: "checkout" } });
    expect(onFlowChange).toHaveBeenCalledWith("checkout");
  });
});

describe("Header review state", () => {
  it("shows awaiting review with the approved and pending counts", () => {
    const run = { id: "r1", mode: "replay" as const, flow_id: "checkout", goal: "", target_url: "", status: "awaiting_review" as const, started_at: "2026-10-31T00:00:00Z",
      axe_violations: 0, findings_verified: 3, findings_rejected: 1, tokens: 0, cost_usd: 0, duration_ms: 0 };
    render(<Header flows={[{ id: "checkout", name: "Checkout", single_page: true }]} flowId="checkout" onFlowChange={() => {}} run={run} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} approved={1} pending={2} />);
    expect(screen.getByText(/awaiting review/i)).toBeInTheDocument();
    expect(screen.getByText(/1 approved · 2 to review/)).toBeInTheDocument();
  });
});

describe("Header patch export", () => {
  const run = { id: "r7", mode: "replay" as const, flow_id: "checkout", goal: "", target_url: "", status: "done" as const, started_at: "2026-10-31T00:00:00Z",
    axe_violations: 0, findings_verified: 3, findings_rejected: 1, tokens: 0, cost_usd: 0, duration_ms: 0 };
  const props = { flows: [{ id: "checkout", name: "Checkout", single_page: true }], flowId: "checkout", onFlowChange: () => {}, mode: "replay" as const, canLive: false, running: false, onModeChange: () => {}, onRun: () => {} };

  it("offers the fix.patch download once a fix is approved", () => {
    render(<Header {...props} run={run} approved={1} pending={0} />);
    const link = screen.getByRole("link", { name: /download fix\.patch/i });
    expect(link).toHaveAttribute("href", "/api/runs/r7/patch");
  });

  it("offers no download before any approval", () => {
    render(<Header {...props} run={run} approved={0} pending={2} />);
    expect(screen.queryByRole("link", { name: /download fix\.patch/i })).toBeNull();
  });
});

describe("Header durations", () => {
  it("formats minutes and marks a replay's time as recorded", async () => {
    const { fmtDuration } = await import("./Header");
    expect(fmtDuration(574713)).toBe("9 m 35 s");
    expect(fmtDuration(101000)).toBe("1 m 41 s");
    expect(fmtDuration(32000)).toBe("32 s");
    const run = { id: "r1", mode: "replay" as const, flow_id: "purchase", goal: "", target_url: "", status: "awaiting_review" as const, started_at: "2026-10-31T00:00:00Z",
      axe_violations: 0, findings_verified: 12, findings_rejected: 5, tokens: 0, cost_usd: 0.14, duration_ms: 574713 };
    render(<Header flows={[{ id: "purchase", name: "Purchase", single_page: false }]} flowId="purchase" onFlowChange={() => {}} run={run} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByText(/recorded 9 m 35 s/)).toBeInTheDocument();
  });
});
