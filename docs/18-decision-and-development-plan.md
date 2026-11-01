# 18 — Decision and development plan: Accessibility Gap Auditor

**Status:** DECIDED, Thu 29 Oct 2026.
**Supersedes:** the open choice in doc 16; evidence is in doc 17.
**Working name:** **Parity**, because it checks that sighted and screen-reader users get the same page. Rename freely.
**Deadline:** Wed 4 Nov, 21:00 ET (Thu 5 Nov, 04:00 SAST). Submit by 18:00 ET.

---

## 1. Why this one, in one paragraph
Six seeded accessibility failures produced **zero** axe-core violations. Muse Spark 1.3 found **6/6** by comparing the screenshot with the accessibility tree, and flagged **0/2** clean controls (doc 17). Spark computer use completed the flow on its own. The pipeline runs on **real, public inputs** (any website), not synthetic data, which removes the panel's main objection to Callback.

**The case for it:**
- **Gap:** the exact job is still unserved (Evinced's agent is "in labs"; TaskAudit is academic).
- **Impact:** citable. WebAIM 2026 found 95.9% of home pages failing; 5,114 ADA web suits were filed in 2025; the EAA has applied since June 2025.
- **People:** the beneficiaries are clear (blind and low-vision users).
- **Hours:** it fits the time available.

Callback's differentiator (diarization deciding the verdict) failed its ablation, so Callback is shelved.

## 2. What office hours changed (29 Oct)

| Answer from Meta / organisers | Impact on the plan |
|---|---|
| Spark 1.3 accepts the `computer` tool; Wonder isn't confirmed; combining Muse models is encouraged | Navigator = `muse-spark-1.3` computer use. Use Spark tiers by role (`-contributor` for bulk/eval). Wonder only for offline judging, if at all |
| 500s are not expected: report them at dev.meta.ai/support with Team ID, model, error, timestamps and request IDs | Log every request ID and timestamp in our trace. Retry with backoff, then report. **Action:** file the 29 Oct 500 |
| `truncation:"auto"` is set **per request** | Set it on every computer-use request |
| Voice Transcribe on fast synthetic speech is unconfirmed; text and language biasing exist; bring a sample if accuracy is poor | **Real screen-reader audio is a stretch layer, not the core.** The accessibility tree is the deterministic "what the screen reader gets". Recording VoiceOver audio decides whether Voice joins the hero (Gate G-V) |
| Third-party sites: follow their terms; AUP questions go to up_exceptions@meta.com | Hero and eval run on **our own demo store**. Public sites only read-only, within their terms, and named only if issues are disclosed responsibly. Optional: email up_exceptions |
| **Every runtime model must be a Meta model** | No non-Meta models anywhere at runtime, **including TTS**: the UI shows screen-reader text, never synthesised speech. Recorded VoiceOver clips may be played as media. axe-core and Playwright are not models, so they're fine |
| **Judges must be able to try the demo without logging in**, runnable from the repo's setup instructions plus the video | A hosted, no-login public URL with a **"Run the audit"** button on our demo store, plus a cached replay so judge traffic can't exhaust credits. The repo has a one-command local run (`MODEL_API_KEY` + `make demo`) |

## 3. The product, the user and the hero moment
- **User and job:** a front-end team lead at a company selling online. Before a release, prove that screen-reader users can complete the key flows (checkout, sign-up), and fix the failures the automated checker misses.
- **Hero moment:**
  1. axe-core shows **"0 violations"** on the checkout.
  2. Parity walks the flow, and at the Pay step the workbench shows two panels side by side:
     - **Sighted:** a green button reading "Pay R1,249", boxed;
     - **Screen reader:** `button, "Submit"`. The price is not announced at all.
  3. Parity files the finding, proposes the fix and re-runs the page to show the gap closed.
  4. The developer clicks **Approve fix**.
- **The person in the moment:** a blind shopper who can't tell what "Submit" will charge. If we get a real tester, their quote is in the video.

## 4. Architecture (our own code; verifiable-agent pattern from doc 14)

```
Goal ("buy the headphones") ─► NAVIGATOR (Spark 1.3 computer use, truncation:auto)
   each step ─► CAPTURE (deterministic: screenshot + Chrome AX tree + DOM boxes + axe-core)
            ─► SEER (Spark grounding: what a sighted user perceives, 0–1000 boxes)
            ─► COMPARATOR (Spark: sighted vs AX divergences → findings[])
            ─► VERIFIER (code: box hits a real element; quoted AX name == actual AX string;
                         element not already flagged by axe; dedupe)  ── refuses invalid findings
            ─► JUDGE (Spark, separate prompt: real barrier? severity? WCAG SC; fails closed)
            ─► FIXER (Spark proposes a code diff for repos we own)
            ─► RE-AUDIT (code + Comparator on the patched page: did the gap close?)
            ─► HUMAN GATE (developer approves fix / files ticket in the workbench)
            ─► REPORT + TRACE (every call: model, request ID, tokens, latency, cost; replayable)
```

- **Checks sit inside the tools** (doc 14). A finding can't reach the report without passing the Verifier, and a fix can't be proposed as done until Re-audit confirms it.
- **The model perceives; code decides** whether evidence is real (the AX string must match exactly).
- **Meta models:**
  - Spark 1.3: computer use, grounding, comparison, judging and fixing.
  - Spark `-contributor`: bulk eval runs.
  - Voice Transcribe: optional, real screen-reader audio (Gate G-V).
- **Why Meta**, measured by ablation:
  - screenshot only, without the AX tree;
  - AX tree only, without the screenshot;
  - with vs without grounding (precision drops when evidence can't be located);
  - computer use vs a fixed script (it reaches flows the script can't) — not measured: the eval audits single pages; the agent walk is shown by the Purchase-flow replay instead (noted 1 Nov).

## 5. Workbench (designed first)
- **Left:** a live screenshot stream from the Navigator, with grounding boxes.
- **Right:** what the screen reader gets, as role and name text for the focused or boxed element, plus an optional recorded VoiceOver clip.
- **Centre column:** a findings feed. Each card shows:
  - the sighted vs screen-reader evidence;
  - a WCAG reference;
  - the Verifier result;
  - an Approve or Reject control for the fix.
- **Header:** axe-core count vs Parity count, and the per-run cost and time.
- **Controls:** a no-login **Run the audit** button on the demo store, with Live and Replay modes, both labelled.

## 6. Evaluation (honest, small n)
- **Demo store:** 3 pages (product, cart, checkout) with **~30 seeded faults** of the axe-passing kind, plus **~10 clean controls**. Labels live outside the agent's folder.
- **Metrics:**
  - recall and precision vs labels;
  - the same for axe-core (the baseline);
  - the ablations in §4;
  - cost and time per page.
- **Real-world sample:** 2–3 public flows audited read-only. Report counts of verified findings only, and disclose issues responsibly before naming any site.

## 7. Day plan (≈40–45 h without leave; more with leave)

| Day | Deliverable | Exit check |
|---|---|---|
| **Thu 29** | Decision. Fresh public repo + `HACKATHON_SCOPE.md`. Report the 500. VoiceOver recording test (Gate G-V). Scaffold: capture module (screenshot, AX tree, boxes, axe) | Capture runs on the demo page |
| **Fri 30** | Seer, Comparator and Verifier on a single page; Navigator loop on a 2-page flow; trace store | Hero finding produced end to end with request IDs logged |
| **Sat 31** | Workbench v1 (stream, panels, findings, approve); Fixer and Re-audit; demo store v2 (3 pages, 30 faults) | Hero moment works live in the UI |
| **Sun 1** | Eval harness, baseline and ablations; 2–3 real-site runs; **tester session** (screen-reader user + front-end dev) | Eval table; one quote; one change made from feedback |
| **Mon 2** | Hosted no-login deploy, Replay mode and rate limit; README (architecture, what's deterministic, how to run); form essays | A judge can run it in under 60 s |
| **Tue 3** | **12:00 feature freeze**; video (≤ 2:55, demo-first, doc 04 §4.4); cold review (doc 04 Part 7) | Video rendered and checked |
| **Wed 4** | Fixes, X post, **submit by 18:00 ET** | Submitted |

## 8. Gates and risks

| ID | Gate / risk | Pass / mitigation |
|---|---|---|
| G-V | VoiceOver audio through Voice Transcribe | ≥ 90% word accuracy on a recorded page → Voice joins the hero; else the AX tree stays the source of truth and Voice is dropped |
| R1 | Computer-use instability (500 seen) | Retries with backoff, request-ID logging, Replay mode for the demo |
| R2 | "Why Meta?" (vendor-swappable) | Measured ablations; fused grounding + computer use + verifier; honest wording, no "only Meta" absolutes |
| R3 | Overlay-style overclaiming (accessiBe's FTC $1M order) | Never claim "compliance"; a human approves every fix; findings are evidence, not certification |
| R4 | Third-party site terms | Hero and eval on our own store; public sites read-only, within their terms, disclosed responsibly |
| R5 | Credit burn from judges | Replay by default; Live behind a per-IP limit; contributor model for eval |
| R6 | Incumbents (Evinced, Deque) ship the same | Position as an open, verifiable agent; speed matters, so build now |

## 9. Video (judged for Demo 25% and Tooling 25%; judges stop at 3:00)

| Time | On screen (always the product) |
|---|---|
| 0:00–0:06 | Scope line, spoken + captioned: "Parity was built this week on Meta's Muse Spark; Playwright and axe-core are pre-existing open source." Workbench idle on the demo checkout |
| 0:06–0:20 | The person and the problem: a blind shopper at checkout. One overlay card: 95.9% of home pages fail; 5,114 US suits in 2025. axe-core badge: **0 violations** |
| 0:20–1:30 | Click **Run the audit**. The Navigator walks the flow (label: *Muse Spark 1.3 · computer use*). Side-by-side panels with grounding boxes (*Spark · grounding*). Findings appear; the Verifier rejects one bad finding (red row). **Hero:** "Pay R1,249" vs `button, "Submit"` |
| 1:30–1:55 | Fixer diff → Re-audit shows the gap closed → developer clicks **Approve** |
| 1:55–2:15 | Ablation strip in the product: screenshot-only / tree-only / full Parity, with recall for each. Tester quote |
| 2:15–2:35 | Eval tab: catch rate and precision vs axe-core on ~30 seeded faults; cost and time per page. A ≤ 10 s architecture card |
| 2:35–2:50 | Impact close + "try it yourself" URL |
| 2:50–2:55 | End card |

## 10. Problem statement
**Build for Your World:** we ship software and its users include screen-reader users. The fallback is *Push the Frontier (software)*. This is our choice; the organisers' answer on it doesn't change scoring.

## 11. External pages: what exists, what ships before the freeze, what waits [D11, decided 1 Nov evening]

**The facts first.**
- Parity already audits pages we do not own, from the command line only: `parity audit <url> --goal … --public` runs the same pipeline behind the
  read-only guard (doc 19 §17: no irreversible clicks, no credential or card typing, no form submission, robots.txt honoured, bot walls and logins
  end the run). Two anonymised samples ship as Replay bundles and show in the Eval tab: Site A (two screens, six verified findings axe-core does
  not report, $0.11, 184 s) and Site B (a bot challenge stopped the walk before any screen; recorded as such, never bypassed).
- The hosted app's Live mode is restricted to our own store by decision D7 and risk R4 (third-party terms, the AUP, credit burn from judges).
- Every accuracy number we publish (recall 84%, precision 97%, the ablations) is measured on faults we seeded ourselves. On pages we did not make
  we publish counts only. That is the strongest honest critique of the evaluation, and nothing in the plan answered it.
- The remaining plan before the Tue 3 Nov 12:00 ET (19:00 SAST) freeze is Phase 6 (Voice, Tasks 26–28, gated on G-V), then the video and submission.

**Decision.** Add an independent, labelled, licensed external benchmark, and make its pages runnable by judges, before the freeze; keep arbitrary
URLs on the hosted app for after the event.

- **The benchmark: the W3C WAI "Before and After Demonstration" (BAD)**, `https://www.w3.org/WAI/demos/bad/` (W3C, 2012, WCAG 2.0). Four "before"
  pages (home, news, tickets, survey) carry published, numbered barrier annotations written by W3C, not by us (home alone lists ten, `#annot_01`
  to `#annot_10`); the four "after" pages are the same pages repaired, which makes them clean controls we did not write either. The pages are live on
  www.w3.org (24 KB, ~50 ms; robots.txt allows `/WAI/demos/`), under the W3C document licence (copying with the copyright notice kept). Verified
  1 Nov.
- **What we claim from it.** Recall on the barriers that are in Parity's scope by design (perceptual gaps: a text alternative missing, meaningless,
  verbose or placeholder; a title-only name; an image-only link with no name; a non-descriptive link; an unlabelled form control), with the
  out-of-scope barriers named and counted (reading order, visual distinction of links, colour, layout tables). Precision on the "after" pages and on
  the labelled clean elements. The same axe-core baseline beside it. Small n, stated.
- **Judge-runnable.** The four "before" pages become hosted flows under "External page (W3C demo, read-only)": Live, with the read-only guard on,
  no fixes (we never patch a page we do not serve), the usual rate limits, and a Replay bundle for each so the default path costs nothing.
  Attribution on screen and in the bundle.
- **Not before submission: arbitrary URL input on the hosted app.** Terms differ per site (R4); an open URL field is an abuse and SSRF surface
  on a service funded by hackathon credits (R5); bot walls end most commercial walks (Site B); third-party screenshots would need a retention and
  takedown policy; and the prompts do not yet mark page text as untrusted. The design and its guard rails are in doc 19 §19 for after the event.

**Timing (amends §7).** Mon 2 Nov, after the VoiceOver-pass fixes: the benchmark core (labels, anchor matching, the runs, the numbers: ~4 h);
then the hosted flows and Replay bundles (~2 h). Go/no-go: core by Mon 15:00 SAST, hosted by Tue 12:00 SAST; whatever misses its gate is
dropped, not squeezed. Phase 6 (Voice) follows the core on Monday; if both cannot land, the benchmark core has priority because it changes what
the evaluation can honestly claim, while Voice adds a third Meta model to a hero that already works. Plan: doc 20 Phase 6b, Task 26E.
