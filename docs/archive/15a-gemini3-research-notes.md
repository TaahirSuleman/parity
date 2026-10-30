# 15a — Appendix: raw research notes (Gemini 3 winners + Resilix audit)

Raw notes from the two scraping agents (winner pages, repos) and the Resilix audit. **Correction:** the agents reported most videos as 'not public'; in fact every winner page embeds a YouTube video (verified 29 Oct; IDs in doc 15 §11).

# Resilix — audit notes (raw, 29 Oct 2026)

## Submission facts
- Devpost: https://devpost.com/software/resilix — team of 3 (Taahir Suleman, Ollie Broadhurst, Ryan Howell); last updated Feb 09 2026 6:18 PM EST. Not a winner.
- Links: Cloud Run demo (resilix-agentic-backend-…run.app), GitHub, plus a drive.google.com link in "Try it out". YouTube embed UyMBlbcyU7w present on the page.
- Video: 254 s (4:14) — rules: "should not be longer than 3 minutes… only the first 3 minutes may be evaluated". 28 views.
- Write-up sections: Inspiration, What it does, How we built it, Gemini 3 Integration (~200 words), Challenges, Accomplishments (Impact KPIs table, n=2), Judging Criteria Fit (self-scored against each criterion), What we learned, What's next. No architecture diagram image in the gallery (5 screenshots: timeline, PR, logs/evidence, links/remediation, Jira ticket).

## Deck (4 slides, browser-tab motif)
1. "Resilix — The autonomous Site Reliability Engineer"; address bar "How do I fix and prevent cascading infrastructure errors".
2. Problem slide titled **"The Problem: Rampant Coupon Abuse in E-Commerce"** (leftover title from Neural Guardians deck) above cards about infra misconfiguration cascades / slow manual response / AWS downtime cost. This slide is the first frame of the video (0:00–~0:32).
3. Architecture: Orchestrator → Sentinel → Sherlock → Administrator → Mechanic; linear pipeline; labelled "thought_signature" hand-off.
4. Impact: "MTTR range 3.72–4.43 mins; avg 4; at least 93% vs 1 hour; 99% over 1+ days"; "Downtime reduction 93%+"; "~95%+ cost reduction"; AWS outage would be prevented.
- Video voiceover says "a couple hours to potentially a couple days … to 5 to 10 minutes" — inconsistent with 4.07 min mean in write-up and 3.72–4.43 on slide. Write-up cost model: (baseline − autonomous MTTR) × $16,700/min → "$433k–$934k per incident" (n=2 runs, constant unsourced in the write-up).

## Video structure (from captions + sampled frames)
| Time | On screen | Content |
|---|---|---|
| 0:00–0:32 | Problem slide (wrong "Coupon Abuse" title) | Problem narration, AWS us-east-1 |
| 0:32–1:15 | Architecture slide | Agent-by-agent description; thought signatures; thinking levels |
| 1:15–1:36 | Product dashboard | Scenario description; trigger Prometheus webhook |
| 1:36–1:50 | Dashboard | "I skipped ahead until it was done for the sake of time" (cut) — no live agent activity shown |
| 1:50–3:27 | Dashboard timeline/logs → Jira ticket → GitHub PR | Post-hoc tour of completed artefacts; incident list visibly contains several FAILED/INVESTIGATING incidents |
| 3:27–3:40 | Dashboard | "although Resilix approved and merged autonomously without human interaction, you can set gates…" (write-up says approval-gated merge) |
| 3:40–4:14 | Impact slide | KPIs — entirely after the 3:00 evaluation cut-off |
- Slides ≈ 75 s + 34 s = ~110 s (43%); product footage ≈ 145 s (57%), but none of it shows agents reasoning live; the "wow" (PR fixing DNS config) appears at ~3:00–3:20, i.e., at/after the cut-off.

## Code facts (github.com/TaahirSuleman/Resilix @ 2026-02-10)
- 97 commits, all 5–10 Feb 2026 (hackathon ran 17 Dec–9 Feb) → ~5-day build; heavy final-48h churn (fix demo simulation runtime errors 8 Feb 22:18; final commits ~1 h before deadline; techspec.md and RECORDING_CHECKLIST.md deleted in last commits while README still references techspec.md).
- ~10.8k Python LOC incl. 122 tests (unit/integration/e2e/contract/simulator) — strong for craft.
- Agents (ADK LlmAgent): Sentinel, Sherlock, Administrator, Mechanic — 26–54 lines each; ALL use `gemini-3-flash-preview` (no Pro). Administrator reuses Sentinel's thinking level.
- "Thought signature" = a custom Pydantic RCA schema named `ThoughtSignature` (root_cause, evidence_chain, confidence, target file...) passed via ADK `output_key`. It is NOT Gemini 3's API "thought signatures" (encrypted reasoning-state tokens returned with function calls). A DeepMind judge reading "we pass thought signatures between agents" would likely see a misused feature name.
- Orchestrator service (1,301 lines) has deterministic fallbacks: MockRunner, `_build_fallback_thought_signature`, "ADK execution failed on missing tool; recovered via deterministic integrations"; README: "Create deterministic remediation PRs for demo targets". Sentinel = deterministic scoring + LLM fallback for ambiguous cases. So model load-bearing-ness is unclear and partly bypassable.
- Text-only: Prometheus alert JSON + synthetic logs. No multimodal input.
- Frontend: React/Vite read-only dashboard (≈1.4k TS LOC) polling /incidents every 5 s; falls back to MOCK_INCIDENTS on error; only action = Approve Merge. Incidents are triggered from CLI simulator, not from the UI → a judge visiting the live link can't make anything happen.
- Live link: Cloud Run; robots-disallowed to fetchers; status today unknown.

# Gemini 3 Hackathon (gemini3.devpost.com) — Winners Batch A (7 projects)

Researched 2026-10-28 via WebFetch of Devpost project pages, GitHub repo pages and live demos. Direct curl/`gh api` to Devpost/GitHub was blocked by the sandbox proxy, so everything below comes from WebFetch (which summarises pages). Repos were not cloned and no code was run. **[UNVERIFIED]** marks anything I could not confirm.

**About the videos:** only Orphafold has a public video on its Devpost page or in its README. For the other six, Devpost shows a still-image gallery and no iframe or YouTube link. I also ran site-restricted YouTube searches and found nothing. My working assumption is that the video was submitted privately through the hackathon form, so judges saw it but the public page doesn't show it.

**About prize mapping:** the hackathon gallery labels 13 projects "Winner" (3 placed winners + 10 honourable mentions), and all 7 in this batch are among them. Badge text on each page: Globot "Winner Grand Prize", Aegis "Winner Second Place", Netra "Winner Third Place", and the other four "Winner Honorable Mentions".

