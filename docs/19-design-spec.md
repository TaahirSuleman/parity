# 19 — Design spec

**Status:** DRAFT for approval, Fri 30 Oct 2026. Implements doc 18 (scope is fixed there). Decisions taken in the 30 Oct brainstorm are marked **[D30]**.
**Precedence:** constitution > doc 18 > this doc > doc 20 (plan).

## 1. Decisions taken on 30 Oct [D30]
| # | Decision | Why |
|---|---|---|
| D1 | Toolchain via Homebrew: `python@3.12`, `node` (26), `uv`. No local Docker; the image builds on Cloud Build. | The Mac has Python 3.9 only. Vite needs Node. |
| D2 | **Host: Google Cloud Run** (one container, `min=max=1`, CPU always allocated, 2 vCPU / 2 GiB, 60-min request timeout). Run bundles persist on a **Cloud Storage bucket mounted as a volume** at `/data`. The SQLite index lives on the container's local disk and is rebuilt from the bundles on start. | $150 free credit; HTTPS and a public URL for free; the builder knows GCP. SQLite WAL is unsafe on a FUSE mount, so the index is derived, never the truth. `max=1` keeps the in-memory rate limiter and the warm Chromium consistent. |
| D3 | Voice Transcribe (Gate G-V) is a stretch after P5. The AX tree is the screen-reader truth. `Finding.sr_transcript` stays optional. | Time. |
| D4 | **Approve fix = record the decision + export a `.patch`.** Re-audit runs on an in-memory patched copy. The hosted store never mutates. | Judges share the store; approval still lands live in the active run via SSE, and old runs keep their decisions. |
| D5 | Stack versions pinned: FastAPI 0.162, uvicorn 0.54, Playwright 1.64, pydantic 2.14, sse-starlette 3.6, aiosqlite 0.22, httpx 0.28, pytest 9; React 19.3, Vite 8.3, TypeScript 7.0, Tailwind 4.3, axe-core 4.14, vitest 5. | Latest on 30 Oct. |
| D6 | Model roles: Spark 1.3 `reasoning.effort` = low (navigator), medium (seer, comparator, judge, fixer). `-contributor` for the eval harness only. | Measured in doc 17; cost. |
| D7 | Public-site runs are out of the plan (stretch). | Budget. |

## 2. Repo layout
```
parity/                 Python package (the agent + server)
  app.py                FastAPI factory; mounts /api, /store, / (SPA)
  config.py             settings from env (pydantic-settings style, hand-rolled)
  api/routes.py         REST routes      api/sse.py  event bus → SSE
  meta/client.py        Meta API client: cache, retries, trace     meta/pricing.py   price table
  meta/prompts/*.txt    one file per model-facing prompt
  pipeline/runner.py    orchestrates a run; emits events; writes the bundle
  pipeline/navigator.py capture.py seer.py comparator.py verifier.py judge.py fixer.py reaudit.py
  store/bundle.py       run bundle on disk (truth)   store/index.py  SQLite index   store/models.py  pydantic types
  replay.py             replays a bundle as paced events
  ratelimit.py          per-IP and global Live limits
web/                    React + Vite + TS + Tailwind workbench (built into parity/static at image build)
store/                  ShopRight demo store (static HTML/CSS/JS), served at /store
eval/                   labels.json (outside the agent's import path), harness.py, ablations.py, results/
fixtures/replay/<run>/  committed hero run bundle for Replay mode
tests/                  pytest; tests/fixtures/meta/*.json are cached model responses
Dockerfile  Makefile  pyproject.toml  deploy/cloudrun.sh  README.md
```
`seeds/` stays as the validation record and is not imported.

## 3. Pipeline modules and interfaces
All stages are plain async functions over pydantic models. The model perceives; code decides. Every model-facing stage takes a `MetaClient` so tests inject a fake backed by fixtures.

