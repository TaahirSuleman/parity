> **Decision taken 29 Oct (doc 18):** after live validation (doc 17), the Accessibility Gap Auditor ("Parity") is the project. Procedure Proof is out (no filming; Meta has no video generation). Callback is shelved (diarization failed its ablation).

# 16 — Fresh evaluation: the approach that wins, and a new ranking of every idea

**Status:** v1, Thu 29 Oct 2026 (D3). Supersedes the ranking in doc 08 §1.

**Inputs:**
- Every project doc (00–15), including the Gemini 3 post-mortem (15) and the Agents 101/102 learnings (12–14).
- The kickoff notes the user restated on 29 Oct.
- Winners of past Meta / Cerebral Valley hackathons.
- A new whitespace check on four new candidates plus a Callback re-check (appendix 16a).
- An independent three-judge panel agent that scored neutral briefs without seeing this ranking (appendix 16a).

**Tags:**
- **[sourced]**: from a cited page.
- **[assumed]**: an estimate.
- **[inferred]**: my judgement.

---

## 0. Bottom line

**Recommendation: build *Procedure Proof*, but only behind a 4-hour spike run Thu night / Fri morning. If it fails, build the *Accessibility Gap Auditor*. Callback v2 drops to third: it now makes sense only with leave days *and* real (not synthetic) inputs.**

**What Procedure Proof is:** proof-of-work for data-centre "remote hands" and maintenance work orders, built from the technician's first-person video plus their spoken callouts.

| Rank | Idea | Golden score (mine / panel) | Risk-adjusted, no leave (mine / panel) | Verdict |
|---|---|---|---|---|
| **1** | **Procedure Proof**: work-order proof for mobile technicians (new) | 8.10 / 7.85 | 7.19 / 6.87 | **Build, if the spike passes** |
| **2** | **Accessibility Gap Auditor**: what you see vs what a screen reader hears (new) | 7.50 / 6.90 | 6.87 / 6.13 | **Fallback** (best expected value per hour) |
| 3 | Callback v2: help-desk vishing forensics | 8.00 / 6.85 | 7.16 / 5.87 | Only with leave + real inputs |
| 4 | First Notice: regulator clocks from the incident bridge | 7.14 / 6.08 | 6.23 / 5.03 | Park |
| 5 | Claim Clock: APP-scam claim adjudication | 6.78 / 5.35 | 6.14 / 4.58 | Drop (employer IP, image-analyzer optics) |
| 6 | Glass: firewall for computer-use agents | 6.65 / 5.93 | 6.02 / 5.15 | Drop (crowded) |
| 7 | Returns-fraud desk | 6.38 / 5.78 | 5.81 / 5.08 | Drop (UPS already does this) |
| — | 15 other ideas from the 27 Oct research | — | — | Stay out (§4) |

Scores are weighted on Meta's rubric: Impact 30, Tooling 25, Depth 20, Demo 25. "Risk-adjusted" multiplies by the chance a convincing core ships at ≈40–45 h without leave. The panel was harsher across the board, but **both of us put Procedure Proof first on ceiling.** We disagree on whether Callback or the Auditor comes second; §5 settles it by fallback logic.

**Three decisions only you can make, tonight:**
1. **G0, employer IP clause.** Applies to every option.
2. **G1, leave.** Two to three days adds +0.35–0.45 to every option's expected score, the biggest single lever.
3. **G-HW, hardware.** Do you have, or can you buy by Friday, a multi-bay NAS or server *or* a cheap managed switch with patch cables? This gates option 1.

---

## 1. What wins this hackathon (the approach)

The evidence and the rule it produces:

