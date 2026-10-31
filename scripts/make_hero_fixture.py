"""Build web/src/fixtures/hero.json offline: the real pipeline over the store page with the recorded
Meta responses (tests/fixtures/meta), so the mock workbench shows real data without a key.

Run: .venv/bin/python scripts/make_hero_fixture.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright  # noqa: E402

from parity.api.events import EventBus  # noqa: E402
from parity.config import load_settings  # noqa: E402
from parity.flows import FLOWS  # noqa: E402
from parity.meta.client import TraceRouter  # noqa: E402
from parity.meta.fake import FakeMetaClient  # noqa: E402
from parity.pipeline.runner import run_single_page  # noqa: E402
from parity.store.blob import LocalBlobStore  # noqa: E402
from parity.store.bundle import RunBundle  # noqa: E402
from parity.store.index import RunIndex  # noqa: E402

META = ROOT / "tests" / "fixtures" / "meta"
OUT = ROOT / "web" / "src" / "fixtures" / "hero.json"


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = load_settings(env={"PARITY_DATA_DIR": tmp})
        bundle = RunBundle(LocalBlobStore(Path(tmp)))
        index = RunIndex(Path(tmp) / "index.db")
        await index.init()
        client = FakeMetaClient(META, trace=TraceRouter())
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 720})

            async def factory():
                return page

            run = await run_single_page(settings, client, EventBus(bundle), bundle, index, FLOWS["checkout"], base_url=ROOT.as_uri(), run_id="hero-fixture", page_factory=factory)
            await browser.close()
        await index.close()
        loaded = await bundle.load(run.id)
    assert run.status == "done", run.error
    data = {
        "run": loaded.run.model_dump(mode="json"), "steps": [s.model_dump(mode="json") for s in loaded.steps],
        "findings": [f.model_dump(mode="json") for f in loaded.findings], "rejected": [r.model_dump(mode="json") for r in loaded.rejected],
        "trace": [c.model_dump(mode="json") for c in loaded.trace],
        "events": [{**e.data, "type": e.type, "run_id": e.run_id, "at": e.at.isoformat()} for e in loaded.events],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    print(f"{run.status}: {run.findings_verified} verified, {run.findings_rejected} rejected, {len(loaded.events)} events, {len(loaded.trace)} calls -> {OUT.relative_to(ROOT)}")
    for f in loaded.findings:
        j = f.judgement
        print(f"  {f.element.dom_id:>5} {f.sighted_text[:30]!r:34} {f.sr_role}, {f.sr_name!r:16} {j and j.severity} {j and [w.sc for w in j.wcag]}")


if __name__ == "__main__":
    asyncio.run(main())
