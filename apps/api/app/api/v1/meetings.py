from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RoleChecker, get_current_org, get_current_user, get_db
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models import (
    MediaFile,
    Meeting,
    MeetingParticipant,
    MeetingStatusEnum,
    Membership,
    Organization,
    ProcessingJob,
    Project,
    RoleEnum,
    User,
)
from app.models.enums import JobStageEnum, JobStatusEnum
from app.providers.storage import get_storage_provider
from app.schemas.common import PaginatedResponse
from app.schemas.domain import (
    ActionItemResponse,
    DecisionResponse,
    MediaFileResponse,
    MeetingCreate,
    MeetingDetailResponse,
    MeetingResponse,
    MeetingUpdate,
    ParticipantResponse,
    ProcessingJobResponse,
    ProjectResponse,
    SummaryResponse,
    TranscriptSegmentResponse,
    UploadResponse,
)
from app.services.state_machine import validate_meeting_transition

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("", response_model=PaginatedResponse[MeetingResponse])
async def list_meetings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: MeetingStatusEnum | None = Query(None, alias="status"),
    project_id: str | None = Query(None),
    search: str | None = Query(None),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MeetingResponse]:
    query = select(Meeting).where(Meeting.organization_id == org.id)

    if status_filter:
        query = query.where(Meeting.status == status_filter)
    if project_id:
        query = query.where(Meeting.project_id == project_id)
    if search:
        query = query.where(Meeting.title.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Meeting.scheduled_start.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    meetings = res.scalars().all()

    pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(
        items=[MeetingResponse.model_validate(m) for m in meetings],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    req: MeetingCreate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> MeetingResponse:
    if req.project_id:
        p_res = await db.execute(
            select(Project).where(Project.id == req.project_id, Project.organization_id == org.id)
        )
        if not p_res.scalars().first():
            raise NotFoundException(message="Associated project not found")

    meeting = Meeting(
        organization_id=org.id,
        project_id=req.project_id,
        title=req.title,
        description=req.description,
        scheduled_start=req.scheduled_start,
        scheduled_end=req.scheduled_end,
        status=MeetingStatusEnum.SCHEDULED,
        mode=req.mode,
        created_by_id=user.id,
    )
    db.add(meeting)
    await db.flush()

    # Automatically add creator as participant
    participant = MeetingParticipant(
        meeting_id=meeting.id,
        user_id=user.id,
        name=user.full_name,
        email=user.email,
        role="Host",
        attended=True,
    )
    db.add(participant)
    await db.flush()

    return MeetingResponse.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> MeetingDetailResponse:
    query = (
        select(Meeting)
        .options(
            selectinload(Meeting.project),
            selectinload(Meeting.participants),
            selectinload(Meeting.media_file),
            selectinload(Meeting.transcript_segments),
            selectinload(Meeting.summary),
            selectinload(Meeting.decisions),
            selectinload(Meeting.action_items),
        )
        .where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    res = await db.execute(query)
    meeting = res.scalars().first()

    if not meeting:
        raise NotFoundException(message="Meeting not found")

    return MeetingDetailResponse(
        id=meeting.id,
        organization_id=meeting.organization_id,
        project_id=meeting.project_id,
        title=meeting.title,
        description=meeting.description,
        scheduled_start=meeting.scheduled_start,
        scheduled_end=meeting.scheduled_end,
        status=meeting.status,
        mode=meeting.mode,
        created_by_id=meeting.created_by_id,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        project=ProjectResponse.model_validate(meeting.project) if meeting.project else None,
        participants=[ParticipantResponse.model_validate(p) for p in meeting.participants],
        media_file=MediaFileResponse.model_validate(meeting.media_file) if meeting.media_file else None,
        transcript_segments=[TranscriptSegmentResponse.model_validate(t) for t in meeting.transcript_segments],
        summary=SummaryResponse.model_validate(meeting.summary) if meeting.summary else None,
        decisions=[DecisionResponse.model_validate(d) for d in meeting.decisions],
        action_items=[ActionItemResponse.model_validate(a) for a in meeting.action_items],
    )


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    req: MeetingUpdate,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> MeetingResponse:
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    if req.status is not None:
        validate_meeting_transition(meeting.status, req.status)
        meeting.status = req.status

    if req.title is not None:
        meeting.title = req.title
    if req.project_id is not None:
        meeting.project_id = req.project_id
    if req.description is not None:
        meeting.description = req.description
    if req.scheduled_start is not None:
        meeting.scheduled_start = req.scheduled_start
    if req.scheduled_end is not None:
        meeting.scheduled_end = req.scheduled_end
    if req.mode is not None:
        meeting.mode = req.mode

    await db.flush()
    return MeetingResponse.model_validate(meeting)


@router.post("/{meeting_id}/archive", response_model=MeetingResponse)
async def archive_meeting(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> MeetingResponse:
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    validate_meeting_transition(meeting.status, MeetingStatusEnum.ARCHIVED)
    meeting.status = MeetingStatusEnum.ARCHIVED
    await db.flush()
    return MeetingResponse.model_validate(meeting)


@router.post("/{meeting_id}/restore", response_model=MeetingResponse)
async def restore_meeting(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> MeetingResponse:
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    validate_meeting_transition(meeting.status, MeetingStatusEnum.COMPLETED)
    meeting.status = MeetingStatusEnum.COMPLETED
    await db.flush()
    return MeetingResponse.model_validate(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    await db.delete(meeting)


# ── Upload endpoint ─────────────────────────────────────────────────────────

@router.post("/{meeting_id}/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_meeting_media(
    meeting_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Upload a media file for a meeting and enqueue it for AI processing."""
    # Fetch and verify meeting ownership
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    # Prevent duplicate upload unless previous job failed
    existing_mf = await db.execute(
        select(MediaFile).where(MediaFile.meeting_id == meeting_id)
    )
    if existing_mf.scalars().first():
        if meeting.status != MeetingStatusEnum.FAILED:
            raise ConflictException(
                message="A media file is already associated with this meeting. "
                "Archive the meeting and create a new one to re-upload, or delete the existing file first."
            )
        # Allow re-upload if previous processing failed — clean up old records
        from sqlalchemy import delete as sql_delete

        await db.execute(sql_delete(MediaFile).where(MediaFile.meeting_id == meeting_id))
        await db.execute(sql_delete(ProcessingJob).where(ProcessingJob.meeting_id == meeting_id))
        await db.flush()

    # Save file
    try:
        storage_key, filename, size_bytes, checksum = await get_storage_provider().save_file(
            file, key_prefix=f"org_{org.id}"
        )
    except BadRequestException:
        raise
    except Exception as exc:
        raise BadRequestException(message=f"File upload failed: {exc!s}")

    # Create MediaFile record
    media_file = MediaFile(
        meeting_id=meeting.id,
        organization_id=org.id,
        storage_key=storage_key,
        filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        checksum_sha256=checksum,
    )
    db.add(media_file)
    await db.flush()

    # Create processing job
    job = ProcessingJob(
        meeting_id=meeting.id,
        organization_id=org.id,
        stage=JobStageEnum.VALIDATE_MEDIA,
        status=JobStatusEnum.PENDING,
        max_attempts=3,
    )
    db.add(job)

    # Transition meeting to UPLOADED
    meeting.status = MeetingStatusEnum.UPLOADED
    await db.flush()

    return UploadResponse(
        meeting_id=meeting.id,
        job_id=job.id,
        filename=filename,
        size_bytes=size_bytes,
        status=JobStatusEnum.PENDING,
        message="File uploaded. Processing has been queued.",
    )


# ── Job status endpoint ──────────────────────────────────────────────────────

@router.get("/{meeting_id}/job", response_model=ProcessingJobResponse)
async def get_processing_job(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ProcessingJobResponse:
    """Get the latest processing job status for a meeting."""
    # Verify meeting ownership
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    if not res.scalars().first():
        raise NotFoundException(message="Meeting not found")

    job_res = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.meeting_id == meeting_id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    job = job_res.scalars().first()
    if not job:
        raise NotFoundException(message="No processing job found for this meeting")

    return ProcessingJobResponse.model_validate(job)


# ── ICS calendar export ──────────────────────────────────────────────────────

@router.get("/{meeting_id}/calendar.ics")
async def export_ics(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export a meeting as an ICS calendar event (RFC 5545)."""
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    def _fmt(dt) -> str:  # type: ignore[no-untyped-def]
        return dt.strftime("%Y%m%dT%H%M%SZ")

    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    now_str = _fmt(_dt.now(_UTC))
    desc = (meeting.description or "").replace("\n", "\\n")

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//SignalRoom//SignalRoom 1.0//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{meeting.id}@signalroom\r\n"
        f"DTSTART:{_fmt(meeting.scheduled_start)}\r\n"
        f"DTEND:{_fmt(meeting.scheduled_end)}\r\n"
        f"DTSTAMP:{now_str}\r\n"
        f"SUMMARY:{meeting.title}\r\n"
        f"DESCRIPTION:{desc}\r\n"
        f"STATUS:{'CONFIRMED' if meeting.status == MeetingStatusEnum.COMPLETED else 'TENTATIVE'}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    return Response(
        content=ics,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="meeting-{meeting_id[:8]}.ics"'
        },
    )


# ── Meeting context (cross-meeting memory) ───────────────────────────────────

@router.get("/{meeting_id}/context")
async def get_meeting_context(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return cross-meeting context: prior decisions, unresolved tasks, related meetings."""
    from app.models import ActionItem, Decision
    from app.models.enums import ActionItemStatusEnum

    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    # Prior completed meetings in same project
    related_query = (
        select(Meeting)
        .where(
            Meeting.organization_id == org.id,
            Meeting.id != meeting_id,
            Meeting.status == MeetingStatusEnum.COMPLETED,
        )
    )
    if meeting.project_id:
        related_query = related_query.where(Meeting.project_id == meeting.project_id)
    related_query = related_query.order_by(Meeting.scheduled_start.desc()).limit(5)
    rel_res = await db.execute(related_query)
    related_meetings = rel_res.scalars().all()

    # Unresolved action items in same project
    open_tasks_query = (
        select(ActionItem)
        .where(
            ActionItem.organization_id == org.id,
            ActionItem.status.in_([ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS]),
        )
    )
    if meeting.project_id:
        # Get all meeting IDs in the project
        proj_meetings_res = await db.execute(
            select(Meeting.id).where(
                Meeting.organization_id == org.id,
                Meeting.project_id == meeting.project_id,
            )
        )
        proj_meeting_ids = [r[0] for r in proj_meetings_res.all()]
        if proj_meeting_ids:
            open_tasks_query = open_tasks_query.where(
                ActionItem.meeting_id.in_(proj_meeting_ids)
            )
    open_tasks_res = await db.execute(open_tasks_query.limit(20))
    open_tasks = open_tasks_res.scalars().all()

    # Recent decisions in same project
    decisions_query = (
        select(Decision)
        .where(Decision.organization_id == org.id)
        .order_by(Decision.created_at.desc())
    )
    if related_meetings:
        related_ids = [m.id for m in related_meetings]
        decisions_query = decisions_query.where(Decision.meeting_id.in_(related_ids))
    dec_res = await db.execute(decisions_query.limit(10))
    recent_decisions = dec_res.scalars().all()

    return {
        "meeting_id": meeting_id,
        "related_meetings": [
            {
                "id": m.id,
                "title": m.title,
                "scheduled_start": m.scheduled_start.isoformat(),
                "status": m.status,
            }
            for m in related_meetings
        ],
        "open_action_items": [
            {
                "id": a.id,
                "title": a.title,
                "owner_name": a.owner_name,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "status": a.status,
                "meeting_id": a.meeting_id,
            }
            for a in open_tasks
        ],
        "recent_decisions": [
            {
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "meeting_id": d.meeting_id,
                "created_at": d.created_at.isoformat(),
            }
            for d in recent_decisions
        ],
    }
