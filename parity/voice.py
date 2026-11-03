"""Voice: real screen-reader audio (spec §16).

Recording kit (Task 26). Everything the kit writes sits on one clock: the WAV starts at ``t0_ms`` (epoch ms on the recording Mac),
``scripts/vo_focus_logger.js`` posts epoch ms for every focus stop, and ``scripts/vo_captions.sh`` writes epoch ms for every phrase
VoiceOver speaks. The sidecars beside the clip hold ms since the clip started, which is what alignment (Task 27) consumes:

- ``store/voice/<page>.json``: ``{"page", "clip", "recorded_at", "duration_ms", "sample_rate", "stops": [{"t_ms", "dom_id", "event"}]}``
- ``store/voice/<page>.captions.txt``: ``<t_ms>\\t<phrase>`` per line, the reference for ``word_accuracy``.

Transcribe and align (Task 27): ``transcribe_page`` sends the clip to Voice Transcribe once (cached by the client), ``align`` gives
every focus stop the turns spoken while it had focus, ``word_accuracy`` measures the transcript against the captions (gate G-V),
and ``transcript_agrees`` is the non-gating evidence check on one finding: the segment, normalised, contains the AX name.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from parity.store.models import VoiceEvidence

log = logging.getLogger(__name__)

Caption = tuple[int, str]
VOICE_DIR = Path(__file__).resolve().parents[1] / "store" / "voice"


def rebase_focus_log(entries: list[dict], *, t0_ms: int, duration_ms: int) -> list[dict]:
    """Keep the stops that fall inside the clip, in time order, as ms since its start."""
    end = t0_ms + duration_ms
    kept = sorted((e for e in entries if t0_ms <= int(e["t_ms"]) <= end), key=lambda e: int(e["t_ms"]))
    return [{"t_ms": int(e["t_ms"]) - t0_ms, "dom_id": str(e["dom_id"]), "event": str(e.get("event", "focusin"))} for e in kept]


def rebase_captions(rows: list[Caption], *, t0_ms: int, duration_ms: int) -> list[Caption]:
    """Keep the phrases spoken inside the clip, in time order, as ms since its start."""
    end = t0_ms + duration_ms
    return [(t - t0_ms, text) for t, text in sorted(rows) if t0_ms <= t <= end]


def format_captions(rows: list[Caption]) -> str:
    return "".join(f"{t}\t{text}\n" for t, text in rows)


def parse_captions(text: str) -> list[Caption]:
    """``<ms>\\t<phrase>`` lines; anything else (blank lines, a line without a tab) is skipped."""
    rows: list[Caption] = []
    for line in text.splitlines():
        ms, sep, phrase = line.partition("\t")
        if sep and ms.strip().isdigit():
            rows.append((int(ms), phrase))
    return rows


def write_recording_sidecars(out_dir: Path, page: str, *, t0_ms: int, duration_ms: int, sample_rate: int,
                             focus_entries: list[dict], captions: list[Caption]) -> dict:
    """Write ``<page>.json`` and ``<page>.captions.txt`` beside ``<page>.wav`` and return the JSON document."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "page": page,
        "clip": f"{page}.wav",
        "recorded_at": datetime.fromtimestamp(t0_ms / 1000, tz=timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "sample_rate": sample_rate,
        "stops": rebase_focus_log(focus_entries, t0_ms=t0_ms, duration_ms=duration_ms),
    }
    (out_dir / f"{page}.json").write_text(json.dumps(doc, indent=2) + "\n")
    (out_dir / f"{page}.captions.txt").write_text(format_captions(rebase_captions(captions, t0_ms=t0_ms, duration_ms=duration_ms)))
    return doc


# --- transcribe and align (Task 27) ---------------------------------------------------------------------

@dataclass(frozen=True)
class Segment:
    start_ms: int
    end_ms: int
    text: str


@dataclass
class Recording:
    clip: Path
    meta: dict
    captions: list[Caption]


@dataclass
class PageVoice:
    page: str
    clip_key: str
    duration_ms: int
    transcript: str
    turns: list[dict]
    segments: dict[str, Segment]
    word_accuracy: float | None  # None when the page has no captions to measure against
    model: str
    request_id: str


_PUNCT = re.compile(r"[^\w\s]")


def _words(text: str) -> list[str]:
    return _PUNCT.sub(" ", (text or "").lower()).split()


