# Meta "legal-agent-workshop": repo analysis

Source: `meta-models/legal-agent-workshop`, one commit (`2a8efc8 Legal agent workshop`). Cloned at `scratchpad/workshop/legal-agent-workshop`. I read everything listed in the brief. I did not run the agent or the tests, because the sandbox cannot reach PyPI to install `openai>=2.0,<3`. The tests are offline by design (see section 3.7).

---

## 1. Purpose, scenario, workshop structure

**Purpose.** This is a teaching kit for the sessions "Agents 101" and "Agents 102". Participants build a *general* document-investigation agent (multimodal: PDFs, scans, a JPG photo) on the Meta Model API using the plain OpenAI Python SDK. They then make it "verifiable": checks that the model cannot skip, escalation to a human, and attorney sign-off. Participants write code only through **Muse Code**, started from `agent/`. `cases/`, `ground_truth/`, `world/` and `solutions/` are deliberately kept outside its workspace, so neither the coding agent nor the runtime agent can see the ground truth or the withheld evidence.

**Scenario: *Northbridge v. Caldera*** (fictional failed ERP go-live, "Project Keystone").
- `cases/northbridge-v-caldera/objective.md` asks: *Did Caldera know the system was not ready for go-live, and tell Northbridge it was?* What is at stake: the liability cap is $4,187,500 and does not apply to fraud, gross negligence or wilful misconduct. The uncapped claim is $9,127,500. The objective's instructions: inspect, don't assume; some documents are irrelevant or contradictory; ground every claim in document + page + exact quote; keep evidence separate from interpretation; don't guess; finish with a memo (answer, one finding per checklist item with citations, gaps).
- **21 initial documents** (`documents/`, Bates-style IDs `NBI-…` and `CALDERA-…`):
  - SOW appendices: readiness criteria, UAT exit criteria, milestone payments.
  - Weekly status reports, SteerCo deck, RAID log, change-order log, invoices.
  - Distractors: a cafeteria-subsidy spreadsheet.
  - A **privileged attorney work-product memo** (`NBI-00000593`), a trap the agent should not cite.
  - A Rule 408 settlement letter, `CALDERA-00000896`.
  - Several **image-only scans with no text layer** (`NBI-00000086`, 11 pages; `-097`, `-151`, `-204`, `-275`, `-453`) and one JPG (`NBI-00000337.jpg`).
  - `NBI-00000151` carries the **genuine reference signature** of Test Manager Marcus Thibodeaux.
- **7 withheld follow-up documents** (`world/follow_up/`, released by `world/release.py` only after the run reaches `needs_input`):
  - Internal Caldera readiness material (the "timing" evidence).
  - A Teams export: "Marcus is on PTO … He said no [to signing remotely] … The cert is a project artefact, not a personal one".
  - `CALDERA-00000419`: a UAT Phase 2 exit certification whose handwritten signature was **deliberately drawn not to match** the reference (`world/utils/build_signature_assets.py`).
  - In other words, the case contains a planted forgery and a privileged-document trap.
- **Ground truth** (`ground_truth/northbridge-v-caldera.json`): `{"about": str, "items": [{"id","question"}]}`. It has 6 items: `not_ready`, `ready_statement`, `timing`, `seniority`, `signatures`, `counterevidence`. It holds only *what must be covered*; there are no answer values. It is used by the checklist check alone.

**Workshop structure** (HANDBOOK.md).

| Session | Step | Participant builds | Solution diff |
|---|---|---|---|
| 1 "Build the agent" | 2.4 Prompt 1: plan; Prompt 2: build loop | `legal_agent/loop.py` only | `agent/` → `solutions/01_session1/agent`: **only `loop.py` changes** (adds `instructions()`, `user()`, `tool_output()`, `drive()`, and implements `run_agent` and `resume_run`; about 85 lines). |
| 1 | 2.5–2.6 run in console, read memo | – | The memo is `unverified`. Built-in lessons: a signature "proven" by minutes saying it was signed, a privileged doc cited, a self-graded checklist. |
| 2 "Make it trustworthy" | 3.3 memo rules | `verification/verify_memo.py` | `01_session1` → `02_session2`: `verify_memo.py` (≈80 lines of pure code, see 3.3). |
| 2 | 3.6 checklist check | `verification/verify_checklist.py` | ≈50 lines: an LLM-as-judge against the ground truth, see 3.2. |
| 2 | 3.4/3.7 `./helper verify RUN --memo/--checklist` | – | Runs the checks post hoc on the Session 1 run. |
| 2 | 3.8 `./helper branch RUN` → resume → `needs_input` → `world/release.py` → resume → `awaiting_signoff` → approve/reject | – | `.env.example` `VERIFICATION=off` → `on`. |