---

## 1. Globot — GRAND PRIZE ($50k)
- **Devpost:** https://devpost.com/software/globot-341w9q | **GitHub:** https://github.com/Vector897/Globot | **Live demo:** none | **Video:** none public [UNVERIFIED]
- **Team:** 4. Victor Orion (lead, multi-agent infrastructure), Everett Deng (full-stack), Molling Ma (financial hedge agent), plus one "Private user" (orchestration/RAG).
- **Problem / user:** supply-chain and logistics managers hit by sudden geopolitical shocks. The opening scenario is the Red Sea crisis at "4:55 PM" on a Friday with "$50 million in cargo". Tagline: "turns sudden supply chain chaos into confident decisions in 60 seconds."
- **Impact claims (none sourced or measured):** "+$180K" fuel-cost impact from a reroute, satellite detection of congestion "6 hours before official announcements", and "first supply chain AI to use satellite imagery for early warning".
- **Gemini use:** Gemini 3 Flash does the reasoning. Gemini Vision reads satellite imagery and returns structured risk assessments, which is the headline innovation. Gemini Embeddings power RAG through ChromaDB. A "2M-token context" (their wording) is used to read 500-page insurance policies. The page doesn't mention thinking levels, grounding, Live API or function calling.
- **Modalities:** text, PDF and satellite images in; text, a 3D globe and route maps out.
- **Agentic architecture:** 5 agents on CrewAI: Market Sentinel (Reuters/Bloomberg signals), Risk Hedger, Logistics Orchestrator (reroutes), Compliance Manager (long-context policy reading) and **Adversarial Debate**, which red-teams each decision "to guard against hallucinations". The UI shows the chain of thought, and **human approval is required for all critical decisions**.
- **Frontend:** React, TypeScript and Vite, with a **Deck.gl 3D globe** that animates rerouted shipping lanes. The UI is central to the pitch. Its 19 screenshots cover port selection, 2D/3D routes, system logs, **token usage**, compliance analysis, file upload and an admin backend. Clerk handles auth.
- **Backend:** FastAPI, WebSocket, SQLite and ChromaDB, plus Python 3.13 monkey patches to keep aiohttp working with CrewAI.
- **Repo signals:** 106 commits, 29 stars, 17 forks, MIT licence. Includes GitHub Actions CI (syntax checks plus a frontend build), Dependabot, CONTRIBUTING, SECURITY, GOVERNANCE, AGENTS.md and a text architecture diagram in the README. There is **no test suite**. **Caution:** the current README has been rewritten into an "open-source decision-support workspace" that runs on mock or synthetic data, uses **Ollama by default** with OpenAI opt-in, and **doesn't mention Gemini**. The repo was clearly reworked after the hackathon, so the judged state can't be confirmed.
- **Write-up:** the full standard structure, punchy and second-person, opening with a story. No diagram on the Devpost page. It has 80+ likes and 18 comments, the most engagement in this batch.
- **Wow moment:** a 3D globe reroutes ships around a conflict zone while an adversarial agent argues against the plan, a satellite image flags congestion before the news does, and a human clicks approve.

## 2. Aegis: Autonomous Multi-Agent Crisis Command — SECOND PLACE ($20k)
- **Devpost:** https://devpost.com/software/aegis-autonomous-multi-agent-crisis-command | **GitHub:** https://github.com/iamdanishm/aegis | **Live:** https://aegis-psi-liart.vercel.app (loads, no login) | **Video:** none public [UNVERIFIED]
- **Team:** 1 listed creator, Danish Mansoori.
- **Problem / user:** emergency dispatch and incident commanders during mass-casualty events. The page says 911 fails on volume, not technology: "~10,000 signals in ten minutes" (unsourced) arriving as messy text, social posts and drone feeds, which pushes response past the "Golden Hour".
- **Gemini use:** Gemini 3 Pro with "Deep Thinking" handles triage, surveillance and logistics. Gemini 3 Flash handles the coordinator and reporter. **Google Search grounding** checks locations, weather and incidents before a pin goes on the map, which fixed their early hallucinated locations. The README mentions a Thinking Configuration and a `thought_signature` per agent for audit. The SDK is google-genai, and the project was built with **Antigravity**.
- **Modalities:** claimed audio, text, image and video (drone footage via ffmpeg-static) in; map, reasoning trace and a SITREP report out. The README says it is "Simulation-First", driven by a deterministic "Doomsday Dataset" (`simulation_data.json`) rather than live feeds.
- **Agentic architecture:** a hierarchy of 5 agents (Coordinator, Triage, Surveillance, Logistics, Reporter) run by a custom "central logic hub" with no framework. Agent streams run in parallel through Next.js Server Actions. **"Protocol Zero"** is the human-in-the-loop gate: the AI flags uncertainty and asks the commander for "Voice of God" approval before deploying heavy assets.
- **Frontend (central to the value):** a dark "tactical" Google Maps view with Advanced Markers and a live **"Reasoning Trace" with a typewriter effect**. The **"Spotlight Protocol"** processes every incident but shows detailed reasoning only for the top-priority threat, to avoid overloading the operator. The page frames UX as a safety issue. The live site shows panels for Incoming Signals/Live Feed, System Reasoning, an AI Reasoning Trace ("[SYSTEM STANDBY] Awaiting Signal...") and an "INITIALIZE / WIPE" control. Note that the README says React-Leaflet while Devpost says Google Maps.
- **Repo signals:** 49 commits, 6 stars, 9 forks. Next.js 16, Tailwind, shadcn and Zustand. `.agent/skills/`, `CONTEXT.md` and `GEMINI.md` are there to steer the AI coding agent. No tests and no diagram. Hosted on Vercel, not Cloud Run. **Security smell:** the API key is set as `NEXT_PUBLIC_GEMINI_API_KEY`, which exposes it to the browser, and a Google Maps key appears in the Devpost page metadata.
- **Write-up:** the full standard structure, specific, with named UX patterns and honest about the challenges it hit (hallucinated locations, black-box trust). Five screenshots and no architecture diagram.
- **Wow moment:** a flood of incidents comes in, the map lights up, the reasoning types itself out for the top threat, and the AI stops and asks the commander before sending a heavy asset.

