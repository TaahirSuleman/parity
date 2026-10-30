# Meta AI tooling reference — Model API, Muse Code, open-weight models, cookbooks

Compiled 2026-10-27 from a full crawl of https://dev.meta.ai (≈130 doc pages incl. API reference, Help Center, cookbook, Muse Code, open-weight docs), the model landing pages, and the two cloned GitHub cookbooks (meta-models/meta-model-cookbook, meta-models/meta-oss-cookbook). Four parts: (A) core Model API synthesis, (B) cookbook / Muse Code / open-weight docs synthesis, (C) cookbook repositories synthesis, (D) model landing pages + secondary resources. Prose is faithful paraphrase; code, tables, IDs, prices and limits are verbatim.

---

# PART A — Core Model API (docs synthesis)

# Meta Model API (dev.meta.ai) — Dense Synthesis for Hackathon Builders

Crawled 2026-10-26/27 from https://dev.meta.ai via WebFetch. Base URL `https://api.meta.ai/v1`; auth `Authorization: Bearer $MODEL_API_KEY`; keys look like `LLM_<numericId>_<secret>`, created in the dashboard (https://dev.meta.ai/platform), shown once. Rate limits are **per team**, not per key. No Meta-specific SDK: use the OpenAI SDK (Responses/Chat Completions), the Anthropic SDK (Messages), or any OpenAI-compatible framework. SDKs do not auto-read `MODEL_API_KEY`; pass it explicitly.

---

## 1. Models

| Model | ID(s) | In → Out | Context | Status | Standard price (per 1M tok) | Contributor price | Rate limit (per team) |
|---|---|---|---|---|---|---|---|
| **Muse Wonder** | `muse-wonder-1.0` | text, image, video, audio, PDF → text | 1,048,576 tokens (output cap in agent configs: 131,072) | **Preview**; Standard mode only; **not available in South Korea**. "Muse Wonder Full" exists only inside Muse Code (Power/Maximum plans) | cached in $0.20 / in $4.00 / out $20.00 | n/a | 3,000 RPM / 4,000,000 TPM |
| **Muse Spark 1.3** | `muse-spark-1.3` | same | 1,048,576 | GA; recommended default; **audio input not fully supported (use 1.2)** | cached $0.15 / in $1.25 / out $4.25 | n/a (use contributor ID) | 3,000 RPM / 4M TPM |
| Muse Spark 1.3 Contributor | `muse-spark-1.3-contributor` | same | 1,048,576 | GA; content may train Meta models; **no `max` reasoning** | — | cached $0.002 / in $0.10 / out $0.20 (~12× cheaper) | **150 RPM** / 3,000,000 TPM |
| Muse Spark 1.2 | `muse-spark-1.2` | same (audio OK) | 1,048,576 | GA | same as 1.3 | — | 3,000 / 4M |
| Muse Spark 1.2 Contributor | `muse-spark-1.2-contributor` | same | 1,048,576 | GA | — | same as 1.3-contributor | 150 / 3M |
| Muse Spark 1.1 | `muse-spark-1.1` | same | 1,048,576 | Standard only; not in Muse Code | same | — | 3,000 / 4M |
| **Muse Image** | `muse-image-1.0` | text + image → image | — | GA | **$0.01 per successfully generated image** (flat; failed/safety-filtered not billed; built-in search included) | n/a | 150 RPM, no TPM |
| **Muse Voice Transcribe** | `muse-voice-transcribe-1.0` | audio → text transcript (no TTS) | — | GA | **$0.18 per hour** of audio, metered in whole seconds rounded down; streaming = file price; ZDR at parity | n/a | 256 concurrent streams; 16,000 streams/hour (shared realtime+file) |
| **SAM 3.1** | `sam-3.1` | text noun-phrase / box / point + image or video → boxes + masks (special-token text) | — | GA (open-weight lineage) | **$2.50 per 1,000 images; $0.20 per 1,000 video frames; min 50 frames billed per video request** | n/a | 3,000 RPM, no TPM |
| Muse Spark Open | (self-host / third-party) | text, image, video, audio → text | — | Open-weight; 816B MoE, 42B active; SGLang/vLLM/TensorRT-LLM/llama.cpp | — | — | — |
| Muse Glimmer | (self-host) | text + image → text | — | Open-weight, Apache 2.0, distilled from Spark; vLLM/SGLang/llama.cpp/ExecuTorch; local/edge | — | — | — |

Other pricing facts: **no long-context premium**; cached input = matching prefix; **web search grounding $2.50 per 1,000 queries** on top of tokens; reasoning tokens billed as output tokens; injected system scaffolding not billed; background responses capped at **600 new submissions/min/team**; `GET /v1/models` lists the hosted catalog (newest first) with only `id/object/created/owned_by` — no capability metadata. Knowledge cutoff dates are not published anywhere. Llama is **not** served on Model API.

**Choosing:** Wonder for long/complex multi-file, multi-hour agent tasks; Spark for high-volume, latency- or cost-sensitive work (subagents). Docs examples default to `muse-spark-1.3`; coding-agent/framework/computer-use guides use `muse-wonder-1.0`.

---

## 2. Capabilities

### 2.1 Tool calling (Muse Wonder, Muse Spark; all 3 protocols)
- Define `tools` (`function` type with name/description/JSON-Schema `parameters`; Responses uses flat objects, Chat Completions nests under `function`). Missing root `"type":"object"` is auto-added.
- **`custom` tools** (Responses only): freeform-text tools, fields `name/description/strict/defer_loading`, no `parameters`.
- Name rule `^[a-zA-Z0-9_.-]+$`, **at most one dot**; use a `namespace` tool for multi-segment MCP-style names (outer name 0 dots).
- **`tool_choice`: only `"auto"`** — `none`/`required`/named → 400. Must handle both tool call and plain text.
- **`parallel_tool_calls` default `true`** (model may emit several calls per turn; return one result per `call_id`). Set `false` to force one call/turn.
- **`max_tool_calls`** caps only built-in tools (web_search etc.), min 1.
- `strict` (default false) only validates schema against strict subset; generated args are never guaranteed valid — always parse/validate.
- `call_id` 1–64 chars; must match; with `previous_response_id` the server resolves IDs. Reserved names: `tool_search`, `browser.search/open/find` (when web_search present).
- Streaming: Chat Completions accumulate `tool_calls` deltas by `index`; Responses use `response.function_call_arguments.delta/.done`.
- Two built-in server-side tools can be combined with your functions: `web_search`, `tool_search`. Plus `computer` and `image_generation`.

### 2.2 Tool search (Responses + Messages; NOT Chat Completions)
- Add `{"type":"tool_search"}` and mark tools `defer_loading: true` (on functions **inside** a namespace, not on the namespace). Deferred tools expose name+description up front; schema is withheld until loaded; loaded definitions are **appended to end of context → cache prefix preserved**.
- **Hosted mode** (default): API searches declared deferred tools, emits `tool_search_call` (`execution: "server"`, `call_id: null`, `arguments.paths`) + `tool_search_output` (loaded defs) then a normal `function_call` with `namespace`.
- **Client-executed mode**: `execution: "client"` + your own `description`/`parameters`; model emits `tool_search_call` with a `call_id` and stops; you reply with `tool_search_output` echoing `call_id` and the tools to load (replay `*first.output`).
- Constraints: one `tool_search` per request; hosted needs ≥1 deferred tool; deferred tools need `tool_search`; keep namespaces <10 functions; **cannot combine with structured output in the same request**; not with `reasoning.effort: none`. On Messages → `server_tool_use` blocks. Changing loaded set later breaks cache.

### 2.3 Search grounding `web_search` (Responses + Messages; NOT Chat Completions)
- `tools: [{"type":"web_search"}]`; model decides whether to search (simple facts often skip). Output: `web_search_call` item + `message` with `url_citation` annotations `{url,title,start_index,end_index}`. `include: ["web_search_call.results"]` returns raw `{type:text_result,title,url,snippet}` hits.
- Params: `search_context_size` `low|medium|high`; `user_location` `{type:"approximate", country (ISO-2), region, city, timezone (IANA)}`. `allowed_domains/blocked_domains/max_uses` → 400 on Messages. Streaming events `response.web_search_call.in_progress/searching/completed`.
- Limitations stated: quality improving, incomplete coverage, best for focused single-fact/recent-event queries; break multi-hop into narrower requests. $2.50/1k queries. Muse Image has its own built-in search (no `web_search` tool).

### 2.4 Image understanding (Wonder, Spark; all protocols)
- Supply via public URL, base64 `data:` URL, or Files API `file_id`. Only in `user` messages. Up to **50 images/request** (PDF pages count); inline 50 MB each, Files API 1 GiB; MIME jpeg/jpg/png/gif/webp/x-icon; no `detail` knob documented (schema has `detail` auto/low/high/original). ~3 tokens for 1×1, ~1,300–1,500 tokens for ~1280px; ~110 token overhead.
- **Perception grounding (differentiator):** model returns coordinates on a **normalized 0–1000 grid** (0,0 top-left). Three prompt modes: **Point** `{x,y}`, **Box** `{bbox:[{x_min,y_min,x_max,y_max}]}` ("You are an object grounding expert" boosts recall), **Count** `{points:[...],count}` (point-then-count handles occlusion). Clamp values (may hit 1001). Divide by 10 → CSS percentages for HTML overlays. Pair with structured output.

### 2.5 Video & audio understanding (Spark/Wonder; Responses + Chat Completions; Messages has `video` block with `fps`)
- Video: `input_video` (`video_url` or `file_id`) or `input_file` (`file_id`); Chat Completions `video_url` part. **Model reads embedded audio too** → one call gives description + transcript. MP4 only. No duration/fps limits documented (schema has `fps`).
- Audio: `input_audio` `{data base64, format: wav|mp3}` (or `audio_url`/`file_id`). **Use `muse-spark-1.2`** for audio; set `max_output_tokens ≥ 4000`; stream or lower reasoning for long clips.

### 2.6 Image generation — Muse Image (Responses or `/v1/images/*`)
- Responses: `input` text and/or `input_image` parts; output `reasoning` (summary of lookups) + `message` + one `image_generation_call` per image (`result` base64). Multi-turn refinement via `previous_response_id` (store default true) or replaying `image_generation_call` with `store:false`.
- `image_generation` tool fields: `enable_image_search/enable_web_search/enable_shell` (all default **true** — model can search web/images and run code for layouts/charts before rendering), `reasoning_strength` `high|low`, `size` "WxH" (aspect ratio only, ≤16:1), `output_format` webp|png|jpeg.
- `/v1/images/generations` (OpenAI-compatible): `n` 1–10, `response_format` b64_json|url, `output_format`, `reasoning_strength`, `tool_enablement` (via `extra_body`), `stream` (single `image_generation.completed` event). `/v1/images/edits`: multipart `image` (list for composition) or JSON `images[]` of `{image_url|file_id}` (1–10). No `mask`, `seed`, `quality`; `moderation` → 400.

### 2.7 Speech to text — Muse Voice Transcribe
- **Realtime** `wss://api.meta.ai/v1/asr/realtime?sessionId=`: first JSON frame = handshake `{authorization:{accessToken:"Bearer …"}, audioEncoding: PCM_24KHZ|PCM_16KHZ, model, mode, partialMode, emitAudioProgress, languageBias[], keywords[]}` within 10 s; server replies `{sessionId}`; stream raw s16le mono PCM binary frames at real time (≤5 s ahead; 80 ms frames in examples); send `{"type":"endStream"}`; read until close 1000. Session max 60 min (close 1011 "Max session duration reached"); 1008 bad config/pacing; 1013 rate-limited.
- **File** `POST /v1/asr/transcribe` multipart (`request` JSON + `audio` WAV mono 16-bit 16/24 kHz; ≤32 MB, ≤10 min). `Accept`: json (default, `{sessionId, transcript, audioDurationMs, turns[{turnId,startMs,endMs,transcript,speaker}]}`), `text/event-stream`, `text/plain` (`A:Hello` lines); else 406.
- Modes: `PUSH_TO_TALK` (default; completion = `transcript.final:true`), `ENDPOINTING` (turn detection; events `speechStart/transcript/speechEnd/speechComplete` keyed by `turnId`; final text only in `speechComplete`), `DIARIZATION` (adds `speaker` events with session-scoped labels A/B…; not tuned for low-latency commands).
- `partialMode` CUMULATIVE (replace) | DELTA (append). 25 evaluated languages with code-switching; `keywords` vocabulary biasing. **Turn-level timestamps only** — no word timestamps, confidences, emotion, or TTS.

### 2.8 Media segmentation — SAM 3.1 (see §6)

### 2.9 File handling / Files API
- Inline (`file_data` base64 or `file_url` http/https) ≤50 MB; `POST /v1/files` (`purpose=user_data`, optional `expires_after{anchor:created_at, seconds 3600–2592000}`) ≤1 GiB; **100 GiB per-team storage** (400 when full; files never expire by default). MIME: images, mp4, mp3/wav, pdf, txt/json/jsonl (`purpose=batch`).
- **PDF**: text from first **100 pages**, images from first **50 pages** (count against 50-image budget).
- Reference via `input_file{file_id|file_url|file_data+filename}`, `input_image{file_id}`, `input_video{file_id}`; Chat Completions `file{file_data|file_id, filename}`; Messages `document` block. List (`limit` ≤10,000, `order`, `after` cursor, `purpose`), retrieve, content, delete.

### 2.10 Reasoning (Wonder, Spark — always-on reasoning models)
- Effort: `none` (**unsupported → 400**), `minimal`, `low`, `medium`, `high`, `xhigh`, `max` (Wonder 1.0 and Spark 1.3 only; not Spark-contributor). Default when omitted is model-determined (quickstart echo shows `high`). Param: Responses `reasoning.effort`; Chat Completions `reasoning_effort`; Messages `thinking:{type:"adaptive"}` + `output_config.effort` low|medium|high|xhigh|max.
- Reasoning tokens count toward `max_output_tokens`/`max_tokens` (min 16 on Responses) and are billed as output; reported in `output_tokens_details.reasoning_tokens` / `completion_tokens_details.reasoning_tokens`. Raw reasoning is never exposed as text; **no logprobs** anywhere.
- **Cross-turn reasoning**: Responses via `previous_response_id` (server state) or stateless replay with `include:["reasoning.encrypted_content"]` + `store:false` (cannot combine with `previous_response_id`). Replayed `reasoning` items need `summary:[]` and must precede an assistant message/`function_call` before the next user turn; dropped turns lose chain-of-thought; `truncation:"auto"` is off by default (400 unless enabled per account) → compact at whole-turn level and verify with `/v1/responses/input_tokens`. Chat Completions **cannot** carry reasoning (`reasoning_content` redacted). Messages carries it via `redacted_thinking` replay.
- Summaries (Responses only): `reasoning.summary` `auto|concise|detailed`, streamed as `response.reasoning_summary_text.delta/done`; may be empty. Assistant `phase: "commentary"` tags pre-tool preambles; must be preserved on replay.

### 2.11 Structured output
- Chat Completions `response_format:{type:"json_schema", json_schema:{name, schema, strict?}}`; Responses `text.format:{type:"json_schema", name, schema, strict?}`; Messages `output_config.format:{type:"json_schema", schema}`. Also `json_object`. Constrained decoding (not post-processing). OpenAI SDK `beta.chat.completions.parse(response_format=PydanticModel)` works.
- Limits (also apply to tool `parameters`): depth 10; 5,000 properties; 120,000 total string chars; 1,000 enum values (single enum >250 values capped at 15,000 chars); 200,000 expanded nodes; **no recursive/`$ref`-cycle schemas**. `strict` default false everywhere; strict subset = object root, no root anyOf/oneOf/allOf/enum/not, no allOf/oneOf anywhere, `additionalProperties:false`, all props `required`. **Not combinable with `tool_search`** in one request.

### 2.12 Prompt caching (automatic)
- Prefix-based KV caching on every request, no flags. Put stable content first (system/developer prompt, tool definitions, few-shot), volatile last. Read `usage.input_tokens_details.cached_tokens` (Responses) / `prompt_tokens_details.cached_tokens` (CC) / `cache_read_input_tokens` (Messages). Cached-input rates: Spark $0.15, Wonder $0.20, Spark-contributor $0.002 per 1M.
- `prompt_cache_key` (stable app/use-case string; replaces deprecated `user`) routes similar requests together; `prompt_cache_retention` `in_memory` (default) | `24h` (hint). `store:false` does not disable caching. With `previous_response_id`, usage shows only the new turn.

### 2.13 Token counting
- `POST /v1/responses/input_tokens` (same body as create; returns `{object:"response.input_tokens", input_tokens}`; includes resolved history, tools, media, injected scaffolding; model-specific; no billing recorded). `POST /v1/messages/count_tokens` for Anthropic format. `usage.input_tokens` with hosted tools is cumulative across iterations — don't use it for context occupancy. Streamed CC needs `stream_options:{include_usage:true}`; Responses always includes usage.

