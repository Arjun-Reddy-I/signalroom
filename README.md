# SignalRoom — AI Meeting Lifecycle Management Platform

SignalRoom transforms recorded meeting discussions into structured, searchable, actionable knowledge. Upload a meeting recording and SignalRoom produces a transcript, AI-generated summary, extracted decisions, and tracked action items — all linked across meetings and projects.

---

## Features

| Feature | Status |
|---|---|
| Meeting management (CRUD, status lifecycle) | ✅ Implemented |
| Multi-tenant RBAC (owner/admin/member/viewer) | ✅ Implemented |
| Audio upload + background processing pipeline | ✅ Implemented |
| Whisper transcription (local, no API key) | ✅ Implemented (requires faster-whisper) |
| LLM analysis via Ollama (local) | ✅ Implemented (requires Ollama) |
| OpenAI fallback (GPT-4o-mini) | ✅ Implemented (requires API key) |
| Semantic + full-text search | ✅ Implemented |
| Cross-meeting context retrieval | ✅ Implemented |
| Action item tracking with lifecycle | ✅ Implemented |
| Password reset with real email | ✅ Implemented |
| Rate limiting on auth endpoints | ✅ Implemented |
| ICS calendar event export | ✅ Implemented |
| Intelligent agenda generation | ✅ Implemented |
| Reminder scheduling | ✅ Implemented |
| Meeting detail page with transcript viewer | ✅ Implemented |
| Audit logging | ✅ Implemented |
| Docker Compose deployment | ✅ Implemented |
| CI pipeline (GitHub Actions) | ✅ Implemented |
| Demo/fallback mode (no API keys needed) | ✅ Implemented |

---

## Architecture

```
Next.js 16 Frontend (React 19, TypeScript, Tailwind v4)
         │  /api/* (Next.js rewrite)
         ▼
FastAPI Backend (Python 3.12, SQLAlchemy async, Pydantic v2)
    │           │              │
    ▼           ▼              ▼
SQLite/      ChromaDB       Background
PostgreSQL   Vector Store    Worker
(Alembic)    (Embeddings)   (Pipeline)
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
           faster-whisper   Ollama/     sentence-
           (STT)            OpenAI      transformers
                            (LLM)       (Embeddings)
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node 22+ with pnpm
- (Optional) [Ollama](https://ollama.ai) for real AI analysis
- (Optional) [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for real transcription

### 1. Backend setup

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# For real STT (downloads ~150MB model on first run):
pip install faster-whisper

# For real local embeddings (~80MB):
pip install sentence-transformers

cp .env.example .env
# Edit .env — see configuration section below

# Create database schema and seed demo data:
python scripts/seed.py

# Start the API server:
uvicorn app.main:app --reload --port 8000
```

### 2. Background worker (separate terminal)

```bash
cd apps/api
.venv\Scripts\activate
python -m app.worker
```

### 3. Frontend setup

```bash
# From repo root:
pnpm install
pnpm dev
```

Open http://localhost:3000. Sign in with demo credentials:
- Email: `alex@signalroom.app`
- Password: `Password123!`

---

## Configuration

Key environment variables in `apps/api/.env`:

```env
# AI Providers
STT_PROVIDER=fallback          # or: whisper
LLM_PROVIDER=fallback          # or: ollama, openai
EMBEDDING_PROVIDER=fallback    # or: sentence_transformers, openai
WHISPER_MODEL=base             # tiny/base/small/medium
LLM_MODEL=llama3.2             # model name for ollama
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=                # optional

# Security (CHANGE IN PRODUCTION)
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-fernet-key-here

# Email (optional — console log by default)
EMAIL_PROVIDER=fallback        # or: smtp
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
```

---

## Enabling Real AI

### Whisper (Speech-to-Text)
```bash
pip install faster-whisper
# In .env:
STT_PROVIDER=whisper
WHISPER_MODEL=base    # ~150MB download on first run
```

### Ollama (LLM Analysis)
```bash
# Install Ollama from https://ollama.ai
ollama serve
ollama pull llama3.2  # ~2GB download
# In .env:
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
```

### Local Embeddings (Semantic Search)
```bash
pip install sentence-transformers
# In .env:
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2  # ~80MB download
```

---

## Running the Full Workflow

1. Sign in at http://localhost:3000
2. Create a project and a meeting
3. Open the meeting detail page (`/meetings/{id}`)
4. Upload a WAV or MP3 recording
5. The background worker picks it up and runs the pipeline
6. Poll the progress bar — 7 stages: validate → transcribe → analyse → persist → embed → reminders
7. View the transcript, summary, decisions, and action items
8. Search across meetings at the Search view or via the search overlay (Ctrl+K)
9. Generate a meeting agenda for an upcoming meeting

---

## Docker Compose

```bash
# Copy and configure env vars:
cp apps/api/.env.example apps/api/.env

docker compose up --build
```

Services:
- `api` — FastAPI on port 8000
- `worker` — Background pipeline worker
- `chromadb` — Vector store on port 8001
- `web` — Next.js frontend on port 3000

---

## Testing

```bash
# Backend tests (13 tests):
cd apps/api
python -m pytest tests/ -v

# Frontend type check:
pnpm exec tsc --noEmit

# Backend lint:
cd apps/api && ruff check app/
```

**Test results (verified 2026-10-14):**
- Backend: 13/13 passing
- TypeScript: 0 errors
- Ruff: 0 errors

---

## Demo vs Real AI Output

All demo/fallback output is:
- Tagged with `provider: "demo-fallback"` in the database
- Marked with `[DEMO]` prefix in transcript and analysis text
- Shown with a visible amber warning banner in the meeting detail UI

When real AI providers are configured, output is tagged with the actual provider name (e.g., `provider: "faster-whisper"`, `provider: "ollama"`).

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Register + create organisation |
| `/auth/login` | POST | Login (rate limited) |
| `/auth/refresh` | POST | Rotate refresh token |
| `/auth/password/forgot` | POST | Request password reset |
| `/auth/password/reset` | POST | Reset with token |
| `/meetings` | GET/POST | List/create meetings |
| `/meetings/{id}` | GET/PATCH/DELETE | Meeting detail |
| `/meetings/{id}/upload` | POST | Upload audio |
| `/meetings/{id}/job` | GET | Processing job status |
| `/meetings/{id}/context` | GET | Cross-meeting context |
| `/meetings/{id}/agenda` | POST | Generate agenda |
| `/meetings/{id}/calendar.ics` | GET | ICS export |
| `/search?q=` | GET | Semantic + full-text search |
| `/action-items` | GET/POST | Action item management |
| `/decisions` | GET/POST | Decisions |
| `/dashboard/aggregates` | GET | Dashboard stats |
| `/health/ready` | GET | Health check |

Full OpenAPI docs available at `http://localhost:8000/api/v1/docs` in development mode.

---

## Known Limitations

- The background worker uses simple sequential polling (no SKIP LOCKED) with SQLite. For parallel workers, switch to PostgreSQL.
- Speaker diarization is not implemented — all speakers are labelled "Speaker 1". Use a diarization library (e.g., pyannote) to add this.
- Google Calendar OAuth integration is partially modelled but not implemented — ICS export is provided as a practical alternative.
- Frontend views for Analytics, Calendar, Team, and Settings are functional placeholders backed by real API data.
- Rate limiting uses in-memory storage — restarting the server resets attempt counters. For production, use Redis.
