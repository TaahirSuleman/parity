import socket
import threading
import time

import pytest
import pytest_asyncio
import uvicorn
from playwright.async_api import async_playwright


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
