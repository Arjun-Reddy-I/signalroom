import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_domain_apis():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register user
        res_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"domain_user_{uid}@test.com",
                "password": "Password123!",
                "full_name": "Domain Test User",
                "organization_name": f"Domain Org {uid}",
            },
        )
        assert res_reg.status_code == 201
        token = res_reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Projects CRUD
        res_proj = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project Alpha", "client": "Client X", "description": "Desc"},
            headers=headers,
        )
        assert res_proj.status_code == 201
        project_id = res_proj.json()["id"]

        # 2. Meetings CRUD
        res_m = await client.post(
            "/api/v1/meetings",
            json={
                "title": "Strategy Meeting 1",
                "project_id": project_id,
                "description": "Weekly sync",
                "scheduled_start": "2026-10-02T10:00:00Z",
                "scheduled_end": "2026-10-02T11:00:00Z",
                "mode": "remote",
            },
            headers=headers,
        )
        assert res_m.status_code == 201
        meeting_id = res_m.json()["id"]

        # 3. Action Items CRUD & Complete
        res_ai = await client.post(
            "/api/v1/action-items",
            json={
                "meeting_id": meeting_id,
                "title": "Setup CI pipeline",
                "priority": "high",
                "status": "open",
            },
            headers=headers,
        )
        assert res_ai.status_code == 201
        ai_id = res_ai.json()["id"]

        # Complete Action Item
        res_comp = await client.post(f"/api/v1/action-items/{ai_id}/complete", headers=headers)
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "completed"

        # 4. Dashboard Aggregates
        res_dash = await client.get("/api/v1/dashboard/aggregates", headers=headers)
        assert res_dash.status_code == 200
        data_dash = res_dash.json()
        assert data_dash["total_meetings"] >= 1
        assert data_dash["active_projects"] >= 1
