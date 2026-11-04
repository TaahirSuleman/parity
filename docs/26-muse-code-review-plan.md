# 26 — Muse Code as the reviewer: what judging rewards, how to run it review-only, and the prompts

**Status:** plan, Wed 4 Nov 2026, afternoon SAST. Review-only: Muse Code reads and reports; nothing it suggests is actioned until the builder has read the suggestion. Submission is due 21:00 ET (Thu 5 Nov 01:00 SAST); the builder submits by 18:00 ET.

## 1. Does Muse Code matter to judging? What the documents say

| Source | What it says | Weight for us |
|---|---|---|
| Constitution I.2, Stage One | Pass/fail requires the Model API or open weights *inside the product*. "Using Muse Code only as a dev tool does not by itself satisfy this." | None: Parity passes Stage One on the Model API alone. |
| Constitution II, constraint 5 | Projects "must incorporate Meta's models", and the list names Muse Code among them. | Muse Code counts as a Meta product, not as a runtime model. |
| Rubric, "Use of Meta AI Tooling 25%: beyond basic integration" | Scored by Meta judges on video, README and product. | Muse Code use is one input to this score, behind the runtime integration (computer use, grounding, Voice). |
| Event page | "code faster with Muse Code coding agent" is the one developer-tool sentence in the pitch. | Meta wants to see it used; the form asks about it directly (below). |
| Constitution VI.5 ladder, rung 2 | `muse serve` / SDK sessions as the product's orchestration substrate is the "surprised even us" angle. | Not taken (D9: one agent, code orchestrates). Do not retrofit now. |
| Doc 12 §2 and §6 (workshop) | Meta's own practice: Spark 1.3 at effort `max`; ground rules pasted at every session start; plan then build; a **builder session and a review-only session**; `git status` as the scope check; never open `.env`; "just ask it to revert". | The review-only session is the pattern we adopt wholesale. |
| Submission form (read live on 4 Nov in the builder's browser) | Essay 7 "Describe your use of Meta products to build the submitted project" (Muse Code belongs here); a 0–5 "How likely are you to recommend Muse Code"; an obstacle question with three Muse Code options; "When your team chooses an AI model or coding tool, what matters most?" | The only place Muse Code is asked about by name is the form. Honest, specific sentences in essay 7 are what it buys. |

**Conclusion.** Muse Code is not a gate and not a large share of the score. It is a credible, cheap addition to essay 7 and to the Tooling score if the use is real and specific, and it is a genuinely useful second pair of eyes on the stack in the last hours. Overclaiming it (for example as the build harness, which it was not) would cost more than it earns: constraint 3 makes "clearly identify what was created and how" a disqualification matter, and the form's own questions assume honest answers.

**Usage visibility.** Nothing in the participant guide, the rules or the kickoff says judges see a project's API usage. Muse Code uses the same API key and the same billing page as the product, so the builder's own billing page is the record. Treat the form's self-report as the only channel judges read, and keep an exported session log as evidence we can cite.

## 2. Which model, which effort, which plan

- **Model: `muse-spark-1.3` (standard tier) at effort `max`** for every review session. This is Meta's own default for Muse Code in the workshop and the strongest reasoning tier on the key. The contributor tier is for the product's runtime budget, not for a reviewer whose value is depth.
- **Muse Wonder 1.0** only for the final cold read of the submission package (prompt R6) if the plan tier allows it; it was measured on our judge task at the same agreement and 2.3× the cost, so it is a second opinion, not a default.
- **Rate limits are shared with the product's key.** The model-sweep session is running eval rows on that key this afternoon, and the verifier session will run one purchase re-record. Run Muse Code reviews one at a time and accept slower turns; never run a review during the purchase re-record (a 429 on the agent's turn fails the recording).

## 3. Review-only, enforced

