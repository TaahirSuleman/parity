import { fireEvent, render, screen } from "@testing-library/react";
import { act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Header, fmtDuration } from "./Header";

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

describe("Header time readout", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("counts elapsed time while the run is in progress instead of showing 0 ms", () => {
    vi.setSystemTime(new Date("2026-11-01T12:00:30Z"));
    const run = { id: "r1", mode: "live" as const, flow_id: "checkout", goal: "", target_url: "", status: "running" as const, started_at: "2026-11-01T12:00:00Z",
      axe_violations: 0, findings_verified: 0, findings_rejected: 0, tokens: 0, cost_usd: 0, duration_ms: 0 };
    render(<Header flows={[{ id: "checkout", name: "Checkout", single_page: true }]} flowId="checkout" onFlowChange={() => {}} run={run} mode="live" canLive={true} running={true} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByTitle(/model cost and wall time/i)).toHaveTextContent("30 s");
    act(() => { vi.advanceTimersByTime(5000); });
    expect(screen.getByTitle(/model cost and wall time/i)).toHaveTextContent("35 s");
  });

  it("does not count the recorded run's age while a Replay plays (its events carry the recorded timestamps)", () => {
    vi.setSystemTime(new Date("2026-11-01T12:00:30Z"));
    const run = { id: "r1", mode: "replay" as const, flow_id: "checkout", goal: "", target_url: "", status: "running" as const, started_at: "2026-10-31T09:00:00Z",
      axe_violations: 0, findings_verified: 0, findings_rejected: 0, tokens: 0, cost_usd: 0, duration_ms: 0, replay_of: "hero-checkout" };
    render(<Header flows={[{ id: "checkout", name: "Checkout", single_page: true }]} flowId="checkout" onFlowChange={() => {}} run={run} mode="replay" canLive={false} running={true} onModeChange={() => {}} onRun={() => {}} />);
    const readout = screen.getByTitle(/model cost and wall time/i);
    expect(readout).toHaveTextContent(/replaying/i);
    expect(readout).not.toHaveTextContent(/\d+ m \d+ s/);
  });

  it("shows the recorded duration once the run has finished", () => {
    const run = { id: "r1", mode: "live" as const, flow_id: "checkout", goal: "", target_url: "", status: "done" as const, started_at: "2026-11-01T12:00:00Z",
      axe_violations: 0, findings_verified: 0, findings_rejected: 0, tokens: 0, cost_usd: 0, duration_ms: 153000 };
    render(<Header flows={[{ id: "checkout", name: "Checkout", single_page: true }]} flowId="checkout" onFlowChange={() => {}} run={run} mode="live" canLive={true} running={false} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByTitle(/model cost and wall time/i)).toHaveTextContent("2 m 33 s");
  });
});

describe("QA pass 2: header honesty", () => {
  const flowsMin = [{ id: "checkout", name: "Checkout", single_page: true }];
  it("keeps focus on Run the audit while a run is going: the button is aria-disabled, not removed from the tab ring", () => {
    const onRun = vi.fn();
    const run = { id: "r1", mode: "live" as const, flow_id: "checkout", goal: "", target_url: "", status: "running" as const, started_at: "2026-11-01T12:00:00Z", axe_violations: 0, findings_verified: 0, findings_rejected: 0, tokens: 0, cost_usd: 0, duration_ms: 0 };
    render(<Header flows={flowsMin} flowId="checkout" onFlowChange={() => {}} run={run} mode="live" canLive={true} running={true} onModeChange={() => {}} onRun={onRun} />);
    const btn = screen.getByRole("button", { name: /auditing/i });
    expect(btn).not.toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(btn);
    expect(onRun).not.toHaveBeenCalled();
  });

  it("names a public sample by its site and hides the store's flow picker", () => {
    const run = { id: "r1", mode: "replay" as const, flow_id: "public", goal: "Site A: Open the first book", target_url: "https://site-a.invalid/", status: "done" as const, started_at: "2026-11-01T12:00:00Z", axe_violations: 7, findings_verified: 6, findings_rejected: 0, tokens: 0, cost_usd: 0.11, duration_ms: 184000, replay_of: "public-a" };
    render(<Header flows={flowsMin} flowId="checkout" onFlowChange={() => {}} run={run} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByText(/Site A/)).toBeInTheDocument();
    expect(screen.queryByText(/ShopRight/)).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("shows dashes, not zeros, before anything has been measured", () => {
    render(<Header flows={flowsMin} flowId="checkout" onFlowChange={() => {}} run={null} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByTitle(/axe-core 4.14 violations/i)).toHaveTextContent("—");
    expect(screen.getByTitle(/model cost and wall time/i)).toHaveTextContent("—");
    expect(screen.queryByText("$0.0000")).toBeNull();
  });

  it("never prints 60 seconds", () => {
    expect(fmtDuration(119600)).toBe("2 m 0 s");
    expect(fmtDuration(153000)).toBe("2 m 33 s");
  });
});

describe("Task 24: a cold judge reads the header", () => {
  const flowsMin = [{ id: "checkout", name: "Checkout", single_page: true }];
  it("labels the modes: Replay is pressed by default and says it is a recorded run; Live says it is rate-limited", () => {
    render(<Header flows={flowsMin} flowId="checkout" onFlowChange={() => {}} run={null} mode="replay" canLive={true} running={false} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByRole("button", { name: /^Replay/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Live \(rate-limited\)/ })).toBeInTheDocument();
    expect(screen.getByText(/recorded run.*no model calls/i)).toBeInTheDocument();
  });
  it("says whose rejection the red count is", () => {
    const run = { id: "r1", mode: "replay" as const, flow_id: "checkout", goal: "", target_url: "", status: "done" as const, started_at: "2026-11-01T12:00:00Z", axe_violations: 0, findings_verified: 7, findings_rejected: 3, tokens: 0, cost_usd: 0.09, duration_ms: 282000 };
    render(<Header flows={flowsMin} flowId="checkout" onFlowChange={() => {}} run={run} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} />);
    expect(screen.getByTitle(/Findings that passed the Verifier/)).toHaveTextContent(/3.*rejected by the Verifier/);
  });
});
