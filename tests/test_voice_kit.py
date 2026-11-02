"""The recording kit's browser and shell parts (Task 26): the focus logger and the VoiceOver captions poller."""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGGER = ROOT / "scripts" / "vo_focus_logger.js"
CAPTIONS = ROOT / "scripts" / "vo_captions.sh"
RECORDER = ROOT / "scripts" / "vo_record.py"


async def _logger_page(page, store_url):
    """The checkout page with the logger pasted in; every POST it makes is captured here instead of reaching a server."""
    posted = []

    async def capture(route, request):
        posted.append(request.post_data_json)
        await route.fulfill(status=200, body='{"count": 1}', content_type="application/json")

    await page.route("**/api/voice/focuslog", capture)
    await page.goto(store_url + "checkout.html")
    await page.add_script_tag(path=str(LOGGER))
    return posted


async def _until(predicate, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not predicate():
        assert time.monotonic() < deadline, "timed out waiting for the logger's POSTs"
        await asyncio.sleep(0.05)


async def test_focus_logger_posts_the_dom_id_of_each_tab_stop(page, store_url):
    posted = await _logger_page(page, store_url)
    await page.focus("#exp")
    await page.keyboard.press("Tab")  # the Terms link (f4)
    await page.keyboard.press("Tab")  # the Submit button (f5)
    await _until(lambda: len(posted) >= 3)
    assert [e["dom_id"] for e in posted] == ["exp", "f4", "f5"]
    assert all(e["event"] == "focusin" and isinstance(e["t_ms"], int) for e in posted)
    assert posted[0]["t_ms"] <= posted[1]["t_ms"] <= posted[2]["t_ms"]
    assert await page.evaluate("window.__parityFocusLog.length") == 3


async def test_focus_logger_falls_back_to_the_capture_css_path_without_an_id(page, store_url):
    posted = await _logger_page(page, store_url)
    await page.focus("nav >> a >> nth=1")  # "Cart": no id
    await _until(lambda: len(posted) >= 1)
    assert posted[0]["dom_id"] == "body > header:nth-of-type(1) > nav:nth-of-type(1) > a:nth-of-type(2)"


async def test_focus_logger_reports_aria_activedescendant_changes(page, store_url):
    posted = await _logger_page(page, store_url)
    await page.evaluate("document.getElementById('order-note').setAttribute('aria-activedescendant', 'step-payment')")
    await _until(lambda: len(posted) >= 1)
    assert posted[0]["dom_id"] == "step-payment" and posted[0]["event"] == "activedescendant"


async def test_focus_logger_pasted_twice_logs_once(page, store_url):
    posted = await _logger_page(page, store_url)
    await page.add_script_tag(path=str(LOGGER))
    await page.focus("#name")
    await _until(lambda: len(posted) >= 1)
    await asyncio.sleep(0.3)
    assert len(posted) == 1


def test_vo_captions_script_logs_only_phrases_that_change_after_it_starts(tmp_path):
    """A stub osascript stands in for VoiceOver: the phrase current at the first poll is the baseline, not a caption."""
    stub = tmp_path / "bin" / "osascript"
    stub.parent.mkdir()
    stub.write_text(
        "#!/bin/sh\n"
        'n=$(cat "$VO_STUB_COUNTER" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$VO_STUB_COUNTER"\n'
        "case $n in 1) echo 'Terminal';; 2) echo 'Google Chrome';; 3|4) echo 'Name on card, edit text';; *) echo 'Submit, button';; esac\n"
    )
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}", "VO_STUB_COUNTER": str(tmp_path / "n")}
    out = tmp_path / "captions.tsv"
    before = int(time.time() * 1000)
    subprocess.run(["/bin/zsh", str(CAPTIONS), "1", str(out)], env=env, check=True, timeout=15)
    after = int(time.time() * 1000)
    rows = [line.split("\t", 1) for line in out.read_text().splitlines()]
    assert [text for _, text in rows] == ["Google Chrome", "Name on card, edit text", "Submit, button"]
    assert all(before <= int(ms) <= after for ms, _ in rows)


def test_vo_captions_script_fails_loudly_when_voiceover_cannot_be_reached(tmp_path):
    stub = tmp_path / "bin" / "osascript"
    stub.parent.mkdir()
    stub.write_text("#!/bin/sh\necho 'execution error: VoiceOver got an error' >&2\nexit 1\n")
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}"}
    done = subprocess.run(["/bin/zsh", str(CAPTIONS), "1", str(tmp_path / "out.tsv")], env=env, capture_output=True, text=True, timeout=15)
    assert done.returncode == 3 and "VoiceOver" in done.stderr


def test_vo_record_help_needs_no_audio_hardware():
    done = subprocess.run([sys.executable, str(RECORDER), "--help"], capture_output=True, text=True, timeout=30, env={**os.environ, "PYTHONPATH": str(ROOT)})
    assert done.returncode == 0 and "--seconds" in done.stdout and "--check" in done.stdout
