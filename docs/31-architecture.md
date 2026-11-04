# 31 — Architecture and Meta Model API integration

For a Technical Depth reader. Labels match the code at commit `2039a9f`, the commit the final hosted revision `parity-00023-qkh` serves (its code is identical to `0ccc2fa`). Where an older document differs, `parity/config.py` and `parity/meta/client.py` win. Measured numbers come only from [eval/results/latest.md](../eval/results/latest.md), [eval/results/model-sweep.md](../eval/results/model-sweep.md) and the [hand-off](30-final-dev-handoff.md), each with its n and date. Findings are evidence, not a conformance claim, and a human approves every fix.

In the diagrams, `META` is a Meta model call, `CODE` is deterministic code written this week, `OSS` is pre-existing open source, and `HUMAN` is a person's decision. The prefix carries the meaning; the colour only repeats it. In section 4, the unprefixed purple nodes are measured results.

## 1. System and integrations map

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 320}}}%%
flowchart TB
    V(["HUMAN · Visitor or judge<br/>no login"])
    G["CODE · GitHub Actions, ci.yml<br/>pytest and vitest, then deploy"]

    subgraph Host["Cloud Run: one Docker image"]
        W["CODE · Workbench<br/>React SPA in parity/static"]
        S["CODE · FastAPI server<br/>rate limits, URL policy, decisions"]
        R["CODE · Replay<br/>copies a committed bundle<br/>no model calls"]
        L["CODE · Live runner<br/>capture, Verifier, re-audit name rule"]
        I[("CODE · SQLite index<br/>a cache, rebuilt at boot")]
        P["OSS · Playwright, Chromium"]
        A["OSS · axe-core 4.14"]
    end

    B[("CODE · Run bundle store: the truth<br/>local disk or Cloud Storage<br/>run.json, steps, findings, trace.jsonl,<br/>events.jsonl, fix.patch")]

    subgraph Meta["Meta Model API: https://api.meta.ai/v1"]
        N["META · Navigator<br/>POST /responses<br/>muse-spark-1.3-contributor, low<br/>computer tool, previous_response_id,<br/>truncation:auto"]
        Se["META · Seer<br/>POST /responses<br/>muse-spark-1.3-contributor, medium<br/>grounding, 0–1000 boxes"]
        C["META · Comparator<br/>POST /responses<br/>muse-spark-1.3-contributor, medium<br/>screenshot plus accessibility tree"]
        J["META · Judge<br/>POST /responses<br/>muse-spark-1.3-contributor, high<br/>fallback: muse-spark-1.3 standard"]
        F["META · Fixer<br/>POST /responses<br/>muse-spark-1.3-contributor, medium"]
        Re["META · Re-audit comparison<br/>POST /responses<br/>the Comparator's model, low"]
        Vo["META · Voice Transcribe<br/>POST /asr/transcribe<br/>muse-voice-transcribe-1.0<br/>real VoiceOver audio, WAV<br/>recorded store pages only"]
        M["CODE · Pre-flight, not a model call<br/>GET /models"]
        N ~~~ F
        Se ~~~ Re
        C ~~~ Vo
        J ~~~ M
    end

    V -->|HTTPS| W
    W -->|"runs, decisions"| S
    S -.->|"SSE: live events"| W
    S --> R
    S --> L
    S -->|"GET /models"| Meta
    R -->|"writes the copy"| B
    L -->|"writes whole objects"| B
    B -->|derives| I
    L --> P
    P --> A
    L -->|"every Meta call, traced"| Meta
    G -->|"WIF, only when app files changed"| Host

    classDef meta fill:#dbeafe,stroke:#1d4ed8,color:#0b1f4d
    classDef code fill:#f1f5f9,stroke:#334155,color:#0f172a
    classDef oss fill:#fef3c7,stroke:#b45309,color:#451a03,stroke-dasharray:4 3
    classDef human fill:#dcfce7,stroke:#15803d,color:#052e16
    class N,Se,C,J,F,Re,Vo meta
    class W,S,R,L,I,B,G,M code
    class P,A oss
    class V human
