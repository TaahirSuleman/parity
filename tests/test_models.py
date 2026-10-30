from parity.store.models import (
    BBox,
    Check,
    Element,
    Finding,
    FindingStatus,
    RunStatus,
    Severity,
    VerifierResult,
)


def test_bbox_clamps():
    b = BBox(x_min=-5, y_min=0, x_max=1200, y_max=10)
    assert (b.x_min, b.x_max) == (0, 1000)


def test_finding_roundtrip():
    f = Finding(
        id="f1",
        run_id="r1",
        step_index=0,
        status=FindingStatus.verified,
        sighted_text="Pay R1,249",
        sr_role="button",
        sr_name="Submit",
        bbox=BBox(x_min=10, y_min=20, x_max=30, y_max=40),
        element=Element(backend_id=7, css_path="button#f5", box_px=(1, 2, 3, 4), outer_html="<button>", dom_id="f5"),
        verifier=VerifierResult(passed=True, checks={"located": Check(passed=True, detail="ok")}),
    )
    assert Finding.model_validate_json(f.model_dump_json()) == f


def test_enums_are_strings():
    assert RunStatus.awaiting_review == "awaiting_review"
    assert Severity.needs_review == "needs_review"
