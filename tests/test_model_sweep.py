"""The per-stage model sweep's pure parts: the capability classification, the row arithmetic and the choice of a best row."""

from eval.model_sweep import classify_computer, classify_grounding, classify_json


def _out(*items):
    return {"output": list(items)}


def _text(s):
    return {"type": "message", "content": [{"type": "output_text", "text": s}]}


def test_classify_json_accepts_only_a_parseable_object():
    assert classify_json(_out(_text('{"ok": true}')))["ok"] is True
    assert classify_json(_out(_text("not json")))["ok"] is False
    assert classify_json(_out(_text("[1]")))["ok"] is False


def test_classify_grounding_counts_boxes_on_the_grid():
    good = '{"percepts": [{"visible_text": "Pay", "kind": "button", "bbox": {"x_min": 10, "y_min": 10, "x_max": 50, "y_max": 50}}]}'
    assert classify_grounding(_out(_text(good))) == {"ok": True, "boxes": 1}
    assert classify_grounding(_out(_text('{"percepts": []}'))) == {"ok": False, "boxes": 0}


def test_classify_computer_needs_a_computer_call():
    assert classify_computer(_out({"type": "computer_call", "actions": [{"type": "click"}]}))["ok"] is True
    assert classify_computer(_out(_text("I can't do that")))["ok"] is False


# --- row arithmetic -----------------------------------------------------------------------------------------

import pytest  # noqa: E402

from eval.model_sweep import aggregate_detection, choose_best, jaccard, merge_sweep_block, render_sweep, score_set, stage_stats  # noqa: E402
from parity.store.models import ModelCall  # noqa: E402


def _call(stage, cost=0.01, tokens=100, latency=1000, rid="r"):
    return ModelCall(id=rid, run_id="x", stage=stage, model="m", request_id=rid, response_id="", prompt_sha256="", cache_hit=False, input_tokens=tokens, cached_tokens=0,
                     output_tokens=0, total_tokens=tokens, latency_ms=latency, cost_usd=cost, http_status=200)


def test_score_set_defines_accuracy_over_faults_and_clean_controls():
    s = score_set(hits=30, matched=30, n=32, fp_clean_distinct=2, n_faults=38, n_clean=20)
    assert s["recall"] == pytest.approx(30 / 38)
    assert s["precision"] == pytest.approx(30 / 32)
    assert s["f1"] == pytest.approx(2 * (30 / 38) * (30 / 32) / (30 / 38 + 30 / 32))
    assert s["accuracy"] == pytest.approx((30 + 18) / 58)  # a clean control with no finding is a true negative


def test_score_set_with_nothing_found_is_zero_not_a_crash():
    s = score_set(hits=0, matched=0, n=0, fp_clean_distinct=0, n_faults=38, n_clean=20)
    assert s["precision"] == 0.0 and s["f1"] == 0.0 and s["accuracy"] == pytest.approx(20 / 58)


def test_jaccard_is_the_mean_over_pairs_and_none_for_one_run():
    assert jaccard([["a", "b"]]) is None
    assert jaccard([["a", "b"], ["a", "b"]]) == 1.0
    assert jaccard([["a", "b"], ["b", "c"], ["a", "b"]]) == pytest.approx((1 / 3 + 1 + 1 / 3) / 3)


def test_stage_stats_means_the_latency_of_paid_calls():
    out = stage_stats([_call("seer", latency=1000), _call("seer", latency=3000), _call("judge", cost=0.1)])
    assert out["seer"]["calls"] == 2 and out["seer"]["latency_ms_mean"] == 2000 and out["seer"]["cost_usd"] == pytest.approx(0.02)
    assert out["judge"]["cost_usd"] == pytest.approx(0.1)


def _run(hits, n=None, cost=0.05, judge_cost=0.01, seconds=100.0, rejected=2, candidates=None, keys=None):
    n = hits if n is None else n
    return {"hits": [f"l{i}" for i in range(hits)], "matched": hits, "n": n, "fp_clean": [], "unlabelled": n - hits, "rejected": rejected, "candidates": candidates or n + rejected,
            "tokens": 1000, "cost_usd": cost, "seconds": seconds, "stages": {"judge": {"calls": n, "cost_usd": judge_cost, "tokens": 1, "latency_ms_mean": 10}},
            "keys": keys or [f"l{i}" for i in range(n)], "run_ids": {}, "request_ids": ["req"], "status": ["done"]}


