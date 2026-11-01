# Session handoff: starting Phase 6 in a fresh chat (written Mon 2 Nov 2026, ~00:30 SAST)

Why this file exists: the chat that ran Phases 0–5, the stress campaign and D11 is long and has been compacted once. Phase 6 starts in a
new chat. This file is what that chat needs that is not in the code, the git log or the plan. The VoiceOver pass over the workbench
(docs/24) continues in the old chat, which holds the tool grants and the driver for it; the two chats share this checkout on `main`
and write disjoint files (see §4).

## 1. State of the repository and the deployment

- `origin/main` at `862f167` (docs). Last code commit `f1c7bd5` (stress pass 5). All commits are sole-author `Taahir Suleman <tai.suleman@gmail.com>`,
  no trailers; verify after every push with `git log -1 --format='%an <%ae>%n%B'`.
- Suites at HEAD: pytest 339 green (`.venv/bin/python -m pytest -q`), vitest 86/86 (`cd web && npm test -- --run`), web smoke 26/26.
- Hosted: `https://parity-u7lcbbxuia-uc.a.run.app`, Cloud Run revision `parity-00004` from image tag `f1c7bd5`. Redeploy is
  `deploy/cloudrun.sh build && deploy/cloudrun.sh deploy` (commit first; ~7 min). `/api/health` must say `storage: gcs`, `models_ok: true`.
- Eval numbers shipped are `eval/results/final.json` (1 Nov, commit `1e6caad`); quote the file, do not re-run (~60 min, ~$5).
- Ledger: `.superpowers/sdd/20-implementation-plan/progress.md` (git-ignored). Phases 0–5 have `complete` lines; the stress campaign and D11 are
  recorded at the end. Read its last 40 lines before starting.

## 2. Decisions that bind Phase 6 and 6b

- **Phases are started only on the user's go-ahead.** Do not begin Phase 6b or Phase 6 without it in the new chat's first message.
- **Ordering (D11, doc 18 §11):** the external benchmark core (Task 26E.1–26E.3) was recommended before Voice; the user has not yet chosen.
  The user's own Task 26 recording is a manual step that needs them at the Mac with VoiceOver and an audio recorder, so the interleave that
  wastes no one's time is: Task 26 kit first (the script and `docs/voice-recording.md`, ~45 min), the user records while the agent runs 26E.1–26E.3,
  then Tasks 27–28. If the user says "Voice only", run 26, 27, 28 and leave 26E for after.
- **Gates (doc 20):** 26E core by Mon 15:00 SAST; 26E hosted by Tue 12:00 SAST; Voice G-V = word accuracy ≥ 0.90 decides whether Voice is
  primary evidence or corroboration. Feature freeze Tue 3 Nov 12:00 ET = 19:00 SAST. A missed gate is dropped, not squeezed.
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

## 4. Two chats, one checkout

- The new chat (Phase 6 / 6b) owns everything except `docs/24-voiceover-pass.md` and this file. It commits only the files it changed.
- The old chat (VoiceOver pass) writes only `docs/24-voiceover-pass.md` (the Heard and Verdict columns) and commits only that.
- Neither chat runs `git stash`, `git reset`, `git checkout -- .` or a rebase; both pull with `git pull --ff-only` before a push.
- The workbench fixes that come out of the VoiceOver pass are done in whichever chat is active once Task 28 has been committed.

## 5. The kickoff message for the new chat

Paste this as the first message of a new chat opened in `/Users/ammarah/Desktop/Meta_Hackathon/parity` (adjust the ordering line if you decide
otherwise):

```
Start Phase 6b and Phase 6 of docs/20-implementation-plan.md in the order given in docs/25-session-handoff.md §2
(Task 26 kit first so I can record while you run 26E.1–26E.3, then 27–28; 26E.4–26E.5 if the Tue 12:00 SAST gate holds).

Read first, in this order: CLAUDE.md (loaded), docs/25-session-handoff.md, the last 40 lines of
.superpowers/sdd/20-implementation-plan/progress.md, docs/20-implementation-plan.md Phase 6b and Phase 6, docs/19-design-spec.md §19,
docs/18-decision-and-development-plan.md §11, and the meta-model-api skill before any API call.

Use superpowers:executing-plans inline with TDD; one ledger line per task in progress.md. Do not touch docs/24-voiceover-pass.md
(another chat owns it). Commit only the files you changed, sole author, no trailers, verify after each push, pull --ff-only first.
Every model call cached and traced; tell me the spend before any run over $1. Stop and ask before: redeploying, any run that costs
more than $2, tagging, or anything in §2's open items.

Confirm you have read the handoff by telling me the three gates and their times in SAST, then begin Task 26.
```

What you (the user) do during Phase 6: record `store/voice/checkout.wav` per `docs/voice-recording.md` when the kit is ready, answer the
G-V number when it is reported, and decide the 26E hosted gate at Tue 12:00 SAST.

## 6. The VoiceOver pass, where it stands

Method, after two constraints discovered on 1 Nov: the desktop-control grant for Safari is read-only and forbids keystrokes by any route;
the Claude in Chrome extension drives a real Chrome tab (focus, clicks, live regions, all of which VoiceOver speaks when Chrome is in
front), and the agent reads each spoken phrase back with the command in §3. VoiceOver-only chords (VO+Right, the rotor, interact) are
out of reach that way; those rows are checked against the accessibility tree instead, which is the data the rotor lists. The extension
was not connected when the pass was attempted; it resumes in the old chat once Chrome has the extension signed in and the hosted page
open in front, with VoiceOver on. Questions A–D remain the user's ten minutes of listening.
