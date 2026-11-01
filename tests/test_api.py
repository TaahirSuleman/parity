import re
import json

import httpx
import pytest
import pytest_asyncio

from tests.helpers import SRC, parse_sse


async def test_health_reports_storage_and_index(api):
    client, _ = api
    body = (await client.get("/api/health")).json()
    assert body["ok"] is True and body["storage"] == "local" and body["runs_indexed"] == 0
    assert body["mode_default"] == "replay" and body["has_key"] is False
    assert body["replay_flows"] == {"checkout": "hero-src"}


async def test_flows_lists_checkout(api):
    client, _ = api
    flows = (await client.get("/api/flows")).json()
    assert [f["id"] for f in flows] == ["checkout", "purchase"] and flows[0]["start_url"] == "/store/checkout.html"
    assert flows[1]["single_page"] is False and len(flows[1]["pages"]) == 4


async def test_post_replay_run_streams_hero(api):
    client, _ = api
    r = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    assert run_id != SRC and r.json()["mode"] == "replay" and r.json()["replay_of"] == SRC
    stream = await client.get(f"/api/runs/{run_id}/events")
    assert stream.status_code == 200 and stream.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(stream.text)
    types = [t for t, _ in events]
    assert types[0] == "run.started" and types[-1] == "run.finished"
    hero = next(d for t, d in events if t == "verifier.result")
    assert hero["finding"]["sighted_text"] == "Pay R1,249" and hero["finding"]["run_id"] == run_id
    assert all(d["run_id"] == run_id for _, d in events if d) and all(d["mode"] == "replay" for _, d in events if d)


