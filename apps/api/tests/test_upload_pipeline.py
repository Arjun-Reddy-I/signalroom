"""Tests for upload endpoint, processing pipeline, search, and agenda."""
import io
import struct
import uuid
import wave

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _make_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a minimal valid WAV file in memory."""
    num_frames = int(duration_seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Write silence (zero samples)
        wf.writeframes(struct.pack(f"<{num_frames}h", *([0] * num_frames)))
    return buf.getvalue()


async def _register_and_get_headers(client: AsyncClient, uid: str) -> tuple[dict, str]:
    """Register a user and return auth headers + org_id."""
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"upload_user_{uid}@test.com",
            "password": "UploadPass123!",
            "full_name": "Upload Test User",
            "organization_name": f"Upload Org {uid}",
        },
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    org_id = res.json()["organization"]["id"]
    return {"Authorization": f"Bearer {token}"}, org_id


async def _create_meeting(client: AsyncClient, headers: dict) -> str:
    """Create a meeting and return its ID."""
    res = await client.post(
        "/api/v1/meetings",
        json={
            "title": "Test Meeting Upload",
            "scheduled_start": "2026-10-15T10:00:00Z",
            "scheduled_end": "2026-10-15T11:00:00Z",
            "mode": "remote",
        },
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_upload_creates_job():
    """Uploading a WAV file should create a MediaFile and ProcessingJob."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        wav_bytes = _make_wav_bytes()
        files = {"file": ("test_audio.wav", wav_bytes, "audio/wav")}

        res_upload = await client.post(
            f"/api/v1/meetings/{meeting_id}/upload",
            files=files,
            headers=headers,
        )
        assert res_upload.status_code == 202, f"Upload failed: {res_upload.text}"
        data = res_upload.json()
        assert data["meeting_id"] == meeting_id
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["filename"] == "test_audio.wav"

        # Job status endpoint should return the pending job
        res_job = await client.get(
            f"/api/v1/meetings/{meeting_id}/job",
            headers=headers,
        )
        assert res_job.status_code == 200
        job_data = res_job.json()
        assert job_data["meeting_id"] == meeting_id
        assert job_data["status"] in ("pending", "processing", "completed")


@pytest.mark.asyncio
async def test_duplicate_upload_rejected():
    """Second upload on same meeting in non-FAILED state should return 409."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        wav_bytes = _make_wav_bytes()
        files = {"file": ("test_audio.wav", wav_bytes, "audio/wav")}

        # First upload
        res1 = await client.post(
            f"/api/v1/meetings/{meeting_id}/upload",
            files=files,
            headers=headers,
        )
        assert res1.status_code == 202

        # Second upload — should be rejected
        files2 = {"file": ("test_audio2.wav", wav_bytes, "audio/wav")}
        res2 = await client.post(
            f"/api/v1/meetings/{meeting_id}/upload",
            files=files2,
            headers=headers,
        )
        assert res2.status_code == 409


@pytest.mark.asyncio
async def test_upload_invalid_extension_rejected():
    """Uploading a .exe file should be rejected."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        files = {"file": ("malware.exe", b"MZ binary data", "application/octet-stream")}
        res = await client.post(
            f"/api/v1/meetings/{meeting_id}/upload",
            files=files,
            headers=headers,
        )
        assert res.status_code == 400
        assert "not allowed" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    """Run the full pipeline with fallback providers and verify DB outputs."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        # Upload a WAV file
        wav_bytes = _make_wav_bytes(duration_seconds=2.0)
        files = {"file": ("pipeline_test.wav", wav_bytes, "audio/wav")}
        res_upload = await client.post(
            f"/api/v1/meetings/{meeting_id}/upload",
            files=files,
            headers=headers,
        )
        assert res_upload.status_code == 202
        job_id = res_upload.json()["job_id"]

        # Run the pipeline directly
        from app.worker.pipeline import run_single_job
        await run_single_job(job_id)

        # Verify meeting is now COMPLETED
        res_meeting = await client.get(f"/api/v1/meetings/{meeting_id}", headers=headers)
        assert res_meeting.status_code == 200
        meeting_data = res_meeting.json()
        assert meeting_data["status"] == "completed", f"Expected completed, got {meeting_data['status']}"

        # Verify transcript segments were persisted
        assert len(meeting_data["transcript_segments"]) > 0, "Expected transcript segments"

        # Verify summary was created
        assert meeting_data["summary"] is not None
        assert len(meeting_data["summary"]["summary_text"]) > 0

        # Verify action items were extracted
        assert len(meeting_data["action_items"]) > 0, "Expected action items from demo fallback"

        # Verify decisions were extracted
        assert len(meeting_data["decisions"]) > 0, "Expected decisions from demo fallback"


@pytest.mark.asyncio
async def test_search_returns_results():
    """After pipeline runs, search should find the meeting content."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        # Upload and run pipeline
        wav_bytes = _make_wav_bytes()
        files = {"file": ("search_test.wav", wav_bytes, "audio/wav")}
        res_upload = await client.post(
            f"/api/v1/meetings/{meeting_id}/upload", files=files, headers=headers
        )
        job_id = res_upload.json()["job_id"]

        from app.worker.pipeline import run_single_job
        await run_single_job(job_id)

        # Search for known content from demo fallback transcript
        res_search = await client.get(
            "/api/v1/search?q=pipeline",
            headers=headers,
        )
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["total"] > 0, "Expected search hits after pipeline"
        assert any(h["meeting_id"] == meeting_id for h in search_data["hits"])


@pytest.mark.asyncio
async def test_ics_export():
    """ICS export should return a valid calendar file."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        res = await client.get(
            f"/api/v1/meetings/{meeting_id}/calendar.ics",
            headers=headers,
        )
        assert res.status_code == 200
        assert "text/calendar" in res.headers["content-type"]
        content = res.text
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "Test Meeting Upload" in content


@pytest.mark.asyncio
async def test_agenda_generation():
    """Agenda generation should return structured agenda items."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        res = await client.post(
            f"/api/v1/meetings/{meeting_id}/agenda",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["meeting_id"] == meeting_id
        assert len(data["items"]) > 0
        # First item should always be the opening
        assert data["items"][0]["source_type"] == "overview"


@pytest.mark.asyncio
async def test_meeting_context():
    """Cross-meeting context endpoint should return structured data."""
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())[:8]

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers, _ = await _register_and_get_headers(client, uid)
        meeting_id = await _create_meeting(client, headers)

        res = await client.get(
            f"/api/v1/meetings/{meeting_id}/context",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "meeting_id" in data
        assert "related_meetings" in data
        assert "open_action_items" in data
        assert "recent_decisions" in data
