# Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; the token budget is tight) to implement this plan task-by-task. Use superpowers:subagent-driven-development only for the independent chunks marked **[subagent-ok]**. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ship Parity, an agent that walks a site's key flows, finds the screen-reader gaps axe-core misses, proves them, proposes fixes and leaves the decision to a human, with a hosted no-login demo by Mon 2 Nov.

**Architecture:** FastAPI + async Playwright pipeline (navigator → capture → seer → comparator → verifier → judge → fixer → re-audit → human gate) writing a run bundle on disk and streaming events over SSE to a React workbench. Muse Spark 1.3 perceives; code verifies; the Verifier is the only door a finding can pass through.

**Tech Stack:** Python 3.12, FastAPI 0.162, Playwright 1.64, pydantic 2.14, sse-starlette 3.6, aiosqlite 0.22, httpx 0.28, google-cloud-storage 3.17, pytest 9; React 19.3, Vite 8.3, TypeScript 7, Tailwind 4.3, axe-core 4.14, vitest 5; Cloud Run.

**Spec:** `docs/19-design-spec.md` (scope from `docs/18-decision-and-development-plan.md`).

## Global Constraints
- Every runtime model is a Meta model. Roles per spec §6.1: `muse-spark-1.3-contributor` by default; `muse-wonder-1.0` or `muse-spark-1.3` as judge; standard `muse-spark-1.3` in private mode; `muse-voice-transcribe-1.0` in P6. Model IDs come from settings, never hard-coded in stages.
- `MODEL_API_KEY` comes from `.env` or the environment; it is never printed, logged or committed.
- Every model call is cached on disk (`sha256(model + canonical body)`) and traced: model, request ID, tokens, latency, cost.
- Every computer-use request sets `"truncation": "auto"`. Viewport is 1280×720.
- Boxes are on the 0–1000 grid; the verifier thresholds are `IOU_MIN = 0.2`, `CENTRE_TOLERANCE = 15`.
- No "compliance" wording anywhere. Replay is the default mode. Labels in `eval/` are never imported by `parity/`.
- Tests never call the live API; model-facing code is tested with `FakeMetaClient` over `tests/fixtures/meta/`.
- Each phase ends demoable, committed and pushed to `origin/main`.
- **Integration tests, TDD, every phase** (added in the post-P2 hardening pass): each phase's user-visible behaviour gets a test in `tests/test_integration.py` through the served app (uvicorn + real Chromium + `FakeMetaClient`), written before the feature. P3: approve/reject through the decision route changes the bundle and the SSE stream; patch export round-trips. P4: the eval harness scores a store-v2 run end to end. P5: rate limiting over HTTP; a container smoke test (build the image, hit `/api/health` and one Replay run). P6: a voice run with fixture audio. Run-to-run model variance is measured with `scripts/variance_runs.py` (live, fresh cache), not in CI.

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
- [ ] **Step 4:** `ci.yml`: on push, Python 3.12, `uv pip install -e ".[dev]"`, `playwright install --with-deps chromium`, `pytest -q`; Node 26, `npm ci && npm test` in `web/` (skips until Task 10b creates it: guard with `if: hashFiles('web/package.json') != ''`).
- [ ] **Step 5:** Commit `chore: scaffold parity (python 3.12, pytest, makefile, ci)`.

### Task 2: Config, pricing and data model

**Files:**
- Create: `parity/config.py`, `parity/meta/pricing.py`, `parity/store/models.py`
- Test: `tests/test_config.py`, `tests/test_pricing.py`, `tests/test_models.py`

**Interfaces:**
- Produces: `Settings` (dataclass from env with the names in `.env.example`; `load_settings(env: Mapping | None = None) -> Settings`; loads `.env` via python-dotenv without overriding existing env).
- `cost_usd(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float` using the table `PRICES = {"muse-spark-1.3": (1.25, 0.15, 4.25), "muse-spark-1.3-contributor": (0.10, 0.002, 0.20), "muse-wonder-1.0": (4.00, 0.20, 20.00)}` per 1M; `asr_cost_usd(audio_ms: int) -> float` at $0.18 per hour; unknown model → `0.0` plus a logged warning.
- `Settings` model fields: `model` (default `muse-spark-1.3-contributor`), `judge_model` (default `muse-spark-1.3` until the Task 19 comparison), `private` (bool; when true `model_for(stage)` returns `muse-spark-1.3` for every Spark stage). `model_for(stage: str) -> str` is the only place stages get a model ID.
- pydantic models exactly as spec §5: `Run, Step, Percept, Candidate, Finding, Rejected, Judgement, Fix, Reaudit, Decision, ModelCall, VerifierResult, Check, BBox, Element, AxNode, Capture`. `BBox` has `x_min, y_min, x_max, y_max: int` with a validator clamping to 0–1000. `RunStatus`, `FindingStatus`, `Severity` are `StrEnum`s.

