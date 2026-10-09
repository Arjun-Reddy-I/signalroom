import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.models import (
    ActionItem,
    ActionItemStatusEnum,
    Base,
    Decision,
    JobStageEnum,
    JobStatusEnum,
    MediaFile,
    Meeting,
    MeetingModeEnum,
    MeetingParticipant,
    MeetingStatusEnum,
    Membership,
    Notification,
    NotificationTypeEnum,
    Organization,
    PriorityEnum,
    ProcessingJob,
    Project,
    RoleEnum,
    Summary,
    TranscriptSegment,
    User,
)


async def seed_data(fixed_date_str: str = "2026-10-01T10:00:00Z"):
    ref_date = datetime.fromisoformat(fixed_date_str.replace("Z", "+00:00"))

    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("Checking existing seed data...")
        res = await session.execute(select(Organization).where(Organization.slug == "signalroom-studio"))
        existing_org = res.scalars().first()

        if existing_org:
            print("Cleaning existing demo organization data for clean seed...")
            await session.delete(existing_org)
            await session.commit()

        print("Creating demo organization...")
        org = Organization(
            name="SignalRoom Studio",
            slug="signalroom-studio",
            created_at=ref_date - timedelta(days=90),
            updated_at=ref_date - timedelta(days=90),
        )
        session.add(org)
        await session.flush()

        print("Creating demo users...")
        pwd_hash = get_password_hash("Password123!")

        users_data = [
            ("alex@signalroom.app", "Alex Morgan", RoleEnum.OWNER, "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"),
            ("sarah@signalroom.app", "Sarah Chen", RoleEnum.ADMIN, "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150"),
            ("david@signalroom.app", "David Kim", RoleEnum.MEMBER, "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150"),
            ("elena@signalroom.app", "Elena Rostova", RoleEnum.MEMBER, "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150"),
            ("marcus@signalroom.app", "Marcus Vance", RoleEnum.MEMBER, "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"),
        ]

        user_map = {}
        for email, name, role, avatar in users_data:
            res = await session.execute(select(User).where(User.email == email))
            u = res.scalars().first()
            if not u:
                u = User(
                    email=email,
                    full_name=name,
                    password_hash=pwd_hash,
                    avatar_url=avatar,
                    is_active=True,
                    created_at=ref_date - timedelta(days=90),
                    updated_at=ref_date - timedelta(days=90),
                )
                session.add(u)
                await session.flush()

            user_map[email] = u

            m = Membership(
                organization_id=org.id,
                user_id=u.id,
                role=role,
                created_at=ref_date - timedelta(days=90),
                updated_at=ref_date - timedelta(days=90),
            )
            session.add(m)

        await session.flush()

        print("Creating demo projects...")
        projects_data = [
            ("Brand Refresh", "Apex Corp", "at_risk", "Complete brand overhaul including identity, web design, and print guidelines.", user_map["sarah@signalroom.app"].id),
            ("Mobile App V2", "Luminary Inc", "on_track", "iOS and Android v2 redesign with offline sync and AI summaries.", user_map["david@signalroom.app"].id),
            ("AI Workspace Hub", "Internal", "in_review", "Internal tool for meeting workflow automation and knowledge integration.", user_map["alex@signalroom.app"].id),
            ("Design System", "Starlight Interactive", "on_track", "Unified React + Web Components design system with dark mode.", user_map["elena@signalroom.app"].id),
        ]

        project_map = {}
        for name, client, status, desc, owner_id in projects_data:
            p = Project(
                organization_id=org.id,
                name=name,
                client=client,
                status=status,
                description=desc,
                owner_id=owner_id,
                created_at=ref_date - timedelta(days=60),
                updated_at=ref_date - timedelta(days=60),
            )
            session.add(p)
            await session.flush()
            project_map[name] = p

        print("Creating demo meetings...")

        # 1. Product Planning (Completed)
        m1 = Meeting(
            organization_id=org.id,
            project_id=project_map["AI Workspace Hub"].id,
            title="Product Planning & Roadmap Sync",
            description="Q4 Feature priority alignment and AI pipeline review.",
            scheduled_start=ref_date - timedelta(days=2, hours=3),
            scheduled_end=ref_date - timedelta(days=2, hours=2),
            status=MeetingStatusEnum.COMPLETED,
            mode=MeetingModeEnum.REMOTE,
            created_by_id=user_map["alex@signalroom.app"].id,
            created_at=ref_date - timedelta(days=3),
            updated_at=ref_date - timedelta(days=2),
        )
        session.add(m1)
        await session.flush()

        # Add participants
        for u_email in ["alex@signalroom.app", "sarah@signalroom.app", "david@signalroom.app"]:
            session.add(MeetingParticipant(
                meeting_id=m1.id,
                user_id=user_map[u_email].id,
                name=user_map[u_email].full_name,
                email=u_email,
                role="Participant",
                attended=True,
                created_at=ref_date - timedelta(days=2),
                updated_at=ref_date - timedelta(days=2),
            ))

        # Media file
        session.add(MediaFile(
            meeting_id=m1.id,
            organization_id=org.id,
            storage_key="uploads/product_planning_20261001.wav",
            filename="product_planning_20261001.wav",
            mime_type="audio/wav",
            size_bytes=14200000,
            checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            duration_seconds=1840.0,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        ))

        # Transcripts
        t1_1 = TranscriptSegment(
            meeting_id=m1.id,
            organization_id=org.id,
            speaker="Alex Morgan",
            start_time=0.0,
            end_time=12.5,
            text="Welcome everyone. Today we are reviewing the Q4 roadmap for SignalRoom and finalizing our background worker processing pipeline.",
            confidence=0.98,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        )
        t1_2 = TranscriptSegment(
            meeting_id=m1.id,
            organization_id=org.id,
            speaker="Sarah Chen",
            start_time=13.0,
            end_time=28.4,
            text="I've prepared the architectural breakdown. We need structured JSON outputs for action items and strict fallback providers when external API keys are missing.",
            confidence=0.96,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        )
        t1_3 = TranscriptSegment(
            meeting_id=m1.id,
            organization_id=org.id,
            speaker="David Kim",
            start_time=29.0,
            end_time=45.2,
            text="I can handle the database indexes and Alembic migration scripts. I will also make sure action items have strict owner foreign keys and completion timestamps.",
            confidence=0.99,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        )
        session.add_all([t1_1, t1_2, t1_3])
        await session.flush()

        # Summary
        session.add(Summary(
            meeting_id=m1.id,
            organization_id=org.id,
            summary_text="The team aligned on the Q4 roadmap priorities for SignalRoom. Sarah presented the worker processing architecture featuring structured JSON LLM output validation and fallback provider abstractions. David committed to optimizing database schemas and Alembic migration scripts.",
            key_points_json=json.dumps([
                "Background worker uses SKIP LOCKED for lock-free parallel execution",
                "Structured JSON schema validation with single retry on LLM failure",
                "Deterministic fallback providers active when environment API keys are omitted"
            ]),
            provider="demo-fallback",
            model="signalroom-deterministic-v1",
            version="1.0",
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        ))

        # Decisions
        d1 = Decision(
            meeting_id=m1.id,
            organization_id=org.id,
            title="Adopt Postgres SKIP LOCKED for background job queue",
            description="Use a simple database-backed processing_jobs table with SELECT FOR UPDATE SKIP LOCKED to avoid extra infrastructure dependencies like Redis.",
            category="Architecture",
            confidence=0.99,
            created_by_id=user_map["alex@signalroom.app"].id,
            source_segment_id=t1_2.id,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        )
        session.add(d1)

        # Action Items
        a1_1 = ActionItem(
            meeting_id=m1.id,
            organization_id=org.id,
            title="Implement Alembic initial migration for multi-tenant schema",
            description="Ensure foreign keys carry ON DELETE CASCADE and indexes cover query patterns.",
            owner_id=user_map["david@signalroom.app"].id,
            owner_name="David Kim",
            due_date=ref_date + timedelta(days=2),
            priority=PriorityEnum.HIGH,
            status=ActionItemStatusEnum.IN_PROGRESS,
            source_segment_id=t1_3.id,
            confidence=0.98,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        )
        a1_2 = ActionItem(
            meeting_id=m1.id,
            organization_id=org.id,
            title="Configure fallback providers for STT, LLM, and Embeddings",
            description="Provide labeled mock responses tagged with provider name when API keys are empty.",
            owner_id=user_map["sarah@signalroom.app"].id,
            owner_name="Sarah Chen",
            due_date=ref_date + timedelta(days=4),
            priority=PriorityEnum.HIGH,
            status=ActionItemStatusEnum.OPEN,
            source_segment_id=t1_2.id,
            confidence=0.97,
            created_at=ref_date - timedelta(days=2),
            updated_at=ref_date - timedelta(days=2),
        )
        session.add_all([a1_1, a1_2])

        # 2. Sprint Review (Completed with Overdue Action Item)
        m2 = Meeting(
            organization_id=org.id,
            project_id=project_map["Brand Refresh"].id,
            title="Sprint Review & Client Strategy",
            description="Reviewing brand refresh deliverables with Apex Corp stakeholders.",
            scheduled_start=ref_date - timedelta(days=5, hours=2),
            scheduled_end=ref_date - timedelta(days=5, hours=1),
            status=MeetingStatusEnum.COMPLETED,
            mode=MeetingModeEnum.REMOTE,
            created_by_id=user_map["sarah@signalroom.app"].id,
            created_at=ref_date - timedelta(days=6),
            updated_at=ref_date - timedelta(days=5),
        )
        session.add(m2)
        await session.flush()

        t2_1 = TranscriptSegment(
            meeting_id=m2.id,
            organization_id=org.id,
            speaker="Elena Rostova",
            start_time=0.0,
            end_time=18.0,
            text="The initial brand guideline proposal needs updated typography and accessibility tokens.",
            confidence=0.95,
            created_at=ref_date - timedelta(days=5),
            updated_at=ref_date - timedelta(days=5),
        )
        session.add(t2_1)
        await session.flush()

        # Overdue action item (due 2 days ago)
        a2_overdue = ActionItem(
            meeting_id=m2.id,
            organization_id=org.id,
            title="Update WCAG AA contrast ratios on primary amber palette",
            description="Ensure touch targets meet 44px and body font sizes exceed 14px.",
            owner_id=user_map["elena@signalroom.app"].id,
            owner_name="Elena Rostova",
            due_date=ref_date - timedelta(days=2),
            priority=PriorityEnum.HIGH,
            status=ActionItemStatusEnum.OPEN,  # Still open despite being past due!
            source_segment_id=t2_1.id,
            confidence=0.96,
            created_at=ref_date - timedelta(days=5),
            updated_at=ref_date - timedelta(days=5),
        )
        session.add(a2_overdue)

        # Completed action item
        a2_completed = ActionItem(
            meeting_id=m2.id,
            organization_id=org.id,
            title="Export brand asset SVG bundle for client review",
            description="Prepare compressed SVG zip archive.",
            owner_id=user_map["marcus@signalroom.app"].id,
            owner_name="Marcus Vance",
            due_date=ref_date - timedelta(days=1),
            priority=PriorityEnum.MEDIUM,
            status=ActionItemStatusEnum.COMPLETED,
            completed_at=ref_date - timedelta(days=1, hours=4),
            created_at=ref_date - timedelta(days=5),
            updated_at=ref_date - timedelta(days=1),
        )
        session.add(a2_completed)

        # 3. Engineering Sync (Failed Job Demo)
        m3_failed = Meeting(
            organization_id=org.id,
            project_id=project_map["Mobile App V2"].id,
            title="Engineering Sync - Audio Pipeline Debugging",
            description="Investigating audio conversion failure on corrupted upload payload.",
            scheduled_start=ref_date - timedelta(hours=6),
            scheduled_end=ref_date - timedelta(hours=5),
            status=MeetingStatusEnum.FAILED,
            mode=MeetingModeEnum.REMOTE,
            created_by_id=user_map["david@signalroom.app"].id,
            created_at=ref_date - timedelta(hours=6),
            updated_at=ref_date - timedelta(hours=5),
        )
        session.add(m3_failed)
        await session.flush()

        failed_job = ProcessingJob(
            meeting_id=m3_failed.id,
            organization_id=org.id,
            stage=JobStageEnum.EXTRACT_AUDIO,
            status=JobStatusEnum.FAILED,
            attempts=3,
            max_attempts=3,
            error_code="MEDIA_CORRUPTED_PAYLOAD",
            error_message="ffmpeg failed to parse audio header: invalid container format or unsupported codec.",
            created_at=ref_date - timedelta(hours=6),
            updated_at=ref_date - timedelta(hours=5),
        )
        session.add(failed_job)

        # 4. Weekly Leadership (Archived Meeting Demo)
        m4_archived = Meeting(
            organization_id=org.id,
            project_id=project_map["AI Workspace Hub"].id,
            title="Q3 Retrospective & Executive Briefing",
            description="Archived quarterly leadership summary and stakeholder sign-off.",
            scheduled_start=ref_date - timedelta(days=30),
            scheduled_end=ref_date - timedelta(days=30, hours=-1),
            status=MeetingStatusEnum.ARCHIVED,
            mode=MeetingModeEnum.HYBRID,
            created_by_id=user_map["alex@signalroom.app"].id,
            created_at=ref_date - timedelta(days=35),
            updated_at=ref_date - timedelta(days=10),
        )
        session.add(m4_archived)

        # 5. Upcoming / Scheduled Meeting
        m5_scheduled = Meeting(
            organization_id=org.id,
            project_id=project_map["AI Workspace Hub"].id,
            title="Weekly Engineering & Architecture Sync",
            description="Reviewing upcoming background worker scheduler and calendar sync integration.",
            scheduled_start=ref_date + timedelta(days=1, hours=2),
            scheduled_end=ref_date + timedelta(days=1, hours=3),
            status=MeetingStatusEnum.SCHEDULED,
            mode=MeetingModeEnum.REMOTE,
            created_by_id=user_map["sarah@signalroom.app"].id,
            created_at=ref_date - timedelta(hours=12),
            updated_at=ref_date - timedelta(hours=12),
        )
        session.add(m5_scheduled)

        # Notifications
        session.add(Notification(
            organization_id=org.id,
            user_id=user_map["elena@signalroom.app"].id,
            title="Action Item Overdue",
            message="Action item 'Update WCAG AA contrast ratios on primary amber palette' is past due.",
            type=NotificationTypeEnum.REMINDER_DUE,
            link="/action-items",
            is_read=False,
            created_at=ref_date - timedelta(hours=2),
            updated_at=ref_date - timedelta(hours=2),
        ))
        session.add(Notification(
            organization_id=org.id,
            user_id=user_map["david@signalroom.app"].id,
            title="Processing Job Failed",
            message="Meeting 'Engineering Sync - Audio Pipeline Debugging' failed during audio extraction.",
            type=NotificationTypeEnum.JOB_FAILED,
            link=f"/meetings/{m3_failed.id}",
            is_read=False,
            created_at=ref_date - timedelta(hours=5),
            updated_at=ref_date - timedelta(hours=5),
        ))

        await session.commit()
        print("Seed data created successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
