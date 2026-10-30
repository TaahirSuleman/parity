"""Thin async client for Meta's Model API (spec docs/19 §6, D10).

Every call is cached on disk by the SHA-256 of its canonical body and traced as a
``ModelCall`` (model, request ID, tokens, latency, cost). 5xx and transport errors
retry three times with backoff; 4xx raise at once. The key is only ever placed in
the Authorization header and never logged.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from parity.config import Settings, load_settings
from parity.meta.pricing import cost_usd
from parity.store.models import ModelCall

log = logging.getLogger(__name__)

RETRY_SLEEPS = (1, 3, 9)
MAX_ATTEMPTS = 3
CALL_TIMEOUT_S = 300


class MetaError(Exception):
    def __init__(self, message: str, *, status: int | None, request_id: str, attempts: int):
        super().__init__(message)
        self.status = status
        self.request_id = request_id
        self.attempts = attempts


@dataclass
class Usage:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_raw(cls, usage: dict[str, Any] | None) -> Usage:
        usage = usage or {}
        total_in = int(usage.get("input_tokens") or 0)
        cached = int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        total = int(usage.get("total_tokens") or (total_in + out))
        return cls(input_tokens=max(0, total_in - cached), cached_tokens=cached, output_tokens=out, total_tokens=total)


@dataclass
class MetaResponse:
    raw: dict[str, Any]
    text: str
    response_id: str
    request_id: str
    usage: Usage
    cache_hit: bool
    latency_ms: int


class TraceSink(Protocol):
    async def record(self, call: ModelCall) -> None: ...


@dataclass
class ListTraceSink:
    calls: list[ModelCall] = field(default_factory=list)

    async def record(self, call: ModelCall) -> None:
        self.calls.append(call)


def canonical(body: dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def cache_key(body: dict[str, Any]) -> str:
    """SHA-256 of model + canonical body; also the fixture file name used by FakeMetaClient."""
    return hashlib.sha256(str(body.get("model", "")).encode() + canonical(body)).hexdigest()


def text_of(raw: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in raw.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "".join(parts)


class MetaClient:
    def __init__(
        self,
        settings: Settings,
        cache_dir: Path,
        trace: TraceSink,
        http: httpx.AsyncClient | None = None,
        sleep=asyncio.sleep,
    ):
        self.settings = settings
        self.cache_dir = Path(cache_dir)
        self.trace = trace
        self._http = http or httpx.AsyncClient(timeout=CALL_TIMEOUT_S)
        self._sleep = sleep
        self._base = settings.meta_api_base.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.model_api_key}", "Content-Type": "application/json"}

    async def models(self) -> list[str]:
        r = await self._http.get(f"{self._base}/models", headers=self._headers())
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]

    async def responses(self, body: dict[str, Any], *, stage: str, run_id: str, step_index: int | None = None) -> MetaResponse:
        key = cache_key(body)
        model = str(body.get("model", ""))
        cached = self._read_cache(key)
        if cached is not None:
            usage = Usage.from_raw(cached.get("usage"))
            call = ModelCall(
                id=uuid.uuid4().hex, run_id=run_id, step_index=step_index, stage=stage, model=model,
                request_id=cached.get("_request_id", ""), response_id=str(cached.get("id", "")), prompt_sha256=key,
                cache_hit=True, input_tokens=usage.input_tokens, cached_tokens=usage.cached_tokens,
                output_tokens=usage.output_tokens, total_tokens=usage.total_tokens, latency_ms=0, cost_usd=0.0,
                http_status=200,
            )
            await self.trace.record(call)
            return MetaResponse(cached, text_of(cached), call.response_id, call.request_id, usage, True, 0)

        data = canonical(body)
        last_error: MetaError | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            t0 = time.perf_counter()
            status: int | None = None
            request_id = ""
            error: str | None = None
            raw: dict[str, Any] | None = None
            try:
                r = await self._http.post(f"{self._base}/responses", content=data, headers=self._headers())
                status = r.status_code
                request_id = r.headers.get("x-request-id", "")
                if status >= 400:
                    error = f"HTTP {status}: {r.text[:500]}"
                else:
                    raw = r.json()
            except httpx.HTTPError as exc:
                error = f"transport: {type(exc).__name__}: {exc}"
            latency_ms = max(1, math.ceil((time.perf_counter() - t0) * 1000))
            usage = Usage.from_raw(raw.get("usage") if raw else None)
            call = ModelCall(
                id=uuid.uuid4().hex, run_id=run_id, step_index=step_index, stage=stage, model=model,
                request_id=request_id, response_id=str((raw or {}).get("id", "")), prompt_sha256=key,
                cache_hit=False, input_tokens=usage.input_tokens, cached_tokens=usage.cached_tokens,
                output_tokens=usage.output_tokens, total_tokens=usage.total_tokens, latency_ms=latency_ms,
                cost_usd=cost_usd(model, usage.input_tokens, usage.cached_tokens, usage.output_tokens) if raw else 0.0,
                http_status=status, error=error, attempt=attempt,
            )
            await self.trace.record(call)
            if raw is not None:
                raw["_request_id"] = request_id
                self._write_cache(key, raw)
                return MetaResponse(raw, text_of(raw), call.response_id, request_id, usage, False, latency_ms)

            log.warning("meta %s attempt %d failed: status=%s request_id=%s", stage, attempt, status, request_id)
            last_error = MetaError(error or "unknown error", status=status, request_id=request_id, attempts=attempt)
            retryable = status is None or status >= 500
            if not retryable or attempt == MAX_ATTEMPTS:
                raise last_error
            await self._sleep(RETRY_SLEEPS[attempt - 1])
        raise last_error  # pragma: no cover

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def _write_cache(self, key: str, raw: dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_dir / f"{key}.json.tmp"
        tmp.write_text(json.dumps(raw))
        tmp.replace(self.cache_dir / f"{key}.json")

    async def aclose(self) -> None:
        await self._http.aclose()


async def _check() -> int:
    settings = load_settings()
    if not settings.has_key:
        print("MODEL_API_KEY is not set (expected in .env)")
        return 1
    client = MetaClient(settings, cache_dir=settings.cache_dir, trace=ListTraceSink())
    try:
        ids = await client.models()
    finally:
        await client.aclose()
    print("\n".join(ids))
    return 0 if "muse-spark-1.3" in ids else 1


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(asyncio.run(_check()))
    print("usage: python -m parity.meta.client --check")
