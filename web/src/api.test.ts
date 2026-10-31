import { describe, expect, it } from "vitest";
import { EVENT_TYPES } from "./api";

describe("EVENT_TYPES", () => {
  it("subscribes to every event the reducer and the timeline handle", () => {
    for (const t of ["run.started", "nav.actions", "nav.blocked", "nav.safety_check", "agent.tool_call", "agent.refused", "agent.tool_error", "step.captured", "seer.done",
      "comparator.candidates", "verifier.result", "judge.result", "fixer.proposed", "fixer.rejected", "reaudit.result", "reaudit.failed",
      "model.call", "decision.recorded", "run.finished", "run.failed"]) {
      expect(EVENT_TYPES, t).toContain(t);
    }
  });
});
