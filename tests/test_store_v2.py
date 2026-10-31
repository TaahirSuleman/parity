"""Store v2: ~30 seeded, axe-passing faults and ~10 clean controls, labelled outside parity/ (spec §10, §13)."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "eval" / "labels.json"
KINDS = {"wrong-name", "meaningless-alt", "pixel-only", "icon-named-wrong", "error-visual-only", "link-text-mismatch",
         "state-visual-only", "hidden-price", "placeholder-as-label", "decorative-named"}


def labels() -> list[dict]:
    return json.loads(LABELS.read_text())


def test_labels_cover_the_store():
    rows = labels()
    assert {tuple(sorted(r)) for r in rows} == {("clean", "description", "id", "kind", "page")}
    faults = [r for r in rows if not r["clean"]]
    clean = [r for r in rows if r["clean"]]
    assert len(faults) >= 30 and len(clean) >= 10, (len(faults), len(clean))
    assert {r["kind"] for r in faults} == KINDS  # every seeded kind is represented
    assert all(r["kind"] == "clean" for r in clean)
    assert len({(r["page"], r["id"]) for r in rows}) == len(rows)  # unique per page
    assert {r["page"] for r in rows} == {"product.html", "cart.html", "checkout.html", "confirm.html"}
    hero = next(r for r in rows if r["page"] == "checkout.html" and r["id"] == "f5")
    assert hero["kind"] == "link-text-mismatch" and not hero["clean"]
    # the pages must not carry the kind: no label text or kind name appears as an attribute value in the HTML
    for page in {r["page"] for r in rows}:
        html = (ROOT / "store" / page).read_text()
        assert "data-parity" not in html and not re.search(r'(class|data-[a-z-]+)="[^"]*\b(fault|seeded|clean|barrier)\b', html), page


@pytest.mark.parametrize("page_name", ["product.html", "cart.html", "checkout.html", "confirm.html"])
async def test_every_label_id_exists_on_its_page(page, store_url, page_name):
    ids = [r["id"] for r in labels() if r["page"] == page_name]
    assert ids, f"no labels for {page_name}"
    await page.goto(store_url + page_name)
    present = await page.evaluate("ids => ids.filter(i => document.getElementById(i) !== null)", ids)
    assert present == ids
    dupes = [i for i, n in Counter(await page.evaluate("() => [...document.querySelectorAll('[id]')].map(e => e.id)")).items() if n > 1]
    assert dupes == []


def test_parity_never_imports_eval():
    """Labels live outside the agent's code path: nothing under parity/ may import or read eval/."""
    offenders = []
    for path in (ROOT / "parity").rglob("*.py"):
        text = path.read_text()
        if re.search(r"^\s*(from|import)\s+eval\b", text, re.M) or "labels.json" in text or '"eval/' in text or "'eval/" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


@pytest.mark.parametrize("page_name", ["product.html", "cart.html", "checkout.html", "confirm.html"])
async def test_every_labelled_element_is_inside_the_capture_viewport(page, store_url, page_name):
    """Capture is 1280x720: a seeded fault below the fold would be invisible to the pipeline and unfair to the eval."""
    ids = [r["id"] for r in labels() if r["page"] == page_name]
    await page.goto(store_url + page_name)
    out = await page.evaluate(
        "ids => ids.map(i => { const r = document.getElementById(i).getBoundingClientRect(); return [i, Math.round(r.bottom), Math.round(r.right), r.width > 0 && r.height > 0]; })"
        " .filter(([, b, r, v]) => !v || b > 720 || r > 1280)", ids)
    assert out == [], out
