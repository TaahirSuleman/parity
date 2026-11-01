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
    def __init__(self, dom_id, judgement=None, fid=None, css_path=None):
        self.id = fid or f"f-{dom_id}"
        self.element = Element(backend_id=1, css_path=css_path if css_path is not None else (f"#{dom_id}" if dom_id else ""), dom_id=dom_id)
        self.judgement = judgement


def test_match_by_dom_id():
    findings = [F("f5"), F("f2"), F("save-later"), F(None), F("f5", fid="dup")]
    m = match(findings, CHECKOUT)
    assert m.hits == {"f5", "f2"}  # distinct fault labels found
    assert m.missed == {r["id"] for r in CHECKOUT if not r["clean"]} - {"f5", "f2"}
    assert m.fp_on_clean == ["f-save-later"]
    assert m.unlabelled == ["f-None"]
    assert m.n_findings == 5 and m.n_faults == sum(not r["clean"] for r in CHECKOUT)


def test_match_uses_the_nearest_id_in_the_css_path():
    """A label on a wrapper (span#k4 > img[alt=""]) is hit by a finding located on the inner img, which has no id of its own:
    the same rule axe's baseline is scored under. An id further up than the nearest one does not count."""
    cart = [r for r in LABELS if r["page"] == "cart.html"]
    clean_id = next(r["id"] for r in cart if r["clean"])
    findings = [F(None, fid="img-in-k4", css_path="div#summary > span#k4 > img:nth-of-type(1)"),
                F(None, fid="img-in-clean", css_path=f"span#{clean_id} > img:nth-of-type(1)"),
                F(None, fid="nowhere", css_path="body > div:nth-of-type(2) > p:nth-of-type(1)")]
    m = match(findings, cart)
    assert m.hits == {"k4"} and m.by_finding["img-in-k4"] == "k4"
    assert m.fp_on_clean == ["img-in-clean"] and m.unlabelled == ["nowhere"]


def test_provenance_names_the_code_and_the_labels(tmp_path):
    """Every results file says which code and which labels produced it, so files from different versions are never merged."""
    import hashlib

    from eval.harness import provenance

    labels = tmp_path / "labels.json"
    labels.write_text("[]")
    p = provenance(labels)
    assert p["labels_sha256"] == hashlib.sha256(b"[]").hexdigest()
    assert len(p["git_sha"]) >= 7 and isinstance(p["git_dirty"], bool)


def test_configs_for_adds_full_when_a_sweep_needs_it():
    from eval.harness import configs_for

    assert configs_for(ablations=False, no_screenshot=False, no_tree=True, no_grounding=False, needs_full=False) == ["screenshot_only"]
    assert configs_for(ablations=False, no_screenshot=False, no_tree=True, no_grounding=False, needs_full=True) == ["full", "screenshot_only"]
    assert configs_for(ablations=True, no_screenshot=False, no_tree=False, no_grounding=False, needs_full=True) == ["full", "screenshot_only", "tree_only", "no_grounding"]
    assert configs_for(ablations=False, no_screenshot=False, no_tree=False, no_grounding=False, needs_full=False) == ["full"]


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
    assert len(result["labels_sha256"]) == 64 and result["git_sha"]  # provenance travels with the numbers


async def test_axe_and_judge_rows_need_a_full_run(tmp_path, server_url, page):
    """An ablation-only invocation has no full run to score axe or the judge on: those sections stay empty rather than
    becoming zeros that would overwrite the real rows in latest.json."""
    from eval.harness import merge_latest, run_eval
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    client = FakeMetaClient(META, stage_defaults=stage_defaults())
    result = await run_eval(client=client, base_url=server_url, pages=["checkout.html"], runs=1, configs=["tree_only"],
                            data_dir=tmp_path / "data", page_factory=factory, judge_models=["muse-wonder-1.0"])
    assert result["axe"] == {} and result["judge"] == {}
    existing = {"axe": {"recall": 0.0, "violations": 0}, "judge": {"muse-spark-1.3": {"n": 29}}, "labels_sha256": result["labels_sha256"]}
    merged = merge_latest(existing, result)
    assert merged["axe"] == existing["axe"] and merged["judge"] == existing["judge"]


