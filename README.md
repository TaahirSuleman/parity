# Parity

**An agent that walks a site's key flows and compares what a sighted user sees with what a screen-reader user gets.** It finds the barriers axe-core misses, proves each one against the page's own accessibility tree, proposes a fix, re-checks it, and leaves the decision to a human.

Built this week (26 Oct – 4 Nov 2026) for the Meta Global AI Developer Hackathon on Meta's **Muse Spark 1.3**. Pre-existing open source: Playwright, axe-core and the usual web stack — listed in [HACKATHON_SCOPE.md](HACKATHON_SCOPE.md). Everything else in this repository was written during the event.

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

axe-core reports **0 violations** on the demo checkout. Parity's Replay then shows seven verified findings on that page. The one it opens on: a sighted shopper sees a button that says **Pay R1,249**; a screen reader announces **button, "Submit"**. Five green ticks say why that is a finding and not a guess: the box landed on a real element, the quoted role and name equal the accessibility tree exactly, the visible text differs from the name, axe does not already report it, and it is not a duplicate. The judge rates it serious (WCAG 2.5.3, Label in Name), the fixer proposes a one-line change, the re-audit loads the patched page in a sandbox and the screen reader now says "Pay R1,249". You approve it with a reason, and **Download fix.patch** gives you a diff that applies to `store/`.

**Live on a page you choose** (hosted, third mode in the header): type a public address, affirm it is public and yours to audit, and Parity audits that screen as a visitor would see it, read-only, with no fixer and no re-audit. A private or internal address is refused in one sentence; robots.txt is honoured; a bot wall or a login ends the run as `blocked by site` and the workbench says so. Four W3C "Before and After Demonstration" pages are also offered as flows.

The Purchase flow (one pick away) is the agent walk: Muse Spark's computer use takes the store from product to order confirmation in nine turns, auditing each screen on the way (35 verified findings over four screens in the recorded run).

## Architecture

