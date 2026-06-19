"""Replace event tasks with 30 networking bingo challenges.

Usage:
  PYTHONPATH=. python -m scripts.install_bingo_tasks DEMO2026
  PYTHONPATH=. python -m scripts.install_bingo_tasks COMP2026 --competition
  PYTHONPATH=. python -m scripts.install_bingo_tasks DEMO2026 --live
"""

import asyncio
import sys

from sqlalchemy import select

from app.data.networking_bingo_tasks import BINGO_TASK_COUNT, networking_bingo_task_templates
from app.db.session import async_session_factory
from app.models.enums import EventMode, EventStatus
from app.models.event import Event
from app.models.task import Task
from app.services.networking_bingo_setup import _deactivate_non_bingo_tasks
from app.services.task_assignment import assign_task_to_all_participants


async def install(
    db,
    event_code: str,
    *,
    keep_competition: bool = False,
    go_live: bool = False,
) -> None:
    event = await db.scalar(select(Event).where(Event.code == event_code.upper()))
    if not event:
        print(f"Event {event_code} not found")
        return

    if not keep_competition and event.mode != EventMode.COMPETITION:
        event.mode = EventMode.NETWORKING
    event.task_count = BINGO_TASK_COUNT
    if go_live:
        event.status = EventStatus.LIVE

    await _deactivate_non_bingo_tasks(db, event.id)

    by_slug = {
        t.slug: t
        for t in (
            await db.execute(select(Task).where(Task.event_id == event.id))
        ).scalars().all()
    }

    templates = networking_bingo_task_templates()
    assert len(templates) == BINGO_TASK_COUNT

    for order, tmpl in enumerate(templates):
        slug = tmpl["slug"]
        existing = by_slug.get(slug)
        if existing:
            existing.title = tmpl["title"]
            existing.description = tmpl["description"]
            existing.type = tmpl["type"]
            existing.points = 0
            existing.sort_order = order
            existing.is_required = True
            existing.is_active = True
            existing.config_json = tmpl.get("config_json")
        else:
            db.add(
                Task(
                    event_id=event.id,
                    slug=slug,
                    title=tmpl["title"],
                    description=tmpl["description"],
                    type=tmpl["type"],
                    points=0,
                    sort_order=order,
                    is_required=True,
                    is_active=True,
                    config_json=tmpl.get("config_json"),
                )
            )
    await db.flush()

    active_bingo = (
        await db.execute(
            select(Task).where(
                Task.event_id == event.id,
                Task.is_active.is_(True),
                Task.slug.like("bingo-%"),
            )
        )
    ).scalars().all()
    for task in active_bingo:
        await assign_task_to_all_participants(db, event.id, task.id)

    mode_label = event.mode.value
    print(f"Bingo catalog ready on {event.code} ({mode_label}): {len(active_bingo)} active tasks")


async def main() -> None:
    args = [a for a in sys.argv[1:] if a.startswith("--")]
    codes = [a for a in sys.argv[1:] if not a.startswith("--")]
    code = codes[0] if codes else "DEMO2026"
    keep_competition = "--competition" in args
    go_live = "--live" in args
    async with async_session_factory() as db:
        await install(db, code, keep_competition=keep_competition, go_live=go_live)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
