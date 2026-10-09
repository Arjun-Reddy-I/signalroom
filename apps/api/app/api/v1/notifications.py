from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models import Notification, Organization, User
from app.schemas.common import PaginatedResponse
from app.schemas.domain import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[NotificationResponse]:
    query = select(Notification).where(
        Notification.organization_id == org.id,
        Notification.user_id == user.id,
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    notifications = res.scalars().all()

    pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    res = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == org.id,
            Notification.user_id == user.id,
        )
    )
    n = res.scalars().first()
    if not n:
        raise NotFoundException(message="Notification not found")

    n.is_read = True
    n.read_at = datetime.now(UTC)
    await db.flush()
    return NotificationResponse.model_validate(n)


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    now = datetime.now(UTC)
    await db.execute(
        update(Notification)
        .where(
            Notification.organization_id == org.id,
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now)
    )
    return {"message": "All notifications marked as read"}
