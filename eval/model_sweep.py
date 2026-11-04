"""The per-stage model and effort sweep (brief in docs/17): which Meta model and reasoning effort is best for each stage.

One stage at a time, every other stage at today's default. Nothing here is imported by parity/.
This file holds the capability spike, the row arithmetic and the choice of a best row; eval/harness.py is the entry point.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from parity.config import CONTRIBUTOR_SPARK, DEFAULT_EFFORT, EFFORTS, STANDARD_SPARK, load_settings
from parity.meta.client import ListTraceSink, MetaError, text_of
from parity.meta.pricing import PRICES
from parity.pipeline.seer import PROMPT as SEER_PROMPT
from parity.pipeline.seer import parse_percepts

SWEEP_DIR = Path(__file__).resolve().parents[1] / "cache" / "model-sweep"  # git-ignored: the run bundles and the per-run response caches behind the committed rows
SPIKE_MODELS = ("muse-spark-1.3-contributor", "muse-spark-1.3", "muse-spark-1.2-contributor", "muse-spark-1.2", "muse-spark-1.1", "muse-wonder-1.0", "sam-3.1")
GOAL = "Click the Pay now button on this checkout page."


# --- the capability spike: one cached call per model and capability ---------------------------------------

def classify_json(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"ok": isinstance(json.loads(text_of(raw)), dict)}
    except json.JSONDecodeError:
        return {"ok": False}


def classify_grounding(raw: dict[str, Any]) -> dict[str, Any]:
    n = len(parse_percepts(text_of(raw), 0))
    return {"ok": n > 0, "boxes": n}


def classify_computer(raw: dict[str, Any]) -> dict[str, Any]:
    calls = [i for i in raw.get("output") or [] if i.get("type") == "computer_call"]
    return {"ok": bool(calls), "safety_checks": sum(len(c.get("pending_safety_checks") or []) for c in calls)}


def spike_bodies(model: str, png_data_url: str) -> dict[str, dict[str, Any]]:
    """The request each stage depends on, in the shape the stage sends it (skill meta-model-api)."""
    image = {"type": "input_image", "image_url": png_data_url}
    return {
        "json": {"model": model, "reasoning": {"effort": "medium"}, "text": {"format": {"type": "json_object"}}, "max_output_tokens": 2000,
                 "input": [{"role": "user", "content": [{"type": "input_text", "text": 'Name the main button on this page. Answer as JSON: {"button": "..."}'}, image]}]},
        "grounding": {"model": model, "reasoning": {"effort": "medium"}, "text": {"format": {"type": "json_object"}}, "max_output_tokens": 8000,
                      "input": [{"role": "user", "content": [{"type": "input_text", "text": SEER_PROMPT.replace("{page_url}", "https://store.example/checkout.html")}, image]}]},
        "computer": {"model": model, "tools": [{"type": "computer"}], "reasoning": {"effort": "low"}, "truncation": "auto", "parallel_tool_calls": False,
                     "input": [{"role": "user", "content": [{"type": "input_text", "text": GOAL}, image]}]},
    }


CLASSIFIERS = {"json": classify_json, "grounding": classify_grounding, "computer": classify_computer}


async def run_spike(client, png_data_url: str, models: tuple[str, ...] = SPIKE_MODELS, log=print) -> dict[str, dict[str, Any]]:
    """{model: {capability: {ok, ..., request_id, tokens, cost_usd | refused}}}. A refusal is a result, recorded in the API's words."""
    out: dict[str, dict[str, Any]] = {}
    for model in models:
        out[model] = {}
        for capability, body in spike_bodies(model, png_data_url).items():
            try:
                resp = await client.responses(body, stage=f"spike-{capability}", run_id="model-sweep-spike")
                row = {**CLASSIFIERS[capability](resp.raw), "request_id": resp.request_id, "tokens": resp.usage.total_tokens, "status": resp.raw.get("status")}
                if not row["ok"]:
                    row["answer"] = text_of(resp.raw)[:200]
            except MetaError as exc:
                row = {"ok": False, "refused": str(exc)[:300], "http_status": exc.status, "request_id": exc.request_id}
            out[model][capability] = row
            log(f"  spike {model:30} {capability:10} ok={row['ok']} {row.get('refused', '')[:110]}")
    return out


# --- row arithmetic (pure) ----------------------------------------------------------------------------------

def score_set(*, hits: int, matched: int, n: int, fp_clean_distinct: int, n_faults: int, n_clean: int) -> dict[str, float]:
    """One run of a page set. Accuracy is over the faults and the clean controls: a found fault and a clean control with no finding are right."""
    recall = hits / n_faults if n_faults else 0.0
    precision = matched / n if n else 0.0
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    accuracy = (hits + n_clean - fp_clean_distinct) / (n_faults + n_clean) if n_faults + n_clean else 0.0
    return {"recall": recall, "precision": precision, "f1": f1, "accuracy": accuracy}


def jaccard(key_sets: list[list[str]]) -> float | None:
    """Mean pairwise Jaccard of what each run found; None for a single run (no spread is claimed from n = 1)."""
    if len(key_sets) < 2:
        return None
    sets = [set(k) for k in key_sets]
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:]]
    return sum(len(a & b) / len(a | b) if a | b else 1.0 for a, b in pairs) / len(pairs)


