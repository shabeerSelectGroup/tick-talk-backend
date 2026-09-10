#!/usr/bin/env bash
# Build ui/ and publish static files for nginx (manual fallback).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI_DIR="${ROOT}/ui"
UI_DIST="${UI_DIST:-/home/deploy/apps/ticktalk/dist}"

if [[ ! -f "${UI_DIR}/package.json" ]]; then
  echo "ERROR: ui/ missing at ${UI_DIR}"
  exit 1
fi

export PATH="/usr/local/bin:/usr/bin:$HOME/.local/bin:$PATH"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1090,SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node not found"
  exit 1
fi

echo "==> Building TickTalk UI with node $(node -v)"
cd "$UI_DIR"

if command -v yarn >/dev/null 2>&1 && [[ -f yarn.lock ]]; then
  yarn install --frozen-lockfile || yarn install
  yarn build
else
  npm ci
  npm run build
fi

if [[ ! -d "${UI_DIR}/dist" ]]; then
  echo "ERROR: ui/dist missing after build"
  exit 1
fi

echo "==> Publishing UI to ${UI_DIST}"
mkdir -p "$UI_DIST"
rsync -a --delete "${UI_DIR}/dist/" "$UI_DIST/" 2>/dev/null || {
  rm -rf "${UI_DIST:?}"/*
  cp -a "${UI_DIR}/dist/." "$UI_DIST/"
}
chown -R deploy:deploy "$UI_DIST" 2>/dev/null || true
echo "==> UI deploy complete"
