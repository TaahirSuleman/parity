# Winning Recipe v3: from The Compliance Gatekeepers (won) and Resilix (didn't place) to the Meta Hackathon

**Status:** v3, 2026-10-29. v2 (2026-10-27) was built from the IBM 2nd-place win.
- **v3 adds Part 7:** lessons from Resilix (Gemini 3 Hackathon, not placed) compared against all 13 Gemini 3 winners. See `15-gemini3-postmortem-resilix-vs-winners.md`.
- **v3 replaces the §4.4 video storyboard** with a demo-first one.
- **v3 tightens §4.1–4.2** around the product surface and honest actuation.

**Reads with:** `00-constitution.md` (rubric = objective function), `03-meta-ai-tooling-reference.md`, `14-build-playbook-verifiable-agents.md`, `15-gemini3-postmortem…`.

**Purpose:** turn one winning recipe and one losing recipe into a single recipe tuned to Meta's rubric, judges and tooling.

> **The two-line version.** Gatekeepers won with a buyer's question, a forcing function, an agent with authority and numbers everywhere. Resilix had better engineering than any Gemini 3 winner and still lost on what judges *saw*:
> - slides first;
> - a live run cut out;
> - text-only input;
> - an afterthought UI;
> - over-length;
> - inconsistent numbers.
>
> Keep the Gatekeepers story machine, add the evidence machine, and **deliver both as narration over a perceptual, interactive product that the judge watches working**.

Evidence base (v2): the 7-slide winning deck ("The Gatekeepers", Canva, Nov 23 2025), the lablab submission page (2nd place, Agentic AI Hackathon with IBM watsonx Orchestrate; tags Finance, Productivity, Procurement & Policy), the IBM judging criteria, the repository structure (visible on slide 7; the repo itself was not reachable from this session), and Taahir Suleman's CV.

---

## Part 1 — What won, slide by slide

The deck uses a **browser-window metaphor**: every slide is a browser tab (Introduction → Problem → Solution → Impact) and the address bar holds the *question the buyer would type*. Navigation doubles as a progress bar and the buyer's question frames every section.

| # | Tab / address-bar question | Content | Job it does |
|---|---|---|---|
| 1 | "How can my bank automate its regulatory compliance?" | Brand **The Gatekeepers**; tagline **"Where non-compliance is terminated"**; node-graph logo | States the buyer, the job and the promise in one glance. The brand implies agency (it *stops* things) |
| 2 | Problem · "Why is financial regulatory compliance so inefficient?" | **"Slow Manual Reviews of Strict Regulations"** — three cards: **scale** (50,000+ vendors; 60% of organisations lack monitoring resources), **accuracy** (83% of risks appear post-due-diligence: humans fail to validate evidence), **liability** (DORA fines of 1% of average daily global turnover) | Rule of three: volume × error × consequence. Each card is a number |
| 3 | Problem · "What is DORA?" | Mandate, stakes, **Article 28**, daily fines, **January 2025** | The *forcing function*: a regulation with a date and a penalty turns "nice to have" into "must buy now" |
| 4 | Solution | Three columns: **Multi-Agent System** (autonomous orchestration of five tools; enforcement authority to block vendors without human approval; Box → watsonx.ai → ERP → Outlook) · **Core Capabilities** (Granite analyses contracts against DORA; auto-generates legal amendments with the missing clauses; Outlook notifications with attachment tracking) · **Autonomous, Scalable, Built for Accuracy** (zero-touch ingestion→notification; custom Python ADK tools; continuous monitoring) | What it is, what it does, why it's trustworthy |
| 5 | Solution · "What does the solution look like" | **Phased swimlane architecture**: User request → **P1 Ingestion** (Box) → **P2 AI Analysis** (Granite 3.3 8B: extraction, semantic clause detection, 0–100 score → structured report) → **P3 Enforcement & Decision** (diamond: score ≥ 80 → green APPROVE / < 80 → red BLOCK, ERP status update + audit) → **P4 Remediation** (amendment generator → formal amendment + email draft) → **P5 Communication** (Outlook via Graph → message ID + timestamp) → User summary. A central **orchestration control plane** spans all phases. Stack callouts box | Shows the system *acts in systems of record*, with a visible decision gate and colour-coded branches |
| 6 | Impact · "What value does your solution provide?" | **"Speed, Scale, Certainty"** — three columns: **Velocity & Accuracy** (99.2% time reduction, 4 h → 2 min; consistency; complete timestamped audit trail) · **Financial Protection at Scale** ($245M+ liability avoided = $40M review cost + $200M+ penalties) · **Operations Simplified** (50,000 contracts in 1,667 h vs 200,000 h; 60% of compliance team freed; blocked "immediately upon detection, not after months") | Before/after, money, capacity. Every claim is a number |
| 7 | Solution | Live demo from the IDE + terminal | Proof it runs |