Everything else is identical across the three snapshots: `agent_kit/`, the tools, `verify_claims.py`, `verify_evidence_request.py`, the scripts and the tests. So the whole "verifiable" layer is pre-built *infrastructure*, and the participant writes about 3 small functions.

Exact code added in the Session 1 loop (`solutions/01_session1/agent/legal_agent/loop.py`):
- `drive()` loop: `turn += 1`. On the last turn it appends user "This is your last turn. Call submit_memo now…". It calls `client.responses.create(..., parallel_tool_calls=False, store=False)` and catches `openai.APIError`, which leads to `save_progress(status="paused", error=…)`. Then `messages += response.output`, and it takes the **first** `function_call` only.
  - If there is a call: `tools.run`, append a `function_call_output`, and `status = result.get("status","running")`.
  - If the model answered in text: it appends the nudge "Plain text is not accepted. Call exactly one tool."
  - If the turn limit is reached with status still running, the status becomes `paused`. It calls `save_progress(..., response, status=status)` every turn.
- `run_agent`: reads `objective.md`, calls `new_run(...)`, and starts with `[user(objective)]`.
- `resume_run`: `step = resume(root, run_id)`. If `step["message"]` is None it returns without a model call. Otherwise it appends `step["message"]` to the saved messages and continues with `turns` more.

---

## 2. Architecture

**API.** It uses the **Responses API** (`client.responses.create`), not Chat Completions. Endpoint: `base_url=https://api.meta.ai/v1` via the OpenAI SDK (`openai>=2.0,<3`).
- Models: `muse-spark-1.3` (agent, readers, judges; `MODEL_API_MODEL`) and `sam-3.1` (segmentation; `SAM_MODEL`).
- `./helper setup` checks that both models appear in `client.models.list()`.
- **No reasoning-effort, temperature, max_output_tokens or json_schema settings anywhere.** Structured output is `text={"format":{"type":"json_object"}}` plus "Return only JSON: {...}" in the prompt, with code-side validation and a retry.

**Tool-calling pattern.**
- Strictly **one tool per turn**: `parallel_tool_calls=False`, and the system prompt says "Call exactly one tool per turn. Never answer in plain text".
- Parallelism lives **inside** a tool: `analyze_document` reads up to 4 documents in a `ThreadPoolExecutor`.
- The loop is model-driven. The ground rules forbid hard-coding the tool order: "The model chooses every tool call".

**Context management.**
- `store=False`. The **entire conversation** (`messages` = user turns + `response.output` items + `function_call_output`s) is resent every turn, with `instructions=` set to the system prompt file each turn.
- There is no summarisation or truncation. The context stays small because document text never enters the agent conversation in bulk: `analyze_document` returns *evidence records* (page, quote, claim, interpretation, ambiguity, verified), not raw text.
- The agent keeps its working memory in the **case record**, not in the context.

**Budgets.**
- Turns: 30 default, resume adds 15. On the last turn the model is forced to call `submit_memo`.
- SDK: `max_retries=4`, `timeout=180s`. The SDK retries 429/503.
- Per-item limits: `MAX_FACTS_PER_ITEM=3`, `MAX_CITATIONS_PER_FINDING=3`, `MAX_DOCS_PER_CALL=4`, `MAX_TRIES=3` checklist attempts, `MAX_REFUSALS=3` memos.
- JSON parse retries: `MAX_ATTEMPTS=2` for transcription and analysis.

