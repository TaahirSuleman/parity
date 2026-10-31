"""Evaluation harness (spec §13): recall and precision against the seeded labels, the axe-core baseline,
ablations, the effort sweep and the judge comparison. The numbers in the README, the video and the form
all come from the file this writes. Nothing here is imported by parity/.

Run (live, costs money):
  .venv/bin/python -m eval.harness --ablations --runs 3            # the four configurations
  .venv/bin/python -m eval.harness --effort-sweep                   # low / medium / high, one run each
  .venv/bin/python -m eval.harness --compare-judge muse-wonder-1.0  # re-judge the same findings with Wonder
  .venv/bin/python -m eval.harness --standard-check                 # one run on standard Spark 1.3
Each invocation writes eval/results/<timestamp>.json and refreshes latest.json / latest.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parity.api.events import EventBus  # noqa: E402
from parity.config import Settings, load_settings  # noqa: E402
from parity.flows import Flow  # noqa: E402
from parity.meta.client import MetaClient, TraceRouter  # noqa: E402
from parity.pipeline.audit import Ablation  # noqa: E402
from parity.pipeline.judge import judge  # noqa: E402
from parity.pipeline.runner import run_flow  # noqa: E402
from parity.store import bundle as bundle_mod  # noqa: E402
from parity.store.blob import LocalBlobStore  # noqa: E402
from parity.store.bundle import RunBundle  # noqa: E402
from parity.store.index import RunIndex  # noqa: E402
from parity.store.models import AxeViolation, AxNode, Capture, Finding  # noqa: E402

LABELS_PATH = ROOT / "eval" / "labels.json"
RESULTS_DIR = ROOT / "eval" / "results"
PAGES = ["product.html", "cart.html", "checkout.html", "confirm.html"]
CONFIGS: dict[str, dict[str, bool]] = {
    "full": {},
    "screenshot_only": {"use_tree": False},
    "tree_only": {"use_screenshot": False, "use_grounding": False},
    "no_grounding": {"use_grounding": False},
}


# --- labels, matching, arithmetic (pure) ---------------------------------------------------------------

def load_labels(path: Path = LABELS_PATH) -> list[dict]:
    return json.loads(Path(path).read_text())


def labels_for(labels: list[dict], page: str) -> list[dict]:
    return [r for r in labels if r["page"] == page]


@dataclass
class Matches:
    hits: set[str]  # distinct fault labels found
    missed: set[str]
    fp_on_clean: list[str]  # finding ids on labelled clean controls
    unlabelled: list[str]  # finding ids on nothing we labelled: a false positive by construction
    n_findings: int
    n_faults: int
    matched: int = 0  # findings that landed on a fault label (precision's numerator)
    by_finding: dict[str, str | None] = field(default_factory=dict)


def match(findings: list, labels: list[dict]) -> Matches:
    """A verified finding matches a label when its located element carries the label's id (spec §13)."""
    faults = {r["id"] for r in labels if not r["clean"]}
    clean = {r["id"] for r in labels if r["clean"]}
    m = Matches(set(), set(), [], [], len(findings), len(faults))
    for f in findings:
        dom_id = f.element.dom_id
        if dom_id in faults:
            m.hits.add(dom_id)
            m.matched += 1
            m.by_finding[f.id] = dom_id
        elif dom_id in clean:
            m.fp_on_clean.append(f.id)
            m.by_finding[f.id] = dom_id
        else:
            m.unlabelled.append(f.id)
            m.by_finding[f.id] = None
    m.missed = faults - m.hits
    return m


def metrics(m: Matches) -> dict[str, Any]:
    return {
        "recall": len(m.hits) / m.n_faults if m.n_faults else 0.0,
        "precision": m.matched / m.n_findings if m.n_findings else 0.0,
        "fp_on_clean": len(m.fp_on_clean),
        "n": m.n_findings,
        "n_labels": m.n_faults,
    }


def _ids_in(target: str) -> list[str]:
    import re

    return re.findall(r"#([A-Za-z][\w-]*)", target)


