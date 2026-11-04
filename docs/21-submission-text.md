# 21 — Submission form answers (paste-ready; every number equals `eval/results/latest.md` or docs/28)

Rewritten 4 Nov 2026, evening (prompt 28 D4). One section per live form field, in form order (27 Oct scrape plus the three questions seen live on 4 Nov). Word counts noted; the live form's character limits were not published, so each essay is kept under 1,800 characters. Rows marked **pending** take the re-recorded bundle's numbers before pasting.

## 1–2. Team Name · Team Members
**Parity** · Taahir Suleman (solo).

## 3. Track
Indie Developer Track.

## 4. Problem statement
**Push the Frontier.** Decided 4 Nov (doc 18 §10). The one-sentence justification, used verbatim in the Project Description and spoken once in the video: *Push the Frontier, in software: Parity gives an agent a new sense, to see a page as a sighted shopper and hear it as a screen reader, and to prove where they differ.* Why not Build for Your World: that statement asks for a problem known firsthand, which would need a tester or a practitioner we do not have, and nothing may be implied; the frontier statement names software and "give a machine a new capability", which is what the evidence measures.

## 5. X post link
Filled after the post goes up (text in §14).

## 6. Project Description (≈ 290 words)

Parity is for the team shipping an online checkout. Its job: prove, before a release, that a blind shopper can complete the purchase, and fix what stops them. Rule engines such as axe-core check markup; they cannot see that a button drawn as "Pay R1,249" is announced as "Submit", or that four stars a shopper chooses by are announced as nothing. On our demo checkout axe-core 4.14 reports 0 violations. 95.9% of the top million home pages have detectable WCAG failures (WebAIM, 2026), and 5,114 US digital-accessibility suits were filed in 2025, 70% against e-commerce (UsableNet).

Push the Frontier, in software: Parity gives an agent a new sense, to see a page as a sighted shopper and hear it as a screen reader, and to prove where they differ. One agent walks the flow with Muse Spark's computer use; on each screen, Spark's perception grounding marks what a sighted user sees as boxes, and a second Spark call reads the screenshot and Chrome's accessibility tree together and quotes where they disagree. Then code decides: six checks (seen on screen, a real element, an exact quote, different words, not already in axe, not a duplicate) gate every claim, a judge rates severity, a fixer proposes a minimal change, a sandboxed re-audit checks the gap closed, and a human approves each fix and downloads one patch. That is the useful result: a verified finding with its proof, a fix a re-audit confirms, and a patch a person approved. Real VoiceOver audio, transcribed by Muse Voice Transcribe, is the evidence on the checkout page.