- [ ] **Step 1:** Tests: `test_settings_defaults_replay` (no env → `default_mode == "replay"`, `live_per_ip_per_hour == 3`); `test_model_for_defaults_contributor`; `test_private_mode_uses_standard_spark` (`model_for("comparator") == "muse-spark-1.3"`); `test_settings_never_exposes_key` (`repr(settings)` does not contain the key value); `test_cost_spark13` (`cost_usd("muse-spark-1.3", 1_000_000, 0, 0) == 1.25`); `test_bbox_clamps` (`BBox(x_min=-5, y_min=0, x_max=1200, y_max=10)` → 0 and 1000); `test_finding_roundtrip` (model_dump_json → model_validate_json equality).
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

- [ ] **Step 1:** Test `test_checkout_has_zero_axe_violations` (Playwright loads `store_url + "checkout.html"`, injects `node_modules/axe-core/axe.min.js` from `web/` (Task 10b) or a vendored `parity/vendor/axe.min.js` fetched at setup, asserts `len(violations) == 0`); `test_checkout_hero_ids_exist` (ids above present); `test_health_ok`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the page, `app.py`, and `make vendor-axe` (copies `axe.min.js` from `web/node_modules/axe-core/` into `parity/vendor/`; until Task 10b, `npm i axe-core@4.14.0 --prefix web`).
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
- Produces: `async judge(client, finding, capture, run_id, model: str | None = None) -> Judgement`; `model` defaults to `settings.model_for("judge")`. JSON `{"is_barrier": bool, "severity": "...", "wcag": [{"sc": "1.1.1", "name": "..."}], "impact": "..."}`. `is_barrier is not True` or unparseable → `Judgement(is_barrier=None, severity="needs_review", …)`. A `MetaError` from a non-Spark judge retries once on `muse-spark-1.3` and records `fallback: true` in `Judgement.model_meta`.

- [ ] **Step 1:** Tests: `test_judge_hero_is_barrier` (fixture → `is_barrier is True`, severity in the enum, a `wcag` entry); `test_judge_unparseable_needs_review`; `test_judge_list_instead_of_bool_needs_review`; `test_wonder_error_falls_back_to_spark`.
- [ ] **Step 2–5:** Fail, implement, pass, commit `feat: judge (fails closed)`.

### Task 9: Runner, bundle, index and event bus

**Files:**
- Create: `parity/store/blob.py`, `parity/store/bundle.py`, `parity/store/index.py`, `parity/api/events.py`, `parity/pipeline/runner.py`
- Test: `tests/test_blob.py`, `tests/test_bundle.py`, `tests/test_index.py`, `tests/test_runner.py`

**Interfaces (spec §5.1):**
- Produces: `BlobStore` protocol: `async put(key: str, data: bytes, content_type: str) -> None`, `async get(key) -> bytes`, `async exists(key) -> bool`, `async list(prefix) -> list[str]`. `LocalBlobStore(root: Path)`; `GcsBlobStore(bucket: str, prefix: str = "", client=None)` using `google-cloud-storage` 3.17 via `asyncio.to_thread`. `make_blob_store(settings) -> BlobStore` picks GCS when `PARITY_GCS_BUCKET` is set.
- `RunBundle(store: BlobStore)`: `create(run) / write_step / write_finding / write_rejected / add_trace / add_event / flush(run_id) / write_run / load(run_id) -> LoadedRun / list_run_ids()`. `add_trace`/`add_event` buffer in memory; `flush` rewrites `trace.jsonl` and `events.jsonl` whole. The runner calls `flush` at the end of every stage.
- `RunIndex(db_path)`: `async upsert_run / upsert_finding / insert_call / list_runs / rebuild(bundle: RunBundle)`. `recover_interrupted(bundle) -> list[str]` marks `running`/`queued` runs `failed` ("interrupted by restart"), bundle first.
- `async audit_view(ctx: RunContext, page: Page, step_index: int, reason: str) -> AuditSummary` in `parity/pipeline/audit.py` (spec §18.3): the one unit that turns a screen into findings. The P1 runner calls it directly; in P2 it becomes the agent's tool unchanged. `AuditSummary(verified: list[FindingBrief], rejected: int, axe_violations: int)`.
- `EventBus`: `publish(run_id, Event)`, `subscribe(run_id) -> AsyncIterator[Event]`, `history(run_id)` from `events.jsonl`.
- `async run_single_page(settings, client, bus, bundle, index, flow: Flow) -> Run`. `Flow(id, name, start_url, goal, pages: list[str])` with `FLOWS = {"checkout": Flow(..., start_url="/store/checkout.html", goal="Pay for the order")}` in `parity/flows.py`. Stage order per spec §3; the bundle is written after every stage; a `MetaError` ends the run as `failed`.

