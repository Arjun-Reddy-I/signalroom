from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ActionItemStatusEnum,
    MeetingModeEnum,
    MeetingStatusEnum,
    NotificationTypeEnum,
    PriorityEnum,
)


# Projects
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client: str | None = None
    status: str = "active"
    description: str | None = None
    owner_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    client: str | None = None
    status: str | None = None
    description: str | None = None
    owner_id: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    client: str | None = None
    status: str
    description: str | None = None
    owner_id: str | None = None
    created_at: datetime
    updated_at: datetime


# Participants
class ParticipantCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str | None = None
    role: str = "Participant"
    user_id: str | None = None
    attended: bool = True


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    user_id: str | None = None
    name: str
    email: str | None = None
    role: str
    attended: bool
    created_at: datetime


# Media
class MediaFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    storage_key: str
    filename: str
    mime_type: str
    size_bytes: int
    duration_seconds: float | None = None
    created_at: datetime


# Transcript
class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float
    created_at: datetime


# Summary
class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    summary_text: str
    key_points_json: str
    provider: str
    model: str
    version: str
    created_at: datetime


# Decisions
class DecisionCreate(BaseModel):
    meeting_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    source_segment_id: str | None = None


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    organization_id: str
    title: str
    description: str | None = None
    category: str | None = None
    confidence: float
    created_by_id: str | None = None
    source_segment_id: str | None = None
    created_at: datetime


# Action Items
class ActionItemCreate(BaseModel):
    meeting_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    due_date: datetime | None = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    status: ActionItemStatusEnum = ActionItemStatusEnum.OPEN
    source_segment_id: str | None = None


class ActionItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    due_date: datetime | None = None
    priority: PriorityEnum | None = None
    status: ActionItemStatusEnum | None = None


class ActionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    organization_id: str
    title: str
    description: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    due_date: datetime | None = None
    priority: PriorityEnum
    status: ActionItemStatusEnum
    confidence: float
    completed_at: datetime | None = None
    source_segment_id: str | None = None
    created_at: datetime
    updated_at: datetime


# Meetings
class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    project_id: str | None = None
    description: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    mode: MeetingModeEnum = MeetingModeEnum.REMOTE


class MeetingUpdate(BaseModel):
    title: str | None = None
    project_id: str | None = None
    description: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: MeetingStatusEnum | None = None
    mode: MeetingModeEnum | None = None


class MeetingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str | None = None
    title: str
    description: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    status: MeetingStatusEnum
    mode: MeetingModeEnum
    created_by_id: str | None = None
    created_at: datetime
    updated_at: datetime


class MeetingDetailResponse(MeetingResponse):
    project: ProjectResponse | None = None
    participants: list[ParticipantResponse] = []
    media_file: MediaFileResponse | None = None
    transcript_segments: list[TranscriptSegmentResponse] = []
    summary: SummaryResponse | None = None
    decisions: list[DecisionResponse] = []
    action_items: list[ActionItemResponse] = []


# Notifications
class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    title: str
    message: str
    type: NotificationTypeEnum
    link: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


# Dashboard Aggregates
class ActivityItem(BaseModel):
    id: str
    title: str
    description: str
    type: str  # meeting_created, action_completed, job_failed, decision_recorded
    timestamp: datetime
    link: str | None = None


class DashboardAggregates(BaseModel):
    total_meetings: int
    completed_meetings: int
    active_projects: int
    open_action_items: int
    overdue_action_items: int
    upcoming_meetings: list[MeetingResponse]
    recent_meetings: list[MeetingResponse]
    action_items: list[ActionItemResponse]
    recent_activity: list[ActivityItem]
