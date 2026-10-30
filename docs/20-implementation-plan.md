# Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; the token budget is tight) to implement this plan task-by-task. Use superpowers:subagent-driven-development only for the independent chunks marked **[subagent-ok]**. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ship Parity, an agent that walks a site's key flows, finds the screen-reader gaps axe-core misses, proves them, proposes fixes and leaves the decision to a human, with a hosted no-login demo by Mon 2 Nov.

**Architecture:** FastAPI + async Playwright pipeline (navigator → capture → seer → comparator → verifier → judge → fixer → re-audit → human gate) writing a run bundle on disk and streaming events over SSE to a React workbench. Muse Spark 1.3 perceives; code verifies; the Verifier is the only door a finding can pass through.

**Tech Stack:** Python 3.12, FastAPI 0.162, Playwright 1.64, pydantic 2.14, sse-starlette 3.6, aiosqlite 0.22, httpx 0.28, pytest 9; React 19.3, Vite 8.3, TypeScript 7, Tailwind 4.3, axe-core 4.14, vitest 5; Cloud Run.

**Spec:** `docs/19-design-spec.md` (scope from `docs/18-decision-and-development-plan.md`).

## Global Constraints
- Every runtime model is a Meta model: `muse-spark-1.3`; `muse-spark-1.3-contributor` for eval only.
- `MODEL_API_KEY` comes from `.env` or the environment; it is never printed, logged or committed.
- Every model call is cached on disk (`sha256(model + canonical body)`) and traced: model, request ID, tokens, latency, cost.
- Every computer-use request sets `"truncation": "auto"`. Viewport is 1280×720.
- Boxes are on the 0–1000 grid; the verifier thresholds are `IOU_MIN = 0.2`, `CENTRE_TOLERANCE = 15`.
- No "compliance" wording anywhere. Replay is the default mode. Labels in `eval/` are never imported by `parity/`.
- Tests never call the live API; model-facing code is tested with `FakeMetaClient` over `tests/fixtures/meta/`.
- Each phase ends demoable, committed and pushed to `origin/main`.

## Review Focus
1. A comparator candidate with a missing or out-of-range `bbox` must be rejected by `located`, never crash the run (test in Task 6).
2. A 5xx from the API after retries mid-run must end the run as `failed` with the error in `run.json` and the trace intact (test in Task 9).
3. An SSE client that connects after the run finished must receive the full `events.jsonl` and then close (test in Task 10).
4. A second Live run while one is in progress must get HTTP 429 and the first run must be unaffected (test in Task 21).
5. AX names differing only by whitespace or case (`"Submit "` vs `"submit"`) must still pass `sr_quote_exact`, and `"Pay R1,249"` vs `"Submit"` must still diverge (test in Task 6).

---

# Phase 1: vertical slice on the checkout page (done by Sat 31 Oct night)

Exit check: `make demo` opens the workbench, **Run the audit** (Live) walks `/store/checkout.html`, the hero card shows "Pay R1,249" vs `button, "Submit"` with five green verifier ticks, the header shows `axe-core · 0 violations`, and Replay plays the same run without the key.

### Task 1: Toolchain and scaffold

**Files:**
- Create: `pyproject.toml`, `Makefile`, `parity/__init__.py`, `tests/test_smoke.py`, `.github/workflows/ci.yml`
- Modify: `.gitignore` (add `.venv/`, `web/node_modules/`, `web/dist/`, `parity/static/`, `data/`, `cache/`, `.pytest_cache/`, `.DS_Store`)

**Interfaces:**
- Produces: `make setup` (brew + uv venv + `playwright install chromium` + `npm ci` in `web/`), `make test`, `make demo`, `make web`.

- [ ] **Step 1:** `brew install python@3.12 node uv`; `uv venv --python 3.12 .venv`; write `pyproject.toml` with dependencies from the Tech Stack, `[tool.pytest.ini_options] asyncio_mode = "auto"`, package `parity`.
- [ ] **Step 2:** Write `tests/test_smoke.py::test_import` asserting `import parity` and `parity.__version__ == "0.1.0"`.
- [ ] **Step 3:** Run `uv pip install -e ".[dev]" && .venv/bin/playwright install chromium && .venv/bin/pytest -q`. Expected: 1 passed.
- [ ] **Step 4:** `ci.yml`: on push, Python 3.12, `uv pip install -e ".[dev]"`, `playwright install --with-deps chromium`, `pytest -q`; Node 26, `npm ci && npm test` in `web/` (skips until Task 11 creates it: guard with `if: hashFiles('web/package.json') != ''`).
- [ ] **Step 5:** Commit `chore: scaffold parity (python 3.12, pytest, makefile, ci)`.