**Repository pattern (slide 7):** `agents/` with six YAML agents (**supervisor**, ingestion, dora_gatekeeper, erp, communication, audit) · `tools/` with five Python tools (box_integration, erp, amendment, outlook_integration, audit) · `data/` (contracts, emails, `dora_requirements.txt`, **`generate_sample_contracts.py`**, `vendor_db.json`) · `integrations/`, `tests/`, `config/` · a full doc suite (`README`, `ARCHITECTURE`, `MULTI_AGENT_GUIDE`, `DEMO_SCRIPT`, `TEST_CASES_GUIDE`, `DEPLOYMENT_GUIDE`, `QUICK_START`, `PROJECT_SUMMARY`) · test scripts (connection, local agent, complete workflow, multi-agent workflow).

**Why it beat most of ~8,000 entrants** (mapped to IBM's four criteria — Application of Technology, Presentation, Business Value, Originality):
1. **Business Value:** a named, regulated buyer with a dated legal mandate and a fine expressed as a fraction of revenue.
2. **Application of Technology:** the platform's orchestrator was the control plane, not a wrapper; five real tools; agents *act* (block, update ERP, draft, send) rather than advise.
3. **Presentation:** a memorable brand, buyer-question framing, rule-of-three cards, one architecture diagram, numbers everywhere.
4. **Originality:** "enforcement authority" — an agent with the power to say no — is a stronger idea than an assistant that summarises.
5. **Craft signals:** the doc suite, a synthetic-data generator, and workflow tests made a 10-day solo project look like a product.

---

## Part 2 — The recipe, distilled (the Gatekeeper pattern)

1. **The buyer's question is the title.** A specific person in a specific institution asking how to make a costly obligation go away.
2. **A forcing function.** Regulation, deadline, penalty or loss that makes the status quo untenable and gives a number to anchor value.
3. **Pain as volume × error × consequence.** Three cards, three numbers.
4. **An agent with authority.** It changes the state of systems of record (block, approve, file, pay, remediate), not just produce text.
5. **Phased, branching architecture.** Ingest → analyse → decide (visible gate, red/green) → remediate → communicate → audit, under one orchestrator.
6. **Remediation, not just detection.** It writes the amendment, the fix, the notice.
7. **Impact as speed / money / capacity.** Per-unit before/after, then scaled.
8. **Live end-to-end run** on a realistic case.
9. **A repo that looks like a product.** Supervisor + specialist agents, tools, a synthetic-data generator, tests, a doc suite.

---

## Part 3 — Gap analysis against Meta's rubric

IBM criteria and Meta's rubric overlap in shape, but Meta's judges are Meta engineers, the rubric is weighted, the primary artifact is a **3-minute video** (not slides), and the tooling bar is "surprised even us". What transfers and what must change:

| Recipe ingredient | Meta category it feeds | Verdict | Required upgrade |
|---|---|---|---|
| Buyer's question + brand + tagline | Impact 30%, Demo 25% | **Keep** | Move it into the first 10 seconds of the video, on screen and in the voiceover |
| Forcing function | Impact | **Keep** | Cite sources on screen; Meta asks "who benefits and how much does it matter" |
| Volume × error × consequence | Impact | **Keep, harden** | Every figure sourced in the README; avoid round, uncited numbers |
| Impact math ($245M, 99.2%, 60%) | Impact | **Upgrade** | Publish a transparent cost model: inputs, sources, per-case cost/time *measured on our own runs*, sensitivity range. Engineers discount unexplained headline numbers |
| "Zero human error", "100% consistency" | Technical Depth 20% | **Replace** | Measured **precision / recall / F1** on a labelled eval set, with error analysis. Meta's Agents 102 session is literally "verifiable agents". Absolute claims will cost credibility with these judges |
| Enforcement "without human approval" | Best Agentic bonus; Depth | **Upgrade to calibrated autonomy** | Auto-act above a confidence/evidence threshold, route the rest to a human with an evidence pack; report the **autonomy rate** and **error rate at that rate**. This is exactly how Best Agentic is judged ("level of autonomy, effectiveness, practical usefulness") and matches Muse Spark 1.3's "confirm before consequential actions" and the computer-use safety-check design |
| Single LLM (Granite 8B) doing extraction + scoring | Tooling 25% | **Replace** | Meta capabilities must be load-bearing and ideally multimodal: Spark video/PDF/image understanding, perception grounding → SAM 3.1 masks, Voice diarization, 1M-context whole-case reasoning, structured outputs at every hop (constitution VI.5 rungs 1–4) |
| One orchestrator + tools | Depth, Tooling | **Upgrade** | Orchestrator + role specialists with schema contracts + an independent **verifier agent** + deterministic validators + append-only audit + replay. Consider Muse Code `muse serve` / subagents as the substrate |
| Threshold diamond (score ≥ 80) | Depth, Demo | **Keep the visual, change the logic** | Decision combines rule checks (deterministic) and model judgement with cited evidence; threshold calibrated on the eval set, shown as a precision/recall curve |
| Remediation (amendment + email) | Impact, Agentic | **Keep** | Remediation artefacts carry citations back to the evidence |
| Swimlane architecture slide | Demo, Depth | **Keep** | One diagram in the video (≈10 s) and in the README; animated highlight of the live run moving through the phases |
| Timestamped audit trail | Depth | **Upgrade** | Turn it into a visible **trace/observability view** in the product: every model call, tool call, decision, validator result, cost, latency |
| Mock ERP (Beeceptor) | Depth (honesty) | **Acceptable if labelled** | Name every mock in `HACKATHON_SCOPE.md` |
| Deck → live IDE demo | Demo 25% | **Replace** | Produced 3-minute video with voiceover (storyboard below) plus a hosted product that "holds up live" on an unseen input |
| Doc suite + synthetic data generator + tests | Depth | **Keep** | Add eval harness, results table, CI regression gate, `HACKATHON_SCOPE.md` |
| Browser-tab narrative device | Demo | **Keep as motif, but as overlays** (v3) | The tabs (Problem / Solution / Proof / Impact) and the address-bar question become **chips and captions over product footage**, not slide segments. The full deck lives on the Devpost/README page and supports the final round (Part 7, L1) |

**The single biggest shift:** IBM rewarded *a convincing story about an autonomous system*. Meta's rubric and judges reward *a convincing story backed by measured evidence, built on capabilities only Meta's stack has*. Keep the story machine; add the evidence machine and the Meta-specific perception layer.

---

## Part 4 — The Meta recipe (operational template)

### 4.1 Pitch skeleton (used for the video, README opening and the form's Project Description)
1. **Buyer's question** (address bar): "How can [role] at [institution] [stop costly thing]?"
2. **Brand + tagline** that implies authority.
3. **Forcing function:** regulation/loss + date + penalty, sourced.
4. **Pain cards:** volume · error rate of the manual process · consequence (each with a number and a source).
5. **What it does in one sentence:** "[Brand] autonomously [ingests X], [verifies Y with evidence], [decides and acts in Z], and [remediates], with every decision traced."
6. **Why Meta:** the two or three Meta capabilities the product cannot exist without (answers form Q "Why are Meta's models important?").
7. **Proof:** P/R/F1, autonomy rate, cost per case, time per case, on N labelled cases.
8. **Impact:** per-case before/after → scaled to the buyer → scaled to the industry, with the model linked.
9. **(v3) A person in a moment:** one named user in one vivid scenario, used as the video's cold open and the README's first paragraph. Gemini 3 examples: "4:55 PM Friday, $50M cargo"; a 911 call "ordering a pizza".
10. **(v3) The hero moment:** one sentence describing the input a human or a rules engine gets wrong and our system gets right. It is the centre of the video, the live demo and the README GIF.

**Consistency rule (v3):** one number set, with measured n disclosed and baselines sourced, used verbatim in the video, deck, README and form. Never extrapolate per-incident millions from a handful of runs (Resilix: n = 2 led to "$934k per incident").

### 4.2 Architecture template (the swimlane, Meta edition)
`Trigger/queue` → **P1 Ingest** (files, video, audio, web; Files API, 1M context) → **P2 Perceive** (Spark multimodal understanding; perception grounding → SAM 3.1 masks/tracks; Voice transcription + diarization) → **P3 Analyse** (specialist agents per rule family; strict JSON contracts; citations to page/timestamp/pixel) → **P4 Verify** (independent verifier agent + deterministic validators; disagreement → escalate) → **P5 Decide & Act** (calibrated gate: auto-act / human review / block; state changes in system of record) → **P6 Remediate** (fix, amendment, notice with citations) → **P7 Communicate & Audit** (notifications; append-only trace; replay). One orchestration control plane spanning all phases, with `reasoning_effort` and model tier set per role (Spark for volume, Wonder for the hardest judgement).

**(v3) Two additions to the template:**
- **Product surface (P0, designed first).** The reviewer's workbench is where every phase becomes visible and where the human acts:
  - trigger a case;
  - watch the agent trace stream;
  - see perception output drawn on the media (boxes, masks, speaker turns, timestamps);
  - see verifier refusals as red rows;
  - approve or reject at the gate;
  - watch the system of record change.

  The public URL offers a no-login **"Run the golden case"** button with live and replay modes, both labelled. There is no silent mock fallback: if live calls fail, the UI says so.
- **Honest actuation.** The model decides; allow-listed, deterministic code acts after the gate. Say this in the README and the video as a safety feature, the way Orbital Assets did ("the valuation is locked in TypeScript; the model narrates").
  - Never imply the model wrote an artefact that a template produced.
  - Name each Meta feature only alongside the artefact it produces. Resilix lost credibility by calling a custom RCA schema "thought signatures".

### 4.3 Evidence template (what the README and video must show)
| Metric | How produced |
|---|---|
| Precision / recall / F1 per violation type and overall | Labelled eval set (synthetic + real public cases), held out from prompt tuning |
| Autonomy rate and error at that rate | Calibrated gate on the eval set; PR curve |
| Time per case (p50/p95) and cost per case | Measured from traces |
| Before/after vs manual baseline | Sourced manual time/cost per case |
| Robustness | Unseen-input live run in the video; prompt-injection test cases |

### 4.4 Video storyboard (v3, demo-first, hard cap 2:55)
*Replaces the v2 storyboard, which spent ~95 s off-product (slides, diagram, eval table, impact). Every Gemini 3 placed winner was product-first, and Resilix lost time on slides, a cut and over-length (doc 15 §4).*

| Time | Chapter chip (overlay) | On screen (always the product, unless noted) | Voiceover purpose |
|---|---|---|---|
| 0:00–0:08 | Address bar: the buyer's question | **Scope line first (organisers' guidance, 30 Oct):** one spoken and captioned sentence on what was pre-existing vs built this week (e.g. "Built this week on Meta's Muse Spark; only Playwright and axe-core are pre-existing open source"), delivered over the product already on screen. Then **cold open on the hero input inside the product**: the media playing (a call waveform, a screenshot, a frame) with the brand and a one-line hook overlaid | The person and the moment (L10) |
| 0:08–0:25 | Problem | Still the product, idle on the case. **One** overlay card (≤ 8 s): forcing function + two sourced numbers | Why now, what it costs, who suffers |
| 0:25–1:35 | Solution (live) | **Trigger from the UI** → agent trace streams → perception drawn on the media (boxes, masks, speaker turns, timestamps) → verifier refuses something (red row) and the agent fixes it → **hero moment** (L2) → gate card → **human clicks Approve** → system of record changes. Uncut, or speed-ramped with a visible "2×" label. Never "I skipped ahead" | Autonomy with control; Meta capabilities doing visible work |
| 1:35–1:55 | Proof (contrast) | Side by side in the product: the rules-only baseline (or the model with the key Meta capability ablated) gets the same case wrong | Why it needs Meta; Impact |
| 1:55–2:10 | Under the hood | **≤ 10 s** architecture card (the swimlane), then back to the trace view showing per-call model, effort, tokens and latency | Depth, honest actuation (L8) |
| 2:10–2:35 | Proof (numbers) | The product's **Eval tab**: P/R on N labelled cases, autonomy rate, cost and time per case, one honest failure | Verifiability |
| 2:35–2:50 | Impact | One per-case before/after, scaled once, sourced; close on brand + URL + "run the golden case yourself" | Close on impact |
| 2:50–2:55 | — | End card | Buffer under the 3:00 limit |

