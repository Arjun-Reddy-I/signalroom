import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_audit(
    db: AsyncSession,
    organization_id: str,
    action: str,
    resource_type: str,
    user_id: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=json.dumps(details) if details else None,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
