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


def test_run_carries_its_source_and_the_visitor_fields():
    """Spec §19.3.2: a visitor-URL run records source, origin, consent_at and screens; a store run has the defaults."""
    import pytest
    from pydantic import ValidationError

    from parity.store.models import Run, RunMode, now

    run = Run(id="r", mode=RunMode.live, flow_id="checkout")
    assert run.source == "flow" and run.origin == "" and run.consent_at is None and run.screens is None
    t = now()
    visitor = Run(id="v", mode=RunMode.live, flow_id="url-1", source="visitor-url", origin="https://a.example", consent_at=t, screens=3)
    again = Run.model_validate_json(visitor.model_dump_json())
    assert again.source == "visitor-url" and again.origin == "https://a.example" and again.consent_at == t and again.screens == 3
    with pytest.raises(ValidationError):
        Run(id="x", mode=RunMode.live, flow_id="f", source="other")