| Stage | Signature | Model call | Deterministic checks inside |
|---|---|---|---|
| Navigator | `next_actions(ctx, screenshot) -> NavTurn` | Spark 1.3, `tools:[{type:"computer"}]`, `truncation:"auto"`, `previous_response_id` | Action allowlist (click, double_click, type, keypress, scroll, wait, screenshot); anything else is dropped and logged. Chords joined with `+`. Viewport fixed 1280×720. Max 12 turns. Target origin must be allowed (Live-hosted: the store only). |
| Capture | `capture(page) -> Capture` | none | PNG; CDP `Accessibility.getFullAXTree` filtered (drop generic/none/StaticText/InlineTextBox/LineBreak/RootWebArea); per node: role, name, backendNodeId, CSS path, DOM box in px and 0–1000; `axe.run` violations; `outerHTML` per interactive node. |
| Seer | `see(client, capture) -> list[Percept]` | Spark 1.3 grounding, JSON | Boxes clamped to 0–1000; empty list is valid. |
| Comparator | `compare(client, capture, percepts, feedback=None) -> list[Candidate]` | Spark 1.3, JSON | Shape validation; unparseable → `[]` and a `comparator.unparseable` event (fails closed). |
| Verifier | `verify(candidate, capture, prior: list[Finding]) -> VerifierResult` | none | §4. |
| Judge | `judge(client, finding, capture) -> Judgement` | Spark 1.3, JSON | Unparseable or `is_barrier` not a strict bool → `needs_review` (fails closed). |
| Fixer | `propose_fix(client, finding, capture) -> Fix` | Spark 1.3, JSON | Patched snippet must parse and must still contain the element's tag; the diff is computed in code. |
| Re-audit | `reaudit(client, page_html, fix, finding) -> ReauditResult` | none, then Comparator on the patched page | `gap_closed` is decided by code: the element's new AX name must equal, or contain, the sighted text (normalised); the Comparator result is recorded as a second signal only. |
| Human gate | `decide(run, finding, decision, reason)` | none | Only a decision can move a finding to `approved`/`rejected`; a run with pending fixes is `awaiting_review`. |

**Feedback loop:** a Comparator candidate that fails the Verifier yields an actionable string (for example "the screen-reader quote does not match any element at that box; quote the exact role and name"). The Comparator is re-run once with the feedback list (cap 2 attempts per page). Feedback never includes labels; the agent folder cannot import `eval/`.

**Run loop (`runner.py`):** goal → for each navigator turn: execute actions → `capture` → `see` → `compare` → `verify` each → `judge` verified → `propose_fix` for judged barriers → `reaudit` → emit events and write the bundle after every stage. A run ends when the Navigator returns text, hits 12 turns, or fails. Single-page flows skip the Navigator (fixed `goto`).

## 4. Verifier (code, the gate every finding must pass)
A candidate becomes a `Finding` only if **all** checks pass. Each check is a named function returning `(passed, detail)`, stored on the finding.

| Check | Rule |
|---|---|
| `located` | The candidate box, on the 0–1000 grid, maps to exactly one AX node: highest IoU ≥ 0.2, or the box centre inside the node's box ± 15 units. |
| `sr_quote_exact` | The quoted screen-reader string equals the mapped node's `role` + `name` after normalisation (trim, collapse whitespace, case-fold). A quote of "not announced" is valid only when no AX node at that box has a non-empty name (for example a `canvas` with `role=presentation`). |
| `diverges` | The quoted sighted text, normalised, is not equal to the AX name. |
| `not_axe` | The mapped node is not a target of an axe-core violation on this capture. Otherwise axe already found it. |
| `unique` | No prior finding in this run maps to the same node (by backendNodeId, then CSS path). |

