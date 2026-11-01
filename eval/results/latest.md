# Eval results — 2026-10-31T22:45:18+00:00

Model `muse-spark-1.3-contributor`, judge `muse-spark-1.3`, effort `medium`, 3 run(s) per page, pages product.html, cart.html, checkout.html, confirm.html. Labels: 38 seeded faults, 20 clean controls (`eval/labels.json`). Recall and precision are means over runs; n is verified findings.

Measured at commit `1e6caad85e86`, labels sha256 `43b432f8abea`. A finding is scored under its element's id or the nearest id above it.

## Parity vs axe-core (same labels)

| System | Recall | Precision | Findings | FP on clean | Cost | Time |
|---|---|---|---|---|---|---|
| Parity (full) | 84% | 97% | 33 / 38 labels | 0.0 | $0.374 | 281 s |
| screenshot only | 17% | 95% | 7 / 38 labels | 0.0 | $0.080 | 391 s |
| tree only | 75% | 98% | 29 / 38 labels | 0.3 | $0.321 | 442 s |
| no grounding | 82% | 95% | 33 / 38 labels | 0.7 | $0.360 | 428 s |
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

## Real-world sample (anonymised, read-only)

| Site | Pages | Verified | Rejected |
|---|---|---|---|
| Site A | 2 | 6 | 0 |
| Site B | 0 | 0 | 0 |

Findings are evidence, not a conformance claim; a human approves every fix.
