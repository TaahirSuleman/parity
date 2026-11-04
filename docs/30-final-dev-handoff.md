# 30 — Final dev hand-off (dev session, 4 Nov 2026)

Facts only, each with its commit, run or revision id. Written for the prompt 28 session (judge-facing docs, storyboard, recordings, form).

## 1. Final hosted revision
- **Final hosted revision: parity-00023-qkh, serving commit `2039a9f`** (CI 41861638895 green, `/api/health` ok, models_ok true, pushed 17:48 SAST). That commit adds only `eval/results/judge-contributor-n1.json`; its code is identical to `0ccc2fa` (changes 1–3 below, CI 41851851333 green, revision parity-00022-5dp, pushed 16:52 SAST), so every clip recorded on parity-00022-5dp shows the same app. Verified on parity-00023-qkh: hero-checkout Replay 20261104-162003-fe947b1c awaiting_review 7/1; hero-purchase Replay 20261104-162032-2175fc12 awaiting_review 30/4; /api/eval still serves the 3-run set (git_sha 3221905, 0.851 / 0.990).
- The results-only push went at 17:48 SAST on the builder's word ("do not wait for the 20:30 deadline"), before the 19:00–19:30 recording window. This hand-off is a docs-only commit (no redeploy).
- **No further pushes planned.**

## 2. Changes in §1
| # | Change | State | Commit | Tests (RED → GREEN) |
|---|---|---|---|---|
| 1 | Judge default `muse-spark-1.3-contributor`, effort `high`; fallback stays `muse-spark-1.3`; env overrides unchanged | done | 0ccc2fa | test_config: 3 red → green (defaults pinned, fallback standard); test_runner's ablation-effort test now expects the judge at its own default |
| 2 | `gap_closed` requires a non-empty sighted text (Muse Code R1) | done | 0ccc2fa | test_reaudit: 2 new (empty text never closes; a one-letter text closes by containment, documented); the hero still closes |
| 3 | Public-site guard: a click whose target sits inside a `<form>` is dropped with its reason; a click with no inspectable target is dropped (Muse Code R2) | done | 0ccc2fa | test_guard: 2 new (a type=button "Go" that submits from a script, a search field in the form; a link outside allowed; a None target refused, scroll allowed); one old assertion flipped; store walks unaffected (the guard runs only on public runs) |
| 4 | Purchase bundle, attempt 6 | done earlier | ec60728 | see §4 |
Cloud Run's env (names only) and ci.yml set no `PARITY_JUDGE_*`, so the default applies hosted. Suite after the push: pytest 558 rc 0, vitest 166, SPA builds.