def axe_baseline(violations: list[AxeViolation], labels: list[dict]) -> dict[str, Any]:
    """What axe-core finds on the same labels: the rule engine's recall on seeded faults."""
    faults = {r["id"] for r in labels if not r["clean"]}
    clean = {r["id"] for r in labels if r["clean"]}
    hits: set[str] = set()
    on_clean: list[str] = []
    for v in violations:
        for target in v.targets:
            ids = set(_ids_in(target))
            hits |= ids & faults
            if ids & clean:
                on_clean.append(target)
    return {"hits": hits, "recall": len(hits) / len(faults) if faults else 0.0, "violations": len(violations), "on_clean": on_clean}


def judge_agreement(findings: list, labels: list[dict], judge_cost_usd: float) -> dict[str, Any]:
    """Agreement of the judge's is_barrier with the labels, on verified findings that landed on a label."""
    faults = {r["id"] for r in labels if not r["clean"]}
    clean = {r["id"] for r in labels if r["clean"]}
    decided = agree = unsure = 0
    for f in findings:
        j = f.judgement
        if j is None or j.is_barrier is None:
            unsure += 1
            continue
        dom_id = f.element.dom_id
        if dom_id in faults:
            decided += 1
            agree += j.is_barrier is True
        elif dom_id in clean:
            decided += 1
            agree += j.is_barrier is False
    n = len(findings)
    return {"agreement": agree / decided if decided else 0.0, "needs_review_rate": unsure / n if n else 0.0,
            "cost_per_finding": judge_cost_usd / n if n else 0.0, "n": n, "decided": decided}


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


# --- running pages --------------------------------------------------------------------------------------

def page_flow(page_name: str) -> Flow:
    return Flow(id=f"eval-{page_name.split('.')[0]}", name=page_name, start_url=f"/store/{page_name}",
                goal="Audit this page as a sighted user and as a screen-reader user.", pages=(page_name,), single_page=True)


async def capture_from_bundle(bundle: RunBundle, run_id: str, step: int, url: str) -> Capture:
    """Rebuild the capture a run saw, for re-judging the same findings with another model."""
    ax = json.loads((await bundle.store.get(bundle_mod.keys.ax(run_id, step))).decode())
    cap = Capture(step_index=step, url=url, ax_nodes=[AxNode.model_validate(n) for n in ax["ax_nodes"]],
                  silent_nodes=[AxNode.model_validate(n) for n in ax.get("silent_nodes", [])])
    cap.screenshot_png = await bundle.read_screenshot(run_id, step)
    return cap


