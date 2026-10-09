# Signalroom

Signalroom is a full-stack operational workspace for a creative studio and SaaS-style delivery team. It combines a Next.js dashboard with a FastAPI backend for authentication, project management, meetings, decisions, action items, and aggregated workspace metrics.

## Product overview

- Frontend: Next.js 16 + React 19 + TypeScript + Tailwind CSS
- Backend: FastAPI + SQLAlchemy + Alembic + SQLite by default
- Core flows: login, dashboard aggregates, project CRUD, action items, decisions, meetings, and notifications
- Typical seed account: `alex@signalroom.app` / `Password123!`

## Prerequisites

- Node.js 20.9+
- pnpm 10+
- Python 3.12+
- Git

## Quick start

### 1) Install frontend dependencies

```powershell
cd E:\Final_Year_Project
pnpm install
```

### 2) Set up the backend environment

```powershell
cd E:\Final_Year_Project\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3) Start the backend

```powershell
cd E:\Final_Year_Project\apps\api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4) Start the frontend

```powershell
cd E:\Final_Year_Project
pnpm dev
```

The app is available at `http://localhost:3000`, and the API docs are available at `http://127.0.0.1:8000/docs`.

## Useful commands

```powershell
# Frontend
pnpm dev
pnpm build
pnpm start

# Backend
cd apps\api
.\.venv\Scripts\Activate.ps1
pytest -q
uvicorn app.main:app --reload
```

## Project structure

```text
app/                  Next.js app router frontend
apps/api/            FastAPI backend and persistence layer
components/          Reusable UI and dashboard shell modules
data/                Seed and mock data
lib/                 Frontend utilities and client configuration
services/            Dashboard and API service wrappers
types/               Shared TypeScript domain types
```

## Deployment notes

This repository is set up as a monorepo for local development and GitHub deployment. The frontend proxy points to the local API, and the backend is intended to run separately from the Next.js app for a clean separation of concerns.

## Verification

The project has been validated with:

```powershell
cd E:\Final_Year_Project
pnpm build
cd apps\api
python -m pytest -q
```

These checks should complete successfully before publishing or pushing a release branch.
pnpm build
```

Then manually check:

- Desktop layout at a wide viewport.
- Mobile layout below 760px wide.
- Keyboard navigation and visible focus states.
- Project filtering and empty results.
- New project validation and creation.
- Refresh behavior and any expected data persistence.
- Reduced-motion behavior when the operating system preference is enabled.

## Current Limitations

This is currently a front-end prototype rather than a complete production dashboard:

- Dashboard data comes from static mock data.
- New projects are not persisted.
- Calendar, Team, Archive, Settings, and Analytics currently use structured frontend states while their backend workflows are pending.
- Meeting recording, transcription, AI processing, calendar sync, semantic search, and notifications are represented by typed mock boundaries rather than live integrations.
- Several labels, dates, statistics, and workspace details remain demo values.
- There is no automated test suite or lint command yet.

These limitations are useful signposts for the next development phase: establish a persistent data model, implement the secondary views, centralize derived statistics, and add automated validation before deployment.

## License

No license file is currently included in the project.