```

- Replay is the default for judges: it copies a committed bundle from `fixtures/replay` under a new id and calls no model.
- Live runs the real pipeline: the store flows, the W3C demo pages, or one public page a visitor chooses. The last two are read-only and have no Fixer or Re-audit.
- `model_for(stage)` is the one place a stage learns its model ID. `PARITY_PRIVATE=true` moves every contributor-tier stage to standard `muse-spark-1.3`.
- The bundle is the truth and the index is a disposable cache. Every write goes to the bundle first.
- CI's `changes` step skips the build and deploy when a push touches only `docs/`, `.superpowers/`, `.github/` or `*.md`. Deploy authenticates by Workload Identity Federation, with no stored key.
- Trace check: bundles recorded before `0ccc2fa` (both heroes and the four W3C pages) show the standard-tier judge in their traces. The first run with the contributor judge in its trace is the fresh-clone Live checkout, `20261104-151555-37c262e1` (hand-off §3, §5).

## 2. One Live run, from URL entry to approval

```mermaid
sequenceDiagram
    autonumber
    actor U as HUMAN · Visitor or judge
    participant A as CODE · API and runner
    participant B as OSS · Chromium, axe-core
    participant M as META · Model API
    participant V as CODE · Verifier
    participant T as CODE · Bundle and trace

    U->>A: Run request (flow, or URL with consent)
    A->>A: check_url, resolve_public, deny list, robots.txt, caps
    alt refused
        A-->>U: One sentence that never echoes the URL
    end
    A->>B: Open the page<br/>(public run: request_guard re-checks every request)
    A->>A: wall_reason: CAPTCHA, bot challenge, login wall
    alt wall found
        A-->>U: blocked by site, nothing sent to a model
    end

    loop Turn budget: 16 on the store, 6 or 12 on a visitor URL
        A->>A: Visitor URL over_budget? Then done, "cost cap reached"
        A->>M: Navigator: POST /responses, computer + audit_view + finish,<br/>previous_response_id, truncation auto
        M-->>A: computer_call or function_call
        alt computer_call
            A->>A: Safety codes, snap_click, public-site guard_action
            Note over A,B: Public site: a click inside a form or on nothing<br/>identifiable is dropped with its reason.<br/>An irreversible step stops the run.
            A->>B: execute (allow-listed kinds only), then is_allowed_target
            B-->>A: Screenshot, sent as computer_call_output on the next turn
        else audit_view on a new screen
            A->>B: Capture
            B-->>A: Screenshot, accessibility tree with boxes, axe result, source
            A->>M: Seer: grounding, 0–1000 boxes
            M-->>A: Percepts
            A->>M: Comparator: screenshot + tree in page_data delimiters
            M-->>A: Candidates that quote the tree
            A->>V: located, sr_quote_exact, diverges, not_axe, unique, seen
            alt any check fails
                V-->>T: Rejected row, with the failing check
                V-->>A: Feedback for one more Comparator try (at most 2)
            else all six pass
                V-->>T: Verified finding, every check recorded
                par Judge fan-out, four at a time
                    A->>M: Judge: contributor tier, high effort
                    M-->>A: Judgement. On an error: retry on muse-spark-1.3
                end
                Note over A,B: No usable verdict fails closed to needs_review.
            end
        else finish
            A->>A: Refused until this screen is audited.<br/>After 3 refusals: finish_forced
        end
    end

    alt store flow: code runs the fix batch
        loop Each finding with is_barrier true
            A->>M: Fixer: minimal HTML change (four at a time)
            A->>B: Sandbox re-audit, serial:<br/>patched source at the real URL, /api blocked
            A->>A: Name rule: gap_closed needs<br/>non-empty sighted text in the new name
            A->>M: Re-audit comparison, low effort: comparator_still_flags
        end
        A-->>U: Status awaiting_review
        U->>A: Approve, with a reason
        A->>T: Save the Decision, rebuild fix.patch
        A-->>U: Download fix.patch
    else public page: never patched
        A-->>U: Status done, findings as evidence only
    end

    Note over A,T: Every attempt is one ModelCall: model, request ID, tokens, latency, cost, cache state.<br/>It goes to trace.jsonl, the index and a model.call event.