async def test_judge_error_during_rejudge_becomes_needs_review(tmp_path, server_url, page):
    """A comparison judge that errors after its retries does not lose the paid run: the finding is needs_review, as in the product."""
    from eval.harness import run_eval
    from parity.meta.client import MetaError
    from parity.meta.fake import FakeMetaClient
    from tests.test_runner import META, stage_defaults

    async def factory():
        return page

    client = FakeMetaClient(META, stage_defaults=stage_defaults(), errors={"muse-wonder-1.0": MetaError("boom", status=503, request_id="r", attempts=5)})
    result = await run_eval(client=client, base_url=server_url, pages=["checkout.html"], runs=1, configs=["full"],
                            data_dir=tmp_path / "data", page_factory=factory, judge_models=["muse-wonder-1.0"])
    wonder = result["judge"]["muse-wonder-1.0"]
    assert wonder["n"] >= 1 and wonder["needs_review_rate"] == 1.0 and wonder["decided"] == 0


def test_merge_latest_keeps_the_richer_configs_and_one_judge_table():
    """Two harness invocations (ablations x3 runs; sweeps x1 run) must not clobber each other's configurations; the judge table
    is one invocation's (its rows are on the same verified findings), so a new one replaces it wholesale."""
    from eval.harness import merge_latest

    existing = {"configs": {"full": {"total": {"recall": 0.8}, "runs": 3}}, "judge": {"muse-spark-1.3": {"n": 30}}, "effort_sweep": {"low": {}}, "labels_sha256": "L"}
    sweeps = {"configs": {"full": {"total": {"recall": 0.7}, "runs": 1}, "tree_only": {"total": {}, "runs": 1}},
              "judge": {"muse-spark-1.3": {"n": 28}, "muse-wonder-1.0": {"n": 28}},
              "standard_tier_check": {"model": "muse-spark-1.3"}, "generated_at": "t2", "labels_sha256": "L"}
    out = merge_latest(existing, sweeps)
    assert out["configs"]["full"]["runs"] == 3 and out["configs"]["full"]["total"]["recall"] == 0.8  # the 3-run result stays
    assert out["configs"]["tree_only"]["runs"] == 1  # a configuration not seen before is added
    assert out["judge"] == sweeps["judge"]
    assert out["effort_sweep"] == {"low": {}} and out["standard_tier_check"]["model"] == "muse-spark-1.3"
    assert out["updated_at"] == "t2"


def test_merge_latest_starts_over_when_the_labels_or_code_changed():
    """Numbers measured against other labels are not comparable: a changed labels file replaces latest.json instead of merging."""
    from eval.harness import merge_latest

    existing = {"configs": {"full": {"total": {"recall": 0.8}, "runs": 3}, "tree_only": {"runs": 3}}, "labels_sha256": "OLD", "effort_sweep": {"low": {}}}
    new = {"configs": {"full": {"total": {"recall": 0.7}, "runs": 1}}, "labels_sha256": "NEW", "generated_at": "t3"}
    out = merge_latest(existing, new)
    assert out["configs"] == new["configs"] and "effort_sweep" not in out and out["labels_sha256"] == "NEW"


def test_latest_md_carries_the_public_sample_rows(tmp_path):
    """public.json is written by hand after each anonymised sample; latest.md (what the README quotes) shows those rows too."""
    from eval.harness import write_results

    out = tmp_path / "results"
    out.mkdir()
    (out / "public.json").write_text(json.dumps([{"name": "Site A", "run_id": "public-a", "pages": 2, "verified": 6, "rejected": 0, "status": "done", "note": ""}]))
    write_results({"generated_at": "t1", "labels_sha256": "L", "configs": {}, "axe": {}, "judge": {}}, out_dir=out, name="x")
    md = (out / "latest.md").read_text()
    assert "Real-world sample" in md and "| Site A | 2 | 6 | 0 |" in md
    assert "public" not in json.loads((out / "latest.json").read_text())  # the samples stay in their own file
