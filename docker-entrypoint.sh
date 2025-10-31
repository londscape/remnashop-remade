#!/bin/sh

set -e

echo "Migrating database..."

if ! alembic -c src/infrastructure/database/alembic.ini upgrade head; then
    echo "Database migration failed! Exiting container..."
    exit 1
fi

echo "Migrations deployed successfully!"

UVICORN_RELOAD_ARGS=""
if [ "$UVICORN_RELOAD_ENABLED" = "true" ]; then
  echo "Uvicorn will run with reload enabled."
  UVICORN_RELOAD_ARGS="--reload --reload-dir /opt/remnashop/src --reload-dir /opt/remnashop/assets --reload-include *.ftl"
else
  echo "Uvicorn will run without reload."
fi

exec uvicorn src.__main__:application --host "${APP_HOST}" --port "${APP_PORT}" --factory --use-colors ${UVICORN_RELOAD_ARGS}