- [ ] **Step 1:** Tests: `test_local_blob_roundtrip_and_list`; `test_gcs_blob_uses_client` (a fake `google.cloud.storage` client records `upload_from_string` with the right key and content type; no network); `test_bundle_layout` (keys from spec §5.1 exist after a fake run); `test_flush_rewrites_whole_event_log` (two flushes → one object holding all events, in order); `test_index_rebuild_matches_bundles`; `test_index_failure_does_not_fail_write` (index raises → bundle still written); `test_recover_interrupted_marks_failed`; `test_runner_hero_end_to_end` (FakeMetaClient + store page: `run.status == "done"`, one finding with `element.dom_id == "f5"`, `axe_violations == 0`, events in order `run.started, step.captured, seer.done, comparator.candidates, verifier.result…, run.finished`); `test_runner_meta_error_marks_failed` (fake raises `MetaError` → status `failed`, `run.json` has `error`, trace rows exist).
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

### Task 10b: Workbench design pass (spec §9.1) — can start right after Task 2, in parallel with Tasks 3–10

**Files:**
- Create: `docs/22-workbench-design.md`, `web/` (Vite react-ts scaffold, Tailwind via `@tailwindcss/vite`, tokens in `web/src/theme.css` as CSS variables for light and dark), `web/src/fixtures/hero.json`, `web/src/components/{Header,SightedPanel,ScreenReaderPanel,FindingsFeed,FindingCard,RejectedRow,TraceDrawer,MetaBadge}.tsx`, `web/src/MockApp.tsx` (state switcher: idle, running, hero selected)
- Test: `web/src/components/FindingCard.test.tsx` (renders `Pay R1,249`, `button, "Submit"`, five verifier ticks, badge text `MUSE SPARK 1.3`)

**Interfaces:**
- Consumes: spec §5 and §8 shapes (hand-written in `web/src/state/types.ts`; Task 11 keeps these types).
- Produces: presentational components with props only, no fetching, which Task 11 wires to the reducer.

- [ ] **Step 1:** Write the brief (direction, tokens, three states, anti-patterns) per spec §9.1.
- [ ] **Step 2:** Write the FindingCard test; run `npm test`; expected FAIL.
- [ ] **Step 3:** Build the components and `MockApp` from the fixture; run `npm test`; expected PASS.
- [ ] **Step 4:** `npm run dev`; screenshot the three states at 1280×720 and 1440×900 in the browser pane, light and dark; send them to the builder. **Stop for one review round**; apply changes.
- [ ] **Step 5:** Commit `feat(web): workbench design brief and static mock`.

### Task 11: Workbench v1 **[subagent-ok]**

**Files:**
- Create: `web/src/state/reducer.ts`, `web/src/api.ts`, `web/src/App.tsx` (wires the Task 10b components; `web/` scaffold, types and components come from Task 10b)
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

### Task 13b: Spike, computer use plus function tools in one request (30 min, a few cents)
- Throwaway script in the scratchpad, not committed: one `muse-spark-1.3` request with `tools: [{"type":"computer"}, audit_view, finish]` on the product page screenshot, goal "Buy the headphones; call audit_view on each new screen". Pass = the API accepts the request and, within 4 turns, returns both a `computer_call` and a `function_call`. Record the result and request IDs in spec D9. Fail = take the fallback in spec §18.3.

