import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TraceDrawer } from "./TraceDrawer";

describe("TraceDrawer", () => {
  it("keeps the full request id in the document, not only in a hover title", () => {
    const calls = [{ stage: "comparator", model: "muse-spark-1.3-contributor", request_id: "a05f175c-2d4e-4a1e-9d2f-0123456789ab", tokens: 5133, latency_ms: 18018, cost_usd: 0.0091, cache_hit: false, attempt: 1, at: "2026-11-01T12:00:00Z" }];
    render(<TraceDrawer calls={calls} open={true} onToggle={() => {}} />);
    expect(screen.getByText("a05f175c-2d4e-4a1e-9d2f-0123456789ab")).toBeInTheDocument();
  });
});
