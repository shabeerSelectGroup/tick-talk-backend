"""Participant-facing copy and meet task helpers."""

import re

from app.models.enums import TaskType
from app.models.participant import ParticipantTask
from app.models.task import Task

MEET_CHALLENGE_SUMMARY = (
    "Meet 3 different people. Take a selfie with each person you connect with."
)
MEET_PERSON_DESCRIPTION = (
    "Meet a different person. Take a selfie with each person you connect with."
)

MEET_SLUG_RE = re.compile(r"^meet-(\d+)$", re.IGNORECASE)
MEET_PERSON_SLUG_RE = re.compile(r"^meet-person-(\d+)-of-(\d+)$", re.IGNORECASE)
MEET_TITLE_RE = re.compile(r"meet\s+(\d+)", re.IGNORECASE)

SLUG_DESCRIPTIONS: dict[str, str] = {
    "meet-3": MEET_CHALLENGE_SUMMARY,
    "meet-5": "Meet 5 different people. Take a selfie with each person you connect with.",
    "department-connect": "Meet someone from another department and take a selfie together.",
    "team-selfie": "Take a selfie with your group or table.",
}

_SCAN_COPY = re.compile(r"scan|badge|qr", re.IGNORECASE)


def _parse_meet_person_slug(slug: str | None) -> tuple[int, int] | None:
    if not slug:
        return None
    m = MEET_PERSON_SLUG_RE.match(slug.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def meet_group_total(task: Task) -> int | None:
    """If this task is one step of a meet-N challenge, returns N."""
    parsed = _parse_meet_person_slug(task.slug)
    if parsed:
        return parsed[1]
    if task.slug and MEET_SLUG_RE.match(task.slug.strip()):
        return meet_target_count(task)
    return None


def meet_group_index(task: Task) -> int | None:
    parsed = _parse_meet_person_slug(task.slug)
    if parsed:
        return parsed[0]
    return None


def participant_task_group_label(task: Task) -> str | None:
    total = meet_group_total(task)
    if total and meet_group_index(task) == 1:
        if total == 3:
            return MEET_CHALLENGE_SUMMARY
        return (
            f"Meet {total} different people. "
            "Take a selfie with each person you connect with."
        )
    return None


def _default_meet_description(task: Task) -> str:
    if _parse_meet_person_slug(task.slug):
        return MEET_PERSON_DESCRIPTION
    title = (task.title or "").strip()
    if title:
        return f"{title}: take a selfie when you've made the connection."
    return MEET_PERSON_DESCRIPTION


def participant_task_description(task: Task) -> str | None:
    if task.slug and task.slug in SLUG_DESCRIPTIONS:
        return SLUG_DESCRIPTIONS[task.slug]
    if _parse_meet_person_slug(task.slug):
        return MEET_PERSON_DESCRIPTION
    raw = (task.description or "").strip()
    if task.type in (TaskType.SCAN, TaskType.SELFIE):
        if not raw or _SCAN_COPY.search(raw):
            return _default_meet_description(task)
    return raw or None


def meet_target_count(task: Task) -> int:
    """Selfies required for this row (1 per task; legacy meet-3 slug = 3)."""
    if task.slug and task.slug.startswith("bingo-"):
        return 1
    parsed = _parse_meet_person_slug(task.slug)
    if parsed:
        return 1
    if task.slug:
        m = MEET_SLUG_RE.match(task.slug.strip())
        if m:
            return max(1, int(m.group(1)))
    if task.title:
        m = MEET_TITLE_RE.search(task.title)
        if m:
            return max(1, int(m.group(1)))
    return 1


def meet_progress_count(participant_task: ParticipantTask, task: Task) -> int:
    from app.models.enums import ParticipantTaskStatus

    if _parse_meet_person_slug(task.slug):
        return 1 if participant_task.status == ParticipantTaskStatus.COMPLETED else 0

    target = meet_target_count(task)
    if participant_task.status == ParticipantTaskStatus.COMPLETED:
        return target
    raw = participant_task.metadata_json or {}
    flow = raw.get("flow") or {}
    return len(flow.get("meet_entries") or [])


def participant_task_instruction(task: Task) -> str | None:
    if task.type not in (TaskType.SCAN, TaskType.SELFIE):
        return participant_task_description(task)
    return participant_task_description(task) or "Take a selfie to complete this task."
