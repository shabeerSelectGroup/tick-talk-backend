"""Competition awards: podium and winner calculation on event end."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.award import Award
from app.models.event_settings import EventSettings
from app.models.participant import Participant
from app.services.leaderboard import get_leaderboard_ordered


async def clear_event_awards(db: AsyncSession, event_id: int) -> None:
    await db.execute(delete(Award).where(Award.event_id == event_id))


async def calculate_awards(
    db: AsyncSession,
    event_id: int,
    *,
    podium_size: int = 3,
) -> list[dict]:
    """
    Persist podium awards for top N by ranking rules.
    Returns serialized award rows.
    """
    settings_result = await db.execute(
        select(EventSettings).where(EventSettings.event_id == event_id)
    )
    settings = settings_result.scalar_one_or_none()
    if not settings or not settings.enable_awards:
        return []

    await clear_event_awards(db, event_id)
    ordered = await get_leaderboard_ordered(db, event_id, limit=podium_size)
    if not ordered:
        return []

    for row in ordered:
        finished_dt = row.get("finished_at_dt")
        db.add(
            Award(
                event_id=event_id,
                participant_id=row["participant_id"],
                place=row["rank"],
                award_type="winner" if row["rank"] == 1 else "podium",
                score=row["score"],
                tasks_completed=row["tasks_completed"],
                finished_at=finished_dt,
                metadata_json={
                    "display_name": row["display_name"],
                    "company": row.get("company"),
                },
            )
        )
    await db.flush()
    return await list_awards(db, event_id)


async def list_awards(db: AsyncSession, event_id: int) -> list[dict]:
    result = await db.execute(
        select(Award, Participant)
        .join(Participant, Award.participant_id == Participant.id)
        .where(Award.event_id == event_id)
        .order_by(Award.place, Award.id)
    )
    return [
        {
            "id": a.id,
            "place": a.place,
            "award_type": a.award_type,
            "participant_id": p.id,
            "display_name": p.display_name,
            "company": p.company,
            "score": a.score,
            "tasks_completed": a.tasks_completed,
            "finished_at": a.finished_at.isoformat() if a.finished_at else None,
        }
        for a, p in result.all()
    ]
