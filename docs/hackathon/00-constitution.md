# Meta Global AI Developer Hackathon — Project Constitution
**Track:** Indie Developer · **Participant:** Taahir Suleman (solo unless a team of ≤4 is formed) · **Status:** v1, written 2026-10-27 (day 2 of 10) · **Supersedes:** nothing — this is the source of truth for every project decision until submission.

Sources (all scraped and saved to this project): the public event page, the login-gated Participant Guide (event details), the Official Rules / Event Waiver, the live submission form, the full 23-minute kickoff transcript, dev.meta.ai documentation (≈130 pages), both Meta cookbook repositories, and the model landing pages. Where sources differ, the Participant Guide and Official Rules govern.

---

## Article I — The objective function

Everything we build is scored by Meta-team judges on this rubric, on a 0–10 scale per category. It is reproduced verbatim from the Participant Guide and is identical in the Official Rules.

| Category (weight) | Verbatim description |
|---|---|
| **Impact (30%)** | What's the real-world potential here? Who benefits, and how much does it matter? Could this actually become something people use? Does it fit into one of the problem statements listed above? |
| **Use of Meta AI Tooling (25%)** | How creatively did this team use Meta's AI tooling? Did they go beyond a basic integration? Did they surface capabilities that surprised even us? |
| **Technical Depth & Execution (20%)** | Is the engineering sound and thoughtfully refined? Does this feel like something that was thought through with real craft. |
| **Demo (25%)** | Is this a working, impressive demo? Does the product hold up live? Is the demo video genuinely cool to watch? |

Indie-track framing (public page + kickoff): "judged on creativity, technical ambition, and whether it works."

**Rule of decision:** any design choice, scope cut, or time allocation must be justified by pointing at a cell of this table. If it cannot be, it is not done.

### I.1 What each category actually tests (decoded)

**Impact (30%) — four sub-questions, score all four.**
1. *Real-world potential:* is the problem real, large, and currently handled badly? Quantify it (money, hours, error rate, people affected).
2. *Who benefits and how much:* a named user with a named job. Saurabh Baji (Meta, Model API eng director) in the kickoff: "Pick a clear user and a clear job to help them accomplish… Aim for a working prototype that you can demonstrate. Put it in someone's hands early." Evidence of a real user touching it is worth points.
3. *Could this become something people use:* a product path, not a toy. Not "could be extended to"; show it on realistic inputs at realistic scale.
4. *Fits a problem statement:* must map cleanly onto **Build for Your World** (a problem we know firsthand; "free up time and mental space") or **Push the Frontier** (new capability for software/robotics/manufacturing/energy/materials/physical systems).

**Use of Meta AI Tooling (25%) — the bar is "surprised even us".** Meta employees are the judges. A basic chat-completion integration scores low by definition. High scores require that Meta-specific capabilities are *load-bearing*: remove them and the product collapses. The submission form forces us to answer "Why are Meta's models important to your solution?" — that answer must be structural, not "we used the API."

**Technical Depth & Execution (20%) — "sound", "refined", "real craft".** Judges read the public repo. Craft is visible as: clean architecture, deterministic validators around every model output, evaluation harness with numbers (precision/recall/F1 against ground truth), observability (traces, audit log, replay), failure handling, tests, and a README that explains all of it.

**Demo (25%) — three tests: working, holds up live, video "genuinely cool to watch".** The 3-minute video is "one of the primary artifacts Judges use… along with your code and live product" (Participant Guide §7). In the final round the judges watch the video live and rank. The video is therefore worth ~25% directly and leaks into all other categories because it is the primary channel through which Impact, Tooling and Depth are perceived.

### I.2 Stage gates (judging process, verbatim structure)
- **Stage One — pass/fail:** project "reasonably fits the theme and reasonably used Meta Model API and/or Meta's open-weight models to build the project in the Hackathon." → We must call the Meta Model API and/or run Muse Glimmer / Muse Spark Open *inside the product*. Using Muse Code only as a dev tool does not by itself satisfy this.
- **Stage Two — rubric scoring 0–10** by Meta-team judges, Nov 5–8. With up to 20,000 accepted participants, assume a judge spends single-digit minutes per project: video first, README second, live product third.
- **Stage Three — top 5 per track**, Nov 9, judges watch video demos live and rank with the same rubric. Winners revealed; community vote opens.

---