### Task 14: Auditor agent (spec §18.3)
- Create `parity/agent/loop.py`, `parity/agent/tools.py`, `parity/pipeline/actions.py`, `parity/meta/prompts/auditor.md`; test `tests/test_agent.py`, `tests/test_actions.py`; fixtures from one recorded live flow.
- Produces: `async run_agent(ctx: RunContext, page: Page, flow: Flow, max_turns: int = 12) -> AgentResult(turns, finished: bool, finish_forced: bool, summary: str)`; `TOOLS: dict[str, Tool]` with `Tool(definition: dict, run: Callable[[RunContext, dict], Awaitable[dict]])` for `audit_view` and `finish`; `dispatch(ctx, call) -> dict` (unknown tool → `{"error": "unknown tool"}`; exception → `{"error": str}`; `NotImplementedError` → run `paused`); `execute(page, action: dict) -> None` with allowlist `ALLOWED = {"click","double_click","type","keypress","scroll","wait","screenshot"}`, chord join `+`, key map (`CTRL→Control, ENTER→Enter, …`); `is_allowed_target(url, settings) -> bool`. The loop persists `conversation.json` after every turn and emits `agent.tool_call`, `agent.refused`, `nav.actions`.
- Tests: `test_execute_rejects_unknown_action` (logged, not raised); `test_keypress_chord_joined`; `test_target_origin_blocked`; `test_dispatch_unknown_tool_refused`; `test_finish_refused_when_screen_unaudited` (feedback names the action to take); `test_finish_forced_after_three_refusals`; `test_last_turn_offers_only_finish`; `test_agent_fixture_flow_reaches_confirm` (fake turns drive the real store; `audit_view` called on product, cart and checkout; the hero finding exists; run `done`); `test_fallback_mode_audits_on_screen_change` (agent has only `computer`; code calls `audit_view` when the screenshot hash changes).
- Runner: `run_flow` = `run_agent` (or the fallback loop) → fix batch (P3) → `awaiting_review`. UI: timeline rows for `agent.tool_call` with badges; the Sighted panel badge switches to `computer use` on `nav.actions`. Commit; push; tag `p2`.

### Task 14b: Verifier on and off, post hoc (no model calls)
- Create `parity/cli.py` command `parity verify RUN --off`: re-scores the stored candidates of a run with the Verifier bypassed and writes `verifier_off.json` (`reported`, `false_vs_labels` when labels exist for the page). Route `GET /runs/{id}/verifier-off`; the findings feed gets a toggle "Without the Verifier" that shows the extra, red-outlined findings.
- Tests: `test_verifier_off_reports_all_candidates`, `test_verifier_off_makes_no_model_calls` (FakeMetaClient records zero calls).

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
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - P2-14 agent test gaps, in `tests/test_agent.py` before Task 15 starts: off-origin navigation stops the run with `nav.blocked`; two function calls in one turn are both dispatched in order; `audit_view` on an already-audited screen returns the cached summary without new model calls; a non-empty `pending_safety_checks` is echoed back as `acknowledged_safety_checks`. (The plain-text nudge is covered since the hardening pass.)

# Phase 4: Demo store v2, eval harness, ablations (Mon 2 Nov morning)

### Task 18: Store v2 with labels **[subagent-ok]**
- Extend the three pages to ~30 seeded axe-passing faults and ~10 clean controls, each with a stable `id` and a `data-parity-kind` free of hints. Kinds: wrong-name, meaningless-alt, pixel-only (canvas/colour), icon-named-wrong, error-visual-only, link-text-mismatch, state-visual-only, hidden-price, placeholder-as-label, decorative-named. Create `eval/labels.json` (`[{page, id, kind, description, clean}]`). Tests: every page 0 axe violations; every label id exists on its page; `test_parity_never_imports_eval` (grep the package).
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - Screen identity: `screen_key` hashes URL + a digest of the accessibility tree, so a same-URL state change (the checkout error state) is audited as a new screen. Test: submitting an invalid card on `checkout.html` yields two audited screens.

### Task 19: Eval harness and ablations
- Create `eval/harness.py`, `eval/ablations.py`, `eval/report.py`; results to `eval/results/<ts>.json` and `eval/results/latest.md`.
- Produces: `match(findings, labels) -> Matches` (by `element.dom_id`), `metrics(matches) -> {recall, precision, fp_on_clean, n}`; `judge_agreement(judgements, labels) -> {agreement, needs_review_rate, cost_per_finding}`; axe baseline from `axe_violations` targets; per-page tokens, cost, seconds. CLI flags per spec §13 including `--effort` and `--judge-model`; model default `muse-spark-1.3-contributor`.
- Tests: `test_match_by_dom_id`, `test_metrics_arithmetic`, `test_axe_baseline_counts`, `test_judge_agreement_arithmetic`.
- Runs: full eval (3 runs × 4 ablation configurations); effort sweep (low/medium/high, 1 run each); judge comparison (Spark 1.3 vs Wonder 1.0 on the same verified findings); one standard-tier run to confirm contributor numbers transfer. Set `PARITY_JUDGE_MODEL` and the default effort from the winners and record both in spec D6. Commit the results file.