| Evidence | What it says | The rule |
|---|---|---|
| **Rubric** (doc 00) | Impact 30 · Tooling 25 ("surprised even us") · Depth 20 · Demo 25 ("holds up live", "genuinely cool to watch"). The top 5 per track are watched live. Indie track: "creativity, technical ambition, and whether it works" | Optimise for the two perception-heavy criteria (Tooling + Demo = 50%) without giving up Impact |
| **Kickoff** (your notes) | Clear user + clear job; define a useful result; working prototype; **put it in someone's hands early**; two themes | One user, one job, one hero case. A real person tries it by Sunday, and their feedback visibly changes something |
| **Meta's workshops** (docs 12–14) | Multimodal agents; verifiable agents (checks inside tools; deterministic, then LLM judge, then human); "see, decide, act"; the LLM plans, code actuates | Architecture = perceive → align/decide in code → verify in tools → gate → act → audit/replay |
| **Gemini 3 post-mortem** (doc 15) | All 3 placed winners were product-first, perceptual, interactive, with a hero moment, a human gate and a person in a moment. Resilix lost on slides, a cut live run, text-only input, a read-only UI and over-length | R5–R8 filters; demo-first storyboard; workbench first; ≤ 2:55 |
| **Past Meta / Cerebral Valley winners** [sourced] | LlamaCon 2025: 3rd = a zero-shot CCTV operator detecting plain-language events in video; 2nd = a fraud/compliance analyser with a voice assistant; best API use = a geologist's own long-document tool. Llama 3 hackathon 2024: 1st = $20 open smart glasses | Meta judges reward **zero-shot perception of the physical world**, glasses/first-person vision and practitioners solving their own problem. Small events, but a consistent taste |
| **Panel critique** (16a) | "You generated every input, so the detector finds what you planted" sank Callback's demo score. "It works on your desk with 20 clips… why believe it generalises?" was the hit on Procedure Proof | **Real inputs beat synthetic ones.** Use device logs as independent ground truth and a second person's clips as held-out tests |

**The approach in ten rules:**
1. **One user, one job, one hero case,** written as one sentence before any code.
2. **Perception decides the verdict, in frame:** a non-text input whose model output is drawn on the media, plus an ablation showing what breaks without it.
3. **Real-world inputs wherever possible.** Synthetic data only for volume, labelled as such, and never in the hero case.
4. **The workbench is the product:**
   - the judge can run the golden case from the public URL without logging in;
   - live and replay modes, both labelled;
   - the trace streams;
   - there is a visible human approval click.
5. **Verifiable-agent architecture, in your own code** (doc 14; no workshop code):
   - checks inside the tools;
   - deterministic first, then the LLM judge, then the human;
   - the model perceives and proposes, code decides and acts;
   - replay.
6. **Honest evidence:**
   - small n, measured;
   - an independent source of truth (a device log, a DOM or accessibility tree);
   - one consistent set of numbers;
   - say plainly what is deterministic.
7. **Put it in someone's hands by Sunday.** One practitioner session, one quote, one change made because of it, mentioned in the video.
8. **Scope to capacity:**
   - thin vertical slice by Saturday night;
   - feature freeze Tue 3 Nov 12:00;
   - video Tue;
   - cold QA and submit early Wed.
9. **Demo-first video:** doc 04 §4.4 v3, ≤ 2:55, product on screen ≥ 80% of the time.
10. **Play the bonus prizes cheaply:**
    - Best Agentic: design for it and say so.
    - Most Viral: post a 20-second hero clip on X at submission.
    - Community Vote: share the gallery link.
    - Skip open-weight and creative builds unless they come free.

---

## 2. What changed since the 27 Oct ranking

