"""The eval harness: deterministic matching and arithmetic, and one offline end-to-end run against the store."""

import json
from pathlib import Path

import pytest

from eval.harness import axe_baseline, judge_agreement, match, metrics
from parity.store.models import AxeViolation, Element, Judgement, Severity

ROOT = Path(__file__).resolve().parents[1]
LABELS = json.loads((ROOT / "eval" / "labels.json").read_text())
CHECKOUT = [r for r in LABELS if r["page"] == "checkout.html"]


class F:  # the slice of a Finding the matcher needs
    def __init__(self, dom_id, judgement=None, fid=None):
        self.id = fid or f"f-{dom_id}"
        self.element = Element(backend_id=1, css_path=f"#{dom_id}" if dom_id else "", dom_id=dom_id)
        self.judgement = judgement


def test_match_by_dom_id():
    findings = [F("f5"), F("f2"), F("save-later"), F(None), F("f5", fid="dup")]
    m = match(findings, CHECKOUT)
    assert m.hits == {"f5", "f2"}  # distinct fault labels found
    assert m.missed == {r["id"] for r in CHECKOUT if not r["clean"]} - {"f5", "f2"}
    assert m.fp_on_clean == ["f-save-later"]
    assert m.unlabelled == ["f-None"]
    assert m.n_findings == 5 and m.n_faults == sum(not r["clean"] for r in CHECKOUT)


def test_metrics_arithmetic():
    m = match([F("f5"), F("f2"), F("save-later"), F(None)], CHECKOUT)
    out = metrics(m)
    faults = sum(not r["clean"] for r in CHECKOUT)
    assert out["recall"] == pytest.approx(2 / faults)
    assert out["precision"] == pytest.approx(2 / 4)  # a clean control and an unlabelled node both count against precision
    assert out["fp_on_clean"] == 1 and out["n"] == 4 and out["n_labels"] == faults
    assert metrics(match([], CHECKOUT)) == {"recall": 0.0, "precision": 0.0, "fp_on_clean": 0, "n": 0, "n_labels": faults}


def test_axe_baseline_counts():
    violations = [AxeViolation(id="image-alt", impact="critical", targets=["#f1", "img#gallery-1"], backend_ids=[]),
                  AxeViolation(id="label", impact="serious", targets=["#name"], backend_ids=[])]
    out = axe_baseline(violations, CHECKOUT)
    assert out["hits"] == {"f1"} and out["recall"] == pytest.approx(1 / sum(not r["clean"] for r in CHECKOUT))
    assert out["violations"] == 2 and out["on_clean"] == ["#name"]
    assert axe_baseline([], CHECKOUT)["recall"] == 0.0


def test_judge_agreement_arithmetic():
    yes = Judgement(is_barrier=True, severity=Severity.serious)
    no = Judgement(is_barrier=False, severity=Severity.minor)
    unsure = Judgement(is_barrier=None, severity=Severity.needs_review)
    findings = [F("f5", yes), F("f2", no), F("save-later", no), F("f4", unsure)]
    out = judge_agreement(findings, CHECKOUT, judge_cost_usd=0.08)
    # f5 fault+yes agrees, f2 fault+no disagrees, save-later clean+no agrees, f4 unsure is neither
    assert out["agreement"] == pytest.approx(2 / 3) and out["needs_review_rate"] == pytest.approx(1 / 4)
    assert out["cost_per_finding"] == pytest.approx(0.02) and out["n"] == 4


async def test_harness_offline_run_on_checkout(tmp_path, server_url, page):
    """One page, one run, full configuration, recorded model answers: the hero is matched and the file has the right shape."""
    from eval.harness import run_eval
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    client = FakeMetaClient(META, stage_defaults=stage_defaults())
    result = await run_eval(client=client, base_url=server_url, pages=["checkout.html"], runs=1, configs=["full"],
                            data_dir=tmp_path / "data", page_factory=factory, judge_models=[])
    full = result["configs"]["full"]
    assert full["total"]["n_labels"] == sum(not r["clean"] for r in CHECKOUT) and full["total"]["n"] >= 1
    assert "f5" in full["per_page"]["checkout.html"]["hits"] and full["total"]["recall"] > 0
    assert full["per_page"]["checkout.html"]["cost_usd"] >= 0 and full["per_page"]["checkout.html"]["seconds"] > 0
    assert result["axe"]["violations"] == 0 and result["axe"]["recall"] == 0.0
    assert result["model"] and result["labels"] == str(Path("eval/labels.json"))


def test_merge_latest_keeps_the_richer_configs_and_all_judges():
    """Two harness invocations (ablations x3 runs; sweeps x1 run) must not clobber each other's part of latest.json."""
    from eval.harness import merge_latest

    existing = {"configs": {"full": {"total": {"recall": 0.8}, "runs": 3}}, "judge": {"muse-spark-1.3": {"n": 30}}, "effort_sweep": {"low": {}}}
    sweeps = {"configs": {"full": {"total": {"recall": 0.7}, "runs": 1}, "tree_only": {"total": {}, "runs": 1}}, "judge": {"muse-wonder-1.0": {"n": 30}},
              "standard_tier_check": {"model": "muse-spark-1.3"}, "generated_at": "t2"}
    out = merge_latest(existing, sweeps)
    assert out["configs"]["full"]["runs"] == 3 and out["configs"]["full"]["total"]["recall"] == 0.8  # the 3-run result stays
    assert out["configs"]["tree_only"]["runs"] == 1  # a configuration not seen before is added
    assert set(out["judge"]) == {"muse-spark-1.3", "muse-wonder-1.0"}
    assert out["effort_sweep"] == {"low": {}} and out["standard_tier_check"]["model"] == "muse-spark-1.3"
    assert out["updated_at"] == "t2"
