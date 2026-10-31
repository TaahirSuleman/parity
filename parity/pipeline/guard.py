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
SUBMIT_KEYS = {"enter", "return", "numpadenter"}
USER_AGENT = "Parity"


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
        if submits:
            return Blocked("form submission is not allowed on a public site")
        if IRREVERSIBLE.search(name):
            word = IRREVERSIBLE.search(name).group(1)
            return Blocked(f"'{name}' looks like an irreversible step ({word.lower()}); stopped before it")
        return Allowed()
    if kind == "type":
        if field_type and field_type.lower() in BLOCKED_FIELDS:
            return Blocked(f"typing into a {field_type.lower()} field is not allowed on a public site")
        return Allowed()
    if kind == "keypress":
        keys = [str(k).lower() for k in (action.get("keys") or ([action.get("key")] if action.get("key") else []))]
        if any(k in SUBMIT_KEYS for k in keys) and (target is not None or submits):
            return Blocked("Enter would submit the form; not allowed on a public site")
        return Allowed()
    return Allowed()  # scroll, wait, screenshot


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


def anonymise(src: Path, dest: Path, *, letter: str, host: str) -> Path:
    """Copy a run bundle as 'Site <letter>': the host and its URLs are replaced everywhere, the page title goes,
    and screenshots are kept only for steps that produced a verified finding. The new run id is public-<letter>."""
    src, dest = Path(src), Path(dest)
    new_id = f"public-{letter.lower()}"
    old_id = src.name
    fake_host = f"site-{letter.lower()}.invalid"
    if dest.exists():
        shutil.rmtree(dest)
    findings = [json.loads(p.read_text()) for p in sorted((src / "findings").glob("*.json"))] if (src / "findings").exists() else []
    steps_with_findings = {int(f["step_index"]) for f in findings}

    def scrub(text: str) -> str:
        text = text.replace(old_id, new_id).replace(host, fake_host)
        text = re.sub(r"<title>[^<]*</title>", f"<title>Site {letter.upper()}</title>", text)
        return text

    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        parts = rel.parts
        if len(parts) == 3 and parts[0] == "steps" and parts[2] == "screenshot.png" and int(parts[1]) not in steps_with_findings:
            continue  # no verified finding on this screen: its pixels are not ours to publish
        target = dest / Path(str(rel).replace(old_id, new_id))
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in (".json", ".jsonl", ".html", ".patch", ".txt", ".md"):
            target.write_text(scrub(path.read_text()))
        else:
            target.write_bytes(path.read_bytes())
    run_path = dest / "run.json"
    if run_path.exists():
        run = json.loads(run_path.read_text())
        run["goal"] = f"Site {letter.upper()}: {run.get('goal', '')}".strip()
        run["flow_id"] = "public"  # every public sample shares one flow id; the Eval tab opens them by run id
        run_path.write_text(json.dumps(run, indent=1) + "\n")
    return dest
