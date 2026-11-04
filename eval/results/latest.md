# Eval results — 2026-11-03T23:59:15+00:00

Model `muse-spark-1.3-contributor`, judge `muse-spark-1.3`, effort `medium`, 3 run(s) per page, pages product.html, cart.html, checkout.html, confirm.html. Labels: 38 seeded faults, 20 clean controls (`eval/labels.json`). Recall and precision are means over runs; n is verified findings.

Measured at commit `3221905baa83` (uncommitted changes present), labels sha256 `43b432f8abea`. A finding is scored under its element's id or the nearest id above it.

## Parity vs axe-core (same labels)

| System | Recall | Precision | Verified findings | FP on clean | Cost | Time |
|---|---|---|---|---|---|---|
| Parity (full) | 85% | 99% | 33 per run · 38 labels | 0.0 | $0.369 | 495 s |
| screenshot only | 17% | 95% | 7 per run · 38 labels | 0.0 | $0.080 | 391 s |
| tree only | 75% | 98% | 29 per run · 38 labels | 0.3 | $0.321 | 442 s |
| no grounding | 82% | 95% | 33 per run · 38 labels | 0.7 | $0.360 | 428 s |
| axe-core 4.14 | 0% | — | 0 violations | — | $0 | — |

## Per page (full configuration)

| Page | Recall | Precision | Found / labels | Found in every run | Cost | Time |
|---|---|---|---|---|---|---|
| product.html | 92% | 100% | 16 / 16 | 13 | $0.168 | 181 s |
| cart.html | 81% | 100% | 8 / 9 | 6 | $0.075 | 118 s |
| checkout.html | 81% | 100% | 8 / 9 | 7 | $0.097 | 128 s |
| confirm.html | 75% | 92% | 4 / 4 | 2 | $0.029 | 68 s |

## Effort sweep (full configuration, one run)

| Effort | Recall | Precision | Cost | Time |
|---|---|---|---|---|
| low | 84% | 97% | $0.351 | 231 s |
| medium | 84% | 97% | $0.374 | 281 s |
| high | 74% | 100% | $0.305 | 339 s |

## Judge comparison (same verified findings)

| Judge | Agreement with labels | Needs review | Cost per finding | n |
|---|---|---|---|---|
| muse-spark-1.3 | 94% | 0% | $0.0108 | 31 |

Standard-tier check (`muse-spark-1.3`, one run): recall 82%, precision 100%, $0.465.

## External pages (W3C BAD): labels we did not write

The four 'before' pages of the W3C WAI Before and After Demonstration and their four repaired 'after' pages, audited read-only on www.w3.org (W3C WAI Before and After Demonstration, Copyright © 2012 W3C® (MIT, ERCIM, Keio), W3C Document License; audited read-only). 2 run(s) per page, model `muse-spark-1.3-contributor`, labels sha256 `f5f6a7114e11`. **Subset stated:** 14 of W3C's 35 numbered barriers are in Parity's scope by kind (perceptual gaps: text alternatives, names, link text, unlabelled controls); the other 21 (structure, presentation, keyboard) are counted, never claimed. Precision counts a finding on an in-scope barrier as right and every finding on a repaired page as wrong; findings on elements W3C did not annotate are reported, not scored.

| System | In-scope recall | Beyond axe-core | Precision | Findings per run | On repaired pages | On out-of-scope barriers | Unlabelled | Cost | Time |
|---|---|---|---|---|---|---|---|---|---|
| Parity (full) | 14% | 22% | 40% | 6 | 3.0 | 0.0 | 1.0 | $0.151 | 733 s |
| axe-core 4.14 | 36% | — | — | 38 violations | — | 4 | — | $0 | — |

The Verifier drops what axe-core already reports, by design: 9 of the 14 in-scope barriers are ones axe-core does not report, and "Beyond axe-core" is Parity's recall on those; Parity and axe-core together reach 50% of the in-scope barriers.

| Page | In-scope hits / labels | Found in every run | Findings | Cost | Time |
|---|---|---|---|---|---|
| bad/before/home.html | 1 / 7 | 1 | 2.0 | $0.052 | 129 s |
| bad/before/news.html | 0 / 3 | 0 | 0.0 | $0.003 | 64 s |
| bad/before/tickets.html | 1 / 2 | 1 | 1.0 | $0.023 | 102 s |
| bad/before/survey.html | 0 / 2 | 0 | 0.0 | $0.003 | 61 s |
| bad/after/home.html | 0 / 0 | 0 | 3.0 | $0.059 | 120 s |
| bad/after/news.html | 0 / 0 | 0 | 0.0 | $0.005 | 111 s |
| bad/after/tickets.html | 0 / 0 | 0 | 0.0 | $0.003 | 74 s |
| bad/after/survey.html | 0 / 0 | 0 | 0.0 | $0.003 | 70 s |

## Real-world sample (anonymised, read-only)

| Site | Pages | Verified | Rejected |
|---|---|---|---|
| Site A | 2 | 6 | 0 |
| Site B | 0 | 0 | 0 |
| W3C demo: home | 1 | 2 | 16 |
| W3C demo: news | 1 | 0 | 8 |
| W3C demo: tickets | 1 | 1 | 7 |
| W3C demo: survey | 1 | 0 | 13 |

Findings are evidence, not a conformance claim; a human approves every fix.
