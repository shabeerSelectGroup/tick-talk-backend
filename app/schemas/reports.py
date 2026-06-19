from pydantic import BaseModel, Field

from app.models.enums import ExportType


class ExportCreateRequest(BaseModel):
    export_type: ExportType


class ExportJobOut(BaseModel):
    id: int
    event_id: int
    export_type: str
    export_label: str
    status: str
    file_name: str | None
    file_size_bytes: int | None
    content_type: str | None
    error_message: str | None
    created_at: str | None
    started_at: str | None
    completed_at: str | None
    download_url: str | None = None
