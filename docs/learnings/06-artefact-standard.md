# Artefact Standard — Demo-First Build (Judging Objectives → Ideal Demonstration → Architecture & MVP)
**Status:** v1, 2026-10-27 · **Applies to:** Callback, Claim Clock, First Notice (finalists from `05-problem-research-and-top-3.md`) · **Governed by:** `00-constitution.md` (rubric, rules, Article VIII/IX), `04-winning-recipe.md` (story machine) · **Evidence base:** a local research note (not in this repository) (Working Backwards PR/FAQ, Shape Up, Google design docs, ADRs/MADR, C4, Husain/Shankar and Anthropic eval guidance, Datasheets for Datasets, OWASP LLM Top 10 2025 + Agentic Top 10, OpenTelemetry GenAI conventions, walking skeleton / tracer bullet).

## 1. The principle
We do not design a platform and then make a presentation. We start from what Meta's judges score, define the single most defensible 3-minute demonstration of that, and engineer the **smallest production-quality system** that can deliver it. The demo must not be theatre: every on-screen claim is either **measured** (run ID), **sourced** (citation) or visibly labelled as a **target/hypothesis**. Mocks, replays and speed-ups are labelled on screen.

**Order of work and why:**

| Step | Question it answers | Artefacts | Rubric served |
|---|---|---|---|
| 1. Judging objectives | What evidence would score 9–10 in each category? | A. Judging Objectives Map | all |
| 2. Ideal demonstration | What does a judge see in 3 minutes, and what must be true for each frame? | B. Golden-Path Demo Spec · C. PR/FAQ & Pitch | Demo 25, Impact 30 |
| 3. Architecture & MVP | What is the smallest system that makes every frame true? | D. Lean AI-PRD · E. Tech Spec + ADRs | Depth 20, Tooling 25 |
| 4. Evidence | How do we prove it works and that Meta's models carry it? | F. Evaluation Plan (+ dataset card, system card, ablations) · G. Impact Model | Depth, Tooling, Impact |
| 5. Execution | How does one person ship it in 8 days without surprises? | H. Build Plan & Risk Register | all (whether it works) |
| 6. Presentation | How do we hand it over? | I. Submission Kit · J. Golden-Path Deck | Demo, Impact |

## 2. Cross-cutting rules (every artefact)
1. **Traceability:** every demo frame → a PRD story → a component in the tech spec → an eval metric → a claim in the ledger. IDs: `F-xx` (frame), `US-xx` (story), `C-xx` (component), `M-xx` (metric), `CL-xx` (claim), `R-xx` (risk), `A-xx` (assumption), `ADR-xxx`.
2. **Honesty tags on every number:** `[measured: run-id]`, `[sourced: link]`, `[assumed: A-xx]`, `[target]`. Nothing is built yet, so all performance figures in these packs are `[target]` acceptance thresholds, never presented as results.
3. **Meta load-bearing proof by ablation:** for each Meta capability, name the metric that should fall when it is removed and the expected direction. This is the primary evidence for the 25% tooling score and the answer to form Q8.
4. **Calibrated autonomy:** every consequential action has an autonomy level (L1 inform → L2 recommend → L3 act-reversible-with-notice → L4 human-approver), a threshold set from the PR curve, and a design that prevents rubber-stamping (the approver sees the evidence, not just a button).
5. **Rules compliance:** new work only (`HACKATHON_SCOPE.md`), public repo, synthetic or properly licensed data, fictional brands and people, no anti-project proximity (medical, hiring, education chatbot, politics/war, basic RAG, simple image analyzer), no employer data/code.
6. **Solo economy:** writing ≤ 10–15% of hours; prefer tables; artefacts become repo docs (`README`, `ARCHITECTURE`, `EVALUATION`, `IMPACT`, `PLAN`, `DEMO_SCRIPT`, `docs/adr/`).

## 3. Artefact templates

### A. Judging Objectives Map (≤1 page)
Table: rubric category (weight) → what a 9–10 looks like for *this* project → the specific evidence we will show → where it appears (video timestamp / README section / live product) → artefact that owns it. Plus: Stage-1 pass/fail check (theme fit, Meta usage), bonus-prize targeting (Best Agentic: autonomy level, effectiveness, usefulness; open-weight prize only if load-bearing), and form-question coverage (Q4 description, Q7 Meta usage, Q8 why Meta).

### B. Golden-Path Demo Spec (DEMO_SCRIPT) — written first
1. Logline (one sentence) and the buyer's question for the address bar.
2. Shot list 0:00–3:00 using browser-tab chapters (Address bar → Problem → Live → Under the hood → Proof → Impact): per shot `F-xx`, time, what is on screen, voiceover line (draft), the system state that must be real, labels shown (live / replay / mocked / sped-up).
3. The **wow moment** (one), the **failure caught on camera** (one, honest), the **receipts beat** (eval table + ablation + trace ID).
4. Live-run protocol: the unseen input a judge can try; replay/fixture mode for API outage, labelled.
5. **Claims-to-evidence ledger:** every spoken or on-screen claim `CL-xx` → evidence type → source/metric → status (`target` now).
6. Draft answers to submission form Q4, Q7, Q8 (≤150 words each).

