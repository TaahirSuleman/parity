"""Would SAM 3.1's tighter boxes change what Parity reports? A replay, not a walk: every candidate and every Seer percept of the three recorded 4 Nov runs
is sent to sam-3.1 as a box prompt on its own recorded screenshot, then the Verifier's six checks and the harness's match() run again on the boxes SAM returns.
The Comparator is not re-run, so this says what SAM does to the boxes it was given, not what a Comparator shown SAM's boxes would propose.

  .venv/bin/python -m eval.sam_boxes   # writes cache/model-sweep/sam-boxes.json; --model-sweep then carries it
Nothing here is imported by parity/."""
from __future__ import annotations

import asyncio
import base64
import json
import math
import re
import statistics
import struct
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from eval.model_sweep import SWEEP_DIR, score_set
from parity.meta.client import ListTraceSink, MetaClient, MetaError, text_of
from parity.pipeline.verifier import NOT_ANNOUNCED, iou, locate, normalise, verify
from parity.store.models import AxeViolation, AxNode, BBox, Candidate, Capture, Percept

SAM = "sam-3.1"
MAX_OBJECTS = 16  # per frame, in Meta's limits for the model
CONCEPTS = ("button", "link", "icon", "price", "star", "logo", "input field", "photo", "image", "text")  # noun phrases, on one product screen
PRICE_PER_IMAGE = 2.50 / 1000  # from our 26 Oct notes on the model; parity/meta/pricing.py has no SAM row and /v1/models carries no prices
_BOX = re.compile(r"(\d+)<\|box;x1=([\d.]+);y1=([\d.]+);x2=([\d.]+);y2=([\d.]+);w=([\d.]+);h=([\d.]+)")


def box_token(obj_id: int, box: BBox, width: int, height: int) -> str:
    """A 0-1000 box as SAM's prompt token: source pixels, inclusive corners, at least one pixel each way, inside the frame."""
    x1 = max(0, min(width - 1, math.floor(box.x_min * width / 1000)))
    y1 = max(0, min(height - 1, math.floor(box.y_min * height / 1000)))
    x2 = max(x1, min(width - 1, math.ceil(box.x_max * width / 1000) - 1))
    y2 = max(y1, min(height - 1, math.ceil(box.y_max * height / 1000) - 1))
    return f"{obj_id}<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={width};h={height}|>"


def box_prompt(boxes: dict[int, BBox], width: int, height: int) -> str:
    return "<0f>" + ",".join(box_token(i, b, width, height) for i, b in boxes.items())


def parse_boxes(text: str) -> dict[int, BBox]:
    """{object id: box on the 0-1000 grid}. Inclusive pixel corners back to exclusive edges; an object SAM did not return is simply absent."""
    out: dict[int, BBox] = {}
    for m in _BOX.finditer(text or ""):
        obj, x1, y1, x2, y2, w, h = int(m[1]), *map(float, m.groups()[1:])
        out[obj] = BBox(x_min=round(x1 * 1000 / w), y_min=round(y1 * 1000 / h), x_max=round((x2 + 1) * 1000 / w), y_max=round((y2 + 1) * 1000 / h))
    return out


def png_size(png: bytes) -> tuple[int, int]:
    return struct.unpack(">II", png[16:24])


def chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def replay_screen(candidates: list[Candidate], capture: Capture, percepts: list[Percept] | None, boxes: dict[int, BBox] | None, prior: list) -> list[dict[str, Any]]:
    """Each candidate through the Verifier in the recorded order, with SAM's box where there is one (`boxes` keyed by position; None: the recorded box)."""
    out = []
    for i, cand in enumerate(candidates):
        box = (boxes or {}).get(i, cand.bbox)
        result = verify(cand.model_copy(update={"bbox": box}), capture, prior, percepts)
        finding = None
        if result.passed and result.element is not None:
            finding = SimpleNamespace(id=f"{capture.step_index}-{i}", element=result.element, sighted_text=cand.sighted_text, bbox=box, step_index=capture.step_index)
            prior.append(finding)
        pool = capture.silent_nodes if normalise(cand.sr_quote) == NOT_ANNOUNCED else capture.ax_nodes
        node = locate(box, pool)
        out.append({"passed": bool(finding), "failed": [k for k, c in result.checks.items() if not c.passed], "node": node.css_path if node else None,
                    "iou_node": iou(box, node.bbox) if node is not None and box is not None and node.bbox is not None else None, "finding": finding})
    return out