**Rules:**
- **Organisers' guidance (30 Oct):**
  - Judges stop watching at 3:00.
  - The video is scored under **Demo (25%)** and **Use of Meta AI Tooling (25%)**, so every Meta model call shown must be visible as such: an on-screen label naming the model on each perception, decision and action step.
  - Show the product working, not slides.
  - Open with the pre-existing vs built-this-week line.
- **Timing:** product on screen ≥ 80% of runtime; slides and cards ≤ 20 s in total; **render, then measure length** before uploading.
- **Production:** script first; record the voiceover separately; music bed; **burned-in captions**; zoom and highlight on the evidence.
- **Content:**
  - every number on screen matches the README;
  - show only hackathon-built functionality;
  - nothing on screen contradicts the README (e.g. "autonomous" vs "approval-gated");
  - hide failed or test runs from lists.
- **QA:** a cold reviewer watches the final cut against the Part 7 checklist before upload.

### 4.5 Repository template
`agents/` (supervisor + specialists + verifier, each with a schema) · `tools/` · `perception/` (Spark/SAM/Voice adapters) · `eval/` (dataset, labels, harness, results) · `data/generate_*.py` · `observability/` (trace store + viewer) · `tests/` · docs: `README`, `ARCHITECTURE`, `EVALUATION`, `DEMO_SCRIPT`, `HACKATHON_SCOPE`, `QUICK_START`, `COST_MODEL`.