### 2.14 Other request-level facts
- Sampling: tuned for `temperature 1.0`, `top_p 1.0` (Messages clamps temp to 0–1); adjust one, not both; `seed` best-effort. `frequency/presence_penalty` −2..2. `n>1`, `stop`, `logit_bias`, `prediction`, `verbosity`, `modalities`, `audio` output → 400/no effect.
- `safety_identifier` (≤64 chars hashed end-user ID; Messages `metadata.user_id`).
- Non-streaming requests have a server time limit → **504 `gateway_timeout`**; stream or use `background:true` (Responses only; `status:"queued"`; poll `GET /v1/responses/{id}`, `?stream=true` for lifecycle tail, `POST …/cancel`; body ≤1 MiB; not with `stream`).
- Status endpoint `GET /v1/status`; status page https://dev.meta.ai/status. Error envelope `{error:{message,type,param,code}}`; retry 429/500/503/504-transient with jitter, honor `Retry-After`; headers `x-ratelimit-{limit,remaining}-{tokens,requests}`.

---

## 3. Protocols & SDK compatibility

| | **Responses** `POST /v1/responses` | **Chat Completions** `POST /v1/chat/completions` | **Messages** `POST /v1/messages` |
|---|---|---|---|
| Wire format | OpenAI Responses | OpenAI Chat | **Anthropic Messages** (adapter over Responses pipeline) |
| SDK | OpenAI SDK, base `https://api.meta.ai/v1`; Vercel `@ai-sdk/openai`; LiteLLM (`openai/` prefix); LangChain; LlamaIndex | Same + `@ai-sdk/openai-compatible` | **Anthropic SDK** with `base_url="https://api.meta.ai"` (no `/v1`) and `auth_token=`; `ANTHROPIC_AUTH_TOKEN` env (not `ANTHROPIC_API_KEY`); `x-api-key` and `anthropic-version` headers also accepted |
| Reasoning across turns | ✓ | ✗ | ✓ (`redacted_thinking`) |
| Server state | `store` (default true), `previous_response_id`, background | none | none (always store off) |
| web_search / tool_search | ✓ / ✓ | ✗ / ✗ | ✓ / ✓ (`server_tool_use`) |
| computer tool, image gen, SAM | ✓ | ✗ | ✗ |
| Structured output | `text.format` | `response_format` | `output_config.format` |
| tool_choice | auto only | auto only | auto/any/none (+`disable_parallel_tool_use`) |
| Media | input_text/image/file/video/audio | text/image_url/input_audio/file/video_url | text/image/video(fps)/document |
| Unsupported | stop, logit_bias, n>1, logprobs | same + web_search_options, modalities | stop_sequences, top_k, container, inference_geo, thinking.disabled, named tool |

So: **OpenAI-compatible: yes (two surfaces). Anthropic-compatible: yes (Messages).** Tools that work out of the box: OpenAI SDK (Py/TS), Anthropic SDK, LangChain, LlamaIndex, Vercel AI SDK, LiteLLM, Claude Code, Claude Agent SDK, OpenAI Codex CLI/app-server, OpenCode, Goose/Roo-style self-configuring agents, Hermes (Nous), Muse Code (first-party).

---

## 4. Tool calling + tool search + parallel calls — details for agent builders
- Responses loop: send `tools` → get `function_call{name,arguments,call_id,status}` items → execute → reply with `function_call_output{call_id,output}` either via `previous_response_id` (send only new items) or by replaying full history (`*prev.output` + outputs; order preserved; reasoning items with `encrypted_content` if `include` requested). Multiple `function_call`s in one turn are the norm (`parallel_tool_calls:true`).
- Chat Completions loop: assistant message with `tool_calls[]` (`finish_reason:"tool_calls"`) → append that full assistant message → append one `tool` message per `tool_call_id` → resend.
- Messages loop: `tool_use` blocks → `tool_result` blocks keyed by `tool_use_id`; built-in calls come back as `server_tool_use`.
- Namespaces: `{type:"namespace", name, description, tools:[…]}` — grouping for MCP/Agents-SDK style multi-dot names and for tool search; mix deferred and non-deferred.
- Large tool libraries: defer with `defer_loading:true` + `tool_search` — saves input tokens and keeps cache prefix; hosted vs client-executed search; client mode lets you gate tools by tenant/project state.
- Budgeting: `max_tool_calls` (built-ins only), `parallel_tool_calls:false`, cap turns in your loop; `max_output_tokens` includes reasoning.
- Validation is strict: full assistant message must be replayed; `call_id` matching; commentary-phase tagging before tool calls; otherwise 400.

---

## 5. Structured output / reasoning / caching specifics (quick card)
- Guaranteed-shape JSON: `strict:true` + `additionalProperties:false` + all required; ≤10 levels; no recursion. Use on the turn *after* tool search. Pydantic parse helper works. Schema guarantees shape, **not facts** (cookbook warns to verify numbers).
- Reasoning: pick lowest effort that works; `max` for accuracy-critical (Wonder/Spark 1.3 only); summaries `auto`; stateless encrypted replay is the recommended multi-turn pattern; cannot pair `include: reasoning.encrypted_content` with `previous_response_id`.
- Caching: automatic; order prompt stable→volatile; `prompt_cache_key` per app; `prompt_cache_retention:"24h"` for bursty traffic; tool search appends loaded tools after the cached prefix; monitor `cached_tokens` ratio.

---

## 6. SAM 3.1 (`sam-3.1`) — segmentation via Responses API
- **Inputs**: one user message with `input_text` + `input_image{image_url}` or `input_video{video_url|file_id}`. Video MP4/MOV (H.264/H.265/MPEG-4; no VP9/WebM), up to **15,000 frames (~10 min)**. Upload via Files API (`purpose user_data`); MP4s auto-remuxed for faststart.
- **Prompt types**: (a) **concept = short noun phrase**, one concept per request ("yellow school bus"; lists/negation/spatial/boolean unreliable; returns every instance in images); (b) **box/point prompts** using the same token grammar: `<Nf>id<|box;x1;y1;x2;y2;w;h|>` and `<|point;x;y;w;h|>` with leading `-` for negative points; ≤16 objects; multiple frames `<30f>…<120f>…`; `w/h` must match media aspect ratio. Helpers `buildObjectPrompt` / `build_object_prompt`. Cannot mix phrase and object prompts. No exemplar prompts.
- **Video tracking**: `metadata.propagation_direction` `both` (default; forward then backward) | `forward` | `backward`; stable object ids across frames (while in frame); up to 16 tracked objects/frame; results keyed by explicit `<Nf>` marker (frames may skip/arrive out of order).
- **Outputs**: streamed `response.output_text.delta`, one line per image/frame: `<Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..[;c=..]|><|mask;x=0;y=0[;c=..];data=H,W,<~|!>base85|>,…`. Boxes in **source pixels** (not normalized); masks as base85 raster payloads, `~` lossless (default) or `!` one_bit (`metadata.mask_encoding:"one_bit"`, several× smaller); `metadata.include_confidence:"true"` adds `c` 0–1 per record. Empty `output_text` = no matches (valid). `usage.images_processed` / `usage.video_frames_processed` report billing.
- **Client libs**: `@meta-sam/parser` (TS, zero deps) / `meta-sam-parser` (Py ≥3.10): `parseImageStream/parseVideoStream` → snapshots + `finalResult`; `recordsOfKind(records,"box"|"mask")`; `decodeMaskToRaster` (Uint8Array 0/1), `decodeMaskToRLE` (COCO), `decodeMaskToSVGPath`; `@meta-sam/graphics` `SegmentationRenderer` (Canvas overlays, `hiddenIds`), `@meta-sam/video` `createMediaPlayer` (frame-accurate), `@meta-sam/react` `<Video>` / `useMediaPlayer`.
- **Pairing**: Muse Spark decides *what* to segment (scene understanding / 0–1000 grounding boxes → convert to pixels) and SAM 3.1 produces pixel masks; Voice Transcribe diarization + SAM "people" tracking → per-speaker captions (cookbook).

---

## 7. Agent frameworks & computer use
- **Documented frameworks page covers only two**: **Claude Agent SDK** (`npm i @anthropic-ai/claude-agent-sdk` / `pip install claude-agent-sdk`; env `ANTHROPIC_BASE_URL=https://api.meta.ai`, `ANTHROPIC_AUTH_TOKEN=$MODEL_API_KEY`, `ANTHROPIC_MODEL`/`_DEFAULT_OPUS_MODEL`→`muse-wonder-1.0`, `_DEFAULT_SONNET_MODEL`/`_DEFAULT_HAIKU_MODEL`/`CLAUDE_CODE_SUBAGENT_MODEL`→`muse-spark-1.3`; `allowedTools`, `permissionMode:"bypassPermissions"` only in sandbox, `settingSources:[]`) and **OpenAI Codex app-server** (JSON-RPC over stdio; `-c model_providers.meta.{base_url,env_key=MODEL_API_KEY,wire_api="responses",requires_openai_auth=false}`; **must supply `model_catalog_json` file** because `/v1/models` lacks the shape Codex expects; `approvalPolicy:"never"`, `sandbox:"workspace-write"`; opt out of delta notifications; act on `turn/completed`).
- **Coding agents page**: Muse Code (first-party terminal/CI agent, `curl -fsSL https://dev.meta.ai/install.sh | sh`, then `muse`), OpenCode (`@ai-sdk/openai` Responses adapter recommended: PDFs + encrypted reasoning replay; `@ai-sdk/openai-compatible` fallback loses both), Codex CLI (`~/.codex/config.toml`, `wire_api="responses"`, `model_auto_compact_token_limit=900000`), Claude Code (env vars above, `ENABLE_TOOL_SEARCH=true` for MCP). Goose/Roo mentioned as self-configuring. LangGraph, CrewAI, OpenAI Agents SDK, AutoGen, Pydantic AI, Mastra, Google ADK are **not documented** (but anything OpenAI-compatible works; SDKs page names LangChain, LlamaIndex, Vercel AI SDK, LiteLLM; cookbook uses Hermes by Nous Research).
- **Production patterns** (from docs): wait for terminal event, wall-clock cap + idle watchdog, per-run sandbox with scrubbed env, allowlist tools/MCP servers, meter cost from final `usage`, retry dropped streams/502s.
- **Computer use** (Responses only; `muse-wonder-1.0`, or `muse-spark-1.3` for cheap long runs): tool `{"type":"computer"}` (no config). Model returns one `computer_call` per turn with a **batch** of actions (`click{button,x,y}`, `double_click`, `drag{path}`, `keypress{keys}`, `move`, `scroll{x,y,scroll_x,scroll_y}`, `type{text}`, `screenshot`, `wait`); you execute in order and return `computer_call_output{call_id, acknowledged_safety_checks[], output:{type:"computer_screenshot", image_url:data-URL}}`. **Pixel coordinates** of the last screenshot (not 0–1000); keep screenshot size constant; PNG/JPEG ≤25 MiB. `pending_safety_checks` must be echoed in `acknowledged_safety_checks` to proceed. State: `previous_response_id` (default) or stateless replay copying `meta_safety_replay_receipt` unchanged (≤29 call/output pairs). `truncation:"auto"` trims old screenshots but must be enabled per account. Drivers: Playwright/Puppeteer (browser), pyautogui (desktop), sandboxed VMs. Alternative: code-execution function tool (`run_python`/`run_browser_script`) for predictable flows. Ends with a plain assistant message; `status:"incomplete"` on token cap.

---

## 8. Rate limits, credits, hackathon notes
- Limits per team per model: Wonder/Spark 3,000 RPM & 4M TPM; contributor variants 150 RPM & 3M TPM; SAM 3,000 RPM; Image 150 RPM; Voice 256 concurrent / 16k streams/hr; background 600/min. Headers `x-ratelimit-*` on token endpoints only. 429 → backoff (start ~500 ms, double, jitter, 3–5 tries). Playground usage counts against the same limits. Higher limits: dashboard Limits page / support.
- **Free credits / trial / hackathon-specific notes: none documented** anywhere on dev.meta.ai docs or Help Center. Billing is pay-as-you-go, no minimums; charged when balance hits a payment threshold (which rises with successful payments) and on the 1st monthly; spend-limit alerts exist. Contributor mode (`-contributor` IDs) is the cheap path (~$0.10/$0.20 per 1M) at the cost of training consent and 150 RPM; forbidden with ZDR; don't send personal data on it.
- Availability: "most countries where Meta AI is available and billing is supported" (Geographic Use Policy); Muse Wonder excluded in South Korea. Users must be 18+. ZDR available on request (sales form) but disables stateful requests, background, file uploads, web search, contributor mode.
- Dashboard Playground has **Compare** (same prompt across models) and **Get code** tabs — useful for demos.

---

## 9. Differentiators a judge would see as "creative use beyond basic integration"
1. **Perception grounding on a 1M-context VLM**: 0–1000 normalized point/box/count prompts → pixel-accurate overlays, counting under occlusion, chart/screenshot extraction — then hand the boxes to **SAM 3.1 box/point prompts** for true masks (VLM decides *what*, SAM delivers *pixels*). Documented combo.
2. **SAM 3.1 video tracking with direction control** (`propagation_direction`, multi-frame prompts, stable ids, confidence, one_bit masks) + `@meta-sam/*` for live Canvas/React overlays; cookbook shows animated sticker packs and head-locked speech bubbles by fusing **Voice Transcribe diarization** with SAM people tracks.
3. **Tool search with deferred namespaces (hosted or client-executed)** — scale to hundreds of MCP tools without blowing the prompt or the cache; client-executed mode gates tools per tenant. Pair with **prompt caching** (`prompt_cache_key`, `24h` retention) and **stateless encrypted reasoning replay** for cheap, auditable, resumable agent loops.
4. **Background mode + streaming retrieval + cancel** for long-horizon Muse Wonder jobs (`max` reasoning, 1M context, no long-context premium), with `input_tokens` preflight and whole-turn compaction.
5. **Search-grounded image generation** (Muse Image automatically web/image-searches and runs code for layouts/charts; $0.01 flat) and multi-turn edits via `previous_response_id`.
6. **Computer-use agent with safety-check acknowledgement loop** (`pending_safety_checks` → human-in-the-loop) on Wonder, or the documented code-execution alternative; cookbook has desktop/macOS recipes and a "voice → chess CUA" demo (Voice Transcribe realtime driving a computer-use agent).
7. **Realtime ASR with endpointing/diarization + keyword biasing** as the front end of a voice agent, feeding Responses tool loops; `text/plain` `A:` transcripts for instant meeting intelligence.
8. **Multi-agent orchestration** with a shared Kanban board (PM/backend/frontend/GTM profiles, auditable comment trail, rework loops) — directly matches "productionised multi-agent orchestration" framing; plus Muse-Code-style guardrails (staged approvals, immutable guardrails, deterministic replay in CI, subagent fan-out in git worktrees, audit/resume from event logs).
9. **Three wire formats on one key** — e.g., run Claude Code/Claude Agent SDK subagents on Messages and Codex/OpenCode on Responses against the same models, or a local **Muse Glimmer** agent that escalates to hosted Spark only after user approval (cookbook "local agent that asks first").
10. **Cost discipline knobs** judges can measure: contributor variants, cached-prefix ratios, `reasoning_effort` tiers, `max_tool_calls`, Spark for subagents / Wonder for the main loop, `safety_identifier` for per-user policy, ZDR for sensitive data.

---

## Pages that failed or were only partially extractable
- None returned HTTP errors. All requested URLs resolved. Limitations: the WebFetch extractor summarizes prose (it refuses verbatim transcription beyond code/tables), so prose sections are detailed paraphrases while code blocks and tables are verbatim where the extractor cooperated.
- **Partial**: `/docs/api-reference/responses/schemas` (156 KB) — the extractor never surfaced the `WebSearchTool`, `ToolSearchTool`, `NamespaceTool`, `CustomTool`, `ImageGenerationTool`, `ToolChoiceParam`, `UrlCitationBody`, `TypeParam`/`WaitParam`, `TokenCountsResource` definitions across three offset windows; their fields are captured from the capability pages instead. `/docs/speech-to-text`: close-code table lives on the realtime reference page (captured there); ffmpeg command reconstructed from description. `/docs/api-reference/voice/realtime`: Python example summarized (equivalent microphone script captured verbatim from the feature page). `/docs/api-reference/files/upload-file`, `/images/edit-image`, `/voice/transcribe`: code summarized by the extractor (equivalent verbatim code captured from feature pages). Group index pages (`/api-reference/{responses,chat-completions,messages,files,images,voice,models}`) are thin navigation pages; substance was pulled from their sub-pages.
- Thin by nature: `/help` (index only), `/help/about-model-api/knowledge-cutoff` (no dates), `/help/policies-and-privacy/data-handling` (points to legal center), `/help/accounts-and-login/supported-countries` (points to Geographic Use Policy).

