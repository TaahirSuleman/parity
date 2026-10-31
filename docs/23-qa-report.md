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

## 3. Requirement matrix

_Filled in from the rules audit._

## 4. When the voice-over is needed

See the end of this report.
