# 22 — Workbench design brief

**Status:** v1, Sat 31 Oct 2026. Implements spec §9 and §9.1. Reviewed once by the builder from screenshots (Task 10b step 4); changes land in Task 11 or Task 24.

## 1. Direction: an instrument, not a dashboard
The workbench exists for one moment: a developer watches the agent walk their checkout and sees, side by side, what a sighted shopper sees and what a blind shopper hears. Everything on screen serves that comparison.

- **The page screenshot dominates.** It is the largest element at every width. Grounding boxes are drawn on it, thin and labelled, never filled.
- **The screen-reader output is typeset like a transcript.** Large monospace, quoted exactly as the accessibility tree has it: `button, "Submit"`. When nothing is announced, the line reads `— not announced —` in the muted colour.
- **Colour carries meaning only.** Green = verified, red = rejected or failed, amber = needs review. Everything else is neutral. No brand gradient, no decorative tints.
- **Badges read like instrument labels.** Small caps, tracked, monospace: `MUSE SPARK 1.3 · GROUNDING`, `CHROME AX TREE · DETERMINISTIC`, `CODE · VERIFIER`. Every model-backed element has one; deterministic steps say so.
- **Quiet motion.** New cards fade in over 150 ms; nothing bounces or pulses. The running state shows a thin progress line under the header, not a spinner.
- **The workbench is itself accessible.** Landmarks, a logical focus order, visible focus rings, AA contrast in both themes, and a polite live region that announces each new finding. It must pass axe with zero violations (asserted in Task 24).

## 2. Tokens (`web/src/theme.css`, CSS variables; light and dark)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | #f5f6f8 | #0f1115 | page |
| `--surface` | #ffffff | #171a21 | panels, cards |
| `--surface-2` | #eef0f3 | #1f232c | drawer, code blocks |
| `--line` | #d9dde3 | #2a2f3a | hairlines |
| `--ink` | #15181e | #e8eaf0 | text |
| `--muted` | #5f6673 | #9aa3b2 | secondary text, labels |
| `--ok` | #137a3d | #3ccf74 | verified |
| `--bad` | #c62828 | #ff6b6b | rejected, failed |
| `--warn` | #a36a00 | #f2b134 | needs review |
| `--focus` | #2f6fed | #7aa7ff | focus ring, selected box |
| `--mono` | ui-monospace, "SF Mono", Menlo, "JetBrains Mono", monospace | | screen-reader quotes, badges, trace |
| `--sans` | -apple-system, "Segoe UI", Inter, system-ui, sans-serif | | everything else |

Spacing scale 4 / 8 / 12 / 16 / 24 / 32 px. Radius 6 px for cards, 4 px for badges, 2 px for boxes on the screenshot. Type: 13 px labels, 14 px body, 16 px card titles, 22 px screen-reader quote, 28 px price line.

## 3. Layout (≥ 1280 px)
```
┌ header: ShopRight · Checkout   [REPLAY] [Run the audit]     axe-core · 0 violations │ Parity · 6 verified · 0 rejected │ $0.02 · 48 s ┐
├───────────────────────────────┬──────────────────────────────┬─────────────────────────────┤
│ SIGHTED                       │ FINDINGS                     │ SCREEN READER               │
│ screenshot 1280×720, scaled   │ card, card, card…            │ button, "Submit"            │
│ grounding boxes; selected box │ red rows for rejected        │ Price: — not announced —    │
│ in --focus; badge bottom-left │ each card: evidence, 5 ticks,│ badge: CHROME AX TREE       │
│                               │ WCAG, severity, fix, approve │ (VoiceOver clip in P6)      │
├───────────────────────────────┴──────────────────────────────┴─────────────────────────────┤
│ TRACE ▸  12 calls · 41k tokens · $0.021   stage | model | request id | tokens | ms | $ | cache │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```
Column widths 5 / 4 / 3. Below 1280 px the columns stack: sighted, screen reader, findings. The trace drawer is collapsed by default and opens to 240 px.

## 4. The three states
1. **Idle.** Header with the mode pill and **Run the audit**. Sighted panel shows the store's first screen (static). Findings column shows one line: "No findings yet. Run the audit to walk the checkout." Screen reader panel shows the quote for the focused element on hover/selection of a box, otherwise "Select a finding".
2. **Running.** Progress hairline under the header. Sighted panel updates per step with the latest screenshot; the badge reads `MUSE SPARK 1.3 · COMPUTER USE` while navigating and `· GROUNDING` while the Seer runs. Cards appear as `verifier.result` events arrive; rejected candidates appear as red rows with the failed check named. Counters tick in the header.
3. **Hero selected.** The "Pay R1,249" card is selected: its box is drawn in `--focus` on the screenshot; the screen reader panel shows `button, "Submit"` at 22 px and `Price: — not announced —`; the card shows five green ticks (located, exact quote, diverges, not axe, unique), `WCAG 2.5.3 Label in Name · serious` with the `MUSE SPARK 1.3 · JUDGE` badge, and the Approve / Reject controls (enabled once a fix and re-audit exist, P3).

## 5. Components (props only, no fetching)
`Header`, `SightedPanel`, `ScreenReaderPanel`, `FindingsFeed`, `FindingCard`, `RejectedRow`, `TraceDrawer`, `MetaBadge`. Types mirror spec §5 and §8 in `web/src/state/types.ts`; the reducer (Task 11) turns SSE events into `RunState`.

## 6. Must not
No gradients, glassmorphism, drop shadows deeper than 1 px, emoji, stock icons, confetti, or decorative illustrations. No "AI" sparkles. No colour that does not mean something. No text in all caps except badges. No claim of "compliance" anywhere.
