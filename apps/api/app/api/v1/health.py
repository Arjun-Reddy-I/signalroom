from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db.vector_store import get_chroma_client
from app.schemas.common import HealthCheckResponse

router = APIRouter(tags=["Health Check"])


@router.get("/health/live", response_model=HealthCheckResponse)
async def health_live() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        database="unknown",
        vector_store="unknown",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/health/ready", response_model=HealthCheckResponse)
async def health_ready(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e!s}"

    chroma_status = "connected"
    try:
        client = get_chroma_client()
        client.heartbeat()
    except Exception as e:
        chroma_status = f"error: {e!s}"

    overall_status = "ok" if (db_status == "connected" and chroma_status == "connected") else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        database=db_status,
        vector_store=chroma_status,
        timestamp=datetime.now(UTC).isoformat(),
    )
