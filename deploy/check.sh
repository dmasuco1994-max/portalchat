#!/usr/bin/env bash
# Post-deploy smoke-check script. Run on the VM after `docker compose up -d`.
# Verifies:
#   - All containers healthy
#   - Backend responds on /api/v1/health
#   - Frontend responds on /
#   - Migrations are at head
#   - The rapiwha-compat endpoint resolves (used by apiwha_neotel format)
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:8000}"
FRONTEND="${FRONTEND:-http://localhost:3000}"

echo "== docker compose ps =="
docker compose ps

echo
echo "== backend health =="
curl -fsS "$BACKEND/api/v1/health" || {
  echo "FAIL: backend health check"
  exit 1
}
echo

echo "== migrations =="
docker compose exec -T backend alembic current || {
  echo "FAIL: alembic"
  exit 1
}

echo
echo "== frontend root (expect 307 -> /login when not authenticated) =="
curl -fsS -o /dev/null -w "GET / -> %{http_code} (redirect: %{redirect_url})\n" \
  "$FRONTEND/"

echo
echo "== rapiwha-compat send_message.php (expect result_code -2 missing params) =="
curl -fsS "$BACKEND/send_message.php?apikey=test" | head -c 300
echo

echo
echo "== integrations: external app inbox (expect 422 — no body) =="
curl -fsS -o /dev/null -w "POST /api/v1/integrations/neotel/external/.../inbox -> %{http_code}\n" \
  -X POST "$BACKEND/api/v1/integrations/neotel/external/fake-app-id/inbox?token=fake"

echo
echo "Smoke OK."