def stage_stats(calls: list) -> dict[str, dict[str, float]]:
    """Calls, tokens, cost and mean latency per stage, from the ModelCall trace. A cache hit counts as a call at 0 ms and is left out of the latency."""
    out: dict[str, dict[str, float]] = {}
    for c in calls:
        s = out.setdefault(c.stage, {"calls": 0, "tokens": 0, "cost_usd": 0.0, "latency_ms_mean": 0.0, "_paid": 0, "_ms": 0})
        s["calls"] += 1
        s["tokens"] += c.total_tokens
        s["cost_usd"] += c.cost_usd
        if not c.cache_hit:
            s["_paid"] += 1
            s["_ms"] += c.latency_ms
    for s in out.values():
        s["latency_ms_mean"] = s.pop("_ms") / s["_paid"] if s["_paid"] else 0.0
        s.pop("_paid")
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _merge_stage_means(records: list[dict]) -> dict[str, dict[str, float]]:
    names = {s for r in records for s in r.get("stages", {})}
    out = {}
    for name in sorted(names):
        rows = [r["stages"][name] for r in records if name in r.get("stages", {})]
        out[name] = {k: _mean([x[k] for x in rows]) for k in ("calls", "tokens", "cost_usd", "latency_ms_mean")}
    return out


def aggregate_detection(spec: dict, records: list[dict], *, n_faults: int, n_clean: int, judge_per_finding: float) -> dict[str, Any]:
    """A Seer or Comparator row from its per-run records (recall, precision and F1 are per run, then the mean)."""
    scores = [score_set(hits=len(r["hits"]), matched=r["matched"], n=r["n"], fp_clean_distinct=len(set(r["fp_clean"])), n_faults=n_faults, n_clean=n_clean) for r in records]
    hit_counts = [len(r["hits"]) for r in records]
    cost = _mean([r["cost_usd"] for r in records])
    judge_cost = _mean([r["stages"].get("judge", {}).get("cost_usd", 0.0) for r in records])
    n = _mean([r["n"] for r in records])
    return {**spec, "runs": len(records), **{k: _mean([s[k] for s in scores]) for k in ("recall", "precision", "f1", "accuracy")},
            "fp_on_clean": _mean([len(r["fp_clean"]) for r in records]), "n_per_run": n, "unlabelled": _mean([r["unlabelled"] for r in records]),
            "candidates": _mean([r["candidates"] for r in records]), "rejected": _mean([r["rejected"] for r in records]),
            "rejection_rate": _mean([r["rejected"] / r["candidates"] if r["candidates"] else 0.0 for r in records]),
            "jaccard": jaccard([r["keys"] for r in records]), "hits_spread": max(hit_counts) - min(hit_counts) if hit_counts else 0,
            "tokens": _mean([r["tokens"] for r in records]), "cost_usd": cost, "cost_default_judge_usd": cost - judge_cost + n * judge_per_finding,
            "seconds": _mean([r["seconds"] for r in records]), "stages": _merge_stage_means(records), "status": sorted({s for r in records for s in r["status"]})}


def _usd(x: float, places: int = 2) -> str:
    return "price unknown" if x == float("inf") else f"${x:.{places}f}"


def _reason(best: dict, default: dict | None, metric_txt: str, why: str) -> str:
    who = f"{best['model']} at {best['effort']}"
    if default is None or (best["model"], best["effort"]) == (default["model"], default["effort"]):
        return f"{who} (today's default): {metric_txt}; {why}."
    return f"{who}: {metric_txt}; {why}."


def _detection_best(stage: str, rows: list[dict], spread_labels: int, n_faults: int) -> dict[str, Any]:
    tol = spread_labels / n_faults if n_faults else 0.0
    default = next((r for r in rows if r.get("is_default")), None)
    top_f1 = max(r["f1"] for r in rows)
    tied = [r for r in rows if r["f1"] >= top_f1 - tol]  # inside the between-run spread nothing separates them: the cheaper one wins, then the default
    pick = min(tied, key=lambda r: (round(r["cost_default_judge_usd"], 3), not r.get("is_default")))
    metric = f"recall {pick['recall']:.0%}, precision {pick['precision']:.0%}, F1 {pick['f1']:.2f}, {_usd(pick['cost_default_judge_usd'])} a page set"
    cheaper = default is not None and pick is not default and pick["cost_default_judge_usd"] < default["cost_default_judge_usd"]
    why = "cheaper inside the between-run spread" if cheaper else f"nothing beats it by more than the between-run spread of {spread_labels} labels" if pick is default else "the highest F1"
    clears, margin = False, "no default row to compare with"
    if default is not None:
        d_recall, d_precision = pick["recall"] - default["recall"], pick["precision"] - default["precision"]
        margin = f"{d_recall * 100:+.0f} recall, {d_precision * 100:+.0f} precision points against the default, F1 {pick['f1'] - default['f1']:+.2f}"
        clears = pick is not default and d_recall > tol and d_precision >= 0 and pick["cost_default_judge_usd"] <= default["cost_default_judge_usd"]
    return {"stage": stage, "model": pick["model"], "effort": pick["effort"], "reason": _reason(pick, default, metric, why), "margin": margin, "clears_bar": clears, "runs": pick["runs"]}


def _ordered_best(stage: str, rows: list[dict], key, metric, ties: str) -> dict[str, Any]:
    default = next((r for r in rows if r.get("is_default")), None)
    pick = min(rows, key=key)
    margin, clears = "no default row to compare with", False
    if default is not None and pick is not default:
        margin = metric(pick) + " against " + metric(default)
        clears = key(pick)[:-2] <= key(default)[:-2] and _cost_of(pick) <= _cost_of(default)
    elif default is not None:
        margin = "the default is the best row"
    cheaper = default is not None and pick is not default and _cost_of(pick) < _cost_of(default)
    why = ties if not cheaper else f"{ties}; cheaper than the default"
    return {"stage": stage, "model": pick["model"], "effort": pick["effort"], "reason": _reason(pick, default, metric(pick), why), "margin": margin, "clears_bar": clears, "runs": pick.get("runs", 1)}


