"""Object storage abstraction for selfies and media."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.exceptions import AppError


class StorageError(AppError):
    pass


@dataclass(frozen=True)
class StoredObjectRef:
    key: str
    url: str
    size_bytes: int
    content_type: str


class StorageBackend(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when this backend can persist objects."""

    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str) -> StoredObjectRef:
        ...

    @abstractmethod
    def delete_object(self, key: str) -> None:
        ...

    @abstractmethod
    def public_url(self, key: str) -> str:
        ...

    def generate_selfie_keys(self, event_id: int, participant_id: int, uid: str) -> tuple[str, str]:
        base = f"events/{event_id}/selfies/{participant_id}/{uid}"
        return f"{base}/full.jpg", f"{base}/thumb.jpg"
