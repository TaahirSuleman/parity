import pytest

from parity.config import load_settings
from parity.store.blob import GcsBlobStore, LocalBlobStore, make_blob_store


async def test_local_blob_roundtrip_and_list(tmp_path):
    store = LocalBlobStore(tmp_path)
    await store.put("runs/a/run.json", b'{"id": "a"}', "application/json")
    await store.put("runs/a/steps/0/screenshot.png", b"\x89PNG", "image/png")
    await store.put("runs/b/run.json", b"{}", "application/json")
    assert await store.get("runs/a/run.json") == b'{"id": "a"}'
    assert await store.exists("runs/a/run.json") and not await store.exists("runs/zzz")
    assert sorted(await store.list("runs/a/")) == ["runs/a/run.json", "runs/a/steps/0/screenshot.png"]
    assert await store.list("runs/") == sorted(await store.list("runs/"))
    with pytest.raises(FileNotFoundError):
        await store.get("runs/missing.json")


class _FakeBlob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name

    def upload_from_string(self, data, content_type=None):
        self.bucket.objects[self.name] = (data, content_type)

    def download_as_bytes(self):
        if self.name not in self.bucket.objects:
            from google.api_core.exceptions import NotFound

            raise NotFound(self.name)
        return self.bucket.objects[self.name][0]

    def exists(self):
        return self.name in self.bucket.objects


class _FakeBucket:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, str | None]] = {}

    def blob(self, name):
        return _FakeBlob(self, name)


class _FakeGcsClient:
    def __init__(self):
        self.buckets: dict[str, _FakeBucket] = {}

    def bucket(self, name):
        return self.buckets.setdefault(name, _FakeBucket())

    def list_blobs(self, bucket_name, prefix=""):
        bucket = self.bucket(bucket_name)
        return [_FakeBlob(bucket, n) for n in sorted(bucket.objects) if n.startswith(prefix)]


async def test_gcs_blob_uses_client():
    client = _FakeGcsClient()
    store = GcsBlobStore("parity-bucket", prefix="prod", client=client)
    await store.put("runs/a/run.json", b"{}", "application/json")
    assert client.buckets["parity-bucket"].objects["prod/runs/a/run.json"] == (b"{}", "application/json")
    assert await store.get("runs/a/run.json") == b"{}"
    assert await store.exists("runs/a/run.json") and not await store.exists("runs/b/run.json")
    assert await store.list("runs/") == ["runs/a/run.json"]
    with pytest.raises(FileNotFoundError):
        await store.get("runs/b/run.json")


def test_make_blob_store_picks_backend(tmp_path):
    local = make_blob_store(load_settings(env={"PARITY_DATA_DIR": str(tmp_path)}))
    assert isinstance(local, LocalBlobStore)
    gcs = make_blob_store(load_settings(env={"PARITY_GCS_BUCKET": "b"}), gcs_client=_FakeGcsClient())
    assert isinstance(gcs, GcsBlobStore)
