import { describe, expect, it } from "vitest";
import hero from "../fixtures/hero.json";
import { initialState, pickHero, reduce, select, shouldReset } from "./reducer";
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
    expect(state.run?.status).toBe("awaiting_review")  // the hero run proposes a fix, so a human must decide;
    expect(state.run?.findings_verified).toBe(hero.run.findings_verified);
    expect(state.run?.axe_violations).toBe(0);
    const hero5 = state.findings.find((f) => f.element.dom_id === "f5")!;
    expect(hero5.judgement?.wcag.map((w) => w.sc)).toContain("2.5.3");
    expect(hero5.status).toBe("reaudited")  // judged, then fixed and re-audited in the hero run;
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

describe("agent timeline", () => {
  it("records nav.actions, agent.tool_call and agent.refused as timeline rows and switches the stage", () => {
    const started = play(events.filter((e) => e.type === "run.started"));
    const at = "2026-10-31T00:00:00Z";
    const s1 = reduce(started, { type: "agent.tool_call", run_id: started.run!.id, at, turn: 1, tool: "audit_view", args: { reason: "product page" }, result: { verified: [], rejected: 0 } });
    const s2 = reduce(s1, { type: "nav.actions", run_id: started.run!.id, at, turn: 2, actions: ["click"], n: 1 });
    const s3 = reduce(s2, { type: "agent.refused", run_id: started.run!.id, at, turn: 3, tool: "finish", args: {}, feedback: "call audit_view first" });
    expect(s3.timeline.map((r) => r.kind)).toEqual(["tool_call", "actions", "refused"]);
    expect(s3.timeline[0].label).toContain("audit_view");
    expect(s3.timeline[1].label).toContain("click");
    expect(s3.timeline[2].label).toContain("audit_view first");
    expect(s2.stage).toBe("navigator");
    expect(s3.timeline[2].turn).toBe(3);
  });
});

describe("agent outcome", () => {
  it("keeps the agent summary from run.finished and notes a forced finish", () => {
    const started = play(events.filter((e) => e.type === "run.started"));
    const done = reduce(started, { type: "run.finished", run_id: started.run!.id, at: "2026-10-31T00:00:10Z", status: "done", agent: { turns: 9, finished: true, finish_forced: true, summary: "Order confirmed" } });
    expect(done.agent?.turns).toBe(9);
    expect(done.agent?.finish_forced).toBe(true);
    expect(done.timeline[done.timeline.length - 1].label).toMatch(/forced/i);
  });
});

describe("the human gate", () => {
  const base = play(events.filter((e) => ["run.started", "step.captured", "verifier.result"].includes(e.type)));
  const fid = base.findings[0].id;
  const at = "2026-10-31T00:00:00Z";

  it("fixer.rejected and reaudit.failed leave notes on the finding instead of a fix", () => {
    let s = reduce(base, { type: "fixer.rejected", run_id: base.run!.id, at, finding_id: fid, reason: "snippet changes the element's tag" });
    expect(s.findings[0].fix_note).toMatch(/changes the element/);
    expect(s.findings[0].fix).toBeFalsy();
    s = reduce(s, { type: "reaudit.failed", run_id: base.run!.id, at, finding_id: fid, reason: "page closed" });
    expect(s.findings[0].reaudit_note).toMatch(/page closed/);
  });

  it("decision.recorded flips the finding and carries the run's status", () => {
    const s = reduce(base, { type: "decision.recorded", run_id: base.run!.id, at, finding_id: fid, status: "approved", run_status: "done",
      decision: { decision: "approve", reason: "ok", decided_at: at }, approved: 1, pending: 0 });
    expect(s.findings[0].status).toBe("approved");
    expect(s.findings[0].decision?.reason).toBe("ok");
    expect(s.run?.status).toBe("done");
  });
});

describe("pre-P4 QA: what the header and the selection show", () => {
  const finished = play(events);

  it("uses the recorded run time on run.finished, not the replay's wall clock", () => {
    const ev = events.find((e) => e.type === "run.finished")!;
    expect(ev.duration_ms).toBeGreaterThan(0);
    expect(finished.run?.duration_ms).toBe(ev.duration_ms);
  });

  it("selects the hero on finish: the strongest finding whose fix closed the gap", () => {
    const f = (id: string, severity: string, closed: boolean | null) => ({ id, judgement: { is_barrier: true, severity, wcag: [], impact: "", model_meta: {} },
      reaudit: closed === null ? null : { gap_closed: closed, sr_name_before: "", sr_name_after: "", comparator_still_flags: false } }) as unknown as import("./types").Finding;
    expect(pickHero([f("a", "moderate", true), f("b", "critical", false), f("c", "serious", true)])?.id).toBe("c");
    expect(pickHero([f("a", "moderate", null), f("b", "critical", null)])?.id).toBe("b");
    expect(finished.selectedFindingId).toBe(pickHero(finished.findings)?.id);
  });

  it("does not reset the workbench when the pressed mode is clicked again or a run is going", () => {
    expect(shouldReset({ ...initialState, mode: "replay", phase: "idle" }, "replay")).toBe(false);
    expect(shouldReset({ ...initialState, mode: "replay", phase: "running" }, "live")).toBe(false);
    expect(shouldReset({ ...initialState, mode: "replay", phase: "finished" }, "live")).toBe(true);
  });
});


describe("safety checks on the timeline", () => {
  it("records an acknowledged routine check as a timeline row", () => {
    const s = reduce(play(events.filter((e) => e.type === "run.started")), { type: "nav.safety_check", run_id: "r", at: "2026-10-31T00:00:00Z", turn: 2, codes: ["computer_action_requires_confirmation"], acknowledged: true });
    expect(s.timeline.at(-1)?.label).toMatch(/safety check acknowledged.*computer_action_requires_confirmation/);
  });
});
