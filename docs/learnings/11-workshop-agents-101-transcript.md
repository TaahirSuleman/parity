# Workshop transcript — "Agents 101: Build a Multimodal AI Agent" (Pt. 1)
Source: https://vimeo.com/1239550947/045ee6e57e (Vimeo auto-transcript, ~32 min). Live session, Tue 27 Oct 2026, 12:00 ET. Host: Maya (Cerebral Valley / Meta events); presenter: Suraj Subramanian, Partner Engineer, Meta. Workshop repo: https://github.com/meta-models/legal-agent-workshop. Part 2 ("Agents 102: Best Practices for Verifiable Agents", Yash Khare) is Wed 28 Oct. Captured 28 Oct 2026; two short gaps in the auto-transcript (≈06:54–07:15, ≈10:00–10:25).

**Prerequisites given to participants:** download Muse Code; sign in to Muse Code with your API key; `git clone https://github.com/meta-models/legal-agent-workshop.git && cd legal-agent-workshop/agent && cp .env.example .env` (add `MODEL_API_KEY`). Expected token spend ≈ $7.

[00:35] Hello, everyone. Welcome, and thanks for joining today's hackathon workshop on building multimodal AI agents. This is a hands-on workshop in two parts.
[00:50] So today you'll see Muse Code and the Meta Model API. You'll use them to build an agent that works across documents, scans, and charts with
[01:01] practical tips that you can actually bring back to your hackathon project. And tomorrow, we're going to focus on verification in the second workshop.
[01:11] So this is a two-part series, and that will really be helping your agent check its work and recognize when it
[01:20] needs more information. So a couple of quick housekeeping notes. We are recording this session, and we'll share it with
[01:28] everyone afterward in Discord, so you can revisit anything that you missed. And if you have questions or get stuck while following
[01:38] along, please just drop them in the chat. For debugging questions that need a little bit closer look at your
[01:47] project, you can join our office hours tomorrow in the Discord and work through those with some of the team
[01:54] members. So now I'd like to introduce Suraj, who's a partner engineer at Meta, and he'll be leading today's workshop. So thanks for joining us, Suraj, and I'll
[02:08] kick it over to you. Thanks, Maya, and welcome, everyone, to the developer hackathon. So happy to have all of you here.
[02:19] Like Maya said, I'm a partner engineer, and I work very closely with the Meta models and Muse Code, and happy to share
[02:26] a little of what we know in terms of building agents. So, just to recap really quick. By now, you should have downloaded Muse Code on your machine and logged in with
[02:39] your API key. You have also cloned the repository from GitHub called Legal Agent Workshop. Make sure you have added your API key to the environment file
[02:52] as per the instructions shared on Discord. You can also refer to section 1.3 in the handbook, also in the repository.
[03:02] I have three tabs open on my end, and you could probably do the same. Two of the tabs are in the repository root,
[03:11] Legal Agent Workshop. And the third tab is Muse Code opened in the Agent folder of Legal Agent Workshop. So what you might want to do is do CD agent
[03:24] and start Muse Code over there. So I have these three tabs over here. The first thing I want to do, and you can also refer to section
[03:35] 1.4 of the handbook, is to run the helper setup. So CD agent. And what this is going to do is basically seed our repository with a few
[03:52] documents and make sure that everything's working, that your machine is able to reach our API. Okay. So we have a short session today,
[04:03] and so we've pre-built some of the plumbing that your agent will be needing. And I'll quickly give you a sense of what we have here.
[04:15] So the first thing, cases. It houses the task that our legal agent is going to solve today. Agent kit contains the primitives that you can use to build the agent.
[04:28] This also includes some of the built-in tools that your agent will be using. And as the scope of your agent
[04:36] grows, it might need more tools to use, and this is where you will want to implement some of those.
[04:45] Legal agent is where you're actually going to be writing the code and where you're actually going to be implementing the agent we have for this session.
[04:53] And we also have a UI, which can provide a visual sense of what the agent is doing. It's a very lightweight console.
[05:03] I'm actually just going to start that now by doing Python ui.py. So this is what it should look like.
[05:21] And the first thing that you see here is the legal challenge that we are going to solve for today.
[05:27] So these companies, North Bridge and Caldera, they don't exist. They're fictitious. The documents are also fake. But my friends in legal, they tell me that this is a fairly relatable
[05:39] task. And in any case, in this session, we are going to focus more on the mechanics of building an AI agent, not the legal task
[05:47] it is working on. So the same principles that you implement for this legal agent can be applicable across different
[05:54] verticals and different domains. Now, let's define how our agent is going to work. And, I'm going to pull up the
[06:07] system prompt here So this is a system prompt we are going to give our agent,
[06:28] and it's basically telling it how we expect it to work. And take a look at it. This is not specific to any given
[06:36] task. It's the behavior we seed our legal agent with. So for example, if you write here, "Always talk like a 17th
[06:44] century pirate," it's going to do that regardless of what the conversation is about. So here, one of the things that matters to us a lot is visibility into
[06:54] what the agent is doing. So we have asked it to put together a checklist for everything that it needs to do,
[07:15] Now, we're going to set some ground rules for Muse Code. Well, actually, before that, Muse Code, it's our coding hard-- It's our harness to
[07:28] code with AI. And I'm using Muse Spark 1.3 over here with the reasoning set to max. You can switch the models
[07:41] from using /model and change the reasoning effort with /effort. So I'm at 1.3 at max reasoning. Now, Muse Code is quite good at reading all the
[07:55] files in a directory, formulating the context it needs, and basically running off with the task. But since we are in a workshop, we want it to go slowly, and we want it to
[08:06] go step by step. So we're going to put in some ground rules for Muse Code. And this is the prompt in section
[08:15] 1.7 of the handbook. I'm just going to copy that here. If for any reason you need to... Oh. Okay, just give me one moment.
[08:50] Suraj, while you're sorting that out, even you can tell us a little bit about what you're debugging or anything that's happening.
[08:57] But also I have several questions about Muse Code. There was a question in the chat about how does the Muse Code plan work?
[09:11] Does it work with rate limits? Do you have an answer for that? So the way I'm using that is with the API key
[09:23] on Muse Code. So basically, the API key that you have created, I'm passing that to Muse Code and initializing it
[09:32] with that. So the rate limits that apply to your API key, it'll be the same thing over here. Was that the question, Maya?
[09:43] Yes, I believe so. Okay. All right. So as any live technical session, we have to have some hiccups, right?
[09:51] It's almost a legacy at Meta at this point. So, we have our ground rules set up in Muse Code.
[09:59] And again, if you have to restart Muse Code for any reason, just paste this again. All right. So looks like we have everything
[10:25] First, I'm going to tell Muse Code what I want at a high level, and then I'm also going to ask it to use the inbuilt primitives in AgentKit and not
[10:32] re-implement anything that already exists. And I'm literally going to tell it. I'm actually thinking of using the voice input here.
[10:41] You can start it with Option V on a Mac. And let's see how it goes. I want to implement an agentic loop in loop.py.
[10:54] The agent's system prompt is in system_instructions.md. And the task it needs to solve is in objective.md. Refer to the primitives in AgentKit.
[11:08] Start with progress.py, tools, and case_record.py. Propose a brief plan for building this loop. Tell me what happens in a turn and when does this loop stop.
[11:23] Don't write any code yet. All right. So to the earlier question, the planning or the reasoning, you see that Muse Code shows the
[11:40] thinking section. That's where it's deciding what needs to be done. It's basically planning. Then when it reads skills or
[11:51] running commands, those are the actions. And then it observes the outputs of those actions and decides what's next to plan. So you're actually seeing the agentic loop in action right
[12:02] over here. Yeah, so we see that it's gathered context from the library, from the repository It's found the primitives.
[12:17] It's referring to the tests to get a sense of what is expected of the agent. It's also getting a sense of what is
[12:28] the task the agent is going to be solving. And it's come up with a plan of action. So the goal, build the agentic loop.
[12:43] Run agent, da, da, da, approach. So it's given a very comprehensive sense of what it is going to do and why
[12:50] it thinks that's the right thing to do. And it's also mentioned specifically that no files have been changed in this
[13:00] planning turn. So now I've gone through this really quickly, also because I'm quite familiar with this plan. I've run this a couple of times now, but when you are actually
[13:10] using Muse Code to write code or any agentic harness for that matter, I think it's a good practice to have it
[13:18] come up with a plan and be very explicit about what it's going to do. So that gives you a chance to align
[13:25] its actions with your vision and, yeah, so that you're not surprised later. And you can always iterate and tweak the
[13:37] plan and get it to understand your vision better before it starts writing any code. So this looks fine, and we're just going to ask it to build it.
[13:48] This looks fine, build it, but don't run the helper turns test after you build it. Make sure that the agent also files a memo with its findings after it's
[14:04] done. Okay, so I did tweak this plan slightly. I've asked it to not run a helper run, and I think I may have misspoke over here.
[14:20] So I'm just going to edit this. So now we're going to see it hopefully edit
[14:40] legal agent loop. And while we're waiting for it to build this out, Maya, if you have any questions, we can take some now.
[14:57] Yes, we do have a few questions. So one of the questions was, would it be possible to use an agent to ingest court documents from a feed
[15:09] such as an RSS feed? I think so, yes. In general, if you can write a function to do something, so let's say if I have a Python
[15:23] function or even a curl command to pull the data from a feed, the agent can call that function, just as you might.
[15:35] So it actually has its own sandbox environment where it can execute code. So it'll just execute the code to pull the RSS feeds and then
[15:45] even post-process it to maybe store it as a markdown or as a PDF, depending on what you want. It can, on the fly, compose multiple tool calls.
[15:56] So one tool call could be just like sourcing RSS feeds. The other one could be pulling that. A third one could be post-processing that into a PDF, and
[16:06] a fourth one could be sending it as an email attachment. So yes, to your point, the agent can do that.
[16:15] Okay, coming back to our console. So Muse Code has built the loop, and as you see, the code has been written in this file, in
[16:27] legal_agent_loop.py. And let's see. It's basically followed the spec that we asked it to do. It's only changed loop.py, and it did not run the helper run, so it did
[16:47] obey the little tweak I made to its plan. Okay, so if you go back to the console now, earlier, start agent might have been grayed
[17:00] out because the loop was not implemented. Now, if the loop is implemented and it's looking good, start agent should be valid.
[17:10] Now, I'm just going to quickly go over a few options over here. We have turns 30. This basically sets a budget of
[17:18] how many turns, plan, act, observe turns, the agent is going to do. I've just kept 30 so that, just to keep a budget.
[17:28] Usually, in the past when I've run this, it just took about 20 turns. And the other option is step through turns. When you check this,
[17:39] after every turn, the agent is going to pause. It's going to pause to allow you to see what it did in that one turn.
[17:46] And for the first turn, I'm going to step through it just to give you a sense of what I'm talking about.
[17:52] So I check step through turns, and I click start agent, and hopefully this works. All right. So it's paused at the first turn, and let's see.
[18:05] The first thing was the agent was, let's see what the model saw, actually. So what it has seen so far is the seed prompt, the system
[18:16] instructions that we shared it, basically the behavior that we want the agent to have. It got the first message as the assignment itself
[18:27] about the two companies. It also saw what tools it had available to it. And based on all of this stuff, all of this context, it has
[18:39] decided it's going to call list documents. That is, to see what documents exist relating to these companies, and it's gotten a list or an index of all the
[18:49] documents out there. So that was one turn. You see the plan, you see the action, and you see the observation.
[19:01] Let's do one more turn. Now, based on the documents it has read, it has decided what are the things it needs to do to solve this legal task,
[19:18] and it has basically populated the checklist with that. Again, I'm just going to open the console here. It's seen the conversation so far, including all of the documents that were
[19:28] available to it. And again, it knows what tools are available to it. It decided to call set checklist, and it has populated the contents of this checklist.
[19:44] And the tool call for set checklist has returned a success and exit zero. So again, that was another granular turn, and you can
[19:55] keep stepping through each turn and going into this console to really understand what are the inputs to the model,
[20:04] what is it deciding, and what are the actions it's taking, and what are the outputs of those actions. And you can see how these all flow together
[20:13] sequentially, turn after turn. So I'm going to just go ahead and click run to end. This is going to take a few minutes.
[20:22] And while this is doing its thing, Maya, maybe we can take on a few more questions as well. Yeah, sounds good. So one question
[20:33] was asking if you could just elaborate a little bit more on the agent console, or the AgentKit, actually. Is it a custom harness? And talk a little bit more about the
[20:45] AgentKit. Yeah. Sure. All right. So let me actually bring my VS Code out here, because that'll be a little easier.
[20:55] Well, actually, this could be a question that Muse Code can answer for you, and let's just try that. Give me a high level summary in about five to six bullets on
[21:11] what AgentKit has. This is something I do a lot, by the way. If I'm getting started with a new repository,
[21:28] I like to get a TLDR of the entire repository, get a sense of the overall architecture of how the code base is structured,
[21:36] and that gives me a sense of where I can dig further in. And I really like that it is able to give a summary,
[21:46] and be very succinct about what it is telling me. So here is what AgentKit contains. Tools is the folder that I mentioned, which is where you would want to
[21:57] extend it if you want to broaden the scope of your agent and the stuff it can do. So maybe the way I would do it is,
[22:05] if you take the RSS example, I would add one file for containing tools relating to RSS feeds. Maybe another one relating to emails,
[22:17] and have the agent figure out how to use both of those tools together to download RSS feeds and send that to me by email.
[22:27] Progress.py, this contains all of the primitives which enable the step through for the turns, and if the agent's execution pauses or fails
[22:42] before it completes its assignment, you can use Progress to resume. Case record contains all of the information related to
[22:54] recording evidence as the agent proceeds through its investigations. Document text contains some utilities for how to process documents. And
[23:09] client basically is the SDK, the OpenAI SDK that's pointed at our API. Our API is fully compatible with the OpenAI SDK, by the way.
[23:21] So, if you have an existing application that uses the OpenAI API, you can just switch the API host to
[23:30] Meta API. Right. Next question. Do we have time? I can take one more question, actually. Okay. Our agent is done. But yeah, I can take a couple of more questions, actually.
[23:47] One more question. Okay. Does Muse Code support custom MCP servers? I would say so, yes. You can have your Muse Code plugin to
[24:01] custom servers, custom skills. Yeah, you can. Okay. Let's carry on, and we can have more questions at the end.
[24:12] Okay. So, the agent that Muse Code built, or we built with Muse Code, has completed its run, and has done it in about 21
[24:22] runs. Let me just open the last run. So, so far it's got one user message, which was the assignment, the original assignment,
[24:36] 20 reasoning notes, one note per turn, 20 tool calls and 20 tool results, and five messages interspersed between that. So
[24:48] just before it wrote out our memo, this was its final observation. I'm not going to really read through it.
[24:59] And then it decided to call submit memo because I guess it realized, or it has concluded that it had enough information to file
[25:07] this memo, and that's what it did. You can see that the memo has been filed, but it is also unverified.
[25:17] And that's important because the output that you see over here is entirely AI-generated. And while it might be true, there's
[25:28] also the chance that it might have some inaccuracies, some misunderstandings, even some hallucinations. No model is immune to that. So we are
[25:41] required or obligated to implement some kind of guardrailing, some kind of defensive checks to ensure that what the model is putting out, or what
[25:53] we are using from the model's output, is actually correct. So that is something that we're going to take a look at in the next session
[26:02] tomorrow. And, yeah. I think it's pretty important. It's as important as building the agentic loop. Okay, so do we have a little bit more time at the end now for some extra
[26:16] questions? Yeah. I'm done with showcasing the agentic loop. I'm happy to take any questions on this. Okay, well, there are several questions that you already are
[26:30] probably going to, or Yash is going to cover in the next workshop, around hallucination and everything like that, and making decisions.
[26:40] But maybe you can talk a little bit about what we're going to learn in the next workshop, and I can ask some of those questions now.
[26:47] So one is, are there recommended patterns in Muse to prevent hallucinations and swallow coverage? So for example, should we be forcing a plan, execute, and
[27:04] verify loop, or using tool output grounding, or is there a built-in critic/reflection parameter to reduce revisions? I don't know if there is a built-in critic, but all the patterns or all
[27:22] the techniques that you mentioned right now are all very valid ways to do this. The models are very good at following
[27:31] instructions, so the more explicit you are in your prompt, the more likely that the result is going to be grounded in your source
[27:43] truth. So I don't want to share any spoilers for tomorrow's session, but there are ways to implement or to encourage your model to be
[27:56] more diligent about what it is reporting. Just having it source citations can enable it to autonomously identify if it has misrepresented
[28:16] hallucinations. In general, as an industry, I think all AI models have improved a lot from how they used to hallucinate even a year ago.
[28:29] Having harnesses, the right skills and the instructions, and even the tools to enable them to fact-check themselves has definitely helped in
[28:37] reducing the rate of hallucinations. But in my experience, the more niche a domain is and the more esoteric the
[28:48] area of work is, the likelihood of hallucinations or misrepresentations can slightly increase. So that's something to watch out for when you're building
[28:58] out your projects. Excellent. And what should we do if the agent did a milestone in the wrong direction? How can we get it back on track so we don't actually
[29:14] lose progress? Hmm. I guess just ask it to revert what it did. So if you think about it, your entire trace or your
[29:32] conversation with Muse Code is a persistent trace. The model is stateless, but because you're using a harness, there is
[29:44] some state because it's recording the conversation so far. So the model always receives the entire conversation so far, as you can even see over here.
[29:57] And so if you ask it to revert it, revert what it did or specify, maybe let's say, for example,
[30:05] "I didn't want you to use system instructions. I wanted you to use legal agent prompt.markdown." It's going to go back, figure out what
[30:19] needs to be changed, and then do another run to sort of basically revert what it did in favor of what you want it to do.
[30:31] So just ask it. That's my simple answer to that. All right, we're about at time, so thank you, everybody,
[30:42] for asking questions and being engaging. Of course, you can always ask questions in the office hours. We'll have office hours tomorrow in the office
[30:53] hours channel, and we'll have folks from the partner engineering team answering some of those questions. And we encourage you to use some of what you learned just
[31:05] as a tool or as a use case. You can also always follow along just for fun. Suraj, do you want to say any final words before we log off?
[31:18] No, just thanks everyone for participating. It's so cool to see, and I'm really excited to see all of the different projects that you guys are going to be building with
[31:29] our models. Just good luck for the hackathon. All right. Thanks, everybody. We'll send this recording in the Discord.
