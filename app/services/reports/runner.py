"""Execute export jobs (sync generation, invoked from background task)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExportStatus, ExportType
from app.models.event import Event
from app.models.export_job import ExportJob
from app.services.reports.collector import (
    build_report_context,
    fetch_leaderboard_export,
    fetch_matches_export,
    fetch_participants_export,
    fetch_selfies_export,
)
from app.services.reports.excel_export import (
    generate_excel_bundle,
    generate_excel_leaderboard,
    generate_excel_matches,
    generate_excel_participants,
)
from app.services.reports.pdf_export import generate_pdf_summary
from app.services.reports.storage import job_file_path
from app.services.reports.zip_export import generate_selfies_zip

EXPORT_META: dict[ExportType, tuple[str, str, str]] = {
    ExportType.PDF_SUMMARY: ("pdf", "application/pdf", "event-summary.pdf"),
    ExportType.EXCEL_PARTICIPANTS: (
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "participants.xlsx",
    ),
    ExportType.EXCEL_MATCHES: (
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "matches.xlsx",
    ),
    ExportType.EXCEL_LEADERBOARD: (
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "leaderboard.xlsx",
    ),
    ExportType.EXCEL_BUNDLE: (
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "event-data.xlsx",
    ),
    ExportType.ZIP_SELFIES: ("zip", "application/zip", "selfies.zip"),
}


async def run_export_job(db: AsyncSession, job_id: int) -> ExportJob:
    result = await db.execute(
        select(ExportJob, Event)
        .join(Event, ExportJob.event_id == Event.id)
        .where(ExportJob.id == job_id)
    )
    row = result.one_or_none()
    if not row:
        raise ValueError(f"Export job {job_id} not found")
    job, event = row

    job.status = ExportStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    job.error_message = None
    await db.flush()

    try:
        ext, content_type, default_name = EXPORT_META[job.export_type]
        data = await _generate(db, job.export_type, event)
        path = job_file_path(event.id, job.id, f".{ext}")
        path.write_bytes(data)
        job.file_path = str(path)
        job.file_name = f"{event.code}_{default_name}"
        job.file_size_bytes = len(data)
        job.content_type = content_type
        job.status = ExportStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        job.status = ExportStatus.FAILED
        job.error_message = str(e)[:2000]
        job.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return job


async def _generate(db: AsyncSession, export_type: ExportType, event: Event) -> bytes:
    if export_type == ExportType.PDF_SUMMARY:
        ctx = await build_report_context(db, event)
        return generate_pdf_summary(event, ctx)

    if export_type == ExportType.EXCEL_PARTICIPANTS:
        rows = await fetch_participants_export(db, event.id)
        return generate_excel_participants(rows)

    if export_type == ExportType.EXCEL_MATCHES:
        rows = await fetch_matches_export(db, event.id)
        return generate_excel_matches(rows)

    if export_type == ExportType.EXCEL_LEADERBOARD:
        rows = await fetch_leaderboard_export(db, event.id)
        return generate_excel_leaderboard(rows)

    if export_type == ExportType.EXCEL_BUNDLE:
        participants = await fetch_participants_export(db, event.id)
        matches = await fetch_matches_export(db, event.id)
        leaderboard = await fetch_leaderboard_export(db, event.id)
        return generate_excel_bundle(participants, matches, leaderboard)

    if export_type == ExportType.ZIP_SELFIES:
        selfies = await fetch_selfies_export(db, event.id)
        return await generate_selfies_zip(event.code, selfies)

    raise ValueError(f"Unsupported export type: {export_type}")
