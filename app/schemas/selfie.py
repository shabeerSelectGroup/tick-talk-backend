from datetime import datetime

from pydantic import BaseModel


class SelfieOut(BaseModel):
    id: int
    event_id: int
    participant_id: int
    task_id: int | None
    match_id: int | None
    image_url: str
    thumbnail_url: str | None
    storage_key: str | None
    status: str
    metadata: dict | None = None
    captured_at: datetime | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class SelfieUploadOut(BaseModel):
    selfie_id: int
    image_url: str
    thumbnail_url: str
    storage_key: str
    thumbnail_storage_key: str
    match_id: int | None = None
    direct_upload: bool = False
    upload_url: str | None = None
    metadata: dict | None = None
