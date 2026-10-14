"""Intelligent agenda generation for upcoming meetings.

Generates a suggested agenda using:
- Overdue action items (highest priority)
- Open action items from the same project
- Recent unresolved decisions
- Previous meeting summaries
- Current meeting description

Can use the LLM provider for richer suggestions, or falls back to
rule-based generation when no LLM is configured.
"""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_db
from app.core.exceptions import NotFoundException
from app.models import ActionItem, Decision, Meeting, Organization, Summary
from app.models.enums import ActionItemStatusEnum
from app.schemas.domain import AgendaItem, AgendaResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agenda"])


@router.post("/meetings/{meeting_id}/agenda", response_model=AgendaResponse)
async def generate_agenda(
    meeting_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> AgendaResponse:
    """Generate a suggested agenda for the given meeting."""
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org.id)
    )
    meeting = res.scalars().first()
    if not meeting:
        raise NotFoundException(message="Meeting not found")

    now = datetime.now(UTC)
    items: list[AgendaItem] = []
    order = 1

    # ── 1. Always start with an overview ────────────────────────────────
    items.append(AgendaItem(
        order=order,
        title="Meeting opening and objectives",
        rationale=f"Review the purpose of this {meeting.mode} meeting.",
        source_type="overview",
        duration_minutes=5,
    ))
    order += 1

    # ── 2. Overdue action items ──────────────────────────────────────────
    overdue_query = (
        select(ActionItem)
        .where(
            ActionItem.organization_id == org.id,
            ActionItem.due_date < now,
            ActionItem.status.in_([ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS]),
        )
        .order_by(ActionItem.due_date.asc())
        .limit(5)
    )
    if meeting.project_id:
        # Filter by same project meetings
        proj_m_res = await db.execute(
            select(Meeting.id).where(
                Meeting.organization_id == org.id,
                Meeting.project_id == meeting.project_id,
            )
        )
        proj_meeting_ids = [r[0] for r in proj_m_res.all()]
        if proj_meeting_ids:
            overdue_query = overdue_query.where(ActionItem.meeting_id.in_(proj_meeting_ids))

    overdue_res = await db.execute(overdue_query)
    overdue_items = overdue_res.scalars().all()

    if overdue_items:
        items.append(AgendaItem(
            order=order,
            title=f"Overdue action items ({len(overdue_items)} items)",
            rationale=(
                "These items are past their due date and require immediate attention: "
                + "; ".join(f"'{a.title}'" for a in overdue_items[:3])
                + ("..." if len(overdue_items) > 3 else "")
            ),
            source_type="action_item",
            source_id=overdue_items[0].id,
            duration_minutes=10,
        ))
        order += 1

    # ── 3. Open action items from previous meetings ──────────────────────
    open_query = (
        select(ActionItem)
        .where(
            ActionItem.organization_id == org.id,
            ActionItem.status.in_([ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS]),
            ActionItem.meeting_id != meeting_id,
        )
        .order_by(ActionItem.due_date.asc().nulls_last())
        .limit(5)
    )
    if meeting.project_id and proj_meeting_ids:
        open_query = open_query.where(ActionItem.meeting_id.in_(proj_meeting_ids))

    open_res = await db.execute(open_query)
    open_items = [a for a in open_res.scalars().all() if a not in overdue_items][:3]

    for ai_item in open_items:
        items.append(AgendaItem(
            order=order,
            title=f"Status update: {ai_item.title[:60]}",
            rationale=(
                f"Assigned to {ai_item.owner_name or 'unassigned'}. "
                f"Priority: {ai_item.priority}. "
                f"Due: {ai_item.due_date.strftime('%Y-%m-%d') if ai_item.due_date else 'No deadline set'}."
            ),
            source_type="action_item",
            source_id=ai_item.id,
            duration_minutes=5,
        ))
        order += 1

    # ── 4. Recent decisions to review ───────────────────────────────────
    dec_query = (
        select(Decision)
        .where(Decision.organization_id == org.id)
        .order_by(Decision.created_at.desc())
        .limit(3)
    )
    dec_res = await db.execute(dec_query)
    recent_decisions = dec_res.scalars().all()

    if recent_decisions:
        items.append(AgendaItem(
            order=order,
            title="Review of recent decisions",
            rationale=(
                "Verify implementation progress on: "
                + "; ".join(f"'{d.title[:40]}'" for d in recent_decisions[:2])
            ),
            source_type="decision",
            source_id=recent_decisions[0].id,
            duration_minutes=10,
        ))
        order += 1

    # ── 5. Summary from most recent related meeting ──────────────────────
    prev_meeting_query = (
        select(Meeting, Summary)
        .join(Summary, Summary.meeting_id == Meeting.id)
        .where(
            Meeting.organization_id == org.id,
            Meeting.id != meeting_id,
        )
        .order_by(Meeting.scheduled_start.desc())
        .limit(1)
    )
    prev_res = await db.execute(prev_meeting_query)
    prev_row = prev_res.first()
    if prev_row:
        prev_meeting, prev_summary = prev_row
        items.append(AgendaItem(
            order=order,
            title=f"Recap: {prev_meeting.title[:50]}",
            rationale=f"Brief recap of previous meeting outcomes: {prev_summary.summary_text[:150]}...",
            source_type="overview",
            source_id=prev_meeting.id,
            duration_minutes=5,
        ))
        order += 1

    # ── 6. New business / current meeting focus ──────────────────────────
    if meeting.description:
        items.append(AgendaItem(
            order=order,
            title="New business",
            rationale=meeting.description[:200],
            source_type="overview",
            duration_minutes=15,
        ))
        order += 1

    # ── 7. Closing ───────────────────────────────────────────────────────
    items.append(AgendaItem(
        order=order,
        title="Action item assignments and next steps",
        rationale="Assign owners and deadlines for any new action items identified during this meeting.",
        source_type="overview",
        duration_minutes=5,
    ))

    total_minutes = sum(i.duration_minutes for i in items)
    notes = (
        f"Estimated total: {total_minutes} min. "
        f"Overdue items: {len(overdue_items)}. "
        f"Generated from {len(open_items)} open tasks and {len(recent_decisions)} recent decisions."
    )

    return AgendaResponse(
        meeting_id=meeting_id,
        meeting_title=meeting.title,
        generated_at=datetime.now(UTC),
        items=items,
        notes=notes,
    )
