# Submission rules + cold-review checklist (from recipe v3 Part 7)

## Part 7: Lessons from Resilix (Gemini 3 Hackathon, not placed) against the 13 winners (v3)

Full evidence is in `15-gemini3-postmortem-resilix-vs-winners.md`.

**What Resilix got right, and we keep:**
- typed contracts;
- 122 tests;
- a deterministic simulator;
- real systems of record (Jira, GitHub);
- a merge-policy gate;
- per-role reasoning budgets.

No Gemini 3 winner showed a test suite. Meta's Technical Depth (20%) and Agents 102 reward exactly these, so we keep them. They just don't win on their own.

**What the winners had that Resilix didn't:**
1. **Product-first videos.** Every top-3 video is product-first; Resilix spent its first ~75 s on slides.
2. **A live hero moment.** Resilix cut its live run.
3. **Perceptual input.** All three placed winners take satellite, audio/drone or live-camera input; Resilix was text-only.
4. **A UI where the decision happens.** Resilix had a read-only monitor, with incidents triggered from a CLI.
5. **A visible human approval click.** Resilix's video said "merged autonomously without human interaction".
6. **A person in a moment.** Resilix had an abstract "cascading errors".
7. **Under 3:00, with everything inside it.** Resilix ran 4:14, with impact at 3:40.

**Recipe rules added in v3** (these extend the R1–R4 filters in constitution Article VIII; see doc 15 §9 for the evidence behind each):

| # | Rule | Check |
|---|---|---|
| L1 | Demo-first video: product by 0:05, ≥ 80% of runtime on the product; deck only as overlays (≤ 10 s each, ≤ 20 s total) | Storyboard §4.4; timed edit |
| L2 | One live, uncut hero moment, in which an input that humans or rules get wrong is shown being got right | Written in §4.1 item 10 before building |
| L3 | Hard cap 2:55; everything that matters lands before 2:50 | Measured on the rendered file |
| L4 | Perception is visible: non-text input, model output drawn on the media, ablation shows the drop | Tooling 25%; Q8 of the form |
| L5 | The UI is the workbench: trigger, stream, evidence, approve, all in the UI; a no-login golden-case button on the public URL; no silent mock fallback | A judge can run it in < 60 s |
| L6 | A visible human gate with a reason | Recorded in the video |
| L7 | Accurate feature naming; each named capability has an on-screen artefact | Cold-review checklist |
| L8 | Honest actuation: "the model decides; allow-listed code acts" stated as a guardrail | README "How it acts" section |
| L9 | One consistent, measured number set; n disclosed | grep across video script, README, form |
| L10 | A person in a moment in the first 15 s | Script line 1 |
| L11 | Submission QA by a cold reviewer at D7 | Checklist below |
| L12 | Plan backwards from the video: feature freeze D6 noon; video D6–D7 with a reshoot buffer | Build plan |

**Recipe screening filters added to R1–R4:**
- **R5 Perceptual load:** at least one non-text modality is load-bearing *and* demoable on screen.
- **R6 Workbench:** the decision moment naturally lives in a UI a judge can operate.
- **R7 Hero moment:** a one-sentence "rules or humans miss it, we catch it" moment exists for the golden case.
- **R8 Face:** a named person in a vivid scenario, not an abstract system failure.

**Cold-review checklist (L11).** Run at D7 by a fresh agent or a person who has not seen the build.
- **Video:**
  - length ≤ 2:55;
  - product visible at 0:05;
  - no slide > 10 s;
  - hero moment uncut or labelled "2×";
  - the human approval click is visible;
  - impact lands before 2:50;
  - burned-in captions;
  - no failed or test runs visible on screen.
- **Consistency:**
  - every number matches the README;
  - no statement contradicts the README;
  - every Meta feature named matches what the code does;
  - every title, slide and file name belongs to *this* project.
- **Live product:**
  - the public URL loads without login;
  - the golden-case button runs to completion (live or labelled replay);
  - no mock data is shown unlabelled.
- **Repo:**
  - the third-party documents are gone (`git ls-files docs/hackathon docs/learnings` lists none of `01-*`, `02-*`, `03-*`, `11*`, `12a*`, `13*`);
  - every file the README links to exists;
  - the README states what is deterministic;
  - the architecture diagram is an image;
  - the hackathon-built scope is stated.
- **Links:** YouTube public; all links open; no Drive links; every contributor listed.
