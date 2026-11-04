# 21 — Submission form answers (paste-ready; every number equals `eval/results/latest.md` or docs/28)

Rewritten 4 Nov 2026, evening (prompt 28 D4). One section per live form field, in form order (27 Oct scrape plus the three questions seen live on 4 Nov). Word counts noted; the live form's character limits were not published, so each essay is kept under 1,800 characters. Rows marked **pending** take the re-recorded bundle's numbers before pasting.

## 1–2. Team Name · Team Members
**Parity** · Taahir Suleman (solo).

## 3. Track
Indie Developer Track.

## 4. Problem statement
**Push the Frontier.** Decided 4 Nov (doc 18 §10). The one-sentence justification, used verbatim in the Project Description and spoken once in the video: *Push the Frontier, in software: Parity gives an agent a new sense, to see a page as a sighted shopper and hear it as a screen reader, and to prove where they differ.* Why not Build for Your World: that statement asks for a problem known firsthand, which would need a tester or a practitioner I do not have, and nothing may be implied; the frontier statement names software and "give a machine a new capability", which is what the evidence measures.

## 5. X post link
Filled after the post goes up (text in §14).

## 6. Project Description (≈ 740 words)

Most websites are built and tested by people who can see them. A blind person uses the same sites through a screen reader, software that reads aloud what the page's code says each element is. When the code and the picture disagree, the sighted customer and the blind customer are on two different sites. On a checkout I built to show this, a green button reads "Pay R1,249" on screen while the screen reader announces "Submit": the shopper cannot tell what they are about to be charged. Four stars under a product are drawn as pixels and announce nothing. A red border is the only sign of an error.

This is common and it is expensive. 95.9% of the top million home pages have detectable WCAG failures (WebAIM, 2026). In 2025, 5,114 digital-accessibility lawsuits were filed in the US, 70% of them against e-commerce sites (UsableNet, a vendor report); one small retailer paid about $46,000 in legal fees and $13,000 to fix its sites (WSJ, 2024). Since 28 June 2025 the EU Accessibility Act covers e-commerce, with fines up to €100,000 in Germany. The people on the other side: 43 million blind and 295 million with moderate to severe vision impairment (Lancet, 2020), and US working-age adults with disabilities hold $674bn in disposable income (AIR, 2026).

The current state of tooling is the rule engine. axe-core, the most widely used, scans a page's code against a list of rules (a missing alt attribute, a form field with no label). It is fast and free, and it cannot see the page. In a UK government test the best of ten automated tools caught 41% of the barriers on a page (GDS, 2017). On my demo checkout, with its 38 seeded barriers, axe-core 4.14 reports 0 violations, because every one of them is a disagreement between what is seen and what is announced, which no rule can detect.

Parity is for the team shipping that checkout. Its job: before a release, prove that a blind shopper can complete the purchase, and fix what stops them. Push the Frontier, in software: Parity gives an agent a new sense, to see a page as a sighted shopper and hear it as a screen reader, and to prove where they differ. One agent, Muse Spark with Meta's computer-use tool, walks the flow from product to order confirmation. On each screen, Spark's perception grounding marks what a sighted user sees as boxes, and a second Spark call reads the screenshot against Chrome's accessibility tree and quotes where they disagree. Then code decides: six checks gate every claim (seen on screen, a real element, an exact quote, different words, not already in axe, not a duplicate), a judge rates severity against WCAG, a fixer proposes the smallest HTML change, a sandboxed re-audit checks that the screen reader now says what the screen shows, and a human approves each fix and downloads one patch. That is the useful result: a proven finding, a fix a re-audit confirms, and a patch a person approved. Real VoiceOver audio, transcribed by Muse Voice Transcribe, is the evidence beside the tree.

