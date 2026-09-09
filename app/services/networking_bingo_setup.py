"""Ensure events using the 30-prompt bingo catalog have tasks and assignments."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.networking_bingo_tasks import BINGO_TASK_COUNT, networking_bingo_task_templates
from app.models.enums import EventMode, TaskType
from app.models.event import Event
from app.models.task import Task
from app.services.task_assignment import assign_all_tasks_to_participant, assign_task_to_all_participants


def event_uses_bingo_catalog(event: Event) -> bool:
    """All networking and competition events use the 30 find-someone-who prompts."""
    return event.mode in (EventMode.NETWORKING, EventMode.COMPETITION)


def _is_bingo_prompt(task: Task) -> bool:
    slug = task.slug or ""
    return slug.startswith("bingo-") or bool((task.config_json or {}).get("bingo"))


def _is_legacy_meet_task(task: Task) -> bool:
    slug = (task.slug or "").lower()
    return slug.startswith("meet-")


async def _active_bingo_task_count(db: AsyncSession, event_id: int) -> int:
    result = await db.execute(
        select(Task).where(Task.event_id == event_id, Task.is_active.is_(True))
    )
    return sum(1 for task in result.scalars().all() if _is_bingo_prompt(task))


async def _deactivate_non_bingo_tasks(
    db: AsyncSession, event_id: int, *, only_legacy: bool = True
) -> int:
    """Hide legacy meet-N tasks so human-bingo prompts (including admin extras) show."""
    result = await db.execute(
        select(Task).where(
            Task.event_id == event_id,
            Task.is_active.is_(True),
            ~Task.slug.like("bingo-%"),
        )
    )
    hidden = 0
    for task in result.scalars().all():
        if (task.config_json or {}).get("bingo"):
            continue
        if only_legacy and not _is_legacy_meet_task(task):
            continue
        task.is_active = False
        hidden += 1
    if hidden:
        await db.flush()
    return hidden


async def _promote_custom_tasks_to_bingo(db: AsyncSession, event_id: int) -> int:
    """Keep admin-added prompts on the player board instead of hiding them."""
    result = await db.execute(select(Task).where(Task.event_id == event_id))
    promoted = 0
    for task in result.scalars().all():
        if _is_legacy_meet_task(task):
            continue
        changed = False
        if not _is_bingo_prompt(task):
            config = dict(task.config_json or {})
            config["bingo"] = True
            config.setdefault("category", "ice_breakers")
            task.config_json = config
            task.type = TaskType.SELFIE
            changed = True
        if not task.is_active:
            task.is_active = True
            changed = True
        if changed:
            promoted += 1
    if promoted:
        await db.flush()
    return promoted


async def ensure_networking_bingo_tasks(db: AsyncSession, event: Event) -> int:
    """
    Create bingo tasks on the event if missing. Returns number of active bingo tasks.
    """
    if not event_uses_bingo_catalog(event):
        return await _active_bingo_task_count(db, event.id)

    from app.services.event_settings import get_settings_for_event

    await _deactivate_non_bingo_tasks(db, event.id)
    await _promote_custom_tasks_to_bingo(db, event.id)

    settings = await get_settings_for_event(db, event.id)
    competition_pts = (
        settings.task_completion_points if settings and event.mode == EventMode.COMPETITION else 0
    )

    count = await _active_bingo_task_count(db, event.id)
    if count >= BINGO_TASK_COUNT:
        event.task_count = count
        await db.flush()
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

    count = await _active_bingo_task_count(db, event.id)
    event.task_count = count
    await db.flush()
    return count


async def ensure_participant_bingo_assignments(
    db: AsyncSession, event: Event, participant_id: int
) -> None:
    if not event_uses_bingo_catalog(event):
        return
    await ensure_networking_bingo_tasks(db, event)
    await assign_all_tasks_to_participant(db, event.id, participant_id)