### Task 19b: Public-site sample (spec §17) — first to drop if the schedule slips
- Modify `parity/cli.py` (add `parity audit --url --goal --public`); create `parity/pipeline/guard.py`, `scripts/anonymise_bundle.py`; test `tests/test_guard.py`.
- Produces: `guard_action(action: dict, target: AxNode | None, field_type: str | None) -> Allowed | Blocked(reason)` with the irreversible-name pattern `IRREVERSIBLE = r"\b(pay|buy|place order|submit|sign ?up|subscribe|confirm|delete|checkout now)\b"` (case-insensitive) and blocked field types `password, cc-number, cc-csc, email, tel`; any `submit` event blocked. `robots_allows(url) -> bool`. `anonymise(bundle, letter)` replaces host, URLs and title with "Site <letter>" and drops screenshots of steps without verified findings.
- Tests: `test_blocks_pay_click`, `test_blocks_password_typing`, `test_allows_add_to_cart_click`, `test_blocks_form_submit`, `test_robots_disallow_stops_run`, `test_anonymise_removes_host` (no original host string anywhere in the output bundle).
- Run 2–3 public flows locally (product → cart, stopping before checkout). Commit only anonymised bundles under `fixtures/replay/public-<letter>/`; keep raw bundles out of git. Record verified-finding counts in `eval/results/public.json`.
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - Capture batching: one CDP round trip per page for the AX tree and box lookups, not three per node (public pages have thousands of nodes). Test: node count and output unchanged on `checkout.html`; CDP call count bounded.

### Task 20: Eval in the product
- Route `GET /api/eval` reads `eval/results/latest.json` and `public.json`; UI **Eval** tab: table (Parity vs axe-core: recall, precision, n), ablation strip (screenshot-only / tree-only / no grounding / full), judge comparison row, cost and time per page, and a "Real-world sample" list of anonymised public runs opening in Replay. Header numbers come from the same file. Commit; push; tag `p4`.

---

# Phase 5: Hosted no-login deploy, Replay default, README (Mon 2 Nov evening)

### Task 21: Rate limiting and Live guards
- Create `parity/ratelimit.py` (`RateLimiter(per_ip_per_hour, global_per_day, clock)`; `check(ip) -> Allowed | Denied(retry_after_s)`), one-Live-run-at-a-time lock in the runner, 429 responses with JSON `{error, retry_after_s, suggestion: "replay"}`. Tests: `test_per_ip_limit`, `test_global_limit`, `test_second_concurrent_live_429`, `test_replay_unlimited`.
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - Model client timeout 300 s → 60 s per spec (retries are now 5× with 429 retryable, done in the hardening pass).
  - The per-IP hash reads the first `X-Forwarded-For` hop behind Cloud Run, falling back to `request.client.host`. Test with a spoofed header from a non-proxy client.
  - Evict a finished run's in-memory event and trace buffers once flushed (history is served from the bundle). Test: buffer empty after `run.finished`; a late SSE subscriber still gets full history.
  - Flush the bundle after each stage, not each screen, so a crash mid-screen keeps the seer and comparator output.

### Task 22: Dockerfile and Cloud Run
- Create `Dockerfile` (two stages per spec §12), `deploy/cloudrun.sh` (idempotent: enable APIs, create bucket, service account with `storage.objectAdmin` on that bucket and `secretAccessor` on the key secret, build, deploy with `PARITY_GCS_BUCKET` and no volume mount), `deploy/README.md` (first deploy, redeploy, teardown). Docker is not needed locally: Cloud Build builds the image.
- App boot: `make_blob_store`, `recover_interrupted`, `index.rebuild`, then serve. `/api/health` adds `storage: "gcs" | "local"` and `runs_indexed`.
- Verify: first deploy; `/api/health` returns `models_ok: true` and `storage: "gcs"`; run one Live audit; redeploy; the run and its decision are still listed and its screenshots load; Replay works from a private window on a phone.
- Carried in from QA pass 2 (1 Nov, docs/23 §6): every Replay click copies a bundle and boot reads every bundle twice (recovery, then rebuild); on a bucket 100 replays ≈ 3,000 sequential object reads at boot. Before the first deploy: recovery reads `run.json` only, in one pass with the rebuild; replay copies are capped (evict the oldest `mode: replay` runs beyond N at boot). `index.html` is already `no-cache` and `/assets/*` immutable (done 1 Nov).
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - SPA deep-link fallback: any non-`/api`, non-`/store` path that is not a file serves `index.html`, so a shared run link opens the workbench. Test: `GET /runs/<id>` returns the SPA; `/api/nope` still 404s.

