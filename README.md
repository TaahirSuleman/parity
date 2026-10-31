# Parity

An agent that walks a site's key flows and compares what a sighted user sees with what a screen-reader user gets. It finds the barriers axe-core misses, proves each one against the page's accessibility tree, proposes a fix, re-checks it, and leaves the decision to a human.

Built during the Meta Global AI Developer Hackathon (26 Oct – 4 Nov 2026) on Meta's Muse Spark 1.3. Playwright and axe-core are pre-existing open source; see [HACKATHON_SCOPE.md](HACKATHON_SCOPE.md).

**Status: Phase 1 (vertical slice).** One page, the ShopRight checkout: capture → seer → comparator → verifier → judge, streamed into the workbench, with a recorded Replay that needs no API key. Navigation, fixes, the human gate, the eval and hosting follow in later phases ([docs/20-implementation-plan.md](docs/20-implementation-plan.md)).

## Run it locally

```bash
cp .env.example .env        # add MODEL_API_KEY for Live mode; Replay works without it
make setup                  # Homebrew python@3.12, node, uv; venv; Chromium; web deps
make demo                   # builds the workbench, serves http://127.0.0.1:8080 and opens it
```

Then click **Run the audit** with **Replay** selected. Switch to **Live** (needs the key) to run the real pipeline against the bundled store.

Tests: `make test` (Python, including browser smoke tests) and `make test-web` (vitest).

## What it is, in one paragraph

axe-core reports 0 violations on `/store/checkout.html`. Parity screenshots the page, reads Chrome's accessibility tree, asks Muse Spark to list what a sighted user sees (grounding) and where that diverges from what a screen reader announces, then **code** verifies every candidate: the box must land on a real element, the quoted role and name must equal the accessibility tree exactly, the visible text must differ from the name, axe must not already report it, and it must not be a duplicate. Only verified findings reach the judge (a separate model call that fails closed) and the workbench. Every model call is cached and traced with model, request ID, tokens, latency and cost.

Findings are evidence, not a certification. Nothing here claims compliance; a human approves every fix.

## Layout

| Path | What |
|---|---|
| `parity/` | the agent and server (FastAPI, Playwright, pipeline stages, run bundles, SQLite index) |
| `web/` | the workbench (React, Vite, Tailwind), built into `parity/static` |
| `store/` | the ShopRight demo store with seeded, axe-passing faults |
| `fixtures/replay/` | the recorded hero run served in Replay mode |
| `tests/` | pytest; model-facing code runs against recorded responses in `tests/fixtures/meta` |
| `docs/` | decisions, design spec, plan ([docs/README.md](docs/README.md)) |
