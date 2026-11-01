# Judge Panel Evaluation: Callback · Claim Clock · First Notice
**Status:** v1, Tue 27 Oct 2026 (D0) · **Panel stance:** an independent, sceptical simulation of Meta-team judges (Indie track). We wrote none of the material under review. · **Rubric:** `00-constitution.md` Art. I–II (Impact 30 / Tooling 25 / Depth 20 / Demo 25) · **Read in full:** 00, A, B, E, F, G, H, J of each pack; C, D (first half) and I skimmed or read · **Context:** `06-artefact-standard.md`, `04-winning-recipe.md`, `03-meta-ai-tooling-reference.md` (grep), `02-kickoff-stream-transcript.md` (grep), and the research report's ranking (treated as a hypothesis, see §10).

> Nothing has been built yet. Every score below is a forecast of how judges would score the submission on Nov 5–8, made from the plans. "Golden path" means the plan executes exactly as written. "Risk-adjusted" weights the score by the panel's estimate of what one employed person actually ships in 8 days.

---

## 0. Verdict

| Category (weight) | Callback golden | Callback risk-adj | Claim Clock golden | Claim Clock risk-adj | First Notice golden | First Notice risk-adj |
|---|---|---|---|---|---|---|
| Impact (30%) | 7.5 | 7.1 | 6.5 | 6.4 | 7.0 | 6.9 |
| Use of Meta AI tooling (25%) | 8.5 | 7.5 | 6.5 | 5.9 | 7.5 | 6.6 |
| Technical depth & execution (20%) | 9.0 | 7.3 | 9.0 | 8.1 | 8.5 | 7.4 |
| Demo (25%) | 9.0 | 7.2 | 7.0 | 6.5 | 7.5 | 6.7 |
| **Weighted total** | **8.43** | **7.25** | **7.12** | **6.62** | **7.55** | **6.86** |
| P(delivers golden path as written) | ≈20% | | ≈35% | | ≈25% | |

**Ranking: 1. Callback · 2. First Notice · 3. Claim Clock.** The ranking is the same on both bases.

**Bottom line.**
1. **Callback is the only pack whose golden path reaches the score a top-5 finish probably needs (roughly 8.3 or more, panel guess).** Its risk-adjusted score is still the highest of the three.
2. **Callback's biggest problem is scope, not the idea.** The plan as written has about a 1-in-5 chance of shipping intact.
3. **Claim Clock is the safest build and has the lowest ceiling.** Even its golden path (7.12) scores below Callback's risk-adjusted expectation (7.25).
4. **First Notice and Claim Clock are tied on expectation.** First Notice has the higher ceiling. Claim Clock has the higher floor, and it is the better fallback if Callback's perception spikes fail on D1 (§10).

**Priority actions:**
- Cut Callback's scope until P(full delivery) is about 40%.
- Re-time Callback from "yesterday's calls overnight" to "within five minutes of hang-up".
- Make the hero case one that only call and screen evidence can catch.

With those three changes the panel's risk-adjusted Callback forecast rises from 7.25 to about 8.0 (§8).

---

## 1. How we scored

**Golden path.** We assume every frame in B §3 is real, the eval tables are filled with numbers near target, and the video is produced as storyboarded. We then score it the way a Meta engineer would on a single-digit-minute pass: video first, README second, live URL third (constitution Art. I.2).

**Risk-adjusted.** For each project we estimate the probability of three outcomes, then take the expectation per category:
- **full:** the golden path ships;
- **core:** the main loop works, but one or two Meta capabilities are demoted or faked, and the eval is smaller;
- **degraded:** fragments only, a mostly replayed demo and few numbers.

The probabilities come from the component tables in §2–4. Scenario scores and arithmetic are reproducible: a local scratch script (`scores.py`, not committed).

**Calibration.** In a field of thousands of Indie entries:
- **7** means a competent, multimodal agent with numbers.
- **8** means judges remember it.
- **9** means "surprised even us", or a video people forward.

A top-5 finish probably needs an 8.3+ weighted average from several judges. That bar is a panel assumption, held with low confidence.

**Capacity reality check.** It is the same person in every pack, but each pack assumes different hours:

| Pack | Hours assumed | Weekday load while employed | Panel view |
|---|---|---|---|
| Callback (H §1, A-18) | ≈72 h | **8 h on Wed, Thu, Fri** | Unrealistic without leave; D1–D3 is where the skeleton must land |
| Claim Clock (H, A-19) | ≈9 focused h/day ≈ 70+ h | 9 h/day | Least realistic |
| First Notice (H §1) | ≈65 h | 6 h weekdays, 12 h weekend | Most honest |

**Credits.** The constitution grants $150 (Art. VI.1).

| Pack | Planned spend | Panel view |
|---|---|---|
| Callback (E §11) | ≤$300, limit $400 | over credits |
| Claim Clock (F §15) | ≈$147, limit $250 | no headroom |
| First Notice | **no build budget at all** | ≈$2.2 per incident (E §12) is ≈$176 for one pass over the 80-incident test set, before ablations, pass^3, judge validation or dev. It also refuses contributor IDs even for synthetic case data (E §4 "Not used") |

---

## 2. Callback, "Where social engineering gets rolled back"

### 2.1 Category scores