### Task 23: README and submission text
- `README.md`: one line pre-existing vs built this week; the hero; architecture diagram image (`docs/img/architecture.png`, exported from a Mermaid or Excalidraw source in `docs/img/`); "How it acts" (the model decides; allow-listed code acts); what is deterministic; run locally (`cp .env.example .env`, `make setup`, `make demo`); eval numbers from `eval/results/latest.md`; limits and honesty (no compliance claims; the prompts do not yet mark page text as untrusted — hosted Live is restricted to our store and public runs sit behind the read-only guard; model-facing tests answer from recorded stage responses). Form essays drafted in `docs/21-submission-text.md`.

### Task 24: UI polish for judges
- Replay selected by default with a visible label; a "Live (rate-limited)" toggle; friendly 429; a ≤10 s architecture card in the Eval tab; keyboard focus order and visible focus rings in the workbench itself (it must pass axe too: add `test_workbench_axe_clean`).
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - Already done in the hardening pass: workbench axe-clean in all three states; keyboard tab ring and visible focus rings (`test_workbench_is_keyboard_reachable_with_visible_focus`).
  - Finding card: one button for selection, not a button wrapping the whole card (invalid content model, very long accessible name). Test: the card's button name is the sighted text only.
  - Below 1280 px the three columns stack (sighted, screen reader, findings). Test: smoke test at 768 px with no horizontal scroll.
- Carried in from QA pass 2 (1 Nov, docs/23 §6):
  - Boxes drawn on the screenshot need a minimum 24×24 px hit area (WCAG 2.5.8) without changing the visible box; the sighted panel should take more of the width at 1280 px.
  - Timeline wording for judges: `audit_view` → "audit this screen", `computer_action_requires_confirmation` → "confirm-to-proceed", "gated tool" explained once.
  - Verifier check details and request ids are hover-only (`title`); expose them to keyboard and touch (a details row or a tooltip on focus).
  - Idle state: one line saying what Parity is, that Replay is a recorded run with no model calls, and a legend of the Meta models in the pipeline; a glossary line for recall and precision on the Eval tab.
  - "Rejected" means two things (the Verifier's rejected candidates in the header; a human's Reject on a card): rename one.

### Task 25: P5 close
- **Pre-submission checklist (decided 31 Oct after the QA pass, docs/23 §5):**
  - **Remove** the third-party documents before the final push: `docs/hackathon/01-*`, `02-*`, `03-*`, `docs/learnings/11*`, `12a*`, `13*`. Keep local copies outside the repo. Verify with `git ls-files docs/hackathon docs/learnings`.
  - **Untrack the coding-assistant files** (decided 31 Oct): `git rm -r --cached` the local assistant instruction file and its settings directory and add both to `.gitignore`, so they stay on disk for local work but leave the public tree. Then review every remaining tracked mention of the assistant (a case-insensitive grep over the tree, excluding fixtures and the lockfile) and remove or reword each. Note: this cleans the final tree only; earlier commits still contain these files. Purging them from history too would need a second rewrite that changes past trees (not just messages) — decide at the time; it is not required for the final tree to be clean.
  - **Done 31 Oct:** co-author trailers removed from five early commit messages (message-only rewrite; every tree, author, committer and date unchanged; `main` and tags p1–p3 re-pushed).
  - **Decide** whether `HACKATHON_SCOPE.md` carries a line disclosing AI coding assistance. Open question; not required by the rules as read (Art. II.3 asks that original contributions be identifiable, which the scope file does).
  - Per-run cap: **15 min** (`PARITY_RUN_TIMEOUT_S=900`, spec §15 updated); the user accepted 10–15.
- Redeploy; commit; push; tag `p5`. The cold-review checklist (`docs/submission-checklist.md`) runs against the hosted URL after P6, Tue 3 Nov 11:00–12:00 ET, then feature freeze at 12:00 ET. If P6 is not done by 11:00, ship without Voice and say so in the README.

---

