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

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from parity import __version__
from parity.api.events import EventBus
from parity.api.routes import router
from parity.config import Settings, load_settings
from parity.meta.client import MetaClient, TraceRouter
from parity.pipeline import browser
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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st = app.state
        await st.index.init()
        recovered = await st.index.recover_interrupted(st.bundle)
        indexed = await st.index.rebuild(st.bundle)
        st.replay_for_flow, st.replay_ids = await discover_replays(st.replay_bundle)
        log.info("boot: %d runs indexed, %d recovered, replays %s, storage %s", indexed, len(recovered), st.replay_ids, "gcs" if settings.gcs_bucket else "local")
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
    st.last_live_run = None  # the newest Live run id, for the finishing-run grace in POST /runs
    st.self_base_url = f"http://127.0.0.1:{settings.port}"
    st.replay_for_flow = {}
    st.replay_ids = []

    @app.middleware("http")
    async def cache_policy(request, call_next):
        # The SPA's assets carry a content hash and may be cached for a year; index.html must be revalidated every time, or a
        # browser that cached it before a redeploy asks for an asset that no longer exists and shows a blank page.
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif not path.startswith(("/api/", "/store/")) and response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.include_router(router)
    app.mount("/store", StaticFiles(directory=STORE_DIR, html=True), name="store")
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="spa")
    return app
