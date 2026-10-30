# 15 — Gemini 3 Hackathon post-mortem: Resilix against the 13 winners

**Status:** v1, 29 Oct 2026. **Purpose:** learn from a past non-winning entry so we don't repeat its mistakes at Meta.

**Evidence base:**
- The Gemini 3 event and rules pages.
- The official winners update: Devpost update 40729, about April 2026, 4,500+ submissions.
- All 13 winner Devpost pages, with their write-ups, repos and live links. Two research agents scraped these; their notes are in `research_gemini3/winners_batch{A,B}.md`.
- All 13 winner videos: length and title for every one. For **Globot, Aegis and Netra** (the top 3), full auto-captions plus a 12-frame contact sheet each. Frame sheets for six honourable mentions (HMs).
- Resilix: the Devpost page, the YouTube video (full captions plus sampled frames), the 4-slide deck and the GitHub repo at its final commit.

**Tags:**
- **[observed]** I saw it myself.
- **[agent]** From the scraping agents, not re-checked.
- **[inferred]** My interpretation.

> **Caveat.** This compares one non-winner with 13 winners out of about 4,500 entries. It shows what winners have in common, not what caused them to win. Judging was not transparent. Treat the lessons as strong priors, not laws.

---

## 1. Bottom line

1. **Engineering quality was not the problem; what the judges *saw* was.** Resilix had 122 tests, typed contracts, Cloud Run deployment and a simulator. None of the 13 winners showed a test suite [agent]. Judges at this scale score mostly from the video and the page, and Resilix's video undersold it:
   - It ran **4:14** when the rules say "only the first 3 minutes may be evaluated".
   - It opened on a slide titled **"The Problem: Rampant Coupon Abuse in E-Commerce"**, left over from another deck.
   - It spent its first **~75 s on slides**.
   - It cut out the live run ("I skipped ahead until it was done for the sake of time").
   - The impact slide came **entirely after 3:00**. [observed]
2. **All three of your hypotheses hold, with nuances** (§6):
   - **Demo-first:** every top-3 video is product-first, and none opens with slides.
   - **The front end has to carry the value:** every winner's UI is where the value is seen *and* where the human acts. Resilix's UI was a read-only monitor, and incidents were started from a CLI.
   - **Multimodal:** **all three placed winners perceive the physical world** (satellite imagery; drone images and 911 audio; a live camera plus voice). Only 3 of the 10 HMs do. Resilix was text-only.
3. **Six shortfalls you didn't list** (§7):
   - **Feature-name misuse:** the write-up's "thought signatures" are a custom Pydantic schema, not Gemini's API feature.
   - **A hidden template behind the hero moment:** the DNS fix shown in the video is a hard-coded patch in `github_direct.py`.
   - **Inconsistent and inflated numbers.**
   - **A crowded "autonomous engineer" concept** with no memorable moment.
   - **A live link a judge couldn't operate.**
   - **A 5-day build squeezed into the last week** of a 7-week window, leaving no time to produce the video.
4. **The Meta rubric amplifies every one of these.**

   | Category | Gemini 3 weight | Meta weight |
   |---|---|---|
   | Demo | 10% | **25%** ("genuinely cool to watch", "holds up live") |
   | Impact | 20% | **30%** |
   | Tooling | — | **25%**, rewarding multimodal Meta capabilities that are load-bearing |

   The lessons in §9 are now in the recipe (doc 04 v3), the constitution (v1.2), the artefact standard and the next steps (doc 08 §9).

---

## 2. The event, and how it compares with Meta

| | Gemini 3 Hackathon (Dec 17 2025 – Feb 9 2026) | Meta (Oct 26 – Nov 4 2026) |
|---|---|---|
| Scale | 35,500 participants, ~4,500 submissions | Up to 20,000 accepted |
| Prizes | $50k / $20k / $10k + 10 × $2k HMs | Track and bonus prizes |
| Rubric | Technical Execution 40% ("leverage Gemini 3", code quality, functional) · Innovation/Wow 30% · Impact 20% · Presentation/Demo 10% ("problem clearly defined… demo and documentation… architectural diagram") | Impact 30% · Tooling 25% · Technical Depth 20% · **Demo 25%** |
| Video | "Should not be longer than 3 minutes… only the first 3 minutes may be evaluated"; must show the project functioning | 3-minute demo video, "one of the primary artifacts"; must show only what was built in the hackathon; final round watched live |
| Live product | Public link, no login (or AI Studio app) | "Does the product hold up live?" is scored |
| Stages | Pass/fail viability, then 1–5 per criterion, averaged | Pass/fail, then 0–10 rubric, then top 5 per track watched live |

