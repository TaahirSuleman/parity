import { useId, useState } from "react";
import type { UrlRunRequest } from "../api";

/** The page offered when the server configures none: W3C's own demonstration page, published to be audited. */
export const W3C_HOME = "https://www.w3.org/WAI/demos/bad/before/home.html";

interface Props {
  suggested: string[]; // pages known to run well (PARITY_SUGGESTED_URLS)
  closed: boolean; // the day's budget is spent: the field says so and offers nothing to click
  running: boolean;
  refusal: string | null; // the server's one sentence when an address was refused, shown verbatim
  onRun: (req: UrlRunRequest) => void;
}

function hostOf(url: string): string {
  try { return new URL(url).hostname; } catch { return url; }
}

/** "Live on a page you choose" (spec §19.3.6): the address, the screens, an optional hint, the affirmation, the policy link. */
export function UrlRun({ suggested, closed, running, refusal, onRun }: Props) {
  const id = useId();
  const [url, setUrl] = useState("");
  const [screens, setScreens] = useState<1 | 3>(1);
  const [hint, setHint] = useState("");
  const [consent, setConsent] = useState(false);
  const pages = suggested.length ? suggested : [W3C_HOME];
  const locked = closed || running;
  const ready = consent && url.trim().length > 0 && !locked;
  return (
    <section className="surface flex flex-col gap-2 px-4 py-3" aria-labelledby={`${id}-h`} style={{ borderRadius: 0, borderWidth: "0 0 1px 0" }}>
      <h2 id={`${id}-h`} className="text-xs uppercase tracking-wider muted font-medium m-0">Live on a page you choose</h2>
      {closed && <p role="status" className="m-0 text-sm">Closed for today: the day's budget for pages visitors choose is spent. The store flows and Replay still work.</p>}
      <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); if (ready) onRun({ url: url.trim(), screens, consent, hint: hint.trim() }); }}>
        <div className="flex items-center gap-2 flex-wrap">
          <label htmlFor={`${id}-url`} className="text-sm">Page address</label>
          <input id={`${id}-url`} type="url" inputMode="url" className="btn-quiet" style={{ flex: "1 1 320px", padding: "4px 8px" }} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" maxLength={2048} disabled={locked} />
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
          <button type="submit" className="btn-primary" disabled={!ready}>{running ? "Auditing…" : "Audit this page"}</button>
          <span className="muted text-xs">Read-only. Sites behind bot challenges or logins end the run early, and we say so.</span>
          <a className="text-xs" href="/audit-policy">What Parity does on your page, what it keeps, how to opt out</a>
        </div>
      </form>
      {refusal && <p role="alert" className="m-0 text-sm" style={{ color: "var(--bad)" }}>{refusal}</p>}
      <p className="m-0 text-xs muted flex items-center gap-2 flex-wrap">
        <span>Pages known to run well:</span>
        {pages.map((p) => <button key={p} type="button" className="btn-quiet text-xs" style={{ padding: "2px 8px" }} onClick={() => setUrl(p)} disabled={locked} title={p}>{hostOf(p)}</button>)}
      </p>
    </section>
  );
}
