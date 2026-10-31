"""Record the committed Replay bundle: one real Live run through the API against the served store.

Starts the app in-process with the real Meta client (cached responses are reused, so a re-run
is free), runs the checkout flow, waits for it to finish and copies the bundle into
fixtures/replay/runs/<name>/ under that stable id. Run: .venv/bin/python scripts/record_replay.py [--name hero-checkout]
"""

import argparse
import asyncio
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from parity.app import create_app  # noqa: E402
from parity.config import load_settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="hero-checkout")
    ap.add_argument("--flow", default="checkout")
    args = ap.parse_args()
    base = load_settings()
    if not base.has_key:
        print("MODEL_API_KEY missing (expected in .env)")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="parity-record-"))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    settings = load_settings(env={
        "MODEL_API_KEY": base.model_api_key, "PARITY_DATA_DIR": str(tmp / "data"), "PARITY_INDEX_PATH": str(tmp / "index.db"),
        # a fresh cache: the committed bundle must show real latency and cost, not cache hits
        "PARITY_CACHE_DIR": str(tmp / "cache"), "PARITY_REPLAY_DIR": str(tmp / "replay"), "PORT": str(port), "PARITY_DEFAULT_MODE": "live",
    })
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    try:
        started = httpx.post(f"{url}/api/runs", json={"flow_id": args.flow, "mode": "live"}, timeout=30)
        started.raise_for_status()
        run_id = started.json()["run_id"]
        print(f"live run {run_id} started; streaming events…")
        with httpx.stream("GET", f"{url}/api/runs/{run_id}/events", timeout=600) as stream:
            for line in stream.iter_lines():
                if line.startswith("event:"):
                    kind = line[6:].strip()
                    if kind not in ("model.call",):
                        print("  ", kind)
        detail = httpx.get(f"{url}/api/runs/{run_id}", timeout=30).json()
        run = detail["run"]
        print(f"status={run['status']} verified={run['findings_verified']} rejected={run['findings_rejected']} axe={run['axe_violations']} tokens={run['tokens']} cost=${run['cost_usd']:.4f} {run['duration_ms']} ms")
        if run["status"] not in ("done", "awaiting_review"):
            print("run did not finish cleanly:", run.get("error"))
            return 1
        hero = [f for f in detail["findings"] if f["element"].get("dom_id") == "f5"]
        if not hero:
            print("no hero finding (#f5) in this run; not recording")
            return 1
    finally:
        server.should_exit = True
        time.sleep(0.5)
    # The committed bundle lives at fixtures/replay/runs/<name>/ under a stable id: every id inside the
    # bundle embeds the run id, so a textual rewrite run_id -> name keeps all cross-references consistent.
    src = tmp / "data" / "runs" / run_id
    dest = ROOT / "fixtures" / "replay" / "runs" / args.name
    if dest.exists():
        shutil.rmtree(dest)
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        target = dest / Path(str(path.relative_to(src)).replace(run_id, args.name))
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in (".json", ".jsonl", ".patch"):
            target.write_text(path.read_text().replace(run_id, args.name))
        else:
            target.write_bytes(path.read_bytes())
    size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    print(f"recorded -> {dest.relative_to(ROOT)} ({size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
