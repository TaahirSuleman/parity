# 19 — Design spec

**Status:** DRAFT for approval, Fri 30 Oct 2026; revised Sat 31 Oct: storage (D8), Voice in P6 (D3), model roles (D6), public-site sample (D7), orchestration (D9), Meta integration (D10), workbench design pass (§9.1). Implements doc 18 (scope is fixed there). Decisions taken in the 30 Oct brainstorm are marked **[D30]**.
**Precedence:** constitution > doc 18 > this doc > doc 20 (plan).

## 1. Decisions taken on 30 Oct [D30]
| # | Decision | Why |
|---|---|---|
| D1 | Toolchain via Homebrew: `python@3.12`, `node` (26), `uv`. No local Docker; the image builds on Cloud Build. | The Mac has Python 3.9 only. Vite needs Node. |
| D2 | **Host: Google Cloud Run** (one container, `min=max=1`, CPU always allocated, 2 vCPU / 2 GiB, 60-min request timeout). | $150 free credit; HTTPS and a public URL for free; the builder knows GCP. `max=1` keeps the in-memory rate limiter, event bus and warm Chromium consistent. |
| D8 | **Storage (31 Oct): run bundles are the truth, written through a `BlobStore` interface with two backends.** Local: the filesystem under `PARITY_DATA_DIR`. Cloud Run: objects in a Cloud Storage bucket, written with the `google-cloud-storage` client API (no FUSE mount). **SQLite is a derived cache only**, on local disk, rebuilt from the bundles at boot. | Cloud Run's local disk is in memory and wiped on restart. SQLite WAL is unsafe on a bucket mount, and appends there re-upload the whole object. Filestore (≈$200/mo minimum), Cloud SQL (≈$10/mo), Spanner (≈$65/mo+) and hosted Postgres/libSQL are overkill for a few hundred write-once runs with one writer. Litestream loses to per-run objects during deploy overlap. Firestore is the upgrade path if we ever need more than one instance. |
| D3 | **Voice is in scope as P6** (revised 31 Oct): built after P5 and before the Tue 3 Nov 12:00 freeze. Recorded VoiceOver clips of the store pages are transcribed by `muse-voice-transcribe-1.0`; the transcript corroborates findings and plays in the Screen reader panel (§16). The AX tree stays the gating truth; Gate G-V decides only whether Voice is shown as corroboration or as primary evidence. | The hero is stronger when judges hear what a blind shopper hears. Not early, because P1–P5 carry the demo. |
| D4 | **Approve fix = record the decision + export a `.patch`.** Re-audit runs on an in-memory patched copy. The hosted store never mutates. | Judges share the store; approval still lands live in the active run via SSE, and old runs keep their decisions. |
| D5 | Stack versions pinned: FastAPI 0.162, uvicorn 0.54, Playwright 1.64, pydantic 2.14, sse-starlette 3.6, aiosqlite 0.22, httpx 0.28, google-cloud-storage 3.17, pytest 9; React 19.3, Vite 8.3, TypeScript 7.0, Tailwind 4.3, axe-core 4.14, vitest 5. | Latest on 30 Oct. |
| D6 | **Model roles** (revised 31 Oct; §6.1). Default model `muse-spark-1.3-contributor` for navigator (effort low), seer, comparator and fixer (effort medium). Judge: `muse-wonder-1.0` if the eval shows it beats Spark on label agreement, else Spark 1.3; any Wonder error falls back to Spark. A **private mode** switches every stage to standard `muse-spark-1.3` for sites whose data must not be used for training. | Contributor is the same model at ≈1/12 the price; Meta may train on inputs, which is fine for our store and public pages. A different judge model avoids self-grading and shows Muse models combined. **Measured 1 Nov (eval/results/final.json, commit 1e6caad, 3 runs per page; doc 17):** judge stays `muse-spark-1.3` — agreement with the labels 0.94, the same as `muse-wonder-1.0` on the same 33 verified findings, at $0.011 vs $0.026 per finding; effort stays `medium` for seer and comparator — low 0.84 / 0.97 at $0.35, medium 0.84 / 0.97 at $0.37, high 0.74 / 1.00 at $0.31 (one run each, within noise; the 3-run table was measured at medium); the standard tier gave 0.82 / 1.00 at $0.47 (one run), so private mode costs about 25% more for the same quality. |
| D7 | **Public-site runs are in scope** (revised 31 Oct; §17): 2–3 read-only flows, run locally by CLI in P4, shown in the UI as anonymised Replay bundles. First item dropped if the schedule slips. | Doc 18 §6 requires a real-world sample; it is Impact evidence. Cost is negligible (≈$0.02–0.30 per flow); the constraint is time and site terms. The earlier "budget" reason was wrong. |

