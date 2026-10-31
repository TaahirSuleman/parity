"""EventBus: a subscriber that connects before the first event must get everything, then close on the terminal event."""

import asyncio

from parity.api.events import EventBus
from parity.store.models import Event


async def test_subscribe_before_first_publish_receives_everything():
    bus = EventBus()
    bus.open("r1")  # the POST handler registers the run before the background task starts
    received: list[str] = []

    async def listen():
        async for ev in bus.subscribe("r1"):
            received.append(ev.type)

    task = asyncio.create_task(listen())
    await asyncio.sleep(0.05)  # the subscriber is attached while nothing has been published yet
    assert not task.done()
    bus.publish("r1", Event(type="run.started", run_id="r1"))
    bus.publish("r1", Event(type="run.finished", run_id="r1"))
    await asyncio.wait_for(task, 2)
    assert received == ["run.started", "run.finished"]
    assert bus.knows("r1") and not bus.knows("zzz")


async def test_unknown_run_without_bundle_yields_nothing():
    bus = EventBus()
    assert [e.type async for e in bus.subscribe("never")] == []
