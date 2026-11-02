import { describe, expect, it } from "vitest";
import checkout from "../../../fixtures/replay/runs/hero-checkout/events.jsonl?raw";
import purchase from "../../../fixtures/replay/runs/hero-purchase/events.jsonl?raw";
import { initialState, reduce } from "./reducer";
import type { ParityEvent } from "./types";

// The bundles judges actually replay. The workbench opens on the hero finding when a run ends: on both bundles that is
// "Pay R1,249" vs button "Submit" (doc 18 §3), whatever order the events arrive in and whichever screen it sits on.
// The event log stores {type, run_id, at, data}; the stream flattens it, which is what the reducer reads.
const play = (log: string) => {
  const flat = (l: string) => { const { type, run_id, at, data } = JSON.parse(l) as { type: string; run_id: string; at: string; data: Record<string, unknown> }; return { type, run_id, at, ...data } as ParityEvent; };
  return log.split("\n").filter(Boolean).map(flat).reduce(reduce, initialState);
};

describe("the committed bundles open on the hero", () => {
  for (const [name, log] of [["hero-checkout", checkout], ["hero-purchase", purchase]] as const) {
    it(`${name} selects "Pay R1,249" when the run ends`, () => {
      const state = play(log);
      expect(state.phase).toBe("finished");
      const picked = state.findings.find((f) => f.id === state.selectedFindingId);
      expect(picked?.sighted_text).toBe("Pay R1,249");
      expect(picked?.sr_name).toBe("Submit");
    });
  }
});
