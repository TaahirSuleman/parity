# 23 — Pre-Phase-4 QA report (31 Oct 2026)

**Scope:** everything built in Phases 1–3 (commits through `8f14c4d`), checked against the hard rules in
the project's working rules, the constitution (Articles II, V, IX), doc 18 (§3 product, §7 day plan, §9 video), the
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
| B-Critical | A snippet that fools Python's HTML parser (`<![CDATA[>…`, `<!-->…`) but not Chromium, plus an encoded path (`/%61pi/…`) past the re-audit's API block, let a model-written fix approve every pending finding by itself (proven end to end) | Declarations/comments refused; the re-audit page may only `GET /store/*` on its origin (decoded, normalised) and is served with a CSP (`connect-src 'none'`, `form-action 'none'`, `frame-src 'none'`). **1 Nov:** the sandbox had inherited the app's `bypass_csp` context, so the CSP was inert in production; the patched page now loads in a context of its own, tested with the production page factory |
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
| UX-I9 | The hero was card 9 of 12, unselected | Strongest finding whose fix closed the gap is selected on finish. **1 Nov:** ties were broken by list order, so the hero was still card 5 or 10 of 11; the score now prefers a control and a Label-in-Name mismatch, and the selected card scrolls into view |
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

1. **Co-author trailers on five early commits** — **done 31 Oct.** Removed by a message-only rewrite: every commit's tree, author, committer and dates verified identical, tags p1–p3 kept their tagger and message; `main` and the tags were force-pushed with leases. Judges cannot tell from the repository; GitHub's Activity view records the force-push for a while.
2. **Third-party documents in the public repo** — **must be removed before submission.** Recorded as a hard rule in the project's working rules, as the first item of Task 25, and in the cold-review checklist (`git ls-files docs/hackathon docs/learnings`).
3. **Disclosing AI coding assistance in `HACKATHON_SCOPE.md`** — **open question, return to it at the end.** Not required by the rules as read: Art. II.3 asks that the hackathon-built, original contribution be clearly identifiable, which the scope file does; it does not ask for tooling disclosure. A one-line disclosure is harmless and honest; the choice is yours at close.
4. **Per-run cap** — **10–15 minutes accepted; 15 kept** (`PARITY_RUN_TIMEOUT_S=900`), spec §15 updated.

## 6. QA pass 2 — after Phase 4, before Phase 5 (1 Nov 2026)

**Scope:** everything through tag `p4` (commit `780a43c`): the store v2, the eval and its numbers, the public-site
sample, the Eval tab, and the review fix pass. Phase 5 items (rate limits, Docker/Cloud Run, README, UI polish for
judges, close) and Phase 6 (Voice) are scheduled, not missing; where a finding falls inside one of those tasks it is
recorded against that task below rather than fixed here.

**Method:** (1) a cold start from a fresh clone of the committed tree (`make setup`, the test suite, the web build);
(2) a Live run of the checkout page through the real UI, then the human gate (approve with a reason, download the
patch), a Replay of the Purchase flow and of both public samples, the trace drawer; (3) two fresh-context reviewers —
one on UX/UI and the workbench's own accessibility (Playwright, axe, keyboard, four viewports), one on requirements
versus implementation (rules, spec routes and events, bundles, the gate, error paths, tests, docs honesty).

### 6.1 First-hand checks

