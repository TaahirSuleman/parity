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
import hashlib
import html
import json
import re
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
from parity.meta.client import MetaClient, MetaError, TraceRouter  # noqa: E402
from parity.pipeline.audit import Ablation  # noqa: E402
from parity.pipeline.judge import judge  # noqa: E402
from parity.pipeline.runner import run_flow  # noqa: E402
from parity.store import bundle as bundle_mod  # noqa: E402
from parity.store.blob import LocalBlobStore  # noqa: E402
from parity.store.bundle import RunBundle  # noqa: E402
from parity.store.index import RunIndex  # noqa: E402
from parity.store.models import AxeViolation, AxNode, Capture, Element, Finding, Judgement, Severity  # noqa: E402

LABELS_PATH = ROOT / "eval" / "labels.json"
RESULTS_DIR = ROOT / "eval" / "results"
# External benchmark (doc 19 §19.1): the W3C WAI Before and After Demonstration, audited read-only on www.w3.org.
EXTERNAL_LABELS_PATH = ROOT / "eval" / "labels_external.json"
EXTERNAL_ORIGIN = "https://www.w3.org"
EXTERNAL_BASE_PATH = "/WAI/demos/"
EXTERNAL_PAGES = [f"bad/{side}/{name}.html" for side in ("before", "after") for name in ("home", "news", "tickets", "survey")]
EXTERNAL_ATTRIBUTION = "W3C WAI Before and After Demonstration, Copyright © 2012 W3C® (MIT, ERCIM, Keio), W3C Document License; audited read-only"
PAGES = ["product.html", "cart.html", "checkout.html", "confirm.html"]
CONFIGS: dict[str, dict[str, bool]] = {
    "full": {},
    "screenshot_only": {"use_tree": False},
    "tree_only": {"use_screenshot": False, "use_grounding": False},
    "no_grounding": {"use_grounding": False},
}


# --- labels, matching, arithmetic (pure) ---------------------------------------------------------------

def load_labels(path: Path = LABELS_PATH) -> list[dict]:
    """The store labels are a list; the external file is an object whose ``rows`` sit under the W3C notice."""
    doc = json.loads(Path(path).read_text())
    return doc["rows"] if isinstance(doc, dict) else doc


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


def label_id_of(element) -> str | None:
    """The id a finding is scored under: the element's own, else the nearest id above it in its css path (a label on a
    wrapper such as span#k4 > img[alt=""] is hit by the inner img). The same rule the axe baseline is scored under."""
    if element.dom_id:
        return element.dom_id
    ids = _ids_in(element.css_path or "")
    return ids[-1] if ids else None


_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")


def _norm(text: str) -> str:
    return _WS.sub(" ", html.unescape(text or "")).strip().lower()


def label_for(element, sighted_text: str, labels: list[dict]) -> str | None:
    """The label a finding is scored under (spec §13, §19.1): the element's own id, or the nearest id above it, when that is a
    label; otherwise the first label whose anchor the element satisfies, ``src`` and ``html`` (substrings of the outer HTML)
    before ``text`` (normalised equality with the element's own text or the sighted text) before ``css`` (a fragment of the
    css path). The axe baseline is scored by the same function."""
    ids = {r["id"] for r in labels}
    dom_id = label_id_of(element)
    if dom_id in ids:
        return dom_id
    outer = element.outer_html or ""
    texts = {_norm(_TAG.sub(" ", outer)), _norm(sighted_text)} - {""}
    css_path = element.css_path or ""
    for kind in ("src", "html", "text", "css"):
        for r in labels:
            value = (r.get("anchor") or {}).get(kind)
            if not value:
                continue
            if kind in ("src", "html") and value in outer:
                return r["id"]
            if kind == "text" and _norm(value) in texts:
                return r["id"]
            if kind == "css" and value in css_path:
                return r["id"]
    return None


def match(findings: list, labels: list[dict]) -> Matches:
    """A verified finding matches a label when its located element carries the label's id (spec §13) or satisfies its anchor (§19.1)."""
    faults = {r["id"] for r in labels if not r["clean"]}
    clean = {r["id"] for r in labels if r["clean"]}
    m = Matches(set(), set(), [], [], len(findings), len(faults))
    for f in findings:
        dom_id = label_for(f.element, getattr(f, "sighted_text", ""), labels)
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
    return re.findall(r"#([A-Za-z][\w-]*)", target)