**Neither event asks for a deck** (your point). Both make the video the main judged artefact, and Meta weights it **2.5 times** as heavily.

---

## 3. The 13 winners at a glance

| Place | Project | User and job | Perceptual input | Agents | Where the value is seen and acted on | Video |
|---|---|---|---|---|---|---|
| **Grand** | Globot | Logistics manager in a geopolitical shock ("4:55 PM Friday, $50M cargo") | **Satellite imagery** (vision), PDFs, news | 5 (CrewAI), incl. an **Adversarial Debate** agent | **3D globe**: route reroutes around a war zone; agent debate log; human clicks "Execute" → map turns green | 2:26, ~100% product, unscripted |
| **2nd** | Aegis | 911 dispatcher in a mass-casualty event ("10,000 signals in 10 minutes") | **Audio calls, drone images**, text | 5 (custom), Pro + Flash | **Tactical map** with a typewriter reasoning trace; "Protocol Zero" voice approval before heavy assets | 2:47, ~75% product, scripted VO, music, captions |
| **3rd** | Netra | Blind person navigating daily life | **Live camera + voice** | 1 (agentic mode) | **The phone *is* the product**: spoken guidance ("Handrail is on your left, 30 cm away") | 2:59, ~45% live POV demo + cinematic b-roll |
| HM | Proofy.AI | Ordinary people facing deepfake scams | **Image, video, audio** | 0 (classifier) | Phone volume-button capture, browser extension, web suite | 2:58, ~85% product |
| HM | BatteryForgeAI | Battery QA and fleet safety engineers | **Webcam/video, PCB images** | 6 (ADK) + physics sim | Multi-mode workbench | 3:09 |
| HM | Gemini GeoFlow | Archaeologists | **Satellite composites** + papers | Pipeline | Map + imagery + Search-grounded citations | 3:05 |
| HM | Orphafold | Rare-disease researchers | Text (+ 3D output) | 4 | 3D AlphaFold viewer | 3:04, ~100% product |
| HM | Orbital Assets | Space-mining investors | Text/URL | 1; **valuation computed in deterministic TypeScript, model narrates** | 3D asteroid + streamed reasoning | 2:59, ~80% product |
| HM | PROCSee | SOC analyst | OS telemetry | 1, self-directed queries, thinking levels | Live investigation dashboard | 2:59, ~100% product/IDE |
| HM | AgentGuard | Merchants facing AI-agent scrapers | Telemetry | 1 judge + cache layers | Command centre with allow/block graphs | 3:00, ~50% product, 50% explainer animation |
| HM | Logic Lift | COBOL modernisation teams | Code | 1 + Pyodide test-and-fix | Report + "certainty score" UI | 2:06 |
| HM | Agent-weaver | Dev teams using coding agents | Code | 5 + MCP (55 tools) | Live agent dashboard | 3:37 |
| HM | CineStream | Executives; Venezuelan students | Text | Prompt "mesh" | Cinematic lesson workstation | 2:12 |

**Patterns** [observed and agent]:
- **All 3 placed winners take perceptual input**, against 3 of 10 HMs.
- **All 3 placed winners have a single unforgettable moment:**
  - Globot: the green reroute after the debate and the approval.
  - Aegis: the "pizza cipher", a woman "ordering a pizza" from 911, recognised as a domestic-violence SOS.
  - Netra: "The water bottle… to the left of your silver laptop, 1.5 m away".
- **Both multi-agent placed winners show a human approval click inside the demo.**
- **Multi-agent is not required:** 7 of 13 are multi-agent, Netra placed 3rd with one agent, and PROCSee and AgentGuard are single-agent HMs.
- **No winner has a test suite** [agent].
- **Impact numbers everywhere are unsourced or unmeasured** [agent].
- **Solo builders are common:** 8 of 13 [agent].
- **Likes don't predict winning:** VaultSim had 139 likes and didn't win [agent].

---

## 4. What the videos show

