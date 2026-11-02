import "@testing-library/jest-dom/vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "./App";

// A fake EventSource the App's stream client talks to; the test emits events on it.
class FakeES {
  static all: FakeES[] = [];
  static CLOSED = 2;
  url: string; readyState = 1; closed = false; onerror: (() => void) | null = null;
  listeners: Record<string, ((m: MessageEvent) => void)[]> = {};
  constructor(url: string) { this.url = url; FakeES.all.push(this); }
  addEventListener(t: string, f: (m: MessageEvent) => void) { (this.listeners[t] ||= []).push(f); }
  close() { this.closed = true; this.readyState = 2; }
  emit(type: string, data: Record<string, unknown>) {
    if (this.closed) return;
    for (const f of this.listeners[type] ?? []) f({ data: JSON.stringify({ type, at: new Date().toISOString(), ...data }) } as MessageEvent);
  }
}

function deferred<T>() { let resolve!: (v: T) => void; const p = new Promise<T>((r) => (resolve = r)); return { p, resolve }; }
const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }));
const health = (over: Record<string, unknown> = {}) => ({ ok: true, mode_default: "replay", live_enabled: true, storage: "local", runs_indexed: 1, has_key: true, models_ok: true, replay_runs: ["hero-checkout"], replay_flows: { checkout: "hero-checkout" }, version: "x", ...over });
const flows = [{ id: "checkout", name: "Checkout page", start_url: "/store/checkout.html", goal: "g", pages: [], single_page: true }];
const runDetail = (id: string) => ({ run: { id, mode: "replay", flow_id: "checkout", status: "awaiting_review" }, findings: [], steps: [], rejected: [], trace: [] });
const stream = (id: string) => FakeES.all.find((e) => e.url.includes(id));

beforeEach(() => {
  FakeES.all = [];
  (globalThis as unknown as { EventSource: unknown }).EventSource = FakeES;
  (Element.prototype as unknown as { scrollIntoView: () => void }).scrollIntoView = () => {};
});
afterEach(() => { vi.restoreAllMocks(); window.history.replaceState(null, "", "/"); });

function serve(opts: { linked?: Promise<Response>; healthOver?: Record<string, unknown>; onPost?: () => void } = {}) {
  let posts = 0;
  globalThis.fetch = vi.fn((url: string, init?: RequestInit) => {
    if (url === "/api/health") return ok(health(opts.healthOver));
    if (url === "/api/flows") return ok(flows);
    if (url === "/api/runs/old-run-1" && opts.linked) return opts.linked;
    if (url === "/api/runs" && init?.method === "POST") { posts += 1; opts.onPost?.(); return ok({ run_id: `new-run-${posts}`, mode: "replay" }); }
    return ok(runDetail("new-run-1"));
  }) as unknown as typeof fetch;
  return () => posts;
}

it("a reloaded ?run= link that answers after Run was clicked does not take over the new run", async () => {
  window.history.replaceState(null, "", "/?run=old-run-1");
  const slowLinked = deferred<Response>();
  serve({ linked: slowLinked.p });
  render(<App />);
  await waitFor(() => expect(screen.getByRole("option", { name: "Checkout page" })).toBeInTheDocument());
  await act(async () => { screen.getByRole("button", { name: "Run the audit" }).click(); });
  await waitFor(() => expect(stream("new-run-1")).toBeDefined());
  act(() => { stream("new-run-1")!.emit("run.started", { run_id: "new-run-1", mode: "replay", flow_id: "checkout" }); });
  await act(async () => { slowLinked.resolve(new Response(JSON.stringify(runDetail("old-run-1")), { status: 200, headers: { "Content-Type": "application/json" } })); });
  expect(stream("new-run-1")!.closed).toBe(false);
  expect(stream("old-run-1")).toBeUndefined();
  act(() => { stream("new-run-1")!.emit("run.finished", { run_id: "new-run-1", status: "awaiting_review", findings_verified: 0 }); });
  await waitFor(() => expect(screen.getByRole("button", { name: "Run the audit" })).toBeInTheDocument());
});

it("the Run button stays taken between the start answering and the first event, so a second click starts nothing", async () => {
  const posts = serve();
  render(<App />);
  await waitFor(() => expect(screen.getByRole("option", { name: "Checkout page" })).toBeInTheDocument());
  await act(async () => { screen.getByRole("button", { name: "Run the audit" }).click(); });
  await waitFor(() => expect(stream("new-run-1")).toBeDefined());
  expect(screen.getByRole("button", { name: "Auditing…" })).toBeInTheDocument();  // no event has arrived yet
  await act(async () => { screen.getByRole("button", { name: "Auditing…" }).click(); });
  expect(posts()).toBe(1);
  act(() => { stream("new-run-1")!.emit("run.started", { run_id: "new-run-1", mode: "replay", flow_id: "checkout" }); });
  expect(screen.getByRole("button", { name: "Auditing…" })).toBeInTheDocument();
});

it("Live is offered only when the server can reach the models", async () => {
  serve({ healthOver: { models_ok: false } });
  render(<App />);
  await waitFor(() => expect(screen.getByRole("option", { name: "Checkout page" })).toBeInTheDocument());
  expect(screen.getByRole("button", { name: /Live/ })).toBeDisabled();
});
