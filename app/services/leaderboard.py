import logging
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.enums import EventMode
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.models.leaderboard import Leaderboard
from app.models.participant import Participant
from app.models.task import Task

logger = logging.getLogger(__name__)

LEADERBOARD_PREFIX = "leaderboard:"

# Ranking: 1) score 2) tasks completed 3) earlier finish time (NULL finish = not done yet)
def rank_order_clauses():
    """MySQL-compatible ORDER BY (MySQL does not support NULLS LAST)."""
    return (
        Leaderboard.score.desc(),
        Leaderboard.tasks_completed.desc(),
        case((Leaderboard.finished_at.is_(None), 1), else_=0).asc(),
        Leaderboard.finished_at.asc(),
    )


RANK_ORDER = rank_order_clauses()


async def ensure_leaderboard_entry(
    db: AsyncSession, event_id: int, participant_id: int
) -> Leaderboard:
    result = await db.execute(
        select(Leaderboard).where(
            Leaderboard.event_id == event_id,
            Leaderboard.participant_id == participant_id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry:
        return entry
    entry = Leaderboard(event_id=event_id, participant_id=participant_id)
    db.add(entry)
    await db.flush()
    return entry


async def sync_leaderboard_stats(db: AsyncSession, participant: Participant) -> Leaderboard | None:
    """Mirror participant progress onto leaderboard row."""
    result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = result.scalar_one_or_none()
    if not event or event.mode != EventMode.COMPETITION:
        return None

    entry = await ensure_leaderboard_entry(db, participant.event_id, participant.id)
    entry.tasks_completed = participant.tasks_completed_count
    entry.matches_count = participant.matches_count
    entry.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return entry


async def add_score(
    db: AsyncSession,
    event_id: int,
    participant_id: int,
    delta: int,
    *,
    notify: bool = True,
) -> None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one()
    if event.mode != EventMode.COMPETITION or delta <= 0:
        return

    entry = await ensure_leaderboard_entry(db, event_id, participant_id)
    entry.score += delta
    entry.updated_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        redis = await get_redis()
        await redis.zadd(f"{LEADERBOARD_PREFIX}{event_id}", {str(participant_id): entry.score})
    except Exception as exc:
        logger.warning("Redis leaderboard update skipped: %s", exc)

    await recalculate_ranks(db, event_id, notify=notify)


def _serialize_entry(lb: Leaderboard, p: Participant, *, rank: int | None = None) -> dict:
    return {
        "rank": rank if rank is not None else (lb.rank or 0),
        "participant_id": p.id,
        "display_name": p.display_name,
        "score": lb.score,
        "company": p.company,
        "tasks_completed": lb.tasks_completed,
        "matches_count": lb.matches_count,
        "finished_at": lb.finished_at.isoformat() if lb.finished_at else None,
        "finished_at_dt": lb.finished_at,
        "is_finished": lb.finished_at is not None,
    }


async def get_leaderboard_ordered(
    db: AsyncSession, event_id: int, limit: int | None = None
) -> list[dict]:
    """Full ordered board with dense ranks (ties share rank)."""
    settings_result = await db.execute(
        select(EventSettings).where(EventSettings.event_id == event_id)
    )
    settings = settings_result.scalar_one_or_none()
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one()
    if settings and not settings.leaderboard_enabled and event.mode == EventMode.COMPETITION:
        return []

    if limit is None:
        limit = settings.leaderboard_size if settings else 20

    result = await db.execute(
        select(Participant, Leaderboard)
        .outerjoin(Leaderboard, (Leaderboard.participant_id == Participant.id) & (Leaderboard.event_id == event_id))
        .where(Participant.event_id == event_id, Participant.is_active.is_(True))
        .order_by(
            case((Leaderboard.id.isnot(None), 0), else_=1).asc(),
            *RANK_ORDER
        )
        .limit(limit)
    )
    rows = result.all()
    output: list[dict] = []
    last_key: tuple | None = None
    dense_rank = 0
    for i, (p, lb) in enumerate(rows):
        if lb is None:
            lb = Leaderboard(
                event_id=event_id,
                participant_id=p.id,
                score=0,
                tasks_completed=0,
                matches_count=0,
                finished_at=None,
                rank=None
            )
        key = (lb.score, lb.tasks_completed, lb.finished_at)
        if key != last_key:
            dense_rank = i + 1
            last_key = key
        output.append(_serialize_entry(lb, p, rank=dense_rank))
    return output


async def get_leaderboard(db: AsyncSession, event_id: int, limit: int | None = None) -> list[dict]:
    board = await get_leaderboard_ordered(db, event_id, limit=limit)
    return [
        {k: v for k, v in row.items() if k not in ("finished_at_dt",)}
        for row in board
    ]


async def recalculate_ranks(
    db: AsyncSession, event_id: int, *, notify: bool = True
) -> None:
    result = await db.execute(
        select(Leaderboard).where(Leaderboard.event_id == event_id).order_by(*RANK_ORDER)
    )
    entries = list(result.scalars().all())
    last_key: tuple | None = None
    dense_rank = 0
    for i, entry in enumerate(entries):
        key = (entry.score, entry.tasks_completed, entry.finished_at)
        if key != last_key:
            dense_rank = i + 1
            last_key = key
        entry.rank = dense_rank
    await db.flush()

    if notify:
        event_result = await db.execute(select(Event).where(Event.id == event_id))
        event = event_result.scalar_one()
        if event.mode == EventMode.COMPETITION:
            from app.services.ws_events import emit_leaderboard_updated

            top = await get_leaderboard(db, event_id, limit=10)
            await emit_leaderboard_updated(event_id, top=top)


async def count_finishers(db: AsyncSession, event_id: int) -> int:
    """Participants who completed all required tasks."""
    return int(
        await db.scalar(
            select(func.count(Leaderboard.id)).where(
                Leaderboard.event_id == event_id,
                Leaderboard.finished_at.isnot(None),
            )
        )
        or 0
    )


async def participant_finished_all_tasks(
    db: AsyncSession, participant: Participant
) -> bool:
    result = await db.execute(
        select(Leaderboard.finished_at).where(
            Leaderboard.event_id == participant.event_id,
            Leaderboard.participant_id == participant.id,
        )
    )
    finished_at = result.scalar_one_or_none()
    return finished_at is not None


async def mark_finished(db: AsyncSession, event_id: int, participant_id: int) -> bool:
    """Set finish time once; returns True if newly marked."""
    result = await db.execute(
        select(Leaderboard).where(
            Leaderboard.event_id == event_id,
            Leaderboard.participant_id == participant_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry or entry.finished_at is not None:
        return False
    entry.finished_at = datetime.now(timezone.utc)
    await db.flush()
    await recalculate_ranks(db, event_id, notify=True)
    return True


async def check_and_mark_finished(
    db: AsyncSession, participant: Participant, settings: EventSettings | None
) -> bool:
    """Mark participant finished when all required tasks done or min matches met."""
    total_tasks = await db.scalar(
        select(func.count(Task.id)).where(
            Task.event_id == participant.event_id,
            Task.is_active.is_(True),
            Task.is_required.is_(True),
        )
    )
    completed = participant.tasks_completed_count
    min_matches = settings.min_matches_for_completion if settings else None

    done = False
    if total_tasks and total_tasks > 0 and completed >= total_tasks:
        done = True
    elif min_matches is not None and min_matches > 0 and participant.matches_count >= min_matches:
        done = True

    if not done:
        return False
    return await mark_finished(db, participant.event_id, participant.id)


async def calculate_winner(
    db: AsyncSession, event_id: int
) -> dict | None:
    """Top competitor after full tie-break rules."""
    board = await get_leaderboard_ordered(db, event_id, limit=1)
    if not board:
        return None
    row = board[0]
    return {k: v for k, v in row.items() if k != "finished_at_dt"}


async def calculate_podium(
    db: AsyncSession, event_id: int, *, size: int = 3
) -> list[dict]:
    """Top N with dense ranks (may include ties)."""
    board = await get_leaderboard_ordered(db, event_id, limit=size)
    return [{k: v for k, v in row.items() if k != "finished_at_dt"} for row in board]
