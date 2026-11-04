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
| **Sun 1** | Eval harness, baseline and ablations; 2–3 real-site runs; **tester session** (screen-reader user + front-end dev) | About & Evals table; one quote; one change made from feedback |
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

**Storyboard v5 (Wed 4 Nov, 21:50 SAST; prompt 28 D2; supersedes v4).** Built on §1c of prompt 28: the IBM Gatekeepers arc (the buyer's question, the problem as volume × error × consequence with a dated forcing function, the solution acting with remediation, impact as speed / scale / certainty) told demo-first over the product. What changed from v4, and why: (1) the buyer's question opens, and the user (the team shipping a checkout) and the job are named by 0:15, because v4 named only the beneficiary; (2) the problem block grows from 12 s to 23 s and carries five sourced figures (WebAIM 2026, not 2025), money and a dated law, because Impact is 30% and v4 had two figures and no cost; (3) "what we built" is one sentence at 0:35, before the walk; (4) the walk is the bundle re-recorded on 4 Nov evening with the contributor-tier judge (attempt 7: 31 verified over four screens in ten turns, finish called), so the "Audit ended early" beat is gone; (5) the live page is a shop page we did not write (books.toscrape.com, a published scraping sandbox: no terms bar it; FlySafair, Takealot and BBC were excluded by theirs), with the hero's class of barrier; (6) the close is a 44 s impact block with one Speed · Scale · Certainty card built from `latest.md` and the verified figures, ending on the person, the job and the theme, not on the URL; (7) every number is the README's (docs/28 ledger); jargon left the first 20 s ("accessibility tree", "word accuracy"); the narration is counted at or under 2.6 words a second per beat; the theme line (§10) is spoken once. Hard stop 2:55; everything that matters by 2:50; two cards of 10 s each and nothing else off the product.

**How the boxes and captions are made.** They are not added in the edit: the recording script (`data/demo-takes/record2.py`, git-ignored) drives the hosted app with Playwright at 1280×720 and, at the moments listed below, draws a **spotlight** in the page: a 2.5 px orange rounded rectangle around the element's real bounding box, with a **caption pill** (13 px, dark, at most six words) under it, held for the stated seconds and faded out in 250 ms. A spotlight never covers the element and never moves the page; at most one is on screen at a time; beats without a listed spotlight have none. The spotlights and captions are editorial (orange, dashed outline) so they cannot be mistaken for product UI. A separate **context chip** (grey, bottom-left) names the run where it matters: "Replay · recorded run · no model calls", "Live · 3 Nov · 2 m 7 s · $0.09". The only things added in the edit are the voice-over, the VoiceOver audio segment at 0:00 and the end card.

**v5 table.** Time · on screen · spotlights and captions (seconds held; one at a time; ≤ 6 words a pill) · narration (words / seconds).

| Time | On screen (the product throughout) | Spotlights and captions | Narration |
|---|---|---|---|
| **1. Hook** 0:00–0:12 | Checkout page Replay, finished; the **Pay R1,249** card selected; the VoiceOver segment plays at 0:03 (the real recording mixed in at assembly, with 0.5 s of silence either side). Badge *Muse Voice Transcribe 1.0 · real VoiceOver audio*. Chip "Replay · recorded run". | 0:00 the address-bar style caption "Can a blind shopper pay on your checkout?" (3 s); 0:03 the Pay button in the screenshot, "a sighted shopper reads: Pay R1,249" (3 s); 0:06 the announced name in the Screen reader panel, "a screen reader says: Submit" (3 s); 0:09 scope caption "Built this week on Meta's Muse Spark and Voice Transcribe · Playwright and axe-core pre-existing" (3 s) | "A checkout button. A sighted shopper reads *Pay R1,249*. A blind shopper hears this." *(0.5 s · VoiceOver: "Submit button" · 0.5 s)* "Parity, built this week on Meta's Muse Spark and Voice Transcribe, is for the team shipping it." (31 / 12 = 2.6) |
| **2. Problem** 0:12–0:35 | Same screen. The axe-core badge **0 violations**. **Card A** 0:17–0:27 (10 s), in the workbench's style, five lines each with its source: "95.9% of top-million home pages fail WCAG · WebAIM, 2026" · "the best automated tool caught 41% of barriers · UK GDS, 2017" · "5,114 US suits in 2025 · 70% against online shops · UsableNet (vendor)" · "EU Accessibility Act: e-commerce since 28 Jun 2025 · fines to €100,000 · Germany, BFSG" · "one retailer: $46,000 legal fees + $13,000 to fix · WSJ, 2024". Back on the product at 0:27. | 0:13 the axe-core badge, "axe-core 4.14: 0 violations" (3 s); 0:28 the Voice badge, "real VoiceOver audio · 96% match on this replay" (3 s; the committed bundle's figure, re-recorded 4 Nov evening) | "Its job: prove a blind shopper can buy, and fix what stops them. axe-core reports zero violations: it checks rules, never what is seen against what is heard. Ninety-six percent of top home pages fail. Five thousand lawsuits last year, seventy percent against online shops. Europe's Accessibility Act covers e-commerce since June 2025; fines reach a hundred thousand euros." (59 / 23 = 2.6) |
| **3a. What we built** 0:35–0:45 | Flow picker → **Purchase flow**, Replay. The idle workbench with its one-sentence framing. | 0:36 the framing sentence, "one agent · gated tools · code orchestrates" (4 s) | "What we built: one agent with gated tools, and code as the orchestrator. Spark sees and drives; six code checks decide what counts as a finding." (26 / 10 = 2.6) |
| **3b. The walk** 0:45–1:20 | **Run the audit.** The Navigator walks product → cart → checkout → confirmation; the timeline shows action batches, a `nav.safety_check` row acknowledged by code, `audit_view` calls. On each screen the Seer's grounding boxes, then cards streaming in with six green ticks; a red Verifier rejection row. The walk ends with the agent's summary ("order … confirmed"). Chip "Replay · 1.7×". | 0:47 the computer-use badge, "Muse Spark · computer use drives the browser" (3 s); 0:54 the safety-check row, "safety check answered by code" (3 s); 1:00 the grounding boxes, "perception grounding: what a sighted user sees" (3 s); 1:06 a card's six ticks, "six code checks, all passed" (3 s); 1:10 the red rejected row, "a claim that failed: rejected" (3 s); 1:15 the header outcome line, "four screens · order confirmed · ten turns" (4 s; the bundle's own count, attempt 7) | "Muse Spark's computer-use tool walks the shop: product, cart, payment, confirmation. It returns actions; code runs only the kinds it allows and answers every safety check. On each screen Spark's perception grounding marks what a sighted shopper sees; a second Spark call reads it against Chrome's accessibility tree and quotes where they disagree. Six code checks gate each claim: seen on screen, a real element, an exact quote, different words, not in axe, not a duplicate. A claim that fails is this red row. The walk ends at the confirmation." (90 / 35 = 2.6) |
| **3c. The trace** 1:20–1:30 | Open the **Trace** drawer: stage, model, request ID, tokens, latency, cost, cache. Scroll once. | 1:22 the table, "every call: model · request ID · cost" (4 s); 1:26 the judge rows, "judge · contributor tier · high effort" (3 s; true on both committed bundles, recorded after 0ccc2fa) | "Every call is in the trace: stage, model, request ID, cost. The judge runs four at a time and fails closed to a human." (24 / 10 = 2.4) |
| **3d. The useful result** 1:30–1:50 | Close the trace. On the hero card: **Proposed fix** (badge *fixer*), the **Diff**; **Re-audit**: "Gap closed: now says Pay R1,249" (badge *code · sandbox*, then *comparison*); click **Approve** with the reason; **Download fix.patch** appears. | 1:31 the proposed fix, "the smallest HTML change" (3 s); 1:36 the re-audit line, "re-audit: now says Pay R1,249" (3 s); 1:41 the Approve button, "a human approves every fix" (3 s); 1:45 Download fix.patch, "the patch is yours" (3 s) | "After the walk, Spark proposes the smallest HTML change. Code loads it in a sandbox; Spark compares again: now it says *Pay R1,249*. That is the useful result: a proven finding, a fix a re-audit confirms, and a developer's approval. Nothing ships by itself; the patch is theirs." (49 / 20 = 2.5) |
| **3e. Live** 1:50–2:10 | **Live on a page you choose**: type `books.toscrape.com/catalogue/category/books/travel_2/`, affirm, run; the guard rows in the timeline. Cut to the finished run `20261104-193842-92175beb` by its link, chip "Live · 4 Nov · 1 m 27 s · $0.008". Header: axe-core 4 beside Parity 4 verified. Select a star-rating card: its box on the screenshot, the Screen reader panel's empty name; **Check details** (six ticks). Then type `ticketmaster.com`: "blocked by site: bot challenge" in seconds at $0 (the existing `tm.webm`). | 1:51 the address field, "any public page, read-only" (2 s); 1:53 the guard rows, "public address · robots.txt honoured" (3 s); 1:57 the header counts, "axe-core 4 · Parity 4 verified" (3 s); 2:00 the stars' box, "sees: 4 out of 5 stars" (3 s); 2:03 the announced name, "hears: nothing" (3 s); 2:07 the Ticketmaster status line, "a bot wall: stopped, $0" (3 s) | "Now a shop page we did not write, read-only. axe-core reports four issues, none of these: a shopper picks by the stars; a screen reader hears nothing. Every check passed. A bot wall stops it in seconds, at no cost." (40 / 20 = 2.0; the extra seconds let the finished run's four shots breathe) |
| **4. Impact** 2:10–2:50 | **About & Evals** tab: the headline row, the ablation rows, the judge row of the sweep. **Card B** 2:28–2:38 (10 s), "Speed · Scale · Certainty", three columns in the workbench's style: *Certainty*: "85% recall · 99% precision · 0 false positives" / "38 seeded faults axe-core passes · 3 runs" / "every finding carries proof · a human approves every fix"; *Speed*: "8 m 15 s per 4-page flow" / "about 3 expert hours a page · Deque, 2013 (vendor)" / "the see-vs-hear gap, not a full audit"; *Scale*: "$0.37 a flow · $0.04 with today's judge (n = 1)" / "manual audit $100–$250 a page · vendor, 2026" / "43 million blind · 295 million moderate–severe · Lancet, 2020" / "$674bn US disposable income · AIR, 2026". Then the bookend: the finished Checkout run, the Pay card selected, badges in view, the URL chip. | 2:11 the dogfooding beat as a caption (not narrated), "tested on Parity's own workbench with VoiceOver" (4 s); 2:15 the Parity (full) row, "85% recall · 99% precision · 38 faults axe passes" (4 s); 2:19 the three ablation rows, "screenshot 17 · tree 75 · both + code gate 85" (4 s); 2:23 the judge row, "judge: contributor tier · 94% agreement · 1/18 the cost (n = 2)" (4 s); 2:39 the theme caption, "Push the Frontier (software): a new sense for software" (4 s); 2:44 the badge stack, "Spark sees, drives, compares, judges, fixes · Voice Transcribe hears" (3 s); 2:47 the URL chip "parity-u7lcbbxuia-uc.a.run.app · no login" | "Thirty-eight faults built to pass axe-core: eighty-five percent found, ninety-nine percent precision, no false positives. Screenshot alone, seventeen; tree alone, seventy-five; both with the code gate, eighty-five. For the seller: thirty-seven cents and eight minutes a flow, caught before release instead of the lawsuit, the fine or the lost sale. For the shopper: forty-three million blind people, and a checkout they can finish. Push the Frontier, in software: an agent with a new sense, to see a page as a sighted shopper, hear it as a screen reader, and prove where they differ. Findings, not compliance. Try it, no login." (99 / 40 = 2.5) |
| **5. End card** 2:50–2:55 | Parity · "Parity closes the gap between what's seen and what's heard." · parity-u7lcbbxuia-uc.a.run.app · github.com/TaahirSuleman/parity · "Built this week on Meta's Muse Spark and Voice Transcribe". Held 5 s. | none | *(silence)* |

Totals: narration 418 words over 170 s of speech (2.5 a second; every beat at or under 2.6; re-balanced 4 Nov 22:40: the live block 20 s, the impact block 40 s, the dogfooding line a caption); cards 20 s; product on screen 155 of 175 s (89%); runtime 2:55.

**Rubric coverage map (v5).**

| Seconds | Beat | Impact 30 | Tooling 25 | Depth 20 | Demo 25 | Best Agentic (autonomy · effectiveness · usefulness) | Indie (creativity · ambition · works) |
|---|---|---|---|---|---|---|---|
| 0:00–0:12 | Hook, user, job, scope | the person and the buyer's question | Voice Transcribe badge | — | the cold open | — | creativity: hear vs see |
| 0:12–0:35 | Problem | volume, error, consequence, the dated law | — | — | — | — | — |
| 0:35–1:20 | What we built, the walk | — | computer use, safety checks, perception grounding, the multimodal comparison | the six checks, the red row | the product working | autonomy: the agent walks and audits | ambition |
| 1:20–1:30 | Trace | — | every call's model and cost; the contributor tier | code orchestrates; observability | — | — | — |
| 1:30–1:50 | Fix, re-audit, Approve, patch | the useful result | fixer; the comparison inside the re-audit | the sandbox and the name rule | the human click | effectiveness; a human gate | — |
| 1:50–2:10 | Live | a page we did not write | — | the guard | holds up live; the bot wall | usefulness | works |
| 2:10–2:50 | Impact | KPIs per flow → seller → shopper; the theme | the ablations; the sweep's judge row | the eval, n stated | — | — | — |
| 2:50–2:55 | End card | — | — | — | — | — | — |

Share of runtime: Impact 63 s (36%), Tooling 60 s (34%), Depth 45 s (26%), Demo throughout (the product is on screen 89% of the time; one Live run). Every Meta capability is named where its artefact is on screen: computer use (the timeline's action batches and safety-check row), perception grounding (the boxes), the multimodal comparison (the quote on the card), the judge (the trace rows), the fixer (the diff), Voice Transcribe (the badge and the audio).

**Wording rules kept (Muse Code R6):** recall is "on our test store, thirty-eight faults built to pass axe-core", never "finds the barriers"; "a proven finding" refers to what Parity reports; "six checks" only on bundles that carry six; "96% match on this replay"; the turn count is the bundle's own; "the standard checker" is named axe-core 4.14; "Three Meta models" is gone (Spark in two tiers, and Voice Transcribe).

**The purchase-walk beat, two versions.** (a) A bundle that finished: the table above, on attempt 7 (4 Nov evening, ten turns). (b) Not needed: attempts 6 and 7 both finished; attempt 2's "budget spent after all four screens were audited" line is retired.

**Stage 3 (watched live in a room).** Sound off, the first 10 s read: "Can a blind shopper pay on your checkout?" → "a sighted shopper reads: Pay R1,249" → "a screen reader says: Submit" → the scope line. The last 20 s read the card's numbers, the theme caption and the URL chip.

**Accessibility of the video.** Burned-in captions for all narration and for the VoiceOver audio ("[VoiceOver] Submit button"); an SRT uploaded with it; every spotlight has a text pill; 13 px pills at 720p are re-rendered at 1080p; no information by colour alone (the red row's pill says "rejected").

<details><summary>Storyboard v4 (Wed 4 Nov, 13:30 SAST): superseded by v5 above; kept for the record</summary>


**Theme line (decided 4 Nov 19:00 SAST, §10; carried into v5 at Checkpoint 2 of prompt 28):** the video names the problem statement once, on screen and spoken, with its one-sentence justification: caption "Push the Frontier (software): a new sense for software"; narration "Push the Frontier, in software: Parity gives an agent a new sense, to see a page as a sighted shopper and hear it as a screen reader, and to prove where they differ." v4 below has no theme line; v5 adds it.

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
| 1:42–1:56 | **About & Evals** tab: the headline row (85% / 99% / axe-core 0% on 38 seeded faults, 20 clean controls; $0.37 and 8 m 15 s per 3 pages), then the ablation rows, then a quick scroll past the per-stage model tables and the SAM 3.1 note (on screen only, no added narration). | 1:43 the Parity (full) row, caption "85% recall · 99% precision · $0.37" (5 s); 1:50 the three ablation rows, caption "both eyes, and the code gate" (4 s) | "Thirty-eight faults built to pass axe-core: eighty-five percent found, ninety-nine percent precision, thirty-seven cents per three pages. Screenshot alone, seventeen. Tree alone, seventy-five. It needs both eyes and the code gate between them." |
| 1:56–2:40 | **Live on a page you choose**: type the address, affirm, run; the guard's rows in the timeline (public address, robots.txt). Cut to the finished run opened by its link, chip "Live · <date> · <time> · <cost>". Header: axe-core's count beside Parity's verified and rejected counts. Select the hero finding: its box on the screenshot, the card, the Screen reader panel's announced name; expand **Check details** (six ticks). Scroll to the red rejected row. Then type `ticketmaster.com`: "blocked by site: bot challenge" in seconds at $0. **Page: BBC News by default** (run `20261103-182732-d823d351`: a search magnifier announced as "Open menu", serious; a second claim, that the magnifier is not announced at all, rejected on the exact-quote check). **If the Meta-page comparison wins, the same shots on that run and the three bracketed phrases change.** | 1:57 the address field, caption "any public page, read-only" (3 s); 2:03 the guard rows in the timeline, caption "public address · robots.txt honoured" (3 s); 2:09 the header counts, caption "axe-core 2 · Parity 2 verified · 1 rejected" (4 s); 2:14 the magnifier box on the screenshot, caption "sees a magnifier" (3 s); 2:18 the announced name, caption "hears: button, Open menu" (4 s); 2:23 the ticks in Check details, caption "every check passed" (3 s); 2:27 the red rejected row, caption "rejected: the tree says Open menu" (4 s); 2:36 the Ticketmaster status line, caption "a bot wall: stopped, $0" (3 s) | "Now a page we did not write, live and read-only: the same agent, one screen, a guard that refuses private addresses and honours robots.txt. [BBC News], two minutes, nine cents. axe-core reports two violations; Parity finds a barrier it does not: [a search magnifier that a screen reader calls *Open menu*]. The finding carries its proof: the box the sighted pass saw, the exact name the tree announces, every check passed. A second claim, [that the magnifier is not announced at all], failed the exact-quote check and was rejected: Parity reports only what it can prove. And when a site puts up a wall, it stops in seconds at no cost and says so." |
| 2:40–2:50 | Back on the finished Checkout run from 0:00 (the bookend), the Pay card selected, its badges in view; the URL as the context chip. | 2:41 the card's badge stack (grounding · comparison, code · verifier, judge, fixer), caption "Spark sees, compares, judges, fixes" (4 s); 2:45 the Voice badge, caption "Voice Transcribe: real VoiceOver audio" (3 s); 2:48 the URL chip | "Three Meta models, one key: Spark sees, drives, compares, judges, fixes; Voice Transcribe makes real VoiceOver audio evidence. Findings, not compliance. Try it, no login." |
| 2:50–2:55 | End card: Parity, the URL, the repository. | none | *(silence)* |

**Where the 22 extra seconds for the live beat came from.** The problem overlay (14 → 12 s), the walk (48 → 42 s, the replay sped from 1.5× to 1.7×), the trace (16 → 12 s, the contributor tier moved from the narration to a caption), the fix (20 → 18 s), the eval (18 → 14 s, the no-grounding sentence dropped: the row is on screen) and the close (14 → 10 s). Nothing named in v3 is lost; the Tooling beats keep every term.

**The live page: BBC News, decided 4 Nov.** Facebook, Marketplace, Instagram and Threads are excluded by Facebook's terms (no automated access to Facebook Products without permission), and the comparison found that every Meta corporate and product site (meta.com, about.meta.com, ai.meta.com, llama.com, developers.facebook.com, whatsapp.com, transparency.meta.com) is governed by the same terms through its robots.txt notice or footer, so none may be audited. The two Meta Open Source properties whose terms permit browsing (opensource.fb.com, react.dev) were run live on the hosted app: react.dev/learn gave nine findings in one shape (a sidebar expand chevron announced as `image, ""`), serious but arguable and with no Meta mark on screen, at $0.66; opensource.fb.com/projects gave nothing verified and two claims refused at $0.003. BBC News (run `20261103-182732-d823d351`, 3 Nov) stays: the only run whose finding a judge grasps in two seconds (a search magnifier announced as "Open menu", serious), with a clean frame, a famous neutral brand, a red rejected row, two minutes and nine cents. Putting "serious" on the sponsor's flagship docs for an arguable finding would read as a reach. Two consequences for the recording: (1) visitor runs are evicted 24 hours after they finish, so the 3 Nov run's link dies between 20:29 and 21:29 SAST on 4 Nov and the live beat is recorded before then (the clip, not the link, is the deliverable); (2) that run predates the sixth check, so its cards carry five ticks and the 2:23 caption reads "every check passed", not "six". A fresh BBC run on 4 Nov landed on BBC's consent dialog and verified nothing, so the re-run is not a safe substitute.

**Why these beats.** The cold open is the whole problem in four seconds with no explanation (a judge hears "Submit" while reading "Pay"), so Voice is the opener. The walk beat is where Tooling is scored: it names the auditor agent (computer use plus the two gated function tools; `previous_response_id` chaining is in the README), the Seer (perception grounding), the Comparator (multimodal, quoting the tree), the Verifier (code), and shows the refusal loop. The Trace drawer stands in for an architecture slide: the product showing its own orchestration, and its line "one agent; code is the orchestrator" answers the stage-two question (why not a crew?) before it is asked; the full argument is the README's "Why one agent with gated tools, not a crew" paragraph. The live beat is now the second-longest because it is the only beat that proves the system on a page we did not seed, and it shows the Verifier refusing a claim on that page, which is the honesty the rubric's Impact score rewards. Dropped since v2: the W3C Replay beat and the Muse Wonder comparison (both in the Eval tab and README). Zoom in the edit only where a spotlight already points.

**Numbers spoken, all from the README (rule L9):** 0 violations; 38 faults, 20 clean controls; 85%, 99%; $0.37 and 8 m 15 s per 3 pages; 17%, 75%; 92% word accuracy (the 4 Nov checkout re-record; v3 said 96% from the 3 Nov take); BBC 2 m 7 s, $0.09; Ticketmaster: blocked in seconds at $0 (9 s on 3 Nov, 6.5 s on 4 Nov; the narration says "in seconds").

**Voice (3 Nov, after Gate G-V).** G-V passed at 0.96 word accuracy on the recorded checkout page (the transcript aligned to VoiceOver's own phrases, every hint spoken in full; a first take with the hints cut short scored 0.58 and was redone), so Voice is **primary evidence** on the **Checkout page Replay**: the Submit card plays the segment where VoiceOver says "Submit button", with the badge *Muse Voice Transcribe · real VoiceOver audio* and the agreement tick. The Purchase replay was not recorded with Voice; the cold open uses the Checkout replay for that reason, and the walk beat switches to Purchase.


</details>

## 10. Problem statement [decided 4 Nov 2026, 19:00 SAST: Push the Frontier (software)]

**The answer on the form: Push the Frontier.** Until 4 Nov this section said Build for Your World with Push the Frontier as the fallback. The builder reversed it after reading both statements against what Parity can honestly claim. The Impact rubric scores "does it fit into one of the problem statements", so either fit earns the point; the choice is about which story the evidence carries and which question a judge then asks.

**Both sides, as weighed.**

| | Build for Your World | Push the Frontier (software) |
|---|---|---|
| The organisers' words | "Solve a problem you know firsthand, free up time and mental space, and make something possible that wasn't before." Kickoff: a problem "that you are an expert at, but that's keeping you up at night." | "Use Meta's models to tackle challenges in software, robotics, manufacturing, energy, materials and beyond. Give a machine a new capability… Show us what becomes possible when these models meet the real world." Kickoff: "bring something new to the world with the Meta models." |
| What Parity can say | We ship web software whose users include screen-reader users, and Parity frees a front-end lead from manual screen-reader passes before a release. | Software is named in the statement. Parity gives an agent a new capability: to see a page as a sighted shopper and hear it as a screen-reader user, prove where the two differ, and fix it. |
| The evidence behind it | Thin. The builder is not an accessibility practitioner or a screen-reader user; no real tester has used Parity; the honesty rules forbid implying one. | Measured. axe-core 4.14 reports 0 violations on the demo checkout; the best of ten automated tools caught 41% of barriers (UK GDS, 2017); the ablations show the capability comes from the models (17% from the screenshot alone, 75% from the tree alone, 85% with both and the code gate); computer use reaches the order confirmation; real VoiceOver audio becomes evidence through Voice Transcribe. |
| The question a judge asks next | "Who are you to this problem?" The answer invites the "who benefits and how much" probe at Parity's weakest point. | "Is it really new?" The answer is the numbers above and the Tooling beats the video already shows, so nothing has to bend to fit. |
| Fit with the Indie framing | Neutral. | "Creativity, technical ambition, and whether it works": ambition pairs with this statement. |
| Risk | A firsthand claim we cannot back. | The statement's examples lean physical (robotics, energy), so a judge may read "frontier" as hardware. Held by naming the clause: software. |

**Decision.** Push the Frontier (software). The reasons, in order: the statement names software and "give a machine a new capability", which is Parity's actual claim; that claim is the one the evidence supports with measured numbers, where Build for Your World would need a firsthand story the rules of honesty do not allow us to supply; and every essay and Tooling beat already argues it, so the fit costs no rewriting.

**Where it is said (one wording everywhere).**
- **Video (storyboard v5, block 1 or the impact close):** caption "Push the Frontier (software): a new sense for software"; narration, spoken once: "Push the Frontier, in software: Parity gives an agent a new sense, to see a page as a sighted shopper and hear it as a screen reader, and to prove where they differ." The buyer (the team shipping a checkout) and the beneficiary (the blind shopper) stay in the first 15 s, so "who benefits" is answered without a firsthand claim.
- **Form:** the radio set to Push the Frontier; the Project Description's first paragraph carries the same sentence (docs/21 "Problem statement").
- **README:** unchanged; it does not name a theme.

## 11. External pages: what exists, what ships before the freeze, what waits [D11, decided 1 Nov evening]

**The facts first.**
- Parity already audits pages we do not own, from the command line only: `parity audit <url> --goal … --public` runs the same pipeline behind the
  read-only guard (doc 19 §17: no irreversible clicks, no credential or card typing, no form submission, robots.txt honoured, bot walls and logins
  end the run). Two anonymised samples ship as Replay bundles and show in the About & Evals tab: Site A (two screens, six verified findings axe-core does
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
