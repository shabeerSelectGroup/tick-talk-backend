from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_event, get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.models.enums import ExportStatus, ExportType
from app.models.event import Event
from app.schemas.common import ok
from app.schemas.reports import ExportCreateRequest, ExportJobOut
from app.services.reports.jobs import (
    create_export_job,
    enqueue_export_job,
    get_export_job,
    job_to_dict,
    list_export_jobs,
)

router = APIRouter()


@router.get("/events/{event_id}/reports/exports")
async def list_exports(
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    jobs = await list_export_jobs(db, event.id)
    return ok([ExportJobOut(**job_to_dict(j)).model_dump() for j in jobs])


@router.post("/events/{event_id}/reports/exports", status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    body: ExportCreateRequest,
    event: Event = Depends(get_admin_event),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.export_type == ExportType.EXCEL_LEADERBOARD and event.mode.value != "competition":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Leaderboard export is only available for competition events",
        )

    job = await create_export_job(
        db,
        event_id=event.id,
        export_type=body.export_type,
        created_by=admin.id,
    )
    enqueue_export_job(job.id)
    return ok(ExportJobOut(**job_to_dict(job)).model_dump())


@router.get("/events/{event_id}/reports/exports/{job_id}")
async def get_export_status(
    job_id: int,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    job = await get_export_job(db, event.id, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Export job not found")
    return ok(ExportJobOut(**job_to_dict(job)).model_dump())


@router.get("/events/{event_id}/reports/exports/{job_id}/download")
async def download_export(
    job_id: int,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    job = await get_export_job(db, event.id, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Export job not found")
    if job.status != ExportStatus.COMPLETED or not job.file_path:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Export is not ready for download",
        )
    path = Path(job.file_path)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Export file missing on disk")

    return FileResponse(
        path,
        media_type=job.content_type or "application/octet-stream",
        filename=job.file_name or path.name,
    )
