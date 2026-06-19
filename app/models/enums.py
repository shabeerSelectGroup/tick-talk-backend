import enum


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"


class EventMode(str, enum.Enum):
    NETWORKING = "networking"
    COMPETITION = "competition"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"


class TaskType(str, enum.Enum):
    SCAN = "scan"
    SELFIE = "selfie"
    MANUAL = "manual"
    QUIZ = "quiz"


class ParticipantTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SelfieStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MatchType(str, enum.Enum):
    QR_SCAN = "qr_scan"
    MANUAL = "manual"
    TASK = "task"
    SELFIE = "selfie"


class ExportType(str, enum.Enum):
    PDF_SUMMARY = "pdf_summary"
    EXCEL_PARTICIPANTS = "excel_participants"
    EXCEL_MATCHES = "excel_matches"
    EXCEL_LEADERBOARD = "excel_leaderboard"
    EXCEL_BUNDLE = "excel_bundle"
    ZIP_SELFIES = "zip_selfies"


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ActivityType(str, enum.Enum):
    PARTICIPANT_JOINED = "participant_joined"
    TASK_COMPLETED = "task_completed"
    MATCH_CREATED = "match_created"
    SELFIE_UPLOADED = "selfie_uploaded"
    SELFIE_APPROVED = "selfie_approved"
    SCORE_UPDATED = "score_updated"
    EVENT_STARTED = "event_started"
    EVENT_ENDED = "event_ended"
    WINNER_ANNOUNCED = "winner_announced"