### C. PR/FAQ & Pitch (≤2 pages)
Press release dated on a hypothetical launch (headline, sub-head, problem, solution, quote from a fictional customer persona clearly marked fictional, how it works, call to action). External FAQ (buyer questions: accuracy, safety, integration, cost). Internal FAQ (why now, why us, why Meta, what's hard, what we won't do). Shape Up pitch: appetite (8 days, solo), solution sketch, rabbit holes, **no-gos**. "Top 3 reasons this fails."

### D. Lean AI-PRD (≤3 pages)
Problem and user (persona, JTBD, current workflow with cost); goals/non-goals; user stories `US-xx` derived from demo frames with acceptance criteria that include eval thresholds; scope in/out (MVP vs roadmap); human-in-the-loop design; data requirements; non-functional requirements (latency, cost per case, reliability = N consecutive clean runs, security, privacy); KPIs with "permissible claim / avoid confusing with" columns (as in the Shockwave PRD); failure modes and guardrails.

### E. Tech Spec (ARCHITECTURE) + ADRs
Context, goals/non-goals; C4 context and container diagrams (Mermaid); agent graph table (agent, contract, Meta capability + model ID + reasoning effort, deterministic validator); sequence diagram of one case (Mermaid); key data contracts (Pydantic-style field lists); state machine with actor attribution; Meta capability map with API specifics (endpoint, mode, limits from the tooling reference); decision gate table with autonomy levels and thresholds; observability (trace spans per OTel GenAI, trace store, viewer, replay); cost and latency budget per case; threat model (STRIDE + OWASP LLM01–10 + agentic risks, each with mitigation and a test); failure modes and fallbacks; alternatives considered; 3–5 ADRs (MADR-lite: context, decision, consequences).

### F. Evaluation Plan (EVALUATION) — includes dataset card and system card
Ground-truth source and generation; label schema; dataset card (motivation, composition, collection, licences, splits, known biases); metrics `M-xx` with definitions and `[target]` thresholds; baseline (manual timed review on N cases; naive single-prompt baseline); **ablation matrix** (remove each Meta capability → expected metric drop); consistency (pass^k over k runs); LLM-judge validation protocol if a judge is used; error-analysis protocol (≥30 traces, failure taxonomy); adversarial/prompt-injection block; regression gate in CI; system card (intended use, out-of-scope use, limitations, human oversight).

### G. Impact Model (IMPACT + `impact/model.py` spec)
Per-unit formula; inputs register (each tagged measured/sourced/assumed); conservative/base/upside cases (headline the conservative); sensitivity (tornado of top 4 inputs); break-even; links to eval error rates (misses and false alarms cost money); who benefits beyond the buyer; scaling path (clients, industries) and what changes per client.

### H. Build Plan & Risk Register (PLAN)
D0–D8 calendar (Tue 27 Oct → Wed 4 Nov 2026, submit by 18:00 ET), with **walking skeleton end-to-end by D3**, freeze D7 noon; spikes as single-question time-boxes ending in an ADR; kill criteria as "state + date"; risk register (risk, likelihood, impact, mitigation, owner trigger); scope-cut ladder (what to drop first); definition of done (tests, eval run, README, deploy, replay, video).

### I. Submission Kit
README outline; `HACKATHON_SCOPE.md` text; full drafts for every form field (project description, use of Meta products, why Meta's models matter, feedback fields); X post copy; repo tree.

### J. Golden-Path Deck (≤12 slides)
Browser-tab narrative from the winning recipe. Slides: title (buyer's question, brand, tagline) · problem (three sourced cards) · forcing function · solution (what it does in one sentence + three columns) · the live case walkthrough (golden path, frame by frame) · architecture swimlane with Meta model per phase · why only Meta (ablation targets) · proof plan (metrics and thresholds, labelled targets) · impact model (conservative case, labelled) · scale path · roadmap/build plan · close. Performance numbers appear only as **targets**.

## 4. Quality bar for every pack (checked in the evaluation step)
- No untagged number; no target presented as a result.
- Every demo frame traceable to a story, component, metric and claim.
- At least three Meta capabilities with an ablation each; the Q8 answer survives "what if we swapped in another vendor?".
- Day-3 walking skeleton is credible for one person.
- Rules and anti-project checks explicitly passed.
- **The video storyboard (amended 2026-10-29 after doc 15):**
  - spends **≥ 80%** of time on the product working;
  - shows the product by 0:05;
  - has no slide segment over 10 s and ≤ 20 s of cards in total;
  - contains one live hero moment and a visible human approval click;
  - ends by 2:55;
  - opens with the pre-existing vs built-this-week line;
  - labels the Meta model on every step shown (the video is also scored for Tooling).
- **Product surface specified first (P0)** (doc 04 §4.2 v3):
  - a workbench where the trigger, the streaming trace, perception output drawn on the media, verifier refusals and the approval all happen;
  - a no-login "Run the golden case" button on the public URL;
  - no silent mock fallback.
- **Honest actuation stated:** what the model decides and what deterministic code executes. Each named Meta feature is mapped to an on-screen artefact.
- **The J deck feeds the page, not the video.** It is used on Devpost/README and in the final round; in the video it appears only as overlay chips and one ≤ 10 s architecture card.