| Category | Golden / risk-adj | Evidence driving the score | Strongest judge objection | What moves it +2 |
|---|---|---|---|---|
| **Impact** | 7.5 / 7.1 | Sourced pain: vishing 11% of intrusions and the #2 vector; $5.29M per breach; £270–440M M&S/Co-op (B §6 CL-01–03). Dated clocks (CL-04, NYDFS CL-05). Named buyer and job (D §1). Honest conservative model: $20.5k a year for full coverage vs ≈1,600 analyst-hours, break-even at 0.39% of one breach (G §3–4) | "**Overnight is too late.** Your own source says hand-off takes 22 s (C §3), and DataPump has OAuth consent at +9 min (B §2). By morning the CRM is gone. Also, Okta/Entra/Falcon-style ITDR already flags 'reset → new factor from a hosting ASN' from logs alone." The headline compares Callback to a *full-coverage manual review that nobody does today* (G §3), so the dollars are small and counterfactual | Re-time to **per call, within 5 min of hang-up** (M-14 already targets per-call p95 ≤ 5 min, so this is a framing and trigger change, not new architecture). Pitch it as a *control* that revokes sessions before the OAuth grant lands. Get one real service-desk or SOC lead to time a manual review (B-1) and give a one-line verdict |
| **Use of Meta tooling** | 8.5 / 7.5 | The most Meta surfaces fused on one evidence coordinate system of the three: Voice DIARIZATION + keywords (C-02); Spark 0–1000 grounding → SAM 3.1 box-prompted tracking on **UI screen recordings**, a new medium for the documented "Spark decides what, SAM delivers pixels" combo (TR §6, §9.1); a 1M context with a cached risk digest (ADR-004); computer use with `pending_safety_checks` routed to the approver (C-11); Wonder escalation; background fan-out. Pre-registered ablations that delete a claim on a null result (F §5) | "In your hero case the **logs alone convict** (factor from AS64501 at +4 min, OAuth at +9 min), and your own rules baseline B-3 would flag it (F §4). The overturn on CB-0152 is also a log fact (VPN egress). So diarization and grounding are *shown*, not *decisive*." Also: "every real IdP has a factor API, so computer use is contrived (A-11)", and "SAM on a table row is decoration" (the pack concedes this may happen, AB-3) | Make the golden case **log-clean**: in-country residential IP, no OAuth yet, so B-3 says *benign*. Put the B-3 verdict on screen beside Callback's *contain*, which is won by the diarized caller pretext and the "verify panel never opened" frames. Make the overturn a **speaker hard negative** (B3: the *agent* says "new phone"). Then perception is visibly load-bearing |
| **Technical depth** | 9.0 / 7.3 | An exceptional design, the strongest of the three: strict contracts; a backend citation resolver (ADR-002); a two-key gate whose actuation follows Meta's Agents Rule of Two, with L3 in deterministic code and L4 by computer use after human approval (E §9); hash-chained intent-before-effect audit; replay re-deriving gate decisions bit for bit (E §10); 15-row threat model, each row with a test (E §12); calibrated logistic scorer with versioned thresholds; injection twins; a hash-committed blind draw (B §5) | "Eight agents, four services, three sandbox apps, a TTS + Playwright + log causal generator, SAM overlays, a synced scrubber, nine ablations and 24 twins, in 72 solo hours." The **D3 "walking skeleton" is almost the whole system** (H §1 D3 lists Dispatcher → Ear → Eye → Procedure ∥ Pretext → Trail → verifier → Second Look → gate → L3 → Undo → Clock → audit/trace/replay, deployed) | Ship a genuinely thin D3 skeleton, and cut along the ladder *now* rather than under pressure (§8 #1). A smaller system that is complete scores higher than a large one that is half real |
| **Demo** | 9.0 / 7.2 | The best storyboard of the three. A dramatic, universally legible attack (fake CFO, "new phone"). The **three-modality snap** wow (F-06), where caption, masked click and log line jump to one scrubber position. Verifier overturn (F-07). Two keys turning and live state change (F-08/F-09). An honest miss (F-13). Receipts with run ID and commit (F-12). 72% working-product time (B §3) | "How much of this is real on the day?" Four perception stages plus computer use sit in series on the golden path. A public blind-draw log will expose misses live (B §5). Opening on a queue and a waveform is quieter than opening on the attack | **Open with 3 s of the (labelled synthetic) vishing call** with diarized captions, then the address bar. Show the 5-minute timeline "call ends → verdict → sessions revoked → OAuth attempt fails". Record the live segment only after the 10-clean-run gate (K7) |

### 2.2 Delivery probabilities (panel estimates, by D7 freeze)

