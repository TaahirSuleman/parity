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


@pytest.fixture(scope="session")
def fixture_url():
    """Local pages for the guard tests (tests/fixtures/pages), served by a throwaway server on localhost with two special
    answers: /private.png (a loopback subresource) and /bounce.png (a redirect to the cloud metadata address). Each request's
    User-Agent is recorded on the server (``fixture_url.agents``)."""
    import http.server
    from functools import partial
    from pathlib import Path

    root = Path(__file__).parent / "fixtures" / "pages"
    agents: list[str] = []
    requests: list[str] = []  # every path asked for, query stripped
    flips = {"n": 0}  # /flip answers 200 once, then redirects to a loopback address: a server that varies its answer (review C1)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:  # keep pytest's output clean
            pass

        def do_GET(self) -> None:
            agents.append(self.headers.get("User-Agent", ""))
            requests.append(self.path.split("?", 1)[0])
            port = self.server.server_address[1]
            if self.path == "/flip-reset":
                flips["n"] = 0
                self.send_response(204)
                self.end_headers()
                return
            if self.path == "/start-flip":
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{port}/flip")
                self.end_headers()
                return
            if self.path == "/flip":
                flips["n"] += 1
                if flips["n"] == 1:
                    body = b"<!doctype html><html><body><h1>flip first answer</h1></body></html>"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{port}/secret")
                self.end_headers()
                return
            if self.path == "/secret":
                body = b"<!doctype html><html><body><h1>SECRET internal page reached</h1></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/flip-img":  # a subresource that redirects on the same host
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{port}/img-final")
                self.end_headers()
                return
            if self.path == "/img-final":
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(b"\x89PNG\r\n\x1a\n")
                return
            if self.path == "/loop":
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{port}/loop")
                self.end_headers()
                return
            if self.path == "/many-hosts.html":
                body = ("<!doctype html><html><body><h1>many hosts</h1>" + "".join(f'<img src="http://h{i}.invalid/x.png" alt="">' for i in range(8)) + "</body></html>").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/go-ip":  # a redirect to the same server under another origin: what an apex or http:// address does
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/hop1.html")
                self.end_headers()
                return
            if self.path == "/slow.html":
                import time as _time

                _time.sleep(3)
            if self.path == "/bounce.png":
                self.send_response(302)
                self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
                self.end_headers()
                return
            if self.path == "/private.png":
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(b"\x89PNG\r\n\x1a\n")
                return
            if self.path.endswith(".html"):  # the page's own port is patched in, so a subresource can point at 127.0.0.1:<port>
                body = (root / self.path.lstrip("/")).read_bytes().replace(b"__PORT__", str(self.server.server_address[1]).encode())
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://localhost:{server.server_address[1]}"

    class Fixture(str):
        pass

    fixture = Fixture(url)
    fixture.agents = agents  # type: ignore[attr-defined]
    fixture.requests = requests  # type: ignore[attr-defined]
    fixture.port = server.server_address[1]  # type: ignore[attr-defined]
    yield fixture
    server.shutdown()


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


@pytest.fixture
def hero():
    """The recorded checkout capture and the verified hero finding (#f5: "Pay R1,249" vs button "Submit")."""
    from pathlib import Path

    from parity.pipeline.verifier import verify
    from parity.store.models import Candidate, Capture, Finding

    fixture = Path(__file__).parent / "fixtures" / "capture_checkout.json"
    cap = Capture.model_validate_json(fixture.read_text())
    cap.screenshot_png = fixture.with_suffix(".png").read_bytes()
    f5 = next(n for n in cap.ax_nodes if n.dom_id == "f5")
    cand = Candidate(step_index=0, sighted_text="Pay R1,249", sr_quote='button, "Submit"', why_it_matters="price hidden", bbox=f5.bbox)
    r = verify(cand, cap, [])
    assert r.passed
    finding = Finding(id="f-1", run_id="r1", step_index=0, sighted_text=cand.sighted_text, sr_role="button", sr_name="Submit",
                      why_it_matters=cand.why_it_matters, bbox=cand.bbox, element=r.element, verifier=r)
    return cap, finding
