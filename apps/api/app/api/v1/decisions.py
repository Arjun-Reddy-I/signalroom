from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_org, get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models import Decision, Meeting, Membership, Organization, RoleEnum, User
from app.schemas.common import PaginatedResponse
from app.schemas.domain import DecisionCreate, DecisionResponse

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.get("", response_model=PaginatedResponse[DecisionResponse])
async def list_decisions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    meeting_id: str | None = Query(None),
    category: str | None = Query(None),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DecisionResponse]:
    query = select(Decision).where(Decision.organization_id == org.id)
    if meeting_id:
        query = query.where(Decision.meeting_id == meeting_id)
    if category:
        query = query.where(Decision.category == category)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Decision.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    decisions = res.scalars().all()

    pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(
        items=[DecisionResponse.model_validate(d) for d in decisions],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(
    req: DecisionCreate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    m_res = await db.execute(
        select(Meeting).where(Meeting.id == req.meeting_id, Meeting.organization_id == org.id)
    )
    if not m_res.scalars().first():
        raise NotFoundException(message="Meeting not found")

    decision = Decision(
        meeting_id=req.meeting_id,
        organization_id=org.id,
        title=req.title,
        description=req.description,
        category=req.category,
        source_segment_id=req.source_segment_id,
        created_by_id=user.id,
    )
    db.add(decision)
    await db.flush()
    return DecisionResponse.model_validate(decision)


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision(
    decision_id: str,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(
        select(Decision).where(Decision.id == decision_id, Decision.organization_id == org.id)
    )
    decision = res.scalars().first()
    if not decision:
        raise NotFoundException(message="Decision not found")

    await db.delete(decision)