### Task 2: Config, pricing and data model

**Files:**
- Create: `parity/config.py`, `parity/meta/pricing.py`, `parity/store/models.py`
- Test: `tests/test_config.py`, `tests/test_pricing.py`, `tests/test_models.py`

**Interfaces:**
- Produces: `Settings` (dataclass from env with the names in `.env.example`; `load_settings(env: Mapping | None = None) -> Settings`; loads `.env` via python-dotenv without overriding existing env).
- `cost_usd(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float` using the table `PRICES = {"muse-spark-1.3": (1.25, 0.15, 4.25), "muse-spark-1.3-contributor": (0.10, 0.002, 0.20)}` per 1M; unknown model → `0.0` plus a logged warning.
- pydantic models exactly as spec §5: `Run, Step, Percept, Candidate, Finding, Rejected, Judgement, Fix, Reaudit, Decision, ModelCall, VerifierResult, Check, BBox, Element, AxNode, Capture`. `BBox` has `x_min, y_min, x_max, y_max: int` with a validator clamping to 0–1000. `RunStatus`, `FindingStatus`, `Severity` are `StrEnum`s.

- [ ] **Step 1:** Tests: `test_settings_defaults_replay` (no env → `default_mode == "replay"`, `live_per_ip_per_hour == 3`); `test_settings_never_exposes_key` (`repr(settings)` does not contain the key value); `test_cost_spark13` (`cost_usd("muse-spark-1.3", 1_000_000, 0, 0) == 1.25`); `test_bbox_clamps` (`BBox(x_min=-5, y_min=0, x_max=1200, y_max=10)` → 0 and 1000); `test_finding_roundtrip` (model_dump_json → model_validate_json equality).
- [ ] **Step 2:** Run `pytest tests/test_config.py tests/test_pricing.py tests/test_models.py -v`. Expected: FAIL (modules missing).
- [ ] **Step 3:** Implement the three modules.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat: settings, pricing table and run data model`.

### Task 3: Meta client with cache, retries and trace

**Files:**
- Create: `parity/meta/client.py`
- Test: `tests/test_meta_client.py`

**Interfaces:**
- Produces: `class MetaClient(settings, cache_dir, trace: TraceSink, http: httpx.AsyncClient | None = None)` with `async responses(body: dict, *, stage: str, run_id: str, step_index: int | None = None) -> MetaResponse` and `async models() -> list[str]`.
- `MetaResponse(raw: dict, text: str, response_id: str, request_id: str, usage: Usage, cache_hit: bool, latency_ms: int)`; `text` joins `output[].content[].type == "output_text"`.
- `TraceSink` protocol: `async record(call: ModelCall) -> None`. `ListTraceSink` for tests.
- `class MetaError(Exception)` with `status`, `request_id`, `attempts`.
- Retry policy: statuses ≥ 500 and transport errors, attempts 3, sleeps `(1, 3, 9)` seconds (injectable `sleep` for tests). 4xx raises immediately.
- `FakeMetaClient(fixture_dir)` in `parity/meta/fake.py`: same interface; looks up `tests/fixtures/meta/<sha256 of model+body>.json`; raises `KeyError` naming the stage when a fixture is missing.

- [ ] **Step 1:** Tests with `httpx.MockTransport`: `test_cache_miss_then_hit` (second identical call makes no HTTP request, `cache_hit` true, `cost_usd == 0`); `test_retries_on_500_then_succeeds` (two 500s, then 200; `attempts == 3` in the trace rows); `test_4xx_raises_without_retry`; `test_trace_fields` (model, request_id from `x-request-id`, tokens from `usage`, latency_ms > 0, cost via pricing); `test_authorization_header_is_bearer_and_never_logged` (caplog does not contain the key); `test_fake_client_raises_on_missing_fixture`.
- [ ] **Step 2:** Run `pytest tests/test_meta_client.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `client.py` and `fake.py`. Cache file = `cache/<key>.json` storing the raw response plus `usage`.
- [ ] **Step 4:** Run tests. Expected: PASS. Then run `.venv/bin/python -m parity.meta.client --check` (prints the model ids via the free `GET /models`, nothing else). Expected: list includes `muse-spark-1.3`.
- [ ] **Step 5:** Commit `feat: meta client with disk cache, retries and per-call trace`.

