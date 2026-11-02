"""Phase 6b, the W3C BAD benchmark (doc 19 §19.1): labels we did not write, anchor matching, the external metrics."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "eval" / "labels_external.json"
PAGES = {"home": 10, "news": 10, "tickets": 8, "survey": 7}  # W3C's own numbering: annot_01..NN on each demo page


def test_external_labels_are_well_formed():
    doc = json.loads(EXTERNAL.read_text())
    assert "W3C" in doc["copyright"] and "2012" in doc["copyright"]
    rows = doc["rows"]
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)) and rows
    for r in rows:
        assert set(r) >= {"page", "id", "kind", "w3c", "description", "sc", "in_scope", "anchor", "clean"}, r["id"]
        assert r["page"].startswith(("bad/before/", "bad/after/")) and r["clean"] == r["page"].startswith("bad/after/")
        assert isinstance(r["in_scope"], bool)
        (key, value), = r["anchor"].items()
        assert key in {"src", "text", "html", "css"} and value.strip()
        assert r["sc"] and all(re.fullmatch(r"\d\.\d(\.\d{1,2})?", s) for s in r["sc"]), r["id"]
    before = [r for r in rows if not r["clean"]]
    after_ids = {r["id"] for r in rows if r["clean"]}
    for r in before:
        assert r.get("no_counterpart") is True or r["counterpart"] in after_ids, r["id"]
    by_kind: dict[str, set[bool]] = {}
    for r in before:
        by_kind.setdefault(r["kind"], set()).add(r["in_scope"])
    assert all(len(v) == 1 for v in by_kind.values()), "in_scope is decided by kind, never per row"
    assert set(doc["scope"]["in_scope_kinds"]) == {r["kind"] for r in before if r["in_scope"]}
    assert set(doc["scope"]["out_of_scope_kinds"]) == {r["kind"] for r in before if not r["in_scope"]}
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["page"]] = counts.get(r["page"], 0) + 1
    assert counts == {f"bad/{k}/{p}.html": n for k in ("before", "after") for p, n in PAGES.items()}
