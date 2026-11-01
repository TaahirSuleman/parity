import { describe, expect, it } from "vitest";
import { ApiError } from "../api";
import { reconcileDecisions, submitDecision } from "./decisions";
import type { Finding, ParityEvent, Run } from "./types";

const run = { id: "r1", status: "awaiting_review" } as Run;
const decided = { id: "f1", status: "approved", decision: { decision: "approve", reason: "ok", decided_at: "2026-10-31T00:00:00Z" } } as unknown as Finding;

describe("submitDecision", () => {
  it("applies the route's response as a decision.recorded event (the stream is closed by then)", async () => {
    const events: ParityEvent[] = [];
    const errors: string[] = [];
    await submitDecision({
      decide: async () => ({ finding: decided, run: { ...run, status: "done" } }), getRun: async () => { throw new Error("not needed"); },
    }, "r1", "f1", "approve", "ok", (ev) => events.push(ev), (m) => errors.push(m));
    expect(errors).toEqual([]);
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ type: "decision.recorded", run_id: "r1", finding_id: "f1", status: "approved", run_status: "done" });
  });

  it("treats 409 (already decided) as a refetch, not a failed run", async () => {
    const events: ParityEvent[] = [];
    const errors: string[] = [];
    await submitDecision({
      decide: async () => { throw new ApiError(409, "finding f1 was already approved"); },
      getRun: async () => ({ run: { ...run, status: "done" }, findings: [decided], steps: [], rejected: [], trace: [] }),
    }, "r1", "f1", "reject", "late", (ev) => events.push(ev), (m) => errors.push(m));
    expect(errors).toEqual([]);
    expect(events[0]).toMatchObject({ type: "decision.recorded", finding_id: "f1", status: "approved", run_status: "done" });
  });

  it("reports other failures as errors", async () => {
    const errors: string[] = [];
    await submitDecision({ decide: async () => { throw new ApiError(503, "down"); }, getRun: async () => { throw new Error("x"); } },
      "r1", "f1", "approve", "ok", () => {}, (m) => errors.push(m));
    expect(errors).toEqual(["down"]);
  });
});

describe("reconcileDecisions", () => {
  it("applies the decisions the server holds for a run (made after the stream closed, or before a reload)", async () => {
    const events: ParityEvent[] = [];
    const undecided = { id: "f2", status: "reaudited", decision: null } as unknown as Finding;
    await reconcileDecisions({ getRun: async () => ({ run: { ...run, status: "done" }, findings: [decided, undecided], steps: [], rejected: [], trace: [] }) }, "r1", (ev) => events.push(ev));
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ type: "decision.recorded", finding_id: "f1", status: "approved", run_status: "done" });
  });

  it("is quiet when the run cannot be fetched", async () => {
    const events: ParityEvent[] = [];
    await reconcileDecisions({ getRun: async () => { throw new ApiError(503, "down"); } }, "r1", (ev) => events.push(ev));
    expect(events).toEqual([]);
  });
});

describe("submitDecision conflicts (stress pass)", () => {
  it("tells the user when another viewer decided first, instead of silently showing that decision as theirs", async () => {
    const notices: string[] = [];
    await submitDecision({
      decide: async () => { throw new ApiError(409, "finding f1 was already approved"); },
      getRun: async () => ({ run, findings: [decided], steps: [], rejected: [], trace: [] }),
    }, "r1", "f1", "reject", "late", () => {}, () => {}, (m) => notices.push(m));
    expect(notices).toHaveLength(1);
    expect(notices[0]).toMatch(/another viewer/i);
    expect(notices[0]).toMatch(/approved/i);
  });
});