---

## Part 5 — Founder fit (from the CV)

**Profile:** Backend Engineer at impact.com (Cape Town), since Oct 2024 progressively: semantic search PoCs (Elasticsearch, Redis, Vertex AI) → data-transformation agent turning unstructured product data into schemas for product detection on scraped pages → **agentic orchestration automating regulated compliance reviews of scraped content for financial clients** → autonomous multi-agent DevOps ticket resolution → LLM sentiment summaries over large unstructured input → now **production compliance agents** (automated onboarding, product/rule ingestion, dynamic system-prompt generation) and an **internal MCP + knowledge graph** with observability, guardrails, rate limiting, access control and feedback loops. UCT BBusSci (Computer Science), top of class with distinction. Java, Python, TS, Kotlin, SQL; GCP/Vertex, Docker, Mongo, Elastic, Redis; evaluations and agentic systems.

**Track record (the pattern):** OfferZen Agentic Hackathon — won; IBM Agentic — 2nd solo; projects: **Resilix** (autonomous SRE: detect → RCA → Jira → remediation PR), **Neural Guardians** (multi-agent coupon-abuse fraud detection with feedback loops and BigQuery), **Compliance Gatekeepers** (DORA). Every one is the same shape: **an autonomous agent that clears an operational queue in a costly, rule-bound domain — detect, decide, act, remediate.** That shape is the recipe; the domain is the variable.

