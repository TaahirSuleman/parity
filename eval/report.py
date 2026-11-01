"""Render eval/results/latest.json as the Markdown tables the README quotes (one number set, recipe rule L9)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "eval" / "results" / "latest.json"
CONFIG_LABELS = {"full": "Parity (full)", "screenshot_only": "screenshot only", "tree_only": "tree only", "no_grounding": "no grounding"}


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.0f}%"


def render(r: dict) -> str:
    lines = [f"# Eval results — {r.get('updated_at', r.get('generated_at', ''))}", "",
             f"Model `{r.get('model', '?')}`, judge `{r.get('judge_model', '?')}`, effort `{r.get('effort', '?')}`, {r.get('runs', '?')} run(s) per page, "
             f"pages {', '.join(r.get('pages', []))}. Labels: {r.get('n_faults', '?')} seeded faults, {r.get('n_clean', '?')} clean controls "
             f"(`{r.get('labels', 'eval/labels.json')}`). Recall and precision are means over runs; n is verified findings.", "",
             f"Measured at commit `{str(r.get('git_sha', 'unknown'))[:12]}`{' (uncommitted changes present)' if r.get('git_dirty') else ''}, "
             f"labels sha256 `{str(r.get('labels_sha256', '?'))[:12]}`. A finding is scored under its element's id or the nearest id above it.", ""]
    cfgs = r.get("configs", {})
    axe = r.get("axe", {})
    lines += ["## Parity vs axe-core (same labels)", "", "| System | Recall | Precision | Verified findings | FP on clean | Cost | Time |", "|---|---|---|---|---|---|---|"]
    for key in ("full", "screenshot_only", "tree_only", "no_grounding"):
        if key in cfgs:
            t = cfgs[key]["total"]
            lines.append(f"| {CONFIG_LABELS[key]} | {pct(t['recall'])} | {pct(t['precision'])} | {t['n']:.0f} per run · {t['n_labels']} labels | {t['fp_on_clean']:.1f} | ${t['cost_usd']:.3f} | {t['seconds']:.0f} s |")
    if axe:
        lines.append(f"| axe-core 4.14 | {pct(axe.get('recall'))} | — | {axe.get('violations', 0)} violations | — | $0 | — |")
    if "full" in cfgs:
        lines += ["", "## Per page (full configuration)", "", "| Page | Recall | Precision | Found / labels | Found in every run | Cost | Time |", "|---|---|---|---|---|---|---|"]
        for page, v in cfgs["full"]["per_page"].items():
            lines.append(f"| {page} | {pct(v['recall'])} | {pct(v['precision'])} | {len(v['hits'])} / {v['n_labels']} | {len(v.get('hits_every_run', []))} | ${v['cost_usd']:.3f} | {v['seconds']:.0f} s |")
    if r.get("effort_sweep"):
        lines += ["", "## Effort sweep (full configuration, one run)", "", "| Effort | Recall | Precision | Cost | Time |", "|---|---|---|---|---|"]
        for eff, t in r["effort_sweep"].items():
            lines.append(f"| {eff} | {pct(t['recall'])} | {pct(t['precision'])} | ${t['cost_usd']:.3f} | {t['seconds']:.0f} s |")
    if r.get("judge"):
        lines += ["", "## Judge comparison (same verified findings)", "", "| Judge | Agreement with labels | Needs review | Cost per finding | n |", "|---|---|---|---|---|"]
        for jm, v in r["judge"].items():
            lines.append(f"| {jm} | {pct(v['agreement'])} | {pct(v['needs_review_rate'])} | ${v['cost_per_finding']:.4f} | {v['n']} |")
    if r.get("standard_tier_check"):
        t = r["standard_tier_check"]
        lines += ["", f"Standard-tier check (`{t['model']}`, one run): recall {pct(t['recall'])}, precision {pct(t['precision'])}, ${t['cost_usd']:.3f}."]
    if r.get("public"):
        lines += ["", "## Real-world sample (anonymised, read-only)", "", "| Site | Pages | Verified | Rejected |", "|---|---|---|---|"]
        for site in r["public"]:
            lines.append(f"| {site['name']} | {site['pages']} | {site['verified']} | {site['rejected']} |")
    lines += ["", "Findings are evidence, not a conformance claim; a human approves every fix."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else LATEST
    print(render(json.loads(path.read_text())))
