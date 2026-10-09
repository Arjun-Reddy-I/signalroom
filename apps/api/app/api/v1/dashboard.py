from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_db
from app.models import ActionItem, ActionItemStatusEnum, AuditLog, Meeting, MeetingStatusEnum, Organization, Project
from app.schemas.domain import ActionItemResponse, ActivityItem, DashboardAggregates, MeetingResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/aggregates", response_model=DashboardAggregates)
async def get_dashboard_aggregates(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> DashboardAggregates:
    now = datetime.now(UTC)

    # Counts
    m_total_res = await db.execute(select(func.count(Meeting.id)).where(Meeting.organization_id == org.id))
    total_meetings = m_total_res.scalar() or 0

    m_comp_res = await db.execute(
        select(func.count(Meeting.id)).where(
            Meeting.organization_id == org.id,
            Meeting.status == MeetingStatusEnum.COMPLETED,
        )
    )
    completed_meetings = m_comp_res.scalar() or 0

    p_act_res = await db.execute(
        select(func.count(Project.id)).where(
            Project.organization_id == org.id,
            Project.status != "completed",
        )
    )
    active_projects = p_act_res.scalar() or 0

    ai_open_res = await db.execute(
        select(func.count(ActionItem.id)).where(
            ActionItem.organization_id == org.id,
            ActionItem.status.in_([ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS]),
        )
    )
    open_action_items = ai_open_res.scalar() or 0

    ai_overdue_res = await db.execute(
        select(func.count(ActionItem.id)).where(
            ActionItem.organization_id == org.id,
            ActionItem.due_date < now,
            ActionItem.status.in_([ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS]),
        )
    )
    overdue_action_items = ai_overdue_res.scalar() or 0

    # Upcoming meetings
    up_res = await db.execute(
        select(Meeting)
        .where(
            Meeting.organization_id == org.id,
            Meeting.scheduled_start >= now,
            Meeting.status != MeetingStatusEnum.ARCHIVED,
        )
        .order_by(Meeting.scheduled_start.asc())
        .limit(5)
    )
    upcoming_meetings = up_res.scalars().all()

    # Recent meetings
    rec_res = await db.execute(
        select(Meeting)
        .where(
            Meeting.organization_id == org.id,
            Meeting.status == MeetingStatusEnum.COMPLETED,
        )
        .order_by(Meeting.scheduled_start.desc())
        .limit(5)
    )
    recent_meetings = rec_res.scalars().all()

    # Action items list
    ai_res = await db.execute(
        select(ActionItem)
        .where(
            ActionItem.organization_id == org.id,
            ActionItem.status.in_([ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS]),
        )
        .order_by(ActionItem.due_date.asc().nulls_last())
        .limit(10)
    )
    action_items = ai_res.scalars().all()

    # Recent activity feed from audit logs
    audit_res = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == org.id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    audit_logs = audit_res.scalars().all()

    recent_activity = [
        ActivityItem(
            id=log.id,
            title=log.action.replace("_", " ").title(),
            description=f"{log.resource_type.title()} {log.resource_id or ''} - {log.details_json or ''}",
            type=log.action,
            timestamp=log.created_at,
            link=f"/{log.resource_type}s/{log.resource_id}" if log.resource_id else None,
        )
        for log in audit_logs
    ]

    return DashboardAggregates(
        total_meetings=total_meetings,
        completed_meetings=completed_meetings,
        active_projects=active_projects,
        open_action_items=open_action_items,
        overdue_action_items=overdue_action_items,
        upcoming_meetings=[MeetingResponse.model_validate(m) for m in upcoming_meetings],
        recent_meetings=[MeetingResponse.model_validate(m) for m in recent_meetings],
        action_items=[ActionItemResponse.model_validate(a) for a in action_items],
        recent_activity=recent_activity,
    )
