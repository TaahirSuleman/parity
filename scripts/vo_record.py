#!/usr/bin/env python3
"""Record one store page as a VoiceOver user hears it: the WAV, the focus log and the captions, all on one clock.

    .venv/bin/python scripts/vo_record.py --check                  preflight: the server, VoiceOver, AppleScript control, the loopback device
    .venv/bin/python scripts/vo_record.py checkout --seconds 90    record store/voice/checkout.{wav,json,captions.txt}

The steps around it (BlackHole, the Multi-Output Device, pasting the focus logger, what to press) are in docs/voice-recording.md.
"""

from __future__ import annotations

import argparse
import array
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parity.voice import parse_captions, write_recording_sidecars  # noqa: E402

CAPTIONS_SH = ROOT / "scripts" / "vo_captions.sh"
TARGET_RATE = 16_000  # what Voice Transcribe wants: 16 kHz mono 16-bit (skill meta-model-api)
SILENCE_PEAK = 300  # an int16 peak below this means nothing reached the loopback device (wrong output device, or a denied microphone permission)
PHRASE = 'tell application "VoiceOver" to return content of last phrase'
MARKER = 'tell application "VoiceOver" to output "Parity recording started"'


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read() or b"{}")


def preflight(server: str, device: str) -> list[str]:
    problems: list[str] = []
    try:
        _get(f"{server}/api/voice/focuslog")
    except urllib.error.HTTPError as e:
        problems.append(f"{server}/api/voice/focuslog answered {e.code}: start the server with PARITY_VOICE_FOCUSLOG=1 (`PARITY_VOICE_FOCUSLOG=1 make serve`)")
    except (urllib.error.URLError, OSError) as e:
        problems.append(f"no server at {server} ({e}): run `PARITY_VOICE_FOCUSLOG=1 make serve` first")
    if subprocess.run(["pgrep", "-x", "VoiceOver"], capture_output=True).returncode != 0:
        problems.append("VoiceOver is not running: press Cmd+F5")
    elif subprocess.run(["osascript", "-e", PHRASE], capture_output=True, text=True).returncode != 0:
        problems.append("VoiceOver refuses AppleScript: tick 'Allow VoiceOver to be controlled with AppleScript' in VoiceOver Utility → General")
    try:
        import sounddevice as sd
    except ImportError:
        problems.append("sounddevice is not installed: uv pip install --python .venv/bin/python -e '.[voice]'")
        return problems
    try:
        sd.query_devices(device, "input")
    except ValueError:
        names = ", ".join(d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0)
        problems.append(f"no input device named {device!r} (inputs seen: {names}): install BlackHole and pick the Multi-Output Device as the system output")
    return problems