| Check | Result |
|---|---|
| Cold clone → `make setup` → tests → `make build-web` | Setup 7 s with tools cached; 261 tests pass. The 14 web smoke tests skipped because the SPA was not built yet — `make setup` now builds it, so `make demo` and the smoke tests work from a fresh clone. |
| Live run, checkout page (dev cache warm) | 7 verified, 0 rejected, 2 m 33 s, $0.0077; judge, fixer and re-audit shown per card; `Download fix.patch` serves `text/x-diff` as an attachment with the approved hunks. |
| Human gate | **Found and fixed:** the reason field is prefilled with the re-audit's suggestion; a click mid-sentence put the caret there and typing spliced into it ("the screeAlt text…n reader"). The suggestion is now selected on focus, so typing replaces it. |
| Header time readout | **Found and fixed:** "0 ms" for the whole run. It now ticks elapsed time during a Live run and says "replaying…" during a Replay (replayed events carry the recorded timestamps, so elapsed time would have been the recording's age). |
| Redeploy behaviour | **Found and fixed:** `index.html` was served with no `Cache-Control`; after a rebuild the browser kept the cached page and asked for a hashed asset that no longer existed (blank page). `index.html` is now `no-cache`; `/assets/*` are `immutable` for a year. A judge who opened the site before a redeploy would have hit this. |
| Replay of the Purchase flow and both public samples | Plays; Site A shows six cards on the masked screenshot; Site B shows `blocked by site: bot challenge` as its outcome line. |
| Trace drawer | Stage, model badge, request id, tokens, latency, cost and cache hit/miss per call; at narrow widths the table scrolls horizontally. |
| Re-recording the Purchase hero (live, 12 turns) | **Found and fixed:** the last turn failed twice with HTTP 400 ("`computer_call_output` input items are not supported" when only `finish` was offered; "invalid parameters" with the computer tool but a reduced function set). A last turn that answers a computer call now carries the same tool set as the turn that made it; the "finish now" notice stays in the instructions. Two failed recordings cost $0.73. |
| Re-recording the Purchase hero (fourth and fifth attempts) | Both walks completed but spent all twelve turns on the cart trying to "fix" the seeded carry-case line (quantity 12 in a red error state) and never reached checkout, so the hero finding was absent and the script refused to record. **Decisions:** the default flow is now the checkout replay (the hero in seconds, every time); the Purchase goal tells the agent to leave other cart items as they are; the recording script records a purchase walk without the hero (`--no-require-hero`) and the integration test asks the purchase replay for a closed-gap fix rather than `#f5`. Five purchase attempts cost $1.69. |
| Re-recording the Purchase hero (third attempt) | **Found and fixed:** the walk now finished, but 33 verified findings put the fix stage past the 900 s run deadline and the whole run was failed ($0.40 lost). The fix stage now starts nothing new past 80% of the deadline and records the skipped fixes and re-audits per finding; the run finishes with what it has. The recording script takes a longer deadline so the committed replay carries every fix. |

### 6.2 Reviewer findings and what was done

Two fresh-context reviewers (UX/UI and the workbench's own accessibility; requirements versus implementation). Grades are theirs; the disposition is ours.

| # | Finding | Done |
|---|---|---|
| UX-C1 / QA-3 | Decisions vanished on reload or a shared link: the client stopped reading at `run.finished`, and `decision.recorded` is appended after it | Fixed. When a run finishes (or its link opens) the client applies the decisions the server holds (`GET /runs/{id}`); the smoke test now approves, reloads and expects "Approved" and the patch link |
| UX-C2 / QA-2 | The hero was never the opening card (ties broken by list order) and the selected card was never scrolled into view | Fixed. The score prefers a control over an image or text and a Label-in-Name mismatch over the rest, later screens on a tie; the feed scrolls the selection into view |
| QA-1 | The committed hero replays predated store v2: the downloaded patch no longer applied to the repository's `store/checkout.html`, and the replayed checkout showed six findings against nine labels | Fixed. Both heroes re-recorded on the current store and code (fresh cache: real latency and cost); `git apply --check` re-verified against the repository (§6.3) |
| QA-4 | A run interrupted by a restart had no terminal event: a browser opening its link reconnected every few seconds forever | Fixed. Boot recovery appends `run.failed {error: "interrupted by restart"}`; a stream drop is now a notice, not a failed run |
| QA-5 | A cancelled Live run (server shutdown mid-call) was settled as `done` | Fixed. `CancelledError` marks the run failed, emits `run.failed`, then propagates |
| QA-6 | The re-audit sandbox inherited the app's `bypass_csp`, so its Content-Security-Policy did nothing in production | Fixed. The patched page loads in a context of its own; tested with the production page factory |
| UX-I1 | The screenshot squashed to 65 px with the trace open at 1280×720 and to nothing at 375 px | Fixed (`flex-shrink: 0`, `object-fit: contain`); smoke test measures the image's shape with the trace open |
| UX-I2 | axe `scrollable-region-focusable` on the Screen reader panel after a run at 768 px and with the trace open | Fixed (the panel is a focusable named region); axe smoke test added at 768 px after a run |
| UX-I3 | Model badges clipped by `white-space: nowrap`; the Sighted panel credited only Chromium after a run | Fixed: badges wrap; the panel shows the grounding badge once boxes are drawn |
| UX-I4 | "name rule: still open" in red beside "comparator: no longer flags it"; the suggested reason said "still says" the new name | Fixed: amber with an explanation when the comparator accepts the fix; the suggestion says "now says" |
| UX-I5 | Focus fell to `<body>` when Run was disabled; no announcement of a start or a decision | Fixed: Run is `aria-disabled` while running; live regions announce start, end and each decision |
| UX-I6 | A failed decision request or a dropped stream failed the whole run, with the message out of view | Fixed: both are notices at the top of the feed (`role="alert"`); the run keeps its state |
| UX-I7 | "ShopRight ·" and the flow picker shown for a public sample; the picker not synced to a reloaded run | Fixed: a public run is named "Site A · read-only sample"; the picker follows the run on screen |
| UX-I8 | Cards did not say which screen they belong to | Fixed: "screen 3 · checkout" on multi-screen runs |
| UX-I10 | "No divergences passed the verifier" for a walk a bot wall stopped; "Run the audit to see the page" after it; "A fix and its re-audit follow" on finished and public runs; "(spec §17)" in a judge-facing note | Fixed: context-aware copy; the spec reference dropped from `public.json` |
| UX-I11 | The Eval toggle had no visible pressed state | Fixed (pressed style). An architecture card and a glossary stay in Task 24 |
| UX minors | `fmtDuration` could print "1 m 60 s"; raw ISO timestamp in the Eval tab; `aria-label` on elements that do not support it; badges from the wrong model field; idle counters that read as measurements | Fixed |
| QA minors | `comparator.unparseable` not shown; "33 / 38 labels" misread as labels found; stale `config.py` comment | Fixed: a timeline row; "33 per run · 38 labels" in the tab, `latest.md` and doc 17; comment corrected |
| UX-I9 | Boxes on the screenshot are below 24×24 px; the screenshot is 38% of the page at 1280 px | **Task 24** (UI polish): a minimum hit area for boxes and a larger sighted panel |
| QA-7 | Model-facing tests answer from recorded stage defaults, not prompt-keyed fixtures (recorded on the v1 checkout) | **Ruling:** spec §14 now says what the fake does; the live smoke run and the eval are the prompt-regression checks. Re-recording per-prompt fixtures for every stage is not worth the hours before the freeze |
| QA-8 | On Cloud Storage, boot time grows with every Replay click (each copies a bundle; boot reads every bundle twice) | **Task 22**: cap or evict replay copies and make recovery read `run.json` only, before the first deploy |
| QA-9 | Prompt-injection hardening (page text marked untrusted in the prompts, with a test) slipped from P4 | **Ruling:** not done before submission: changing the prompts now would invalidate the measured eval (the shipped numbers are tied to commit `1e6caad`'s prompts), hosted Live mode is restricted to our own store, and public runs sit behind the read-only guard. Stated as a limit in the README (Task 23) |
| QA minors kept | `GET …/verifier-off` caches its report in the bundle; `needs_review` findings end the run `done`; an unknown `PARITY_MODEL` is priced at $0; unused index tables; a corrupt finding file hides its run | **Rulings:** kept as they are (documented in spec §5.1 where relevant); none changes what a judge sees |
| UX minors deferred | Developer wording on the timeline (`audit_view`, `computer_action_requires_confirmation`, "gated tool"); hover-only verifier details and request ids; two meanings of "rejected"; "Replay = a recorded run, no model calls" explanation and a Meta pipeline legend in the idle state; a glossary for recall and precision | **Task 24** |

### 6.3 Verification of this pass

- vitest 64/64; the Python suite and the browser smoke tests green (see the ledger for the counts); the smoke tests gained: decisions survive a reload and the header follows the run's flow; axe-clean at 768 px after a run with the trace open; the screenshot keeps its 16:9 shape with the trace open; `index.html` is `no-cache` and hashed assets immutable.
- Hero bundles re-recorded 1 Nov on store v2 with the final code and a fresh cache. hero-checkout: 7 verified, 3 rejected, $0.09, 4 m 42 s; all seven fixes approved on a replay give a 4,276-byte patch that `git apply --check` accepts against the repository's `store/checkout.html`. hero-purchase (sixth attempt, with the goal telling the agent to leave other cart items alone): all four screens, the agent finished in 9 turns, 35 verified, 2 rejected, 33 fixes proposed and re-audited (16 closed the gap, none skipped by the budget), $0.44, 20 m 9 s recorded under the 30-minute recording deadline; the hero `#f5` is among the findings. All 33 fixes approved on a replay give a patch that `git apply --check` accepts against the repository (see the ledger for the byte count and files).

### 6.4 Hosted deploy (Task 22, 1 Nov evening)

`https://parity-u7lcbbxuia-uc.a.run.app` — Cloud Run, us-central1, one warm 2-CPU/2 GiB instance, bundles in a private bucket, the key from Secret Manager.
Checked after the first deploy: `/api/health` reports `storage: gcs`, `models_ok: true`; `/` is `no-cache` and a deep link (`/runs/<id>`) serves the workbench; `/api/nope` is 404.
A Replay of the checkout hero finished in 2 s; approving its fix persisted (re-read from the API) and `fix.patch` downloaded as `text/x-diff`; the step
screenshot was served from the bucket. One Live run of the checkout page on the hosted instance: 7 verified, 0 rejected, 278 s, $0.096. From the desktop
pane (a fresh browser, no login) the hosted Replay opened on "Pay R1,249" vs `button, "Submit"`. Persistence across a redeploy is recorded in the ledger
(the run, its decision and its screenshot re-read after the second deploy).


## 7. Stress campaign — after Phase 5, before the recording (1 Nov 2026, evening)

The whole app under load and under hostile input, before any further development: an adversarial backend tester (API fuzz, pipeline
pieces, bundles, index, blob keys), a browser stress tester (viewports, dark mode, a keyboard-only journey, dropped streams, two tabs,
rapid clicks, a server kill mid-replay, a long session), our own soak and concurrency script, and the same against the hosted instance.
Every bug got a root cause, a failing test, a fix and a re-run of the repro.

### 7.1 Load and concurrency (local, one process)

- Soak: 60 sequential Replays; RSS 20 → 71 MB in the first twenty, then flat. Replay copies on disk capped at 20 as configured.
- 20 Replays started at once: all 20 streams ended in `run.finished`, 0.4 s wall clock. 50 subscribers on one paced Replay: every stream
  saw all 61 events and `run.finished`.
- 10 racing decisions on one finding: exactly one 200 and nine 409; one decision persisted.
- 150 half-open SSE connections held for 8 s: `/api/health` still answered in under 10 ms; RSS 81 MB; back to 80 MB after.
- Boot with 20 kept copies and the model probe: under 2 s.
- A failed Live run (the demo store unreachable) ends in `run.failed` within a second and frees the Live slot (the next POST is 202).

### 7.2 Hosted (Cloud Run, the judges' URL)

- 10 concurrent hosted Replays in 3.7 s, none bad; deep links and API 404s as designed; the fuzz list produced no 5xx.
- A second Live POST while one runs: 429 with `retry_after_s: 60` and the Replay suggestion. The Live run itself finished: 7 verified,
  $0.106, 164 s.

### 7.3 Bugs found, root causes, fixes

1. **Over-long or NUL-bearing run ids were a 500 that reset the connection.** `GET /api/runs/<2,000 characters>` went from the URL
   straight into a filesystem path; `os.stat` raised `ENAMETOOLONG` (a NUL raised `ValueError`). Fix: run and finding ids are validated
   at the API boundary (`^[A-Za-z0-9][A-Za-z0-9-]*$`, at most 80 characters, otherwise 404), a step index must be 0–999 (422), and the
   local blob store treats a name the filesystem cannot hold as missing. Tests: ids are validated on every route that takes one; the
   store answers "missing" for unstorable keys.
2. **The SPA catch-all 500ed on `/%00`, `/eval/%00` and a 2,000-character path** (`Path.resolve` / `is_file` raised). Such a path is
   neither a static file nor a run link: it is now a 404. This one was live on the hosted demo; the API-side one was masked there by the
   bucket store. Test: the catch-all answers 404 for paths the filesystem cannot name, and a real-looking deep link still opens the workbench.
3. **A Replay still playing could be evicted by a newer Replay start.** Eviction ranked copies by age only. With at least `PARITY_REPLAY_KEEP`
   Replays in flight (twenty judges clicking at once), the oldest one's bundle was deleted mid-stream: its screenshots and detail route
   went 404 and its publisher task died on a `KeyError`. Fix: eviction skips any run the event bus still has in flight; it becomes evictable
   once its stream ends. Test: with the cap at 1, a second start leaves the first playing and serving screenshots; the third start, after
   both finished, evicts them.
4. **Request bodies had no size limit, and errors echoed the input.** A 60 MB body took the instance from 13 to 362 MB and came back
   whole inside a 404; eight 30 MB bodies in flight peaked at 1 GB (Cloud Run allows 32 MB bodies and 20 concurrent requests on a 2 GiB
   instance). Bodies are now refused over 64 KB (413, unread when declared, counted when not), and no error echoes a body.
5. **FastAPI's own 422 became a 500 for `pace_ms: Infinity` or a lone surrogate in a reason**, because the default handler re-serialises
   the offending input. A safe handler returns the error without the input; a reason that is not valid UTF-8 is refused.
6. **A corrupt stored record was a 422 full of internals on the decision route and a traceback on the detail route.** Both are now one
   JSON 500, "a stored record for this run is unreadable; see the server log".
7. **`/api/eval` crashed on a truncated or list-shaped results file;** it is now a logged 404, which the Eval tab shows as "no results".
8. **A global Live limit of 0 raised `IndexError`.** Setting `PARITY_LIVE_GLOBAL_PER_DAY=0` is how an operator turns Live off; it now answers 429.
9. **Any visitor could list every run id and decide every other visitor's findings.** The public run list is gone (the count stays in
   `/api/health`); a run id is the capability, and a shared link shares the decisions by design.
10. **Run ids carried 16 random bits**: 0.55% of 30-id bursts collided, and a collision merged two bundles. Ids carry 32 bits, and a start
    that lands on an existing id draws again.
11. **Boot kept index rows for bundles that were gone** (runs whose detail was 404) **and ranked eviction by id**, which within one second is
    random. The index is cleared and rebuilt, and eviction ranks by start time.
12. **A finished Replay a judge was still reviewing could be evicted by twenty other judges' clicks** (Approve then returned 404 for ever).
    Beyond the cap, only copies older than `PARITY_REPLAY_MIN_AGE_S` (two hours) are evicted; the message for a run that is gone says so.
13. **A redeploy never finalised runs in flight.** uvicorn re-raises SIGTERM after its own graceful close, so background tasks never saw
    `CancelledError`: a replay cut by a redeploy stayed `running` for ever with an event log that never ended, and a viewer reconnected
    for ever. The app now tracks every run task, cancels and awaits them at shutdown (5 s), and the replay publisher records the
    interruption and closes the log with `run.failed`.
14. **The public-site guard let forms submit.** `"\n"`, `"\r"`, `"numpad enter"` and `"Shift+Enter"` are all Enter to the executor but were
    not to the guard; a button labelled only by CSS `::before` (an empty accessible name) and labels such as "Complete purchase" or
    "Place your order" passed. The guard now refuses every spelling of Enter and Space, unnamed buttons, and a wider list of
    irreversible words after zero-width characters are stripped and the name is NFKC-normalised.
15. **The fix validator accepted `formaction="https://evil.example"` and `<animate attributeName="href" values="javascript:…">`.** Form
    destination attributes may not change from the original element, attributes may not repeat (browsers keep the first, the check
    read the last), and SVG animation elements are refused.
16. **A name ending in a quote mark (`Monitor 27"`) was rejected when quoted exactly**, because every quote character was stripped. One
    wrapping pair is stripped; a quote mark inside the name stays.
17. **Deeply nested brackets or a 5,000-digit number in a comparator answer failed the run** (only `JSONDecodeError` was caught). Any
    unparseable answer is now treated alike.
18. **The public-audit CLI stored `user:pw@` URL credentials in `run.json`** and printed the anonymise hint after a failed walk. Fixed.

### 7.4 Workbench findings (browser stress) and what was done

The browser pass held on axe-core (0 violations in every state, both themes, 1440/768/375), contrast, visible focus, no focus traps,
the start and finish announcements, the run guard while a run is going, reloads at any moment, and a 30-replay session (DOM, listeners
and heap flat). It found 21 issues; the four critical ones first:

- **A double click on Run started two or three runs and mixed them into one feed** (14 verified in the feed, 7 in the header, boxes
  drawn twice; approving a card from the other run returned 404). One start at a time: a start request in flight blocks a second click,
  the Run button is taken while it is pending, and the reducer ignores events from another run and a second `run.started` over a running one.
- **Site A and Site B played under "ShopRight · Checkout page".** The samples' `run.started` event still said `flow_id: public-<host>`
  (run.json said `public`). The anonymiser now relabels the start event and the two committed samples were relabelled in place; the
  workbench also tolerates the older spelling.
- **A rejection in a second tab silently showed "Approved".** The 409 path still adopts the recorded decision, and now says that
  another viewer decided first and that this rejection was not recorded.
- **Eviction broke Approve and run links on a shared host** (see 7.3 item 12).

Important: the layout collapsed at 200% zoom and on phones (`main` 85 px tall; the three panels 12 px slivers) — short or narrow
viewports now scroll the page, with a 280 px floor per panel; after a server restart the "reconnecting" notice outlived `run.failed`
and the failure was neither badged nor announced — notices clear on a terminal event, the header shows "failed", the live region says
"Audit failed", and the failure line sits at the top of the feed; finishing a run stole a card the judge had picked (and the focus
from its reason field) — a card the judge chose stays; "Replay Site A" and Run from the Eval tab left focus on `<body>` or stayed on
Eval — a start switches to the workbench and focuses it; a bad or evicted `?run=` link and a failed flow list were silent — both
produce a notice; a `reaudit.result` after an approval reset the status (the approved count and the patch link vanished mid-run) — a
decided finding's status is never downgraded and approvals are counted by decision; `/runs/<id>` links opened an idle workbench — the
SPA reads them now. Minor: the header row wraps at 320 px; the diff wraps and the reason field spans the card; a failed screenshot on
our store no longer claims third-party pixels; no axe count before a screen is captured; no "blocked: blocked by site"; step tooltips
show the path, not a local origin; "Diff" and "Check details" are named per finding; the boxes' tab order follows reading order
(largest-lowest z-index keeps the hit test); the tab title follows the run's state; a favicon; no "0 ms"; "run"/"runs".
Left for the user's VoiceOver pass: the length of the status read on load, two near-identical "capturing" announcements, "image, image"
during the run, and whether a freshly inserted `role=status` is announced.
