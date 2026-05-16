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

   - Frontend: http://localhost:3000
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
    db/               Database session, base
    models/           SQLAlchemy ORM models
    schemas/          Pydantic request/response schemas
    services/         Business logic
    workers/          arq background workers
frontend/             Next.js 15 App Router app
  src/
    app/              Route groups: (auth) public, (app) protected
      api/auth/       Route handlers that proxy backend auth and set the
                      httpOnly refresh cookie
    components/
      providers/      AuthProvider, QueryProvider, ThemeProvider
      ui/             shadcn/ui primitives
      app/            App shell (header, etc.)
    lib/
      api/            Browser-side API client with silent refresh
      auth/           Server-side helpers for the route handlers
postgres/             Postgres init scripts
docker-compose.yml    Service orchestration
```

## Development phases

- [x] **Phase 1** — Base setup: Docker Compose with Postgres + Redis + Evolution API + FastAPI hello-world
- [x] **Phase 2** — Auth + multi-tenancy + user CRUD (ABM)
- [x] **Phase 3** — WhatsApp number management (Evolution instances, QR scan flow)
- [x] **Phase 4** — Incoming webhook router + message persistence
- [x] **Phase 5** — Outgoing REST API + webhook queue to external CRMs
- [x] **Phase 6** — Frontend: login, dashboard, QR scanner, conversation viewer
    - [x] 6.1 — Bootstrap: Next.js + auth (login/signup) + protected shell + API client
    - [x] 6.2 — Numbers + QR
    - [x] 6.3 — Conversation viewer
- [ ] **Phase 7** — Frontend: webhook config UI, theming polish

## Frontend auth model

- **Access token** lives in memory only (React context). It never touches `localStorage`, so XSS can't lift it.
- **Refresh token** is set by the Next route handlers under `/api/auth/*` as an `httpOnly`, `SameSite=Lax` cookie. Browser JS can't read it.
- **Silent refresh:** on every page load the `AuthProvider` calls `POST /api/auth/refresh`, which uses the cookie to rotate the pair and returns a fresh access token plus the current user.
- **Auto retry on 401:** the API client retries the original request once after a silent refresh; if that fails too, it clears state and pushes to `/login`.
- **Edge guard:** middleware blocks protected routes when no refresh cookie is present, so unauthenticated traffic never reaches client components.

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