## Article II — Hard constraints (disqualification risks)

| # | Constraint | Source |
|---|---|---|
| 1 | **Deadline: Wed Nov 4, 9:00 PM ET.** Late submissions not considered. Nov 3 is the last full day for submission/tech questions. | Guide §3, §7 |
| 2 | **Public GitHub repository.** "We will be evaluating all of them." | Guide §4; kickoff 13:17 |
| 3 | **New work only; demo only what was built during the hackathon.** "Judges must be able to clearly identify what was created during the Hackathon. Failure to clearly identify your original contributions will result in immediate disqualification." Prior work may be used only if explicitly called out and the boundary is clear. | Guide §4; kickoff 12:24 |
| 4 | **Team ≤ 4, all members approved participants.** Solo allowed. One Representative submits. | Guide §4; Rules |
| 5 | **Must incorporate Meta's models** (Muse Spark series, Muse Wonder, Muse Image, Muse Voice Transcribe, SAM 3.1 via Model API; Muse Glimmer / Muse Spark Open open weights; Muse Code). | Guide §1 |
| 6 | **Banned:** violates legal, ethical, or platform policies; uses code/data/assets we lack rights to. | Guide §4 |
| 7 | **Anti-projects (explicitly discouraged):** AI medical advice (mental-health advisor, skin-blemish detector…), basic RAG apps, simple image analyzers, simple "AI for Education" chatbots, AI job-application screener, AI nutrition coach, personality analyzers, sports analyzers/coaches, anything political or involving war. Kickoff adds: "simple chat wrappers". | Guide §4; kickoff 13:55 |
| 8 | **3-minute demo video** with good voiceover, well produced: "describing your project, what you built, showing it in action." Must only highlight hackathon-built functionality. | Guide §7; kickoff 20:50 |
| 9 | **IP:** we retain ownership; we grant Meta/CV a perpetual, irrevocable, royalty-free, non-exclusive licence to use/adapt/publish the Submission for any purpose. Nothing shared is confidential. Submission must be original and solely owned; OSS allowed if licences are followed and we build upon it. | Official Rules |
| 10 | **Eligibility:** 18+, not in sanctioned regions, not Meta/CV affiliated. | Rules |

**Operational corollary of #3:** start a fresh repo with a first commit dated after the Oct 26 kickoff; keep a `HACKATHON_SCOPE.md` declaring what was built during the event and listing any pre-existing libraries/data with their licences.

---

## Article III — Prizes and what they imply

**Indie Developer track ($400K):** 1st $150K · 2nd $100K · 3rd $75K · 4th $50K · 5th $25K.
**Startups ($550K):** $250K / $150K / $75K / $50K / $25K.
**Bonus ($50K, from Meta):**

| Prize | $ | Rewards | How judged | Our stance |
|---|---|---|---|---|
| Best Agentic Use-Case | 5,000 | "strongest use of AI agents to complete meaningful tasks, make decisions, or coordinate multi-step workflows" | "level of autonomy, effectiveness in completing its intended task, and practical usefulness" | **Target.** Our thesis (autonomous multi-agent orchestration that resolves a costly workflow) is literally this prize's definition. Design for it explicitly and say so in the submission. |
| Best Build on Meta Open Weight Models | 10,000 | best project on Muse Glimmer or Muse Spark Open, own hardware or partner inference | flagged in round one; infra partner verifies it runs on an eligible open-weight model | **Opportunistic.** Include a Glimmer (local, Apache 2.0) or Spark Open (Baseten `meta-models/muse-spark-open-1026`) tier if it is load-bearing (e.g., privacy-preserving first pass, cost tier, or a post-trained specialist). Do not bolt it on cosmetically. |
| Community Vote | 10,000 | most votes in public gallery (one per verified account); announced Nov 16 | platform votes | Low-effort upside: share the gallery link widely after submission. |
| Most Viral Project | 20,000 | highest engagement on X until Nov 8 EOD | post demo on X, submit link in form | Post the video on X at submission time; a visually striking demo helps both this and the Demo score. |
| Best Creative Build | 5,000 | Muse Image or Muse Wonder creative project | originality, execution | Not our lane unless Muse Image is incidentally load-bearing. |

Bonus prizes do not reduce track prizes; a project can win both.

---

## Article IV — Calendar (all ET)

