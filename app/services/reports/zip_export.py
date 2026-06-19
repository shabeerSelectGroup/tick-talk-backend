"""ZIP archive of all event selfies."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.storage.local import LocalStorageBackend


async def _load_image_bytes(storage_key: str | None, image_url: str) -> bytes | None:
    if storage_key:
        try:
            backend = LocalStorageBackend()
            path = backend.resolve_path(storage_key)
            if path.is_file():
                return path.read_bytes()
        except Exception:
            pass

    if not image_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(image_url)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        return None
    return None


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name)[:80]


async def generate_selfies_zip(event_code: str, selfies: list[dict]) -> bytes:
    buf = BytesIO()
    used_names: set[str] = set()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "README.txt",
            f"Tick Talk selfies export — event {event_code}\n"
            f"Total entries: {len(selfies)}\n",
        )
        for item in selfies:
            data = await _load_image_bytes(item.get("storage_key"), item.get("image_url", ""))
            if not data:
                continue
            base = _safe_filename(f"{item['id']}_{item['participant_name']}")
            ext = ".jpg"
            if item.get("storage_key"):
                suffix = Path(item["storage_key"]).suffix
                if suffix:
                    ext = suffix
            name = f"{base}{ext}"
            n = 1
            while name in used_names:
                name = f"{base}_{n}{ext}"
                n += 1
            used_names.add(name)
            zf.writestr(f"selfies/{name}", data)

    return buf.getvalue()
