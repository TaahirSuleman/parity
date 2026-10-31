import { useMemo, useState } from "react";
import checkout from "./fixtures/checkout.png";
import hero from "./fixtures/hero.json";
import { initialState, reduce, select } from "./state/reducer";
import type { ParityEvent, RunState } from "./state/types";
import { Workbench } from "./Workbench";

type Mock = "idle" | "running" | "hero";
const events = hero.events as unknown as ParityEvent[];

function stateFor(mock: Mock): RunState {
  if (mock === "idle") return initialState;
  if (mock === "running") {
    const cut = events.findIndex((e) => e.type === "judge.result");
    return { ...events.slice(0, cut).reduce(reduce, initialState), phase: "running", selectedFindingId: null };
  }
  const done = events.reduce(reduce, initialState);
  const heroId = done.findings.find((f) => f.element.dom_id === "f5")?.id ?? null;
  return select(done, heroId);
}

/** Static design mock (?mock=idle|running|hero): the real components over the recorded hero run, no server. */
export default function MockApp() {
  const initial = (new URLSearchParams(location.search).get("mock") as Mock) || "hero";
  const [mock, setMock] = useState<Mock>(["idle", "running", "hero"].includes(initial) ? initial : "hero");
  const [state, setState] = useState<RunState>(() => stateFor(mock));
  const theme = new URLSearchParams(location.search).get("theme");
  useMemo(() => {
    if (theme) document.documentElement.dataset.theme = theme;
  }, [theme]);
  const switchTo = (m: Mock) => {
    setMock(m);
    setState(stateFor(m));
  };
  return (
    <>
      <nav aria-label="Design mock states" className="flex gap-2 px-3 py-1 text-xs" style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--line)" }}>
        <span className="muted">Design mock ·</span>
        {(["idle", "running", "hero"] as Mock[]).map((m) => (
          <button key={m} type="button" className="btn-quiet" style={{ padding: "1px 8px", fontWeight: m === mock ? 600 : 400 }} onClick={() => switchTo(m)}>{m}</button>
        ))}
      </nav>
      <Workbench
        state={state} flows={[{ id: "checkout", name: "Checkout page", single_page: true }, { id: "purchase", name: "Purchase flow", single_page: false }]} flowId="checkout" onFlowChange={() => {}} canLive={true} screenshotUrl={state.steps.length ? checkout : null} model="muse-spark-1.3-contributor"
        onModeChange={(mode) => setState((s) => ({ ...s, mode }))} onRun={() => switchTo("running")} onSelect={(id) => setState((s) => select(s, id))}
      />
    </>
  );
}
