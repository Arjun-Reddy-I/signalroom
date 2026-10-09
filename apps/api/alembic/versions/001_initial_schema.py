"""Initial multi-tenant SignalRoom schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-01 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # 2. Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_organizations_slug', 'organizations', ['slug'])

    # 3. Memberships
    op.create_table(
        'memberships',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_membership_org_user')
    )
    op.create_index('idx_membership_org_user', 'memberships', ['organization_id', 'user_id'])

    # 4. Refresh Tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('replaced_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_refresh_token_hash', 'refresh_tokens', ['token_hash'])

    # 5. Projects
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('client', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_project_org_status', 'projects', ['organization_id', 'status'])

    # 6. Meetings
    op.create_table(
        'meetings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='scheduled'),
        sa.Column('mode', sa.String(50), nullable=False, server_default='remote'),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_meeting_org_status', 'meetings', ['organization_id', 'status'])
    op.create_index('idx_meeting_org_start', 'meetings', ['organization_id', 'scheduled_start'])

    # 7. Meeting Participants
    op.create_table(
        'meeting_participants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('role', sa.String(100), nullable=False, server_default='Participant'),
        sa.Column('attended', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_participant_meeting', 'meeting_participants', ['meeting_id'])

    # 8. Media Files
    op.create_table(
        'media_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_key', sa.String(512), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(64), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Transcript Segments
    op.create_table(
        'transcript_segments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('speaker', sa.String(100), nullable=False, server_default='Speaker 1'),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_transcript_meeting_start', 'transcript_segments', ['meeting_id', 'start_time'])

    # 10. Summaries
    op.create_table(
        'summaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('key_points_json', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 11. Decisions
    op.create_table(
        'decisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_segment_id', sa.String(36), sa.ForeignKey('transcript_segments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_decision_org_meeting', 'decisions', ['organization_id', 'meeting_id'])

    # 12. Action Items
    op.create_table(
        'action_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('source_segment_id', sa.String(36), sa.ForeignKey('transcript_segments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_action_org_due', 'action_items', ['organization_id', 'due_date'])
    op.create_index('idx_action_org_status', 'action_items', ['organization_id', 'status'])
    op.create_index('idx_action_owner', 'action_items', ['owner_id'])

    # 13. Processing Jobs
    op.create_table(
        'processing_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False, server_default='validate_media'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_job_org_status', 'processing_jobs', ['organization_id', 'status'])
    op.create_index('idx_job_meeting', 'processing_jobs', ['meeting_id'])

    # 14. Reminders
    op.create_table(
        'reminders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_item_id', sa.String(36), sa.ForeignKey('action_items.id', ondelete='CASCADE'), nullable=True),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('target', sa.String(255), nullable=False),
        sa.Column('fire_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False, server_default='in_app'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_reminder_fire_status', 'reminders', ['fire_at', 'status'])
    op.create_index('idx_reminder_org', 'reminders', ['organization_id'])

    # 15. Calendar Connections
    op.create_table(
        'calendar_connections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False, server_default='google'),
        sa.Column('encrypted_tokens', sa.Text(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'user_id', 'provider', name='uq_cal_conn')
    )

    # 16. Calendar Events
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_id', sa.String(36), sa.ForeignKey('calendar_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('external_event_id', sa.String(255), nullable=False),
        sa.Column('sync_status', sa.String(50), nullable=False, server_default='synced'),
        sa.Column('etag', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 17. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False, server_default='system'),
        sa.Column('link', sa.String(512), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_notification_user_read', 'notifications', ['user_id', 'is_read'])

    # 18. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_audit_org_created', 'audit_logs', ['organization_id', 'created_at'])

    # 19. Meeting Embeddings
    op.create_table(
        'meeting_embeddings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('segment_id', sa.String(36), sa.ForeignKey('transcript_segments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('chroma_id', sa.String(255), nullable=False, unique=True),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_embedding_chroma', 'meeting_embeddings', ['chroma_id'])


def downgrade() -> None:
    op.drop_table('meeting_embeddings')
    op.drop_table('audit_logs')
    op.drop_table('notifications')
    op.drop_table('calendar_events')
    op.drop_table('calendar_connections')
    op.drop_table('reminders')
    op.drop_table('processing_jobs')
    op.drop_table('action_items')
    op.drop_table('decisions')
    op.drop_table('summaries')
    op.drop_table('transcript_segments')
    op.drop_table('media_files')
    op.drop_table('meeting_participants')
    op.drop_table('meetings')
    op.drop_table('projects')
    op.drop_table('refresh_tokens')
    op.drop_table('memberships')
    op.drop_table('organizations')
    op.drop_table('users')