*(v3 note.)* Resilix was a 3-person team entry in the Gemini 3 Hackathon and did not place among 13 winners from ~4,500 entries. The shape is not the problem. The weak points were how it was **shown**, the **text-only input** and the **product surface** (Part 7). Wherever the shape is reused, it must be delivered perceptually and interactively.

**Unfair advantages to exploit:**
1. **Firsthand regulated-compliance automation in production** (financial clients, scraped web content, rule ingestion) → credible "Build for Your World" story and real knowledge of where manual review fails.
2. **Partnership/affiliate/creator marketing domain knowledge** (impact.com) → insight into high-volume, multimodal content that must be checked against rules (disclosures, financial promotions, brand guidelines) and into fraud patterns (coupon abuse).
3. **Production agent engineering**: observability, guardrails, evals, MCP, knowledge graphs — exactly what Technical Depth rewards.
4. **Proven solo execution** under hackathon time pressure, with a winning presentation format.

**Constraints and risks:**
- **Solo, ~8 days left, while employed.** Scope must reach an end-to-end run by day 3.
- **Employer overlap.** A project too close to impact.com's own compliance product could raise IP-assignment or conflict-of-interest questions, and the Official Rules require the submission to be solely owned by the entrant. Check the employment contract's IP clause; prefer an adjacent domain or a clearly distinct product, built only on personal time, equipment and public/synthetic data.
- **Skill gaps relative to some options:** no GPU/post-training history on the CV → RL/SFT on open weights is a stretch goal, not the plan. Frontend/video production are not listed → budget time for the trace UI and the video.
- **Avoid Gatekeepers déjà vu:** a second contract-vs-regulation checker would be original to Meta's judges but not to you; reuse the pattern, change the medium. Meta's tooling advantage is multimodal (video, images, audio, pixel-level grounding), whereas Gatekeepers was text-only.

