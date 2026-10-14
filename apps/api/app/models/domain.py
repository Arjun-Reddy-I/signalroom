from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    ActionItemStatusEnum,
    CalendarProviderEnum,
    JobStageEnum,
    JobStatusEnum,
    MeetingModeEnum,
    MeetingStatusEnum,
    NotificationTypeEnum,
    PriorityEnum,
    ReminderChannelEnum,
    ReminderStatusEnum,
    RoleEnum,
)


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Password reset (single-use token stored as hash)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[list["Membership"]] = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    meetings: Mapped[list["Meeting"]] = relationship("Meeting", back_populates="organization", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        Index("idx_membership_org_user", "organization_id", "user_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.MEMBER, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_refresh_token_hash", "token_hash"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replaced_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_project_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, at_risk, review, completed
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    meetings: Mapped[list["Meeting"]] = relationship("Meeting", back_populates="project", cascade="all, delete-orphan")


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        Index("idx_meeting_org_status", "organization_id", "status"),
        Index("idx_meeting_org_start", "organization_id", "scheduled_start"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[MeetingStatusEnum] = mapped_column(Enum(MeetingStatusEnum), default=MeetingStatusEnum.SCHEDULED, nullable=False)
    mode: Mapped[MeetingModeEnum] = mapped_column(Enum(MeetingModeEnum), default=MeetingModeEnum.REMOTE, nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="meetings")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="meetings")
    participants: Mapped[list["MeetingParticipant"]] = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")
    media_file: Mapped[Optional["MediaFile"]] = relationship("MediaFile", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan")
    summary: Mapped[Optional["Summary"]] = relationship("Summary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    action_items: Mapped[list["ActionItem"]] = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship("ProcessingJob", back_populates="meeting", cascade="all, delete-orphan")


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        Index("idx_participant_meeting", "meeting_id"),
    )

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(100), default="Participant", nullable=False)
    attended: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="participants")


class MediaFile(Base):
    __tablename__ = "media_files"

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="media_file")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        Index("idx_transcript_meeting_start", "meeting_id", "start_time"),
    )

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    speaker: Mapped[str] = mapped_column(String(100), default="Speaker 1", nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="transcript_segments")


class Summary(Base):
    __tablename__ = "summaries"

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    key_points_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of strings
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="summary")


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        Index("idx_decision_org_meeting", "organization_id", "meeting_id"),
    )

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_segment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="decisions")


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (
        Index("idx_action_org_due", "organization_id", "due_date"),
        Index("idx_action_org_status", "organization_id", "status"),
        Index("idx_action_owner", "owner_id"),
    )

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[PriorityEnum] = mapped_column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM, nullable=False)
    status: Mapped[ActionItemStatusEnum] = mapped_column(Enum(ActionItemStatusEnum), default=ActionItemStatusEnum.OPEN, nullable=False)
    source_segment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="action_items")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        Index("idx_job_org_status", "organization_id", "status"),
        Index("idx_job_meeting", "meeting_id"),
    )

    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[JobStageEnum] = mapped_column(Enum(JobStageEnum), default=JobStageEnum.VALIDATE_MEDIA, nullable=False)
    status: Mapped[JobStatusEnum] = mapped_column(Enum(JobStatusEnum), default=JobStatusEnum.PENDING, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="processing_jobs")


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("idx_reminder_fire_status", "fire_at", "status"),
        Index("idx_reminder_org", "organization_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    action_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("action_items.id", ondelete="CASCADE"), nullable=True)
    meeting_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)  # email address or user id
    fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[ReminderChannelEnum] = mapped_column(Enum(ReminderChannelEnum), default=ReminderChannelEnum.IN_APP, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ReminderStatusEnum] = mapped_column(Enum(ReminderStatusEnum), default=ReminderStatusEnum.PENDING, nullable=False)


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "provider", name="uq_cal_conn"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[CalendarProviderEnum] = mapped_column(Enum(CalendarProviderEnum), default=CalendarProviderEnum.GOOGLE, nullable=False)
    encrypted_tokens: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted JSON string
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    connection_id: Mapped[str] = mapped_column(String(36), ForeignKey("calendar_connections.id", ondelete="CASCADE"), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sync_status: Mapped[str] = mapped_column(String(50), default="synced", nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notification_user_read", "user_id", "is_read"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NotificationTypeEnum] = mapped_column(Enum(NotificationTypeEnum), default=NotificationTypeEnum.SYSTEM, nullable=False)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_org_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)


class MeetingEmbedding(Base):
    __tablename__ = "meeting_embeddings"
    __table_args__ = (
        Index("idx_embedding_chroma", "chroma_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    segment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transcript_segments.id", ondelete="CASCADE"), nullable=True)
    chroma_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)  # transcript, summary, decision, action_item