def _input_rate(sd, device: str) -> int:
    try:
        sd.check_input_settings(device=device, channels=1, samplerate=TARGET_RATE, dtype="int16")
        return TARGET_RATE
    except Exception:  # the device does not do 16 kHz: record at its own rate and let afconvert resample
        return int(sd.query_devices(device, "input")["default_samplerate"])


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def record(device: str, seconds: int, wav_path: Path, captions_path: Path, *, marker: bool) -> tuple[int, int, int]:
    """Record ``seconds`` of ``device`` to ``wav_path`` while the captions poller runs. Returns (t0_ms, duration_ms, peak)."""
    import sounddevice as sd

    rate = _input_rate(sd, device)
    chunks: list[bytes] = []

    def on_audio(indata, frames, _time, status):
        if status:
            print(f"audio: {status}", file=sys.stderr)
        chunks.append(bytes(indata))

    poller = subprocess.Popen(["/bin/zsh", str(CAPTIONS_SH), str(seconds + 1), str(captions_path)])
    with sd.RawInputStream(device=device, channels=1, samplerate=rate, dtype="int16", callback=on_audio):
        t0_ms = int(time.time() * 1000)
        if marker:
            subprocess.Popen(["osascript", "-e", MARKER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(seconds)
    duration_ms = int(time.time() * 1000) - t0_ms
    poller.wait(timeout=seconds + 10)
    pcm = b"".join(chunks)
    samples = array.array("h")
    samples.frombytes(pcm)
    peak = max((abs(s) for s in samples), default=0)
    if rate == TARGET_RATE:
        _write_wav(wav_path, pcm, rate)
    else:
        native = wav_path.with_suffix(f".{rate}.wav")
        _write_wav(native, pcm, rate)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{TARGET_RATE}", "-c", "1", str(native), str(wav_path)], check=True)
        native.unlink()
    return t0_ms, duration_ms, peak


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", nargs="?", help="the store page to record: checkout, product or cart")
    ap.add_argument("--seconds", type=int, default=90, help="length of the clip (default 90; a Tab walk of the checkout takes about 60)")
    ap.add_argument("--device", default="BlackHole 2ch", help="the loopback input device (default: BlackHole 2ch)")
    ap.add_argument("--server", default="http://127.0.0.1:8080", help="the local Parity server started with PARITY_VOICE_FOCUSLOG=1")
    ap.add_argument("--out", default=str(ROOT / "store" / "voice"), help="where the three files go (default store/voice)")
    ap.add_argument("--countdown", type=int, default=5, help="seconds to switch to the browser before the clip starts (default 5)")
    ap.add_argument("--no-marker", action="store_true", help="do not have VoiceOver say 'Parity recording started' as the clip begins")
    ap.add_argument("--check", action="store_true", help="run the preflight checks and exit")
    args = ap.parse_args(argv)
    if not args.check and not args.page:
        ap.error("name the page to record, or pass --check")

    problems = preflight(args.server, args.device)
    for problem in problems:
        print(f"✗ {problem}")
    if problems:
        return 2
    print("✓ the server, VoiceOver, AppleScript control and the input device are ready")
    if args.check:
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    urllib.request.urlopen(urllib.request.Request(f"{args.server}/api/voice/focuslog", method="DELETE"), timeout=5).read()
    for n in range(args.countdown, 0, -1):
        print(f"recording {args.page} for {args.seconds} s in {n}: switch to the browser", flush=True)
        time.sleep(1)
    wav = out / f"{args.page}.wav"
    raw_captions = out / f".{args.page}.captions.raw.tsv"
    t0_ms, duration_ms, peak = record(args.device, args.seconds, wav, raw_captions, marker=not args.no_marker)
    entries = _get(f"{args.server}/api/voice/focuslog")["entries"]
    captions = parse_captions(raw_captions.read_text()) if raw_captions.exists() else []
    raw_captions.unlink(missing_ok=True)
    doc = write_recording_sidecars(out, args.page, t0_ms=t0_ms, duration_ms=duration_ms, sample_rate=TARGET_RATE, focus_entries=entries, captions=captions)
    kept = parse_captions((out / f"{args.page}.captions.txt").read_text())
    print(f"{wav}: {duration_ms / 1000:.1f} s, peak {peak}/32767")
    print(f"{out / (args.page + '.json')}: {len(doc['stops'])} focus stops  {out / (args.page + '.captions.txt')}: {len(kept)} captions")
    for stop in doc["stops"]:
        print(f"  {stop['t_ms']:>7} ms  {stop['dom_id']}")
    ok = True
    if peak < SILENCE_PEAK:
        print("✗ the clip is silent: is the Multi-Output Device the system output, and did Terminal get the microphone permission?")
        ok = False
    if not doc["stops"]:
        print("✗ no focus stops: paste scripts/vo_focus_logger.js into the page's console before recording, and start the server with PARITY_VOICE_FOCUSLOG=1")
        ok = False
    if not kept:
        print("✗ no captions: VoiceOver said nothing new during the clip, or AppleScript control is off")
        ok = False
    if ok:
        print(f"listen: afplay {wav}   then commit the three files")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
