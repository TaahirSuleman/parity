# VoiceOver pass over the workbench (before P6)

The browser stress pass (docs/23 §7.4) was run by a script that records live regions and focus; it cannot judge what a screen-reader
user actually hears. This pass does. Do it on the hosted demo, in Safari, with VoiceOver; repeat anything odd in Chrome.
Record what VoiceOver said (VO+Shift+C copies the last phrase to the clipboard), what you expected, and a verdict:
**blocks** (a judge could not do the step), **confusing** (doable, but wrong or noisy), **cosmetic**, or **ok**.

## 0. Setup

| # | Step | Done |
|---|---|---|
| 0.1 | macOS: System Settings → Keyboard → **Keyboard navigation** on. Safari → Settings → Advanced → **Press Tab to highlight each item on a webpage** on. | |
| 0.2 | VoiceOver Utility: leave Verbosity at default; Web → Navigation: "DOM order" (not "Group items"), so what you hear matches the document; Quick Nav off (VO+Left+Right toggles it). | |
| 0.3 | Keys: VO = Control+Option. VO+Right/Left reads the next/previous item; VO+Space activates; VO+U opens the rotor (Left/Right changes list: Headings, Landmarks, Form Controls, Links, Tables); VO+Shift+Down interacts with a group/table/list, VO+Shift+Up leaves it; VO+A reads from here on; Control stops speech; VO+Shift+C copies the last phrase. | |
| 0.4 | Open a new Safari window at `https://parity-u7lcbbxuia-uc.a.run.app/` and turn VoiceOver on (Cmd+F5). Keep a notes file open for the verbatim phrases. | |

## 1. Idle page (nothing run yet)

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 1.1 | Note what VoiceOver says as the page loads, before you press anything. | Window title "Parity"; a short orientation. **Question A:** is a long status paragraph read on load? Copy it verbatim and say whether it helps or is noise. | | |
| 1.2 | Press Tab repeatedly from the top. | Order: "Flow" pop-up button (Checkout page) → "Replay" button, pressed → "Live (rate-limited)" button, not pressed → "Run the audit" button → "Eval" button → the trace toggle at the bottom ("0 model calls"). No unlabelled stop. | | |
| 1.3 | VO+U → Headings. | Parity (1); Sighted (2); Findings (2); Screen reader (2). Names make sense; no empty heading. | | |
| 1.4 | VO+U → Landmarks. | banner; main. | | |
| 1.5 | VO+U → Form Controls. | Flow; Replay; Live (rate-limited); Run the audit; Eval; trace toggle. Nothing named just "button". | | |
| 1.6 | VO+Right through the main area. | The idle framing is readable: what Parity does, "Run the audit to see the page" in the Sighted panel, the empty feed text, the screen-reader panel's empty text. | | |

## 2. Start a Replay by keyboard (Checkout page)

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 2.1 | Tab to "Run the audit", press VO+Space (or Space). | Immediately: "Audit started: capturing the page and comparing what is seen with what is announced." The button now reads "Auditing…" and is dimmed. **Question B:** is the start announced once or twice (two near-identical "capturing" phrases)? | | |
| 2.2 | Do nothing for ~15 s and listen. | **Question C:** list every phrase spoken during the run. The script heard `image, "image"` and `button, "Submit"` (the screen-reader quote of the selected finding). Say whether hearing the quote when the selection moves is useful or noise. | | |
| 2.3 | At the end. | "Audit finished: 7 verified findings." Where is the VoiceOver cursor and the keyboard focus now (VO+F3 describes the item)? The run is announced, "Run the audit" is enabled again. | | |
| 2.4 | Press Cmd+L and read the address. | It ends in `?run=<id>`: the run is reloadable and shareable. | | |

## 3. The findings feed

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 3.1 | VO+Right into the feed; VO+Shift+Down to interact with the list. | "Findings" heading; "7 verified · 3 rejected by the Verifier"; "Without the Verifier" toggle; a list of 7 items. | | |
| 3.2 | Read the first card (the hero, "Pay R1,249") item by item. | "Sighted user sees"; heading level 3 "Pay R1,249", a pressed button (it is selected); severity ("serious" or similar); "Screen reader gets" then `button, "Submit"`; list "Verifier checks" with each check "…: passed"; "Check details for Pay R1,249" disclosure; WCAG line ("WCAG 2.5.3 Label in Name"); the judge badge names a Muse model; "Re-audit" with before → after and "gap closed"; "Proposed fix" with the fixer badge and the explanation; "Diff for Pay R1,249" disclosure. | | |
| 3.3 | Open "Check details" and "Diff" (VO+Space on each). | The details list reads check by check. The diff is a region "Unified diff for Pay R1,249" you can Tab into and read line by line (added lines, removed lines). | | |
| 3.4 | Move to a card that is not selected and press its heading button. | It becomes pressed; the Sighted panel's box and the Screen-reader panel follow it (check with VO+Right; note anything announced automatically). | | |
| 3.5 | Find the three rejected rows. | Each says what the model proposed and which check failed, as evidence the Verifier is real; they do not read like findings. | | |
| 3.6 | Press "Without the Verifier". | The feed shows what would have been reported without the gate; the switch state is announced; press again to go back. | | |