def load_recording(voice_dir: Path, page: str) -> Recording | None:
    """The clip and its sidecars, or None when the page was never recorded (Voice is skipped cleanly)."""
    voice_dir = Path(voice_dir)
    clip, meta = voice_dir / f"{page}.wav", voice_dir / f"{page}.json"
    if not clip.exists() or not meta.exists():
        return None
    captions_path = voice_dir / f"{page}.captions.txt"
    captions = parse_captions(captions_path.read_text()) if captions_path.exists() else []
    return Recording(clip=clip, meta=json.loads(meta.read_text()), captions=captions)


LAST_STOP_TAIL_MS = 3000  # a phrase VoiceOver starts at its caption time is over well within this


def align(transcript: str, captions: list[tuple[int, str]], stops: list[dict], *, duration_ms: int) -> dict[str, Segment]:
    """Give each focus stop the words the transcriber heard while its element had focus.

    The API returns no usable timing per element (PUSH_TO_TALK: no turns; DIARIZATION: a few pause-delimited turns spanning
    many stops; both seen 3 Nov), so the flat transcript is aligned word by word to the captions, which carry the clock: a
    word-level edit path (the same distance ``word_accuracy`` uses) maps each transcript word to a caption, a word the
    transcriber added stays with the caption of the word before it, and each caption belongs to the stop that had focus when
    it was spoken. A stop's segment starts at its focus event and ends at the next stop's (or the clip's end); its text is the
    transcript's own words, in order. Speech before the first stop belongs to nobody."""
    tokens = [(tok, norm) for tok in (transcript or "").split() if (norm := _PUNCT.sub("", tok.lower()))]
    ref = [(i, w) for i, (_, text) in enumerate(captions) for w in _words(text)]
    ordered = sorted(stops, key=lambda s: int(s["t_ms"]))
    if not tokens or not ref or not ordered:
        return {}
    n, m = len(ref), len(tokens)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i
    for j in range(1, m + 1):
        d[0][j] = j
    # A substitution costs as much as a deletion plus an insertion, so an exact match a few words on is never traded for a
    # mis-heard word here: the hero's "Submit" must land on the "Submit button" caption, not on the hint cut short before it.
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (0 if ref[i - 1][1] == tokens[j - 1][1] else 2))
    owner: list[int | None] = [None] * m  # caption index per transcript word
    i, j = n, m
    while i > 0 and j > 0:
        if ref[i - 1][1] == tokens[j - 1][1] and d[i][j] == d[i - 1][j - 1]:
            owner[j - 1] = ref[i - 1][0]
            i, j = i - 1, j - 1
        elif d[i][j] == d[i][j - 1] + 1:
            j -= 1  # a word the transcriber added (or mis-heard): it stays with the caption of the word before it
        else:
            i -= 1  # a caption word it missed
    last: int | None = None
    for k in range(m):
        if owner[k] is None:
            owner[k] = last
        else:
            last = owner[k]
    caption_stop: list[int | None] = []
    for t_ms, _ in captions:
        idx = None
        for si, stop in enumerate(ordered):
            if int(stop["t_ms"]) <= int(t_ms):
                idx = si
            else:
                break
        caption_stop.append(idx)
    words: dict[int, list[str]] = {}
    spoken_until: dict[int, int] = {}  # the last caption time per stop: the final stop's segment ends soon after it, not at the clip's end
    for k, (tok, _) in enumerate(tokens):
        c = owner[k]
        si = caption_stop[c] if c is not None else None
        if si is not None:
            words.setdefault(si, []).append(tok)
            spoken_until[si] = max(spoken_until.get(si, 0), int(captions[c][0]))
    segments: dict[str, Segment] = {}
    for si in sorted(words):
        stop = ordered[si]
        start = int(stop["t_ms"])
        end = int(ordered[si + 1]["t_ms"]) if si + 1 < len(ordered) else min(int(duration_ms), spoken_until[si] + LAST_STOP_TAIL_MS)
        seg = segments.get(str(stop["dom_id"]))
        text = " ".join(words[si])
        segments[str(stop["dom_id"])] = Segment(start, max(end, start), text) if seg is None else Segment(seg.start_ms, max(seg.end_ms, end), f"{seg.text} {text}")
    return segments


