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
- [x] **Phase 7** — Frontend: webhook config UI, deliveries debug viewer, theme toggle
- [x] **Phase 8** — Neotel integration (multi-format webhook adapters)
    - [x] 8.1 — `apiwha_neotel` format (rapiwha drop-in spec)
    - [x] 8.2 — `neotel_custom` format (Custom Provider, bidirectional)
    - [x] 8.3 — `/send_message.php` etc. rapiwha-compat endpoints at root
- [x] **Phase 9** — `external_neotel` format (Neotel External Application API, fully self-service)

## Neotel integration paths

The webhook format dropdown on each number's webhook page chooses how outbound
events are shaped and which inbound endpoint Neotel calls. Pick based on the
access you have on the Neotel side:

| Format | Neotel-side setup | Direction | Caveats |
|--------|-------------------|-----------|---------|
| `portal` | n/a — generic | Outbound only (JSON + HMAC) | Default for non-Neotel CRMs |
| `apiwha_neotel` | CAPIWHA account + `.config` override of apiwha host | Bidirectional | Requires Neotel admin / focal point to repoint `panel.apiwha.com` |
| `neotel_custom` | Custom Provider account with assigned channel | Bidirectional | Requires Neotel-side Custom Provider provisioning |
| `external_neotel` | Aplicación Externa (self-service, "Obtener Credenciales" button) | Customer-initiated only | No focal point needed; agents can only reply, can't start chats from the WhatsApp dropdown |

For Neotel deployments on a private network where the user can deploy VMs
internally but doesn't have shell on the Neotel server, **`external_neotel`
is the only viable path** — the others all need filesystem or DNS
modifications on the Neotel host.

## Frontend auth model

- **Access token** lives in memory only (React context). It never touches `localStorage`, so XSS can't lift it.
- **Refresh token** is set by the Next route handlers under `/api/auth/*` as an `httpOnly`, `SameSite=Lax` cookie. Browser JS can't read it.
- **Silent refresh:** on every page load the `AuthProvider` calls `POST /api/auth/refresh`, which uses the cookie to rotate the pair and returns a fresh access token plus the current user.
- **Auto retry on 401:** the API client retries the original request once after a silent refresh; if that fails too, it clears state and pushes to `/login`.
- **Edge guard:** middleware blocks protected routes when no refresh cookie is present, so unauthenticated traffic never reaches client components.

## Deploying to an internal VM (production)

**For the full top-to-bottom walkthrough (VM creation → operativo en ~40min),
ver [DEPLOY.md](DEPLOY.md).** Resumen abajo.

For Neotel customers running on a private network, the recommended deploy is a
dedicated VM **inside** that network. Neotel server reaches the VM by its
private IP, no tunnel or public host needed.

### VM sizing

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| vCPU | 2 | 4 |
| Disk | 20 GB | 50 GB |
| OS | Ubuntu 22.04 / Debian 12 | same |

### One-time setup on the VM

```bash
# 1. Install docker engine + compose plugin (Debian/Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER  # log out + in after this

# 2. Clone the repo
git clone <repo-url> /opt/whatsapp-portal
cd /opt/whatsapp-portal

# 3. Create .env (copy values from your dev .env, then change at minimum:
#    - SECRET_KEY: generate fresh, e.g. `openssl rand -hex 32`
#    - POSTGRES_PASSWORD: fresh
#    - EVOLUTION_API_KEY: fresh
#    - DATABASE_URL: update to match the new password
#    - NEXT_PUBLIC_API_BASE_URL: http://<VM-private-IP>:8000/api/v1
#    - NEXT_PUBLIC_APP_URL: http://<VM-private-IP>:3000
#    - ENVIRONMENT: production
nano .env

# 4. Build + launch the prod stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 5. Run migrations
docker compose exec backend alembic upgrade head

# 6. Smoke-check
bash deploy/check.sh
```

### Networking checklist

- VM listens on:
  - `8000` (backend) — Neotel needs to reach this
  - `3000` (frontend) — your team needs to reach this from inside the network
  - `8080` (Evolution) — optional, only needed for direct Evolution debugging
- Firewall: allow the Neotel server's IP to reach `8000/tcp`
- DNS: optional — give the VM a friendly internal hostname (e.g. `wa-portal.local`)
  and use it in `NEXT_PUBLIC_API_BASE_URL` instead of the raw IP

### Pairing the WhatsApp number

The simplest approach is **re-pair from scratch** on the new VM (~30 seconds):
- Log into the frontend at `http://<VM-IP>:3000`
- Create your number, click into the detail page, scan the QR with WhatsApp

If you need to **migrate the existing pairing** without re-scanning, copy these
docker volumes from the old host to the new VM before first start:
- `<project>_postgres_data` (auth + multi-tenant data + Evolution's tables)
- `<project>_evolution_instances` (Evolution session files)
- `<project>_redis_data` (queued jobs — usually safe to skip)

### Configuring Neotel (External Application path)

1. In Neotel: `Redes Sociales → Aplicaciones Externas` → new account
2. Click "Obtener Credenciales" → copy `ApplicationId` and `AccessToken`
3. In our portal: number's Webhook page → format `Neotel External Application`,
   paste ApplicationId + AccessToken, save
4. Copy the callback URL from the green panel
5. Paste it into Neotel's `Webhook URL` field on the same account
6. Verify: send a WhatsApp from another phone → conversation should appear in
   Neotel within ~1-2 seconds. Agent reply → arrives at the WhatsApp phone.

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
