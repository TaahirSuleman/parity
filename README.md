# Parity

**An agent that walks a site's key flows and compares what a sighted user sees with what a screen-reader user gets.** It finds many of the barriers axe-core misses (85% of the 38 seeded on its own store), proves each one it reports against the page's own accessibility tree, proposes a fix, re-checks it, and leaves the decision to a human.

Built this week (26 Oct – 4 Nov 2026) for the Meta Global AI Developer Hackathon on Meta's **Muse Spark 1.3** and **Muse Voice Transcribe 1.0**. Pre-existing open source: Playwright, axe-core and the libraries listed in [HACKATHON_SCOPE.md](HACKATHON_SCOPE.md), nothing else. Everything else in this repository was written during the event, with Claude Code and Muse Code as coding assistants; the design, the code and the tests are the builder's work.

## Try it

- **Hosted demo:** [https://parity-u7lcbbxuia-uc.a.run.app](https://parity-u7lcbbxuia-uc.a.run.app). No login. Press **Run the audit** with **Replay** selected: a recorded run plays back with no model calls. **Live** runs the real pipeline against the bundled store, one of W3C's demonstration pages, or a public page you choose (read-only), and is rate-limited per visitor.
- **Locally, in three commands:**

```bash
cp .env.example .env        # add MODEL_API_KEY for Live mode; Replay works without it
```
```bash
make setup                  # Homebrew python@3.12, node, uv; venv; Chromium; web deps; builds the workbench
```
```bash
make demo                   # serves http://127.0.0.1:8080 and opens it
```

Tests: `make test` (pytest, including browser smoke tests) and `make test-web` (vitest). The eval: `.venv/bin/python -m eval.harness --ablations --runs 3` (live; about $3.50 for the four configurations on a cold cache).

## What you will see

axe-core reports **0 violations** on the demo checkout. Parity's Replay then shows seven verified findings on that page. The one it opens on: a sighted shopper sees a button that says **Pay R1,249**; a screen reader announces **button, "Submit"**. Six green ticks say why that is a finding and not a guess: the sighted pass saw it, the box landed on a real element, the quoted role and name equal the accessibility tree exactly, the visible text differs from the name, axe does not already report it, and it is not a duplicate. The judge rates it serious (WCAG 2.5.3, Label in Name), the fixer proposes a one-line change, the re-audit loads the patched page in a sandbox and the screen reader now says "Pay R1,249". You approve it with a reason, and **Download fix.patch** gives you a diff that applies to `store/`.

**Live on a page you choose** (hosted, third mode in the header): type a public address, affirm it is public and yours to audit, and Parity audits that screen as a visitor would see it, read-only, with no fixer and no re-audit. A private or internal address is refused in one sentence; robots.txt is honoured; a bot wall or a login ends the run as `blocked by site` and the workbench says so. Four W3C "Before and After Demonstration" pages are also offered as flows.

The Purchase flow (one pick away) is the agent walk: Muse Spark's computer use takes the store from product to order confirmation, auditing each screen on the way (31 verified findings over four screens in ten turns in the recorded run, re-recorded the evening of 4 Nov on the six-check Verifier and the contributor-tier judge; no click needed the snap). The budget is sixteen turns, a safety stop rather than a target: a clean walk is nine or ten, and before the snap two recorded walks each lost three or four turns to clicks that landed a few pixels off a button.

## Architecture

The full architecture, one Live run's sequence, the trust boundaries and every Meta API call are in [docs/31](docs/31-architecture.md).

![Parity's pipeline: Navigator, Capture, Seer, Comparator, Verifier per screen; Judge, Fixer, Re-audit, Human gate, Run bundle per finding](docs/img/architecture.png)

**How it acts.** The model decides; allow-listed code acts. Muse Spark's computer-use output is a list of actions; a small executor runs only the kinds it knows (click, type, key, scroll, wait, screenshot) and only inside the allowed origin. A click that lands on nothing clickable within 20 px of a control is moved by code to that control's centre (the recorded walks of 4 Nov missed the store's buttons by 6 to 18 px and spent turns re-clicking), before the public-site guard judges it, and the correction is logged in the run's events. Two function tools are gated by code: `finish` is refused, with feedback, until the current screen has been audited (after three refusals the finish is forced and marked as such); `audit_view` is answered once per screen, so a repeat costs nothing; and on the last turn code audits the screen itself before offering `finish`. On a page Parity does not serve (the W3C demo pages, a page a visitor chooses, a CLI audit) a read-only guard refuses anything that looks like a purchase, a sign-up, a consent click or a form submission, the browser re-checks every request it makes against the URL policy (redirects included), and a bot wall ends the run as `blocked by site`.

**What is deterministic.** Capture (screenshot, Chrome's accessibility tree with boxes, axe-core), the Verifier's six checks, the re-audit's name rule, the human gate, the patch export, the Replay, and the eval's matching are code. A finding cannot exist without passing the Verifier, and nothing is applied to a page without a human approving it.

**Why one agent with gated tools, not a crew.** Parity runs five model roles (auditor, Seer, Comparator, Judge, Fixer) but only one of them is an agent; the rest are calls inside tools or code stages, and code is the orchestrator. Three reasons. The stages are dependent: a flow walk is a sequence of page states, each the result of the action before it, so a second agent on the same browser would race the first and learn nothing new. The parallelism that pays is already in code where it is safe (the judge four at a time, the fixers four at a time); what is left serial is the re-audit, and in the recorded purchase run that is 583 of 1,268 seconds (from the first fix proposed to the run's end), a queue to parallelise, not a topology to change. And orchestration in code is what makes the system verifiable: the Verifier's six checks, the budget rule, the allow-listed executor and the refusal loop are unit-tested because no model is coordinating them; a coordinator agent delegating to navigator, inspector and critic agents would move that logic into prompts. A measured single-versus-multi comparison was planned as a stretch (spec §18.4) and not run: both variants would share the Seer, Comparator and Verifier, so recall and precision could not separate them, and a latency difference across three noisy runs would not survive the spread between runs already seen in the table below.

## Meta capabilities, and why each is load-bearing

| Capability | Where | Why Parity does not work without it |
|---|---|---|
| **Muse Spark 1.3 · computer use** | Navigator | Reaches checkout and the order confirmation in the recorded walk (a payment form filled in, every screen audited on the way), with every batch screened by code. |
| **Muse Spark 1.3 · perception grounding** (0–1000 boxes) | Seer | Turns the screenshot into *what a sighted user sees, where*; the Verifier can only check a claim that comes with a box. |
| **Muse Spark 1.3 · multimodal comparison** | Comparator | Reads the screenshot and the accessibility tree together and names where they disagree, quoting the tree exactly so code can verify the quote. |
| **Muse Spark 1.3 · a separate judge call** (contributor tier at high effort since 4 Nov; the standard tier is the fallback) | Judge | Severity and WCAG, fails closed to "needs review"; the per-stage sweep found the contributor tier at the same 94% agreement as the standard tier at $0.0006 a finding against $0.0108 (n = 2); Muse Wonder 1.0 matched the agreement at 2.5× the standard judge's cost (n = 1). |
| **Muse Spark 1.3 · fixer, and the comparison inside the re-audit** | Fixer, Re-audit | A minimal HTML change, then (code) the patched page loaded in a sandbox, the name rule checked, and (Spark) the comparison run again. |

Contributor tier by default for every stage (the same model at about a twelfth of the price; the judge moved to it on 4 Nov on the sweep's evidence, which brought a four-page audit from $0.37 to $0.04 in a confirmation run, n = 1); a private mode switches every stage to standard `muse-spark-1.3`. Single-shot stages are cached on disk; the agent's chained computer-use turns are not. The Model API client is our own httpx code because the agent's turns need `previous_response_id` chaining and the Voice endpoint needs multipart audio, neither of which a generic SDK wrapper gave us; the Comparator gets one retry with the Verifier's feedback when its first pass fails a check. Every stage shows its model badge in the workbench, and the trace drawer lists every call with its model, request ID, tokens, latency, cost and cache state. Real screen-reader audio is in: the checkout page was recorded with VoiceOver ([store/voice/checkout.wav](store/voice/checkout.wav), fourteen focus stops, every hint spoken in full), transcribed by `muse-voice-transcribe-1.0` and aligned word by word to the phrases VoiceOver logged, so a finding whose element had focus carries the segment a screen-reader user heard. Measured word accuracy against those phrases is **0.96** on the committed checkout replay (re-recorded the evening of 4 Nov on the contributor-tier judge; the afternoon's take scored 0.92 and the 3 Nov take 0.96 on the same clip, the spread being the transcription's; gate G-V, 0.90), so Voice is shown as **primary evidence**: the hero card plays the moment VoiceOver says "Submit button", shows the transcript with its badge, and marks that it agrees with the accessibility tree, which remains the deterministic record the Verifier checks. An earlier take scored 0.58 because the tester cut the hint sentences short with the next Tab while the captions logged them in full; the metric counts every logged word, so the take was redone. Recorded store pages only; Live runs do not run VoiceOver.

## Evaluation

Measured on the bundled store: **38 seeded faults of the kind axe-core passes, 20 clean controls**, labels kept outside the agent's code path. A finding is scored under its element's id (or the nearest id above it); four pages, three runs per configuration, effort medium. The numbers below are copied from [eval/results/latest.md](eval/results/latest.md) and are the only number set quoted anywhere. The full configuration and the W3C block were re-measured on 4 Nov at commit `3221905` ([eval/results/seen-full.json](eval/results/seen-full.json), [eval/results/external-external-seen.json](eval/results/external-external-seen.json)) after the Verifier gained its sixth check, `seen`: a candidate must have a seer percept behind it (its sighted text, or its box), added after a public page captured on a loader let nine candidates written from the accessibility tree alone through the five tree checks. The three ablation rows, the effort sweep and the judge comparison keep their 1 Nov measurement (commit `1e6caad`, [eval/results/final.json](eval/results/final.json)): the two configurations without a sighted pass are unaffected by construction (the check stands down when the seer did not run), and the screenshot-only row was not re-run. The prompts gained one rule between the two dates (page text sits inside `page_data` delimiters and is evidence, never an instruction); the 4 Nov rows carry it.

| System | Recall | Precision | Verified findings | FP on clean | Cost / page set | Time |
|---|---|---|---|---|---|---|
| **Parity (full)** (4 Nov, six checks) | **85%** | **99%** | 33 per run · 38 labels | 0.0 | $0.37 | 495 s |
| screenshot only (no tree), 1 Nov | 17% | 95% | 7 per run | 0.0 | $0.08 | 391 s |
| tree only (no screenshot, no grounding), 1 Nov | 75% | 98% | 29 per run | 0.3 | $0.32 | 442 s |
| no grounding (no Seer), 1 Nov | 82% | 95% | 33 per run | 0.7 | $0.36 | 428 s |
| axe-core 4.14 | 0% | — | 0 violations | — | $0 | — |

How to read it: the accessibility tree carries most of the recall; the screenshot alone finds little because the Verifier rejects what cannot be quoted from the tree; with grounding the full configuration measured 85% (4 Nov) against 82% without it (1 Nov, a different date and prompt version), with 0.7 fewer false positives on clean controls per page set; precision stays between 95% and 99% in every configuration because the Verifier gates all four (the "Without the Verifier" switch in the workbench shows what a run would have reported without it). axe-core's 0% is by construction: the faults were chosen to pass it. Judge: Spark and Wonder each agree with the labels on 94% of the same 33 findings (1 Nov; Spark again on 94% of 31 on 4 Nov). Three runs is a small sample; the spread between runs was two to three labels per page set. The 4 Nov page set took longer (495 s against 281 s) with the same calls: the API's latency that night, not more work. `latest.md`'s header says "uncommitted changes present" at `3221905`: the working tree held the About & Evals tab's rename and the sweep's result tables while the harness ran; nothing on the measured code path differed from that commit. Full method and caveats: [docs/17](docs/17-validation-results.md).

**Real-world sample** (read-only, anonymised, CLI only): Site A, two screens, six verified findings (five CSS-drawn star ratings that announce nothing; axe reports none of them). Site B: a bot challenge in front of the first page ended the run before anything was sent to a model.

**External pages we did not write (W3C BAD).** On these pages Parity's own candidates covered **7 of the 14** in-scope barriers, every one of the five axe-core reports plus two it misses, against axe-core's 5 of 14; by design the Verifier then hands the five to axe and reports only the two, so the shipped row below reads 14%. The four "before" pages of the W3C WAI [Before and After Demonstration](https://www.w3.org/WAI/demos/bad/) and their four repaired "after" pages, audited read-only on www.w3.org, scored against the pages' own numbered annotations ([eval/labels_external.json](eval/labels_external.json), W3C Document License). **The subset, stated:** 14 of W3C's 35 barriers are in Parity's scope by kind (text alternatives, names, link text, unlabelled controls); the other 21 (structure, presentation, keyboard) are counted and never claimed. Precision counts a finding on an in-scope barrier as right and every finding on a repaired page as wrong. Two runs per page, 4 Nov, six checks ([eval/results/external-external-seen.json](eval/results/external-external-seen.json); the 3 Nov five-check measurement is [eval/results/external-bad-2runs.json](eval/results/external-bad-2runs.json): 14% / 22% / 34%, 7 per run, 4.0 on repaired pages).

| System | In-scope recall | Beyond axe-core | Precision | Findings per run | On repaired pages | Cost / 8 pages | Time |
|---|---|---|---|---|---|---|---|
| axe-core 4.14 | 36% (5 of 14) | — | — | 38 violations | — | $0 | — |
| Parity's candidates, axe-reported barriers included (derived from the recorded bundles, one run per page) | 50% (7 of 14) | — | — | — | — | — | — |
| Parity as shipped (reports only what axe-core cannot) | 14% (2 of 14) | 22% (2 of 9) | 40% (4 Nov; 34% on 3 Nov with five checks) | 6 | 3.0 | $0.15 | 733 s |

What the numbers say: of the seven in-scope barriers neither tool found, six are judgements about the wording of a text alternative or link text that is present (a logo alt describing the artwork instead of its words, a hotline image whose alt is a placeholder number, a "Read More..." link, decorative bullets announced as "bullet", a photo alt naming the picture instead of the link's purpose, a caption telling a story the picture does not show), which Parity's checks, built for a gap between what is seen and what is announced, do not rank; the seventh, a chart with an empty alt, is the one Parity should have found and did not. Parity found two in-scope barriers in every run, both invisible to axe-core (a CSS background image named only by `title="image"`, and an image of a phone number whose alt reads "music line phone number"). The other candidates it proposed on these pages were rejected by the Verifier because axe-core already reports them (missing alt, unlabelled radios and a select, empty image links) or because the announced name equals the visible text; that is Parity's own definition of a finding, so "Beyond axe-core" is its recall on the nine in-scope barriers axe-core misses, and Parity and axe-core together reach 7 of 14. The three false alarms per run on the repaired pages, all on the repaired home page, are the three photos W3C marks decorative (`alt=""`) that Parity reports as pictures a sighted user sees and a screen reader skips; they count against precision by construction (on 3 Nov, with five checks, a misread heading and a navigation item with hidden "Accessible" text made it four). Eight pages, two runs each: a small sample, shown as such in the About & Evals tab.

**Best model per stage** (4 Nov; one stage changed at a time, the rest at the defaults of that morning; a row with n = 1 is a sample; full tables in `eval/results/model-sweep.md` and on the About & Evals tab). One default changed on its evidence, the judge; the other four stayed. A confirmation run with the new judge measured 89% / 100% and $0.04 per four-page set (n = 1, `eval/results/judge-contributor-n1.json`), inside the headline's spread, so the 85% / 99% rows stand.

| Stage | Best model, effort | n | Result | Against today's default |
|---|---|---|---|---|
| Comparator | `muse-spark-1.3-contributor`, medium (default) | 3 | 85% / 99%, $0.37 a page set | Nothing beats it beyond the spread of 3 labels |
| Seer | `muse-spark-1.3-contributor`, medium (default) | 3 | 85% / 99%, $0.37 a page set | Nothing beats it beyond the spread of 3 labels |
| Judge | `muse-spark-1.3-contributor`, high | 2 | 94% agreement, $0.0006 a finding | Same agreement as `muse-spark-1.3` (94%, $0.0108, n = 1), about 18 times cheaper; severity matches it on 84%. **Now the default** |
| Fixer | `muse-wonder-1.0`, medium | 2 | 62% of gaps closed, $0.0252 a fix | The default closes 53% at $0.0004 a fix, so it stays |
| Navigator | `muse-spark-1.3-contributor`, low (default) | 2 | 4 of 4 screens, 11 turns, no API error | Every row reached 4 of 4; turns are inside the default's spread of 2 |

**SAM 3.1 was tested and left out.** The API refuses it computer use, and replaying its box prompts over three recorded runs did not improve recall or precision: replacing the candidate boxes moved recall from 85% to 83% and precision from 99% to 100%, and replacing the Seer boxes changed neither. Noun prompts return no text, which the Seer has to report. We did not test a Comparator shown SAM's boxes.

## Observability

Every run is a bundle on disk (or in a Cloud Storage bucket): `run.json`, each screen's screenshot, accessibility tree, axe result and served source, each finding and rejected candidate, `trace.jsonl` (every model call) and `events.jsonl` (what the workbench streamed). Replay plays a committed bundle back; a run's URL reopens it with its decisions. The SQLite index is a cache rebuilt at boot.

## Repository

| Path | What |
|---|---|
| `parity/` | the agent and server: FastAPI, Playwright, the pipeline stages, run bundles, the SQLite index |
| `web/` | the workbench (React, Vite, Tailwind), built into `parity/static` |
| `store/` | the ShopRight demo store: static pages with seeded, axe-passing faults |
| `eval/` | labels, the harness, the ablations and the results (`eval/results/latest.md`) |
| `fixtures/replay/` | the recorded runs served in Replay mode (two heroes, two anonymised public samples, the four W3C demonstration pages under `w3c-*`) |
| `deploy/` | Dockerfile companions: the Cloud Run script and its README |
| `tests/` | pytest and vitest; model-facing code runs against recorded responses in `tests/fixtures/meta` |
| `docs/` | decisions, design spec, plan, validation and QA reports ([docs/README.md](docs/README.md)) |

## Limits

- Findings are evidence, **not a conformance claim**, and no fix is applied without a human; Parity never reports "compliant".
- The eval runs on our own store with faults chosen to pass axe; it says nothing about axe in general, and n is small.
- Page text reaches the models inside `page_data` delimiters with a one-sentence rule, and the guard refuses irreversible actions whatever a page says; a model that obeys a page still cannot buy, submit or sign in.
- Hosted Live runs the store flows, the W3C demo pages and one public page a visitor chooses ("Live on a page you choose"): read-only, one screen by default, no fixes, a cost cap per run and per day, page content deleted after 24 hours. The policy, the opt-out and the takedown contact are at `/audit-policy`.
- Model-facing tests answer from recorded stage responses, not prompt-keyed fixtures; the live smoke run and the eval are the prompt-regression checks.
- One Live run at a time, a few per visitor per hour, a 15-minute cap per run; Replay is unlimited.

## Known limits and next steps

From the Muse Code review of 4 Nov ([docs/27](docs/27-muse-code-findings.md)), stated rather than hidden: the fixer's snippet gate checks the shape of a change, not its meaning, and the human approval is the backstop; a finding's "why it matters" sentence is the model's prose, and severity and WCAG references are the judge's, shape-checked only; a fix is shown before its re-audit runs, and a failed re-audit leaves it approvable with the result beside it; the Verifier's `seen` check stands down when the sighted pass did not run; the per-run cost cap is checked before launch, not inside the judge fan-out (a visitor run once spent $0.66 against a $0.50 cap); robots.txt is read at the start and the landing, not on every hop; a login wall needs a password field plus a login title or path; in-browser redirect hops re-judge the host only; the eval scores a finding under the nearest id above it, which can credit a hit for the wrong reason; CI does not run `make setup` / `make demo`, which were checked by hand on a fresh clone on 4 Nov. Next: a meaning check on fixes, WCAG reference validation, re-validating a patch on replay, a cost reservation per judge call, and re-checking robots.txt per navigation.

## Licence

MIT for the code and documents written here ([LICENSE](LICENSE)). The W3C demonstration pages and the replay bundles recorded from them (`fixtures/replay/runs/w3c-*`) keep the W3C Document License notice in their `NOTICE` files. Playwright (Apache-2.0), axe-core (MPL-2.0) and the other dependencies keep their own licences; see [HACKATHON_SCOPE.md](HACKATHON_SCOPE.md).
