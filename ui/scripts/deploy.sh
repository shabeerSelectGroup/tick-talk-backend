#!/usr/bin/env bash
# Server-side deploy for TickTalk frontend (Vite + nginx static dist).
# Prefer GitHub Actions (.github/workflows/deploy.yml): builds in CI and uploads dist.
# This script is a manual fallback only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"

echo "==> Deploying TickTalk frontend in $ROOT (branch: $BRANCH)"

export PATH="/usr/local/bin:/usr/bin:$HOME/.local/bin:$PATH"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1090,SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
[ -s "$HOME/.bashrc" ] && . "$HOME/.bashrc" 2>/dev/null || true

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node not found for user $(whoami)."
  exit 1
fi
echo "Using node $(node -v) as $(whoami)"

if [[ ! -f "$ROOT/.env.production" ]]; then
  echo "ERROR: .env.production missing at $ROOT/.env.production"
  exit 1
fi

echo "==> Fetch latest code"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "==> Install dependencies"
if [[ -f yarn.lock ]] && command -v yarn >/dev/null 2>&1; then
  yarn install --frozen-lockfile || yarn install
elif [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

echo "==> Build production bundle"
npm run build

if [[ ! -d "$ROOT/dist" ]] || [[ -z "$(ls -A "$ROOT/dist" 2>/dev/null || true)" ]]; then
  echo "ERROR: dist/ missing or empty after build"
  exit 1
fi

echo "==> Deploy complete (nginx serves $ROOT/dist)"
