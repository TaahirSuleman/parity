"""FastAPI application factory: /api, /store (demo store) and / (the workbench SPA)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from parity.config import Settings, load_settings

ROOT = Path(__file__).resolve().parent.parent
STORE_DIR = ROOT / "store"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Parity", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.settings = settings

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "ok": True,
            "mode_default": settings.default_mode,
            "live_enabled": settings.live_enabled,
            "storage": "gcs" if settings.gcs_bucket else "local",
        }

    app.mount("/store", StaticFiles(directory=STORE_DIR, html=True), name="store")
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="spa")
    return app