I measured it rather than described it. On the demo store, 38 seeded faults axe-core passes and 20 clean controls, three runs: recall 85%, precision 99%, no false positives, $0.37 and 8 m 15 s per four-page flow, and $0.04 with today's judge (n = 1). Ablations show where the capability lives: the screenshot alone finds 17%, the tree alone 75%, both with the code gate 85%. On W3C's demonstration pages, which I did not write, Parity's candidates covered 7 of 14 in-scope barriers against axe-core's 5. A per-stage sweep of seven Meta models chose each role on evidence and changed one default. I ran Parity's own workbench through VoiceOver and fixed what it found. Live, it audits any public page read-only; a bot wall stops it in seconds at no cost.

The impact, per flow: an audit for cents and minutes where a manual review costs $100–$250 a page (vendor pricing, 2026), catching the barrier before release instead of after the lawsuit, the fine or the lost sale, for a customer who otherwise clicks away (69% do; Click-Away Pound, 2019). Findings are evidence, never a conformance claim; nothing is applied without a person. Autonomy: the agent walks, audits and proposes on its own; every fix waits for approval.

## 7. Public GitHub repository
https://github.com/TaahirSuleman/parity

## 8. Demo video
Filled after the upload (title and description in §13).

## 9. Describe your use of Meta products to build the submitted project (≈ 770 words)

Parity is an agentic workflow built entirely on Meta's models. The job is a multi-step one: walk a site's purchase flow, audit each screen two ways, prove each gap, judge it, fix it, re-check the fix, and hand a person the decision. I built it as five specialist model roles, one of them an agent with tools, coordinated by code rather than by a coordinator model. Code is the orchestrator because the stages are dependent (each screen is the result of the action before it), because the parallelism that pays is safe only in code (judges and fixers four at a time), and because orchestration in code is what makes the system verifiable: the budget rule, the allow-listed executor and the six Verifier checks are unit-tested, and there is no nondeterministic coordinator to fail. Every model call at runtime is a Meta model through the Model API; the workbench shows each stage's model badge and the trace lists every call's model, request ID, tokens, latency and cost.

Muse Spark 1.3, by role, each choice measured:

- Navigator, the agent: `muse-spark-1.3-contributor` at low effort with Meta's `computer` tool, `truncation` set per request, `previous_response_id` chaining. It sees a screenshot and returns one batch of actions; an allow-listed executor runs only the kinds it knows, inside the allowed origin, and answers every `pending_safety_checks` item in code. Two function tools are gated: `audit_view` captures the screen once, and `finish` is refused until the screen has been audited. In the recorded walk it reaches the payment form and the order confirmation in ten turns, with 31 findings verified over four screens. The sweep showed every Spark tier reaching 4 of 4 screens; Muse Wonder refuses the `computer` tool (HTTP 400), so Spark navigates.
- Seer: Spark's perception grounding, returning what a sighted user sees as 0–1000 boxes. This is the capability that lets code verify each claim against a real element; without it the same pipeline measured 82% with 0.7 false positives per page set (1 Nov), against 85% with it (4 Nov).
- Comparator: one multimodal call that reads the screenshot and Chrome's accessibility tree together and quotes the tree exactly, so code can check the quote. The contributor tier at medium effort measured 85% recall and 99% precision over three runs; the standard tier 79–82%; Wonder 88% at 1.8× the cost, inside the run-to-run spread, so the default stayed.
- Judge: a separate Spark call that rates severity and cites WCAG and fails closed to "needs review". The sweep compared nine model and effort combinations on the same 31 findings: the contributor tier at high effort matched the standard tier's 94% agreement with my labels at $0.0006 a finding against $0.0108, so it became the default on 4 November and a confirmation run measured $0.04 per four-page set (n = 1). Wonder matched 94% at 2.5× the standard judge's cost.
- Fixer and re-audit: Spark proposes the smallest HTML change; code loads the patched page in a sandbox and checks the name rule; Spark compares again. The default closes 53% of gaps on its first proposal; Wonder 62% at about 60× the cost, so it stays.

Muse Voice Transcribe 1.0 adds a second modality: a real VoiceOver recording of the checkout page, transcribed and aligned word by word to what VoiceOver logged (0.92 word accuracy on the committed replay), so a finding carries the segment a screen-reader user actually heard. SAM 3.1 was tested and left out on evidence: replaying its box prompts over three recorded runs tightened the Seer's boxes (overlap 0.61 to 0.75) without moving recall or precision, and it returns no text.