def _cost_of(row: dict) -> float:
    return row.get("cost_per_finding", row.get("cost_per_fix", row.get("cost_usd_stage", 0.0)))


def choose_best(stage: str, rows: list[dict], *, spread_labels: int = 3, n_faults: int = 38) -> dict[str, Any]:
    """The best row of a stage and whether it clears the bar for changing the default. The rule is the sweep's: inside the between-run
    spread nothing separates two rows, so the cheaper one wins; a default changes only for a win beyond the spread at no higher cost,
    and then only by the builder's decision. Recall has to beat the spread; precision (99% today, little room above it) must not fall."""
    inf = float("inf")
    live = [{**r, **{k: inf for k in ("cost_default_judge_usd", "cost_per_finding", "cost_per_fix", "cost_usd_stage") if k in r}} if r.get("unpriced") else r
            for r in rows if not r.get("failed")]  # a model with no known price cannot win on cost, and $0 would say it does
    if not live:
        return {"stage": stage, "model": None, "effort": None, "reason": "no row ran", "margin": "", "clears_bar": False, "runs": 0}
    if stage in ("seer", "comparator"):
        return _detection_best(stage, live, spread_labels, n_faults)
    if stage == "judge":
        return _ordered_best(stage, live, lambda r: (-round(r["agreement"], 2), round(r["needs_review_rate"], 2), r["cost_per_finding"], not r.get("is_default")),
                             lambda r: f"{r['agreement']:.0%} agreement with the labels, {r['needs_review_rate']:.0%} needing review, {_usd(r['cost_per_finding'], 4)} a finding", "the highest agreement")
    if stage == "fixer":
        return _ordered_best(stage, live, lambda r: (-round(r["gap_closed_rate"], 2), r["rejected"], r["cost_per_fix"], not r.get("is_default")),
                             lambda r: f"{r['gap_closed_rate']:.0%} of gaps closed, {r['rejected']} fixes rejected, {_usd(r['cost_per_fix'], 4)} a fix", "the most gaps closed")
    return _ordered_best(stage, live, lambda r: (-r["screens"], r["turns"], r["cost_usd_stage"], not r.get("is_default")),
                         lambda r: f"{r['screens']:.1f} of 4 screens, {r['turns']:.1f} turns, {_usd(r['cost_usd_stage'], 3)} of navigator calls", "the most screens in the fewest turns")


def merge_sweep_block(block: dict[str, Any]) -> dict[str, Any]:
    """What goes into latest.json: only the labels (so the merge keeps the file) and the block. No generated_at or git_sha at the top:
    those date and name the main table's numbers, which this sweep did not re-measure."""
    return {"labels_sha256": block.get("labels_sha256"), "model_sweep": block}