def _recorded_candidates(events: list, capture: Capture, step_index: int, findings_by_id: dict[str, Any]) -> list[Candidate]:
    """The candidates of a screen in the order the Verifier saw them. A verified one has no candidate on record: its quote is the node it matched."""
    out = []
    for e in events:
        if e.type != "verifier.result" or e.data.get("index") != step_index:
            continue
        if not e.data.get("passed"):
            out.append(Candidate.model_validate(e.data["candidate"]))
            continue
        f = findings_by_id[e.data["finding_id"]]
        silent = next((n for n in capture.silent_nodes if n.backend_id == f.element.backend_id), None)
        node = next((n for n in capture.ax_nodes if n.backend_id == f.element.backend_id), None)
        quote = NOT_ANNOUNCED if silent is not None and node is None else f'{node.role}, "{node.name}"' if node is not None else ""
        out.append(Candidate(step_index=step_index, sighted_text=f.sighted_text, sr_quote=quote, why_it_matters=f.why_it_matters, bbox=f.bbox, attempt=e.data.get("attempt", 1)))
    return out


def _load_capture(run_dir: Path, step) -> Capture:
    step_dir = run_dir / "steps" / str(step.index)
    ax = json.loads((step_dir / "ax.json").read_text())
    axe_doc = json.loads((step_dir / "axe.json").read_text())
    violations = axe_doc.get("violations", axe_doc) if isinstance(axe_doc, dict) else axe_doc
    return Capture(step_index=step.index, url=step.url, viewport=tuple(step.viewport), screenshot_png=(step_dir / "screenshot.png").read_bytes(),
                   ax_nodes=[AxNode.model_validate(n) for n in ax["ax_nodes"]], silent_nodes=[AxNode.model_validate(n) for n in ax["silent_nodes"]],
                   axe_violations=[AxeViolation.model_validate(v) for v in violations])


def score(findings_by_page: dict[str, list], labels: list[dict], n_faults: int, n_clean: int) -> dict[str, Any]:
    from eval.harness import labels_for, match

    hits, matched, n, fp = [], 0, 0, []
    for page, findings in findings_by_page.items():
        m = match(findings, labels_for(labels, page))
        hits += sorted(f"{page}#{h}" for h in m.hits)
        matched += m.matched
        n += m.n_findings
        fp += [m.by_finding[i] for i in m.fp_on_clean]
    return {"hits": hits, "n": n, "matched": matched, **score_set(hits=len(hits), matched=matched, n=n, fp_clean_distinct=len(set(fp)), n_faults=n_faults, n_clean=n_clean)}