@dataclass
class ExternalMatches:
    """One run of one W3C page against its labels (§19.1): in-scope barriers are the only recall target; out-of-scope
    barriers are counted; every finding on a repaired ('after') page is a false positive by construction."""

    hits: set[str]  # in-scope fault labels found
    out_of_scope_hits: set[str]  # out-of-scope fault labels a finding landed on
    on_clean: list[str]  # finding ids on labelled repaired elements
    unlabelled: list[str]  # finding ids on nothing W3C annotated: reported, never scored
    n_findings: int
    n_in_scope: int
    n_out_of_scope: int
    n_clean: int
    matched: int = 0  # findings on in-scope fault labels (precision's numerator)
    out_of_scope_findings: int = 0
    fp: int = 0  # findings on a repaired page
    by_finding: dict[str, str | None] = field(default_factory=dict)


def match_external(findings: list, labels: list[dict]) -> ExternalMatches:
    in_scope = {r["id"] for r in labels if not r["clean"] and r["in_scope"]}
    out_scope = {r["id"] for r in labels if not r["clean"] and not r["in_scope"]}
    clean = {r["id"] for r in labels if r["clean"]}
    repaired_page = bool(clean) and not in_scope and not out_scope
    m = ExternalMatches(set(), set(), [], [], len(findings), len(in_scope), len(out_scope), len(clean))
    for f in findings:
        lid = label_for(f.element, getattr(f, "sighted_text", ""), labels)
        m.by_finding[f.id] = lid
        if lid in in_scope:
            m.hits.add(lid)
            m.matched += 1
        elif lid in out_scope:
            m.out_of_scope_hits.add(lid)
            m.out_of_scope_findings += 1
        elif lid in clean:
            m.on_clean.append(f.id)
        else:
            m.unlabelled.append(f.id)
    if repaired_page:
        m.fp = len(findings)
    return m


def external_metrics(by_page: dict[str, list[ExternalMatches]]) -> dict[str, Any]:
    """Totals over the pages, means over runs (run i of every page scored together). Recall is over the in-scope barriers of
    the before pages; precision counts findings on in-scope barriers as right and every finding on a repaired page as wrong."""
    runs = max((len(v) for v in by_page.values()), default=0)
    before = {p: v for p, v in by_page.items() if "/before/" in p}
    n_in_scope = sum(v[0].n_in_scope for v in before.values() if v)
    out_count = sum(v[0].n_out_of_scope for v in before.values() if v)
    n_clean = sum(v[0].n_clean for v in by_page.values() if v)
    rows = []
    for i in range(runs):
        ms = {p: v[i] for p, v in by_page.items() if i < len(v)}
        hits = set().union(*[m.hits for m in ms.values()]) if ms else set()
        matched = sum(m.matched for m in ms.values())
        fp = sum(m.fp for m in ms.values())
        rows.append({"recall": len(hits) / n_in_scope if n_in_scope else 0.0, "precision": matched / (matched + fp) if matched + fp else 0.0,
                     "fp": fp, "oos": sum(m.out_of_scope_findings for m in ms.values()), "n": sum(m.n_findings for m in ms.values()),
                     "unlabelled": sum(len(m.unlabelled) for p, m in ms.items() if "/before/" in p)})
    return {"in_scope_recall": mean([r["recall"] for r in rows]), "precision": mean([r["precision"] for r in rows]),
            "fp_on_after_pages": mean([r["fp"] for r in rows]), "out_of_scope_hits": mean([r["oos"] for r in rows]),
            "unlabelled_on_before": mean([r["unlabelled"] for r in rows]), "n": mean([r["n"] for r in rows]),
            "n_in_scope": n_in_scope, "out_of_scope_count": out_count, "n_clean": n_clean, "runs": runs}


