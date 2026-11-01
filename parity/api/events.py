"""In-memory event bus: live subscribers get history first, then new events, until the run ends."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from parity.store.bundle import RunBundle
from parity.store.models import Event

TERMINAL = {"run.finished", "run.failed"}


class EventBus:
    def __init__(self, bundle: RunBundle | None = None):
        self.bundle = bundle
        self._history: dict[str, list[Event]] = {}
        self._subs: dict[str, list[asyncio.Queue[Event]]] = {}
        self._done: set[str] = set()

    def open(self, run_id: str) -> None:
        """Register a run before its first event so early subscribers attach live instead of reading an empty log."""
        self._history.setdefault(run_id, [])

    def knows(self, run_id: str) -> bool:
        return run_id in self._history

    def publish(self, run_id: str, event: Event) -> None:
        if run_id not in self._history and run_id in self._done:
            return  # a forgotten run: the event is already in the bundle, and a partial in-memory history would shadow it
        self._history.setdefault(run_id, []).append(event)
        for q in self._subs.get(run_id, []):
            q.put_nowait(event)
        if event.type in TERMINAL:
            self._done.add(run_id)

    def forget(self, run_id: str) -> None:
        """Drop a finished run's in-memory history once the bundle holds it; late subscribers read the bundle."""
        self._history.pop(run_id, None)
        self._subs.pop(run_id, None)

    def is_finished(self, run_id: str) -> bool:
        return run_id in self._done

    async def history(self, run_id: str) -> list[Event]:
        if run_id in self._history:
            return list(self._history[run_id])
        if self.bundle is not None:
            return await self.bundle.events(run_id)
        return []

    async def subscribe(self, run_id: str) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        live = run_id in self._history and run_id not in self._done
        if live:
            self._subs.setdefault(run_id, []).append(queue)
        try:
            past = await self.history(run_id)
            for event in past:
                yield event
            if not live or any(e.type in TERMINAL for e in past):
                return
            while True:
                event = await queue.get()
                yield event
                if event.type in TERMINAL:
                    return
        finally:
            if queue in self._subs.get(run_id, []):
                self._subs[run_id].remove(queue)
