import json
from pathlib import Path

import pytest

from parity.pipeline.verifier import CHECKS, NOT_ANNOUNCED, iou, locate, normalise, verify
from parity.store.models import AxeViolation, BBox, Candidate, Capture, Element, Finding, Percept, VerifierResult

FIXTURE = Path(__file__).parent / "fixtures" / "capture_checkout.json"


@pytest.fixture
def cap() -> Capture:
    return Capture.model_validate_json(FIXTURE.read_text())


def box_of(cap: Capture, dom_id: str) -> BBox:
    for n in [*cap.ax_nodes, *cap.silent_nodes]:
        if n.dom_id == dom_id and n.bbox:
            return n.bbox
    raise AssertionError(f"no node {dom_id}")


def cand(cap: Capture, dom_id: str | None, sighted: str, sr: str, bbox: BBox | None = None) -> Candidate:
    return Candidate(step_index=0, sighted_text=sighted, sr_quote=sr, bbox=bbox or (box_of(cap, dom_id) if dom_id else None))


def test_hero_passes(cap):
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [])
    assert r.passed is True
    assert tuple(r.checks) == CHECKS  # six since 4 Nov; percepts=None here, so seen passes as "no sighted pass"
    assert all(c.passed for c in r.checks.values())
    assert r.element and r.element.dom_id == "f5" and r.element.css_path == "button#f5"
    assert r.feedback is None


def test_quote_whitespace_case_normalised(cap):
    r = verify(cand(cap, "f5", "Pay R1,249", 'Button, " submit "'), cap, [])
    assert r.checks["sr_quote_exact"].passed is True


def test_wrong_quote_fails_with_feedback(cap):
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Pay now"'), cap, [])
    assert r.passed is False
    assert r.checks["sr_quote_exact"].passed is False
    assert "exact role and accessible name" in (r.feedback or "")
    assert "Submit" not in (r.feedback or "")  # feedback instructs; it never hands over the answer


def test_no_divergence_fails(cap):
    r = verify(cand(cap, "c2", "Save for later", 'button, "Save for later"'), cap, [])
    assert r.checks["diverges"].passed is False and r.passed is False


def test_missing_bbox_fails_located(cap):
    r = verify(cand(cap, None, "Pay R1,249", 'button, "Submit"', bbox=None), cap, [])
    assert r.checks["located"].passed is False and r.passed is False
    assert "box" in (r.feedback or "")


def test_out_of_range_bbox_fails_located(cap):
    r = verify(cand(cap, None, "Pay R1,249", 'button, "Submit"', bbox=BBox(x_min=995, y_min=995, x_max=1000, y_max=1000)), cap, [])
    assert r.checks["located"].passed is False


def test_canvas_not_announced_passes(cap):
    r = verify(cand(cap, "f2", "R1,249.00", NOT_ANNOUNCED), cap, [])
    assert r.passed is True, r.checks
    assert r.element and r.element.dom_id == "f2"


def test_not_announced_rejected_when_named(cap):
    r = verify(cand(cap, "c1", "Returns policy", NOT_ANNOUNCED), cap, [])
    assert r.checks["sr_quote_exact"].passed is False and r.passed is False


def test_axe_target_rejected(cap):
    f5 = next(n for n in cap.ax_nodes if n.dom_id == "f5")
    cap.axe_violations.append(AxeViolation(id="button-name", targets=["#f5"], backend_ids=[f5.backend_id]))
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [])
    assert r.checks["not_axe"].passed is False and r.passed is False


def test_duplicate_rejected(cap):
    first = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [])
    prior = Finding(
        id="x", run_id="r", step_index=0, sighted_text="Pay R1,249", sr_role="button", sr_name="Submit",
        bbox=box_of(cap, "f5"), element=first.element, verifier=first,
    )
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [prior])
    assert r.checks["unique"].passed is False and r.passed is False


def test_helpers():
    assert normalise('  Button,  "SUBMIT" ') == 'button, "submit"'
    assert iou(BBox(x_min=0, y_min=0, x_max=10, y_max=10), BBox(x_min=5, y_min=0, x_max=15, y_max=10)) == pytest.approx(1 / 3)
    assert iou(BBox(x_min=0, y_min=0, x_max=10, y_max=10), BBox(x_min=20, y_min=20, x_max=30, y_max=30)) == 0.0


def test_text_fragment_announced_in_full_does_not_diverge():
    """'Order SR-10428. …' read as one paragraph: flagging the <strong> fragment is a false positive."""
    from parity.pipeline.verifier import verify
    from parity.store.models import AxNode, BBox, Candidate, Capture

    nodes = [
        AxNode(backend_id=1, role="text", name="Order ", bbox=BBox(x_min=100, y_min=100, x_max=140, y_max=120)),
        AxNode(backend_id=2, role="text", name="SR-10428", bbox=BBox(x_min=140, y_min=100, x_max=200, y_max=120)),
        AxNode(backend_id=3, role="text", name=". Noise-cancelling headphones × 1, R1,249.00 charged to the card ending 1111.", bbox=BBox(x_min=200, y_min=100, x_max=700, y_max=120)),
        AxNode(backend_id=4, role="text", name="R1,599.00", bbox=BBox(x_min=100, y_min=200, x_max=180, y_max=220)),
    ]
    cap = Capture(step_index=0, url="http://x/store/confirm.html", ax_nodes=nodes)
    fragment = Candidate(step_index=0, sighted_text="Order SR-10428. Noise-cancelling headphones × 1, R1,249.00 charged to the card ending 1111.",
                         sr_quote='text, "SR-10428"', why_it_matters="x", bbox=BBox(x_min=140, y_min=100, x_max=200, y_max=120))
    r = verify(fragment, cap, [])
    assert r.passed is False and r.checks["diverges"].passed is False and "announced in full" in r.checks["diverges"].detail
    strike = Candidate(step_index=0, sighted_text="R1,599.00 crossed-out original price", sr_quote='text, "R1,599.00"', why_it_matters="x",
                       bbox=BBox(x_min=100, y_min=200, x_max=180, y_max=220))
    assert verify(strike, cap, []).checks["diverges"].passed is True  # the strike-through meaning is not announced anywhere


