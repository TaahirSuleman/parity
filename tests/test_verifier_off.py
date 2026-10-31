"""Verifier on/off, post hoc: what a run would have reported without the gate. No model calls."""

import asyncio
import json

import pytest

from parity.cli import main as cli_main
from parity.meta.fake import FakeMetaClient
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.models import Candidate, Check, Rejected, RunStatus, VerifierResult
from parity.verifier_off import verifier_off
from tests.test_bundle import sample_finding, sample_run


async def seed(root) -> RunBundle:
    bundle = RunBundle(LocalBlobStore(root))
    run = sample_run("r1", RunStatus.done)
    run.findings_verified, run.findings_rejected = 2, 1
    await bundle.create(run)
    await bundle.write_finding(sample_finding("r1", "r1-f01"))
    second = sample_finding("r1", "r1-f02")
    second.sighted_text, second.sr_name = "Terms", "Click here"
    await bundle.write_finding(second)
    cand = Candidate(step_index=0, sighted_text="Delivery Free", sr_quote="not announced", bbox=None)
    vr = VerifierResult(passed=False, checks={"located": Check(passed=False, detail="no box given"), "sr_quote_exact": Check(passed=True)}, feedback="give the box")
    await bundle.write_rejected(Rejected(id="r1-r01", run_id="r1", step_index=0, candidate=cand, verifier=vr))
    dup = Candidate(step_index=0, sighted_text="Pay R1,249", sr_quote='button, "Submit"', bbox=None)
    dup_vr = VerifierResult(passed=False, checks={"located": Check(passed=True), "sr_quote_exact": Check(passed=True), "diverges": Check(passed=True), "not_axe": Check(passed=True), "unique": Check(passed=False, detail="already reported")})
    await bundle.write_rejected(Rejected(id="r1-r02", run_id="r1", step_index=0, candidate=dup, verifier=dup_vr))
    return bundle


async def test_verifier_off_reports_all_candidates(tmp_path):
    bundle = await seed(tmp_path)
    report = await verifier_off(bundle, "r1")
    assert report.run_id == "r1" and report.reported == 4 and report.verified == 2 and report.rejected_by_verifier == 2
    assert report.false_vs_labels is None
    # A rejection is a "false report" only when the evidence itself failed; a duplicate of a true finding is not.
    assert report.false_reports == 1 and report.duplicates == 1 and report.already_in_axe == 0
    bad = [c for c in report.candidates if not c.verifier_passed]
    assert {c.sighted_text: c.kind for c in bad} == {"Delivery Free": "false", "Pay R1,249": "duplicate"}
    assert bad[0].checks_failed == ["located"] or bad[1].checks_failed == ["located"]
    assert sorted(c.sighted_text for c in report.candidates if c.verifier_passed) == ["Pay R1,249", "Terms"]
    stored = json.loads(await bundle.store.get("runs/r1/verifier_off.json"))
    assert stored["reported"] == 4 and len(stored["candidates"]) == 4


async def test_verifier_off_makes_no_model_calls(tmp_path):
    bundle = await seed(tmp_path)
    fake = FakeMetaClient(tmp_path / "no-fixtures")  # any call would raise KeyError
    report = await verifier_off(bundle, "r1", client=fake)
    assert report.reported == 4 and fake.calls == []


async def test_verifier_off_unknown_run(tmp_path):
    bundle = RunBundle(LocalBlobStore(tmp_path))
    with pytest.raises(KeyError):
        await verifier_off(bundle, "nope")


def test_cli_verify_off_writes_file(tmp_path, capsys):
    """The CLI owns its own event loop, so this test is synchronous."""
    asyncio.run(seed(tmp_path / "data"))
    code = cli_main(["verify", "r1", "--off", "--data-dir", str(tmp_path / "data")])
    out = capsys.readouterr().out
    assert code == 0 and "reported 4" in out and "1 would be false" in out and "1 duplicate" in out
    assert (tmp_path / "data" / "runs" / "r1" / "verifier_off.json").exists()
    assert cli_main(["verify", "missing", "--off", "--data-dir", str(tmp_path / "data")]) == 1


def test_cli_index_rebuild(tmp_path, capsys):
    asyncio.run(seed(tmp_path / "data"))
    code = cli_main(["index", "rebuild", "--data-dir", str(tmp_path / "data"), "--index-path", str(tmp_path / "index.db")])
    assert code == 0 and "1 run" in capsys.readouterr().out
