from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import EventMode, EventStatus, ParticipantTaskStatus


class JoinRequest(BaseModel):
    event_code: str = Field(..., min_length=4, max_length=12)
    display_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr | None = None
    company: str | None = Field(None, max_length=120)
    title: str | None = Field(None, max_length=120)

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("event_code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("display_name", "company", "title")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class JoinPreviewOut(BaseModel):
    code: str
    name: str
    description: str | None
    mode: EventMode
    status: EventStatus
    can_join: bool
    message: str | None = None
    participant_count: int = 0
    max_participants: int | None = None
    capabilities: dict | None = None
    public_wall_url: str | None = None


class ParticipantOut(BaseModel):
    id: int
    event_id: int
    display_name: str
    email: str | None
    company: str | None
    title: str | None
    avatar_url: str | None
    score: int = 0
    rank: int | None = None
    tasks_completed_count: int = 0
    matches_count: int = 0
    progress_percent: float = 0.0

    model_config = {"from_attributes": True}


class JoinResponse(BaseModel):
    session_token: str
    participant: ParticipantOut
    event_code: str
    event_id: int
    participant_id: int
    qr_code: str
    qr_payload: str
    qr_code_data_url: str
    resumed: bool = False
    event: dict | None = None
    capabilities: dict | None = None


class AdminParticipantCreate(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr | None = None
    company: str | None = Field(None, max_length=120)

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("display_name", "company")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class AdminParticipantBulkRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)


class AdminParticipantRosterOut(BaseModel):
    id: int
    display_name: str
    email: str | None
    company: str | None
    score: int = 0
    rank: int | None = None
    tasks_completed_count: int = 0
    matches_count: int = 0
    progress_percent: float = 0.0
    joined_at: datetime | None = None
    signed_in: bool = False


class ParticipantTaskOut(BaseModel):
    id: int
    task_id: int
    title: str
    description: str | None
    type: str
    status: ParticipantTaskStatus
    points: int
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ScanRequest(BaseModel):
    """Full QR payload or legacy token from a scanned badge."""

    qr_token: str = Field(..., min_length=8, max_length=512)


class ScanResponse(BaseModel):
    scanned_name: str
    points_earned: int
    already_scanned: bool


class LeaderboardEntry(BaseModel):
    rank: int
    participant_id: int
    display_name: str
    score: int
    company: str | None
    tasks_completed: int = 0
    matches_count: int = 0
    finished_at: str | None = None
    is_finished: bool = False


class AwardOut(BaseModel):
    id: int
    place: int
    award_type: str
    participant_id: int
    display_name: str
    company: str | None = None
    score: int
    tasks_completed: int = 0
    finished_at: str | None = None


class TimerResponse(BaseModel):
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    remaining_seconds: int | None


class ParticipantBadgeOut(BaseModel):
    """Full badge card: ID, name, signed QR payload."""

    participant_id: int
    event_id: int
    event_code: str
    display_name: str
    company: str | None = None
    secure_token: str
    qr_payload: str
    qr_code_data_url: str
    version: str = "v1"


class BadgeResponse(ParticipantBadgeOut):
    """Backward-compatible alias; `qr_token` mirrors `secure_token`."""

    qr_token: str

    @classmethod
    def from_badge(cls, badge: ParticipantBadgeOut) -> "BadgeResponse":
        data = badge.model_dump()
        data["qr_token"] = badge.secure_token
        return cls(**data)


class BadgeValidateRequest(BaseModel):
    qr_payload: str = Field(..., min_length=8, max_length=512)


class BadgeValidateResponse(BaseModel):
    valid: bool
    participant_id: int | None = None
    event_id: int | None = None
    display_name: str | None = None
    company: str | None = None
    error_code: str | None = None
    message: str | None = None
