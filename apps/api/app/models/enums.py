import enum


class RoleEnum(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class MeetingStatusEnum(enum.StrEnum):
    SCHEDULED = "scheduled"
    PREPARING = "preparing"
    RECORDING = "recording"
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class MeetingModeEnum(enum.StrEnum):
    IN_PERSON = "in_person"
    REMOTE = "remote"
    HYBRID = "hybrid"


class PriorityEnum(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionItemStatusEnum(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class JobStatusEnum(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStageEnum(enum.StrEnum):
    VALIDATE_MEDIA = "validate_media"
    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIBE = "transcribe"
    ANALYZE = "analyze"
    PERSIST = "persist"
    VECTOR_EMBED = "vector_embed"
    REMINDERS = "reminders"
    COMPLETED = "completed"


class ReminderStatusEnum(enum.StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReminderChannelEnum(enum.StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"


class CalendarProviderEnum(enum.StrEnum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"


class NotificationTypeEnum(enum.StrEnum):
    ACTION_ITEM_ASSIGNED = "action_item_assigned"
    REMINDER_DUE = "reminder_due"
    MEETING_READY = "meeting_ready"
    JOB_FAILED = "job_failed"
    SYSTEM = "system"