---
- Carried in from the P1/P2 reviews and the post-P2 hardening pass (ledger: `.superpowers/sdd/20-implementation-plan/progress.md`):
  - Manual VoiceOver pass by the builder (Cmd+F5, tab through a Replay run, open a finding) before the cold review; note the result in `docs/submission-checklist.md`.

# Phase 6b: External benchmark on pages we did not make (W3C BAD) — Mon 2 Nov [D11, doc 18 §11, doc 19 §19]

The VoiceOver pass over the workbench (docs/24) is **not a gate** for Phase 6b or Phase 6 (ruled Mon 2 Nov, docs/25 §2): its outcome is wording and
announcement fixes in `web/src`, which land after Task 28 so one change touches the UI at a time. Phase 6 runs in a fresh chat from the kickoff in docs/25 §5.

Two gates. **Core** (Tasks 26E.1–26E.3) by Mon 15:00 SAST; **hosted** (26E.4–26E.5) by Tue 12:00 SAST. A gate missed is dropped, not squeezed.
Runs use `muse-spark-1.3-contributor` for the eval and `muse-spark-1.3` for the recorded Replay bundles; every call is cached and traced as usual.

### Task 26E.1: Labels we did not write
- Create `eval/labels_external.json` from the BAD annotations of `before/{home,news,tickets,survey}.html` (one row per `#annot_NN`, `in_scope` by kind
  per doc 19 §19.1, an `anchor` per row) and the repaired counterparts on `after/*` as `clean: true` rows. Keep the W3C copyright line in the file header.
- Test `tests/test_eval_external.py::test_external_labels_are_well_formed`: every row has page, id, kind, in_scope, anchor with exactly one key,
  clean; ids unique; every before-page fault row has a counterpart or an explicit `"no_counterpart": true`.

### Task 26E.2: Anchor matching in the harness
- `eval/harness.py`: `label_for(element, sighted_text, labels) -> str | None` (nearest-id rule first, then `src` file name in the element's outer HTML,
  then normalised `text` equality with the sighted text, then `css` path); `match()` and the axe baseline use it; `--external` selects the external
  label file and the absolute page URLs; results land in `latest.json["external"]` per doc 19 §19.1.
- Tests (deterministic, fixtures only): `test_label_for_prefers_dom_id`, `test_label_for_matches_src_file_name`, `test_label_for_matches_visible_text`,
  `test_external_metrics_count_in_scope_only_and_report_out_of_scope`, `test_axe_baseline_scored_by_the_same_anchor`.

### Task 26E.3: The runs and the numbers
- `python -m eval.harness --external --runs 2` (16 runs, ~$1.50). Record cost and seconds. Write the `external` block; `eval/report.py` renders it;
  the Eval tab gains the row group "External pages (W3C BAD)" with the in-scope note (vitest `EvalTab.test.tsx: renders the external row with its
  subset note`); the README eval table gains the row with the subset stated in words. Commit `eval/results/latest.json` and `final.json` as for Task 19.
- **Gate (core):** numbers exist with n stated, or the row says "not run" and nothing is claimed.

### Task 26E.4: Judge-runnable external flows
- `parity/flows.py`: `Flow.public`, `Flow.attribution`, `EXTERNAL_FLOWS` (doc 19 §19.2); `GET /api/flows` returns both fields; `start_run` passes
  `public=flow.public`, `base_url=origin`; `PARITY_EXTERNAL_FLOWS` toggles the group.
- Tests: `tests/test_api.py::test_external_flows_are_public_and_listed_with_attribution`, `tests/test_runner.py::test_external_flow_runs_public_and_never_fixes`
  (FakeMetaClient; asserts no fixer call and the guard active); vitest `Header.test.tsx: names an external flow's site, never the store` and
  `Workbench.test.tsx: external runs expect no fixes`.
- UI: the flow picker groups "External page (W3C demo, read-only)"; the attribution line under the header; `fixesExpected=false` for `public` flows.

### Task 26E.5: Replay bundles and the record
- Record `fixtures/replay/runs/bad-{home,news,tickets,survey}` once each (`scripts/record_replay.py` with the flow id), add the `NOTICE`, add the
  W3C BAD row to `HACKATHON_SCOPE.md`, the public samples list in `eval/results/public.json`, and a line in the video script where the external
  page is shown. Smoke: `tests/test_web_smoke.py::test_external_replay_plays_with_attribution`.
- **Gate (hosted):** a judge can pick "W3C demo: home" and watch it in Replay for free, or run it Live within the limits.