---

# PART B — Cookbook docs, Muse Code, open-weight models (docs synthesis)

# Meta Model API / Muse platform — extended docs synthesis

Crawled 2026-10-26 from https://dev.meta.ai via WebFetch. Scope: full Cookbook (all 9 categories, 54 recipes), all 11 Muse Code pages, all 16 open-weight pages (Muse Spark Open + Muse Glimmer), plus 8 supplementary platform pages (models, pricing, agent-frameworks, coding-agents, tool-search, file-handling, sdks, Responses protocol) needed to make the synthesis actionable. Per-page notes are in this directory as `<path-with-underscores>.md`. Cookbook sources: https://github.com/meta-models/meta-model-cookbook (hosted API) and https://github.com/meta-models/meta-oss-cookbook (open weights).

Zero pages failed to fetch. Caveat: WebFetch's extractor condenses rather than copies verbatim, so code blocks are described, not reproduced; every command, flag, model ID, limit, price and URL that the extractor surfaced is preserved in the per-page files. The Muse Code changelog (~146K chars) was captured as a per-version summary without dates.

---

## 0. Platform facts you need before reading anything else

**Endpoint and auth.** Base URL `https://api.meta.ai/v1` (OpenAI-compatible: Responses `/v1/responses`, Chat Completions, Files `/v1/files`, Models `/v1/models`; Anthropic-compatible Messages at `https://api.meta.ai` + `/v1/messages`). Key in env var `MODEL_API_KEY`; no SDK reads it automatically, pass it explicitly. Voice: `wss://api.meta.ai/v1/asr/realtime` and `https://api.meta.ai/v1/asr/transcribe`.

**Hosted models (model IDs).**
| ID | Role | Context | Notes |
|---|---|---|---|
| `muse-wonder-1.0` | Most capable (preview); long multi-hour agent runs | 1,048,576 | $4 in / $20 out / $0.20 cached per 1M; RPM 3,000 / TPM 4M |
| `muse-spark-1.3` | Recommended default; agentic + coding; text/image/video/PDF in (audio not fully supported) | 1,048,576 | $1.25 in / $4.25 out / $0.15 cached; RPM 3,000 / TPM 4M |
| `muse-spark-1.3-contributor` | Same model, Meta may train on your data | 1,048,576 | $0.10 in / $0.20 out / $0.002 cached; RPM 150 / TPM 3M |
| `muse-spark-1.2` (+ `-contributor`) | Previous; recommended for audio input | 1,048,576 | same prices as 1.3 |
| `muse-image-1.0` | Image generation + editing, agentic (web search, code before render) | n/a | $0.01 per image flat; RPM 150 |
| `muse-voice-transcribe-1.0` | Real-time STT, diarization, endpointing, keyword biasing, 25 languages | n/a | $0.18/hour; 256 concurrent streams, 16,000 streams/hour |
| `sam-3.1` | Open-vocabulary segmentation + video tracking from a noun phrase | n/a | $2.50/1,000 images; $0.20/1,000 frames (50-frame min); RPM 3,000 |
Web search grounding: +$2.50 per 1,000 queries. Rate limits are per team, not per key. Background responses: 600 submissions/min/team.

**Reasoning.** All Muse Spark/Wonder calls reason before answering; `reasoning_effort` ∈ {minimal, low, medium, high, xhigh} (`none` rejected on Muse Spark; `xhigh` == `high` on the hosted API). Reasoning tokens bill as output (`usage.completion_tokens_details.reasoning_tokens`). Only the Responses API preserves reasoning across turns (encrypted `reasoning` items via `store:false` + `include:["reasoning.encrypted_content"]`, or `previous_response_id`).

**API quirks (all return HTTP 400).** `tool_choice` only `"auto"`; no `stop`, `logit_bias`, `logprobs`, `n>1`, `verbosity`; no recursive JSON schemas; structured output is `response_format` on Chat Completions but `text.format` on Responses; `truncation:"auto"` rejected (compact client-side; measure with `POST /v1/responses/input_tokens`); `web_search` and `tool_search` are Responses/Messages only, not Chat Completions; images only in `user` messages; input+output must fit the 1,048,576 window.

**Files.** Inline 50 MB; Files API 1 GiB (`purpose=user_data`); 100 GiB per team; PDF text from first 100 pages, images from first 50; ~50 images/request; MP4 video includes embedded-audio transcription; `expires_after` 1h–30d.

**Tool search** (Responses/Messages): `{"type":"tool_search"}` + `defer_loading:true` on tools; hosted mode or client-executed mode (`execution:"client"`) for tenant-dependent tool inventories.

---

## 1. Cookbook catalogue (54 recipes) with patterns demonstrated

Legend for patterns: **LOOP** agent loop, **TOOL** tool use, **MULTI** multi-agent, **ORCH** orchestration/dispatch, **HANDOFF** inter-agent handoff/messaging, **MEM** memory/state, **EVAL** evaluation/verification harness, **GUARD** guardrails/approval/sandbox, **OBS** observability/audit, **RAG** retrieval/grounding, **VISION** multimodal perception, **HITL** human-in-the-loop, **SCHED** scheduling, **STRUCT** structured output.

### 1.1 API fundamentals (10) — Python notebooks, `muse-spark-1.3`, OpenAI SDK
1. **Quickstart: chat completions** — first call; `developer` role beats `system`; temperature default 1.0 is best; stateless history; 1M window; retry 429/5xx not 400; watch `x-ratelimit-remaining-*`. [TOOL-free baseline]
2. **Streaming responses** — `stream=True`; final chunk `delta.content=None`; `stream_options={"include_usage":True}`; retries restart the stream.
3. **Tool and function calling** — detect `finish_reason=="tool_calls"`, append assistant msg then one `tool` msg per `tool_call_id`, loop until no tool calls, cap `max_turns`; only `tool_choice="auto"`. [LOOP, TOOL]
4. **Structured output** — `response_format: json_schema` with `additionalProperties:false`, `required`, `enum`; Pydantic via `client.beta.chat.completions.parse()`; recursive schemas 400. [STRUCT]
5. **Prompt caching** — automatic longest-prefix match; stable content first; `prompt_cache_key`, `prompt_cache_retention: "24h"`; monitor `usage.prompt_tokens_details.cached_tokens`.
6. **Reasoning and thinking tokens** — effort levels; reasoning billed as output; Responses `reasoning` item with `encrypted_content`; `previous_response_id` for multi-turn. [MEM]
7. **Vision input** — `image_url` parts (URL or base64); up to ~50 images/request, 50 MB inline, 1 GiB via Files; token cost scales with resolution; count via `/v1/responses/input_tokens`. [VISION]
8. **Long context** — 1,048,576 shared input+output; measure first; sliding window or summarization; no server truncation. [MEM]
9. **Error handling and retry** — typed exceptions, backoff+jitter, rate-limit headers, circuit breaker. [production hardening]
10. **Search grounding** — `tools=[{"type":"web_search"}]` on Responses; `url_citation` annotations with `start_index/end_index`; `search_context_size` low/medium/high; footnote rendering. [RAG]

### 1.2 Agent patterns (5) — OpenCode harness unless noted
11. **Basic agent loop** — perceive→decide→act with pytest as the "done" oracle; 5 planted bugs, 5/5 fixed, avg 7.6 turns; doom-loop detection by hashing `(tool_name,args)` and stopping after 3 repeats. [LOOP, TOOL, EVAL]
12. **Interleaved reasoning and tool use** — reasoning→tool→result→reasoning stream; `--variant minimal|high|max`; callback→async migration in 5 escalating steps; `minimal` can be slower than `high` (15 turns/1,500 tokens vs 12/817). [LOOP, TOOL]
13. **Multi-turn context management** — `STATE.md` running state (goal, decisions, task graph, file map), selective re-retrieval, emergent subagent delegation; 301 calls, peak 54% of 1M window, no compaction. [MEM, MULTI]
14. **Search-and-replace edits** — exact-match-once edit tool; zero matches = hallucination, multi = ambiguity; lint/compile after every edit. [TOOL design, EVAL]
15. **Alert fatigue copilot** — Python CLI or OpenCode; 42 synthetic SRE alerts → probe JSON (patterns, refined purpose, signals) → grounded chat → self-assessment written to state files; schema validator + pytest; loop ends on schema pass or guard. [LOOP, STRUCT, MEM, EVAL (self-assess), OBS use case]

