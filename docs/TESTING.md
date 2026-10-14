# SignalRoom Testing

## Running Tests

### Backend (Python / pytest)

```bash
cd apps/api
python -m pytest tests/ -v
```

**Requirements**: Python 3.12, all packages from `requirements.txt` installed. The test database is SQLite in-memory (auto-created by the session fixture in `conftest.py`).

**Environment**: The `conftest.py` forces `STT_PROVIDER=fallback`, `LLM_PROVIDER=fallback`, `EMBEDDING_PROVIDER=fallback` so no AI models are downloaded during tests.

### Frontend (TypeScript)

```bash
pnpm exec tsc --noEmit
```

### Linting

```bash
cd apps/api && ruff check app/
```

---

## Test Results (Verified 2026-10-14)

| Test | Status |
|---|---|
| `test_domain_apis::test_domain_apis` | ✅ PASSED |
| `test_tenant_isolation::test_tenant_isolation` | ✅ PASSED |
| `test_auth_extended::test_password_reset_flow` | ✅ PASSED |
| `test_auth_extended::test_rate_limiting_login` | ✅ PASSED |
| `test_auth_extended::test_refresh_token_rotation` | ✅ PASSED |
| `test_upload_pipeline::test_upload_creates_job` | ✅ PASSED |
| `test_upload_pipeline::test_duplicate_upload_rejected` | ✅ PASSED |
| `test_upload_pipeline::test_upload_invalid_extension_rejected` | ✅ PASSED |
| `test_upload_pipeline::test_pipeline_end_to_end` | ✅ PASSED |
| `test_upload_pipeline::test_search_returns_results` | ✅ PASSED |
| `test_upload_pipeline::test_ics_export` | ✅ PASSED |
| `test_upload_pipeline::test_agenda_generation` | ✅ PASSED |
| `test_upload_pipeline::test_meeting_context` | ✅ PASSED |
| **Total** | **13/13 passed** |

TypeScript check: **0 errors**
Ruff lint: **0 errors**

---

## Test Coverage by Area

### Authentication (`test_auth_extended.py`)
- Registration + login flow
- Password reset: forgot → token storage → reset → login with new password → token reuse rejected
- Rate limiting: 5 failed logins → 429 on 6th attempt
- Refresh token rotation: new token issued, DB confirms old token marked revoked

### Core Domain (`test_domain_apis.py`)
- User registration
- Project creation
- Meeting creation
- Action item creation + completion
- Dashboard aggregates

### Multi-tenant Isolation (`test_tenant_isolation.py`)
- User A cannot access Org B's data via X-Organization-ID header (403)
- Database-level: no Membership record exists for cross-org access

### Upload & Pipeline (`test_upload_pipeline.py`)
- WAV file upload → MediaFile + ProcessingJob created
- Duplicate upload on same meeting → 409 Conflict
- Invalid extension (`.exe`) → 400 Bad Request
- Full pipeline E2E: upload → `run_single_job()` → meeting status=completed, transcript/summary/decisions/action_items persisted
- Search: content indexed and retrievable after pipeline
- ICS export: valid RFC 5545 calendar file
- Agenda generation: structured items with opening + overdue + action items + decisions
- Cross-meeting context: returns related meetings, open tasks, recent decisions

---

## AI Provider Testing

Because AI models require hardware resources and model downloads, AI tests run against deterministic fallback providers. All fallback output is tagged:
- `provider: "demo-fallback"` in database records
- `[DEMO]` prefix in transcript text and summary text

To test with real AI providers:

### Whisper (STT)
```bash
# Set in apps/api/.env:
STT_PROVIDER=whisper
WHISPER_MODEL=base
# Run a manual test:
cd apps/api
python -c "
import asyncio
from pathlib import Path
from app.providers.stt import get_transcription_provider
async def test():
    p = get_transcription_provider()
    # requires a real audio file
    result = await p.transcribe(Path('test_audio.wav'))
    print(f'Segments: {len(result.segments)}')
    print(result.segments[0].text[:100])
asyncio.run(test())
"
```

### Ollama (LLM)
```bash
# Start Ollama and pull a model:
ollama serve
ollama pull llama3.2

# Set in apps/api/.env:
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2

# Test:
cd apps/api
python -c "
import asyncio
from datetime import datetime
from app.providers.llm import get_llm_provider
async def test():
    p = get_llm_provider()
    result = await p.analyze_transcript('We decided to use PostgreSQL. John will set up the database by Friday.', datetime.now())
    print(result.summary_text)
    print(f'Decisions: {len(result.decisions)}, Action items: {len(result.action_items)}')
asyncio.run(test())
"
```

---

## Missing Tests (Future Work)

- Frontend E2E tests (Playwright) — not implemented
- Reminder scheduler tests
- Email sending tests (SMTP integration)
- Performance tests (large audio files, many concurrent uploads)
- Security tests (brute force over multiple IPs, token tampering)
- AI evaluation: WER for Whisper, precision/recall for action item extraction