**Multimodal input** (`agent_kit/document_text.py`). It is **Files API first**, not page PNGs:
1. Upload the original PDF/JPG once: `client.files.create(file=stream, purpose="user_data")`. The `file_id` is cached in `workspace/cache/files.json`, keyed by SHA-256 (with a thread lock).
2. **Transcribe once**: `input_text` (TRANSCRIBE_PROMPT: verbatim, page by page, include tables/handwriting/stamps, `[illegible]`, JSON `{"pages":[{"page","text"}]}`) plus `{"type":"input_file","file_id":…}`. The result is saved to `workspace/cache/text/<sha>.json`. **That transcript is the "source of truth" every quote is checked against.**
3. **Analyse per request**: the prompt includes the verified page text *and* the same `input_file` again. It returns evidence JSON, and each record gets `verified = quote_on_page(quote, page_text)`. Results are cached by `sha256(doc_sha|request)`.
4. Page PNGs (100 dpi grayscale, `pages/<ID>-p<n>.png`, pre-rendered or produced by `pdftoppm`) are used only by `check_signatures`/SAM (`input_image` with a base64 data URL) and by the console.

**Tools** (`agent_kit/tools/`, one file each: `DEFINITION` JSON schema with `additionalProperties:false` plus `run(ctx,args)`).

| Tool | When | Args | Contract |
|---|---|---|---|
| `set_checklist` | always | `items[{id snake_case, question, evidence_needed, needs_signature_check}]` | Validates items. With verification on, runs `verify_checklist` first; refused → `{"error":"checklist refused","feedback"}`; accepted after 3 tries with the score kept. Items that already have facts or requests cannot be dropped. Items added after a failed first draft get `added_after_check=true`. |
| `update_plan` | always | `plan[str]` | Echo only; the plan lives in the conversation. |
| `list_documents` | always | – | `{id, modality pdf/image, pages}` for the inbox. |
| `analyze_document` | always | `document_ids[1..4], request` | Parallel reads; per-doc failure is isolated; flagged docs refused; `mark_read`. |
| `record_fact` | always | `item, document_id, page, quote, claim` | **Refused unless the normalised quote (≥8 chars) is a substring of the cached page transcript**, and also if the doc is flagged, not yet analysed, or the item already has 3 facts. Refusals are logged to `rejected_facts`. The result includes `progress` (open items, next step). |
| `submit_memo` | always | `conclusion, findings[{item, status proven/not_proven/escalated, summary, citations≤3[{document_id,page,quote}]}], gaps` | Off: filed `unverified` → `answered`. On: memo rules → claims check → `awaiting_signoff`, or refused with problems; the 3rd refusal escalates with rule `memo_refused`. |
| `flag_privileged` | verification on | `document_id, reason` | Withdraws that doc's facts (items revert to open), blocks re-reading and citing, attorney reviews. |
| `request_evidence` | verification on | `item, need` | Gated by `verify_evidence_request`; opens request `R<n>` → `needs_input`. |
| `check_signatures` | verification on | `document_id, page, signer, reference_document_id, reference_page` | Reference must be a different page. **PLACEHOLDER returns "consistent".** The intended design: SAM 3.1 boxes ("ink scribble"), then Muse Spark compares both pages ("consistency check, not forgery detection"). Non-consistent verdicts (`inconsistent/unclear/unsigned`) become signature flags. |

`tools.run()` parses arguments and rejects unknown or disabled tools. `NotImplementedError` → `{"error", "status":"paused"}`, which stops the run cleanly when a check isn't built. Any other exception becomes `{"error": msg}` and goes back to the model as an observation, so the model self-corrects.

**Case record** (`agent_kit/case_record.py`). One JSON per run, `workspace/case_records/<run>.json`:
- `checklist{id: {question, evidence_needed, needs_signature_check, status open/proven/escalated, facts[ids], request, added_after_check}}`
- `checklist_checks[]`, `memo_checks[]`, `read_ids[]`, `facts[{id F<n>, item, document_id, page, quote, claim, at}]`
- `rejected_facts[]`, `flags[{kind privileged/signature, document_id, reason, review}]`, `signature_checks[]`, `requests[{id R<n>, item, rule, need, visible_ids, evidence_so_far, status, response}]`, `memo`
- `audit[{at, actor agent/verification/human/runtime, action, detail}]`

Writes are atomic (tmp + replace). It is written only through this module. **Only `record_fact` can move an item to `proven`; only `open_request` can move it to `escalated`.** The model cannot assert status directly.

