#!/usr/bin/env bash
# Server-side deploy for TickTalk API (FastAPI + supervisor uvicorn).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"
VENV="${ROOT}/venv"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
SERVER_ENV="${ROOT}/.env.server"

echo "==> Deploying TickTalk API in $ROOT (branch: $BRANCH)"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "ERROR: venv missing at $VENV"
  exit 1
fi

if [[ ! -f "$SERVER_ENV" ]]; then
  echo "ERROR: durable server env missing at $SERVER_ENV"
  echo "Create it once (copy of production .env) so deploys do not wipe secrets."
  exit 1
fi

echo "==> Fetch latest code"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

# .env is tracked in this repo with docker defaults — always restore production env
cp -a "$SERVER_ENV" "$ROOT/.env"
chmod 600 "$ROOT/.env"

echo "==> Install Python dependencies"
"$VENV/bin/pip" install -q -r requirements.txt

if [[ "$RUN_MIGRATIONS" == "true" ]]; then
  echo "==> Run migrations"
  if ! "$VENV/bin/alembic" upgrade head; then
    echo "WARN: alembic upgrade failed — continuing with restart"
  fi
fi

echo "==> Allow large selfie uploads in nginx (default is 1MB)"
NGINX_SNIPPET="/etc/nginx/conf.d/ticktalk-uploads.conf"
REPO_SNIPPET="${ROOT}/deploy/nginx-uploads.conf"
if [[ -d /etc/nginx/conf.d && -f "$REPO_SNIPPET" ]]; then
  if sudo cp "$REPO_SNIPPET" "$NGINX_SNIPPET" \
    && sudo nginx -t \
    && sudo systemctl reload nginx; then
    echo "nginx client_max_body_size set to 25m"
  else
    echo "WARN: could not update nginx upload limit."
    echo "On the API host run:"
    echo "  sudo cp $REPO_SNIPPET $NGINX_SNIPPET && sudo nginx -t && sudo systemctl reload nginx"
  fi
fi

echo "==> Restart supervisor program ticktalk"
sudo /usr/bin/supervisorctl restart ticktalk
sleep 2
sudo /usr/bin/supervisorctl status ticktalk

echo "==> Health check"
ok=0
for attempt in $(seq 1 30); do
  if curl -sf --max-time 5 "http://127.0.0.1:8108/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" -ne 1 ]]; then
  echo "ERROR: API health check failed on :8108"
  sudo /usr/bin/supervisorctl status ticktalk || true
  tail -n 40 /var/log/ticktalk-api.err.log || true
  exit 1
fi

echo "==> Deploy complete"
