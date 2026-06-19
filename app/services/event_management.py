from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import EventError
from app.models.enums import EventMode, EventStatus, TaskType
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.models.task import Task
from app.schemas.event import EventCreateRequest, EventSettingsInput, EventUpdateRequest
from app.services.events import generate_event_code, get_event_by_code
from app.services.qr import generate_qr_data_url
from app.data.networking_bingo_tasks import BINGO_TASK_COUNT, networking_bingo_task_templates
from app.services.task_presenter import MEET_CHALLENGE_SUMMARY, MEET_PERSON_DESCRIPTION

# Ordered task templates — meet-N expands into N separate selfie tasks
TASK_TEMPLATES: list[dict] = [
    {
        "slug": "intro",
        "title": "Introduction",
        "description": "Complete your profile and say hello",
        "type": TaskType.MANUAL,
        "points": 10,
    },
    {
        "slug": "meet-3",
        "title": "Meet 3 People",
        "description": MEET_CHALLENGE_SUMMARY,
        "type": TaskType.SELFIE,
        "points": 30,
    },
    {
        "slug": "meet-5",
        "title": "Meet 5 People",
        "description": "Meet 5 different people. Take a selfie with each person you connect with.",
        "type": TaskType.SELFIE,
        "points": 50,
    },
    {
        "slug": "team-selfie",
        "title": "Team Selfie",
        "description": "Take a selfie with your networking group",
        "type": TaskType.SELFIE,
        "points": 25,
    },
    {
        "slug": "icebreaker",
        "title": "Icebreaker Challenge",
        "description": "Complete the icebreaker conversation prompt",
        "type": TaskType.MANUAL,
        "points": 15,
    },
    {
        "slug": "department-connect",
        "title": "Cross-Department Connect",
        "description": MEET_PERSON_DESCRIPTION,
        "type": TaskType.SELFIE,
        "points": 20,
    },
    {
        "slug": "quiz-warmup",
        "title": "Event Quiz",
        "description": "Answer the event trivia questions",
        "type": TaskType.QUIZ,
        "points": 20,
    },
    {
        "slug": "final-reflection",
        "title": "Final Reflection",
        "description": "Submit your event takeaway",
        "type": TaskType.MANUAL,
        "points": 10,
    },
]


def build_join_url(event_code: str) -> str:
    base = get_settings().app_public_url.rstrip("/")
    return f"{base}/join/{event_code.upper()}"


async def generate_unique_event_code(db: AsyncSession, length: int = 8, max_attempts: int = 10) -> str:
    for _ in range(max_attempts):
        code = generate_event_code(length)
        if not await get_event_by_code(db, code):
            return code
    raise EventError("CODE_GENERATION_FAILED", "Could not generate a unique event code", 500)


def _apply_settings_to_model(settings: EventSettings, input_settings: EventSettingsInput, mode: EventMode) -> None:
    from app.services.event_mode import apply_networking_settings_defaults

    settings.leaderboard_enabled = input_settings.leaderboard_enabled
    settings.enable_awards = input_settings.enable_awards
    settings.show_live_ranking = input_settings.show_live_ranking
    settings.show_ranking_only_at_end = input_settings.show_ranking_only_at_end
    settings.enable_selfie_verification = input_settings.enable_selfie_verification
    settings.enable_public_wall = input_settings.enable_public_wall
    settings.scan_match_points = input_settings.scan_match_points
    settings.task_completion_points = input_settings.task_completion_points
    settings.speed_bonus_enabled = input_settings.speed_bonus_enabled
    settings.speed_bonus_max_points = input_settings.speed_bonus_max_points
    settings.speed_bonus_window_seconds = input_settings.speed_bonus_window_seconds
    settings.selfie_requires_approval = input_settings.enable_selfie_verification
    settings.show_scores_on_wall = (
        input_settings.show_live_ranking and mode == EventMode.COMPETITION
    )
    if mode == EventMode.NETWORKING:
        apply_networking_settings_defaults(settings)
    elif mode == EventMode.COMPETITION:
        from app.services.event_mode import apply_competition_settings_defaults

        apply_competition_settings_defaults(settings)