| Component (pack ref) | P(as written) | Fallback and its cost |
|---|---|---|
| Causal synthetic corpus: 224 eval cases + 200 demo-day; TTS + G.711 degrade + Playwright bursts spliced onto the call timeline + 10k-user log noise (F §2, H D2) | 0.45 | ≈100 cases: 0.85 (wider CIs) |
| Gatehouse / Deskline / Ledgerly sandboxes (E §3) | 0.85 | Stub Ledgerly |
| Voice role accuracy ≥0.90 on degraded 2-speaker TTS (S1, K1) | 0.75 | Dual-channel: works, but diarization is no longer load-bearing |
| Spark grounding of control and row ≥4/5 (S2) | 0.75 | Spark boxes only |
| "Verify panel never opened" correct ≥0.90 (M-08), given keyframe gaps | 0.60 | Lower procedure accuracy |
| SAM 3.1 stable track on UI rows through scroll / AB-3 ≥10 pts | 0.50 / 0.30 | SAM becomes rendering only (ladder step 6) |
| Trail 1M + cached digest works / AB-4 ≥15 pts | 0.80 / 0.60 | — |
| Calibrated gate + Second Look | 0.80 | Hand-set τ |
| Computer-use rollback ≥4/5 within 25 steps (S3, K5) | 0.60 | API dry-run; AB-8 to the roadmap |
| UI incl. the synced three-pane scrubber with SAM overlays (R-16) | 0.50 polished / 0.80 usable | Static jump links |
| Eval of record: frozen 100, 9 ablations, pass^3, 24 twins, human-voiced 10, 3 baselines | 0.35 full / 0.75 core | Fewer ablations, smaller n |
| Hosted + replay + blind draw | 0.75 | Replay only |
| Video | 0.85 | — |
| **Scenario mix** | **full 0.20 · core 0.55 · degraded 0.25** | |

### 2.3 Assessments

**Stage-1 pass risk:** negligible (<2%). It calls the Meta API inside the product even in the degraded case.

**Theme fit:** "Build for Your World". The founder-fit claim ("the IT ticket queue is firsthand territory", A §2) is a stretch from DevOps tickets to IAM help-desk security, but it is credible enough. It is pass/fail, and it touches only one Impact sub-question.

**Anti-project proximity:** none on the list. Two watch-items:
- **Dual use.** The generator writes social-engineering scripts; they are held at public-TTP level (T15).
- **Employee-monitoring optics.** VS findings evaluate the help-desk agent's conduct, while the system card excludes "assessing staff" (F §12). Phrase the findings as process control, not people.

**Meta "surprise":** moderate-high. Two things a Meta engineer has probably not seen:
- SAM 3.1 box-prompt tracking on screen recordings of business UIs;
- one cross-modal evidence ID across turn, frame + mask, and log event.

Rule-of-Two split actuation also speaks Meta's own security language.

**First 20 seconds:** strong (8/10). The buyer's question, M&S/MGM-class stakes and "Callback" land with any engineer. The weakness is the word **"yesterday"**, which concedes the attacker a head start.

**Load-bearing vs swappable:**

| Capability | Verdict |
|---|---|
| Diarization | Load-bearing **only if** the demo shows a speaker hard negative. Otherwise any diarizing ASR swaps in |
| Spark grounding on UI frames | Load-bearing for VS checks, since logs record the reset, not the skipped check. The strongest claim |
| SAM 3.1 | Likely decorative (the pack says so) |
| 1M context | Load-bearing for campaign links if AB-4 holds. A SQL join is the obvious counter |
| Computer use | Swappable or unnecessary unless the console is credibly API-less |
| "One key, one coordinate system" | The true Meta-specific claim, and the Q8 answer handles it correctly (B §7) |

**Demo fragility:** the highest of the three: five model stages in series, plus computer use. Mitigations are good: the replay label, the K7 gate, and recording after the freeze.

**Bonus odds** (panel guesses, conditional on at least the core version shipping):

| Prize | Odds | Note |
|---|---|---|
| Best Agentic ($5K) | best fit of the three, ≈5–10% | It acts on a system of record, with a measured autonomy rate |
| Open weights | ≈0 | Correctly not targeted (A §3) |
| Most Viral | best clip of the three | Audience size dominates |
| Community | network-driven | — |

---

## 3. Claim Clock, "Same evidence, same decision, inside five days"

### 3.1 Category scores