**Progress and trace** (`agent_kit/progress.py`). `workspace/runs/<run>/progress.json` holds:
- `run_id, verification` (fixed per run), `model, started, status, turn`
- `messages` (SDK objects → `model_dump(mode="json", exclude_none=True)`)
- `turns[{time, status, end, turn, saw, output, input_tokens, output_tokens}]`, `notes`
- plus `instructions.md` and `objective.md` snapshots.

It prints one terminal line per turn ("Turn 7: record_fact → fact F3 recorded · facts 3 · running"). Step mode works through `workspace/control.json`, which the console writes.

Other functions:
- `resume()` is a state machine over `paused | needs_input | awaiting_signoff`, described in 3.5.
- `branch()` replays the conversation up to the first `set_checklist` call into a new run with verification on and **re-executes that call**, so the new checklist check judges the old checklist.

The UI (`ui/ui.py`, stdlib only, 127.0.0.1:8765) builds events from progress plus the case record: a plan/act/observe timeline, the checklist panel with facts and verdicts, handoff and sign-off cards, and metrics (turns, tool calls, tokens, rejected, escalations). Cost is **token counts only; no price conversion**.

---

## 3. Verification design

Principle (HANDBOOK 3.2): **checks sit inside the tools at the moments the agent tries to move forward, not as optional tools.** "A confident model skips [a verify tool]." Every check has one signature: `run_verification(ctx, work) -> {"passed": bool, "feedback": …}`. `ctx` carries `client, root, run_id, case, verification`. The agent sees **only the feedback**, never scores or reference data.

### 3.1 Quote grounding (always on, kit level)
`normalize()`: collapse whitespace, map smart quotes and dashes to ASCII, lowercase. `quote_on_page`: normalised quote of at least 8 characters must be a substring of the normalised cached transcript **for that page**. It is applied:
- at read time (`verified` flag on evidence),
- at `record_fact` (hard refusal),
- at memo time (each citation must equal a recorded fact: same doc + page + normalised quote).

Weak spot: the "truth" is the model's own transcription, so an OCR hallucination becomes ground truth. The quote check proves that the quote is consistent with the transcript, not with the pixels.

### 3.2 `verify_checklist.py` (participant-built; LLM-as-judge against hidden ground truth)
- `load_reference(root)` reads `../ground_truth/<case-folder>.json` (`GROUND_TRUTH_DIR` overrides). If the file is missing, the check passes with `score=None`.
- One Muse Spark call in JSON mode. The prompt contains REFERENCE CHECKLIST (id + question) and AGENT CHECKLIST, and asks for `{"covered":{ref_id: bool}, "feedback": "..."}`.
- **Code computes** `score = covered/len(reference)` and `passed = score >= 1.0`. Unparseable output leaves the marks empty (fail closed on score), with generic fallback feedback.
- The feedback must point to *the kind of question* that is missing and must never quote, paraphrase or count reference items, so the agent can't copy the answer key. The handbook says nothing enforces this automatically; the test only asserts that no ground-truth question string appears in agent requests and that "score" never appears.
- `set_checklist` gives 3 attempts, then accepts the checklist and keeps score and feedback for the attorney.

### 3.3 `verify_memo.py` (participant-built; deterministic rules, no model)
It returns one problem string per violation:
- no checklist → problem;
- each checklist item has a finding (`no finding for X`);
- item status `open` → "neither proven nor escalated: record a fact or call request_evidence";
- a finding marked proven but the item not proven in the case record → "no recorded fact";
- proven with zero citations;
- `needs_signature_check` + proven → there must be a `signature_checks` entry on a **cited** document, and every such verdict must be `consistent`. Otherwise: "mark the item not proven and name it as a gap";
- every citation: the doc is not flagged privileged, and it matches a recorded fact (doc, page, normalised quote);
- any open evidence request → problem.

### 3.4 `verify_claims.py` (pre-built; entailment judge)
- One Muse Spark call per memo, only after the rules pass. Input: proven findings with citations as `{item, claim: summary, quotes[]}`. Output JSON: `{"unsupported":[{"item","reason"}]}`.
- **It fails open**: unparseable judgement → passed. The comment reads "an unreadable judgement never blocks the memo".

