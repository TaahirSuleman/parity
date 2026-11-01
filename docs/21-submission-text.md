# 21 — Submission text (drafts for the form; keep every number equal to `eval/results/latest.md`)

Form fields (constitution Art. V): 4 Project Description · 7 Use of Meta products · 8 Why Meta's models matter. Video: `docs/18 §9`.

## 4. Project Description — "Describe your project and what problem it solves"

Parity is an agent that walks a site's key flows the way a shopper would and compares, screen by screen, what a sighted user sees with what a screen-reader user gets. Rule engines such as axe-core check markup; they cannot see that a button drawn as "Pay R1,249" is announced as "Submit", that a star rating is only pixels, or that an error is only a red border. Those are the gaps blind users hit at checkout, and they pass every automated checker.

Parity screenshots each screen, reads Chrome's accessibility tree, asks Muse Spark to say what a sighted user sees and where that diverges from what is announced, and then lets code decide: a candidate becomes a finding only if its box lands on a real element, its quote equals the accessibility tree exactly, the visible text differs, axe does not already report it, and it is not a duplicate. A separate judge call rates severity and cites WCAG; a fixer proposes a minimal change; a re-audit loads the patched page in a sandbox and checks the gap closed; a human approves or rejects each fix and downloads one patch.

On our demo store, 38 seeded faults that axe passes: full Parity recall 84%, precision 97%, zero false positives on 20 clean controls, 37 cents per page set. Findings are evidence, never a conformance claim.

## 7. "Describe your use of Meta products to build the submitted project"

Every model call at runtime is a Meta model through the Model API. Muse Spark 1.3 (contributor tier) drives five roles: computer use for the Navigator, which walks the store from product to order confirmation through an allow-listed executor; perception grounding for the Seer, which returns what a sighted user sees as 0–1000 boxes drawn on the screenshot; multimodal comparison for the Comparator, which reads screenshot and accessibility tree together and quotes the tree exactly; a separate Judge call, on standard `muse-spark-1.3`, that rates severity and WCAG and fails closed to human review; and the Fixer and re-audit comparison. Muse Wonder 1.0 was measured as an alternative judge on the same findings (same agreement, 2.3× the cost per finding), so Spark stays. Every stage shows its model badge in the workbench; the trace lists each call's model, request ID, tokens, latency and cost; responses are cached on disk.

## 8. "Why are Meta's models important to your solution?"

Remove them and Parity collapses into axe-core. The accessibility tree says what is announced; only a model that can look at the rendered page can say what a sighted user *sees* there, and only one that returns boxes lets code verify the claim element by element. The ablations show the dependency: with the screenshot alone recall is 17%; with the tree alone 75%; the full stack with Spark's grounding reaches 84% at 97% precision, with no false positives on clean controls. Computer use is what makes it an agent rather than a page checker: it reaches the screens a shopper reaches (a filled-in payment form, the confirmation), auditing each one, while code screens every action. Meta's models perceive; our code decides.

## One-line scope statement (video 0:00 and README)
"Parity was built this week on Meta's Muse Spark; Playwright and axe-core are pre-existing open source."

## X post (Most Viral)
axe-core says 0 violations. A blind shopper still can't tell what the Pay button charges. Parity (built this week on Meta's Muse Spark) walks the checkout as a sighted user and as a screen reader, proves each gap against the accessibility tree, proposes the fix and re-checks it. 84% recall / 97% precision on faults axe passes. [video] [URL]
