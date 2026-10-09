from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_org, get_db
from app.core.exceptions import NotFoundException
from app.models import Membership, Organization, Project, RoleEnum
from app.schemas.common import PaginatedResponse
from app.schemas.domain import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectResponse]:
    query = select(Project).where(Project.organization_id == org.id)
    if status_filter:
        query = query.where(Project.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Project.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    projects = res.scalars().all()

    pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreate,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = Project(
        organization_id=org.id,
        name=req.name,
        client=req.client,
        status=req.status,
        description=req.description,
        owner_id=req.owner_id,
    )
    db.add(project)
    await db.flush()
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    res = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org.id)
    )
    project = res.scalars().first()
    if not project:
        raise NotFoundException(message="Project not found")
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER])),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    res = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org.id)
    )
    project = res.scalars().first()
    if not project:
        raise NotFoundException(message="Project not found")

    if req.name is not None:
        project.name = req.name
    if req.client is not None:
        project.client = req.client
    if req.status is not None:
        project.status = req.status
    if req.description is not None:
        project.description = req.description
    if req.owner_id is not None:
        project.owner_id = req.owner_id

    await db.flush()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    org: Organization = Depends(get_current_org),
    _role: Membership = Depends(RoleChecker([RoleEnum.OWNER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org.id)
    )
    project = res.scalars().first()
    if not project:
        raise NotFoundException(message="Project not found")

    await db.delete(project)
