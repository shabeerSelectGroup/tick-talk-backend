"""Admin pre-registration and shared participant creation."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import EventMode, EventStatus
from app.models.event import Event
from app.models.participant import Participant
from app.services.badge import generate_secure_badge_token
from app.services.session import generate_token, session_is_active
from app.services.task_assignment import assign_all_tasks_to_participant


class RegistrationError(AppError):
    pass


def _normalize_name(name: str) -> str:
    return name.strip()


async def _count_active_participants(db: AsyncSession, event_id: int) -> int:
    count = await db.scalar(
        select(func.count(Participant.id)).where(
            Participant.event_id == event_id, Participant.is_active.is_(True)
        )
    )
    return int(count or 0)


async def find_existing_by_email(
    db: AsyncSession, event_id: int, email: str
) -> Participant | None:
    if not email or not email.strip():
        return None
    normalized = email.strip().lower()
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event_id,
            Participant.is_active.is_(True),
            func.lower(Participant.email) == normalized,
        )
    )
    return result.scalar_one_or_none()


async def _ensure_can_add_participant(db: AsyncSession, event: Event) -> None:
    if event.status == EventStatus.ENDED:
        raise RegistrationError(
            "EVENT_ENDED",
            "Cannot add participants to an ended event.",
            403,
        )
    if event.max_participants is not None:
        count = await _count_active_participants(db, event.id)
        if count >= event.max_participants:
            raise RegistrationError(
                "EVENT_FULL",
                "This event is at capacity.",
                403,
            )


async def find_unclaimed_by_display_name(
    db: AsyncSession, event_id: int, display_name: str
) -> Participant | None:
    """Participant pre-registered by admin who has not signed in on a device yet."""
    normalized = _normalize_name(display_name).lower()
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event_id,
            Participant.is_active.is_(True),
            func.lower(Participant.display_name) == normalized,
        )
    )
    candidates = result.scalars().all()
    unclaimed = []
    for p in candidates:
        if not await session_is_active(p.session_token):
            unclaimed.append(p)
    if len(unclaimed) == 1:
        return unclaimed[0]
    return None


async def create_participant_record(
    db: AsyncSession,
    event: Event,
    display_name: str,
    email: str | None = None,
    company: str | None = None,
) -> Participant:
    participant = Participant(
        event_id=event.id,
        session_token=generate_token(),
        qr_code=generate_secure_badge_token(),
        display_name=_normalize_name(display_name),
        email=email.strip().lower() if email else None,
        company=company.strip() if company else None,
    )
    db.add(participant)
    await db.flush()
    await assign_all_tasks_to_participant(db, event.id, participant.id)
    if event.mode == EventMode.COMPETITION:
        from app.services.leaderboard import ensure_leaderboard_entry

        await ensure_leaderboard_entry(db, event.id, participant.id)
    await db.flush()
    return participant


async def admin_register_participant(
    db: AsyncSession,
    event: Event,
    display_name: str,
    email: str | None = None,
    company: str | None = None,
) -> Participant:
    await _ensure_can_add_participant(db, event)

    name = _normalize_name(display_name)
    if len(name) < 2:
        raise RegistrationError(
            "INVALID_NAME",
            "Display name must be at least 2 characters.",
            422,
        )

    if email:
        existing = await find_existing_by_email(db, event.id, email)
        if existing:
            raise RegistrationError(
                "EMAIL_ALREADY_REGISTERED",
                "A participant with this email is already on the roster.",
                409,
            )
    else:
        existing = await find_unclaimed_by_display_name(db, event.id, name)
        if existing:
            raise RegistrationError(
                "NAME_ALREADY_REGISTERED",
                f"{name} is already on the roster. Add an email to register another person with the same name.",
                409,
            )

    return await create_participant_record(db, event, name, email, company)


def parse_bulk_names(text: str) -> list[dict[str, str | None]]:
    """One person per line: Name | email | company (email and company optional)."""
    entries: list[dict[str, str | None]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        display_name = parts[0]
        if len(display_name) < 2:
            continue
        email = parts[1] if len(parts) > 1 and parts[1] else None
        company = parts[2] if len(parts) > 2 and parts[2] else None
        entries.append(
            {"display_name": display_name, "email": email or None, "company": company or None}
        )
    return entries


async def admin_register_participants_bulk(
    db: AsyncSession,
    event: Event,
    text: str,
) -> dict:
    entries = parse_bulk_names(text)
    if not entries:
        raise RegistrationError(
            "EMPTY_ROSTER",
            "Add at least one name (one per line).",
            422,
        )

    created: list[dict] = []
    skipped: list[dict] = []
    for entry in entries:
        try:
            p = await admin_register_participant(
                db,
                event,
                entry["display_name"],
                entry.get("email"),
                entry.get("company"),
            )
            created.append(
                {
                    "id": p.id,
                    "display_name": p.display_name,
                    "email": p.email,
                    "company": p.company,
                }
            )
        except RegistrationError as e:
            skipped.append(
                {
                    "display_name": entry["display_name"],
                    "code": e.code,
                    "message": e.message,
                }
            )

    return {"created": created, "skipped": skipped, "created_count": len(created)}