The evaluation harness closes the loop: 38 seeded faults and 20 clean controls, labels kept outside the agent's code path, ablations per capability, an axe-core baseline, W3C's annotated pages as an external set, and the per-stage sweep that ranked seven Meta models per role, with every result quoted from one file.

In the build, I used Muse Code for QA and for a thorough review across the stack: nine prompts, the session read the pipeline, the guard, the eval and the judge-facing documents against Meta's own verifiable-agent guidance, and reported 80 findings (3 tagged disqualification, 21 high), each marked verified-in-code or inferred. It kept the work pointed at using Meta's models well: it caught a re-audit that closed on empty text, a form-submit gap in the public-site guard, a cost-cap overshoot and the licence and scope wording, and three fixes landed test-first the same afternoon. Muse Code reviewed; I kept the design and the final say.

## 10. Why are Meta's models important to your solution? (≈ 600 words)

Parity exists because of three things Meta's models do that a rule engine cannot: look at a rendered page and say what a sighted person sees, where; drive a browser through a real purchase as an agent; and turn a screen reader's speech into text. Remove any of them and the product collapses into axe-core, which reports zero violations on the very checkout Parity is built to catch.

The architecture is agentic end to end. One agent, Muse Spark with the `computer` tool, carries the walk: it perceives a screenshot, decides the next actions, and acts through an allow-listed executor that answers every safety check in code. Inside its `audit_view` tool, four more Spark roles do the specialist work: the Seer grounds what a sighted user sees as boxes; the Comparator reads the screenshot and the accessibility tree in one multimodal call and quotes the disagreement; the Judge rates it; the Fixer proposes the change and the re-audit's comparison confirms it. Code orchestrates the roles deterministically, so the only nondeterminism is where the models earn it (perception and judgement), the fan-out that pays runs four at a time, and latency stays inside minutes for a four-page flow. The result is a multi-role agentic workflow with the strengths of each model placed in the role that needs them.

The dependence is measured, not asserted. With the screenshot alone recall is 17%; with the accessibility tree alone 75%; the full stack with Spark's perception grounding reaches 85% at 99% precision with no false positives on clean controls (38 seeded faults, 20 controls, three runs). Grounding is what lets code verify each claim element by element: a box on a 0–1000 grid maps to one accessibility-tree node, and the Verifier's six checks run on that mapping. Without grounding the same pipeline measures 82% with 0.7 false positives per page set. Computer use is what makes Parity an agent rather than a page checker: in the recorded walk it adds a product to the cart, fills the payment form and reaches the order confirmation, auditing every screen on the way; the sweep showed every Spark tier reaching all four screens and Wonder unable to use the tool. Voice Transcribe turns real VoiceOver audio into evidence beside the tree at 0.96 word accuracy on the committed replay, a second modality that corroborates the first.

The ecosystem is what made this buildable in a week by one person. One key and one API give me computer use, perception grounding, multimodal comparison, structured JSON output, per-request effort control, server-side conversation state for the agent's turns, and speech transcription, and the per-stage sweep could rank seven Meta models and three effort levels on the same labels because they share one interface. The contributor tier makes it affordable to run on every release: the same model at about a twelfth of the price, which the sweep showed loses nothing on the judge (94% agreement either way) and brought a full four-page audit to $0.04. The cost of the alternative is visible in the same tables: Wonder at 2.5× for the same agreement, SAM 3.1 returning tighter boxes but no text.

Meta's models perceive; my code decides. Six checks, a sandboxed re-audit and a human approval sit between a model's claim and a patch, and that is the only reason a finding from a probabilistic model can be handed to a developer as evidence. The models supply the sense; the harness supplies the proof; together they make a result a person can act on.

## 11. Feedback on Meta products (≈ 230 words)