def render_sweep(block: dict[str, Any]) -> str:
    """model-sweep.md, and the section of latest.md the README quotes."""
    pct = lambda x: "—" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    lines = [f"Measured at commit `{str(block.get('git_sha', '?'))[:12]}`, labels sha256 `{str(block.get('labels_sha256', '?'))[:12]}`, {block.get('generated_at', '')}. "
             f"{block.get('method', '')} Spend ${block.get('spend_usd', 0):.2f}, {block.get('wall_s', 0) / 60:.0f} min of model and browser time.", ""]
    if block.get("spike"):
        lines += ["### What each model accepted (one call each)", "", "| Model | JSON | Grounding | Computer use |", "|---|---|---|---|"]
        cell = lambda c: "yes" if c.get("ok") else f"no ({str(c.get('refused') or c.get('answer') or 'no usable answer')[:70]})".replace("|", "/").replace("\n", " ")  # noqa: E731
        for model, caps in block["spike"].items():
            lines.append(f"| {model} | {cell(caps.get('json', {}))} | {cell(caps.get('grounding', {}))} | {cell(caps.get('computer', {}))} |")
        lines.append("")
    best = block.get("best", {})
    if best:
        lines += ["### Best model per stage", "", "| Stage | Best model | Effort | Runs | Why | Margin | Clears the bar to change the default |", "|---|---|---|---|---|---|---|"]
        for stage, b in best.items():
            lines.append(f"| {stage} | {b.get('model')} | {b.get('effort')} | n = {b.get('runs')} | {b.get('reason')} | {b.get('margin')} | {'yes' if b.get('clears_bar') else 'no'} |")
        lines.append("")
    for stage, entry in block.get("stages", {}).items():
        rows = entry.get("rows", [])
        b = best.get(stage, {})
        mark = lambda r: f"**{r['model']}**" if (r["model"], r["effort"]) == (b.get("model"), b.get("effort")) else r["model"]  # noqa: E731
        lines += [f"### {stage.capitalize()}", ""]
        if stage in ("seer", "comparator"):
            lines += ["| Model | Effort | n | Recall | Precision | F1 | Accuracy | FP on clean | Verified per run | Rejected share | Jaccard | Tokens | Cost | Cost with the default judge | Time | Stage latency |", "|" + "---|" * 16]
            for r in rows:
                if r.get("failed"):
                    lines.append(f"| {r['model']} | {r['effort']} | n = 0 | failed: {r['failed']} |" + " — |" * 12)
                    continue
                j = "—" if r.get("jaccard") is None else f"{r['jaccard']:.2f}"
                lat = (r.get("stages") or {}).get(stage, {}).get("latency_ms_mean", 0) / 1000
                lines.append(f"| {mark(r)} | {r['effort']} | n = {r['runs']} | {pct(r['recall'])} | {pct(r['precision'])} | {r['f1']:.2f} | {pct(r['accuracy'])} | {r['fp_on_clean']:.1f} | {r['n_per_run']:.0f} | {pct(r['rejection_rate'])} | {j} | {r['tokens']:,.0f} | ${r['cost_usd']:.3f} | ${r['cost_default_judge_usd']:.3f} | {r['seconds']:.0f} s | {lat:.0f} s |")
        elif stage == "judge":
            lines += ["| Model | Effort | n findings | Agreement with labels | Severity same as the default judge | Needs review (fail closed) | Cost per finding | Latency |", "|" + "---|" * 8]
            for r in rows:
                if r.get("failed"):
                    lines.append(f"| {r['model']} | {r['effort']} | 0 | failed: {r['failed']} | — | — | — | — |")
                    continue
                lines.append(f"| {mark(r)} | {r['effort']} | {r['n']} | {pct(r['agreement'])} | {pct(r.get('severity_same'))} | {pct(r['needs_review_rate'])} | ${r['cost_per_finding']:.4f} | {r.get('latency_ms_mean', 0) / 1000:.0f} s |")
        elif stage == "fixer":
            lines += ["| Model | Effort | n barriers | Gaps closed | Comparator still flags | Fixes rejected | Cost per fix | Fixer latency | Time |", "|" + "---|" * 9]
            for r in rows:
                if r.get("failed"):
                    lines.append(f"| {r['model']} | {r['effort']} | 0 | failed: {r['failed']} | — | — | — | — | — |")
                    continue
                lines.append(f"| {mark(r)} | {r['effort']} | {r['n']} | {pct(r['gap_closed_rate'])} | {pct(r.get('still_flags_rate'))} | {r['rejected']} | ${r['cost_per_fix']:.4f} | {r.get('latency_ms_mean', 0) / 1000:.0f} s | {r.get('seconds', 0):.0f} s |")
        else:
            lines += ["| Model | Effort | n | Screens of 4 | Turns | Refusals | Safety checks | Navigator cost | Run cost | Navigator latency | Time |", "|" + "---|" * 11]
            for r in rows:
                if r.get("failed"):
                    lines.append(f"| {r['model']} | {r['effort']} | n = 0 | failed: {r['failed']} |" + " — |" * 7)
                    continue
                lines.append(f"| {mark(r)} | {r['effort']} | n = {r['runs']} | {r['screens']:.1f} | {r['turns']:.1f} | {r['refusals']:.1f} | {r['safety_checks']:.1f} | ${r['cost_usd_stage']:.3f} | ${r['cost_usd']:.3f} | {r.get('latency_ms_mean', 0) / 1000:.0f} s | {r['seconds']:.0f} s |")
        lines.append("")
    return "\n".join(lines) + "\n"


# --- running rows ------------------------------------------------------------------------------------------

STAGES = ("comparator", "seer", "judge", "fixer", "navigator")  # the order of value: a cut-off still leaves the rows that matter most
DEFAULTS = {stage: (STANDARD_SPARK if stage == "judge" else CONTRIBUTOR_SPARK, DEFAULT_EFFORT[stage]) for stage in STAGES}
FIX_CONCURRENCY = 4


def parse_row(spec: str) -> tuple[str, str, str]:
    parts = spec.split(":")
    if len(parts) != 3 or parts[0] not in STAGES or parts[2] not in EFFORTS:
        raise ValueError(f"a row is stage:model:effort, with a stage in {STAGES} and an effort in {EFFORTS}: {spec!r}")
    return parts[0], parts[1], parts[2]


def row_env(stage: str, model: str, effort: str, *, cheap_judge: bool) -> dict[str, str]:
    """The overrides of one row. ``cheap_judge``: Seer, Comparator and Navigator rows judge on the contributor tier of the same model, about 1/12 of the
    price; a judgement enters neither recall nor precision, and the row's cost is also projected at the default judge."""
    env = {f"PARITY_{stage.upper()}_MODEL": model, f"PARITY_{stage.upper()}_EFFORT": effort}
    if cheap_judge and stage in ("seer", "comparator", "navigator"):
        env["PARITY_JUDGE_MODEL"] = CONTRIBUTOR_SPARK
    return env


def row_slug(stage: str, model: str, effort: str) -> str:
    return f"{stage}--{model}--{effort}"


def _load_records(row_dir: Path) -> list[dict]:
    path = Path(row_dir) / "records.json"
    return json.loads(path.read_text()) if path.exists() else []


def _save_records(row_dir: Path, records: list[dict]) -> None:
    Path(row_dir).mkdir(parents=True, exist_ok=True)
    (Path(row_dir) / "records.json").write_text(json.dumps(records, indent=1) + "\n")


def _run_common(loaded) -> dict[str, Any]:
    return {"tokens": loaded.run.tokens, "cost_usd": loaded.run.cost_usd, "seconds": loaded.run.duration_ms / 1000, "status": str(getattr(loaded.run.status, "value", loaded.run.status)),
            "error": loaded.run.error, "request_ids": [c.request_id for c in loaded.trace if c.request_id]}


