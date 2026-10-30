# Parity: project ground truth for Claude Code

**What:** an agent that walks a site's key flows and compares what a sighted user sees with what a screen-reader user gets. It finds the barriers axe-core misses, proves each one with grounded evidence, proposes a fix, re-checks it, and leaves the decision to a human.

**Event:** Meta Global AI Developer Hackathon, Indie track. **Deadline:** Wed 4 Nov 2026, 21:00 ET; submit by 18:00 ET. **Feature freeze:** Tue 3 Nov, 12:00 ET.

**Rubric:**
- Impact 30%.
- Use of Meta AI Tooling 25%: beyond basic integration.
- Technical Depth 20%: craft.
- Demo 25%: works live; a video worth watching.

## Read first (in order). The full docs map and precedence rules are in `docs/README.md`
1. `docs/18-decision-and-development-plan.md`: user, hero moment, architecture, workbench, eval, day plan, video. **The source of truth for scope.**
1b. `docs/19-design-spec.md` (interfaces, data model, routes, deploy on Cloud Run) and `docs/20-implementation-plan.md` (the phased TDD plan being executed).
2. `docs/17-validation-results.md`: what is proven on the live API (and what failed).
3. `docs/14-build-playbook-verifiable-agents.md`: the verifiable-agent architecture. Learn the patterns; write our own code (no workshop code).
4. `docs/submission-checklist.md`: video and cold-review rules.
4b. `docs/hackathon/00-constitution.md`: rules, rubric, hard constraints (it wins any rules conflict).
5. Skill `meta-model-api`: verified request formats. Use it before writing any API call.

## Hard rules (disqualification or credibility)
- **Runtime models:** every model called at runtime is a Meta model (`muse-spark-1.3`, `-contributor`, `muse-voice-transcribe-1.0`). No other LLMs or TTS at runtime. Playwright and axe-core are fine (not models).
- **No-login demo:** judges can try it without logging in. Ship a hosted URL with a "Run the audit" button and Live/Replay modes, plus a one-command local run.
- **Built this week:** a new repo; everything built this week; `HACKATHON_SCOPE.md` lists pre-existing OSS.
- **Never claim "compliance".** Findings are evidence, and a human approves every fix.
- **Secrets:** never print or commit `MODEL_API_KEY`. It is loaded from `.env`, which is git-ignored.
- **Logging:** log the model, request ID, tokens, latency and cost for every call. Cache responses on disk; never pay twice in dev.
- **Third-party sites:** read-only and within their terms. The hero and eval run on our own demo store.

## Decided architecture defaults (confirm or adjust in brainstorming; don't re-research)
- **Backend:** Python 3.12, FastAPI, async Playwright (Chromium). Pipeline stages are plain modules: navigator → capture → seer → comparator → verifier → judge → fixer → re-audit → human gate.
- **Checks inside the tools:** a finding cannot persist without passing the verifier. The model perceives; code decides.
- **Frontend:** React + Vite + TypeScript + Tailwind SPA, served by FastAPI, with live updates over SSE. The workbench is designed first; every step shows a Meta-model badge.
- **Storage:** run bundles (JSON + PNG) are the truth, on local disk or a Cloud Storage bucket via the client API; SQLite is a derived cache rebuilt at boot (doc 19 D8). Replay mode serves committed bundles.
- **Deploy:** one Docker image (a Playwright base image) on a container host with HTTPS. Live mode is rate-limited per IP; Replay is the default for judges.
- **Demo store:** static pages served by the same app at `/store`, with ~30 seeded axe-passing faults and ~10 clean controls. Labels live outside the agent's code path.
- **Eval:** recall and precision vs labels; axe-core baseline; ablations (screenshot-only, tree-only, no grounding); cost and time per page.

## Working style (token budget is tight)
- **Superpowers:** brainstorming, then writing-plans, then **executing-plans** (inline, cheap). Use subagent-driven-development only for big independent chunks.
- **Tests:** TDD for the verifier, capture and eval code (deterministic). For model-facing code, use cached fixtures, not live calls.
- **Context:** `/clear` between phases. Keep this file under 100 lines and point to docs instead of pasting them.
- **Seeds:** working prototypes from validation live in `seeds/`. Rewrite them into the app; don't copy them blindly.