def test_locate_ignores_zero_area_offscreen_nodes():
    from parity.pipeline.verifier import locate
    from parity.store.models import AxNode, BBox

    visible = AxNode(backend_id=1, role="button", name="Place order", bbox=BBox(x_min=400, y_min=960, x_max=600, y_max=1000))
    offscreen = AxNode(backend_id=2, role="link", name="Privacy", bbox=BBox(x_min=400, y_min=1000, x_max=600, y_max=1000))  # clamped to a line
    assert locate(BBox(x_min=410, y_min=965, x_max=590, y_max=999), [offscreen, visible]) is visible


def test_parse_quote_strips_one_pair_of_quote_marks_and_keeps_the_rest():
    """'button, "Monitor 27""' quotes a name that ends in an inch mark exactly; stripping every quote character made the exact
    quote fail and dropped a correct finding."""
    from parity.pipeline.verifier import normalise, parse_quote

    assert parse_quote('button, "Monitor 27""') == ("button", normalise('Monitor 27"'))
    assert parse_quote('link, "Customers\'"') == ("link", normalise("Customers'"))
    assert parse_quote('heading, "“Quoted”"') == ("heading", normalise("“Quoted”"))
    assert parse_quote('button, "Submit"') == ("button", "submit")
    assert parse_quote("button, Submit") == ("button", "submit")
    assert parse_quote('button, "Submit') == ("button", "submit")  # a missing closing quote is forgiven


def test_parse_quote_is_linear_on_hostile_input():
    import time

    from parity.pipeline.verifier import parse_quote

    t0 = time.perf_counter()
    parse_quote("button" + " " * 20000 + ', "x"')
    parse_quote("x" * 50000)
    assert time.perf_counter() - t0 < 0.2


def test_parse_quote_bounds_hostile_lengths():
    """'a' + 20,000 spaces + 'b' took 1.8 s in the role regex (quadratic backtracking); a quote that long is not a role and a name."""
    import time

    from parity.pipeline.verifier import parse_quote

    t0 = time.perf_counter()
    for n in (2_000, 10_000, 20_000):
        parse_quote("a" + " " * n + "b")
    assert time.perf_counter() - t0 < 0.3


# --- seen: a candidate must have a seer percept behind it (the sixth check, 4 Nov) ---


def percept(text: str, bbox: BBox, kind: str = "text") -> Percept:
    return Percept(step_index=0, visible_text=text, kind=kind, bbox=bbox)


def test_seen_fails_a_tree_only_candidate_when_the_seer_saw_nothing(cap):
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [], percepts=[])
    assert r.passed is False
    assert r.checks["seen"].passed is False
    assert r.checks["seen"].detail == "no sighted percept with that text or at that box"
    assert r.feedback == "the sighted pass did not see that text at that box; only report what is on screen"


def test_seen_passes_when_a_percept_carries_the_sighted_text(cap):
    far_away = BBox(x_min=900, y_min=900, x_max=950, y_max=950)
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [], percepts=[percept("Pay R1,249", far_away, "button")])
    assert r.checks["seen"].passed is True and r.passed is True


def test_seen_passes_a_silent_candidate_by_box_alone(cap):
    box = box_of(cap, "f2")  # the canvas; no words in common with the percept
    r = verify(cand(cap, "f2", "Total: R1,249.00", NOT_ANNOUNCED), cap, [], percepts=[percept("a drawing", box, "image")])
    assert r.checks["seen"].passed is True and r.passed is True


def test_seen_passes_the_canvas_total_by_text_at_an_adjacent_box(cap):
    """The one miss of the box-only rule on the recorded runs: the seer lists the drawn price by its exact text, one row below the canvas."""
    canvas = BBox(x_min=185, y_min=419, x_max=295, y_max=461)
    below = BBox(x_min=145, y_min=462, x_max=266, y_max=491)
    assert iou(canvas, below) == 0.0
    r = verify(cand(cap, None, "Total: R1,249.00", NOT_ANNOUNCED, bbox=canvas), cap, [], percepts=[percept("Total: R1,249.00", below, "price")])
    assert r.checks["seen"].passed is True and r.passed is True


def test_seen_passes_when_no_sighted_pass_ran(cap):
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [], percepts=None)
    assert r.checks["seen"].passed is True and r.checks["seen"].detail == "no sighted pass on this screen"
    assert r.passed is True


def test_six_checks_are_named_and_carried(cap):
    assert CHECKS == ("located", "sr_quote_exact", "diverges", "not_axe", "unique", "seen")
    r = verify(cand(cap, "f5", "Pay R1,249", 'button, "Submit"'), cap, [], percepts=[percept("Pay R1,249", box_of(cap, "f5"), "button")])
    assert tuple(r.checks) == CHECKS and all(c.passed for c in r.checks.values())
