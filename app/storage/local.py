"""Local filesystem storage when R2 is not configured (development)."""

from pathlib import Path

from app.core.config import get_settings
from app.storage.base import StorageBackend, StorageError, StoredObjectRef


class LocalStorageBackend(StorageBackend):
    def __init__(self) -> None:
        settings = get_settings()
        self._root = Path(settings.local_storage_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        base = settings.local_storage_public_base.strip()
        if not base:
            # Relative path works with Vite proxy (5173) and production nginx on the same host.
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
