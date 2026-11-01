"""BlobStore: where run bundles live (spec docs/19 §5.1, D8).

Local: files under PARITY_DATA_DIR. Cloud Run: objects in a Cloud Storage bucket through the
client library. Keys are relative paths like ``runs/<id>/run.json``; every object is written whole.
"""

from __future__ import annotations

import asyncio
import errno
import os
import shutil
from pathlib import Path
from typing import Any, Protocol

from parity.config import Settings


class BlobStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def exists(self, key: str) -> bool: ...
    async def list(self, prefix: str) -> list[str]: ...
    async def delete_prefix(self, prefix: str) -> int: ...


class LocalBlobStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"key escapes the store root: {key}")
        return path

    @staticmethod
    def _unstorable(exc: BaseException) -> bool:
        """A key the filesystem cannot name (too long, an embedded NUL) is 'not there'; other OSErrors are real faults."""
        return isinstance(exc, ValueError) or getattr(exc, "errno", None) in (errno.ENAMETOOLONG, errno.EINVAL, errno.ENOTDIR)

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    async def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except (OSError, ValueError) as exc:
            if self._unstorable(exc):
                raise FileNotFoundError(key) from None
            raise

    async def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except (OSError, ValueError) as exc:
            if self._unstorable(exc):
                return False
            raise

    async def list(self, prefix: str) -> list[str]:
        base = self.root.resolve()
        try:
            start = self._path(prefix.rstrip("/")) if prefix else base
            if not start.exists():
                return []
        except (OSError, ValueError) as exc:
            if self._unstorable(exc):
                return []
            raise
        out: list[str] = []
        for p in start.rglob("*"):
            if p.is_file() and not p.name.endswith(".tmp"):
                rel = p.relative_to(base).as_posix()
                if rel.startswith(prefix):
                    out.append(rel)
        return sorted(out)

    async def delete_prefix(self, prefix: str) -> int:
        """Remove every object under ``prefix`` (a run's directory); returns how many files went."""
        keys = await self.list(prefix)
        for key in keys:
            self._path(key).unlink(missing_ok=True)
        folder = self._path(prefix.rstrip("/")) if prefix else None
        if folder is not None and folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
        return len(keys)


class GcsBlobStore:
    def __init__(self, bucket: str, prefix: str = "", client: Any | None = None):
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            from google.cloud import storage  # imported lazily: only Cloud Run needs it

            self._client = storage.Client()
        return self._client

    def _name(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def _blob(self, key: str) -> Any:
        return self._get_client().bucket(self.bucket_name).blob(self._name(key))

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        await asyncio.to_thread(self._blob(key).upload_from_string, data, content_type=content_type)

    async def get(self, key: str) -> bytes:
        from google.api_core.exceptions import NotFound

        try:
            return await asyncio.to_thread(self._blob(key).download_as_bytes)
        except NotFound as exc:
            raise FileNotFoundError(key) from exc

    async def exists(self, key: str) -> bool:
        return bool(await asyncio.to_thread(self._blob(key).exists))

    async def list(self, prefix: str) -> list[str]:
        full = self._name(prefix)
        blobs = await asyncio.to_thread(lambda: list(self._get_client().list_blobs(self.bucket_name, prefix=full)))
        cut = len(self.prefix) + 1 if self.prefix else 0
        return sorted(b.name[cut:] for b in blobs)

    async def delete_prefix(self, prefix: str) -> int:
        full = self._name(prefix)

        def go() -> int:
            blobs = list(self._get_client().list_blobs(self.bucket_name, prefix=full))
            for b in blobs:
                b.delete()
            return len(blobs)

        return await asyncio.to_thread(go)


def make_blob_store(settings: Settings, gcs_client: Any | None = None) -> BlobStore:
    if settings.gcs_bucket:
        return GcsBlobStore(settings.gcs_bucket, client=gcs_client)
    return LocalBlobStore(settings.data_dir)
