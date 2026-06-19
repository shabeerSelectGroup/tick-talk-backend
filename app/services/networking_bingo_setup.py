"""Ensure events using the 30-prompt bingo catalog have tasks and assignments."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.networking_bingo_tasks import BINGO_TASK_COUNT, networking_bingo_task_templates
from app.models.enums import EventMode
from app.models.event import Event
from app.models.task import Task
from app.services.task_assignment import assign_all_tasks_to_participant, assign_task_to_all_participants


def event_uses_bingo_catalog(event: Event) -> bool:
    """All networking and competition events use the 30 find-someone-who prompts."""
    return event.mode in (EventMode.NETWORKING, EventMode.COMPETITION)


async def _active_bingo_task_count(db: AsyncSession, event_id: int) -> int:
    result = await db.execute(
        select(func.count(Task.id)).where(
            Task.event_id == event_id,
            Task.is_active.is_(True),
            Task.slug.like("bingo-%"),
        )
    )
    return int(result.scalar() or 0)


async def _deactivate_non_bingo_tasks(db: AsyncSession, event_id: int) -> int:
    """Hide legacy meet-N / competition tasks so only human-bingo prompts show."""
    result = await db.execute(
        select(Task).where(
            Task.event_id == event_id,
            Task.is_active.is_(True),
            ~Task.slug.like("bingo-%"),
        )
    )
    legacy = list(result.scalars().all())
    for task in legacy:
        task.is_active = False
    if legacy:
        await db.flush()
    return len(legacy)


async def ensure_networking_bingo_tasks(db: AsyncSession, event: Event) -> int:
    """
    Create bingo tasks on the event if missing. Returns number of active bingo tasks.
    """
    if not event_uses_bingo_catalog(event):
        return await _active_bingo_task_count(db, event.id)

    from app.services.event_settings import get_settings_for_event

    await _deactivate_non_bingo_tasks(db, event.id)
    event.task_count = BINGO_TASK_COUNT

    settings = await get_settings_for_event(db, event.id)
    competition_pts = (
        settings.task_completion_points if settings and event.mode == EventMode.COMPETITION else 0
    )

    count = await _active_bingo_task_count(db, event.id)
    if count >= BINGO_TASK_COUNT:
        return count

    by_slug = {
        t.slug: t
        for t in (
            await db.execute(select(Task).where(Task.event_id == event.id))
        ).scalars().all()
    }

    templates = networking_bingo_task_templates()
    created = 0
    for order, tmpl in enumerate(templates):
        slug = tmpl["slug"]
        existing = by_slug.get(slug)
        task_points = competition_pts if event.mode == EventMode.COMPETITION else 0
        if existing:
            existing.title = tmpl["title"]
            existing.description = tmpl["description"]
            existing.type = tmpl["type"]
            existing.points = task_points
            existing.sort_order = order
            existing.is_required = True
            existing.is_active = True
            existing.config_json = tmpl.get("config_json")
            continue
        db.add(
            Task(
                event_id=event.id,
                slug=slug,
                title=tmpl["title"],
                description=tmpl["description"],
                type=tmpl["type"],
                points=task_points,
                sort_order=order,
                is_required=True,
                is_active=True,
                config_json=tmpl.get("config_json"),
            )
        )
        created += 1
    await db.flush()

    if created:
        new_tasks = (
            await db.execute(
                select(Task).where(
                    Task.event_id == event.id,
                    Task.is_active.is_(True),
                    Task.slug.like("bingo-%"),
                )
            )
        ).scalars().all()
        for task in new_tasks:
            await assign_task_to_all_participants(db, event.id, task.id)

    return await _active_bingo_task_count(db, event.id)


async def ensure_participant_bingo_assignments(
    db: AsyncSession, event: Event, participant_id: int
) -> None:
    if not event_uses_bingo_catalog(event):
        return
    await ensure_networking_bingo_tasks(db, event)
    await assign_all_tasks_to_participant(db, event.id, participant_id)