Evidence recorded, not gated: `sighted_text_in_dom` (the sighted text occurs in the node's `innerText`), which the card shows as "visible text confirmed".

## 5. Data model (pydantic in `store/models.py`; one JSON file per object in the bundle)
```
Run        id, mode(live|replay), flow_id, goal, target_url, status(queued|running|awaiting_review|done|failed),
           started_at, finished_at, axe_violations, findings_verified, findings_rejected, tokens, cost_usd,
           duration_ms, client_ip_hash, error
Step       run_id, index, url, actions[], screenshot(path), ax_tree(path), axe(path), viewport, captured_at
Percept    step_index, visible_text, kind(button|link|text|image|price|error|icon|other), bbox
Candidate  step_index, sighted_text, sr_quote, why_it_matters, bbox, attempt
Finding    id, run_id, step_index, status(verified|judged|fix_proposed|reaudited|approved|rejected),
           sighted_text, sr_role, sr_name, sr_transcript?, bbox, element{backend_id, css_path, box_px, outer_html},
           verifier{passed, checks{name:{passed, detail}}}, judgement?, fix?, reaudit?, decision?
Rejected   same as Candidate + verifier result (shown as the red row)
Judgement  is_barrier, severity(critical|serious|moderate|minor), wcag[{sc, name}], impact, model_meta
Fix        before_html, after_html, diff(unified), explanation, model_meta
Reaudit    gap_closed(bool), sr_name_before, sr_name_after, comparator_still_flags(bool|null)
Decision   decision(approve|reject), reason, decided_at
ModelCall  id, run_id, step_index?, stage, model, request_id, response_id, prompt_sha256, cache_hit,
           input_tokens, output_tokens, total_tokens, latency_ms, cost_usd, http_status, error, at
```
**Bundle on disk:** `data/runs/<run_id>/{run.json, steps/<n>/{step.json, screenshot.png, ax.json, axe.json}, findings/<id>.json, rejected/<id>.json, trace.jsonl, events.jsonl, fix.patch}`. Only `runner.py` and the decision route write it.
**SQLite index** (`data/index.db`, WAL): tables `runs`, `findings`, `model_calls` with the columns above (JSON blobs for nested parts). Rebuilt by `parity index rebuild` from bundles; used for listing, the eval harness and the cost header.

## 6. Meta client (`meta/client.py`)
- httpx async, `Authorization: Bearer`, base from env. `POST /responses`; `GET /models` as the preflight.
- **Cache:** key = sha256(model + canonical JSON body); `cache/<key>.json`. A hit costs $0 and is traced with `cache_hit=true`. Computer-use turns include `previous_response_id`, so they cache per turn.
- **Retries:** 3 attempts with backoff 1 s, 3 s, 9 s on 5xx and network errors; the request ID (`x-request-id` header, else response `id`) and timestamp go into the trace and the log line for the dev.meta.ai/support report.
- **Trace:** one `ModelCall` per attempt, appended to `trace.jsonl` and the index, and emitted as a `model.call` event. Cost = tokens × `pricing.py` (Spark 1.3: $1.25 in, $0.15 cached, $4.25 out per 1M; contributor: $0.10 / $0.002 / $0.20).
- Outputs are read from `output[].content[].type == "output_text"`; failures are detected by HTTP status only.

## 7. API routes (FastAPI, prefix `/api`)
| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | `{ok, mode_default, live_enabled, models_ok}` |
| GET | `/flows` | demo flows: `checkout` (single page), `purchase` (product → cart → checkout) |
| POST | `/runs` | `{flow_id, mode}` → `{run_id}`. Live is rate-limited (429 with retry-after); Replay returns a new run id backed by the committed bundle. |
| GET | `/runs` | list (index) |
| GET | `/runs/{id}` | full run with findings and trace |
| GET | `/runs/{id}/events` | SSE stream; replays `events.jsonl` first, then live events |
| GET | `/runs/{id}/steps/{n}/screenshot.png` | PNG |
| POST | `/runs/{id}/findings/{fid}/decision` | `{decision, reason}` |
| GET | `/runs/{id}/patch` | `fix.patch` for approved fixes |
| GET | `/eval` | latest `eval/results/*.json` summary and ablations |
Static: `/store/*` demo store, `/` the SPA. Local one-command run: `make demo` (installs, builds, starts on :8080, opens the workbench).

## 8. SSE events (`{type, run_id, at, data}`)
`run.started`, `nav.actions {turn, actions[]}`, `step.captured {index, url, axe_violations, ax_nodes}`, `seer.done {index, percepts}`, `comparator.candidates {index, n, attempt}`, `verifier.result {candidate, passed, checks, finding_id?}`, `judge.result {finding_id, judgement}`, `fixer.proposed {finding_id, diff}`, `reaudit.result {finding_id, gap_closed, before, after}`, `model.call {stage, model, request_id, tokens, latency_ms, cost_usd, cache_hit}`, `decision.recorded {finding_id, decision}`, `run.finished {summary}`, `run.failed {error}`.
Replay emits the same events from `events.jsonl` with 250 ms pacing (×1 or ×2 selectable); screenshots come from the bundle. Replay is labelled in the UI and in every event (`run.mode`).

## 9. Workbench (React SPA; designed around the hero)
Layout at ≥1280 px: header, three columns, trace drawer.
- **Header:** flow name and mode pill (**Live** / **Replay**), **Run the audit** button, axe-core badge (`axe-core · 0 violations`) beside the Parity counter (`Parity · 6 verified · 1 rejected`), cost and time for the run.
- **Left, Sighted:** the latest screenshot with grounding boxes; the selected finding's box in green; percept boxes faint. Badge: *Muse Spark 1.3 · computer use* while navigating, *· grounding* when the Seer runs.
- **Right, Screen reader:** large monospace line for the selected element: `button, "Submit"`; below it the price line `Price: not announced`. Optional VoiceOver clip player (hidden unless the bundle has one). Badge: *Chrome accessibility tree (deterministic)*.
- **Centre, Findings feed:** cards appear as `verifier.result` events arrive. A card shows the sighted crop, the screen-reader quote, the five verifier checks as green ticks, WCAG SC and severity (*Spark · judge*), the fix diff (*Spark · fixer*), the re-audit before/after (*code*), and **Approve** / **Reject** with a reason field. A rejected candidate renders as a red row with the failed check. Hero card: "Pay R1,249" vs `button, "Submit"`.
- **Trace drawer:** table of model calls (stage, model, request ID, tokens, latency, cost, cache hit). **Eval tab:** recall and precision table, axe baseline, ablation strip, cost and time per page.
- Every model-backed element carries a badge naming the Meta model and the capability; deterministic steps say so.

## 10. Demo store (`store/`)
ShopRight, 3 pages: `product.html`, `cart.html`, `checkout.html`, plus `confirm.html`. Checkout keeps the validated hero (`Pay R1,249` with `aria-label="Submit"`, canvas price, red-border error, "Click here" link, trash icon named "Close", alt="image" banner) and two clean controls. V2 adds faults to ~30 and clean controls to ~10, spread across pages, each with a stable `id`. Labels (`eval/labels.json`: page, element id, fault kind, description, clean=false|true) live outside `parity/`. The pages must stay at **0 axe-core violations**; a test asserts it.

## 11. Live and Replay modes
- **Replay (default for judges):** plays the committed hero bundle. No model calls, no key needed. Works offline and in CI.
- **Live:** real Navigator and model calls against the bundled store. Per-IP limit (3/hour) and global limit (40/day) from env; 429 shows a friendly message and offers Replay. On the hosted URL, targets are restricted to the store origin.
- The UI labels the mode everywhere; nothing mock is shown unlabelled.

## 12. Deploy (Cloud Run) [D2]
- `Dockerfile`: stage 1 `node:26` builds `web/` → `parity/static`; stage 2 `mcr.microsoft.com/playwright/python:v1.64.1-noble` installs the package and runs `uvicorn parity.app:create_app --factory --port $PORT`.
- `deploy/cloudrun.sh`: `gcloud builds submit` → Artifact Registry → `gcloud run deploy parity --region us-central1 --min-instances 1 --max-instances 1 --cpu 2 --memory 2Gi --no-cpu-throttling --timeout 3600 --concurrency 20 --allow-unauthenticated --set-secrets MODEL_API_KEY=parity-model-api-key:latest --add-volume name=data,type=cloud-storage,bucket=$BUCKET --add-volume-mount volume=data,mount-path=/data`.
- Env on Cloud Run: `PARITY_DATA_DIR=/data`, `PARITY_CACHE_DIR=/data/cache`, `PARITY_DEFAULT_MODE=replay`.
- Risk: FUSE write latency on PNGs. Mitigation: write the step locally, then copy; the bundle layout is the same. Fallback: local disk only, accepting loss on redeploy (Replay is baked into the image either way).

## 13. Eval harness (`eval/`)
- `harness.py --model muse-spark-1.3-contributor --pages product,cart,checkout [--no-screenshot|--no-tree|--no-grounding] --runs 3`: runs capture → seer → comparator → verifier per page, matches verified findings to labels by element id (a finding matches a label when its mapped node has the label's `id`), and writes `eval/results/<timestamp>.json`: per-page and total recall, precision, false positives on clean controls, axe-core recall on the same labels, tokens, cost and seconds per page.
- `ablations.py` runs the three ablations plus full Parity and writes one table. `--no-grounding` strips boxes before the Verifier, so `located` fails; precision drop is the measurement.
- Labels never enter prompts; a test asserts `eval` is not imported by `parity`.
- Numbers in the README, video and form come from one results file (recipe rule L9).

## 14. Testing
- **TDD (pytest):** verifier (table-driven on the hero capture), capture (against `store/checkout.html` served by Playwright; asserts 0 axe violations and the expected AX names), bundle and index round-trip, replay event order, rate limiter, eval matching, fixer diff application, re-audit `gap_closed` rule.
- **Model-facing code:** `FakeMetaClient` returns fixtures from `tests/fixtures/meta/` keyed by prompt hash; the first live run records them. No live calls in tests.
- **Frontend:** vitest for the event reducer (events → run state); a Playwright smoke test opens Replay and asserts the hero card text.
- CI: GitHub Actions runs pytest and vitest on push.

## 15. Security and limits
- The key is read from env only; logs redact `Authorization`. `.env` is git-ignored; the deny list in `.claude/settings.json` blocks reading it.
- Live runs: allowed origins, 12 navigator turns, 60 s per model call, 10 min per run, one concurrent Live run per server (a queue of 1; others get 429).
- No "compliance" wording anywhere in the UI or docs; findings are evidence and every fix waits for a human.