| Date | Event | Action for us |
|---|---|---|
| Mon Oct 26 | Kickoff (done) | — |
| **Tue Oct 27, 12:00–1:00 PM** | **Agents 101: Build a Multimodal AI Agent** — Suraj Subramanian (Meta) | Attend / watch recording; harvest patterns Meta considers canonical. |
| **Wed Oct 28, 12:00–1:00 PM** | **Agents 102: Best Practices for Verifiable Agents** — Yash Khare (Meta) | **Must attend.** "Verifiable agents" is exactly our dependability/precision/recall/observability thesis; align vocabulary and architecture with what Meta teaches here. |
| Fri Oct 30, 12:00–1:00 PM | Fireworks: "Building Specialized Intelligence on Fireworks: From Inference to Training with Muse Open Models" — Sinan Ozdemir | Attend if pursuing an open-weight/fine-tuned specialist. |
| Weekdays 10–11 AM | Meta office hours in Discord #office-hours (text) | Use for API blockers and to validate our tooling angle with Meta engineers. |
| Tue Nov 3 | Last full day for submission/tech questions | Submission dry run complete by this day. |
| **Wed Nov 4, 9:00 PM** | **Submissions due**; credit claim deadline | Submit by ~6 PM to leave margin. |
| Nov 5–8 | Judging (Stage 1 + 2) | X post live for viral prize (engagement counted to Nov 8 EOD). |
| Mon Nov 9, 12:00 PM | Closing ceremony: top 10 announced, live finals, winners; community vote opens | — |
| Nov 16 | Community vote winner | — |

Build window remaining as of this writing: **~8.5 days**. Reserve the last 36 hours for video production, README, eval tables, and submission.

---

## Article V — Submission package (what judges receive)

The live form (captured from the platform) requires, in order:
1. Team Name*; Team Members
2. Track* (Indie Developer) · Problem statement* (Build for Your World / Push the Frontier)
3. X post link (Most Viral)
4. **Project Description*** — "Describe your project and what problem it solves…"
5. **Public GitHub Repository***
6. **3-Minute Demo Video*** (YouTube link)
7. **"Describe your use of Meta products to build the submitted project"***
8. **"Why are Meta's models important to your solution?"***
9. Feedback on Meta products · Feedback on partner technologies (Fireworks, Modal, Baseten)
10. Consent to publish/promote submitted materials.

Items 4, 7 and 8 are free-text essays read by judges. Draft them from day one as the project's north star; if 8 is hard to answer convincingly, the architecture is wrong.

**Judge-facing artefacts, in order of exposure:**
1. **Video (hard cap 2:55).** Follows the **demo-first** storyboard in `04-winning-recipe.md` §4.4 (v3). Amended v1.2 after the Gemini 3 post-mortem (doc 15).
   - **Running order:**
     - 0:00–0:08: one line on what was pre-existing vs built this week (organisers, 30 Oct), then cold open on the hero input inside the product.
     - 0:08–0:25: the problem told over the product, with one sourced overlay card.
     - 0:25–1:35: live run triggered from the UI. The trace streams, perception is drawn on the media, a verifier refusal appears, then the hero moment, a **visible human approval click** and the system of record changing.
     - 1:35–1:55: baseline or ablation contrast.
     - 1:55–2:10: ≤ 10 s architecture card, then the trace view.
     - 2:10–2:35: the eval tab.
     - 2:35–2:50: impact and close.
   - **Product on screen** ≥ 80% of runtime; slides and cards ≤ 20 s in total; the browser-tab motif appears only as overlay chips.
   - **Production:** scripted voiceover, music bed, burned-in captions, no dead air, no "skipped ahead" cuts.
   - **Length:** measured on the rendered file.
2. **README** — problem and user; architecture diagram; Meta capabilities used and why each is load-bearing; eval methodology and results table; observability/audit screenshots; how to run in 5 minutes; `HACKATHON_SCOPE.md` link; licences.
3. **Live product** — a hosted URL or one-command local run that "holds up live" on an unseen input.

---

## Article VI — Meta AI tooling map (what we can use, what it costs, what counts as creative)

### VI.1 Hosted Model API (base `https://api.meta.ai/v1`, key `MODEL_API_KEY`, OpenAI-SDK compatible; Anthropic-style `/v1/messages` also supported)