def _expand_meet_templates(templates: list[dict]) -> list[dict]:
    """Turn meet-3 / meet-5 into separate tasks (one selfie each)."""
    import re

    meet_slug = re.compile(r"^meet-(\d+)$", re.IGNORECASE)
    expanded: list[dict] = []
    for tmpl in templates:
        slug = tmpl.get("slug") or ""
        m = meet_slug.match(slug)
        if not m:
            expanded.append(tmpl)
            continue
        total = max(1, int(m.group(1)))
        base_points = tmpl.get("points", 10)
        per_task = max(1, base_points // total) if base_points else 0
        for i in range(1, total + 1):
            expanded.append(
                {
                    "slug": f"meet-person-{i}-of-{total}",
                    "title": f"Meet someone new ({i} of {total})",
                    "description": MEET_PERSON_DESCRIPTION,
                    "type": TaskType.SELFIE,
                    "points": per_task,
                }
            )
    return expanded


def _build_task_templates(task_count: int) -> list[dict]:
    templates = _expand_meet_templates(list(TASK_TEMPLATES))
    n = 1
    while len(templates) < task_count:
        templates.append(
            {
                "slug": f"networking-{n}",
                "title": f"Networking Challenge {n}",
                "description": MEET_PERSON_DESCRIPTION,
                "type": TaskType.SELFIE,
                "points": 10 + (n % 5) * 5,
            }
        )
        n += 1
    return templates[:task_count]


async def _create_tasks_for_event(
    db: AsyncSession, event: Event, task_count: int, mode: EventMode
) -> int:
    if mode in (EventMode.NETWORKING, EventMode.COMPETITION):
        templates = networking_bingo_task_templates()
    else:
        templates = _build_task_templates(task_count)
    created = 0
    for order, tmpl in enumerate(templates):
        is_bingo = bool((tmpl.get("config_json") or {}).get("bingo"))
        if mode == EventMode.NETWORKING:
            points = 0
        elif mode == EventMode.COMPETITION and is_bingo:
            points = 100
        elif tmpl["type"] == TaskType.SELFIE:
            points = 100
        else:
            points = tmpl["points"]
        db.add(
            Task(
                event_id=event.id,
                slug=tmpl["slug"],
                title=tmpl["title"],
                description=tmpl["description"],
                type=tmpl["type"],
                points=points,
                sort_order=order,
                is_required=True,
                is_active=True,
                config_json=tmpl.get("config_json"),
            )
        )
        created += 1
    await db.flush()
    return created


async def create_event_managed(
    db: AsyncSession, data: EventCreateRequest, admin_id: int
) -> dict:
    code = await generate_unique_event_code(db)
    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(minutes=data.duration_minutes)

    task_count = BINGO_TASK_COUNT if data.mode == EventMode.COMPETITION else data.task_count

    event = Event(
        code=code,
        name=data.name.strip(),
        description=data.description,
        mode=data.mode,
        status=EventStatus.SCHEDULED,
        starts_at=now,
        ends_at=ends_at,
        timezone=data.timezone,
        max_participants=data.max_participants,
        task_count=task_count,
        created_by=admin_id,
    )
    db.add(event)
    await db.flush()

    settings = EventSettings(
        event_id=event.id,
        duration_minutes=data.duration_minutes,
    )
    _apply_settings_to_model(settings, data.settings, data.mode)
    db.add(settings)
    await db.flush()

    tasks_created = await _create_tasks_for_event(db, event, task_count, data.mode)

    join_url = build_join_url(code)
    qr_code_data_url = generate_qr_data_url(join_url)

    return {
        "event": event,
        "settings": settings,
        "join_url": join_url,
        "qr_code_data_url": qr_code_data_url,
        "tasks_created": tasks_created,
    }


async def get_event_detail(db: AsyncSession, event: Event) -> dict:
    result = await db.execute(
        select(Event)
        .where(Event.id == event.id)
        .options(selectinload(Event.settings), selectinload(Event.tasks))
    )
    loaded = result.scalar_one()
    settings = loaded.settings
    join_url = build_join_url(loaded.code)
    qr_code_data_url = generate_qr_data_url(join_url)

    from app.models.participant import Participant

    participant_count = await db.scalar(
        select(func.count(Participant.id)).where(
            Participant.event_id == loaded.id, Participant.is_active.is_(True)
        )
    ) or 0

    return {
        "event": loaded,
        "settings": settings,
        "join_url": join_url,
        "qr_code_data_url": qr_code_data_url,
        "participant_count": participant_count,
        "tasks_count": len(loaded.tasks),
    }


async def update_event_managed(
    db: AsyncSession, event: Event, data: EventUpdateRequest
) -> Event:
    if data.name is not None:
        event.name = data.name.strip()
    if data.description is not None:
        event.description = data.description
    if data.mode is not None:
        event.mode = data.mode
    if data.status is not None:
        event.status = data.status
    if data.max_participants is not None:
        event.max_participants = data.max_participants
    if data.task_count is not None:
        event.task_count = data.task_count

    if data.duration_minutes is not None:
        now = datetime.now(timezone.utc)
        event.starts_at = event.starts_at or now
        event.ends_at = (event.starts_at or now) + timedelta(minutes=data.duration_minutes)

    result = await db.execute(select(EventSettings).where(EventSettings.event_id == event.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = EventSettings(event_id=event.id)
        db.add(settings)
        await db.flush()

    if data.duration_minutes is not None:
        settings.duration_minutes = data.duration_minutes
    if data.settings is not None:
        _apply_settings_to_model(settings, data.settings, event.mode)

    await db.flush()
    return event
