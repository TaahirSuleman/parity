# 12 — Workshop learnings: Agents 101 (live, 27 Oct) + legal-agent-workshop repo

Sources:
- the transcript ([11-workshop-agents-101-transcript.md](11-workshop-agents-101-transcript.md));
- a full read of `meta-models/legal-agent-workshop` (one commit, `2a8efc8`), including the hidden Session 1 and Session 2 solutions. I did not run the agent or the tests: the workshop runs on your own machine and your own key, at about $7.

Honesty tags follow doc 06:
- **[sourced]** means it is stated in the session or the repo.
- **[inferred]** is my reading of what it implies.
- **[action]** is something to do.

---

## 1. The single most important takeaway

Meta has shown us the pattern its own partner engineers consider "good agent" practice. **It is the same evaluation lens the judges will bring.** [inferred] The pattern is:

1. **One general loop** with a behaviour-level system prompt. Task specifics live in an objective file, not in the prompt. [sourced]
2. **Tools with strict contracts** (`additionalProperties:false`), one file each. Errors are returned to the model as observations so it can correct itself. [sourced]
3. **A case record that only tools can change.** The model can never declare something "proven". Only `record_fact` (which checks the quote) can move an item to proven, and only a gated `request_evidence` can move it to escalated. [sourced]
4. **Verification inside the gates, not as optional tools.** The handbook's words: "a confident model skips" a verify tool. Checks run when the agent tries to move forward: setting the checklist, recording a fact, filing the memo. [sourced]
5. **Human-in-the-loop as states, not chat.** The states are `needs_input`, then `awaiting_signoff`, then `done`. While blocked there are **no model calls**. A run resumes only when new evidence or a reviewer's answer arrives. [sourced]
6. **Visibility as a feature.** A checklist, a plan and a step-through console show what the model saw, what it decided, what it did and the result on every turn. Token counts are logged per turn. [sourced]

Session 1 builds steps 1, 2 and 6, and ends on a memo stamped **"unverified"**. Session 2 (Agents 102, Yash, **Wed 28 Oct 12:00 ET = 18:00 SAST**) builds step 4. Suraj said verification is "as important as building the agentic loop". [sourced] **Callback v2's two-key gate and evidence locators are already this pattern. We should present them in Meta's own vocabulary.** [inferred]

---

## 2. Muse Code — how Meta wants it used

| Practice | Detail | Status |
|---|---|---|
| Model and effort | Muse Spark 1.3, effort `max`; `/model` and `/effort` switch them | [sourced] |
| Auth and limits | Same API key as your code; **same rate limits** (Muse Code competes with your agent for RPM) | [sourced] |
| Ground rules first | Pasted at every session start (handbook §1.7). They say: build only what is asked; edit only the named folders; `agent_kit/` is read-only; no hard-coded tool order or case specifics; don't run the agent or tests unless asked; **never open `.env` or print keys**; every report lists files changed, commands run and limitations. **Re-paste after a restart.** | [sourced] |
| Plan, then build | Prompt 1 says "Propose a brief plan… what happens in a turn and when does the loop stop. Don't write any code yet." Prompt 2 says "Looks fine, build it, but don't run X… make sure it also files a memo." | [sourced] |
| Tests are the spec | Muse Code reads the `tests/` (fake model) to infer the expected contract. Scope check: `git status` shows only the expected files changed. | [sourced] |
| Workspace boundary by folder layout | `ground_truth/`, `world/` (withheld evidence) and `solutions/` sit **outside** `agent/`, so neither the coding agent nor the runtime agent can see the answer key | [sourced] |
| Orientation | "Give me a high-level summary in 5–6 bullets of X" on any new repo | [sourced] |
| Voice prompting | Option+V on a Mac | [sourced] |
| Course correction | "Just ask it to revert". The harness keeps the trace, and the model is stateless. | [sourced] |
| Extensibility | Custom MCP servers and skills are supported | [sourced] (verbal, no demo) |

**[action]** Use Muse Code as our *primary* coding harness for the build. Record a short screen capture of the plan → build exchange for the video or README. This adds visible "Use of Meta AI Tooling" (25%) at no extra cost. Keep a `GROUND_RULES.md` in the Callback repo modelled on §1.7.

---

## 3. Meta Model API patterns confirmed working (learn from these; we write our own code)

All of these are [sourced] from the repo code.

- **Client:** the OpenAI SDK `openai>=2,<3`, `base_url=https://api.meta.ai/v1`, `max_retries=4`, `timeout=180`. Preflight checks that the model IDs appear in `client.models.list()`.
- **Agent turn:** the Responses API with `store=False`. The **whole item list is resent each turn**, with `instructions=` set to the system prompt each turn and `parallel_tool_calls=False`. It takes the first `function_call` only. If the model answers in plain text, the loop nudges: "Plain text is not accepted. Call exactly one tool". On the last turn it forces `submit_memo`.
- **Documents:** `client.files.create(purpose="user_data")` gives `{"type":"input_file","file_id":…}`, cached by SHA-256. Each document is **transcribed once**, verbatim page by page as JSON. That transcript becomes the source of truth every quote is checked against.
- **Structured output:** `text={"format":{"type":"json_object"}}` plus "Return only JSON: {…}". Code validates the result and retries once with the error. The repo does **not** use `json_schema` strict mode, reasoning effort or streaming.
- **SAM 3.1 boxes:** use `input_image` with a base64 data URL. The output has inline special tokens `<|box;x1=;y1=;x2=;y2=;w=;h=|>`, parsed by regex; empty text means no match. **The prompt "signature" does not match scanned signatures; "ink scribble" does.** SAM concept prompts must be tested empirically.
- **Parallelism lives inside tools:** a `ThreadPoolExecutor` reads up to 4 documents at a time, and a failure in one document is isolated from the rest.
- **Errors:** `openai.APIError` around a turn leads to `status=paused` with the error saved, so the run can be resumed. `NotImplementedError` in a tool also pauses the run cleanly.
- **Not shown anywhere: audio or video input.** **This is the biggest open risk for Callback v2.** [inferred]