| Category | Golden / risk-adj | Evidence driving the score | Strongest judge objection | What moves it +2 |
|---|---|---|---|---|
| **Impact** | 6.5 / 6.4 | A real, dated, regulated queue: ≈301,500 claims in 18 months; refunds 21–94% by firm; caution exception 0% vs >25% (B §6 CL-02–04). Sympathetic beneficiaries (scam victims). A credible product path beside Pay.UK's RCMS (C §1, A §1) | "**The address bar promises what the product can't do.** 'Would the bank down the road decide the same?' — yet the precedent store holds only *this* bank's own human-approved decisions (E §4 C-08). Cross-bank variance is policy and fraud mix, not handler noise." Also: "82% already close in 5 days (B §1); your conservative case is +£0.90 a claim, £0.18m UK, *with autonomy switched off* (G §3)." And a parochial UK scheme with heavy acronyms (APP, PSR, CDRS, RCMS, FOS) for a likely US-based panel | Measure **human inconsistency** on the invariance pairs: 2–3 people decide 20 pairs, then show "humans flipped X%, Claim Clock flipped Y%". Change the address bar to an in-bank promise ("Did we refuse Sam on the same facts we just refunded Dana?"). Headline overturn-proof consistency, not £/claim |
| **Use of Meta tooling** | 6.5 / 5.9 | Spark image + 0–1000 grounding on screenshots (C-02); Spark video on the ad; SAM 3.1 masks for redact-before-persist (C-03, ADR-005); Voice third-speaker coaching (F-09); crop-entailment self-verification by Second Look (C-07); Files API expiry; effort tiering | "**This is the most 'simple image analyzer'-adjacent of the three** (R-08). The warning you box on the screenshot is already in the bank's own intervention log (`interventions[].template_id`, E §7; B F-05 "matching PSP log W-GEN-01"), so vision confirms what the bank already knows. SAM on text PII is overkill, because the Spark rectangle suffices (AB-5 concedes the gain is on faces, ID photos and video)." Any VLM + OCR swaps in for most hops | Re-centre perception on what the bank **lacks** in structured form: scam chats and ads (typology, red flags, payee) and the coached call. Justify SAM with faces, ID documents and video, or drop it from Q8. If the open-weight prize is in play, make a Glimmer pre-egress redaction tier load-bearing; it is the most natural open-weight story of the three |
| **Technical depth** | 9.0 / 8.1 | The cleanest engineering thesis of the three:<br>• a deterministic Rulebook with Hypothesis property tests (E §10);<br>• the model never computes amounts or routes (ADR-001);<br>• adverse outcomes are human-only by state machine (E §6);<br>• typed Case Signatures + a materiality map, not embeddings (ADR-003);<br>• **metamorphic** invariance / sensitivity / identity-swap pairs (F §5), a genuinely sophisticated eval idea a Meta eval engineer will respect;<br>• consumer-harm rows in the threat model (T-12–T-16);<br>• FOS decisions as indicative real-world labels with careful licence handling (ADR-004) | "Labels are the author's reading of the rules (circularity, R-04). n = 50 cannot certify 2% (F §6 says so)." The F-07 conflict is a **planted pair** (CC-0093 is seeded), so "it found the case we put there" | A batch-level consistency audit over 30 noisy "prior handler" decisions, surfacing conflicts the author did not hand-place. A practitioner κ on 20 packs |
| **Demo** | 7.0 / 6.5 | Masks appearing (F-03); boxes on the warning and Continue button (F-04); rules ticking in code (F-05); a real verifier overturn, with a REPLAY fallback if none occurs (F-06); the side-by-side "material distance 0, opposite outcome" wow (F-07); refund scheduled with a veto window (F-08) | The wow is **intellectual, not visceral**, and it needs 20 s of UK context first. Boxes on chat screenshots look like every VLM demo. The F-02 strip and F-12 put "EU platform liability" and platform notices on screen, and Meta's platforms are the usual subject of that debate (R-07). That is an awkward look in front of Meta judges | Open on Dana's and Sam's two outcomes side by side (the human story) before any acronym. Cut the platform-liability and platform-notice beats. Show a consistency dashboard over a batch rather than one pair |

### 3.2 Delivery probabilities

| Component | P(as written) | Fallback |
|---|---|---|
| HTML→PNG pack generator with DOM truth (E ADR-005) | 0.90 | — |
| Ad MP4 from HTML animation + stills | 0.80 | Stills only |
| 160 packs with every pair type / 110 packs | 0.60 / 0.85 | Ladder step 7 |
| Grounding IoU ≥0.5 on ≥85% (S-1, K-1) | 0.70 | Quote-level OCR citations (the "points at" claim dropped) |
| Rulebook + property tests | 0.95 | — |
| 4 assessors + Second Look crop entailment | 0.80 | — |
| Signatures + precedent conflicts | 0.85 | — |
| SAM image masks / SAM video URL track | 0.75 / 0.50 | Rectangles; keyframe spans |
| Voice third-speaker recall ≥0.8 at 8 kHz (S-3) | 0.55 | Two-speaker claim only |
| 100 FOS labels + extraction ≥90% (S-2, K-2) | 0.60 | Drop M-15 |
| Eval incl. metamorphic pairs, full / core | 0.75 / 0.90 | — |
| UI (queue, review console, /proof, /trace) | 0.75 | — |
| **Scenario mix** | **full 0.35 · core 0.50 · degraded 0.15** | Capacity (A-19, 9 h/day) is the binding risk |

### 3.3 Assessments

**Stage-1 pass risk:** negligible. Even if grounding fails, Spark is still in the loop.

**Theme fit:** the weakest founder fit of the three. It admits "no first-hand UK claims-operations role" (C §3); this is pass/fail only.