async def test_events_after_finish_replays_history_then_closes(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    first = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    second = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert [t for t, _ in first] == [t for t, _ in second] and second[-1][0] == "run.finished"
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["status"] == "awaiting_review" and detail["run"]["mode"] == "replay"


async def test_get_run_detail_includes_trace(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["id"] == run_id and detail["findings"][0]["sr_name"] == "Submit"
    assert detail["trace"][0]["stage"] == "comparator" and detail["trace"][0]["request_id"] == "req-1"
    assert detail["steps"][0]["screenshot"] == "steps/0/screenshot.png"
    assert (await client.get("/api/health")).json()["runs_indexed"] == 1  # indexed; the list itself is not public


async def test_screenshot_png_content_type(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    r = await client.get(f"/api/runs/{run_id}/steps/0/screenshot.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert (await client.get(f"/api/runs/{run_id}/steps/9/screenshot.png")).status_code == 404


async def test_unknown_flow_404(api):
    client, _ = api
    assert (await client.post("/api/runs", json={"flow_id": "nope", "mode": "replay"})).status_code == 404
    assert (await client.get("/api/runs/nope")).status_code == 404
    assert (await client.get("/api/runs/nope/events")).status_code == 404


async def test_post_live_without_key_503(api):
    client, _ = api
    r = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    assert r.status_code == 503 and "MODEL_API_KEY" in r.json()["detail"]


async def test_verifier_off_route(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")
    r = await client.get(f"/api/runs/{run_id}/verifier-off")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id and body["reported"] == 1 and body["verified"] == 1 and body["rejected_by_verifier"] == 0
    assert (await client.get("/api/runs/nope/verifier-off")).status_code == 404


async def test_second_live_post_gets_429_while_first_runs(api, tmp_path):
    """The Live slot is taken in the handler, not later in the task, so a double click cannot queue two runs."""
    from parity.meta.fake import FakeMetaClient

    client, app = api
    app.state.client = FakeMetaClient(tmp_path / "none")  # a live run will fail fast (no fixtures), which is fine here
    first = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    second = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
    assert first.status_code == 202 and second.status_code == 429 and "Retry-After" in second.headers
    run_id = first.json()["run_id"]
    stream = await client.get(f"/api/runs/{run_id}/events")  # connected right after the POST: must not 404 and must not be empty
    events = parse_sse(stream.text)
    assert events and events[0][0] == "run.started" and events[-1][0] in ("run.finished", "run.failed")
    app.state.client = None


async def test_replay_writes_final_state_before_terminal_event(api):
    import asyncio

    client, app = api
    st = app.state
    from parity import replay as replay_mod

    run = await replay_mod.start(SRC, st.replay_bundle, st.bus, st.bundle, st.index, pace_ms=0)
    seen = []
    async for ev in st.bus.subscribe(run.id):
        if ev.type == "run.finished":
            seen.append((await st.bundle.load(run.id)).run.status)
    await asyncio.sleep(0)
    assert seen == ["awaiting_review"]


async def replayed_run(client) -> str:
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")  # drain: the replay has finished
    return run_id


async def test_decision_requires_reason(api):
    client, _ = api
    run_id = await replayed_run(client)
    url = f"/api/runs/{run_id}/findings/{run_id}-f01/decision"
    assert (await client.post(url, json={"decision": "approve", "reason": "   "})).status_code == 422
    assert (await client.post(url, json={"decision": "maybe", "reason": "x"})).status_code == 422
    assert (await client.post(f"/api/runs/{run_id}/findings/nope/decision", json={"decision": "approve", "reason": "x"})).status_code == 404
    assert (await client.post(f"/api/runs/nope/findings/x/decision", json={"decision": "approve", "reason": "x"})).status_code == 404
    assert (await client.get(f"/api/runs/{run_id}/patch")).status_code == 404  # nothing approved yet


async def test_decision_records_and_patch_contains_only_approved(api):
    client, _ = api
    run_id = await replayed_run(client)
    fid = f"{run_id}-f01"
    r = await client.post(f"/api/runs/{run_id}/findings/{fid}/decision", json={"decision": "approve", "reason": "Looks right"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["finding"]["status"] == "approved" and body["finding"]["decision"]["reason"] == "Looks right"
    assert body["run"]["status"] == "done"  # nothing left to review
    patch = await client.get(f"/api/runs/{run_id}/patch")
    assert patch.status_code == 200 and patch.headers["content-type"].startswith("text/x-diff")
    assert "+++ b/store/checkout.html" in patch.text and "Pay R1,249" in patch.text
    events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert events[-1][0] == "decision.recorded" and events[-1][1]["decision"]["decision"] == "approve" and events[-1][1]["run_status"] == "done"
    assert (await client.post(f"/api/runs/{run_id}/findings/{fid}/decision", json={"decision": "reject", "reason": "changed my mind"})).status_code == 409
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["status"] == "done" and detail["findings"][0]["status"] == "approved"
    assert (await client.get(f"/api/runs/{run_id}")).json()["run"]["status"] == "done"


async def test_rejected_fix_leaves_no_patch(api):
    client, _ = api
    run_id = await replayed_run(client)
    r = await client.post(f"/api/runs/{run_id}/findings/{run_id}-f01/decision", json={"decision": "reject", "reason": "Not a barrier in context"})
    assert r.status_code == 200 and r.json()["finding"]["status"] == "rejected" and r.json()["run"]["status"] == "done"
    assert (await client.get(f"/api/runs/{run_id}/patch")).status_code == 404


async def test_decisions_during_replay_playback_settle_the_run(api):
    """Judges approve while the replay is still pacing out events; the run must end done, not stuck awaiting review."""
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 150})).json()["run_id"]
    r = await client.post(f"/api/runs/{run_id}/findings/{run_id}-f01/decision", json={"decision": "approve", "reason": "during playback"})
    assert r.status_code == 200, r.text
    events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert events[-1][0] in ("run.finished", "decision.recorded")
    detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert detail["run"]["status"] == "done" and detail["findings"][0]["status"] == "approved"


async def test_public_run_responses_carry_no_ip_hash_or_internal_url(api):
    client, _ = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await client.get(f"/api/runs/{run_id}/events")
    listed = (await client.get(f"/api/runs/{run_id}")).json()["run"]
    detail = (await client.get(f"/api/runs/{run_id}")).json()["run"]
    for body in (listed, detail):
        assert "client_ip_hash" not in body and "127.0.0.1" not in str(body.get("target_url", ""))


async def test_eval_route_serves_the_latest_results(tmp_path, monkeypatch):
    """GET /api/eval is the one number set the Eval tab, the README and the video quote."""
    from parity.app import create_app
    from parity.config import load_settings

    results = tmp_path / "results"
    results.mkdir()
    (results / "latest.json").write_text(json.dumps({"updated_at": "t", "model": "muse-spark-1.3-contributor", "n_faults": 37, "n_clean": 20,
        "configs": {"full": {"runs": 3, "total": {"recall": 0.8, "precision": 0.9, "fp_on_clean": 0, "n": 30, "n_labels": 37, "cost_usd": 0.1, "seconds": 120}}},
        "axe": {"recall": 0.0, "violations": 0}, "judge": {"muse-spark-1.3": {"agreement": 0.95, "needs_review_rate": 0.0, "cost_per_finding": 0.01, "n": 30}}}))
    (results / "public.json").write_text(json.dumps([{"name": "Site A", "run_id": "public-a", "pages": 2, "verified": 3, "rejected": 1}]))
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
                                  "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay"), "PARITY_EVAL_DIR": str(results)})
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/eval")
            assert r.status_code == 200
            body = r.json()
            assert body["configs"]["full"]["total"]["recall"] == 0.8 and body["axe"]["violations"] == 0
            assert body["public"] == [{"name": "Site A", "run_id": "public-a", "pages": 2, "verified": 3, "rejected": 1}]
    (results / "latest.json").unlink()
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/eval")).status_code == 404


async def test_replay_by_run_id_for_a_public_sample(tmp_path):
    """A public bundle has no flow in FLOWS: Replay starts it by run id (the Eval tab's 'open in Replay')."""
    from parity.app import create_app
    from parity.config import load_settings
    from tests.helpers import make_replay_bundle

    await make_replay_bundle(tmp_path / "replay")
    src = tmp_path / "replay" / "runs"
    (src / SRC).rename(src / "public-a")
    for p in (src / "public-a").rglob("*"):
        if p.is_file() and p.suffix in (".json", ".jsonl"):
            p.write_text(p.read_text().replace(SRC, "public-a").replace('"flow_id": "checkout"', '"flow_id": "public"'))
        elif p.is_file() and SRC in p.name:
            p.rename(p.with_name(p.name.replace(SRC, "public-a")))
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
                                  "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay")})
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert "public-a" in (await client.get("/api/health")).json()["replay_runs"]
            r = await client.post("/api/runs", json={"mode": "replay", "replay_of": "public-a", "pace_ms": 0})
            assert r.status_code == 202, r.text
            run_id = r.json()["run_id"]
            events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
            assert events[0][0] == "run.started" and events[-1][0] == "run.finished"
            assert (await client.post("/api/runs", json={"mode": "replay", "replay_of": "nope"})).status_code == 404
            assert (await client.post("/api/runs", json={"mode": "live", "replay_of": "public-a"})).status_code == 422  # replay_of is for Replay only


