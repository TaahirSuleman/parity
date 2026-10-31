"""Anonymise a public-site run bundle as "Site <letter>" before it is committed (spec §17).

Run: .venv/bin/python scripts/anonymise_bundle.py --data-dir data --run-id <id> --host shop.example --letter A
Writes fixtures/replay/runs/public-<letter>/ (host and URLs replaced, title dropped, screenshots kept only for steps with a
verified finding). Raw bundles stay out of git.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parity.pipeline.guard import anonymise  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--host", required=True, help="the site's host name, replaced everywhere")
    ap.add_argument("--letter", required=True, help="A, B, C ...")
    ap.add_argument("--dest", default=None, help="default fixtures/replay/runs/public-<letter>")
    args = ap.parse_args()
    src = Path(args.data_dir) / "runs" / args.run_id
    if not src.exists():
        print(f"no bundle at {src}")
        return 1
    dest = Path(args.dest) if args.dest else ROOT / "fixtures" / "replay" / "runs" / f"public-{args.letter.lower()}"
    out = anonymise(src, dest, letter=args.letter, host=args.host)
    leaked = [p for p in out.rglob("*") if p.is_file() and args.host.encode() in p.read_bytes()]
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}; host leaks: {len(leaked)}")
    return 0 if not leaked else 1


if __name__ == "__main__":
    sys.exit(main())
