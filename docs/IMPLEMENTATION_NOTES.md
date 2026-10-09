# SignalRoom Implementation Notes

## Architecture Overview
SignalRoom is an AI-powered Meeting Lifecycle Management and Workflow Automation System built with a Next.js 16 frontend and a Python FastAPI backend.

```
+-------------------------------------------------------------------+
|                        Next.js Frontend (./)                      |
| (React 19, TypeScript, Tailwind v4, Motion, TanStack / Custom API) |
+-------------------------------------------------------------------+
                                  |
                                  v REST / SSE
+-------------------------------------------------------------------+
|                       FastAPI Backend (apps/api)                  |
| (Python 3.12, Pydantic v2, SQLAlchemy 2.0 Async, OAuth2 JWT/Argon2)|
+-------------------------------------------------------------------+
          |                       |                      |
          v                       v                      v
+------------------+     +------------------+    +-------------------+
| PostgreSQL 16 DB |     |  ChromaDB Vector |    | Job Queue Worker  |
|  (Alembic Migr)  |     |     Store        |    | (SKIP LOCKED)     |
+------------------+     +------------------+    +-------------------+
```

## Repository Layout Decision
- **Frontend**: Remains at the root directory (`./`) to preserve existing Next.js layout, scripts (`pnpm dev`, `pnpm build`), and path aliases (`@/*`).
- **Backend**: Located under `apps/api/` with Python 3.12, FastAPI, SQLAlchemy async, and Alembic migrations.
- **Shared / Artifacts**: Docker compose manifests at root (`docker-compose.yml`, `docker-compose.prod.yml`), CI workflow in `.github/workflows/ci.yml`.

## Audit Findings & Baseline
- **Existing Frontend**: Clean build (`pnpm build`) and TypeScript type-check (`tsc --noEmit`). Currently uses static mock data (`data/mock/dashboard.ts`) and mock service layer (`services/dashboard.ts`).
- **Required Modifications**:
  - Remove mock service dependencies and replace with `lib/api` client.
  - Implement full page routing for `/meetings`, `/meetings/[id]`, `/action-items`, `/calendar`, `/team`, `/search`, `/analytics`, `/archive`, `/settings`, `/projects`.
  - Add authentication pages (`/login`, `/register`, `/forgot-password`, `/reset-password`).
  - Upgrade audio/video upload component to post real media files to backend and stream/poll 9-stage pipeline progress.
  - Replace raw `framer-motion` imports with `lib/motion.ts` abstractions honoring `prefers-reduced-motion`.

## Fallback Providers Strategy
All external integrations (Speech-to-Text, LLM, Embeddings, Email, Calendar) implement provider interfaces with deterministic fallbacks when external API keys are not supplied. Fallback outputs are explicitly tagged with `provider: "demo-fallback"` so fallback data is never presented as live AI results.