```

- Code runs the audit in a fixed order. The model chooses only where to navigate and when to audit.
- Order inside a batch, as in `run_agent`: safety codes, `snap_click` (a near miss within 20 px moves to its control), `guard_action`, `execute`, origin check, `wall_reason` again.
- Measured on the recorded purchase bundle (one run, 4 Nov): nine turns, 30 verified, 4 rejected, 27 fixes, 27 re-audits, 14 closed, $0.373, 1,343 s, of which the serial re-audit took 669 s (hand-off §4).
- Caps: 3 Live runs per IP per hour, hosted and local. Hosted visitor-URL runs also have $0.50 a run, $5 a day and 3 per origin a day (hand-off §5, §7).
- Known limits (hand-off §6): the per-run cost cap is not checked inside the judge fan-out; robots.txt is read at start and landing only; a login wall needs a password field plus a login title or path.

## 3. Trust boundaries

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 340}}}%%
flowchart TB
    G0["CODE · Entry gates, before any model<br/>URL policy, robots.txt, request_guard, wall_reason"]
    A1["META · Navigator proposes an action batch"]
    G1["CODE · Action gates<br/>safety codes, snap_click, guard_action,<br/>allow-listed execute, is_allowed_target"]
    A2["META · Navigator proposes finish"]
    G2["CODE · finish gate<br/>screen audited, or finish_forced after 3 refusals"]
    A3["META · Seer percepts, Comparator candidates"]
    G3["CODE · Verifier: six checks<br/>located, sr_quote_exact, diverges,<br/>not_axe, unique, seen"]
    A4["META · Judge proposes severity, WCAG, is_barrier"]
    G4["CODE · Judge gate<br/>fallback, then needs_review;<br/>only is_barrier true gets a fix"]
    A5["META · Fixer proposes an HTML snippet"]
    G5["CODE · Fix gates<br/>snippet shape, diff computed in code,<br/>sandbox re-audit, gap_closed"]
    H{{"HUMAN · Approve or reject, with a reason"}}
    Out(["CODE · fix.patch"])

    G0 --> A1
    A1 --> G1
    G0 --> A2
    A2 --> G2
    G0 --> A3
    A3 --> G3
    G3 -->|"verified only"| A4
    A4 --> G4
    G4 --> A5
    A5 --> G5
    G5 --> H
    H -->|"approved only"| Out

    classDef meta fill:#dbeafe,stroke:#1d4ed8,color:#0b1f4d
    classDef code fill:#f1f5f9,stroke:#334155,color:#0f172a
    classDef human fill:#dcfce7,stroke:#15803d,color:#052e16
    class A1,A2,A3,A4,A5 meta
    class G0,G1,G2,G3,G4,G5,Out code
    class H human
```

- A finding cannot persist without passing the Verifier. A failed candidate is kept as a visible rejected row, not dropped.
- Page text reaches the models inside `page_data` delimiters as evidence. If a model obeys a page anyway, the action gates still refuse the irreversible step (test fixture `tests/fixtures/pages/injection.html`).
- The Judge's model is decided by config, not by the model: `muse-spark-1.3-contributor`, then `muse-spark-1.3` on an error.
- Stated limits (hand-off §6): `seen` stands down when the sighted pass did not run; judge output is not validated for shape (severity and WCAG refs).
- Also stated: the snippet gate checks shape, not meaning; fixes are shown before their re-audit runs, and a failed re-audit leaves a fix approvable. The human is the last gate, not a formality.