def detection_record(loaded_by_page: dict[str, Any], labels: list[dict]) -> dict[str, Any]:
    """One run of the page set, scored by the harness's own match(), from the bundles on disk."""
    from eval.harness import label_for, labels_for, match

    hits, keys, fp_clean, request_ids, status, errors, calls = [], [], [], [], [], [], []
    matched = n = unlabelled = rejected = candidates = tokens = 0
    cost = seconds = 0.0
    for page, loaded in loaded_by_page.items():
        page_labels = labels_for(labels, page)
        m = match(loaded.findings, page_labels)
        hits += sorted(m.hits)
        matched += m.matched
        n += m.n_findings
        unlabelled += len(m.unlabelled)
        fp_clean += [m.by_finding[i] for i in m.fp_on_clean]
        keys += [f"{page}#{label_for(f.element, f.sighted_text, page_labels) or f.element.css_path}" for f in loaded.findings]
        rejected += loaded.run.findings_rejected
        candidates += sum(int(e.data.get("n", 0)) for e in loaded.events if e.type == "comparator.candidates")
        common = _run_common(loaded)
        tokens += common["tokens"]
        cost += common["cost_usd"]
        seconds += common["seconds"]
        request_ids += common["request_ids"]
        status.append(common["status"])
        if common["error"]:
            errors.append(common["error"])
        calls += loaded.trace
    return {"hits": hits, "matched": matched, "n": n, "fp_clean": fp_clean, "unlabelled": unlabelled, "rejected": rejected, "candidates": candidates, "tokens": tokens,
            "cost_usd": cost, "seconds": seconds, "stages": stage_stats(calls), "keys": keys, "run_ids": {p: l.run.id for p, l in loaded_by_page.items()},
            "request_ids": request_ids, "status": sorted(set(status)), "errors": errors}


def _stores(data_dir: Path):
    from parity.api.events import EventBus
    from parity.store.blob import LocalBlobStore
    from parity.store.bundle import RunBundle
    from parity.store.index import RunIndex

    bundle = RunBundle(LocalBlobStore(Path(data_dir)))
    return bundle, EventBus(bundle), RunIndex(Path(data_dir) / "index.db")


async def run_detection_row(stage: str, model: str, effort: str, *, runs: int, base_url: str, row_dir: Path, env_base: dict[str, str], client_factory, pages: list[str] | None = None,
                            page_factory=None, cheap_judge: bool = True, log=print) -> list[dict]:
    """Seer or Comparator: the page set, ``runs`` times, every other stage at the default. Rows already on disk are kept: a run is never paid for twice, and asking for more runs adds to them."""
    from eval.harness import PAGES, load_labels, page_flow
    from parity.pipeline.audit import Ablation
    from parity.pipeline.runner import run_flow

    row_dir = Path(row_dir)
    records = _load_records(row_dir)
    pages = pages or PAGES
    labels = load_labels()
    data = row_dir / "data"
    settings = load_settings(env={**env_base, **row_env(stage, model, effort, cheap_judge=cheap_judge), "PARITY_DATA_DIR": str(data)})
    bundle, bus, index = _stores(data)
    await index.init()
    kwargs = {"page_factory": page_factory} if page_factory is not None else {}
    try:
        for r in range(len(records), runs):
            client = client_factory(settings, r)
            loaded = {}
            for page in pages:
                run = await run_flow(settings, client, bus, bundle, index, page_flow(page), base_url=base_url, ablation=Ablation(run_fixes=False), **kwargs)
                loaded[page] = await bundle.load(run.id)
                log(f"  [{stage} {model} {effort}] {page} run {r + 1}/{runs}: verified={run.findings_verified} rejected={run.findings_rejected} ${run.cost_usd:.3f} {run.duration_ms / 1000:.0f}s {run.status}")
            records.append(detection_record(loaded, labels))
            _save_records(row_dir, records)  # a paid run is on disk before the next one starts
    finally:
        await index.close()
    return records


def _reached(loaded) -> list[str]:
    from eval.harness import PAGES

    urls = [s.url for s in loaded.steps] + [str((e.data or {}).get("final_url") or "") for e in loaded.events if e.type == "run.finished"]
    return [p for p in PAGES if any(p in u for u in urls)]


def navigator_record(loaded) -> dict[str, Any]:
    finished = next((e.data for e in loaded.events if e.type == "run.finished"), {}) or {}
    agent = finished.get("agent") or {}
    calls = [c for c in loaded.trace if c.stage == "auditor"]
    return {**_run_common(loaded), "status": [_run_common(loaded)["status"]], "screens": len(_reached(loaded)), "reached": _reached(loaded), "turns": agent.get("turns", 0), "finished": bool(agent.get("finished")),
            "refusals": sum(e.type == "agent.refused" for e in loaded.events), "blocked": sum(e.type == "nav.blocked" for e in loaded.events),
            "safety_checks": sum(int(e.data.get("safety_checks", 0)) for e in loaded.events if e.type == "nav.actions"), "stages": stage_stats(loaded.trace),
            "cost_usd_stage": sum(c.cost_usd for c in calls), "n": loaded.run.findings_verified, "run_id": loaded.run.id}