def axe_baseline(violations: list[AxeViolation], labels: list[dict]) -> dict[str, Any]:
    """What axe-core finds on the same labels, each flagged node scored by label_for over its selector and its HTML. Recall is
    over the fault labels in scope (every store label is)."""
    faults = {r["id"] for r in labels if not r["clean"] and r.get("in_scope", True)}
    out_scope = {r["id"] for r in labels if not r["clean"] and not r.get("in_scope", True)}
    clean = {r["id"] for r in labels if r["clean"]}
    hits: set[str] = set()
    out_of_scope: set[str] = set()
    on_clean: list[str] = []
    for v in violations:
        htmls = list(v.htmls) + [""] * (len(v.targets) - len(v.htmls))
        for target, snippet in zip(v.targets, htmls):
            lid = label_for(Element(backend_id=0, css_path=target, outer_html=snippet or None), "", labels)
            if lid in faults:
                hits.add(lid)
            elif lid in out_scope:
                out_of_scope.add(lid)
            elif lid in clean:
                on_clean.append(target)
    return {"hits": hits, "recall": len(hits) / len(faults) if faults else 0.0, "violations": len(violations), "on_clean": on_clean, "out_of_scope": out_of_scope}


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
        dom_id = label_id_of(f.element)
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


def provenance(labels_path: Path = LABELS_PATH) -> dict[str, Any]:
    """Which code and which labels produced a results file: numbers from different versions are never merged."""
    import hashlib
    import subprocess

    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    sha = git("rev-parse", "HEAD") or "unknown"
    return {"git_sha": sha, "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
            "labels_sha256": hashlib.sha256(Path(labels_path).read_bytes()).hexdigest()}


def configs_for(*, ablations: bool, no_screenshot: bool, no_tree: bool, no_grounding: bool, needs_full: bool) -> list[str]:
    """The configurations an invocation runs. A sweep, a judge comparison or the standard check scores against the full run,
    so they add it when the flags left it out."""
    if ablations:
        return list(CONFIGS)
    cfg = "tree_only" if no_screenshot else "screenshot_only" if no_tree else "no_grounding" if no_grounding else "full"
    return ["full", cfg] if needs_full and cfg != "full" else [cfg]


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


def external_page_flow(page: str) -> Flow:
    """One W3C BAD page as a single-screen, read-only flow: the survey's goal says not to submit (§19.2)."""
    name = page.removeprefix("bad/").removesuffix(".html").replace("/", "-")
    return Flow(id=f"external-{name}", name=f"W3C BAD {name}", start_url=EXTERNAL_BASE_PATH + page,
                goal="Audit this page as a sighted user and as a screen-reader user. Read only: fill in nothing and submit nothing.",
                pages=(page,), single_page=True)