### 3.5 Escalation and human-in-the-loop (`ESCALATION_RULES.md`, `verify_evidence_request.py`, `progress.resume`)
- `request_evidence` is allowed only if the item exists, is not already proven, and **every visible non-flagged document has been read** (`read_ids`). This stops lazy escalation.
- An allowed request opens `R<n>` with rule `missing_evidence`, and the status becomes `needs_input`. **No model calls happen while waiting.**
- Resume after `needs_input`: it proceeds only if new documents appeared in the inbox (compared with the request's `visible_ids`) or a reviewer answered. Otherwise it returns "nothing new…" with no model call. The message to the agent names the released document IDs.
- 3 refused memos → `escalate(item=first open item, rule="memo_refused")`. A human sends one line of guidance.
- A memo that passes → `awaiting_signoff`. `./helper review RUN --approve` makes resume set `done` with no model call. `--reject --notes` sends the notes back, and a revised memo goes through all checks again. At review, flags are marked `confirmed`, or set per document via `flag_decisions`.
- The handoff card shows the blocked item, the rule fired, documents read, the request, and the verified facts so far (`evidence_so_far`).

### 3.6 Ground truth and scoring
- There is only *coverage* ground truth (checklist questions). It holds **no expected verdict and no expected facts/citations**, and the memo is never scored against an answer key.
- The "eval" is therefore: coverage score, plus counts of refusals (rule and claim), escalations, rejected facts and flags in the console, plus human sign-off.
- `./helper verify RUN --memo|--checklist` runs the same functions **post hoc on a finished run** without changing it, and appends results to `workspace/runs/<run>/verification.json`. `./helper branch` gives counterfactual replay from a checkpoint.

### 3.7 Tests (offline fake model)
- `tests/fake_model.py`: `Scripted` builds a **real `OpenAI` client** with `httpx.Client(transport=ScriptedTransport)`, `max_retries=0`, and answers `/responses`, `/files` and `/models` locally.
- `ScriptedModel` routes requests by content:
  - requests with `tools` get the next scripted tool call;
  - "Transcribe document" gets the supplied transcripts;
  - "VERIFIED PAGE TEXT" gets evidence quoting the first long line;
  - "REFERENCE CHECKLIST" gets coverage by id substring;
  - "CLAIMS TO CHECK" gets a configurable unsupported list;
  - SAM-model requests get recorded box strings.
- A `Refused` exception produces HTTP 400, which simulates an API failure. Every call is recorded for assertions.
- `support.py` builds a tiny on-disk case in a tempdir: 4 initial docs + 2 follow-up, a 6-item ground truth that mirrors the real one, and a `release()`.
- Suites:
  - `test_agent.py` (11 loop-contract tests: tool order, error fed back, instructions sent verbatim, progress per turn, plain-text nudge, turn-limit pause/resume, last-turn memo, API failure → paused → resume).
  - `test_kit.py` (≈20 tests).
  - `test_environment.py` (preflight/reset).
  - `test_verification.py` (skipped unless `VERIFICATION=on`): `ChecklistCheckTest`, `MemoRulesTest`, an end-to-end `VerifiedRunTest` (refuse → escalate → release → resume → claims → sign-off → done; reject loop; 3 refusals → person; flagged doc unreadable), and `ContinueFromSessionOneTest` (verify + branch).
- **The tests are the spec handed to Muse Code** ("the tests are the spec"). Run with `./helper test [--verification]`, which is `python -m unittest discover -s tests` after a preflight.

---

## 4. Meta API usage patterns worth copying

Client (`agent_kit/client.py`):
```python
from openai import OpenAI
client = OpenAI(api_key=os.environ["MODEL_API_KEY"],
                base_url=os.environ.get("MODEL_API_BASE_URL") or "https://api.meta.ai/v1",
                max_retries=4, timeout=180)
models = {m.id for m in client.models.list().data}   # preflight: muse-spark-1.3, sam-3.1
```

Agent turn (Responses API, stateless, one tool):
```python
response = client.responses.create(
    model="muse-spark-1.3", instructions=system_md, input=messages,
    tools=[{"type":"function","name":..., "description":..., "parameters":{...,"additionalProperties":False}}],
    parallel_tool_calls=False, store=False)
messages += response.output
call = next((i for i in response.output if i.type == "function_call"), None)
messages.append({"type":"function_call_output","call_id":call.call_id,"output":json.dumps(result)})
```

Files API + document input + JSON mode:
```python
file_id = client.files.create(file=open(path,"rb"), purpose="user_data").id
r = client.responses.create(model="muse-spark-1.3",
      input=[{"role":"user","content":[{"type":"input_text","text":prompt},
                                       {"type":"input_file","file_id":file_id}]}],
      text={"format":{"type":"json_object"}})
data = json.loads(r.output_text)       # validate; on failure retry once with "Your previous output was invalid: {err}"
```

Image input + SAM 3.1 segmentation (special-token output):
```python
url = "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()
r = client.responses.create(model="sam-3.1", input=[{"role":"user","content":[
        {"type":"input_text","text":"ink scribble"},          # "signature" does NOT match on scans
        {"type":"input_image","image_url":url}]}])
BOX = re.compile(r"(\d+)<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")
boxes = [m.groups() for m in BOX.finditer(r.output_text or "")]   # empty text = no match
```

Error handling: rely on the SDK's retries (429/503 honour Retry-After). Catch `openai.APIError` around the turn → persist `status="paused"` with the error → resumable. Inside tools, per-document `try/except (DocumentError, openai.APIError, OSError, ValueError)` returns `{"evidence":[], "note":"error: …"}` so one failure doesn't sink a batch.

Cost tracking: per turn, `response.usage.input_tokens` and `output_tokens` are stored in `progress.turns[]`. The UI sums them. Only agent turns are logged; the reader, transcription, judge and SAM calls inside tools are **not** counted, which is a gap.

Not demonstrated: reasoning effort, `json_schema` strict structured outputs, streaming, Chat Completions, audio or video input. Do not assume the Meta API supports any of these from this repo.

---

## 5. Muse Code usage implied

- Install from `https://dev.meta.ai/docs/muse-code`. Run `muse` from `agent/`, sign in with "Paste an API key" (the same Meta key), and trust the folder.
- The workspace boundary is enforced by folder layout: the ground truth, the withheld evidence and the solutions sit in sibling folders.
- **The ground-rules prompt (HANDBOOK 1.7)** is pasted at every session start: build only what is asked; edit only `legal_agent/` and `verification/`; `agent_kit/` is read-only; no hard-coded tool order or case specifics; don't run the agent or tests unless asked; never open `.env` or print keys; every report lists files changed, commands run and limitations.
- The workflow is **plan prompt, then build prompt**. The spec lives in docstrings plus tests (`./helper test --verification`), and the scope check is `git status` showing only the expected files. Undo with `git checkout -- verification/` (never `legal_agent/`, which is uncommitted).
- `./helper` is a single bash entry point: `setup | test [--verification] | run [--turns N] [--resume ID] | verify ID --memo|--checklist | branch ID | review ID --approve|--reject --notes|--answer R1 --notes | reset [--clear-runs] | describe`. It sources `.env`, uses `.venv/bin/python`, and `describe` emits JSON for the console (including a `built` map via a "NotImplementedError(" probe).
- Catch-up: `rsync -a --delete --exclude .env --exclude .venv --exclude workspace solutions/0X/agent/ agent/`.

---

## 6. Lessons for our project

### Confirms our plans
- **The evidence contract is the core.** Their atom is `{document_id, page, quote, claim}`, checked mechanically against a cached source of truth. Ours (Callback v2) maps to `{source: call_audio|screen_rec|idp_log, locator: t_start–t_end / frame_ts / log_row_id, excerpt, claim}`, with the excerpt checked against the diarized transcript segment, frame OCR, or the raw log row. This confirms our "no claim without a locator" plan, and that status changes (`proven`) must happen *only* through the evidence-recording tool, never by model assertion.
- **Verifiers inside the gates, not optional tools.** This validates our two-key gate. Key 1 is deterministic rules (verify_memo-style). Key 2 is an LLM entailment judge (verify_claims-style). Both run inside `submit_verdict`, so the agent cannot bypass them.
- **Escalation with preconditions.** The "read everything visible before escalating" rule maps to ours: ingest all call segments, recording windows and identity-log rows before requesting human or extra evidence. Plus resume without model calls while blocked, release-and-resume, and a 3-strikes escalation to a person.
- **Hidden ground truth plus feedback that doesn't leak.** This matches our eval-separation plan. Keep labels in a folder the agent and coding agent never see.
- **Replay and branch.** `progress.json` (the full Responses item list) + `branch()` from a checkpoint + post hoc `verify` on old runs equals our replay story. Copy it almost verbatim.
- **Fake-model offline tests** via an `httpx` transport behind the real `OpenAI` client. Copy `tests/fake_model.py` wholesale and route our audio, vision and judge prompts by marker strings.
- **One tool per turn, parallelism inside tools** (bounded `ThreadPoolExecutor`, per-item error isolation, SHA-keyed caching of uploads, transcripts and analyses). Directly reusable for per-segment or per-frame analysis.

### Contradicts or warns
- **The workshop is single-agent.** "Multi-agent" here means *verifier calls inside tools*, not separate orchestrated agents. Our multi-agent orchestration (diarizer/transcriber, screen-grounder, log analyst, verifier, adjudicator) goes beyond it. Judges may prefer this simpler, auditable pattern, so frame our sub-agents as tools with contracts and gates in the same style.
- **Ground truth here is coverage-only, and there is no accuracy scoring.** Our plan (eval vs labelled ground truth, calibrated thresholds) needs more: per-case expected verdicts and expected evidence locators, with scoring on precision/recall of findings and calibration (Brier/ECE) of the gate's confidence. Their pattern lacks it, so it is our differentiator, but build it ourselves.
- **Their judge fails open** (`verify_claims` passes on an unparseable answer). For a fraud/vishing "two-key" gate we should **fail closed**: an unparseable or uncertain judgement means escalate to a human.
- **The signature check is a placeholder** that always says "consistent", even though the case plants a mismatched signature. Meta did not show working visual-comparison verification. A real SAM-plus-Muse comparison (screen-recording grounding: boxes on the frame, then a second-model check) would be a visible step beyond the reference repo. Note the SAM prompt quirk ("ink scribble", not "signature"): **test SAM prompts empirically** for UI elements in screen recordings.
- **Truth equals the model's own transcription.** For audio, a diarized ASR transcript plays the same role. Store it once, hash-keyed, and treat it as the checkable source. Disclose that it is model-derived, and spot-check the ASR with a second pass or confidence scores.
- **Media is fed via the Files API (`input_file`)** for PDF/JPG plus `input_image` data URLs. There is **no audio or video example**. We must verify early, against the live API, whether Muse accepts audio files or video. Otherwise pre-process: run ASR and diarization elsewhere, sample keyframes to PNG, and send `input_image`.
- **No reasoning-effort or cost accounting in the reference.** Add per-call usage logging for *every* model call, including those inside tools, plus a $ estimate. This makes our "saves money" claim quantitative.

### Concrete files to lift
- `agent_kit/progress.py`: run persistence, turn ledger, resume state machine, branch.
- `agent_kit/case_record.py`: append-audited record, status transitions only via tools, flags and requests, refusal log.
- `agent_kit/tools/__init__.py`: the `DEFINITION` + `run(ctx,args)` registry, error-as-observation, and `NotImplementedError` → paused.
- `agent_kit/document_text.py`: `normalize`/`quote_on_page`, Files API upload cache, transcribe-once.
- `verification/verify_memo.py`, `verify_claims.py`, `verify_evidence_request.py`: templates for our deterministic gate, entailment judge (switch to fail-closed), and escalation precondition.
- `tests/fake_model.py`, `tests/support.py`: offline harness.
- `scripts/verify.py`, `scripts/branch.py`, `scripts/review.py`, `helper`: ops surface and human review CLI.
- `legal_agent/system_instructions.md`: playbook structure (checklist → plan → investigate → answer; judgement; when stuck; rules). Its "always include a counterevidence item" maps to our "benign explanation" item: a legitimate reset request, or a claimant-authorised payment in Claim Clock.

### For Claim Clock (fallback)
The legal pattern transfers almost one-to-one: screenshots and chats map to documents (Files API / `input_image`); "authorised push payment criteria" map to the checklist and ground truth; reimbursement decisions map to the memo with findings and citations; escalation means requesting bank or claimant evidence; sign-off is the claims handler. The risk is lower than Callback because the modalities are images, which this repo demonstrates working.
