from app.data.networking_bingo_tasks import BINGO_TASK_COUNT, networking_bingo_task_templates
from app.models.enums import TaskType


def test_bingo_has_30_tasks():
    templates = networking_bingo_task_templates()
    assert len(templates) == 30
    assert BINGO_TASK_COUNT == 30
    assert all(t["config_json"]["bingo"] for t in templates)
    assert all(t["type"] == TaskType.SELFIE for t in templates)
    assert templates[0]["title"] == "Loves traveling"
