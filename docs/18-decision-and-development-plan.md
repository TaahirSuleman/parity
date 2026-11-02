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
| R7 | The open URL field (D12): SSRF, abuse, credit burn, third-party terms | Policy in code with a test per refused class, re-checked on every request the browser makes; per-run, per-origin and per-day caps; consent, a policy page, 24 h deletion; kill switch `PARITY_OPEN_URL=0` |

## 9. Video (judged for Demo 25% and Tooling 25%; judges stop at 3:00)

| Time | On screen (always the product) |
|---|---|
| 0:00–0:06 | Scope line, spoken + captioned: "Parity was built this week on Meta's Muse Spark; Playwright and axe-core are pre-existing open source." Workbench idle (the Sighted panel fills on the click; the axe-core badge reads "—" until then) |
| 0:06–0:20 | The person and the problem: a blind shopper at checkout. One overlay card: 95.9% of home pages fail; 5,114 US suits in 2025. The axe-core badge shows **0 violations** a quarter-second after the click that opens the next beat |
| 0:20–1:30 | Click **Run the audit** on the **Purchase flow, Replay** (a recorded run, labelled REPLAY: it plays in ≈71 s and is the only flow with computer-use rows; a Live walk takes 7–10 min and is not shown). The Navigator walks the flow (label: *Muse Spark 1.3 contributor · computer use*). Side-by-side panels with grounding boxes (*grounding*). Findings appear; scroll to a red row (the Verifier's rejections sit after the cards). **Hero:** the run ends on "Pay R1,249" vs `button, "Submit"` (deterministic since 2 Nov); click "Total: R1,249.00" for "not announced" if time allows |
| 1:30–1:55 | Proposed fix → open **Diff** on camera → Re-audit shows the gap closed → developer clicks **Approve fix** (the filled button) → "Download fix.patch" appears in the header |
| 1:55–2:15 | Eval tab, the ablation rows: screenshot only 17% / tree only 75% / no grounding 82% / full Parity 84% recall, and false alarms on clean 0.0 vs 0.7 without grounding (no tester quote: there is no on-screen artefact for one, rule L7) |
| 2:15–2:35 | Eval tab: recall 84% and precision 97% vs axe-core 0% on 38 seeded faults built to pass axe-core, 20 clean controls; $0.37 and 4 m 41 s per 3 pages (say "per three pages", not "per page"). The ≤ 10 s architecture card; the judge comparison (Muse Wonder) if a second is free |
| 2:35–2:42 | Pages we did not make: the flow picker's "External page (W3C demo, read-only)" group → **W3C demo: home** in Replay (≈15 s): the header names www.w3.org with W3C's attribution; then, in one breath, "Live on a page you choose" with a judge's own address (one screen, read-only, the policy link) |
| 2:42–2:50 | Impact close + "try it yourself" URL. Record at 1280 px wide (three columns, everything ≈12% larger); zoom in the edit on the hero pair and on the Approve click |
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

**Amended by D12 (§12, Mon 2 Nov 19:00 SAST):** the last bullet (arbitrary URLs after the event) and the timing paragraph are superseded;
the benchmark and the judge-runnable flows stand.

## 12. Any public page on the hosted app, before the freeze [D12, decided Mon 2 Nov 19:00 SAST]

**What changed since D11.** D11 (§11) kept an open URL field for after the event. The user ruled that nothing after the event counts for judging
and asked for the full version before the freeze, without dropping Voice, as an additional phase ordered by value. The design is doc 19 §19.3
(rewritten); the plan is doc 20 Phase 6c (Tasks 26F.1–26F.6); the chats and branches are docs/25 §4–§5.

**Decision.** The hosted workbench gets a third mode, "Live on a page you choose": the visitor types a public URL, affirms it is public and they
may audit it, and Parity audits that screen as a visitor would see it (one screen by default, up to three on request), with no fixer and no
re-audit, behind guard rails that are code, not model judgement: a URL policy that refuses every non-public address and is re-checked on every
request the browser makes; per-run, per-origin and per-day cost caps on top of the existing per-IP limits; a policy page with the opt-out and
takedown contact; 24-hour deletion of page content; prompts that mark page text as data; a kill switch that hides the field. The outcomes a
judge may hit ("blocked by site", "robots.txt disallows this page", "this address is not public") are shown as outcomes, not errors, and three
pages known to run well sit under the field. Approaches rejected: a curated allow list (a judge who types their own site gets "not on the
list", which reads as a demo that cannot do what it says) and a free-goal multi-screen walk by default (longer, more bot walls, more cost, and a
free goal is one more injection path; it is where Site B died).

**Risk and reward, Phase 6c against Voice (Phase 6).** Both ship if their clocks allow; the table decides who gets the merge slot and the
builder's time when they collide.

| | Phase 6c: any public page | Phase 6: Voice |
|---|---|---|
| Rubric lines served | Impact 30% and Demo 25% directly (a judge audits a page they chose); Technical depth (policy, SSRF defence and caps are craft) | Use of Meta AI tooling 25% (a fourth Meta model, a second modality); Technical depth (alignment, word accuracy) |
| What it answers | "Your numbers are on faults you seeded" and "does it work outside your store": the judge sees for themselves | "Is the accessibility tree what a screen-reader user hears": real speech corroborates the tree |
| Evidence it will work | Site A: six verified findings axe-core misses, $0.11, 184 s; the W3C pages run clean; the pipeline, the guard and `--public` exist | Voice Transcribe verified on the live API (doc 17); the alignment and the UI are new code; G-V is unmeasured |
| Main risk | A live run in front of a judge ends "blocked by site" (Site B); an abuse and SSRF surface on a credit-funded service; ~10 h of agent work the day before the freeze | G-V < 0.90 demotes Voice to corroboration; the recording is an hour of the builder's time no agent can do; the hero card changes the day before the freeze |
| Mitigation | Honest outcomes and the known-good list; the policy in code with a test per refused class; caps and a kill switch; Replay untouched | The gate was designed for it; the kit records captions by script; the UI change is one panel and one badge |
| Cost | ~10 h agent, ~$2 of verification runs, one page of policy text | ~5 h agent, ~1 h builder, ~$1 (hero re-record $0.40) |
| If it slips | The field ships hidden (`PARITY_OPEN_URL=0`); judges keep the W3C flows and the store; nothing else regresses | Ships without Voice and the README says so (Task 25 rule); the tree stays the evidence |
| Value if it lands | The product claim becomes "point it at a public page" instead of "watch it on our store" | A fourth Meta model in a hero that already works, with a measured accuracy beside it |

**Ruling.** Phase 6c has the higher reward and a bounded risk (its failure mode is a hidden field), so it takes priority: the first Tuesday merge
and redeploy, the earlier hosted gate, and the builder's attention when the two collide. Voice is not dropped: it runs in parallel on the other
track, keeps its own gate, and only its own clock can end it. The benchmark core (26E.1–26E.3) keeps its place before Voice on that track
because four hours buy a labelled number on pages we did not write; the benchmark answers the critique in numbers, Phase 6c answers it in deeds.

**Ordering: two tracks in parallel (amends §11's timing; the Mon 15:00 gate passed with nothing started, so every gate is re-set from Mon 19:00 SAST).**
- Track A, chat A, on `main`: Task 26 kit (45 min; the builder records while the agent continues) → 26E.1–26E.3 → Task 27 → Task 28 → the
  VoiceOver-pass fixes (docs/24) if time remains.
- Track B, chat B, in a worktree on `feat/open-url`: 26E.4 → 26F.1–26F.6 → merge into `main` → the first redeploy → 26E.5 bundles and the hosted
  verification of 6c.
- Gates (SAST): benchmark core Tue 10:00; 6c complete locally (suites green, three third-party pages run locally, the injection test) Tue 11:00;
  merge and first redeploy Tue 12:30; 6c verified on the hosted app Tue 14:30; Voice Task 28 committed Tue 14:00, hero re-recorded with the
  second and last redeploy Tue 16:00; 26E.5 bundles Tue 15:00; cold review Tue 17:00; freeze Tue 19:00. A gate missed is dropped, not squeezed.
- Drop order if the day runs short, first to go first: 26E.5 Replay bundles (the W3C flows still run Live); the three-screen option of 6c (one
  screen ships); the hero re-record (Voice then shows on Live checkout runs, not in the committed hero bundle). Task 29 was never in.

**Retention, answered.** Deletion is not about storage (a bundle is a few megabytes and the bucket is cheap). It is the promise on the policy page
that makes a read-only audit of someone else's page defensible under R4, and the takedown path needs it to exist anyway. Page content goes after
24 h; a small summary (origin, outcome, counts, cost, time) stays so the day's spend and the stats survive.
