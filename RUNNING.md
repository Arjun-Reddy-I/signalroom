# Running SignalRoom — Developer Guide

This guide walks you through setting up, running, and developing the SignalRoom project.

---

## 1. Prerequisites

Before you begin, ensure you have:

- **Node.js 22+** — [Download](https://nodejs.org/)
- **Python 3.12+** — [Download](https://python.org/)
- **pip** — Included with Python
- **pnpm** — Install globally: `npm install -g pnpm`

Optional (for real AI features):
- **Ollama** — [Download](https://ollama.ai) (for local LLM analysis)
- **faster-whisper** — Installed via pip (for local transcription)

---

## 2. Quick Start

### 2.1 Clone & Install Dependencies

```bash
# From repository root
pnpm install

cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Optional: Install extra dependencies for real AI (not required for demo mode)
# pip install faster-whisper
# pip install sentence-transformers
```

### 2.2 Environment Setup

Copy and configure the backend `.env` file:

```bash
cd apps/api
cp .env.example .env
```

Edit `.env`:

```env
# Required for demo mode (no API keys needed):
STT_PROVIDER=fallback
LLM_PROVIDER=fallback
EMBEDDING_PROVIDER=fallback

# Change these in production:
SECRET_KEY=signalroom-secret-key-change-this-in-production-32bytes!
ENCRYPTION_KEY=your-fernet-key-here
```

For real AI features:
- Set `STT_PROVIDER=whisper` and `OLLAMA_BASE_URL=http://localhost:11434`
- Add `OPENAI_API_KEY=...` if you have one

### 2.3 Database & Seed Data

```bash
cd apps/api
.venv\Scripts\activate
python scripts/seed.py
```

This creates the SQLite database and seeds demo data (including user `alex@signalroom.app`).

### 2.4 Start Services

SignalRoom requires three separate terminal sessions:

#### Terminal 1 — Backend API

```bash
cd apps/api
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`

#### Terminal 2 — Background Worker

```bash
cd apps/api
.venv\Scripts\activate
python -m app.worker
```

The worker processes audio uploads, runs transcription and AI analysis.

#### Terminal 3 — Frontend

```bash
cd apps/api
.venv\Scripts\activate
cd ..
pnpm dev
```

Frontend runs at `http://localhost:3000`

### 2.5 Sign In

Open `http://localhost:3000` and sign in with:

- **Email:** `alex@signalroom.app`
- **Password:** `Password123!`

---

## 3. Development Workflow

### 3.1 Running Tests

Backend tests:

```bash
cd apps/api
.venv\Scripts\activate
python -m pytest tests/ -v
```

Frontend TypeScript check:

```bash
pnpm exec tsc --noEmit
```

### 3.2 Linting & Type Checks

Backend lint:

```bash
cd apps/api
.venv\Scripts\activate
ruff check app/
```

Frontend lint (if configured):

```bash
pnpm lint
```

Type check:

```bash
pnpm exec tsc --noEmit
```

### 3.3 Building for Production

```bash
pnpm build
```

Serve the production build:

```bash
pnpm start
```

---

## 4. Project Structure

```
e:\Final_Year_Project\
├── apps/
│   └── api/                      # FastAPI backend (Python)
│       ├── app/
│       │   ├── api/              # REST API endpoints
│       │   │   ├── v1/
│       │   │   │   ├── auth.py
│       │   │   │   ├── meetings.py
│       │   │   │   ├── projects.py
│       │   │   │   ├── search.py
│       │   │   │   └── ...
│       │   │   └── ...
│       │   ├── core/             # Config, logging, exceptions
│       │   ├── db/               # Database models and session
│       │   ├── models/           # Pydantic schemas, SQLAlchemy models
│       │   ├── services/         # Business logic (transcription, LLM)
│       │   ├── worker.py         # Background job processor
│       │   └── main.py           # FastAPI app entrypoint
│       ├── scripts/
│       │   └── seed.py           # Database seeding
│       ├── tests/                # pytest test suite
│       ├── .venv/                # Virtual environment (created)
│       ├── requirements.txt
│       └── .env.example
├── app/                          # Next.js frontend (TypeScript, React)
│   ├── app/                      # Next.js app directory
│   │   ├── (auth)/               # Login, register, forgot password
│   │   ├── (dashboard)/          # Home, projects, meetings
│   │   ├── (settings)/           # User settings, integrations
│   │   ├── api/                  # API routes (rewrites to backend)
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/               # Reusable UI components
│   ├── lib/                      # Utilities, clients
│   └── types.ts
├── docs/                         # Documentation
├── .agents/                      # AI agent configuration
├── README.md
├── RUNNING.md                    # This file
├── package.json
└── .env                          # Root-level env (optional)
```

### Key Code Locations

| Feature | Location |
|---------|----------|
| Meeting CRUD | `apps/api/app/api/v1/meetings.py` |
| Audio upload & processing | `apps/api/app/services/audio.py`, `apps/api/app/workflow/` |
| Transcription | `apps/api/app/services/stt/` |
| LLM analysis | `apps/api/app/services/llm/` |
| Search | `apps/api/app/api/v1/search.py` |
| Action items | `apps/api/app/api/v1/action_items.py` |
| Frontend meetings view | `app/app/(dashboard)/meetings/[id]/page.tsx` |

---

## 5. AI Providers Configuration

### 5.1 Fallback (Demo Mode — No Setup Required)

Default configuration works out of the box. All AI output is marked `[DEMO]`.

```env
STT_PROVIDER=fallback
LLM_PROVIDER=fallback
EMBEDDING_PROVIDER=fallback
```

### 5.2 Local Speech-to-Text (faster-whisper)

```bash
cd apps/api
.venv\Scripts\activate
pip install faster-whisper
```

Edit `.env`:

```env
STT_PROVIDER=whisper
WHISPER_MODEL=base    # tiny/base/small/medium
WHISPER_DEVICE=cpu
```

Model downloads ~75–1500MB on first run.

### 5.3 Local LLM (Ollama)

1. Install [Ollama](https://ollama.ai)
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. Edit `.env`:
   ```env
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.2
   OLLAMA_BASE_URL=http://localhost:11434
   ```

### 5.4 Local Embeddings (sentence-transformers)

```bash
cd apps/api
.venv\Scripts\activate
pip install sentence-transformers
```

Edit `.env`:

```env
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Model downloads ~80MB on first run.

### 5.5 OpenAI (GPT-4o-mini)

Edit `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
```

---

## 6. Common Issues & Troubleshooting

### 6.1 Port Already in Use

**Error:** `ERROR:    Could not find a port to bind the server...`

```bash
# Windows: Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

Or change the port in your command:

```bash
uvicorn app.main:app --reload --port 8001
```

Update CORS origins in `.env` to match the new port.

### 6.2 Missing API Keys

If `OPENAI_API_KEY` is set but invalid, the backend logs warnings but falls back to demo mode.

Verify your `.env` has:

```env
OPENAI_API_KEY=sk-...
```

Test with:

```bash
cd apps/api
.venv\Scripts\activate
python -c "from app.core.config import settings; print(settings.OPENAI_API_KEY is not None and len(settings.OPENAI_API_KEY) > 0)"
```

### 6.3 Database/Schema Issues

If you see `Table 'xxx' doesn't exist` errors:

```bash
cd apps/api
.venv\Scripts\activate
python -c "from app.db.session import engine; from app.models import Base; engine.sync_engine.dispose(); import asyncio; asyncio.run(Base.metadata.create_all(engine.sync_engine))"
```

To reset the database (deletes all data):

```bash
cd apps/api
.venv\Scripts\activate
rm signalroom.db
python scripts/seed.py
```

### 6.4 ChromaDB Errors

If `chromadb` fails to initialize:

```bash
cd apps/api
.venv\Scripts\activate
pip install --force-reinstall chromadb==1.5.9
```

Verify persistence directory exists:

```bash
ls chroma_db
```

### 6.5 Frontend Not Connecting to Backend

Verify CORS in `.env`:

```env
CORS_ORIGINS_STR=http://localhost:3000,http://127.0.0.1:3000
```

Restart the backend after `.env` changes.

---

## 7. Deployment Notes

### 7.1 Environment Variables (Production)

At minimum:

```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<32-byte-random-hex>
ENCRYPTION_KEY=<fernet-key>
CORS_ORIGINS_STR=<your-domain>
STT_PROVIDER=whisper  # or fallback
LLM_PROVIDER=ollama   # or openai
OPENAI_API_KEY=<real-key-if-using>
```

### 7.2 Database

Production should use PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/signalroom
```

Run migrations:

```bash
cd apps/api
.venv\Scripts\activate
alembic upgrade head
```

### 7.3 File Storage

For production, configure cloud storage (S3, GCS, etc.):

```env
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_BUCKET_NAME=signalroom-uploads
```

### 7.4 Docker Compose

The project includes `docker-compose.yml`:

```bash
cp apps/api/.env.example apps/api/.env
# Edit .env with production values
docker compose up --build
```

---

## 8. Full Workflow Example

Here's what a typical user workflow looks like:

1. **Sign in** — `alex@signalroom.app` / `Password123!`
2. **Create a project** — e.g., "Product Team"
3. **Create a meeting** — Name it "Sprint Planning"
4. **Upload audio** — Drag a `.wav` or `.mp3` file (max 250MB)
5. **Wait for processing** — Background worker runs 7 stages:
   - Validate → Transcribe → Analyze → Persist → Embed → Reminders → Notify
6. **View results** — Open meeting detail (`/meetings/{id}`)
   - See transcript, summary, decisions, action items
   - Click "Generate Agenda" for next meeting
7. **Search** — Use Ctrl+K to search across all meetings
8. **Export** — Download `.ics` file for calendar

---

## 9. API Docs

Once the backend is running, visit:

- **Swagger UI:** `http://localhost:8000/api/v1/docs`
- **ReDoc:** `http://localhost:8000/api/v1/redoc`
- **Health:** `http://localhost:8000/api/v1/health/ready`

---

## 10. Gotchas & Best Practices

- **Backend restarts** — Changes to `.env` require a backend restart
- **Worker isolation** — The worker runs sequentially. For parallel processing, switch to PostgreSQL and use SKIP LOCKED
- **Demo mode** — All `[DEMO]` output is stored in the database and indistinguishable from real AI output (except metadata)
- **ChromaDB size** — The vector store grows over time. Periodically clean old collections if needed
- **Frontend build** — `pnpm build` creates `next.config.js`-defined output in `.next/`

---

## Need Help?

Check the logs:
- Backend: Console output (stdout/stderr)
- Frontend: Browser DevTools → Console

Review the existing documentation:
- `README.md` — Project overview and features
- `docs/QA_AUDIT_REPORT.md` — System architecture and known issues
- `apps/api/app/core/config.py` — Configuration schema