### 1.3 Use cases (14)
16. **Chart analysis** (OpenClaw) — explain-only rule ("Explain, do not advise"); structured JSON (instrument, timeframe, trend, keyLevels, pctChangeVisible, notableEvents, unreadable); every number verified against gridlines; visual rendered by a deterministic generator so the visual can't invent data; `AGENTS.md` rules. [VISION, STRUCT, GUARD, EVAL]
17. **Error screenshot fix** (OpenCode) — screenshot → Plan agent diagnoses/asks scope → Build agent fixes; cal.com monorepo pinned commit; 9/9 tests + tsc. [VISION, MULTI (plan/build split), EVAL]
18. **Smart glasses with OpenClaw** — VisionClaw iOS app → OpenClaw gateway (port 18789, token auth, OpenAI-compatible endpoint) targeting agent `openclaw/default`; thin client holds no keys; Ray-Ban Meta via Wearables Device Access Toolkit. [VISION, thin-client/gateway architecture]
19. **Generating slides** (Python, Responses API) — research (3–5 web searches) → JSON outline → reveal.js HTML; `*_slides_stats.json` metrics (queries, tokens, timing, sources). [RAG, STRUCT, pipeline, OBS]
20. **Browser-verified web design** (OpenCode + Playwright MCP `@playwright/mcp`) — agent builds site, opens at 1280x800, screenshots, fixes visual bugs. [TOOL/MCP, EVAL (self-verify)]
21. **Iterative game dev** (OpenCode + Playwright MCP) — Three.js racing game; fetch Kenney CC0 assets first; play-test with console + screenshots; 4 refinement passes. [EVAL, iterative loop]
22. **Sandboxed execution** (Python, Docker) — SWE-bench task in throwaway container; tools `run` + `write_file`; `pred.patch` graded by official SWE-bench grader (`resolved 1/1`); 129 s sample. [GUARD (sandbox), LOOP, EVAL (benchmark)]
23. **Multi-agent orchestration** (Hermes) — PM/backend/frontend/gtm profiles with `SOUL.md`; PM has only `clarify` tool (can't code); Kanban tasks with `parent_id` dependencies dispatched by gateway; `needs_input` blocking; comment/event trail in `~/.hermes/kanban.db`; rework loop; `TESTING.md`. [MULTI, ORCH, HITL, OBS, least-privilege]
24. **One-shot game dev** (OpenCode, `xhigh`) — invisible-bug rules in `AGENTS.md` + prompt with role/stack/assets/mechanics/deliverable/acceptance criteria; no retry loop. [constraint engineering, EVAL criteria]
25. **Perception grounding** (Python, Responses) — fridge photo → self-contained HTML with pixel-anchored dots, health score, hover nutrition. [VISION grounding]
26. **GitHub agent** (OpenCode + GitHub Actions) — 7 agents: `triage`, `review`, `qa` (citations), `rfc`, `bugfix` (only writer), `stale` (weekly cron), `repo-agent` (orchestrator for `/oc`); `opencode.json` provider `model_api` via `@ai-sdk/openai-compatible`; secret `MODEL_API_KEY`; issue/PR text treated as data; CODEOWNERS on `.github/workflows/*` and `.opencode/*`; 4-phase rollout. [MULTI, ORCH, GUARD, HITL gates, SCHED, event-driven automation]
27. **Computer use** (OpenCode + Cua Docker sandbox, `cua_local_mcp.py` stdio MCP) — screenshot→act→screenshot loop; Minesweeper. [TOOL/MCP, VISION, GUARD]
28. **Computer use on macOS** (`metacua`, Swift/Python) — Responses API with `parallel_tool_calls:false`, `store:false`; tools `computer.computer`, `computer.stop`; 0–1000 normalized coords; no sandbox (safety warnings). [VISION, native automation]
29. **Local agent that asks first** (Hermes + Muse Glimmer local + Muse Spark cloud) — `consult_remote_model` tool gated by approval showing exact outbound bytes; `egress.jsonl` ledger stores digest/bytes/model/duration but never content; approvals scoped to text digest; `fallback_providers` empty; WhatsApp approvals optional. [hybrid local/cloud routing, HITL, GUARD, OBS (privacy-preserving audit)]

### 1.4 Building with Muse Code (10) — `muse` CLI, "durable, auditable agents"
30. **Audit and resume agent sessions** — append-only `session.jsonl`; proposal→review→decision→intent→run→result; `decision_source` (static policy / `llm_judge`); `muse export` byte-deterministic (hashable), `--redacted`; `muse resume` flags in-flight effect as unknown, idempotency keys prevent duplicate side effects. [OBS, EVAL, GUARD]
31. **Deterministic replay in CI** — golden fixture (`schema_version:1`, `agent.run` records, `expected_model_context`); `muse trace inspect`; `replay_gate.sh` + GitHub Actions required check; offline, no model calls; check JSON `diffs` count (exit code is always 0). [EVAL harness, regression testing]
32. **Staged approvals** — compound shell split into stages; dangerous list (`rm -f`, `rm -rf`, incl. under `sudo`/`setsid`); `--approval-mode untrusted`; trust scopes persisted to `approval-policy.json` (never for `python|bash|sh|node|sudo|git`); `trust.json`; `jq` over `requested`/`decision_applied` events. [GUARD, HITL, OBS]
33. **Contained execution** — Seatbelt/bubblewrap sandbox; live enforcement probe (fail-closed if OS isn't enforcing); 3 boundary tests (write to `$HOME`, write to `.git/`, network egress) all denied and logged; `--disable-approval --trust-workspace` for unattended runs. [GUARD]
34. **Immutable guardrails** — `.agents/AGENTS.md` and `.muse/` protected by (a) mediated-write review with allow-once-only and (b) read-only sandbox paths (`.git .muse .agents .sl .hg .eden`, `.envrc`, shell rc files). [GUARD, self-modification prevention]
35. **Subagent fanout** — `--subagent-worktree-isolation`; parent spawn/status/steer/cancel/wait; 6 parallel subagents on "Bastion Breaker" scored by one test suite; host-dependent concurrency with queueing. [MULTI, ORCH, EVAL]
36. **Goal tracking** — `/goal` with a checkable oracle; step probe after ~10 calls without progress; completion audit gates `update_goal`; `perigord_gateway` HMAC migration with 6 acceptance tests. [EVAL, drift control, MEM]
37. **Bundled skills** — `/plan` (grounded plan, stops for approval), `/grilling` (one decision-forcing question at a time), `/grill-with-docs` (writes `docs/DECISIONS.md`), `/taste` (anti-AI-look UI checklist); skills loaded via `read_skill` from `SKILL.md`. [procedural memory, HITL elicitation]
38. **Loop and cron** — `/loop` natural language → cron (`0 8 * * *`); jitter ≤30 min; 7-day expiry; one catch-up; session-scoped; needs Muse Code running. [SCHED]
39. **Side chats** — `/side` (`/btw`) read-only branch; main thread never sees it; no subagents/workflows inside. [context isolation]

### 1.5 Muse Image (4) — `muse-image-1.0`, Responses API, `.webp` output
40. **Generate, edit, and compose** — `image_generation_call` item; chain with `previous_response_id`; `input_image` parts in a `user` message; `store=False` + replay item for stateless. 41. **Search-grounded image generation** — product visualization from web search; three chained turns. [RAG] 42. **Anchored image series** — reference anchors (character sheets, background plates) → 6 panels → compose → letter; consistency across series. 43. **Edit image details across turns** — price tags on resale photo; remove sold item; strike-through price; "specify what must stay unchanged".

### 1.6 Muse Voice Transcribe (2) — `muse-voice-transcribe-1.0`
44. **Speech to text** — WebSocket PCM 16/24 kHz streaming (cumulative partials, `final:true`), modes `PUSH_TO_TALK` / `ENDPOINTING` / `DIARIZATION` (events `speechStart`→partials→`speaker`→`speechEnd`→`speechComplete`, correlate by `turnId`); one-shot HTTP ≤10 min / 32 MB; `keywords`, `languageBias`; close codes 1008/1011/1013; 60-min session cap. 45. **Control Apple Chess with voice** — deterministic grammar parser, Accessibility-validated board, dry-run, fail-closed native input, HUD. [VISION/voice + GUARD]

### 1.7 SAM (3) — `sam-3.1`
46. **SAM API basics** — one noun phrase per request; image as data URL or video via Files (`purpose=user_data`); stream + `meta_sam_parser`/`@meta-sam/parser`; `summary.json`, `mask-*.svg`. 47. **Video to animated stickers** — longest-lived track → APNG → 512x512 WebP stickers (<500 KB), WhatsApp `contents.json`. 48. **Multi-speaker headlocked captions** — Voice diarization ∥ SAM `people` tracks → human matches voice to person in `@meta-sam/react` → `@meta-sam/graphics` collision-aware bubbles → FFmpeg MP4. [multimodal fusion, parallel calls, HITL]

### 1.8 Run locally / Post-training (3) — open weights
49. **Muse Spark Open on Mac** — 2× (512 GB) or 4× (256 GB) M5 Ultra Mac Studios, Thunderbolt 5 RDMA, `mlx.launch --backend jaccl … mlx_lm.server --model meta-models/Muse-Spark-Open-816B-A42B-NVFP4 --port 8080`. 50. **RL with TorchTitan** — GRPO/DAPO; 256 trainer + 16 generator GPUs; swap in Sample/Dataset/Env/Reward (`Rubric`); `python -m torchtitan.rl.train --module rl --config muse_spark_dapo_math`. 51. **SFT with TorchTitan** — full-parameter text/image/audio SFT; 128 GPUs (DP16×TP8×EP32); JSONL `messages`; loss only on assistant tokens; expected held-out losses listed.

(Category index pages themselves: 52–54 `run-locally`, `post-training`, and the top-level cookbook index.)

---

## 2. Muse Code — what it is and how to use it inside a product

**What.** Meta's first-party coding agent for terminal and CI, built on Muse Spark (default model `muse-spark-1.2`; `/models` or `--model` to switch; Muse Wonder on subscription plans). Native `muse` binary. Two independent safety layers on by default: **approval** (stage-by-stage shell review, LLM auto-reviewer profile) and **OS sandbox** (Seatbelt / bubblewrap / Windows sandbox; `.git .muse .agents` read-only; `--sandbox-network proxy-only|restricted|unrestricted`).

**Install.** `curl -fsSL https://dev.meta.ai/install.sh | sh` (macOS/Linux) or `irm https://dev.meta.ai/install.ps1 | iex` (Windows); `muse --version`; `cd project && muse`; `/login` or `META_API_KEY` env var / `muse auth set`; `muse logout`. Billing: PAYG tokens or 4 flat subscription tiers (Everyday/High/Power/Maximum = 1×/5×/20×/80×; subscriptions default to Contributor mode, toggle via `/settings` or `--contributor-mode` / `MUSE_CONTRIBUTOR_MODE`); `muse usage` shows allowance.

**Headless / CI / automation.**
- `muse exec "<prompt>"` (or `--prompt-file`) runs one prompt to completion; `--json` emits JSONL events with token usage/allowance; `--output-schema` for typed output; `--max-model-steps` caps work; `--disable-request-user-input`, `--disable-reminders` for unattended runs; `--session-id <uuid>` resumes non-interactively.
- Exit codes: 0 completed, 1 failed/cancelled, 2 usage error, 130/143 signals (reflect termination, not correctness).
- Approval postures: `--disable-approval` (sandbox stays), `--disable-sandbox`, `--yolo` (both off; disposable containers only; `AGENTS.md` in a checkout is attacker-controlled). Linux CI needs bubblewrap + non-musl build.
- `-c key=value` one-run config overrides; `MUSE_TRANSPORT_TRACE=1` raw provider traffic to stderr.

**Programmatic embedding (SDK / session protocol).** `muse serve` exposes a versioned JSON session protocol (`muse schema` prints it); keeps up to 256 sessions loaded; `--preset` (incl. `empty` = no built-in tools); runs its own LLM reviewer and can default to Auto-review. TypeScript SDK `npm install @muse-code/sdk`, Python SDK on PyPI (docs: https://meta-models.github.io/muse-code-sdk). Protocol methods/events seen in changelog: `session/resume` (with `permissionProfile`), `session/leave` (hand a session to another host), approval-reviewing events, skill listing/invocation, plugin install + marketplace management, hook/plugin catalogs, interim narration items, live status + usage reporting, multiple workspace roots, per-process provider/model selection, clients can answer agent questions. This is the path for wrapping Muse Code as an engine inside a product rather than shelling out to `muse exec`.

**Session messaging** (macOS/Linux, interactive sessions only): peer sessions named via `/name` (3–32 chars, lowercase, `all/self/current` reserved); `muse -w` gives each writer its own worktree; delivery modes steer-now / queue-next-turn / notify-only, wake-idle; recipient approval with 30-min expiry; messages are untrusted data (cannot approve tools or change config); 8,192-byte plain text; off for `--no-session-log`. Workflows (staged/parallel child agents, up to 1,000 child calls, ≤16 active, JS workflow scripts saved via `muse workflows save <name> --from <file> --scope project` into `.agents/workflows/`, `muse workflows recover <run-id> --session <id> --apply`, `/workflows` control room) are rollout-gated and absent on the public `aarch64-apple-darwin` build.

**Extensibility.**
- **Hooks**: shell command bound to one of 17 lifecycle events (`PreToolUse`, `PostToolUse`, `PostToolBatch`, `PreLLMCall`, `Stop`, `StopFailure`, `SessionEnd`, …) from `<project>/.muse/hooks.json`, user settings, or `managed_hooks_path`; run outside sandbox/approval; `onFailure` fallback.
- **Skills**: `<repo>/.agents/skills/<id>/SKILL.md`; `muse skills list|inspect|enable|install|validate|import` (imports Claude/Codex skills); built-ins `/plan /grill /grilling /grill-with-docs /taste /threejs /migrate /blender` + visual-coding/browser-game/web3d.
- **MCP**: `mcp_servers` block (`stdio` or `streamable_http`), `mode: required|optional`, `${VAR}` interpolation, `MUSE_SESSION_ID` passed, wildcard toolsets, OAuth 2.1 `muse mcp login <server>`; MCP tools are not sandboxed. Plugins can ship MCP servers with per-server review.
- **Subagents**: default 8 concurrent per tree (`agents.execution_capacity` 1–64); worktree isolation never silently skipped; four background observers (memory recall, skill recall, goal tracking, verification) feeding a reconciler.
- **Memory**: Markdown with `MEMORY.md` index; scopes personal-project (default), project (`.agents/memory/`, committed, loads even untrusted — prompt-injection risk), personal; up to 48 files indexed at start.
- **Instructions**: `AGENTS.md` → `CLAUDE.md` → `.agents/AGENTS.md` → `.claude/CLAUDE.md` per directory up to `.git`; `muse init` scaffolds; project rules need workspace trust.
- **Config**: `~/.config/muse/settings.json` (`schema_version:1`), `permissions.default_profile` (Auto-review / Ask me / Unrestricted / Read-only), `session_retention_days`, `ca_bundle`, `network.local_ports`, `muse config validate|status` for enterprise.
- **Interactive**: `/goal`, `/loop` (cron), `/side`, `/compact`, `/recap`, `/export transcript|trajectory`, `/rewind` (branching with Exact/Review-required/Blocked labels), `/fork`, `/resume --last`, `/tasks`, `/subagents`, `/stop`, `/hud`, voice `Alt+V`, `/voice status`.

---

## 3. Open-weight models

| | Muse Spark Open | Muse Glimmer |
|---|---|---|
| Size | 816B MoE, 42B active, 62 layers (46 sliding-window 2,048 + 16 full attention), 256 routed experts | 30B dense, GQA 2 KV heads, SWA on 3 of 4 layers, built-in vision encoder (distilled from Muse Spark) |
| Modalities | text/image/audio/video → text | text/image → text |
| Context | 1,048,576 | 128K default, longer supported |
| License | **Muse Model License + Acceptable Use Policy** (HF: `meta-models/Muse-Spark-Open-816B-A42B/blob/main/LICENSE.md`, `USE_POLICY.md`) | **Apache 2.0** |
| HF repos | `meta-models/Muse-Spark-Open-816B-A42B` (BF16, ~1.65 TB, 65 shards), `…-NVFP4` (~537 GB, 127 shards); AMD `amd/…-Quark-MXFP4`, `amd/…-Quark-PTPC-FP8`; Intel `intel-ai/…-INT4`; `ggml-org/Muse-Spark-Open-816B-A42B-GGUF` (Q4_K_S/Q8_0/Q2_K); Unsloth `UD-Q2_K_XL` | `meta-models/Muse-Glimmer-30B` (bf16 ~60 GB), `…-GGUF` (Q4_K_M 16.8 GB, Q4_K_XL 19.7 GB, `mmproj` 1.4 GB, `dflash` draft 1.6 GB), `…-assistant` (DFlash draft), `…-ExecuTorch-PTE` (16 exports) |
| Hardware | NVFP4: 4× B300/GB300 (TP4/EP4, FP8 KV); BF16: 8× B300 (TP8/EP8), ~2 TB VRAM budget; AMD 8× MI355X/MI350X; Intel Xeon 6 6980P CPU (INT4, TP2); Apple 2×512 GB or 4×256 GB M5 Ultra Mac Studios over Thunderbolt 5 RDMA; Unsloth GGUF ~300 GB (2-bit)–950 GB (8-bit) | bf16 ~72 GB VRAM (one B300: 85.8 tok/s single, ~2,094 tok/s at 256 concurrent); Q4_K_M + projector + 131K ctx = **19.0 GiB** (fits 24 GB card); Intel Arc Pro B70 ×2 (TP2); Xeon 6 CPU-only; Ollama/LM Studio/Unsloth desktop |
| Runtimes | SGLang (`lmsysorg/sglang:dev-muse-spark-open`, port 30000, DFlash2 draft, HiCache, PD-disaggregation), vLLM (`vllm/vllm-openai:muse-spark-open` / `-rocm`, port 8000, DSpark spec-decode), TensorRT-LLM (`feat/musespark-open` branch), NVIDIA Dynamo, Transformers ≥5.19, llama.cpp, Unsloth, MLX | vLLM (`vllm/vllm-openai:muse-glimmer`, parsers `muse_glimmer`), SGLang (bf16/GGUF/NVFP4/MLX), llama.cpp ≥ b10353, ExecuTorch (CUDA/MLX AOT), Transformers ≥5.15, Ollama ≥0.32.7 (`ollama run muse-glimmer`, port 11434), LM Studio (`lms server start`, 1234), Unsloth Studio (8888) |
| Hosted providers | Together `meta-models/muse-spark-open` (`api.together.xyz/v1`), Fireworks `accounts/fireworks/models/muse-spark-open`, **Baseten** `meta-models/muse-spark-open` (`inference.baseten.co/v1`), Groq (org approval), Nebius Token Factory, **Modal**, OpenRouter; catalogs: SageMaker, Google Model Garden, Microsoft Foundry | Together `meta-models/Muse-Glimmer-30B`; partners Fireworks, OpenRouter, Hugging Face |
| Prompting | Chat template `<|start|>role … <|message|> … <|eot|>`; `<|eom|>` between tool calls (never a stop token); `reasoning_effort` low=8/medium=32/high=256/xhigh=512 (default), cannot be off; `Reasoning strength: N` in system prompt overrides; parallel tool calls OK; OpenAI tool format; parsers `--reasoning-parser muse --tool-call-parser muse`; sampling T=1.0, top_p=1.0; stop on `<|eot|>`(200008)/`<|end_of_text|>`(200001) | Same framing tokens; recipients `to=user|self|<tool>`; `reasoning_strength` default `high`; `reasoning_content` replay; **one tool call per turn**; native ATEM format parsed to `tool_calls`; `AutoProcessor` + `<|image|>` for images; sampling T=1.0, top_p=0.95, top_k=64; greedy decoding loops |
| Spec decoding | DFlash2 (SGLang), DSpark draft (vLLM, 7 spec tokens on AMD) | DFlash block-diffusion draft: llama.cpp `-md … --spec-type draft-dflash`, SGLang `--speculative-algorithm DFLASH`, ExecuTorch `export_dflash` |
| Post-training | TorchTitan (SFT LoRA r8 131K ctx on 16 GB300; full SFT text/image/audio 128 GPUs; RL DAPO 256+16 GPUs), Miles (GRPO, 64 H200, `--vlm` Geometry3K), NeMo AutoModel, Megatron Bridge, TRL (LoRA r16, 64 H100, 14.2 s/step, 194 MB adapter); hosted: **Together Post-Training** (SFT, GRPO), **Fireworks** serverless LoRA (SFT/DPO/ORPO/distill/RL, rank ≤64, 262K seq) | Axolotl (QLoRA 1×H100 ~27 GB; bf16 LoRA FSDP2; full FSDP2 8×H100 ~97 GB), TRL SFT (LoRA r8–32, α=2r, LR 1e-4–3e-4, keep reasoning traces in targets), TitanRL GRPO (8×H100, "data-analyst" CSV→`answer.json` tiered reward 1.0/0.25/0.15/0.05/−0.05, reward 0.21→0.98 in 15 steps, ~75 min), TRL DPO (β≈0.1, LR 5e-7) / GRPO (`num_generations` 4–16, LR 1e-6) |

---

## 4. Recipes that map to business-process automation, document processing, orchestration, evaluation, observability

**Business-process / ops automation.**
- *Alert fatigue copilot* (#15): the closest thing to a "noisy operational feed → structured triage → grounded Q&A → self-assessment" template; strict JSON per turn, state files as memory, validator + pytest as harness. Directly reusable for ticket queues, claims, incidents, compliance alerts.
- *GitHub agent* (#26): production-shaped event-driven multi-agent system with an orchestrator, read-only specialists, exactly one writer, human gates (`/oc`, `agent-fix` label), weekly cron, injection defense and CODEOWNERS hardening. Swap GitHub events for webhooks from any system of record.
- *Loop and cron* (#38) + *Goal tracking* (#36): recurring digest generation and objective-gated completion inside Muse Code.
- *Local agent that asks first* (#29): approval-gated egress with a content-free ledger; the pattern for regulated data (PII/PHI) where cloud calls must be explicitly consented and auditable.

**Document / multimodal processing.**
- Files API (PDF 100 pages text / 50 page images, 1 GiB, MP4 with audio transcription) + *Vision input* (#7) + *Structured output* (#4) + *Chart analysis* (#16: "every number is a claim to verify", render separately from reasoning) + *Perception grounding* (#25: pixel-anchored annotations) + *Search grounding* (#10: inline citations) + *Speech to text* (#44: diarized call/meeting transcripts) + *SAM* (#46–48: object tracking in video).
- *Generating slides* (#19): research→outline→artifact pipeline with a stats sidecar.

**Multi-agent orchestration.**
- *Multi-agent orchestration* (#23): Kanban-dispatched role agents with dependency graph, least-privilege toolsets, `needs_input` escalation, SQLite audit trail — the reference design for "digital team" automation.
- *Subagent fanout* (#35) and Muse Code *Workflows* (staged/parallel with synthesis, worktree isolation, 1,000-child budget).
- *Multi-turn context management* (#13): `STATE.md` + selective retrieval + delegation for long runs.
- *Session messaging*: peer agents coordinating on one machine with trust boundaries.

**Evaluation harnesses.**
- *Deterministic replay in CI* (#31): golden fixtures replayed offline as a merge gate (no model calls) — an agent regression suite.
- *Goal tracking* (#36), *Basic agent loop* (#11), *Sandboxed execution* (#22, SWE-bench grader), *Subagent fanout* (#35): tests/oracles as the completion signal, scoring across parallel agents.
- *Alert fatigue* self-assessment, *Chart analysis* numeric verification, *Browser-verified* and *Iterative game dev* (agent self-verifies via Playwright/console).

**Observability / audit.**
- *Audit and resume* (#30): append-only `session.jsonl`, intent-before-effect, `decision_source` incl. `llm_judge`, byte-deterministic hashable `muse export`, idempotent resume.
- *Staged approvals* (#32) and *Contained execution* (#33): every denial logged; `jq` over `requested`/`decision_applied`.
- Hooks (`PreToolUse`/`PostToolUse`/`PreLLMCall`/…) as a telemetry tap; `muse exec --json` JSONL stream; `*_stats.json` in slides; `egress.jsonl` ledger.

---

## 5. What would count as creative / deep use of Meta's tooling in a judged hackathon

1. **Muse Code as an embedded orchestration engine, not just a CLI.** Drive `muse serve` through `@muse-code/sdk` (or the Python SDK) from your product backend: spawn per-case sessions, inject domain skills (`SKILL.md`), hooks that push every `PreToolUse`/`PostToolUse` event into your own observability store, MCP servers exposing your system-of-record, and `session/leave` to hand sessions between workers. Almost nobody will do this; the docs explicitly position it ("Muse Code can be driven from your own program through a versioned session protocol").
2. **Auditable, replayable agent runs as the product.** Combine `session.jsonl` intent-before-effect logging, `muse export` (hashable, `--redacted`), and *deterministic replay* golden fixtures to ship a compliance story: every automated decision has an authorizer (`decision_source`), is reproducible, and regressions are caught in CI without model calls. Pair with the *immutable guardrails* and *staged approvals* layers for a least-privilege narrative.
3. **Hybrid edge/cloud routing with consent.** Run Muse Glimmer (Apache 2.0, 19 GiB on a 24 GB GPU, or Ollama/LM Studio on a laptop) for first-pass extraction/classification (`reasoning_strength: low`), escalate only hard cases to `muse-spark-1.3`/`muse-wonder-1.0` through an approval-gated `consult_remote_model`-style tool with a content-free egress ledger. Cost + privacy + capability story in one architecture; uses both the open-weight and hosted halves of the platform.
4. **Multimodal fusion that only Meta's catalogue makes cheap.** SAM 3.1 video tracking ($0.20/1k frames) ∥ Voice Transcribe diarization ($0.18/h) ∥ Muse Spark video+PDF understanding, fused the way *headlocked captions* does (parallel calls, human-in-the-loop matching). E.g., safety/compliance review of site-inspection video, call-center QA with speaker attribution, retail shelf audits with pixel-grounded overlays (#25).
5. **Reasoning-continuity and cost engineering.** Use the Responses API stateless encrypted replay (`store:false`, `include:["reasoning.encrypted_content"]`) so reasoning survives across tool loops; **tool search** with `defer_loading` and namespaces (client-executed mode for per-tenant tool inventories) to keep a huge tool surface off the prompt and the cache prefix stable; prompt caching with `prompt_cache_key` / `24h` retention; `reasoning_effort` tiered per step (low for extraction, high for synthesis); `background:true` for long jobs (600/min/team). Report `cached_tokens` and `reasoning_tokens` on a dashboard.
6. **Evaluation-first agent design.** Make the acceptance oracle explicit (tests, schema validators, SWE-bench-style graders, `Rubric`-weighted rewards) and gate completion on it (`/goal` + completion audit; `update_goal` only when criteria pass). Then close the loop with **post-training**: use TitanRL GRPO on Muse Glimmer with a verifiable reward (the docs' own "data-analyst CSV → `answer.json`" tiered reward is a template for business-data tasks; 8×H100, ~75 min) or Fireworks/Together hosted LoRA on Muse Spark Open. Showing a fine-tuned open model beating the base on your task metric is a distinctive artifact.
7. **Kanban-dispatched role agents with least privilege** (Hermes pattern, #23): PM-only `clarify`, exactly one writer, dependency-released tasks, `needs_input` escalation, every decision a comment. Re-implement on top of Muse Code subagents/workflows or the Agent SDK/Codex app-server (both documented against `api.meta.ai`) and you have a defensible "digital operations team" rather than a chatbot.
8. **Guardrail stack as a demoable feature.** Live-probed sandbox (fail-closed), stage-by-stage shell review with persisted argv-prefix trust rules, interpreter prefixes never auto-allowed, protected rule paths, peer messages that cannot grant permissions, `AGENTS.md` treated as attacker-controlled. Judges reward agents that visibly cannot hurt the host.
9. **Image generation that is grounded and consistent**: `muse-image-1.0` with web-search grounding and anchored series (#41–42) for generated marketing/catalogue assets at $0.01/image, chained via `previous_response_id`; combine with structured outputs for a content pipeline.
10. **Smart-glasses / voice front ends** (#18, #44–45): thin client → gateway → agent; the gateway owns model choice, skills and safety; hands-free field workflows (inspections, warehouse picking) with diarized voice notes.

### Practical defaults for a hackathon build
- Model: `muse-spark-1.3` everywhere (`muse-wonder-1.0` only for the top-level planner); `-contributor` variants cut cost ~12× but RPM drops to 150 and data is used for training.
- API: Responses API (`/v1/responses`) with OpenAI SDK; `store:false` + encrypted reasoning replay; `text.format` JSON schema with `additionalProperties:false`; `tools=[{"type":"web_search"}]` when grounding is needed; measure with `/v1/responses/input_tokens`.
- Agent harness options documented against the API: Muse Code (`muse exec --json`, `muse serve` + SDK), OpenCode (`@ai-sdk/openai` adapter for reasoning continuity + PDFs), Codex app-server (JSON-RPC), Claude Agent SDK (Messages API with `ANTHROPIC_AUTH_TOKEN`), Hermes, OpenClaw.
- Local: Muse Glimmer Q4_K_M via `llama serve -hf meta-models/Muse-Glimmer-30B-GGUF --hf-file Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` or `ollama run muse-glimmer`; never stop on `<|eom|>`; `top_p 0.95 top_k 64`.

---

# PART C — Cookbook repositories (cloned source synthesis)

# Meta Cookbooks Synthesis: `meta-model-cookbook` + `meta-oss-cookbook`

Factual synthesis drawn from the two cloned cookbook repos (model cookbook at HEAD `0a99b98`, MIT license). Everything below comes from the READMEs, notebooks, and source files in those trees.

## 0. Orientation: the API and model surface

| Item | Value (as stated in the repos) |
|---|---|
| Hosted API base URL | `https://api.meta.ai/v1` — OpenAI-compatible; the root README also claims Anthropic-SDK and OpenCode/Claude Code compatibility |
| Auth | `MODEL_API_KEY` env var, format `LLM|{numeric_id}|{secret}`; passed explicitly to the OpenAI SDK, or `Authorization: Bearer` on raw HTTP |
| Hosted model IDs | `muse-spark-1.3` (text/image/video/PDF in, text out, 1,048,576-token window, reasoning model); `muse-image-1.0` (Responses API, image out); `muse-voice-transcribe-1.0` (WebSocket + HTTP ASR, 25 languages); `sam-3.1` (Responses API segmentation); `muse-spark-1.3-contributor` (used by the Muse Code security recipe) |
| Open-weight models | **Muse Spark Open** `meta-models/Muse-Spark-Open-816B-A42B` (BF16 ~1.65 TB) and `-NVFP4` (~537 GB); **Muse Glimmer** `meta-models/Muse-Glimmer-30B` (bf16 ~60 GB) and `-GGUF` (Q4 ~17–20 GB) |
| Harnesses | OpenAI Python SDK (notebooks); OpenCode (`opencode -m meta/muse-spark-1.3`); OpenClaw (gateway + Canvas); Hermes (profiles + Kanban); Muse Code (`muse` CLI); `metacua` (native macOS computer-use, Swift+Python); Cua (throwaway Linux desktop); Playwright MCP |
| Rate limits mentioned | preview free tier ~2,400 requests/min, 800,000 tokens/min per team; `x-ratelimit-remaining-*` headers |

A recurring convention across recipes: invented domain terms (Quokkascale, Frobnitz-9, Zorptic, Glimber, Kestrel/Falcon) so a correct answer can only come from files the agent actually read — itself a reusable anti-memorization evaluation trick.

---

## 1. Catalogue

### 1.1 `meta-model-cookbook` — `01_api_fundamentals/` (10 notebooks, OpenAI SDK, `muse-spark-1.3`)

| # | Notebook | Builds / demonstrates | Notable |
|---|---|---|---|
| 01 | `01_chat_completions` | First chat call; `developer` role as highest-precedence instruction; `temperature` default 1.0; statelessness (a follow-up without history fails); a backoff+jitter retry wrapper. | Prefer `developer` over `system`; `system` is applied at developer level and does not override the model's own system prompt. `stop`, `logit_bias`, `n>1`, `verbosity` → HTTP 400. |
| 02 | `02_streaming` | `stream=True`; guard empty `choices` and `delta.content is None`; `stream_options={"include_usage":True}` for a final usage chunk. | Reasoning precedes the first visible delta (pause, not hang). Keep partial text on timeout. |
| 03 | `03_tool_calling` | Function tools; `finish_reason=="tool_calls"`; append the assistant `tool_calls` message then one `tool` message per `tool_call_id` (skipping the assistant message → 400); bounded loop. | Parallel tool calls arrive in one turn. `tool_choice` supports only `"auto"`; others → 400. `web_search` is Responses-only. |
| 04 | `04_structured_output` | `response_format={"type":"json_schema",...}` constrained decoding; `client.beta.chat.completions.parse(response_format=PydanticModel)` → `message.parsed`. | `additionalProperties:false`+`required`+`enum`; recursive `$ref` → 400; on Responses API the field is `text.format`. |
| 05 | `05_prompt_caching` | Automatic prefix caching; `usage.prompt_tokens_details.cached_tokens`; optional stable `prompt_cache_key`; `prompt_cache_retention` `"in_memory"`/`"24h"`. | Volatile content before the stable prefix defeats the cache; don't over-partition keys. |
| 06 | `06_reasoning_tokens` | `reasoning_effort` ∈ `none<minimal<low<medium<high` (`xhigh`=`high`); `completion_tokens_details.reasoning_tokens` are billed output tokens; Responses `include=["reasoning.encrypted_content"]`, `store=False`; `previous_response_id`. | `reasoning_content` empty on Chat today; Responses reasoning item is encrypted; default effort "still being finalized". |
| 07 | `07_vision_input` | `image_url` part (URL or base64) in a `user` message only (developer/system+image → 400); multi-image (~50/req); `POST /v1/responses/input_tokens` to pre-count (Responses shape `input_text`/`input_image`). | Formats jpeg/jpg/png/gif/webp/x-icon; 50 MB inline, 1 GiB via Files API. |
| 08 | `08_long_context` | 1,048,576-token window shared by input+output; measurement endpoint; full-file vs summary; sliding-window `trim_history`. | No server-side truncation; over-window → 400 with token counts. |
| 09 | `09_error_handling` | OpenAI error envelope (branch on `type`+`status_code`, `code` often null); retry table (429/5xx/timeout yes; 400/401/404 no); `with_raw_response` for `x-ratelimit-*`; a `CircuitBreaker` class. | Reusable resilience primitives. |
| 10 | `10_search_grounding` | Responses `tools=[{"type":"web_search"}]` + `search_context_size`; output list interleaves `reasoning`/`web_search_call`/`message`; `url_citation` annotations (`start_index`/`end_index`/`url`/`title`); back-to-front footnote rendering + URL dedup; streaming via `responses.stream()` reading `get_final_response()`. | Search is model-decided; no-citation `message` is a valid ungrounded answer. |

### 1.2 `02_agent_patterns/`

- **01 agent_loop_basics** — OpenCode fixes five planted bugs in `agent-loop-target/` (Python + Go mirror), `pytest` as oracle. Loop RECEIVE→READ→THINK→ACT→OBSERVE→EVALUATE with guards (max iterations, token budget, stuck detection = hash `(tool_name,args)`, stop after 3 repeats, user interrupt). Result: 5/5 fixed, avg 7.6 turns.
- **02 interleaved_reasoning** — Migrates a callback Express+TS API to async/await in dependency order; effort knob `--variant minimal/high/max`; a too-low budget costs more turns end-to-end (15 vs 12 on task 2).
- **03 managing_context** — Builds a TS reverse-proxy/load-balancer (`proxy_build/`, 58 vitest tests) then three injected requirement changes; prompted `STATE.md` working memory + re-read-before-edit; emergent subagent delegation. ~301 agent calls, peak context ~54% of 1M, no compaction. Verbatim prompts in `prompt.md`.
- **04 validated_in_place_edits** — Six real edits on `facebookresearch/segment-anything` with exact OpenCode `edit`/`write` payloads; search/replace must match exactly once; `py_compile`+`flake8` oracle.
- **05 alert_fatigue_copilot** — Probe→chat→self-assess over 42 synthetic SRE alerts; strict JSON; stdlib validator + pytest (detail in §3).

### 1.3 `03_use_cases/` (15 recipes)

- **01 chart-explainer** — OpenClaw agent reads a chart PNG (vision), writes `analysis.json`, execs a deterministic `render-summary.py` → HTML card on OpenClaw Canvas. Teaches "multimodal in, text out; a tool renders the visual"; explain-only guardrail (no financial advice); schema guarantees shape not facts, so a verify step checks every number.
- **02 screenshot_bugfix** — OpenCode + `muse-spark-1.3` vision reads two bug screenshots of the cal.com monorepo, localizes components via i18n keys, chooses minimal vs global fix via OpenCode Plan agent's `question` tool, applies in Build agent, runs `tsc`/tests/biome. Shows pixels→root-cause and a default-flip opt-out.
- **03 visionclaw** — Thin iOS app (Swift) on Ray-Ban Meta glasses (Meta Wearables Device Access Toolkit) → one chat turn (text+image) to an OpenClaw gateway serving `meta/muse-spark-1.3`; on-device `SFSpeechRecognizer`/`AVSpeechSynthesizer`. The app holds no key or tools; the gateway is the brain.
- **04 doc_generation** — `research_to_slides.py`: Responses `web_search` (`search_context_size:"high"`) research → JSON outline (normalized for key variance) → streamed reveal.js HTML; writes `*_stats.json` (searches, token usage, citations). Example run: 5 searches, 116,677 tokens, 12 slides.
- **05 web_design** — OpenCode + Playwright browser MCP builds a CRT-terminal site, then the agent screenshots its own render and fixes visual bugs (vision self-check), then a styled refinement pass. "An agent with eyes" loop.
- **06 iterative_game_dev** — Same build→browser-playtest→refine loop for a 3D Three.js solar-system racer; agent fetches CC0 Kenney assets, reads console, dispatches held keydown/keyup to drive, finds visual-only bugs (ACES tone-mapping washing colors).
- **07 sandbox_execution** — `sandbox_scaffold.py` gives `muse-spark-1.3` two tools (`run`, `write_file`) that act only inside a throwaway Docker container holding a SWE-bench instance (`psf/requests-6028`); reproduce→fix→verify loop; writes `pred.patch`; `grade.py` runs the official SWE-bench harness in a fresh container (`resolved 1/1`). Raw-urllib Chat Completions call with `tools`+`tool_choice:"auto"`.
- **08 multi_agent_orchestration** — Hermes four-profile product studio (detail in §3).
- **09 one-shot-game_dev** — One `AGENTS.md` (coordinate system, position-based collision, log drift, train spawn order, Kenney asset load) + one structured prompt at `reasoning_effort=xhigh` builds a complete Crossy Road in a single pass. Teaches: put unstated constraints on the page, let max reasoning do the "iteration" internally.
- **10 perception_grounding** — Single Responses call: fridge photo + dietary prompt → self-contained interactive HTML with color-coded dots at percentage pixel locations, hover nutrition tooltips. One `system`+`user` (input_image+input_text), streamed; downsized to 1280 px max. "Perception grounding" (where, not just what).
- **11 github_repo_agent** — Autonomous GitHub Actions bot on OpenCode + `muse-spark-1.3`: agents defined as markdown in `.opencode/agent/*.md` (triage, review, qa, rfc, bugfix, stale, repo-agent orchestrator). `opencode.json` wires the Meta provider via `@ai-sdk/openai-compatible`. Event-first routing (LLM only for free-text `/oc`); per-agent tool allow-lists; shared `AGENTS.md` SECURITY section (treats issue/PR text as untrusted data, refuses self-config edits); never merges, gated write paths, phased rollout.
- **12 computer_use** — OpenCode + a small `cua_local_mcp.py` bridge exposes screenshot/click/type/run_command on a throwaway Cua Linux desktop; `muse-spark-1.3` finds and plays GNOME Mines from screenshots; delegates to `task` subagents to stay under the 50-images/request limit. Look-act-look.
- **13 macos_cua** — `metacua`, a native macOS computer-use agent built twice (Swift SwiftPM + Python). Posts to `{base}/responses` with `parallel_tool_calls:false`, `store:false`, `reasoning.effort`; tools `computer.computer` (normalized 0–1000 coords) + `computer.stop` (+ opt-in `bash`); `--batched-actions`; Python OSWorld `pyautogui` mode parsed with `ast`, never `exec`'d; retains ≤`--max-images` screenshots, drops reasoning items on replay (store:false). Drives the real primary display.
- **14 muse_robotics** — Booth demo orchestrating five Meta models (detail in §4). Offline-by-default; live adapters for each.
- **15 glimmer_api_agent** — Hermes runs locally on `muse-glimmer-30b`; a `consult_remote_model` plugin tool calls `muse-spark-1.3` only after Hermes' human approval gate; logs digest/byte-count/destination to `egress.jsonl` (not the question/answer); empty `fallback_providers` so a local failure can't silently become a cloud call. Local-first with an auditable egress boundary.

### 1.4 `04_muse_code/` (11 recipes, `muse` CLI, model `muse-spark`)

Muse Code is Meta's terminal coding agent. Every recipe ends in a replayable proof point. Append-only event log per session at `~/.local/share/muse/sessions/YYYY/MM/DD/<id>/session.jsonl`.

- **01 append_only_audit_log** — `muse export` projects the log to a byte-deterministic, offline JSON trajectory (`--redacted` variant); walk a six-step approval chain (`proposed`→`accepted`→`approval.review requested`→`decision_applied` with `decision_source`→`side_effect_intent policy_decision`→`effect.started`); `muse resume` rebuilds state, treats a committed terminal record as done, flags an in-flight intent with no terminal record as unknown, and uses `idempotency_key` to avoid duplicate side effects across a crash.
- **02 deterministic_replay** — Author a golden fixture (`schema_version:1`, run records + `expected_model_context`); `muse trace inspect --fixture` projects offline (no model/tool/network) and reports diffs; `replay_gate.sh` fails CI on any diff (gate on diff count, not exit code); GitHub Actions template `ci-replay-gate.yml`.
- **03 staged_approvals** — A compound shell command is parsed into stages; each resolved independently (`known_safe` / policy allow / `unresolved`); the first unclearable stage blocks; reject denies the whole command (fail-closed); trust scopes `Allow once` / `Always allow in this workspace (<prefix>)` / reject, recorded in `approval-policy.json`; interpreters (`python`,`bash`,`sudo`,bare `git`…) never offer a persistent prefix.
- **04 contained_execution** — OS-level sandbox grants write to workspace+temp, keeps the rest read-only, restricts egress; a live probe confirms enforcement before trusting it and refuses to run if not enforcing; three boundaries demonstrated (write outside workspace, `.git/` read-only inside a writable root, network egress). `--yolo`/`--disable-sandbox` turn it off.
- **05 immutable_guardrails** — `.agents/AGENTS.md` and `.muse/` protected two ways: a mediated-write approval that offers only `allow_once`/`abort` (no standing grant) and an OS sandbox mounting `.git`/`.muse`/`.agents`/`.sl`/`.hg`/`.eden` read-only. The agent can't widen trust over its own rules.
- **06 subagent_fanout** — `subagent_spawn(role, objective, worktree_isolation:true)` fans one job to parallel children, each in its own `git worktree` (runtime-owned, under `.muse/worktrees/`, detached HEAD, `cleanup_policy:remove_if_clean`); `subagent_status/send_message(interrupt?)/cancel/wait/read_result`; concurrency ≈ cores−2 clamped 4–8, extras queue. Steer is queued (next turn) unless interrupting; cancel is cooperative. Sample: six workers on a brick-out game, scored by one test suite.
- **07 goal_tracking** — `/goal <objective>` pins a durable objective with a status-line `Goal(...)` indicator; a step probe re-injects "continue toward the goal" every ~10 no-progress model calls; a completion audit gates `update_goal` so the agent runs the acceptance tests first. Sample: Kestrel→Falcon HMAC auth migration (`SPEC.md`, six checks).
- **08 bundled_skills** — Built-in `muse-core` skills loaded as summaries, full `SKILL.md` pulled on explicit invocation only, scoped to that turn: `/plan` (grounded plan, stops for approval), `/grilling` (one decision-forcing question at a time), `/grill-with-docs` (same, writes settled decisions to project docs), `/taste` (anti-AI-slop visual-defaults checklist).
- **09 loop_and_cron** — `/loop` turns a natural-language cadence into a 5-field cron; jobs are session-scoped, fire only while Muse Code runs, jitter ≤30 min, 7-day lifetime, one catch-up run after resume; list/cancel from chat. Use external schedulers for closed-terminal work.
- **10 side_chats** — `/side` (alias `/btw`) branches a read-only side conversation seeded from the main thread at a cut point; its own session stream; main run keeps going; Ctrl+C restores the main thread; no subagents/workflows in the side lane.
- **11 mcp_security_tooling** — A security-research recipe wiring Burp Suite, a bug-bounty toolkit, headless Ghidra and LLDB into Muse Code as MCP servers (`stdio` or `streamable_http` in `settings.json`, `mode:"optional"`), pointed only at authorized targets (PortSwigger's deliberately vulnerable demo site, a sanctioned bounty programme, a public patched CVE). Reusable mechanics: MCP servers expose named typed tools; `/mcp` lists them; a `PreToolUse` hook enforces scope the sandbox can't; recurring work can be packaged as a skill or split across subagents; `muse exec` in CI (gate on your own checks, not its exit code).

### 1.5 `05_muse_image/` (`muse-image-1.0`, Responses API)

- **01 image_api_fundamentals** — Generate from a prompt; refine via `previous_response_id` (server holds state, send only the change); steer/compose with `input_image` parts inside a `{"role":"user","content":[...]}` message (bare list → 400); image is base64 `result` on the `image_generation_call` output item; `store=False` path replays the prior image item.
- **02 backyard_restyle** — Prompt asks the model to web-search mid-generation for currently-sold furniture, render a product grid, then compose onto a real backyard photo across chained turns; a second search adds a matching table.
- **03 anchored_generation** — Build reference anchors (hero, cat, two location plates) once, chain every panel from them so character/style/setting stay on-model; per-turn `tools=[{"type":"image_generation","size":"1536x1024"|"1024x1536"}]`; compose panels into a page, then letter it.
- **04 image_editing_with_reasoning** — Upload a photo, add price tags in one turn, update after a sale across turns; model reasons over the frame, changes only what's named, preserves the rest.

### 1.6 `06_muse_voice/` (`muse-voice-transcribe-1.0`)

- **01 voice_api_fundamentals** — Two transports: streaming `wss://api.meta.ai/v1/asr/realtime` (credential inside the handshake JSON `authorization.accessToken`; raw PCM frames; cumulative partials; `endStream`) and one-shot `POST https://api.meta.ai/v1/asr/transcribe` (`Authorization` header, WAV). Three modes `PUSH_TO_TALK`/`ENDPOINTING`/`DIARIZATION` (fixed at handshake); speaker-attributed turns (`speechStart`→partials→`speaker`→`speechEnd`→`speechComplete`, correlate by `turnId`); `keywords` and `languageBias` biasing; cutoff close codes 1008/1011/1013; 60-min streaming cap, 10-min/32 MB one-shot cap. Must pace against an absolute schedule.
- **02 voice_chess_cua** — Spoken "Move E2 to E4" → deterministic local parser (exact grammar only, no second model call) → macOS Accessibility validation → two approved clicks → post-move confirmation. Passive HUD + calibrated grid overlay; `--dry-run`; fail-closed native input; transcripts are the only thing leaving the machine.

### 1.7 `07_sam/` (`sam-3.1`, Responses API via OpenAI SDK + `meta-sam` parsers)

- **01 api_basics** — Python and TS: segment an image (`input_image` data URL) or upload an MP4 (`files.create(purpose="user_data")` → `input_video` by `file_id`), stream with `meta_sam_parser`/`@meta-sam/parser`; `summary.json` (boxes, decoded masks, track visibility) + per-object SVG masks; one short noun phrase per request; completed-with-zero-masks is a valid empty match.
- **02 video_to_sticker_pack** — SAM tracks an animal through a video (longest-lived track), masks each source frame, selects three high-motion windows, exports transparent animated WebP stickers + WhatsApp-style `contents.json`; all non-SAM image ops are deterministic; `--events events.ndjson` reuses a saved response with no new call.
- **03 headlocked_speech_bubble_captions** — Uploads a conversation video; Muse Voice diarization and one SAM `people` request run in parallel; maps each anonymous voice to a SAM-tracked person; `@meta-sam/react`+`/video`+`/graphics` render collision-aware head-locked speech bubbles (head anchor derived from the pixel mask); Python/Pillow/FFmpeg render the final H.264 MP4. Server keys stay on the local Express server.

### 1.8 `meta-oss-cookbook` — Muse Spark Open

- **README / model card** — 816B total / 42B active sparse MoE with built-in perception encoders; multimodal in, text out; 100+ languages; 1,048,576-token window. BF16 serves TP8/EP8 on 8×B300 (~2 TB VRAM budget); NVFP4 serves TP4/EP4 on a single 4-GPU Blackwell node. License: Muse Model License + Acceptable Use Policy.
- **quickstart** — `hf download meta-models/Muse-Spark-Open-816B-A42B[-NVFP4]`; verify tokenizer/chat template with `AutoTokenizer.apply_chat_template`; rendered framing `<|start|>role<|message|>…<|eot|>`.
- **prompting** — Conversation = system/developer/user/assistant/tool; template's system block prepends defaults (knowledge cutoff 2026-01-04, current date), then your prompt, tools, reasoning strength, recipient list; recipients `self`(reasoning)/`commentary`/tool-name/`user`. `reasoning_effort` → numeric strength (low=8, medium=32, high=256, xhigh=512 default); can't be disabled; a `Reasoning strength:` line in the system prompt overrides the request. Tool loop (one `tool` message per call; parser `muse`); parallel tool calls each end `<|eom|>` except the last (`<|eot|>`). Media as `image_url`/`video_url`/`audio_url` parts (placeholders `<|patch|>`/`<|video|>`/`<|audio|>`).
- **inference-server** — SGLang, vLLM, TensorRT-LLM, NVIDIA Dynamo, HF Transformers, llama.cpp (ggml-org GGUFs Q4_K_S/Q8_0/Q2_K), Unsloth (Dynamic GGUFs), MLX (across Mac Studios). All OpenAI-compatible except Transformers (Python). Parser flags `--reasoning-parser muse --tool-call-parser muse`; speculative decoding (SGLang DFLASH `RadixArk/...-DFlash2`, vLLM `dspark` `Inferact/...-DSpark`).
- **settings** — temp 1.0/top_p 1.0/do_sample true; 62 decoder layers (46 sliding-window 2,048, 16 full-attention keep the long-context KV); stop only on `<|eot|>`(200008)/`<|end_of_text|>`(200001), never `<|eom|>`(200007); `eos_token_id=[200001,200008]`.
- **recipes/muse-spark-open-mac** — Serve NVFP4 across two (512 GB) or four (256 GB) M5-Ultra Mac Studios over Thunderbolt-5 RDMA with MLX `jaccl` (`mlx.launch --hostfile ... --backend jaccl`); macOS 26.2+, MLX 0.30.1+, passwordless SSH. ~4 hours.
- **hosted providers** — Together AI (`meta-models/muse-spark-open`), Fireworks AI (`accounts/fireworks/models/muse-spark-open`), Baseten (full 1M context + image/video/audio), Groq (131,072 context, access-gated), Nebius Token Factory, plus Modal and OpenRouter. All OpenAI-compatible; `reasoning_effort` honored.
- **post-training** — SFT: TorchTitan (full-parameter, text/image/audio), TRL (LoRA, 8×8 H100), NeMo AutoModel, Megatron Bridge; hosted Together (SFT+GRPO) and Fireworks (serverless LoRA SFT/DPO/ORPO/distillation/RL, base `...-nvfp4`, rank ≤64, seq ≤262,144). RL: TorchTitan/TitanRL (GRPO + DAPO loss; `rl.py` + `qa_task.py` template with Dataset/Env/Reward over DAPO-Math) and Miles (GRPO on 64×H200, SGLang rollouts, `--vlm` Geometry3K mode). `with_task(config, task)` keeps the model system fixed and swaps only the three task pieces.

### 1.9 `meta-oss-cookbook` — Muse Glimmer

- **README / model card** — 30B dense decoder (Llama/Gemma2-style text stack), text+image in / text out via a ~1.8B perception encoder, 131,072 context, ATEM `<atem:function_calls>` tool format, channel-scoped chat (`to=self` reasoning). bf16 ~60 GB; quantized Q4 ~16–20 GB on a 24–32 GB GPU. License on the HF model card; Together lists it as Apache-2.0.
- **quickstart** — vLLM (image `vllm/vllm-openai:muse-glimmer`, flags `--tool-call-parser muse_glimmer --reasoning-parser muse_glimmer --enable-auto-tool-choice`, 72 GB VRAM budget), HF Transformers (tested path, `eos_token_id=[<|eot|>,<|end_of_text|>]`), Ollama (`ollama run muse-glimmer`, `:30b-mlx`), LM Studio. One tool call per message (consecutive assistant messages, not one `tool_calls` array).
- **agentic-fundamentals** — Runnable pure-Python agent loop on HF weights: `response_parser.py` (`MuseGlimmerATEMParser`, strips `to=self`/`to=user` spans before scanning invokes), `agent_loop.py` (`@tool` registry, stop set `[<|eot|>,<|end_of_text|>]`, feeds parsed dict args back), `run_agent.py` (reviews real code with `list_files`/`read_file`/`write_file`, self-corrects on tool errors returned as JSON). Max VRAM ~60 GB bf16.
- **recipes** — structured-output (Pydantic `Contract`, server-constrained, `X|None` for "not stated"), reasoning-effort (same problem at low/medium/high/xhigh with a token/latency table; `reasoning` field via `--reasoning-parser`), alert-triage-copilot (three-stage strict-JSON pipeline, §3), computer-use-web (quantized GGUF on llama.cpp + `metacua` driving real Safari, screenshots+coords), sandboxed-agent (NVIDIA NemoClaw/OpenShell: an agent told to exfiltrate a fake credential is blocked twice by the sandbox — guardrails outside the model), voice-agent-macos (fully local LiveKit + ExecuTorch Parakeet ASR + Muse Glimmer + Supertonic TTS on Apple silicon).
- **inference-server** — vLLM (reference, unmerged PR image), Ollama, LM Studio Bionic, SGLang (four checkpoint formats incl. NVFP4+MXFP8 and MLX Q4), llama.cpp (verified on Metal; vision+tools+DFlash), Unsloth, ExecuTorch (ahead-of-time `.pte` export to CUDA/MLX, K-Quant-17GB targets 24 GB / K-Quant-Dynamic targets 32 GB). Shared rule: never stop on `<|eom|>`.
- **platform** — Partner-contributed hardware pages (Intel Arc Pro / Core Ultra / Xeon 6; NVIDIA B300 with a vLLM concurrency sweep). Precision status labels Verified/Works-not-verified/Planned/Not-supported.
- **hosted** — Together AI only so far (`meta-models/Muse-Glimmer-30B`, $0.35/$1.50 per 1M in/out, 128K+ context, Chat+Vision, fp8 serving, parallel tool calls in one turn).
- **post-training** — SFT via Axolotl (QLoRA / bf16 LoRA FSDP2 / full FSDP2 on 8×H100; CoSyn/Tulu/Docmatix datasets; measured val losses and W&B links); RL via TitanRL data-analyst (§5).

---

## 2. API mechanics learned from the notebooks

**Client / base URL / auth.** One setup reused everywhere:
```python
from openai import OpenAI
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
```
Two request formats: **Chat Completions** (stateless, send full `messages` each call) and **Responses** (`client.responses.create`, server-managed state via `previous_response_id`, plus built-in tools).

**Tool calling (Chat Completions).** Tools nest under `function`. On `finish_reason=="tool_calls"`, append the whole assistant message, then one `tool` message per `tool_call_id`; loop until no more tool calls. Parallel calls come back in a single turn (answer each). Only `tool_choice:"auto"` is supported.

**Structured output.** `response_format={"type":"json_schema","json_schema":{"name":...,"schema":{...}}}` constrains decoding; `client.beta.chat.completions.parse(response_format=PydanticModel)` returns `message.parsed`. Lock shape with `additionalProperties:false`+`required`+`enum`. Robotics recipe uses `"strict": True` with an `enum`-bounded skills/objects schema. Responses API uses `text.format`.

**Reasoning tokens / effort.** `reasoning_effort` ∈ `none<minimal<low<medium<high`, `xhigh`=`high`. Reasoning tokens are billed output tokens at `usage.completion_tokens_details.reasoning_tokens`. Chat `reasoning_content` is empty today; the Responses `reasoning` output item is encrypted (replayable, not readable), requested with `include=["reasoning.encrypted_content"]`, `store=False`.

**Prompt caching.** Automatic on stable leading tokens; read `usage.prompt_tokens_details.cached_tokens`; optional stable `prompt_cache_key` raises hit rate; `prompt_cache_retention` `"in_memory"`/`"24h"`. Put stable content first, volatile last.

**Long context.** 1,048,576 tokens shared by input+output. `POST /v1/responses/input_tokens` returns the count without generating. No server-side truncation; over-window → 400.

**Vision.** `image_url` part (public URL the server fetches, or base64 data URL) in a `user` message only. ~50 images/request, 50 MB inline, 1 GiB via Files API. Measure with the input-tokens endpoint.

**Search grounding (Responses only).** `tools=[{"type":"web_search","search_context_size":"low|medium|high"}]`. Output is a list; filter by `item.type` (`reasoning`/`web_search_call`/`message`). `url_citation` annotations carry `url`/`title`/`start_index`/`end_index` indexing into the block text. Insert footnote markers back-to-front, dedup by URL.

**Error handling.** Branch on `type`+`status_code` (not `code`). Retry 429/5xx/timeout with exponential backoff + jitter; never retry 400/401/404. Throttle from `x-ratelimit-remaining-*` (via `with_raw_response`); add a circuit breaker.

**Image generation (`muse-image-1.0`).** Responses API; image is base64 `result` on the `image_generation_call` item; `tools=[{"type":"image_generation","output_format":"png","size":...}]`; chain with `previous_response_id`; reference/compose with `input_image` parts in a `user` message; `store=False` replays the prior image item.

**Segmentation (`sam-3.1`).** Responses API with `input_image`/`input_video` (video via `files.create(purpose="user_data")` → `file_id`); `metadata={"mask_encoding":"one_bit"}`; stream=True with cumulative snapshots; decode with `meta_sam_parser`/`@meta-sam/parser`.

**ASR (`muse-voice-transcribe-1.0`).** Not an HTTP-only endpoint. Streaming WebSocket `wss://api.meta.ai/v1/asr/realtime` — handshake JSON `{mode, authorization:{accessToken}, audioEncoding:"PCM_24KHZ"|"PCM_16KHZ", model}`, binary PCM frames paced to real time, `endStream`. One-shot `POST /v1/asr/transcribe` with `Authorization` header and WAV. Close codes 1008/1011/1013.

**Open-weight serving differences.** Both open models use the channel-scoped `<|start|>role<|message|>…<|eot|>` format and the `<|eom|>` end-of-message gotcha (never a stop token; stopping on it collapses parallel tool calling). Muse Spark Open parser `muse`; Muse Glimmer parser `muse_glimmer` and ATEM tool blocks; Glimmer emits one tool call per message as consecutive assistant messages, Spark Open can emit several `<|eom|>`-separated calls in one turn.

---

## 3. Agent patterns in depth (reuse for production multi-agent orchestration)

**Agent loop basics.** The contract: one tool per turn, an observed result, and an objective oracle for "done" (a test or build). Guards bound the run: max iterations, token budget, stuck detection (hash `(tool_name, args)`, stop after 3 identical calls), user interrupt. In production: every loop needs a machine-checkable stop condition and a stuck detector; log turns as a trace. The sandbox recipe's `sandbox_scaffold.py` is a complete minimal harness (raw-urllib Chat Completions with `tools`+`tool_choice:"auto"`, a dispatch function, truncated tool output, retries) you can lift directly.

**Interleaved reasoning.** `reasoning → tool_call → tool_result → reasoning`. The lever is `reasoning_effort`; measure end-to-end, not per-call (a thin budget adds recovery turns). For an orchestrator: raise effort on the turns that decide structure (ordering, cross-file dependencies), keep it low on mechanical steps.

**Managing context.** Prompt the agent to keep a `STATE.md` (goal, key decisions, task graph with status, file map, current step, open questions) and to re-read a file before editing it. Selective re-retrieval keeps verbose file bytes out of permanent context. Heavy cross-cutting refactors can be offloaded to Task subagents whose separate contexts absorb the churn — emergent, not guaranteed. Result on a real run: ~301 calls, context peaked ~54% of 1M, no compaction. Directly reusable as the memory + delegation design for a long-running orchestrator.

**Validated in-place edits.** Search/replace with an exactly-once match rule (zero = hallucination → reject; >1 = ambiguous → add context); read-before-edit; `write` only for new files; `replaceAll` for intentional global changes. Pair with a compile/lint oracle after every edit. This is the safe mutation primitive for any code-writing agent.

**Alert fatigue copilot (business-process style).** Architecture: three stages in one session — **probe** (read `data/synthetic_alerts.json`, compute a ~12-line digest in Python, emit strict JSON `{patterns[], refined_purpose{statement,rationale}, signals[]}`), **chat** (answer a grounded question citing only digest numbers), **self-assess** (first-person gap analysis + up to 8 `proposals` of kinds `purpose|mandate|signal|memory|scenario`, each `low|high` risk). State files: `purpose.json`, `signals.json`, `memory.jsonl` (one JSON per line, namespace/tier/content/salience), `proposals.json`, `assessment.json`. Loop guards (from `alert_fatigue_spec.md`): max 3 turns, token budget, strict-JSON parse required, user interrupt; termination = `final_json_valid`/`max_turns`/`token_budget`/`parse_fail`/`user_interrupt`. Validators: `validate_alert_output.py` (stdlib, exactly-once balanced-`{...}` extraction, checks `patterns[].text`, `refined_purpose.statement`, each signal's `source_connector/extraction/unit/direction/role/proxy_strength/rationale`, each proposal's allowlisted `kind` + `low/high` risk) with a pytest wrapper. `metrics.json`: `{probe_valid, self_assess_valid, patterns_count, signals_count, proposals_count, turns, model}`. Guards (from the spec): digest pre-computed in Python so the model cites rather than hallucinates numbers; propose-only (no external actions); synthetic `.example` data, no PII; token budget kept small by sending a digest not the 42-item dump. The self-assess stage is explicitly where a weaker model produces confident-wrong or unparseable output — the reusable idea is a self-critique stage that must name its weakest claim, missing evidence, and defer to a human. This is the template for an observable, auditable "copilot that improves its own spec."

**Subagent fanout.** `subagent_spawn(worktree_isolation:true)` per task, each in a runtime-owned git worktree (detached HEAD from the parent HEAD, `remove_if_clean`); parent tracks all via `subagent_status`, steers with `subagent_send_message(interrupt?)`, stops with `subagent_cancel` (cooperative), collects with `subagent_wait`/`read_result`; concurrency ≈ cores−2 (4–8), extras queue. Isolation = no file collisions; the event log records every spawn/status/control action. The production lesson: isolate write-capable parallel workers in worktrees, drive them from one control point, and keep the control actions in the audit log.

**Staged approvals + immutable guardrails + contained execution (the safety trio).** Decompose compound commands and judge each stage; fail closed on anything unparseable or dangerous; scope trust per-action/per-workspace (`Allow once` / workspace-prefix rule / reject), never a standing grant for guardrail files; a live-probed OS sandbox refuses to run unless enforcement is real; guardrail paths (`.git`/`.muse`/`.agents`/…) are read-only at the sandbox and mediated at the approval layer. Together these give an orchestrator a fail-closed permission model that an injected or runaway agent cannot widen.

**Goal tracking with a judge.** Pin the objective once; carry it across turns with a status indicator and a step probe that nudges on no-progress; a completion audit gates closing the goal until acceptance checks pass. Name the oracle in the objective ("done only when test X passes") so the judge has a concrete target — the anti-premature-completion mechanism for autonomous runs.

**Append-only audit log + deterministic replay.** Journal intent-before-effect (each side effect lands as an intent record carrying its authorization decision, then the effect runs); the log is the record. `muse export` → a byte-deterministic offline trajectory (hash pins a run); `--redacted` for sharing. `muse resume` reconciles a crash via idempotency keys (committed terminal → done; in-flight intent with no terminal → unknown, re-verify). `muse trace inspect --fixture` replays a golden fixture's model-context projection offline as a merge-blocking CI gate. This is the observability + auditability + eval backbone: every action and authorizer is replayable evidence, and projection changes are caught in CI.

**Loop & cron, side chats, bundled skills, MCP.** `/loop` schedules session-scoped recurring agent work; `/side` branches read-only investigation off a busy thread; bundled skills (`/plan`, `/grilling`, `/grill-with-docs`, `/taste`) are explicit-invocation playbooks loaded on demand; MCP servers add typed tools (web proxy, decompiler, debugger, browser) with a `PreToolUse` hook enforcing scope. All compose into an orchestration surface where scheduling, side investigations, reusable playbooks, and external tools are first-class and logged.

---

## 4. Multimodal recipes (what the models can do)

**Vision understanding (`muse-spark-1.3`).** Reads charts and extracts structured data (chart-explainer); diagnoses a UI bug from a screenshot and traces it to the component (screenshot_bugfix); sees its own browser/game screenshots to find visual-only bugs like tone-mapping washing colors (web_design, iterative_game_dev); reads a desktop/Mac screen and plans clicks (computer_use, macos_cua); pins health-score dots at percentage pixel locations from a fridge photo (perception_grounding); answers from a photo captured on Ray-Ban Meta glasses (visionclaw). Model is multimodal-in, text-out — a downstream tool renders any visual.

**Muse Image (`muse-image-1.0`).** Reasoning image model on the Responses API: generate, refine across turns (`previous_response_id`, send only the change), steer/compose from reference `input_image` parts, anchor a consistent character/style across a whole series by chaining from reference anchors, web-search mid-generation to render from real current products, and edit a described region while preserving the rest. Sizes via the `image_generation` tool (e.g. `1536x1024`, `1024x1536`).

**Muse Voice (`muse-voice-transcribe-1.0`).** Streaming and one-shot ASR with model-side punctuation, speech-boundary detection, and diarization (speaker-attributed turns). The **voice chess CUA** shows a safe pattern: ASR + vocabulary biasing + partial transcripts feed a *deterministic local parser* (exact move grammar, no second model call), then a macOS Accessibility-validated, fail-closed two-click executor with post-move confirmation — speech is the only data that leaves the machine.

**SAM 3 (`sam-3.1`).** Prompt with one short noun phrase, get pixel masks for every match and persistent object identity across a whole video. Turned into finished apps: a pet video → transparent animated sticker pack (longest-lived track, high-motion windows, deterministic compositing), and multi-speaker head-locked speech-bubble captions (SAM `people` tracks + Muse Voice diarization run in parallel, voices mapped to tracks, bubbles anchored to the pixel-mask head and collision-avoided).

**Muse robotics (five models in one booth flow, `14_muse_robotics`).** Muse Voice transcribes the visitor (`wss://.../v1/asr/realtime`) → local intent routing (model-selected intents never directly drive motors/retention/printing) → `muse-spark-1.3` returns a strict-JSON plan constrained by a `"strict":true` schema with `enum`-bounded skills (`pick_and_place_multi`, `sort_by_color`) and objects (red/green/blue) → deterministic full-mesh MuJoCo Franka Panda executes and verifies block positions → hosted `sam-3.1` previews a target mask (deliberately *outside* the control loop; failure fails open to motion) → `muse-image-1.0` restyles an opt-in portrait (`image_generation` tool, `store=False`, never writes the source) → Reachy Mini camera/mic/speaker/reactions → a loopback-only kiosk with launch token, single-flight execution, and file-first QR postcards. The reference design for an orchestration where the LLM plans but never directly actuates, each modality is a narrow adapter with an offline fixture, and segmentation decorates but cannot alter a plan.

---

## 5. Open-weight: Muse Spark Open and Muse Glimmer

**Sizes / licenses.** Muse Spark Open — 816B total / 42B active sparse MoE, multimodal in / text out, 1M context, Muse Model License + AUP; BF16 ~1.65 TB (8×B300) or NVFP4 ~537 GB (4-GPU Blackwell). Muse Glimmer — 30B dense, text+image in / text out, 131,072 context, license on the HF card (Together lists Apache-2.0); bf16 ~60 GB, Q4 GGUF ~16–20 GB on a 24–32 GB GPU.

**How to run.**
- **vLLM / SGLang** (both models) — OpenAI-compatible; Spark Open flags `--reasoning-parser muse --tool-call-parser muse` (TP4/EP4 NVFP4 or TP8/EP8 BF16; SGLang adds MegaMoE + DFLASH speculative, vLLM adds `dspark`); Glimmer needs the unmerged-PR Docker image `vllm/vllm-openai:muse-glimmer` or SGLang built from source, flags `--tool-call-parser muse_glimmer --reasoning-parser muse_glimmer --enable-auto-tool-choice`, 72 GB serving budget.
- **llama.cpp** — `llama serve -hf ggml-org/Muse-Spark-Open-816B-A42B-GGUF` (Q4_K_S/Q8_0/Q2_K) and `meta-models/Muse-Glimmer-30B-GGUF` (verified on Metal: text+vision+tools+DFlash); `--chat-template-kwargs '{"reasoning_effort|reasoning_strength":...}'`.
- **Ollama** — `ollama run muse-glimmer` (`:30b-mlx`), can launch coding agents (`ollama launch claude/pi/opencode/hermes/openclaw --model muse-glimmer`).
- **ExecuTorch** — ahead-of-time `.pte` export for Glimmer to CUDA (`model.pte`+`aoti_cuda_blob.ptd`) or Apple-silicon MLX; K-Quant-17GB (24 GB) / K-Quant-Dynamic (32 GB); CPU export unsupported.
- **MLX** — Spark Open NVFP4 across Thunderbolt-linked Mac Studios (`jaccl` RDMA); Glimmer MLX quants.
- Others: Transformers, TensorRT-LLM, NVIDIA Dynamo, Unsloth, LM Studio Bionic.

**Hosted providers.** Muse Spark Open: Together AI, Fireworks AI, Baseten, Groq, Nebius Token Factory, Modal, OpenRouter. Muse Glimmer: Together AI ($0.35/$1.50 per 1M, fp8 serving, parallel tool calls). Fireworks also offers serverless LoRA post-training.

**Post-training.**
- **SFT via Axolotl (Glimmer)** — QLoRA (4-bit frozen base + adapters, ~27 GB, runs on 1 GPU), bf16 LoRA FSDP2 (~33–41 GB), full-parameter FSDP2 (~57–97 GB peak at final save); CoSyn (single-image), Tulu (text), Docmatix (multi-image) datasets prepared to OpenAI Messages JSONL with local PNGs; measured val losses 0.80–0.90 (CoSyn) / 0.72 (Docmatix) with W&B links; language projections only, vision tower frozen. TRL (LoRA) and TorchTitan (full, text/image/audio) also provided for Spark Open.
- **RL via TitanRL (data-analyst, Glimmer)** — GRPO with DAPO loss (asymmetric clip `ratio_clip_low 0.2`/`high 0.28`, no KL/reference), `adamw lr=1e-6`, 8 prompts × 8 samples/step, trainer FSDP3×TP2 on 6 GPUs + generator TP2 on 2 (Glimmer's 2 KV heads cap generator TP at 2), ~93 GiB peak on 8×H100. **Three task pieces**: `data.py` (four offline templates — csv sum, csv group-by-max, log count, log top-status — golden answer computed at generation, disjoint train/val index ranges), `env.py` (single `bash` tool, private scratch dir, grades the workspace after every command, reports via `env_rewards`), `rubric.py` (graded reward: 1.0 correct number in `answer.json`, 0.25 well-formed wrong value, 0.15 malformed file, 0.05 any command ran, 0.0 nothing, −0.05 per repeated failed command — graded tiers keep GRPO reward variance alive so a batch isn't dropped as untrainable; correctness strictly dominates). It trains a *behavior* fix (the model already computes the right number but ran out of turns without writing the file): rollouts that ran out of tokens mid-answer 48%→0%, completed 20%→70%, correct-file 52%→100%, reward 0.21→0.98 by step 15 where the task saturates (10 consecutive untrainable batches). `bash` chosen over a clean `run_python` tool precisely so the shell-heredoc bug being fixed stays in scope. The RL-with-a-rubric/env recipe is the template for training a specialist on a machine-checkable reward with no judge and no labels.
- **RL via Miles (Spark Open)** — GRPO on 64×H200, DAPO-Math or `--vlm` Geometry3K (vision tower frozen).
- **Sandboxed agent (Glimmer, NVIDIA NemoClaw/OpenShell)** — an agent instructed to exfiltrate a *fake* credential is blocked twice by the sandbox (credential brokering keeps the key out of the agent's environment; deny-by-default egress blocks the upload); the point is that guardrails belong outside the model, and a more capable tool-using model is exactly the one worth sandboxing.
- **computer-use-web (Glimmer)** — quantized GGUF on llama.cpp + `metacua` driving real Safari from screenshots and normalized 0–1000 coordinates (no accessibility tree); `reasoning_strength` set server-side.
- **structured-output / reasoning-effort (Glimmer)** — server-constrained Pydantic extraction with `X|None` for "not stated"; a four-level effort/latency/token comparison; `reasoning` surfaced as a separate field via `--reasoning-parser muse_glimmer`.
- **alert-triage-copilot (Glimmer)** — the Muse Spark alert recipe ported to local Glimmer: a three-stage schema-chained pipeline (`TriageResult` → `RemediationPlan` → `SelfAssessment` with `verdict: safe_to_action|needs_human_review`), each stage consuming the prior stage's typed object; gate auto-remediation on `safe_to_action`, page on `needs_human_review`. The baseline failure it fixes: a weaker model couldn't emit parseable self-assessment output.

---

## 6. "Judge-impressing" angles (creative use beyond basic integration)

Judging weights: Impact 30% / creative Use of Meta AI Tooling 25% / Technical Depth 20% / Demo 25%, plus a $5K "Best Agentic Use-Case" and $10K "Best Build on Meta Open Weight Models" bonus. Combinations below are drawn straight from what the cookbooks demonstrate:

1. **Interleaved reasoning + parallel tool calls in one loop** — effort dialed up only on structure-deciding turns, down on mechanical ones; show the token/turn tradeoff you measured. (Technical depth; directly from `02_interleaved_reasoning` + `06_reasoning_tokens`.)
2. **SAM 3 + Muse Spark + Muse Image + Muse Voice chained** — e.g. segment a product/person, reason/plan over it, restyle or caption, narrate — the `muse_robotics` five-model orchestration proves the chaining works. (Creative tooling use; targets the open-weight bonus if Spark Open is self-hosted.)
3. **Muse Code headless subagent fanout across isolated git worktrees** — parallelize an audit/refactor/bugfix batch, each worker in its own worktree, steered/stopped from one control point with everything in the audit log. (Agentic bonus.)
4. **RL-post-train a Muse Glimmer specialist with a rubric env** — a machine-checkable reward (file exists / number matches / test passes) and graded tiers to keep GRPO variance; show a before/after outcome shift like the data-analyst 48%→0% truncation fix. (Open-weight bonus + technical depth.)
5. **Deterministic replay + append-only audit log for auditability** — ship a feature whose every agent action is replayable evidence and whose model-context projection is a merge-blocking CI gate. (Impact in regulated/enterprise framing.)
6. **Self-improving copilot (probe → chat → self-assess)** — an agent that extracts grounded patterns, answers from memory, and proposes changes *to its own spec* with risk-tagged proposals and a strict-JSON validator/eval. (Agentic bonus; the alert-fatigue template.)
7. **Vision self-verification loop** — a build/design/game agent that screenshots its own output, finds visual-only bugs a code-only agent can't, and re-verifies — "an agent with eyes." (Demo impact.)
8. **Search-grounded generation with real citations** — Responses `web_search` with mapped `url_citation` spans rendered as footnotes, or Muse Image searching mid-generation to render from real current products. (Creative tooling; trust/impact.)
9. **Goal-tracked autonomy with a completion judge** — pin an objective whose oracle is a test suite; the harness refuses to close the goal until acceptance checks pass. (Agentic reliability.)
10. **Fail-closed permission model (staged approvals + live-probed sandbox + immutable guardrails)** — demonstrate an injected/runaway agent that cannot widen its own trust or edit its own rules. (Technical depth + safety story.)
11. **Local-first + selective cloud escalation with an auditable egress boundary** — Glimmer on-device, `muse-spark-1.3` only after a human approval gate, every outbound byte logged (the `glimmer_api_agent` pattern). (Privacy/impact; open-weight bonus.)
12. **One-shot high-constraint generation with an `AGENTS.md` + max reasoning** — show a complex artifact (3D game, app) produced in a single pass because the invisible constraints were written down and `xhigh` did the iteration internally. (Demo wow + technical depth.)
13. **Computer-use (CUA) from pixels only** — drive a real Mac or a throwaway Linux desktop from screenshots and normalized 0–1000 coordinates with subagent fanout to stay under the image-per-request limit. (Demo + agentic.)
14. **Perception grounding to a self-contained interactive artifact** — one API call turns an image into an HTML overlay with pixel-located interactive elements (the fridge/health-score pattern), generalizable to inventory, retail, inspection. (Creative tooling; one-call simplicity.)
15. **MCP-extended specialist agent** — wire domain tools (browser proxy, decompiler, debugger, or your own domain MCP) into Muse Code with a `PreToolUse` scope hook, and package the workflow as a reusable skill. (Technical depth; agentic extensibility — keep targets authorized.)

---

## 7. Gaps / caveats (missing, broken, preview-only, hardware-heavy)

**Preview / finalizing surfaces.**
- Hosted preview is free but rate-limited; the official Model API client package is out of date (use the OpenAI SDK).
- `reasoning_effort` default is "still being finalized"; the `"none"` string "isn't reliably available yet"; `xhigh` just maps to `high`.
- Chat `reasoning_content` is empty and Responses `reasoning.summary` is empty for Muse Spark today — you can replay encrypted reasoning, not read it.
- Realtime ASR access "may be limited during rollout" (voice chess).

**Hardware-heavy.**
- Muse Spark Open: BF16 ~2 TB VRAM (8×B300), NVFP4 a 4-GPU Blackwell node; the Mac recipe needs 2–4 M5-Ultra Mac Studios (256–512 GB each), macOS 26.2+, Thunderbolt-5 RDMA — ~4 hours.
- Muse Glimmer bf16 ~60 GB (serve budget 72 GB); single-GPU only when quantized (~17–20 GB).
- Post-training: Axolotl full FSDP2 peaks ~97 GB/GPU at final save (almost no margin on an H100); TitanRL data-analyst ~93 GiB on 8×H100; Miles 64×H200 with InfiniBand + ~1.6 TB storage per node; Adam fp32 state allocates on the first `optimizer.step()` so memory jumps between step 1 and 2.

**Unverified / unmerged / fragile.**
- Muse Glimmer vLLM support is an unmerged PR shipped only in `vllm/vllm-openai:muse-glimmer` (`pip install vllm` won't serve it); SGLang support is merged to `main` but not in a release (build from source or use `lmsysorg/sglang:dev-muse-glimmer`). Several Glimmer quickstart paths are "pending publish" (Ollama tag, LM Studio/MLX quant).
- OSS cookbook quickstart statuses: vLLM Spark Open and Glimmer marked "unverified end to end"; voice-agent-macos "release readiness remains false" pending clean-machine validation; sandboxed-agent and computer-use-web "not reproduced/not verified on this checkpoint"; ExecuTorch "not re-run for this cookbook."
- `computer-use-web` needs an open `metacua` PR (`pr-11`) or the HF tool-result path fails on step 2.
- Platform/perf numbers are partner self-reported and dated, not independently re-run.

**Preview / environmental dependencies in the model cookbook.**
- Multi-agent orchestration (Hermes) needs an Anthropic/OpenAI/Nous Portal API key for the harness (not just the Meta key), plus `tmux`/`ffmpeg`/~6 GB disk; the Kanban dispatcher only runs while the gateway process is up; jobs are session-scoped.
- `muse_robotics` live SAM/image/voice/Reachy paths need the Meta key and optional hardware (Reachy Mini, CUPS printer); MuJoCo on headless Linux needs `MUJOCO_GL=egl`.
- SWE-bench sandbox and Cua desktop recipes need Docker; the first SWE-bench run builds a multi-GB image.
- macOS CUA (`metacua`) drives the real machine with no sandbox and no confirmation step (irreversible actions possible) and primary display only — the repo flags it CAUTION, run on a spare/low-privilege account.

**Scope limits.**
- Muse Spark/Image/Glimmer are text-out (and image-out for Muse Image) — no video generation; Glimmer processes video only as individual frames (not optimized for it) and server image support varies by runtime.
- Structured output guarantees JSON *shape*, not factual correctness — every extracted number is a claim to verify (chart-explainer, alert-fatigue, perception-grounding all re-check).
- `tool_choice` is `auto`-only; recursive JSON schemas rejected; no server-side context truncation.
- The MCP security recipe is strictly for authorized targets (vulnerable demo site, sanctioned bounty, public patched CVE); the cookbook gates it behind scope hooks and authorized-target warnings.

---

# PART D — Model landing pages and secondary resources

# Meta dev.meta.ai — product & model landing pages (WebFetch summaries, 2026-10-27)

## Meta Model API (https://dev.meta.ai/products/meta-model-api)
- Self-serve access to Muse models for agentic and multimodal workflows. OpenAI SDK compatible (point SDK at the service with API key). Web search grounding available as a tool.
- Text model pricing per 1M tokens (input / cached input / output):
  - muse-wonder-1.0: 1M ctx, $4.00 / $0.20 / $20.00
  - muse-spark-1.3: 1M ctx, $1.25 / $0.15 / $4.25 (not used to improve Meta's products)
  - muse-spark-1.3-contributor: 1M ctx, $0.10 / $0.002 / $0.20 (used to improve Meta's products) — ~12x cheaper
  - muse-spark-1.2 / 1.1 same rates; 1.2-contributor same as 1.3-contributor
  - muse-wonder-full-1.0: subscription-only in Muse Code
- Muse Image: $0.01 per image. Muse Voice Transcribe 1.0: $3.00 per 1,000 minutes ($0.18/hr). SAM 3.1: $2.50 per 1,000 images; $0.20 per 1,000 video frames.
- Muse Spark also on OpenRouter. Cookbooks advertised: quick start, multi-agent orchestration, search grounding, computer use, GitHub agent, browser-verified web design.
- Also: Meta AI Connectors, Muse Connectors (products).

## Muse Spark 1.3 (https://dev.meta.ai/models/muse-spark)
- "Trained for agentic workflows and optimized for competitive coding performance"; higher first-attempt accuracy, reliable tool calling; "max" reasoning level.
- Tracks context and prior results, works through messy/conflicting inputs, asks for input when needed. Long-horizon coding with fewer turns.
- Multimodal: video, images, documents; visual reasoning runs through a real execution environment.
- Benchmarks vs Spark 1.2 (xhigh), GPT 5.6 Sol (max), Opus 5 (max): GDPVal-AA v2, JobBench, OSWorld 2.0, DeepSearchQA, Agentic IF Index, AutomationBench, MRCR 256K–1M, DeepSWE v1.1, SWEAtlas CodeBase QnA, Terminal-Bench 2.1.
- Cookbooks: quick start, multi-agent orchestration (four-profile agentic team), agent fan-out (subagents in isolated worktrees), computer use, GitHub agent (OpenCode), search grounding.
- Blog: research.meta.ai/blog/introducing-muse-spark-1-3

## Muse Wonder (https://dev.meta.ai/models/muse-wonder)
- "Frontier coding, long-running agents and advanced computer use to tackle your most demanding work." muse-wonder-1.0 (API + Muse Code) and muse-wonder-full-1.0 (Muse Code subscription only; most advanced). 1M ctx. API price $4 / $0.20 / $20.
- Long-running agents: multi-step tasks for hours, planning, sub-agent delegation, parallel tool calls, error recovery. Advanced computer use (browser, desktop, mobile). Active memory.
- Benchmarks vs Claude Fable 5.1, GPT-6 Astra, Claude Opus 5.5: Personal Superintelligence Index, Harvey LAB-AA, Vals Finance Agent V2, HealthBench Pro, AutomationBench-AA, GDP.pdf, JobBench, OSWorld V2.1, MemoryBench, Terminal-Bench 4.0-AA, DeepSWE 1.1, SWE-Marathon, ProgramBench, AA Index.
- Muse Code subs: Everyday $5; High $15; Power $50 (Wonder Full, 20x); Maximum $200 (80x).
- Model card: research.meta.ai/static/muse-wonder-model-card/ · Playground: dev.meta.ai/playground

## SAM 3.1 (https://dev.meta.ai/models/sam-3-1)
- Detects, segments, tracks objects in images and video from a text prompt (short noun phrase) → box + pixel-precise mask per match; video tracking with identity preserved in a single call; zero-shot. DETR architecture. Model ID `sam-3-1`.
- Price: $2.50/1k images, $0.20/1k video frames. Playground: dev.meta.ai/playground/segmentation. Docs: /docs/media-segmentation, /docs/sam/overview, /docs/sam/segmenting.
- Shares endpoint/keys/billing with other models; pairs with Muse Spark (reasoning) and Voice Transcribe in one pipeline.

## Muse Glimmer (https://dev.meta.ai/models/muse-glimmer)
- "An open model built for always-on local agents." 30B params, Apache 2.0, single consumer GPU or Mac. Tool use, long tasks, failure recovery; persistent state across restarts; self-managed memory across hours-long sessions; multimodal perception.
- Benchmarks (high reasoning) vs Gemma4-31B, Qwen3.6-27B: leads on MCP Atlas 75.5, DeepSearchQA 74.6, τ³-Banking 23.5, WildClawBench 47.6, GAIA2 43.3, SkillsBench 44.3, SWE-Bench Pro 51.2, SWE-Bench Verified 76.0, SciCode 43.6, CharXiv 78.8, IFBench 77.0, AIME 2026 94.7, AA-LCR 80.0, Beam 128K 65.1. Trails Qwen on GDPval-AA (953 vs 1141), OSWorld-Verified (65.9 vs 75.6), TerminalBench 2.1 (51.7 vs 60.7), OmniDocBench (75.8 vs 77.8). ScreenSpot Pro 75.4. Safety: CI Memories violation 26.4%; AgentDojo ASR 28.4% (utility 94.2%).
- Run: Ollama, Unsloth Desktop, LM Studio; hosted: Fireworks, Together.ai, OpenRouter; guides: prompting, quantization, speculative decoding, vLLM, llama.cpp, ExecuTorch (mobile/edge). HF: huggingface.co/meta-models/Muse-Glimmer-30B.

## Muse Spark Open (https://dev.meta.ai/models/muse-spark-open)
- "Most capable open-weight model from a US lab." Derived from Muse Spark (Aug release) with extra safety post-training. ~816B total / 42B active MoE (from URL slug 816B-A42B; NVFP4 variant exists). License not stated on page (check HF).
- Coding, multimodal perception (video/images/docs), agentic workflows; multi-agent workflows on one model; separate **commentary channel** lets the model state intent before acting.
- Benchmarks vs Inkling, Nemotron 3 Ultra, Beam, Mistral Large 4, Qwen3.8, GLM 5.3, Kimi K3: JobBench, MCP-Atlas, GDPval-AA v2, HLE-Diamond, SciCode, AA-Omniscience, Terminal-Bench 2.1, DeepSWE 1.1, ZeroBench, BabyVision, SimpleVQA.
- Hosted: AMD, AWS SageMaker JumpStart, Baseten, Fireworks, Google Cloud, Groq, Hugging Face, vLLM, Intel, Azure, Modal, Nebius, NVIDIA, OpenRouter, SGLang, Together.ai, Unsloth. Download: dev.meta.ai/platform/models/download/muse-spark-open. HF collection: huggingface.co/collections/meta-models/muse-spark-open. Blog: dev.meta.ai/resources/blog/build-with-muse-spark-open.
- Hackathon note (Baseten): use `meta-models/muse-spark-open-1026`.

## Muse Code (https://dev.meta.ai/lp/muse-code)
- Coding agent powered by Muse Spark; macOS & Windows. **Multi-agent by default** (workers in parallel, reviewers in background). **Fully auditable** actions. Co-trained with the model. Install: `curl -fsSL https://dev.meta.ai/install.sh | bash`.
- Plans: Everyday $5 (Spark, Wonder, Image; 10–50 prompts/5h; voice mode; web search); High $15 (5x); Power $50 (Wonder Full, 20x); Maximum $200 (80x). Docs: dev.meta.ai/docs/muse-code/

## Muse Image (https://dev.meta.ai/models/muse-image)
- Agentic image generation grounded by search and reasoning before rendering; create + edit in one model; plans, pulls web references, generates/runs code where precision matters, checks results. Edits change exactly what's specified. Use cases: generation, precise editing, anchored composition, multi-turn refinement. $0.01/image. Model `muse-image-1.0`. Also on fal, Runway, OpenRouter.

## Muse Voice Transcribe (https://dev.meta.ai/models/muse-voice-transcribe)
- `muse-voice-transcribe-1.0`. Leading streaming WER; speaker attribution for 20+ speakers inside the recognition model; end-of-speech/turn detection; contextual & keyword biasing without fine-tuning. $3.00/1,000 min ($0.18/hr). Docs: /docs/speech-to-text.

# Secondary resources (on-demand sessions, partner docs, blog)

## Meta Connect on-demand sessions (Sept 24, 2026) — no transcripts on page
- "Building with Muse Spark and Muse Code: from capabilities to production" — Claire Zhou, PM. Model capabilities = intelligence to see/decide/act; harness (Muse Code) = reliability, scale, auditability for shipping production code.
- "The multimodal intelligence of Muse Spark" — Michelle Ko, Research PM. "Muse Spark treats what it perceives as something to act on, not just something to caption." Introduces Muse Voice Transcribe as first real-time audio perception model; code, physical action, video-heavy workflows.
- "The road ahead: the superintelligence blueprint and what's next" — Jack Krawczyk, Sr Director PM. How the model family fits together.
- Also related: "Build AI agents with Meta Business Agent Platform".

## Baseten (hosted Muse Spark Open)
- Base URL https://inference.baseten.co/v1, OpenAI SDK, BASETEN_API_KEY. Hackathon slug: `meta-models/muse-spark-open-1026`.
- Reasoning always on; returned in `reasoning_content`, final in `content`; reasoning tokens billed as completion tokens. `reasoning_effort`: low/medium/high/xhigh (default xhigh).

## Muse Spark 1.3 launch blog (research.meta.ai, Sept 2, 2026)
- Longer-horizon work; juggles multiple workflows in one thread; builds own context from messy/conflicting sources via tools; corrects plan gaps; tracks learnings; asks clarifying questions; asks for help when stuck; **confirms before consequential actions**; adapts update cadence; reliable long-form instruction following; aware of limits, reports hurdles rather than hallucinating outcomes.
- Coding: ~20% fewer tool calls, ~25% fewer tokens vs 1.2.
- Safety: stronger adversarial robustness / prompt-injection resistance; better calibration on irreversible actions.
- Eval report: research.meta.ai/static/muse-spark-1-3-evaluation-report
