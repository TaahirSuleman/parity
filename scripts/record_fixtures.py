"""Run seer + comparator once, live, on the recorded checkout capture; copy the cached responses into tests/fixtures/meta/.

Costs a few cents the first time; every later run is served from cache/.
Run: .venv/bin/python scripts/record_fixtures.py
"""

import asyncio
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parity.config import load_settings  # noqa: E402
from parity.meta.client import ListTraceSink, MetaClient  # noqa: E402
from parity.pipeline.comparator import compare  # noqa: E402
from parity.pipeline.seer import see  # noqa: E402
from parity.pipeline.verifier import verify  # noqa: E402
from parity.store.models import Capture  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


async def main() -> None:
    settings = load_settings()
    assert settings.has_key, "MODEL_API_KEY missing"
    cap = Capture.model_validate_json((FIX / "capture_checkout.json").read_text())
    cap.screenshot_png = (FIX / "capture_checkout.png").read_bytes()
    trace = ListTraceSink()
    client = MetaClient(settings, cache_dir=settings.cache_dir, trace=trace)
    model = settings.model_for("comparator")
    try:
        percepts = await see(client, cap, run_id="fixture", model=model)
        candidates = await compare(client, cap, percepts, run_id="fixture", model=model)
    finally:
        await client.aclose()
    (FIX / "meta").mkdir(exist_ok=True)
    for call in trace.calls:
        src = settings.cache_dir / f"{call.prompt_sha256}.json"
        shutil.copy(src, FIX / "meta" / src.name)
        print(f"{call.stage}: model={call.model} request_id={call.request_id} tokens={call.total_tokens} latency_ms={call.latency_ms} cost=${call.cost_usd:.4f} cache_hit={call.cache_hit}")
    print(f"\n{len(percepts)} percepts; {len(candidates)} candidates:")
    verified = []
    for c in candidates:
        r = verify(c, cap, verified)
        mark = "PASS" if r.passed else "fail"
        dom = r.element.dom_id if r.element else "-"
        box = c.bbox and (c.bbox.x_min, c.bbox.y_min, c.bbox.x_max, c.bbox.y_max)
        print(f"  [{mark}] {dom:>5} {str(box):24} | sighted={c.sighted_text[:34]!r:38} sr={c.sr_quote[:28]!r:30} {'' if r.passed else r.feedback}")
        if r.passed:
            from parity.store.models import Finding
            verified.append(Finding(id=str(len(verified)), run_id="fixture", step_index=0, sighted_text=c.sighted_text, sr_role="", sr_name="", bbox=c.bbox, element=r.element, verifier=r))


if __name__ == "__main__":
    asyncio.run(main())
