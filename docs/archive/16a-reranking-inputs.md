# 16a — Appendix: inputs to the 29 Oct re-ranking

Contents: (1) whitespace and market check on new candidates + Callback re-check; (2) neutral briefs given to the independent panel; (3) the panel's scores; (4) bottom-up hour estimates. Note: the panel's remark that SAM 3.1 video tracking needs a GPU is wrong for our design. We use the hosted Model API (`sam-3.1`).

---
# New candidates: whitespace and market check (29 Oct 2026)

Scope: five candidates for the Meta Global AI Developer Hackathon (submission 4 Nov 2026). Method: WebSearch and WebFetch on 29 Oct 2026. **[V]** marks a vendor-sourced number. **[UNVERIFIED]** marks something taken from prior knowledge or a secondary source that I could not open.

---

## 1. Procedure Proof (zero-shot verification that a procedure was performed)

**(a) Who already does this job: crowded in manufacturing, thin for mobile technicians**
- **DeepHow "Live SOP Verification"**, running live at Foxconn on NVIDIA Cosmos (a VLM) plus the Metropolis VSS Blueprint. It verifies "every operator's step in real time" and claims 99% micro-action accuracy and +3% first-pass yield **[V]**. [BusinessWire, 2 Jun 2026](https://www.businesswire.com/news/home/20260602068205/en/)
- **Partners shown on NVIDIA VSS + Cosmos Reason 2 at Hannover Messe (Apr 2026)**:
  - Invisible AI "Vision Execution System" (customers include Ford, Toyota, GM and BMW).
  - Tulip "Factory Playback" (Terex: +3% yield, −10% rework **[V]**).
  - Fogsphere.
  - Pegatron used VSS for SOP analysis and claims −67% defects **[V]**.
  - Source: [Classmethod write-up](https://dev.classmethod.jp/en/articles/dgx-spark-vss-3-1-revisit/).
- **Invisible AI** moved to acquire nFlux, an assembly copilot (Jul 2025). It also runs a "Studio" experiment: upload shop-floor video and the AI sketches the standard work. [Invisible AI blog](https://landing-website-6b1.pages.dev/blog/the-future-of-ai-powered-manufacturing-invisible-ais-acquisition-of-nflux/)
- **Retrocausal** names 3M, Stellantis, Stryker and Boston Scientific as customers and reports "multiple millions" in ARR **[V]**. [TechIntelPro, 17 Jan 2026](https://techintelpro.com/news/ai/enterprise-ai/retrocausal-appoints-steve-rodda-as-ceo-for-enterprise-growth)
- **Funding in the space**:
  - Squint raised $40M at a $265M valuation. [Fortune, Aug 2025](https://www.fortune.com/2025/08/12/exclusive-squint-raises-40-million-at-265-million-valuation-to-modernize-manufacturing-for-companies-like-pepsi-and-michelin)
  - Cerrion raised an $18M Series A. [SiliconANGLE, 25 Nov 2025](https://siliconangle.com/?p=722778)
  - Zapdos Labs raised a $500K pre-seed. It reads site manuals "zero-shot" but targets PPE and safety on CCTV. [BriefGlance, 1 May 2026](https://briefglance.com/articles/ai-that-reads-the-manual-zapdos-labs-targets-factory-safety)
- **Field and mobile work**:
  - TechSee does photo-based job verification for telecom technicians. [TechSee](https://techsee.com/resources/brochures/job-verification-field-services/)
  - Strivr "Frontline Intelligence" describes smart-glasses "execution verification" as a positioning piece. It says this needs customer-specific models. [Strivr, Aug 2026](https://www.strivr.com/blog/what-ai-needs-to-see-understand-and-verify-frontline-work)
- **Data-centre remote hands**: I found no product that verifies the work, only runbooks and AI guidance tools.
- **The technology is not solved.** IKEA-Bench (Aalto, Apr 2026) scored VLMs on assembly step recognition. The best open model reached 59.4% against a 25% chance baseline, and video discrimination is the main bottleneck. [arXiv 2604.00913](https://arxiv.org/html/2604.00913v1)
- **Not checked**: Drishti's current status (last known: a $25M Series B), Augmentir, Pathr and Powerarena.

**(b) Cost of the problem**
- **Uptime 2025 report**:
  - Human error plays a part in two-thirds to four-fifths of outages.
  - Failure to follow procedures appears in 58% of human-error outages, up 10 percentage points year on year.
  - Faulty procedures appear in 45%.
  - Source: [The Register, 7 May 2025](https://www.theregister.com/2025/05/07/human_error_a_factor_in)
- **Uptime 2026 report**:
  - Failure to follow procedures is the leading human-error driver.
  - 57% said their last major outage cost more than $100k, and 20% said more than $1M.
  - Source: [BusinessWire, 13 May 2026](https://www.businesswire.com/news/home/20260513289344/en/Uptime-Announces-Annual-Outage-Analysis-Report-2026)
- **Boeing door plug (Alaska 1282)**:
  - The NTSB found four bolts missing and cited "failure to follow proper manufacturing procedures". [AVweb, 10 Jul 2025](https://avweb.com/aviation-news/ntsb-cites-boeing-faa-shortcomings-in-alaska-door-plug-final-report/)
  - The FAA proposed $3.14M in fines over "hundreds of quality system violations". [FAA, 12 Sep 2025](https://www.faa.gov/newsroom/faa-proposes-31-million-fines-against-boeing)
- **Cost of poor quality**:
  - ASQ's rule of thumb is 15–20% of sales. This is a heuristic, not survey data.
  - US warranty claims were $30.37B in 2025 (Warranty Week).
  - Both via [ReliaMag](https://reliamag.com/articles/cost-of-poor-quality-scrap-rework-returns/).

**(c) Forcing functions**
- The FAA SMS rule was published 26 Apr 2024. Part 135 operators must declare compliance by 28 May 2027, and Part 21 holders are covered. [NATA](https://nata.aero/member-update-sms-final-rule-published/)
- There is no data-centre regulation. The pressure there is the annual Uptime findings and colocation SLAs.

**(d) Judge discomfort**
- **This is worker surveillance.** EU AI Act Annex III lists systems that monitor or evaluate workers as high-risk, now from 2 Dec 2027 after the Omnibus deal of 6 May 2026. [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)
- Emotion recognition at work has been banned since Feb 2025. [HRD](https://www.hcamag.com/ca/specialization/employment-law/eus-new-ai-act-restricts-emotion-recognition-systems-in-workplaces/524292)
- German works-council co-determination rules apply **[UNVERIFIED]**.
- Smart-glasses privacy is a known sensitivity for Meta.
- Mitigation: verify the work object, not the worker. Use SAM 3.1 to blur faces and do no productivity scoring.

**(e) Verdict.** Verification at fixed manufacturing stations is crowded. NVIDIA's VSS + Cosmos Reason stack has turned it into a partner category (DeepHow, Invisible AI, Tulip), so judges will see "Meta's version of an NVIDIA blueprint". The only credible opening is **work-order proof for mobile technicians**: data-centre remote hands (drive swaps) and MRO task cards. That version would fuse first-person video with the technician's spoken callouts, check against the written task card with no training, and produce a SAM-tracked evidence pack plus a QA hold. That job is only partly served (TechSee uses photos; Strivr is still positioning). **Partly served. Viable only if scoped tightly to remote hands or MRO.**

---

## 2. Accessibility gap auditor (sighted view vs screen-reader experience)

**(a) Who already does this job: incumbents are adding AI fast; the exact divergence job is in labs**
- **Deque**:
  - Machine-vision "advanced rules" that work on screenshots.
  - AI-run Intelligent Guided Tests.
  - An axe MCP server for coding agents.
  - Source: [Deque, Feb 2025, updated Dec 2025](https://www.deque.com/blog/advancing-ai-for-axe-the-next-leap-in-digital-accessibility)
- **Level Access** launched AI agents (Find/Fix/Prove plus an MCP server). None is a screen-reader agent. [Release, 6 Oct 2025](https://am590theanswer.com/technology/level-access-launches-new-ai-agents-to-pioneer-the-next-wave-of-digital-accessib/f413259a935f4c48bd95387f52201489)
- **Evinced** is the closest threat:
  - It shipped the agentic-fix suite Autopilot/Resolve/Harness. [Webull/PR, 29 Jul 2026](https://www.webull.ca/news-detail/15310838901335040)
  - Its **"Actor agents"**, including a "screen reader agent" that emulates assistive-technology users and files Jira tickets, are "still in our labs" and "coming soon". [Evinced](https://evinced.com/ai/monitoring)
- **BrowserStack** launched an Accessibility Issue Detection Agent that checks the DOM, the accessibility tree and focus order. [Tribune advertorial, 29 Oct 2025](https://www.tribuneindia.com/news/business/browserstack-launches-issue-detection-ai-agent-that-brings-human-intelligence-to-accessibility-testing)
- **Academic**: TaskAudit (UW/CMU) runs LLM agents through a TalkBack proxy. It reached 61.5% recall on functionality errors, against 5.2% for Google Accessibility Scanner. [arXiv 2510.12972](https://arxiv.org/pdf/2510.12972v1)
- **accessiBe** received an FTC order to pay $1M over misleading AI claims. [FTC, Apr 2025](https://ftc.gov/news-events/news/press-releases/2025/04/ftc-approves-final-order-requiring-accessibe-pay-1-million)
- **Not checked**: Equally AI, Applause and TestParty's current product. TestParty has a $4M seed and an SBIR Phase II award, per search titles only.

**(b) Size of the problem**
- **WebAIM Million 2026**:
  - 95.9% of home pages have detectable WCAG failures (94.8% in 2025).
  - Pages average 56.1 errors, up 10.1%.
  - Pages that use ARIA average 59.1 errors, against 42 for pages without it.
  - Source: [Priority Pixels summary](https://prioritypixels.co.uk/insights/web-accessibility-is-getting-worse-according-to-the-2026-webaim-million-report/)
- **Lawsuits (UsableNet 2025)**: 5,114 ADA digital-accessibility suits in 2025 (3,195 federal, 1,919 NY/CA state), 70% of them against e-commerce. Widgets "did not slow litigation" **[V]**. [UsableNet](https://info.usablenet.com/2025-year-end-digital-accessibility-lawsuit-report-plain-text)
- **What automation catches**:
  - Deque says automated testing covers 57% of issues by volume **[V]**.
  - BrowserStack says tools catch about 60% of web issues and under 30% of mobile issues **[V]**.

**(c) Forcing functions**
- **European Accessibility Act**, applicable since 28 Jun 2025. First actions, per [Disability World, 22 May 2026](https://www.disabilityworld.org/articles/eaa-first-year-enforcement-report/) (companies unnamed, figures **[UNVERIFIED]**):
  - Germany: a BAFA penalty in Q1 2026 in the "upper five figures".
  - Spain: sanctions in late 2025.
  - France: DGCCRF formal notices in early 2026.
- **DOJ ADA Title II**: the deadline for large public entities moved from 24 Apr 2026 to 26 Apr 2027, and for small entities to 2028. [Plante Moran](https://plantemoran.com/explore-our-thinking/insight/2026/04/doj-extends-ada-title-ii-web-accessibility-compliance-deadlines)

**(d) Judge discomfort: low**
- Overlay stigma after the FTC action: never claim "compliance", and keep a human (ideally a screen-reader user) approving tickets.
- Run computer use only on sites you are authorised to test.

**(e) Verdict.** Rule engines and AI fix suggestions are crowded (Deque, Level Access, Evinced, BrowserStack). The specific job is an agent that drives flows with computer use, captures what the screen reader actually says, and diffs that against vision-grounded screenshots to find divergences axe cannot see. That job **exists only as Evinced lab tech and academic prototypes**. It fits Meta's tools strongly (grounding plus computer use, with visual evidence boxes next to speech transcripts), and the impact is citable. **Partly served, with a window open now that is likely to close within months.**

---

## 3. Computer-use agent firewall ("Glass")

**(a) Who already does this job: crowded and consolidating, with over $1.4B in M&A**
- **Acquisitions**:
  - Check Point bought Lakera for about $300M. [SiliconANGLE, Sep 2025](https://siliconangle.com/?p=711465)
  - SentinelOne bought Prompt Security. [SiliconANGLE, Aug 2025](https://siliconangle.com/2025/08/05/sentinelone-acquires-ai-security-startup-prompt-security/)
  - Palo Alto Networks bought Protect AI **[UNVERIFIED: prior knowledge, 2025]**.
  - CrowdStrike bought Seraphic for about $420M. [GovInfoSecurity, 14 Jan 2026](https://www.govinfosecurity.com/seraphic-acquisition-arms-crowdstrike-for-ai-browser-threats-a-30520)
  - Akamai bought LayerX for $205M. [Fintech Global, May 2026](https://fintech.global/2026/05/19/akamai-acquires-layerx-to-close-enterprise-ai-gap/) Before the deal, LayerX shipped "Agentic Browser Protection", which detects and blocks prompt injection and applies policy to agent actions. [Akamai blog, 18 Feb 2026](https://www.akamai.com/blog/security/layerx-announces-the-first-dedicated-solution-for-agentic-browser-protection)
- **Menlo Agent Runtime Security** was expanded at Black Hat. [Menlo, Aug 2026](https://www.menlosecurity.com/press-releases/menlo-security-named-to-the-2026-inc-5000-as-enterprises-race-to-secure-ai-agents)
- **Island** raised $400M at a $6.4B valuation and is moving into AI agent controls. [RuntimeWire, 24 Sep 2026](https://runtimewire.com/article/island-400m-series-f-ai-agent-security)
- **Microsoft Defender AI agent runtime protection** (preview, docs dated Oct 2026) blocks prompt injection and harmful tool actions for Claude Code, Codex CLI and Copilot CLI. It does not mention screens. [Microsoft Learn](https://learn.microsoft.com/defender-endpoint/ai-agent-runtime-protection-overview)
- **Academic work on pixel-level guards**: WebAgentGuard, a multimodal guard over HTML and screenshots ([arXiv 2604.12284](https://arxiv.org/abs/2604.12284), Apr 2026); SnapGuard ([arXiv 2604.25562](https://arxiv.org/pdf/2604.25562)); MirrorGuard ([arXiv 2601.12822](https://arxiv.org/html/2601.12822v1)); VPI-Bench.
- **Meta's own work**: the Agents Rule of Two plus LlamaFirewall, Prompt Guard and Llama Guard. [Meta AI, 31 Oct 2025](https://ai.meta.com/blog/practical-ai-agent-security/)

**(b) Size of the problem (thin on money figures)**
- Anthropic, Claude for Chrome: prompt-injection attack success was 23.6% without mitigations and 11.2% with them. [TechSpot, Aug 2025](https://www.techspot.com/news/109252-claude-chrome-arrives-despite-11-prompt-injection-success.html)
- OpenAI says prompt injection is "unlikely to ever be fully 'solved'". [Fortune, 23 Dec 2025](https://www.fortune.com/2025/12/23/openai-ai-browser-prompt-injections-cybersecurity-hackers)
- Brave showed near-invisible screenshot text hijacking Perplexity Comet (reported 1 Oct 2025). [Brave](https://brave.com/blog/unseeable-prompt-injections/)
- There is no hard dollar-loss statistic. The money signal is the M&A values listed above.

**(c) Forcing functions**
- Gartner advisory "Cybersecurity Must Block AI Browsers for Now". [The Register, 8 Dec 2025](https://www.theregister.com/2025/12/08/gartner_recommends_ai_browser_ban)
- The EU AI Act robustness obligations for high-risk systems slipped to Dec 2027.
- No hard deadline exists.

**(d) Judge discomfort**
- The idea aligns with Meta's Rule of Two, which is a plus. Judges will still ask "why not LlamaFirewall?"
- An attack demo on Muse Spark's own computer use would expose weaknesses in Meta's model.

**(e) Verdict.** **Crowded.** Every browser-security incumbent, the major AI-firewall acquirers and Microsoft are shipping runtime agent defences. Pixel-level, rendered-screen inspection is a thin seam that academia is already working on. The impact case is hard to put in money terms, and a solo developer would be up against $400M-funded companies. **Not recommended** unless reframed narrowly as a "Rule-of-Two enforcer" demo for Muse Spark.

---

## 4. Returns-fraud inspection desk

**(a) Who already does this job: the exact job is in pilot at UPS and moving into rollout**
- **UPS Happy Returns "Return Vision"**:
  - Compares returned items with catalog images to catch decoy returns, e.g. a strap that is too wide, a missing logo or a wrong tag.
  - Staff decide first and the AI validates. Flagged items are audited within a day.
  - Under 1% of returns are flagged, at $218 prevented loss per flag **[V]**.
  - Pilot with Everlane; broader rollout planned for 2026.
  - Source: [Retail Dive, 12 Jan 2026](https://www.retaildive.com/news/ups-happy-returns-vision-software-pilot-everlane/809083/)
- **Clarity + ReturnPro**: X-ray plus computer vision, about 3 seconds per item. It compares each item with the manufacturer's profile to catch component swaps and counterfeits, across more than 20M units a year. [BusinessWire, 5 Feb 2026](https://www.businesswire.com/news/home/20260205136789/en/)
- **Two Boxes**: a bench platform with image classification, anomaly detection and fraud ID. It has raised $13M in total and processes about $1B of returned inventory a year **[V]**. [BusinessWire, 7 Apr 2026](https://www.businesswire.com/news/home/20260407584127/en/Two-Boxes-Accelerates-AI-Powered-Returns-Processing-Platform-with-New-Funding-Led-by-Assembly-Ventures)
- **Loop (Spring 2026)**: AI checks shopper-uploaded photos, and "Fraud Tools 2.0" claims $250M of at-risk refunds uncovered **[V]**. [Loop](https://www.loopreturns.com/launches/spring-2026/)
- **Narvar Shield** scores shopper risk before a return; it does no physical inspection. [Narvar, Mar 2025](https://corp.narvar.com/press/narvar-introduces-shield)
- **Appriss Retail** offers AI returns-fraud screening for Shopify. [BusinessWire, Apr 2025](https://businesswire.com/news/home/20250407249051/en/Appriss-Retail-Introduces-AI-Enabled-Returns-Fraud-Solution-for-Shopify)
- **Not checked**: ReturnGO, and Optoro's grading.

**(b) Size of the problem**
- **NRF/Happy Returns** ([NRF, 15 Oct 2025](https://nrf.com/media-center/press-releases/consumers-expected-to-return-nearly-850-billion-in-merchandise-in-2025)):
  - $849.9B returned in 2025, 15.8% of sales; online returns 19.3%.
  - 9% of returns are fraudulent.
  - Among retailers that track fraud, 64% saw more decoy or counterfeit returns and 65% saw more empty-box returns.
  - 85% already use AI against return fraud.
- **Appriss Retail 2026 benchmark** ([BusinessWire, 19 Feb 2026](https://www.businesswire.com/news/home/20260219293604/en)):
  - $706B returned in 2025.
  - $100B (14.2% of returns) lost to fraud and abuse: abuse 12%, fraud 2%.
  - The two reports' totals differ by methodology, and both are partly vendor-sourced.

**(c) Forcing functions**: none from regulation. The pressure is seasonal: the holiday return peak in Jan 2027, which is also when Happy Returns plans its wider rollout.

**(d) Judge discomfort: low to moderate.** Wrongful refund denials and false fraud accusations against consumers are the risk, along with GDPR Art. 22 limits on automated decisions. Adverse decisions must go to a human. There is no conflict with Meta's platforms.

**(e) Verdict.** **Crowded.** UPS/Happy Returns already does "compare returned item vs listing images" in pilot moving to rollout, Clarity goes deeper with X-ray, and Two Boxes owns the bench workflow. The remaining gaps (serial-label vs shipment cross-checks, SAM-tracked evidence) are features, not a category. A hackathon entry would read as derivative. **Not recommended.**

---

## 5. Callback (post-call help-desk social-engineering forensics)

**(a) Sep–Oct 2026 re-check: no product found that fuses diarized call audio, agent screen recording and IdP logs with human-gated containment.** The neighbours have moved closer:
- **Humanix** is the closest:
  - $18M across seed and Series A ([BusinessWire, 12 Nov 2025](https://businesswire.com/news/home/20251112119985/en/Humanix-Raises-$18M-to-Protect-the-Human-Layer-and-Stop-Social-Engineering-Attacks)); RSAC 2026 Innovation Sandbox top 10.
  - On 28–29 May 2026 it launched detection of "**live** violations of security procedures" across voice, chat, email and tickets. [Help Net Security](https://www.helpnetsecurity.com/2026/05/29/humanix-violations-detection/), [Techstrong](https://techstrong.it/?p=97097)
  - Integrations: Entra ID, ServiceNow, SIEM/SOAR. Responses can include account disablement.
  - It has no screen-evidence or post-call fusion. [Zeltser profile](https://zeltser.com/media/rsac-2026-sandbox/humanix)
- **RSA Help Desk Live Verify** does two-way verification plus ID document checks. [BusinessWire, 15 Jun 2026](https://www.businesswire.com/news/home/20260615853737/en/)
- **Pindrop Protect Fraud Assist** is agentic fraud investigation for phone calls in contact centres, not the IT help desk. [LetsDataScience, 17 Mar 2026](https://letsdatascience.com/news/pindrop-launches-protect-fraud-assist-solution-6f33a4f8)
- **imper.ai** raised $28M for real-time impersonation detection across Zoom, Teams, Slack and help desks. It has no containment. [Newswire, 4 Dec 2025](https://www.newswire.com/news/imper-ai-launches-with-28-million-in-funding-to-pioneer-real-time-22680543)
- **SecurityWeek, "Social Engineering Detection Moves Into the Live Conversation"**: the page would not load, so its content is **[UNVERIFIED]**. The title suggests the market is moving toward *in-call* detection, which leaves *post-call* forensics plus containment open.

**(b) Cost of the problem**
- **Clorox v Cognizant**: a $380M suit over help-desk password resets. A judge let the bulk of the suit proceed. [Law360, 25 Mar 2026](https://www.law360.com/articles/2457590)
- **M&S**: about a £300M hit; it ended its TCS help-desk contract. [Computing, 2025](https://www.computing.co.uk/news/2025/security/m-s-ends-contract-with-tcs)
- **Scattered Spider**: more than 100 compromises and over $100M in ransoms. Jubair is charged over 120 intrusions and $115M. [Vectra, 6 Jul 2026, citing DOJ filings](https://www.vectra.ai/blog/the-fbi-wrote-down-the-scattered-spider-playbook-and-it-starts-with-a-phone-call)

**(c) Forcing functions**
- **Canadian Cyber Centre alert AL26-010** (1 May 2026). It lists as warning signs "identity validation gaps in support tickets or **call logs**", MFA resets outside normal procedure, and OAuth tokens created around a suspicious call. That is close to Callback's evidence model. [cyber.gc.ca](https://cyber.gc.ca/en/alerts-advisories/al26-010-cyber-criminals-social-engineering-enabled-compromise-enterprise-saas-environments)
- Litigation is shifting liability onto outsourced help desks (the Clorox ruling).

**(d) Judge discomfort: moderate**
- It means recording and analysing employee calls and screens. Two-party consent laws apply, and the Humanix profile itself flags unanswered privacy questions.
- If speaker embeddings are matched across calls, they become voiceprints under BIPA/CUBI. Meta paid Texas $1.4B over biometrics. [Engadget, Jul 2024](https://www.engadget.com/meta-will-pay-14-billion-to-texas-settling-biometric-data-collection-suit-165451338.html)
- Mitigation: diarize within a single call only, never enrol voiceprints, keep retention short, and require human approval before any revocation.

**(e) Verdict.** **Still unclaimed as the exact job**: post-call fused proof that the verification step was skipped, combining who said what, what the agent's screen shows, and what the IdP did, followed by human-approved session revocation. Humanix is real-time and conversation-only, but it is about one feature away, since it already has Entra ID, ServiceNow and account-disable actions. Meta-tool fit is the best of the five: Voice Transcribe diarization, plus Muse Spark reading the screen recording, plus SAM 3.1 to highlight the skipped field. **Strongest whitespace of the five; move fast and position against Humanix explicitly.**

---
# Candidate briefs for independent scoring (Meta Global AI Developer Hackathon, Indie track)

**Situation (early Thu 29 Oct 2026, Cape Town).**
- **Builder:** one person, a backend engineer with production agent experience (compliance automation agents, SRE/DevOps ticket agents, guardrails, observability, evals) who is employed full time.
- **Deadline:** submission closes **Wed 4 Nov 2026, 21:00 ET** (Thu 5 Nov 04:00 SAST), about 7 calendar days away.
- **Realistic capacity:** about 40–45 focused hours (weeknight evenings plus the weekend), or about 60–70 h with 2–3 days of leave. That has not been decided. No technical spikes have been run yet.
- **Calibration from past Meta / Cerebral Valley hackathons** (small events, judged by Meta staff):
  - LlamaCon 2025: 1st an internal expert-finder over Jira/GitHub/docs; 2nd a fraud/compliance transaction analyser with a voice assistant; 3rd a zero-shot CCTV operator detecting plain-language events in video; best API use was a geologist's long-document → 3D model tool built for his own work.
  - Llama 3 hackathon 2024: 1st a $20 open smart-glasses build; 2nd a multi-agent debate arena; 3rd jailbreak research.
- **Required:** public GitHub repo, live product link, a 3-minute demo video watched by Meta judges, and three essays (project description, use of Meta products, "why are Meta's models important").
- **Stage 1** (pass/fail): fits a problem statement and uses Meta models.
- **Stage 2:** Meta judges score 0–10 on Impact 30% (real-world potential, who benefits, fit with a problem statement), Use of Meta AI Tooling 25% (creative, beyond basic integration, "surprised even us"), Technical Depth & Execution 20% (sound, refined engineering, real craft) and Demo 25% (working, holds up live, video "genuinely cool to watch").
- **Stage 3:** the top 5 per track are watched live and ranked.
- **Indie track framing:** "creativity, technical ambition, and whether it works."
- **Problem statements:** *Build for Your World* (a problem you know first-hand) or *Push the Frontier* (software, robotics, manufacturing, energy, materials; "give a machine a new capability… understand and control a physical system").
- **Anti-projects:** medical advice, basic RAG, simple image analyzers, simple education chatbots, job-application screeners, nutrition, personality, sports, politics/war, simple chat wrappers.
- **Meta stack available:**
  - Muse Spark 1.3: multimodal text/image/video/PDF input, 1M context, perception grounding on a 0–1000 grid, computer use, structured output, reasoning effort.
  - Muse Voice Transcribe: file and realtime ASR with speaker diarization.
  - SAM 3.1: open-vocabulary segmentation and video object tracking with stable IDs.
  - Muse Wonder (preview), Muse Image.
  - Open weights: Muse Glimmer (30B, Apache 2.0) and Muse Spark Open. Muse Code (coding agent).
- **House style signalled by Meta's workshops:** multimodal agents; verifiable agents (checks inside the tools, deterministic first, then LLM-as-judge, then a human); "see, decide, act"; the LLM plans, deterministic code actuates.

**Lessons from the builder's previous hackathon loss** (Gemini 3, ~4,500 entries; all three placed winners shared these traits):
- product-first videos;
- perceptual (non-text) input;
- a UI where the decision actually happens;
- a single memorable "hero moment";
- a visible human approval click;
- a named person in a vivid scenario.

The losing entry was a text-only backend pipeline with an afterthought dashboard and a slide-heavy, over-length video.

---

## A. Callback v2: help-desk social-engineering forensics and containment
- **User and job:** an IAM / service-desk security lead. Within minutes of a password or MFA-reset call ending, decide whether the reset was social engineering, then contain it.
- **Inputs:**
  - the recorded call, diarized: who said what (e.g. "I'm travelling, new phone");
  - keyframes from the help-desk agent's screen recording: was the callback-to-number-on-file verification step opened or skipped?
  - identity-provider logs after the reset.
- **Hero case:** the logs look benign, and a rules-only baseline says "benign". The diarized pretext plus the skipped verification step convict. A speaker hard negative ("new phone" said by the *agent*, not the caller) shows diarization overturning a false alarm. A human approves session revocation, executed by deterministic code against a sandbox IdP API.
- **Impact evidence:**
  - vishing is ~11% of initial intrusion vectors (M-Trends 2026, #2 vector);
  - vishing-and-smishing breaches average $5.29M (IBM 2026);
  - help-desk social engineering is believed to be the route in the M&S/Co-op attacks (£270–440M);
  - the attacker hand-off can be within seconds.
- **Whitespace (27 Oct):** real-time caller-verification tools and identity-threat tools are neighbours; no product found fusing recorded call + screen + IdP evidence with containment.
- **Build:** synthetic data (TTS two-voice calls with telephony degradation, Playwright recordings of a fictional admin console, synthetic IdP logs), a diarization step, a Spark keyframe check, a pretext analyser, a log trail, a citation check, a gate, sandbox revoke, a reviewer console and a small labelled eval (~40–80 cases).
- **Unknowns:** diarization accuracy on 8 kHz synthetic calls; Spark grounding accuracy on UI keyframes.
- **Previous independent estimates:** core skeleton 40–60 h after re-scope.
- **Other concerns:**
  - **Founder fit:** honest line "I build production agent pipelines for ops queues".
  - **Dual use:** the attack-script generator must stay at public-TTP level.
  - **Shape:** similar to the builder's losing Resilix (event → investigate → act in a system of record).

## B. Claim Clock: UK APP-scam reimbursement adjudication
- **User and job:** a bank fraud-claims handler. Decide a scam-victim reimbursement claim (UK mandatory APP reimbursement since Oct 2024) consistently and with evidence.
- **Inputs:** chat screenshots, the scam advert, bank warning screens and the recorded call. Rules (cap £85k, excess, the consumer standard of caution, 50:50 split between banks) are computed in code.
- **Hero case:** two near-identical claims decided differently by humans; Claim Clock flags the inconsistency. Adverse outcomes are always human-decided.
- **Impact evidence:**
  - ~301,500 in-scope claims in 18 months;
  - refund rates of 21–94% across firms;
  - the caution exception is applied 0% at some firms vs >25% at others.
- **Whitespace:** no adjudication product found; prevention tools exist.
- **Concerns:**
  - employer IP overlap is medium–high (the builder's employer does compliance automation for financial clients);
  - UK-specific acronyms for a likely US panel;
  - perception is less decisive (the bank's own logs hold the caution facts);
  - "intellectual rather than visceral" wow;
  - closest of the set to the "simple image analyzer" anti-project.
- **Build:** image-based, more tractable. Previous estimate 40–55 h.

## C. First Notice: multi-regime incident-reporting clocks from war-room evidence
- **User and job:** an incident commander or DPO at a regulated company. From the incident bridge recording, chat and dashboards, establish when the company became "aware" and which regulatory clocks are running (NIS2 24/72 h, DORA, GDPR 72 h, EU Cyber Resilience Act reporting live since Sep 2026 via a web-only portal). Then draft the initial notifications for human sign-off.
- **Hero case:** "Your incident tool says 03:05; the regulator's clock started at 02:23", because the IC said "confirmed" on the bridge (diarized) and the chart's spike (grounded) preceded it.
- **Whitespace:** narrowed by existing GRC notification tools (IR-OS, D3 Morpheus, OneTrust/RadarFirst/BreachRx) and bridge transcription (incident.io, PagerDuty).
- **Fit:** the strongest founder fit (the builder's SRE world).
- **Concerns:** paperwork drama (no adversary, no rescue); 3–7-speaker diarization. Previous estimate 45–65 h for a skeleton.

## D. Procedure Proof: zero-shot verification that a physical procedure was performed as written (NEW)
- **User and job:** a QA or operations supervisor (e.g. a data-centre operations lead closing "remote hands" work orders, or a maintenance/assembly QA inspector). Before a work order is closed or a unit released, verify from the technician's body-cam / smart-glasses / fixed-camera video, plus their spoken callouts, that each written step was actually done, in order, on the right object.
- **Hero case:** the technician says "pulling drive seven" (Voice), but the SAM-tracked hand pulls the drive from bay six (a healthy RAID member). The ticket would have closed as "done". Procedure Proof holds it, plays the 4-second clip with the tracked mask and the step alignment, and the supervisor approves "hold and page on-call".
- **Meta stack:**
  - SAM 3.1 video tracking on real-world video (its home turf);
  - Spark video understanding and 0–1000 grounding to localise steps and objects;
  - Voice diarization for callouts;
  - deterministic sequence alignment (SOP steps vs detected events) in code;
  - optionally Glimmer on-device.
- **Data:** self-filmed, staged clips (20–30) with exact labels (correct, skipped, wrong order, wrong object), using available hardware props (a multi-bay NAS or PC, or a bench assembly).
- **Theme:** Push the Frontier (physical systems, manufacturing), with a link to the builder's SRE world (data-centre outages).
- **Concerns:**
  - fine-grained hand-object accuracy is unknown (needs a spike);
  - staging realism;
  - worker-surveillance optics (frame it as proof-of-work that protects technicians, with consent);
  - incumbents in vision-based assembly verification (see research);
  - no first-hand domain user.
- **Build:** entirely new pipeline; estimated 40–55 h.

## E. Accessibility Gap Auditor (NEW)
- **User and job:** a product team at a company selling into the EU/US. Before release, find the accessibility failures that automated rule engines miss, prove them, and fix them.
- **How it works:** an agent walks the app's key flows (Spark computer use). At each step it compares what a sighted user sees (vision grounding on the screenshot) with what a screen-reader user gets (the accessibility tree and, optionally, real screen-reader speech). It files grounded tickets and draft code fixes for a developer to approve.
- **Hero case:** at checkout, axe-core reports zero errors, but the screen reader announces "button, button, image" where sighted users see "Pay R1,249". The agent shows both side by side, files the ticket and drafts the aria-label fix. A blind tester confirms.
- **Theme:** Build for Your World (the builder ships software) or Push the Frontier (software).
- **Concerns:** a crowded accessibility-tooling market (see research); "why not GPT/Gemini computer use" (vendor swap); Meta-tooling depth is moderate (computer use + grounding; SAM and Voice optional).
- **Data:** a deliberately flawed demo app with seeded, labelled violations, plus public sites. Estimated 30–45 h.

## F. Glass: runtime firewall for computer-use agents (from the 27 Oct long list)
- **User and job:** a platform/security team deploying browser or computer-use agents. Inspect what the agent sees on screen (rendered pixels, hidden or low-contrast text, injected instructions) before each action, and block or escalate risky actions under Meta's "Agents Rule of Two".
- **Hero case:** a product page with an invisible instruction tells a shopping agent to email the user's saved addresses to an attacker. Glass grounds the hidden text, blocks the action and shows why.
- **Concerns:** economics are thin and hard to quantify; a security-research feel; similar to a Gemini 3 honourable mention (AgentGuard).
- **Build:** ~30–40 h. Founder fit good (guardrails).

## G. Returns-fraud inspection desk (NEW)
- **User and job:** a returns associate at an online retailer or small merchant. At the returns bench, compare the returned item (photos or a short video, serial labels) with the order, listing images and shipment record. Catch item swaps ("brick in the box"), counterfeits and used/"wardrobed" items. Auto-approve clean refunds; route adverse decisions to a human.
- **Hero case:** the serial label grounded on the returned laptop does not match the one shipped. The refund is held and a human decides with the evidence boxed.
- **Meta stack:** Spark grounding and reading of labels and defects; SAM masks and video tracking at the bench; Spark comparing listing and return images.
- **Fit:** Build for Your World (the builder previously built e-commerce fraud agents).
- **Concerns:** an "image analyzer" feel unless the case workflow is rich; consumer-adverse decisions; incumbents (see research).
- **Data:** staged at home. ~35–45 h.

---

## Whitespace research results (29 Oct 2026, independent web check; full notes in new_candidates_whitespace.md)

**Callback (A): still unclaimed as the exact job.**
- No Sep–Oct 2026 product fuses diarized call + agent screen recording + IdP logs with human-gated containment.
- The closest neighbour is Humanix ($18M; RSAC 2026 Innovation Sandbox top 10). It detects *live* procedure violations across voice, chat, email and tickets, integrates with Entra/ServiceNow and can disable accounts. It has no screen evidence and no post-call fusion, so it is about one feature away.
- Other neighbours: RSA Help Desk Live Verify (two-way verification, Jun 2026); imper.ai ($28M, real-time impersonation detection); Pindrop Fraud Assist (contact centres).
- **New evidence:**
  - Clorox v Cognizant, a $380M suit over help-desk password resets, allowed to proceed in Mar 2026.
  - Canadian Cyber Centre alert AL26-010 (May 2026) names "identity validation gaps in support tickets or call logs", MFA resets outside procedure and OAuth tokens around suspicious calls as warning signs.
  - Scattered Spider: 120+ intrusions and $115M in ransoms per DOJ filings.
- **Sensitivities:** recording and analysing employee calls and screens (two-party consent); voiceprint/biometric laws if speakers are matched across calls. Mitigation: diarize within a call only, never enrol voiceprints.

**Procedure Proof (D): partly served.**
- Fixed-station factory SOP verification is crowded and now an NVIDIA partner category:
  - DeepHow is live at Foxconn on NVIDIA Cosmos (Jun 2026);
  - Invisible AI, Tulip and Pegatron run on NVIDIA VSS;
  - Retrocausal (3M, Stellantis, Stryker);
  - Squint ($40M); Cerrion ($18M).
- **Mobile technician work-order proof is open:** data-centre remote hands and MRO task cards, fusing first-person video with spoken callouts. TechSee only checks photos for telecom techs; Strivr is still at the "positioning" stage.
- **The technology is not solved:** IKEA-Bench (Apr 2026), the best open VLM reaches 59.4% on assembly-step recognition against 25% chance.
- **Impact:** Uptime 2025/2026 says human error plays a part in two-thirds to four-fifths of outages, failure to follow procedures appears in 58% of human-error outages (the leading cause), and 20% of major outages cost >$1M. Boeing door plug: four bolts missing, "failure to follow proper manufacturing procedures".
- **Sensitivity:** worker monitoring is "high-risk" under the EU AI Act Annex III (Dec 2027); smart-glasses privacy is sensitive for Meta.

**Accessibility auditor (E): partly served, window open now.**
- Deque, Level Access, Evinced and BrowserStack ship AI rule checks and fixes.
- The exact sighted-vs-screen-reader divergence job exists only as Evinced's in-lab "screen reader agent" ("coming soon") and an academic prototype (TaskAudit, 61.5% recall vs 5.2% for Google Accessibility Scanner).
- **Impact:**
  - WebAIM Million 2026: 95.9% of home pages fail detectable WCAG checks, averaging 56.1 errors.
  - 5,114 ADA digital-accessibility suits in 2025 (UsableNet, vendor), 70% against e-commerce.
  - Automated tools catch ~57–60% of issues (vendor).
  - EAA in force since 28 Jun 2025, with first enforcement actions reported (unverified).
- **Judge discomfort:** low (the accessiBe FTC action means never claiming "compliance").

**Glass (F): crowded.** Lakera (Check Point, ~$300M), Prompt Security (SentinelOne), Seraphic (CrowdStrike, ~$420M), LayerX (Akamai, $205M, "Agentic Browser Protection"), Menlo, Island ($400M) and Microsoft Defender's agent runtime protection preview. There are no hard dollar-loss figures. Meta's own LlamaFirewall invites "why not that?". Not recommended.

**Returns desk (G): crowded.** UPS Happy Returns "Return Vision" compares returned items with catalog images (pilot with Everlane, rollout in 2026); Clarity + ReturnPro do X-ray plus vision; Two Boxes owns the bench workflow; Loop does AI photo checks. Impact: $100B lost to return fraud/abuse (Appriss 2026). Not recommended.

---
# Independent judge-panel scores, candidates A–G (29 Oct 2026)

Judges: **(R)** research engineer, **(W)** workshop/partner engineer, **(V)** startup/VC. Weights 30/25/20/25. "Golden" = a solid core version ships.

## 1. Golden scores

**A. Callback v2: 6.85**
- Impact 7 (V): Scattered Spider, M&S and Clorox make the pain obvious and the buyer has budget, but Humanix is one feature away and post-call is slower than live.
- Tooling 6.5 (R): real three-modality fusion, but two-speaker diarization and reading one console state are commodity jobs.
- Depth 7.5 (W): house style (deterministic joins, citation check, gate, sandbox revoke) on the builder's home ground.
- Demo 6.5 (V): "the logs say benign, the call convicts" is a good beat, but TTS voices on a fictional console read as staged.

**B. Claim Clock: 5.35**
- Impact 6 (V): the 21–94% refund spread is a real fairness problem, but UK-only and sold to a cost centre.
- Tooling 4.5 (R): reading screenshots is the "simple image analyzer" anti-pattern; perception does not decide the case.
- Depth 6.5 (W): rules in code plus a consistency engine is sound, verifiable work.
- Demo 4.5 (V): intellectual, not visceral.

**C. First Notice: 6.08**
- Impact 6 (V): fines rarely bite, GRC incumbents exist, and legal may not want a tool documenting earlier awareness.
- Tooling 6.5 (R): turning 0–1000 chart grounding into timestamps is clever; 3–7-speaker diarization is meaningful but fragile.
- Depth 7 (W): deterministic regime clocks with human sign-off is correct verifiable-agent design.
- Demo 5 (V): a timeline and a draft; no adversary, no rescue.

**D. Procedure Proof: 7.85**
- Impact 7 (V): procedure failure leads human-error outages and the Boeing door plug is unforgettable, but wrong-pull frequency and the exact buyer are unquantified.
- Tooling 8.5 (R): SAM 3.1 tracking on real first-person video, Voice timestamps and Spark step localisation, each on home turf, fused into a say/do mismatch: the "surprised us" combination.
- Depth 7.5 (W): deterministic alignment over perception events is "model perceives, code decides"; real clips beat synthetic generators.
- Demo 8.5 (V): "pulling drive seven" over a mask on bay six is a 4-second hero clip needing no narration.

**E. Accessibility Gap Auditor: 6.90**
- Impact 7.5 (V): 95.9% failing pages, 5,000+ suits a year and the EAA give a budgeted market with obvious human benefit, though an incumbent could absorb it.
- Tooling 6 (R): computer use plus grounding is load-bearing but obvious and vendor-swappable.
- Depth 7 (W): seeded, labelled violations give a clean eval; the accessibility-tree diff is honest engineering.
- Demo 7 (V): hearing "button, button, image" beside "Pay R1,249" lands, harder with a named blind tester.

**F. Glass: 5.93**
- Impact 5 (V): no dollar-loss figures; $1.4B+ of incumbent M&A leaves no wedge.
- Tooling 6 (R): grounding hidden text is fine, but Meta ships LlamaFirewall, and attacking Spark on stage is awkward.
- Depth 6.5 (W): a Rule-of-Two policy gate is on-message but thin.
- Demo 6.5 (V): a good reveal, already seen as a Gemini 3 honourable mention.

**G. Returns desk: 5.78**
- Impact 6 (V): $100B, but UPS, Clarity and Two Boxes already do this job.
- Tooling 5.5 (R): comparing labels and images is the anti-project shape.
- Depth 5.5 (W): the refund gate is the only non-trivial engineering.
- Demo 6 (V): fun, but an image comparer with a refund button.

## 2. Ship probability and risk-adjusted expected score

A degraded build is assumed to lose 2 points each on Tooling, Depth and Demo, which is −1.4 weighted. Expected score (EV) = golden − 1.4 × (1 − p). "Convincing core" means the hero case works live, plus a small honest eval, a workbench UI and the video.

| | Golden | p (40–45 h) | EV (no leave) | p (60–70 h) | EV (leave) |
|---|---|---|---|---|---|
| **D** | 7.85 | 0.30 | **6.87** | 0.55 | **7.22** |
| **E** | 6.90 | 0.45 | 6.13 | 0.75 | 6.55 |
| **A** | 6.85 | 0.30 | 5.87 | 0.60 | 6.29 |
| F | 5.92 | 0.45 | 5.15 | 0.75 | 5.58 |
| G | 5.78 | 0.50 | 5.08 | 0.80 | 5.50 |
| C | 6.08 | 0.25 | 5.03 | 0.50 | 5.38 |
| B | 5.35 | 0.45 | 4.58 | 0.75 | 5.00 |

**What drives p:** A (~60 h) is risky by volume (three generators plus a media UI); C stacks multi-speaker diarization on ~58 h; D has the one real feasibility unknown (which caddy left which bay under hand occlusion); E, F and G fit in ~50 h.

**Caveat on D.** The −2 assumption flatters D. If tracking fails, there is no hero at all, so the outcome is closer to −4 per criterion. On that basis D falls to 5.89 without leave (level with A, below E) and 6.59 with leave.

**The robust play** is a 4-hour D spike on Thursday night with a hard kill criterion and E as fallback. With a 0.6 pass chance (p then ~0.45 / 0.70) and E shipping on the remaining time if it fails, EV is about **6.6 without leave and 7.0 with leave**.

**Leave is worth +0.35–0.45 EV for every candidate.** It is the single biggest lever available.

## 3. Biggest objection in the room, and the change that would raise the score most

| | Objection | Single change |
|---|---|---|
| A | "You generated every input (TTS voices, a fake console, fake logs), so the detector finds what you planted. And Humanix already catches this live." | Run it on real systems: a human-voiced call over a real phone line, a real open-source help-desk/IdP UI (e.g. Keycloak), and a revoke that kills a real dev-tenant session on camera. |
| B | "This is a screenshot reader plus a rules table, and your employer may own it." | Drop it. |
| C | "Who buys a tool that proves you knew 42 minutes before you said so? And nothing happens on screen." | Make it real-time on the live bridge (Voice realtime), so the clock starts on screen and the draft beats the deadline. |
| D | "It works on your desk with 20 clips you filmed and labelled yourself, yet IKEA-Bench says VLMs get 59%. Why should I believe it generalises?" | Make bay identity deterministic: SAM 3.1 track geometry against a bay grid calibrated from one frame, verified against the NAS's own hot-swap log. That log also auto-labels the eval, including held-out clips filmed by a second person. |
| E | "Why Meta? Any frontier model's computer use does this, and Evinced ships it next quarter." | Find one real divergence on a real, axe-clean public flow (disclosed responsibly), and have a named blind tester confirm it on camera. |
| F | "Why not LlamaFirewall?" | Drop it. |
| G | "UPS already does this." | Drop it. |

## 4. Likely top-5 live finalists (if built golden)

**1. D, 2. E, 3. A.** Even golden, the chance of reaching the Indie top 5 among thousands of entries is modest: roughly 10–20% for D, 5–10% for E and 4–8% for A.

**Pairwise in the final:**
- **D beats E (~65%):** D shows more creativity and technical ambition, and its physical demo is more watchable. E's best counter is its human benefit.
- **D beats A (~70%):** real video and an instantly legible mistake beat a staged security console.
- **E beats A (~55%):** both are software. E's audio side-by-side and blind tester carry more emotion than synthetic voices do, though A's Scattered Spider story keeps it close.

## 5. Final ranking

1. **D. Procedure Proof.** It has the highest ceiling on the two perception-heavy criteria (Tooling and Demo, 50% combined), it fits *Push the Frontier* exactly, and its hero can be made deterministic. Build it only behind a day-one spike gate.
2. **E. Accessibility Gap Auditor.** It is the best expected value per hour and the right fallback, because it degrades gracefully and has the clearest beneficiaries.
3. **A. Callback v2.** It has the strongest whitespace and story. But it takes the most hours, depends on synthetic data, and carries the highest risk of sliding back into the Resilix "backend pipeline" pattern.
4. **C. First Notice.** A dominates it on drama and tooling. Park it.
5. **F. Glass.** Drop.
6. **G. Returns desk.** Drop.
7. **B. Claim Clock.** Drop. The employer IP overlap alone disqualifies it.

**Drop outright: B, F, G.** C is not worth building this week. The real decision is D versus E, and A only makes sense if the builder takes leave *and* rejects D's technical risk.

## 6. Doubtful facts and naive strategy in the briefs

1. **E's hero is probably wrong as written.** axe-core's defaults flag unnamed buttons (`button-name`) and missing alt text (`image-alt`), so "zero errors" plus "button, button, image" won't reproduce. Use failures axe passes: `alt="image"`, an `aria-label` contradicting visible text (`label-content-name-mismatch` is experimental, off by default), canvas/CSS-generated prices, focus traps.
2. **A's timing contradicts itself.** If hand-off is "within seconds", containment "within minutes" is late. Reframe around later persistence (new MFA factors, OAuth grants) and make revocation undo those, not just sessions.
3. **A's hard negative may not prove diarization matters.** Who said "new phone" needs role mapping, which an LLM usually infers from context anyway, and clean two-voice TTS makes diarization easy. Design a case that is genuinely ambiguous without speaker labels.
4. **D's statistics cover all human-error outages, not remote hands;** don't imply 58% are preventable by video. SAM 3.1 video tracking needs a GPU (precompute golden cases; budget a GPU upload path), check the SAM licence, and confirm a hot-swap multi-bay unit is actually owned. A bench-assembly fallback is IKEA-Bench territory and far weaker.
5. **Employer IP risk is not only B's.** A and C are compliance-adjacent too; check the contract first.
6. **One day of "no product found" is weak evidence, and whitespace is not a criterion.** Impact scores potential and beneficiaries; "one feature away" is true of every candidate.
7. **The calibration events were small.** At thousands of entries, screening runs on the video; the first 20 seconds outweigh the architecture.
8. **Capacity figures disagree** (40–45 / 60–70 h in the brief vs 35–40 / 55–65 h in `hours_estimates.md`). Without leave, A, C and D (55–60 h) exceed capacity by ~40% before planning-fallacy correction, with no spikes run.
9. **Unverified capabilities** (Spark computer use, 0–1000 grounding on dense UIs, 8 kHz diarization) underpin the plans; spike before committing.
10. **Verify essay statistics:** re-source M-Trends 2026 (11%, #2) and IBM 2026 ($5.29M); "£270–440M" is the Cyber Monitoring Centre's estimate for M&S and Co-op *combined*.
11. **E's theme fit:** the builder is not an accessibility practitioner, so frame E as *Push the Frontier (software)*.
12. **Optional extras are a trap.** Glimmer on-device (D) or SAM (A) add hours, not score; "beyond basic" means load-bearing models, not more logos.

---
# Bottom-up hour estimates for a core build, solo, with coding agents (29 Oct)

**Common to every candidate (≈19 h):**
- repo, contracts, trace store, case record and verification-in-tools skeleton: 4 h;
- workbench UI shell with streaming trace and approve control: 6 h;
- deploy + golden-case button + replay: 3 h;
- small eval harness + table: 3 h;
- README / docs / form essays: 3 h.

**Video:** script, record, edit and captions ≈ 8 h. Cold QA + submit ≈ 2 h.
**Shared total:** ≈ 29 h.

**Domain-specific work:**

| Candidate | Domain items | Domain total | Grand total |
|---|---|---|---|
| A. Callback v2 | TTS call generator + telephony degrade 4 h; Playwright console + keyframes 4 h; IdP log generator 3 h; Voice diarization adapter + role mapping 3 h; Spark keyframe step check 3 h; pretext analyser + cross-call 3 h; trail joins 2 h; sandbox revoke API 2 h; media player with diarized transcript in UI 4 h; spikes 3 h | 31 h | ≈ 60 h |
| B. Claim Clock | screenshot/chat generator 4 h; rulebook in code + tests 4 h; Spark lens grounding 3 h; consistency engine 4 h; adjudication UI 4 h; spikes 2 h | 21 h | ≈ 50 h |
| C. First Notice | bridge-call generator multi-speaker 5 h; chart generator 2 h; diarization + anchors 4 h; chart grounding + pixel-to-time 4 h; regime plug-ins 4 h; drafting + sign-off 3 h; UI timeline 4 h; spikes 3 h | 29 h | ≈ 58 h |
| D. Procedure Proof | filming 20–30 clips 3 h; SOP schema + work orders 2 h; SAM video tracking adapter (parser, SAM licence) 4 h; Spark step detection + grounding 5 h; Voice callouts 2 h; deterministic alignment 3 h; video player with mask overlay (@meta-sam/react) 4 h; spikes 3 h | 26 h | ≈ 55 h. Highest technical uncertainty |
| E. Accessibility auditor | flawed demo app with seeded labels 3 h; computer-use loop on sandbox 5 h; a11y-tree capture + diff 3 h; grounding of visual elements 3 h; ticket/PR drafting 2 h; side-by-side UI 3 h; spikes 2 h | 21 h | ≈ 50 h |
| F. Glass | injected-page corpus 3 h; computer-use loop 5 h; screen inspector (grounding + DOM/pixel diff) 4 h; policy gate 3 h; UI 3 h; spikes 2 h | 20 h | ≈ 49 h |
| G. Returns desk | staged photo/video set 3 h; order/listing/shipment mock 2 h; Spark label/serial grounding + compare 4 h; SAM masks 2 h; refund gate + Stripe/Shopify test mode 3 h; bench UI 4 h; spikes 2 h | 20 h | ≈ 49 h |

**Capacity:** ≈ 35–40 h without leave; ≈ 55–65 h with 2–3 days of leave. At 35–40 h, every candidate must cut domain scope by 30–40%. The candidates that degrade most gracefully are the ones whose hero case needs only one perception step.
