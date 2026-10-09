import os
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db
from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from app.core.security import create_access_token, get_password_hash, hash_token, verify_password
from app.models import Membership, Organization, RefreshToken, RoleEnum, User
from app.providers.email import get_email_provider
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    OrganizationResponse,
    PasswordChangeRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text or "org"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    res = await db.execute(select(User).where(User.email == req.email))
    if res.scalars().first():
        raise ConflictException(message="An account with this email address already exists")

    user = User(
        email=req.email,
        full_name=req.full_name,
        password_hash=get_password_hash(req.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    base_slug = slugify(req.organization_name)
    slug = base_slug
    counter = 1
    while True:
        res_slug = await db.execute(select(Organization).where(Organization.slug == slug))
        if not res_slug.scalars().first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(
        name=req.organization_name,
        slug=slug,
    )
    db.add(org)
    await db.flush()

    membership = Membership(
        organization_id=org.id,
        user_id=user.id,
        role=RoleEnum.OWNER,
    )
    db.add(membership)
    await db.flush()

    # Generate tokens
    access_token = create_access_token(subject=user.id, extra_claims={"org_id": org.id})
    raw_refresh = os.urandom(32).hex()
    hashed_refresh = hash_token(raw_refresh)

    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_entry)

    await log_audit(
        db=db,
        organization_id=org.id,
        user_id=user.id,
        action="user_registered",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    set_auth_cookies(response, access_token, raw_refresh)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=raw_refresh,
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(org),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    res = await db.execute(select(User).where(User.email == req.email))
    user = res.scalars().first()

    if not user or not verify_password(req.password, user.password_hash):
        raise UnauthorizedException(message="Invalid email or password")

    if not user.is_active:
        raise UnauthorizedException(message="Account has been deactivated")

    res_org = await db.execute(
        select(Organization)
        .join(Membership)
        .where(Membership.user_id == user.id)
        .limit(1)
    )
    org = res_org.scalars().first()
    if not org:
        raise BadRequestException(message="User account is not assigned to any organization")

    access_token = create_access_token(subject=user.id, extra_claims={"org_id": org.id})
    raw_refresh = os.urandom(32).hex()
    hashed_refresh = hash_token(raw_refresh)

    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_entry)

    await log_audit(
        db=db,
        organization_id=org.id,
        user_id=user.id,
        action="user_login",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    set_auth_cookies(response, access_token, raw_refresh)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=raw_refresh,
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(org),
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    refresh_token: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    raw_rt = refresh_token or request.cookies.get("refresh_token")
    if raw_rt:
        hashed = hash_token(raw_rt)
        res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
        token_rec = res.scalars().first()
        if token_rec:
            token_rec.revoked = True

    clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    response: Response,
    request: Request,
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    raw_rt = refresh_token or request.cookies.get("refresh_token")
    if not raw_rt:
        raise UnauthorizedException(message="Refresh token missing")

    hashed = hash_token(raw_rt)
    res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    token_rec = res.scalars().first()

    if not token_rec or token_rec.revoked or token_rec.expires_at < datetime.now(UTC):
        clear_auth_cookies(response)
        raise UnauthorizedException(message="Refresh token invalid or expired")

    token_rec.revoked = True

    res_user = await db.execute(select(User).where(User.id == token_rec.user_id, User.is_active))
    user = res_user.scalars().first()
    if not user:
        clear_auth_cookies(response)
        raise UnauthorizedException(message="User account inactive")

    res_org = await db.execute(
        select(Organization)
        .join(Membership)
        .where(Membership.user_id == user.id)
        .limit(1)
    )
    org = res_org.scalars().first()

    access_token = create_access_token(subject=user.id, extra_claims={"org_id": org.id if org else None})
    new_raw_refresh = os.urandom(32).hex()
    new_hashed_refresh = hash_token(new_raw_refresh)

    token_rec.replaced_by = new_hashed_refresh

    new_refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=new_hashed_refresh,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh_entry)

    set_auth_cookies(response, access_token, new_raw_refresh)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_raw_refresh,
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(org) if org else None,
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    res_mem = await db.execute(
        select(Membership).where(
            Membership.organization_id == org.id,
            Membership.user_id == current_user.id,
        )
    )
    membership = res_mem.scalars().first()

    return {
        "user": UserResponse.model_validate(current_user),
        "organization": OrganizationResponse.model_validate(org),
        "role": membership.role if membership else RoleEnum.VIEWER,
    }


@router.post("/password/change")
async def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not verify_password(req.current_password, current_user.password_hash):
        raise BadRequestException(message="Current password verification failed")

    current_user.password_hash = get_password_hash(req.new_password)

    await log_audit(
        db=db,
        organization_id=org.id,
        user_id=current_user.id,
        action="password_changed",
        resource_type="user",
        resource_id=current_user.id,
    )

    return {"message": "Password changed successfully"}


@router.post("/password/forgot")
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    res = await db.execute(select(User).where(User.email == req.email))
    user = res.scalars().first()

    if user:
        reset_token = os.urandom(16).hex()
        email_provider = get_email_provider()
        await email_provider.send_email(
            recipient=user.email,
            subject="SignalRoom Password Reset Request",
            body_html=f"<p>Use token <strong>{reset_token}</strong> to reset your password.</p>",
            body_text=f"Use token {reset_token} to reset your password.",
        )

    return {"message": "If the account exists, a password reset token has been dispatched."}