| D9 | **Orchestration (31 Oct): one agent with gated tools, not multi-agent** (§18). The auditor agent (Spark 1.3 computer use plus two function tools, `audit_view` and `finish`) decides where to go and when to audit. Seer, comparator, judge and fixer are model calls *inside* tools or code stages, not autonomous agents. **Spike 13b passed (31 Oct):** `muse-spark-1.3` accepted `tools: [computer, audit_view, finish]` with `truncation: auto` and `parallel_tool_calls: false`, and over 6 turns alternated `function_call audit_view` (product, cart, checkout, each before acting) with `computer_call` action batches (click; click+keypress+type to fix the card). 31k tokens, $0.026. Request IDs a931d9e8, cc72c988, dd139de9, 57b6c335, ef3ffd52, dde1c21f. The fallback (code calls `audit_view` on screen change) stays implemented as a mode, not the default. | Matches Meta's workshop pattern (model chooses, code acts, checks inside tools) and scores on Tooling without the cost and unverifiability of agents talking to agents. Every finding still passes through one code gate. |
| D10 | **Meta integration (31 Oct):** our own thin httpx client over the Responses and ASR endpoints, not the OpenAI SDK. Computer-use turns chain with `previous_response_id`; the full item list is still persisted per run for resume and branch. JSON via `json_object` plus code validation; `reasoning.effort` set per role. | The SDK lacks the ASR multipart endpoint and Meta-specific items (`computer_call.actions` batches, 0–1000 `bbox`); a raw client keeps cache keys on the exact request body and reads `x-request-id` directly. `previous_response_id` is the format proven live in doc 17. |

| D11 | **axe-core 4.14 changed the hero's shape (31 Oct, found in Task 4).** 4.14 enables `label-content-name-mismatch` (WCAG 2.5.3) by default, so a *text* button "Pay R1,249" with `aria-label="Submit"` is now an axe violation (it was not in 4.10.2, doc 17). The store therefore renders the pay label and the Terms link as **images with empty alt inside labelled controls**: sighted users still see "Pay R1,249" and "Terms"; the AX tree still says `button, "Submit"` and `link, "Click here"`; axe 4.14 reports 0 violations. The hero and its quotes are unchanged. Rule for store v2: every seeded fault must carry its visible meaning in pixels, structure, colour or position, never in a text node that contradicts the name, because axe now catches the text case. | We audit against the **latest** axe and say so; pinning an old axe would be cherry-picking. Image-text buttons are common in real shops. |

## 2. Repo layout
```
parity/                 Python package (the agent + server)
  app.py                FastAPI factory; mounts /api, /store, / (SPA)
  config.py             settings from env (pydantic-settings style, hand-rolled)
  api/routes.py         REST routes      api/sse.py  event bus → SSE
  meta/client.py        Meta API client: cache, retries, trace     meta/pricing.py   price table
  meta/prompts/*.txt    one file per model-facing prompt
  agent/loop.py tools.py  auditor agent loop and gated tool registry (§18.3)
  pipeline/audit.py     audit_view: capture → seer → comparator → verifier → judge for one screen
  pipeline/runner.py    orchestrates a run; emits events; writes the bundle
  agent/loop.py (the navigator) · pipeline/capture.py seer.py comparator.py verifier.py judge.py fixer.py reaudit.py
  store/blob.py         BlobStore: LocalBlobStore | GcsBlobStore     store/bundle.py  run bundle over a BlobStore (truth)
  store/index.py        SQLite index (derived cache)                 store/models.py  pydantic types
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
| Judge | `judge(client, finding, capture) -> Judgement` | `PARITY_JUDGE_MODEL` (Wonder 1.0 or Spark 1.3), JSON; fallback to Spark on error | Unparseable or `is_barrier` not a strict bool → `needs_review` (fails closed). |
| Fixer | `propose_fix(client, finding, capture) -> Fix` | Spark 1.3, JSON | Patched snippet must parse and must still contain the element's tag; the diff is computed in code. |
| Re-audit | `reaudit(client, page_html, fix, finding) -> ReauditResult` | none, then Comparator on the patched page | `gap_closed` is decided by code: the element's new AX name must equal, or contain, the sighted text (normalised); the Comparator result is recorded as a second signal only. |
| Human gate | `decide(run, finding, decision, reason)` | none | Only a decision can move a finding to `approved`/`rejected`; a run with pending fixes is `awaiting_review`. |

**Feedback loop:** a Comparator candidate that fails the Verifier yields an actionable string (for example "the screen-reader quote does not match any element at that box; quote the exact role and name"). The Comparator is re-run once with the feedback list (cap 2 attempts per page). Feedback never includes labels; the agent folder cannot import `eval/`.

**Run loop:** see §18. In short: one auditor agent drives the browser and calls `audit_view` on each new screen; `audit_view` runs capture → seer → comparator → verifier → judge inside the tool; after the walk, code runs fixer → re-audit per verified barrier, then the run waits for the human. Single-page flows skip the agent and call `audit_view` directly.

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
           sighted_text, sr_role, sr_name, voice?{clip_key, start_ms, end_ms, transcript, agrees}, bbox, element{backend_id, css_path, box_px, outer_html},
           verifier{passed, checks{name:{passed, detail}}}, judgement?, fix?, reaudit?, decision?
Rejected   same as Candidate + verifier result (shown as the red row)
Judgement  is_barrier, severity(critical|serious|moderate|minor), wcag[{sc, name}], impact, model_meta
Fix        before_html, after_html, diff(unified, git-style a/ b/ paths, computed in code), explanation, model_meta
           (P3) Capture carries html = the document as served (page.request.get), persisted as steps/<n>/source.html: the base the fixer
           splices into (element located by id) and the base fix.patch is rebuilt from on every decision (one combined diff per file,
           `git apply --check` clean). The re-audit serves the patched source at the real URL with /api blocked for that page.
Reaudit    gap_closed(bool), sr_name_before, sr_name_after, comparator_still_flags(bool|null)
Decision   decision(approve|reject), reason, decided_at
ModelCall  id, run_id, step_index?, stage, model, request_id, response_id, prompt_sha256, cache_hit,
           input_tokens, output_tokens, total_tokens, latency_ms, cost_usd, http_status, error, at
```
### 5.1 Storage [D8]
Two layers. Only the first holds data; the second can be deleted at any time.

