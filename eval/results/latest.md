# Eval results — 2026-10-31T21:35:38+00:00

Model `muse-spark-1.3-contributor`, judge `muse-spark-1.3`, effort `medium`, 1 run(s) per page, pages product.html, cart.html, checkout.html, confirm.html. Labels: 37 seeded faults, 20 clean controls (`eval/labels.json`). Recall and precision are means over runs; n is verified findings.

## Parity vs axe-core (same labels)

| System | Recall | Precision | Findings | FP on clean | Cost | Time |
|---|---|---|---|---|---|---|
| Parity (full) | 68% | 86% | 29 / 37 labels | 1.0 | $0.327 | 246 s |
| axe-core 4.14 | 0% | — | 0 violations | — | $0 | — |

## Per page (full configuration)

| Page | Recall | Precision | Found / labels | Found in every run | Cost | Time |
|---|---|---|---|---|---|---|
| product.html | 67% | 83% | 10 / 15 | 10 | $0.134 | 77 s |
| cart.html | 67% | 86% | 6 / 9 | 6 | $0.076 | 61 s |
| checkout.html | 78% | 100% | 7 / 9 | 7 | $0.095 | 65 s |
| confirm.html | 50% | 67% | 2 / 4 | 2 | $0.022 | 43 s |

## Effort sweep (full configuration, one run)

| Effort | Recall | Precision | Cost | Time |
|---|---|---|---|---|
| low | 70% | 87% | $0.332 | 199 s |
| medium | 68% | 86% | $0.327 | 246 s |
| high | 62% | 92% | $0.275 | 306 s |

## Judge comparison (same verified findings)

| Judge | Agreement with labels | Needs review | Cost per finding | n |
|---|---|---|---|---|
| muse-spark-1.3 | 92% | 0% | $0.0110 | 29 |
| muse-wonder-1.0 | 85% | 0% | $0.0272 | 29 |

Standard-tier check (`muse-spark-1.3`, one run): recall 74%, precision 93%, $0.455.

Findings are evidence, not a conformance claim; a human approves every fix.
