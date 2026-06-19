from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_event
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.event import Event
from app.models.task import Task
from app.schemas.common import ok
from app.schemas.task import (
    BulkImportRequest,
    BulkImportResult,
    TaskCreate,
    TaskOut,
    TaskReorderRequest,
    TaskUpdate,
)
from app.services import tasks as task_service

router = APIRouter()


def _handle_error(exc: AppError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _task_out(task: Task, stats: dict) -> dict:
    return TaskOut(
        id=task.id,
        event_id=task.event_id,
        slug=task.slug,
        title=task.title,
        description=task.description,
        type=task.type,
        points=task.points,
        sort_order=task.sort_order,
        is_required=task.is_required,
        is_active=task.is_active,
        assigned_count=stats.get("assigned_count", 0),
        completed_count=stats.get("completed_count", 0),
    ).model_dump()


@router.get("/events/{event_id}/tasks")
async def list_event_tasks(
    include_inactive: bool = Query(False),
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    items = await task_service.list_tasks(db, event.id, include_inactive)
    return ok(
        [
            TaskOut(
                id=t["id"],
                event_id=t["event_id"],
                slug=t["slug"],
                title=t["title"],
                description=t["description"],
                type=t["type"],
                points=t["points"],
                sort_order=t["sort_order"],
                is_required=t["is_required"],
                is_active=t["is_active"],
                assigned_count=t.get("assigned_count", 0),
                completed_count=t.get("completed_count", 0),
                selfie_count=t.get("selfie_count", 0),
            ).model_dump()
            for t in items
        ]
    )


@router.get("/events/{event_id}/tasks/{task_id}/submissions")
async def task_submissions(
    task_id: int,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    from app.services.task_gallery import get_admin_task_submissions

    data = await get_admin_task_submissions(db, event.id, task_id)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")
    return ok(data)


@router.post("/events/{event_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await task_service.create_task(db, event, body)
        stats = await task_service.get_task_stats(db, task.id)
    except AppError as e:
        raise _handle_error(e) from e
    return ok(_task_out(task, stats))


@router.patch("/events/{event_id}/tasks/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(db, event.id, task_id)
    try:
        task = await task_service.update_task(db, event, task, body)
        stats = await task_service.get_task_stats(db, task.id)
    except AppError as e:
        raise _handle_error(e) from e
    return ok(_task_out(task, stats))


@router.delete("/events/{event_id}/tasks/{task_id}")
async def delete_task(
    task_id: int,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(db, event.id, task_id)
    try:
        await task_service.delete_task(db, event, task)
    except AppError as e:
        raise _handle_error(e) from e
    return ok({"deleted": True, "task_id": task_id})


@router.put("/events/{event_id}/tasks/reorder")
async def reorder_tasks(
    body: TaskReorderRequest,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    try:
        tasks = await task_service.reorder_tasks(db, event, body.task_ids)
    except AppError as e:
        raise _handle_error(e) from e
    out = []
    for task in tasks:
        stats = await task_service.get_task_stats(db, task.id)
        out.append(_task_out(task, stats))
    return ok(out)


@router.post("/events/{event_id}/tasks/bulk-import")
async def bulk_import(
    body: BulkImportRequest,
    event: Event = Depends(get_admin_event),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await task_service.bulk_import_tasks(db, event, body)
    except AppError as e:
        raise _handle_error(e) from e

    task_outs = []
    for task in result["tasks"]:
        stats = await task_service.get_task_stats(db, task.id)
        task_outs.append(_task_out(task, stats))

    return ok(
        BulkImportResult(
            created=result["created"],
            skipped_duplicates=result["skipped_duplicates"],
            tasks=task_outs,
            errors=result["errors"],
        ).model_dump()
    )


async def _get_task(db: AsyncSession, event_id: int, task_id: int) -> Task:
    from sqlalchemy import select

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.event_id == event_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task
