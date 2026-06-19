"""Backward-compatible R2 helpers — prefer app.storage and app.services.selfie_storage."""

from app.storage import get_storage_backend
from app.storage.r2 import R2StorageBackend


def generate_selfie_key(event_id: int, participant_id: int) -> str:
    uid = R2StorageBackend.new_object_id()
    key, _ = get_storage_backend().generate_selfie_keys(event_id, participant_id, uid)
    return key


def create_presigned_upload_url(key: str, expires_in: int = 3600) -> str | None:
    storage = get_storage_backend()
    if isinstance(storage, R2StorageBackend) and storage.is_configured():
        return storage.create_presigned_upload_url(key, expires_in)
    return None


def public_url(key: str) -> str:
    return get_storage_backend().public_url(key)
