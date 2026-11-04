# 28 — Final claims ledger (4 Nov 2026, evening; prompt 28 D1)

One row per number or factual claim that appears in the video (narration, captions, cards, end card), the README, the form essays (docs/21) or the X post. "Source" is the file a judge can open. Rows marked **pending** wait on the hero re-record push (the attempt-6 session, 4 Nov 21:30–22:35 SAST) and are reconciled in this file before the clips are recorded. Real-world figures come only from the verified-sources file kept outside the repository (28a, 4 Nov) and are tagged primary / vendor / derived as that file tags them.

## 1. Our measured numbers (store, eval, runs)

| # | Claim | Where it appears | Source | Value at source | Mismatch found | Fix |
|---|---|---|---|---|---|---|
| 1 | Recall 85%, precision 99%, 0.0 false positives on 20 clean controls, 38 seeded faults, 33 verified per run | video block 4 card, eval beat, README, docs/21 | `eval/results/latest.md` "Parity vs axe-core"; 3 runs, 4 Nov, commit 3221905, standard-tier judge | 85% / 99% / 0.0 / 20 / 38 / 33 | none | state "3 runs, 4 Nov" wherever n is asked |
| 2 | Cost per **4-page** store set $0.37; time 495 s (8 m 15 s) | card, eval beat, README, docs/21 | `latest.md` | $0.369, 495 s | storyboard v4 and docs/21 said "per 3 pages" / "per page set" | "per 4-page store set" everywhere |
| 3 | Cost with today's defaults $0.04 per 4-page set | eval beat caption, README, docs/21 | `eval/results/judge-contributor-n1.json`, n = 1, 4 Nov 17:03 SAST, git 0ccc2fa (89% / 100% on that run) | $0.043 | new since v4 | always "n = 1, 4 Nov, contributor judge"; never a new headline |
| 4 | Ablations: screenshot only 17%, tree only 75%, no grounding 82% / 95% with 0.7 FP | eval beat, docs/21, README | `latest.md` (1 Nov rows, commit 1e6caad) | 17 / 75 / 82 / 95 / 0.7 | v4 says "grounding adds three points" implicitly (85 vs 82 across dates) | say "85% on 4 Nov against 82% on 1 Nov, different dates" (Muse Code R3) |
| 5 | axe-core 4.14: 0 violations on the demo checkout, 0% recall on the 38 faults | cold open, card, README | `latest.md` | 0 / 0% | v4 says "the standard checker" | name axe-core 4.14; "the faults were chosen to pass it" stays |
| 6 | Judge agreement 94% | eval beat, docs/21 | `latest.md` judge table (31 findings, standard tier, n = 1); confirmation run 94% (32 of 34, contributor tier, n = 1) | 94% both | none | quote with n |
| 7 | Judge default `muse-spark-1.3-contributor` at high; fallback `muse-spark-1.3`; $0.0006 vs $0.0108 a finding (18×, n = 2) | eval beat caption, README, docs/19 §6.1, docs/21 | `eval/results/model-sweep.md` Judge table; `parity/config.py` at 0ccc2fa | as stated | README model line and docs/21 still named the standard judge | README "a separate judge call" row and the contributor sentence; docs/21 essay 7 |
| 8 | Wonder as judge: same 94% agreement at 2.5× the cost per finding ($0.0266 vs $0.0108, n = 1) | README table, docs/21 | `model-sweep.md` Judge table | 2.46 → "2.5×" | README and docs/21 said 2.3× (1 Nov, $0.026 vs $0.011) | 2.5× everywhere, "n = 1, 4 Nov" |
| 9 | Fixer closes 53% of gaps on its first proposal (default); Wonder 62% (29 barriers, n = 2) | README, docs/21 | `model-sweep.md` Fixer table | 53 / 62 | none | never imply every fix closes: "every fix is re-audited, and a human approves" |
| 10 | Seven Meta models tried per role; Wonder refuses the `computer` tool (HTTP 400); SAM 3.1 boxes tighter (overlap 0.61 → 0.75) with recall and precision unchanged | Tooling beat, docs/21, README | `model-sweep.md` "What each model accepted", "SAM 3.1 box prompts" | as stated | none | the claim is "measured model choice per role", with n and dates |
| 11 | Derived: judging ≈ 96% of a run's cost at the standard judge (33 × $0.0108 ≈ $0.36 of $0.37) | docs/21 only | arithmetic on `latest.md` rows | ≈ 96% | — | labelled derived |
| 12 | W3C BAD: axe-core 5 of 14 (36%); Parity's candidates 7 of 14 (50%, all five axe reports plus two it misses); Parity as shipped 2 of 14 (14%), beyond axe 2 of 9 (22%), precision 40%, 3.0 on repaired pages, n = 2 per page, 4 Nov | README, About & Evals tab (re-framed by the attempt-6 session's push) | `latest.md` W3C block (`union_recall` 0.5, `axe_recall` 0.357); the 7-of-14 candidate count is a rescoring of the four committed `w3c-*` bundles with `not_axe` treated as off (one run each, 3 Nov; derived) | as stated | README led with 14% | README paragraph rewritten (§3 below); not used in the video |
| 13 | W3C precision on 3 Nov was 34% with 4.0 on repaired pages (five checks) | README | `eval/results/external-bad-2runs.json` | 34% / 4.0 | both figures appear undated | date both: 40% (4 Nov, six checks), 34% (3 Nov, five checks) |
| 14 | Voice word accuracy 0.92 on the committed checkout replay; 0.96 on the 3 Nov take (gate G-V ≥ 0.90) | cold open caption, README, docs/21 | README "Meta capabilities" paragraph; docs/24; docs/18 §9 Voice note | 0.92 / 0.96 | v4 said "92% word accuracy" (jargon) | caption "real VoiceOver audio · 92% match on this replay"; **pending**: the re-recorded checkout bundle's own figure replaces 0.92 |
| 15 | Hero checkout bundle: 7 verified / 1 rejected, $0.11, 252 s | cold open, close | `fixtures/replay/runs/hero-checkout/run.json` | 7 / 1 / $0.113 / 251,875 ms | — | **pending** re-record |
| 16 | Purchase walk: 30 verified / 4 rejected over four screens in nine turns, finish called ("order SR-10428 confirmed"), 27 fixes / 27 re-audits (14 closed), $0.373, 1,343 s, re-audit share 669 s | walk beat, README, docs/21 | `fixtures/replay/runs/hero-purchase/run.json`; `docs/30` §4 | as stated | v4 said 34 findings, "12-turn budget spent", "Audit ended early" (attempt 2) | **pending** re-record; whichever bundle ships, the walk beat quotes its own count and turns |
| 17 | Six Verifier checks on current bundles; five on the 3 Nov W3C and BBC runs | walk beat, README | `docs/19` §4; the bundles' `verifier.checks` | 6 / 5 | README "What you will see" said "Five green ticks" | "six" on the hero bundles; "five" only where a 3 Nov bundle is shown |
| 18 | Turn budget 16 (a safety stop; a clean walk is nine) | README, docs/19 §18.3 | `parity/config.py` STORE_MAX_TURNS at d293707 | 16 | v4 said "12-turn budget" | state the budget as the recorded walk used it |
| 19 | Live beat: books.toscrape.com (a travel category page), read-only, one screen, 4 Nov: 4 verified / 0 rejected, axe-core 4, 1 m 27 s, $0.008 | live beat chip and captions, docs/21 | hosted run `20261104-193842-92175beb` (§2) | as stated | — | chip "Live · 4 Nov · 1 m 27 s · $0.008"; caption "axe-core 4 · Parity 4 verified"; no red row on this run, so the Verifier-refusal beat stays on the hero walk |
| 20 | Ticketmaster: `blocked by site: bot challenge` in seconds at $0 | live beat tail | `docs/23` §10.7 (9 s, 3 Nov); `clips-v4/log.json` (6.5 s, 4 Nov) | 9 s / 6.5 s | — | narration "in seconds"; caption "a bot wall: stopped, $0" |
| 21 | Real-world sample: Site A two screens, six verified, five star ratings that announce nothing | README, About & Evals | `fixtures/replay/runs/public-a`; `docs/17` | 6 / 0, $0.11, 184 s | — | Site A is books.toscrape.com (a published scraping sandbox); naming it is allowed, the README keeps "Site A" |
| 22 | `latest.md` header "uncommitted changes present" at 3221905 | README | ledger (`.superpowers/.../progress.md`, 4 Nov) | the working tree held the About & Evals rename and the sweep tables while the harness ran; no code on the measured path differed from 3221905 | unexplained in any judge-facing doc | one README sentence (§3) |
| 23 | Tests: pytest 558, vitest 166 at 0ccc2fa | README, docs/21 | `docs/30` §2 | 558 / 166 | **pending** the re-record push may change pins | quote the final counts |
| 24 | "Three Meta models" | v4 close | runtime models: `muse-spark-1.3-contributor`, `muse-spark-1.3` (fallback, private mode), `muse-voice-transcribe-1.0` | two models, one in two tiers | overclaim | "Spark in two tiers, and Voice Transcribe" |
| 25 | "Built this week"; pre-existing: Playwright, axe-core and the libraries in HACKATHON_SCOPE; Claude Code and Muse Code assisted | scope line, README, HACKATHON_SCOPE | `HACKATHON_SCOPE.md` | as listed | README said "the usual web stack" (Muse Code R6, disqualification-tagged) | one wording: "Built this week on Meta's Muse Spark and Voice Transcribe; Playwright, axe-core and the libraries in HACKATHON_SCOPE are pre-existing open source." |
| 26 | Licence: MIT for our code; W3C pages and their replay bundles keep the W3C notice | README | `LICENSE`, `fixtures/replay/runs/w3c-*/NOTICE` | — | README said "MIT for everything written here" (R6) | README Licence section |