async def run_eval(*, client=None, client_factory=None, base_url: str, pages: list[str], runs: int, configs: list[str], data_dir: Path,
                   page_factory=None, settings: Settings | None = None, labels_path: Path = LABELS_PATH, effort: str = "medium",
                   judge_models: list[str] = ("muse-wonder-1.0",), log=print) -> dict[str, Any]:
    """Audit each page `runs` times per configuration; match verified findings to the labels; return the results dict."""
    labels = load_labels(labels_path)
    settings = settings or load_settings(env={"PARITY_DATA_DIR": str(data_dir)})
    bundle = RunBundle(LocalBlobStore(Path(data_dir)))
    index = RunIndex(Path(data_dir) / "index.db")
    await index.init()
    bus = EventBus(bundle)
    results: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "model": settings.model_for("comparator"),
        "judge_model": settings.model_for("judge"), "effort": effort, "runs": runs, "pages": list(pages), "labels": "eval/labels.json",
        "n_faults": sum(not r["clean"] for r in labels if r["page"] in pages), "n_clean": sum(bool(r["clean"]) for r in labels if r["page"] in pages),
        "configs": {}, "axe": {"per_page": {}}, "judge": {},
    }
    kwargs: dict[str, Any] = {}
    if page_factory is not None:
        kwargs["page_factory"] = page_factory
    full_runs: dict[str, tuple[str, list[Finding]]] = {}  # page -> (run_id, findings) of the first full run, for axe and judges
    try:
        for cfg in configs:
            flags = CONFIGS[cfg]
            per_page: dict[str, Any] = {}
            for page_name in pages:
                page_labels = labels_for(labels, page_name)
                page_runs: list[dict[str, Any]] = []
                for r in range(runs):
                    c = client if client is not None else client_factory(r)
                    ablation = Ablation(effort=effort, run_fixes=False, **flags)
                    t0 = time.perf_counter()
                    run = await run_flow(settings, c, bus, bundle, index, page_flow(page_name), base_url=base_url, ablation=ablation, **kwargs)
                    loaded = await bundle.load(run.id)
                    m = match(loaded.findings, page_labels)
                    row = {**metrics(m), "hits": sorted(m.hits), "missed": sorted(m.missed), "fp_ids": [m.by_finding[i] for i in m.fp_on_clean],
                           "unlabelled": len(m.unlabelled), "tokens": run.tokens, "cost_usd": run.cost_usd,
                           "seconds": max(run.duration_ms / 1000, time.perf_counter() - t0), "run_id": run.id, "status": run.status, "error": run.error,
                           "judge_cost_usd": sum(t.cost_usd for t in loaded.trace if t.stage == "judge")}
                    page_runs.append(row)
                    log(f"  [{cfg}] {page_name} run {r + 1}/{runs}: recall={row['recall']:.2f} precision={row['precision']:.2f} n={row['n']} ${row['cost_usd']:.3f} {row['seconds']:.0f}s {run.status}")
                    if cfg == "full" and page_name not in full_runs:
                        full_runs[page_name] = (run.id, loaded.findings)
                per_page[page_name] = {
                    "recall": mean([x["recall"] for x in page_runs]), "precision": mean([x["precision"] for x in page_runs]),
                    "fp_on_clean": mean([x["fp_on_clean"] for x in page_runs]), "n": mean([x["n"] for x in page_runs]), "n_labels": len([r for r in page_labels if not r["clean"]]),
                    "hits": sorted(set().union(*[set(x["hits"]) for x in page_runs])), "hits_every_run": sorted(set.intersection(*[set(x["hits"]) for x in page_runs])),
                    "tokens": mean([x["tokens"] for x in page_runs]), "cost_usd": mean([x["cost_usd"] for x in page_runs]), "seconds": mean([x["seconds"] for x in page_runs]),
                    "runs": page_runs,
                }
            n_labels = sum(v["n_labels"] for v in per_page.values())
            hits_total = mean([sum(len(x["hits"]) for x in [per_page[p]["runs"][i] for p in pages]) for i in range(runs)]) if pages else 0.0
            n_find = sum(v["n"] for v in per_page.values())
            matched = mean([sum(x["precision"] * x["n"] for x in [per_page[p]["runs"][i] for p in pages]) for i in range(runs)]) if pages else 0.0
            results["configs"][cfg] = {
                "runs": runs, "per_page": per_page,
                "total": {"recall": hits_total / n_labels if n_labels else 0.0, "precision": matched / n_find if n_find else 0.0,
                          "fp_on_clean": sum(v["fp_on_clean"] for v in per_page.values()), "n": n_find, "n_labels": n_labels,
                          "tokens": sum(v["tokens"] for v in per_page.values()), "cost_usd": sum(v["cost_usd"] for v in per_page.values()),
                          "seconds": sum(v["seconds"] for v in per_page.values())},
            }
        # axe-core baseline on the same labels, from the full run's own axe scan of each page
        axe_hits: set[str] = set()
        axe_viol = 0
        for page_name, (run_id, _) in full_runs.items():
            raw = json.loads((await bundle.store.get(bundle_mod.keys.axe(run_id, 0))).decode())
            viol = [AxeViolation.model_validate(v) for v in (raw if isinstance(raw, list) else raw.get("violations", []))]
            b = axe_baseline(viol, labels_for(labels, page_name))
            results["axe"]["per_page"][page_name] = {"recall": b["recall"], "violations": b["violations"], "hits": sorted(b["hits"])}
            axe_hits |= b["hits"]
            axe_viol += b["violations"]
        results["axe"].update({"recall": len(axe_hits) / results["n_faults"] if results["n_faults"] else 0.0, "violations": axe_viol, "hits": sorted(axe_hits)})
        # the run's own judge, then the comparison models on the same verified findings
        own = settings.model_for("judge")
        all_findings = [f for _, fs in full_runs.values() for f in fs]
        page_of = {f.id: p for p, (_, fs) in full_runs.items() for f in fs}
        own_cost = 0.0
        for page_name, (run_id, _) in full_runs.items():
            own_cost += sum(t.cost_usd for t in (await bundle.load(run_id)).trace if t.stage == "judge")
        results["judge"][own] = _agreement_by_page(all_findings, page_of, labels, own_cost)
        for jm in judge_models:
            if jm == own or not all_findings:
                continue
            router = TraceRouter()
            c = client if client is not None else client_factory(0, trace=router)
            rejudged: list[Finding] = []
            for page_name, (run_id, fs) in full_runs.items():
                url = base_url.rstrip("/") + f"/store/{page_name}"
                cap = await capture_from_bundle(bundle, run_id, 0, url)
                for f in fs:
                    g = f.model_copy(deep=True)
                    g.judgement = await judge(c, g, cap, run_id, model=jm, fallback_model=jm)
                    rejudged.append(g)
            cost = sum(t.cost_usd for t in getattr(router, "unrouted", []) if t.stage == "judge")
            results["judge"][jm] = _agreement_by_page(rejudged, page_of, labels, cost)
    finally:
        await index.close()
    return results


