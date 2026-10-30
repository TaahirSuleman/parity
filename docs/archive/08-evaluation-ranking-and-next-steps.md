> **Superseded 29 Oct 2026:** the ranking in §1 is replaced by `16-fresh-ranking-and-approach.md`. Procedure Proof (behind a spike) is now ahead, with the Accessibility Gap Auditor as fallback and Callback v2 third. §5–§9 remain useful reference.

# Critical Evaluation, Final Ranking and Next Steps — Callback · Claim Clock · First Notice
**Status:** v1, Tue 27 Oct 2026 (D0) · **Inputs:** the three demo-first packs (`07-pack-*.md`), the artefact standard (`06`), the constitution (`00`), the winning recipe (`04`), the research report (`05`), and two independent reviews written by reviewers who did not author the packs: a simulated Meta judge panel (`09-judge-panel-evaluation.md`) and a red-team audit with ~60 web checks (`10-red-team-audit.md`). · **Golden-path decks:** three Slides artifacts, corrected after the audit.

---

## 1. Bottom line

**Build Callback, but only as the re-scoped Callback v2 in §5, and only if two day-1 spikes pass by Wed 28 Oct 22:00 SAST. If either fails, switch to Claim Clock with the audit's fixes. Park First Notice.**

The two independent reviews disagree on the order, and the disagreement is the point:

| Lens | Callback | Claim Clock | First Notice |
|---|---|---|---|
| Judge panel, golden-path score (if the plan ships as written) | **8.43** | 7.12 | 7.55 |
| Judge panel, risk-adjusted expected score | **7.25** | 6.62 | 6.86 |
| Judge panel, chance the full plan ships | ≈20% | ≈35% | ≈25% |
| Judge panel, head-to-head in the live final | beats FN 65/35, CC 75/25 | loses both | beats CC 60/40 |
| Red team, fitness to build as specified | **Not fit** | **Fit, with conditions** | Conditionally fit, high schedule risk |
| Red team, D0–D3 hours: planned / estimated | 27 / 60–90 | ≈36 / 40–55 | 21 / 45–65 |
| Red team, full plan: planned / estimated | 72 / 150–220 | 72–81 / 120–170 | 65 / 140–200 |
| Load-bearing Meta capabilities after fixes | 2–3 (Voice, Spark screen grounding, + cross-call linkage if it ablates) | 2–3 (Spark image/video on customer evidence, Voice on coached calls; SAM only for faces/video) | 3 (Voice, Spark chart grounding, computer use on a web-only portal) |
| Whitespace after the audit's extra searches | **Exact job still unclaimed**; the log half is commodity | **Holds for post-payment adjudication**; pre-payment screenshot AI exists (Starling) | **Narrowed**: IR-OS, D3 Morpheus, incident.io / PagerDuty Scribe |
| Employer-IP overlap (audit X-11) | Low–Medium | **Medium–High** | Medium |
| Policy / sensitivity for Meta judges | Dual-use generator (manageable) | Scam-ad platform-liability beats (soften) | None |

**How to read it:** the judge panel answers *which project scores best if built*; the red team answers *which can be built as written*. Neither full plan fits the hours a full-time employee actually has (≈45–56 focused hours before Nov 4 without leave). So the real question is **which project scores best after it is cut to fit**. Callback keeps the highest ceiling after cutting, because the elements judges reward most survive the cut: a live attack, three kinds of evidence, a visible rescue, and an unclaimed job. The elements the audit condemns (SAM on UI video, computer use, the 1M claim, the log-catchable hero case) are the very ones the cut removes.

---

## 2. Method

1. **Artefact standard (`06`):** demo-first order (judging objectives → golden-path demo → PRD/tech spec → evidence → execution → presentation), honesty tags on every number, ablations as proof that Meta's models are load-bearing, calibrated autonomy.
2. **Three packs** written to that standard (11 artefacts each), plus three golden-path decks.
3. **Two independent reviews,** run in parallel by reviewers who had not seen the drafting:
   - The **judge panel** scored each project 0–10 per rubric category, golden-path and risk-adjusted, with component-level delivery probabilities and head-to-head verdicts.
   - The **red team** verified 30 load-bearing facts against sources and checked every Meta API assumption against the tooling reference. It re-estimated build hours bottom-up, ran rules/ethics checks and searched again for competitors.
4. **This synthesis** reconciles the two reviews with the constitution's Article VIII criteria and recipe filters R1–R4, applies the factual corrections to the decks, and sets the decision gates.

---

## 3. Project-by-project critical evaluation