## 2. The live run used in the video

| Field | Value |
|---|---|
| Page | `https://books.toscrape.com/catalogue/category/books/travel_2/index.html` (Zyte's scraping sandbox: "a safe place for beginners learning web scraping and for developers validating their scraping technologies"; no robots.txt; no terms barring automation) |
| Why this page | The FlySafair terms list "intelligent agents or any other automated process" as abuse (5.11 viii) and bar reproducing the site (5.7); Takealot's bar "any robot, spider, other automatic device" monitoring or copying; BBC's require permission for content used "to do computer analysis" (8a) and for its logo (7d); every US retailer and airline checked (Target, Best Buy, Southwest; Walmart, Etsy, Expedia by archived copies) bars robots and agents, Target and Best Buy naming agentic tools. The sandbox exists to be visited by automation, looks like a shop, and carries the hero's class of barrier. |
| Run 1 (home page) | `20261104-193726-86c1cf03`, 4 verified / 0 rejected, axe 4, done in 9 s at $0.00: the server answered from its response cache (the page was sampled on 1 Nov), so it is not used on camera |
| Run 2 (category page, unseen; **the one used**) | `20261104-193842-92175beb`, `https://books.toscrape.com/catalogue/category/books/travel_2/index.html`, 4 Nov 21:38 SAST on parity-00023-qkh: 4 verified / 0 rejected, axe-core 4 violations, 87 s (1 m 27 s), $0.0078, six checks passed on every card, judge `muse-spark-1.3-contributor` on all four, every trace row a real call (seer 27.5 s, comparator 21.4 s, judges 12–31 s). Findings: four star ratings ("2 out of 5 stars", "4 out of 5 stars", "3 out of 5 stars", "2 out of 5 stars") announced as nothing; two rated serious, two moderate. The link lives 24 h (until about 21:40 SAST Thu); the clip is the deliverable |
| Caption set | "any public page, read-only" · "public address · robots.txt honoured" · "axe-core 4 · Parity 4 verified" · "sees: 4 out of 5 stars" · "hears: nothing" · "six code checks, all passed" · "a bot wall: stopped, $0" |

## 3. README edits (docs only, after the re-record push)

1. Scope line (row 25) and the Licence section (row 26).
2. "Five green ticks" → "Six green ticks" with the sixth named (`seen`); "the standard checker" wording kept out of the README (it already names axe-core).
3. The judge rows: default `muse-spark-1.3-contributor` at high, fallback standard; Wonder 2.5× (n = 1); the confirmation run's $0.04 beside $0.37; "measured alternative, n = 1".
4. "It finds the barriers axe-core misses" → "It finds many of the barriers axe-core misses (85% of 38 seeded ones on our store)"; "proves each one" → "proves each one it reports".
5. "Reaches the screens a fixed script would not" → "Reaches checkout and the order confirmation in the recorded walk".
6. W3C paragraph: axe-core 5 of 14; Parity's candidates 7 of 14 (all five axe reports plus two it misses); the Verifier defers the five by design; shipped 2 of 14 and 2 of 9; precision 40% (three decorative photos on the repaired home page); 34% on 3 Nov dated; the seven neither tool found and why (six are judgements on the wording of a present text alternative or link text; the chart with an empty alt is the one Parity should have found).
7. "grounding adds three points" → dated comparison (row 4); "single-shot stages are cached; chained agent turns are not"; one sentence on why our own httpx client; the Comparator retry mentioned.
8. One sentence on `latest.md`'s "uncommitted changes present" (row 22).
9. A "Known limits and next steps" section crediting the Muse Code review (R1: the fixer's snippet gate checks shape, not meaning; WCAG references are the judge's, shape-checked; a fix is shown before its re-audit and a failed re-audit leaves it approvable; `seen` stands down when the sighted pass did not run; R2: the cost cap is checked before launch, not inside the judge fan-out; robots.txt read at start and landing; login walls need a password field plus a login title or path; redirect hops re-judge host only; R3: scoring by nearest id above and text anchors; R7: no CI run of `make setup` / `make demo`, checked by hand on a fresh clone on 4 Nov).
10. Under "## Architecture", one line linking `docs/31-architecture.md`.
11. The AI-assistance line in HACKATHON_SCOPE: "Claude Code and Muse Code were used as coding assistants during the event; the design, the code and the tests are the builder's work."

## 4. Real-world figures used on screen (28a rows; each with its tag)

| Figure | On-screen wording | 28a row | Tag |
|---|---|---|---|
| 95.9% of the top million home pages have detectable WCAG failures | "95.9% of top-million home pages fail WCAG (WebAIM, 2026)" | 1a | primary |
| 56.1 errors per home page | "56.1 detectable errors a page (WebAIM, 2026)" | 1c | primary; alternate |
| Best of ten automated tools found 41% of barriers | "the best automated tool caught 41% (UK GDS, 2017)" | 4c | primary |
| 5,114 US digital-accessibility suits in 2025; 70% e-commerce | "5,114 US suits in 2025 · 70% e-commerce (UsableNet)" | 2a, 2c | vendor (said so in the README sources) |
| EU Accessibility Act covers e-commerce since 28 June 2025; Germany fines up to €100,000 | "EU Accessibility Act: e-commerce, since 28 Jun 2025 · fines to €100,000 (Germany)" | 7a, 7b | primary (statute) |
| One retailer: $46,000 legal fees + $13,000 fixes | "one retailer: $46,000 in legal fees, $13,000 to fix (WSJ, 2024)" | 3c | journalism via vendor |
| 69% of disabled users click away | "69% click away from hard sites (Click-Away Pound, 2019)" | 5a | primary (survey) |
| Manual audit $100–$250 per key page | "manual audits: $100–$250 a page (vendor pricing, 2026)" | 4a | vendor |
| ~3 expert hours to evaluate one page | "about 3 expert hours a page (Deque, 2013)" | 4b | vendor, old |
| 43 million blind; 295 million moderate–severe impairment | "43 million blind · 295 million with moderate to severe impairment (Lancet, 2020)" | 6b | primary |
| $674bn disposable income (US working-age adults with disabilities) | "$674bn in US disposable income (AIR, 2026)" | 5c | primary |
| California: at least $4,000 per violation | alternate only | 3d | primary (statute) |

**Derived, shown as such:** $0.37 ÷ 4 pages ≈ $0.09 a page (our store, 4 Nov, 3 runs); no ratio against the manual-audit price is shown (vendor-priced, and not a full audit). Never added together: UsableNet's 5,114 and Seyfarth's 3,117. Never shown: the Netherlands maximum fine, overlay shares, Deque's 57%.

## 5. Decisions recorded from Checkpoint 1 (4 Nov, 19:00–21:40 SAST)
Problem statement Push the Frontier (software) (doc 18 §10). Purchase bundle: the fresh re-record if it lands, else attempt 6. Scope line as row 25. Tagline: "Parity closes the gap between what's seen and what's heard." Live page: books.toscrape.com (§2); FlySafair, BBC and Takealot excluded by their terms; W3C kept in the eval and out of the video. Judge change: $0.37 headline with the $0.04 confirmation beside it. No code pushes except the attempt-6 session's bundle push with the About & Evals change. Docs split before submission: internal docs move to a git-ignored `local-docs/`. Real tester session: none; no quote. YouTube public. Team "Parity", Taahir Suleman. Muse Code rating 4; obstacle "reliability".
