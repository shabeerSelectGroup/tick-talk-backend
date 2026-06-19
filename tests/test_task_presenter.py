from app.models.enums import TaskType
from app.services.task_presenter import (
    MEET_CHALLENGE_SUMMARY,
    meet_group_total,
    meet_target_count,
    participant_task_description,
    participant_task_group_label,
)


class _Task:
    def __init__(self, **kwargs):
        self.slug = kwargs.get("slug")
        self.title = kwargs.get("title", "")
        self.description = kwargs.get("description")
        self.type = kwargs.get("type", TaskType.SELFIE)


def test_meet_person_task_description():
    task = _Task(slug="meet-person-2-of-3", title="Meet someone new (2 of 3)")
    desc = participant_task_description(task)
    assert "different person" in desc.lower()
    assert "selfie" in desc.lower()


def test_meet_person_target_is_one():
    task = _Task(slug="meet-person-1-of-3")
    assert meet_target_count(task) == 1
    assert meet_group_total(task) == 3


def test_group_label_on_first_of_three():
    first = _Task(slug="meet-person-1-of-3")
    second = _Task(slug="meet-person-2-of-3")
    assert participant_task_group_label(first) == MEET_CHALLENGE_SUMMARY
    assert participant_task_group_label(second) is None


def test_legacy_meet_3_still_has_summary():
    task = _Task(
        slug="meet-3",
        title="Meet 3 People",
        description="Scan 3 unique participant badges",
        type=TaskType.SCAN,
    )
    desc = participant_task_description(task)
    assert "3" in desc
    assert meet_target_count(task) == 3
