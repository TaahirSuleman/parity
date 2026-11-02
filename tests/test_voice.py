"""Voice (spec §16): the recording kit's clock helpers (Task 26); transcription and alignment (Task 27)."""

import json

from parity.voice import format_captions, parse_captions, rebase_captions, rebase_focus_log, write_recording_sidecars


def test_focus_log_is_trimmed_to_the_clip_and_rebased_to_its_start():
    entries = [
        {"t_ms": 900, "dom_id": "early", "event": "focusin"},
        {"t_ms": 3500, "dom_id": "card", "event": "focusin"},
        {"t_ms": 1000, "dom_id": "name", "event": "focusin"},
        {"t_ms": 6001, "dom_id": "late", "event": "focusin"},
    ]
    assert rebase_focus_log(entries, t0_ms=1000, duration_ms=5000) == [
        {"t_ms": 0, "dom_id": "name", "event": "focusin"},
        {"t_ms": 2500, "dom_id": "card", "event": "focusin"},
    ]


def test_captions_keep_only_phrases_spoken_within_the_clip():
    rows = [(900, "Terminal"), (1200, "Google Chrome"), (4000, "Submit, button"), (6500, "Terminal")]
    assert rebase_captions(rows, t0_ms=1000, duration_ms=5000) == [(200, "Google Chrome"), (3000, "Submit, button")]


def test_captions_tsv_round_trip():
    rows = [(0, "Google Chrome"), (3000, "Submit, button")]
    text = format_captions(rows)
    assert text == "0\tGoogle Chrome\n3000\tSubmit, button\n"
    assert parse_captions(text) == rows
    assert parse_captions("12\tfirst\n\n  \nbad line\n") == [(12, "first")]  # blank and malformed lines are skipped


def test_write_recording_sidecars_writes_the_focus_log_and_captions(tmp_path):
    doc = write_recording_sidecars(
        tmp_path, "checkout", t0_ms=1_700_000_000_000, duration_ms=5000, sample_rate=16000,
        focus_entries=[{"t_ms": 1_700_000_000_000, "dom_id": "name", "event": "focusin"}, {"t_ms": 1_700_000_009_000, "dom_id": "late", "event": "focusin"}],
        captions=[(1_700_000_000_500, "Name on card, edit text"), (1_699_999_999_000, "Terminal")],
    )
    assert json.loads((tmp_path / "checkout.json").read_text()) == doc
    assert doc["page"] == "checkout" and doc["duration_ms"] == 5000 and doc["sample_rate"] == 16000 and doc["clip"] == "checkout.wav"
    assert doc["recorded_at"] == "2023-11-14T22:13:20+00:00"
    assert doc["stops"] == [{"t_ms": 0, "dom_id": "name", "event": "focusin"}]
    assert (tmp_path / "checkout.captions.txt").read_text() == "500\tName on card, edit text\n"
