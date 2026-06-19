from pydantic import BaseModel


class WallTimerOut(BaseModel):
    status: str
    starts_at: str | None
    ends_at: str | None
    remaining_seconds: int | None


class WallStatsOut(BaseModel):
    mode: str
    status: str
    participants: int
    connections: int
    tasks_completed: int
    task_total: int
    selfies: int
    leaderboard_enabled: bool
    leaderboard_visible: bool = False
    finisher_count: int = 0
    show_scores: bool


class WallSelfieOut(BaseModel):
    id: int
    participant_id: int
    display_name: str
    company: str | None
    task_id: int | None = None
    task_title: str | None = None
    image_url: str
    thumbnail_url: str
    uploaded_at: str | None
    status: str


class WallTaskOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    type: str
    selfie_count: int = 0
    bingo: bool = False
    category: str | None = None