async def test_replay_of_a_bundle_whose_screenshot_was_withheld(api, tmp_path):
    """An anonymised public sample keeps a screenshot only where a finding was verified (spec §17): a step without one must
    still replay; its screenshot route answers 404 and the rest of the step is served."""
    client, app = api
    (tmp_path / "replay" / "runs" / SRC / "steps" / "0" / "screenshot.png").unlink()
    r = await client.post("/api/runs", json={"mode": "replay", "replay_of": SRC, "pace_ms": 0})
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    assert (await client.get(f"/api/runs/{run_id}/steps/0/screenshot.png")).status_code == 404
    events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert events[0][0] == "run.started" and events[-1][0] == "run.finished"  # the rest of the step replays as usual


async def _app_with(tmp_path, **env):
    from parity.app import create_app
    from parity.config import load_settings
    from tests.helpers import make_replay_bundle

    await make_replay_bundle(tmp_path / "replay")
    settings = load_settings(env={
        "PARITY_DATA_DIR": str(tmp_path / "data"), "PARITY_CACHE_DIR": str(tmp_path / "cache"),
        "PARITY_INDEX_PATH": str(tmp_path / "index.db"), "PARITY_REPLAY_DIR": str(tmp_path / "replay"), **env,
    })
    return create_app(settings)


