from app.core.config import get_settings
from app.storage import get_storage_backend
from app.storage.local import LocalStorageBackend


def test_local_storage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("LOCAL_STORAGE_PUBLIC_BASE", "http://localhost:8000/api/v1/media")
    monkeypatch.setenv("R2_ENDPOINT_URL", "")
    get_settings.cache_clear()
    get_storage_backend.cache_clear()

    backend = LocalStorageBackend()
    data = b"test-image-bytes"
    ref = backend.put_object("events/1/selfies/2/abc/full.jpg", data, "image/jpeg")
    assert ref.size_bytes == len(data)
    assert "events/1/selfies/2/abc/full.jpg" in ref.url
    path = backend.resolve_path("events/1/selfies/2/abc/full.jpg")
    assert path.read_bytes() == data
    backend.delete_object("events/1/selfies/2/abc/full.jpg")
    assert not path.exists()


def test_generate_selfie_keys():
    backend = LocalStorageBackend()
    img, thumb = backend.generate_selfie_keys(5, 10, "uid123")
    assert img.endswith("/full.jpg")
    assert thumb.endswith("/thumb.jpg")
    assert "events/5/selfies/10/uid123" in img