async def run_external(*, client_factory, runs: int, data_dir: Path, settings: Settings, labels_path: Path = EXTERNAL_LABELS_PATH,
                       effort: str = "medium", pages: list[str] = EXTERNAL_PAGES, base_url: str = EXTERNAL_ORIGIN, page_factory=None,
                       log=print) -> dict[str, Any]:
    """Audit the W3C BAD pages `runs` times each, read-only, no fixes; score by the external labels; return the `external` block."""
    labels = load_labels(labels_path)
    bundle = RunBundle(LocalBlobStore(Path(data_dir)))
    index = RunIndex(Path(data_dir) / "index.db")
    await index.init()
    bus = EventBus(bundle)
    kwargs: dict[str, Any] = {"page_factory": page_factory} if page_factory is not None else {}
    by_page: dict[str, list[ExternalMatches]] = {}
    per_page: dict[str, Any] = {}
    axe_hits: set[str] = set()
    axe_oos: set[str] = set()
    axe_viol = 0
    axe_per_page: dict[str, Any] = {}
    try:
        for page in pages:
            page_labels = labels_for(labels, page)
            in_scope_ids = {r["id"] for r in page_labels if not r["clean"] and r["in_scope"]}
            page_runs: list[dict[str, Any]] = []
            for r in range(runs):
                c = client_factory(r)
                t0 = time.perf_counter()
                run = await run_flow(settings, c, bus, bundle, index, external_page_flow(page), base_url=base_url,
                                     ablation=Ablation(effort=effort, run_fixes=False), public=True, **kwargs)
                loaded = await bundle.load(run.id)
                m = match_external(loaded.findings, page_labels)
                by_page.setdefault(page, []).append(m)
                row = {"hits": sorted(m.hits), "out_of_scope_hits": sorted(m.out_of_scope_hits), "on_clean": len(m.on_clean), "unlabelled": len(m.unlabelled),
                       "fp": m.fp, "n": m.n_findings, "tokens": run.tokens, "cost_usd": run.cost_usd,
                       "seconds": max(run.duration_ms / 1000, time.perf_counter() - t0), "run_id": run.id, "status": run.status, "error": run.error}
                page_runs.append(row)
                log(f"  [external] {page} run {r + 1}/{runs}: hits={len(m.hits)}/{m.n_in_scope} oos={m.out_of_scope_findings} fp={m.fp} "
                    f"unlabelled={len(m.unlabelled)} n={m.n_findings} ${run.cost_usd:.3f} {row['seconds']:.0f}s {run.status}")
                if r == 0:  # the axe baseline from the first run's own scan of the page
                    raw = json.loads((await bundle.store.get(bundle_mod.keys.axe(run.id, 0))).decode())
                    viol = [AxeViolation.model_validate(v) for v in (raw if isinstance(raw, list) else raw.get("violations", []))]
                    b = axe_baseline(viol, page_labels)
                    axe_per_page[page] = {"recall": b["recall"], "violations": b["violations"], "hits": sorted(b["hits"]),
                                          "out_of_scope": sorted(b["out_of_scope"]), "on_clean": len(b["on_clean"])}
                    axe_hits |= b["hits"]
                    axe_oos |= b["out_of_scope"]
                    axe_viol += b["violations"]
            hits_union = set().union(*[set(x["hits"]) for x in page_runs])
            per_page[page] = {
                "n_in_scope": len(in_scope_ids), "hits": sorted(hits_union), "hits_every_run": sorted(set.intersection(*[set(x["hits"]) for x in page_runs])),
                "missed": sorted(in_scope_ids - hits_union), "n": mean([x["n"] for x in page_runs]), "fp": mean([x["fp"] for x in page_runs]),
                "unlabelled": mean([x["unlabelled"] for x in page_runs]), "tokens": mean([x["tokens"] for x in page_runs]),
                "cost_usd": mean([x["cost_usd"] for x in page_runs]), "seconds": mean([x["seconds"] for x in page_runs]), "runs": page_runs,
            }
    finally:
        await index.close()
    totals = external_metrics(by_page)
    n_in = totals["n_in_scope"]
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "model": settings.model_for("comparator"), "judge_model": settings.model_for("judge"),
        "effort": effort, "runs": runs, "pages": list(pages), "origin": base_url, "attribution": EXTERNAL_ATTRIBUTION, "labels": "eval/labels_external.json",
        "labels_sha256": hashlib.sha256(Path(labels_path).read_bytes()).hexdigest(), **totals,
        "axe_recall": len(axe_hits) / n_in if n_in else 0.0,
        "axe": {"violations": axe_viol, "hits": sorted(axe_hits), "out_of_scope": sorted(axe_oos), "per_page": axe_per_page},
        "cost_usd": sum(v["cost_usd"] for v in per_page.values()), "seconds": sum(v["seconds"] for v in per_page.values()), "per_page": per_page,
    }


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
        **provenance(labels_path), "configs": {}, "axe": {}, "judge": {},
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
        if not full_runs:  # ablation-only invocation: nothing to score axe or the judges on (zeros would overwrite real rows)
            return results
        # axe-core baseline on the same labels, from the full run's own axe scan of each page
        axe_hits: set[str] = set()
        axe_viol = 0
        results["axe"] = {"per_page": {}}
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
                    try:
                        g.judgement = await judge(c, g, cap, run_id, model=jm, fallback_model=jm)
                    except MetaError as exc:  # as in the product: a judge that fails after its retries sends the finding to a human
                        log(f"  judge {jm} failed on {f.id} (request {exc.request_id}): needs_review")
                        g.judgement = Judgement(is_barrier=None, severity=Severity.needs_review, model_meta={"error": str(exc), "model": jm})
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
    public = out_dir / "public.json"  # the anonymised samples, written by hand after each one; shown in the rendering, kept out of latest.json
    (out_dir / "latest.md").write_text(render({**merged, "public": json.loads(public.read_text())} if public.exists() else merged))
    return path