## 4. Decide a finding (the human gate)

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 4.1 | On the selected card, Tab to the reason field. | "Reason, edit text" with the suggested text ("Re-audit: gap closed, the screen reader now says …") read out; the text is selected so typing replaces it. | | |
| 4.2 | Tab to "Approve" and press it. | The Approve/Reject controls disappear; focus stays on this card's heading button (not the top of the page); **Question D:** is "Approved · <reason>" announced? The header now says "1 approved · 6 to review" and a "Download fix.patch" link exists. | | |
| 4.3 | Select another card, type a reason, press "Reject". | "Rejected · <reason>" announced; counts update. | | |
| 4.4 | Reload (Cmd+R). | Same run, both decisions still shown; nothing re-announces the whole run as new beyond the page load. | | |
| 4.5 | Tab to "Download fix.patch". | A link named "Download fix.patch"; activating it downloads `parity-<id>.patch`. | | |

## 5. Header counters

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 5.1 | VO+Right across the header after the run. | "axe-core 0 violations"; "Parity 7 verified · 3 rejected by the Verifier"; "$0.0901 · recorded 4 m 42 s"; "replay"; "awaiting review"; "1 approved · 6 to review". Each makes sense without its tooltip (tooltips are not read). | | |

## 6. Sighted panel

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 6.1 | VO+Right onto the screenshot. | Image, "The audited page as a sighted user sees it". | | |
| 6.2 | Tab through the boxes drawn on it. | Buttons "Finding: sighted user sees <text>", pressed for the selected one, in reading order (top to bottom, left to right). Pressing one selects that card. | | |
| 6.3 | Note anything else announced in the panel. | The grounding badge names a Muse model; the faint outlines (percepts) are not announced. | | |

## 7. Screen-reader panel

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 7.1 | VO+Right through the right-hand panel with the hero selected. | The quote `button, "Submit"` and a short explanation of what a screen-reader user gets for the sighted text "Pay R1,249". | | |
| 7.2 | Select a different card and listen without moving. | **Question C again:** does the panel speak on its own when the selection changes, and should it? | | |

## 8. Trace drawer

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 8.1 | Tab to the trace toggle ("24 model calls · 109,371 tokens · $0.0901") and open it. | A table; VO+Shift+Down to interact, VO+arrows move by cell and read the column header (stage, model, request id, tokens, latency, cost, cache hit). | | |

## 9. Eval tab and a public sample

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 9.1 | Press "Eval". | The view changes; headings for the results table, the ablations, the judge comparison, the architecture card, the glossary and the public samples. | | |
| 9.2 | Interact with the results table. | Column headers read with each cell; the "full" row is the headline; numbers read as percentages/dollars sensibly. | | |
| 9.3 | Press "Replay Site A". | The view switches back to the workbench, focus lands in the main area (not on the page body), "Audit started…" is announced, the header says "Site A · read-only sample" (never "ShopRight"). | | |
| 9.4 | After it finishes, read a Site A card. | Verified findings for a third-party page; no fix or re-audit is promised; the screenshot message, where one is withheld, says why. | | |

## 10. Purchase flow (the agent walk)

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 10.1 | Open the "Flow" pop-up (VO+Space), choose "Purchase flow (agent)", press "Run the audit". | The start announcement; during the ~20 s the timeline rows appear in the Sighted panel ("computer: …", "audit this screen: …"); note whether they are spoken automatically (they should not flood you). | | |
| 10.2 | After it finishes. | "Screens of the flow" group with four pressed-state buttons ("1 · product" …); 35 findings, each "Diff for …" and "Check details for …" named by its own text; the outcome line ("finished: …") is readable. | | |

## 11. Notices and errors

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 11.1 | Open `https://parity-u7lcbbxuia-uc.a.run.app/?run=nope`. | On load, an alert: "The linked run is not on this server any more: Replay copies are kept for a limited time. Start a new Replay." | | |
| 11.2 | Optional, costs about $0.10: press "Live (rate-limited)", then "Run the audit", and within a few seconds press "Run the audit" again in a second tab. | The second tab gets an alert: "Live is busy or rate-limited: a Live run is already in progress… or watch a Replay…". The first tab's run finishes in 4–5 minutes with 7 verified findings; the fixer and re-audit badges name Muse models. | | |
| 11.3 | Zoom Safari to 200% (Cmd+Plus until 200%) with a run on screen. | The page scrolls; nothing is clipped; VoiceOver order is unchanged. Reset with Cmd+0. | | |

## 12. Final sweep with a finished run on screen

| # | Step | Expected | Heard | Verdict |
|---|---|---|---|---|
| 12.1 | VO+U → Form Controls. | No control named only "button", "link" or "edit text"; nothing you cannot tell apart. | | |
| 12.2 | VO+U → Headings. | Levels nest: 1 (Parity) → 2 (panels) → 3 (findings). | | |
| 12.3 | VO+U → Links. | "Download fix.patch" (after an approval) and the Eval tab's links; nothing bare. | | |
| 12.4 | VO+A from the top of the main area. | The read-all order tells the story a sighted judge sees: the page, the findings, the decisions. Note anything read out of place. | | |
| 12.5 | Repeat 2.1–2.3 and 4.2 in Chrome with VoiceOver. | Same announcements; note any difference. | | |

## 13. What to send back

- The table above with Heard and Verdict filled in (verbatim phrases where the verdict is not ok).
- Your answers to Questions A–D: (A) the load-time status: keep, shorten, or drop; (B) one or two start announcements; (C) the quote spoken on selection: keep or make it silent; (D) whether "Approved/Rejected" is announced after a decision.
- Anything a judge using VoiceOver would stumble on that is not listed here.