## 3. The judge change
- Old → new: `muse-spark-1.3` at medium → `muse-spark-1.3-contributor` at high. Fallback on a judge error stays `muse-spark-1.3`.
- Sweep evidence (eval/results/model-sweep.md, 4 Nov, n = 2 over 31 findings): the same 94% agreement with the labels as the standard tier, 0% needing review, $0.0006 vs $0.0108 a finding, latency 22 s vs 20 s, severity same as the old judge on 84% (the standard tier's own low and high variants: 84% and 87%).
- Confirmation run (`eval/results/judge-contributor-n1.json`, **n = 1, 4 Nov 17:03 SAST, git 0ccc2fa**, full configuration, same labels): recall 89% (34 of 38), precision 100%, 0.0 false positives on the 20 clean controls, **$0.043 per 4-page set** (was $0.37 with the standard judge), 540 s; judge agreement 94% (32 of 34), needs review 0%, $0.0007 a finding, mean judge latency 21.6 s over 34 calls. Within the 3-run headline's spread (85% ± 3 labels), so the headline stays.
- What prompt 28 may quote: the headline **85% / 99% / 0.0 FP** stays as "3 runs, 4 Nov, commit 3221905, standard-tier judge" (unchanged in latest.json and /api/eval); the cost per page set with today's defaults is **$0.04 (n = 1, 4 Nov, after the judge change)**, labelled as such; the judge line is "94% agreement with the labels (n = 1, 34 findings, contributor tier at high)". Do not blend the two sets.
- Bundles whose trace shows the standard-tier judge (recorded before the change): hero-checkout (7 judgements), hero-purchase (30), w3c-home/news/survey/tickets; public-a/b carry no trace. The first run with the new judge in its trace is the clone's Live checkout run (§5).

## 4. The purchase bundle in the video
- Attempt 6, run `20261104-134552-aa32888f`, committed as `hero-purchase` in ec60728 (revision parity-00021-5x2, then served unchanged by parity-00022-5dp): nine turns, finish called ("Purchased noise-cancelling headphones with card ending 1111, expiry 10/28; order SR-10428 confirmed."), one click snapped (the card field), 30 verified / 4 rejected over four screens, six checks on every card, hero #f5 "Pay R1,249" vs "Submit" with its fix and re-audit **Gap closed**, 27 fixes / 27 re-audits (14 closed, none cut by the budget), Voice on five findings (0.92 accuracy), $0.373, 1,343 s; re-audit share 669 of 1,343 s. Hosted Replay on parity-00022-5dp: run 20261104-150342-479a89d7, awaiting_review 30/4.
- Its trace shows the standard-tier judge (recorded before change 1). The clip needs re-recording only if it was cut on an earlier bundle (attempt 2, "did not finish within 12 turns", or the 1 Nov 35-finding one); the bundle itself has not changed since ec60728.

## 5. Smoke runs
- Hosted Live, parity-00022-5dp, https://www.wikipedia.org/ (read-only, non-Meta): one screen, run `20261104-150434-9bcc2ab2`, done, 2 verified / 3 rejected, six checks on both cards, judge contributor tier on both, $0.007, 143 s; three screens, run `20261104-150733-1fdef6d8`, done in 3 agent turns, 2/2, six checks, contributor judge, $0.008, 143 s. The agent described the page without clicking, so the form-click refusal was not exercised live; it is test-covered. No 429s.
- Local smoke from a fresh clone (`git clone` of the public repo into a temp folder at 0ccc2fa; port 8080 was held by another local server, so 8090 and 8091 were used):

| Step | Result | Time |
|---|---|---|
| git clone | ok | 2 s |
| make setup | ok, no prompts (python 3.12, node, uv, Chromium already on this Mac: a clean machine's Homebrew and browser downloads are not measured) | 11 s |
| make demo, no key | app starts; health has_key false, models_ok false, open_url false; Replay works; Live store → 503 "Live mode needs MODEL_API_KEY on the server; use Replay"; visitor URL → 403 "pages you choose are not offered on this server" | starts in < 5 s |
| make demo, with the key in the environment | Live checkout run `20261104-151555-37c262e1`: awaiting_review 7/0, six checks, judge contributor tier on all seven, hero fix with gap closed, $0.024 | 299 s |
| pytest from the clone | 558 passed, rc 0 | 3 m 36 s |
| vitest / SPA build from the clone | 166 passed / built | ~6 s / < 1 s |
| flaky shadow-root timing test alone | passed alone (the 4 s bound held) | |

- Parity, clone (no key) vs hosted parity-00022-5dp, identical on every row: replay_flows and replay_runs lists; hero-checkout Replay awaiting_review 7/1, six checks on every card, hero "Pay R1,249" vs button "Submit", fix diff on store/, Gap closed, patch download 404 "no approved fixes yet" until the hero is approved then 200 (1,053 bytes), Voice on five (0.92); hero-purchase 30/4, six checks; public-b done 0/0; w3c-home done 2/16, five checks (3 Nov bundle); /api/eval git_sha 3221905, full 0.851 / 0.990 / 0.0 FP / axe 0.0, runs 3, judge row muse-spark-1.3, model_sweep present. Health differs only by design: has_key, models_ok, storage (local vs gcs), open_url (off without a key), runs_indexed. Live caps: 3 Live runs per IP per hour on both; the hosted app also runs the visitor-URL caps ($0.50 a run, $5 a day, 3 per origin a day); locally open_url is off without a key.
- Hygiene from the clone: no commit on any branch ever touched `.env*` (only `.env.example` is tracked); LICENSE is MIT; a grep for key-shaped strings hits only long test function names; the README's links answer 200 in a private window (hosted URL, W3C BAD page, the local address).
- Mismatches: none found. The temp clone's servers are stopped; the clone folder sits in this session's scratchpad (deleting it was refused by the session's permission rule; the scratchpad is temporary).

## 6. Facts prompt 28 must change in the README, docs/18, 19 and 21
- Judge model and effort: `muse-spark-1.3-contributor` at `high` (spec §6.1 role table; README model line; docs/18 and 21 where the judge is named); fallback `muse-spark-1.3`.
- Cost: $0.04 per 4-page set with today's defaults (n = 1, 4 Nov), beside the $0.37 figure that the 85 / 99 rows were measured at.
- Guard behaviour (spec §17, README "How it acts"): on a public site a click inside a form, or on nothing identifiable, is not made and the event says why; the walk goes on.
- `gap_closed` (spec §9 / README re-audit sentence): closed only when a non-empty sighted text appears in the new accessible name.
- Test counts: pytest 558, vitest 166 (at 0ccc2fa).
- `make setup` / `make demo`: as the README says; a judge needs a free 8080 or `PORT=…`; nothing else differed.
- Known limits that remain (Muse Code R1/R2 rows not fixed): fixes are shown before their re-audit runs and a failed re-audit leaves them approvable; the fixer's snippet gate checks shape, not meaning; the Verifier's `seen` check stands down when the sighted pass did not run; judges fail open on shape (severity and WCAG refs unvalidated); the per-run cost cap is checked before launch, not inside the judge fan-out; robots.txt is read at start and landing only; login walls need a password field plus a login title or path; in-browser redirect hops re-judge host only.

## 7. Spend and caps for judging
- This session (prompt 30): Wikipedia smoke runs $0.015, clone Live run $0.024, confirmation eval $0.043: **$0.08**. The day's earlier work in this session (purchase re-record ×6 $2.24, checkout re-record $0.67, eval $1.11, W3C $0.15, FlySafair $0.11): about $4.30.
- Live caps (Nov 5–9): 3 Live runs per IP per hour; visitor-URL runs capped at $0.50 each, $5 a day, 3 per origin a day; the day's visitor budget was open at the time of writing (`external_closed_today` false). Spend alert: not visible to this session (the Cloud Billing Budgets API is not enabled on the project, and enabling it is Cloud Run/billing config, out of scope); the builder's Cloud Console shows the budget alert state.