def test_aggregate_detection_projects_the_default_judge_and_means_over_runs():
    row = aggregate_detection({"stage": "seer", "model": "m", "effort": "low"}, [_run(30), _run(32)], n_faults=38, n_clean=20, judge_per_finding=0.01)
    assert row["runs"] == 2 and row["recall"] == pytest.approx(31 / 38)
    assert row["n_per_run"] == 31 and row["jaccard"] is not None
    assert row["rejection_rate"] == pytest.approx(2 / 33, abs=0.01)
    assert row["cost_usd"] == pytest.approx(0.05)
    # the swept stages plus the judge at the default's per-finding price, as if the row had run on the default judge
    assert row["cost_default_judge_usd"] == pytest.approx(0.05 - 0.01 + 31 * 0.01)
    assert row["hits_spread"] == 2


def _row(stage, model, effort, recall, precision, cost, default=False, **extra):
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    return {"stage": stage, "model": model, "effort": effort, "recall": recall, "precision": precision, "f1": f1, "cost_default_judge_usd": cost, "runs": 1, "is_default": default, "seconds": 100, **extra}


def test_best_stays_with_the_default_inside_the_between_run_spread():
    rows = [_row("seer", "d", "medium", 0.85, 0.99, 0.37, default=True), _row("seer", "x", "medium", 0.87, 0.99, 0.37)]
    best = choose_best("seer", rows, spread_labels=3, n_faults=38)
    assert best["model"] == "d" and best["clears_bar"] is False


def test_a_tie_inside_the_spread_goes_to_the_cheaper_row():
    rows = [_row("seer", "d", "medium", 0.85, 0.99, 0.37, default=True), _row("seer", "x", "low", 0.85, 0.99, 0.30)]
    best = choose_best("seer", rows, spread_labels=3, n_faults=38)
    assert best["model"] == "x" and best["clears_bar"] is False and "cheaper" in best["reason"]


def test_a_cost_gap_inside_the_margin_does_not_unseat_the_default():
    """$0.349 against $0.369 is two fewer findings to judge, not a cheaper model (seen on the first Comparator rows, 4 Nov)."""
    rows = [_row("comparator", "d", "medium", 0.85, 0.99, 0.369, default=True), _row("comparator", "x", "medium", 0.82, 1.0, 0.349)]
    best = choose_best("comparator", rows, spread_labels=3, n_faults=38)
    assert best["model"] == "d" and "cheaper" not in best["reason"]


def test_a_clear_winner_clears_the_bar_only_at_no_higher_cost():
    d = _row("seer", "d", "medium", 0.70, 0.95, 0.37, default=True)
    assert choose_best("seer", [d, _row("seer", "x", "medium", 0.90, 0.96, 0.37)], spread_labels=3, n_faults=38)["clears_bar"] is True
    dearer = choose_best("seer", [d, _row("seer", "x", "medium", 0.90, 0.96, 0.90)], spread_labels=3, n_faults=38)
    assert dearer["model"] == "x" and dearer["clears_bar"] is False


def test_failed_rows_never_win():
    rows = [_row("seer", "d", "medium", 0.85, 0.99, 0.37, default=True), _row("seer", "x", "medium", 0.99, 0.99, 0.01, failed="refused")]
    assert choose_best("seer", rows, spread_labels=3, n_faults=38)["model"] == "d"


def test_judge_best_prefers_agreement_then_cost():
    rows = [{"stage": "judge", "model": "d", "effort": "medium", "agreement": 0.94, "needs_review_rate": 0.0, "cost_per_finding": 0.0108, "n": 33, "is_default": True, "runs": 1},
            {"stage": "judge", "model": "c", "effort": "medium", "agreement": 0.94, "needs_review_rate": 0.0, "cost_per_finding": 0.001, "n": 33, "is_default": False, "runs": 1}]
    best = choose_best("judge", rows)
    assert best["model"] == "c" and "cheaper" in best["reason"] and best["clears_bar"] is True


def test_fixer_best_prefers_gap_closed_then_cost():
    rows = [{"stage": "fixer", "model": "d", "effort": "medium", "gap_closed_rate": 0.8, "rejected": 1, "cost_per_fix": 0.001, "n": 30, "is_default": True, "runs": 1},
            {"stage": "fixer", "model": "w", "effort": "medium", "gap_closed_rate": 0.9, "rejected": 0, "cost_per_fix": 0.05, "n": 30, "is_default": False, "runs": 1}]
    best = choose_best("fixer", rows)
    assert best["model"] == "w" and best["clears_bar"] is False  # it costs more