| Video | Length | Share of time on the product working | First 10 seconds | Structure |
|---|---|---|---|---|
| Globot (Grand) | 2:26 | ~100% | Product landing page | Unscripted screen walkthrough: "simulate the rising crisis" → agents debate in the event log → reroute → click "Execution" → green |
| Aegis (2nd) | 2:47 | ~75% (plus ~10% real-world footage and ~15% code) | Disaster footage + hook line | Scripted, music, burned-in captions. Problem in 20 s over footage → product from ~0:20 → three scenario beats (drowning risk, drone fire, pizza cipher) → human approval → auto SITREP → 20 s tech stack at the end |
| Netra (3rd) | 2:59 | ~45% live POV demo (the AI's own voice audible) | Cinematic b-roll | Trailer-style: problem → architecture card (≈10 s) → staircase, smile, coffee task, find-my-bottle → close |
| Orbital Assets (HM) | 2:59 | ~80% | 3D asteroid in the product | Product with webcam inset → architecture diagram in the last ~25 s |
| PROCSee / Orphafold / Proofy (HMs) | ~3:00 | 85–100% | Product | Screen-recorded product throughout; Orphafold has burned-in subtitles |
| AgentGuard (HM) | 3:00 | ~50% | Product, then animated explainer | Explainer animations, product, flow diagram, go-to-market slide |
| **Resilix** | **4:14** | **~57%, all of it a tour *after* the run had finished** | **Slide with the wrong title** | Problem slide (0:00–0:32) → architecture slide (0:32–1:15) → trigger (1:15–1:36) → "skipped ahead" → tour of timeline, logs, Jira and PR (1:50–3:27) → "merged autonomously without human interaction" → impact slide (3:40–4:14, **past the cut-off**) |

**Where the deck can live** [inferred]. The best videos still *present*: problem, who, why, stack. They do it as **narration and overlays on top of the product**, or as a 10-second card, never as a slide segment. Your browser-tab motif survives as **overlay chips and an address-bar caption over product footage**. The full deck belongs on the Devpost/README page and as backup material, not in the video timeline.

---

## 5. Resilix audit: what each judging criterion saw

| Criterion (weight) | Strengths | What hurt |
|---|---|---|
| **Technical Execution (40%)**: "leverage Gemini 3", code quality, functional | ~10.8k Python LOC; 122 tests (unit, integration, e2e, contract, simulator); typed Pydantic contracts; Cloud Run; approval/CI/code-owner merge policy; a deterministic simulator | (a) Gemini use was generic: all four agents run **`gemini-3-flash-preview`**, text-only, with no grounding, multimodal input or long context. (b) The "thought signatures" claim describes **a custom RCA schema (`models/thought_signature.py`)**, not Gemini's API thought signatures (the opaque reasoning-state tokens the SDK passes back with function calls); a DeepMind judge could read that as borrowing a feature name. (c) After the agents run, `apply_direct_integrations()` **always** files the Jira ticket and PR in code, and the DNS fix is a **hard-coded patch** (`_patch_coredns_config`: `forward . 1.1.1.1 8.8.8.8 9.9.9.9`, `failover_mode: "AUTO"`), yet the video says the Mechanic "solves the issue". (d) Fallback paths (`MockRunner`, deterministic signatures, a UI that falls back to `MOCK_INCIDENTS`) make it unclear when the model is actually doing the work. (e) Administrator reuses Sentinel's thinking level. |
| **Innovation / Wow (30%)** | An end-to-end loop that acts: Jira plus a real GitHub PR | "Autonomous SRE / AIOps" is a crowded category that commercial products already occupy. No moment a judge would retell. The fix appears around 3:00, at the cut-off. |
| **Impact (20%)** | A real, expensive problem (AWS us-east-1) | Three different number sets: the video says "hours to days → 5–10 min"; the slide says "3.72–4.43 min, 93%, ~95%+ cost"; the write-up says "4.07 min, $433k–$934k per incident". These come from **n = 2 runs** and an unsourced $16,700/min constant. No named user or institution. |
| **Presentation / Demo (10%)** | Clear 4-agent story; screenshots on Devpost | Over the length limit; wrong slide title; slides first; live run cut; dashboard showed several FAILED/INVESTIGATING incidents; video contradicts the write-up on the approval gate; no architecture diagram image on Devpost; the repo README links to `techspec.md`, deleted in the last commit; the gallery "Try it out" includes a Google Drive video link. |

**Build timeline** [observed]: 97 commits, all between 5 and 10 Feb 2026 in a 17 Dec – 9 Feb hackathon. There were 61 commits on 7–8 Feb, a fix for "demo simulation runtime errors" late on 8 Feb, and the final README and story about an hour before the deadline. That left no time to rehearse, re-record or QA the submission.

---

## 6. Your three hypotheses, tested

**H1: "The demo was not the central focus of the video; the presentation was."**
- **Verdict: confirmed, and the fix goes further than you framed it.** In time, Resilix was 43% slides and 57% product. But the product footage was a *tour after the run had finished*, so judges never saw the agents working. Winners showed the system working in real time, with a single moment that landed. The four ways Resilix lost were: slides first, a cut instead of the live run, a contradiction about autonomy, and the payoff after 3:00.
- **Nuance:** the presentation still matters. The polished winners (Aegis, Netra) are scripted, with music and captions. They tell the story *over* the product.
- **Rule:** product on screen by 0:05 and at least 80% of runtime; deck content only as overlays or cards of ≤ 10 s each, ≤ 20 s in total.

**H2: "The product must be full-stack, with value on both front and back end, not a backend workflow with an afterthought frontend."**
- **Verdict: confirmed.** In every winner, the human-facing surface is where the value becomes visible *and* where the human acts:
  - globe reroute plus Execute;
  - map plus voice approval;
  - phone guidance;
  - volume-button capture;
  - 3D protein.
- Even backend-heavy HMs (PROCSee, AgentGuard) **stream the reasoning live** into the UI.
- Resilix's UI was a polling monitor whose only action was Approve Merge. Incidents had to be started from a CLI simulator, so a judge on the live link could not make anything happen.
- **Nuance:** "full-stack" doesn't mean a heavy frontend. It means **the decision moment and the evidence live in the UI.**
- **Rule:**
  - one-click "run the golden case" on the public URL, no login;
  - the reasoning trace streams;
  - evidence is shown on the media itself;
  - the human approves in the UI;
  - no silent mock fallback.

**H3: "It was agentic but not multimodal."**
- **Verdict: confirmed as the strongest single correlate of placing.** All three placed winners take perceptual input (satellite, audio and drone, live camera). Overall, 6 of 13 winners do.
- For Meta this is decisive: Tooling (25%) asks for capabilities that "surprised even us", and Meta's stack is perception-first (Spark perception grounding, SAM 3.1, Voice Transcribe diarization).
- **Rule:**
  - at least one non-text input is load-bearing;
  - its output is **drawn on the media in frame** (box, mask, speaker turn, timestamp);
  - an ablation shows the metric that drops without it.

---

## 7. Shortfalls you didn't list

1. **Name features accurately, and show each one doing visible work.** Write only what the code does. For Meta: "Muse Spark perception grounding returns a 0–1000 box we draw on the keyframe", not "we use perception".
2. **Honest actuation is a *strength* when you say so.** Orbital Assets won an HM *because* it said "the valuation is locked in TypeScript; the model narrates". Resilix had the same safety pattern (the model diagnoses; allow-listed playbooks act) but presented it as the model fixing the issue. Said openly, deterministic actuation is a guardrail; hidden, it is a credibility risk.
3. **Consistency and modesty in the numbers.** Use one number set across video, deck and README, measured where possible, sourced where not. Never extrapolate $934k per incident from n = 2.
4. **Choose a concept with a person and a moment.** Every placed winner centres a person in a high-stakes moment: a dispatcher, a blind user, a logistics manager on a Friday afternoon. "Cascading infrastructure errors" has no face.
5. **A judge must be able to operate the live product.** It is scored at Meta ("holds up live").
6. **Run QA on the submission as its own workstream.** Errors that a cold review would have caught:
   - a wrong slide title;
   - a deleted file still referenced;
   - "autonomous" contradicting "approval-gated";
   - failed incidents visible on screen;
   - a Drive link among the public links.
7. **Time allocation.** Plan backwards from the video: features freeze, rehearsal and recording, then submission QA. Engineering rigour is still needed for Meta's Technical Depth (20%), where judges read repos, but cap it so it never eats the demo.

---

## 8. What Resilix did better than the winners, and what to keep

- **Tests and contracts:** 122 tests, a deterministic simulator and verification of external side effects. Meta's Technical Depth rewards these, and Agents 102 is exactly this philosophy. **Keep them.**
- **A real system of record:** a Jira ticket and a GitHub PR that merges. Acting in real tools is still a differentiator. **Keep it, but make it visible and live.**
- **A merge-policy gate** (CI, code-owner review, manual approval). **Keep it, and demo the human click.**
- **Per-role reasoning budgets.** Meta's `reasoning_effort` is the equivalent. **Keep it, with a measured latency/cost table.**

---

## 9. Lessons, as rules (now in doc 04 v3 §4.4 and Part 7)

| # | Rule | Evidence | Meta category |
|---|---|---|---|
| L1 | Product on screen by 0:05; ≥ 80% of runtime is the product working; slides only as overlays (≤ 10 s each, ≤ 20 s in total) | §4 | Demo 25% |
| L2 | **One hero moment, live and uncut** (or speed-ramped with a visible "2×" label) between 0:30 and 1:30: an input a human or a rules engine gets wrong and our system gets right, shown *as it happens* | Pizza cipher, water bottle, green reroute | Demo, Impact |
| L3 | **Hard cap 2:55.** Everything that matters, impact included, lands before 2:50. Render and time-check before uploading | Resilix's impact at 3:40 | Demo |
| L4 | **Perception is visible:** non-text input with model output drawn on it in frame, plus an ablation | Top 3 are all perceptual | Tooling 25% |
| L5 | **The UI is the workbench:** trigger, streaming reasoning, evidence on media, human approval, all in the UI; one-click golden case on the public URL; no silent mock fallback | §6 H2 | Demo ("holds up live"), Impact |
| L6 | **A visible human gate** with a reason, e.g. "Protocol Zero" | Globot, Aegis | Best Agentic, Depth |
| L7 | **Accurate feature naming;** each named capability has an on-screen artefact | Thought-signature misuse | Tooling, Depth |
| L8 | **Say what is deterministic:** "the model decides, allow-listed code acts" as a guardrail | Orbital Assets | Depth, Tooling credibility |
| L9 | **One consistent number set:** measured, small n disclosed, sourced baselines; no extrapolated per-incident millions | §5 Impact | Impact 30% |
| L10 | **A person in a moment:** a named user in a vivid scenario in the first 15 s | All placed winners | Impact |
| L11 | **Submission QA by a cold reviewer** (fresh agent or person) against a checklist, at D7 | §7.6 | All |
| L12 | **Plan backwards from the video;** the video is a 1.5-day workstream with a reshoot buffer | Build timeline | Demo |

---

## 10. What this means for our current plan

**Callback v2** (doc 08 §5) already satisfies L4 (call audio plus screen recording plus logs) and has a natural hero moment: the speaker-flip hard negative, and the case that rules miss shown beside the rules-only baseline. It is **structurally at risk of repeating Resilix**, though: it is a security-ops pipeline (event → investigate → act in a system of record) with a dashboard. Required changes:
1. **Design the reviewer console first:**
   - call playback with a diarized transcript synced to the audio, and speakers coloured;
   - the keyframe with Spark's grounding box on the skipped-verification step;
   - the identity-log timeline joined to call turns;
   - live agent trace streaming;
   - verifier refusals as red rows (doc 14);
   - the gate card with a **"Revoke sessions" approval button**.
2. **Golden case on the public URL:** "Run case CB-hero" replays the pre-recorded call through the real pipeline (live mode) or from cached traces (replay mode, labelled).
3. **Video:**
   - cold-open on the caller's voice ("I'm travelling, new phone…") with the waveform and speaker labels in the product;
   - the problem as narration over it;
   - the hero moment, the baseline contrast, the approval click and the revocation landing, all before 2:00.
4. **State outright** that revocation is deterministic code behind the approval (L8). Name each Meta capability only alongside its on-screen artefact (L7).

**Claim Clock (fallback):**
- **Perception:** screenshots, chats and statements as input are a strength (L4).
- **Hero moment:** the agent spots, inside a screenshot, a scam tell the claimant missed, and the reimbursement figure is computed in code (the £7,050 split).
- **UI:** the claims handler's adjudication workbench, with an approve control.

**The deck** (your Canva browser-tab format) is kept for the Devpost/README page and the final round. It enters the video only as overlay chips (address-bar question, tab names) and one ≤ 10 s architecture card.

---

## 11. Sources

- Gemini 3 Hackathon overview and rules: https://gemini3.devpost.com/ · https://gemini3.devpost.com/rules
- Winners announcement: https://gemini3.devpost.com/updates/40729-the-moment-you-ve-been-waiting-so-patiently-for
- Gallery: https://gemini3.devpost.com/project-gallery
- Winner pages: devpost.com/software/ followed by globot-341w9q, aegis-autonomous-multi-agent-crisis-command, netra-empowering-the-visually-impaired, fakey-ai, agent-weaver, orphafold, orbital-assets, the-bunny-ear-adventure, agentguard-the-semantic-firewall-for-the-agentic-web, procsee, batteryforgeai, gemini-geoflow, cinestream-a2a-mesh-cinematic-learning
- Winner videos (YouTube IDs): FM2LGhqMnC8 (Globot), UCYckQYVM2Q (Aegis), Ax3SkwHOkkk (Netra), Ugw71T82hx8, 4J6_dSrbcFc, V_IF-Vv3PbM, W7CqQGy8dt0, Jpd55mdef9g, xfuLnawvPEs, J8HYX4PNWLs, YUrrsM74gu4, Yrcev5_9Jcs, d7G_H33Iis4
- Resilix: https://devpost.com/software/resilix · https://www.youtube.com/watch?v=UyMBlbcyU7w · https://github.com/TaahirSuleman/Resilix · ResilixPresentation.pdf
