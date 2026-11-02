# Voice recording: the kit (doc 20 Task 26; spec §16)

What it produces, per store page, in `store/voice/`:

| File | What | Clock |
|---|---|---|
| `<page>.wav` | VoiceOver reading the page, 16 kHz mono 16-bit (what Voice Transcribe takes) | starts at 0 |
| `<page>.json` | every focus stop: `{"t_ms", "dom_id", "event"}` in order, plus `recorded_at`, `duration_ms` | ms since the clip started |
| `<page>.captions.txt` | every phrase VoiceOver spoke, one `<t_ms><TAB><phrase>` line each: the reference for `word_accuracy` (Task 27) | ms since the clip started |

The three sit on one clock because the kit records the WAV itself (`scripts/vo_record.py`) and timestamps the other two against the
clip's start: the logger in the page posts `Date.now()` for each focus stop, and the captions poller writes the same epoch ms for each
phrase. Alignment (Task 27) assigns each transcript turn to the element focused at that moment.

## Once per Mac (about ten minutes)

1. **BlackHole**, the free loopback audio driver (MIT, existential.audio): in a Terminal, `brew install --cask blackhole-2ch` (asks for your
   password). If "BlackHole 2ch" does not appear in step 2, run `sudo killall coreaudiod` and look again.
2. **A Multi-Output Device**, so you still hear VoiceOver while the kit records the copy: open Audio MIDI Setup (Applications → Utilities),
   press "+" at the bottom left → "Create Multi-Output Device"; tick "MacBook Air Speakers" and "BlackHole 2ch"; tick "Drift Correction" on
   the BlackHole row. Set the speaker volume you want **before** step 3: a Multi-Output Device has no volume control.
3. **System Settings → Sound → Output → "Multi-Output Device".** Switch back to the speakers when you are done recording.
4. **VoiceOver Utility** (VoiceOver on with Cmd+F5, then VO+F8, where VO = Control+Option):
   - General → tick **"Allow VoiceOver to be controlled with AppleScript"** (password). This is what lets `vo_captions.sh` read what was spoken.
   - Speech → Rate: a typical user's speed, about the middle of the slider (45–55). Not the fast setting: the transcriber must understand it.
   - Verbosity: leave the defaults.
5. **The recorder's dependency:** `uv pip install --python .venv/bin/python -e ".[voice]"` (sounddevice; PortAudio comes inside the wheel).
6. **Microphone permission:** the first recording makes macOS ask "Terminal would like to access the microphone". Allow it: BlackHole counts
   as a microphone. If you clicked "Don't Allow", fix it under System Settings → Privacy & Security → Microphone.

## Each recording (about five minutes)

1. Terminal 1: `PARITY_VOICE_FOCUSLOG=1 make serve` (the local server on :8080 with the focus-log endpoint on; it never exists on the hosted app).
2. Terminal 2: `.venv/bin/python scripts/vo_record.py --check`. It must print one line of ticks: the server, VoiceOver, AppleScript control,
   the input device. Each cross says what to fix.
3. **Chrome** (Safari skips links on Tab unless "Press Tab to highlight each item" is on in its Advanced settings): open
   `http://127.0.0.1:8080/store/checkout.html`. Open the console (Cmd+Option+J; type `allow pasting` and Enter if Chrome asks), paste the whole
   of `scripts/vo_focus_logger.js`, Enter. It prints "Parity focus logger: on". Close the console (Cmd+Option+J again) and click once on the
   "Your order" heading so the page has the keyboard.
4. VoiceOver on (Cmd+F5) if it is not already.
5. Terminal 2: `.venv/bin/python scripts/vo_record.py checkout --seconds 90`. During the five-second countdown, Cmd+Tab to Chrome. VoiceOver
   says "Parity recording started" as the clip begins (it is the first caption; `--no-marker` drops it).
6. **Press Tab, wait until VoiceOver has finished the phrase, press Tab again.** Nothing else: no mouse, no typing, no Shift+Tab. The checkout
   has fourteen stops, in this order:
   Shop · Cart · Returns policy · Note for the courier · Name on card · Card number · Expiry · "Click here" (the Terms link) · **Submit (the hero,
   `#f5`)** · Close (`#f6`) · Save for later · CVV · Help · "Button" (Pay with wallet).
   About a minute. Then wait; the clip ends by itself and the summary prints.
7. Read the summary: the peak must be well above 300, the stops must list the fourteen ids in that order, and the captions count should be
   about fifteen. Listen once: `afplay store/voice/checkout.wav`. Open `store/voice/checkout.captions.txt`: it must contain `Submit, button`.
8. Commit the three files:
   `git add store/voice/checkout.wav store/voice/checkout.json store/voice/checkout.captions.txt && git commit -m "voice: checkout clip, focus log and captions (VoiceOver, Chrome)"`.
9. Product and cart if time allows: the same with `product` or `cart`. Their findings are mostly images, which Tab skips, so walk those with
   VO+Right (Control+Option+Right) instead: the captions carry every phrase, and the focus log carries the stops that are focusable.

## What can go wrong

| Symptom | Cause and fix |
|---|---|
| "the clip is silent" | The system output is not the Multi-Output Device, or Terminal was denied the microphone. Fix, re-record. |
| "no focus stops" | The logger was not pasted, or the page was reloaded after pasting (paste again), or the server runs without `PARITY_VOICE_FOCUSLOG=1`. |
| "no captions" / `--check` fails on AppleScript | "Allow VoiceOver to be controlled with AppleScript" is off, or VoiceOver was turned on after the check: tick it, press Cmd+F5 twice. |
| The clip starts with "Terminal" or a long Chrome announcement | You switched late. Harmless: the captions mark it, and the first focus stop is where alignment starts. |
| Two consecutive stops have the same name (two "Close, button") | The captions log a phrase only when it changes, so the second is missing there; the focus log still has both stops. |
| VoiceOver reads the Terminal's countdown | Switch to Chrome during the countdown, not after. Or raise `--countdown`. |

## Why not a synthesizer

`say -o` would give clean audio from the same voice, but the badge on the finding card says *real VoiceOver audio*, and the point of G-V is
whether the model transcribes what a screen-reader user actually hears, pauses, role suffixes and all. The clip is VoiceOver, recorded.