## 3. Netra: Empowering the Visually Impaired — THIRD PLACE ($10k)
- **Devpost:** https://devpost.com/software/netra-empowering-the-visually-impaired | **GitHub:** https://github.com/ZentraHost/netra_project | **Live:** none (runs on localhost:5000) | **Video:** none public [UNVERIFIED]
- **Team:** 1 listed creator, Amita Mantri.
- **Problem / user:** blind and visually impaired people. The page cites "285 million visually impaired individuals worldwide" without a source and argues existing assistive tech is "socially blind".
- **Gemini use:** `gemini-3-flash-preview` per `app/config.py`, which also sets a 20 s model timeout. It relies on native multimodal video and audio, with the context window used for memory. The page says "Netra is ONLY possible with Gemini 3's speed". The **Live API is not used**: it runs a custom WebSocket pipeline from FastAPI to Gemini. It doesn't mention thinking, function calling or grounding.
- **Modalities:** realtime camera video plus voice (press and hold to ask) in; **spoken audio out** through a "Speech Management Service" that dedupes and prioritises speech. This is the most "live" project in the batch.
- **Features:** continuous hazard and **social-cue** awareness ("a person turning to smile"), crowd-flow guidance, scene Q&A (e.g. diet soda, medicine label), "Find My..." persistent object search with **hand-level "Micro-Navigation"**, "Help Me Do..." agentic task checklists checked visually step by step, and a **"Memory Palace"** of tagged landmarks stored in JSON that survives restarts. Also a "0.5-meter safety rule".
- **Agentic architecture:** a single model with an "Agentic Mode" and multi-layer prompts. No framework and no multi-agent setup.
- **Frontend:** HTML5, CSS and vanilla JS (WebComponents-style) with the Web Audio API. A camera-first, audio-first experience where the UI *is* the product.
- **Repo signals:** 25 commits, 7 stars, 10 forks. A clean `app/` layout (config, prompts, services/processor, memory, tracking, routes) on Python 3.13+. No tests, Docker or deployment.
- **Write-up:** **non-standard and hyperbolic**. It is titled "NETRA: The Definitive Submission for the Gemini 3 Grand Prize" and calls itself "the most ambitious" and "the most technically demanding" entry, with **no latency, accuracy or user-test numbers**. On the plus side, it includes an **architecture diagram image** (the only Devpost-hosted diagram in the top 3) and 7 captioned screenshots.
- **Wow moment:** the user points the phone at a room, hears "someone to your left is smiling at you", and gets guided to an object by hand.

## 4. Proofy.AI — HONOURABLE MENTION ($2k)
- **Devpost:** https://devpost.com/software/fakey-ai | **GitHub:** https://github.com/aadhi97x/proofy-app2 (Android), https://github.com/jiviteshreddy44-netizen/proofyyy/ (web; fetch failed, likely private or removed [UNVERIFIED]), https://github.com/aadhi97x/proofy-extension | **Live:** https://proofyyy.vercel.app/ (titled "PROOFY.AI | Truth Verification Suite"; the body is client-rendered so I couldn't confirm it works or whether it needs login [UNVERIFIED]) | **AI Studio app:** https://aistudio.google.com/app/apps/drive/1taoKnW49mcYcuUeISTdvceV3az5L0BSX?showPreview=true&showAssistant=true&fullscreenApplet=true (needs a Google login) | **Video:** none public [UNVERIFIED]
- **Team:** 3. Jivitesh Reddy, Adhidev Jayaraj, Nathan James (pitch). Also submitted to "AI For Good" on Devpost.
- **Problem / user:** ordinary people targeted by deepfake scams. The personal hook: the creator's mother nearly invested after seeing a deepfake of India's Finance Minister. They say existing detectors are built for researchers.
- **Impact claims:** "First place at a national-level hackathon held at IIT Delhi" with a "₹50,000" prize (unrelated to this event). No accuracy or benchmark figures.
- **Gemini use:** described as "Gemini-powered" via @google/genai, AI Studio and Antigravity, with "structured" responses and a "safeinvoke" wrapper per the tags. **No specific Gemini 3 feature is named.** The Android README calls raw `generateContent` with a fallback across **gemini-2.5-flash, 2.0-flash and 2.5-pro** on 429/503 errors. Gemini 3 use isn't evident in that repo.
- **Modalities:** image, video (frame by frame with anomaly timestamps), audio (voice-clone cues) and text in; verdicts with confidence and evidence plus an export out.
- **Agentic architecture:** none. Direct multimodal classification calls.
- **Frontend (three surfaces, all central):** an Android app (Kotlin/Compose) whose **hardware gesture, Volume Up + Volume Down, captures the screen** in an overlay for instant analysis; a browser extension for in-page checks; and a React/Vite/Three.js/Framer Motion web suite with multi-file upload, a source finder and frame-level timestamps. The Android README includes a Mermaid sequence diagram.
- **Repo signals:** the Android repo has 8 commits and 3 stars, with stray extension files at the root and `build_output.txt` committed. Thin.
- **Write-up:** the full standard structure with a strong emotional hook. Light on "How we built it" ("share the same detection logic"). 12 screenshots and no diagram.
- **Wow moment:** press both volume buttons while watching a suspicious video and get a verdict over whatever is on screen.

## 5. Agent-weaver — HONOURABLE MENTION ($2k)
- **Devpost:** https://devpost.com/software/agent-weaver | **GitHub:** https://github.com/Pranav301102/Gemini-hack | **Live:** https://gemini-hack-ruddy.vercel.app/ (a landing page plus a dashboard with a `?demo=true` mode and no login. Real data needs the MCP server running locally. Its GitHub link points to a "yourusername" placeholder.) | **Video:** none public [UNVERIFIED]
- **Team:** 1 listed creator, Pranav Trivedi.
- **Problem / user:** developer teams using AI coding agents, where every prompt "starts from zero", agents misread messy codebases, and teammates repeat the same analysis.
- **Impact claims:** "20–30% improvement" in one-shot capability and "significantly less input token usage". These are **unmeasured**, and "What's next" lists "a benchmark suite to measure efficiency gains", which tacitly admits it.
- **Gemini use:** a Gemini CLI extension with "google-gemini-3.0-flash" in Built With; the README says "Gemini 3 Pro API" via `@google/generative-ai`. Gemini writes natural-language descriptions of Tree-sitter AST symbols. The page claims function calling for all 55 tools and "2M-token context windows". They explicitly **did not use AI Studio**.
- **Modalities:** code and text in; text and dashboard out.
- **Agentic architecture:** **5 role agents** (Architect, PM, Developer, QA, Code Reviewer) behind one **MCP server with 55 tools across 19 modules**. Shared memory is a `.weaver/` JSON "context board" committed to git, and an Express "Hub" syncs it by branch. **Human-verified annotations** on code symbols are the trust layer. Works with Claude via MCP too.
- **Frontend:** a Next.js 15 / React 19 / Tailwind 4 dashboard showing live agent activity over SSE (chokidar file watch) with Mermaid diagrams. This is observability rather than the core value, since the product lives in the CLI.
- **Repo signals:** 15 commits, 3 stars, MIT licence, an ASCII architecture diagram and clear install steps (`gemini extensions install`). No tests.
- **Write-up:** standard structure, specific stack. Honest about scope ("just a few days").
- **Wow moment:** one teammate's agent scan, committed to git, makes the next person's agent instantly smarter, and you can watch five agents work in a live dashboard.