---

# Phase 6: Voice, real screen-reader audio (Mon 2 Nov night to Tue 3 Nov 11:00, before the freeze)

Exit check: in Replay, selecting the hero finding plays the VoiceOver segment saying "Submit, button", shows its Voice Transcribe transcript with the badge *Muse Voice Transcribe · real VoiceOver audio*, and the card shows `transcript_agrees` ticked. G-V accuracy is shown beside it.

### Task 26: Recording kit (manual step for the builder)
- Create `scripts/vo_focus_logger.js` (injected into the store page; logs `{t_ms, dom_id}` on every focus or VoiceOver cursor change via `focusin` and a `MutationObserver` on `aria-activedescendant`, posts to `POST /api/voice/focuslog` in dev only) and `docs/voice-recording.md` (exact macOS steps: VoiceOver on, speech rate, record system audio with a named free tool, export WAV 16 kHz mono 16-bit, save the VoiceOver caption text).
- Deliverable: `store/voice/checkout.wav`, `checkout.json` (focus log) and `checkout.captions.txt` committed; then the same for product and cart if time allows. **Can be recorded any time after Task 13; ideally during the Sun tester session.**
- Captions by script, not by hand (docs/25 §3): with "Allow VoiceOver to be controlled with AppleScript" on, `osascript -e 'tell application "VoiceOver" to return content of last phrase'` returns the text just spoken; `scripts/vo_captions.sh <seconds>` polls it every ~120 ms and writes `{t_ms, text}` lines, which become `checkout.captions.txt` and the `word_accuracy` reference in Task 27.

### Task 27: Transcribe and align
- Create `parity/voice.py`; test `tests/test_voice.py` with a cached transcribe fixture.
- Produces: `async transcribe_page(client, page: str) -> PageVoice` (keywords = AX names on that page; mode `PUSH_TO_TALK`); `align(transcript_turns, focus_log) -> dict[dom_id, Segment(start_ms, end_ms, text)]`; `word_accuracy(hypothesis, reference) -> float` (1 − WER on normalised words); `transcript_agrees(segment, ax_role, ax_name) -> bool`.
- Tests: `test_align_assigns_turns_by_time`, `test_word_accuracy_identical_is_one`, `test_word_accuracy_arithmetic`, `test_transcript_agrees_submit_button`, `test_missing_clip_returns_none` (pages without a recording skip Voice cleanly).

### Task 28: Voice in the pipeline and UI
- Runner: after `verify`, attach `Finding.voice` when the page has a clip; emit `voice.transcribed`. Gate G-V: `accuracy >= 0.90` → hero shows Voice as primary evidence; else as corroboration with the accuracy. Serve clips at `/store/voice/*.wav` with HTTP range support so the player can seek to a segment.
- UI: clip player in the Screen reader panel scoped to the selected finding's segment; transcript line; badge. vitest: `test_reducer_attaches_voice`; Playwright smoke: the hero card has an audio element with a `#t=` fragment.
- Re-record `fixtures/replay/hero-checkout` with Voice; commit; push; tag `p6`. Update README and the video script with the G-V result.

---

# Stretch (only if P1–P6 land by Mon 2 Nov night; otherwise skip)

### Task 29: Single agent vs multi-agent evaluation (spec §18.4)
- Create `parity/agent/multi.py` (coordinator with `delegate`; navigator, inspector, critic loops; instructions in `parity/meta/prompts/multi_*.md`), `eval/architectures.py`; test `tests/test_multi_agent.py`.
- Produces: `async run_multi_agent(ctx, page, flow, budget: Budget) -> AgentResult` with the same return type as `run_agent`; `Budget(max_turns: int, max_tokens: int)` shared by both architectures and enforced in the client wrapper; harness flag `--orchestration single|multi`; `jaccard(a: set[str], b: set[str]) -> float` over finding dom ids across runs.
- Tests (FakeMetaClient): `test_multi_inspector_candidates_pass_through_verifier` (a bad candidate is rejected exactly as in single-agent); `test_multi_budget_exceeded_marks_unfinished`; `test_critic_unparseable_needs_review`; `test_jaccard_arithmetic`; `test_multi_never_served` (no API route can start a multi-agent run).
- Run: 3 runs per architecture on product, cart and checkout with `muse-spark-1.3-contributor`; write `eval/results/architectures.json`; add the row to the Eval tab and README with n disclosed. Commit; push.