def test_navigator_best_prefers_screens_then_turns_then_cost():
    rows = [{"stage": "navigator", "model": "m", "effort": "low", "screens": 4.0, "turns": 9.0, "cost_usd_stage": 0.01, "is_default": True, "runs": 1},
            {"stage": "navigator", "model": "m", "effort": "high", "screens": 3.0, "turns": 5.0, "cost_usd_stage": 0.01, "is_default": False, "runs": 1},
            {"stage": "navigator", "model": "m", "effort": "medium", "screens": 4.0, "turns": 12.0, "cost_usd_stage": 0.02, "is_default": False, "runs": 1}]
    assert choose_best("navigator", rows)["effort"] == "low"


def test_merge_sweep_block_leaves_the_main_tables_timestamp_and_commit_alone():
    from eval.harness import merge_latest

    existing = {"labels_sha256": "L", "git_sha": "main-numbers", "updated_at": "2026-11-03", "configs": {"full": {"runs": 3, "total": {}}}}
    out = merge_latest(existing, merge_sweep_block({"stages": {}, "best": {}, "labels_sha256": "L", "git_sha": "sweep"}))
    assert out["git_sha"] == "main-numbers" and out["updated_at"] == "2026-11-03" and out["model_sweep"]["git_sha"] == "sweep"


def test_render_sweep_discloses_n_and_marks_the_best_row():
    block = {"git_sha": "abc", "labels_sha256": "L", "generated_at": "t", "method": "one stage at a time", "spend_usd": 1.0, "wall_s": 10,
             "spike": {"m": {"json": {"ok": True}, "grounding": {"ok": True}, "computer": {"ok": False, "refused": "HTTP 400"}}},
             "stages": {"seer": {"rows": [_row("seer", "d", "medium", 0.85, 0.99, 0.37, default=True, fp_on_clean=0.0, accuracy=0.9, n_per_run=33, rejection_rate=0.1, jaccard=None, tokens=1, cost_usd=0.37, stages={})]}},
             "best": {"seer": {"model": "d", "effort": "medium", "reason": "the default", "margin": "none", "clears_bar": False}}}
    md = render_sweep(block)
    assert "n = 1" in md and "| **d** |" in md or "**d**" in md
    assert "HTTP 400" in md and "best" in md.lower()


def test_an_unpriced_model_never_wins_on_cost():
    rows = [_row("seer", "d", "medium", 0.85, 0.99, 0.37, default=True), _row("seer", "muse-spark-1.1", "medium", 0.85, 0.99, 0.0, unpriced=True)]
    best = choose_best("seer", rows, spread_labels=3, n_faults=38)
    assert best["model"] == "d"
    alone = choose_best("seer", [_row("seer", "muse-spark-1.1", "medium", 0.95, 0.99, 0.0, unpriced=True), _row("seer", "d", "medium", 0.60, 0.99, 0.37, default=True)], spread_labels=3, n_faults=38)
    assert alone["model"] == "muse-spark-1.1" and alone["clears_bar"] is False and "inf" not in alone["reason"] and "price unknown" in alone["reason"]


def test_parse_row_spec():
    from eval.model_sweep import parse_row

    assert parse_row("comparator:muse-wonder-1.0:high") == ("comparator", "muse-wonder-1.0", "high")
    for bad in ("comparator:m", "nope:m:low", "seer:m:max"):
        with pytest.raises(ValueError):
            parse_row(bad)


def test_row_env_sets_only_the_swept_stage_and_the_cheap_judge_where_it_cannot_change_the_score():
    from eval.model_sweep import row_env

    env = row_env("seer", "m", "high", cheap_judge=True)
    assert env == {"PARITY_SEER_MODEL": "m", "PARITY_SEER_EFFORT": "high", "PARITY_JUDGE_MODEL": "muse-spark-1.3-contributor"}
    assert "PARITY_JUDGE_MODEL" not in row_env("seer", "m", "high", cheap_judge=False)
    assert row_env("judge", "m", "low", cheap_judge=True) == {"PARITY_JUDGE_MODEL": "m", "PARITY_JUDGE_EFFORT": "low"}
    assert row_env("fixer", "m", "low", cheap_judge=True) == {"PARITY_FIXER_MODEL": "m", "PARITY_FIXER_EFFORT": "low"}


