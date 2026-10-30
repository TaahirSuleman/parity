---
name: meta-model-api
description: Verified request formats and gotchas for Meta's Model API (Muse Spark responses, computer use, grounding, Voice Transcribe). Use before writing or debugging any call to api.meta.ai.
---
# Meta Model API: verified on 29 Oct 2026

All of the formats below were tested live (see `docs/17-validation-results.md`).

**Base and auth**
- Base `https://api.meta.ai/v1`; header `Authorization: Bearer $MODEL_API_KEY`.
- The API is OpenAI-SDK compatible, but plain HTTP works fine (see `seeds/meta.py`, which caches responses to disk).
- `GET /v1/models` is free and serves as the key check.
- Our key can use: `muse-spark-1.1/1.2/1.3` (and `-contributor` variants for 1.2 and 1.3), `muse-wonder-1.0`, `muse-image-1.0`, `muse-voice-transcribe-1.0`, `sam-3.1`.

**Responses** (`POST /responses`)
- Body: `{"model":"muse-spark-1.3","input":...,"reasoning":{"effort":"low|medium|high"},"text":{"format":{"type":"json_object"}},"max_output_tokens":N}`. Put the JSON shape in the prompt and validate it in code.
- Output text is in `output[].content[].type=="output_text"`. A successful response contains `"error": null`, so detect failures by HTTP status, never by the presence of the `error` key.

**Images and grounding**
- Send images as `{"type":"input_image","image_url":"data:image/png;base64,..."}`.
- Grounding returns boxes on a 0–1000 grid via `{"bbox":{"x_min","y_min","x_max","y_max"}}`; prompt with "You are an object grounding expert".
- Boxes land on the right element, but loosely (median IoU ≈ 0.35). Map each box to the nearest DOM/AX element in code rather than trusting pixels.

**Computer use**
- Request: `tools:[{"type":"computer"}]` on `muse-spark-1.3`. Wonder support is unconfirmed.
- Set `"truncation":"auto"` **on every request**; it is a per-request setting.
- The model returns `computer_call` items with an **`actions` batch**. Execute them in order, then send back `{"type":"computer_call_output","call_id":...,"acknowledged_safety_checks":<pending_safety_checks>,"output":{"type":"computer_screenshot","image_url":<data-url>}}` with `previous_response_id`.
- Coordinates are pixels of the last screenshot, so keep the viewport fixed (1280×720).
- **Gotcha:** `keypress.keys` like `["ctrl","a"]` is a *chord*. Join it with `+` for Playwright (`Control+a`); pressing the keys sequentially breaks select-all.
- A 500 `server_error` can occur on a follow-up turn. Retry with backoff; log the request ID and timestamp, then report it at dev.meta.ai/support (Team ID, model, error, timestamps, request IDs; never the key).

**Voice Transcribe** (`POST /asr/transcribe`, multipart)
- Part `request` (application/json): `{"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"DIARIZATION"|"PUSH_TO_TALK","keywords":[...]}`. `audioEncoding:"WAV"` is required, and other values return "Malformed request".
- Part `audio`: a WAV file (16-bit mono, 16 kHz), ≤ 10 min, ≤ 32 MB.
- Response: `{transcript, audioDurationMs, turns:[{turnId,startMs,endMs,transcript,speaker?}]}`. `speaker` can be missing, and spurious extra speakers happen.
- Accuracy on fast synthetic (screen-reader) speech is unconfirmed by Meta, so test it on a real VoiceOver recording.

**Costs observed:**
- Spark grounding or judgement: ~2–4.5k tokens per call (well under a cent).
- Computer-use flow: ~1.7k tokens when it succeeds in one batch.
- Total validation spend: ~$0.21.
