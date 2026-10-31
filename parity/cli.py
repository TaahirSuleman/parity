"""Command line: `parity verify RUN --off`, `parity index rebuild`."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from parity.config import load_settings
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.verifier_off import verifier_off


def _bundle(data_dir: str | None) -> RunBundle:
    settings = load_settings()
    return RunBundle(LocalBlobStore(Path(data_dir) if data_dir else settings.data_dir))


async def _verify(args) -> int:
    bundle = _bundle(args.data_dir)
    try:
        report = await verifier_off(bundle, args.run_id)
    except KeyError:
        print(f"unknown run {args.run_id}")
        return 1
    print(f"run {report.run_id}: without the Verifier it would have reported {report.reported} findings; "
          f"{report.rejected_by_verifier} would be false (verifier on: {report.verified} verified)")
    for c in report.candidates:
        mark = "ok  " if c.verifier_passed else "FALSE"
        print(f"  [{mark}] step {c.step_index} {c.sighted_text[:40]!r} -> {c.sr_quote[:30]!r}" + (f"  failed: {', '.join(c.checks_failed)}" if c.checks_failed else ""))
    return 0


async def _index_rebuild(args) -> int:
    settings = load_settings()
    bundle = _bundle(args.data_dir)
    index = RunIndex(Path(args.index_path) if args.index_path else settings.index_path)
    try:
        await index.init()
        count = await index.rebuild(bundle)
    finally:
        await index.close()
    print(f"index rebuilt: {count} run{'s' if count != 1 else ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parity")
    sub = parser.add_subparsers(dest="cmd", required=True)
    verify = sub.add_parser("verify", help="re-score a stored run")
    verify.add_argument("run_id")
    verify.add_argument("--off", action="store_true", help="report what the run would contain with the Verifier bypassed")
    verify.add_argument("--data-dir")
    verify.set_defaults(fn=_verify)
    index = sub.add_parser("index", help="SQLite index maintenance")
    index_sub = index.add_subparsers(dest="index_cmd", required=True)
    rebuild = index_sub.add_parser("rebuild", help="rebuild the index from the run bundles")
    rebuild.add_argument("--data-dir")
    rebuild.add_argument("--index-path")
    rebuild.set_defaults(fn=_index_rebuild)
    args = parser.parse_args(argv)
    if args.cmd == "verify" and not args.off:
        print("only --off is implemented in this phase")
        return 2
    return asyncio.run(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