**Anti-project proximity:** "simple image analyzer", moderate. The pack knows it (R-08, C §3 failure #1).

**Meta sensitivity:** scam adverts on social platforms (R-07; G §7 names platform liability as the second product line). Not disqualifying, but avoidable friction.

**Meta "surprise":** low-moderate. Crop-entailment self-verification and redact-before-egress are tidy. The novelty is in the eval method, not in the use of Meta.

**First 20 seconds:** 6/10 for a non-UK judge. "£14,200 APP claim" plus "five business days" needs a gloss. The 21–94% statistic is the hook, so lead with it.

**Load-bearing vs swappable:** the weakest of the three. Grounding is mostly for display and citation. SAM is overkill on text. Voice is present in about 30% of packs (F §3). The strongest Meta-specific claim is the one-key box → mask hand-off for redacted sharing, which only matters if sharing is central.

**Demo fragility:** the lowest of the three. The images-only skeleton is credible (H §2), and the deterministic core replays.

**Bonus odds:**

| Prize | Odds | Note |
|---|---|---|
| Best Agentic | weak (≈2–4%) | The hero agentic action (GREEN auto-schedule) is the one its own impact model switches off in the conservative case (G §3) |
| Open weights | 2–4% only if the Glimmer tier ships and is measured | — |
| Viral | low | — |

---

## 4. First Notice, "One incident, every regulator, on the clock"

### 4.1 Category scores

| Category | Golden / risk-adj | Evidence driving the score | Strongest judge objection | What moves it +2 |
|---|---|---|---|---|
| **Impact** | 7.0 / 6.9 | Live forcing functions: the CRA has been binding since 11 Sep 2026 via a web-only portal (CL-01/02); NIS2 24/72 h; GDPR 72 h; DORA 3,383 major incidents (CL-05). Large stakes (G §5). A relatable job: every engineer knows the 02:00 bridge. Honest conservative case: ≈5,075 h and ≈€0.40M a year, DORA only (G §3) | "**Applicability and deadline tracking across jurisdictions is an existing GRC category.** RadarFirst, OneTrust Incident & Breach and BreachRx have sold multi-regime notification decisioning with deadlines for years (panel background knowledge; the pack lists OneTrust, Archer and BreachRx as *unchecked*, 00 summary). incident.io and PagerDuty Scribe already transcribe bridges (C §3)." Low per-entity frequency, and "awareness is spoken" is the generator's own default (A-07, 70%) | Verify the whitespace today and reposition as the **evidence → awareness** layer that feeds those tools. Build the "**you're already 42 minutes late**" case: the incident tool's SEV declaration time lags the IC's spoken "confirmed" on the bridge, so the regulator's clock started before the paperwork says |
| **Use of Meta tooling** | 7.5 / 6.6 | Diarized turns become **playable clock anchors** (F-04); Spark grounds the chart's **axis ticks**, with pixel→time mapping done in code (ADR-004); 1M whole-incident context (C-05); computer use into a portal with no API, the **best-justified computer use of the three** (sourced CL-02); the executor's Submit intercept as key 2, with safety checks routed to the same human (ADR-005); plug-in rule texts as cached prefixes | "Chart reading with gridline verification is already a cookbook recipe (chart-explainer, TR Part B #16), so it is less surprising. SAM is admitted to have ≈ no effect on text (AB-07). Diarization is decisive only if the facts are not typed in chat." Is 2-minute precision feasible? On a 6-h axis one grid unit is 21.6 s, so the M-02 median ≤2 min target (F §4) needs tick localisation within about ±5 units | Drop SAM from Q8. Make the spoken-vs-typed discrepancy the hero (above) so diarization is decisive. Keep the axis-tick method, which is good craft, but report its precision honestly on the slice |
| **Technical depth** | 8.5 / 7.4 | Clockmaster is a pure function with DST fold and gap property tests (E §7). Verifier rules come from ESMA's published error list (E §10). Each plug-in carries `status` and `effective_from`, with UK CSR in shadow mode (E §6). Criteria are flagged coded or judged. Errors are asymmetric by design, with the earliest plausible anchor and M-01b reported separately (G §5). Read-back diff before submit. A Rule-of-Two session table | The F-08 failure catch is **seeded by construction** (an analyst edit carrying two ESMA-list errors). An LLM judge needs about 100 labelled items to validate (F §8). The same author wrote generator, labels and system (F §2) | Replace F-08 with a real inconsistency the verifier catches between model-drafted v1 and v2. Cut the LLM judge and use a human-rated sample |
| **Demo** | 7.5 / 6.7 | "**Clocks born from evidence**": a pin drops, a countdown starts, click the clock and hear the sentence (F-04). Chart vs call in UTC vs CET (F-05). The lex-specialis matrix (F-06). Verifier block (F-08). Computer-use filing with read-back (F-09). A cinematic war-room aesthetic (J) | No adversary and no rescue, so the drama is paperwork. The pack's own top risk is the "weakest wow" (R-03). Many moving parts: 3–7 speakers, recordings of 4–30 min against a 10-min file cap, so chunk linking is needed (F §2, ADR-003) | Lead with the late-clock reveal ("Your incident tool says 03:05. The regulator's clock started at 02:23"). Keep the golden case to 3–4 speakers and calls of ≤10 min |

### 4.2 Delivery probabilities

| Component | P(as written) | Fallback |
|---|---|---|
| Generator: 120 incidents, 1–3 recordings (4–30 min, 3–7 speakers), dashboards, status pages, chat, prior versions (F §2) / 80 incidents | 0.50 / 0.80 | Smaller n |
| Role accuracy ≥0.90 with 4–7 speakers, roster mapping, cross-chunk links (S1, K1) | 0.55 | L2 "candidates for human pick" |
| Awareness ≥90% within 15 min (M-01) | 0.65 | — |
| Gauge median ≤2 min / ≤5 min usable (M-02, S2) | 0.40 / 0.65 | Charts marked `judged` |
| 4 plug-ins + Clockmaster + Verifier (incl. S6 reading the regulatory texts) | 0.85 | Drop GDPR |
| Drafter + backend-verified citations | 0.80 | — |
| Filer CU ≥9/10 over 5 layouts / scripted fallback | 0.60 / 0.95 | Labelled scripted fill |
| SAM redaction | 0.70 | Cut (ladder 2) |
| Second Look + reconciliation | 0.75 | Cut (ladder 5) |
| UI: lanes, pins, playable clips, countdowns | 0.70 | — |
| Eval with validated LLM judge, full / core | 0.35 / 0.75 | Human-rated sample |
| No credit budget: P(overrun forces cuts) | 0.30 | — |
| **Scenario mix** | **full 0.25 · core 0.55 · degraded 0.20** | |

### 4.3 Assessments

**Stage-1 pass risk:** negligible.

**Theme fit:** the strongest founder fit of the three (SRE + DORA).

**The "DORA sequel" risk (R-01) is overweighted.** Meta's judges did not judge, and will not know, the IBM entry. It matters only for the new-work rule, which a fresh repo satisfies.

**Anti-project proximity:** none. Watch the legal-advice optics (R-09); it "proposes" and does not conclude.

**Meta "surprise":** moderate. The executor-intercept-as-second-key and axis-tick grounding are clever, but they extend documented cookbook patterns.

**First 20 seconds:** 7/10. "It's 2 a.m. Payments are failing in three countries" is relatable, but "who do we owe a report to" is a compliance question that only some judges feel.

**Load-bearing vs swappable:**

| Capability | Verdict |
|---|---|
| Diarization | Load-bearing if the spoken-vs-typed gap is demonstrated |
| Grounding | Load-bearing for occurrence and time zone, if precise enough |
| 1M context | Plausible (retraction slice) |
| Computer use | **Genuinely needed** (no API) |
| SAM | Not load-bearing |

**Demo fragility:** medium. The D3 skeleton deliberately omits the hard parts (H §2), which is honest but leaves diarization with 4+ speakers as a late risk.

**Bonus odds:**

| Prize | Odds | Note |
|---|---|---|
| Best Agentic | ≈2–4% | Autonomy stops at drafts and "ready" anchors (M-15) |
| Open weights | 2–4% only if the Glimmer pre-egress tier ships | — |
| Viral | low-moderate | The "click the clock, hear the sentence" clip |

---

## 5. Side by side

| Dimension | Callback | Claim Clock | First Notice |
|---|---|---|---|
| Stage-1 pass risk | <2% | <2% | <2% |
| Theme fit (Build for Your World) | Adequate (adjacent) | Weakest (disclosed gap) | Strongest |
| Anti-project proximity | None (watch dual use and monitoring optics) | "Simple image analyzer", moderate | None (watch legal-advice optics) |
| Meta-relationship risk | None | Scam-ad platform liability | None |
| Would a Meta engineer learn something? | Yes: SAM tracking on UI video; cross-modal evidence IDs; Rule-of-Two split actuation | Mostly the eval method (metamorphic pairs), not the Meta use | Some: axis-tick grounding, intercept as key 2 |
| First 20 seconds | 8/10 (but "yesterday") | 6/10 (UK jargon) | 7/10 |
| Meta capabilities truly load-bearing (pack as written) | 2–3 of 5 (grounding, 1M; diarization only with a hard negative) | 1–2 of 5 | 2–3 of 5 (CU genuinely; diarization and grounding conditionally) |
| Demo fragility | High | Low | Medium |
| P(golden path ships) | ≈0.20 | ≈0.35 | ≈0.25 |
| Ceiling (golden weighted) | 8.43 | 7.12 | 7.55 |
| Best Agentic fit | Strong | Weak (self-contradicted) | Medium-weak |
| Rough P(top-5 Indie), as written (low confidence) | ≈10% | ≈3% | ≈5% |

---

## 6. Totals, ranking and sensitivity

| | Golden weighted | Risk-adjusted weighted | Rank |
|---|---|---|---|
| Callback | 8.43 | **7.25** | 1 |
| First Notice | 7.55 | 6.86 | 2 |
| Claim Clock | 7.12 | 6.62 | 3 |

**What would flip the ranking.**
- **Claim Clock cannot overtake Callback on expectation.** Even with certain delivery, its ceiling (7.12) is below Callback's risk-adjusted 7.25. It wins only if Callback degrades badly, which we put at about 25%.
- **First Notice overtakes Callback only if** P(First Notice ships in full) ≥ ≈0.48 with no degraded mass, *and* Callback stays as written. Given its 3–7-speaker diarization and Gauge precision risks, the panel does not believe that.
- **Payoffs are convex** (only the top five pay). That favours the highest ceiling at comparable expectation, which is Callback again.

---

## 7. Head-to-head in the top-5 live final (judges watch the videos live and rank)

| Pairing | Verdict | Why |
|---|---|---|
| **Callback vs First Notice** | **Callback, ≈65/35** | An adversary, a rescue and a three-modality snap beat a countdown on watchability. Callback also fuses more Meta surfaces visibly. First Notice wins only if (a) Callback's perception frames are visibly replayed or wobbly, or (b) judges press "overnight is too late". (b) is fixable now (§8 #2). First Notice's "click the clock, hear the sentence" is crisp, but it is a document workflow at heart |
| **Callback vs Claim Clock** | **Callback, ≈75/25** | Claim Clock's video needs about 20 s of UK scheme context before the stakes land. Its wow (identical facts, opposite outcome) is a smart idea, not a spectacle. Claim Clock wins only on a judge panel that weights Technical Depth heavily and values the metamorphic eval, *and* if Callback's live segment visibly fails |
| **First Notice vs Claim Clock** | **First Notice, ≈60/40** | First Notice is more universal (any engineer knows incident bridges; GDPR and CRA reach well beyond UK banking) and justifies computer use honestly. Claim Clock has the human story (Dana vs Sam) and the more rigorous core. If both are delivered at the core level, Claim Clock's deterministic Rulebook and consistency proof could edge it with eval-minded judges (Agents 102 alignment) |

---

## 8. Top 5 improvements per project (ordered by expected score gain)

### Callback
| # | Change | Why (rubric cell) | Est. effect |
|---|---|---|---|
| 1 | **Cut scope now so the full version has a ≈40% chance, not ≈20%.**<br>• D3 skeleton = Ear → Eye (grounding only) → Procedure ∥ Pretext → Trail → gate (hand-set τ) → L3 revoke + trace/replay.<br>• Move Second Look, Undo and Clock to D4–D5.<br>• Cut Ledgerly, Wonder, the Clock narrative and memo (F-10), SAM tracking unless S2 passes cleanly, and the demo-day batch (200 → 40, or reuse test cases).<br>• Cut twins 24 → 8 and frozen test 100 → 60; the human-voiced slice becomes optional | Depth 20 and Demo 25 ("whether it works") | Largest single lever; with #2–#3 the risk-adjusted score goes 7.25 → ≈8.0 (scratchpad `improved.py`) |
| 2 | **Re-time from overnight batch to per call within 5 min of hang-up.**<br>• New address bar: "Did that MFA reset just hand an attacker the keys?"<br>• Show the timeline call end 09:16 → verdict 09:19 → sessions revoked 09:19 → DataPump consent at 09:21 fails | Impact 30: neutralises "too late"; a control, not a forensic report | Impact +0.5–1.0 |
| 3 | **Make the hero case log-clean and the overturn perceptual.**<br>• CB-0147 enrols from an in-country residential ASN with no OAuth yet, so the B-3 rules/ITDR baseline says *benign* on screen.<br>• Callback contains on the diarized pretext plus the "verify panel never opened" frames.<br>• CB-0152 becomes a B3 speaker hard negative (the agent says "new phone") | Tooling 25: proves the "only Meta" sentence inside the frame | Tooling +0.75–1.0, Demo +0.25 |
| 4 | **Open with the call itself, and add one real practitioner.**<br>• First 3 s: the (labelled synthetic) vishing audio with diarized captions.<br>• One service-desk or SOC lead times a manual review (B-1) and gives a one-line quote; this replaces the Trusona vendor-model inputs in G | Demo 25 (first 20 s); Impact 30 ("put it in someone's hands", Art. VII) | Demo +0.25, Impact +0.25–0.5 |
| 5 | **Make computer use honest or keep it off the critical path, and fix the budget.**<br>• Either declare Gatehouse a legacy console whose factor restore exists only in the UI (say so on screen), or keep API rollback as the default and show computer use only if K5 passes.<br>• Run all synthetic dev and ablations on `-contributor` to stay near the $150 credits (E §11 plans $300) | Tooling 25 (bolted-on CU costs credibility); execution | Removes a judge objection; protects the eval budget |

### Claim Clock
| # | Change | Why | Est. effect |
|---|---|---|---|
| 1 | **Measure human inconsistency and headline consistency, not £/claim.**<br>• 2–3 people decide 20 invariance pairs.<br>• Show "humans flipped X%, Claim Clock Y%, single prompt Z%".<br>• Stop leading with the "+£0.90 copilot" conservative case (G §3) | Impact 30, Depth 20 | Impact +0.5–1.0 |
| 2 | **Fix the address-bar promise.** Either reword it to an in-bank question, or add a shared, PII-free industry precedent exchange of typed signatures. That exchange also makes SAM redact-before-share load-bearing | Impact 30, Tooling 25 | Removes the sharpest objection |
| 3 | **Move perception to where it is decisive.**<br>• Scam chats and ads (typology, red flags, payee) and the coached call.<br>• Demote warning-screenshot boxing, which the PSP log already records.<br>• Justify SAM with faces, ID documents and video, or drop it from Q8 | Tooling 25; distance from the "simple image analyzer" anti-project | Tooling +0.5–0.75 |
| 4 | **De-parochialise and de-risk the video.**<br>• No APP/PSR/CDRS/RCMS before 0:30.<br>• Open on Dana vs Sam.<br>• Cut the EU platform-liability and platform-notice beats (Meta sensitivity, R-07) | Demo 25, first 20 s | Demo +0.5 |
| 5 | **Re-plan at realistic weekday hours** (A-19 assumes 9 h/day).<br>• Cut FOS to 30 decisions, Drift Sentinel and bulk-500.<br>• Either cut Glimmer, or make it the load-bearing pre-egress redaction tier and target the $10K open-weight prize, the most natural fit of the three | Execution; bonus | Raises P(full); optional bonus |

### First Notice
| # | Change | Why | Est. effect |
|---|---|---|---|
| 1 | **Run the whitespace check today** against RadarFirst, OneTrust Incident & Breach, BreachRx and ServiceNow IRM. Reposition as the evidence → awareness layer that feeds them, and claim no novelty for plug-in applicability or deadlines | Impact 30 ("could this become something people use") | Avoids a credibility hit |
| 2 | **Build the "you're already 42 minutes late" hero case.** The ticket or incident tool's declared time trails the IC's spoken "confirmed". Show the rules-only baseline (B2) and a chat-only reading missing it | Impact 30, Tooling 25 (makes diarization decisive; counters the circularity of A-07) | Impact +0.5, Tooling +0.5, Demo +0.5 |
| 3 | **Cut to the bone and set a budget.**<br>• Drop SAM (AB-07), the validated LLM judge (≈100 labels), the UK CSR shadow plug-in and layouts 3–5.<br>• Keep the golden case at 3–4 speakers and calls of ≤10 min.<br>• Use `-contributor` for synthetic dev and ablations, and write a credit budget | Execution | Raises P(full) ≈0.25 → ≈0.35 |
| 4 | **Replace the staged F-08 catch** with a real verifier catch between model-drafted v1 and v2, and give the real failure (F-11) more screen time | Depth 20, Demo 25 (judges discount staged failures) | Depth +0.25 |
| 5 | **Add one real incident-reporting lead or DPO.** They run B0 and react on camera. Frame impact as "never miss a 24-hour clock", showing the stakes (G §5) and minutes per entity | Impact 30 | Impact +0.25–0.5 |

With these changes the panel's estimates are: Callback ≈8.85 golden / ≈8.0 risk-adjusted; First Notice ≈8.1 / ≈7.4; Claim Clock ≈7.6 / ≈7.15. The ranking holds.

---

## 9. Reasons to kill, outright or conditionally

| Project | Kill outright? | Conditional kill (state + date) |
|---|---|---|
| Callback | No | (a) D1 18:00 ET: S1 *and* S2 both fail (role accuracy <0.90 and grounding <4/5): pivot, as the pack pre-registers (K1/K2). (b) D1 office hours: Meta staff raise a policy concern about the synthetic social-engineering corpus and abstraction does not resolve it. (c) The IP clause is unclear (R-10) |
| Claim Clock | **Do not pick as primary.** Its ceiling with Meta judges (7.1) is below the leader's expected value | Kill as fallback too if S-1 grounding fails *and* S-3 Voice fails. The pipeline would then be text-in, text-out, next to "basic RAG" and the image analyzer |
| First Notice | No (keep as second option) | (a) The whitespace check shows an incumbent already ingests bridge audio or dashboards into notification drafting. (b) D1: role accuracy <0.80 with 4+ speakers (K1) |

---

## 10. Where the panel departs from the research report

The report ranked Callback first (53/60), then overrode raw score order to put Claim Clock (47) ahead of First Notice (48) (report, "Eighteen candidates scored", last paragraph).

1. **Agree: Callback first.** But the report's build score of 3 understates the risk *as the pack is now written*. The pack added scope after the report (Ledgerly, Clock memo, demo-day batch of 200, blind-draw commitments, 9 ablations). The fix is to cut scope, not to switch project.
2. **Disagree on the primary order of First Notice and Claim Clock.** The override rested on three things:
   - the "DORA sequel" risk, which Meta judges cannot see;
   - unverified whitespace, which the First Notice pack has since partly checked;
   - R2 authority stopping at a draft, which is true but costs less than Claim Clock's Tooling and Impact caps.
   
   On the rubric, First Notice has the higher ceiling.
3. **Agree that Claim Clock is the right fallback, for a reason the report did not state.** Callback's D1 kill triggers are diarization on telephony audio and grounding on UI frames. First Notice depends even more on diarization (3–7 speakers) and on fine-grained chart grounding, so its failure is **correlated** with Callback's. Claim Clock's grounding is on clean static HTML screenshots, and Voice is optional. Conditional on Callback failing its spikes, Claim Clock is the more likely to survive.
4. **The report underweighted** four Claim Clock problems: UK parochialism; Meta scam-ad sensitivity; the warning-box redundancy; and the address-bar promise the product cannot keep.

---

## 11. Defects found in the packs (fix list)

**Callback**
- **D3 is not a walking skeleton.** H §1 D3 is nearly the full system, in about 27 h of weekday work while employed.
- **Over budget.** Planned spend ($300, E §11) is double the $150 of credits.
- **The decisive evidence is log-only.** The golden case (B §2) and the overturn (CB-0152) are both decided by log facts, so the B-3 rules baseline (F §4) would match Callback on the hero case.
- **The impact headline compares against a counterfactual.** The headline (G §3) compares to full manual coverage that nobody performs today. Lead with the risk break-even instead.
- **Computer use rests on an assumption.** Its justification is A-11, and real IdPs expose factor APIs.

**Claim Clock**
- **The address bar overpromises.** Its question (B §1) is not answered by C-08, which holds the bank's own precedents only.
- **The impact model switches off the agentic feature.** The conservative case (G §3) disables the hero agentic action shown in F-08 and targeted for Best Agentic (A §3).
- **The eval budget leaves no headroom.** It is ≈$147 against $150 of credits (F §15).
- **The capacity assumption is unrealistic.** A-19 assumes 9 focused hours a day.
- **The wow is staged.** The F-07 wow is a planted pair; label it as such and add a batch audit.

**First Notice**
- **No build-period credit budget,** and contributor IDs are refused even for synthetic data. That is a self-imposed cost risk.
- **The whitespace check is incomplete.** OneTrust, Archer and BreachRx are unchecked (00 summary), and that is the category most likely to already exist.
- **SAM is in Q8 but not load-bearing.** It is claimed in Q8 (B §7) while AB-07 expects no effect on text.
- **The failure catch is staged.** F-08 is seeded by construction.
- **The data spec exceeds an API limit.** Recordings of 4–30 min with 3–7 speakers (F §2) exceed the 10-min file cap and force chunk speaker linking. Keep the golden case inside the cap.

**All three**
- **Synthetic data only, and no real user has touched any of them.** Saurabh Baji's "put it in someone's hands early" (constitution Art. VII) is the cheapest Impact point left on the table: one practitioner, timed, quoted.
- **Muse Code `muse serve` is unused as a product substrate.** The constitution flags it as a rarely used "surprised even us" angle (Art. VI.2, rung 2). Deferring it is the right call for 8 days, but no pack uses it.