- **Time.** It is D3. The D1 spikes (S1/S2) never ran and the workshops weren't attended live (both are captured in docs 11–14). Remaining capacity is ≈40–45 focused hours without leave, or ≈60–70 h with 2–3 days [assumed].
- **The post-mortem.** R5–R8 added; real perceptual input and a workbench UI now weigh heavily (doc 15).
- **Whitespace, re-checked 29 Oct:**
  - **Callback** is still unclaimed, but Humanix ($18M; RSAC 2026 Sandbox top 10) now catches procedure violations *live* and can disable accounts, so it is about one feature away.
  - **Procedure Proof:** factory stations are crowded (DeepHow at Foxconn on NVIDIA Cosmos, Invisible AI, Tulip, Retrocausal, Squint $40M), but **work-order proof for mobile technicians is open** (TechSee only checks photos; Strivr is still positioning).
  - **Accessibility:** the "see vs hear" divergence job exists only as Evinced's in-lab agent and an academic prototype.
  - **Glass and Returns** are crowded.
- **An independent panel rescored everything.** It ranked Callback lower than the 27 Oct panel did (6.85 vs 8.43 golden), mainly because every Callback input is synthetic and Humanix is close.

---

## 3. The shortlist, idea by idea

### 3.1 Procedure Proof — Rank 1 (build behind a spike)
**One sentence:** before a data-centre "remote hands" work order closes, Procedure Proof watches the technician's first-person video, hears their callouts, and proves each step was done on the right object, or holds the ticket.

- **User and job:** a data-centre operations lead (colo or enterprise) closing remote-hands tickets such as drive swaps, cable moves and cross-connects. It generalises to maintenance task cards (MRO).
  - **Status quo** [inferred]: the technician's word plus an optional photo, reviewed by a human or not at all.
- **Hero case:** the technician says *"pulling drive seven"*, but the hand pulls the caddy from **bay six**, a healthy RAID member.
  - Bay identity comes from SAM 3.1's track of the caddy against a bay grid calibrated from one frame, cross-checked by Spark's grounding of the bay labels.
  - The device's own hot-swap or link log confirms it independently.
  - The ticket would have closed "done"; instead the agent holds it and pages on-call.
  - The supervisor watches the 4-second masked clip and approves "hold + page".
  - On camera, a rules-only baseline (ticket text + photo) says "done".
- **Why it scores:**
  - **Tooling:** SAM 3.1 video tracking on real first-person video (its home turf), Voice Transcribe timestamps on the callout, and Spark video and grounding, fused into a say/do mismatch. Panel: "the 'surprised us' combination".
  - **Demo:** a hero clip that needs no narration, with obvious viral potential.
  - **Theme:** *Push the Frontier*, almost word for word ("understand and control a physical system").
  - **Taste:** matches what Meta judges rewarded before (zero-shot video, first-person/glasses).
  - **Not Resilix:** it isn't a backend pipeline.
- **Impact evidence** [sourced, scoped honestly]:
  - Uptime 2025/26: human error plays a part in two-thirds to four-fifths of outages; failure to follow procedures appears in 58% of human-error outages (the leading cause); 20% of major outages cost > $1M.
  - The Boeing door plug (bolts missing, "failure to follow proper manufacturing procedures") as the universal analogy.
  - Do **not** claim 58% of outages are preventable by video.
