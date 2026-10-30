"""Data model (spec docs/19 §5). One JSON file per object in the run bundle."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> datetime:
    return datetime.now(UTC)


class RunMode(StrEnum):
    live = "live"
    replay = "replay"


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    awaiting_review = "awaiting_review"
    done = "done"
    failed = "failed"


class FindingStatus(StrEnum):
    verified = "verified"
    judged = "judged"
    fix_proposed = "fix_proposed"
    reaudited = "reaudited"
    approved = "approved"
    rejected = "rejected"


class Severity(StrEnum):
    critical = "critical"
    serious = "serious"
    moderate = "moderate"
    minor = "minor"
    needs_review = "needs_review"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BBox(Strict):
    """Box on the 0–1000 grid used by Spark grounding."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @model_validator(mode="after")
    def _clamp(self) -> BBox:
        for name in ("x_min", "y_min", "x_max", "y_max"):
            object.__setattr__(self, name, min(1000, max(0, getattr(self, name))))
        return self

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)

    @property
    def area(self) -> int:
        return max(0, self.x_max - self.x_min) * max(0, self.y_max - self.y_min)


class Element(Strict):
    backend_id: int
    css_path: str
    box_px: tuple[int, int, int, int] | None = None
    outer_html: str | None = None
    dom_id: str | None = None


class AxNode(Strict):
    backend_id: int
    role: str
    name: str
    css_path: str = ""
    box_px: tuple[int, int, int, int] | None = None
    bbox: BBox | None = None
    outer_html: str | None = None
    dom_id: str | None = None

    def to_element(self) -> Element:
        return Element(
            backend_id=self.backend_id,
            css_path=self.css_path,
            box_px=self.box_px,
            outer_html=self.outer_html,
            dom_id=self.dom_id,
        )


class AxeViolation(Strict):
    id: str
    impact: str | None = None
    targets: list[str] = Field(default_factory=list)
    backend_ids: list[int] = Field(default_factory=list)


class Capture(Strict):
    """Everything deterministic we know about one screen."""

    step_index: int
    url: str
    viewport: tuple[int, int] = (1280, 720)
    screenshot_png: bytes = Field(default=b"", exclude=True, repr=False)
    ax_nodes: list[AxNode] = Field(default_factory=list)
    # Visible DOM elements with no accessibility node (canvas, alt="" images, aria-hidden): what pixels show and screen readers never get.
    silent_nodes: list[AxNode] = Field(default_factory=list)
    axe_violations: list[AxeViolation] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=now)


class Percept(Strict):
    step_index: int
    visible_text: str
    kind: str = "other"
    bbox: BBox


class Candidate(Strict):
    step_index: int
    sighted_text: str
    sr_quote: str
    why_it_matters: str = ""
    bbox: BBox | None = None
    attempt: int = 1


class Check(Strict):
    passed: bool
    detail: str = ""


class VerifierResult(Strict):
    passed: bool
    checks: dict[str, Check] = Field(default_factory=dict)
    element: Element | None = None
    feedback: str | None = None


class WcagRef(Strict):
    sc: str
    name: str = ""


class Judgement(Strict):
    is_barrier: bool | None
    severity: Severity
    wcag: list[WcagRef] = Field(default_factory=list)
    impact: str = ""
    model_meta: dict[str, Any] = Field(default_factory=dict)


class Fix(Strict):
    before_html: str
    after_html: str
    diff: str
    explanation: str = ""
    model_meta: dict[str, Any] = Field(default_factory=dict)


class Reaudit(Strict):
    gap_closed: bool
    sr_name_before: str
    sr_name_after: str
    comparator_still_flags: bool | None = None


class Decision(Strict):
    decision: Literal["approve", "reject"]
    reason: str
    decided_at: datetime = Field(default_factory=now)


class VoiceEvidence(Strict):
    clip_key: str
    start_ms: int
    end_ms: int
    transcript: str
    agrees: bool


class Finding(Strict):
    id: str
    run_id: str
    step_index: int
    status: FindingStatus = FindingStatus.verified
    sighted_text: str
    sr_role: str
    sr_name: str
    why_it_matters: str = ""
    voice: VoiceEvidence | None = None
    bbox: BBox
    element: Element
    verifier: VerifierResult
    judgement: Judgement | None = None
    fix: Fix | None = None
    reaudit: Reaudit | None = None
    decision: Decision | None = None


class Rejected(Strict):
    id: str
    run_id: str
    step_index: int
    candidate: Candidate
    verifier: VerifierResult


class ModelCall(Strict):
    id: str
    run_id: str
    step_index: int | None = None
    stage: str
    model: str
    request_id: str = ""
    response_id: str = ""
    prompt_sha256: str = ""
    cache_hit: bool = False
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    http_status: int | None = None
    error: str | None = None
    attempt: int = 1
    at: datetime = Field(default_factory=now)


class Step(Strict):
    run_id: str
    index: int
    url: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    screenshot: str = ""
    ax_tree: str = ""
    axe: str = ""
    viewport: tuple[int, int] = (1280, 720)
    axe_violations: int = 0
    ax_nodes: int = 0
    captured_at: datetime = Field(default_factory=now)


class Run(Strict):
    id: str
    mode: RunMode
    flow_id: str
    goal: str = ""
    target_url: str = ""
    status: RunStatus = RunStatus.queued
    started_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    axe_violations: int = 0
    findings_verified: int = 0
    findings_rejected: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    client_ip_hash: str = ""
    error: str | None = None
    replay_of: str | None = None  # source run id when mode == replay


class Event(Strict):
    type: str
    run_id: str
    at: datetime = Field(default_factory=now)
    data: dict[str, Any] = Field(default_factory=dict)