**Layer 1, run bundle (truth).** Keys: `runs/<run_id>/{run.json, steps/<n>/{step.json, screenshot.png, ax.json, axe.json}, findings/<id>.json, rejected/<id>.json, trace.jsonl, events.jsonl, fix.patch}`. Written by the runner, the decision route, boot recovery (which appends a `run.failed` terminal event to an interrupted run) and the verifier-off report cache; Replay copies a bundle under a new id.
- `BlobStore` interface: `put(key, data: bytes, content_type)`, `get(key) -> bytes`, `exists(key)`, `list(prefix) -> list[str]`. No append operation.
- `LocalBlobStore(root)`: files under `PARITY_DATA_DIR` (default `./data`). Used by `make demo`, tests and the eval harness.
- `GcsBlobStore(bucket, prefix)`: `google-cloud-storage` client, calls wrapped in `asyncio.to_thread`. Selected when `PARITY_GCS_BUCKET` is set.
- Every object is written whole. `trace.jsonl` and `events.jsonl` are buffered in memory per run and rewritten as whole objects at the end of each stage, so a crash loses at most the current stage.
- One writer per run (`run.json` and the two logs are rewritten only by that writer), and keys are per run, so two Cloud Run revisions overlapping during a deploy never write the same object.
- Committed Replay bundles live in the image under `PARITY_REPLAY_DIR` and are read through a `LocalBlobStore`; they never depend on the bucket.

**Layer 2, SQLite index (derived cache).** File `PARITY_INDEX_PATH` (default `./data/index.db`; on Cloud Run `/tmp/index.db`), WAL, one process. Tables `runs`, `findings`, `model_calls` with the columns above (JSON blobs for nested parts). Used for listing runs, the trace drawer, the cost header and eval cost-per-page queries.
- Every write goes to the bundle first, then the index. If the index write fails, the request still succeeds and a warning is logged.
- At boot, `rebuild()` lists `runs/*/run.json`, loads each bundle and repopulates the index (≈1 s for a few hundred runs on local disk; on a bucket each bundle costs several round trips and every Replay click adds a bundle, so Task 22 caps or evicts replay copies before the first deploy). `parity index rebuild` runs it by hand.
- At boot, any run whose `run.json` says `running` or `queued` is marked `failed` with error `interrupted by restart`, in the bundle first.
- Locally the index sits on real disk and survives restarts; on Cloud Run it sits on in-memory disk and is rebuilt on every start.

## 6. Meta client (`meta/client.py`)
- httpx async, `Authorization: Bearer`, base from env. `POST /responses`; `GET /models` as the preflight.
- **Cache:** key = sha256(model + canonical JSON body); `cache/<key>.json`. A hit costs $0 and is traced with `cache_hit=true`. Computer-use turns include `previous_response_id`, so they cache per turn.
- **Retries:** 5 attempts with backoff 1 s, 3 s, 9 s, 20 s on 429, 5xx and network errors; the request ID (`x-request-id` header, else response `id`) and timestamp go into the trace and the log line for the dev.meta.ai/support report.
- **Trace:** one `ModelCall` per attempt, appended to `trace.jsonl` and the index, and emitted as a `model.call` event. Cost = tokens × `pricing.py`, per 1M tokens in / cached / out: Spark 1.3 $1.25 / $0.15 / $4.25; Spark 1.3 contributor $0.10 / $0.002 / $0.20; Wonder 1.0 $4.00 / $0.20 / $20.00. Voice Transcribe: $0.18 per audio hour.
- `POST /asr/transcribe` (multipart, `audioEncoding: "WAV"`) is a second method, `transcribe(wav: bytes, keywords: list[str], stage, run_id) -> Transcript`, cached and traced the same way.

### 6.1 Model roles [D6]
| Stage | Model | Effort | Notes |
|---|---|---|---|
| Navigator | `PARITY_MODEL` (contributor) | low | Computer use proven on Spark 1.3; `truncation: "auto"` on every turn |
| Seer, Comparator | `PARITY_MODEL` | medium | Effort chosen by the eval effort sweep (§13); default medium |
| Judge | `PARITY_JUDGE_MODEL` | medium | Wonder 1.0 or Spark 1.3, chosen by the eval judge comparison; fallback to Spark |
| Fixer | `PARITY_MODEL` | medium | Re-audit checks every fix in code |
| Voice | `muse-voice-transcribe-1.0` | n/a | P6; keyword biasing with the page's AX names |
| Private mode | `muse-spark-1.3` for every Spark stage | as above | `PARITY_PRIVATE=true`; Wonder judge stays allowed (standard tier) |
The workbench badge shows the exact model ID per step, so the contributor tier is visible, not hidden.
Expected cost per run with these roles: single page ≈ $0.01 (contributor) plus ≈ $0.03–0.05 per finding if Wonder judges; three-page flow ≈ $0.02–0.05 plus judging.
- Outputs are read from `output[].content[].type == "output_text"`; failures are detected by HTTP status only.