- **Risks and their fixes:**
  - **Perception reliability:** IKEA-Bench, best open VLM 59% on assembly steps [sourced]. Fix: verify the **end state and the object** (which bay or port changed), not fine motions. Make bay identity deterministic (grid geometry + SAM track) and use the device log as independent truth that also auto-labels the eval. Hold out clips filmed by a second person.
  - **Worker-surveillance optics** (EU AI Act Annex III; smart-glasses privacy is sensitive for Meta). Fix: verify the *work object, not the worker*; SAM blurs faces; no productivity scoring; frame it as the technician's own proof-of-work that protects them in disputes; consent stated.
  - **Hardware dependency.** Fix: any multi-bay NAS or server, or a cheap managed switch with numbered ports and patch cables (the "wrong cable pulled" variant, verified by the switch's link log). Gate G-HW tonight.
  - **Founder fit is partial.** Honest line: "SRE by trade; outages from the wrong drive pulled are our folklore." The problem statement is *Push the Frontier*, which doesn't require first-hand domain.
- **Panel correction:** the panel assumed SAM 3.1 tracking needs a local GPU. We use the hosted Model API (`sam-3.1`, $0.20 per 1,000 video frames), so no GPU is needed. Pre-compute the golden case anyway for replay.
- **Estimates:** ≈55 h in total [assumed]. P(core ships): 0.30–0.35 without leave, 0.55 with leave; higher if the spike passes cleanly.

### 3.2 Accessibility Gap Auditor — Rank 2 (fallback)
**One sentence:** an agent walks your checkout flow, compares what a sighted user sees with what a screen-reader user hears, and proves the failures axe misses, with a fix ready for a developer to approve.

- **Why it ranks here:**
  - The best expected score per hour: pure software, a fully controllable demo app, P(core) 0.45–0.55 without leave.
  - The clearest beneficiaries; citable impact (WebAIM 2026: 95.9% of home pages fail; 5,114 ADA web suits in 2025; EAA in force since June 2025).
  - The exact job is still in labs (Evinced, TaskAudit).
- **Two fixes from the panel:**
  - **The hero must use failures axe-core genuinely passes:** `alt="image"`, an aria-label that contradicts the visible text, a price drawn on a canvas, a focus trap. Unnamed buttons are flagged by axe, so "zero errors" won't reproduce.
  - **Answer "why Meta" explicitly:**
    - Spark computer use to explore unknown flows;
    - grounding to box the visual truth;
    - **Voice Transcribe on the real screen-reader audio**, so the agent literally *listens* to what a blind user hears.
- **Weaknesses:**
  - Tooling is vendor-swappable (panel 6.0).
  - Its outputs (tickets + PRs) echo Resilix: keep the side-by-side see/hear moment as the hero, not the PR.
  - You aren't an accessibility practitioner, so frame it as *Push the Frontier (software)* and recruit one blind tester for the "in someone's hands" beat.

### 3.3 Callback v2 — Rank 3
- **Still the strongest whitespace and money story:** Scattered Spider, the Clorox $380M suit, M&S, Canada's AL26-010 alert naming call-log verification gaps.
- **Why it falls:**
  1. **Every input would be synthetic** (TTS calls, a fake console, fake logs): "the detector finds what you planted".
  2. **Most hours:** three generators plus a media UI, about 60 h.
  3. **Humanix is one feature away.**
  4. **It is the Resilix shape.**
  5. **Its own internal contradictions:** hand-off in seconds vs containment in minutes, and a hard negative an LLM could solve without diarization.
- **What would restore it:**
  - real inputs: a human-voiced call over a real phone line, a real open-source IdP/help-desk UI (e.g. Keycloak), and a revoke that kills a real dev-tenant session on camera;
  - reframe containment around undoing persistence (new MFA factor, OAuth grant);
  - a genuinely speaker-ambiguous case.
- **Choose it only** if you take leave *and* reject Procedure Proof's perception risk.

### 3.4 First Notice — Rank 4 (park)
Your strongest founder fit (SRE). But it is paperwork drama with no adversary or rescue, GRC incumbents already exist, and it relies on fragile 3–7-speaker diarization. Callback beats it on drama and tooling. Its best idea, pinning a clock to the sentence that started it, can live inside any winner's audit trail.

### 3.5 Dropped: Claim Clock, Glass, Returns desk
- **Claim Clock:** employer-IP overlap plus "screenshot reader plus rules table" optics (panel tooling 4.5).
- **Glass:** more than $1.4B of incumbent M&A, Microsoft's preview, and Meta's own LlamaFirewall; attacking Spark on stage is awkward.
- **Returns desk:** UPS Happy Returns "Return Vision" already compares returns with catalog images.

---

## 4. Everything else from the 27 Oct long list (re-screened through R5–R8 and the time left)

| Idea (27 Oct score /60) | Status | Why |
|---|---|---|
| Creator fin-prom video pre-approval (48) | Out | Employer overlap; solely-owned rule |
| Proof-of-Control: grounded control evidence (47) | Out | A Gatekeepers sequel; GRC tools are partly there; screenshots read as the analyzer pattern |
| Scam-ad / finfluencer flagger (47) | Out | Employer adjacency; Meta hosts the ads, so awkward in front of these judges |
| Insurance claim-pack consistency (47) | Out | Tractable/Shift/CCC territory; no forcing function; staging damage is hard |
| Recall Desk: deepfake-payment recall (44) | Out | Ground truth and build both scored 2; needs bank rails |
| Merchant storefront KYB (44) | Out | Incumbents; crawl legality |
| UFLPA admissibility auditor (41) | Out | Data rights; founder fit |
| KYC deepfake ring linkage (41) | Out | Biometrics policy; crowded IDV |
| CRA 24-hour vulnerability agent (41) | Out | Text-only (fails R5, criterion 4) |
| Assurance-artefact forensics (40) | Out | Gatekeepers sequel |
| HTS/ECCN classification (40) | Out | Reads as retrieval; crowded |
| Affiliates-Rule ownership exposure (38) | Out | e2open+Kharon, Sayari |
| Vessel KYC (34) | Out | Data access; war adjacency |
| Compliance Shockwave 1.0 (32) | Out | Meta tooling not load-bearing |
| Field/factory SOP verification at fixed stations | Folded into #1 | Crowded (NVIDIA partners); only the mobile-technician scope survives |

---

## 5. How the two rankings were reconciled

- **Mine:** Callback ≈ Procedure Proof > Auditor.
- **Panel:** Procedure Proof > Auditor > Callback.

I moved Callback to third for four reasons:
1. The panel's "synthetic everything" objection is exactly the Gemini 3 lesson (real perceptual input won).
2. Its ≈60 h does not fit without leave.
3. Its shape repeats Resilix.
4. If Procedure Proof's spike fails on Friday, the fallback has the least time of any option, so it must be the most shippable. That is the Auditor (P(core) 0.45 vs 0.30 without leave).

**The panel's robust-play estimate** (spike Procedure Proof, fall back to the Auditor): expected ≈ 6.6 without leave and ≈ 7.0 with leave. That beats committing to any single idea except Procedure Proof with a clean spike.

---

## 6. The next 24 hours (decision protocol)

| When (SAST) | Step | Pass → | Fail → |
|---|---|---|---|
| Thu, first thing | **G0:** read the IP and moonlighting clause; personal laptop and accounts only | continue | stop and seek consent |
| Thu | **G1:** decide leave (Mon 2 + Tue 3 Nov is ideal) | plan at 60–70 h | plan at 40–45 h, no stretch goals |
| Thu | **G-HW:** confirm a multi-bay NAS or server, or buy a managed switch + patch cables (≈R600–R1,200 [assumed]) | spike D | go straight to the Auditor |
| Thu evening (4 h) | **Spike D** (details below) | build D | build the Auditor from Fri |
| Thu, parallel (15 min) | Claim credits, set the Spend Limit, `GET /v1/models` (confirm `sam-3.1`), fresh public repo + `HACKATHON_SCOPE.md` | — | — |
| Fri | Line up one tester: an SRE or DC-ops friend for D, or a blind screen-reader user plus a front-end developer for the Auditor. Session on Sat or Sun | — | — |

**Spike D:**
1. Film 6 first-person clips: 2 correct, 2 wrong bay or port, 1 skipped step, 1 second-person clip.
2. Run Voice Transcribe on the callouts to get timestamps.
3. Have Spark ground the bay or port labels on one calibration frame.
4. Run SAM 3.1 video tracking of "drive caddy" or "patch cable" on the hero clip.
5. Compute "which bay or port changed" in code and compare it with the device log.
6. **Pass:** ≥ 5/6 end states correct, a stable track on the hero clip, ≤ 90 s and ≤ $0.50 per clip.

**Build plan if Procedure Proof passes** (backwards from the video):

| Day | Work |
|---|---|
| **Fri** | Contracts, work-order model, case record, checks inside tools |
| **Sat** | Thin slice end to end on the hero clip: intake → Voice + SAM + Spark → alignment (code) → verifier → gate → hold/close in a mock ticketing system → audit/replay. Workbench v1: video player with mask overlay, callout transcript, step checklist, approve button |
| **Sun** | 20–30 clips (including a second person's); device-log labels; eval table; ablations (no Voice / no SAM / no grounding); tester session; Uptime-sourced impact card |
| **Mon** | Deploy with the golden-case button and replay; README; essays; polish |
| **Tue** | 12:00 freeze; video (script, voiceover, captions, ≤ 2:55); cold review against the doc 04 Part 7 checklist |
| **Wed** | Fix list; X post; **submit by 18:00 ET** |

---

## 7. What would change this ranking

- **Spike D fails on bay or port identity, or there is no suitable hardware** → the Auditor.
- **Leave granted, and you can stage real Callback inputs** (a human-voiced phone call, Keycloak, a dev tenant) → Callback rises to #2 and competes with the Auditor.
- **The IP clause blocks compliance or security-adjacent work** → Procedure Proof and the Auditor are the least exposed; Callback and Claim Clock are out.
- **Office hours say hosted SAM 3.1 video tracking is rate-limited or slow at our clip lengths** → keep SAM on the hero clip only and use Spark keyframes for the rest.

---

## Sources

- Uptime Institute outage analysis: [The Register, 7 May 2025](https://www.theregister.com/2025/05/07/human_error_a_factor_in); [BusinessWire, 13 May 2026](https://www.businesswire.com/news/home/20260513289344/en/Uptime-Announces-Annual-Outage-Analysis-Report-2026)
- Boeing door plug: [AVweb, 10 Jul 2025](https://avweb.com/aviation-news/ntsb-cites-boeing-faa-shortcomings-in-alaska-door-plug-final-report/)
- DeepHow live SOP verification at Foxconn: [BusinessWire, 2 Jun 2026](https://www.businesswire.com/news/home/20260602068205/en/)
- IKEA-Bench, VLM assembly-step recognition: [arXiv 2604.00913](https://arxiv.org/html/2604.00913v1)
- Evinced screen-reader agent (in labs): [Evinced](https://evinced.com/ai/monitoring)
- TaskAudit: [arXiv 2510.12972](https://arxiv.org/pdf/2510.12972v1)
- UsableNet 2025 ADA suits: [UsableNet](https://info.usablenet.com/2025-year-end-digital-accessibility-lawsuit-report-plain-text)
- WebAIM Million 2026 summary: [Priority Pixels](https://prioritypixels.co.uk/insights/web-accessibility-is-getting-worse-according-to-the-2026-webaim-million-report/)
- Humanix: [Help Net Security, 29 May 2026](https://www.helpnetsecurity.com/2026/05/29/humanix-violations-detection/)
- Canadian Cyber Centre AL26-010: [cyber.gc.ca](https://cyber.gc.ca/en/alerts-advisories/al26-010-cyber-criminals-social-engineering-enabled-compromise-enterprise-saas-environments)
- UPS Happy Returns Return Vision: [Retail Dive, 12 Jan 2026](https://www.retaildive.com/news/ups-happy-returns-vision-software-pilot-everlane/809083/)
- Akamai acquires LayerX: [Fintech Global, May 2026](https://fintech.global/2026/05/19/akamai-acquires-layerx-to-close-enterprise-ai-gap/)
- LlamaCon hackathon winners: [Meta AI blog](https://ai.meta.com/blog/llamacon-hackathon/)
- Llama 3 hackathon recap: [Meta AI blog](https://ai.meta.com/blog/llama-3-hackathon-recap-cerebral-valley/)