### Task 4: Demo store v1 served by the app

**Files:**
- Create: `store/checkout.html` (rewrite of `seeds/checkout.html`: same faults and ids `f1 f2 f4 f5 f6 c1 c2 card`, product "Noise-cancelling headphones", "Pay R1,249", `#done` confirmation), `store/style.css`, `parity/app.py`
- Test: `tests/test_store_pages.py`

**Interfaces:**
- Produces: `create_app(settings: Settings | None = None) -> FastAPI` mounting `/store` (StaticFiles) and `/api/health`. `tests/conftest.py` fixture `store_url` starts uvicorn on a free port in a thread and yields `http://127.0.0.1:<port>/store/`.

- [ ] **Step 1:** Test `test_checkout_has_zero_axe_violations` (Playwright loads `store_url + "checkout.html"`, injects `node_modules/axe-core/axe.min.js` from `web/` (Task 11) or a vendored `parity/vendor/axe.min.js` fetched at setup, asserts `len(violations) == 0`); `test_checkout_hero_ids_exist` (ids above present); `test_health_ok`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the page, `app.py`, and `make vendor-axe` (copies `axe.min.js` from `web/node_modules/axe-core/` into `parity/vendor/`; until Task 11, `npm i axe-core@4.14.0 --prefix web`).
- [ ] **Step 4:** Run tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat: ShopRight checkout demo page served at /store`.

### Task 5: Capture

**Files:**
- Create: `parity/pipeline/capture.py`, `parity/pipeline/browser.py` (launch Chromium 1280×720, one shared browser per process)
- Test: `tests/test_capture.py`, fixture writer `tests/record_capture.py` → `tests/fixtures/capture_checkout.json` + `.png`

**Interfaces:**
- Produces: `async capture(page: Page, step_index: int) -> Capture`; `Capture(url, viewport, screenshot_png: bytes, ax_nodes: list[AxNode], axe_violations: list[AxeViolation], captured_at)`; `AxNode(backend_id, role, name, css_path, box_px: tuple[int,int,int,int] | None, bbox: BBox | None, outer_html: str | None, dom_id: str | None)`; `AxeViolation(id, impact, targets: list[str], backend_ids: list[int])`.
- `to_grid(px_box, viewport) -> BBox` (x/1.28, y/0.72 at 1280×720, rounded).

- [ ] **Step 1:** Tests on the live store page: `test_ax_contains_submit_button` (some node has `role == "button"` and `name == "Submit"` and `dom_id == "f5"`); `test_canvas_price_has_no_ax_name` (no node with name containing "1,249"); `test_boxes_on_grid` (every bbox within 0–1000 and `x_min < x_max`); `test_axe_violations_empty`; `test_filtered_roles` (no `generic`, `StaticText`, `InlineTextBox`); `test_to_grid`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with CDP `Accessibility.getFullAXTree`, `DOM.getBoxModel`, `DOM.resolveNode` + `Runtime.callFunctionOn` for `outerHTML`, `id` and a CSS path (`tag#id` when an id exists, else `tag:nth-of-type` chain).
- [ ] **Step 4:** Run tests. Expected: PASS. Run `python tests/record_capture.py` to write the fixture.
- [ ] **Step 5:** Commit `feat: deterministic capture (screenshot, AX tree, boxes, axe)`.

### Task 6: Verifier

**Files:**
- Create: `parity/pipeline/verifier.py`
- Test: `tests/test_verifier.py` (table-driven on `tests/fixtures/capture_checkout.json`)

**Interfaces:**
- Produces: `verify(candidate: Candidate, capture: Capture, prior: list[Finding]) -> VerifierResult`; `VerifierResult(passed: bool, checks: dict[str, Check], element: Element | None, feedback: str | None)`; check names `located, sr_quote_exact, diverges, not_axe, unique`. Helpers: `normalise(s) -> str`, `iou(a: BBox, b: BBox) -> float`, `locate(bbox, nodes) -> AxNode | None`, `NOT_ANNOUNCED = "not announced"`.

