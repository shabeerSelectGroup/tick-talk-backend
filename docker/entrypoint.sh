#!/bin/sh
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi
if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "Seeding database..."
  python -m scripts.seed
fi
exec "$@"
