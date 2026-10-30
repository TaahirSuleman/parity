# 14 — Build playbook: Meta's verifiable-agent architecture, practices and templates

**Purpose:** the reference to open when the architecture and development phase starts. It does not depend on which idea we choose; section 8 maps it onto Callback v2 and Claim Clock.

**Sources:**
- the Agents 101 transcript (doc 11) and the Agents 102 transcript (doc 13);
- `meta-models/legal-agent-workshop` at commit `2a8efc8`, read first-hand: HANDBOOK, VERIFICATION.md, ESCALATION_RULES.md, `agent_kit/`, `verification/`, and the `solutions/01_session1` and `02_session2` diffs;
- docs 12 and 12a (Session 1 learnings and the repo analysis);
- doc 03 (tooling reference) for the Muse Code features not shown in the workshops.

**Tags:**
- **[S1]**, **[S2]**: said in Session 1 or 2, with the timestamp.
- **[repo]**: in the code or the handbook.
- **[inferred]**: my reading.
- **[decide]**: a choice we still have to make.

---

## 1. The architecture in one picture

```
                ┌───────────────────────── Console (stdlib web UI) ─────────────────────────┐
                │ plan/act/observe timeline · checklist panel · memo · handoff · sign-off    │
                └───────────────▲──────────────────────────────────────────────▲─────────────┘
                                │ reads                                         │ person acts
objective.md ──► LOOP (≈85 lines, yours) ──► model: Responses API, store=False, │ (release / reply /
playbook.md      one tool per turn             whole item list resent           │  approve / reject)
                 │                                                               │
                 ▼                                                               │
            TOOLS (strict schemas, error = observation, unknown tool = refused)  │
                 │   set_checklist ──► [checklist check: LLM judge vs hidden ground truth]
                 │   record_fact   ──► [quote-on-page check: code]               │
                 │   request_evidence ► [escalation precondition: code] ──► needs_input
                 │   submit_memo   ──► [memo rules: code] ─► [claims judge: LLM] ─► awaiting_signoff
                 ▼                                                               │
            CASE RECORD (only tools write; audited; status changes only via tools)
            PROGRESS (every turn saved: messages, tokens, status) ── resume() state machine
                                                                  └─ branch() counterfactual replay
```

**The idea in one line** (HANDBOOK 3.9) [repo]: *"The model does the reasoning. The checks, which sit outside it at the moments that matter, decide whether the work is good enough to move on."*

---

## 2. Twelve design principles

| # | Principle | Evidence |
|---|---|---|
| P1 | **The model chooses; the code acts and keeps the record.** Never hard-code which tool runs when; keep anything case-specific out of the code. | Handbook 2.3 and the 1.7 ground rules [repo] |
| P2 | **Mandatory checks live *inside* the tools that move the work forward, never as optional tools.** "Verification should not be added as a choice to the agent… which the agent cannot skip, the agent cannot change." The agent may run extra checks of its own, but the mandatory ones are built in. | [S2 07:57–09:00]; Handbook 3.2 |
| P3 | **Layer the checks: deterministic first, then an LLM judge, then a human.** Code checks completeness and format; the judge checks correctness; a domain expert signs off. | [S2 10:05–11:39, 28:07] |
| P4 | **Use deterministic checks wherever the property can be computed.** "You don't want the agent to output a number… that is a very easy deterministic check." Keep a balance between rules and judges. | [S2 16:56–17:29] |
| P5 | **Verify intermediate milestones, not just the end.** The checklist is checked as it is set: the memo is only as good as its checklist. Milestone checks are also the answer to delayed outcomes and credit assignment. | [S2 12:12, 25:26–26:30]; Handbook 3.5 |
| P6 | **Checks feed back into a loop with a retry cap, then a human.** Three tries is the workshop default. | [S2 14:48–16:24] |
| P7 | **Feedback must not leak the answer key.** Point to *what kind of thing* is missing; never quote, paraphrase or count the ground truth. Scores go to the human and the console, never to the agent. | Handbook 3.3 and 3.6 [repo] |
| P8 | **Constrain the action space in the harness.** Offer only the allowlisted tools and discard anything else the model asks for. This is also the answer to "swap the document after approval". | [S2 18:31–19:36]; `tools.run` returns `unknown tool` [repo] |
| P9 | **Place checks for the speed–accuracy trade-off.** The checks moved the run from about 20 turns to 30. Block on a check when later steps depend on its output; defer non-critical, independent checks to a batch run. | [S2 20:40–21:42, 28:39, 29:46–30:17] |
| P10 | **Thresholds are domain decisions.** Legal, finance and healthcare need thresholds "right up there". The demo's 80% "had no thinking behind it"; experts set the real value. | [S2 23:50–24:55] |
| P11 | **Escalation must be earned, and it costs nothing while waiting.** The agent may ask a person only after reading every visible document. A blocked run makes no model calls; it resumes only on new evidence or a reply. | ESCALATION_RULES.md; `verify_evidence_request.py` [repo] |
| P12 | **The agent cannot assert state.** Only `record_fact` (quote checked) can mark an item proven; only a gated request can mark it escalated. Until a checklist exists, the agent cannot record, escalate or file. | Handbook 3.2; `case_record.py` [repo] |