| Model ID | Role | Context | Price per 1M tokens (in / cached / out) | Limits |
|---|---|---|---|---|
| `muse-spark-1.3` | **Default workhorse.** GA. Agentic + coding; text, image, video, PDF in; reliable parallel tool calling; reasoning up to `max`. Audio input not fully supported → use 1.2 for audio | 1,048,576 | $1.25 / $0.15 / $4.25 | 3,000 RPM / 4M TPM per team |
| `muse-spark-1.3-contributor` | Same model, ~12× cheaper, Meta may train on data; no `max` effort; not with ZDR | 1,048,576 | $0.10 / $0.002 / $0.20 | 150 RPM / 3M TPM |
| `muse-wonder-1.0` | Most capable — **Preview**, Standard mode only, unavailable in South Korea; long multi-hour agents, planning, sub-agent delegation, computer use; output capped 131,072 in agent configs | 1,048,576 | $4.00 / $0.20 / $20.00 | 3,000 RPM / 4M TPM |
| `muse-spark-1.2` (+contributor) | Previous gen, GA; **recommended for audio input** (`input_audio` wav/mp3) | 1,048,576 | as 1.3 | as 1.3 |
| `muse-image-1.0` | Agentic image generation/editing (web-grounded, code-before-render) | — | $0.01 / image | 150 RPM |
| `muse-voice-transcribe-1.0` | Real-time + file STT; diarization (20+ speakers), endpointing, keyword biasing, 25 languages | — | $0.18 / hour ($3 / 1k min) | 256 concurrent streams |
| `sam-3.1` | Open-vocabulary segmentation + video tracking from a noun phrase → boxes + masks with persistent identity | — | $2.50 / 1k images; $0.20 / 1k frames | 3,000 RPM |
| Web search grounding | Built-in tool with `url_citation` spans | — | +$2.50 / 1k queries | Responses/Messages only |

**$150 credit math:** at Spark 1.3 prices a typical agent step of 50K input + 5K output ≈ $0.08 → ~1,800 steps; with prompt caching far more. Credits are ample for development and demo; the constraint is engineering time, not tokens. A credit card must be attached before any call (pre-auth hold); set a Spend Limit on the Billing page.

**Capabilities that matter for an orchestration product:**
- **Responses API** with `previous_response_id` or `store:false` + `include:["reasoning.encrypted_content"]` → reasoning continuity across agent turns (Chat Completions cannot do this).
- **Structured output** (`json_schema`, `additionalProperties:false`, Pydantic `.parse`) → every agent emits a validated contract. No recursive schemas; `tool_choice` is `"auto"` only.
- **Parallel tool calls** (`parallel_tool_calls` default true; `max_tool_calls` to budget); **tool search** (`{"type":"tool_search"}` + `defer_loading`, namespaces; hosted or client-executed; not combinable with structured output); **background responses** (`background:true`, 600 submissions/min/team, poll/stream/cancel) for fan-out and long runs — non-streaming long calls 504.
- **`reasoning_effort`** `minimal` / `low` / `medium` / `high` / `xhigh` / `max` (`max` only on Wonder and Spark 1.3 Standard; `none` → 400); reasoning tokens billed as output; tier effort per agent role for cost control.
- **Prompt caching** automatic on stable prefixes (`prompt_cache_key`, 24h retention) → cheap repeated system prompts/policies.
- **Files API** (1 GiB per file, 100 GiB/team, `purpose=user_data`; PDFs: text from first 100 pages, images from first 50; MP4 includes audio → description + transcript in one call) + ~50 images per request + 1M window → whole case files in one call.
- **Vision/video understanding** native to Spark; **perception grounding** returns points/boxes/counts on a 0–1000 grid that can be fed directly as SAM 3.1 box/point prompts; **SAM 3.1** pixel masks + video tracking (≤15,000 frames ≈ 10 min, ≤16 objects, propagation direction, confidence); **Voice** diarized transcripts with `turnId` correlation, endpointing, keyword biasing.
- **Computer use** built-in tool (Responses only; Wonder, or Spark for cheap long runs) with mandatory safety-check acknowledgement — a human-in-the-loop hook by design.
- **Three wire formats on one key:** Responses, Chat Completions, Anthropic-style Messages (`base_url=https://api.meta.ai`, `ANTHROPIC_AUTH_TOKEN`) — so OpenAI SDK, Anthropic SDK, Vercel AI SDK, LiteLLM, LangChain, LlamaIndex, Claude Agent SDK, Codex app-server, OpenCode, Hermes and Muse Code all work. Only Claude Agent SDK and Codex app-server are formally documented as agent frameworks.

