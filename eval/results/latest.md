# Eval results — 2026-11-02T22:31:31+00:00

Model `muse-spark-1.3-contributor`, judge `muse-spark-1.3`, effort `medium`, 3 run(s) per page, pages product.html, cart.html, checkout.html, confirm.html. Labels: 38 seeded faults, 20 clean controls (`eval/labels.json`). Recall and precision are means over runs; n is verified findings.

Measured at commit `839c39334d3e` (uncommitted changes present), labels sha256 `43b432f8abea`. A finding is scored under its element's id or the nearest id above it.

## Parity vs axe-core (same labels)

| System | Recall | Precision | Verified findings | FP on clean | Cost | Time |
|---|---|---|---|---|---|---|
| Parity (full) | 84% | 97% | 33 per run · 38 labels | 0.0 | $0.374 | 281 s |
| screenshot only | 17% | 95% | 7 per run · 38 labels | 0.0 | $0.080 | 391 s |
| tree only | 75% | 98% | 29 per run · 38 labels | 0.3 | $0.321 | 442 s |
| no grounding | 82% | 95% | 33 per run · 38 labels | 0.7 | $0.360 | 428 s |
| axe-core 4.14 | 0% | — | 0 violations | — | $0 | — |

## Per page (full configuration)

| Page | Recall | Precision | Found / labels | Found in every run | Cost | Time |
|---|---|---|---|---|---|---|
| product.html | 96% | 100% | 16 / 16 | 15 | $0.179 | 95 s |
| cart.html | 85% | 100% | 8 / 9 | 7 | $0.081 | 72 s |
| checkout.html | 74% | 95% | 7 / 9 | 6 | $0.088 | 67 s |
| confirm.html | 58% | 81% | 3 / 4 | 2 | $0.026 | 47 s |

## Effort sweep (full configuration, one run)

| Effort | Recall | Precision | Cost | Time |
|---|---|---|---|---|
| low | 84% | 97% | $0.351 | 231 s |
| medium | 84% | 97% | $0.374 | 281 s |
| high | 74% | 100% | $0.305 | 339 s |

## Judge comparison (same verified findings)

| Judge | Agreement with labels | Needs review | Cost per finding | n |
|---|---|---|---|---|
| muse-spark-1.3 | 94% | 0% | $0.0114 | 33 |
| muse-wonder-1.0 | 94% | 0% | $0.0263 | 33 |

Standard-tier check (`muse-spark-1.3`, one run): recall 82%, precision 100%, $0.465.

## External pages (W3C BAD): labels we did not write

The four 'before' pages of the W3C WAI Before and After Demonstration and their four repaired 'after' pages, audited read-only on www.w3.org (W3C WAI Before and After Demonstration, Copyright © 2012 W3C® (MIT, ERCIM, Keio), W3C Document License; audited read-only). 2 run(s) per page, model `muse-spark-1.3-contributor`, labels sha256 `f5f6a7114e11`. **Subset stated:** 14 of W3C's 35 numbered barriers are in Parity's scope by kind (perceptual gaps: text alternatives, names, link text, unlabelled controls); the other 21 (structure, presentation, keyboard) are counted, never claimed. Precision counts a finding on an in-scope barrier as right and every finding on a repaired page as wrong; findings on elements W3C did not annotate are reported, not scored.

| System | In-scope recall | Beyond axe-core | Precision | Findings per run | On repaired pages | On out-of-scope barriers | Unlabelled | Cost | Time |
|---|---|---|---|---|---|---|---|---|---|
| Parity (full) | 14% | 22% | 34% | 7 | 4.0 | 0.0 | 1.0 | $0.165 | 1031 s |
| axe-core 4.14 | 36% | — | — | 38 violations | — | 4 | — | $0 | — |

The Verifier drops what axe-core already reports, by design: 9 of the 14 in-scope barriers are ones axe-core does not report, and "Beyond axe-core" is Parity's recall on those; Parity and axe-core together reach 50% of the in-scope barriers.

| Page | In-scope hits / labels | Found in every run | Findings | Cost | Time |
|---|---|---|---|---|---|
| bad/before/home.html | 1 / 7 | 1 | 2.0 | $0.050 | 158 s |
| bad/before/news.html | 0 / 3 | 0 | 0.0 | $0.006 | 187 s |
| bad/before/tickets.html | 1 / 2 | 1 | 1.0 | $0.021 | 104 s |
| bad/before/survey.html | 0 / 2 | 0 | 0.0 | $0.003 | 76 s |
| bad/after/home.html | 0 / 0 | 0 | 3.0 | $0.054 | 103 s |
| bad/after/news.html | 0 / 0 | 0 | 0.5 | $0.011 | 101 s |
| bad/after/tickets.html | 0 / 0 | 0 | 0.5 | $0.017 | 197 s |
| bad/after/survey.html | 0 / 0 | 0 | 0.0 | $0.004 | 104 s |

## Real-world sample (anonymised, read-only)

| Site | Pages | Verified | Rejected |
|---|---|---|---|
| Site A | 2 | 6 | 0 |
| Site B | 0 | 0 | 0 |

Findings are evidence, not a conformance claim; a human approves every fix.
