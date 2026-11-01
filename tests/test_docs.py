"""The README is what a judge reads first: its numbers come from the eval's own file and it never claims compliance."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()


def test_readme_eval_numbers_match_latest_json():
    latest = json.loads((ROOT / "eval" / "results" / "latest.json").read_text())
    full = latest["configs"]["full"]["total"]
    recall, precision = f"{round(100 * full['recall'])}%", f"{round(100 * full['precision'])}%"
    assert recall in README and precision in README, (recall, precision)
    assert f"{latest['n_faults']} seeded faults" in README or f"{latest['n_faults']} labels" in README
    assert "latest.md" in README  # the README points at the file it quotes


def test_readme_names_the_demo_path_and_the_limits():
    for phrase in ("Run the audit", "Replay", "make setup", "make demo", "cp .env.example .env", "docs/img/architecture.png", "Limits"):
        assert phrase in README, phrase
    assert "Muse Spark" in README and "Playwright" in README and "axe-core" in README


def test_no_compliance_claims_where_a_judge_reads():
    """'compliance' may appear only as a negation ('not a compliance claim'); the same for 'compliant' and 'WCAG-conformant'."""
    files = [ROOT / "README.md", ROOT / "HACKATHON_SCOPE.md", ROOT / "docs" / "21-submission-text.md", *(p for p in (ROOT / "web" / "src").rglob("*.tsx") if not p.name.endswith(".test.tsx"))]
    offenders = []
    for path in files:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if re.search(r"complian|conformant|certif", line, re.I) and not re.search(r"\b(not|no|never|nothing|neither)\b[^.]{0,60}(complian|conformant|certif)", line, re.I):
                offenders.append(f"{path.relative_to(ROOT)}: {line.strip()[:100]}")
    assert offenders == [], offenders


def test_readme_and_docs_map_links_resolve():
    """The cold review's rule: every file the README (and the docs map) links to exists."""
    missing = []
    for doc in (ROOT / "README.md", ROOT / "docs" / "README.md"):
        text = doc.read_text()
        for target in re.findall(r"\]\(([^)#\s]+)", text) + re.findall(r"`((?:docs|eval|deploy|store|parity|web|fixtures)/[^`\s]+\.[a-z]+)`", text):
            if target.startswith(("http://", "https://")):
                continue
            path = (doc.parent / target) if not target.startswith(("docs/", "eval/", "deploy/", "store/", "parity/", "web/", "fixtures/")) else ROOT / target
            if not path.exists():
                missing.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert missing == [], missing


def test_readme_quotes_every_ablation_and_describes_gating_as_the_code_does():
    latest = json.loads((ROOT / "eval" / "results" / "latest.json").read_text())
    for key in ("screenshot_only", "tree_only", "no_grounding"):
        assert f"{round(100 * latest['configs'][key]['total']['recall'])}%" in README, key
    assert "a screen must be audited before the walk moves on" not in README  # only finish is gated; code audits the last screen itself
    assert "`finish` is refused" in README


import pytest


def test_readme_has_the_hosted_url():
    assert "run.app" in README and "added after the first deploy" not in README
