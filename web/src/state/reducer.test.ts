import { describe, expect, it } from "vitest";
import hero from "../fixtures/hero.json";
import { initialState, reduce, select } from "./reducer";
import type { ParityEvent, RunState } from "./types";

const events = hero.events as unknown as ParityEvent[];
const play = (evs: ParityEvent[], from: RunState = initialState) => evs.reduce(reduce, from);

describe("reduce", () => {
  it("verifier.result adds a finding when passed and a rejected row when not", () => {
    const started = play(events.filter((e) => e.type === "run.started"));
    const passed = events.find((e) => e.type === "verifier.result" && e.passed === true)!;
    const withFinding = reduce(started, passed);
    expect(withFinding.findings).toHaveLength(1);
    expect(withFinding.findings[0].sighted_text).toBe((passed.finding as { sighted_text: string }).sighted_text);
    expect(withFinding.run?.findings_verified).toBe(1);

    const rejectedEvent: ParityEvent = {
      type: "verifier.result", run_id: started.run!.id, at: "2026-10-31T00:00:00Z", passed: false, rejected_id: `${started.run!.id}-r01`, index: 0, attempt: 1,
      candidate: { step_index: 0, sighted_text: "Terms", sr_quote: 'link, "Terms"', why_it_matters: "", bbox: null, attempt: 1 },
      checks: { located: { passed: false, detail: "no box given" } }, feedback: "give the box",
    };
    const withRejected = reduce(withFinding, rejectedEvent);
    expect(withRejected.rejected).toHaveLength(1);
    expect(withRejected.rejected[0].verifier.checks.located.passed).toBe(false);
    expect(withRejected.run?.findings_rejected).toBe(1);
  });

  it("model.call accumulates tokens and cost and records the stage", () => {
    const state = play(events.filter((e) => e.type === "run.started" || e.type === "model.call"));
    const calls = events.filter((e) => e.type === "model.call");
    expect(state.calls).toHaveLength(calls.length);
    const tokens = calls.reduce((s, e) => s + (e.tokens as number), 0);
    expect(state.run?.tokens).toBe(tokens);
    expect(state.run?.cost_usd).toBeCloseTo(calls.reduce((s, e) => s + (e.cost_usd as number), 0), 8);
    expect(state.stage).toBe(calls[calls.length - 1].stage);
  });

  it("run.finished sets the status, phase and counters; judge.result attaches the judgement", () => {
    const state = play(events);
    expect(state.phase).toBe("finished");
    expect(state.run?.status).toBe("done");
    expect(state.run?.findings_verified).toBe(hero.run.findings_verified);
    expect(state.run?.axe_violations).toBe(0);
    const hero5 = state.findings.find((f) => f.element.dom_id === "f5")!;
    expect(hero5.judgement?.wcag.map((w) => w.sc)).toContain("2.5.3");
    expect(hero5.status).toBe("judged");
    expect(state.steps[0].screenshot).toBe("steps/0/screenshot.png");
  });

  it("run.failed records the error and select picks a finding", () => {
    const started = play(events.filter((e) => e.type === "run.started"));
    const failed = reduce(started, { type: "run.failed", run_id: started.run!.id, at: "2026-10-31T00:00:00Z", error: "Meta API error 500" });
    expect(failed.phase).toBe("failed");
    expect(failed.error).toContain("500");
    const done = play(events);
    expect(select(done, done.findings[2].id).selectedFindingId).toBe(done.findings[2].id);
  });
});
