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


# --- transcribe and align (Task 27) ---------------------------------------------------------------------

import wave  # noqa: E402

import pytest  # noqa: E402

from parity.meta.client import transcribe_key  # noqa: E402
from parity.meta.fake import FakeMetaClient  # noqa: E402
from parity.voice import Segment, align, load_recording, transcribe_page, transcript_agrees, word_accuracy  # noqa: E402

STOPS = [{"t_ms": 0, "dom_id": "name", "event": "focusin"}, {"t_ms": 3000, "dom_id": "card", "event": "focusin"}, {"t_ms": 7000, "dom_id": "f5", "event": "focusin"}]
TURNS = [
    {"turnId": 1, "startMs": 200, "endMs": 2500, "transcript": "Name on card, edit text, T Suleman"},
    {"turnId": 2, "startMs": 3100, "endMs": 6000, "transcript": "Card number, edit text"},
    {"turnId": 3, "startMs": 7200, "endMs": 8900, "transcript": "Submit, button"},
    {"turnId": 4, "startMs": 9500, "endMs": 10000, "transcript": "Close, button"},
]


CAPTIONS = [(150, "Name on card, edit text, T Suleman"), (3050, "Card number, edit text"), (7150, "Submit, button"), (9400, "Close, button")]


def test_align_maps_transcript_words_to_captions_and_times_each_stop_from_the_focus_log():
    # The live API returns no turns in PUSH_TO_TALK mode and three pause-delimited turns in DIARIZATION (3 Nov), so the
    # flat transcript is aligned to the captions word by word; the captions carry the clock, the focus log the element.
    transcript = "Name on card, edit text, T Suleman Card number, edit text Submit, button Close, button"
    segments = align(transcript, CAPTIONS, STOPS, duration_ms=10000)
    assert segments["name"] == Segment(start_ms=0, end_ms=3000, text="Name on card, edit text, T Suleman")
    assert segments["card"] == Segment(start_ms=3000, end_ms=7000, text="Card number, edit text")
    assert segments["f5"] == Segment(start_ms=7000, end_ms=10000, text="Submit, button Close, button")  # every caption until the next stop belongs to the stop


def test_align_survives_asr_errors_and_drops_speech_before_the_first_stop():
    transcript = "Google Chrome name on card edit text T Suleman card card number edit text submit button button close button"
    segments = align(transcript, [(50, "Google Chrome")] + CAPTIONS, STOPS[1:], duration_ms=10000)  # 'name' is not a stop here
    assert "name" not in segments and "Google" not in " ".join(s.text for s in segments.values())  # spoken before the first stop: nobody's
    assert segments["card"].text == "card number edit text"  # the extra "card" was heard while the name field still had focus: it stays there
    assert segments["f5"].text == "submit button button close button" and (segments["f5"].start_ms, segments["f5"].end_ms) == (7000, 10000)
    assert align(transcript, [(50, "Google Chrome")] + CAPTIONS, STOPS[1:], duration_ms=90000)["f5"].end_ms == 12400  # the last stop ends 3 s after its last caption, not after a minute of silence
    assert align("", CAPTIONS, STOPS, duration_ms=10000) == {}
    assert align(transcript, [], STOPS, duration_ms=10000) == {}  # no captions: nothing to time the words with


def test_word_accuracy_identical_is_one():
    assert word_accuracy("Submit, button", "submit button") == 1.0
    assert word_accuracy("", "") == 0.0  # no reference, no claim


def test_word_accuracy_arithmetic():
    assert word_accuracy("name on edit text", "Name on card, edit text") == pytest.approx(0.8)  # one deletion over five reference words
    assert word_accuracy("name on cart edit text", "Name on card, edit text") == pytest.approx(0.8)  # one substitution
    assert word_accuracy("pay are one two four nine button", "Submit, button") == 0.0  # worse than empty is clamped, never negative


def test_transcript_agrees_submit_button():
    assert transcript_agrees(Segment(7200, 8900, "Submit, button"), "button", "Submit") is True
    assert transcript_agrees(Segment(0, 1, "submit button"), "button", "Submit") is True
    assert transcript_agrees(Segment(0, 1, "Pay R1,249, button"), "button", "Submit") is False
    assert transcript_agrees(Segment(0, 1, "radio button"), "radio", "") is True  # an unnamed control: the role is all there is to agree on
    assert transcript_agrees(None, "button", "Submit") is False


def _recording(voice_dir, page="checkout", seconds=10):
    voice_dir.mkdir(parents=True, exist_ok=True)
    with wave.open(str(voice_dir / f"{page}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000 * seconds)
    (voice_dir / f"{page}.json").write_text(json.dumps({"page": page, "clip": f"{page}.wav", "recorded_at": "2026-11-03T08:00:00+00:00", "duration_ms": seconds * 1000, "sample_rate": 16000, "stops": STOPS}))
    (voice_dir / f"{page}.captions.txt").write_text("150\tName on card, edit text, T Suleman\n3050\tCard number, edit text\n7150\tSubmit, button\n9400\tClose, button\n")
    return (voice_dir / f"{page}.wav").read_bytes()


async def test_missing_clip_returns_none(tmp_path):
    assert load_recording(tmp_path, "product") is None
    assert await transcribe_page(FakeMetaClient(tmp_path / "fixtures"), "product", voice_dir=tmp_path) is None  # pages without a recording skip Voice cleanly


async def test_transcribe_page_reads_the_clip_and_aligns_from_a_cached_fixture(tmp_path):
    wav = _recording(tmp_path / "voice")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    request = {"model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV", "mode": "PUSH_TO_TALK", "keywords": ["Submit", "Card number"]}
    raw = {"transcript": " ".join(t["transcript"] for t in TURNS), "audioDurationMs": 10000, "turns": TURNS, "_request_id": "req-asr-1"}
    (fixtures / f"{transcribe_key(request, wav)}.json").write_text(json.dumps(raw))
    client = FakeMetaClient(fixtures)
    voice = await transcribe_page(client, "checkout", keywords=["Submit", "Card number"], voice_dir=tmp_path / "voice", run_id="r1")
    assert voice.page == "checkout" and voice.clip_key == "checkout.wav" and voice.duration_ms == 10000 and voice.model == "muse-voice-transcribe-1.0"
    assert voice.segments["f5"] == Segment(7000, 10000, "Submit, button Close, button") and voice.transcript.startswith("Name on card")
    assert voice.word_accuracy == 1.0  # the transcript matches the captions VoiceOver wrote, word for word
    assert voice.request_id == "req-asr-1" and client.calls[-1]["mode"] == "PUSH_TO_TALK" and client.calls[-1]["keywords"] == ["Submit", "Card number"]
    assert client.trace.calls[-1].stage == "voice" and client.trace.calls[-1].model == "muse-voice-transcribe-1.0"


def test_voice_keywords_drop_names_over_the_api_limit_and_cap_the_count():
    # The live API refused the hero re-record of 3 Nov: "ASR keyword 7 exceeds the maximum length of 30 characters".
    from parity.voice import KEYWORD_MAX_CHARS, KEYWORDS_MAX, voice_keywords
    long = "Automatic payment methods filling is disabled"
    names = ["Submit", " Card number ", "", "Submit", long, "   "] + [f"n{i}" for i in range(60)]
    kws = voice_keywords(names)
    assert kws[:2] == ["Submit", "Card number"] and long not in kws and "" not in kws
    assert len(kws) == KEYWORDS_MAX and all(len(k) <= KEYWORD_MAX_CHARS for k in kws)