async def run_navigator_row(model: str, effort: str, *, runs: int, base_url: str, row_dir: Path, env_base: dict[str, str], client_factory, page_factory=None, max_turns: int = 12, cheap_judge: bool = True, log=print) -> list[dict]:
    """The purchase flow, no fixes: how far the walk gets. Chained agent turns are never cached, so each run here is a new walk."""
    from parity.flows import FLOWS
    from parity.pipeline.audit import Ablation
    from parity.pipeline.runner import run_flow

    row_dir = Path(row_dir)
    records = _load_records(row_dir)
    data = row_dir / "data"
    settings = load_settings(env={**env_base, **row_env("navigator", model, effort, cheap_judge=cheap_judge), "PARITY_DATA_DIR": str(data)})
    bundle, bus, index = _stores(data)
    await index.init()
    kwargs = {"page_factory": page_factory} if page_factory is not None else {}
    try:
        for r in range(len(records), runs):
            run = await run_flow(settings, client_factory(settings, r), bus, bundle, index, FLOWS["purchase"], base_url=base_url, ablation=Ablation(run_fixes=False), max_turns=max_turns, **kwargs)
            records.append(navigator_record(await bundle.load(run.id)))
            _save_records(row_dir, records)
            rec = records[-1]
            log(f"  [navigator {model} {effort}] run {r + 1}/{runs}: screens={rec['screens']} turns={rec['turns']} refusals={rec['refusals']} safety={rec['safety_checks']} ${rec['cost_usd']:.3f} {rec['seconds']:.0f}s {run.status}")
    finally:
        await index.close()
    return records


async def _base_findings(data_dir: Path, run_ids: dict[str, str]):
    """The recorded findings a Judge or Fixer row is scored on: the same ones for every model."""
    bundle, _, _ = _stores(data_dir)
    out = {}
    for page, run_id in run_ids.items():
        out[page] = (run_id, await bundle.load(run_id))
    return bundle, out


def _agreement(findings_by_page: dict[str, list], labels: list[dict]) -> dict[str, Any]:
    from eval.harness import _agreement_by_page

    page_of = {f.id: p for p, fs in findings_by_page.items() for f in fs}
    return _agreement_by_page([f for fs in findings_by_page.values() for f in fs], page_of, labels, 0.0)


async def judge_default_row(data_dir: Path, run_ids: dict[str, str], *, base_url: str = "") -> dict[str, Any]:
    """Today's judge on the recorded findings, from the recorded run: no call."""
    from eval.harness import load_labels

    _, base = await _base_findings(data_dir, run_ids)
    calls = [c for _, l in base.values() for c in l.trace if c.stage == "judge"]
    agreement = _agreement({p: l.findings for p, (_, l) in base.items()}, load_labels())
    n = agreement["n"]
    model, effort = DEFAULTS["judge"]
    return {"stage": "judge", "model": model, "effort": effort, "is_default": True, "runs": 1, "n": n, "decided": agreement["decided"], "agreement": agreement["agreement"], "needs_review_rate": agreement["needs_review_rate"],
            "severity_same": 1.0, "cost_per_finding": sum(c.cost_usd for c in calls) / n if n else 0.0, "cost_usd": sum(c.cost_usd for c in calls), "tokens": sum(c.total_tokens for c in calls),
            "latency_ms_mean": stage_stats(calls).get("judge", {}).get("latency_ms_mean", 0.0), "request_ids": [c.request_id for c in calls if c.request_id], "note": "the recorded run (seen-full, run 1)"}


async def run_judge_row(model: str, effort: str, data_dir: Path, run_ids: dict[str, str], *, base_url: str, client, concurrency: int = 4, log=print) -> dict[str, Any]:
    """Re-judge the recorded verified findings with this model, four at a time as the product does; a failure sends the finding to review (fail closed)."""
    from eval.harness import capture_from_bundle, load_labels
    from parity.pipeline.judge import judge
    from parity.store.models import Judgement, Severity

    bundle, base = await _base_findings(data_dir, run_ids)
    gate = asyncio.Semaphore(concurrency)
    trace = client.trace if isinstance(getattr(client, "trace", None), ListTraceSink) else None
    before = len(trace.calls) if trace else 0
    t0 = time.perf_counter()
    rejudged: dict[str, list] = {}
    pending = []

    async def one(g, cap, run_id):
        async with gate:
            try:
                g.judgement = await judge(client, g, cap, run_id, model=model, fallback_model=model, effort=effort)
            except MetaError as exc:
                log(f"  judge {model} failed on {g.id} (request {exc.request_id}): needs_review")
                g.judgement = Judgement(is_barrier=None, severity=Severity.needs_review, model_meta={"error": str(exc), "model": model})

    same = total = 0
    original = {}
    for page, (run_id, loaded) in base.items():
        rejudged[page] = []
        caps = {}
        for f in loaded.findings:
            if f.step_index not in caps:
                caps[f.step_index] = await capture_from_bundle(bundle, run_id, f.step_index, base_url.rstrip("/") + f"/store/{page}")
            g = f.model_copy(deep=True)
            original[g.id] = f.judgement
            rejudged[page].append(g)
            pending.append(one(g, caps[f.step_index], run_id))
    await asyncio.gather(*pending)
    for fs in rejudged.values():
        for g in fs:
            was = original.get(g.id)
            if was is not None and g.judgement is not None and g.judgement.is_barrier is not None:
                total += 1
                same += g.judgement.severity == was.severity
    agreement = _agreement(rejudged, load_labels())
    calls = trace.calls[before:] if trace else []
    cost = sum(c.cost_usd for c in calls if c.stage == "judge")
    n = agreement["n"]
    return {"stage": "judge", "model": model, "effort": effort, "runs": 1, "n": n, "decided": agreement["decided"], "agreement": agreement["agreement"], "needs_review_rate": agreement["needs_review_rate"],
            "severity_same": same / total if total else None, "cost_per_finding": cost / n if n else 0.0, "cost_usd": cost, "tokens": sum(c.total_tokens for c in calls),
            "latency_ms_mean": stage_stats(calls).get("judge", {}).get("latency_ms_mean", 0.0), "seconds": time.perf_counter() - t0, "request_ids": [c.request_id for c in calls if c.request_id]}