**Known quirks (HTTP 400):** no `stop`, `logit_bias`, `n>1`, `logprobs`; `tool_choice` only `"auto"`; images only in `user` messages; no recursive schemas (depth ≤10); no server-side truncation (measure with `POST /v1/responses/input_tokens`); `web_search`/`tool_search` only on Responses/Messages; structured output is `response_format` on Chat but `text.format` on Responses; Chat Completions cannot carry reasoning across turns. Preview caveats: Wonder is preview; default `reasoning_effort` "being finalized"; realtime ASR access limited during rollout; no official Meta SDK — use the OpenAI or Anthropic SDK.

### VI.2 Muse Code (coding agent; also an embeddable engine)
- Install `curl -fsSL https://dev.meta.ai/install.sh | sh`; `muse` in a project; PAYG or Everyday $5 / High $15 / Power $50 (Wonder Full) / Maximum $200.
- **Headless:** `muse exec "<prompt>" --json --output-schema … --max-model-steps …`; exit codes; `--session-id` resume.
- **Programmatic:** `muse serve` JSON session protocol (≤256 sessions), TypeScript `@muse-code/sdk` and Python SDK; hooks (17 events incl. `PreToolUse`/`PostToolUse`/`PreLLMCall`/`Stop`); MCP servers (`stdio`/`streamable_http`); skills (`.agents/skills/<id>/SKILL.md`); subagents (8 concurrent default, worktree isolation, spawn/status/steer/cancel/wait); four observers (memory, skill, goal, verification); `/goal` with completion audit; `/loop` cron.
- **Auditability primitives:** append-only `session.jsonl` (intent-before-effect, `decision_source` incl. `llm_judge`), `muse export` byte-deterministic (`--redacted`), `muse resume` idempotent crash reconcile, deterministic replay golden fixtures as a CI gate, staged approvals (fail-closed), live-probed OS sandbox, immutable guardrails on `.agents/`/`.muse/`.
- Use it (a) as our build accelerator and (b) potentially as the orchestration/audit substrate of the product itself — the docs describe this path (`muse serve` + SDK) and it is rarely used: a candidate "surprised even us" angle.

### VI.3 Open-weight models
| | Muse Spark Open | Muse Glimmer |
|---|---|---|
| Size / licence | 816B MoE, 42B active; **Muse Model License + AUP** | 30B dense + vision encoder; **Apache 2.0** |
| Context | 1,048,576 | 131,072 |
| Run | Needs 4×B300 (NVFP4) or 8×B300 (BF16), or Mac Studio cluster → **use hosted:** Baseten `meta-models/muse-spark-open-1026` ($100 credits + 2M TPM, 2,000 participants, use-case reviewed), Fireworks ($25), Modal ($100, first 1,000), Together, OpenRouter | **Runs on a 24 GB GPU or a Mac** (Q4_K_M ≈ 19 GiB with vision + 131K ctx): Ollama `ollama run muse-glimmer`, llama.cpp (`-hf meta-models/Muse-Glimmer-30B-GGUF`), LM Studio, ExecuTorch (edge); hosted on Together/Fireworks/OpenRouter |
| Agentic notes | Parallel tool calls; "commentary channel" states intent before acting; `reasoning_effort` low/med/high/xhigh (cannot be off); Baseten returns reasoning in `reasoning_content` | Tool use, long tasks, failure recovery, persistent state; **one tool call per turn**; ATEM tool format; strong on MCP Atlas / SWE-Bench Verified for its size |
| Post-training | TorchTitan SFT/RL (large), TRL LoRA, hosted LoRA on Fireworks (SFT/DPO/RL) or Together | Axolotl QLoRA on 1×H100 (~27 GB); **TitanRL GRPO rubric-env recipe (8×H100, ~75 min)** with a verifiable business-data reward — documented data-analyst example lifts reward 0.21→0.98 |

### VI.4 Harnesses documented against the Meta API
Muse Code · OpenCode (`@ai-sdk/openai-compatible`, used in most cookbook recipes) · Hermes (profiles + Kanban multi-agent) · OpenClaw (gateway) · Codex app-server · Claude Agent SDK (`ANTHROPIC_AUTH_TOKEN`) · Playwright MCP · Cua / `metacua` computer use. Any OpenAI-SDK-based framework (LangGraph, OpenAI Agents SDK, etc.) works via `base_url`.

