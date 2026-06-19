import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventStatus
from app.models.event import Event
from app.models.participant import Participant


def generate_event_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def list_events(db: AsyncSession, status: EventStatus | None = None) -> list[Event]:
    q = select(Event).order_by(Event.created_at.desc())
    if status:
        q = q.where(Event.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_event_by_id(db: AsyncSession, event_id: int) -> Event | None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def get_event_by_code(db: AsyncSession, code: str) -> Event | None:
    result = await db.execute(select(Event).where(Event.code == code.upper()))
    return result.scalar_one_or_none()


async def get_event_stats(db: AsyncSession, event_id: int) -> dict:
    result = await db.execute(
        select(func.count(Participant.id)).where(
            Participant.event_id == event_id, Participant.is_active.is_(True)
        )
    )
    count = result.scalar() or 0
    return {"participant_count": count}