1. **A clean worktree for the reviewer**: `git worktree add ../parity-review main` and start `muse` there, so a slip cannot touch the working checkout. `git -C ../parity-review status` after every session must print nothing; if it prints anything, `git checkout -- .` and record it.
2. **`REVIEWER_RULES.md` pasted as the first message of every session** (the text is in §4; re-paste after any restart, as the workshop does).
3. **Headless for the structured passes**: `muse exec "<prompt>" --json --output-schema review.schema.json --max-model-steps 60` returns findings as JSON (file, line, severity, claim, evidence, suggested change) that go into `docs/muse-code/R<n>.json`; the interactive session is for the conversational passes (R0, R5, R6).
4. **Export every session** with `muse export --redacted` into `docs/muse-code/` (redacted so no key or page content leaks); that folder is the evidence behind essay 7 and the one-line Muse Code entry in `HACKATHON_SCOPE.md`.
5. **Never**: open `.env*`, run the eval or a Live run, edit anything, or push. The reviewer may run `pytest -q` and `npm test` read-only if a prompt says so.

## 4. Session preamble (paste first, every session)

```
REVIEWER RULES (Parity, Meta Global AI Developer Hackathon, review-only session)
You are reviewing, not building. Do not create, edit, move or delete any file. Do not run the product, the eval, Playwright or any network call. Do not open or print any .env file or any key. If a step would need any of those, stop and say so.
Read in this order before answering: CLAUDE.md, README.md, HACKATHON_SCOPE.md, docs/18-decision-and-development-plan.md, docs/19-design-spec.md, docs/14-build-playbook-verifiable-agents.md, docs/17-validation-results.md, eval/results/latest.md, then the code the prompt names.
Every claim you make cites file:line or a document section. Distinguish "I verified in code" from "I infer". Rank findings by effect on a judge or a user, not by how easy they are. End with: files read, commands run (if any), limitations.
```

## 5. The prompts, in the order to run them (R5 and R6 first: they feed the form)

Each prompt is pasted after the preamble. Expected time is the reviewer's, at effort max, on the shared key.

### R0 — Orientation (5 min, interactive)
"Give a high-level summary in six bullets of what Parity is, how a run flows from `POST /api/runs` to a finding a human can approve, which Meta model call sits at each stage, and what is code rather than model. Then list the three places where you would look first for a correctness bug, with the reason."

### R5 — The submission essays, read as a Meta judge (20 min, interactive; first because the form is the deliverable)
"Read `docs/21-submission-text.md` and the rubric in `docs/hackathon/00-constitution.md` (Impact 30, Tooling 25 beyond basic integration, Depth 20, Demo 25) and the form questions below. For each essay (Project Description; 'Describe your use of Meta products to build the submitted project'; 'Why are Meta's models important to your solution?') answer: (1) which sentences a judge with five minutes would remember; (2) every claim that is not backed by a number in `eval/results/latest.md` or a file in the repo, quoted; (3) what is missing that the rubric rewards (name the capability and the file that proves it exists); (4) whether any sentence could be read as a compliance claim or as claiming pre-existing work as this week's (constraint 3). Then draft, in at most 120 words each, honest answers to the two questions the form adds: 'Compared with other AI models your team has used for the same kind of work, how did Meta's models perform?' (the form offers: much better / somewhat better / about the same / somewhat worse / much worse / used others but no clear comparison / have not used others) and 'If you took this project to production, what would most likely stop you from using Meta's models?' (options: model quality, price or unpredictable costs, rate limits or capacity, reliability, data use, security or compliance, region, cloud availability, missing production features such as batch or spend limits, long-term support, something else, nothing, not going to production). Ground the second in the trace: read `data/runs/*/events.jsonl` model.call latencies and errors, `docs/23-qa-report.md` §10 and the README's latency note (495 s against 281 s for the same calls), and say which option the evidence supports and why. Do not flatter; the essays are judged against other teams' essays."

