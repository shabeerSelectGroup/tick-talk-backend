from pydantic import BaseModel, Field, field_validator, model_validator


class TaskFlowScanRequest(BaseModel):
    qr_payload: str = Field(..., min_length=8, max_length=512)


class TaskFlowValidateScanResponse(BaseModel):
    valid: bool = True
    partner_id: int
    partner_name: str
    partner_company: str | None = None
    message: str


class TaskFlowScanResponse(TaskFlowValidateScanResponse):
    match_id: int
    participant_task_id: int
    task_id: int
    requires_selfie: bool = True


class TaskFlowSelfieUploadResponse(BaseModel):
    upload_url: str | None = None
    storage_key: str
    image_url: str
    thumbnail_url: str | None = None
    selfie_id: int
    direct_upload: bool = False
    match_id: int | None = None
    metadata: dict | None = None


class TaskFlowCompleteRequest(BaseModel):
    selfie_id: int | None = None
    partner_name: str | None = Field(None, max_length=120)
    partner_sign: str | None = Field(None, max_length=400_000)

    @field_validator("partner_name", "partner_sign", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def require_selfie_or_name(self):
        if self.selfie_id is not None:
            return self
        if self.partner_name and len(self.partner_name) >= 2:
            return self
        raise ValueError("Provide a photo or a name (at least 2 characters)")


class TaskFlowCompleteResponse(BaseModel):
    participant_task_id: int
    task_id: int
    status: str
    task_finished: bool = True
    progress_count: int | None = None
    target_count: int | None = None
    points_awarded: int
    base_points: int = 0
    speed_bonus: int = 0
    match_id: int | None = None
    selfie_id: int
    partner_name: str | None = None
    message: str | None = None
    all_tasks_completed: bool = False
    leaderboard_unlocked: bool = False


class TaskFlowStateResponse(BaseModel):
    participant_task_id: int
    task_id: int
    task_type: str
    status: str
    step: str
    partner_id: int | None = None
    partner_name: str | None = None
    match_id: int | None = None
    selfie_id: int | None = None
