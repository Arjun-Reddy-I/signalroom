# SignalRoom Implementation Checklist

Last updated: 2026-10-14

## Phase A — Baseline (DONE)
- [x] Inspect repository, reproduce baseline

## Phase B — Critical Fixes (DONE)
- [x] Delete stray file inal_year_projectypessignalroom.ts
- [x] Create apps/api/.env from .env.example
- [x] Add startup rejection of hardcoded SECRET_KEY in production (model_validator)
- [x] Implement password reset token storage on User model
- [x] Add POST /auth/password/reset route
- [x] Fix SQLite tz-naive datetime comparisons in auth.py and pipeline.py
- [x] Add rate limiting on login endpoint (in-memory sliding window)
- [x] Fix SMTPEmailProvider to actually send via smtplib
- [x] Add Alembic migration 002 for password_reset columns
- [x] Fix CORS_ORIGINS parsing (.env quote issue) → switched to CORS_ORIGINS_STR property

## Phase C — Upload + Processing Pipeline (DONE)
- [x] POST /api/v1/meetings/{id}/upload endpoint
- [x] GET /api/v1/meetings/{id}/job (processing job status)
- [x] Background worker (app/worker/pipeline.py) with asyncio polling loop
- [x] All 7 pipeline stages: validate → extract_audio → transcribe → analyze → persist → vector_embed → reminders
- [x] Idempotent pipeline (deletes old AI content on reprocess)
- [x] SQLite-compatible locking (sequential polling); PostgreSQL SKIP LOCKED for production
- [x] EmbeddingProvider (FallbackEmbeddingProvider + SentenceTransformersEmbeddingProvider + OpenAIEmbeddingProvider)
- [x] WhisperTranscriptionProvider (faster-whisper, CPU-compatible)
- [x] OllamaLLMProvider (local Ollama server)
- [x] OpenAILLMProvider (structured JSON output)
- [x] All providers clearly tag demo/fallback output
- [x] Reminders created for action items after pipeline completes
- [x] Notification created on pipeline completion

## Phase D — Embeddings + Search (DONE)
- [x] GET /api/v1/search?q=... (semantic + SQL full-text hybrid search)
- [x] org_id scoping on all ChromaDB queries
- [x] GET /api/v1/meetings/{id}/context (cross-meeting memory)
- [x] SearchOverlay.tsx updated to call real search API with local fallback

## Phase E — Reminders + Calendar + Agenda (DONE)
- [x] Reminder scheduling in worker loop (_process_due_reminders)
- [x] Real SMTPEmailProvider implementation
- [x] ICS calendar export GET /api/v1/meetings/{id}/calendar.ics
- [x] POST /api/v1/meetings/{id}/agenda (rule-based agenda generation)
- [x] AgendaSection component in meeting detail page

## Phase F — Frontend (DONE)
- [x] components/signalroom/dialogs/MeetingDialog.tsx (extracted)
- [x] components/signalroom/dialogs/ProjectDialog.tsx (extracted)
- [x] components/signalroom/SearchOverlay.tsx (real API search)
- [x] app/meetings/[id]/page.tsx (full meeting detail page)
- [x] Upload component with XHR progress + pipeline polling
- [x] Transcript viewer with timestamps and speakers
- [x] Summary, decisions, action items display
- [x] ICS download button
- [x] Agenda generation UI
- [x] app/forgot-password/page.tsx (calls real API)
- [x] app/reset-password/page.tsx (calls real API, handles token)
- [x] Demo output clearly labelled in UI

## Phase G — Testing (DONE)
- [x] tests/test_domain_apis.py — 2 tests (existing)
- [x] tests/test_tenant_isolation.py — 1 test (existing)
- [x] tests/test_auth_extended.py — 3 tests (password reset, rate limit, token rotation)
- [x] tests/test_upload_pipeline.py — 7 tests (upload, pipeline, search, ICS, agenda, context)
- [x] Total: 13/13 tests passing
- [x] TypeScript: 0 errors (pnpm exec tsc --noEmit)
- [x] Ruff lint: 0 errors

## Phase H — Deployment + Documentation (DONE)
- [x] apps/api/Dockerfile
- [x] Dockerfile (frontend)
- [x] docker-compose.yml (api + worker + chromadb + web)
- [x] .github/workflows/ci.yml (backend lint+test, frontend tsc+build)
- [x] apps/api/.env.example (comprehensive, all new settings documented)
- [x] docs/IMPLEMENTATION_CHECKLIST.md (this file)

## Remaining / Blocked
- [ ] faster-whisper not installed in .venv (commented out in requirements.txt)
  → Install with: pip install faster-whisper; set STT_PROVIDER=whisper in .env
- [ ] sentence-transformers not installed (commented out in requirements.txt)
  → Install with: pip install sentence-transformers; set EMBEDDING_PROVIDER=sentence_transformers
- [ ] Ollama not running (LLM_PROVIDER=fallback)
  → Install Ollama, run: ollama serve && ollama pull llama3.2; set LLM_PROVIDER=ollama
- [ ] workspace-shell.tsx refactor is partial (dialogs and search extracted; views still inline)
  → Major views (Analytics, Calendar, Team, Settings) still show ConnectedView placeholder
- [ ] Frontend E2E tests (Playwright) not implemented
- [ ] Password change form in Settings view not implemented
- [ ] Team member management UI not implemented
- [ ] Analytics chart rendering not implemented (data available via dashboard aggregates API)