async def run(client, data_dir: Path, run_ids: dict[int, dict[str, str]], labels: list[dict], log=print) -> dict[str, Any]:
    from parity.store.bundle import RunBundle
    from parity.store.blob import LocalBlobStore

    bundle = RunBundle(LocalBlobStore(data_dir))
    n_faults, n_clean = sum(not r["clean"] for r in labels), sum(bool(r["clean"]) for r in labels)
    started, images, request_ids, runs, recorded_verified, base_results, sam_results, no_box = time.monotonic(), 0, [], [], 0, [], [], 0
    percept_iou_recorded, percept_iou_sam, percepts_total, seen_verified = [], [], 0, 0
    for i in sorted(run_ids):
        base_by_page, sam_by_page, seen_by_page = {}, {}, {}
        for page, run_id in run_ids[i].items():
            loaded = await bundle.load(run_id)
            recorded_verified += len(loaded.findings)
            by_id = {f.id: f for f in loaded.findings}
            base_prior, sam_prior, seen_prior = [], [], []
            for step in loaded.steps:
                cap = _load_capture(data_dir / "runs" / run_id, step)
                seer = next((e for e in loaded.events if e.type == "seer.done" and e.data.get("index") == step.index), None)
                percepts = [Percept.model_validate(p) for p in seer.data["percepts"]] if seer else None
                cands = _recorded_candidates(loaded.events, cap, step.index, by_id)
                width, height = png_size(cap.screenshot_png)
                url = "data:image/png;base64," + base64.b64encode(cap.screenshot_png).decode()

                async def tighten(boxes: dict[int, BBox]) -> dict[int, BBox]:
                    nonlocal images
                    out: dict[int, BBox] = {}
                    for part in chunks(list(boxes), MAX_OBJECTS):
                        body = {"model": SAM, "input": [{"role": "user", "content": [{"type": "input_text", "text": box_prompt({k + 1: boxes[k] for k in part}, width, height)}, {"type": "input_image", "image_url": url}]}]}
                        resp = await client.responses(body, stage="sam-boxes", run_id="sam-boxes", step_index=step.index)
                        images += int((resp.raw.get("usage") or {}).get("images_processed", 1))
                        request_ids.append(resp.request_id)
                        out.update({obj - 1: b for obj, b in parse_boxes(text_of(resp.raw)).items()})
                    return out

                tight = await tighten({k: c.bbox for k, c in enumerate(cands) if c.bbox is not None})
                tight_p = await tighten(dict(enumerate(p.bbox for p in percepts or [])))
                nodes = [n.bbox for n in cap.ax_nodes + cap.silent_nodes if n.bbox is not None]
                nearest = lambda box: max((iou(box, n) for n in nodes), default=0.0)  # noqa: E731
                percept_iou_recorded += [nearest(p.bbox) for p in percepts or []]
                percept_iou_sam += [nearest(tight_p[k]) for k in range(len(percepts or [])) if k in tight_p]
                percepts_total += len(percepts or [])
                percepts_sam = [p.model_copy(update={"bbox": tight_p.get(k, p.bbox)}) for k, p in enumerate(percepts)] if percepts is not None else None
                seen_side = replay_screen(cands, cap, percepts_sam, None, seen_prior)
                seen_verified += sum(r["passed"] for r in seen_side)
                no_box += sum(1 for k, c in enumerate(cands) if c.bbox is not None and k not in tight)
                base = replay_screen(cands, cap, percepts, None, base_prior)
                sam = replay_screen(cands, cap, percepts, tight, sam_prior)
                base_results += [{**b, "page": page} for b in base]
                sam_results += [{**s, "page": page, "sighted": c.sighted_text[:80]} for s, c in zip(sam, cands)]
            base_by_page[page] = base_prior
            sam_by_page[page] = sam_prior
            seen_by_page[page] = seen_prior
        runs.append({"recorded": score({p: (await bundle.load(r)).findings for p, r in run_ids[i].items()}, labels, n_faults, n_clean),
                     "baseline": score(base_by_page, labels, n_faults, n_clean), "sam": score(sam_by_page, labels, n_faults, n_clean), "sam_percepts": score(seen_by_page, labels, n_faults, n_clean)})
        log(f"  sam run {i}: recorded {len(runs[-1]['recorded']['hits'])} labels, replay {len(runs[-1]['baseline']['hits'])}, with SAM's boxes {len(runs[-1]['sam']['hits'])}")
    return {**summarise(runs, base_results, sam_results, images=images, no_box=no_box, request_ids=request_ids, seconds=time.monotonic() - started, recorded_verified=recorded_verified),
            "percepts": percepts_total, "percepts_boxed": len(percept_iou_sam), "median_iou_percept_recorded": statistics.median(percept_iou_recorded) if percept_iou_recorded else None,
            "median_iou_percept_sam": statistics.median(percept_iou_sam) if percept_iou_sam else None, "sam_percepts_verified": seen_verified,
            **{f"sam_percepts_{k}": statistics.fmean(r["sam_percepts"][k] for r in runs) for k in ("recall", "precision", "f1")}}