### 3.1 Callback: help-desk vishing investigation and containment
**What is strong**
- The largest, most current loss story. Vishing is the #2 intrusion vector (M-Trends 2026, 11%) and vishing-and-smishing breaches are the costliest vector ($5.29M). The help-desk route is believed to explain the M&S/Co-op event (£270–440M).
- The exact job is still unclaimed. Live caller-verification tools (GetReal, Nametag, Pindrop, Humanix, Netarx) stop at the call; identity-threat and AI-SOC tools don't take call recordings.
- It fits the grand-prize profile: an attack on a clock, non-text evidence that decides the verdict, an agent that changes state in a system of record, and a named human approval step.
- Strongest demo of the three (judge panel: Demo 9.0 golden). It is literally the Best Agentic definition. Lowest employer overlap.

**What the reviews broke**
- **CB-1 (Critical):** the "walking skeleton" was nearly the whole system. 27 h planned, 60–90 h estimated.
- **CB-2 (High):** the hero case is caught by a free public log rule and by the pack's own rules-only baseline. On camera, perception would add nothing.
- **CB-3 (High):** computer use was justified by "consoles without APIs", but Microsoft Graph and Okta's Factors API both remove factors. Driving a console with a model when an API exists also breaks the pack's own "model plans, code acts" principle.
- **X-01 (High):** two "only Meta" pillars fail a vendor-swap test. Gemini also returns 0–1000 boxes, and OpenAI's computer use also has acknowledged safety checks.
- **X-02 (High):** the 1M-context ablation was against a 32k strawman.
- **CB-6 (Medium):** SAM on UI screen recordings is likely to fail its own ablation.
- **CB-11 (Medium):** the public generator could act as a vishing-script kit.
- **CB-12 (Medium):** the founder-fit claim was overstated. The CV shows DevOps/SRE agents, not service-desk or IAM work.

**What survives (the case for v2)**
- Diarization is genuinely decisive. The audit's own worked example is a speaker hard negative: the *agent* says "new phone", and logs cannot tell who said it.
- Screen evidence of a verification step that leaves no IdP trace (callback to the number on file; video ID) is genuinely decisive.
- Cross-call pretext linkage (the same scripted phrasing across several calls) is something a SQL join cannot do. It gives whole-case reasoning a real job.
- Re-timing to "minutes after hang-up" fixes the "overnight is too late" objection (attackers hand off access in 22 s; OAuth consent came 9 min after the call).