## 7. API routes (FastAPI, prefix `/api`)
| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | `{ok, mode_default, live_enabled, models_ok, storage: "local"\|"gcs", runs_indexed}` |
| GET | `/flows` | demo flows: `checkout` (single page), `purchase` (product → cart → checkout) |
| POST | `/runs` | `{flow_id, mode}` → `{run_id}`. Live is rate-limited (429 with retry-after); Replay returns a new run id backed by the committed bundle. |
| GET | `/runs/{id}` | full run with findings and trace. There is no public list of runs (1 Nov): a run id is the only capability a visitor holds over a run, so a shared link shares its decisions by design, and the count stays in `/health`. Ids are validated before storage (`^[A-Za-z0-9][A-Za-z0-9-]*$`, ≤ 80); anything else is 404. |
| GET | `/runs/{id}/events` | SSE stream; replays `events.jsonl` first, then live events |
| GET | `/runs/{id}/steps/{n}/screenshot.png` | PNG |
| POST | `/runs/{id}/findings/{fid}/decision` | `{decision, reason}` |
| GET | `/runs/{id}/patch` | `fix.patch` for approved fixes |
| GET | `/eval` | latest `eval/results/*.json` summary and ablations |
Static: `/store/*` demo store, `/` the SPA (`/runs/{id}` and `?run={id}` open a run). Local one-command run: `make demo` (installs, builds, starts on :8080, opens the workbench).
Hardening from the stress pass (1 Nov, docs/23 §7): request bodies over 64 KB are refused (413) and no error echoes a body; validation errors never
re-serialise the input; a stored record that no longer parses is one JSON 500. Replay copies: a copy that is still streaming, or younger than
`PARITY_REPLAY_MIN_AGE_S` (2 h), is never evicted; beyond `PARITY_REPLAY_KEEP` (20) only older ones go, at a Replay start and at boot. Shutdown cancels and
awaits every run task (5 s) so a redeploy leaves `run.failed` behind; uvicorn gets a 3 s graceful close.

