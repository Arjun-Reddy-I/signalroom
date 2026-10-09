from collections.abc import AsyncGenerator

from fastapi import Cookie, Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models import Membership, Organization, RoleEnum, User

security_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    access_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if bearer and bearer.credentials:
        token = bearer.credentials
    elif access_token:
        token = access_token
    elif "authorization" in request.headers:
        auth_hdr = request.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            token = auth_hdr[7:].strip()

    if not token:
        raise UnauthorizedException(message="Authentication token missing")

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise UnauthorizedException(message="Invalid token payload")
    except Exception as e:
        raise UnauthorizedException(message=f"Invalid or expired access token: {e!s}")

    res = await db.execute(select(User).where(User.id == user_id, User.is_active))
    user = res.scalars().first()
    if not user:
        raise UnauthorizedException(message="User account inactive or not found")

    return user


async def get_current_org(
    x_organization_id: str | None = Header(None, alias="X-Organization-ID"),
    org_id_query: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    target_org_id = x_organization_id or org_id_query

    if not target_org_id:
        # Default to first organization user belongs to
        res = await db.execute(
            select(Organization)
            .join(Membership)
            .where(Membership.user_id == user.id)
            .limit(1)
        )
        org = res.scalars().first()
        if not org:
            raise NotFoundException(message="User does not belong to any organization")
        return org

    res = await db.execute(
        select(Organization)
        .join(Membership)
        .where(Organization.id == target_org_id, Membership.user_id == user.id)
    )
    org = res.scalars().first()
    if not org:
        raise ForbiddenException(message="Access denied to requested organization")

    return org


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        user: User = Depends(get_current_user),
        org: Organization = Depends(get_current_org),
        db: AsyncSession = Depends(get_db),
    ) -> Membership:
        res = await db.execute(
            select(Membership).where(
                Membership.organization_id == org.id,
                Membership.user_id == user.id,
            )
        )
        membership = res.scalars().first()
        if not membership:
            raise ForbiddenException(message="User is not a member of this organization")

        if membership.role not in self.allowed_roles:
            raise ForbiddenException(
                message=f"Role '{membership.role}' insufficient for this action. Required: {[r.value for r in self.allowed_roles]}"
            )

        return membership
