"""Server-sent events for one run: history first, then live events, closing on run.finished/failed."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from parity.api.events import EventBus


async def event_stream(bus: EventBus, run_id: str) -> AsyncIterator[ServerSentEvent]:
    n = 0
    async for event in bus.subscribe(run_id):
        n += 1
        payload = {**event.data, "type": event.type, "run_id": event.run_id, "at": event.at.isoformat()}
        yield ServerSentEvent(event=event.type, id=str(n), data=json.dumps(payload))


def sse_response(bus: EventBus, run_id: str) -> EventSourceResponse:
    return EventSourceResponse(event_stream(bus, run_id), ping=15, sep="\n")
