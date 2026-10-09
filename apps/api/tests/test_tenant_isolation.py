import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Membership


@pytest.mark.asyncio
async def test_tenant_isolation():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]
    email_a = f"usera_{uid}@orga.com"
    email_b = f"userb_{uid}@orgb.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register User A (Org A)
        res_a = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_a,
                "password": "Password123!",
                "full_name": "User A",
                "organization_name": f"Organization A {uid}",
            },
        )
        assert res_a.status_code == 201
        data_a = res_a.json()
        token_a = data_a["access_token"]

        # 2. Register User B (Org B)
        res_b = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_b,
                "password": "Password123!",
                "full_name": "User B",
                "organization_name": f"Organization B {uid}",
            },
        )
        assert res_b.status_code == 201
        data_b = res_b.json()
        org_b_id = data_b["organization"]["id"]

        # 3. User A tries to access Org B with X-Organization-ID header
        headers = {
            "Authorization": f"Bearer {token_a}",
            "X-Organization-ID": org_b_id,
        }
        res_forbidden = await client.get("/api/v1/auth/me", headers=headers)
        assert res_forbidden.status_code == 403
        assert res_forbidden.json()["code"] == "FORBIDDEN"

        # 4. Verify DB level isolation
        async with AsyncSessionLocal() as session:
            res_mem = await session.execute(
                select(Membership).where(
                    Membership.organization_id == org_b_id,
                    Membership.user_id == data_a["user"]["id"],
                )
            )
            assert res_mem.scalars().first() is None
