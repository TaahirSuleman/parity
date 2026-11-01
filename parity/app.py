"""FastAPI application factory: /api, /store (demo store) and / (the workbench SPA).

Boot order (spec docs/19 §5.1): open the index, fail runs interrupted by a restart, rebuild the
index from the bundles, discover replay bundles, then serve.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from parity import __version__
from parity.api.events import EventBus
from parity.api.routes import router
from parity.config import Settings, load_settings
from parity.meta.client import MetaClient, TraceRouter
from parity.pipeline import browser
from parity.ratelimit import RateLimiter
from parity.store.blob import LocalBlobStore, make_blob_store
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
STORE_DIR = ROOT / "store"
STATIC_DIR = Path(__file__).resolve().parent / "static"


async def discover_replays(replay_bundle: RunBundle) -> tuple[dict[str, str], list[str]]:
    """(flow_id -> the newest recorded run for that flow, every readable run id). Public samples share the flow
    "public", so the Eval tab opens them by run id."""
    by_flow: dict[str, str] = {}
    all_ids: list[str] = []
    for run_id in await replay_bundle.list_run_ids():
        try:
            run = (await replay_bundle.load(run_id)).run
        except Exception as exc:
            log.warning("replay bundle %s unreadable: %s", run_id, exc)
            continue
        by_flow[run.flow_id] = run_id  # list_run_ids is sorted; later ids win
        all_ids.append(run_id)
    return by_flow, sorted(all_ids)


async def probe_models(client: MetaClient | None) -> bool:
    """Once at boot: can the model API be reached with this key? Surfaced by /api/health as models_ok; never fatal."""
    if client is None:
        return False
    try:
        return bool(await asyncio.wait_for(client.models(), timeout=15))
    except Exception as exc:
        log.warning("model API probe failed: %s", exc)
        return False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st = app.state
        await st.index.init()
        booted = await st.index.boot(st.bundle, replay_keep=settings.replay_keep)
        st.replay_for_flow, st.replay_ids = await discover_replays(st.replay_bundle)
        st.models_ok = await probe_models(st.client)
        log.info("boot: %d runs indexed, %d recovered, %d replay copies evicted, replays %s, storage %s, models_ok %s", booted["indexed"], len(booted["recovered"]),
                 len(booted["evicted"]), st.replay_ids, "gcs" if settings.gcs_bucket else "local", st.models_ok)
        try:
            yield
        finally:
            await st.index.close()
            if st.client is not None:
                await st.client.aclose()
            await browser.shutdown()

    app = FastAPI(title="Parity", version=__version__, docs_url=None, redoc_url=None, lifespan=lifespan)
    st = app.state
    st.settings = settings
    st.bundle = RunBundle(make_blob_store(settings))
    st.replay_bundle = RunBundle(LocalBlobStore(settings.replay_dir))
    st.index = RunIndex(settings.index_path)
    st.bus = EventBus(st.bundle)
    st.trace = TraceRouter()
    st.client = MetaClient(settings, cache_dir=settings.cache_dir, trace=st.trace) if settings.has_key else None
    st.live_lock = asyncio.Lock()
    st.limiter = RateLimiter(settings.live_per_ip_per_hour, settings.live_global_per_day)
    st.last_live_run = None  # the newest Live run id, for the finishing-run grace in POST /runs
    st.self_base_url = f"http://127.0.0.1:{settings.port}"
    st.replay_for_flow = {}
    st.replay_ids = []
    st.models_ok = False

    @app.middleware("http")
    async def cache_policy(request, call_next):
        # The SPA's assets carry a content hash and may be cached for a year; index.html must be revalidated every time, or a
        # browser that cached it before a redeploy asks for an asset that no longer exists and shows a blank page.
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/assets/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif not path.startswith(("/api/", "/store/")) and response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.include_router(router)
    app.mount("/store", StaticFiles(directory=STORE_DIR, html=True), name="store")
    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        async def spa(path: str) -> FileResponse:
            # A shared run link (/runs/<id>, or ?run= on any path) opens the workbench: any path that is not an API route, a
            # store page or a real file under static/ serves index.html. A missing file (favicon.ico) stays a 404.
            if path.startswith(("api/", "store/")) or path in ("api", "store"):
                raise HTTPException(404)
            candidate = (STATIC_DIR / path).resolve() if path else STATIC_DIR / "index.html"
            if path and STATIC_DIR.resolve() in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            if "." in path.rsplit("/", 1)[-1]:
                raise HTTPException(404)
            return FileResponse(STATIC_DIR / "index.html")
    return app