async def _finish(client, run_id: str) -> None:
    events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)
    assert events[-1][0] in ("run.finished", "run.failed")


async def test_live_runs_are_rate_limited_per_ip_with_a_json_429_and_replay_is_unlimited(tmp_path):
    """Spec §15: a visitor gets a few Live runs an hour; the refusal says when to retry and points at Replay, which is never counted."""
    import httpx

    from parity.meta.fake import FakeMetaClient

    app = await _app_with(tmp_path, PARITY_LIVE_PER_IP_PER_HOUR="1")
    async with app.router.lifespan_context(app):
        app.state.client = FakeMetaClient(tmp_path / "none")  # a live run fails fast without fixtures, which is all this needs
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
            assert first.status_code == 202
            await _finish(client, first.json()["run_id"])
            second = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"})
            assert second.status_code == 429 and second.headers.get("Retry-After")
            body = second.json()
            assert body["suggestion"] == "replay" and isinstance(body["retry_after_s"], int) and body["retry_after_s"] > 0 and "error" in body
            for _ in range(5):  # Replay is unlimited
                assert (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).status_code == 202


async def test_forwarded_for_header_is_trusted_only_behind_a_proxy(tmp_path):
    """Behind Cloud Run the visitor is the RIGHT-most X-Forwarded-For hop (the front end appends the address it saw; anything to the
    left is what the client typed); from a direct client the whole header is ignored."""
    import httpx

    from parity.meta.fake import FakeMetaClient

    async def two_posts(app):
        async with app.router.lifespan_context(app):
            app.state.client = FakeMetaClient(tmp_path / "none")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                first = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"}, headers={"X-Forwarded-For": "10.9.9.1, 198.51.100.7"})
                assert first.status_code == 202
                await _finish(client, first.json()["run_id"])
                forged = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"}, headers={"X-Forwarded-For": "10.9.9.2, 198.51.100.7"})).status_code
                other = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "live"}, headers={"X-Forwarded-For": "203.0.113.9"})).status_code
                return forged, other

    assert await two_posts(await _app_with(tmp_path / "direct", PARITY_LIVE_PER_IP_PER_HOUR="1")) == (429, 429)  # header ignored: one visitor
    assert await two_posts(await _app_with(tmp_path / "proxied", PARITY_LIVE_PER_IP_PER_HOUR="1", PARITY_TRUST_PROXY="1")) == (429, 202)  # a forged left hop is still the same visitor; a new right hop is another


async def test_finished_run_buffers_are_evicted_and_history_is_still_served(api):
    """A finished run's events and trace live in the bundle; keeping them in memory as well would grow with every Replay click."""
    client, app = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await _finish(client, run_id)
    assert not app.state.bus.knows(run_id) and run_id not in app.state.bundle._events and run_id not in app.state.bundle._trace
    events = parse_sse((await client.get(f"/api/runs/{run_id}/events")).text)  # a late subscriber reads the bundle
    assert events[0][0] == "run.started" and events[-1][0] == "run.finished" and len(events) > 5


async def test_health_reports_storage_index_and_model_reachability(api):
    """The deploy check reads these three: where bundles live, how many runs the index holds, and whether the model API answered at boot."""
    client, _ = api
    body = (await client.get("/api/health")).json()
    assert body["storage"] == "local" and isinstance(body["runs_indexed"], int)
    assert body["models_ok"] is False  # no key in tests: the boot probe did not run


async def test_replay_start_caps_the_copies_kept(tmp_path):
    """Every Replay click copies a bundle; the cap applies when a Replay starts, not only at the next boot, so a day of judges cannot slow the next restart."""
    import httpx

    app = await _app_with(tmp_path, PARITY_REPLAY_KEEP="1", PARITY_REPLAY_MIN_AGE_S="0")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            ids = []
            for _ in range(3):
                r = await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})
                assert r.status_code == 202
                ids.append(r.json()["run_id"])
                await _finish(client, ids[-1])
            kept = await app.state.bundle.list_run_ids()
    assert ids[-1] in kept and ids[0] not in kept and ids[1] not in kept, (ids, kept)