Measured on our store, 38 seeded faults that axe passes, 3 runs: recall 85%, precision 99%, no false positives on 20 clean controls, $0.37 and 8 m 15 s per 4-page flow ($0.04 with today's judge, n = 1). Live, it audits any public page read-only. We ran Parity's own workbench through VoiceOver and fixed what it found. Findings are evidence, never a conformance claim; nothing is applied without a person. Autonomy: the agent walks and audits on its own; every fix waits for approval.

## 7. Public GitHub repository
https://github.com/TaahirSuleman/parity

## 8. Demo video
Filled after the upload (title and description in §13).

## 9. Describe your use of Meta products to build the submitted project (≈ 330 words)

At runtime every model call is a Meta model through the Model API; the workbench shows each stage's model badge and the trace lists every call's model, request ID, tokens, latency and cost (single-shot stages are cached on disk; chained agent turns are not).

Muse Spark 1.3 by role. Navigator: the contributor tier with the `computer` tool, `truncation` set per request, one batch of actions per turn executed by an allow-listed executor, every `pending_safety_checks` acknowledged by code, and `finish` refused until the screen is audited. Seer: perception grounding, what a sighted user sees as 0–1000 boxes, which is what lets code verify each claim against a real element. Comparator: the screenshot and the accessibility tree in one multimodal call, quoting the tree exactly so code can check the quote. Judge: the contributor tier at high effort, chosen by a per-stage sweep (94% agreement with our labels, the same as the standard tier, at $0.0006 a finding against $0.0108, n = 2); it fails closed to human review. Fixer and the re-audit's comparison: Spark again. Muse Voice Transcribe 1.0 transcribes a real VoiceOver recording of the checkout page, aligned word by word to what VoiceOver logged, 0.92 word accuracy on the committed replay (**pending**), so a finding carries the segment a screen-reader user heard.

The choice per role is measured, not assumed. The sweep ran seven Meta models (Spark 1.1, 1.2, 1.3, their contributor tiers, Wonder 1.0, SAM 3.1) one stage at a time on the same labels: Wonder refuses the `computer` tool (HTTP 400), so Spark navigates; Wonder matched the judge's 94% at 2.5× the cost (n = 1); SAM 3.1 box prompts replayed over three recorded runs tightened the Seer's boxes (overlap 0.61 → 0.75) without changing recall or precision, and return no text, so Spark's grounding stays. The ablations (screenshot alone 17%, tree alone 75%, no grounding 82% with 0.7 false positives) say which capability carries what.

In the build, Muse Code ran as a review-only session with one writable file: nine prompts, 80 findings (3 tagged disqualification, 21 high), each marked verified-in-code or inferred. It caught what our own tests had not: the licence and scope wording, a re-audit that closed on empty text, a form-submit gap in the public-site guard, a cost-cap overshoot. Three fixes landed test-first the same afternoon; the rest are stated as known limits. Muse Code reviewed; it did not build.

## 10. Why are Meta's models important to your solution? (≈ 200 words)

Remove them and Parity collapses into axe-core. The accessibility tree says what is announced; only a model that looks at the rendered page can say what a sighted shopper sees there, and Spark's perception grounding returns that as boxes code can check element by element. The ablations show the dependency: the screenshot alone gives 17% recall, the tree alone 75%, the full stack with grounding 85% at 99% precision with no false positives on clean controls (3 runs, 38 seeded faults). Computer use is what makes it an agent rather than a page checker: in the recorded walk it reaches the payment form and the order confirmation, auditing each screen, while code screens every action and answers every safety check. Voice Transcribe turns a screen reader's real speech into evidence beside the tree. The contributor tier makes a four-page audit cost cents, so a team can run it on every release. Meta's models perceive; our code decides: six checks, a sandboxed re-audit and a human approval sit between a model's claim and a patch.

## 11. Feedback on Meta products (≈ 230 words)

Specific and from the trace. (1) Reliability: the same four-page set took 495 s one night and 281 s another with the same calls; a chained computer-use turn returned an intermittent 400 ("`computer_call_output` input items are not supported" when only one function tool was offered; "invalid parameters" with a reduced set), fixed on our side by sending the full tool set on the last turn; 500s appeared in bursts with request IDs logged. (2) Computer-use clicks landed 5–7 px below the store's buttons on 4 Nov where the same buttons were hit first time on 1 Nov; code now snaps a click that lands on nothing to the control within 20 px. (3) `truncation` has to be set per request and the account must allow it; the docs could say so on the computer-use page. (4) Voice Transcribe's file endpoint needs multipart with `audioEncoding: "WAV"` or returns "Malformed request"; it handled VoiceOver's synthetic speech at 0.92–0.96 word accuracy. (5) Wonder 1.0 refuses the `computer` tool (HTTP 400 "Unsupported tool type"), so it cannot navigate. (6) The contributor tier is the reason a full audit costs $0.04: the same model at about a twelfth of the price; please keep it. (7) Spark 1.1 has no published price, so a sweep cannot rank it on cost. (8) A spend limit per key, and a token-count endpoint we could use before a judge fan-out, would let us cap cost before launch rather than after.

## 12. Feedback on partner technologies (Fireworks, Modal, Baseten)
Not used. Every model call runs on the Meta Model API; no open-weight model was needed, and we did not request partner credits.

## 13. YouTube title and description (public)

**Title:** Parity: what a blind shopper hears on your checkout, proven and fixed

**Description:**
Parity walks a site's key flows as a sighted shopper and as a screen-reader user, proves where they differ, proposes a fix, re-checks it, and leaves the decision to a person. Built this week on Meta's Muse Spark and Voice Transcribe for the Meta Global AI Developer Hackathon; Playwright, axe-core and the libraries in HACKATHON_SCOPE are pre-existing open source.

Try it, no login: https://parity-u7lcbbxuia-uc.a.run.app
Code: https://github.com/TaahirSuleman/parity

Chapters (**pending** the final cut): 0:00 the Pay button · 0:12 the problem · 0:35 the walk · 1:30 the fix and the approval · 1:50 the numbers · 2:05 live on a page we did not write · 2:25 impact

Sources for the figures on screen: WebAIM Million 2026 (webaim.org/projects/million); UK GDS, "What we found when we tested tools on the world's least accessible webpage" (2017); UsableNet 2025 year-end report (a vendor report); Directive (EU) 2019/882 art. 2 and 31; BFSG §37 (Germany); Wall Street Journal, July 2024, as quoted by UsableNet; Click-Away Pound 2019; Accessible.org pricing (vendor, 2026); Deque, 2013 (vendor); GBD 2019 Blindness and Vision Impairment Collaborators, Lancet Global Health 2021; AIR and Disability:IN, April 2026. Our own numbers: eval/results/latest.md in the repository (38 seeded faults, 20 clean controls, 3 runs).

Findings are evidence, not a conformance claim. Captions and a subtitle file are included.

## 14. X post (Most Viral)

axe-core says 0 violations. A blind shopper still can't tell what the Pay button charges.

Parity walks the checkout as a sighted shopper and as a screen reader, proves each gap against the page's own accessibility tree, proposes the fix and re-checks it. Built this week on Meta's Muse Spark. 85% recall, 99% precision on faults axe passes.

Try it, no login: https://parity-u7lcbbxuia-uc.a.run.app
[video]

## 15. The Muse Code questions (seen live on 4 Nov)
- **How likely are you to recommend Muse Code (0–5):** 4. It read the code and found real defects our tests missed, in a review-only session that never touched a file but its own report.
- **Obstacle / production blocker:** reliability (the latency swing between nights, the intermittent 400 on a chained last turn, bursts of 500s), not price or quality.
- **When your team chooses an AI model or coding tool, what matters most:** that its output can be checked: structured output code can validate, grounding code can verify, and a price that lets the check run on every release.
- **Compared with other models for the same work:** used others, no clear comparison.

## 16. Consent
Ticking the box grants Meta and Cerebral Valley the right to use, publish and promote the submitted materials.