- [ ] **Step 1:** Tests: `test_hero_passes` (candidate sighted "Pay R1,249", sr `button, "Submit"`, bbox of `#f5` → passed, all five checks true); `test_quote_whitespace_case_normalised` (`'Button, " submit "'` passes); `test_wrong_quote_fails_with_feedback` (sr "Pay now" → `sr_quote_exact` false, feedback mentions "exact role and name"); `test_no_divergence_fails` (sighted "Save for later" on `#c2` → `diverges` false); `test_missing_bbox_fails_located`; `test_out_of_range_bbox_fails_located`; `test_canvas_not_announced_passes` (`#f2`, sr `NOT_ANNOUNCED`); `test_not_announced_rejected_when_named` (`#c1` with `NOT_ANNOUNCED` → false); `test_axe_target_rejected` (inject a fake axe violation on `#f5` → `not_axe` false); `test_duplicate_rejected`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Feedback strings are instructions ("quote the exact role and accessible name of the element inside the box"), never labels.
- [ ] **Step 4:** Run tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat: verifier gates (located, exact quote, diverges, not axe, unique)`.

### Task 7: Seer and Comparator

**Files:**
- Create: `parity/pipeline/seer.py`, `parity/pipeline/comparator.py`, `parity/meta/prompts/seer.txt`, `parity/meta/prompts/comparator.txt`, `parity/meta/images.py` (`png_to_data_url`), `scripts/record_fixtures.py`
- Test: `tests/test_seer.py`, `tests/test_comparator.py`, fixtures `tests/fixtures/meta/*.json`

**Interfaces:**
- Produces: `async see(client, capture, run_id) -> list[Percept]`; `async compare(client, capture, percepts, run_id, feedback: list[str] | None = None, *, use_screenshot=True, use_tree=True) -> list[Candidate]` (the two flags are the ablation switches).
- Prompts: Seer = "You are an object grounding expert…" listing visible elements with text and box; Comparator = the validated doc-17 prompt plus the percept list, JSON `{"findings":[{"what_sighted_user_sees","what_screen_reader_says","why_it_matters","bbox"}]}`, with the AX tree as `role, name, bbox` triples. `reasoning.effort = "medium"`, `text.format = json_object`, `max_output_tokens = 6000`.
- `parse_candidates(text) -> list[Candidate]`: unparseable or wrong shape → `[]`.

- [ ] **Step 1:** Tests with `FakeMetaClient`: `test_parse_candidates_valid`, `test_parse_candidates_garbage_returns_empty`, `test_compare_includes_feedback_in_prompt` (fake records the body; feedback text present), `test_compare_no_tree_omits_ax` (ablation flag removes the tree block), `test_seer_percepts_clamped`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. `scripts/record_fixtures.py` runs seer + comparator once live on the checkout capture (cached) and copies the cache files into `tests/fixtures/meta/`.
- [ ] **Step 4:** Run tests. Expected: PASS. Run the recorder; confirm the comparator fixture contains a candidate at `#f5`.
- [ ] **Step 5:** Commit `feat: seer (grounding) and comparator with ablation flags`.

### Task 8: Judge

**Files:**
- Create: `parity/pipeline/judge.py`, `parity/meta/prompts/judge.txt`
- Test: `tests/test_judge.py`

**Interfaces:**
- Produces: `async judge(client, finding, capture, run_id) -> Judgement`. JSON `{"is_barrier": bool, "severity": "...", "wcag": [{"sc": "1.1.1", "name": "..."}], "impact": "..."}`. `is_barrier is not True` or unparseable → `Judgement(is_barrier=None, severity="needs_review", …)`.

- [ ] **Step 1:** Tests: `test_judge_hero_is_barrier` (fixture → `is_barrier is True`, severity in the enum, a `wcag` entry); `test_judge_unparseable_needs_review`; `test_judge_list_instead_of_bool_needs_review`.
- [ ] **Step 2–5:** Fail, implement, pass, commit `feat: judge (fails closed)`.

### Task 9: Runner, bundle, index and event bus

**Files:**
- Create: `parity/store/bundle.py`, `parity/store/index.py`, `parity/api/events.py`, `parity/pipeline/runner.py`
- Test: `tests/test_bundle.py`, `tests/test_index.py`, `tests/test_runner.py`

**Interfaces:**
- Produces: `RunBundle(root)`: `create(run) / write_step / write_finding / write_rejected / append_trace / append_event / write_run / load(run_id) -> LoadedRun`.
- `RunIndex(db_path)`: `async upsert_run / upsert_finding / insert_call / list_runs / rebuild(data_dir)`.
- `EventBus`: `publish(run_id, Event)`, `subscribe(run_id) -> AsyncIterator[Event]`, `history(run_id)` from `events.jsonl`.
- `async run_single_page(settings, client, bus, bundle, index, flow: Flow) -> Run`. `Flow(id, name, start_url, goal, pages: list[str])` with `FLOWS = {"checkout": Flow(..., start_url="/store/checkout.html", goal="Pay for the order")}` in `parity/flows.py`. Stage order per spec §3; the bundle is written after every stage; a `MetaError` ends the run as `failed`.

- [ ] **Step 1:** Tests: `test_bundle_layout` (paths from spec §5 exist after a fake run); `test_index_rebuild_matches_bundles`; `test_runner_hero_end_to_end` (FakeMetaClient + store page: `run.status == "done"`, one finding with `element.dom_id == "f5"`, `axe_violations == 0`, events in order `run.started, step.captured, seer.done, comparator.candidates, verifier.result…, run.finished`); `test_runner_meta_error_marks_failed` (fake raises `MetaError` → status `failed`, `run.json` has `error`, trace rows exist).
- [ ] **Step 2–5:** Fail, implement, pass, commit `feat: runner writes bundle, index and events`.

### Task 10: API, SSE and Replay

**Files:**
- Create: `parity/api/routes.py`, `parity/api/sse.py`, `parity/replay.py`
- Modify: `parity/app.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: routes from spec §7 (`/runs` POST with `{"flow_id","mode"}`, GET list/detail/events/screenshot). `replay.start(run_id_src, bus, bundle, pace_ms=250) -> Run` copies the source bundle to a new run id and republishes its events with pacing. SSE event format `event: <type>\ndata: <json>\n\n`; a subscriber gets `history()` first, then live events, and the stream closes after `run.finished` or `run.failed`.

- [ ] **Step 1:** Tests via `httpx.AsyncClient(transport=ASGITransport)`: `test_post_replay_run_streams_hero` (POST mode replay on a fixture bundle in a temp `PARITY_REPLAY_DIR`; events contain a `verifier.result` with `sighted_text == "Pay R1,249"`); `test_events_after_finish_replays_history_then_closes`; `test_get_run_detail_includes_trace`; `test_screenshot_png_content_type`; `test_unknown_flow_404`.
- [ ] **Step 2–5:** Fail, implement, pass, commit `feat: api routes, sse stream and replay mode`.

### Task 11: Workbench v1 **[subagent-ok]**

**Files:**
- Create: `web/` (Vite react-ts template, Tailwind via `@tailwindcss/vite`), `web/src/state/reducer.ts`, `web/src/state/types.ts` (mirror of spec §5 and §8), `web/src/components/{Header,SightedPanel,ScreenReaderPanel,FindingsFeed,FindingCard,RejectedRow,TraceDrawer,MetaBadge}.tsx`, `web/src/api.ts`, `web/src/App.tsx`
- Test: `web/src/state/reducer.test.ts` (vitest), `tests/test_web_smoke.py` (Playwright against the built SPA)

**Interfaces:**
- Consumes: routes §7 and events §8.
- Produces: `reduce(state: RunState, ev: ParityEvent) -> RunState`; `RunState{run, steps, findings, rejected, calls, selectedFindingId, mode}`. Vite `build.outDir = "../parity/static"`; `app.py` serves it at `/` with an SPA fallback. `MetaBadge({model, capability})` renders `Muse Spark 1.3 · computer use` style text.

- [ ] **Step 1:** vitest: `test_reducer_verifier_result_adds_finding_or_rejected`, `test_reducer_model_call_accumulates_cost`, `test_reducer_run_finished_sets_status`. Playwright smoke: open `/`, click **Run the audit** with Replay selected, wait for the card containing `Pay R1,249` and `button, "Submit"`, assert header contains `0 violations`.
- [ ] **Step 2–4:** Fail, implement the layout of spec §9 (header, three columns, trace drawer; rejected rows red; selected finding box green on the screenshot; badges on every model-backed element), pass.
- [ ] **Step 5:** Commit `feat: workbench v1 (stream, panels, findings feed, trace)`.

### Task 12: Phase 1 demo bundle and one-command run

**Files:**
- Create: `fixtures/replay/hero-checkout/` (recorded Live run), `scripts/record_replay.py`
- Modify: `Makefile` (`make demo` = build web, start server on :8080, open browser), `README.md` (stub: run instructions only)

- [ ] **Step 1:** Run Live once on `/store/checkout.html`; copy the bundle into `fixtures/replay/hero-checkout/`; `pytest -q` and `npm test` pass; `make demo` shows the hero in Replay without `MODEL_API_KEY`.
- [ ] **Step 2:** Commit `feat(p1): hero replay bundle and make demo`; `git push origin main`; tag `p1`.

---

# Phase 2: Navigator (computer use) on the purchase flow (Sun 1 Nov morning)

### Task 13: Store pages for the flow
- Create `store/product.html` (Add to cart), `store/cart.html` (Checkout link), link to `checkout.html`; `confirm.html` after pay. Keep every page at 0 axe violations (extend `test_store_pages.py` to all pages). Add flow `purchase` to `FLOWS` (`start_url="/store/product.html"`, goal "Buy the noise-cancelling headphones and pay"). Commit.

### Task 14: Navigator
- Create `parity/pipeline/navigator.py`, `parity/pipeline/actions.py`, test `tests/test_navigator.py`, fixtures from one recorded live flow.
- Produces: `async navigate(client, page, flow, run_id, on_step: Callable[[int], Awaitable[None]], max_turns=12) -> NavResult(turns, finished_text, actions_log)`; `execute(page, action: dict) -> None` with allowlist `ALLOWED = {"click","double_click","type","keypress","scroll","wait","screenshot"}`, chord join `+`, key map (`CTRL→Control, ENTER→Enter, …`); `is_allowed_target(url, settings) -> bool`.
- Tests: `test_execute_rejects_unknown_action` (logged, not raised); `test_keypress_chord_joined`; `test_navigate_fixture_flow_reaches_confirm` (fake turns from fixtures drive the real store; `#done` or confirm page visible; `on_step` called once per turn); `test_target_origin_blocked`.
- Runner: `run_flow` uses `navigate` with `on_step` running capture → seer → comparator → verifier → judge per turn; events `nav.actions`. Commit; push; tag `p2`. UI: Sighted panel badge switches to `computer use` on `nav.actions`.

---

# Phase 3: Fixer, Re-audit and the human gate (Sun 1 Nov afternoon)

### Task 15: Fixer
- Create `parity/pipeline/fixer.py`, prompt `fixer.txt`, test `tests/test_fixer.py`.
- Produces: `async propose_fix(client, finding, capture, run_id) -> Fix`; `apply_fix(page_html: str, element: Element, after_html: str) -> str` (replace the element's `outer_html` once; raise `FixNotApplied` if not found exactly once); `unified_diff(before, after, path) -> str`.
- Tests: `test_fix_hero_removes_aria_label_or_sets_matching_name` (fixture → `after_html` accessible name resolves to text containing "Pay R1,249"), `test_apply_fix_replaces_once`, `test_apply_fix_raises_when_absent`, `test_fix_rejected_when_tag_changes`.

### Task 16: Re-audit
- Create `parity/pipeline/reaudit.py`, test `tests/test_reaudit.py`.
- Produces: `async reaudit(client, browser, page_html, base_url, fix, finding, run_id) -> Reaudit`: `page.set_content(patched, base_url)`, `capture`, locate the element by `css_path`, `gap_closed = normalise(sighted) in normalise(new_name) or normalise(new_name) == normalise(sighted)`; then `compare` on the patched capture and record `comparator_still_flags`.
- Tests: `test_reaudit_hero_gap_closed` (name after == "Pay R1,249"); `test_reaudit_bad_fix_not_closed` (fix that keeps `aria-label="Submit"` → false).

### Task 17: Decision route, patch export, UI approve/reject
- Routes `POST /runs/{id}/findings/{fid}/decision`, `GET /runs/{id}/patch`; runner sets `awaiting_review` when any finding has a fix; `fix.patch` concatenates approved diffs. UI: diff view and before/after on the card, Approve/Reject with a reason, `decision.recorded` flips the card and the header count. Tests: `test_decision_requires_reason`, `test_patch_contains_only_approved`, Playwright smoke clicks Approve in Replay. Commit; push; re-record `fixtures/replay/hero-checkout` with fix + re-audit; tag `p3`.

---

# Phase 4: Demo store v2, eval harness, ablations (Mon 2 Nov morning)

### Task 18: Store v2 with labels **[subagent-ok]**
- Extend the three pages to ~30 seeded axe-passing faults and ~10 clean controls, each with a stable `id` and a `data-parity-kind` free of hints. Kinds: wrong-name, meaningless-alt, pixel-only (canvas/colour), icon-named-wrong, error-visual-only, link-text-mismatch, state-visual-only, hidden-price, placeholder-as-label, decorative-named. Create `eval/labels.json` (`[{page, id, kind, description, clean}]`). Tests: every page 0 axe violations; every label id exists on its page; `test_parity_never_imports_eval` (grep the package).

### Task 19: Eval harness and ablations
- Create `eval/harness.py`, `eval/ablations.py`, `eval/report.py`; results to `eval/results/<ts>.json` and `eval/results/latest.md`.
- Produces: `match(findings, labels) -> Matches` (by `element.dom_id`), `metrics(matches) -> {recall, precision, fp_on_clean, n}`; axe baseline from `axe_violations` targets; per-page tokens, cost, seconds. CLI flags per spec §13; model default `muse-spark-1.3-contributor`.
- Tests: `test_match_by_dom_id`, `test_metrics_arithmetic`, `test_axe_baseline_counts`. Run the full eval (3 runs × 4 configurations ≈ 36 contributor calls per page set); commit the results file.

### Task 20: Eval in the product
- Route `GET /api/eval` reads `eval/results/latest.json`; UI **Eval** tab: table (Parity vs axe-core: recall, precision, n), ablation strip (screenshot-only / tree-only / no grounding / full), cost and time per page. Header numbers come from the same file. Commit; push; tag `p4`.

---

# Phase 5: Hosted no-login deploy, Replay default, README (Mon 2 Nov evening)

### Task 21: Rate limiting and Live guards
- Create `parity/ratelimit.py` (`RateLimiter(per_ip_per_hour, global_per_day, clock)`; `check(ip) -> Allowed | Denied(retry_after_s)`), one-Live-run-at-a-time lock in the runner, 429 responses with JSON `{error, retry_after_s, suggestion: "replay"}`. Tests: `test_per_ip_limit`, `test_global_limit`, `test_second_concurrent_live_429`, `test_replay_unlimited`.

### Task 22: Dockerfile and Cloud Run
- Create `Dockerfile` (two stages per spec §12), `deploy/cloudrun.sh`, `deploy/README.md` (bucket, secret, first deploy, redeploy). Verify locally that `docker build` is not required: Cloud Build builds it. First deploy; confirm `/api/health` returns `models_ok: true` and Replay works from a private window on a phone.

### Task 23: README and submission text
- `README.md`: one line pre-existing vs built this week; the hero; architecture diagram image (`docs/img/architecture.png`, exported from a Mermaid or Excalidraw source in `docs/img/`); "How it acts" (the model decides; allow-listed code acts); what is deterministic; run locally (`cp .env.example .env`, `make setup`, `make demo`); eval numbers from `eval/results/latest.md`; limits and honesty (no compliance claims). Form essays drafted in `docs/21-submission-text.md`.

### Task 24: UI polish for judges
- Replay selected by default with a visible label; a "Live (rate-limited)" toggle; friendly 429; a ≤10 s architecture card in the Eval tab; keyboard focus order and visible focus rings in the workbench itself (it must pass axe too: add `test_workbench_axe_clean`).

### Task 25: Freeze
- Run the cold-review checklist (`docs/submission-checklist.md`) against the hosted URL; fix; commit; push; tag `p5`. Feature freeze Tue 3 Nov 12:00 ET.

---

## Stretch (only after P5)
- Voice Transcribe on a real VoiceOver recording of the checkout (Gate G-V ≥ 90% word accuracy) → `sr_transcript` on the finding and a clip player in the Screen reader panel.
- 2–3 public flows, read-only, counts only, disclosed before naming.