## 4. The eval feedback loop

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 420}}}%%
flowchart TB
    L1[("Seeded labels: 38 faults, 20 clean controls<br/>4 store pages, outside the agent's code path")]
    L2[("W3C BAD labels: 14 of 35 barriers in scope<br/>4 before and 4 after pages")]
    H["CODE · eval/harness.py<br/>recall, precision, cost, time"]
    W3["W3C result (n = 2 per page, 4 Nov)<br/>in-scope recall 14%, beyond axe 22%, precision 40%<br/>axe-core: 36% in scope"]
    Ab["Ablations: recall / precision<br/>screenshot only 17 / 95<br/>tree only 75 / 98<br/>no grounding 82 / 95<br/>full 85 / 99<br/>axe-core 4.14: 0%, by construction"]
    Sw["Per-stage sweep, 4 Nov, commit 7f5376e<br/>one stage at a time, the rest at defaults"]
    Pr["What seven models accepted<br/>five Spark models: JSON, grounding, computer use<br/>muse-wonder-1.0: JSON, grounding, no computer use (HTTP 400)<br/>sam-3.1: none of the three"]
    Sam["SAM 3.1 box prompts on 3 recorded runs<br/>candidate boxes: recall 85 to 83, precision 99 to 100<br/>Seer boxes: both unchanged. No stage given"]
    Bar{{"The bar for the Judge: no loss in<br/>agreement or needs-review, not more expensive.<br/>Other stages: must beat the between-run spread"}}
    Ch["Judge default changed, commit 0ccc2fa<br/>muse-spark-1.3 medium to contributor tier, high<br/>94% agreement, 0% needs review, n = 2, 31 findings<br/>$0.0108 to $0.0006 a finding"]
    Ke["Four defaults kept<br/>Seer, Comparator, Fixer, Navigator"]
    Co["Confirmation run, n = 1, 4 Nov<br/>$0.37 (3 runs, standard judge) to $0.04 per 4-page set<br/>recall 89%, precision 100%, within the spread<br/>headline stays 85 / 99"]

    L1 --> H
    L2 --> H
    H --> W3
    H --> Ab
    Ab --> Sw
    Sw --> Pr
    Pr --> Sam
    Sw --> Bar
    Bar -->|"Judge clears it"| Ch
    Bar -->|"none clears it"| Ke
    Ch --> Co
    Co -.->|"judge-contributor-n1.json<br/>beside latest.json"| H

    classDef code fill:#f1f5f9,stroke:#334155,color:#0f172a
    classDef result fill:#f5f3ff,stroke:#6d28d9,color:#1e1b4b
    class L1,L2,H,Bar,Ke,Ch code
    class W3,Ab,Sw,Pr,Sam,Co result
