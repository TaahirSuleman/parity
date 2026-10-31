# 23 — Pre-Phase-4 QA report (31 Oct 2026)

**Scope:** everything built in Phases 1–3 (commits through `979ef4e`), checked against the hard rules in
`CLAUDE.md`, the constitution (Articles II, V, IX), doc 18 (§3 product, §7 day plan, §9 video), the
submission checklist and the spec (doc 19). Phases 4–6 are scheduled, not missing.

**Method:** (1) a requirements audit and two whole-codebase reviews by fresh-context reviewers (backend;
workbench + API as a judge would use it); (2) first-hand checks: a cold start from a fresh clone, a Live
run through the real UI, the CLI on real bundles, the recorded replay bundles, the test suites.

## 1. First-hand checks

| Check | Result |
|---|---|
| Test suites | before the pass: pytest 187, vitest 24 · after the pass: pytest 216, vitest 36, all green (incl. 10 integration tests through the served app) |
| Cold start from a fresh clone (no `.env`) | `make setup` → `make build-web` → serve → `/api/health` → Replay checkout (57 events) → approve → `GET /patch` 200: **pass**, no key needed |
| Console script `parity` | works in the fresh clone; the local `.venv` had a stale editable install (reinstalled) |
| Live checkout run through the real UI | 6 verified, fixes and re-audits streamed while auditing, a mid-run approval was counted, run settled to *awaiting review* at 101 s, $0.006 (cache hits labelled in the trace) |
| Exported patch | `git apply --check` passes on every file of both recorded runs (checkout 6/6; purchase 3/3, 2/2, 6/6) |
| Recorded replays (after the pass) | hero-checkout: 6 verified / 1 rejected / 6 fixes / 4 closed, $0.073, 210 s · hero-purchase: 11 / 2 / 11 / 7, $0.134, 488 s; no false positives, patches apply on every file |
| Variance (3 live purchase runs, fresh cache, earlier today) | same 12 barriers by element in both completed runs; one run died on an API 500 burst → retries now 5× over ~33 s |
| Workbench accessibility | axe clean in idle / running / hero; keyboard ring complete with visible focus; VoiceOver pass by hand still owed (Task 25) |

**Defects found and fixed in this pass (each with a test that failed first):**
- At short viewports the findings and screen-reader panels overflowed their grid cells and badges painted
  *through* the open trace drawer (`test_trace_drawer_is_not_painted_over_by_panel_content`). Columns now
  scroll inside a 100vh app; the drawer is stacked above the grid; badges no longer use opacity.
- No UI affordance for the exported patch: the header now offers **Download fix.patch** once a fix is approved.

**Noted, not fixed:** the `?mock=` design pages scroll because of their extra nav (the real app does not);
the header shows `0 ms` while a run is in progress (duration lands at the end).

## 2. Reviewer findings and what was done

Three fresh-context reviewers (backend, workbench + API, rules audit). Severity as re-graded by effect on a judge.

**Fixed in this pass (each with a test that failed first):**