async def _base(tmp_path, server_url, page):
    """A small recorded eval, as seen-full is: one page, one run, offline."""
    from eval.harness import run_eval
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    data = tmp_path / "base" / "data"
    result = await run_eval(client=FakeMetaClient(META, stage_defaults=stage_defaults()), base_url=server_url, pages=["checkout.html"], runs=1, configs=["full"],
                            data_dir=data, page_factory=factory, judge_models=[])
    return data, {"checkout.html": result["configs"]["full"]["per_page"]["checkout.html"]["runs"][0]["run_id"]}


async def test_detection_row_records_a_run_and_keeps_it_on_disk(tmp_path, server_url, page):
    from eval.model_sweep import run_detection_row
    from parity.meta.client import TraceRouter
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    client = FakeMetaClient(META, trace=TraceRouter(), stage_defaults=stage_defaults())
    records = await run_detection_row("seer", "m-seer", "low", runs=1, base_url=server_url, row_dir=tmp_path / "row", env_base={}, client_factory=lambda s, r: client,
                                      pages=["checkout.html"], page_factory=factory, cheap_judge=True, log=lambda *_: None)
    rec = records[0]
    assert "f5" in rec["hits"] and rec["n"] >= 1 and rec["candidates"] >= rec["n"] and rec["run_ids"]["checkout.html"]
    assert "seer" in rec["stages"] and rec["status"] and (tmp_path / "row" / "records.json").exists()
    assert {c["model"] for c in client.calls if c.get("reasoning", {}).get("effort") == "low"} >= {"m-seer"}
    again = await run_detection_row("seer", "m-seer", "low", runs=1, base_url=server_url, row_dir=tmp_path / "row", env_base={}, client_factory=lambda s, r: client,
                                    pages=["checkout.html"], page_factory=factory, cheap_judge=True, log=lambda *_: None)
    assert again == records  # a row already on disk is never paid for twice


async def test_judge_row_rejudges_the_same_findings_and_fails_closed(tmp_path, server_url, page):
    from eval.model_sweep import judge_default_row, run_judge_row
    from parity.meta.client import MetaError
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    data, run_ids = await _base(tmp_path, server_url, page)
    default = await judge_default_row(data, run_ids, base_url=server_url)
    assert default["n"] >= 1 and default["is_default"] is True and default["cost_per_finding"] >= 0

    fine = FakeMetaClient(META, stage_defaults=stage_defaults())
    row = await run_judge_row("m-judge", "low", data, run_ids, base_url=server_url, client=fine, log=lambda *_: None)
    assert row["n"] == default["n"] and row["needs_review_rate"] == 0.0 and "severity_same" in row
    assert all(c["model"] == "m-judge" and c["reasoning"]["effort"] == "low" for c in fine.calls)

    broken = FakeMetaClient(META, stage_defaults=stage_defaults(), errors={"judge": MetaError("boom", status=500, request_id="r", attempts=5)})
    closed = await run_judge_row("m-judge", "low", data, run_ids, base_url=server_url, client=broken, log=lambda *_: None)
    assert closed["needs_review_rate"] == 1.0


async def test_fixer_row_scores_the_gap_closed_rate_on_the_recorded_barriers(tmp_path, server_url, page, monkeypatch):
    from eval.model_sweep import run_fixer_row
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    data, run_ids = await _base(tmp_path, server_url, page)
    client = FakeMetaClient(META, stage_defaults=stage_defaults())
    row = await run_fixer_row("m-fix", "high", data, run_ids, base_url=server_url, client=client, page_factory=factory, concurrency=1, log=lambda *_: None)
    assert row["n"] >= 1 and 0.0 <= row["gap_closed_rate"] <= 1.0 and row["proposed"] + row["rejected"] == row["n"]
    assert any(c["model"] == "m-fix" and c["reasoning"]["effort"] == "high" for c in client.calls)


async def test_navigator_row_counts_screens_turns_and_safety(tmp_path, server_url, page):
    from eval.model_sweep import run_navigator_row
    from parity.meta.client import TraceRouter
    from parity.meta.fake import FakeMetaClient
    from tests.test_agent import function_call, turn
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    client = FakeMetaClient(META, trace=TraceRouter(), stage_defaults=stage_defaults(), script={"auditor": [turn(function_call("finish", {"summary": "done"}, "c1"), rid="r1")]})
    records = await run_navigator_row("m-nav", "medium", runs=1, base_url=server_url, row_dir=tmp_path / "nav", env_base={}, client_factory=lambda s, r: client, page_factory=factory, max_turns=1, cheap_judge=True, log=lambda *_: None)
    rec = records[0]
    assert rec["screens"] == 1 and rec["turns"] == 1 and "auditor" in rec["stages"] and rec["safety_checks"] == 0


