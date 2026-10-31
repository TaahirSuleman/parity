"""Browser smoke test: the built SPA, served by FastAPI, replays the hero run end to end."""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "parity" / "static" / "index.html"
pytestmark = pytest.mark.skipif(not STATIC.exists(), reason="web/ not built (run `make build-web`)")


async def test_replay_shows_hero_card(page, server_url):
    await page.goto(server_url + "/")
    await page.get_by_role("button", name="Replay").click()
    await page.get_by_role("button", name="Run the audit").click()
    card = page.get_by_role("button", name="Pay R1,249").first
    await card.wait_for(timeout=30000)
    await card.click()
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('0 violations')", timeout=30000)
    assert 'button, "Submit"' in await page.locator("section[aria-labelledby='sr-h']").inner_text()
    assert "MUSE SPARK 1.3" in await page.locator("main").inner_text()
    header = await page.locator("header").inner_text()
    assert "verified" in header and "replay" in header.lower()


@pytest.mark.parametrize("state", ["idle", "running", "hero"])
async def test_workbench_itself_is_axe_clean(page, server_url, state):
    from tests.test_store_pages import AXE

    await page.goto(server_url + f"/?mock={state}")
    await page.get_by_role("heading", name="Parity").wait_for()
    await page.wait_for_timeout(400)  # let the 150 ms card fade-in finish; axe reads computed colours mid-animation otherwise
    await page.add_script_tag(path=str(AXE))
    result = await page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    assert [(v["id"], [n["target"] for n in v["nodes"]]) for v in result["violations"]] == []


async def test_workbench_is_keyboard_reachable_with_visible_focus(page, server_url):
    """Every stop in the tab ring is a real control and shows a visible focus indicator."""
    await page.goto(server_url + "/?mock=hero")
    await page.get_by_role("heading", name="Parity").wait_for()
    await page.wait_for_timeout(400)
    ring = []
    for _ in range(40):
        await page.keyboard.press("Tab")
        info = await page.evaluate(
            """() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const s = getComputedStyle(el);
                const visible = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none';
                return {tag: el.tagName, text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40), visible};
            }"""
        )
        if info is None:
            break  # wrapped past the last control
        ring.append(info)
    assert ring, "nothing on the workbench is focusable"
    bad_tags = [r for r in ring if r["tag"] not in {"BUTTON", "SELECT", "A", "INPUT", "SUMMARY", "TEXTAREA"}]
    assert not bad_tags, bad_tags
    invisible = [r for r in ring if not r["visible"]]
    assert not invisible, f"focus is invisible on: {invisible}"
    texts = " | ".join(r["text"] for r in ring)
    for control in ("Replay", "Live", "Run the audit", "Pay R1,249"):
        assert control in texts, f"{control!r} is not reachable by keyboard: {texts}"


async def test_replay_approve_records_the_decision(page, server_url):
    """The judge's path: replay, open the hero card, approve the fix with the suggested reason, see it recorded."""
    await page.goto(server_url + "/")
    await page.get_by_role("button", name="Replay").click()
    await page.get_by_role("button", name="Run the audit").click()
    card = page.get_by_role("button", name="Pay R1,249").first
    await card.wait_for(timeout=30000)
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('awaiting review')", timeout=30000)
    await card.click()
    approve = page.get_by_role("button", name="Approve fix")
    await approve.wait_for()
    assert await page.get_by_label("Reason").input_value()
    await approve.click()
    await page.get_by_text("Approved ·").wait_for(timeout=10000)
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('1 approved')", timeout=10000)
    assert "awaiting review" not in (await page.locator("header").inner_text()).lower()


async def test_trace_drawer_is_not_painted_over_by_panel_content(page, server_url):
    """At a short viewport the right panel's content must not bleed through the open trace drawer."""
    await page.set_viewport_size({"width": 1024, "height": 700})
    await page.goto(server_url + "/?mock=hero")
    await page.get_by_role("heading", name="Parity").wait_for()
    await page.get_by_role("button", name="Pay R1,249").first.click()  # the screen-reader panel fills with the judge's text
    await page.locator('button[aria-controls="trace-table"]').click()
    await page.locator("#trace-table tbody tr").first.wait_for()
    intruders = await page.evaluate(
        """() => {
            const rows = [...document.querySelectorAll('#trace-table tbody tr')].slice(0, 4);
            const bad = [];
            for (const tr of rows) {
              const r = tr.getBoundingClientRect(); const y = r.top + r.height / 2;
              for (let x = 60; x < innerWidth - 20; x += 40) {
                const e = document.elementsFromPoint(x, y)[0];
                if (e && !e.closest('#trace-table')) bad.push(`${x},${Math.round(y)}: ${e.tagName} ${(e.textContent || '').trim().slice(0, 24)}`);
              }
            }
            return bad;
        }"""
    )
    assert intruders == [], intruders


@pytest.mark.parametrize("scheme", ["light", "dark"])
async def test_finished_replay_is_axe_clean(page, server_url, scheme):
    """The brief says zero violations: that must hold after a run, with the diff, timeline and trace on screen."""
    from tests.test_store_pages import AXE

    await page.emulate_media(color_scheme=scheme)
    await page.goto(server_url + "/")
    await page.get_by_role("button", name="Replay").click()
    await page.get_by_role("button", name="Run the audit").click()
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('awaiting review')", timeout=60000)
    await page.get_by_role("button", name="Pay R1,249").first.click()
    await page.locator('button[aria-controls="trace-table"]').click()
    await page.wait_for_timeout(400)
    await page.add_script_tag(path=str(AXE))
    result = await page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    assert [(v["id"], [n["target"] for n in v["nodes"]]) for v in result["violations"]] == []


@pytest.mark.parametrize("width", [768, 390])
async def test_workbench_has_no_horizontal_scroll_on_narrow_screens(page, server_url, width):
    await page.set_viewport_size({"width": width, "height": 900})
    await page.goto(server_url + "/?mock=hero")
    await page.get_by_role("heading", name="Parity").wait_for()
    wide = await page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert wide <= 0, f"page scrolls sideways by {wide}px at {width}"


async def test_columns_stack_below_1280(page, server_url):
    """Below the desktop width the three panels stack instead of squeezing into unreadable columns."""
    await page.set_viewport_size({"width": 1024, "height": 900})
    await page.goto(server_url + "/?mock=hero")
    await page.get_by_role("heading", name="Parity").wait_for()
    tops = await page.evaluate("() => [...document.querySelectorAll('main > section')].map(s => Math.round(s.getBoundingClientRect().top))")
    assert len(tops) == 3 and len(set(tops)) >= 2, tops  # not all three side by side


async def test_run_link_reloads_the_run(page, server_url):
    """A finished run has a URL: reloading it brings the findings and decisions back."""
    await page.goto(server_url + "/")
    await page.get_by_role("button", name="Replay").click()
    await page.get_by_role("button", name="Run the audit").click()
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('awaiting review')", timeout=60000)
    assert "run=" in page.url
    await page.reload()
    await page.get_by_role("button", name="Pay R1,249").first.wait_for(timeout=30000)
    await page.wait_for_function("() => document.querySelector('header')?.textContent.includes('awaiting review')", timeout=30000)


async def test_eval_tab_shows_the_results_table(page, server_url):
    await page.goto(server_url + "/")
    await page.get_by_role("button", name=re.compile(r"^Eval")).click()
    await page.get_by_role("heading", name=re.compile(r"Parity vs axe-core")).wait_for(timeout=10000)
    assert "seeded faults" in await page.locator("main").inner_text()
