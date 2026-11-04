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
| FastAPI, uvicorn, sse-starlette, httpx, pydantic, aiosqlite, python-dotenv, Pillow | backend (Pillow masks public-sample screenshots) | MIT / BSD / MIT-CMU |
| google-cloud-storage | run bundle storage on Cloud Run | Apache-2.0 |
| pytest, pytest-asyncio | tests | MIT |
| React, Vite, TypeScript, Tailwind CSS | workbench | MIT / Apache-2.0 |
| Playwright Docker base image | deploy image | Apache-2.0 |
| sounddevice (PortAudio), BlackHole 2ch | the VoiceOver recording kit only (`scripts/vo_record.py`, run by hand on a Mac to make `store/voice/*.wav`); neither runs in the app | MIT / MIT (BlackHole, existential.audio) |
| W3C WAI "Before and After Demonstration" (BAD) pages, `https://www.w3.org/WAI/demos/bad/` | an external, labelled benchmark we did not write: the four "before" pages are audited read-only in the eval and offered as Replay and Live flows; the recorded bundles under `fixtures/replay/runs/w3c-*` carry W3C's notice | W3C document licence (Copyright © 2012 W3C® (MIT, ERCIM, Keio)) |

No pre-existing application code, models, datasets or prompts are reused. The README quotes only numbers measured here; any public statistic shown in the video is cited on screen.

## Models at runtime
Only Meta models: `muse-spark-1.3-contributor` (default for navigation, perception, comparison and fixes), `muse-spark-1.3` (the judge, the judge fallback and private mode); `muse-wonder-1.0` was measured as an alternative judge in the eval and is not used at runtime. `sam-3.1` was tested and is not used at runtime either (doc 17). `muse-voice-transcribe-1.0` transcribes the recorded VoiceOver clip of the checkout page once per run that audits it (the README states the measured word accuracy, 0.92 on the committed replay, and that Voice is primary evidence beside the accessibility tree). Playwright and axe-core are not models. VoiceOver is Apple's screen reader; if used, it only records audio clips and is never called at runtime.