def _agreement_by_page(findings: list[Finding], page_of: dict[str, str], labels: list[dict], cost: float) -> dict[str, Any]:
    decided = agree = unsure = 0
    for page_name in set(page_of.values()):
        fs = [f for f in findings if page_of.get(f.id) == page_name]
        a = judge_agreement(fs, labels_for(labels, page_name), 0.0)
        decided += a["decided"]
        agree += round(a["agreement"] * a["decided"])
        unsure += round(a["needs_review_rate"] * a["n"])
    n = len(findings)
    return {"agreement": agree / decided if decided else 0.0, "needs_review_rate": unsure / n if n else 0.0,
            "cost_per_finding": cost / n if n else 0.0, "n": n, "decided": decided, "cost_usd": cost}


# --- files ---------------------------------------------------------------------------------------------

def write_results(results: dict[str, Any], out_dir: Path = RESULTS_DIR, name: str | None = None) -> Path:
    from eval.report import render

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = name or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{stamp}.json"
    path.write_text(json.dumps(results, indent=1, default=_json_default) + "\n")
    latest = out_dir / "latest.json"
    merged = merge_latest(json.loads(latest.read_text()) if latest.exists() else {}, results)
    latest.write_text(json.dumps(merged, indent=1, default=_json_default) + "\n")
    (out_dir / "latest.md").write_text(render(merged))
    return path


