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
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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


def align(turns: list[dict], stops: list[dict]) -> dict[str, Segment]:
    """Each turn belongs to the stop that had focus when it started; a stop's segment spans every turn until the next stop.
    Turns spoken before the first stop belong to nobody."""
    ordered = sorted(stops, key=lambda s: int(s["t_ms"]))
    segments: dict[str, Segment] = {}
    for turn in sorted(turns, key=lambda t: int(t.get("startMs", 0))):
        start, end, text = int(turn.get("startMs", 0)), int(turn.get("endMs", turn.get("startMs", 0))), str(turn.get("transcript") or "").strip()
        owner = None
        for stop in ordered:
            if int(stop["t_ms"]) <= start:
                owner = str(stop["dom_id"])
            else:
                break
        if owner is None or not text:
            continue
        seg = segments.get(owner)
        segments[owner] = Segment(start, end, text) if seg is None else Segment(seg.start_ms, max(seg.end_ms, end), f"{seg.text} {text}")
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
    """Transcribe the page's clip (PUSH_TO_TALK, the AX names as keywords) and align it to the focus log; None without a clip."""
    rec = load_recording(voice_dir, page)
    if rec is None:
        return None
    t = await client.transcribe(rec.clip.read_bytes(), keywords=list(keywords), mode="PUSH_TO_TALK", run_id=run_id, step_index=step_index)
    hypothesis = " ".join(str(x.get("transcript") or "") for x in t.turns) or t.transcript
    accuracy = word_accuracy(hypothesis, " ".join(text for _, text in rec.captions)) if rec.captions else None
    return PageVoice(page=page, clip_key=str(rec.meta.get("clip") or f"{page}.wav"), duration_ms=t.duration_ms or int(rec.meta.get("duration_ms") or 0),
                     transcript=t.transcript, turns=t.turns, segments=align(t.turns, list(rec.meta.get("stops") or [])), word_accuracy=accuracy,
                     model=t.model, request_id=t.request_id)
