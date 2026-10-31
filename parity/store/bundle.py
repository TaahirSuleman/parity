"""The run bundle: the truth about a run, as plain objects in a BlobStore (spec docs/19 §5.1).

Only the runner and the decision route write it. Trace and events are buffered in memory and
rewritten whole on ``flush``; a crash loses at most the current stage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from parity.store.blob import BlobStore
from parity.store.models import Capture, Event, Finding, ModelCall, Rejected, Run, Step

JSON = "application/json"


class keys:
    @staticmethod
    def prefix(run_id: str) -> str:
        return f"runs/{run_id}/"

    @staticmethod
    def run(run_id: str) -> str:
        return f"runs/{run_id}/run.json"

    @staticmethod
    def step(run_id: str, n: int) -> str:
        return f"runs/{run_id}/steps/{n}/step.json"

    @staticmethod
    def screenshot(run_id: str, n: int) -> str:
        return f"runs/{run_id}/steps/{n}/screenshot.png"

    @staticmethod
    def ax(run_id: str, n: int) -> str:
        return f"runs/{run_id}/steps/{n}/ax.json"

    @staticmethod
    def axe(run_id: str, n: int) -> str:
        return f"runs/{run_id}/steps/{n}/axe.json"

    @staticmethod
    def finding(run_id: str, fid: str) -> str:
        return f"runs/{run_id}/findings/{fid}.json"

    @staticmethod
    def rejected(run_id: str, rid: str) -> str:
        return f"runs/{run_id}/rejected/{rid}.json"

    @staticmethod
    def trace(run_id: str) -> str:
        return f"runs/{run_id}/trace.jsonl"

    @staticmethod
    def events(run_id: str) -> str:
        return f"runs/{run_id}/events.jsonl"

    @staticmethod
    def patch(run_id: str) -> str:
        return f"runs/{run_id}/fix.patch"


@dataclass
class LoadedRun:
    run: Run
    steps: list[Step] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    rejected: list[Rejected] = field(default_factory=list)
    trace: list[ModelCall] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


def _jsonl(items: list[Any]) -> bytes:
    return ("\n".join(i.model_dump_json() for i in items) + ("\n" if items else "")).encode()


class RunBundle:
    def __init__(self, store: BlobStore):
        self.store = store
        self._trace: dict[str, list[ModelCall]] = {}
        self._events: dict[str, list[Event]] = {}

    async def exists(self, run_id: str) -> bool:
        return await self.store.exists(keys.run(run_id))

    async def create(self, run: Run) -> None:
        await self.write_run(run)

    async def write_run(self, run: Run) -> None:
        await self.store.put(keys.run(run.id), run.model_dump_json(indent=1).encode(), JSON)

    async def write_step(self, step: Step, capture: Capture) -> None:
        n = step.index
        step.screenshot = f"steps/{n}/screenshot.png"
        step.ax_tree = f"steps/{n}/ax.json"
        step.axe = f"steps/{n}/axe.json"
        step.viewport = capture.viewport
        step.axe_violations = len(capture.axe_violations)
        step.ax_nodes = len(capture.ax_nodes)
        step.captured_at = capture.captured_at
        ax = {"ax_nodes": [n.model_dump(mode="json") for n in capture.ax_nodes], "silent_nodes": [n.model_dump(mode="json") for n in capture.silent_nodes]}
        await self.store.put(keys.screenshot(step.run_id, n), capture.screenshot_png, "image/png")
        await self.store.put(keys.ax(step.run_id, n), json.dumps(ax).encode(), JSON)
        await self.store.put(keys.axe(step.run_id, n), json.dumps([v.model_dump(mode="json") for v in capture.axe_violations]).encode(), JSON)
        await self.store.put(keys.step(step.run_id, n), step.model_dump_json(indent=1).encode(), JSON)

    async def write_finding(self, finding: Finding) -> None:
        await self.store.put(keys.finding(finding.run_id, finding.id), finding.model_dump_json(indent=1).encode(), JSON)

    async def write_rejected(self, rejected: Rejected) -> None:
        await self.store.put(keys.rejected(rejected.run_id, rejected.id), rejected.model_dump_json(indent=1).encode(), JSON)

    async def write_patch(self, run_id: str, patch: str) -> None:
        await self.store.put(keys.patch(run_id), patch.encode(), "text/x-diff")

    async def read_patch(self, run_id: str) -> str | None:
        key = keys.patch(run_id)
        if not await self.store.exists(key):
            return None
        return (await self.store.get(key)).decode()

    async def append_event(self, run_id: str, event: Event) -> None:
        """Persist one event after the run's buffers were flushed (a decision): read, append, write whole."""
        events = await self.events(run_id)
        events.append(event)
        if run_id in self._events:
            self._events[run_id].append(event)
        await self.store.put(keys.events(run_id), _jsonl(events), "application/x-ndjson")

    def add_trace(self, run_id: str, call: ModelCall) -> None:
        self._trace.setdefault(run_id, []).append(call)

    def add_event(self, run_id: str, event: Event) -> None:
        self._events.setdefault(run_id, []).append(event)

    async def flush(self, run_id: str) -> None:
        if run_id in self._trace:
            await self.store.put(keys.trace(run_id), _jsonl(self._trace[run_id]), "application/x-ndjson")
        if run_id in self._events:
            await self.store.put(keys.events(run_id), _jsonl(self._events[run_id]), "application/x-ndjson")

    async def _read_jsonl(self, key: str, model: type) -> list[Any]:
        if not await self.store.exists(key):
            return []
        text = (await self.store.get(key)).decode()
        return [model.model_validate_json(line) for line in text.splitlines() if line.strip()]

    async def events(self, run_id: str) -> list[Event]:
        if run_id in self._events:
            return list(self._events[run_id])
        return await self._read_jsonl(keys.events(run_id), Event)

    async def trace(self, run_id: str) -> list[ModelCall]:
        if run_id in self._trace:
            return list(self._trace[run_id])
        return await self._read_jsonl(keys.trace(run_id), ModelCall)

    async def read_screenshot(self, run_id: str, n: int) -> bytes:
        return await self.store.get(keys.screenshot(run_id, n))

    async def load(self, run_id: str) -> LoadedRun:
        if not await self.exists(run_id):
            raise KeyError(run_id)
        run = Run.model_validate_json(await self.store.get(keys.run(run_id)))
        loaded = LoadedRun(run=run)
        prefix = keys.prefix(run_id)
        for key in await self.store.list(prefix):
            rel = key[len(prefix):]
            if rel.startswith("steps/") and rel.endswith("/step.json"):
                loaded.steps.append(Step.model_validate_json(await self.store.get(key)))
            elif rel.startswith("findings/"):
                loaded.findings.append(Finding.model_validate_json(await self.store.get(key)))
            elif rel.startswith("rejected/"):
                loaded.rejected.append(Rejected.model_validate_json(await self.store.get(key)))
        loaded.steps.sort(key=lambda s: s.index)
        loaded.findings.sort(key=lambda f: f.id)
        loaded.rejected.sort(key=lambda r: r.id)
        loaded.trace = await self.trace(run_id)
        loaded.events = await self.events(run_id)
        return loaded

    async def list_run_ids(self) -> list[str]:
        ids = {key.split("/")[1] for key in await self.store.list("runs/") if key.endswith("/run.json")}
        return sorted(ids)