Specific and from my traces. (1) Reliability: the same four-page set took 495 s one night and 281 s another with the same calls; a chained computer-use turn returned an intermittent 400 ("`computer_call_output` input items are not supported" when only one function tool was offered; "invalid parameters" with a reduced set), fixed on my side by sending the full tool set on the last turn; 500s appeared in bursts with request IDs logged. (2) Computer-use clicks landed 5–7 px below the store's buttons on 4 Nov where the same buttons were hit first time on 1 Nov; code now snaps a click that lands on nothing to the control within 20 px. (3) `truncation` has to be set per request and the account must allow it; the docs could say so on the computer-use page. (4) Voice Transcribe's file endpoint needs multipart with `audioEncoding: "WAV"` or returns "Malformed request"; it handled VoiceOver's synthetic speech at 0.92–0.96 word accuracy across takes. (5) Wonder 1.0 refuses the `computer` tool (HTTP 400 "Unsupported tool type"), so it cannot navigate. (6) The contributor tier is the reason a full audit costs $0.04: the same model at about a twelfth of the price; please keep it. (7) Spark 1.1 has no published price, so a sweep cannot rank it on cost. (8) A spend limit per key, and a token-count endpoint I could use before a judge fan-out, would let us cap cost before launch rather than after.

## 12. Feedback on partner technologies (Fireworks, Modal, Baseten)
Not used. Every model call runs on the Meta Model API; no open-weight model was needed, and I did not request partner credits.

## 13. YouTube title and description (public)

**Title:** Parity: what a blind shopper hears on your checkout, proven and fixed

**Description:**
Parity walks a site's key flows as a sighted shopper and as a screen-reader user, proves where they differ, proposes a fix, re-checks it, and leaves the decision to a person. Built this week on Meta's Muse Spark and Voice Transcribe for the Meta Global AI Developer Hackathon; Playwright, axe-core and the libraries in HACKATHON_SCOPE are pre-existing open source.

Try it, no login: https://parity-u7lcbbxuia-uc.a.run.app
Code: https://github.com/TaahirSuleman/parity

Chapters (**pending** the final cut): 0:00 the Pay button · 0:12 the problem · 0:35 the walk · 1:30 the fix and the approval · 1:50 the numbers · 2:05 live on a page we did not write · 2:25 impact

Sources for the figures on screen: WebAIM Million 2026 (webaim.org/projects/million); UK GDS, "What we found when we tested tools on the world's least accessible webpage" (2017); UsableNet 2025 year-end report (a vendor report); Directive (EU) 2019/882 art. 2 and 31; BFSG §37 (Germany); Wall Street Journal, July 2024, as quoted by UsableNet; Click-Away Pound 2019; Accessible.org pricing (vendor, 2026); Deque, 2013 (vendor); GBD 2019 Blindness and Vision Impairment Collaborators, Lancet Global Health 2021; AIR and Disability:IN, April 2026. My own numbers: eval/results/latest.md in the repository (38 seeded faults, 20 clean controls, 3 runs).

Findings are evidence, not a conformance claim. Captions and a subtitle file are included.

## 14. X post (Most Viral)

axe-core says 0 violations. A blind shopper still can't tell what the Pay button charges.

Parity walks the checkout as a sighted shopper and as a screen reader, proves each gap against the page's own accessibility tree, proposes the fix and re-checks it. Built this week on Meta's Muse Spark. 85% recall, 99% precision on faults axe passes.

Try it, no login: https://parity-u7lcbbxuia-uc.a.run.app
[video]

## 15. The Muse Code questions (seen live on 4 Nov)
- **How likely are you to recommend Muse Code (0–5):** 4. It read the whole stack and found real defects my tests had missed, and it kept the work pointed at Meta's models.
- **Obstacle / production blocker:** reliability (the latency swing between nights, the intermittent 400 on a chained last turn, bursts of 500s), not price or quality.
- **When your team chooses an AI model or coding tool, what matters most:** that its output can be checked: structured output code can validate, grounding code can verify, and a price that lets the check run on every release.
- **Compared with other models for the same work:** used others, no clear comparison.

## 16. Consent
Ticking the box grants Meta and Cerebral Valley the right to use, publish and promote the submitted materials.
