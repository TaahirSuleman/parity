import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

function serveUrlMode(answer: (body: Record<string, unknown>) => Promise<Response>) {
  const posts: Record<string, unknown>[] = [];
  globalThis.fetch = vi.fn((url: string, init?: RequestInit) => {
    if (url === "/api/health") return ok(health({ open_url: true, suggested_urls: ["https://a.example/"], external_closed_today: false }));
    if (url === "/api/flows") return ok(flows);
    if (url === "/api/runs" && init?.method === "POST") { const body = JSON.parse(String(init.body)) as Record<string, unknown>; posts.push(body); return answer(body); }
    return ok(runDetail("url-run-1"));
  }) as unknown as typeof fetch;
  return posts;
}

it("Live on a page you choose: the field, consent and the request body; the header names the host once the run starts", async () => {
  const posts = serveUrlMode(() => ok({ run_id: "url-run-1", mode: "live" }));
  render(<App />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Live on a page you choose/ })).toBeInTheDocument());
  await act(async () => { screen.getByRole("button", { name: /Live on a page you choose/ }).click(); });
  const field = screen.getByRole("textbox", { name: /page address/i });
  await act(async () => { fireEvent.change(field, { target: { value: "https://www.w3.org/WAI/demos/bad/before/home.html" } }); });
  await act(async () => { fireEvent.click(screen.getByRole("checkbox", { name: /public and I may audit it/i })); });
  await act(async () => { screen.getByRole("button", { name: /audit this page/i }).click(); });
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0]).toMatchObject({ url: "https://www.w3.org/WAI/demos/bad/before/home.html", mode: "live", screens: 1, consent: true });
  await waitFor(() => expect(stream("url-run-1")).toBeDefined());
  act(() => { stream("url-run-1")!.emit("run.started", { run_id: "url-run-1", mode: "live", flow_id: "url-1a2b3c4d", public: true, source: "visitor-url", origin: "https://www.w3.org", attribution: "www.w3.org · audited read-only at a visitor's request", target_url: "https://www.w3.org/WAI/demos/bad/before/home.html" }); });
  await waitFor(() => expect(screen.getByRole("banner")).toHaveTextContent("www.w3.org"));
  expect(screen.getByRole("banner")).not.toHaveTextContent("ShopRight");
});

it("a refused address is shown verbatim in the panel, and the run is not marked failed", async () => {
  serveUrlMode(() => Promise.resolve(new Response(JSON.stringify({ detail: "This address is not public." }), { status: 422, headers: { "Content-Type": "application/json" } })));
  render(<App />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Live on a page you choose/ })).toBeInTheDocument());
  await act(async () => { screen.getByRole("button", { name: /Live on a page you choose/ }).click(); });
  await act(async () => { fireEvent.change(screen.getByRole("textbox", { name: /page address/i }), { target: { value: "http://localhost/x" } }); });
  await act(async () => { fireEvent.click(screen.getByRole("checkbox", { name: /public and I may audit it/i })); });
  await act(async () => { screen.getByRole("button", { name: /audit this page/i }).click(); });
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("This address is not public."));
  expect(document.title).not.toMatch(/failed/);
  expect(screen.getByRole("button", { name: /audit this page/i })).toBeEnabled();  // a second try is one click away
});

// QA gate before the 6c merge: the URL mode is part of the run on screen, and every server answer lands where the visitor is looking.
const visitorStarted = { run_id: "url-run-1", mode: "live", flow_id: "url-1a2b3c4d", public: true, source: "visitor-url", origin: "https://www.w3.org", attribution: "www.w3.org · audited read-only at a visitor's request", target_url: "https://www.w3.org/WAI/demos/bad/before/home.html" };

async function startVisitorRun() {
  await waitFor(() => expect(screen.getByRole("button", { name: /Live on a page you choose/ })).toBeInTheDocument());
  await act(async () => { screen.getByRole("button", { name: /Live on a page you choose/ }).click(); });
  await act(async () => { fireEvent.change(screen.getByRole("textbox", { name: /page address/i }), { target: { value: "https://www.w3.org/WAI/demos/bad/before/home.html" } }); });
  await act(async () => { fireEvent.click(screen.getByRole("checkbox", { name: /public and I may audit it/i })); });
  await act(async () => { screen.getByRole("button", { name: /audit this page/i }).click(); });
}