async def test_asset_404_is_not_cached_for_a_year_and_head_root_is_allowed(api):
    client, _ = api
    missing = await client.get("/assets/index-nope.js")
    assert missing.status_code == 404 and "immutable" not in missing.headers.get("cache-control", "")
    assert (await client.head("/")).status_code == 200  # uptime checkers use HEAD


async def test_run_and_finding_ids_are_validated_before_touching_storage(api):
    """A 2,000-character id reached os.stat and raised 'File name too long' (a 500 that reset the connection). Ids are validated
    at the API boundary: anything that is not a run id answers 404, for every route that takes one."""
    client, _ = api
    long_id = "a" * 2000
    for path in (f"/api/runs/{long_id}", f"/api/runs/{long_id}/events", f"/api/runs/{long_id}/steps/0/screenshot.png", f"/api/runs/{long_id}/patch", f"/api/runs/{long_id}/verifier-off",
                 "/api/runs/..%2F..%2Fetc", "/api/runs/run%00id", "/api/runs/x y"):
        r = await client.get(path)
        assert r.status_code == 404, (path[:60], r.status_code)
    r = await client.post(f"/api/runs/{long_id}/findings/{long_id}/decision", json={"decision": "approve", "reason": "x"})
    assert r.status_code == 404
    r = await client.get("/api/runs/20261101-000000-abcd/steps/-1/screenshot.png")
    assert r.status_code == 422  # a negative step is a malformed request, not a missing screenshot
    r = await client.get("/api/runs/20261101-000000-abcd/steps/99999999999999999999/screenshot.png")
    assert r.status_code == 422


async def test_spa_catch_all_answers_404_for_paths_the_filesystem_cannot_name(api):
    """GET /%00 and GET /<2,000 characters> reached Path.resolve()/is_file() and raised (a 500 that reset the connection).
    Such a path is neither a static file nor a run link: 404."""
    client, _ = api
    for path in ("/%00", "/eval/%00", "/" + "a" * 2000, "/runs/" + "b" * 2000, "/store/%00"):
        r = await client.get(path)
        assert r.status_code == 404, (path[:40], r.status_code)
    r = await client.get("/runs/20261101-000000-abcd")  # a real-looking deep link still opens the workbench
    assert r.status_code == 200 and b"<!doctype html" in r.content.lower()


async def test_replay_eviction_never_removes_a_replay_that_is_still_playing(tmp_path):
    """With the cap at 1, a second Replay click used to delete the first copy while its events were still streaming (screenshots 404,
    the detail route 404). A playing replay is exempt from eviction; it becomes evictable once its stream has ended."""
    import httpx

    app = await _app_with(tmp_path, PARITY_REPLAY_KEEP="1", PARITY_REPLAY_MIN_AGE_S="0")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 400})).json()["run_id"]
            second = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
            assert first in await app.state.bundle.list_run_ids(), "the playing replay was evicted"
            assert (await client.get(f"/api/runs/{first}/steps/0/screenshot.png")).status_code == 200
            await _finish(client, second)
            await _finish(client, first)
            third = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
            await _finish(client, third)
            kept = await app.state.bundle.list_run_ids()
    assert third in kept and first not in kept and second not in kept, kept


