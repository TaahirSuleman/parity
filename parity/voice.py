"""Voice: real screen-reader audio (spec §16).

Recording kit (Task 26). Everything the kit writes sits on one clock: the WAV starts at ``t0_ms`` (epoch ms on the recording Mac),
``scripts/vo_focus_logger.js`` posts epoch ms for every focus stop, and ``scripts/vo_captions.sh`` writes epoch ms for every phrase
VoiceOver speaks. The sidecars beside the clip hold ms since the clip started, which is what alignment (Task 27) consumes:

- ``store/voice/<page>.json``: ``{"page", "clip", "recorded_at", "duration_ms", "sample_rate", "stops": [{"t_ms", "dom_id", "event"}]}``
- ``store/voice/<page>.captions.txt``: ``<t_ms>\\t<phrase>`` per line, the reference for ``word_accuracy``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

Caption = tuple[int, str]


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
