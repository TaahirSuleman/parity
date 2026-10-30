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