**A gap in the reference that we should close** [inferred]: the evidence-request precondition checks *effort* (everything was read). It does not check *specificity*, beyond `open_request` refusing an empty `need`.

---

## 3. The verification layer: contracts and templates

### 3.1 One contract for every check [repo]
```python
run_verification(ctx, work) -> {"passed": bool, "feedback": str | [str], ...}
# ctx: client (OpenAI SDK → api.meta.ai), root, run_id, case (the case record), verification flag
```
- There is one file per check in `verification/`. Tools import them at fixed points.
- `./helper verify RUN --memo|--checklist` runs the same functions **post hoc** on a saved run without changing it.
- A check that is not built yet raises `NotImplementedError`, so the run pauses cleanly instead of silently passing.

### 3.2 The checkpoints, and what each one costs [repo]

| Gate (tool) | Check | Kind | On failure | Cap |
|---|---|---|---|---|
| `set_checklist` | Coverage of the hidden ground truth | 1 LLM call (judge); **code computes the score** | Refused with non-leaking feedback | 3 tries, then **accepted**, with score and feedback kept for the attorney (*not* escalated, despite the live wording [S2 21:42]) |
| `record_fact` | Normalised quote of at least 8 characters appears on that page of the cached transcript; item exists; document not flagged; at most 3 facts per item | Code | Refused, logged in `rejected_facts` | — |
| `analyze_document` | A flagged (privileged) document cannot be read again | Code | Refused | — |
| `request_evidence` | Item exists, is not proven, and every visible unflagged document has been read | Code | Refused with the reason | — |
| `submit_memo` (key 1) | Memo rules (list below) | Code, no model | Refused with a list of problems | 3 refused memos → `memo_refused` escalation to a person |
| `submit_memo` (key 2) | Each proven finding is supported by its quotes | 1 LLM call per memo | Refused with the unsupported claims | (same counter) |
| After both keys | Attorney sign-off | Human | Notes go back to the agent; the revised memo is checked again | — |

### 3.3 The memo rules (Session 2 solution, about 80 lines, no model) [repo]
1. A checklist exists.
2. Every checklist item has a finding.
3. No item is still `open`. Each must be proven or escalated ("record a fact or call request_evidence").
4. A finding marked proven needs an item proven in the case record ("no recorded fact").
5. A finding marked proven needs at least one citation.
6. A proven signature item needs a `check_signatures` entry on a **cited** document, and every such verdict must be `consistent`. Otherwise: "mark the item not proven and name it as a gap".
7. Every citation is on an unflagged document and matches a recorded fact exactly (document, page, normalised quote).
8. No evidence request is still open.

**The pattern** [inferred]: each problem string is written as an **instruction the agent can act on**, not a diagnostic code. That is why the agent converged on its third memo in the live run [S2 27:04–27:37].