---

## 4. Where the reference stops, and where we can go further

These are the gaps a judge who knows this workshop will notice we filled. [inferred]

| Reference repo | Gap | Callback v2 / Claim Clock move |
|---|---|---|
| `check_signatures` is a **placeholder that always returns "consistent"**, although the case contains a planted forged signature | Meta did not show working visual verification | A real SAM, then Spark comparison (boxes, then a second-model consistency check) on screen-recording frames is a visible step beyond Meta's own demo |
| `verify_claims` **fails open**: an unparseable judgement passes | Wrong default for fraud or security | **Fail closed**: an unreadable or uncertain judgement goes to escalation, with the reason shown on the handoff card |
| Ground truth is **coverage only** (6 checklist questions); the memo is never scored for accuracy | No accuracy eval | Labelled per-case expected verdicts and evidence locators; precision/recall, plus Brier/ECE on gate confidence; ablations (doc 06) |
| Truth is the model's **own transcription** | An OCR or ASR hallucination becomes "truth" | Disclose that it is model-derived; spot-check with a second pass or confidence; for Callback, check the diarized segment against the raw IdP log row (an independent source) |
| Only **agent-turn** tokens are logged; the tokens used by readers, judges and SAM inside tools are not | Cost claims cannot be measured | Log usage for every model call, with a $ estimate, which feeds our "saves money" Impact claim |
| **Single agent**; "multi-agent" means verifier calls inside tools | — | Keep our specialist sub-agents, **but frame each as a contracted tool behind a gate**, in Meta's own style. Don't build a free-form agent swarm. |

---

## 5. Concrete changes to our plan (doc 08 Callback v2 spec)

1. **Adopt the repo skeleton** instead of designing our own:
   - `agent_kit/progress.py`: run ledger, resume state machine, `branch()` replay from a checkpoint.
   - `case_record.py`: atomic, audited, status changes only through tools.
   - the tools registry pattern.
   - `tests/fake_model.py`: a real OpenAI client over a scripted `httpx` transport, so CI runs offline.
   - the stdlib UI console (plan/act/observe timeline, checklist, handoff and sign-off cards).

   The repo has no LICENSE file I could find. **Decision (29 Oct):** no workshop code is copied. We take the lessons only and build our own implementation, for differentiation and to keep G0 (sole-ownership IP) clean.
2. **Evidence atom:** `{source: call_audio|screen_rec|idp_log, locator: t_start–t_end | frame_ts+box | log_row_id, excerpt, claim}`. `record_finding` refuses the call unless the excerpt is found in the cached diarized transcript segment, the frame's OCR, or the raw log row. This is our `quote_on_page`.
3. **Map the gates one to one:**
   - `set_checklist` → coverage check against hidden labels (feedback that doesn't leak).
   - `record_finding` → locator check.
   - `request_evidence` → allowed only after every call segment, recording window and log row has been ingested.
   - `submit_verdict` → deterministic rules (key 1), then an entailment judge that fails closed (key 2), then `awaiting_signoff`, then **rollback through the API only after approval** (L3).
4. **Checklist always includes a "benign explanation" item.** This mirrors their mandatory `counterevidence` item, for example "legitimate help-desk reset by the real user".
5. **Demo beat borrowed from the console:** "step through turns" on the first two turns (the judge sees the inputs, decision and action), then "run to end", then a stamped memo. Our twist: the verdict is shown **verified**, with the gate's refusal log visible, where theirs says "unverified".
6. **Spike S1 gets more urgent:** the repo has no audio path. **[action]** Before Wed 22:00 SAST, test `muse-voice-transcribe-1.0` diarization on 2–3 synthetic vishing calls. Also test whether Spark's Responses API accepts audio or video `input_file`. If it doesn't, the pipeline is ASR, then text plus keyframe PNGs as `input_image`.

**Claim Clock (fallback):** the legal pattern transfers almost one to one:
- screenshots and chats → documents;
- APP-reimbursement criteria → checklist;
- reimbursement decision → memo;
- bank or claimant evidence → `request_evidence`;
- claims handler → sign-off.

Its modalities (images and PDFs) are exactly what the repo shows working, so **technical risk is lower than Callback's**. This strengthens it as a fallback if S1 fails. [inferred]

---

## 6. Things to do in the next 24 hours

| When (SAST) | Action |
|---|---|
| Before Wed 18:00 | **Do Session 1 on your own machine** (about $7 of tokens on your key; I can't run it from here). Session 2 starts from your Session 1 run (`./helper branch RUN`); if you skip it, catch up with `rsync … solutions/01_session1/agent/ agent/`. |
| Wed 16:00–17:00 office hours | Ask: (a) does the Responses API accept **audio or video** `input_file` for Spark 1.3, or only via Voice Transcribe? (b) the licence for reusing `legal-agent-workshop` code; (c) the recommended SAM prompts for UI elements in screen recordings; (d) whether Muse Code rate limits are shared with the agent key (confirmed yes; ask about a contributor-tier key for Muse Code). |
| Wed 18:00 | Attend **Agents 102** (Yash): verification, escalation, sign-off. Capture its transcript the same way and fold anything new into this doc. |
| Wed 22:00 | Decide S1/S2 as planned in doc 08, now with the audio-input answer in hand. |
