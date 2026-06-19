"""Participant join flow: validation, duplicates, session, badge."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import EventMode, EventStatus
from app.models.event import Event
from app.models.participant import Participant
from app.services.events import get_event_by_code
from app.services.badge import build_badge_data
from app.services.participant_registration import (
    create_participant_record,
    find_existing_by_email,
    find_unclaimed_by_display_name,
)
from app.services.session import generate_token, invalidate_session, store_session


class JoinError(AppError):
    pass


async def validate_event_for_join(db: AsyncSession, event_code: str) -> Event:
    event = await get_event_by_code(db, event_code)
    if not event:
        raise JoinError("EVENT_NOT_FOUND", "This event does not exist. Check the QR code or link.", 404)

    if event.status == EventStatus.ENDED:
        raise JoinError("EVENT_ENDED", "This event has ended. Thanks for participating!", 403)
    if event.status not in (EventStatus.DRAFT, EventStatus.SCHEDULED, EventStatus.LIVE):
        raise JoinError("EVENT_NOT_OPEN", "This event is not accepting new participants.", 403)

    if event.max_participants is not None:
        count = await db.scalar(
            select(func.count(Participant.id)).where(
                Participant.event_id == event.id, Participant.is_active.is_(True)
            )
        )
        if count is not None and count >= event.max_participants:
            raise JoinError("EVENT_FULL", "This event is full. Contact the organizer.", 403)

    return event


async def resume_participant_session(
    db: AsyncSession, participant: Participant, event: Event
) -> dict:
    """Re-issue session for returning participant (same email)."""
    if participant.session_token:
        await invalidate_session(participant.session_token)
    participant.session_token = generate_token()
    from datetime import datetime, timezone

    participant.last_active_at = datetime.now(timezone.utc)
    await db.flush()
    await store_session(participant.session_token, participant.id)
    return _build_join_result(participant, event, resumed=True)


async def join_participant(
    db: AsyncSession,
    event_code: str,
    display_name: str,
    email: str | None = None,
    company: str | None = None,
) -> dict:
    event = await validate_event_for_join(db, event_code.upper())

    if email:
        existing = await find_existing_by_email(db, event.id, email)
        if existing:
            if existing.display_name.strip().lower() != display_name.strip().lower():
                raise JoinError(
                    "EMAIL_ALREADY_REGISTERED",
                    "This email is already registered for this event under a different name.",
                    409,
                )
            return await resume_participant_session(db, existing, event)
    else:
        unclaimed = await find_unclaimed_by_display_name(db, event.id, display_name)
        if unclaimed:
            return await resume_participant_session(db, unclaimed, event)

    participant = await create_participant_record(
        db,
        event,
        display_name,
        email,
        company,
    )
    if event.mode == EventMode.NETWORKING:
        from app.services.networking_bingo_setup import ensure_participant_bingo_assignments

        await ensure_participant_bingo_assignments(db, event, participant.id)
    await store_session(participant.session_token, participant.id)
    return _build_join_result(participant, event, resumed=False)


def _build_join_result(participant: Participant, event: Event, resumed: bool) -> dict:
    badge = build_badge_data(participant, event)
    return {
        "participant": participant,
        "event": event,
        "session_token": participant.session_token,
        "event_code": event.code,
        "participant_id": badge.participant_id,
        "event_id": badge.event_id,
        "qr_code": badge.secure_token,
        "qr_payload": badge.qr_payload,
        "qr_code_data_url": badge.qr_code_data_url,
        "resumed": resumed,
    }