```

- Provenance: the full row (3 runs, standard-tier judge) and the W3C block (2 runs per page) are 4 Nov at commit `3221905`. The three ablation rows keep their 1 Nov measurement at commit `1e6caad`.
- The two cost figures are not one experiment: $0.369 is the mean of 3 runs with the standard judge, and $0.043 is n = 1 with the contributor judge. The 85 / 99 headline was not re-measured on the new judge.
- Judge caveat: severity matches the old judge on 84% of findings, and the standard tier's own low and high variants match it on 84% and 87%. At medium, the same contributor model agrees with the labels on only 90%, at the same $0.0006.
- Comparator and Seer: nothing beats the default by more than the spread of 3 labels. Contributor tier at high (88 / 98, n = 2) and Wonder (88 / 97, n = 2) are inside it.
- Fixer: Wonder closes 62% of gaps at $0.0252 a fix against the default's 53% at $0.0004 (n = 2, 29 barriers), so the default stays. Read gaps closed beside "Comparator still flags": 2% against 14%.
- Navigator: every row reached 4 of 4 screens, and the default's 11 turns are inside its spread of 2. These walks ran with twelve turns, before the click correction, and were not re-measured.

## 5. Every Meta capability

| Stage | Model and tier | Effort | API feature used | Code that checks its output | Evidence |
|---|---|---|---|---|---|
| Navigator (traced as stage `auditor`) | `muse-spark-1.3-contributor` | low | `POST /responses`; `computer` tool with function tools `audit_view` and `finish`; `previous_response_id`; `truncation: "auto"`; `parallel_tool_calls: false` | Safety codes, `snap_click`, `guard_action`, allow-listed `execute`, `is_allowed_target`, `wall_reason`, the `finish` gate | Sweep (n = 2, 4 Nov): 4 of 4 screens, 11 turns, $0.004. Tests: `test_guard` |
| Seer | `muse-spark-1.3-contributor` | medium | `POST /responses`; screenshot input; perception grounding, 0–1000 boxes | Verifier `seen` (a candidate needs a percept behind it) and `located` | Ablation: no grounding 82 / 95, 0.7 FP on clean; full 85 / 99, 0.0 FP (`latest.md`) |
| Comparator | `muse-spark-1.3-contributor` | medium | `POST /responses`; screenshot and accessibility tree together; at most 2 tries with Verifier feedback | All six Verifier checks | Sweep (n = 3, 4 Nov): 85 / 99, 10% rejected. Ablations: tree only 75 / 98, screenshot only 17 / 95 |
| Judge | `muse-spark-1.3-contributor`; fallback `muse-spark-1.3` (standard) | high | `POST /responses`; JSON answer; a separate call per verified finding, four at a time | Fails closed to `needs_review`; only `is_barrier` true reaches the Fixer | Sweep (n = 2, 31 findings): 94%, 0% needs review, $0.0006. Confirmation (n = 1, 34 findings): 94%, 32 of 34. Tests: `test_config` |
| Fixer | `muse-spark-1.3-contributor` | medium | `POST /responses`; returns a minimal HTML change | Snippet gate (shape), diff computed in code, then the Re-audit | Sweep (n = 2, 29 barriers): 53% of gaps closed, 14% still flagged, $0.0004 a fix |
| Re-audit comparison | The Comparator's model (`muse-spark-1.3-contributor`) | low | `POST /responses`, on the patched page in a sandbox | `gap_closed` name rule in `parity/pipeline/reaudit.py`; the model's answer is recorded as `comparator_still_flags` | Purchase bundle (one run, 4 Nov): 27 re-audits, 14 closed. Tests: `test_reaudit` |
| Voice Transcribe | `muse-voice-transcribe-1.0` | n/a | `POST /asr/transcribe`; multipart `request` and `audio` (WAV, 16 kHz mono 16-bit); `keywords` | Word alignment against the phrases VoiceOver logged; the accessibility tree stays the record the Verifier checks | Word accuracy 0.92 on the committed checkout replay, Voice on five findings (hand-off §5). Recorded store pages only |
| Pre-flight | Not a model call | n/a | `GET /models` | `python -m parity.meta.client --check` exits non-zero unless `muse-spark-1.3` is listed; `/api/health` reports `models_ok` | Hosted `models_ok` true on `parity-00023-qkh` (hand-off §1) |
| Measured, no stage: Wonder | `muse-wonder-1.0` | medium | `POST /responses`: JSON and grounding accepted; `computer` refused with HTTP 400 | Same gates as the stage under test | Judge 94%, $0.0266 a finding (n = 1). Fixer 62%, $0.0252 a fix (n = 2) |
| Measured, no stage: SAM | `sam-3.1` | n/a | Box prompts, replayed on 3 recorded runs; returns boxes and masks, no text | Verifier and scoring run again on its boxes | Candidate boxes: recall 85 to 83, precision 99 to 100. Not tested: a Comparator shown SAM's boxes |

What every call shares, in `parity/meta/client.py`:

- **Cache:** keyed by SHA-256 of the model and the canonical body. A hit costs $0 and is traced with `cache_hit`. Chained agent turns are never read from or written to the cache, since a cached turn would chain a live call to a stale server-side response. An incomplete answer is never cached.
- **Retry:** 5 attempts, sleeping 1, 3, 9 and 20 s, on 429, 5xx and transport errors. Any other 4xx raises at once. One `ModelCall` is traced per attempt.
- **Secrets:** the key travels only in the `Authorization` header and is scrubbed from error strings. `Settings` keeps it out of `repr`.