### 3.4 The LLM-as-judge pattern (checklist check)
```python
PROMPT = """You review an investigation checklist against a REFERENCE CHECKLIST that the agent must not see.
REFERENCE CHECKLIST: {reference}      AGENT CHECKLIST: {agent}
1. For each reference item, decide whether some agent item asks the same thing, even if worded differently.
2. Write feedback ... Point to the direction only. Do not quote, paraphrase, or count the reference items.
Answer only with JSON: {"covered": {"<reference id>": true|false}, "feedback": "..."}"""
r = client.responses.create(model=model(), input=prompt, text={"format": {"type": "json_object"}})
marks = json.loads(r.output_text).get("covered") or {}          # unparseable → {} → score 0 (fails closed)
score = sum(marks.get(x["id"]) is True for x in reference) / len(reference)
passed = score >= THRESHOLD                                      # repo solution: 1.0; live demo: 0.8
```
Three practices to adopt (as ideas, in our own code) [repo + S2]:
- **The model marks items; code does the arithmetic** (never ask the model for the score).
- **`is True` is a strict boolean test.** The live demo failed first because the model returned a list where a dictionary of booleans was expected; Muse Code fixed the parsing [S2 15:18, 17:59]. Validate the shape and treat anything else as not covered.
- **Make the threshold a named constant set by the domain** (P10).

**Live evidence that the feedback works** [S2 21:42–22:48]: coverage went from 50% to 67% (refused) to 83% (accepted at the 80% threshold). That is 3/6, then 4/6, then 5/6 of the six ground-truth items. **This before/after convergence is a strong demo beat for us.**

### 3.5 The claims judge (key 2)
- One call per memo, run only after the rules pass, so judge tokens are not spent on structurally broken memos.
- Input: proven findings, each as `{item, claim, quotes[]}`. Output: `{"unsupported":[{item, reason}]}`.
- **The reference fails *open* on an unparseable answer.** For security or finance gates we flip this to **fail closed**: an unparseable or unsure judgement goes to a human (doc 12 §4). [decide: confirm per gate]

---

## 4. Human-in-the-loop as a state machine [repo]

```
running ──request_evidence (allowed)──► needs_input ──(new docs released | reviewer reply)──► running
running ──3rd memo refusal────────────► needs_input (rule memo_refused) ──(one line of guidance)──► running
running ──memo passes both keys────────► awaiting_signoff ──approve──► done (no model call)
                                                          └─reject + notes──► running (re-checked)
running ──turn limit / API failure────► paused ──resume (+15 turns)──► running
```
- **The handoff card shows a reviewer five things:** the blocked item, the rule that fired, the documents already read, the one specific request, and the verified facts so far.
- **`resume()` refuses** with "nothing new…" when nothing changed, and makes no model call.
- **`branch(RUN)`** replays a finished run's conversation up to its first `set_checklist`, starts a *new* run with verification on, and re-runs that call so the new check judges the old checklist. The original run is untouched. This is how the workshop shows before and after on the same trajectory (Handbook 3.8–3.9).
- **The sign-off review** also confirms or rejects each flag (privileged, signature) per document.

---

## 5. Meta API usage: what's proven to work

The full code is in doc 12a §4. The short list [repo]:
- **Client:** OpenAI SDK, `base_url=https://api.meta.ai/v1`, `max_retries=4`, `timeout=180`. Preflight checks the model IDs via `models.list()`.
- **Agent turn:** the Responses API with `store=False`. The whole item list is resent, with `instructions=` set each turn. `parallel_tool_calls=False`; the first `function_call` is executed. If the model answers in plain text, it gets the nudge "Plain text is not accepted"; on the last turn it is forced to file the memo.
- **Judges and readers:** `text={"format":{"type":"json_object"}}` plus the JSON shape in the prompt, with validation in code and one retry. The reference does **not** use `json_schema` strict, reasoning effort, streaming, audio or video.
- **Files API** (`purpose="user_data"`) carries PDFs and JPGs as `input_file`. Each document is transcribed once, cached by SHA-256, and that transcript is the source of truth for quotes.
- **SAM 3.1** takes an `input_image` data URL and returns box special tokens parsed by regex. Concept prompts must be tested empirically: "ink scribble", not "signature".
- **Only agent-turn tokens are logged.** We should log every call, including judges and readers, with a dollar estimate.

