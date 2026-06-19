import re
import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, EventError
from app.models.enums import EventMode, EventStatus, ParticipantTaskStatus, TaskType
from app.models.event import Event
from app.models.participant import Participant, ParticipantTask
from app.models.task import Task
from app.schemas.task import BulkImportRequest, BulkTaskLine, TaskCreate, TaskUpdate, normalize_title
from app.services.task_assignment import assign_task_to_all_participants
from app.services.task_gallery import selfie_counts_by_task


class TaskError(AppError):
    pass


def slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    if len(base) < 3:
        base = "task"
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    return f"{base}-{suffix}"


async def _ensure_event_editable(db: AsyncSession, event: Event) -> None:
    if event.status == EventStatus.ENDED:
        raise TaskError("EVENT_ENDED", "Cannot modify tasks on an ended event", 400)


async def _duplicate_title_exists(
    db: AsyncSession, event_id: int, title: str, exclude_task_id: int | None = None
) -> bool:
    normalized = normalize_title(title)
    result = await db.execute(select(Task.id, Task.title).where(Task.event_id == event_id))
    for task_id, existing_title in result.all():
        if exclude_task_id and task_id == exclude_task_id:
            continue
        if normalize_title(existing_title) == normalized:
            return True
    return False


async def _next_sort_order(db: AsyncSession, event_id: int) -> int:
    result = await db.scalar(
        select(func.coalesce(func.max(Task.sort_order), -1)).where(Task.event_id == event_id)
    )
    return (result or -1) + 1


async def _sync_event_task_count(db: AsyncSession, event_id: int) -> None:
    count = await db.scalar(
        select(func.count(Task.id)).where(Task.event_id == event_id, Task.is_active.is_(True))
    )
    event = await db.get(Event, event_id)
    if event:
        event.task_count = count or 0
        await db.flush()


async def get_task_stats(db: AsyncSession, task_id: int) -> dict:
    assigned = await db.scalar(
        select(func.count(ParticipantTask.id)).where(ParticipantTask.task_id == task_id)
    )
    completed = await db.scalar(
        select(func.count(ParticipantTask.id)).where(
            ParticipantTask.task_id == task_id,
            ParticipantTask.status == ParticipantTaskStatus.COMPLETED,
        )
    )
    return {"assigned_count": assigned or 0, "completed_count": completed or 0}


async def list_tasks(db: AsyncSession, event_id: int, include_inactive: bool = False) -> list[dict]:
    q = select(Task).where(Task.event_id == event_id).order_by(Task.sort_order, Task.id)
    if not include_inactive:
        q = q.where(Task.is_active.is_(True))
    result = await db.execute(q)
    selfie_counts = await selfie_counts_by_task(db, event_id)
    items = []
    for task in result.scalars().all():
        stats = await get_task_stats(db, task.id)
        items.append(
            {
                "id": task.id,
                "event_id": task.event_id,
                "slug": task.slug,
                "title": task.title,
                "description": task.description,
                "type": task.type,
                "points": task.points,
                "sort_order": task.sort_order,
                "is_required": task.is_required,
                "is_active": task.is_active,
                "selfie_count": selfie_counts.get(task.id, 0),
                **stats,
            }
        )
    return items


async def create_task(
    db: AsyncSession, event: Event, data: TaskCreate, assign: bool = True
) -> Task:
    await _ensure_event_editable(db, event)
    if await _duplicate_title_exists(db, event.id, data.title):
        raise TaskError("DUPLICATE_TASK", f"A task with title '{data.title}' already exists", 409)

    points = data.points
    if event.mode == EventMode.NETWORKING:
        points = 0

    slug = slugify(data.title)
    for _ in range(5):
        existing = await db.execute(
            select(Task.id).where(Task.event_id == event.id, Task.slug == slug)
        )
        if not existing.scalar_one_or_none():
            break
        slug = slugify(data.title)

    task = Task(
        event_id=event.id,
        slug=slug,
        title=data.title,
        description=data.description,
        type=data.type,
        points=points,
        sort_order=await _next_sort_order(db, event.id),
        is_required=data.is_required,
        is_active=data.is_active,
    )
    db.add(task)
    await db.flush()

    if assign and task.is_active:
        await assign_task_to_all_participants(db, event.id, task.id)

    await _sync_event_task_count(db, event.id)
    return task


