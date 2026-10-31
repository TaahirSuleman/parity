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
| Checkout (single page) | 6 (6 rejected) | 6 | 4 | $0.083 | 221 s |
| Purchase (agent, 4 screens) | 12 (5 rejected) | 11 | 5 | $0.140 | 574 s |

- The hero fix is the one you would write: `<button id="f5" class="btn">Pay R1,249</button>` (or the image
  with `alt="Pay R1,249"`); the re-audit reads the new name "Pay R1,249" from the tree and closes the gap.
- `gap_closed` is strict by design (name must equal or contain the sighted text): a trash icon renamed
  "Delete" is a good fix but stays "open", so the human sees the before/after and decides.
- Cost of the fix stage is small (fixer ≈ $0.0004 per finding at contributor rates). Time: with fixer calls
  4-wide and the second-signal comparator at effort low, the fix stage adds ~2.5 min to a live purchase run
  (575 s total, was 772 s). Replay stays the default for judges.
- After the review fix pass the exported patch is rebuilt from the served source and `git apply --check`
  passes on every file of both recorded runs (an id-less element is located by its css_path).