### R6 — Cold read of the judge-facing package (15 min; Wonder if available)
"You are a Meta judge with five minutes. Read only README.md, HACKATHON_SCOPE.md and docs/18 §9 (the video storyboard). Score the project 0–10 on each rubric line with one sentence of reason each. Then list, in order of damage: every number that appears in two places with two values; every sentence that claims more than the eval supports; every place a judge could not tell what was built this week from what is pre-existing (constraint 3: immediate disqualification if unclear); anything a non-expert would not understand in the first 20 seconds of the storyboard. Suggest the smallest wording change for each. Do not propose new features."

### R1 — Is "the model perceives, code decides" true everywhere? (30 min, headless with schema)
"Doc 14 and spec §4 and §18 claim that no model output persists as a finding, a fix or a decision without passing a deterministic code gate, and that the orchestration is code. Verify this against `parity/pipeline/verifier.py`, `parity/pipeline/audit.py`, `parity/pipeline/gate.py`, `parity/pipeline/reaudit.py`, `parity/agent/loop.py`, `parity/agent/tools.py` and `parity/api/routes.py`. For each stage (Navigator actions, Seer percepts, Comparator candidates, Verifier, Judge, Fixer, Re-audit, human decision) state the exact code line where a model output is accepted or refused, what input would pass the gate wrongly, and whether a test covers it (`tests/`). Report every path where a model value reaches storage, the UI or the patch file without a gate, and every gate that trusts a model-formatted field (for example a quote compared after normalisation, a box that is never located, a judgement parsed from free text). Rank by the harm a wrong finding or a wrong fix would do to a user who approves it."

### R2 — The open-URL guard, adversarially (30 min, headless)
"Spec §17 and risk R7 promise that 'Live on a page you choose' is read-only, refuses private and non-public addresses, honours robots.txt, re-checks every request the browser makes (redirects included), never types credentials or card numbers, never submits a form, and ends the run on a bot wall or a login. Read `parity/` for the URL policy, the request interception, the consent handling, the per-run and per-day cost caps and the 24-hour deletion. Try to break each promise on paper: a redirect chain to an internal address, a page that instructs the model to click 'buy', a data: or file: URL, a robots.txt that is unreachable, a page that keeps the agent clicking until the cap, a cost cap that is checked between stages but not inside a fan-out (the judge runs four at a time; a run on 4 Nov cost $0.66 against a $0.50 cap). For each attempt: the code path, whether it is refused, by which line, and whether a test proves it. Report the unprotected cases first."

### R3 — Eval integrity (25 min, headless)
"The README's headline numbers (85% recall, 99% precision, 0.0 false positives on 20 clean controls, $0.37 and 495 s per page set; W3C BAD 14% / 22% / 40%) come from `eval/harness.py` against `eval/labels.json` and `eval/labels_external.json`. Verify: (1) the labels are never readable by the agent's code path at runtime (grep for the label paths and for any id list that could leak); (2) how a finding is matched to a label (the id rule, the 'nearest id above' fallback) and what that rule could count as a hit that a human would not; (3) that precision counts every finding on a clean control as wrong; (4) that every number in README.md, docs/17, docs/21 and the Eval tab equals the number in `eval/results/latest.md`, listing each mismatch; (5) what the three-run sample size means for the stated two-to-three-label spread; (6) whether 'Findings are evidence, not a conformance claim' is honoured by every sentence that mentions WCAG. Report mismatches first, then matching-rule risks, then wording."

### R4 — Use of the Meta Model API, beyond basic integration (25 min, interactive)
"Read `.claude/skills/meta-model-api/SKILL.md`, `parity/meta/client.py` and every call site under `parity/`. For each stage, state the request shape (model, tools, reasoning effort, text.format, truncation, previous_response_id, max_output_tokens) and compare it with what the API offers: prompt caching and cache-aware prompt layout, encrypted reasoning continuity across turns, strict json_schema contracts at every hop, reasoning effort tiered by role, background fan-out, structured outputs on the judge and fixer, the input_tokens endpoint for budget checks. Say which of these Parity uses, which it does not, and for each unused one whether adopting it would change a judged number (cost, latency, precision) and how much work it is. Do not propose changes that would alter the verified behaviour before submission; this is for the 'future work' section and for the Tooling essay's accuracy. Also check that every logged model.call carries model, request id, tokens, latency and cost, as CLAUDE.md requires, and name any call that is not logged."

