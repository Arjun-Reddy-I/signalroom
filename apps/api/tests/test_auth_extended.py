"""Extended auth tests: password reset, rate limiting, token rotation."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_password_reset_flow():
    """Test forgot → reset password end-to-end."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]
    email = f"reset_user_{uid}@test.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register
        res_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "OldPassword123!",
                "full_name": "Reset Test User",
                "organization_name": f"Reset Org {uid}",
            },
        )
        assert res_reg.status_code == 201

        # Forgot password — stores hashed token in DB
        res_forgot = await client.post(
            "/api/v1/auth/password/forgot",
            json={"email": email},
        )
        assert res_forgot.status_code == 200
        assert "dispatched" in res_forgot.json()["message"]

        # Retrieve the stored hash from DB and derive a known token
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import select

        from app.core.security import hash_token
        from app.db.session import AsyncSessionLocal
        from app.models import User

        plain_token = f"test-reset-token-{uid}"
        async with AsyncSessionLocal() as session:
            res_user = await session.execute(select(User).where(User.email == email))
            user = res_user.scalars().first()
            assert user is not None
            # Override with our known plain token (hashed)
            user.password_reset_token_hash = hash_token(plain_token)
            user.password_reset_expires_at = datetime.now(UTC) + timedelta(minutes=30)
            await session.commit()

        # Reset with wrong token — should fail
        res_bad = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": "completely-wrong-token", "new_password": "NewPassword456!"},
        )
        assert res_bad.status_code == 400

        # Reset with correct token
        res_reset = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": plain_token, "new_password": "NewPassword456!"},
        )
        assert res_reset.status_code == 200, f"Reset failed: {res_reset.text}"

        # Login with new password
        res_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "NewPassword456!"},
        )
        assert res_login.status_code == 200, f"Login after reset failed: {res_login.text}"

        # Token should be consumed — using it again should fail
        res_reset2 = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": plain_token, "new_password": "AnotherPass789!"},
        )
        assert res_reset2.status_code == 400


@pytest.mark.asyncio
async def test_rate_limiting_login():
    """Test that repeated failed logins trigger rate limiting."""
    from app.core.rate_limit import _attempt_log

    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]
    email = f"ratelimit_user_{uid}@test.com"

    # Clear any stale state
    _attempt_log.clear()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register the user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "ValidPass123!",
                "full_name": "Rate Limit Test",
                "organization_name": f"RL Org {uid}",
            },
        )

        # Send 5 failed login attempts (wrong password)
        for _ in range(5):
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "WrongPassword!"},
            )
            assert res.status_code in (401, 429)

        # 6th attempt should be rate limited
        res_limited = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        assert res_limited.status_code == 429
        assert "RATE_LIMITED" in res_limited.json().get("code", "")

    _attempt_log.clear()


@pytest.mark.asyncio
async def test_refresh_token_rotation():
    """Test that refresh tokens are rotated and new tokens work."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register
        res_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"refresh_user_{uid}@test.com",
                "password": "Refresh123!",
                "full_name": "Refresh Test",
                "organization_name": f"Refresh Org {uid}",
            },
        )
        assert res_reg.status_code == 201
        old_refresh = res_reg.json()["refresh_token"]
        old_access = res_reg.json()["access_token"]

        # Use the refresh token to get a new one
        res_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert res_refresh.status_code == 200
        new_refresh = res_refresh.json()["refresh_token"]
        new_access = res_refresh.json()["access_token"]

        # New refresh token should be different
        assert new_refresh != old_refresh
        # Access tokens may be identical if generated in the same second (same exp)
        # Just verify new_access is a valid JWT and new_refresh works

        # New token should be usable
        res_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert res_me.status_code == 200

        # Verify in DB that old token is marked revoked
        from sqlalchemy import select

        from app.core.security import hash_token
        from app.db.session import AsyncSessionLocal
        from app.models import RefreshToken

        async with AsyncSessionLocal() as session:
            old_hash = hash_token(old_refresh)
            res_tok = await session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == old_hash)
            )
            old_tok = res_tok.scalars().first()
            assert old_tok is not None
            assert old_tok.revoked is True, "Old refresh token should be marked revoked"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_session_and_clears_cookie_auth():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        registered = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"logout_user_{uid}@test.com",
                "password": "Logout123!",
                "full_name": "Logout Test",
                "organization_name": f"Logout Org {uid}",
            },
        )
        assert registered.status_code == 201
        refresh_token = registered.json()["refresh_token"]

        logged_out = await client.post(
            "/api/v1/auth/logout",
            params={"refresh_token": refresh_token},
        )
        assert logged_out.status_code == 200
        assert (await client.get("/api/v1/auth/me")).status_code == 401
        assert (
            await client.post(
                "/api/v1/auth/refresh",
                params={"refresh_token": refresh_token},
            )
        ).status_code == 401


@pytest.mark.asyncio
async def test_malformed_access_token_has_generic_public_error():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer malformed-token"},
        )

    assert response.status_code == 401
    assert "Not enough segments" not in response.text
    assert response.json()["message"] == "Invalid or expired access token"
