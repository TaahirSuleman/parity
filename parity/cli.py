"""Command line: `parity verify RUN --off`, `parity index rebuild`."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlsplit

from parity.config import load_settings
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.verifier_off import verifier_off


def _bundle(data_dir: str | None) -> RunBundle:
    settings = load_settings()
    return RunBundle(LocalBlobStore(Path(data_dir) if data_dir else settings.data_dir))


def public_target(url: str) -> tuple[str, str, str] | None:
    """(origin, start path, host) for a public audit URL, or None when it is not http(s). Credentials in the URL are dropped:
    they would otherwise be stored in run.json and printed in the hint."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    netloc = parts.hostname + (f":{parts.port}" if parts.port else "")
    return f"{parts.scheme}://{netloc}", (parts.path or "/") + (f"?{parts.query}" if parts.query else ""), netloc


async def _verify(args) -> int:
    bundle = _bundle(args.data_dir)
    try:
        report = await verifier_off(bundle, args.run_id)
    except KeyError:
        print(f"unknown run {args.run_id}")
        return 1
    print(f"run {report.run_id}: without the Verifier it would have reported {report.reported} findings; "
          f"{report.false_reports} would be false, {report.duplicates} duplicate, {report.already_in_axe} already in axe "
          f"(verifier on: {report.verified} verified)")
    for c in report.candidates:
        mark = "ok  " if c.verifier_passed else c.kind.upper()[:5]
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


async def _audit(args) -> int:
    """One public-site walk from the command line. Never from the hosted UI."""

    from parity.api.events import EventBus
    from parity.flows import Flow
    from parity.meta.client import MetaClient, TraceRouter
    from parity.pipeline.runner import run_flow
    from parity.store.blob import LocalBlobStore
    from parity.store.bundle import RunBundle
    from parity.store.index import RunIndex

    settings = audit_settings(args.data_dir)
    if not settings.has_key:
        print("MODEL_API_KEY missing (expected in .env); a public audit calls the model and needs it")
        return 1
    target = public_target(args.url)
    if target is None:
        print(f"not an http(s) URL: {args.url}")
        return 2
    origin, start, netloc = target
    flow = Flow(id=f"public-{netloc}", name=f"Public: {netloc}", start_url=start, goal=args.goal, pages=(start,), single_page=False)
    bundle = RunBundle(LocalBlobStore(settings.data_dir))
    index = RunIndex(settings.index_path)
    await index.init()
    client = MetaClient(settings, cache_dir=settings.cache_dir, trace=TraceRouter())
    try:
        run = await run_flow(settings, client, EventBus(bundle), bundle, index, flow, base_url=origin, max_turns=args.max_turns, public=True)
    finally:
        await client.aclose()
        await index.close()
    loaded = await bundle.load(run.id)
    agent = next((e.data.get("agent") for e in loaded.events if e.type == "run.finished"), None) or {}
    blocked = [e.data.get("reason") for e in loaded.events if e.type == "nav.blocked"]
    print(f"run {run.id}: status={run.status} screens={len(loaded.steps)} verified={run.findings_verified} rejected={run.findings_rejected} "
          f"tokens={run.tokens} cost=${run.cost_usd:.4f} {run.duration_ms} ms")
    print(f"agent: {agent.get('summary', run.error or '')}")
    for b in blocked:
        print(f"blocked: {b}")
    if run.status != "failed":
        print(f"anonymise before sharing: scripts/anonymise_bundle.py --data-dir {settings.data_dir} --run-id {run.id} --host {netloc} --name '<brand name>' --letter <A|B|C>")
    return 0 if run.status != "failed" else 1


def audit_settings(data_dir: str | None):
    """Settings from .env / the environment as usual; --data-dir only moves the bundle and its index."""
    import dataclasses
    from pathlib import Path

    from parity.config import load_settings

    settings = load_settings()
    if data_dir:
        root = Path(data_dir)
        settings = dataclasses.replace(settings, data_dir=root, index_path=root / "index.db")
    return settings


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
    audit = sub.add_parser("audit", help="audit a flow on a site you do not own: read-only, robots.txt honoured, local only (spec §17)")
    audit.add_argument("--url", required=True, help="the start URL")
    audit.add_argument("--goal", required=True, help="what a shopper would try to do, e.g. 'add the first product to the cart'")
    audit.add_argument("--public", action="store_true", required=True, help="required: the read-only guard is always on for sites we do not own")
    audit.add_argument("--data-dir", help="where the run bundle is written (default: settings)")
    audit.add_argument("--max-turns", type=int, default=12)
    audit.set_defaults(fn=_audit)
    args = parser.parse_args(argv)
    if args.cmd == "verify" and not args.off:
        print("only --off is implemented in this phase")
        return 2
    return asyncio.run(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
