"""Run a flow live N times with a fresh cache each time and measure run-to-run stability.

Each run costs real money (the cache is fresh on purpose), so the default is the purchase
flow three times (~$0.45). Findings are keyed by (page, sighted_text, sr_name); the report
says which barriers every run found, which were flaky, and the spread of cost and time.
Run: .venv/bin/python scripts/variance_runs.py [--flow purchase] [--runs 3] [--out variance.json]
"""

import argparse
import json
import socket
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from parity.app import create_app  # noqa: E402
from parity.config import load_settings  # noqa: E402


def one_run(flow: str, key: str) -> dict:
    """One live run on a fresh app with a fresh cache; returns the summary and finding keys."""
    tmp = Path(tempfile.mkdtemp(prefix="parity-variance-"))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    settings = load_settings(env={
        "MODEL_API_KEY": key, "PARITY_DATA_DIR": str(tmp / "data"), "PARITY_INDEX_PATH": str(tmp / "index.db"),
        "PARITY_CACHE_DIR": str(tmp / "cache"), "PARITY_REPLAY_DIR": str(tmp / "replay"), "PORT": str(port), "PARITY_DEFAULT_MODE": "live",
    })
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    try:
        run_id = httpx.post(f"{url}/api/runs", json={"flow_id": flow, "mode": "live"}, timeout=30).json()["run_id"]
        with httpx.stream("GET", f"{url}/api/runs/{run_id}/events", timeout=900) as stream:
            for line in stream.iter_lines():
                if line.startswith("event:") and line[6:].strip() in ("run.finished", "run.failed", "step.captured"):
                    print("  ", line[6:].strip(), flush=True)
        detail = httpx.get(f"{url}/api/runs/{run_id}", timeout=30).json()
    finally:
        server.should_exit = True
        time.sleep(0.5)
    run = detail["run"]
    page_of = {s["index"]: s["url"].rsplit("/", 1)[-1] for s in detail["steps"]}
    findings = sorted(
        # keyed on the verifier-grounded element, not the model's wording of sighted_text,
        # so a paraphrase ("crossed-out price" vs "crossed-out original price") is not "flaky"
        f"{page_of.get(f['step_index'], f['step_index'])} #{f['element'].get('dom_id') or f['element'].get('selector') or '?'}"
        f" | {f['sr_role']}, \"{f['sr_name']}\""
        for f in detail["findings"]
    )
    return {
        "run_id": run_id, "status": run["status"], "error": run.get("error"),
        "verified": run["findings_verified"], "rejected": run["findings_rejected"], "axe": run["axe_violations"],
        "tokens": run["tokens"], "cost_usd": run["cost_usd"], "duration_s": round(run["duration_ms"] / 1000, 1),
        "findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", default="purchase")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "docs" / "variance.json"))
    args = ap.parse_args()
    base = load_settings()
    if not base.has_key:
        print("MODEL_API_KEY missing (expected in .env)")
        return 1

    results = []
    for i in range(args.runs):
        print(f"run {i + 1}/{args.runs} ({args.flow}, fresh cache)…", flush=True)
        r = one_run(args.flow, base.model_api_key)
        print(f"   status={r['status']} verified={r['verified']} rejected={r['rejected']} "
              f"cost=${r['cost_usd']:.4f} {r['duration_s']}s", flush=True)
        results.append(r)

    seen = Counter(k for r in results for k in set(r["findings"]))
    every_run = sorted(k for k, n in seen.items() if n == len(results))
    flaky = sorted(k for k, n in seen.items() if 0 < n < len(results))
    report = {
        "flow": args.flow, "runs": len(results), "recorded_at": time.strftime("%Y-%m-%d %H:%M"),
        "verified_counts": [r["verified"] for r in results],
        "cost_usd": [round(r["cost_usd"], 4) for r in results],
        "duration_s": [r["duration_s"] for r in results],
        "stable_findings": every_run, "flaky_findings": flaky,
        "stability": round(len(every_run) / max(1, len(seen)), 3),
        "results": results,
    }
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"\nstable in all {len(results)} runs: {len(every_run)}  flaky: {len(flaky)}  "
          f"stability={report['stability']:.0%}  -> {args.out}")
    for k in flaky:
        print("  flaky:", k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
