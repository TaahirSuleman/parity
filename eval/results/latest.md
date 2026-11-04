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

## Per-stage model and effort sweep

Measured at commit `76d98b681945`, labels sha256 `43b432f8abea`, 2026-11-04T13:25:22+00:00. One stage at a time, every other stage at today's default. Seer and Comparator rows run the store's page set (38 seeded faults, 20 clean controls); Judge and Fixer rows re-use the verified findings of the first recorded run of 4 Nov, so every model sees the same findings; Navigator rows walk the purchase flow with no fixes. In Seer, Comparator and Navigator rows the judge ran on the contributor tier of the same model (a judgement enters neither recall nor precision); "Cost with the default judge" projects the row at the default judge's price per finding. Accuracy is over the faults and the clean controls: a clean control with no finding is a true negative. A row with n = 1 is a sample, not a measurement of spread. A gap counts as closed only when the sighted text appears in the new accessible name, so a barrier sighted as a description ("trash icon button") cannot pass with a correct name such as "Remove item": read gaps closed with "Comparator still flags". muse-spark-1.1 has no price in our table; its rows print the price as unknown and cannot win on cost. Spend $6.28, 281 min of model and browser time.

### What each model accepted (one call each)

| Model | JSON | Grounding | Computer use |
|---|---|---|---|
| muse-spark-1.3-contributor | yes | yes | yes |
| muse-spark-1.3 | yes | yes | yes |
| muse-spark-1.2-contributor | yes | yes | yes |
| muse-spark-1.2 | yes | yes | yes |
| muse-spark-1.1 | yes | yes | yes |
| muse-wonder-1.0 | yes | yes | no (HTTP 400: {"error":{"code":null,"message":"Unsupported tool type: 'computer'","param":"too) |
| sam-3.1 | no (no usable answer) | no (no usable answer) | no (HTTP 400: {"error":{"code":null,"message":"Unsupported tool type: 'computer'","param":"too) |

### SAM 3.1 box prompts, replayed on the recorded runs

The spike's Spark-style requests were not SAM's prompt format, so 114 recorded candidate boxes and 341 Seer boxes from 3 runs went to sam-3.1 as box prompts (40 images, about $0.10 at a price from our notes, not from Meta's API), and the Verifier and scoring ran again. Candidate boxes: recall 85% to 83%, precision 99% to 100%, verified 98 to 95, box failures 2 to 2, median overlap with the element the box lands on 1.00 to 0.86 (the Comparator already copies the tree's boxes). Seer boxes: overlap with the nearest element 0.61 to 0.75, tighter, with recall and precision unchanged (85%, 99%). Noun-phrase prompts found objects for 3 of 10 nouns on one screen, and SAM returns boxes and masks, no text. Not tested: a Comparator shown SAM's boxes, which would need new walks.

### Best model per stage

| Stage | Best model | Effort | Runs | Why | Margin | Clears the bar to change the default |
|---|---|---|---|---|---|---|
| comparator | muse-spark-1.3-contributor | medium | n = 3 | muse-spark-1.3-contributor at medium (today's default): recall 85%, precision 99%, F1 0.91, $0.37 a page set; nothing beats it by more than the between-run spread of 3 labels. | +0 recall, +0 precision points against the default, F1 +0.00 | no |
| seer | muse-spark-1.3-contributor | medium | n = 3 | muse-spark-1.3-contributor at medium (today's default): recall 85%, precision 99%, F1 0.91, $0.37 a page set; nothing beats it by more than the between-run spread of 3 labels. | +0 recall, +0 precision points against the default, F1 +0.00 | no |
| judge | muse-spark-1.3-contributor | high | n = 2 | muse-spark-1.3-contributor at high: 94% agreement with the labels, 0% needing review, $0.0006 a finding; the highest agreement; cheaper than the default. | 94% agreement with the labels, 0% needing review, $0.0006 a finding against 94% agreement with the labels, 0% needing review, $0.0108 a finding | yes |
| fixer | muse-wonder-1.0 | medium | n = 2 | muse-wonder-1.0 at medium: 62% of gaps closed, 0.0 fixes rejected, $0.0252 a fix; the most gaps closed. | 62% of gaps closed, 0.0 fixes rejected, $0.0252 a fix against 53% of gaps closed, 0.0 fixes rejected, $0.0004 a fix | no |
| navigator | muse-spark-1.3-contributor | low | n = 2 | muse-spark-1.3-contributor at low (today's default): 4.0 of 4 screens, 0 of 2 runs ended by an API error, 11.0 turns, $0.004 of navigator calls; nothing reaches more screens without an API error, or finishes in fewer turns by more than the default's spread of 2. | the default is the best row | no |

### Comparator

| Model | Effort | n | Recall | Precision | F1 | Accuracy | FP on clean | Verified per run | Rejected share | Jaccard | Tokens | Cost | Cost with the default judge | Time | Stage latency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **muse-spark-1.3-contributor** | medium | n = 3 | 85% | 99% | 0.91 | 90% | 0.0 | 33 | 10% | 0.83 | 207,774 | $0.369 | $0.369 | 495 s | 33 s |
| muse-spark-1.1 | medium | n = 1 | 76% | 97% | 0.85 | 84% | 0.0 | 30 | 8% | — | 185,684 | price unknown | price unknown | 322 s | 11 s |
| muse-spark-1.2-contributor | medium | n = 2 | 79% | 98% | 0.88 | 86% | 0.0 | 30 | 7% | 0.91 | 189,374 | $0.035 | $0.345 | 318 s | 12 s |
| muse-spark-1.3 | medium | n = 2 | 79% | 97% | 0.87 | 86% | 0.0 | 31 | 13% | 0.94 | 190,255 | $0.116 | $0.431 | 397 s | 27 s |
| muse-spark-1.3-contributor | high | n = 2 | 88% | 98% | 0.93 | 92% | 0.0 | 34 | 5% | 0.89 | 214,050 | $0.039 | $0.384 | 451 s | 31 s |
| muse-spark-1.3-contributor | low | n = 2 | 79% | 94% | 0.86 | 86% | 0.0 | 32 | 18% | 0.78 | 193,136 | $0.035 | $0.360 | 386 s | 19 s |
| muse-wonder-1.0 | medium | n = 2 | 88% | 97% | 0.92 | 92% | 0.0 | 34 | 6% | 0.92 | 203,797 | $0.307 | $0.656 | 370 s | 20 s |

### Seer

| Model | Effort | n | Recall | Precision | F1 | Accuracy | FP on clean | Verified per run | Rejected share | Jaccard | Tokens | Cost | Cost with the default judge | Time | Stage latency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **muse-spark-1.3-contributor** | medium | n = 3 | 85% | 99% | 0.91 | 90% | 0.0 | 33 | 10% | 0.83 | 207,774 | $0.369 | $0.369 | 495 s | 26 s |
| muse-spark-1.1 | medium | n = 2 | 78% | 98% | 0.87 | 85% | 0.0 | 30 | 12% | 0.88 | 193,395 | price unknown | price unknown | 396 s | 7 s |
| muse-spark-1.2-contributor | medium | n = 2 | 83% | 98% | 0.90 | 89% | 0.0 | 32 | 9% | 0.94 | 194,856 | $0.036 | $0.360 | 355 s | 8 s |
| muse-spark-1.3 | medium | n = 2 | 82% | 95% | 0.88 | 88% | 0.0 | 32 | 13% | 0.86 | 199,470 | $0.091 | $0.421 | 415 s | 23 s |
| muse-spark-1.3-contributor | high | n = 2 | 83% | 97% | 0.89 | 89% | 0.0 | 32 | 4% | 0.81 | 207,765 | $0.038 | $0.367 | 472 s | 28 s |
| muse-spark-1.3-contributor | low | n = 2 | 84% | 98% | 0.91 | 90% | 0.0 | 32 | 17% | 0.86 | 211,404 | $0.038 | $0.368 | 458 s | 15 s |
| muse-wonder-1.0 | medium | n = 2 | 78% | 97% | 0.86 | 85% | 0.0 | 30 | 31% | 0.91 | 201,501 | $0.238 | $0.547 | 468 s | 17 s |

### Judge

| Model | Effort | Runs | n findings | Agreement with labels | Severity same as the default judge | Needs review (fail closed) | Cost per finding | Latency |
|---|---|---|---|---|---|---|---|---|
| muse-spark-1.3 | medium | n = 1 | 31 | 94% | 100% | 0% | $0.0108 | 20 s |
| muse-spark-1.1 | medium | n = 1 | 31 | 90% | 81% | 0% | price unknown | 5 s |
| muse-spark-1.2 | medium | n = 1 | 31 | 90% | 81% | 0% | $0.0081 | 9 s |
| muse-spark-1.2-contributor | medium | n = 1 | 31 | 87% | 68% | 0% | $0.0007 | 10 s |
| muse-spark-1.3 | high | n = 1 | 31 | 94% | 87% | 0% | $0.0137 | 23 s |
| muse-spark-1.3 | low | n = 1 | 31 | 94% | 84% | 0% | $0.0071 | 9 s |
| **muse-spark-1.3-contributor** | high | n = 2 | 31 | 94% | 84% | 0% | $0.0006 | 22 s |
| muse-spark-1.3-contributor | medium | n = 2 | 31 | 90% | 81% | 0% | $0.0006 | 18 s |
| muse-wonder-1.0 | medium | n = 1 | 31 | 94% | 77% | 0% | $0.0266 | 10 s |

### Fixer

| Model | Effort | n barriers | Runs | Gaps closed | Comparator still flags | Fixes rejected | Cost per fix | Fixer latency | Time |
|---|---|---|---|---|---|---|---|---|---|
| muse-spark-1.3 | medium | 29 | n = 2 | 57% | 7% | 0.0 | $0.0069 | 10 s | 223 s |
| muse-spark-1.3-contributor | medium | 29 | n = 2 | 53% | 14% | 0.0 | $0.0004 | 10 s | 229 s |
| **muse-wonder-1.0** | medium | 29 | n = 2 | 62% | 2% | 0.0 | $0.0252 | 9 s | 210 s |

### Navigator

| Model | Effort | n | Screens of 4 | Runs ended by an API error | Turns | Refusals | Safety checks | Navigator cost | Run cost | Navigator latency | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| muse-spark-1.1 | low | n = 1 | 4.0 | 0 | 9.0 | 0.0 | 4.0 | price unknown | price unknown | 11 s | 694 s |
| muse-spark-1.2-contributor | low | n = 1 | 4.0 | 0 | 11.0 | 0.0 | 6.0 | $0.003 | $0.040 | 13 s | 576 s |
| muse-spark-1.3-contributor | high | n = 2 | 4.0 | 1 | 10.0 | 0.0 | 6.0 | $0.003 | $0.042 | 19 s | 674 s |
| **muse-spark-1.3-contributor** | low | n = 2 | 4.0 | 0 | 11.0 | 0.0 | 7.0 | $0.004 | $0.042 | 12 s | 617 s |
| muse-spark-1.3-contributor | medium | n = 2 | 4.0 | 2 | — | 0.0 | 6.5 | $0.004 | $0.041 | 11 s | 608 s |

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