async def update_task(db: AsyncSession, event: Event, task: Task, data: TaskUpdate) -> Task:
    await _ensure_event_editable(db, event)
    if data.title is not None:
        if await _duplicate_title_exists(db, event.id, data.title, exclude_task_id=task.id):
            raise TaskError("DUPLICATE_TASK", f"A task with title '{data.title}' already exists", 409)
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.type is not None:
        task.type = data.type
    if data.points is not None:
        task.points = 0 if event.mode == EventMode.NETWORKING else data.points
    if data.is_required is not None:
        task.is_required = data.is_required
    if data.is_active is not None:
        was_inactive = not task.is_active
        task.is_active = data.is_active
        if was_inactive and task.is_active:
            await assign_task_to_all_participants(db, event.id, task.id)
    await db.flush()
    await _sync_event_task_count(db, event.id)
    return task


async def delete_task(db: AsyncSession, event: Event, task: Task) -> None:
    await _ensure_event_editable(db, event)
    await db.delete(task)
    await db.flush()
    await _reorder_tasks(db, event.id)
    await _sync_event_task_count(db, event.id)


async def _reorder_tasks(db: AsyncSession, event_id: int) -> None:
    result = await db.execute(
        select(Task).where(Task.event_id == event_id).order_by(Task.sort_order, Task.id)
    )
    for order, task in enumerate(result.scalars().all()):
        task.sort_order = order
    await db.flush()


async def reorder_tasks(db: AsyncSession, event: Event, task_ids: list[int]) -> list[Task]:
    await _ensure_event_editable(db, event)
    result = await db.execute(select(Task).where(Task.event_id == event.id))
    tasks_by_id = {t.id: t for t in result.scalars().all()}

    if set(task_ids) != set(tasks_by_id.keys()):
        raise TaskError("INVALID_REORDER", "task_ids must include every task for this event exactly once", 400)

    for order, task_id in enumerate(task_ids):
        tasks_by_id[task_id].sort_order = order
    await db.flush()
    return sorted(tasks_by_id.values(), key=lambda t: t.sort_order)


def parse_bulk_text(text: str) -> list[BulkTaskLine]:
    lines: list[BulkTaskLine] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            title, desc = line.split("|", 1)
            lines.append(BulkTaskLine(title=title.strip(), description=desc.strip()))
        else:
            lines.append(BulkTaskLine(title=line))
    return lines


async def bulk_import_tasks(
    db: AsyncSession, event: Event, payload: BulkImportRequest
) -> dict:
    await _ensure_event_editable(db, event)
    to_import: list[BulkTaskLine] = []
    if payload.tasks:
        to_import.extend(payload.tasks)
    if payload.text:
        to_import.extend(parse_bulk_text(payload.text))
    if not to_import:
        raise TaskError("EMPTY_IMPORT", "No tasks to import", 400)

    created_tasks: list[Task] = []
    skipped = 0
    errors: list[str] = []

    for i, line in enumerate(to_import, start=1):
        try:
            if await _duplicate_title_exists(db, event.id, line.title):
                skipped += 1
                continue
            task = await create_task(
                db,
                event,
                TaskCreate(
                    title=line.title,
                    description=line.description,
                    type=line.type,
                    points=line.points,
                ),
                assign=True,
            )
            created_tasks.append(task)
        except TaskError as e:
            if e.code == "DUPLICATE_TASK":
                skipped += 1
            else:
                errors.append(f"Line {i}: {e.message}")
        except Exception as e:
            errors.append(f"Line {i}: {str(e)}")

    return {
        "created": len(created_tasks),
        "skipped_duplicates": skipped,
        "tasks": created_tasks,
        "errors": errors,
    }