### VI.5 The "beyond basic integration" ladder (ranked by how much Meta judges will care)
1. **Meta-only multimodal fusion that is load-bearing:** Spark perception grounding (0–1000 points/boxes/counts) → SAM 3.1 masks/tracks + Spark video/PDF understanding + Voice diarization in one pipeline, with outputs cross-referenced (the cookbook's head-locked captions and robotics recipes prove the pattern; the media-segmentation docs say it outright: "Muse Spark interprets a scene and picks what to segment; SAM 3.1 produces the masks"). No other vendor bundles these on one key.
2. **Orchestration on Meta's own agent substrate:** Muse Code `muse serve`/SDK sessions as workers, hooks streamed into our observability store, subagent fan-out in isolated worktrees, `/goal` completion audits, deterministic replay as the eval gate.
3. **Verifiable-agent engineering with Meta primitives:** strict `json_schema` contracts at every hop, Responses encrypted-reasoning continuity, deterministic validators and graders, `reasoning_effort` tiering by role, prompt-cache-aware prompt layout, background fan-out.
4. **Hybrid open/closed with an egress boundary:** Glimmer locally for first-pass/PII-sensitive extraction, escalation to Spark 1.3 / Wonder through an approval-gated tool with a content-free egress ledger (cookbook "local agent that asks first").
5. **Post-trained specialist:** TitanRL GRPO or hosted LoRA on Glimmer/Spark Open with a rubric reward derived from our ground truth; show fine-tuned beats base on our eval. Highest depth, highest schedule risk.
6. **1M-context whole-case reasoning** replacing retrieval pipelines (explicitly *not* "basic RAG").
7. Web-search grounding with mapped citations; Muse Image only if it genuinely produces a deliverable.

A basic integration (one model, one prompt, chat UI) is the floor the anti-project list describes. We must be on rungs 1–4 simultaneously.

---

## Article VII — What the organizers told us they want (signals from the kickoff)

- "Start with the problem you understand. Think about a task that you have to repeat, a process that takes too long, or something that people in your community struggle to access."
- "Maybe you build an agent that helps a small business work through a complicated workflow." (The one business example Meta volunteered.)
- "Pick a clear user and a clear job to help them accomplish. That'll help you decide what to build first and what a useful result looks like."
- "Aim for a working prototype that you can demonstrate. Put it in someone's hands early, watch how they use it, and let that feedback shape your next iteration."
- "Keep checking whether your prototype delivers the result you intended. Look at the output, test the workflow, and learn from the failures."
- "Push these Meta models to the edge… try and come up with something more unique."
- Meta's own framing of its stack (Connect sessions): the model gives "intelligence to see, decide, and act"; the harness gives "reliability, scale, and auditability for shipping production code." Muse Spark "treats what it perceives as something to act on, not just something to caption."
- Workshop titles: *Agents 101: Build a Multimodal AI Agent*; *Agents 102: Best Practices for Verifiable Agents* → multimodal + verifiable is the house style.

---

## Article VIII — Problem-selection doctrine (how candidates are scrutinised)

Our thesis, restated as the hackathon's language: a **high-value problem** (Impact) that is today handled by **manual, slow, inaccurate workflows** (status quo pain), resolved by an **autonomous multi-agent orchestration** (Best Agentic + Tooling) that is **dependable, verifiable (precision/recall/F1), observable** (Technical Depth; Agents 102), and runs **fast, at scale, cheaply**, **saving or making a lot of money** (Impact; Demo numbers).

Every candidate problem is scored 0–5 on the twelve criteria below. Hard-fail criteria are marked ✱; a 0–1 on any of them eliminates the candidate regardless of total.

| # | Criterion | 5 looks like | 0–1 looks like |
|---|---|---|---|
| 1 ✱ | **Economic magnitude** | Industry cost ≥ $1B/yr and a per-unit cost we can state (e.g., "$X per case, Y hours"); the beneficiary pays today | Vague "saves time"; cannot name who pays |
| 2 ✱ | **Status-quo failure is demonstrable** | We can show the manual workflow, its error rate and latency on real/representative inputs | Status quo already automated well, or failure is anecdotal |
| 3 ✱ | **Multi-agent is necessary, not decorative** | The job decomposes into ≥3 specialised roles with verifiable intermediate contracts and a decision/coordination step | One prompt would do it (then it is a chat wrapper) |
| 4 ✱ | **Meta tooling is load-bearing** | ≥3 Meta capabilities from VI.5 rungs 1–4 that cannot be swapped without the product collapsing (messy multimodal inputs: video, photos, scans, calls; 1M context; SAM/Voice) | Text-only prompts any API could serve |
| 5 ✱ | **Verifiability / ground truth** | Labelled or synthesisable ground truth → P/R/F1, exact-match or rubric graders; deterministic validators; replayable runs | Output quality is a matter of taste |
| 6 ✱ | **Demo-able in 3 minutes** | Visible input → visible autonomous work → visible output + before/after numbers; live dashboard; survives an unseen input | Needs explanation to be impressive; output is a wall of text |
| 7 ✱ | **Buildable in ~8 days, solo, with coding assistants** | Public/synthetic data with clear licences; no hardware, no partner API approvals on the critical path; MVP in 3 days | Needs proprietary data, integrations we can't access, GPUs we don't have |
| 8 | **Theme fit + credibility** | "Build for Your World": we know the domain firsthand and can say so; or a crisp "Push the Frontier" physical-world story | Domain we can't speak to; judges will ask "who benefits" and we'd guess |
| 9 ✱ | **Not an anti-project / policy-safe** | Nowhere near medical advice, hiring screening, education chatbots, nutrition, personality, sports, politics/war, basic RAG, image analyzer | Any proximity to that list |
| 10 | **Bonus eligibility** | Natural Best-Agentic fit; a load-bearing Glimmer/Spark Open tier | Neither |
| 11 | **Open-source-ability** | Everything we need to publish is ours or permissively licensed; synthetic data is realistic | Depends on data we can't publish |
| 12 | **Wow / virality** | A moment in the video that a non-expert finds remarkable (e.g., pixel-grounded evidence, hours → seconds, a dashboard of money saved) | Internally impressive, externally dull |

**Recipe filters (from the winning recipe, `04-winning-recipe.md`), applied alongside the table:** (R1) a forcing function with a date, regulation or quantified loss; (R2) the agent holds real authority over a system of record, with calibrated autonomy (auto-act / escalate / block) and a measurable autonomy rate; (R3) at least one non-text input modality that Meta's stack uniquely handles is central to the job; (R4) founder fit — draws on firsthand domain knowledge from the CV, while staying clear of the employer's own product. **Added v1.2** (from the Gemini 3 post-mortem, doc 15; motivated by Demo 25%, Tooling 25% and Impact 30%):
- **(R5) Perceptual load.** A non-text modality is load-bearing *and* demoable: its output is drawn on the media in frame.
- **(R6) Workbench.** The decision moment naturally lives in a UI a judge can operate from the public URL without logging in.
- **(R7) Hero moment.** A one-sentence "humans or rules miss it, we catch it" moment exists for the golden case.
- **(R8) Face.** A named person in a vivid scenario, not an abstract system failure.

A candidate that fails R5–R8 is rescoped before build, not after.

**Scrutiny protocol before any build:** (a) write the one-paragraph "user + job + cost of status quo"; (b) sketch the agent graph with each hop's output schema and its validator; (c) name the ground-truth source and the metric; (d) list the Meta capabilities per hop and answer form question 8 in two sentences; (e) storyboard the 3-minute video; (f) estimate build days per component; (g) check against the anti-project list and rights; (h) score the table; (i) only then prototype the riskiest hop for one day. Kill fast if (i) fails.

**Red flags that have sunk comparable hackathon entries:** chat UI as the product; retrieval-over-documents as the whole idea; "could work on real data" with only toy data; no numbers; the demo video narrates slides instead of showing the thing running; Meta models swappable for any other API; scope that needs a week of integration before the first end-to-end run.

---

## Article IX — Engineering standards (non-negotiable for Technical Depth)

1. **Contracts everywhere:** every inter-agent message is a `json_schema`-validated object; validation failures are logged, retried with the error, and counted.
2. **Oracle for "done":** each agent and the whole pipeline has an objective completion check (tests, graders, schema + rule validators) — never the model's own say-so. Self-assessment stages must name their weakest claim and defer to a human (cookbook alert-fatigue pattern).
3. **Evaluation harness from day one:** a fixed eval set with ground truth; precision/recall/F1 (or task-appropriate metric), latency, cost per case; results table in README; regression gate in CI.
4. **Observability:** per-run trace (every model call, tool call, decision, validator result) persisted and viewable; audit log is append-only; a run can be replayed deterministically from its record.
5. **Guardrails:** least-privilege tools per role; destructive or external actions require an explicit gate; treat all ingested content as untrusted data (prompt-injection posture Meta highlights for Spark 1.3).
6. **Cost/latency engineering:** `reasoning_effort` per role; prompt layout for caching; parallel/background fan-out; measured and reported.
7. **Reproducibility:** one-command run, pinned deps, `.env.example`, seed data, `HACKATHON_SCOPE.md`.

---

## Article X — Operational setup checklist

- [ ] Claim $150 Model API credits (form in Participant Guide §5) — per participant, by Nov 4 9 PM ET; add card; set Spend Limit.
- [ ] Request Baseten credits ($100 + 2M TPM; use-case reviewed) and Modal credits ($100, first 1,000) — only if an open-weight tier is planned; Fireworks ($25) optional.
- [ ] Join Discord via event page `/discord`; claim Linked Role; watch #announcements, #office-hours.
- [ ] Install Muse Code; verify `muse --version`; decide plan tier.
- [ ] Create public repo after kickoff date; add `HACKATHON_SCOPE.md`, `LICENSE`, `.env.example`.
- [ ] Register for the Oct 27/28/30 sessions (livestream page) and note recordings.
- [ ] Dry-run the submission form by Nov 3 (fields in Article V).

---

## Article XI — Open questions and risks (track and resolve)

1. Muse Code on Linux vs macOS/Windows: landing page says macOS & Windows; docs cover Linux (bubblewrap for CI). Confirm on our dev machine.
2. Partner credit approval is discretionary and batch-distributed; do not put Spark Open hosted inference on the critical path until credits land.
3. Preview behaviours: `reasoning_effort` defaults, realtime ASR rollout limits, Wonder preview — test early, pin what works, fall back to Spark 1.3.
4. Realistic data with publication rights is the most common blocker for "Impact" credibility — resolve during problem selection, not after.
5. Judges' time per project is small: if the video does not land in 20 seconds, nothing else is read.

---

## Amendment process
This constitution is amended only by appending a dated entry below with the reason and the rubric cell that motivates it.

- v1 — 2026-10-27 — initial constitution from full crawl of event pages, rules, submission form, kickoff transcript, Meta docs and cookbooks.
- v1.1 — 2026-10-27 — integrated the winning recipe from The Compliance Gatekeepers (IBM Agentic Hackathon, 2nd place): video storyboard (Article V) now follows the browser-tab format; recipe filters R1–R4 added to Article VIII. Motivated by Demo 25% and Impact 30%. Key upgrade over the IBM version: measured evidence and calibrated autonomy replace absolute claims ("zero human error", "without human approval"), for Technical Depth 20% and Best Agentic.
- **v1.2 (2026-10-29): integrated the Gemini 3 Hackathon post-mortem** (Resilix, which did not place, compared against all 13 winners; doc 15).
  - **Article V:** the video moves to the demo-first storyboard (doc 04 §4.4 v3), with a hard cap of 2:55 and product on screen ≥ 80% of runtime.
  - **Article VIII:** recipe filters R5–R8 added (perceptual load, workbench, hero moment, face).
  - **Motivation:** Demo 25% ("holds up live", "genuinely cool to watch"), Tooling 25% and Impact 30%.
  - **The evidence:**
    - All three placed Gemini 3 winners were product-first and perceptual, with an interactive surface and a visible human gate.
    - Resilix lost judged time to slides, a cut live run, a text-only input, a read-only UI and over-length (4:14, with impact after the 3:00 cut-off).
- **v1.3 (2026-10-30): organiser guidance on video judging.**
  - The video is judged under Demo (25%) and Use of Meta AI Tooling (25%).
  - Show the product working, not slides.
  - Open with one line on what was pre-existing and what was built this week.
  - Judges stop at 3:00.
  - **Changes:**
    - Article V's running order now starts with the scope line.
    - Each on-screen step labels the Meta model doing it.
    - The 2:55 cap stands.