def _spec_row(path, records):
    path.mkdir(parents=True, exist_ok=True)
    (path / "records.json").write_text(__import__("json").dumps(records))


def test_build_block_reads_rows_from_disk_and_chooses_per_stage(tmp_path):
    import json

    from eval.model_sweep import build_block

    sweep = tmp_path / "sweep"
    (sweep / "rows").mkdir(parents=True)
    (sweep / "spike.json").write_text(json.dumps({"m": {"json": {"ok": True}}}))
    (sweep / "spike-spend.json").write_text("0.1")
    base = [_run(32, cost=0.37, judge_cost=0.35), _run(33, cost=0.37, judge_cost=0.35), _run(31, cost=0.37, judge_cost=0.35)]
    (sweep / "base-records.json").write_text(json.dumps(base))
    _spec_row(sweep / "rows" / "comparator--muse-wonder-1.0--medium", [_run(36, cost=0.9, judge_cost=0.03)])
    _spec_row(sweep / "rows" / "seer--muse-spark-1.1--medium", [_run(32, cost=0.1, judge_cost=0.03)])
    _spec_row(sweep / "rows" / "comparator--muse-spark-1.2-contributor--low", [{**_run(0, cost=0.0, judge_cost=0.0), "status": ["failed"], "errors": ["HTTP 400"]}])
    nav = {"status": ["done"], "screens": 4, "turns": 9, "finished": True, "refusals": 0, "blocked": 0, "safety_checks": 5, "stages": {"auditor": {"calls": 9, "tokens": 9, "cost_usd": 0.01, "latency_ms_mean": 5000}}, "cost_usd_stage": 0.01, "cost_usd": 0.05, "seconds": 300, "tokens": 9, "n": 7, "reached": [], "request_ids": ["n"], "run_id": "x", "error": None}
    _spec_row(sweep / "rows" / "navigator--muse-spark-1.3-contributor--low", [nav, nav])
    (sweep / "rows" / "judge--muse-spark-1.3-contributor--medium").mkdir()
    (sweep / "rows" / "judge--muse-spark-1.3-contributor--medium" / "row.json").write_text(json.dumps({"stage": "judge", "model": "muse-spark-1.3-contributor", "effort": "medium", "runs": 1, "n": 33, "agreement": 0.94, "needs_review_rate": 0.0, "cost_per_finding": 0.001, "cost_usd": 0.03, "seconds": 100, "request_ids": ["j"]}))
    block = build_block(sweep, judge_default={"stage": "judge", "model": "muse-spark-1.3", "effort": "medium", "is_default": True, "runs": 1, "n": 33, "agreement": 0.94, "needs_review_rate": 0.0, "cost_per_finding": 0.0108, "cost_usd": 0.35, "request_ids": []},
                        git_sha="abc", labels_sha="L", n_faults=38, n_clean=20)
    comp = block["stages"]["comparator"]["rows"]
    assert {r["model"] for r in comp} == {"muse-spark-1.3-contributor", "muse-wonder-1.0", "muse-spark-1.2-contributor"}
    default = next(r for r in comp if r["is_default"])
    assert default["runs"] == 3 and default["cost_default_judge_usd"] == pytest.approx(0.37, abs=0.01)
    assert next(r for r in comp if r["model"] == "muse-spark-1.2-contributor")["failed"] == "HTTP 400"
    assert next(r for r in block["stages"]["seer"]["rows"] if r["model"] == "muse-spark-1.1")["unpriced"] is True
    assert block["best"]["judge"]["model"] == "muse-spark-1.3-contributor"
    assert block["best"]["navigator"]["effort"] == "low" and block["stages"]["navigator"]["rows"][0]["screens"] == 4
    assert block["spend_usd"] == pytest.approx(0.1 + 0.9 + 0.1 + 0.05 * 2 + 0.03)  # new spend only: the recorded default row is not counted
    assert block["records"]["navigator--muse-spark-1.3-contributor--low"][0]["request_ids"] == ["n"]
    assert block["spread_labels"] == 2


