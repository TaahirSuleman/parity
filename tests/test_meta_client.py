import json
import logging

import httpx
import pytest

from parity.config import load_settings
from parity.meta.client import ListTraceSink, MetaClient, MetaError
from parity.meta.fake import FakeMetaClient

KEY = "sk-test-secret-0123456789"
BODY = {"model": "muse-spark-1.3", "input": "hello", "reasoning": {"effort": "low"}}
OK_RESPONSE = {
    "id": "resp_1",
    "error": None,
    "output": [{"type": "message", "content": [{"type": "output_text", "text": "hi "}, {"type": "output_text", "text": "there"}]}],
    "usage": {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 200}, "output_tokens": 100, "total_tokens": 1100},
}


def make_client(tmp_path, handler, statuses=None):
    calls = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request, len(calls))

    settings = load_settings(env={"MODEL_API_KEY": KEY})
    trace = ListTraceSink()
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    http = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    client = MetaClient(settings, cache_dir=tmp_path / "cache", trace=trace, http=http, sleep=fake_sleep)
    return client, calls, trace, sleeps


def ok(request, n):
    return httpx.Response(200, json=OK_RESPONSE, headers={"x-request-id": f"req-{n}"})


async def test_cache_miss_then_hit(tmp_path):
    client, calls, trace, _ = make_client(tmp_path, ok)
    first = await client.responses(BODY, stage="comparator", run_id="r1")
    second = await client.responses(BODY, stage="comparator", run_id="r1")
    assert len(calls) == 1
    assert first.cache_hit is False and second.cache_hit is True
    assert second.text == "hi there"
    assert trace.calls[-1].cache_hit is True and trace.calls[-1].cost_usd == 0


async def test_retries_on_500_then_succeeds(tmp_path):
    def flaky(request, n):
        if n < 3:
            return httpx.Response(500, json={"error": {"type": "server_error"}}, headers={"x-request-id": f"req-{n}"})
        return ok(request, n)

    client, calls, trace, sleeps = make_client(tmp_path, flaky)
    resp = await client.responses(BODY, stage="seer", run_id="r1")
    assert resp.text == "hi there"
    assert len(calls) == 3
    assert [c.attempt for c in trace.calls] == [1, 2, 3]
    assert [c.http_status for c in trace.calls] == [500, 500, 200]
    assert sleeps == [1, 3]


async def test_gives_up_after_three_server_errors(tmp_path):
    def broken(request, n):
        return httpx.Response(503, json={}, headers={"x-request-id": f"req-{n}"})

    client, calls, trace, sleeps = make_client(tmp_path, broken)
    with pytest.raises(MetaError) as info:
        await client.responses(BODY, stage="seer", run_id="r1")
    assert len(calls) == 3
    assert info.value.status == 503 and info.value.attempts == 3 and info.value.request_id == "req-3"
    assert sleeps == [1, 3]


async def test_4xx_raises_without_retry(tmp_path):
    def bad(request, n):
        return httpx.Response(400, json={"error": {"message": "bad input"}}, headers={"x-request-id": "req-x"})

    client, calls, trace, sleeps = make_client(tmp_path, bad)
    with pytest.raises(MetaError) as info:
        await client.responses(BODY, stage="judge", run_id="r1")
    assert len(calls) == 1 and sleeps == []
    assert info.value.status == 400 and info.value.request_id == "req-x"
    assert trace.calls[0].error and "bad input" in trace.calls[0].error


async def test_trace_fields(tmp_path):
    client, calls, trace, _ = make_client(tmp_path, ok)
    resp = await client.responses(BODY, stage="comparator", run_id="r1", step_index=2)
    call = trace.calls[0]
    assert call.model == "muse-spark-1.3" and call.stage == "comparator"
    assert call.run_id == "r1" and call.step_index == 2
    assert call.request_id == "req-1" and call.response_id == "resp_1"
    assert (call.input_tokens, call.cached_tokens, call.output_tokens, call.total_tokens) == (800, 200, 100, 1100)
    assert call.latency_ms > 0 and resp.latency_ms == call.latency_ms
    assert round(call.cost_usd, 8) == round((800 * 1.25 + 200 * 0.15 + 100 * 4.25) / 1e6, 8)
    assert len(call.prompt_sha256) == 64


async def test_authorization_header_is_bearer_and_never_logged(tmp_path, caplog):
    with caplog.at_level(logging.DEBUG):
        client, calls, trace, _ = make_client(tmp_path, ok)
        await client.responses(BODY, stage="comparator", run_id="r1")
    assert calls[0].headers["authorization"] == f"Bearer {KEY}"
    assert KEY not in caplog.text
    assert KEY not in json.dumps([c.model_dump(mode="json") for c in trace.calls])


async def test_models_lists_ids(tmp_path):
    def models(request, n):
        assert request.method == "GET" and request.url.path.endswith("/models")
        return httpx.Response(200, json={"data": [{"id": "muse-spark-1.3"}, {"id": "sam-3.1"}]})

    client, *_ = make_client(tmp_path, models)
    assert await client.models() == ["muse-spark-1.3", "sam-3.1"]


async def test_fake_client_raises_on_missing_fixture(tmp_path):
    fake = FakeMetaClient(tmp_path)
    with pytest.raises(KeyError) as info:
        await fake.responses(BODY, stage="comparator", run_id="r1")
    assert "comparator" in str(info.value)


async def test_fake_client_serves_fixture_and_records_body(tmp_path):
    from parity.meta.client import cache_key

    (tmp_path / f"{cache_key(BODY)}.json").write_text(json.dumps(OK_RESPONSE))
    fake = FakeMetaClient(tmp_path)
    resp = await fake.responses(BODY, stage="comparator", run_id="r1")
    assert resp.text == "hi there" and resp.cache_hit is True
    assert fake.calls == [BODY]