async def run_fixer_row(model: str, effort: str, data_dir: Path, run_ids: dict[str, str], *, base_url: str, client, page_factory=None, concurrency: int = FIX_CONCURRENCY, log=print) -> dict[str, Any]:
    """Propose and re-audit a fix for every recorded barrier, the re-audit at its own defaults (the comparator's model, effort low), in a sandbox page of its own."""
    from eval.harness import capture_from_bundle
    from parity.pipeline import browser
    from parity.pipeline.fixer import FixNotApplied, FixRejected, propose_fix
    from parity.pipeline.reaudit import reaudit

    bundle, base = await _base_findings(data_dir, run_ids)
    gate = asyncio.Semaphore(concurrency)
    trace = client.trace if isinstance(getattr(client, "trace", None), ListTraceSink) else None
    before = len(trace.calls) if trace else 0
    settings = load_settings(env={})
    t0 = time.perf_counter()
    outcomes: list[dict[str, Any]] = []
    own_pages = page_factory is None
    factory = page_factory or browser.new_page

    async def one(finding, cap, run_id):
        async with gate:
            try:
                fix = await propose_fix(client, finding, cap, run_id, model=model, effort=effort)
            except (FixRejected, FixNotApplied, MetaError) as exc:
                outcomes.append({"id": finding.id, "proposed": False, "reason": str(exc)[:200]})
                log(f"  fixer {model} rejected {finding.id}: {str(exc)[:100]}")
                return
            pages: list = []

            async def tracked():
                p = await factory()
                pages.append(p)
                return p

            try:
                result = await reaudit(client, tracked, cap.html, cap.url, fix, finding, run_id, model=settings.model_for("reaudit"), effort=settings.effort_for("reaudit"))
                outcomes.append({"id": finding.id, "proposed": True, "gap_closed": result.gap_closed, "still_flags": result.comparator_still_flags})
            except Exception as exc:  # a fix that cannot be re-audited is not a closed gap; the row says how many
                outcomes.append({"id": finding.id, "proposed": True, "gap_closed": False, "still_flags": None, "reaudit_error": f"{type(exc).__name__}: {exc}"[:200]})
                log(f"  re-audit failed for {finding.id}: {type(exc).__name__}: {str(exc)[:100]}")
            finally:
                if own_pages:
                    for p in pages:
                        await p.context.close()

    pending = []
    for page, (run_id, loaded) in base.items():
        caps = {}
        for f in loaded.findings:
            if not (f.judgement and f.judgement.is_barrier is True):
                continue
            if f.step_index not in caps:
                cap = await capture_from_bundle(bundle, run_id, f.step_index, base_url.rstrip("/") + f"/store/{page}")
                cap.html = await bundle.read_source(run_id, f.step_index)
                caps[f.step_index] = cap
            pending.append(one(f.model_copy(deep=True), caps[f.step_index], run_id))
    await asyncio.gather(*pending)
    calls = trace.calls[before:] if trace else []
    proposed = [o for o in outcomes if o["proposed"]]
    closed = sum(bool(o.get("gap_closed")) for o in proposed)
    checked = [o for o in proposed if o.get("still_flags") is not None]
    fixer_calls = [c for c in calls if c.stage == "fixer"]
    fixer_cost = sum(c.cost_usd for c in fixer_calls)
    n = len(outcomes)
    return {"stage": "fixer", "model": model, "effort": effort, "runs": 1, "n": n, "proposed": len(proposed), "rejected": n - len(proposed), "gap_closed": closed, "gap_closed_rate": closed / n if n else 0.0,
            "still_flags_rate": sum(bool(o["still_flags"]) for o in checked) / len(checked) if checked else None, "reaudit_errors": sum("reaudit_error" in o for o in proposed),
            "cost_per_fix": fixer_cost / len(proposed) if proposed else 0.0, "cost_usd": sum(c.cost_usd for c in calls), "cost_fixer_usd": fixer_cost, "tokens": sum(c.total_tokens for c in calls),
            "latency_ms_mean": stage_stats(fixer_calls).get("fixer", {}).get("latency_ms_mean", 0.0), "seconds": time.perf_counter() - t0, "request_ids": [c.request_id for c in calls if c.request_id], "outcomes": outcomes}


# --- the block: rows from disk to model-sweep.json, latest.json and latest.md ---------------------------------

METHOD = ("One stage at a time, every other stage at today's default. Seer and Comparator rows run the store's page set (38 seeded faults, 20 clean controls); Judge and Fixer rows re-use "
          "the verified findings of the first recorded run of 4 Nov, so every model sees the same findings; Navigator rows walk the purchase flow with no fixes. "
          "In Seer, Comparator and Navigator rows the judge ran on the contributor tier of the same model (a judgement enters neither recall nor precision); \"Cost with the default judge\" projects the row at the default judge's price per finding. "
          "Accuracy is over the faults and the clean controls: a clean control with no finding is a true negative. A row with n = 1 is a sample, not a measurement of spread.")


def _spec(stage: str, model: str, effort: str) -> dict[str, Any]:
    return {"stage": stage, "model": model, "effort": effort, "is_default": (model, effort) == DEFAULTS[stage], "unpriced": model not in PRICES}