---

## Part 6 — Brief for the next stage: research across adjacent industries

**Search space.** Domains adjacent to the CV where a costly, rule-bound queue is cleared manually today, and where the inputs are **messy and multimodal** (so Meta's perception stack is load-bearing):

| Adjacent cluster | Link to CV | Example queues to investigate (hypotheses, not conclusions) |
|---|---|---|
| Marketing & financial-promotions compliance | Current role; scraped-content compliance for financial clients | Creator/"finfluencer" video and image content against disclosure and financial-promotion rules; ad and landing-page review at volume |
| Partnership / affiliate / ad fraud | Neural Guardians; impact.com | Affiliate, coupon, click and lead fraud investigation and clawbacks |
| Third-party / vendor risk (DORA follow-on) | Compliance Gatekeepers | Register-of-information, KYB, ongoing vendor evidence monitoring |
| Payments & disputes | Financial clients | Chargeback evidence assembly and representment; merchant onboarding review |
| Insurance & claims | Regulated, document- and image-heavy | First-notice-of-loss triage, damage evidence from photos/video, subrogation, fraud signals |
| Trade & supply chain | Unstructured product data → schemas | Customs tariff classification from product images/specs, sanctions/dual-use screening, label/packaging compliance |
| Finance operations | Agentic data transformation | Invoice/AP exception handling, expense audit with receipt images |
| Operations / SRE (Resilix follow-on) | DevOps ticket orchestration | Incident triage — likely crowded and close to Muse Code's own territory |
| Physical-world inspection ("Push the Frontier") | Pattern transfer | Infrastructure, construction or safety inspection from drone/phone video with SAM-grounded findings |

**Screening for the research:** constitution Article VIII (12 criteria, 7 hard-fail) **plus** three recipe-specific filters: (a) a forcing function with a date or penalty; (b) the agent can hold real authority over a system of record, with calibrated autonomy; (c) at least one input modality beyond text that Meta's stack uniquely handles. Also excluded: anything that drifts into medical advice, hiring decisions, or politics (anti-project list), and anything too close to the employer's product.

**Research deliverable:** a long list scored against the criteria, narrowed to a top 3, each with the user + job + cost of the status quo, the agent graph, ground-truth source, Meta capabilities per hop, a draft storyboard, build estimate and kill criteria — then a final pick before development starts.

---

## Part 7: Lessons from Resilix (Gemini 3 Hackathon, not placed) against the 13 winners (v3)

Full evidence is in `15-gemini3-postmortem-resilix-vs-winners.md`.

**What Resilix got right, and we keep:**
- typed contracts;
- 122 tests;
- a deterministic simulator;
- real systems of record (Jira, GitHub);
- a merge-policy gate;
- per-role reasoning budgets.

No Gemini 3 winner showed a test suite. Meta's Technical Depth (20%) and Agents 102 reward exactly these, so we keep them. They just don't win on their own.

**What the winners had that Resilix didn't:**
1. **Product-first videos.** Every top-3 video is product-first; Resilix spent its first ~75 s on slides.
2. **A live hero moment.** Resilix cut its live run.
3. **Perceptual input.** All three placed winners take satellite, audio/drone or live-camera input; Resilix was text-only.
4. **A UI where the decision happens.** Resilix had a read-only monitor, with incidents triggered from a CLI.
5. **A visible human approval click.** Resilix's video said "merged autonomously without human interaction".
6. **A person in a moment.** Resilix had an abstract "cascading errors".
7. **Under 3:00, with everything inside it.** Resilix ran 4:14, with impact at 3:40.

**Recipe rules added in v3** (these extend the R1–R4 filters in constitution Article VIII; see doc 15 §9 for the evidence behind each):

| # | Rule | Check |
|---|---|---|
| L1 | Demo-first video: product by 0:05, ≥ 80% of runtime on the product; deck only as overlays (≤ 10 s each, ≤ 20 s total) | Storyboard §4.4; timed edit |
| L2 | One live, uncut hero moment, in which an input that humans or rules get wrong is shown being got right | Written in §4.1 item 10 before building |
| L3 | Hard cap 2:55; everything that matters lands before 2:50 | Measured on the rendered file |
| L4 | Perception is visible: non-text input, model output drawn on the media, ablation shows the drop | Tooling 25%; Q8 of the form |
| L5 | The UI is the workbench: trigger, stream, evidence, approve, all in the UI; a no-login golden-case button on the public URL; no silent mock fallback | A judge can run it in < 60 s |
| L6 | A visible human gate with a reason | Recorded in the video |
| L7 | Accurate feature naming; each named capability has an on-screen artefact | Cold-review checklist |
| L8 | Honest actuation: "the model decides; allow-listed code acts" stated as a guardrail | README "How it acts" section |
| L9 | One consistent, measured number set; n disclosed | grep across video script, README, form |
| L10 | A person in a moment in the first 15 s | Script line 1 |
| L11 | Submission QA by a cold reviewer at D7 | Checklist below |
| L12 | Plan backwards from the video: feature freeze D6 noon; video D6–D7 with a reshoot buffer | Build plan |

**Recipe screening filters added to R1–R4:**
- **R5 Perceptual load:** at least one non-text modality is load-bearing *and* demoable on screen.
- **R6 Workbench:** the decision moment naturally lives in a UI a judge can operate.
- **R7 Hero moment:** a one-sentence "rules or humans miss it, we catch it" moment exists for the golden case.
- **R8 Face:** a named person in a vivid scenario, not an abstract system failure.

**Cold-review checklist (L11).** Run at D7 by a fresh agent or a person who has not seen the build.
- **Video:**
  - length ≤ 2:55;
  - product visible at 0:05;
  - no slide > 10 s;
  - hero moment uncut or labelled "2×";
  - the human approval click is visible;
  - impact lands before 2:50;
  - burned-in captions;
  - no failed or test runs visible on screen.
- **Consistency:**
  - every number matches the README;
  - no statement contradicts the README;
  - every Meta feature named matches what the code does;
  - every title, slide and file name belongs to *this* project.
- **Live product:**
  - the public URL loads without login;
  - the golden-case button runs to completion (live or labelled replay);
  - no mock data is shown unlabelled.
- **Repo:**
  - every file the README links to exists;
  - the README states what is deterministic;
  - the architecture diagram is an image;
  - the hackathon-built scope is stated.
- **Links:** YouTube public; all links open; no Drive links; every contributor listed.
