"""Export job lifecycle and background enqueue."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.enums import ExportStatus, ExportType
from app.models.export_job import ExportJob
from app.services.reports.runner import run_export_job

logger = logging.getLogger(__name__)

# Prevent duplicate tasks for same job id
_running: set[int] = set()


def export_type_label(export_type: ExportType) -> str:
    labels = {
        ExportType.PDF_SUMMARY: "Event summary (PDF)",
        ExportType.EXCEL_PARTICIPANTS: "Participants (Excel)",
        ExportType.EXCEL_MATCHES: "Matches (Excel)",
        ExportType.EXCEL_LEADERBOARD: "Leaderboard (Excel)",
        ExportType.EXCEL_BUNDLE: "Full data workbook (Excel)",
        ExportType.ZIP_SELFIES: "All selfies (ZIP)",
    }
    return labels.get(export_type, export_type.value)


async def create_export_job(
    db: AsyncSession,
    *,
    event_id: int,
    export_type: ExportType,
    created_by: int | None,
) -> ExportJob:
    job = ExportJob(
        event_id=event_id,
        export_type=export_type,
        created_by=created_by,
        status=ExportStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


def enqueue_export_job(job_id: int) -> None:
    """Schedule background processing (in-process asyncio task)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_process_job_background(job_id))
    except RuntimeError:
        asyncio.run(_process_job_background(job_id))


async def _process_job_background(job_id: int) -> None:
    if job_id in _running:
        return
    _running.add(job_id)
    try:
        async with async_session_factory() as db:
            try:
                await run_export_job(db, job_id)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Export job %s failed", job_id)
    finally:
        _running.discard(job_id)


async def get_export_job(db: AsyncSession, event_id: int, job_id: int) -> ExportJob | None:
    result = await db.execute(
        select(ExportJob).where(ExportJob.id == job_id, ExportJob.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def list_export_jobs(
    db: AsyncSession, event_id: int, *, limit: int = 20
) -> list[ExportJob]:
    result = await db.execute(
        select(ExportJob)
        .where(ExportJob.event_id == event_id)
        .order_by(ExportJob.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def job_to_dict(job: ExportJob) -> dict:
    return {
        "id": job.id,
        "event_id": job.event_id,
        "export_type": job.export_type.value
        if hasattr(job.export_type, "value")
        else str(job.export_type),
        "export_label": export_type_label(
            job.export_type
            if isinstance(job.export_type, ExportType)
            else ExportType(job.export_type)
        ),
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "file_name": job.file_name,
        "file_size_bytes": job.file_size_bytes,
        "content_type": job.content_type,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "download_url": f"/api/v1/admin/events/{job.event_id}/reports/exports/{job.id}/download"
        if job.status == ExportStatus.COMPLETED
        else None,
    }
