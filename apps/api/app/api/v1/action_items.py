from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_org, get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models import ActionItem, ActionItemStatusEnum, Meeting, Membership, Organization, PriorityEnum, RoleEnum, User
from app.schemas.common import PaginatedResponse
from app.schemas.domain import ActionItemCreate, ActionItemResponse, ActionItemUpdate
from app.services.audit import log_audit
from app.services.state_machine import validate_action_item_transition

router = APIRouter(prefix="/action-items", tags=["Action Items"])


class ReassignRequest(BaseModel):
    owner_id: str | None = None
    owner_name: str | None = None


@router.get("", response_model=PaginatedResponse[ActionItemResponse])
async def list_action_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: ActionItemStatusEnum | None = Query(None, alias="status"),
    priority_filter: PriorityEnum | None = Query(None, alias="priority"),
    meeting_id: str | None = Query(None),
    owner_id: str | None = Query(None),
    overdue_only: bool = Query(False),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ActionItemResponse]:
    query = select(ActionItem).where(ActionItem.organization_id == org.id)

    if status_filter:
        query = query.where(ActionItem.status == status_filter)
    if priority_filter:
        query = query.where(ActionItem.priority == priority_filter)
    if meeting_id:
        query = query.where(ActionItem.meeting_id == meeting_id)
    if owner_id:
        query = query.where(ActionItem.owner_id == owner_id)
    if overdue_only:
        now = datetime.now(UTC)
        query = query.where(
            ActionItem.due_date < now,
            ActionItem.status != ActionItemStatusEnum.COMPLETED,
            ActionItem.status != ActionItemStatusEnum.CANCELLED,
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(ActionItem.due_date.asc().nulls_last(), ActionItem.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    items = res.scalars().all()

    pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(
        items=[ActionItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("", response_model=ActionItemResponse, status_code=status.HTTP_201_CREATED)
async def create_action_item(
    req: ActionItemCreate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse:
    m_res = await db.execute(
        select(Meeting).where(Meeting.id == req.meeting_id, Meeting.organization_id == org.id)
    )
    if not m_res.scalars().first():
        raise NotFoundException(message="Meeting not found")

    item = ActionItem(
        meeting_id=req.meeting_id,
        organization_id=org.id,
        title=req.title,
        description=req.description,
        owner_id=req.owner_id,
        owner_name=req.owner_name,
        due_date=req.due_date,
        priority=req.priority,
        status=req.status,
        source_segment_id=req.source_segment_id,
    )
    db.add(item)
    await db.flush()

    await log_audit(
        db=db,
        organization_id=org.id,
        user_id=user.id,
        action="action_item_created",
        resource_type="action_item",
        resource_id=item.id,
        details={"title": item.title, "owner_name": item.owner_name},
    )

    return ActionItemResponse.model_validate(item)


@router.get("/{action_item_id}", response_model=ActionItemResponse)
async def get_action_item(
    action_item_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse:
    res = await db.execute(
        select(ActionItem).where(ActionItem.id == action_item_id, ActionItem.organization_id == org.id)
    )
    item = res.scalars().first()
    if not item:
        raise NotFoundException(message="Action item not found")
    return ActionItemResponse.model_validate(item)


@router.patch("/{action_item_id}", response_model=ActionItemResponse)
async def update_action_item(
    action_item_id: str,
    req: ActionItemUpdate,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse:
    res = await db.execute(
        select(ActionItem).where(ActionItem.id == action_item_id, ActionItem.organization_id == org.id)
    )
    item = res.scalars().first()
    if not item:
        raise NotFoundException(message="Action item not found")

    if req.status is not None:
        validate_action_item_transition(item.status, req.status)
        item.status = req.status
        if req.status == ActionItemStatusEnum.COMPLETED:
            item.completed_at = datetime.now(UTC)
        elif req.status == ActionItemStatusEnum.OPEN:
            item.completed_at = None

    if req.title is not None:
        item.title = req.title
    if req.description is not None:
        item.description = req.description
    if req.owner_id is not None:
        item.owner_id = req.owner_id
    if req.owner_name is not None:
        item.owner_name = req.owner_name
    if req.due_date is not None:
        item.due_date = req.due_date
    if req.priority is not None:
        item.priority = req.priority

    await db.flush()
    return ActionItemResponse.model_validate(item)


@router.post("/{action_item_id}/complete", response_model=ActionItemResponse)
async def complete_action_item(
    action_item_id: str,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse:
    res = await db.execute(
        select(ActionItem).where(ActionItem.id == action_item_id, ActionItem.organization_id == org.id)
    )
    item = res.scalars().first()
    if not item:
        raise NotFoundException(message="Action item not found")

    validate_action_item_transition(item.status, ActionItemStatusEnum.COMPLETED)
    item.status = ActionItemStatusEnum.COMPLETED
    item.completed_at = datetime.now(UTC)
    await db.flush()

    await log_audit(
        db=db,
        organization_id=org.id,
        user_id=user.id,
        action="action_item_completed",
        resource_type="action_item",
        resource_id=item.id,
        details={"title": item.title},
    )

    return ActionItemResponse.model_validate(item)


@router.post("/{action_item_id}/reassign", response_model=ActionItemResponse)
async def reassign_action_item(
    action_item_id: str,
    req: ReassignRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse:
    res = await db.execute(
        select(ActionItem).where(ActionItem.id == action_item_id, ActionItem.organization_id == org.id)
    )
    item = res.scalars().first()
    if not item:
        raise NotFoundException(message="Action item not found")

    prev_owner = item.owner_name
    item.owner_id = req.owner_id
    if req.owner_name is not None:
        item.owner_name = req.owner_name

    await db.flush()

    await log_audit(
        db=db,
        organization_id=org.id,
        user_id=user.id,
        action="action_item_reassigned",
        resource_type="action_item",
        resource_id=item.id,
        details={"previous_owner": prev_owner, "new_owner": item.owner_name},
    )

    return ActionItemResponse.model_validate(item)


@router.delete("/{action_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_item(
    action_item_id: str,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(
        select(ActionItem).where(ActionItem.id == action_item_id, ActionItem.organization_id == org.id)
    )
    item = res.scalars().first()
    if not item:
        raise NotFoundException(message="Action item not found")

    await db.delete(item)
