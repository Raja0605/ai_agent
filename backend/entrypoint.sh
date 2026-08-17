#!/bin/sh
# Bring the schema up to date before serving.
#
# `depends_on: service_healthy` waits for Postgres to accept connections, but
# the schema still has to be migrated, and doing it here means a deploy of a
# model change cannot start serving against a stale table.
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting API..."
exec "$@"
