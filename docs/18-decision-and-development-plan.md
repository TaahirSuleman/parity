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

**Storyboard v4 (Wed 4 Nov, 13:30 SAST; supersedes v3 after the first recorded cut).** Three changes from v3, from the builder's review of that cut: (1) **attention boxes and small captions**, drawn only where they direct the eye, so the video reads as one continuous take with a voice over it rather than a tour; (2) the **live beat doubled** (22 s to 44 s), because a page we did not write is the strongest proof of real-world value, and the beat now shows *every* finding's proof and the claim the Verifier refused, not just one card; (3) the **page for the live beat is chosen by a measured comparison** between BBC News and a Meta-owned public page (candidates and runs in the subagent report of 4 Nov; the decision is recorded below the table). Still written for a judge with no context: the product is on screen from 0:00; overlays total under 20 s; every number is the README's; hard stop 2:55, everything that matters by 2:50; narration at or under 2.6 words a second (measured).

**How the boxes and captions are made.** They are not added in the edit: the recording script (`data/demo-takes/record2.py`, git-ignored) drives the hosted app with Playwright at 1280×720 and, at the moments listed below, draws a **spotlight** in the page: a 2.5 px orange rounded rectangle around the element's real bounding box, with a **caption pill** (13 px, dark, at most six words) under it, held for the stated seconds and faded out in 250 ms. A spotlight never covers the element and never moves the page; at most one is on screen at a time; beats without a listed spotlight have none. The spotlights and captions are editorial (orange, dashed outline) so they cannot be mistaken for product UI. A separate **context chip** (grey, bottom-left) names the run where it matters: "Replay · recorded run · no model calls", "Live · 3 Nov · 2 m 7 s · $0.09". The only things added in the edit are the voice-over, the VoiceOver audio segment at 0:00 and the end card.

