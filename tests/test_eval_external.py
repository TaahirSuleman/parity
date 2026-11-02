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


# --- anchor matching (Task 26E.2) -----------------------------------------------------------------------

from eval.harness import axe_baseline, external_metrics, label_for, labels_for, load_labels, match_external  # noqa: E402
from parity.store.models import AxeViolation, Element  # noqa: E402

EXT = load_labels(EXTERNAL)
STORE = load_labels()
HOME = labels_for(EXT, "bad/before/home.html")
AFTER_HOME = labels_for(EXT, "bad/after/home.html")
SURVEY = labels_for(EXT, "bad/before/survey.html")
AFTER_SURVEY = labels_for(EXT, "bad/after/survey.html")
CHECKOUT = labels_for(STORE, "checkout.html")
CART = labels_for(STORE, "cart.html")


def el(outer_html: str = "", css_path: str = "", dom_id: str | None = None) -> Element:
    return Element(backend_id=1, css_path=css_path, outer_html=outer_html or None, dom_id=dom_id)


class F:  # the slice of a Finding the matcher reads
    def __init__(self, fid: str, element: Element, sighted_text: str = ""):
        self.id, self.element, self.sighted_text = fid, element, sighted_text


def test_load_labels_reads_the_external_file_shape():
    assert isinstance(STORE, list) and isinstance(EXT, list) and EXT[0]["id"] == "home-01"
    assert len(HOME) == 10 and len(AFTER_HOME) == 10


def test_label_for_prefers_dom_id():
    assert label_for(el(css_path="button#f5", dom_id="f5"), "Pay R1,249", CHECKOUT) == "f5"
    assert label_for(el(css_path="div#summary > span#k4 > img:nth-of-type(1)"), "", CART) == "k4"  # the nearest id above
    # an id that is not a label does not stop the anchors from being tried
    assert label_for(el(outer_html='<select name="cc" id="cc" title="cities of the world">', css_path="select#cc", dom_id="cc"), "", AFTER_SURVEY) == "after-survey-04"


def test_label_for_matches_src_file_name():
    logo = '<img src="../img/top_logo.gif" width="443px" height="86px" alt="Red dot with a white letter C...">'
    assert label_for(el(outer_html=logo, css_path="body > table:nth-of-type(1) > tbody > tr > td > a > img"), "CITYLIGHTS your access to the city", HOME) == "home-01"
    assert label_for(el(outer_html='<a href="../news/annotations"><img src="../img/morearrow.gif" alt=""></a>'), "", HOME) == "home-07"  # the link carries the image
    assert label_for(el(outer_html='<img src="../img/chart1.png" alt="Brain Donations...">'), "", HOME) is None  # another page's file


def test_label_for_matches_visible_text():
    assert label_for(el(outer_html='<a href="../tickets/annotations" style="text-decoration:none;">Read More...</a>'), "", HOME) == "home-05"
    assert label_for(el(outer_html='<a href="#"><img alt=""></a>'), "  read   more... ", HOME) == "home-05"  # the sighted text, normalised
    assert label_for(el(outer_html="<p>Read More... and then some</p>"), "", HOME) is None  # equality, not containment


def test_label_for_matches_html_fragment_and_css_path():
    assert label_for(el(outer_html='<input class="align" type="radio" name="res" value="2">'), "", SURVEY) == "survey-03"
    rows = [{"id": "x", "page": "p", "kind": "k", "in_scope": True, "clean": False, "anchor": {"css": "form > select:nth-of-type(1)"}}]
    assert label_for(el(css_path="body > form > select:nth-of-type(1)"), "", rows) == "x"
    assert label_for(el(css_path="body > div > select:nth-of-type(1)"), "", rows) is None


def test_external_metrics_count_in_scope_only_and_report_out_of_scope():
    before = [F("a", el(outer_html='<img src="../img/top_logo.gif">')), F("b", el(outer_html="<a>Heat wave linked to temperatures</a>")),
              F("c", el(outer_html="<p>nothing W3C labelled</p>")), F("d", el(outer_html='<img src="../img/top_logo.gif" class="dup">'))]
    after = [F("e", el(outer_html='<img src="../img/toplogo.png" alt="Citylights: your access to the city.">')), F("f", el(outer_html="<p>unlabelled on a repaired page</p>"))]
    home = match_external(before, HOME)
    assert home.hits == {"home-01"} and home.out_of_scope_hits == {"home-03"} and home.unlabelled == ["c"] and home.matched == 2
    assert home.n_in_scope == 7 and home.n_out_of_scope == 3 and home.fp == 0
    repaired = match_external(after, AFTER_HOME)
    assert repaired.on_clean == ["e"] and repaired.fp == 2 and repaired.hits == set()  # every finding on a repaired page is a false positive by construction
    totals = external_metrics({"bad/before/home.html": [home], "bad/after/home.html": [repaired]})
    assert totals["in_scope_recall"] == 1 / 7 and totals["precision"] == 2 / 4 and totals["fp_on_after_pages"] == 2
    assert totals["out_of_scope_hits"] == 1 and totals["unlabelled_on_before"] == 1 and totals["n"] == 6
    assert totals["n_in_scope"] == 7 and totals["out_of_scope_count"] == 3 and totals["n_clean"] == 10
    empty = external_metrics({"bad/before/home.html": [match_external([], HOME)]})
    assert empty["in_scope_recall"] == 0.0 and empty["precision"] == 0.0


def test_axe_baseline_scored_by_the_same_anchor():
    v = AxeViolation(id="image-alt", impact="critical", targets=["td > div > img"], backend_ids=[7], htmls=['<img src="../img/teaser_right1.jpg" width="150px" height="106px">'])
    w = AxeViolation(id="link-name", impact="serious", targets=['a[href$="annotations"]'], htmls=['<a href="../news/annotations"><img src="../img/morearrow.gif" alt=""></a>'])
    structural = AxeViolation(id="list", impact="serious", targets=["p:nth-child(4)"], htmls=['<p>Killer bees. <a href="../../offsite.html">Click here</a>'])
    out = axe_baseline([v, w, structural], HOME)
    assert out["hits"] == {"home-02", "home-07"} and out["recall"] == 2 / 7  # over the in-scope labels only
    assert out["violations"] == 3 and out["out_of_scope"] == {"home-09"}
    clean = axe_baseline([AxeViolation(id="x", targets=["img"], htmls=['<img src="../img/toplogo.png" alt="...">'])], AFTER_HOME)
    assert clean["on_clean"] == ["img"] and clean["recall"] == 0.0


def test_beyond_axe_recall_scores_parity_on_what_axe_misses():
    """The Verifier defers to axe-core by design (not_axe), so the block also says how Parity does on the in-scope barriers axe misses, and their union."""
    from eval.harness import beyond_axe

    home = match_external([F("a", el(outer_html='<img src="../img/top_logo.gif">')), F("b", el(outer_html='<img src="../img/teaser_right1.jpg">'))], HOME)
    in_scope = {"home-01", "home-02", "home-04", "home-05", "home-07", "home-08", "home-10"}
    b = beyond_axe({"bad/before/home.html": [home]}, axe_hits={"home-02", "home-07"}, in_scope_ids=in_scope)
    assert b["n_beyond_axe"] == 5 and b["recall_beyond_axe"] == 1 / 5 and b["union_recall"] == 3 / 7
    assert beyond_axe({}, axe_hits=set(), in_scope_ids=set()) == {"n_beyond_axe": 0, "recall_beyond_axe": 0.0, "union_recall": 0.0}