def summarise(runs: list[dict], base: list[dict], sam: list[dict], *, images: int, no_box: int, request_ids: list[str], seconds: float, recorded_verified: int) -> dict[str, Any]:
    mean = lambda key, side: statistics.fmean(r[side][key] for r in runs)  # noqa: E731
    node_moved = sum(1 for b, s in zip(base, sam) if b["node"] != s["node"])
    lost = [{"page": s["page"], "sighted": s["sighted"], "failed": s["failed"]} for b, s in zip(base, sam) if b["passed"] and not s["passed"]]
    gained = [{"page": s["page"], "sighted": s["sighted"]} for b, s in zip(base, sam) if s["passed"] and not b["passed"]]
    ious_b = [b["iou_node"] for b in base if b["iou_node"] is not None]
    ious_s = [s["iou_node"] for s in sam if s["iou_node"] is not None]
    return {"model": SAM, "runs": len(runs), "candidates": len(base), "recorded_verified": recorded_verified, "baseline_verified": sum(b["passed"] for b in base), "sam_verified": sum(s["passed"] for s in sam),
            "baseline_located_failures": sum("located" in b["failed"] for b in base), "sam_located_failures": sum("located" in s["failed"] for s in sam), "no_box_returned": no_box,
            "node_moved": node_moved, "lost": lost, "gained": gained, "median_iou_node_recorded": statistics.median(ious_b) if ious_b else None, "median_iou_node_sam": statistics.median(ious_s) if ious_s else None,
            **{f"{side}_{k}": mean(k, side) for side in ("recorded", "baseline", "sam") for k in ("recall", "precision", "f1", "accuracy")},
            "hits_per_run": {side: [len(r[side]["hits"]) for r in runs] for side in ("recorded", "baseline", "sam")},
            "labels_only_recorded": sorted({h for r in runs for h in set(r["baseline"]["hits"]) - set(r["sam"]["hits"])}), "labels_only_sam": sorted({h for r in runs for h in set(r["sam"]["hits"]) - set(r["baseline"]["hits"])}),
            "images": images, "estimated_cost_usd": images * PRICE_PER_IMAGE, "seconds": seconds, "request_ids": request_ids}


async def concepts(client, png: bytes, log=print) -> dict[str, int]:
    """How many objects a noun phrase finds on a screen: SAM's other prompt, and the only one that could stand in for the Seer."""
    url = "data:image/png;base64," + base64.b64encode(png).decode()
    out = {}
    for noun in CONCEPTS:
        body = {"model": SAM, "input": [{"role": "user", "content": [{"type": "input_text", "text": noun}, {"type": "input_image", "image_url": url}]}]}
        try:
            resp = await client.responses(body, stage="sam-concept", run_id="sam-boxes")
            out[noun] = len(parse_boxes(text_of(resp.raw)))
        except MetaError as exc:
            out[noun] = -1
            log(f"  concept {noun}: {str(exc)[:160]}")
    return out


async def main() -> int:
    from eval.harness import _sweep_base, load_labels
    from parity.config import load_settings

    settings = load_settings()
    if not settings.has_key:
        print("MODEL_API_KEY missing (expected in .env)")
        return 1
    client = MetaClient(settings, cache_dir=SWEEP_DIR / "sam-cache", trace=ListTraceSink())
    run_ids, data = await _sweep_base()
    result = await run(client, data, run_ids, load_labels())
    product_run = run_ids[min(run_ids)]["product.html"]
    result["concepts"] = await concepts(client, (data / "runs" / product_run / "steps" / "0" / "screenshot.png").read_bytes())
    (SWEEP_DIR / "sam-boxes.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "request_ids"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