| Time | On screen (the product throughout) | Spotlights and captions (seconds held) | Narration (plain words; the terms are the badges on screen) |
|---|---|---|---|
| 0:00–0:08 | Checkout page Replay, finished; the **Pay R1,249** card selected; the VoiceOver segment playing. Badge *Muse Voice Transcribe 1.0 · real VoiceOver audio*; the agreement tick ("Transcript agrees with the accessibility tree"). Scope caption: "Built this week on Meta's Model API; Playwright and axe-core are pre-existing open source." | 0:01 the Pay R1,249 button inside the screenshot, caption "a sighted shopper reads Pay R1,249" (3 s); 0:04 the announced name in the Screen reader panel, caption "a screen reader says: Submit" (4 s) | "A checkout button. A sighted shopper reads *Pay R1,249*. This is what a blind shopper hears." *(audio: "Submit button")* |
| 0:08–0:20 | Same screen. The axe-core badge **0 violations**. Overlay card (6 s): 95.9% of home pages fail (WebAIM Million 2025); 5,114 US web-accessibility suits in 2025 (UsableNet). | 0:09 the axe-core badge, caption "the standard checker: 0 violations" (4 s); 0:14 the Voice Transcribe badge, caption "real VoiceOver audio · 92% word accuracy" (4 s) | "She cannot tell what she is paying. The standard checker says zero violations: it checks rules, never what is seen against what is heard. Most of the web is like this." |
| 0:20–0:30 | Flow picker to **Purchase flow**, Replay. The idle workbench with its one-sentence framing. | none (the framing sentence is the caption) | "Parity does the comparison. One agent walks the site as a sighted shopper and as a screen-reader user, and proves every place they disagree." |
| 0:30–1:12 | **Run the audit.** The Navigator walks product → cart → checkout → confirmation; badge *Muse Spark 1.3 · computer use*; the timeline shows action batches, a `nav.safety_check` row acknowledged by code, `audit_view` tool calls. On each screen: the Seer's grounding boxes on the screenshot, then cards streaming in, each with six green ticks; a red Verifier rejection row. The walk ends on "Pay R1,249" vs `button, "Submit"`. Replay sped to fit, chip "Replay · 1.7×". **The 4 Nov purchase bundle (commit 77c3b34, 34 verified, six ticks) used all twelve agent turns without calling `finish`, so the header reads "Audit ended early" and the outcome line "did not finish within 12 turns": the spotlight at 1:08 owns it (the budget ended on the confirmation page after every screen was audited by code), which is the honest beat, not a flaw to hide.** | 0:32 the computer-use badge, caption "the agent drives the browser" (3 s); 0:40 the safety-check row in the timeline, caption "safety check answered by code" (3 s); 0:50 the grounding boxes on the screenshot, caption "grounding: what a sighted user sees" (3 s); 1:00 a card's six ticks, caption "six code checks, all passed" (3 s); 1:04 the red rejected row, caption "a claim that failed: rejected" (3 s); 1:08 the header outcome line "Audit ended early", caption "12-turn budget spent; all four screens audited" (4 s) | "One agent does the walking: Muse Spark 1.3 with Meta's computer-use tool. It sees a screenshot and returns actions; code runs only the kinds it allows and answers every safety check. Two more tools. *audit_view* captures the screenshot, Chrome's accessibility tree and axe-core; Spark's perception grounding marks what a sighted user sees as boxes; a second Spark call reads both and quotes where they disagree. Six code checks gate each claim: seen on screen, a real element, an exact quote, different words, not in axe, not a duplicate. A failed claim is this red row. And *finish* is refused until the screen has been audited." |
| 1:12–1:24 | Open the **Trace** drawer: the table of model calls (stage, model, request ID, tokens, latency, cost, cache). Scroll once. | 1:14 the model column over the judge rows, caption "judge ×4 in parallel · contributor tier" (5 s) | "Every call is in the trace: stage, model, request ID, tokens, cost. One agent; code is the orchestrator. The judge runs four at a time and fails closed." |
| 1:24–1:42 | Close the trace. On the hero card: **Proposed fix** (badge *fixer*), open the **Diff**; **Re-audit**: "Gap closed: now says Pay R1,249" (badge *code · sandbox*, then *comparison*); click **Approve** with the reason; **Download fix.patch** appears in the header. | 1:25 the proposed fix, caption "the smallest HTML change" (3 s); 1:31 the re-audit line, caption "re-audit: now says Pay R1,249" (3 s); 1:36 the Approve button, caption "a human approves every fix" (2 s); 1:39 Download fix.patch, caption "the patch is yours" (3 s) | "After the walk, Spark proposes the smallest HTML change for each finding, four at once. Code loads the patch in a sandbox and checks the name rule; Spark compares again: now it says *Pay R1,249*. Nothing ships by itself: a developer approves, and the patch is theirs." |
| 1:42–1:56 | **Eval** tab (or "About & Evals" if the rename has shipped): the headline row (85% / 99% / axe-core 0% on 38 seeded faults, 20 clean controls; $0.37 and 8 m 15 s per 3 pages), then the ablation rows. | 1:43 the Parity (full) row, caption "85% recall · 99% precision · $0.37" (5 s); 1:50 the three ablation rows, caption "both eyes, and the code gate" (4 s) | "Thirty-eight faults built to pass axe-core: eighty-five percent found, ninety-nine percent precision, thirty-seven cents per three pages. Screenshot alone, seventeen. Tree alone, seventy-five. It needs both eyes and the code gate between them." |
| 1:56–2:40 | **Live on a page you choose**: type the address, affirm, run; the guard's rows in the timeline (public address, robots.txt). Cut to the finished run opened by its link, chip "Live · <date> · <time> · <cost>". Header: axe-core's count beside Parity's verified and rejected counts. Select the hero finding: its box on the screenshot, the card, the Screen reader panel's announced name; expand **Check details** (six ticks). Scroll to the red rejected row. Then type `ticketmaster.com`: "blocked by site: bot challenge" in seconds at $0. **Page: BBC News by default** (run `20261103-182732-d823d351`: a search magnifier announced as "Open menu", serious; a second claim, that the magnifier is not announced at all, rejected on the exact-quote check). **If the Meta-page comparison wins, the same shots on that run and the three bracketed phrases change.** | 1:57 the address field, caption "any public page, read-only" (3 s); 2:03 the guard rows in the timeline, caption "public address · robots.txt honoured" (3 s); 2:09 the header counts, caption "axe-core 2 · Parity 2 verified · 1 rejected" (4 s); 2:14 the magnifier box on the screenshot, caption "sees a magnifier" (3 s); 2:18 the announced name, caption "hears: button, Open menu" (4 s); 2:23 the six ticks in Check details, caption "six checks passed" (3 s); 2:27 the red rejected row, caption "rejected: the tree says Open menu" (4 s); 2:36 the Ticketmaster status line, caption "a bot wall: stopped, $0" (3 s) | "Now a page we did not write, live and read-only: the same agent, one screen, a guard that refuses private addresses and honours robots.txt. [BBC News], two minutes, nine cents. axe-core reports two violations; Parity finds a barrier it does not: [a search magnifier that a screen reader calls *Open menu*]. The finding carries its proof: the box the sighted pass saw, the exact name the tree announces, six checks passed. A second claim, [that the magnifier is not announced at all], failed the exact-quote check and was rejected: Parity reports only what it can prove. And when a site puts up a wall, it stops in seconds at no cost and says so." |
| 2:40–2:50 | Back on the finished Checkout run from 0:00 (the bookend), the Pay card selected, its badges in view; the URL as the context chip. | 2:41 the card's badge stack (grounding · comparison, code · verifier, judge, fixer), caption "Spark sees, compares, judges, fixes" (4 s); 2:45 the Voice badge, caption "Voice Transcribe: real VoiceOver audio" (3 s); 2:48 the URL chip | "Three Meta models, one key: Spark sees, drives, compares, judges, fixes; Voice Transcribe makes real VoiceOver audio evidence. Findings, not compliance. Try it, no login." |
| 2:50–2:55 | End card: Parity, the URL, the repository. | none | *(silence)* |

