import asyncio
import socket
import threading
import time

import pytest
import pytest_asyncio
import uvicorn
from playwright.async_api import async_playwright

from tests.helpers import make_replay_bundle


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server_url(tmp_path_factory):
    """The real app served by uvicorn in a thread, on a free port, with a temp data dir."""
    from parity.app import create_app
    from parity.config import load_settings

    root = tmp_path_factory.mktemp("parity-data")
    asyncio.run(make_replay_bundle(root / "replay"))  # a recorded run, so Replay works in tests
    settings = load_settings(
        env={
            "PARITY_DATA_DIR": str(root / "data"),
            "PARITY_CACHE_DIR": str(root / "cache"),
            "PARITY_INDEX_PATH": str(root / "index.db"),
            "PARITY_REPLAY_DIR": str(root / "replay"),
        }
    )
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn did not start"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def store_url(server_url):
    return server_url + "/store/"


@pytest_asyncio.fixture
async def page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        yield page
        await browser.close()


@pytest_asyncio.fixture
async def api(tmp_path):
    """The app over ASGI with a seeded replay bundle: the shared REST/SSE integration fixture."""
    import httpx

    from parity.app import create_app
    from parity.config import load_settings

    await make_replay_bundle(tmp_path / "replay")
    settings = load_settings(env={
        "PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
        "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay"),
    })
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, app
