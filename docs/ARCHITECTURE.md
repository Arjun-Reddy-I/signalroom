# SignalRoom Architecture

## Overview

SignalRoom is a two-tier web application with a React/Next.js frontend and a Python FastAPI backend, connected via a REST API. Audio processing runs in a separate background worker process.

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (Next.js 16, React 19, TypeScript, Tailwind v4)    │
│  Route: /              SPA shell (dashboard, meetings, tasks)│
│  Route: /meetings/[id] Full meeting detail + upload          │
│  Route: /login /register /forgot-password /reset-password   │
└──────────────────────────┬───────────────────────────────────┘
                           │  /api/* → Next.js rewrite proxy
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI (Python 3.12)  apps/api/app/main.py                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │  auth    │ │ meetings │ │ projects │ │ action_items  │  │
│  │  /login  │ │ /upload  │ │  CRUD    │ │  lifecycle    │  │
│  │  /reset  │ │ /job     │ │          │ │               │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ decisions│ │  search  │ │  agenda  │ │  dashboard    │  │
│  │          │ │ hybrid   │ │  gen     │ │  aggregates   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
   ┌──────────────┐  ┌──────────┐  ┌─────────────────────┐
   │  SQLite /    │  │ ChromaDB │  │  Background Worker  │
   │  PostgreSQL  │  │ (vectors)│  │  app/worker/        │
   │  (Alembic)   │  │          │  │  pipeline.py        │
   └──────────────┘  └──────────┘  └──────────┬──────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                ▼                ▼
                     ┌──────────────┐  ┌────────────┐  ┌──────────────┐
                     │ faster-whisper│  │   Ollama   │  │ sentence-    │
                     │ (STT, local) │  │  (LLM,     │  │ transformers │
                     │              │  │  local)    │  │ (Embeddings) │
                     └──────────────┘  └────────────┘  └──────────────┘
```

## Data Flow: Meeting Recording → Actionable Knowledge

```
1. User uploads WAV/MP3 via POST /meetings/{id}/upload
   ↓
2. MediaFile record created, ProcessingJob enqueued (status=PENDING)
   ↓
3. Background worker claims job (SQLite: sequential; PostgreSQL: SKIP LOCKED)
   ↓
4. Stage VALIDATE_MEDIA: check file exists on disk
5. Stage EXTRACT_AUDIO: pass file to STT (WAV/MP3 pass-through; ffmpeg for others)
6. Stage TRANSCRIBE: faster-whisper → TranscriptSegment records
7. Stage ANALYZE: Ollama/OpenAI → Summary + Decisions + ActionItems (Pydantic-validated)
8. Stage PERSIST: write all records to database (idempotent, deletes prior AI content)
9. Stage VECTOR_EMBED: embed each segment + summary → ChromaDB + MeetingEmbedding records
10. Stage REMINDERS: create Reminder records for action items with due dates
    → Notification created for meeting creator
   ↓
11. Meeting status → COMPLETED, Job status → COMPLETED
   ↓
12. User sees transcript, summary, decisions, action items on /meetings/{id}
   ↓
13. Search: GET /search?q= queries ChromaDB (semantic) + SQL LIKE (full-text)
14. Context: GET /meetings/{id}/context returns related meetings + open tasks
15. Agenda: POST /meetings/{id}/agenda generates structured agenda from task history
```

## Key Design Decisions

**Multi-tenancy**: Every DB record has `organization_id`. All queries are scoped by org. `RoleChecker` dependency enforces RBAC on every protected route. Tenant isolation is tested in `tests/test_tenant_isolation.py`.

**Provider abstractions**: STT, LLM, Embeddings, Email, and Storage all implement ABC interfaces with labelled fallbacks. Demo fallback output is tagged `[DEMO]` in text and `provider: "demo-fallback"` in DB records. This allows zero-configuration startup while clearly distinguishing real AI output.

**Idempotent pipeline**: On re-upload, the pipeline deletes prior AI-generated content (transcript segments, summary, decisions, AI action items where `confidence < 1.0`) before persisting new results. Manual action items (`confidence = 1.0`) are preserved.

**SQLite ↔ PostgreSQL compatibility**: The app runs on both. The worker uses simple `SELECT + UPDATE` for SQLite and `SELECT FOR UPDATE SKIP LOCKED` for PostgreSQL. Datetime comparisons are normalised to UTC-aware throughout.

**JWT + rotating refresh tokens**: Access tokens expire in 30 minutes. Refresh tokens are SHA-256 hashed in the DB, single-use, and rotated on each `/auth/refresh` call. The old token is marked `revoked=True` and linked via `replaced_by`.

## Component Responsibilities

| Component | Location | Responsibility |
|---|---|---|
| API routes | `apps/api/app/api/v1/` | HTTP interface, auth, validation |
| Domain models | `apps/api/app/models/domain.py` | SQLAlchemy ORM, relationships |
| Schemas | `apps/api/app/schemas/` | Pydantic request/response shapes |
| Providers | `apps/api/app/providers/` | AI and external service abstractions |
| Worker | `apps/api/app/worker/pipeline.py` | Async background pipeline execution |
| State machine | `apps/api/app/services/state_machine.py` | Meeting/action item status transitions |
| Audit | `apps/api/app/services/audit.py` | Structured event logging |
| Vector store | `apps/api/app/db/vector_store.py` | ChromaDB client initialisation |
| Frontend shell | `components/signalroom/workspace-shell.tsx` | SPA shell, navigation, view routing |
| Dashboard data | `services/dashboard.ts` | API fetch + type mapping for dashboard |
| API client | `lib/api/client.ts` | Typed fetch wrapper with auth headers |