def merge_latest(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """latest.json is the union of every invocation measured against the same labels: a configuration is replaced only
    by one with at least as many runs, the judge table is one invocation's (its rows share the verified findings) and is
    replaced wholesale, and the other sections are replaced when the new results carry them. Other labels start over."""
    if existing.get("labels_sha256") != new.get("labels_sha256"):
        existing = {}
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


def _factory_for(settings: Settings, work: Path, tag: str = "main"):
    def client_factory(run_index: int, trace=None):  # a fresh cache per invocation and run: variance is measured, not replayed
        return MetaClient(settings, cache_dir=work / f"cache-{tag}-{run_index}", trace=trace or TraceRouter())
    return client_factory


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
    ap.add_argument("--external", action="store_true", help="the W3C BAD benchmark (doc 19 §19.1): its eight pages, --runs each, read-only; writes latest.json['external']")
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
    configs = configs_for(ablations=args.ablations, no_screenshot=args.no_screenshot, no_tree=args.no_tree, no_grounding=args.no_grounding,
                          needs_full=bool(args.effort_sweep or args.standard_check or args.compare_judge))
    stamp = args.name or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    if args.external:
        async def go_external() -> int:
            work = Path(tempfile.mkdtemp(prefix="parity-eval-ext-"))
            settings = load_settings(env={**env, "PARITY_DATA_DIR": str(work / "data")})
            ext_pages = EXTERNAL_PAGES if args.pages == ",".join(PAGES) else [p for p in pages if p in EXTERNAL_PAGES]  # --pages names BAD pages here
            print(f"external: model={settings.model_for('comparator')} judge={settings.model_for('judge')} effort={args.effort} pages={ext_pages} runs={args.runs} origin={EXTERNAL_ORIGIN}")
            ext = await run_external(client_factory=_factory_for(settings, work, "external"), runs=args.runs, data_dir=work / "data", settings=settings, effort=args.effort, pages=ext_pages)
            path = write_results({"generated_at": ext["generated_at"], **provenance(), "external": ext}, name=f"external-{stamp}")
            print(f"wrote {path.relative_to(ROOT)} and refreshed latest.json / latest.md")
            print(f"  external: in_scope_recall={ext['in_scope_recall']:.2f} precision={ext['precision']:.2f} n={ext['n']:.0f} fp_after={ext['fp_on_after_pages']:.1f} "
                  f"oos={ext['out_of_scope_hits']:.1f} unlabelled={ext['unlabelled_on_before']:.1f} axe_recall={ext['axe_recall']:.2f} ${ext['cost_usd']:.3f} {ext['seconds']:.0f}s")
            return 0
        return asyncio.run(go_external())

    async def go() -> int:
        server, base_url = _serve(base)
        work = Path(tempfile.mkdtemp(prefix="parity-eval-"))
        try:
            def make_settings(extra: dict[str, str] | None = None) -> Settings:
                return load_settings(env={**env, **(extra or {}), "PARITY_DATA_DIR": str(work / "data")})

            def factory_for(settings: Settings, tag: str = "main"):
                return _factory_for(settings, work, tag)

            settings = make_settings()
            print(f"model={settings.model_for('comparator')} judge={settings.model_for('judge')} effort={args.effort} pages={pages} runs={args.runs} configs={configs}")
            results = await run_eval(client_factory=factory_for(settings), base_url=base_url, pages=pages, runs=args.runs, configs=configs,
                                     data_dir=work / "data", settings=settings, effort=args.effort, judge_models=args.compare_judge)
            write_results(results, name=stamp)  # the paid runs are on disk before any optional phase can fail
            if args.effort_sweep:
                results["effort_sweep"] = {}
                for eff in ("low", "medium", "high"):
                    if eff == args.effort:  # the main run already measured this effort
                        results["effort_sweep"][eff] = {**results["configs"]["full"]["total"], "note": "the main run"}
                        continue
                    print(f"effort sweep: {eff}")
                    r = await run_eval(client_factory=factory_for(settings, f"effort-{eff}"), base_url=base_url, pages=pages, runs=1, configs=["full"],
                                       data_dir=work / f"data-{eff}", settings=settings, effort=eff, judge_models=[])
                    results["effort_sweep"][eff] = r["configs"]["full"]["total"]
            if args.standard_check:
                std = make_settings({"PARITY_MODEL": "muse-spark-1.3"})
                print("standard-tier check")
                r = await run_eval(client_factory=factory_for(std, "standard"), base_url=base_url, pages=pages, runs=1, configs=["full"],
                                   data_dir=work / "data-standard", settings=std, judge_models=[])
                results["standard_tier_check"] = {"model": "muse-spark-1.3", **r["configs"]["full"]["total"]}
            path = write_results(results, name=stamp)
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
