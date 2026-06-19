"""Split legacy meet-3 / meet-5 tasks into separate per-person tasks for an event.

Usage: PYTHONPATH=. python -m scripts.split_meet_tasks DEMO2026
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.enums import TaskType
from app.models.event import Event
from app.models.participant import Participant, ParticipantTask
from app.models.task import Task
from app.services.task_assignment import assign_task_to_all_participants
from app.services.task_presenter import MEET_PERSON_DESCRIPTION


async def split_event(db, event_code: str) -> None:
    event = await db.scalar(select(Event).where(Event.code == event_code.upper()))
    if not event:
        print(f"Event {event_code} not found")
        return

    legacy = (
        await db.execute(
            select(Task).where(
                Task.event_id == event.id,
                Task.slug.in_(["meet-3", "meet-5"]),
                Task.is_active.is_(True),
            )
        )
    ).scalars().all()

    if not legacy:
        print("No legacy meet-3/meet-5 tasks to split.")
        return

    for old in legacy:
        m = old.slug.split("-")
        total = int(m[1]) if len(m) == 2 and m[1].isdigit() else 3
        print(f"Splitting {old.slug} ({old.title}) into {total} tasks…")
        old.is_active = False

        for i in range(1, total + 1):
            exists = await db.scalar(
                select(Task.id).where(
                    Task.event_id == event.id,
                    Task.slug == f"meet-person-{i}-of-{total}",
                )
            )
            if exists:
                continue
            new_task = Task(
                event_id=event.id,
                slug=f"meet-person-{i}-of-{total}",
                title=f"Meet someone new ({i} of {total})",
                description=MEET_PERSON_DESCRIPTION,
                type=TaskType.SELFIE,
                points=old.points // total if old.points else 0,
                sort_order=old.sort_order + i - 1,
                is_required=old.is_required,
                is_active=True,
            )
            db.add(new_task)
            await db.flush()
            await assign_task_to_all_participants(db, event.id, new_task.id)

        # Deactivate old participant_tasks for legacy task
        pts = (
            await db.execute(
                select(ParticipantTask).where(ParticipantTask.task_id == old.id)
            )
        ).scalars().all()
        for pt in pts:
            pt.status = pt.status  # keep history; task inactive hides from new joins

    await db.commit()
    print("Done.")


async def main() -> None:
    code = sys.argv[1] if len(sys.argv) > 1 else "DEMO2026"
    async with async_session_factory() as db:
        await split_event(db, code)


if __name__ == "__main__":
    asyncio.run(main())