## 6. Orphafold — HONOURABLE MENTION ($2k)
- **Devpost:** https://devpost.com/software/orphafold | **GitHub:** https://github.com/Paulhb7/orphafold | **Live:** https://orphafold-deep-structural-search-for-rare-disease-61857687256.us-west1.run.app (**Cloud Run**, deployed from AI Studio. The page title is "Orphafold | Deep Genomic Discovery". It is client-rendered, so I couldn't confirm it works or whether it needs a login or key [UNVERIFIED].) | **Video:** **https://youtu.be/W7CqQGy8dt0** (embedded on Devpost as youtube.com/embed/W7CqQGy8dt0)
- **Team:** 1 listed creator, Paul Barbaste. He previously built Prometheus BCI (people with motor disabilities carried the Paris 2024 Olympic flame using brain signals) and co-founded Inclusive Brains, which gives him strong credibility.
- **Problem / user:** rare-disease researchers and geneticists. The page cites "~300 million" patients and says "95% of these 7,000+ conditions have no approved treatment". These are well-known figures but uncited on the page. The data is fragmented across Orphanet, UniProt, AlphaFold and PubMed.
- **Gemini use:** Gemini 3 is the orchestrator and reasoning engine. **Search Grounding** checks prevalence and inheritance, a thinking budget (Thinking Config) drives the repurposing agent, and long context feeds the Hypothesis Lab. Built with the google-genai SDK and AI Studio. **Inconsistency:** the README text says "Gemini 1.5 Pro" while its badge says Gemini 3.
- **Modalities:** text queries in; a structured report, an **interactive 3D AlphaFold protein viewer** and a RIS bibliography export out.
- **Agentic architecture:** a **"Pre-Flight" grounding layer** fetches real data from REST APIs (Orphanet/OMIM, UniProt/NCBI Gene, ClinVar, PubMed, ClinicalTrials.gov, AlphaFold DB) *before* prompting, so every hypothesis cites a real UniProt ID or PubMed citation. A Gemini 3 orchestrator then runs 4 agents: Clinical Grounding, Bio-Mechanism, Discovery and Hypothesis Lab/Repurposing (structural homology and binding-pocket comparison, weighted by pLDDT). The pipeline is custom; ADK is on the roadmap. The README labels it a "Research Prototype / PoC", not a clinical tool, and the page has an "Ethics" section.
- **Frontend:** React, Vite and TypeScript with a "Structural Proteomics Lab" 3D viewer, so the visuals are central. Tags say react-native, which is a mismatch.
- **Repo signals:** 16 commits, 2 stars, a Makefile, `.env.example` and `documentation/architecture.md` with a **Mermaid flowchart**. No tests and no licence.
- **Write-up:** the full standard structure, specific and honest about latency and hallucination risk. 13 screenshots.
- **Wow moment:** the Hypothesis Lab spots that two unrelated rare diseases share a structural defect, suggesting a drug could be repurposed, and shows it on a rotating AlphaFold structure.

## 7. Orbital Assets — HONOURABLE MENTION ($2k)
- **Devpost:** https://devpost.com/software/orbital-assets | **GitHub:** https://github.com/OrbitalAssets/OrbitalAssets (every fetch failed, likely private or removed [UNVERIFIED]) | **Live:** https://orbitalassets.net (**loads, no login**. It has a NASA Eyes URL box, SBDB autocomplete search, a static Apophis sample report showing "NPV $314,432", and Logic Engine and Methodology sections.) | **Video:** none public [UNVERIFIED]
- **Team:** 2. Mauricio Castro and Tiancheng Chen.
- **Problem / user:** space-mining investors and analysts (AstroForge and TransAstra are cited). The pitch is that hyped "quadrillion-dollar" asteroid valuations ignore physics and markets. Tagline: "The first Investment Bank for the solar system."
- **Gemini use:** `gemini-3-pro-preview` acts as a "Senior Analyst", and **its reasoning is streamed live** (one screenshot caption reads "Gemini 3 Flash Thinking", which is inconsistent with the Pro model named in the text). Built with AI Studio. **Key design choice:** the numbers come from a deterministic TypeScript valuation library, and the model "writes the narrative while the valuation is locked in TypeScript constants". The page claims "zero hallucinations", which is unverified.
- **Deterministic engine:** NPV at space-specific discount rates of 20–35%, the Shoemaker-Helin delta-v approximation, a Market Damping Factor (returning 100% of annual global production would crash the price to about 1% of spot), diameter inferred from absolute magnitude and albedo when SBDB data is missing, and water valued at US$1,500–2,500/kg as the cost of launching it from Earth.
- **Modalities:** URL or text in; streamed reasoning, a 3D NASA shape model (React Three Fiber/Three.js, Eros/Bennu) and an emailed Investment Memorandum (Resend) out.
- **Agentic architecture:** single model and not agentic. A hybrid where deterministic tools come first and the LLM narrates.
- **Frontend / infra:** Next.js App Router on Edge Runtime/Cloudflare, Tailwind, and Firebase Firestore for lead capture and logs. It has a polished marketing site with a custom domain.
- **Write-up:** the full standard structure with dense, specific domain content. Includes a "System Architecture" image (NASA data, then Cloudflare Edge, then the Gemini 3 Reasoning Core, then the UI) and 10 screenshots.
- **Wow moment:** paste a NASA Eyes link for Psyche and watch Gemini reason live into a bank-style investment memo with an NPV grounded in orbital mechanics.

---