| # | Finding | Fix |
|---|---|---|
| B-Critical | A snippet that fools Python's HTML parser (`<![CDATA[>…`, `<!-->…`) but not Chromium, plus an encoded path (`/%61pi/…`) past the re-audit's API block, let a model-written fix approve every pending finding by itself (proven end to end) | Declarations/comments refused; the re-audit page may only `GET /store/*` on its origin (decoded, normalised) and is served with a CSP (`connect-src 'none'`, `form-action 'none'`, `frame-src 'none'`) |
| B-I1 | A decision made between `fixer.proposed` and `reaudit.result` was overwritten by the re-audit's save | Saves merge under the run lock and never clear a decision |
| B-I2 | Replay wrote the source's final status, leaving a run `awaiting_review` after judges had decided everything during playback | Replay settles from pending fixes under the run lock |
| B-I3 / audit 6 | Every completed agent turn was traced with a false error; no per-call log line; the key could travel in an error body | Fixed; INFO line per call; key scrubbed; recorded trace repaired |
| B-I4 | Comparator retries re-proposed verified elements, inflating "rejected" (3 of 6 red rows were the system's own repeats) | Retry only for fixable failures; repeats dropped silently |
| B-I5 / UX-I2 | A clean sentence (`Order <strong>SR-10428</strong>…`) shipped as a verified *serious* barrier in the hero replay | Verifier: a text fragment announced in full by its surroundings does not diverge; bundles re-recorded |
| B-I6 | One corrupt bundle stopped the server booting | Recovery skips it |
| B-I7 | No run deadline: a stalled call could hold the Live slot ~26 min | `PARITY_RUN_TIMEOUT_S` (900 s) fails the run cleanly |
| B-I8 | Provider safety checks were acknowledged unread after the actions ran | A pending check stops the batch and ends the run with `nav.blocked` |
| B-I11 | Malformed judge output aborted the audit mid-way | Fails closed to `needs_review`; a judge error never hides a finding |
| UX-Critical | On the default Purchase replay every box was drawn on the last page's screenshot | Boxes belong to their screen; a step strip switches screens; the selected finding's screen is shown |
| UX-I1 | "Gap still open" on good fixes; the comparator's agreement never shown; no Meta badge on the second signal | Both signals shown ("name rule" + "comparator"), with the badge |
| UX-I3 | Header showed replay wall-clock (32 s) for a 9.6-minute run | Recorded duration from the event, labelled "recorded" |
| UX-I4 | Reload lost the run; no run URL | `?run=<id>` is set on start and reloads the run's history |
| UX-I5 | Pressing the current mode mid-run wiped the workbench and left the stream attached | Guarded; stream closed on a real mode change |
| UX-I6 | axe failed after a finished run (scrollable regions, 11 duplicate landmarks, dark label contrast) | Fixed; test runs axe on a finished replay in both themes |
| UX-I7 | Card was one 240-character button; list re-read on every addition; trace heading inside a button | Card is an article named by its heading with a short select button; live region removed; heading outside |
| UX-I8 | No responsive layout (sideways scroll at 768, unusable at 390) | Columns stack below 1280 px; tests at 1024/768/390 |
| UX-I9 | The hero was card 9 of 12, unselected | Strongest finding whose fix closed the gap is selected on finish |
| UX-I11 / audit | Visitor IP hash and internal host exposed by the API | Dropped from public responses; listing bounded |
| Audit 1a | Judge fallback model hard-coded | Setting; a test forbids model-id literals outside config |
| Audit §8 | `agent.tool_error` never reached the UI | Subscribed |
| Minors done | Reject allowed for a finding with no fix; visible switch state; coloured diff; flow-aware idle copy; "to see" not "to hear"; consistent cost format; `Download fix.patch` | |

**Deferred (scheduled or your call):** per-IP/global Live limits and `X-Forwarded-For` (Task 21, before any key goes on a host); Replay copies grow storage per click (Task 21: overlay or limit); 60 s per-call timeout (Task 21); request-level cross-origin abort and the public-site guard (Task 19b); store ids that encode labels (Task 18); README rewrite and `HACKATHON_SCOPE.md` accuracy (Tasks 23/25); Python lockfile and lint/type CI steps; prompts do not yet frame page text as untrusted data (P4, with an injection test); `?mock` pages ship in production (labelled); judge severity varies between recordings (model variance; cannot be pinned); elapsed time while running; the timeline cap; no `comparator.unparseable` event.

## 3. Requirement matrix (from the rules audit, condensed)

| Requirement | Status | Evidence / gap |
|---|---|---|
| Only Meta models at runtime | **Met** | No other provider or model anywhere in `parity/`, `web/src`, `store/`; the only model HTTP client is `parity/meta/client.py`. Every stage id comes from `Settings.model_for` (the judge fallback was the last literal; now a setting). A test fails on any `muse-` literal outside config/pricing. |
| No-login demo: hosted URL + Run button + Live/Replay | **Scheduled (P5)** for the URL; the button, modes and Replay default exist | Deploy (Task 22) is the biggest schedule risk. |
| One-command local run | **Met on macOS** | Cold start verified from a fresh clone. Assumes Homebrew; Linux/Windows path arrives with Docker (Task 22). |
| Built this week; `HACKATHON_SCOPE.md` | **Partial** | First commit 30 Oct, all commits by Taahir Suleman. The scope file lists unbuilt items (eval, Dockerfile, labels, Voice) as if built, omits dev/test deps and the Chromium binary, and does not mention the third-party docs under `docs/hackathon` and `docs/learnings`. **Decision needed** (see §5). |
| Never claim "compliance" | **Met** | Only negations in code, UI, prompts and docs. The judge cites WCAG criteria as evidence, not conformance. |
| Secrets | **Met** | Key only from env/`.env`; `repr=False`; never in cache files, bundles, traces, health; `.env` never in git history; error strings now scrubbed. |
| Per-call logging and disk cache | **Met** (defect fixed) | Trace rows + `model.call` events carry model, request id, tokens, latency, cost; INFO log line per call; agent turns and incomplete answers bypass the cache. |
| Third-party sites read-only | **Met for the store; public path Scheduled (P4)** | Start URLs fixed to our flows; origin guard after every action; `PARITY_LIVE_TARGET_ORIGINS=self`. Guard is detective (the page has loaded before it fires); a request-level abort is listed for Task 19b. |
| Labels outside the agent path | **Partial** | `eval/` does not exist yet; `parity/` imports nothing label-like. Store ids (`f1…f6`, `c1`, `c2`) encode fault/control and appear in `outer_html` shown to the judge/fixer; Task 18 renames them. |
| README / LICENSE / CI | **Partial** | LICENSE MIT (Taahir Suleman); CI builds the SPA and runs both suites. README is stale ("Phase 1 … later phases") — Task 23 rewrites it; "every model call is cached" is corrected there. |
| Replay default, Live limited | **Partial** | Replay default, no key needed; one Live run at a time; 403/503 never fall back silently. Per-IP and global limits and `X-Forwarded-For` are Task 21 — **must land before a key goes on a host**. |
| Engineering standards (Art. IX) | **Mostly met** | Contracts (`extra="forbid"`, parsers fail closed), oracles (verifier, `gap_closed`, human gate), observability (trace, events, replay), guardrails (allow-listed executor, gated tools, snippet validator, sandboxed re-audit), per-role effort, reproducibility (one command, `.env.example`, seed store). Gaps: eval gate (P4), no lint/type step in CI, no Python lockfile, prompts do not delimit page text as untrusted data. |

## 5. Decisions (taken 31 Oct)

1. **`Co-Authored-By: Claude` trailers on five early commits** (`be0dfe2`, `37b4b02`, `11bb9ed`, `40f2674`, `50610d7`) — **open item, revisit at the P5 close** (Task 25). Could judges tell if we rewrote history? From the repository itself, no: a rebase that strips the trailers produces a normal linear history with new SHAs and the same author dates; nothing in `git log` marks a rewrite. Where a trace could remain: GitHub's repository **Activity** view and events API record force-pushes (with the old SHAs) for a while; anyone who cloned or forked earlier keeps the old SHAs; tags `p1`–`p3` would have to be moved. If it is done, do it once, early on the final day, re-tag, and note nothing — the content is identical either way. Leaving them is also defensible: AI assistance is not prohibited, and the scope file states who built what.
2. **Third-party documents in the public repo** — **must be removed before submission.** Recorded as a hard rule in `CLAUDE.md`, as the first item of Task 25, and in the cold-review checklist (`git ls-files docs/hackathon docs/learnings`).
3. **Disclosing AI coding assistance in `HACKATHON_SCOPE.md`** — **open question, return to it at the end.** Not required by the rules as read: Art. II.3 asks that the hackathon-built, original contribution be clearly identifiable, which the scope file does; it does not ask for tooling disclosure. A one-line disclosure is harmless and honest; the choice is yours at close.
4. **Per-run cap** — **10–15 minutes accepted; 15 kept** (`PARITY_RUN_TIMEOUT_S=900`), spec §15 updated.
