import re

from pydantic import BaseModel, Field, field_validator

from app.models.enums import TaskType


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = Field(None, max_length=5000)
    type: TaskType = TaskType.MANUAL
    points: int = Field(default=0, ge=0, le=1000)
    is_required: bool = True
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = Field(None, max_length=5000)
    type: TaskType | None = None
    points: int | None = Field(None, ge=0, le=1000)
    is_required: bool | None = None
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class TaskOut(BaseModel):
    id: int
    event_id: int
    slug: str
    title: str
    description: str | None
    type: TaskType
    points: int
    sort_order: int
    is_required: bool
    is_active: bool
    assigned_count: int = 0
    completed_count: int = 0
    selfie_count: int = 0

    model_config = {"from_attributes": True}


class TaskSubmissionOut(BaseModel):
    id: int
    participant_id: int
    display_name: str
    company: str | None
    image_url: str
    thumbnail_url: str
    status: str
    uploaded_at: str | None


class TaskSubmissionsResponse(BaseModel):
    task: dict
    submissions: list[TaskSubmissionOut]
    submission_count: int


class TaskReorderRequest(BaseModel):
    task_ids: list[int] = Field(..., min_length=1)

    @field_validator("task_ids")
    @classmethod
    def unique_ids(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("task_ids must be unique")
        return v


class BulkTaskLine(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    type: TaskType = TaskType.MANUAL
    points: int = Field(default=0, ge=0, le=1000)


class BulkImportRequest(BaseModel):
    """Import via structured list or raw text (one title per line)."""

    tasks: list[BulkTaskLine] | None = None
    text: str | None = Field(None, max_length=50000)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class BulkImportResult(BaseModel):
    created: int
    skipped_duplicates: int
    tasks: list[TaskOut]
    errors: list[str]