**Verdict:** first choice, conditional on the v2 re-scope (§5) and the D1 spikes. Re-scoped risk-adjusted expectation is ≈7.6–8.0 (judge panel's improvement estimate, discounted for the lower tooling count after cutting SAM and computer use).

### 3.2 Claim Clock: APP scam reimbursement adjudication
**What is strong**
- Best-verified whitespace. Pay.UK's RCMS leaves decisions to humans, and no adjudication product turned up in two rounds of searching.
- Cleanest sourcing (9 of 11 facts verified) and a documented failure to fix: refund rates of 21–94% across individual PSPs.
- The only real outcome labels: Ombudsman decisions, used as IDs and derived labels only.
- The most honest impact model ("a copilot by default; autonomy where it is earned"), the most credible skeleton (40–55 h), and excellent consumer-harm safeguards.

**What the reviews broke**
- **CC-1:** the golden-path recovery split was wrong (£7,050, not £7,100); now corrected in the deck.
- **CC-2:** SAM on text PII is a design mismatch.
- **CC-3:** the decisive caution fact sits in the bank's own structured logs, so "the decisive facts are visual" is weak exactly where the demo leans on it.
- **Ceiling:** the lowest tooling score (5.9 risk-adjusted). It needs ~20 s of UK-scheme context, and its wow is "clever rather than visceral" (judge panel).
- **Employer IP is Medium–High:** the CV describes compliance automation for regulated financial clients.
- Its EU platform-liability beats are awkward in front of Meta judges, since Meta hosts scam adverts.

**Verdict:** the fallback, not the primary. It is the most likely to survive if Callback's perception spikes fail, because it grounds clean static screenshots and Voice is optional (judge panel §10; audit §10). Its gap to Callback cannot close on expectation: even a perfect Claim Clock (7.12 golden) scores below Callback's risk-adjusted 7.25 *as written*.

### 3.3 First Notice: multi-regime incident reporting from war-room evidence
**What is strong**
- The strongest dated forcing functions: CRA reporting live since 11 Sep 2026 via a web-only platform with no API; NIS2 24/72 h with four member states before the EU Court; DORA's 3,383 major incidents in 2025.
- Verified regulatory facts and the most universal story, with an excellent gate design (hash-bound sign-off, submit intercept).
- It is the one project where computer use is honestly justified, because the portal really has no API.
- "Clocks born from evidence" is a good, legible wow.

**What the reviews broke**
- **FN-1 (Critical):** 21 h planned for the skeleton against 45–65 h estimated.
- **FN-2 (High):** the whitespace is narrower than claimed. IR-OS already runs multi-regime clocks, drafts and a hash-chained record; D3 Security's Morpheus auto-drafts DORA initial reports; incident.io and PagerDuty transcribe bridge calls.
- **FN-3 (High):** the golden case contains a legal error that any domain reviewer would catch. Payment institutions are not an NIS2 entity type, and the Netherlands has not fully transposed NIS2. Now corrected in the deck.
- The DORA-sequel risk remains: invisible to most Meta judges, but real to anyone who knows the participant's prior entry.
- It leans harder on diarization (4+ speakers) than Callback, so if Callback's diarization spike fails, First Notice likely fails too.

**Verdict:** third. Its distinctive mechanism (pin a regulator's clock to a playable sentence) is worth keeping. In Callback v2 it becomes the incident memo's "awareness pin", so the best idea is not lost.

---

## 4. Rubric, rules and constitution compliance (after corrections)

| Check (source) | Callback v2 | Claim Clock (fixed) | First Notice (fixed) |
|---|---|---|---|
| Stage 1: theme and Meta usage (`00` Art. I.2) | Pass: Build for Your World; Model API central | Pass | Pass |
| Anti-project list (`00` Art. II) | Clear (defensive security) | Watch "simple image analyzer"; lead with decisions | Clear |
| New work only; public repo; ≤4 team | Fresh repo after kickoff + `HACKATHON_SCOPE.md` | Same | Same |
| Data rights (`10` §7–8) | Kokoro TTS Apache-2.0; consented human slice; Entra field names only; attack audio gated | Ombudsman IDs and derived labels only (site terms forbid reproduction) | Synthetic incidents; CC BY dataset |
| Third-party licences | `meta-sam-parser` is under Meta's "SAM License": list it in `THIRD_PARTY.md` if SAM is used | Same | Same |
| Art. VIII hard-fail criteria | All ≥3 after re-scope (Meta load ≥3 only if two ablations pass) | All ≥3 (Meta load borderline 3) | All ≥3 (whitespace weakened) |
| Recipe filters R1–R4 (`00`, `04`) | R1 ✓ · R2 ✓ (L3 auto-revoke with measured autonomy) · R3 ✓ · R4 ✓ (honest line) | R1 ✓ · R2 ✓ · R3 ~ · R4 ✗/~ (employer overlap) | R1 ✓ · R2 ~ (authority stops at a signed filing) · R3 ✓ · R4 ~ (sequel) |
| Standard quality bar (`06` §4) | Must re-check after the v2 rewrite | Pass after CC-1..5 | Pass after FN-1..3 |
| Best Agentic bonus | Strongest | Strong | Medium |
| Open-weight bonus ($10K) | Weak fit | **Most natural**: a Glimmer local PII-redaction tier | Plausible: local processing of confidential incident data |

---

## 5. Callback v2: the re-scoped golden path (what to build)

**Logline:** *Minutes after a help-desk call ends, Callback hears who said what, sees what the agent did, reads what happened next in the identity logs, and revokes the attacker's sessions before they're used, with a human approving anything irreversible.*
**Address bar:** "Did that MFA reset just hand an attacker the keys?"

| Area | v1 (pack) | v2 (build this) | Why (review ID) |
|---|---|---|---|
| Timing | Overnight batch of 200 calls | Per call, within minutes of hang-up; demo batch of 40 | Judge panel improvement #2; 22 s hand-off |
| Hero case | Reset → hosting-ASN factor +4 min → OAuth +9 min (rule-catchable) | Logs look benign (e.g. enrolment from a residential ISP consistent with the travel story); conviction comes from the diarized pretext plus the screen showing the agent skipped callback-to-number-on-file. The rules-only baseline is shown on screen saying "benign" | CB-2 |
| Verifier overturn | Decided by a log fact | Speaker hard negative: the *agent* says "new phone"; diarization flips it | Judge panel #3 |
| Skeleton by D3 | 12 components | Voice diarization → Spark keyframe procedure check (grounding boxes, no SAM) → Pretext → Trail (digest + deterministic joins) → citation check (code) → two-key gate (code) → L3 session revoke via sandbox API → audit, trace, replay | CB-1 |
| L4 rollback | Spark computer use on a console | Sandbox API after human approval; computer use moves to the roadmap | CB-3 |
| SAM 3.1 | Tracking on UI recordings | Overlay polish only if its ablation passes; out of Q8 until then | CB-6 |
| 1M context | Claimed via a 32k strawman | Claimed only if it beats a 200k window on cross-call pretext linkage; otherwise "whole-case reasoning" | X-02, CB-7 |
| Q8 "why Meta" | "Only Meta" absolutes | "The combination on one key and one trace, proven by measured ablations": diarization (precision on speaker hard negatives) and Spark screen grounding (verification-step accuracy) as the two headline ablations | X-01, CB-4 |
| Incident memo | Full clocks memo | Awareness pin borrowed from First Notice: the memo cites the turn and frame that made the firm aware; deadline wording is regime-correct | CB-8 |
| Data | 40 labelled cases by D2 | 10 by D2, 60–80 by D5; human-voiced slice of 10 with consent naming the Meta/CV licence; attack audio in a gated dataset | CB-1, CB-11, X-06 |
| Budget | $300–400 against $150 credit | `-contributor` model for synthetic dev runs (no personal data); Spend Limit on D0; replay mode during judging | X-04 |
| Founder-fit line | "firsthand territory" | "I build production agent pipelines for ops queues; this applies the pattern to IAM resets." | CB-12 |
| Names | DataPump, Deskline, Ledgerly | Rename all three | CB-16 |

**Expected tooling story after v2:** at least two measured, load-bearing Meta capabilities (Voice diarization; Spark perception grounding on screen keyframes), plus one candidate third (cross-call whole-case reasoning, or SAM overlays if they ablate). On the constitution's criterion 4, three or more load-bearing capabilities score a 5; two score a 3–4. That is not a hard fail, but it is a weaker tooling score, so the third capability is worth winning on D5 by ablation. If it isn't won, say so honestly; the judge panel still scores this project above Claim Clock.

---

## 6. Decision gates and kill criteria (state + time, SAST)

| Gate | When | Pass | If it fails |
|---|---|---|---|
| G0: employment IP clause | Tonight, D0 | Personal-time, unrelated work permitted, or written consent | Stop. Claim Clock fails this first (highest overlap) |
| G1: capacity | Tonight, D0 | Decide leave days. With 2–3 days, the v2 plan plus L4 and Second Look fit; without leave, the v2 skeleton plus eval only | Cut to the v2 skeleton; no stretch goals |
| S1: diarization spike | Wed 28 Oct, by 22:00 | ≥0.90 speaker-role accuracy on 10 telephony-degraded (8 kHz) TTS calls, keyword-biased | Try stereo channel-split recordings; if that also fails, switch to Claim Clock |
| S2: screen-grounding spike | Wed 28 Oct, by 22:00 | Spark localises the reset click, target user and verification-panel state in ≥4 of 5 recordings | Switch to Claim Clock |
| S3: SAM on UI (optional) | D4 | Its ablation moves a metric by ≥5 points | Drop SAM from the claim |
| K3: walking skeleton | Fri 30 Oct, 23:00 | One case end-to-end with L3 revoke, traced and replayable | Cut Second Look and the memo; if still no end-to-end run, switch |
| K4: whitespace | D1 | SecurityWeek "live conversation" piece and Okta ITP / Push / SlashID release notes show no product fusing call + screen + IdP evidence with containment | Reposition as the case-fusion layer over that product |
| Freeze | Tue 3 Nov, 18:00 | 10 consecutive clean golden runs | Record from replay, labelled |
| Submit | Wed 4 Nov, 18:00 ET (= Thu 01:00 SAST; hard deadline 21:00 ET = 04:00 SAST) | Form complete, repo public, video live | — |

US clocks change on 1 Nov: Agents 102 (Wed 28 Oct, 12:00 ET) is **18:00 SAST**, and Meta office hours (10–11 ET) are **16:00–17:00 SAST** until 30 Oct, then 17:00–18:00 SAST.

---

## 7. Next steps (ordered)

**Tonight (D0, Tue 27 Oct)**
1. Read the employment contract's IP and moonlighting clauses (G0). Personal laptop and accounts only from here on.
2. Decide leave days (G1). This is the single largest lever on every project's score.
3. Claim the $150 Model API credits, add the card and set a Spend Limit. Confirm `GET /v1/models` IDs (including `sam-3.1` vs `sam-3-1`). Read the SAM License.
4. Create the public repo with a first commit after kickoff, plus `HACKATHON_SCOPE.md` and `THIRD_PARTY.md`.
5. Line up one practitioner (service-desk or IAM lead) for a 20-minute timed manual review and a one-line quote this week. This replaces the weakest impact input.

**Wednesday 28 Oct (D1)**
6. Run S1 and S2 (§6). Generate 10 telephony-degraded TTS calls (Kokoro) and 5 Playwright screen recordings of the fictional console.
7. 16:00 SAST office hours: ask Meta whether a synthetic social-engineering corpus built from public TTPs raises any concern (policy gate), and confirm the audio path (Voice file mode; Spark 1.2 for any audio input).
8. 18:00 SAST: attend **Agents 102: Best Practices for Verifiable Agents**. Adopt its vocabulary in the README and voiceover.
9. Decision by 22:00 SAST: Callback v2 or Claim Clock (fixed).

**Then**
10. Rewrite the chosen pack to v2. Re-run the standard's quality bar, update the deck, and draft the form answers Q4/Q7/Q8 from measured-ablation language.
11. Build to the v2 plan, with the D3 walking skeleton as the first hard milestone.

---

## 8. Corrections already applied to the decks
- **Callback:** clock headline now "Disclosure clocks run from what the firm knows…"; M&S/Co-op route "believed"; the computer-use row is limited to UI-only consoles; "only Meta" became "Why Meta: the combination, on one key".
- **Claim Clock:** recovery split £7,050 (excess waived, not shared); refund-variance and caution-exception wording matched to the source; "only Meta" eyebrow reworded.
- **First Notice:** NIS2 applicability reason corrected (payment institutions are not an NIS2 entity type; transposition status flagged); "only Meta" eyebrow reworded.
- **Packs (`07-*`):** an errata block at the top of each lists every Critical and High finding. The pack bodies remain v1.

**Still open:** the Callback deck shows the v1 golden path (overnight batch, hosting-ASN hero case, computer-use rollback). It will be redrawn to v2 once the D1 spikes decide the project.

---

## 9. What the Gemini 3 post-mortem changes (added 29 Oct, from doc 15)

The ranking stands: Callback v2 first, Claim Clock as the fallback. Both pass R5 (perceptual load). The post-mortem changes **how** we build and show either one.

**Callback v2. Risk: it repeats the Resilix shape.** Resilix and Callback v2 are both event → investigate → act in a system of record, built by the same person. Changes:
1. **The reviewer console is the first thing designed, before the agent graph is coded.** It shows, all inside the product:
   - call playback with the diarized transcript synced to the audio, speakers coloured, and the speaker flip visible;
   - the keyframe with Spark's grounding box on the skipped callback-to-number-on-file step;
   - the identity-log timeline joined to call turns;
   - the agent trace streaming;
   - verifier refusals as red rows;
   - the gate card with a reason and an **"Approve: revoke sessions"** button;
   - the revocation landing in the sandbox IdP.
2. **The public URL gets a no-login "Run case CB-hero" button** with live mode (the real pipeline) and replay mode (cached traces), both labelled. The judge can run it in under 60 s.
3. **The hero moment:** the rules-only baseline says "benign"; Callback hears that the *caller*, not the agent, said "new phone", sees the skipped check, and stops the account takeover. It plays live between 0:30 and 1:30 and ends in the approval click.
4. **State the actuation honestly:** "Spark and Voice decide; revocation is deterministic code behind your approval" (L8). Name each Meta feature only alongside its on-screen artefact (L7).
5. **The video follows doc 04 §4.4 v3:** cold open on the caller's voice, hard cap 2:55, product on screen ≥ 80% of runtime.

**Claim Clock (fallback):**
- **Workbench:** the claims handler's adjudication workbench (evidence screenshots with grounded highlights, the criteria checklist, the £ computation done in code, Approve/Reject).
- **Hero moment:** a scam tell inside a screenshot that the claimant missed changes the reimbursement outcome.

**Plan changes:**
- **D6 noon feature freeze.** D6 afternoon to D7: script, record, edit, re-shoot buffer.
- **D7: cold review** against the doc 04 Part 7 checklist by a fresh agent or a person.
- **D8:** submit early.
- **Engineering rigour** (tests, eval harness, replay) stays in scope for Technical Depth, but no D6–D7 hours go to it.

**Deck:** the existing Slides artifacts become the Devpost/README visuals and final-round support. In the video they appear only as overlay chips and one ≤ 10 s architecture card.
