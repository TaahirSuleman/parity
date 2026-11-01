"""Render docs/img/architecture.svg to docs/img/architecture.png with Playwright's Chromium (no new dependencies).

Run: .venv/bin/python scripts/render_architecture.py
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "img" / "architecture.svg"
OUT = ROOT / "docs" / "img" / "architecture.png"
PUBLIC = ROOT / "web" / "public" / "architecture.png"  # served at /architecture.png for the Eval tab's card


async def main() -> int:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1300, "height": 620}, device_scale_factor=2)
        await page.set_content(f"<!doctype html><html><body style=\"margin:0;background:#fff\">{SRC.read_text()}</body></html>", wait_until="load")
        await page.locator("svg").first.screenshot(path=str(OUT))
        PUBLIC.parent.mkdir(parents=True, exist_ok=True)
        PUBLIC.write_bytes(OUT.read_bytes())
        box = await page.locator("svg").first.bounding_box()
        await browser.close()
    print(json.dumps({"png": str(OUT.relative_to(ROOT)), "size_px": [round(box["width"]), round(box["height"])], "bytes": OUT.stat().st_size}))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
