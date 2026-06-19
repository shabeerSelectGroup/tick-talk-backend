"""Task-level selfie submissions for admin and public wall."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SelfieStatus
from app.models.participant import Participant
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.selfie_urls import resolve_selfie_urls


async def selfie_counts_by_task(db: AsyncSession, event_id: int) -> dict[int, int]:
    result = await db.execute(
        select(Selfie.task_id, func.count(Selfie.id))
        .where(
            Selfie.event_id == event_id,
            Selfie.task_id.isnot(None),
            Selfie.status != SelfieStatus.REJECTED,
        )
        .group_by(Selfie.task_id)
    )
    return {int(task_id): int(count) for task_id, count in result.all() if task_id is not None}


async def get_admin_task_submissions(
    db: AsyncSession, event_id: int, task_id: int
) -> dict | None:
    task = await db.get(Task, task_id)
    if not task or task.event_id != event_id:
        return None

    result = await db.execute(
        select(Selfie, Participant)
        .join(Participant, Selfie.participant_id == Participant.id)
        .where(
            Selfie.event_id == event_id,
            Selfie.task_id == task_id,
            Selfie.status != SelfieStatus.REJECTED,
        )
        .order_by(Selfie.uploaded_at.desc())
        .limit(200)
    )
    submissions = []
    for s, p in result.all():
        image_url, thumbnail_url = resolve_selfie_urls(s)
        submissions.append(
            {
                "id": s.id,
                "participant_id": p.id,
                "display_name": p.display_name,
                "company": p.company,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "status": s.status.value,
                "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None,
            }
        )
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "slug": task.slug,
            "type": task.type.value,
        },
        "submissions": submissions,
        "submission_count": len(submissions),
    }


async def get_wall_task_list(db: AsyncSession, event_id: int) -> list[dict]:
    counts = await selfie_counts_by_task(db, event_id)
    result = await db.execute(
        select(Task)
        .where(Task.event_id == event_id, Task.is_active.is_(True))
        .order_by(Task.sort_order, Task.id)
    )
    return [
        {
            "id": t.id,
            "slug": t.slug,
            "title": t.title,
            "description": t.description,
            "type": t.type.value,
            "selfie_count": counts.get(t.id, 0),
            "bingo": bool((t.config_json or {}).get("bingo")),
            "category": (t.config_json or {}).get("category"),
        }
        for t in result.scalars().all()
    ]
