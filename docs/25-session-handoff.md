# Session handoff: Phases 6, 6b and 6c in two fresh chats (written Mon 2 Nov 2026 ~00:30 SAST; D12 and the two tracks added Mon 19:00 SAST)

Why this file exists: the chat that ran Phases 0–5, the stress campaign and D11 is long and has been compacted once. Phase 6 starts in a
new chat (chat A). Since D12 (Mon 19:00 SAST) a second new chat (chat B) builds Phase 6c in its own worktree. This file is what those chats
need that is not in the code, the git log or the plan. The VoiceOver pass over the workbench (docs/24) continues in the old chat, which holds
the tool grants and the driver for it; the chats write disjoint files (see §4).

## 1. State of the repository and the deployment

- `origin/main` at the D12 docs commit (Mon 2 Nov 19:00 SAST); nothing of Phases 6, 6b or 6c has started. Last code commit `f1c7bd5` (stress pass 5). All commits are sole-author `Taahir Suleman <tai.suleman@gmail.com>`,
  no trailers; verify after every push with `git log -1 --format='%an <%ae>%n%B'`.
- Suites at HEAD: pytest 339 green (`.venv/bin/python -m pytest -q`), vitest 86/86 (`cd web && npm test -- --run`), web smoke 26/26.
- Hosted: `https://parity-u7lcbbxuia-uc.a.run.app`, Cloud Run revision `parity-00004` from image tag `f1c7bd5`. Redeploy is
  `deploy/cloudrun.sh build && deploy/cloudrun.sh deploy` (commit first; ~7 min). `/api/health` must say `storage: gcs`, `models_ok: true`.
- Eval numbers shipped are `eval/results/final.json` (1 Nov, commit `1e6caad`); quote the file, do not re-run (~60 min, ~$5).
- Ledger: `.superpowers/sdd/20-implementation-plan/progress.md` (git-ignored). Phases 0–5 have `complete` lines; the stress campaign and D11 are
  recorded at the end. Read its last 40 lines before starting.

## 2. Decisions that bind Phase 6 and 6b

