from pydantic import BaseModel

from app.models.enums import EventMode


class EventCapabilitiesOut(BaseModel):
    mode: EventMode
    scores_enabled: bool
    rankings_enabled: bool
    leaderboard_enabled: bool
    shared_tasks_enabled: bool = True
    selfie_verification_enabled: bool = True
    public_wall_enabled: bool = True
    analytics_enabled: bool = True
    show_task_points: bool = False
    show_match_points: bool = False
    public_wall_url: str | None = None
