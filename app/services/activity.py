from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.enums import ActivityType
from app.services.websocket import broadcast_event


async def log_activity(
    db: AsyncSession,
    event_id: int,
    activity_type: ActivityType | str,
    participant_id: int | None = None,
    payload: dict | None = None,
    summary: str | None = None,
) -> ActivityLog:
    if isinstance(activity_type, str):
        activity_type = ActivityType(activity_type)

    entry = ActivityLog(
        event_id=event_id,
        participant_id=participant_id,
        activity_type=activity_type,
        summary=summary,
        payload_json=payload,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    await broadcast_event(
        event_id,
        {
            "type": "activity",
            "payload": {
                "id": entry.id,
                "activity_type": activity_type.value,
                "participant_id": participant_id,
                "summary": summary,
                "data": payload,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            },
        },
    )
    return entry
