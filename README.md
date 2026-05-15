# WhatsApp Portal

Multi-tenant WhatsApp gateway portal built on top of Evolution API.

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| WhatsApp | Evolution API v2 |
| Containers | Docker Compose |
| Frontend (later) | Next.js 15 + Tailwind + shadcn/ui |

## Quick start

1. Copy environment variables and edit the secrets:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Build and start all services:

   ```powershell
   docker compose up -d --build
   ```

3. Verify everything is up:

   - Backend health: http://localhost:8000/api/v1/health
   - Backend API docs (Swagger): http://localhost:8000/docs
   - Evolution API: http://localhost:8080
   - Postgres: `localhost:5432` (user `portal`)
   - Redis: `localhost:6379`

## Project structure

```
backend/              FastAPI application
  app/
    api/v1/           Versioned API routes
    core/             Configuration, security helpers
    db/               Database session, base (Phase 2+)
    models/           SQLAlchemy ORM models (Phase 2+)
    schemas/          Pydantic request/response schemas (Phase 2+)
    services/         Business logic (Phase 2+)
postgres/             Postgres init scripts
docker-compose.yml    Service orchestration
.env.example          Environment variables template
```

## Development phases

- [x] **Phase 1** — Base setup: Docker Compose with Postgres + Redis + Evolution API + FastAPI hello-world
- [ ] **Phase 2** — Auth + multi-tenancy + user CRUD (ABM)
- [ ] **Phase 3** — WhatsApp number management (Evolution instances, QR scan flow)
- [ ] **Phase 4** — Incoming webhook router + message persistence
- [ ] **Phase 5** — Outgoing REST API + webhook queue to external CRMs
- [ ] **Phase 6** — Frontend: login, dashboard, QR scanner, conversation viewer
- [ ] **Phase 7** — Frontend: webhook config UI, theming polish

## Useful commands

```powershell
# View logs of all services
docker compose logs -f

# View logs of one service
docker compose logs -f backend

# Restart just the backend
docker compose restart backend

# Stop everything (keeps data)
docker compose down

# Stop and wipe data (DANGER)
docker compose down -v
```
