"""Resolve public image URLs for selfies (uses storage keys when present)."""

from __future__ import annotations

from app.models.selfie import Selfie
from app.storage import get_storage_backend


def resolve_selfie_urls(selfie: Selfie) -> tuple[str, str]:
    """Return (image_url, thumbnail_url), preferring live storage URLs from keys."""
    storage = get_storage_backend()
    image_url = selfie.image_url
    thumbnail_url = selfie.thumbnail_url or image_url

    if selfie.storage_key:
        image_url = storage.public_url(selfie.storage_key)
    if selfie.thumbnail_storage_key:
        thumbnail_url = storage.public_url(selfie.thumbnail_storage_key)
    elif selfie.storage_key:
        thumbnail_url = image_url

    return image_url, thumbnail_url or image_url