def merge_latest(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """latest.json is the union of every invocation: a configuration is replaced only by one with at least as many
    runs, judges accumulate, and the other sections are replaced when the new results carry them."""
    out = dict(existing)
    for key, value in new.items():
        if value in ({}, None, []):
            continue
        if key == "configs":
            cfgs = dict(out.get("configs", {}))
            for name, entry in value.items():
                if name not in cfgs or int(entry.get("runs", 1)) >= int(cfgs[name].get("runs", 1)):
                    cfgs[name] = entry
            out["configs"] = cfgs
        elif key == "judge":
            out["judge"] = {**out.get("judge", {}), **value}
        else:
            out[key] = value
    out["updated_at"] = new.get("generated_at", existing.get("updated_at"))
    return out


def _json_default(o):
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


# --- CLI -----------------------------------------------------------------------------------------------

def _serve(settings: Settings):
    """The store, served by the real app on a free port (Replay data goes to a temp dir)."""
    import uvicorn

    from parity.app import create_app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    tmp = Path(tempfile.mkdtemp(prefix="parity-eval-srv-"))
    app_settings = load_settings(env={"MODEL_API_KEY": "", "PARITY_DATA_DIR": str(tmp / "data"), "PARITY_INDEX_PATH": str(tmp / "index.db"),
                                      "PARITY_CACHE_DIR": str(tmp / "cache"), "PARITY_REPLAY_DIR": str(tmp / "replay"), "PORT": str(port)})
    server = uvicorn.Server(uvicorn.Config(create_app(app_settings), host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server, f"http://127.0.0.1:{port}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=None, help="PARITY_MODEL for the run (default: settings)")
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--judge-model", default=None, help="the judge used during the run (default: settings)")
    ap.add_argument("--compare-judge", action="append", default=[], help="re-judge the same findings with this model (repeatable)")
    ap.add_argument("--no-screenshot", action="store_true")
    ap.add_argument("--no-tree", action="store_true")
    ap.add_argument("--no-grounding", action="store_true")
    ap.add_argument("--ablations", action="store_true", help="run all four configurations")
    ap.add_argument("--effort-sweep", action="store_true", help="low, medium and high, one run each, full configuration")
    ap.add_argument("--standard-check", action="store_true", help="one full run on standard muse-spark-1.3")
    ap.add_argument("--name", default=None, help="results file name (default: timestamp)")
    args = ap.parse_args(argv)
    base = load_settings()
    if not base.has_key:
        print("MODEL_API_KEY missing (expected in .env)")
        return 1
    env = {"MODEL_API_KEY": base.model_api_key}
    if args.model:
        env["PARITY_MODEL"] = args.model
    if args.judge_model:
        env["PARITY_JUDGE_MODEL"] = args.judge_model
    pages = [p.strip() for p in args.pages.split(",") if p.strip()]
    if args.ablations:
        configs = list(CONFIGS)
    else:
        configs = ["full" if not (args.no_screenshot or args.no_tree or args.no_grounding) else
                   "tree_only" if args.no_screenshot else "screenshot_only" if args.no_tree else "no_grounding"]

    async def go() -> int:
        server, base_url = _serve(base)
        work = Path(tempfile.mkdtemp(prefix="parity-eval-"))
        try:
            def make_settings(extra: dict[str, str] | None = None) -> Settings:
                return load_settings(env={**env, **(extra or {}), "PARITY_DATA_DIR": str(work / "data")})

            def factory_for(settings: Settings):
                def client_factory(run_index: int, trace=None):  # a fresh cache per run: variance is measured, not replayed
                    return MetaClient(settings, cache_dir=work / f"cache-{run_index}", trace=trace or TraceRouter())
                return client_factory

            settings = make_settings()
            print(f"model={settings.model_for('comparator')} judge={settings.model_for('judge')} effort={args.effort} pages={pages} runs={args.runs} configs={configs}")
            results = await run_eval(client_factory=factory_for(settings), base_url=base_url, pages=pages, runs=args.runs, configs=configs,
                                     data_dir=work / "data", settings=settings, effort=args.effort, judge_models=args.compare_judge)
            if args.effort_sweep:
                results["effort_sweep"] = {}
                for eff in ("low", "medium", "high"):
                    print(f"effort sweep: {eff}")
                    r = await run_eval(client_factory=factory_for(settings), base_url=base_url, pages=pages, runs=1, configs=["full"],
                                       data_dir=work / f"data-{eff}", settings=settings, effort=eff, judge_models=[])
                    results["effort_sweep"][eff] = r["configs"]["full"]["total"]
            if args.standard_check:
                std = make_settings({"PARITY_MODEL": "muse-spark-1.3"})
                print("standard-tier check")
                r = await run_eval(client_factory=factory_for(std), base_url=base_url, pages=pages, runs=1, configs=["full"],
                                   data_dir=work / "data-standard", settings=std, judge_models=[])
                results["standard_tier_check"] = {"model": "muse-spark-1.3", **r["configs"]["full"]["total"]}
            path = write_results(results, name=args.name)
            print(f"wrote {path.relative_to(ROOT)} and refreshed latest.json / latest.md")
            for cfg, v in results["configs"].items():
                t = v["total"]
                print(f"  {cfg:16} recall={t['recall']:.2f} precision={t['precision']:.2f} n={t['n']:.0f}/{t['n_labels']} fp_clean={t['fp_on_clean']:.1f} ${t['cost_usd']:.3f} {t['seconds']:.0f}s")
            print(f"  axe-core: recall={results['axe'].get('recall', 0):.2f} violations={results['axe'].get('violations', 0)}")
            for jm, v in results["judge"].items():
                print(f"  judge {jm}: agreement={v['agreement']:.2f} needs_review={v['needs_review_rate']:.2f} cost/finding=${v['cost_per_finding']:.4f} n={v['n']}")
            return 0
        finally:
            server.should_exit = True
    return asyncio.run(go())


if __name__ == "__main__":
    sys.exit(main())
