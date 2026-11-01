"""SQLite index: a derived cache over the bundles for listing and queries. Rebuilt at boot."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from pathlib import Path

import aiosqlite

from parity.store.bundle import RunBundle, keys
from parity.store.models import Event, Finding, ModelCall, Run, RunMode, RunStatus, now

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, status TEXT, mode TEXT, flow_id TEXT, started_at TEXT, cost_usd REAL, tokens INTEGER, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, run_id TEXT, status TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_calls (id TEXT PRIMARY KEY, run_id TEXT, stage TEXT, model TEXT, total_tokens INTEGER, cost_usd REAL, at TEXT, json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS findings_run ON findings (run_id);
CREATE INDEX IF NOT EXISTS calls_run ON model_calls (run_id, at);
"""


class RunIndex:
    def __init__(self, db_path: Path):
        self.path = Path(db_path)
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        if self._db is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self.path)
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.executescript(SCHEMA)
            await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def _conn(self) -> aiosqlite.Connection:
        await self.init()
        assert self._db is not None
        return self._db

    async def upsert_run(self, run: Run) -> None:
        db = await self._conn()
        async with self._lock:
            await db.execute(
                "INSERT OR REPLACE INTO runs (id, status, mode, flow_id, started_at, cost_usd, tokens, json) VALUES (?,?,?,?,?,?,?,?)",
                (run.id, run.status, run.mode, run.flow_id, run.started_at.isoformat(), run.cost_usd, run.tokens, run.model_dump_json()),
            )
            await db.commit()

    async def upsert_finding(self, finding: Finding) -> None:
        db = await self._conn()
        async with self._lock:
            await db.execute(
                "INSERT OR REPLACE INTO findings (id, run_id, status, json) VALUES (?,?,?,?)",
                (finding.id, finding.run_id, finding.status, finding.model_dump_json()),
            )
            await db.commit()

    async def insert_call(self, call: ModelCall) -> None:
        db = await self._conn()
        async with self._lock:
            await db.execute(
                "INSERT OR REPLACE INTO model_calls (id, run_id, stage, model, total_tokens, cost_usd, at, json) VALUES (?,?,?,?,?,?,?,?)",
                (call.id, call.run_id, call.stage, call.model, call.total_tokens, call.cost_usd, call.at.isoformat(), call.model_dump_json()),
            )
            await db.commit()

    async def list_runs(self, limit: int = 100) -> list[Run]:
        db = await self._conn()
        async with db.execute("SELECT json FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)) as cur:
            return [Run.model_validate_json(row[0]) for row in await cur.fetchall()]

    async def get_run(self, run_id: str) -> Run | None:
        db = await self._conn()
        async with db.execute("SELECT json FROM runs WHERE id = ?", (run_id,)) as cur:
            row = await cur.fetchone()
        return Run.model_validate_json(row[0]) if row else None

    async def findings_for(self, run_id: str) -> list[Finding]:
        db = await self._conn()
        async with db.execute("SELECT json FROM findings WHERE run_id = ? ORDER BY id", (run_id,)) as cur:
            return [Finding.model_validate_json(row[0]) for row in await cur.fetchall()]

    async def calls_for(self, run_id: str) -> list[ModelCall]:
        db = await self._conn()
        async with db.execute("SELECT json FROM model_calls WHERE run_id = ? ORDER BY at, id", (run_id,)) as cur:
            return [ModelCall.model_validate_json(row[0]) for row in await cur.fetchall()]

    async def count_runs(self) -> int:
        db = await self._conn()
        async with db.execute("SELECT COUNT(*) FROM runs") as cur:
            return int((await cur.fetchone())[0])

    async def rebuild(self, bundle: RunBundle) -> int:
        """Repopulate the index from every bundle. Idempotent; a second run changes nothing."""
        count = 0
        for run_id in await bundle.list_run_ids():
            try:
                loaded = await bundle.load(run_id)
            except Exception as exc:  # a corrupt bundle must not block boot
                log.warning("skipping unreadable bundle %s: %s", run_id, exc)
                continue
            await self.upsert_run(loaded.run)
            for finding in loaded.findings:
                await self.upsert_finding(finding)
            for call in loaded.trace:
                await self.insert_call(call)
            count += 1
        return count

    async def boot(self, bundle: RunBundle, *, replay_keep: int = 50) -> dict[str, Any]:
        """Everything boot needs from the bundles in ONE pass over them (a bucket read costs a round trip): index each run,
        fail the ones a restart interrupted (with a terminal event), and evict the oldest Replay copies beyond ``replay_keep``
        so a day of judges clicking Replay does not slow the next boot. Newest first, so the kept replays are the recent ones."""
        indexed, recovered, evicted = 0, [], []
        replays_seen = 0
        for run_id in sorted(await bundle.list_run_ids(), reverse=True):
            try:
                run = Run.model_validate_json(await bundle.store.get(keys.run(run_id)))  # one read decides eviction; the rest is loaded once
            except Exception as exc:  # one corrupt bundle must not stop the server from booting
                log.warning("boot skips unreadable bundle %s: %s", run_id, exc)
                continue
            if run.mode == RunMode.replay:
                replays_seen += 1
                if replays_seen > replay_keep:
                    await bundle.delete_run(run_id)  # evicted without reading its screens, findings or logs
                    evicted.append(run_id)
                    continue
            try:
                loaded = await bundle.load(run_id, run=run)
            except Exception as exc:
                log.warning("boot skips unreadable bundle %s: %s", run_id, exc)
                continue
            if run.status in (RunStatus.running, RunStatus.queued):
                run.status = RunStatus.failed
                run.error = "interrupted by restart"
                run.finished_at = now()
                await bundle.write_run(run)
                await bundle.append_event(run_id, Event(type="run.failed", run_id=run_id, data={"error": run.error}))
                recovered.append(run_id)
            await self.upsert_run(run)
            for finding in loaded.findings:
                await self.upsert_finding(finding)
            for call in loaded.trace:
                await self.insert_call(call)
            indexed += 1
        return {"indexed": indexed, "recovered": sorted(recovered), "evicted": sorted(evicted)}

    async def replay_ids_oldest_first(self) -> list[str]:
        db = await self._conn()
        async with db.execute("SELECT id FROM runs WHERE mode = ? ORDER BY started_at ASC, id ASC", (RunMode.replay.value,)) as cur:
            return [row[0] for row in await cur.fetchall()]

    async def delete_run(self, run_id: str) -> None:
        db = await self._conn()
        await db.execute("DELETE FROM model_calls WHERE run_id = ?", (run_id,))
        await db.execute("DELETE FROM findings WHERE run_id = ?", (run_id,))
        await db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        await db.commit()

    async def recover_interrupted(self, bundle: RunBundle) -> list[str]:
        """Runs still marked running/queued after a restart are failed, bundle first, then index."""
        recovered: list[str] = []
        for run_id in await bundle.list_run_ids():
            try:
                run = (await bundle.load(run_id)).run
            except Exception as exc:  # one corrupt bundle must not stop the server from booting
                log.warning("recovery skips unreadable bundle %s: %s", run_id, exc)
                continue
            if run.status in (RunStatus.running, RunStatus.queued):
                run.status = RunStatus.failed
                run.error = "interrupted by restart"
                run.finished_at = now()
                await bundle.write_run(run)
                # the event log ends with a terminal event, or a browser opening the run's link streams the history and
                # then reconnects forever waiting for an end that never comes
                await bundle.append_event(run_id, Event(type="run.failed", run_id=run_id, data={"error": run.error}))
                await self.upsert_run(run)
                recovered.append(run_id)
        return recovered
