"""On Cloud Run every object in the bucket is a round trip of tens of milliseconds. A Replay click copies a bundle object by
object, and a shared link loads one the same way: in sequence that was 5.9 s to start the Purchase replay and 2.7 s to open a
run on the hosted app (measured 2 Nov; 50 ms and 17 ms on local disk). These tests pin that the copy and the load overlap
their object reads and writes."""
import asyncio
from pathlib import Path

from parity import replay
from parity.api.events import EventBus
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex

REPLAY_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "replay"


class CountingStore:
    """Wraps a store; each object operation takes a tick, so overlapping calls show as a peak above one."""

    def __init__(self, inner):
        self.inner, self.in_flight, self.peak = inner, 0, 0

    async def _track(self, coro):
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(0.002)
            return await coro
        finally:
            self.in_flight -= 1

    async def put(self, key, data, content_type="application/octet-stream"):
        return await self._track(self.inner.put(key, data, content_type))

    async def get(self, key):
        return await self._track(self.inner.get(key))

    async def exists(self, key):
        return await self._track(self.inner.exists(key))

    async def list(self, prefix):
        return await self.inner.list(prefix)

    async def delete_prefix(self, prefix):
        return await self.inner.delete_prefix(prefix)


async def test_load_reads_a_run_s_objects_concurrently():
    store = CountingStore(LocalBlobStore(REPLAY_ROOT))
    loaded = await RunBundle(store).load("hero-purchase")
    assert len(loaded.findings) >= 30 and len(loaded.steps) == 4
    assert store.peak >= 8, f"objects were read one at a time (peak in flight {store.peak})"


async def test_replay_start_copies_a_bundle_concurrently(tmp_path):
    source = RunBundle(LocalBlobStore(REPLAY_ROOT))
    dest_store = CountingStore(LocalBlobStore(tmp_path / "data"))
    dest = RunBundle(dest_store)
    index = RunIndex(tmp_path / "index.sqlite")
    await index.init()
    tasks: set[asyncio.Task] = set()
    try:
        run = await replay.start("hero-purchase", source, EventBus(dest), dest, index, pace_ms=0, tasks=tasks)
        await asyncio.gather(*tasks)
    finally:
        await index.close()
    copied = await dest.load(run.id)
    assert len(copied.findings) == 34 and len(copied.steps) == 4 and len(copied.events) > 0
    assert dest_store.peak >= 8, f"objects were copied one at a time (peak in flight {dest_store.peak})"