## 8. SSE events (`{type, run_id, at, data}`)
`run.started`, `nav.actions {turn, actions[]}`, `nav.blocked {turn, action, reason}`, `nav.safety_check {turn, codes, acknowledged, reason}`, `agent.tool_call {turn, tool, args, result}`, `agent.refused {turn, tool, feedback}`, `agent.tool_error {turn, tool, error}`, `voice.transcribed {page, accuracy?}`, `step.captured {index, url, axe_violations, ax_nodes}`, `seer.done {index, percepts}`, `comparator.candidates {index, n, attempt, parse_ok}`, `comparator.unparseable {index, attempt}`, `verifier.result {candidate, passed, checks, finding_id?}`, `judge.result {finding_id, judgement}`, `fixer.proposed {finding_id, diff, fix}`, `fixer.rejected {finding_id, reason}` (snippet refused or fixer error; the finding keeps its evidence), `reaudit.result {finding_id, gap_closed, before, after, reaudit}`, `reaudit.failed {finding_id, reason}`, `model.call {stage, model, request_id, tokens, latency_ms, cost_usd, cache_hit}`, `decision.recorded {finding_id, decision, status, run_status, approved, pending}` (also appended to `events.jsonl` after the run; the client applies the server's decisions from `GET /runs/{id}` when a run finishes or a run link opens, since the stream ends at the terminal event), `run.finished {summary}`, `run.failed {error}`.
Replay emits the same events from `events.jsonl` with a fixed pacing (the ×1/×2 control was dropped); screenshots come from the bundle. Replay is labelled in the UI and in every event (`run.mode`).

## 9. Workbench (React SPA; designed around the hero)
**Default flow (1 Nov):** the header opens on the single-page checkout replay, which reaches the hero finding in about fifteen seconds and always carries it; the Purchase flow (the agent walk, longer, and whose findings vary with where the agent scrolls before it audits) is one pick away in the same control. Its goal tells the agent to leave other cart items alone: on store v2 the seeded carry-case line (quantity error shown only in red) sent two of five recorded walks into a loop on the cart.
Layout at ≥1280 px: header, three columns, trace drawer.
- **Header:** flow name and mode pill (**Live** / **Replay**), **Run the audit** button, axe-core badge (`axe-core · 0 violations`) beside the Parity counter (`Parity · 6 verified · 1 rejected`), cost and time for the run.
- **Left, Sighted:** the latest screenshot with grounding boxes; the selected finding's box in green; percept boxes faint. Badge: *Muse Spark 1.3 · computer use* while navigating, *· grounding* when the Seer runs.
- **Right, Screen reader:** large monospace line for the selected element: `button, "Submit"`; below it the price line `Price: not announced`. From P6: a **VoiceOver clip** player for the selected element's segment, with its Voice Transcribe transcript and a badge *Muse Voice Transcribe · real VoiceOver audio* (§16); hidden for pages without a recording. Badge: *Chrome accessibility tree (deterministic)*.
- **Centre, Findings feed:** cards appear as `verifier.result` events arrive. A card shows the sighted crop, the screen-reader quote, the five verifier checks as green ticks, WCAG SC and severity (*Spark · judge*), the fix diff (*Spark · fixer*), the re-audit before/after (*code*), and **Approve** / **Reject** with a reason field. A rejected candidate renders as a red row with the failed check. On finish the feed opens on the strongest finding whose fix closed the gap, preferring a control over an image or a bare text and a Label-in-Name mismatch over the rest, and scrolls it into view: on the store that is "Pay R1,249" vs `button, "Submit"`.
- **Trace drawer:** table of model calls (stage, model, request ID, tokens, latency, cost, cache hit). **Eval tab:** recall and precision table, axe baseline, ablation strip, cost and time per page.
- Every model-backed element carries a badge naming the Meta model and the capability; deterministic steps say so.

### 9.1 Design pass before building (Task 10b)
No Figma. A written brief plus a static mock in the real stack, reviewed once by the builder before any wiring.
- **Brief** `docs/22-workbench-design.md`: visual direction, colour and type tokens, spacing scale, the three states (idle, running, hero selected), and what the UI must not do.
- **Direction:** an instrument, not a dashboard. The page screenshot dominates; the screen-reader output is large monospace; colour carries meaning only (green verified, red rejected, amber needs review); neutral surfaces in light and dark; no gradients, glass, decorative cards, emoji or stock icons; badges read like instrument labels (`MUSE SPARK 1.3 · GROUNDING`).
- **Mock:** `web/` components rendered from a hand-written hero fixture (`web/src/fixtures/hero.json`, shaped like spec §5 and §8), at 1280×720 and 1440×900. Screenshots go to the builder for one round of changes; Task 11 then wires the same components to SSE.
- **The workbench is itself accessible:** landmarks, focus order, visible focus, contrast AA, run start, run end and each recorded decision announced via live regions; axe-clean (asserted in Task 24).

## 10. Demo store (`store/`)
ShopRight, 3 pages: `product.html`, `cart.html`, `checkout.html`, plus `confirm.html`. Checkout keeps the validated hero (`Pay R1,249` with `aria-label="Submit"`, canvas price, red-border error, "Click here" link, trash icon named "Close", alt="image" banner) and two clean controls. V2 adds faults to ~30 and clean controls to ~10, spread across pages, each with a stable `id`. Labels (`eval/labels.json`: page, element id, fault kind, description, clean=false|true) live outside `parity/`. The pages must stay at **0 axe-core violations**; a test asserts it.

## 11. Live and Replay modes
- **Replay (default for judges):** plays the committed hero bundle. No model calls, no key needed. Works offline and in CI.
- **Live:** real Navigator and model calls against the bundled store. Per-IP limit (3/hour) and global limit (40/day) from env; 429 shows a friendly message and offers Replay. On the hosted URL, targets are restricted to the store origin.
- The UI labels the mode everywhere; nothing mock is shown unlabelled.

## 12. Deploy (Cloud Run) [D2, D8]
- `Dockerfile`: stage 1 `node:26` builds `web/` → `parity/static`; stage 2 `mcr.microsoft.com/playwright/python:v1.64.1-noble` installs the package and runs `uvicorn parity.app:create_app --factory --port $PORT`.
- `deploy/cloudrun.sh`: `gcloud builds submit` → Artifact Registry → `gcloud run deploy parity --region us-central1 --min-instances 1 --max-instances 1 --cpu 2 --memory 2Gi --no-cpu-throttling --timeout 3600 --concurrency 20 --allow-unauthenticated --set-secrets MODEL_API_KEY=parity-model-api-key:latest --service-account parity-run@$PROJECT.iam.gserviceaccount.com --set-env-vars PARITY_GCS_BUCKET=$BUCKET,...`. No volume mount.
- One-time setup in the script: create the bucket in `us-central1` (uniform access, not public), a service account with `roles/storage.objectAdmin` on that bucket only and `roles/secretmanager.secretAccessor` on the key secret.
- Env on Cloud Run: `PARITY_GCS_BUCKET=<bucket>`, `PARITY_INDEX_PATH=/tmp/index.db`, `PARITY_CACHE_DIR=/tmp/cache`, `PARITY_DEFAULT_MODE=replay`. The model response cache is ephemeral on Cloud Run; it is a dev cost saver, not data.
- Screenshots are served by the app from the bucket (`GET /runs/{id}/steps/{n}/screenshot.png`); the bucket is never public.
- Cost: storage and operations for this volume are a few cents a month; the Cloud Run instance dominates.
- Memory budget: in-memory disk counts against the 2 GiB, so the index and cache stay small and Chromium gets the rest. Raise to 4 GiB if memory alerts appear.

## 13. Eval harness (`eval/`)
- `harness.py --model muse-spark-1.3-contributor --pages product,cart,checkout [--no-screenshot|--no-tree|--no-grounding] --runs 3`: runs capture → seer → comparator → verifier per page, matches verified findings to labels by element id (a finding matches a label when its mapped node has the label's `id`), and writes `eval/results/<timestamp>.json`: per-page and total recall, precision, false positives on clean controls, axe-core recall on the same labels, tokens, cost and seconds per page.
- Extra flags: `--effort low|medium|high` (effort sweep for seer and comparator), `--judge-model muse-spark-1.3|muse-wonder-1.0` (judge comparison: agreement of `is_barrier` with labels on verified findings, plus false positives on clean controls, cost per finding). The winners set the defaults in D6 and are recorded in the results file.
- Contributor and standard Spark 1.3 are the same model, so a small check (one run per page on standard) confirms the contributor numbers transfer.
- `ablations.py` runs the three ablations plus full Parity and writes one table. `--no-grounding` skips the Seer: the comparator boxes from the screenshot alone and the Verifier still gates every configuration; the change in recall and in false positives on clean controls is the measurement (measured 1 Nov: 82% / 95% vs full 84% / 97%).
- Labels never enter prompts; a test asserts `eval` is not imported by `parity`.
- Numbers in the README, video and form come from one results file (recipe rule L9).

## 14. Testing
- **TDD (pytest):** verifier (table-driven on the hero capture), capture (against `store/checkout.html` served by Playwright; asserts 0 axe violations and the expected AX names), bundle and index round-trip, replay event order, rate limiter, eval matching, fixer diff application, re-audit `gap_closed` rule.
- **Model-facing code:** `FakeMetaClient` answers from `tests/fixtures/meta/`: an exact prompt-hash fixture when one exists, else the recorded answer for that stage (`stage_defaults`), else a scripted answer. The stage answers were recorded on the v1 checkout page; a prompt or request-shape regression is caught by the live smoke run and the eval, not by these tests (QA pass 2, 1 Nov). No live calls in tests.
- **Frontend:** vitest for the event reducer (events → run state); a Playwright smoke test opens Replay and asserts the hero card text.
- CI: GitHub Actions runs pytest and vitest on push.

## 15. Security and limits
- The key is read from env only; logs redact `Authorization`. `.env` is git-ignored and local tooling is configured never to read it.
- Live runs: allowed origins, 12 navigator turns, 120 s per model call (60 s until Task 21; the comparator's 12,000-token budget needs more), 10–15 min per run (`PARITY_RUN_TIMEOUT_S`, default 900 s; a live purchase run measured 8–9.5 min on store v1 and verifies ~33 findings on store v2, whose fix stage alone outlasts the remainder), one concurrent Live run per server (a queue of 1; others get 429). **The fix stage starts nothing new past 80% of the deadline** (`gate.FIX_BUDGET_FRACTION`): fixes and re-audits that did not start are recorded per finding (`fixer.rejected` / `reaudit.failed` with the budget reason) and the run finishes inside its budget with what it has, instead of being failed by the deadline (1 Nov). Recorded replays may be made with a longer deadline (`record_replay.py --timeout-s`).
- No "compliance" wording anywhere in the UI or docs; findings are evidence and every fix waits for a human.

## 18. Orchestration and the workshop comparison [D9, D10]
### 18.1 What Meta's workshop repo does (meta-models/legal-agent-workshop; analysed in `learnings/12a`, re-checked 31 Oct)
- **Single agent, model-driven loop.** Responses API via the OpenAI SDK, `store=False`, the whole item list resent each turn, one function tool per turn (`parallel_tool_calls=False`). The model picks every tool; the code never hard-codes the order.
- **Checks live inside the tools.** `record_fact` refuses quotes not found in the cached transcript; `submit_memo` runs rules, then an LLM claims judge; refusals return actionable feedback; 3 strikes go to a human.
- **State only via tools.** A case record where only gated tools can mark an item proven or escalated; an audit log of every actor.
- **Run ledger with resume and branch.** Every turn persisted; `resume()` as a state machine (`paused`, `needs_input`, `awaiting_signoff`); `branch()` replays a run with verification switched on so the same trajectory is judged before and after.
- **Offline fake model** behind the real client via an httpx transport.
- **Gaps:** judges fail open; cost is tokens only and only for agent turns; the visual check (signatures with SAM) is a placeholder; ground truth scores coverage only, not accuracy.

### 18.2 Parity compared
| Concern | Workshop | Parity | Verdict |
|---|---|---|---|
| Who decides the next step | Model, every turn | Model for navigation and when to audit; code for the per-screen audit pipeline and the post-walk fix batch | Hybrid. A model-chosen audit order adds cost and variance without improving findings; navigation is where judgement pays. |
| Agents | One | One auditor agent; specialist model calls inside tools | Same as Meta. No agent-to-agent messaging. |
| Gate a finding must pass | Quote on page (code) | Box maps to a real element, exact accessible-name quote, divergence, not axe, unique (code) | Ours is the real multimodal verifier Meta left as a placeholder. |
| Judge failure | Fails open | Fails closed to `needs_review` | Ours. |
| Retry with feedback | 3 tries, non-leaking feedback | Comparator 2 tries with verifier feedback; `finish` 3 refusals then accepted with a flag | Same pattern. |
| Human gate | Sign-off state machine | `awaiting_review`; only a decision moves a finding to approved or rejected | Same pattern. |
| Before and after on one run | `branch()` re-runs with checks on | `parity verify RUN --off` re-scores stored candidates with the Verifier bypassed, no model calls; the UI shows "without the Verifier: N reported, M false" | Same idea, cheaper. Strong demo beat. |
| Cost | Tokens, agent turns only | Every call priced, including calls inside tools | Ours. |
| Accuracy | Coverage judge | Recall and precision vs labels, axe baseline, ablations | Ours. |
| Client | OpenAI SDK, `store=False` | Own httpx client, `previous_response_id` for computer use | Ours, for ASR and Meta-specific items (D10). |

### 18.3 The auditor agent (Phase 2)
- **Request:** `muse-spark-1.3` family per §6.1, `tools: [{"type":"computer"}, audit_view, finish]`, `truncation: "auto"`, `parallel_tool_calls: false`, `instructions` from `meta/prompts/auditor.md`, the flow goal as the first user message with the first screenshot.
- **Tools** (registry in `parity/agent/tools.py`: strict JSON schema, `additionalProperties: false`, unknown tool refused, exceptions returned as `{error}` observations, `NotImplementedError` pauses the run):

| Tool | Args | Inside the tool | Returns to the model |
|---|---|---|---|
| `computer` (built in) | action batch | allow-listed executor; public-mode guard (§17); origin check | screenshot |
| `audit_view` | `{reason: str}` | capture → seer → comparator (≤ 2 tries with verifier feedback) → verifier → judge; findings persisted only here | `{verified: [{id, sighted, screen_reader}], rejected: n, axe_violations: n}`; never labels |
| `finish` | `{summary: str}` | refused if the current screen, by screenshot hash, has not been audited, or no screen was audited; 3 refusals then accepted with `finish_forced: true` | `{accepted}` or `{error, feedback}` |

- **Budgets:** 12 turns; on the last turn only `finish` is offered. One Live run per server.
- **After the walk (code, batch):** for each finding with `judgement.is_barrier is True`: fixer → re-audit; then status `awaiting_review`.
- **Persisted:** `conversation.json` (every request item and response item, screenshots by key) beside the bundle, so a run can be resumed after a crash or branched in eval.
- **Events:** `agent.tool_call {turn, tool, args_summary}`, `agent.refused {turn, tool, feedback}` in addition to §8. The workbench timeline shows each tool call with its Meta-model badge.
- **Fallback if the spike fails** (Spark rejects `computer` plus function tools in one request): the agent gets only `computer`; code calls `audit_view` whenever the screenshot hash changes and treats a text answer as `finish` with the same precondition. Everything else is unchanged.

### 18.4 Stretch: single agent vs multi-agent, measured (Task 29)
A fair comparison, not a strawman: the multi-agent variant gets the same models, the same Verifier gate, the same budgets and the same pages.
- **Multi-agent variant** (`parity/agent/multi.py`, eval-only, never served): a **coordinator** agent with one tool, `delegate(agent, task)`, over three specialist agents, each its own model loop with its own instructions:
  - **Navigator:** computer use only; returns "now on <screen>" when it reaches a new screen.
  - **Inspector:** tools `get_ax_subtree(bbox)`, `crop_screenshot(bbox)` and `propose_candidate(...)`; candidates go through the same Verifier, so the gate is identical.
  - **Critic:** reads verified findings, may call `get_ax_subtree` and `crop_screenshot`, and returns a verdict per finding in the judge's JSON shape (fails closed).
- **Shared budget:** the same total model-turn cap as the single agent (12 navigation turns plus the per-screen audit allowance), and the same token ceiling; a run that exceeds it is scored as unfinished.
- **Metrics per architecture** (3 runs each, store v2, contributor tier): recall, precision, false positives on clean controls, run-to-run variance of the finding set (Jaccard), unfinished-run rate, model calls, tokens, cost and wall time per flow, and Verifier rejection rate (how much noise each architecture generates).
- **Reporting:** one row per architecture in the Eval tab and README, whichever wins. The expected result is that single-agent matches recall at lower cost and variance; if multi-agent wins on recall, that is reported too, and D9 is revisited only after submission.

## 16. Voice: real screen-reader audio (P6) [D3]
- **Recording (manual, the builder, on macOS):** VoiceOver on, rate set to a typical user speed, Safari or Chrome on the local store; navigate each store page with VO+Right through every element; record system audio to WAV, 16 kHz mono 16-bit. One clip per page, stored in `store/voice/<page>.wav` with `store/voice/<page>.json` listing the element order (dom id per VO stop) written during recording by a small helper that logs focus changes.
- **Transcription:** `transcribe(wav, keywords=<AX names on that page>)` with `mode: "PUSH_TO_TALK"`; turns are aligned to elements by the focus log timestamps. Cached; recorded clips are transcribed once per clip and bundled.
- **Use in findings:** non-gating evidence check `transcript_agrees`: the aligned transcript segment, normalised, contains the AX name (for example "Submit, button"). The card shows the clip segment and the transcript beside the AX quote.
- **Gate G-V:** word accuracy of transcripts vs the VO speech text (VoiceOver's caption panel, saved during recording) on the checkout clip. ≥ 90%: Voice is shown as primary evidence in the hero. < 90%: shown as corroboration with the measured accuracy beside it. The AX tree remains the gate either way.
- **Limits:** Live runs on Cloud Run cannot run VoiceOver, so Voice applies to the recorded store pages and their Replay bundles. The UI says so.

## 17. Public-site sample (P4) [D7]
- **CLI only:** `parity audit --url <start> --goal "<text>" --public` runs locally; never from the hosted UI. The hosted Live mode stays restricted to the store.
- **Read-only guard:** in public mode the Navigator's action executor refuses, and ends the flow before, any click on an element whose AX name or text matches pay/buy/place order/submit/sign up/subscribe/confirm/delete, any typing into password, card, email or phone fields, and any form submit. The refusal is logged as `nav.blocked` and the run ends with status `done` and reason `stopped before irreversible step`.
- **Bot walls:** consent banners may be dismissed only with the most privacy-preserving option; CAPTCHAs, bot challenges and logins end the run with reason `blocked by site`. Never bypassed.
- **Politeness:** respect robots.txt for the start URL, one run per site, no parallel requests, ≤ 12 navigator turns.
- **Disclosure:** results are stored as Replay bundles under `fixtures/replay/runs/public-<letter>/` with the host, its URLs and the brand name replaced by "Site A/B/C" in every text file; the agent's own screenshots and transcript are not copied; a step screenshot is kept only where a finding was verified, and masked to the findings' boxes (the evidence stays, the rest of the page does not travel). A bot wall ends the run as `blocked by site` before anything is sent to a model (revised 1 Nov after the P4 review). Counts of verified findings appear in the README and the Eval tab. A site is named only after its owner has been notified.

## 19. External pages: the W3C BAD benchmark now, arbitrary URLs after the event [D11]

### 19.1 Benchmark (Phase 6b)
- **Pages.** `https://www.w3.org/WAI/demos/bad/before/{home,news,tickets,survey}.html` (faults) and `…/after/{same}.html` (controls). Read-only,
  robots.txt honoured (it allows `/WAI/demos/`), one run per page at a time, ≤ 12 turns, the W3C copyright notice kept wherever a screenshot or
  text from the pages is stored. `HACKATHON_SCOPE.md` lists the pages under the W3C document licence once they are used.
- **Labels: `eval/labels_external.json`**, transcribed by hand from the pages' own annotations (`#annot_NN`), one row per annotation:
  `{page: "bad/before/home.html", id: "home-01", kind, description, sc: ["1.1.1"], in_scope: true|false, anchor: {...}, clean: false}`; and one row
  per repaired counterpart on the "after" page with `clean: true`. `in_scope` is decided by kind, not by what Parity found: alt text missing /
  meaningless / verbose / placeholder, title-only name, image-only link without a name, non-descriptive link text, unlabelled or mis-labelled form
  control are in scope; reading order, link visual distinction, colour alone, layout tables, heading structure are out of scope and reported as such.
- **Anchors.** BAD elements rarely have ids, so a label anchors by one of: `{"src": "<file name>"}` (matched against the finding's element outer
  HTML), `{"text": "<visible text>"}` (normalised equality with the finding's sighted text), or `{"css": "<path>"}`. `eval/harness.py` gains
  `label_for(element, sighted_text, labels)`: the existing nearest-id rule first, then the anchors; the axe baseline is scored by the same function.
  A label matched by more than one finding counts once (as today).
- **Runs.** `python -m eval.harness --external --runs 2` with the contributor model: 16 runs, about $1.50 and 30 minutes. Output: an `external`
  block in `latest.json` (`in_scope_recall`, `precision`, `fp_on_after_pages`, `out_of_scope_count`, `axe_recall`, cost and seconds per page, n).
- **Surfaces.** The Eval tab adds a row group "External pages (W3C BAD)" with the in-scope note and the out-of-scope count; the README's eval table
  gains the same row with the subset stated in words. No number is quoted anywhere before the run exists.

### 19.2 Judge-runnable external flows (Phase 6b, second gate)
- `Flow` gains `public: bool = False` and `attribution: str = ""`. `EXTERNAL_FLOWS` holds `bad-home`, `bad-news`, `bad-tickets`, `bad-survey`
  with absolute `start_url`s, a read-only goal each (the survey's goal says not to submit), `single_page=True`, `public=True`. `GET /api/flows`
  returns `public` and `attribution`; the runner takes `public=flow.public` and the flow's origin as `base_url`.
- The workbench groups them as "External page (W3C demo, read-only)", shows the attribution line, and passes `fixesExpected=false` (no fixer, no
  re-audit: §17 stands, we never patch a page we do not serve). The header names the site from the flow, never "ShopRight".
- Replay bundles `fixtures/replay/runs/bad-<page>` recorded once each with the Spark model (~$0.10 each), not anonymised (the pages are a public
  demonstration published for this purpose), with a `NOTICE` carrying the W3C copyright line. Rate limits unchanged; `PARITY_EXTERNAL_FLOWS=0`
  hides the group.

### 19.3 After the event: arbitrary URLs on the hosted app
What the hosted app would need before a URL field is safe to expose, none of which fits before the freeze:
- A URL policy: http(s) only, public DNS answers only (resolve first; refuse private, link-local, loopback and cloud-metadata ranges, and re-check
  on every redirect), a deny list, one run per origin at a time, a crawl delay, robots.txt as now.
- Terms and consent: the visitor affirms they may audit the page; a per-site opt-out list; an abuse contact and a takedown path in the README.
- Retention: third-party bundles masked to the findings' boxes by default (the anonymiser's rule), deleted after 24 h, never in the public samples
  without the owner's agreement.
- Cost: a per-URL and per-day cap on top of the per-visitor limit; the contributor model by default.
- The prompts mark page text as untrusted (the README's open gap) before any page we did not write can steer the navigator.
- No fixes and no re-audit on pages we do not serve; proposed snippets only if a later product serves the developer's own staging site (the real
  customer path: a CI step or an extension running against the developer's own origin, where fixes can be applied and re-audited).