**Session 1 facts worth keeping:**
- Muse Code shares the API key's rate limits [S1 09:11].
- The API is fully OpenAI-SDK compatible: "just switch the API host" [S1 23:09].
- Custom MCP servers and skills are supported [S1 23:47].

---

## 6. Development workflow with Muse Code

| Practice | How | Source |
|---|---|---|
| **Ground rules, first message, every session** | Build only what's asked, then stop and report; edit only the named folders; the kit is read-only; never hard-code tool order or case specifics; don't run the agent or tests unless asked; never open `.env` or print keys; every report lists files changed, commands run and limitations. The rules live only in the conversation, so re-paste them after any restart. | Handbook 1.7 [repo]; [S2 06:55] |
| **Read-first prompt** | "Do not change files. Read VERIFICATION.md and the docstrings in X. In five bullets, say what each check receives, what it returns, and who sees the result." Then check the answer against the spec before any code. | Handbook 3.3 |
| **Plan, then build** | "Propose a brief plan… no code yet." Fix the plan in one sentence; "code takes much longer to untangle". | Handbook 2.4; [S1 13:00] |
| **Spec = docstrings + tests** | Each function's docstring is its contract; `./helper test --verification` is the acceptance test. Tests use a **fake model**: a real OpenAI client over a scripted `httpx` transport, so CI is offline and free. | Handbook 3.2; doc 12a §3.7 |
| **Scope check** | `git status` shows only the expected files changed. Undo with `git checkout -- <folder>`, but never on uncommitted work. | Handbook 2.4, 3.3 |
| **Debug by pasting the error** | Copy the console error back to Muse Code; it fixed the judge-parsing bug live. | [S2 15:18, 17:59] |
| **Builder plus reviewer** | Two Muse Code sessions: one can write code, the other can only review and cannot change anything. | [S2 30:49] |
| **Course-correct by asking** | "Just ask it to revert." The harness holds state; the model is stateless. | [S1 29:14] |
| **Separate the workspace from the answer key** | Start Muse Code in `agent/`. Ground truth, withheld evidence and solutions sit in sibling folders outside its workspace, so neither the coding agent nor the runtime agent can see them. | Handbook 1.6, 3.6 |
| Muse Code features worth trying | `/plan`, `/grilling`, `subagent_spawn` with worktree isolation, `/goal` with a completion audit, deterministic replay fixtures with a CI replay gate, immutable `.agents/AGENTS.md`. Not shown in the workshops. | doc 03 (cookbook) |

**[decide]** Commit a `GROUND_RULES.md` and a `REVIEWER_RULES.md` to our repo on D0. Run builder and reviewer sessions in parallel; this costs extra tokens on the same key, so use a `-contributor` model for the reviewer where possible.

---

## 7. What this means for the demo and the submission [inferred]

1. **Show the before and after on one trajectory.** Unverified run, then `branch` with verification on: checklist refused (coverage 50%, then 83%), memo refused twice with the rule that caught it each time, handoff, sign-off. This is the workshop's own 3.9 comparison, and judges from Meta will recognise it.
2. **Put the refusals on screen.** The red rows, each naming its check, are the evidence that the checks don't trust the model. A run with no refusals proves nothing.
3. **Report the cost of verification honestly.** For example: "+50% turns (20 → 30) buys N caught errors." This uses Yash's own framing.
4. **Use Meta's vocabulary.** Checks *inside the tools*; *deterministic → LLM-as-judge → human*; *milestone verification*; *escalation preconditions*; *no model calls while waiting*; *a ground truth the agent can't see*.
5. **Go beyond the reference where it stops** (doc 12 §4):
   - a real multimodal verifier where theirs is a placeholder;
   - fail-closed judges;
   - accuracy ground truth (expected verdicts and locators), not just coverage;
   - cost per call.