![Parity's pipeline: Navigator, Capture, Seer, Comparator, Verifier per screen; Judge, Fixer, Re-audit, Human gate, Run bundle per finding](docs/img/architecture.png)

**How it acts.** The model decides; allow-listed code acts. Muse Spark's computer-use output is a list of actions; a small executor runs only the kinds it knows (click, type, key, scroll, wait, screenshot) and only inside the allowed origin. Two function tools are gated by code: `finish` is refused, with feedback, until the current screen has been audited (after three refusals the finish is forced and marked as such); `audit_view` is answered once per screen, so a repeat costs nothing; and on the last turn code audits the screen itself before offering `finish`. On a page Parity does not serve (the W3C demo pages, a page a visitor chooses, a CLI audit) a read-only guard refuses anything that looks like a purchase, a sign-up, a consent click or a form submission, the browser re-checks every request it makes against the URL policy (redirects included), and a bot wall ends the run as `blocked by site`.

**What is deterministic.** Capture (screenshot, Chrome's accessibility tree with boxes, axe-core), the Verifier's five checks, the re-audit's name rule, the human gate, the patch export, the Replay, and the eval's matching are code. A finding cannot exist without passing the Verifier, and nothing is applied to a page without a human approving it.

## Meta capabilities, and why each is load-bearing

| Capability | Where | Why Parity does not work without it |
|---|---|---|
| **Muse Spark 1.3 · computer use** | Navigator | Reaches the screens a fixed script would not (quantity changes, a payment form filled in, the confirmation), with every batch screened by code. |
| **Muse Spark 1.3 · perception grounding** (0–1000 boxes) | Seer | Turns the screenshot into *what a sighted user sees, where*; the Verifier can only check a claim that comes with a box. |
| **Muse Spark 1.3 · multimodal comparison** | Comparator | Reads the screenshot and the accessibility tree together and names where they disagree, quoting the tree exactly so code can verify the quote. |
| **Muse Spark 1.3 · a separate judge call** | Judge | Severity and WCAG, fails closed to "needs review"; Muse Wonder 1.0 was measured as an alternative judge (same agreement, 2.3× the cost). |
| **Muse Spark 1.3 · fixer, and the comparison inside the re-audit** | Fixer, Re-audit | A minimal HTML change, then (code) the patched page loaded in a sandbox, the name rule checked, and (Spark) the comparison run again. |

Contributor tier by default (the same model at about a twelfth of the price); a private mode switches every stage to standard `muse-spark-1.3`. Every stage shows its model badge in the workbench, and the trace drawer lists every call with its model, request ID, tokens, latency, cost and cache state. Real screen-reader audio is in: the checkout page was recorded with VoiceOver ([store/voice/checkout.wav](store/voice/checkout.wav), fourteen focus stops), transcribed by `muse-voice-transcribe-1.0` and aligned word by word to the phrases VoiceOver logged, so a finding whose element had focus carries the segment a screen-reader user heard. Measured word accuracy against those phrases is **0.58** (gate G-V was 0.90, the hint sentences cut short by the next Tab count against it), so Voice is shown as **corroboration beside the accessibility tree, not as primary evidence**: the hero card plays the moment VoiceOver says "Submit button" and marks that the transcript agrees with the tree. Recorded store pages only; Live runs do not run VoiceOver.

## Evaluation

Measured on the bundled store: **38 seeded faults of the kind axe-core passes, 20 clean controls**, labels kept outside the agent's code path. A finding is scored under its element's id (or the nearest id above it); four pages, three runs per configuration, effort medium. The numbers below are copied from [eval/results/latest.md](eval/results/latest.md) (commit `1e6caad`, 1 Nov) and are the only number set quoted anywhere. The prompts have since gained one rule (page text sits inside `page_data` delimiters and is evidence, never an instruction); the eval has not been re-run on them, and the smoke suite's recorded W3C run is the regression check.

| System | Recall | Precision | Verified findings | FP on clean | Cost / page set | Time |
|---|---|---|---|---|---|---|
| **Parity (full)** | **84%** | **97%** | 33 per run · 38 labels | 0.0 | $0.37 | 281 s |
| screenshot only (no tree) | 17% | 95% | 7 per run | 0.0 | $0.08 | 391 s |
| tree only (no screenshot, no grounding) | 75% | 98% | 29 per run | 0.3 | $0.32 | 442 s |
| no grounding (no Seer) | 82% | 95% | 33 per run | 0.7 | $0.36 | 428 s |
| axe-core 4.14 | 0% | — | 0 violations | — | $0 | — |

How to read it: the accessibility tree carries most of the recall; the screenshot alone finds little because the Verifier rejects what cannot be quoted from the tree; grounding adds two points of recall and removes 0.7 false positives on clean controls per page set; precision stays between 95% and 98% in every configuration because the Verifier gates all four (the "Without the Verifier" switch in the workbench shows what a run would have reported without it). axe-core's 0% is by construction: the faults were chosen to pass it. Judge: Spark and Wonder each agree with the labels on 94% of the same 33 findings. Three runs is a small sample; the spread between runs was two to three labels per page set. Full method and caveats: [docs/17](docs/17-validation-results.md).

**Real-world sample** (read-only, anonymised, CLI only): Site A, two screens, six verified findings (five CSS-drawn star ratings that announce nothing; axe reports none of them). Site B: a bot challenge in front of the first page ended the run before anything was sent to a model.

**External pages we did not write (W3C BAD).** The four "before" pages of the W3C WAI [Before and After Demonstration](https://www.w3.org/WAI/demos/bad/) and their four repaired "after" pages, audited read-only on www.w3.org, scored against the pages' own numbered annotations ([eval/labels_external.json](eval/labels_external.json), W3C Document License). **The subset, stated:** 14 of W3C's 35 barriers are in Parity's scope by kind (text alternatives, names, link text, unlabelled controls); the other 21 (structure, presentation, keyboard) are counted and never claimed. Precision counts a finding on an in-scope barrier as right and every finding on a repaired page as wrong. Two runs per page, 3 Nov ([eval/results/external-bad-2runs.json](eval/results/external-bad-2runs.json)).

| System | In-scope recall | Beyond axe-core | Precision | Findings per run | On repaired pages | Cost / 8 pages | Time |
|---|---|---|---|---|---|---|---|
| Parity (full) | 14% (2 of 14) | 22% (2 of 9) | 34% | 7 | 4.0 | $0.17 | 1,031 s |
| axe-core 4.14 | 36% (5 of 14) | — | — | 38 violations | — | $0 | — |

What the numbers say: Parity found two in-scope barriers in every run, both invisible to axe-core (a CSS background image named only by `title="image"`, and an image of a phone number whose alt reads "music line phone number"). The other candidates it proposed on these pages, about nine per page, were rejected by the Verifier because axe-core already reports them (missing alt, unlabelled radios and a select, empty image links) or because the announced name equals the visible text; that is Parity's own definition of a finding, so "Beyond axe-core" is its recall on the nine in-scope barriers axe-core misses, and Parity and axe-core together reach 7 of 14. The four false alarms per run on the repaired pages are three photos W3C marks decorative (`alt=""`) that Parity reports as pictures a sighted user sees and a screen reader skips, a heading the Seer misread by one letter, and a navigation item with hidden "Accessible" text; they count against precision by construction. Eight pages, two runs each: a small sample, shown as such in the Eval tab.

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

## Licence

MIT for everything written here. Playwright (Apache-2.0), axe-core (MPL-2.0) and the other dependencies keep their own licences; see [HACKATHON_SCOPE.md](HACKATHON_SCOPE.md).
