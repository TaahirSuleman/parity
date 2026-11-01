# 17 — Live validation on Meta's API (29 Oct 2026)

**Total spend:** ≈ $0.21: 37 Spark calls and 145 s of audio, including one aborted run. Every response is cached in `meta-validation/cache` so nothing is billed twice. Raw results are in `Desktop/Meta_Hackathon/validation/` (JSON files).

## Callback

| Test | Setup | Result | Verdict |
|---|---|---|---|
| **V1 diarization** | 6 synthetic 2-voice calls (Kokoro TTS), degraded to 8 kHz telephony; Voice Transcribe in `DIARIZATION` mode | Role accuracy (by talk time) 99.6–100%. Key line ("new phone", "skip it this time") attributed to the right speaker 5/5. Spurious 3rd speaker label on 3/6 calls. ~5 s per call | **Pass** (on easy synthetic voices) |
| **V3 does speaker attribution matter?** | Spark 1.3 judges each call 3 ways: diarized, turns without speakers, flat transcript | Verdict 6/6 and verification 6/6 in **all three** | **Fail as a differentiator.** In two-party calls the roles are obvious from the content, so diarization does not change the outcome |
| **V2 screen check** | 6 help-desk console screenshots (skipped / callback / push / KBA-only / push denied / callback failed); Spark 1.3 + 0–1000 grounding | Verification state 6/6 correct. Boxes land on the right rows but are loose (median IoU ≈ 0.35). ~2k tokens and ~3 s each | **Pass** (state); boxes good enough for highlighting |
| V4 Keycloak revoke | Not run: this environment blocks running downloaded server binaries | Deterministic REST, low risk | Deferred |

**Implication:** Callback's "why Meta" leaned on diarization deciding the case, and that did not hold. What remains (ASR plus screen reading) is real but replaceable with other vendors, and the inputs are still synthetic.

## Accessibility Gap Auditor

| Test | Setup | Result | Verdict |
|---|---|---|---|
| **Rule-engine blind spot** | Checkout page with 6 seeded faults (meaningless alt text, price drawn on a canvas, error shown only as a red border, "Terms" vs "Click here", "Pay R1,249" vs "Submit", trash icon named "Close") and 2 correct controls | axe-core 4.10.2: **0 violations** | Confirms the gap is real |
| **A2 sighted vs screen-reader divergence** | Screenshot + Chrome accessibility tree → Spark 1.3 with grounding | **6/6 faults found**, 0/2 controls flagged, 1 extra flag caused by my own tree filtering; 4.5k tokens, 14 s | **Pass** |
| **A1 computer use** | Spark 1.3 `computer` tool drives the page: set expiry, then pay | Completed in one batched turn (11.7 s, 1.7k tokens). The next call hit a one-off server 500 | **Pass** (the build needs retries) |
| A3 Voice on real screen-reader audio | Not run here (no screen reader in the container) | Test on a Mac with VoiceOver | Pending: the user's own test |

## Procedure Proof
Not testable under the "no filming" constraint. Meta's API has no video generation model, and generated footage would undercut a product that claims to verify reality.

## Run-to-run variance (post-P2 hardening, 31 Oct)

Three live purchase-flow runs through the agent, each with a fresh cache (no replayed responses),
via `scripts/variance_runs.py`; full data in `docs/variance.json`.

| Run | Status | Verified | Rejected | Cost | Duration |
|---|---|---|---|---|---|
| 1 | **failed** — Meta API 500 burst, 3 retries in ~6 s exhausted | 4 (partial) | 0 | $0.038 | 84 s |
| 2 | done | 13 | 6 | $0.143 | 365 s |
| 3 | done | 12 | 3 | $0.133 | 368 s |

- **Keyed on the verifier-grounded element, the two completed runs found the same 12 barriers**
  (stability 92%); the one flaky extra was a weak confirm-page text finding seen once. Wording of
  `sighted_text` paraphrases freely between runs (expected: it is model prose), which is why the
  element, not the text, is the identity.
- The failure was the API, not the agent: three 500s in a row (request_id c13f5568…), the same
  outage class seen while recording the hero bundle. **Hardened in response:** the client now
  retries 5 times over ~33 s (was 3 over ~4 s) and treats 429 as retryable.
- Judged against the 12-finding hero bundle, run-to-run recall on seeded barriers is stable;
  per-barrier recall/precision vs labels is Phase 4 (Task 19).

## Fixer and re-audit, live (Phase 3, 31 Oct)

| Flow | Verified | Fixes proposed | Gaps closed by re-audit | Cost | Time |
|---|---|---|---|---|---|
| Checkout (single page) | 6 (1 rejected) | 6 | 4 | $0.073 | 210 s |
| Purchase (agent, 4 screens) | 11 (2 rejected) | 11 | 7 | $0.134 | 488 s |

