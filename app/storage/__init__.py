from functools import lru_cache

from app.storage.base import StorageBackend, StorageError
from app.storage.local import LocalStorageBackend
from app.storage.r2 import R2StorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    r2 = R2StorageBackend()
    if r2.is_configured():
        return r2
    return LocalStorageBackend()


__all__ = ["StorageBackend", "StorageError", "get_storage_backend"]
