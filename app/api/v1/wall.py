from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.schemas.common import ok
from app.schemas.participant import LeaderboardEntry
from app.schemas.wall import WallSelfieOut, WallStatsOut, WallTaskOut, WallTimerOut
from app.services.events import get_event_by_code
from app.services.task_gallery import get_wall_task_list
from app.services.wall import (
    get_wall_leaderboard,
    get_wall_selfies,
    get_wall_stats,
    get_wall_timer,
)

router = APIRouter()


async def _wall_event_or_403(db: AsyncSession, code: str):
    from app.services.event_settings import get_settings_for_event, is_public_wall_enabled

    event = await get_event_by_code(db, code)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")
    settings = await get_settings_for_event(db, event.id)
    if not is_public_wall_enabled(settings):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Public wall is disabled for this event")
    return event, settings


@router.get("/{code}")
async def wall_event(code: str, db: AsyncSession = Depends(get_db)):
    event, settings = await _wall_event_or_403(db, code)
    from app.services.event_presenter import event_public_dict

    return ok(event_public_dict(event, settings))


@router.get("/{code}/timer")
async def wall_timer(code: str, db: AsyncSession = Depends(get_db)):
    event, _ = await _wall_event_or_403(db, code)
    data = await get_wall_timer(db, event)
    return ok(WallTimerOut(**data).model_dump())


@router.get("/{code}/stats")
async def wall_stats(code: str, db: AsyncSession = Depends(get_db)):
    event, _ = await _wall_event_or_403(db, code)
    data = await get_wall_stats(db, event)
    return ok(WallStatsOut(**data).model_dump())


@router.get("/{code}/tasks")
async def wall_tasks(code: str, db: AsyncSession = Depends(get_db)):
    event, _ = await _wall_event_or_403(db, code)
    rows = await get_wall_task_list(db, event.id)
    return ok([WallTaskOut(**r).model_dump() for r in rows])


@router.get("/{code}/selfies")
async def wall_selfies(
    code: str,
    limit: int = Query(24, ge=1, le=60),
    task_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    event, _ = await _wall_event_or_403(db, code)
    rows = await get_wall_selfies(db, event.id, limit=limit, task_id=task_id)
    return ok([WallSelfieOut(**r).model_dump() for r in rows])


@router.get("/{code}/leaderboard")
async def wall_leaderboard(code: str, db: AsyncSession = Depends(get_db)):
    event, _ = await _wall_event_or_403(db, code)
    board = await get_wall_leaderboard(db, event)
    return ok([LeaderboardEntry(**row).model_dump() for row in board])


@router.get("/{code}/highlights")
async def wall_highlights(
    code: str,
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    event, _ = await _wall_event_or_403(db, code)
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.event_id == event.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    items = [
        {
            "type": a.activity_type.value,
            "summary": a.summary,
            "payload": a.payload_json,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().all()
    ]
    return ok(items)