**Where the 22 extra seconds for the live beat came from.** The problem overlay (14 → 12 s), the walk (48 → 42 s, the replay sped from 1.5× to 1.7×), the trace (16 → 12 s, the contributor tier moved from the narration to a caption), the fix (20 → 18 s), the eval (18 → 14 s, the no-grounding sentence dropped: the row is on screen) and the close (14 → 10 s). Nothing named in v3 is lost; the Tooling beats keep every term.

**The live page: BBC News or a Meta page?** Facebook, Marketplace, Instagram and Threads are excluded by Facebook's own terms (no automated access to Facebook Products without permission), which our rule on third-party sites makes binding. Meta's corporate and product sites (meta.com, about.meta.com, ai.meta.com, llama.com, developers.facebook.com) were checked for robots.txt and terms and run live on the hosted app on 4 Nov; the decision, the run id and the reason are recorded here once the comparison is in: _pending the subagent report_. The criteria, in order: a barrier a judge grasps in two seconds from sighted text vs announced name; severity serious or critical; a clean frame; a recognisable brand; two minutes and ten cents; and the framing (auditing the sponsor's page in the sponsor's hackathon reads as confidence if the finding is real and the tone is respectful, and as a cheap shot if it is minor).

**Why these beats.** The cold open is the whole problem in four seconds with no explanation (a judge hears "Submit" while reading "Pay"), so Voice is the opener. The walk beat is where Tooling is scored: it names the auditor agent (computer use plus the two gated function tools; `previous_response_id` chaining is in the README), the Seer (perception grounding), the Comparator (multimodal, quoting the tree), the Verifier (code), and shows the refusal loop. The Trace drawer stands in for an architecture slide: the product showing its own orchestration, and its line "one agent; code is the orchestrator" answers the stage-two question (why not a crew?) before it is asked; the full argument is the README's "Why one agent with gated tools, not a crew" paragraph. The live beat is now the second-longest because it is the only beat that proves the system on a page we did not seed, and it shows the Verifier refusing a claim on that page, which is the honesty the rubric's Impact score rewards. Dropped since v2: the W3C Replay beat and the Muse Wonder comparison (both in the Eval tab and README). Zoom in the edit only where a spotlight already points.

**Numbers spoken, all from the README (rule L9):** 0 violations; 38 faults, 20 clean controls; 85%, 99%; $0.37 and 8 m 15 s per 3 pages; 17%, 75%; 92% word accuracy (the 4 Nov checkout re-record; v3 said 96% from the 3 Nov take); BBC 2 m 7 s, $0.09; Ticketmaster: blocked in seconds at $0 (9 s on 3 Nov, 6.5 s on 4 Nov; the narration says "in seconds").

**Voice (3 Nov, after Gate G-V).** G-V passed at 0.96 word accuracy on the recorded checkout page (the transcript aligned to VoiceOver's own phrases, every hint spoken in full; a first take with the hints cut short scored 0.58 and was redone), so Voice is **primary evidence** on the **Checkout page Replay**: the Submit card plays the segment where VoiceOver says "Submit button", with the badge *Muse Voice Transcribe · real VoiceOver audio* and the agreement tick. The Purchase replay was not recorded with Voice; the cold open uses the Checkout replay for that reason, and the walk beat switches to Purchase.

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