it("switching to the store's Live after a visitor run clears that run from the screen and brings the picker back", async () => {
  let starts = 0;
  serveUrlMode(() => ok({ run_id: ++starts === 1 ? "url-run-1" : "store-run-2", mode: "live" }));
  render(<App />);
  await startVisitorRun();
  await waitFor(() => expect(stream("url-run-1")).toBeDefined());
  act(() => { stream("url-run-1")!.emit("run.started", visitorStarted); });
  act(() => { stream("url-run-1")!.emit("run.finished", { run_id: "url-run-1", status: "done", findings_verified: 0 }); });
  await waitFor(() => expect(screen.getByRole("banner")).toHaveTextContent("www.w3.org"));
  await act(async () => { screen.getByRole("button", { name: /^Live \(rate-limited\)/ }).click(); });
  expect(screen.getByRole("banner")).not.toHaveTextContent("www.w3.org");
  expect(screen.getByRole("combobox")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Run the audit" })).toBeInTheDocument();
  // and back: pressing the third pill with a store run on screen clears it too, since the header will say "a page you choose"
  await act(async () => { screen.getByRole("button", { name: "Run the audit" }).click(); });
  await waitFor(() => expect(stream("store-run-2")).toBeDefined());
  act(() => { stream("store-run-2")!.emit("run.started", { run_id: "store-run-2", mode: "live", flow_id: "checkout" }); });
  act(() => { stream("store-run-2")!.emit("run.finished", { run_id: "store-run-2", status: "done", findings_verified: 0 }); });
  await waitFor(() => expect(screen.getByRole("button", { name: "Run the audit" })).toBeInTheDocument());
  await act(async () => { screen.getByRole("button", { name: /Live on a page you choose/ }).click(); });
  expect(screen.getByRole("button", { name: /Live on a page you choose/ })).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByRole("button", { name: "Run the audit" })).toBeNull();
});

it("a linked visitor run loads with the third pill pressed and no store button", async () => {
  window.history.replaceState(null, "", "/?run=url-run-1");
  globalThis.fetch = vi.fn((url: string) => {
    if (url === "/api/health") return ok(health({ open_url: true, suggested_urls: [], external_closed_today: false }));
    if (url === "/api/flows") return ok(flows);
    return ok({ run: { id: "url-run-1", mode: "live", flow_id: "url-1a2b3c4d", status: "done", source: "visitor-url", origin: "https://www.w3.org", public: true }, findings: [], steps: [], rejected: [], trace: [] });
  }) as unknown as typeof fetch;
  render(<App />);
  await waitFor(() => expect(stream("url-run-1")).toBeDefined());
  act(() => { stream("url-run-1")!.emit("run.started", visitorStarted); });
  await waitFor(() => expect(screen.getByRole("button", { name: /Live on a page you choose/ })).toHaveAttribute("aria-pressed", "true"));
  expect(screen.queryByRole("button", { name: "Run the audit" })).toBeNull();
  expect(screen.getByRole("banner")).toHaveTextContent("www.w3.org");
});

it("a 410 on a linked run says the audit has expired, in the server's sentence and nothing else", async () => {
  window.history.replaceState(null, "", "/?run=old-run-1");
  serve({ linked: Promise.resolve(new Response(JSON.stringify({ detail: "This audit has expired: pages you choose are kept for 24 hours." }), { status: 410, headers: { "Content-Type": "application/json" } })) });
  render(<App />);
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("This audit has expired: pages you choose are kept for 24 hours."));
  expect(screen.getByRole("alert").textContent).toBe("This audit has expired: pages you choose are kept for 24 hours.");
});

it("a site that has had its runs for today is answered in the panel, without the Replay suggestion", async () => {
  serveUrlMode(() => Promise.resolve(new Response(JSON.stringify({ error: "this site has had its runs for today; try another page, or come back tomorrow", retry_after_s: 36000, detail: "x" }), { status: 429, headers: { "Content-Type": "application/json" } })));
  render(<App />);
  await startVisitorRun();
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/this site has had its runs for today/));
  expect(screen.getByRole("alert")).toHaveTextContent(/about 10 h/);
  expect(screen.getByRole("alert")).not.toHaveTextContent(/Replay/);
});

it("the day's budget being spent is said once, as the panel's status, with the pill still on screen", async () => {
  serveUrlMode(() => Promise.resolve(new Response(JSON.stringify({ detail: "closed for today: the day's budget for pages visitors choose is spent" }), { status: 503, headers: { "Content-Type": "application/json" } })));
  render(<App />);
  await startVisitorRun();
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/closed for today/i));
  expect(screen.getAllByText(/closed for today/i)).toHaveLength(1);
  expect(screen.getByRole("button", { name: /Live on a page you choose/ })).toBeDisabled();
});
