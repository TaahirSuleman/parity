"""Public-site guard (spec §17): read-only by construction.

Outside our own store the agent may look but never commit: no click on anything named like an
irreversible step, no typing into credential, card or contact fields, no form submission. The
guard decides from the element under the pointer (its accessible role/name and field type) before
the action runs; a refusal ends the walk with ``stopped before irreversible step``. robots.txt is
honoured for the start URL. Bundles are anonymised before they are shared.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from parity.store.models import AxNode

log = logging.getLogger(__name__)
IRREVERSIBLE = re.compile(r"\b(pay|buy|place order|submit|sign ?up|subscribe|confirm|delete|checkout now)\b", re.IGNORECASE)
BLOCKED_FIELDS = {"password", "cc-number", "cc-csc", "cc-exp", "email", "tel", "new-password", "current-password"}
SUBMIT_KEYS = {"enter", "return", "numpadenter", "space", " "}  # Enter submits a form; Space activates a focused control
USER_AGENT = "Parity"
# Bot walls and login walls (spec §17): recognised from the title, the URL and a few well-known markers; never bypassed.
CHALLENGE_TITLES = re.compile(r"just a moment|attention required|access denied|verify you are human|are you a robot|checking your browser|security check|unusual traffic", re.I)
CAPTCHA_MARKERS = (".g-recaptcha", "iframe[src*='recaptcha']", "iframe[src*='hcaptcha']", "[data-sitekey]")
CHALLENGE_MARKERS = ("iframe[src*='challenges.cloudflare.com']", "#challenge-form", "#challenge-running", "#px-captcha", "#sec-cpt-if")
LOGIN_TITLES = re.compile(r"\b(sign in|log ?in|login|signin)\b", re.I)
LOGIN_PATHS = re.compile(r"/(login|signin|sign-in|log-in|account/login|auth)\b", re.I)
CHALLENGE_PROBES = (*CAPTCHA_MARKERS, *CHALLENGE_MARKERS, "input[type=password]")
MASK_RGB = (214, 216, 222)
MASK_MARGIN_PX = 8


@dataclass(frozen=True)
class Allowed:
    allowed: bool = True
    reason: str = ""


@dataclass(frozen=True)
class Blocked:
    reason: str
    allowed: bool = False


Verdict = Allowed | Blocked


def guard_action(action: dict, target: AxNode | None, field_type: str | None, *, submits: bool = False) -> Verdict:
    """One action against the element under it. ``field_type`` is the input's type/autocomplete token; ``submits``
    says the target submits a form (a submit button, or an input inside a form)."""
    kind = str(action.get("type") or "").lower()
    name = (target.name if target else "") or ""
    if kind in ("click", "double_click"):
        if target is not None and target.role == "iframe":
            return Blocked("the click lands inside an embedded frame, whose content is not inspected; not allowed on a public site")
        if submits:
            return Blocked("form submission is not allowed on a public site")
        if IRREVERSIBLE.search(name):
            word = IRREVERSIBLE.search(name).group(1)
            return Blocked(f"'{name}' looks like an irreversible step ({word.lower()}); stopped before it")
        return Allowed()
    if kind == "type":
        if target is not None and target.role == "iframe":
            return Blocked("the focused field is inside an embedded frame, whose content is not inspected; not allowed on a public site")
        blocked = [t for t in (field_type or "").lower().split() if t in BLOCKED_FIELDS]
        if blocked:
            return Blocked(f"typing into a {blocked[0]} field is not allowed on a public site")
        if "\n" in str(action.get("text", "")) or "\r" in str(action.get("text", "")):
            return Blocked("the typed text contains a newline, which submits a form; not allowed on a public site")
        return Allowed()
    if kind == "keypress":
        keys = [str(k).lower() for k in (action.get("keys") or ([action.get("key")] if action.get("key") else []))]
        if any(k in SUBMIT_KEYS for k in keys) and (target is not None or submits):
            return Blocked("Enter or Space on a focused control would submit or activate it; not allowed on a public site")
        return Allowed()
    return Allowed()  # scroll, wait, screenshot


def challenge_reason(title: str, url: str, markers_present: list[str]) -> str | None:
    """'blocked by site: <what>' when the screen is a CAPTCHA, a bot challenge or a login wall, else None. A password field
    alone is not a wall (shops keep one in the header); it is one with a login title or path."""
    present = set(markers_present)
    if present & set(CAPTCHA_MARKERS):
        return "blocked by site: CAPTCHA"
    if present & set(CHALLENGE_MARKERS) or CHALLENGE_TITLES.search(title or ""):
        return "blocked by site: bot challenge"
    if "input[type=password]" in present and (LOGIN_TITLES.search(title or "") or LOGIN_PATHS.search(urlsplit(url).path)):
        return "blocked by site: login"
    return None


def robots_allows(url: str, fetch: Callable[[str], str | None] | None = None) -> bool:
    """robots.txt for the start URL's origin, user-agent Parity. No file, or an unreachable one, allows (and is logged)."""
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        body = (fetch or _fetch)(robots_url)
    except Exception as exc:
        log.warning("robots.txt unreachable at %s: %s; proceeding", robots_url, exc)
        return True
    if not body:
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(body.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def _fetch(url: str) -> str | None:
    import httpx

    r = httpx.get(url, timeout=10, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    return r.text if r.status_code == 200 else None


def anonymise(src: Path, dest: Path, *, letter: str, host: str, names: list[str] | tuple[str, ...] = ()) -> Path:
    """Copy a run bundle as 'Site <letter>': the host, its URLs and the brand ``names`` are replaced everywhere (any case),
    the page title goes, the agent's own screenshots and conversation are not copied, and a step screenshot is kept only
    where a finding was verified, masked to the findings' boxes. The new run id is public-<letter>."""
    src, dest = Path(src), Path(dest)
    new_id = f"public-{letter.lower()}"
    old_id = src.name
    fake_host = f"site-{letter.lower()}.invalid"
    site = f"Site {letter.upper()}"
    if dest.exists():
        shutil.rmtree(dest)
    findings = [json.loads(p.read_text()) for p in sorted((src / "findings").glob("*.json"))] if (src / "findings").exists() else []
    steps_with_findings = {int(f["step_index"]) for f in findings}
    brands = [re.compile(re.escape(n), re.IGNORECASE) for n in names if n]

    def scrub(text: str) -> str:
        text = text.replace(old_id, new_id).replace(host, fake_host)
        text = re.sub(r"<title>[^<]*</title>", f"<title>{site}</title>", text)
        for brand in brands:
            text = brand.sub(site, text)
        return text

    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        parts = rel.parts
        if parts[0] == "agent":
            continue  # the agent's screenshots and transcript show the whole site; the audited steps are the sample
        if len(parts) == 3 and parts[0] == "steps" and parts[2] == "screenshot.png" and int(parts[1]) not in steps_with_findings:
            continue  # no verified finding on this screen: its pixels are not ours to publish
        target = dest / Path(str(rel).replace(old_id, new_id))
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in (".json", ".jsonl", ".html", ".patch", ".txt", ".md"):
            target.write_text(scrub(path.read_text()))
        elif len(parts) == 3 and parts[0] == "steps" and parts[2] == "screenshot.png":
            target.write_bytes(mask_screenshot(path.read_bytes(), _boxes_px(src, int(parts[1]), [f for f in findings if int(f["step_index"]) == int(parts[1])])))
        else:
            target.write_bytes(path.read_bytes())
    run_path = dest / "run.json"
    if run_path.exists():
        run = json.loads(run_path.read_text())
        run["goal"] = f"Site {letter.upper()}: {run.get('goal', '')}".strip()
        run["flow_id"] = "public"  # every public sample shares one flow id; the Eval tab opens them by run id
        run_path.write_text(json.dumps(run, indent=1) + "\n")
    return dest


def _boxes_px(src: Path, step: int, findings: list[dict]) -> list[tuple[int, int, int, int]]:
    """The verified findings' boxes on one step, in pixels (the element's box, else the 0-1000 grid box scaled to the viewport)."""
    viewport = (1280, 720)
    step_json = src / "steps" / str(step) / "step.json"
    if step_json.exists():
        vp = json.loads(step_json.read_text()).get("viewport") or viewport
        viewport = (int(vp[0]), int(vp[1]))
    boxes: list[tuple[int, int, int, int]] = []
    for f in findings:
        px = (f.get("element") or {}).get("box_px")
        if px:
            boxes.append(tuple(int(v) for v in px))
            continue
        b = f.get("bbox")
        if b:
            boxes.append((round(b["x_min"] * viewport[0] / 1000), round(b["y_min"] * viewport[1] / 1000),
                          round(b["x_max"] * viewport[0] / 1000), round(b["y_max"] * viewport[1] / 1000)))
    return boxes


def mask_screenshot(png: bytes, boxes_px: list[tuple[int, int, int, int]], margin: int = MASK_MARGIN_PX) -> bytes:
    """The screenshot with everything outside the given boxes (plus a margin) painted one flat colour: the evidence stays,
    the rest of the third-party page does not travel."""
    from io import BytesIO

    from PIL import Image

    image = Image.open(BytesIO(png)).convert("RGB")
    masked = Image.new("RGB", image.size, MASK_RGB)
    for x0, y0, x1, y1 in boxes_px:
        region = (max(0, x0 - margin), max(0, y0 - margin), min(image.width, x1 + margin), min(image.height, y1 + margin))
        if region[2] > region[0] and region[3] > region[1]:
            masked.paste(image.crop(region), region[:2])
    out = BytesIO()
    masked.save(out, format="PNG", optimize=True)
    return out.getvalue()
