"""Offline stand-in for MetaClient: serves cached fixtures, records every request body."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parity.meta.client import ListTraceSink, MetaResponse, TraceSink, Usage, cache_key, text_of
from parity.store.models import ModelCall


class FakeMetaClient:
    def __init__(self, fixture_dir: Path, trace: TraceSink | None = None):
        self.fixture_dir = Path(fixture_dir)
        self.trace = trace or ListTraceSink()
        self.calls: list[dict[str, Any]] = []

    async def models(self) -> list[str]:
        return ["muse-spark-1.3", "muse-spark-1.3-contributor", "muse-wonder-1.0", "muse-voice-transcribe-1.0"]

    async def responses(self, body: dict[str, Any], *, stage: str, run_id: str, step_index: int | None = None) -> MetaResponse:
        self.calls.append(body)
        key = cache_key(body)
        path = self.fixture_dir / f"{key}.json"
        if not path.exists():
            raise KeyError(f"no fixture for stage {stage}: expected {path.name} in {self.fixture_dir}")
        raw = json.loads(path.read_text())
        usage = Usage.from_raw(raw.get("usage"))
        await self.trace.record(
            ModelCall(
                id=f"fake-{len(self.calls)}", run_id=run_id, step_index=step_index, stage=stage,
                model=str(body.get("model", "")), request_id=raw.get("_request_id", ""),
                response_id=str(raw.get("id", "")), prompt_sha256=key, cache_hit=True,
                input_tokens=usage.input_tokens, cached_tokens=usage.cached_tokens, output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens, http_status=200,
            )
        )
        return MetaResponse(raw, text_of(raw), str(raw.get("id", "")), raw.get("_request_id", ""), usage, True, 0)

    async def aclose(self) -> None:
        return None