---

## 8. Mapping template: fill this in for whichever idea wins

| Workshop concept | Callback v2 | Claim Clock |
|---|---|---|
| Case / `objective.md` | One reset call: "Was this reset social engineering, and is the account at risk?" | One APP-scam claim: "Is it reimbursable under the PSR rules, and how much?" |
| Documents in the inbox | Call audio (diarized transcript), keyframes from the agent's screen recording, identity-provider log rows | Claimant statement, chat and SMS screenshots, bank statements, payment records |
| Withheld evidence (`world/`) | Later log rows; callback-to-number-on-file result; the employee's confirmation | Receiving-bank response; police reference; vulnerability evidence |
| Checklist (ground truth = coverage) | Caller identity asserted vs verified; procedure step skipped?; pretext signals; post-reset anomalies; **benign explanation** (counterevidence item) | Authorised push payment?; consumer standard of caution / gross negligence; vulnerability; amount and cap; **claimant-side explanation** |
| `record_fact` quote check | Excerpt must match the diarized segment `t_start–t_end`, the OCR of the frame plus grounding box, or the raw log row | Quote must be on the page of the uploaded screenshot or statement (repo pattern as is) |
| Signature check analogue | **Screen-procedure check:** Spark grounds whether the verification step was performed on the frame. A real multimodal verifier. | Document authenticity or consistency (e.g. statement totals), deterministic where possible |
| Privileged-document analogue | Calls containing an employee's personal data outside scope → excluded from citation | Third-party personal data → excluded |
| Memo rules (key 1) | Every item settled; every citation matches a recorded finding; containment requires corroboration from two of the three channels; no open request | Every criterion settled; amount arithmetic computed by code (the £7,050 split); caps applied by code |
| Claims judge (key 2) | Fail closed | Fail closed |
| Escalation precondition | Every segment, keyframe window and log row in scope ingested | Every document read; mandatory evidence requested from the bank |
| Sign-off | IAM lead approves the L3 session revoke (sandbox API); the action runs **after** approval | Claims handler approves the reimbursement decision |
| Threshold (P10) | High: an action on an account follows; [decide] coverage 1.0 | High: a financial decision; coverage 1.0 |
| Block vs defer (P9) | Block: anything feeding the revoke decision. Defer: overlay polish, campaign linkage across calls | Block: eligibility and amount. Defer: trend reporting |

---

## 9. Suggested build order (mirrors the workshop, de-risks the demo)

1. **Kit (D0–D1):** `progress.py`, `case_record.py`, tools registry, console, fake-model test harness. **Decision (29 Oct): never copy workshop code.** Learn the patterns, write our own implementation with our own naming and data model. This is for differentiation, and because the repo has no LICENSE file (G0).
2. **Loop (D1):** about 85 lines, built with Muse Code using plan, then build. First unverified run end to end on one golden case.
3. **Deterministic gates (D2):** quote/locator check in `record_finding`; memo rules; escalation precondition.
4. **Judges (D2–D3):** checklist coverage and claims, both fail closed. Hidden labels sit outside the agent folder.
5. **HITL states plus branch/replay (D3):** needs_input, awaiting_signoff, then the action after approval.
6. **The real multimodal verifier (D3–D4):** our step beyond Meta's placeholder.
7. **Eval and ablations (D4–D5):** coverage plus accuracy against labels; per-call cost; turns with verification on vs off.

---

## 10. Open questions for office hours (carried over from doc 12, still unanswered)

1. Does the Responses API accept **audio or video** `input_file` for Spark 1.3, or is Voice Transcribe the only audio path?
2. What is the licence for reusing `legal-agent-workshop` code (no LICENSE file in the repo)?
3. What are the recommended SAM 3.1 concept prompts for UI elements in screen recordings?
4. Is `json_schema` strict structured output supported on the Responses API? The workshop deliberately used `json_object`.
5. Can a separate key or the `-contributor` tier be used for Muse Code, so it doesn't consume the agent's rate limit?