async def test_oversized_request_bodies_are_refused_before_they_are_read(api):
    """A 60 MB body took the instance from 13 to 362 MB and came back whole inside a 404. No API body is larger than a few KB."""
    client, _ = api
    big = b'{"flow_id":"checkout","mode":"replay","pad":"' + b"x" * (2 * 1024 * 1024) + b'"}'
    r = await client.post("/api/runs", content=big, headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json()["detail"]

    async def chunks():  # no Content-Length: the body is counted as it arrives
        for _ in range(40):
            yield b"x" * 8192

    r = await client.post("/api/runs", content=chunks(), headers={"content-type": "application/json"})
    assert r.status_code == 413
    r = await client.post("/api/runs", json={"flow_id": "f" * 5000, "mode": "replay"})
    assert r.status_code == 404 and len(r.text) < 300, len(r.text)  # the unknown flow id is not echoed back whole


async def test_validation_errors_stay_json_for_inputs_that_cannot_be_serialised(api):
    """FastAPI's default 422 echoes the input; `Infinity` and a lone surrogate cannot be re-serialised, which made a 500."""
    client, _ = api
    r = await client.post("/api/runs", content=b'{"flow_id":"checkout","mode":"replay","pace_ms":Infinity}', headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["detail"]
    r = await client.post("/api/runs/20261101-000000-abcd/findings/x/decision", content=b'{"decision":"approve","reason":"\\ud800"}', headers={"content-type": "application/json"})
    assert r.status_code == 422, r.status_code  # a reason that is not valid text is refused, not stored


async def test_a_corrupt_stored_record_is_a_clean_500_not_a_traceback_or_a_422(api):
    """A finding file that no longer parses is a server-side fault: one JSON 500 with a short detail, on the detail route and the
    decision route alike (the decision route used to map pydantic's ValidationError, a ValueError, to a 422 full of internals)."""
    client, app = api
    run_id = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    await _finish(client, run_id)
    findings_dir = app.state.settings.data_dir / "runs" / run_id / "findings"
    first = sorted(findings_dir.glob("*.json"))[0]
    first.write_text('{"id": "broken"')
    for method, path, body in (("GET", f"/api/runs/{run_id}", None), ("POST", f"/api/runs/{run_id}/findings/{first.stem}/decision", {"decision": "reject", "reason": "x"})):
        r = await client.request(method, path, json=body)
        assert r.status_code == 500, (path, r.status_code)
        assert r.headers["content-type"].startswith("application/json") and "unreadable" in r.json()["detail"] and "ValidationError" not in r.text


async def test_eval_results_that_do_not_parse_are_a_404_not_a_500(tmp_path):
    """The Eval tab treats 404 as 'no results yet'; a truncated or list-shaped latest.json is an operator error to log, not a crash."""
    import httpx

    results = tmp_path / "results"
    results.mkdir()
    for bad in ('{"configs": ', "[1, 2]", b"\xff\xfe".decode("latin-1")):
        (results / "latest.json").write_text(bad)
        app = await _app_with(tmp_path, PARITY_EVAL_DIR=str(results))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get("/api/eval")
                assert r.status_code == 404 and "unreadable" in r.json()["detail"], (bad[:10], r.status_code)


async def test_run_listing_is_not_public(api):
    """Run ids are the only capability a visitor holds over a run (a shared link shares the decisions, by design); a public list of
    every id would let any visitor decide every other visitor's findings. The count stays in /api/health."""
    client, _ = api
    assert (await client.get("/api/runs")).status_code == 404
    assert isinstance((await client.get("/api/health")).json()["runs_indexed"], int)


async def test_generated_run_ids_carry_32_random_bits_and_never_reuse_an_existing_id(api, monkeypatch):
    """Four hex digits collided in 0.55% of 30-id bursts and a collision merged two bundles. Ids now carry eight, and a start
    that lands on an existing id draws again."""
    from parity import replay

    client, app = api
    first = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    assert re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{8}", first), first
    await _finish(client, first)
    draws = iter([first, first, "20261101-000000-0badf00d"])
    monkeypatch.setattr(replay, "new_run_id", lambda: next(draws))
    second = (await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"]
    assert second == "20261101-000000-0badf00d"


async def test_young_replay_copies_survive_the_cap_when_a_replay_starts(tmp_path):
    """The same rule on the Replay-start path: with the cap at 1 and the default minimum age, three fresh copies all stay."""
    import httpx

    app = await _app_with(tmp_path, PARITY_REPLAY_KEEP="1")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            ids = []
            for _ in range(3):
                ids.append((await client.post("/api/runs", json={"flow_id": "checkout", "mode": "replay", "pace_ms": 0})).json()["run_id"])
                await _finish(client, ids[-1])
            kept = await app.state.bundle.list_run_ids()
    assert set(ids) <= set(kept), (ids, kept)