- The hero fix is the one you would write: `<button id="f5" class="btn">Pay R1,249</button>` (or the image
  with `alt="Pay R1,249"`); the re-audit reads the new name "Pay R1,249" from the tree and closes the gap.
- `gap_closed` is strict by design (name must equal or contain the sighted text): a trash icon renamed
  "Delete" is a good fix but stays "open", so the human sees the before/after and decides.
- Cost of the fix stage is small (fixer ≈ $0.0004 per finding at contributor rates). Time: with fixer calls
  4-wide and the second-signal comparator at effort low, the fix stage adds ~2.5 min to a live purchase run
  (575 s total, was 772 s). Replay stays the default for judges.
- After the review fix pass the exported patch is rebuilt from the served source and `git apply --check`
  passes on every file of both recorded runs (an id-less element is located by its css_path).
- Re-recorded again after the pre-P4 QA pass (docs/23): rejections are now only real refusals (the comparator's
  own repeats are no longer counted), the `Order SR-10428` text-fragment false positive is gone, and the agent's
  routine `computer_action_requires_confirmation` checks are acknowledged on our store and shown on the timeline.

## Eval on the seeded store (Phase 4, 1 Nov)

Measured with `eval/harness.py` at commit `1e6caad` (labels sha256 `43b432f8abea`): 4 configurations × 3 runs × 4 pages, effort `medium`, judge `muse-spark-1.3`. The file is `eval/results/final.json`; `latest.md` is its rendering and the only number set the README, the Eval tab and the video quote. A finding is scored under its element's id or the nearest id above it; the labels never reach the agent (`tests/test_store_v2.py` checks `parity/` does not import `eval/`).

| System | Recall | Precision | Findings | FP on clean | Cost / page set | Time |
|---|---|---|---|---|---|---|
| Parity (full) | 84% | 97% | 33 / 38 | 0.0 | $0.37 | 281 s |
| screenshot only | 17% | 95% | 7 / 38 | 0.0 | $0.08 | 391 s |
| tree only | 75% | 98% | 29 / 38 | 0.3 | $0.32 | 442 s |
| no grounding | 82% | 95% | 33 / 38 | 0.7 | $0.36 | 428 s |
| axe-core 4.14 | 0% | — | 0 violations | — | $0 | — |

Per page (full): product 96% / 100% (16 of 16 found), cart 85% / 100% (8 of 9), checkout 74% / 95% (7 of 9), confirm 58% / 81% (3 of 4). Missed in every run — cart: `promo-input` (placeholder-as-label); checkout: `cvv` (placeholder-as-label), `step-payment` (state-visual-only); confirm: `status-packed` (state-visual-only).

**Reading.** The accessibility tree carries most of the recall (tree only: 75%); the screenshot alone finds little (17%) because without the tree the model cannot quote what is announced, and the Verifier rejects what it cannot quote. Grounding (the Seer's boxes) adds two points of recall and removes 0.7 false positives on clean controls per page set. Precision stays at or above 95% in every configuration because the Verifier gates all four; the ablations say nothing about the Verifier itself — that number is the workbench's "Without the Verifier" toggle. axe-core's 0% is by construction: the 38 faults were chosen to pass it (0 violations on all four pages), so it is a statement about this class of gap, not about axe in general. Three runs is a small sample; run-to-run spread on recall was 2–3 labels per page set.

**Effort sweep** (full, one run each): low 84% / 97% at $0.35 and 231 s; medium 84% / 97% at $0.37 and 281 s; high 74% / 100% at $0.31 and 339 s. Medium stays the default for seer and comparator: low is within noise of it on one run, and the 3-run table above was measured at medium.

**Judge** (the same 33 verified findings): `muse-spark-1.3` agrees with the labels on 94%, `muse-wonder-1.0` on 94%, at $0.011 vs $0.026 per finding; Spark stays the judge (D6). Neither sent a finding to needs_review.

**Standard tier** (`muse-spark-1.3` for every stage, one run): 82% / 100% at $0.47 — private mode costs about 25% more for the same quality.

**Real-world sample** (read-only, anonymised; spec §17): Site A, 2 screens, 6 verified and 0 rejected — five CSS-drawn star ratings that announce nothing (judged barriers, moderate) and a cover image named by its title alone (judged not a barrier); axe-core reports none of them. Site B: a bot challenge in front of the first page ended the run as `blocked by site` in 1.2 s with nothing sent to a model.

**An earlier pass** (31 Oct, pre-review code, 37 labels, 3 runs) gave full 74% / 91% and no grounding 78% / 93%; it is not quoted. The difference comes from the review fixes: CSS-drawn elements captured as silent nodes and generated text kept, labels on wrappers scored under the nearest id, and the comparator's retry after a non-JSON answer no longer served from the cache.