## Cross-project patterns (what these 7 share)
1. **A vivid, specific scenario beats an abstract problem.** Examples: "4:55 PM Friday, $50M cargo", "10,000 signals in ten minutes", a mother nearly scammed by a deepfake minister, a person smiling at a blind user. Even the placed winners use mostly **unsourced or unmeasured** numbers. None reported a real evaluation or benchmark, so judges evidently rewarded concept and demo over measured accuracy.
2. **The top 2 are named multi-agent swarms of 5 agents** with role names, an explicit verification step (Adversarial Debate; Search grounding to stop hallucinated pins) and a **visible human-approval gate** (Globot's human approval; Aegis's "Protocol Zero"). Orphafold has 4 agents and Agent-weaver 5. The two single-model winners make up for it with a strong live modality (Netra) or **deterministic math guardrails** (Orbital Assets).
3. **Visible reasoning is a UI feature.** Streamed or typewriter "reasoning traces" (Aegis, Orbital Assets, Globot's chain of thought) and UX that filters what the operator sees (Aegis's "Spotlight").
4. **The UI is central and visual.** The common set is a 3D globe, a tactical map, a camera with voice, 3D protein structures, a 3D asteroid and a phone hardware-button trigger. None of these winners is just an afterthought dashboard; Agent-weaver comes closest, and it is only an honourable mention.
5. **Grounding against real data sources is the anti-hallucination story.** Examples: Google Search grounding (Aegis, Orphafold), the pre-flight API fetch (Orphafold), the deterministic engine (Orbital Assets) and RAG (Globot).
6. **The engineering is thin and no one has tests.** Repos range from 8 to 106 commits, no project shows automated tests, few use Cloud Run (only Orphafold, via AI Studio), and several have hygiene issues (exposed `NEXT_PUBLIC_` key, model name inconsistencies, repos missing or rewritten after the event). The "Technical Execution 40%" criterion was evidently judged mostly from the demo video, not the code.
7. **Most are solo or small teams.** Four have one listed creator, one has two, one three and one four (the Grand Prize winner).
8. **Gemini 3 features named most often:** multimodal vision, long context, thinking/"deep thinking" and Search grounding. **None** used the Live API, Veo, Nano Banana image generation or computer use. Antigravity and AI Studio show up as build tools.
9. **Demo videos weren't public** for 6 of the 7, so the video was evidently a private submission field and the public Devpost page carried the write-up and screenshots.

# Gemini 3 Hackathon (gemini3.devpost.com): Winners Batch B + Non-winning Comparators

Researched 2026-10-28 using WebFetch on Devpost pages, GitHub READMEs, YouTube oEmbed and the official Devpost update. Fetched content was treated as data. Claims are the entrants' own unless marked otherwise. **[UNVERIFIED]** means I could not confirm it.

**Key placement finding:** all six projects in this batch are **Honorable Mentions** ($2k each). Each Devpost page shows "Winner: Honorable Mentions", and the official winners update confirms it (see the placements table at the end).

**Access limits:** direct curl to Devpost was blocked by the proxy (403). AI Studio app links and GitHub `tree/` sub-pages are robots-disallowed, and agentguard.baseid.ai failed to fetch. Video durations could not be read (YouTube rate-limited). Titles come from oEmbed.

---