def test_write_sweep_writes_the_files_and_keeps_records_out_of_latest(tmp_path):
    import json

    from eval.model_sweep import write_sweep

    (tmp_path / "latest.json").write_text(json.dumps({"labels_sha256": "L", "updated_at": "kept", "git_sha": "main", "configs": {}}))
    block = {"labels_sha256": "L", "git_sha": "s", "generated_at": "t", "method": "m", "spend_usd": 1.0, "wall_s": 1, "spike": {}, "best": {}, "stages": {"seer": {"rows": [{**_row("seer", "d", "medium", 0.8, 0.9, 0.3, default=True, fp_on_clean=0.0, accuracy=0.9, n_per_run=33, rejection_rate=0.1, jaccard=None, tokens=1, cost_usd=0.3, stages={}), "request_ids": ["x"]}]}}, "records": {"a": [1]}, "spread_labels": 2}
    write_sweep(block, tmp_path)
    full = json.loads((tmp_path / "model-sweep.json").read_text())
    latest = json.loads((tmp_path / "latest.json").read_text())
    assert full["records"] == {"a": [1]} and "records" not in latest["model_sweep"] and "request_ids" not in latest["model_sweep"]["stages"]["seer"]["rows"][0]
    assert latest["updated_at"] == "kept" and latest["git_sha"] == "main"
    assert "Best model" in (tmp_path / "latest.md").read_text() or "seer" in (tmp_path / "latest.md").read_text().lower()
    assert (tmp_path / "model-sweep.md").exists()


def test_model_sweep_flag_rebuilds_from_the_committed_file_without_a_key_or_a_call(tmp_path, monkeypatch):
    import json

    from eval import harness
    from eval import model_sweep as ms

    monkeypatch.setattr(ms, "SWEEP_DIR", tmp_path / "absent")
    monkeypatch.setattr(harness, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(harness, "load_settings", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no settings needed")))
    block = {"labels_sha256": "L", "git_sha": "s", "generated_at": "t", "method": "m", "spend_usd": 1.0, "wall_s": 1, "spike": {}, "best": {}, "stages": {}, "records": {}, "spread_labels": 2}
    (tmp_path / "model-sweep.json").write_text(json.dumps(block))
    assert harness.main(["--model-sweep"]) == 0
    assert (tmp_path / "model-sweep.md").exists()


def test_sam_sentence_states_the_replay_and_what_it_did_not_test():
    sam = {"candidates": 114, "percepts": 341, "runs": 3, "images": 40, "estimated_cost_usd": 0.1, "baseline_recall": 0.85, "sam_recall": 0.83, "baseline_precision": 0.99, "sam_precision": 1.0,
           "baseline_verified": 98, "sam_verified": 95, "baseline_located_failures": 2, "sam_located_failures": 2, "median_iou_node_recorded": 1.0, "median_iou_node_sam": 0.86,
           "median_iou_percept_recorded": 0.61, "median_iou_percept_sam": 0.75, "sam_percepts_recall": 0.85, "sam_percepts_precision": 0.99, "concepts": {"button": 10, "link": 0}}
    from eval import model_sweep as ms

    text = ms.sam_sentence(sam)
    assert "recall 85% to 83%" in text and "1.00 to 0.86" in text and "1 of 2 nouns" in text and "Not tested" in text
    assert "### SAM 3.1 box prompts" in ms.render_sweep({"sam_boxes": sam})
    public = ms._public({"sam_boxes": {**sam, "request_ids": ["r"]}})
    assert public["sam_note"] == text and "request_ids" not in public["sam_boxes"]


def test_merge_fixer_runs_means_the_rates_and_reports_the_spread():
    from eval import model_sweep as ms

    a = {"n": 29, "gap_closed": 15, "gap_closed_rate": 15 / 29, "rejected": 0, "cost_per_fix": 0.01, "cost_usd": 1.0, "seconds": 10, "request_ids": ["a"], "outcomes": [{"id": "x"}]}
    b = {**a, "gap_closed": 19, "gap_closed_rate": 19 / 29, "cost_per_fix": 0.03, "request_ids": ["b"]}
    assert ms.merge_fixer_runs([a]) is a
    merged = ms.merge_fixer_runs([a, b])
    assert merged["runs"] == 2 and merged["gap_closed"] == 17 and merged["gap_closed_spread"] == 4 and merged["request_ids"] == ["a", "b"]
    assert abs(merged["gap_closed_rate"] - 17 / 29) < 1e-9 and abs(merged["cost_per_fix"] - 0.02) < 1e-9
