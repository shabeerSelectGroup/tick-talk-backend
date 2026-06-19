"""Networking task completion: scan → validate → selfie → complete."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import (
    EventStatus,
    MatchType,
    ParticipantTaskStatus,
    SelfieStatus,
    TaskType,
)
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.models.match import Match
from app.models.participant import Participant, ParticipantTask
from app.models.selfie import Selfie
from app.models.task import Task
from app.services.badge import BadgeError, resolve_participant_from_badge, validate_badge_for_scanner
from app.services.leaderboard import add_score
from app.services.progress import refresh_participant_progress
from app.services.scoring import calculate_task_completion_score
from app.services.task_presenter import meet_target_count
from app.models.enums import EventMode


class TaskCompletionError(AppError):
    pass


def _flow_meta(participant_task: ParticipantTask) -> dict[str, Any]:
    raw = participant_task.metadata_json or {}
    return dict(raw.get("flow") or {})


def _set_flow_meta(participant_task: ParticipantTask, flow: dict[str, Any]) -> None:
    raw = dict(participant_task.metadata_json or {})
    raw["flow"] = flow
    participant_task.metadata_json = raw


async def assert_event_active(db: AsyncSession, event_id: int) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise TaskCompletionError("EVENT_NOT_FOUND", "Event not found.", 404)
    if event.status == EventStatus.DRAFT:
        raise TaskCompletionError(
            "EVENT_NOT_OPEN",
            "This event is not open yet. Wait for the host to go live.",
            403,
        )
    if event.status == EventStatus.ENDED:
        raise TaskCompletionError(
            "EVENT_ENDED",
            "This event has ended.",
            403,
        )
    return event


async def get_participant_task(
    db: AsyncSession, participant: Participant, participant_task_id: int
) -> tuple[ParticipantTask, Task]:
    result = await db.execute(
        select(ParticipantTask, Task)
        .join(Task, ParticipantTask.task_id == Task.id)
        .where(
            ParticipantTask.id == participant_task_id,
            ParticipantTask.participant_id == participant.id,
            Task.event_id == participant.event_id,
            Task.is_active.is_(True),
        )
    )
    row = result.one_or_none()
    if not row:
        raise TaskCompletionError("TASK_NOT_FOUND", "Task not found.", 404)
    return row[0], row[1]


def task_uses_selfie_flow(task: Task) -> bool:
    """Tasks completed by uploading a selfie (no QR scan)."""
    if task.type in (TaskType.SCAN, TaskType.SELFIE):
        return True
    return task.type == TaskType.MANUAL and bool((task.config_json or {}).get("bingo"))


def assert_task_not_completed(participant_task: ParticipantTask) -> None:
    if participant_task.status == ParticipantTaskStatus.COMPLETED:
        raise TaskCompletionError(
            "TASK_ALREADY_COMPLETED",
            "You have already completed this task.",
            409,
        )


async def assert_partner_not_used(
    db: AsyncSession, event_id: int, initiator_id: int, partner_id: int
) -> None:
    existing = await db.execute(
        select(Match.id).where(
            Match.event_id == event_id,
            Match.initiator_id == initiator_id,
            Match.partner_id == partner_id,
        )
    )
    if existing.scalar_one_or_none():
        raise TaskCompletionError(
            "PARTNER_ALREADY_SCANNED",
            "You have already connected with this participant. Scan someone new.",
            409,
        )


async def validate_scan_for_task(
    db: AsyncSession,
    participant: Participant,
    participant_task: ParticipantTask,
    task: Task,
    qr_payload: str,
) -> dict:
    """Validate badge + task rules without persisting a match."""
    await assert_event_active(db, participant.event_id)
    assert_task_not_completed(participant_task)

    if task.type != TaskType.SCAN:
        raise TaskCompletionError(
            "TASK_NOT_SCAN_TYPE",
            "This task does not require scanning a badge.",
            400,
        )

    badge_result = await validate_badge_for_scanner(db, qr_payload, participant)
    if not badge_result.valid:
        raise TaskCompletionError(
            badge_result.error_code or "BADGE_INVALID",
            badge_result.message or "Invalid badge.",
            400,
        )

    partner = await resolve_participant_from_badge(
        db, qr_payload, scanner_event_id=participant.event_id
    )
    if partner.id == participant.id:
        raise TaskCompletionError("BADGE_SELF_SCAN", "You cannot scan your own badge.", 400)

    await assert_partner_not_used(db, participant.event_id, participant.id, partner.id)

    return {
        "valid": True,
        "partner_id": partner.id,
        "partner_name": partner.display_name,
        "partner_company": partner.company,
        "message": f"Ready to connect with {partner.display_name}",
    }


async def record_scan_for_task(
    db: AsyncSession,
    participant: Participant,
    participant_task: ParticipantTask,
    task: Task,
    qr_payload: str,
) -> dict:
    """Validate and create match; mark task in progress pending selfie."""
    preview = await validate_scan_for_task(
        db, participant, participant_task, task, qr_payload
    )
    partner = await resolve_participant_from_badge(
        db, qr_payload, scanner_event_id=participant.event_id
    )

    settings_result = await db.execute(
        select(EventSettings).where(EventSettings.event_id == participant.event_id)
    )
    settings = settings_result.scalar_one_or_none()
    points = task.points or (settings.scan_match_points if settings else 10)

    match = Match(
        event_id=participant.event_id,
        initiator_id=participant.id,
        partner_id=partner.id,
        task_id=task.id,
        match_type=MatchType.TASK,
        points_awarded=points,
        metadata_json={"participant_task_id": participant_task.id},
    )
    db.add(match)
    participant.matches_count += 1
    participant.last_active_at = datetime.now(timezone.utc)
    await db.flush()

    participant_task.status = ParticipantTaskStatus.IN_PROGRESS
    _set_flow_meta(
        participant_task,
        {
            "step": "awaiting_selfie",
            "partner_id": partner.id,
            "partner_name": partner.display_name,
            "match_id": match.id,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db.flush()

    return {
        **preview,
        "match_id": match.id,
        "participant_task_id": participant_task.id,
        "task_id": task.id,
        "requires_selfie": True,
    }


async def begin_task_flow_timer(
    db: AsyncSession, participant_task: ParticipantTask, task: Task
) -> dict[str, Any]:
    """Start the speed-scoring clock when the participant opens a selfie task."""
    assert_task_not_completed(participant_task)
    flow = _flow_meta(participant_task)
    if task_uses_selfie_flow(task):
        if participant_task.status == ParticipantTaskStatus.PENDING:
            participant_task.status = ParticipantTaskStatus.IN_PROGRESS
        if not flow.get("started_at"):
            flow["started_at"] = datetime.now(timezone.utc).isoformat()
        if not flow.get("step"):
            flow["step"] = "awaiting_selfie"
        _set_flow_meta(participant_task, flow)
        await db.flush()
    return flow


async def assert_flow_ready_for_selfie(
    participant_task: ParticipantTask, task: Task
) -> dict[str, Any]:
    assert_task_not_completed(participant_task)
    flow = _flow_meta(participant_task)
    if task_uses_selfie_flow(task):
        if participant_task.status == ParticipantTaskStatus.PENDING:
            participant_task.status = ParticipantTaskStatus.IN_PROGRESS
            if not flow.get("started_at"):
                flow["started_at"] = datetime.now(timezone.utc).isoformat()
            if not flow.get("step"):
                flow["step"] = "awaiting_selfie"
            _set_flow_meta(participant_task, flow)
    else:
        raise TaskCompletionError(
            "TASK_TYPE_UNSUPPORTED",
            "This task type cannot be completed through the mobile flow yet.",
            400,
        )
    return flow


async def link_selfie_to_flow(
    db: AsyncSession,
    participant: Participant,
    participant_task: ParticipantTask,
    task: Task,
    selfie_id: int,
) -> Selfie:
    await assert_event_active(db, participant.event_id)
    flow = await assert_flow_ready_for_selfie(participant_task, task)

    result = await db.execute(
        select(Selfie).where(
            Selfie.id == selfie_id,
            Selfie.participant_id == participant.id,
            Selfie.event_id == participant.event_id,
        )
    )
    selfie = result.scalar_one_or_none()
    if not selfie:
        raise TaskCompletionError("SELFIE_NOT_FOUND", "Selfie not found.", 404)

    if selfie.task_id and selfie.task_id != task.id:
        raise TaskCompletionError(
            "SELFIE_WRONG_TASK",
            "This selfie belongs to a different task.",
            400,
        )

    selfie.task_id = task.id
    flow["selfie_id"] = selfie.id
    flow["step"] = "selfie_uploaded"
    _set_flow_meta(participant_task, flow)
    await db.flush()
    return selfie


async def complete_task(
    db: AsyncSession,
    participant: Participant,
    participant_task: ParticipantTask,
    task: Task,
    selfie_id: int,
) -> dict:
    """Finalize task after selfie upload."""
    await assert_event_active(db, participant.event_id)
    assert_task_not_completed(participant_task)

    selfie = await link_selfie_to_flow(
        db, participant, participant_task, task, selfie_id
    )

    flow = _flow_meta(participant_task)
    match_id = flow.get("match_id")

    if task_uses_selfie_flow(task) and not selfie_id:
        raise TaskCompletionError("SELFIE_REQUIRED", "A selfie is required for this task.", 400)

    target = meet_target_count(task) if task.type in (TaskType.SCAN, TaskType.SELFIE) else 1
    if target > 1:
        entries = list(flow.get("meet_entries") or [])
        entries.append(
            {
                "selfie_id": selfie.id,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        flow["meet_entries"] = entries
        flow["target_count"] = target
        progress = len(entries)
        flow["progress_count"] = progress

        if progress < target:
            participant_task.status = ParticipantTaskStatus.IN_PROGRESS
            flow["step"] = "select"
            for key in ("match_id", "partner_id", "partner_name", "selfie_id"):
                flow.pop(key, None)
            _set_flow_meta(participant_task, flow)
            await db.flush()
            return {
                "participant_task_id": participant_task.id,
                "task_id": task.id,
                "status": participant_task.status.value,
                "task_finished": False,
                "progress_count": progress,
                "target_count": target,
                "points_awarded": 0,
                "base_points": 0,
                "speed_bonus": 0,
                "match_id": None,
                "selfie_id": selfie.id,
                "partner_name": None,
                "message": f"{progress} of {target} people — take another selfie when you meet someone new.",
            }

    # Approve selfie when event does not require manual review
    settings_result = await db.execute(
        select(EventSettings).where(EventSettings.event_id == participant.event_id)
    )
    settings = settings_result.scalar_one_or_none()
    if settings and not settings.selfie_requires_approval:
        selfie.status = SelfieStatus.APPROVED

    participant_task.status = ParticipantTaskStatus.COMPLETED
    participant_task.completed_at = datetime.now(timezone.utc)
    flow["step"] = "completed"
    flow["completed_at"] = participant_task.completed_at.isoformat()
    _set_flow_meta(participant_task, flow)

    event_result = await db.execute(select(Event).where(Event.id == participant.event_id))
    event = event_result.scalar_one()

    if event.mode == EventMode.NETWORKING:
        score_breakdown = {"base_points": 0, "speed_bonus": 0, "points_awarded": 0}
    else:
        score_breakdown = calculate_task_completion_score(
            settings, task, participant_task, completed_at=participant_task.completed_at
        )
    points = score_breakdown["points_awarded"]
    flow["scoring"] = score_breakdown
    _set_flow_meta(participant_task, flow)

    if event.mode == EventMode.COMPETITION and points > 0:
        await add_score(db, participant.event_id, participant.id, points)

    if match_id:
        match_result = await db.execute(select(Match).where(Match.id == match_id))
        match = match_result.scalar_one_or_none()
        if match:
            match.points_awarded = points

    from app.services.leaderboard import participant_finished_all_tasks

    was_finished = await participant_finished_all_tasks(db, participant)
    await refresh_participant_progress(db, participant)
    await db.flush()
    all_tasks_completed = await participant_finished_all_tasks(db, participant)

    return {
        "participant_task_id": participant_task.id,
        "task_id": task.id,
        "status": participant_task.status.value,
        "task_finished": True,
        "progress_count": target if target > 1 else 1,
        "target_count": target,
        "points_awarded": points,
        "base_points": score_breakdown["base_points"],
        "speed_bonus": score_breakdown["speed_bonus"],
        "match_id": match_id,
        "selfie_id": selfie.id,
        "partner_name": flow.get("partner_name"),
        "all_tasks_completed": all_tasks_completed,
        "leaderboard_unlocked": all_tasks_completed and not was_finished,
    }


def get_flow_state(participant_task: ParticipantTask, task: Task) -> dict:
    from app.services.task_presenter import meet_progress_count

    flow = _flow_meta(participant_task)
    target = meet_target_count(task)
    progress = meet_progress_count(participant_task, task)
    return {
        "participant_task_id": participant_task.id,
        "task_id": task.id,
        "task_type": task.type.value,
        "status": participant_task.status.value,
        "step": flow.get("step") or (
            "completed"
            if participant_task.status == ParticipantTaskStatus.COMPLETED
            else "select"
        ),
        "partner_id": flow.get("partner_id"),
        "partner_name": flow.get("partner_name"),
        "match_id": flow.get("match_id"),
        "selfie_id": flow.get("selfie_id"),
        "target_count": target,
        "progress_count": progress,
    }