### R7 — Tests and the last-day changes (20 min, headless)
"Read `tests/` and `web/src/**/*.test.tsx` against the pipeline. List: (1) the behaviours the README promises that no test exercises; (2) tests that pass by construction (assert on the fixture they built); (3) tests that depend on timing or network (one push today went out on a local timing flake); (4) for the four commits of 4 Nov (`git log --since='2026-11-04' --oneline`: the sixth Verifier check, the purchase re-record, the loop fix and the 16-turn budget, the storyboard) whether each has a test that would fail if the change were reverted. Report the untested promises first."

### R8 — The workshop pattern, as a comparison only (15 min, interactive, optional)
"Doc 12 describes Meta's legal-agent-workshop reference: a single model-driven loop, checks inside tools, state only through gated tools, a run ledger with resume and branch, judges that fail open, cost counted for agent turns only. Spec §18.2 claims Parity keeps the good patterns and improves the gaps. For each row of that table, verify the Parity claim in code (file:line) and say whether it holds, partly holds, or is aspirational. Treat the workshop as a reference point, not ground truth; where Parity departs from it, say whether the departure is justified by the product and whether the README explains it."

## 6. What to do with the output

- Every finding goes into a table in `docs/27-muse-code-findings.md` with: prompt id, severity, file:line, the claim, the reviewer's evidence, and a decision column (fix now / fix after / disagree, with reason). The builder fills the decision column; nothing is changed before that.
- "Fix now" is reserved for: a disqualification risk (constraint 3 wording, a compliance claim), a number mismatch, a guard bypass with a test, a crash path a judge could hit. Everything else is after submission; the feature freeze stands.
- Essay 7 gets two honest sentences: what Muse Code reviewed (the prompts above, with the session exports as evidence) and what changed because of it. The form's Muse Code 0–5 and obstacle answers come from the same experience.

## 7. The two questions the builder asked

**Should we run evals against other vendors' models for technical depth and a final hero moment?** No. The runtime rule (Meta models only) is not the obstacle; an offline comparison is allowed. The reasons are: the form asks it as a radio button, not an essay, so no judge reads a comparison; a credible comparison needs other keys, harness changes and three runs per configuration, landing hours before submission; a result that favours another vendor could not be shown and could not honestly be hidden; and the per-stage Meta model sweep already running (Spark 1.1, 1.2, 1.3, contributor tiers, Wonder, three efforts) is the comparison a Meta judge values: it shows which Meta model and effort earn their place at each stage, with cost and latency, on our own labels. Answer the radio from real experience: the honest options are "somewhat better", "about the same" or "used others but no clear comparison"; the builder picks the one that is true for them.

**What would most likely stop you in production?** The evidence points at one option: *rate limits or capacity too low for real traffic* (the product already rations Live to three runs per visitor per hour and one at a time per server; the key is shared with the coding agent; a page set took 495 s on 4 Nov against 281 s on 1 Nov with the same calls). The runner-up is *price or unpredictable costs* (the judge fan-out took a run to $0.66 against a $0.50 cap). R5 asks Muse Code to confirm this from the traces before the builder answers.

## 8. Time budget (today)

R5 and R6 first (35 min), then R1, R2, R3 (85 min, headless, can queue), then R4 and R7 (45 min), R8 only if time remains. About three hours of reviewer time, sequential on the shared key, interleaved with the purchase re-record and the sweep so no two API consumers run at once.
