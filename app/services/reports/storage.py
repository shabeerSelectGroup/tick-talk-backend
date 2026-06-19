"""Persist generated export files on disk."""

from pathlib import Path

from app.core.config import get_settings


def exports_root() -> Path:
    root = Path(get_settings().exports_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def event_exports_dir(event_id: int) -> Path:
    path = exports_root() / str(event_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_file_path(event_id: int, job_id: int, extension: str) -> Path:
    return event_exports_dir(event_id) / f"export_{job_id}{extension}"