## 1. Logic Lift: COBOL "Logic Archaeology" to Python
- **Prize:** Honorable Mention. Source: Devpost label plus the official update. The Devpost slug `the-bunny-ear-adventure` shows the project was renamed from an earlier idea.
- **Problem / user:** banks and enterprises running COBOL mainframes face a shrinking pool of experts and a "black box" risk. The user is a modernization or enterprise engineering team.
- **Impact claims:** "95% of ATM swipes" and "43% of banking systems" on COBOL are cited industry statistics, not project results. "100% parity" and "100% completion" are design goals, not measurements. There are no benchmarks.
- **Gemini 3 use:** Gemini 3 Pro, with the long context window for whole-repository reasoning. Search grounding is used for documentation. Built in the **AI Studio app builder**, then refined in **Antigravity**, so the project leans on Google's own tooling. Code-execution-style verification runs Python in the browser with **Pyodide**, not Gemini's code execution tool.
- **Modalities:** text and code in; Python code, pytest suites, reports and an architecture "blueprint" out.
- **Agentic architecture:** an essentially single agent with a self-correction loop: generate Python, generate a pytest parity suite, run it in Pyodide, read the traceback, revise. Each module gets a "Certainty Score". A state machine with skip/next fixed the "83% stall". No framework is named. Human-in-the-loop is not described.
- **Frontend:** React, TypeScript and Tailwind, with a "System Stream" terminal, an "Archaeology Report" view, an impact dashboard ("Architecture Enrichment", "Security Posture") and an Ouroboros brand in light and dark modes. The UI is central and polished. The backend is thin: client-side Gemini calls in the AI Studio app style.
- **Deployment:** an AI Studio app link, which probably needs a Google login **[UNVERIFIED: robots-blocked]**. A Cloud Run URL exists, but the creator's own May 2026 update says it "returns an API error". **No GitHub repo is listed.**
- **Write-up:** clear section structure, honest about challenges (the 83% stall, AI Studio's one-way GitHub sync) and about its roadmap (PL/I, RPG, Fortran). No architecture diagram was found on the page.
- **Wow moment:** AI-generated code tests itself in the browser, the agent fixes it from the traceback, and each module ends with a parity "Certainty Score".
- **Team:** solo (Alissa Troiano).
- **Video:** https://www.youtube.com/watch?v=YUrrsM74gu4, titled "Logic Lift - Enterprise Mainframe to Modern Logic Recovery" (channel "Alissa Explains It All").

## 2. AgentGuard: The Semantic Firewall for the Agentic Web
- **Prize:** Honorable Mention (Devpost plus the official update).
- **Problem / user:** merchants block every AI shopping agent because a WAF cannot tell a legitimate agent (AP2/ACP protocol) from a scraper that spoofs tokens. The users are e-commerce merchants and their security teams.
- **Impact claims:** "sub-300ms" reasoning, "99% of traffic handled by cache at zero AI cost", and README targets of 98%+ cache hit rate and 10k+ req/s. All are stated targets or claims, not measurements. Demo request thresholds include a retry rate above 50/min.
- **Gemini 3 use:** `gemini-3-flash-preview`, chosen for latency. Forced JSON output with few-shot prompts and system-prompt rules (valid token plus bad behaviour means BLOCK). Gemini returns a natural-language "Reasoning Trace". An AI Studio version also exists. **Discrepancy:** ARCHITECTURE.md names "Gemini 2.0 Flash Exp, temp 0.1", so that doc is probably stale **[UNVERIFIED which model is in prod]**. No multimodal input, grounding or thinking-level use.
- **Modalities:** structured telemetry in (velocity, headers, traversal pattern); a verdict (ALLOWED, RESTRICTED or BLOCKED) plus reasoning, risk factors and a cache decision out.
- **Architecture:** a single LLM judge inside a real systems design. Layers run in this order: (1) Redis manual whitelist/blacklist override, (2) edge-gateway in-memory cache with per-verdict TTLs (5 minutes for ALLOWED, 60 minutes for BLOCKED), (3) PostgreSQL reputation, (4) Gemini. A human override sits at the top layer. A Python traffic simulator plays the edge gateway, so the demo needs no live DNS.
- **Frontend:** a React, Vite and Recharts "Command Center" with Monitor, Auditor, Integration and About tabs, showing live allow/block graphs and an auditable reasoning trail. The UI matters to the story because it shows explainability, but the value lives in the backend.
- **Deployment:** the live dashboard at https://agentguard.baseid.ai is described as **no login**. The Auditor tab takes a judge key (`BASEID-2026`) and allows 15 requests per session. My fetch of the site failed. The AI Studio app uses the same database.
- **Repo:** https://github.com/mayurpawar/agentguard-monorepo has 24 commits. It contains `apps/{dashboard,brain-api,edge-gateway}`, `infrastructure/docker-compose.yml`, a Postgres `init.sql`, `tests/traffic_simulator.py` (a load simulator, not unit tests), and ARCHITECTURE.md and SETUP.md with ASCII diagrams. The `devpost` branch holds the simplified AI Studio code and `main` holds production. No CI was confirmed.
- **Write-up:** strong. It is business-framed (ties to AP2/UCP), has a credible go-to-market (Shopify app, then SDK or sidecar, then Cloudflare Workers), and states its trade-offs honestly (latency against security, hallucination).
- **Wow moment:** a bot with a *valid* AP2 token gets blocked anyway because its behaviour looks like scraping, and the block comes with a plain-English explanation.
- **Team:** solo (Mayur Pawar).
- **Video:** https://www.youtube.com/watch?v=J8HYX4PNWLs, titled "AgentGuard: The Semantic Firewall for the Agentic Web (Built with Gemini 3.0)".

## 3. PROCSee: autonomous process forensics ("your system as a crime scene")
- **Prize:** Honorable Mention (Devpost plus the official update).
- **Problem / user:** endpoint security tools are reactive: they poll, alert and wait. PROCSee aims to investigate every process itself. The users are SOC analysts and security-minded power users on Windows.
- **Impact claims (all self-reported):** under 10 ms WMI capture latency, "100% detection" of processes including sub-second ones, more than 40 MITRE ATT&CK patterns, triage time cut from 8–12 s to 2–4 s using low thinking, and about 95% fewer API calls thanks to behaviour pre-scoring (from the dev.to post). The setup was stress-tested with 5 concurrent investigations.
- **Gemini 3 use:** `gemini-3-pro-preview` through google-genai 1.51+. **Dynamic thinking levels** are central: low for triage, high for forensics and reports. Multi-turn **self-directed tool-like querying** lets Gemini request more data through 5 query types (process, time range, pattern, network, files), capped at 4 rounds. The 1M-token context holds the investigation history. Gemini returns confidence and uncertainty fields to counter overconfidence. Reports are produced only when risk is at least 0.5 and confidence at least 0.6.
- **Modalities:** OS telemetry in (WMI events, psutil, network activity, registry and scheduled tasks); a verdict JSON (for example CONFIRMED_THREAT, risk 0.95, confidence 0.92), a first-person Markdown report and an evidence timeline with integrity hashes out.
- **Architecture:** a single investigator agent with an orchestrator and a phase state machine (analysis, query, re-analysis, verdict). Phase snapshots let it **resume after a crash**. It uses a raw-events database and a 1-minute-summary database (SQLite in WAL mode), with at most 3 concurrent deep investigations. No framework is used. Prevention actions were cut, and the `beta_prevention` block in config is disabled. The roadmap adds human confirmation before critical actions.
- **Frontend:** React 18, Vite and Tailwind, with WebSocket live updates, a viewer for Gemini's conversation, a report viewer and the evidence timeline. The UI makes the AI's reasoning visible. The backend is the deepest in this batch: real OS integration, plus concurrency and retention engineering.
- **Deployment:** none. It runs locally only and needs Windows for WMI. There is no live demo.
- **Repo:** https://github.com/abbasmir12/procsee (MIT licence, 17 commits). It contains `agent/ api/ dashboard/ database/ demo/` (a PowerShell attack simulation and an autonomous-query test script), `config.yaml`, and **4 Mermaid diagrams** in the README (system, data flow, classes, sequence). It has no test suite, CI or Docker.
- **Write-up:** very long and engineering-specific. It documents 7 challenges with concrete fixes (WAL mode, busy timeout, polling replaced by WMI callbacks, summaries before raw data). Its "100% detection" claim is the weakest point.
- **Wow moment:** the agent decides on its own to pull network data for PID 4821, finds C2 traffic to 203.0.113.42, and writes a first-person forensic report.
- **Team:** solo (Mir Abbas).
- **Video:** **no video embed or link found** on Devpost, the README or the dev.to article (dev.to/mirshah12/procsee-...). Its absence did not stop it winning an HM **[UNVERIFIED: an embed may have failed to render in fetches]**.

## 4. BatteryForgeAI: multi-agent battery intelligence
- **Prize:** Honorable Mention (Devpost plus the official update).
- **Problem / user:** battery failures such as the Note 7 and thermal-runaway incidents are costly and dangerous, and quality control relies on manual or destructive testing. The users are battery manufacturers, BMS/PCB engineers and EV fleet operators.
- **Impact claims:** none in dollars. Build stats: about 15k LOC, 72-hour sprint, 5 specialist agents plus a root agent, more than 20 tools, 6 analysis modes, 100+ *simulated* packs, and 1 FPS video analysis. The team explicitly calls thermal detection "a prototype, not a validated safety system", which is a point for honesty.
- **Gemini 3 use:** `gemini-3-flash-preview` for orchestration and vision. The team switched because `gemini-3-pro-preview` returned 404 in v1beta. **Multimodal vision** works on webcam, screen-share and video frames for thermal runaway, and on zero-shot PCB defect images (opens, shorts, solder mask). Function calling via ADK tools. Gemini embeddings for RAG. Gemini also maps CSV headers to an adaptive parser.
- **Modalities:** images, video and live webcam or screen-share, CSV, EIS data, Gerber files and documents in; charts, simulations, safety actions and compliance certificates out.
- **Architecture:** **Google ADK multi-agent** with a root "Commander" that routes to Defect Analysis, Charging Optimization, Fleet Commander, Safety Guardian (with human-in-the-loop controls) and Predictive Maintenance. Physics grounding comes from PyBaMM's Doyle-Fuller-Newman model, run in a thread pool. RAG uses ChromaDB. WebSocket streams live agent traces.
- **Frontend:** React 18, Vite, Recharts, Leaflet, Framer Motion and React Player, with 10+ components. It is a feature-dense multi-mode workbench where the UI is the product surface, though it is broad rather than deep.
- **Deployment:** none live. The README gives docker-compose instructions (frontend on port 80 via Nginx, backend on 8000 with Swagger) plus Cloud Run, ECS and Azure recipes.
- **Repo:** https://github.com/suryaremanan/BatteryForgeAI (MIT licence, 11 commits). It contains `backend/`, `frontend/`, `scripts/`, DOCKER.md and docker-compose. Hygiene problems: a committed `.venv/` and a root `.env` (a possible secret leak) **[UNVERIFIED contents]**. The README says 5 agents, but its table lists 6. No tests or CI were visible. An architecture diagram is linked (postimg).
- **Write-up:** long and specific. The challenges section is practical (ADK `List[str]` schema 400s, async event generators, YouTube CORS solved by screen-share) and the roadmap is phased.
- **Wow moment:** pointing a webcam or screen-share at a thermal-runaway video while the Safety Guardian agent flags it live, with Gemini reasoning combined with real electrochemistry simulation.
- **Team:** 2 (Kumari Surya Remanan, Shankar Rajan).
- **Video:** https://youtu.be/NVNg9XcHVvA, titled "explanatory BatteryForgeAI" (channel "DIYResearcher"). The page calls it an "extended video". No separate gallery embed was found.

## 5. Gemini GeoFlow: from research papers to satellite-checked archaeological sites
- **Prize:** Honorable Mention. Source: the official update. The README also says "Gemini 3 Hackathon honorable mention".
- **Problem / user:** archaeological site detection is slow, and field survey does not scale in areas like the Amazon. The users are archaeologists and remote-sensing researchers, especially under-resourced ones. The team built it with input from an archaeologist.
- **Impact claims:** none quantified, with no accuracy figures or dataset size. It was started on Feb 2, 2026, about a week before the deadline.
- **Gemini 3 use:** `gemini-3-flash-preview` in all three calls (verified in `services/llm_service.py`): (1) structured site extraction from paper *text* (the code passes `paper_text`, so the PDF is parsed before Gemini sees it rather than sent natively **[likely]**); (2) **vision** analysis of a 6-panel satellite composite (Sentinel-2 RGB, NDVI, NDWI, BSI, SRTM DEM, slope) for earthworks and vegetation anomalies; (3) **Google Search grounding** for comparable sites and conservation status, with citations. It does **not** use `response_schema` (it strips code fences and calls `json.loads`) or `thinking_config`.
- **Modalities:** PDF or manual coordinates (decimal degrees, DMS or UTM) in; JSON, a satellite composite, an AI interpretation, cited context, a Google Maps view and downloadable GEE data out.
- **Architecture:** a deterministic **pipeline** of 3 LLM steps with Earth Engine in between. It is not multi-agent. It has validation and confidence scoring. No human-in-the-loop beyond the user reviewing results. Crowdsourced validation is on the roadmap.
- **Frontend:** a Flask template with vanilla JS modules (`mapHelpers.js` and similar) and Google Maps. It is simple and functional, and the map and imagery are the core output.
- **Deployment:** live at https://geoflow.boslis.com/ with no login wall visible (PDF upload and manual-coordinate modes). The repo includes a Dockerfile and docker-compose.
- **Repo:** https://github.com/BostonListener/GeminiGeoFlow (MIT licence, **3 commits**). Tidy `routes/services/prompts/utils` layout, a README pipeline diagram and a sample paper PDF. No tests or CI.
- **Write-up:** shorter and modest. It is honest about pivots (Copernicus and FABDEM abandoned for GEE) and specific about coordinate-format parsing.
- **Wow moment:** a real paper (Amazon geoglyphs) goes in, and a site pinned on a map comes out with multi-band satellite evidence and Gemini's read of earthworks.
- **Team:** 2 (Linduo Li, Zifeng Wang).
- **Video:** https://www.youtube.com/watch?v=V_IF-Vv3PbM, titled "Gemini GeoFlow Demo" (channel "Nomad's Manuscript").

## 6. CineStream: A2A Mesh & Cinematic Learning
- **Prize:** Honorable Mention (Devpost plus the official update).
- **Problem / user:** two problems at once: (a) executives losing time on dense static reports, and (b) Venezuela's education crisis, which the author, a Venezuelan developer, frames personally. The users are executives and students.
- **Impact claims:** an anecdote that the A2A mesh "resolved a simulated supply-chain crisis in seconds" when a human team would take hours. No metrics.
- **Gemini 3 use:** three tiers. Gemini 3 Flash for inter-agent sync, Gemini 3 Pro as the "Decision Brain" with **`thinkingConfig`** for recursive trade-off analysis, and **Gemini 2.5 Flash** for audio and visual generation (the "Multimodal Cortex", probably TTS **[UNVERIFIED]**). Built entirely in the **AI Studio app builder**, and the author says Gemini wrote most of the code. Veo was skipped to stay on the free tier.
- **Modalities:** text and concepts in; agent debate, briefings, scripts, storyboards and audio out.
- **Architecture:** a client-side, prompt-orchestrated "A2A mesh" of role agents (Logistics, Finance, Ops) that negotiate trade-offs. The "a2a" tag suggests the A2A protocol, but nothing shows a real A2A protocol implementation **[UNVERIFIED]**. Modules: Mission Orchestrator, Audience DNA, Script Planner, Sound Studio and Master Briefing Mode. No verification or safety layer is described.
- **Frontend:** the frontend *is* the product: 17 gallery screenshots of a cinematic, multi-module workstation. There is essentially no backend beyond Gemini calls.
- **Deployment:** an AI Studio app link only (likely needs a Google login **[UNVERIFIED]**). **No GitHub repo.**
- **Write-up:** short and buzzword-heavy ("Knowledge Friction", "Pillar Alpha/Beta", "Agentic Noise"). It has no "What's next" section. Its strengths are the human story and visual polish.
- **Wow moment:** abstract theory turned into a cinematic, audience-tailored lesson with audio. The emotional hook is reaching Venezuelan students who lack teachers.
- **Team:** solo (Xavier Nuñez).
- **Video:** **none found** on Devpost (no embed and no link) or by web search.

---

## Non-winning comparators

**Aegis / "AEGIS Commander" (aegis-8rk6bx).** *Do not confuse it with the 2nd-place "Aegis: Autonomous Multi-Agent Crisis Command" (submission 932020).* It is a 3-agent self-auditing system: a Worker, a Code Reviewer, and an Audit agent that gives pass/fail with confidence. Work runs through 5 phases, and a rejected phase triggers a retry with a side-by-side diff. It uses `gemini-3-pro-preview`, structured JSON, a thinking budget per level, a Hedera Hashgraph audit ledger, and a Figma-style zoomable board. The stack is React, TypeScript and Vite. The demo is at aegis-bay.vercel.app, with no GitHub or video listed. The team has 3 members. Its weakness is a generic meta-problem ("who watches the watchers") with a toy deliverable (writing a research paper). The self-reported "100% audit pass rate" undercuts the premise of an auditor, and no domain user or cost is named.

**VaultSim.** Privacy-preserving legal reasoning. A "private fine-tuned LLM" masks PII client-side into AES-256 tokens. Gemini 3 Pro then runs a support, opposition and judge debate on the masked data, and the session holds no data after logout. The stack is Next.js, FastAPI, Redis and Docker on Railway. The demo is at vault-8zsk.vercel.app, with two GitHub repos and a video at https://www.youtube.com/watch?v=CWjPGa1ubPE. The team has 2 members. It had **139 likes**, far more than any winner in this batch (1–10 likes), so popularity did not predict winning. Its weaknesses: the masking model is vague (a "fine-tuned LLM" whose identity is unclear), Gemini's role is a generic 3-agent debate, and the demo domain (legal cases) is a stand-in for claimed generality.

**SanskaraAI-agent.** An Indian wedding "project manager" built on Google ADK: a Planner agent plus a Search Specialist sub-agent, with Google Places grounding and Firestore state injected into the prompt each turn. It can create payment links and schedule. The demo is at agent.sanskaraai.com, with a Telegram bot. No GitHub or video is listed. The team has 3 members. The **core model is Gemini 2.5 Flash Lite, not Gemini 3**, which fails the "leverages Gemini 3" part of the 40% Technical Execution criterion. The problem is also consumer convenience with low stakes, and the cost fallback is a rough heuristic (Venue + Guests × 5000).

---

## Placements table (all 13 winners)

| Place | Project | Submission link | In this batch? |
|---|---|---|---|
| Grand Prize ($50k) | Globot | gemini3.devpost.com/submissions/899751-globot | no |
| Second ($20k) | Aegis: Autonomous Multi-Agent Crisis Command | .../932020-aegis-autonomous-multi-agent-crisis-command | no |
| Third ($10k) | Netra: Empowering the Visually Impaired | .../931982-netra-empowering-the-visually-impaired | no |
| HM ($2k) | AgentGuard | .../887687-agentguard-... | yes |
| HM | BatteryForgeAI | .../903053-batteryforgeai | yes |
| HM | Logic Lift | .../893597-logic-lift | yes |
| HM | PROCSee | .../927627-procsee | yes |
| HM | Proofy.AI | .../929811-proofy-ai | no |
| HM | Agent-weaver | .../916969-agent-weaver | no |
| HM | Orbital Assets | .../904816-orbital-assets | no |
| HM | CineStream: A2A Mesh & Cinematic Learning | (devpost.com/software/cinestream-...) | yes |
| HM | Orphafold | (not fetched) | no |
| HM | Gemini GeoFlow | (devpost.com/software/gemini-geoflow) | yes |

**Sources:**
- The official Devpost update "The moment you've been waiting (so patiently!) for..." at https://gemini3.devpost.com/updates/40729-the-moment-you-ve-been-waiting-so-patiently-for lists all 3 placings and all 10 HMs. It is dated about April 2026: earlier updates set the expected results window as April 13–17, after delays from April 1 and April 8. Entries: 4,500+ submissions, and the gallery shows 4,499.
- Each project's Devpost page shows the "Winner: Honorable Mentions" label.
- The gallery at https://gemini3.devpost.com/project-gallery shows 13 "Winner" badges.
- No Google, DeepMind or X winners post turned up in web search. One third-party analysis page exists (adrianwwwang.github.io, Kaggle_Google_deepmind_winner_analysis), which I did not fetch.

---

## Cross-project patterns (HM tier)

1. **Narrow, named, high-stakes domain beats a generic agent framework.** Every winner here names a specific industry pain: COBOL banking, agentic-commerce bot blocking, endpoint forensics, battery thermal runaway, archaeology survey, and (weakest) executive reports and Venezuelan education. Two of the three comparators chose meta-problems (auditing agents, PII masking), and the third chose a low-stakes consumer task.
2. **Gemini 3 is load-bearing, and the specific feature is named.** PROCSee uses thinking levels (low vs high, with measured latency), AgentGuard uses Flash for latency, BatteryForge uses vision on live video and screen-share, GeoFlow uses vision plus Search grounding, Logic Lift uses long context, and CineStream uses `thinkingConfig`. SanskaraAI ran on 2.5 Flash Lite and lost.
3. **A verification or grounding loop is a common motif:** Pyodide test-and-fix (Logic Lift), confidence and uncertainty plus self-directed queries (PROCSee), PyBaMM physics plus human-in-the-loop safety (BatteryForge), Earth Engine imagery plus search citations (GeoFlow), and layered override, cache and LLM checks (AgentGuard).
4. **Multi-agent is not required.** Only BatteryForge (ADK, 5+1 agents) and CineStream (a prompt-level "mesh") are multi-agent. PROCSee, AgentGuard, GeoFlow and Logic Lift are single-agent loops or pipelines inside good systems engineering.
5. **Engineering rigor at HM level is modest.** No winner here has a real unit test suite or confirmed CI. Commit counts run from 3 to 24. Two winners (Logic Lift, CineStream) have no public repo at all and are AI Studio apps. Docker-compose is common (AgentGuard, BatteryForge, GeoFlow).
6. **A video and a live demo were not strictly required for an HM.** PROCSee and CineStream show no video, and PROCSee and BatteryForge have no live deployment. The scale (4,500 entries) suggests first-round screening leaned heavily on the written page.
7. **Write-ups that won are long, sectioned and honest about challenges.** They list specific failures and fixes (the 83% stall, ADK schema 400s, WAL locking, the 404 on 3-Pro) and often state limits ("prototype, not validated"). Quantified impact is weak everywhere: numbers are mostly cited industry statistics or self-reported latency, never measured business outcomes.
8. **Solo builders do well:** 4 of the 6 are solo. Google-tool alignment helps too: the AI Studio app builder, Antigravity, ADK, Earth Engine and Maps grounding appear repeatedly.
9. **What distinguishes the non-winners:** the problem is generic or meta, or low-stakes; Gemini 3 is not used or not central (Sanskara); "100%" claims undercut the premise (Aegis); or the key mechanism is vague (VaultSim's masking model). Community likes do not correlate with winning (VaultSim 139 vs winners 1–10).
