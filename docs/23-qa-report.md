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
| Test suites | pytest 187/187 (incl. 9 integration tests through the served app), vitest 26/26 |
| Cold start from a fresh clone (no `.env`) | `make setup` → `make build-web` → serve → `/api/health` → Replay checkout (57 events) → approve → `GET /patch` 200: **pass**, no key needed |
| Console script `parity` | works in the fresh clone; the local `.venv` had a stale editable install (reinstalled) |
| Live checkout run through the real UI | 6 verified, fixes and re-audits streamed while auditing, a mid-run approval was counted, run settled to *awaiting review* at 101 s, $0.006 (cache hits labelled in the trace) |
| Exported patch | `git apply --check` passes on every file of both recorded runs (checkout 6/6; purchase 3/3, 2/2, 6/6) |
| Recorded replays | hero-checkout: 6 verified / 6 rejected / 6 fixes / 4 closed, $0.083, 221 s · hero-purchase: 12 / 5 / 11 / 5, $0.140, 574 s |
| Variance (3 live purchase runs, fresh cache, earlier today) | same 12 barriers by element in both completed runs; one run died on an API 500 burst → retries now 5× over ~33 s |
| Workbench accessibility | axe clean in idle / running / hero; keyboard ring complete with visible focus; VoiceOver pass by hand still owed (Task 25) |

**Defects found and fixed in this pass (each with a test that failed first):**
- At short viewports the findings and screen-reader panels overflowed their grid cells and badges painted
  *through* the open trace drawer (`test_trace_drawer_is_not_painted_over_by_panel_content`). Columns now
  scroll inside a 100vh app; the drawer is stacked above the grid; badges no longer use opacity.
- No UI affordance for the exported patch: the header now offers **Download fix.patch** once a fix is approved.

**Noted, not fixed:** the `?mock=` design pages scroll because of their extra nav (the real app does not);
the header shows `0 ms` while a run is in progress (duration lands at the end).

## 2. Reviewer findings

_Filled in below as each reviewer reports._

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

## 5. Decisions only you can make

1. **Five early commits carry `Co-Authored-By: Claude` trailers** (`be0dfe2`, `37b4b02`, `11bb9ed`, `40f2674`, `50610d7`). They contradict the solo declaration. Removing them means rewriting history and force-pushing `main`; I will not do that without your say-so.
2. **Third-party material in the public repo**: `docs/hackathon/01–03` (participant guide, kickoff transcript, Meta docs dump) and `docs/learnings/11, 12a, 13` (workshop transcripts). Remove before the final push, or declare them in `HACKATHON_SCOPE.md`.
3. **Disclosing AI coding assistance** in `HACKATHON_SCOPE.md` (the constitution asks that original contributions be clearly identified). Your call on wording.
4. **Per-run cap**: the spec says 10 minutes; a live purchase run now takes ~9.5 minutes. Enforce 10, or raise to 15 with Replay as the judges' default.

## 4. When the voice-over is needed

See the end of this report.
