# Docs map: what is authoritative

**Authoritative (read when relevant; later items never override earlier ones):**
1. `hackathon/00-constitution.md`: rules, rubric, hard constraints, calendar, submission form (amendments up to v1.3). **The constitution wins any conflict about rules.**
2. `18-decision-and-development-plan.md`: Parity's scope, architecture, eval, day plan and video. **It wins any conflict about the product.**
3. `17-validation-results.md`: what is proven on the live Meta API.
4. `hackathon/01-event-pages-rules-and-submission-form.md`: verbatim rules, the submission form and judging stages.
5. `hackathon/03-meta-ai-tooling-reference.md`: the full Meta API, models, Muse Code and cookbook reference. For quick, verified API formats, use the `meta-model-api` skill.
6. `submission-checklist.md` + `learnings/04-winning-recipe.md` §4.4 and Part 7: video storyboard and cold-review checklist.
7. `14-build-playbook-verifiable-agents.md` + `learnings/12-workshop-learnings.md`: Meta's verifiable-agent patterns. Learn from them; never copy workshop code.

**Context (why decisions were made; consult, don't re-litigate):**
- `hackathon/02-kickoff-stream-transcript.md`: organisers' guidance.
- `learnings/06-artefact-standard.md`: honesty tags and quality bar.
- `learnings/15-gemini3-postmortem-resilix-vs-winners.md`: why demo-first, perceptual, workbench UI.
- `learnings/11`, `12a`, `13`: workshop transcripts and repo analysis.

**Archive (superseded options and research; historical only):** `archive/`.
- 05: problem research.
- 07: Callback, Claim Clock and First Notice packs.
- 08–10: evaluations and audit.
- 15a: raw notes on the Gemini 3 winners.
- 16, 16a: the re-ranking and its inputs.

**Organiser clarifications received after the docs above (30 Oct):**
- The video is judged under Demo 25% and Tooling 25%.
- Show the product, not slides.
- Open with one line on what was pre-existing vs built this week.
- Judges stop watching at 3:00.
- Every runtime model must be a Meta model.
- Judges must be able to try the demo without logging in, from the repo setup instructions plus the video.
- `truncation` is set per request.
- Report 500s at dev.meta.ai/support.
- For the API acceptable-use policy, ask up_exceptions@meta.com.

**Rule:** new decisions go into `docs/` (append to doc 18 or add `19-...`). Never leave a decision only in chat.
