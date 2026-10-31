"""Run seer + comparator + judge + fixer once, live, on the recorded checkout capture; copy the cached responses into tests/fixtures/meta/.

Costs a few cents the first time; every later run is served from cache/.
Run: .venv/bin/python scripts/record_fixtures.py
"""

import asyncio
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parity.config import load_settings  # noqa: E402
from parity.meta.client import ListTraceSink, MetaClient  # noqa: E402
from parity.pipeline.comparator import compare  # noqa: E402
from parity.pipeline.fixer import propose_fix  # noqa: E402
from parity.pipeline.judge import judge  # noqa: E402
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
    verified = []
    rejected = []
    for c in candidates:
        r = verify(c, cap, verified)
        if r.passed:
            from parity.store.models import Finding
            node = next((n for n in cap.ax_nodes if n.backend_id == r.element.backend_id), None)
            verified.append(Finding(id=f"fx-{len(verified)+1}", run_id="fixture", step_index=0, sighted_text=c.sighted_text,
                                    sr_role=node.role if node else "", sr_name=node.name if node else "", why_it_matters=c.why_it_matters,
                                    bbox=c.bbox, element=r.element, verifier=r))
        else:
            rejected.append((c, r))
    client = MetaClient(settings, cache_dir=settings.cache_dir, trace=trace)
    judgements = {}
    try:
        for f in verified:
            judgements[f.id] = await judge(client, f, cap, run_id="fixture", model=settings.model_for("judge"), fallback_model=settings.model_for("judge_fallback"))
    finally:
        await client.aclose()
    hero = next((f for f in verified if f.element.dom_id == "f5"), None)
    fix = None
    if hero is not None:
        hero.judgement = judgements[hero.id]
        client = MetaClient(settings, cache_dir=settings.cache_dir, trace=trace)
        try:
            fix = await propose_fix(client, hero, cap, run_id="fixture", model=settings.model_for("fixer"))
        finally:
            await client.aclose()
    (FIX / "meta").mkdir(exist_ok=True)
    manifest = {}
    for call in trace.calls:
        src = settings.cache_dir / f"{call.prompt_sha256}.json"
        shutil.copy(src, FIX / "meta" / src.name)
        if call.stage not in manifest and (call.stage != "judge" or (hero and call.step_index == 0 and manifest.get('judge') is None and len([c for c in trace.calls if c.stage == 'judge']) >= 1)):
            manifest[call.stage] = src.name
        print(f"{call.stage}: model={call.model} request_id={call.request_id} tokens={call.total_tokens} latency_ms={call.latency_ms} cost=${call.cost_usd:.4f} cache_hit={call.cache_hit}")
    (FIX / "meta" / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\n{len(percepts)} percepts; {len(candidates)} candidates; manifest: {manifest}")
    for f in verified:
        j = judgements[f.id]
        print(f"  [PASS] {f.element.dom_id or '-':>5} | sighted={f.sighted_text[:34]!r:38} sr={f.sr_role}, {f.sr_name!r:16} judge={j.is_barrier} {j.severity} {[w.sc for w in j.wcag]}")
    for c, r in rejected:
        print(f"  [fail] {'-':>5} | sighted={c.sighted_text[:34]!r:38} sr={c.sr_quote[:28]!r:30} {r.feedback}")
    if fix is not None:
        print(f"\nfixer on the hero: {fix.explanation}\n  before: {fix.before_html[:120]}\n  after:  {fix.after_html[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
