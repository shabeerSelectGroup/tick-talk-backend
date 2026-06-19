from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import EventMode, EventStatus


class EventSettingsInput(BaseModel):
    leaderboard_enabled: bool = True
    enable_awards: bool = False
    show_live_ranking: bool = True
    show_ranking_only_at_end: bool = False
    enable_selfie_verification: bool = True
    enable_public_wall: bool = True
    scan_match_points: int = Field(default=10, ge=0, le=1000)
    task_completion_points: int = Field(default=100, ge=0, le=1000)
    speed_bonus_enabled: bool = False
    speed_bonus_max_points: int = Field(default=25, ge=0, le=500)
    speed_bonus_window_seconds: int = Field(default=300, ge=30, le=3600)

    @model_validator(mode="after")
    def validate_ranking_flags(self) -> "EventSettingsInput":
        if self.show_live_ranking and self.show_ranking_only_at_end:
            raise ValueError("Cannot enable both live ranking and end-only ranking")
        return self


class EventCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=5000)
    duration_minutes: int = Field(..., ge=15, le=10080, description="15 min to 7 days")
    task_count: int = Field(
        ...,
        ge=1,
        le=30,
        description="Competition: number of tasks. Networking uses the full 30 bingo challenges.",
    )
    mode: EventMode = EventMode.NETWORKING
    timezone: str = Field(default="UTC", max_length=64)
    max_participants: int | None = Field(None, ge=1, le=100000)
    settings: EventSettingsInput = Field(default_factory=EventSettingsInput)

    @model_validator(mode="after")
    def validate_mode_settings(self) -> "EventCreateRequest":
        if self.mode == EventMode.NETWORKING:
            if self.settings.leaderboard_enabled:
                self.settings.leaderboard_enabled = False
            if self.settings.enable_awards:
                self.settings.enable_awards = False
            if self.settings.show_live_ranking:
                self.settings.show_live_ranking = False
            if self.settings.show_ranking_only_at_end:
                self.settings.show_ranking_only_at_end = False
        elif self.mode == EventMode.COMPETITION:
            if not self.settings.leaderboard_enabled and (
                self.settings.show_live_ranking or self.settings.show_ranking_only_at_end
            ):
                raise ValueError("Enable leaderboard for ranking display options")
        return self


class EventUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=5000)
    mode: EventMode | None = None
    status: EventStatus | None = None
    duration_minutes: int | None = Field(None, ge=15, le=10080)
    task_count: int | None = Field(None, ge=1, le=30)
    max_participants: int | None = Field(None, ge=1, le=100000)
    settings: EventSettingsInput | None = None


class EventSettingsOut(BaseModel):
    duration_minutes: int | None
    leaderboard_enabled: bool
    enable_awards: bool
    show_live_ranking: bool
    show_ranking_only_at_end: bool
    enable_selfie_verification: bool
    enable_public_wall: bool
    leaderboard_size: int
    scan_match_points: int
    task_completion_points: int = 100
    speed_bonus_enabled: bool = False
    speed_bonus_max_points: int = 25
    speed_bonus_window_seconds: int = 300
    selfie_requires_approval: bool

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    mode: EventMode
    status: EventStatus
    starts_at: datetime | None
    ends_at: datetime | None
    timezone: str
    max_participants: int | None
    task_count: int

    model_config = {"from_attributes": True}


class EventDetailOut(EventOut):
    settings: EventSettingsOut | None = None
    join_url: str | None = None
    qr_code_data_url: str | None = None
    participant_count: int = 0
    tasks_count: int = 0


class EventCreateResponse(BaseModel):
    event: EventOut
    settings: EventSettingsOut
    join_url: str
    qr_code_data_url: str
    tasks_created: int


class EventPublicOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    mode: EventMode
    status: EventStatus
    starts_at: datetime | None
    ends_at: datetime | None
    capabilities: dict | None = None
    public_wall_url: str | None = None

    model_config = {"from_attributes": True}


# Legacy aliases
class EventCreate(EventCreateRequest):
    pass


class EventUpdate(EventUpdateRequest):
    pass
