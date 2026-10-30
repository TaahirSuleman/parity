# Hackathon scope: what was built during the event

**Event:** Meta Global AI Developer Hackathon, Indie track. Kickoff Mon 26 Oct 2026. Submission Wed 4 Nov 2026.
**Builder:** Taahir Suleman (solo).
**Repository created:** Fri 30 Oct 2026 (first commit after kickoff).

## Built during the hackathon (all of it, this week)
- The Parity pipeline: navigator (Muse Spark 1.3 computer use), capture, seer (grounding), comparator, verifier, judge, fixer, re-audit, human gate, trace.
- The Meta Model API client with disk cache and a per-call trace (model, request ID, tokens, latency, cost).
- The workbench SPA (React + Vite), the SSE event stream, Live and Replay modes.
- The ShopRight demo store (static pages with seeded, axe-passing faults) and its labels.
- The evaluation harness, the axe-core baseline and the ablations.
- Tests, Dockerfile, Cloud Run deploy scripts, README and docs.
- `seeds/`: throwaway validation prototypes written on 29 Oct 2026 (inside the event window) and rewritten into the app.

## Pre-existing open source used (not written by us)
| Dependency | Role | Licence |
|---|---|---|
| Playwright (Python) | browser automation, screenshots, CDP accessibility tree | Apache-2.0 |
| axe-core | rule-engine baseline the agent is compared against | MPL-2.0 |
| FastAPI, uvicorn, sse-starlette, httpx, pydantic, aiosqlite, python-dotenv | backend | MIT / BSD |
| pytest, pytest-asyncio | tests | MIT |
| React, Vite, TypeScript, Tailwind CSS | workbench | MIT / Apache-2.0 |
| Playwright Docker base image | deploy image | Apache-2.0 |

No pre-existing application code, models, datasets or prompts are reused. Public statistics quoted in the demo (WebAIM Million 2026; US ADA web suits 2025) are cited in the README.

## Models at runtime
Only Meta models: `muse-spark-1.3`, `muse-spark-1.3-contributor` (eval), and optionally `muse-voice-transcribe-1.0` (stretch, off by default). Playwright and axe-core are not models.
