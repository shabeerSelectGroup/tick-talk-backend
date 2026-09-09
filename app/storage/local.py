"""Local filesystem storage when R2 is not configured (development)."""

from pathlib import Path

from app.core.config import get_settings
from app.storage.base import StorageBackend, StorageError, StoredObjectRef

# app/storage/local.py → backend project root
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def resolve_local_storage_root(local_storage_dir: str) -> Path:
    root = Path(local_storage_dir)
    if not root.is_absolute():
        root = _BACKEND_ROOT / root
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


class LocalStorageBackend(StorageBackend):
    def __init__(self) -> None:
        settings = get_settings()
        self._root = resolve_local_storage_root(settings.local_storage_dir)
        base = settings.local_storage_public_base.strip()
        if not base or "localhost:8000" in base or "127.0.0.1:8000" in base:
            # Same-origin path so the Vite proxy (and nginx) can serve files.
            base = "/api/v1/media"
        self._public_base = base.rstrip("/")

    def is_configured(self) -> bool:
        return True

    def public_url(self, key: str) -> str:
        return f"{self._public_base}/{key}"

    def put_object(self, key: str, data: bytes, content_type: str) -> StoredObjectRef:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(data)
        except OSError as e:
            raise StorageError("LOCAL_WRITE_FAILED", f"Could not save file: {e}", 500) from e
        return StoredObjectRef(
            key=key,
            url=self.public_url(key),
            size_bytes=len(data),
            content_type=content_type,
        )

    def delete_object(self, key: str) -> None:
        path = self._root / key
        if path.is_file():
            path.unlink(missing_ok=True)

    def resolve_path(self, key: str) -> Path:
        full = (self._root / key).resolve()
        if not str(full).startswith(str(self._root)):
            raise StorageError("INVALID_KEY", "Invalid storage key.", 400)
        return full