- **Phases are started only on the user's go-ahead.** Do not begin Phase 6b or Phase 6 without it in the new chat's first message.
- **Ordering (D12, doc 18 §12, decided Mon 2 Nov 19:00 SAST; supersedes D11's timing):** two tracks in parallel.
  - Track A, chat A, on `main`: Task 26 kit first (~45 min; the user records while the agent continues) → 26E.1–26E.3 → Task 27 → Task 28 →
    the VoiceOver-pass fixes if time remains.
  - Track B, chat B, worktree on `feat/open-url`: 26E.4 → Phase 6c (26F.1–26F.6) → merge into `main` → the first redeploy → 26E.5 bundles and
    the hosted verification of 6c.
  - Phase 6c has priority when the two collide (the first merge slot, the earlier hosted gate, the user's attention); Voice is not dropped and is
    ended only by its own clock. Drop order if the day runs short: 26E.5 bundles, then 6c's three-screen option, then the hero re-record.
- **Gates (SAST):** benchmark core Tue 10:00; 6c complete locally Tue 11:00; merge and first redeploy Tue 12:30; 6c verified on the hosted app
  Tue 14:30; Voice Task 28 committed Tue 14:00, hero re-recorded with the second and last redeploy Tue 16:00; 26E.5 by Tue 15:00; cold review
  Tue 17:00; freeze Tue 19:00 (= 12:00 ET). G-V = word accuracy ≥ 0.90 decides whether Voice is primary evidence or corroboration. A missed
  gate is dropped, not squeezed.
- **The VoiceOver pass is not a gate for Phase 6** (ruled Mon 2 Nov, below). Its findings are workbench wording and announcement fixes
  (the stress pass's M5 items). They land after Task 28 so that only one hand touches `web/src` at a time.
- **Open items the user owns:** the AI-coding-assistance line in `HACKATHON_SCOPE.md` (left out for now, kept open); the pre-submission
  deletions (doc 20 Task 25 list).
- **Standing rules** (CLAUDE.md, still binding): Meta models only at runtime; never read, print or commit `MODEL_API_KEY` or `.env*` (a deny rule
  blocks Bash on them; `.env.example` is written with a python heredoc); only the user adds Secret Manager versions; cache every API response;
  log model, request id, tokens, latency and cost; never claim "compliance"; third-party sites read-only; `rm -rf` is denied.
- **Environment quirks:** zsh does not word-split `$var` (use `${=var}`); macOS has no `timeout`; the shell cwd resets between calls, use
  absolute paths; the venv `.pth` can get the hidden flag (`python -m parity.cli` works regardless).

## 3. A finding that helps Task 26 (the recording kit)

VoiceOver is scriptable once "Allow VoiceOver to be controlled with AppleScript" is on (VoiceOver Utility → General; password prompt).
Verified on this Mac on 1 Nov:

```bash
osascript -e 'tell application "VoiceOver" to return content of last phrase'
```

returns the exact text VoiceOver just spoke. Polled every ~120 ms during a recording, it yields `checkout.captions.txt` with timestamps
without the caption panel and without transcribing by hand, and it is the reference against which `word_accuracy` (Task 27) is measured.
The driver used for the workbench pass is at the old chat's scratchpad (`vo/vo.sh`, `watch <seconds>` subcommand); Task 26 should carry
its own copy under `scripts/` since the scratchpad is session-scoped.

## 4. Three chats, two checkouts

- **Chat A** (Phase 6b core and Phase 6) works in this checkout on `main` and owns everything there except `docs/24-voiceover-pass.md`, this file,
  and the files Phase 6c creates or changes (`parity/pipeline/urlpolicy.py`, `parity/pipeline/browser.py`, `parity/ratelimit.py`, `parity/replay.py`,
  `parity/static/audit-policy.html`, the prompts in `parity/meta/prompts/`, `web/src/components/UrlRun.tsx`, `parity/flows.py`). Chat A's edits to
  `parity/api/routes.py`, `parity/config.py`, `parity/pipeline/runner.py`, `web/src/App.tsx`, `Workbench.tsx` and `Header.tsx` are expected and are
  merged by chat B; keep them small and local to Voice.
- **Chat B** (26E.4 and Phase 6c) works in the worktree `../parity-open-url` on `feat/open-url`. The user creates it (one command in §5b) and copies
  `.env` into it, because the agent may not touch `.env*`. Chat B runs `make venv web vendor-axe` there (its own `.venv` and `node_modules`), sets
  `PARITY_CACHE_DIR` to this checkout's `cache/` (absolute path) so no model call is paid twice, and keeps `data/` local to the worktree. Before the
  final merge it runs `git merge main` into its branch (a merge, not a rebase), then on `main` `git pull --ff-only` and a fast-forward merge.
- **The old chat** (VoiceOver pass) writes only `docs/24-voiceover-pass.md` and commits only that.
- No chat runs `git stash`, `git reset`, `git checkout -- .` or a rebase on `main`; every chat pulls with `git pull --ff-only` before a push and
  verifies the author after it. Only the user adds Secret Manager versions; redeploys are Tue 12:30 (chat B) and Tue 16:00 (chat A) unless the user says otherwise.
- The workbench fixes that come out of the VoiceOver pass are done in chat A once Task 28 has been committed.

## 5. The kickoff message for the new chat

Paste this as the first message of a new chat opened in `/Users/ammarah/Desktop/Meta_Hackathon/parity` (adjust the ordering line if you decide
otherwise):

```
You are chat A, track A of docs/25-session-handoff.md §2: Task 26 kit first so I can record while you run 26E.1–26E.3, then Tasks 27 and 28,
all on main in this checkout. Chat B builds 26E.4 and Phase 6c in a worktree on feat/open-url and merges Tue 12:30 SAST; do not do their
tasks and do not touch their files (docs/25 §4).

Read first, in this order: CLAUDE.md (loaded), docs/25-session-handoff.md, the last 40 lines of
.superpowers/sdd/20-implementation-plan/progress.md, docs/20-implementation-plan.md Phase 6b and Phase 6, docs/19-design-spec.md §16 and §19,
docs/18-decision-and-development-plan.md §11–§12, and the meta-model-api skill before any API call.

Use superpowers:executing-plans inline with TDD; one ledger line per task in progress.md. Do not touch docs/24-voiceover-pass.md
(another chat owns it). Commit only the files you changed, sole author, no trailers, verify after each push, pull --ff-only first.
Every model call cached and traced; tell me the spend before any run over $1. Stop and ask before: redeploying, any run that costs
more than $2, tagging, or anything in §2's open items.

Confirm you have read the handoff by telling me your gates (benchmark core, Task 28, the second redeploy) in SAST, then begin Task 26.
```

What you (the user) do during Phase 6: record `store/voice/checkout.wav` per `docs/voice-recording.md` when the kit is ready, answer the
G-V number when it is reported, and approve the Tue 16:00 SAST redeploy.

## 5b. The kickoff message for chat B (Phase 6c)

First, in this checkout, create the worktree and give it the key (the agent may not touch `.env*`):

```bash
git worktree add ../parity-open-url -b feat/open-url
```

```bash
cp .env ../parity-open-url/.env
```

Then open a new chat in `/Users/ammarah/Desktop/Meta_Hackathon/parity-open-url` and paste:

```
You are chat B, track B of docs/25-session-handoff.md §2: Task 26E.4 first, then Phase 6c (Tasks 26F.1–26F.6) of
docs/20-implementation-plan.md, in this worktree on branch feat/open-url. Chat A runs 26E.1–26E.3 and Voice on main in the
main checkout; do not do their tasks. Set up with `make venv web vendor-axe`, point PARITY_CACHE_DIR at the main checkout's cache/
(absolute path) so nothing is paid twice, and keep data/ local.

Read first, in this order: CLAUDE.md (loaded), docs/25-session-handoff.md, the last 40 lines of
.superpowers/sdd/20-implementation-plan/progress.md in the main checkout, docs/20-implementation-plan.md Phase 6b (26E.4) and
Phase 6c, docs/19-design-spec.md §17 and §19, docs/18-decision-and-development-plan.md §11–§12, and the meta-model-api skill
before any API call.

Use superpowers:executing-plans inline with TDD; one ledger line per task in the main checkout's progress.md. Commit on the
branch only, sole author, no trailers; before the final merge run `git merge main` into the branch, suites green, then on main
`git pull --ff-only`, fast-forward merge, push, verify the author. Every model call cached and traced; tell me the spend before any
run over $1. Stop and ask before: the merge, redeploying, any run that costs more than $2, adding any site to the suggested list,
or anything in §2's open items. The policy contact is the repository author's email; the daily cap starts at $5.

Confirm you have read the handoff by telling me your three gates in SAST and the drop order, then begin Task 26E.4.
```

What you (the user) do for Phase 6c: create the worktree and copy `.env` (above), approve the Tue 12:30 SAST merge and redeploy, and pick
or confirm the three third-party pages for the hosted verification when chat B proposes them.

## 6. The VoiceOver pass, where it stands

Method, after two constraints discovered on 1 Nov: the desktop-control grant for Safari is read-only and forbids keystrokes by any route;
the Claude in Chrome extension drives a real Chrome tab (focus, clicks, live regions, all of which VoiceOver speaks when Chrome is in
front), and the agent reads each spoken phrase back with the command in §3. VoiceOver-only chords (VO+Right, the rotor, interact) are
out of reach that way; those rows are checked against the accessibility tree instead, which is the data the rotor lists. The extension
was not connected when the pass was attempted; it resumes in the old chat once Chrome has the extension signed in and the hosted page
open in front, with VoiceOver on. Questions A–D remain the user's ten minutes of listening.
