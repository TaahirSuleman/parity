import { describe, expect, it } from "vitest";
import { EVENT_TYPES } from "./api";

describe("EVENT_TYPES", () => {
  it("subscribes to every event the reducer and the timeline handle", () => {
    for (const t of ["run.started", "nav.actions", "nav.blocked", "nav.safety_check", "agent.tool_call", "agent.refused", "agent.tool_error", "step.captured", "seer.done",
      "comparator.candidates", "comparator.unparseable", "verifier.result", "judge.result", "fixer.proposed", "fixer.rejected", "reaudit.result", "reaudit.failed",
      "model.call", "decision.recorded", "run.finished", "run.failed"]) {
      expect(EVENT_TYPES, t).toContain(t);
    }
  });
});

describe("ApiError detail (QA gate before the 6c merge)", () => {
  it("joins a validation body's messages instead of printing [object Object]", async () => {
    const { startUrlRun, ApiError } = await import("./api");
    globalThis.fetch = (() => Promise.resolve(new Response(JSON.stringify({ detail: [{ loc: ["body", "url"], msg: "String should have at most 2048 characters", type: "string_too_long" }] }), { status: 422, headers: { "Content-Type": "application/json" } }))) as unknown as typeof fetch;
    const err = await startUrlRun({ url: "https://a.example/", screens: 1, consent: true, hint: "" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as InstanceType<typeof ApiError>).detail).toBe("String should have at most 2048 characters");
  });
});