def _failed(records: list[dict]) -> str | None:
    """Every run failed (a refusal or a repeated API error): the row is reported in the API's words and cannot win."""
    if records and all(set(r.get("status", [])) <= {"failed"} for r in records):
        errs = [e for r in records for e in (r.get("errors") or ([r["error"]] if r.get("error") else []))]
        return (errs[0] if errs else "failed")[:200]
    return None


def aggregate_navigator(spec: dict, records: list[dict]) -> dict[str, Any]:
    mean = lambda k: _mean([r[k] for r in records])  # noqa: E731
    stages = _merge_stage_means(records)
    return {**spec, "runs": len(records), "screens": mean("screens"), "turns": mean("turns"), "finished": _mean([bool(r["finished"]) for r in records]), "refusals": mean("refusals"), "blocked": mean("blocked"),
            "safety_checks": mean("safety_checks"), "cost_usd_stage": mean("cost_usd_stage"), "cost_usd": mean("cost_usd"), "tokens": mean("tokens"), "seconds": mean("seconds"), "n_per_run": mean("n"),
            "latency_ms_mean": stages.get("auditor", {}).get("latency_ms_mean", 0.0), "stages": stages, "status": sorted({s for r in records for s in r["status"]})}


def build_block(sweep_dir: Path, *, judge_default: dict | None, git_sha: str, labels_sha: str, n_faults: int, n_clean: int) -> dict[str, Any]:
    """Everything the sweep reports, from what is on disk: no model call happens here."""
    sweep_dir = Path(sweep_dir)
    base_path = sweep_dir / "base-records.json"
    base = json.loads(base_path.read_text()) if base_path.exists() else []
    n_base = _mean([r["n"] for r in base])
    judge_per_finding = _mean([r["stages"].get("judge", {}).get("cost_usd", 0.0) for r in base]) / n_base if n_base else 0.0
    stages: dict[str, dict[str, Any]] = {s: {"rows": []} for s in STAGES}
    records: dict[str, Any] = {}
    spend = float(json.loads((sweep_dir / "spike-spend.json").read_text())) if (sweep_dir / "spike-spend.json").exists() else 0.0
    wall = 0.0
    if base:
        for stage in ("comparator", "seer"):
            model, effort = DEFAULTS[stage]
            stages[stage]["rows"].append({**aggregate_detection(_spec(stage, model, effort), base, n_faults=n_faults, n_clean=n_clean, judge_per_finding=judge_per_finding), "note": "the recorded 4 Nov run"})
        records["default-detection"] = base
    if judge_default:
        stages["judge"]["rows"].append(judge_default)
    for row_dir in sorted((sweep_dir / "rows").glob("*")) if (sweep_dir / "rows").exists() else []:
        stage, model, effort = row_dir.name.split("--")
        spec = _spec(stage, model, effort)
        if (row_dir / "row.json").exists():
            row = {**spec, **json.loads((row_dir / "row.json").read_text())}
            spend += row.get("cost_usd", 0.0)
            wall += row.get("seconds", 0.0)
            records[row_dir.name] = {"request_ids": row.pop("request_ids", []), "outcomes": row.pop("outcomes", [])}
            stages[stage]["rows"].append(row)
            continue
        recs = _load_records(row_dir)
        if not recs:
            continue
        spend += sum(r["cost_usd"] for r in recs)
        wall += sum(r["seconds"] for r in recs)
        records[row_dir.name] = recs
        if stage == "navigator":
            row = aggregate_navigator(spec, recs)
        else:
            row = aggregate_detection(spec, recs, n_faults=n_faults, n_clean=n_clean, judge_per_finding=judge_per_finding)
        if failed := _failed(recs):
            row["failed"] = failed
        stages[stage]["rows"].append(row)
    spread = max(2, max((r["hits_spread"] for r in stages["comparator"]["rows"] if r.get("is_default")), default=0))
    best = {s: choose_best(s, e["rows"], spread_labels=spread, n_faults=n_faults) for s, e in stages.items() if e["rows"]}
    spike_path = sweep_dir / "spike.json"
    spike = json.loads(spike_path.read_text()) if spike_path.exists() else {}
    return {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "git_sha": git_sha, "labels_sha256": labels_sha, "method": METHOD, "n_faults": n_faults, "n_clean": n_clean,
            "defaults": {s: {"model": m, "effort": e} for s, (m, e) in DEFAULTS.items()}, "spread_labels": spread, "spend_usd": spend, "wall_s": wall, "spike": spike,
            "stages": {s: e for s, e in stages.items() if e["rows"]}, "best": best, "records": records}


def _public(block: dict[str, Any]) -> dict[str, Any]:
    """latest.json carries the rows and the best block; the per-run records and request ids stay in model-sweep.json."""
    out = {k: v for k, v in block.items() if k != "records"}
    out["stages"] = {s: {"rows": [{k: v for k, v in r.items() if k != "request_ids"} for r in e["rows"]]} for s, e in block.get("stages", {}).items()}
    return out


def write_sweep(block: dict[str, Any], out_dir: Path) -> None:
    from eval.harness import merge_latest
    from eval.report import render

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "model-sweep.json").write_text(json.dumps(block, indent=1) + "\n")
    (out_dir / "model-sweep.md").write_text("# Per-stage model and effort sweep\n\n" + render_sweep(block))
    latest = out_dir / "latest.json"
    merged = merge_latest(json.loads(latest.read_text()) if latest.exists() else {}, merge_sweep_block(_public(block)))
    latest.write_text(json.dumps(merged, indent=1) + "\n")
    public = out_dir / "public.json"
    (out_dir / "latest.md").write_text(render({**merged, "public": json.loads(public.read_text())} if public.exists() else merged))
