from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RoleChecker, get_current_org, get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models import (
    Meeting,
    MeetingParticipant,
    MeetingStatusEnum,
    Membership,
    Organization,
    Project,
    RoleEnum,
    User,
)
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
    ProjectResponse,
    SummaryResponse,
    TranscriptSegmentResponse,
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
