from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.storage import get_storage_backend
from app.storage.local import LocalStorageBackend

router = APIRouter()


@router.get("/media/{storage_path:path}")
async def serve_local_media(storage_path: str):
    """Serve files from local storage backend (development)."""
    storage = get_storage_backend()
    if not isinstance(storage, LocalStorageBackend):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        path: Path = storage.resolve_path(storage_path)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    media_type = "image/jpeg"
    if storage_path.endswith(".png"):
        media_type = "image/png"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})