def word_accuracy(hypothesis: str, reference: str) -> float:
    """1 - word error rate (Levenshtein over normalised words), clamped at 0; no reference means no claim (0.0)."""
    ref, hyp = _words(reference), _words(hypothesis)
    if not ref:
        return 0.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return max(0.0, 1.0 - prev[-1] / len(ref))


def transcript_agrees(segment: Segment | None, ax_role: str, ax_name: str) -> bool:
    """Non-gating evidence: the segment, normalised, contains the AX name (the role when the control has no name)."""
    if segment is None:
        return False
    want = " ".join(_words(ax_name or ax_role))
    return bool(want) and want in " ".join(_words(segment.text))


async def transcribe_page(client, page: str, *, keywords: list[str] | tuple[str, ...] = (), voice_dir: Path = VOICE_DIR, run_id: str = "",
                          step_index: int | None = None) -> PageVoice | None:
    """Transcribe the page's clip (PUSH_TO_TALK, the AX names as keywords) and align it to the captions and focus log; None without a clip."""
    rec = load_recording(voice_dir, page)
    if rec is None:
        return None
    t = await client.transcribe(rec.clip.read_bytes(), keywords=list(keywords), mode="PUSH_TO_TALK", run_id=run_id, step_index=step_index)
    hypothesis = " ".join(str(x.get("transcript") or "") for x in t.turns) or t.transcript
    accuracy = word_accuracy(hypothesis, " ".join(text for _, text in rec.captions)) if rec.captions else None
    duration = t.duration_ms or int(rec.meta.get("duration_ms") or 0)
    segments = align(hypothesis, rec.captions, list(rec.meta.get("stops") or []), duration_ms=duration)
    return PageVoice(page=page, clip_key=str(rec.meta.get("clip") or f"{page}.wav"), duration_ms=duration, transcript=t.transcript, turns=t.turns,
                     segments=segments, word_accuracy=accuracy, model=t.model, request_id=t.request_id)


# --- the runner hook (Task 28) --------------------------------------------------------------------------

KEYWORDS_MAX = 50
KEYWORD_MAX_CHARS = 30  # the API rejects a longer keyword with 400 ("ASR keyword N exceeds the maximum length of 30 characters")


def voice_keywords(names) -> list[str]:
    """The biasing hints for the transcriber: the page's accessibility names, stripped, unique, in order, within the API's limits.
    A name over the length limit is dropped, not cut: a truncated hint would bias toward a word nobody speaks."""
    seen: dict[str, None] = {}
    for raw in names:
        name = (raw or "").strip()
        if name and len(name) <= KEYWORD_MAX_CHARS:
            seen.setdefault(name, None)
    return list(seen)[:KEYWORDS_MAX]


async def attach_voice(ctx, cap, findings: list, step_index: int) -> dict | None:
    """After verify, on one of our own store pages: transcribe the page's clip once (cached) and give each new finding whose
    element had focus during the recording its segment, with the agreement check. Emits ``voice.transcribed``. Never on a site
    we do not own, never without a clip, and never fatal: Voice is evidence, not a gate."""
    url = str(getattr(cap, "url", "") or "")
    if ctx.public or ctx.client is None or "/store/" not in url:
        return None
    page = Path(urlparse(url).path).stem
    names = voice_keywords(n.name for n in cap.ax_nodes)
    try:
        voice = await transcribe_page(ctx.client, page, keywords=names, voice_dir=ctx.settings.voice_dir, run_id=ctx.run.id, step_index=step_index)
    except Exception as exc:  # a transcription that fails after its retries leaves the finding's evidence as it was
        log.warning("voice: transcription of %s failed: %s: %s", page, type(exc).__name__, exc)
        return None
    if voice is None:
        return None
    attached: dict[str, dict] = {}
    for finding in findings:
        segment = voice.segments.get(finding.element.dom_id or "")
        if segment is None:
            continue
        finding.voice = VoiceEvidence(clip_key=voice.clip_key, start_ms=segment.start_ms, end_ms=segment.end_ms, transcript=segment.text,
                                      agrees=transcript_agrees(segment, finding.sr_role, finding.sr_name))
        await ctx.save_finding(finding)
        attached[finding.id] = finding.voice.model_dump(mode="json")
    data = {"page": page, "accuracy": voice.word_accuracy, "clip_key": voice.clip_key, "duration_ms": voice.duration_ms, "model": voice.model,
            "segments": len(voice.segments), "findings": attached}
    await ctx.emit("voice.transcribed", data)
    return data
