import { useEffect, useId, useRef, useState } from "react";
import type { UrlRunRequest } from "../api";

/** The page offered when the server configures none: W3C's own demonstration page, published to be audited. */
export const W3C_HOME = "https://www.w3.org/WAI/demos/bad/before/home.html";

interface Props {
  suggested: string[]; // pages known to run well (PARITY_SUGGESTED_URLS)
  closed: boolean; // the day's budget is spent: the field says so and offers nothing to click
  running: boolean;
  refusal: string | null; // the server's one sentence when an address was refused, shown verbatim
  active?: string | null; // the host of the visitor's run on screen: the panel folds to one line so the screenshot keeps its height
  onRun: (req: UrlRunRequest) => void;
}

function hostOf(url: string): string {
  try { return new URL(url).hostname; } catch { return url; }
}

/** What a suggested page is called on its button: the host, or host and path when two pages share a host. */
export function pageLabel(url: string, all: string[]): string {
  const host = hostOf(url);
  if (all.filter((u) => hostOf(u) === host).length < 2) return host;
  try { const u = new URL(url); return `${u.hostname}${u.pathname === "/" ? "" : u.pathname}`; } catch { return url; }
}

/** An address typed without a scheme is a web address: "www.w3.org/x" means https://www.w3.org/x. The server judges the rest. */
export function withScheme(url: string): string {
  const s = url.trim();
  return /^[a-z][a-z0-9+.-]*:/i.test(s) ? s : `https://${s}`;
}

/** "Live on a page you choose" (spec §19.3.6): the address, the screens, an optional hint, the affirmation, the policy link. */
export function UrlRun({ suggested, closed, running, refusal, active = null, onRun }: Props) {
  const id = useId();
  const [url, setUrl] = useState("");
  const [screens, setScreens] = useState<1 | 3>(1);
  const [hint, setHint] = useState("");
  const [consent, setConsent] = useState(false);
  const [unfolded, setUnfolded] = useState(false);  // the visitor asked for the form back while a run of theirs is on screen
  const field = useRef<HTMLInputElement>(null);
  useEffect(() => { setUnfolded(false); }, [active]);  // a new run folds the panel again
  useEffect(() => { if (refusal) field.current?.focus(); }, [refusal]);  // a refusal is answered where the retry is typed
  useEffect(() => { if (unfolded) field.current?.focus(); }, [unfolded]);
  const pages = suggested.length ? suggested : [W3C_HOME];
  const locked = closed || running;
  const ready = consent && url.trim().length > 0 && !closed;
  const folded = Boolean(active) && !unfolded;
  return (
    <section className="surface flex flex-col gap-2 px-4 py-3" aria-labelledby={`${id}-h`} style={{ borderRadius: 0, borderWidth: "0 0 1px 0" }}>
      <h2 id={`${id}-h`} className="text-xs uppercase tracking-wider muted font-medium m-0">Live on a page you choose</h2>
      {closed && <p role="status" className="m-0 text-sm">Closed for today: the day's budget for pages visitors choose is spent. The store flows and Replay still work.</p>}
      {folded ? (
        <p className="m-0 text-sm flex items-center gap-3 flex-wrap">
          <span>{running ? "Auditing" : "Audited"} {active}, read-only.</span>
          <button type="button" className="btn-quiet text-xs" style={{ padding: "2px 8px" }} onClick={() => setUnfolded(true)} disabled={closed}>Audit another page</button>
        </p>
      ) : (
      <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); if (ready && !running) onRun({ url: withScheme(url), screens, consent, hint: hint.trim() }); }}>
        <div className="flex items-center gap-2 flex-wrap">
          <label htmlFor={`${id}-url`} className="text-sm">Page address</label>
          <input ref={field} id={`${id}-url`} type="text" inputMode="url" autoComplete="url" spellCheck={false} className="btn-quiet" style={{ flex: "1 1 320px", padding: "4px 8px" }} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" maxLength={2048} disabled={locked} />
        </div>
        <fieldset className="m-0 p-0 flex items-center gap-4 flex-wrap text-sm" style={{ border: 0 }}>
          <legend className="sr-only">Screens</legend>
          <label className="flex items-center gap-1"><input type="radio" name={`${id}-screens`} checked={screens === 1} onChange={() => setScreens(1)} disabled={locked} /> One screen</label>
          <label className="flex items-center gap-1"><input type="radio" name={`${id}-screens`} checked={screens === 3} onChange={() => setScreens(3)} disabled={locked} /> Up to three screens (the agent walks, read-only)</label>
        </fieldset>
        <div className="flex items-center gap-2 flex-wrap">
          <label htmlFor={`${id}-hint`} className="text-sm">What the page is about (optional)</label>
          <input id={`${id}-hint`} type="text" className="btn-quiet" style={{ flex: "1 1 240px", padding: "4px 8px" }} value={hint} onChange={(e) => setHint(e.target.value)} maxLength={120} disabled={locked} />
        </div>
        <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} disabled={locked} /> This page is public and I may audit it.</label>
        <div className="flex items-center gap-3 flex-wrap">
          {/* while the run is going the button is aria-disabled, not disabled: a disabled control drops keyboard focus to the page (docs/24 §2.1) */}
          <button type="submit" className="btn-primary" disabled={!ready && !running} aria-disabled={running || undefined} data-running={running}>{running ? "Auditing…" : "Audit this page"}</button>
          <span className="muted text-xs">Read-only. Sites behind bot challenges or logins end the run early, and we say so.</span>
          <a className="text-xs" href="/audit-policy" target="_blank" rel="noopener noreferrer">What Parity does on your page, what it keeps, how to opt out (opens in a new tab)</a>
        </div>
      </form>
      )}
      {refusal && <p role="alert" className="m-0 text-sm" style={{ color: "var(--bad)" }}>{refusal}</p>}
      {!folded && (
        <p className="m-0 text-xs muted flex items-center gap-2 flex-wrap">
          <span>Pages known to run well:</span>
          {pages.map((p) => <button key={p} type="button" className="btn-quiet text-xs" style={{ padding: "2px 8px" }} onClick={() => { setUrl(p); field.current?.focus(); }} disabled={locked} title={p}>{pageLabel(p, pages)}</button>)}
        </p>
      )}
    </section>
  );
}
