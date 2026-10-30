"""Record the checkout capture as a fixture for the deterministic verifier tests.

Run: .venv/bin/python tests/record_capture.py
Writes tests/fixtures/capture_checkout.json and capture_checkout.png.
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from parity.pipeline.capture import capture

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto((ROOT / "store" / "checkout.html").as_uri())
        cap = await capture(page, step_index=0)
        await browser.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "capture_checkout.json").write_text(cap.model_dump_json(indent=1))
    (OUT / "capture_checkout.png").write_bytes(cap.screenshot_png)
    print(f"wrote {len(cap.ax_nodes)} AX nodes, {len(cap.axe_violations)} axe violations")


if __name__ == "__main__":
    asyncio.run(main())
